from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from benchmark.arms import DEFAULT_EXPERIMENT_ARMS, arm_includes, get_arm
from benchmark.collect import collect_run, write_checkpoint_jsons
from benchmark.manifest import build_manifest, write_manifest
from benchmark.paths import (
    CONFIGS_DIR,
    DEFAULT_AGENT,
    DEFAULT_MODEL,
    DEFAULT_PROBLEM,
    DEFAULT_PROVIDER,
    DEFAULT_THINKING,
    PROBLEMS_DIR,
    REPO_ROOT,
    RESULTS_DIR,
    SCB_DIR,
    SUPPORTED_AGENTS,
)
from benchmark.resume_state import (
    clear_stale_resume_artifacts,
    detect_native_resume,
    latest_state,
    load_state,
    read_json_dict,
    run_dirs,
    verify_selection_against_state,
    write_state,
)
from benchmark.rework import record_rework_events
from benchmark.rework_hook import (
    DEFAULT_FEEDBACK_STRATEGY,
    FEEDBACK_STRATEGIES,
    LEGACY_FEEDBACK_STRATEGY,
)
from benchmark.versions import load_arm_meta, load_pins

# SCB ResolvedRunConfig accepts only none/disabled/low/medium/high/xhigh.
# Codex gpt-5.6-luna also supports effort=max; map + force via agent extra_args.
_SCB_THINKING_ALIASES = {
    "max": "xhigh",
}
DEFAULT_REWORK_ATTEMPTS = 2
DEFAULT_TRANSIENT_RETRIES = 0


def _scb_thinking(thinking: str) -> str:
    return _SCB_THINKING_ALIASES.get(thinking, thinking)


def new_experiment_id(prefix: str | None = None) -> str:
    """Return a collision-resistant id for a new experiment."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    suffix = uuid.uuid4().hex[:8]
    return f"{prefix}-{stamp}-{suffix}" if prefix else f"{stamp}-{suffix}"


def resolve_run_selection(
    *,
    agent: str | None,
    arm: str,
    provider: str | None,
    model: str | None,
    thinking: str | None,
) -> tuple[str, str, str, str]:
    """Resolve agent/provider/model/thinking.

    Codex keeps historical defaults when flags are omitted.
    OpenCode requires explicit --provider and --model; thinking defaults to none.
    """
    agent = DEFAULT_AGENT if agent is None else agent
    if agent not in SUPPORTED_AGENTS:
        raise ValueError(
            f"unsupported agent {agent!r}; expected one of: {', '.join(SUPPORTED_AGENTS)}"
        )

    if agent == "opencode":
        if not provider:
            raise ValueError(
                "OpenCode requires --provider (e.g. --provider opencode_auth)"
            )
        if not model:
            raise ValueError(
                "OpenCode requires --model (e.g. --model deepseek-v4-flash-free)"
            )
        return agent, provider, model, thinking if thinking is not None else "none"

    return (
        DEFAULT_AGENT,
        provider if provider is not None else DEFAULT_PROVIDER,
        model if model is not None else DEFAULT_MODEL,
        thinking if thinking is not None else DEFAULT_THINKING,
    )


def _agent_config_path(agent: str) -> Path:
    if agent == "opencode":
        return CONFIGS_DIR / "agent_opencode.yaml"
    return CONFIGS_DIR / "agent_codex.yaml"


def _agent_config_for_thinking(agent: str, thinking: str, output_dir: Path) -> Path:
    """Return agent yaml; for Codex thinking=max, pin reasoning effort to max."""
    base = _agent_config_path(agent)
    if agent != "codex" or thinking != "max":
        return _resolve_config_paths(base)
    import yaml

    data = yaml.safe_load(base.read_text(encoding="utf-8"))
    extra = list(data.get("extra_args") or [])
    extra.extend(["--config", 'model_reasoning_effort="max"'])
    data["extra_args"] = extra
    out = output_dir / "agent_codex.max.yaml"
    out.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return out


def _agent_version(agent: str, pins: dict[str, Any]) -> str | None:
    if agent == "opencode":
        return pins.get("opencode_cli_version")
    return pins.get("codex_cli_host_version")


def _arm_config(arm: str) -> Path:
    return get_arm(arm).config_path


def _resolve_config_paths(config_path: Path) -> Path:
    """Return absolute config path; SCB resolves relative paths from CWD."""
    return config_path if config_path.is_absolute() else (REPO_ROOT / config_path)


def _environment_config(arm: str) -> Path:
    """Resolve Docker environment yaml for an arm (absolute path for SCB)."""
    if arm_includes(arm, "supermemory"):
        return CONFIGS_DIR / "environments" / "docker-python3.12-uv-hostnet.yaml"
    local = CONFIGS_DIR / "environments" / "docker-python3.12-uv.yaml"
    return local if local.is_file() else SCB_DIR / "configs" / "environments" / "docker-python3.12-uv.yaml"


@dataclass
class RunContext:
    """Resolved identity and lifecycle inputs for one benchmark run."""

    experiment_id: str
    arm: str
    problem: str
    run_index: int
    output_dir: Path
    run_id: str
    agent: str
    model: str
    provider: str
    thinking: str
    rework_attempts: int
    transient_retries: int
    feedback_strategy: str
    problems_path: Path | None
    pins: dict[str, Any]

    @property
    def selection(self) -> dict[str, str]:
        return {
            "agent": self.agent,
            "model": self.model,
            "provider": self.provider,
            "thinking": self.thinking,
        }

    def persist(self, *, phase: str, exit_code: int | None = None) -> Path:
        """Persist one lifecycle transition for this run."""
        return write_state(
            output_dir=self.output_dir,
            experiment_id=self.experiment_id,
            arm=self.arm,
            run_index=self.run_index,
            problem=self.problem,
            selection=self.selection,
            problems_path=self.problems_path,
            rework_attempts=self.rework_attempts,
            transient_retries=self.transient_retries,
            feedback_strategy=self.feedback_strategy,
            exit_code=exit_code,
            phase=phase,
        )


def _resolve_rework_attempts(
    requested: int | None,
    saved_state: dict[str, Any] | None,
) -> int:
    saved = saved_state.get("rework_attempts") if saved_state else None
    if saved is not None:
        try:
            saved = int(saved)
        except (TypeError, ValueError) as exc:
            raise ValueError("resume refused — invalid rework_attempts in state.json") from exc
        if requested is None:
            return saved
        if requested != saved:
            raise ValueError(
                "resume refused — requested rework_attempts differs from the recorded run: "
                f"run={saved!r} requested={requested!r}"
            )
    return requested if requested is not None else DEFAULT_REWORK_ATTEMPTS


def _resolve_transient_retries(
    requested: int | None,
    saved_state: dict[str, Any] | None,
) -> int:
    saved = saved_state.get("transient_retries") if saved_state else None
    if saved is not None:
        try:
            saved = int(saved)
        except (TypeError, ValueError) as exc:
            raise ValueError("resume refused — invalid transient_retries in state.json") from exc
        if requested is None:
            return saved
        if requested != saved:
            raise ValueError(
                "resume refused — requested transient_retries differs from the recorded run: "
                f"run={saved!r} requested={requested!r}"
            )
    value = requested if requested is not None else DEFAULT_TRANSIENT_RETRIES
    if value < 0:
        raise ValueError("transient_retries must be >= 0")
    return value


def _resolve_feedback_strategy(
    requested: str | None,
    saved_state: dict[str, Any] | None,
) -> str:
    saved = saved_state.get("feedback_strategy") if saved_state else None
    if saved == "v1":
        saved = LEGACY_FEEDBACK_STRATEGY
    if requested == "v1":
        requested = LEGACY_FEEDBACK_STRATEGY
    if saved is not None:
        if saved not in FEEDBACK_STRATEGIES:
            raise ValueError("resume refused — invalid feedback_strategy in state.json")
        if requested is None:
            return saved
        if requested != saved:
            raise ValueError(
                "resume refused — requested feedback_strategy differs from the recorded run: "
                f"run={saved!r} requested={requested!r}"
            )
    value = requested if requested is not None else DEFAULT_FEEDBACK_STRATEGY
    if value not in FEEDBACK_STRATEGIES:
        choices = ", ".join(sorted(FEEDBACK_STRATEGIES))
        raise ValueError(f"feedback_strategy must be one of: {choices}")
    return value


def _resume_defaults(
    experiment_id: str | None,
    arm: str,
    problem: str,
) -> dict[str, Any]:
    if experiment_id is None:
        return {}
    return latest_state(RESULTS_DIR / experiment_id, arm, problem=problem) or {}


def _recorded_run_selection(run_dir: Path) -> dict[str, Any] | None:
    """Read the immutable selection from state, falling back to a manifest."""
    state = load_state(run_dir)
    if state is not None:
        return {
            "arm": state.get("arm"),
            "problem": state.get("problem"),
            "agent": state.get("agent"),
            "provider": state.get("provider"),
            "model": state.get("model"),
            "thinking": state.get("thinking"),
            "rework_attempts": state.get("rework_attempts"),
            "transient_retries": state.get("transient_retries"),
            "feedback_strategy": state.get("feedback_strategy"),
        }

    manifest = read_json_dict(Path(run_dir) / "manifest.json")
    if manifest is None:
        return None
    settings = manifest.get("model_settings") or {}
    extra = manifest.get("extra") or {}
    return {
        "arm": manifest.get("arm"),
        "problem": manifest.get("problem"),
        "agent": manifest.get("agent"),
        "provider": settings.get("provider"),
        "model": manifest.get("model"),
        "thinking": settings.get("thinking"),
        "rework_attempts": extra.get("rework_attempts"),
        "transient_retries": extra.get("transient_retries"),
        "feedback_strategy": extra.get("feedback_strategy"),
    }


def _validate_existing_experiment(
    experiment_dir: Path,
    *,
    arms: Sequence[str],
    problem: str,
    selection_by_arm: dict[str, tuple[str, str, str, str]],
    rework_attempts: int,
    transient_retries: int,
    feedback_strategy: str,
) -> None:
    """Prevent a fresh run from mixing or overwriting an experiment."""
    for arm in arms:
        agent, provider, model, thinking = selection_by_arm[arm]
        requested = {
            "arm": arm,
            "problem": problem,
            "agent": agent,
            "provider": provider,
            "model": model,
            "thinking": thinking,
            "rework_attempts": rework_attempts,
            "transient_retries": transient_retries,
            "feedback_strategy": feedback_strategy,
        }
        for run_dir in run_dirs(experiment_dir, arm):
            recorded = _recorded_run_selection(run_dir)
            if recorded is None:
                raise ValueError(
                    f"cannot append to {experiment_dir}: {run_dir} has no state.json "
                    "or manifest.json; use a new --experiment-id"
                )
            mismatches = [
                f"{field}: run={recorded.get(field)!r} requested={value!r}"
                for field, value in requested.items()
                if recorded.get(field) is not None and recorded.get(field) != value
            ]
            if mismatches:
                raise ValueError(
                    f"experiment {experiment_dir.name} already contains a different "
                    f"selection in {run_dir}:\n  " + "\n  ".join(mismatches)
                    + "\nUse a new --experiment-id for another adapter/model/harness combination."
                )


def _next_append_index(experiment_dir: Path, arms: Sequence[str]) -> int:
    """Choose a fresh common run index without overwriting any arm's data."""
    highest = max(
        (
            int(path.name.removeprefix("run_"))
            for arm in arms
            for path in run_dirs(experiment_dir, arm)
        ),
        default=0,
    )
    return highest + 1


def _resume_reference(
    experiment_dir: Path,
    *,
    arms: Sequence[str],
    problem: str,
    agent: str | None,
    provider: str | None,
    model: str | None,
    thinking: str | None,
    rework_attempts: int | None,
    transient_retries: int | None,
    feedback_strategy: str | None,
) -> dict[str, Any]:
    """Validate one experiment's saved selection and return shared defaults."""
    records: list[tuple[Path, dict[str, Any]]] = []
    for arm in arms:
        for run_dir in run_dirs(experiment_dir, arm):
            recorded = _recorded_run_selection(run_dir)
            if recorded is not None:
                records.append((run_dir, recorded))
    if not records:
        return {}

    fields = (
        "problem",
        "agent",
        "provider",
        "model",
        "thinking",
        "rework_attempts",
        "transient_retries",
        "feedback_strategy",
    )
    reference_path, reference = records[0]
    for path, recorded in records[1:]:
        mismatches = [
            f"{field}: {reference.get(field)!r} != {recorded.get(field)!r}"
            for field in fields
            if reference.get(field) is not None
            and recorded.get(field) is not None
            and reference.get(field) != recorded.get(field)
        ]
        if mismatches:
            raise ValueError(
                f"resume refused — experiment contains different selections in "
                f"{reference_path} and {path}:\n  " + "\n  ".join(mismatches)
            )

    requested = {
        "problem": problem,
        "agent": agent,
        "provider": provider,
        "model": model,
        "thinking": thinking,
        "rework_attempts": rework_attempts,
        "transient_retries": transient_retries,
        "feedback_strategy": feedback_strategy,
    }
    mismatches = [
        f"{field}: run={reference.get(field)!r} requested={value!r}"
        for field, value in requested.items()
        if value is not None
        and reference.get(field) is not None
        and reference.get(field) != value
    ]
    if mismatches:
        raise ValueError(
            "resume refused — requested selection differs from the experiment:\n  "
            + "\n  ".join(mismatches)
        )
    return reference


def _build_scb_env(
    output_dir: Path,
    arm: str,
    problem: str,
    *,
    problems_path: Path | None = None,
    rework_attempts: int = 2,
    transient_retries: int = 0,
    feedback_strategy: str = DEFAULT_FEEDBACK_STRATEGY,
) -> dict[str, str]:
    """Build the per-run environment used by SCB."""
    spec = get_arm(arm)
    env = os.environ.copy()
    env["SCBENCH_PROBLEMS_PATH"] = str(problems_path or PROBLEMS_DIR)
    # Keep SCB cache separate per arm/run for isolation of catalog state.
    env["SCBENCH_HOME"] = str(output_dir / ".scbench_home")
    env["HB_ARM"] = arm
    env["HB_RUN_OUTPUT"] = str(output_dir)
    env["HB_REWORK_ATTEMPTS"] = str(rework_attempts)
    env["HB_TRANSIENT_RETRIES"] = str(transient_retries)
    env["HB_REWORK_FEEDBACK"] = feedback_strategy
    # supermemory container tag per problem: memory of one task must not leak
    # into another task's run (see versions.SUPERMEMORY_BENCHMARK_CONTAINER_TAG).
    if arm_includes(arm, "supermemory"):
        env["SUPERMEMORY_BENCHMARK_TAG"] = f"hb_supermemory_{problem}"
    # Ensure sitecustomize runs inside ProcessPool workers too.
    env["PYTHONPATH"] = os.pathsep.join(
        p
        for p in [
            str(REPO_ROOT / "harness_sitecustomize"),
            str(REPO_ROOT),
            env.get("PYTHONPATH", ""),
        ]
        if p
    )

    # docker-py fails when host Docker config has broken credHelpers (e.g. yc).
    # Public base images used by SCB do not need those helpers.
    docker_config_dir = output_dir / ".docker"
    docker_config_dir.mkdir(parents=True, exist_ok=True)
    (docker_config_dir / "config.json").write_text('{"auths": {}}\n', encoding="utf-8")
    env["DOCKER_CONFIG"] = str(docker_config_dir)

    if spec.needs_hook:
        env["HB_ENABLE_HARNESS"] = "1"
        if arm_includes(arm, "ponytail"):
            env["HB_ENABLE_PONYTAIL"] = "1"
        else:
            env.pop("HB_ENABLE_PONYTAIL", None)
    else:
        env.pop("HB_ENABLE_HARNESS", None)
        env.pop("HB_ENABLE_PONYTAIL", None)
    return env


def run_slop_code(
    *,
    arm: str,
    problem: str = DEFAULT_PROBLEM,
    thinking: str = DEFAULT_THINKING,
    model: str = DEFAULT_MODEL,
    provider: str = DEFAULT_PROVIDER,
    agent: str = DEFAULT_AGENT,
    output_dir: Path,
    dry_run: bool = False,
    problems_path: Path | None = None,
    rework_attempts: int = 2,
    transient_retries: int = 0,
    feedback_strategy: str = DEFAULT_FEEDBACK_STRATEGY,
    resume: bool = False,
) -> Path:
    """Invoke SlopCodeBench run for one arm into output_dir.

    ``resume`` switches the underlying invocation to SCB's native
    ``run --resume <output_dir>/scb``: the saved config.yaml / environment.yaml
    supply model, agent and prompts, and SCB itself detects which checkpoints
    survived (see vendor ``agent_runner/resume.py``). All explicit selection
    flags are skipped on resume because they conflict with ``--resume``.
    """
    spec = get_arm(arm)
    if dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    env = _build_scb_env(
        output_dir,
        arm,
        problem,
        problems_path=problems_path,
        rework_attempts=rework_attempts,
        transient_retries=transient_retries,
        feedback_strategy=feedback_strategy,
    )
    scb_thinking = _scb_thinking(thinking)
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "benchmark.scb_main",
        "run",
    ]
    if resume:
        cmd += ["--resume", str(output_dir / "scb")]
    else:
        agent_cfg = _agent_config_for_thinking(agent, thinking, output_dir)
        cmd += [
            "--config",
            str(_resolve_config_paths(_arm_config(arm))),
            "--agent",
            str(agent_cfg),
            "--prompt",
            str(_resolve_config_paths(spec.prompt_path)),
            "--environment",
            str(_resolve_config_paths(_environment_config(arm))),
            "--model",
            f"{provider}/{model}",
            "--problem",
            problem,
            f"thinking={scb_thinking}",
            f"save_dir={output_dir}",
            "save_template=scb",
        ]

    log_path = output_dir / "scb_run.log"
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            check=False,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
    (output_dir / "scb_exit_code.txt").write_text(str(proc.returncode), encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            f"slop-code run failed for arm={arm} (exit {proc.returncode}); see {log_path}"
        )
    return output_dir


def find_scb_problem_dir(scb_root: Path, problem: str) -> Path:
    direct = scb_root / problem
    if direct.exists():
        return direct
    matches = list(scb_root.rglob(problem))
    for match in matches:
        if match.is_dir() and (match / "checkpoint_1").exists():
            return match
    raise FileNotFoundError(f"Could not find SCB problem dir for {problem} under {scb_root}")


def _finalize_run(ctx: RunContext) -> dict[str, Any]:
    """Collect artifacts and publish the completed run metadata."""
    scb_problem_dir = find_scb_problem_dir(ctx.output_dir / "scb", ctx.problem)
    environment = {
        "agent": ctx.agent,
        "agent_version": _agent_version(ctx.agent, ctx.pins),
        "provider": ctx.provider,
        "model": ctx.model,
        "thinking": ctx.thinking,
        "rework_attempts": ctx.rework_attempts,
        "transient_retries": ctx.transient_retries,
        "feedback_strategy": ctx.feedback_strategy,
        "slop_code_commit": ctx.pins.get("slop-code-bench"),
        "problems_commit": ctx.pins.get("scb-problems"),
        "harness_meta": load_arm_meta(ctx.arm),
        "ponytail_commit": ctx.pins.get("ponytail_version")
        if arm_includes(ctx.arm, "ponytail")
        else None,
        "harness": ctx.arm,
        "docker_image": "ghcr.io/astral-sh/uv:python3.12-trixie-slim",
    }
    collected = collect_run(
        scb_problem_dir=scb_problem_dir,
        run_id=ctx.run_id,
        arm=ctx.arm,
        problem=ctx.problem,
        environment=environment,
        pricing_path=CONFIGS_DIR / "pricing.yaml",
    )
    metrics_dir = ctx.output_dir / "metrics"
    write_checkpoint_jsons(collected, metrics_dir)

    if get_arm(ctx.arm).needs_hook:
        verified = all(
            cp.get("harness", {}).get("harness_activation_verified")
            for cp in collected["checkpoints"]
        )
        collected["harness_activation_verified"] = verified
        (metrics_dir / "activation.json").write_text(
            json.dumps(
                {
                    "harness_activation_verified": verified,
                    "checkpoints": [
                        {
                            "checkpoint": cp["checkpoint"],
                            "verified": cp.get("harness", {}).get(
                                "harness_activation_verified"
                            ),
                        }
                        for cp in collected["checkpoints"]
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if not verified:
            collected["excluded_from_comparison"] = True

    manifest = build_manifest(
        experiment_id=ctx.experiment_id,
        arm=ctx.arm,
        problem=ctx.problem,
        model=ctx.model,
        thinking=ctx.thinking,
        provider=ctx.provider,
        agent=ctx.agent,
        runs=1,
        docker_image=environment["docker_image"],
        pricing_path=CONFIGS_DIR / "pricing.yaml",
        extra={
            "run_id": ctx.run_id,
            "run_index": ctx.run_index,
            "rework_attempts": ctx.rework_attempts,
            "transient_retries": ctx.transient_retries,
            "feedback_strategy": ctx.feedback_strategy,
        },
    )
    write_manifest(ctx.output_dir / "manifest.json", manifest)
    collected["manifest"] = manifest
    (metrics_dir / "run.json").write_text(
        json.dumps(collected, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    record_rework_events(collected=collected, manifest=manifest, run_dir=ctx.output_dir)
    resume_info = detect_native_resume(ctx.output_dir, ctx.problem, ctx.problems_path)
    phase = (
        "completed"
        if resume_info is not None and not resume_info.resume_from_checkpoint
        else "incomplete"
    )
    ctx.persist(phase=phase, exit_code=0)
    return collected


def run_one(
    *,
    arm: str,
    problem: str = DEFAULT_PROBLEM,
    thinking: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    agent: str | None = None,
    run_index: int = 1,
    experiment_id: str | None = None,
    problems_path: Path | None = None,
    rework_attempts: int | None = None,
    transient_retries: int | None = None,
    feedback_strategy: str | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    experiment_id = experiment_id or new_experiment_id()
    run_id = f"{experiment_id}-{arm}-r{run_index}-{uuid.uuid4().hex[:8]}"
    out_dir = RESULTS_DIR / experiment_id / arm / f"run_{run_index}"
    saved_state = load_state(out_dir) if resume and out_dir.exists() else None

    if resume and out_dir.exists() and saved_state is None:
        raise ValueError(
            f"cannot resume {out_dir}: no state.json "
            "(this run never started, or pass a different --experiment-id)"
        )
    if not resume and out_dir.exists():
        raise ValueError(
            f"refusing to overwrite existing run {out_dir}; use --resume to continue "
            "it or choose a new --experiment-id/run index"
        )
    if saved_state is not None:
        agent = agent if agent is not None else saved_state.get("agent")
        provider = provider if provider is not None else saved_state.get("provider")
        model = model if model is not None else saved_state.get("model")
        thinking = thinking if thinking is not None else saved_state.get("thinking")

    rework_attempts = _resolve_rework_attempts(rework_attempts, saved_state)
    transient_retries = _resolve_transient_retries(transient_retries, saved_state)
    feedback_strategy = _resolve_feedback_strategy(feedback_strategy, saved_state)
    agent, provider, model, thinking = resolve_run_selection(
        agent=agent,
        arm=arm,
        provider=provider,
        model=model,
        thinking=thinking,
    )

    if not resume:
        experiment_dir = RESULTS_DIR / experiment_id
        if experiment_dir.exists():
            _validate_existing_experiment(
                experiment_dir,
                arms=(arm,),
                problem=problem,
                selection_by_arm={arm: (agent, provider, model, thinking)},
                rework_attempts=rework_attempts,
                transient_retries=transient_retries,
                feedback_strategy=feedback_strategy,
            )

    if resume and out_dir.exists():
        mismatches = verify_selection_against_state(
            saved_state,
            experiment_id=experiment_id,
            arm=arm,
            run_index=run_index,
            problem=problem,
            agent=agent,
            provider=provider,
            model=model,
            thinking=thinking,
            rework_attempts=rework_attempts,
            transient_retries=transient_retries,
            feedback_strategy=feedback_strategy,
        )
        if mismatches:
            raise ValueError(
                "resume refused — requested identity differs from the recorded run:\n  "
                + "\n  ".join(mismatches)
                + "\nRe-run without --resume to start fresh."
            )
        native_resume = (
            detect_native_resume(out_dir, problem, problems_path)
            if (out_dir / "scb").is_dir()
            else None
        )
        if (
            saved_state.get("phase") == "completed"
            and saved_state.get("exit_code") == 0
            and native_resume is not None
            and not native_resume.resume_from_checkpoint
        ):
            collection = read_existing_collection(out_dir)
            if collection is not None:
                return collection
        if native_resume is None:
            shutil.rmtree(out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
        else:
            clear_stale_resume_artifacts(
                out_dir, problem, native_resume, problems_path
            )
    else:
        out_dir.mkdir(parents=True, exist_ok=True)

    pins = load_pins()
    ctx = RunContext(
        experiment_id=experiment_id,
        arm=arm,
        problem=problem,
        run_index=run_index,
        output_dir=out_dir,
        run_id=run_id,
        agent=agent,
        model=model,
        provider=provider,
        thinking=thinking,
        rework_attempts=rework_attempts,
        transient_retries=transient_retries,
        feedback_strategy=feedback_strategy,
        problems_path=problems_path,
        pins=pins,
    )
    # Start marker written BEFORE SCB launches: an interrupted run must still
    # be self-describing (identity + which checkpoint was reached last).
    ctx.persist(phase="started")
    use_native_resume = resume and (out_dir / "scb").is_dir()

    try:
        run_slop_code(
            arm=arm,
            problem=problem,
            thinking=ctx.thinking,
            model=ctx.model,
            provider=ctx.provider,
            agent=ctx.agent,
            output_dir=ctx.output_dir,
            problems_path=ctx.problems_path,
            rework_attempts=ctx.rework_attempts,
            transient_retries=ctx.transient_retries,
            feedback_strategy=ctx.feedback_strategy,
            resume=use_native_resume,
        )
        return _finalize_run(ctx)
    except BaseException as exc:  # noqa: BLE001 — persist lifecycle before propagating
        exit_code_path = ctx.output_dir / "scb_exit_code.txt"
        try:
            exit_code = int(exit_code_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            exit_code = None
        ctx.persist(
            phase="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
            exit_code=exit_code,
        )
        raise


def run_smoke(
    *,
    arm: str,
    problem: str = DEFAULT_PROBLEM,
    thinking: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    agent: str = DEFAULT_AGENT,
    experiment_id: str | None = None,
    rework_attempts: int = 0,
    transient_retries: int = 0,
    feedback_strategy: str = DEFAULT_FEEDBACK_STRATEGY,
    checkpoint_count: int = 1,
) -> dict[str, Any]:
    """Run a reduced-checkpoint smoke (default CP1) for one harness arm and write SMOKE.json."""
    from benchmark.smoke import (
        analyze_smoke_snapshot,
        stage_cp1_only_problem,
        write_smoke_marker,
    )

    spec = get_arm(arm)
    if not spec.needs_hook:
        raise ValueError(f"arm {arm!r} is baseline — smoke is only for skill harnesses")

    experiment_id = experiment_id or new_experiment_id(f"smoke-{arm}")
    out_dir = RESULTS_DIR / experiment_id / arm / "run_1"
    problems_root = RESULTS_DIR / experiment_id / "_smoke_problems"
    staged = stage_cp1_only_problem(
        problem=problem,
        dest_root=problems_root,
        checkpoint_count=checkpoint_count,
    )

    collected = run_one(
        arm=arm,
        problem=problem,
        thinking=thinking,
        model=model,
        provider=provider,
        agent=agent,
        run_index=1,
        experiment_id=experiment_id,
        problems_path=staged,
        rework_attempts=rework_attempts,
        transient_retries=transient_retries,
        feedback_strategy=feedback_strategy,
    )

    cps = collected.get("checkpoints") or []
    cp1 = next((cp for cp in cps if cp.get("checkpoint") == 1), cps[0] if cps else None)
    snapshot_dir: Path | None = None
    if cp1:
        snap = (cp1.get("paths") or {}).get("snapshot_dir")
        if snap:
            snapshot_dir = Path(snap)
    analysis = analyze_smoke_snapshot(snapshot_dir) if snapshot_dir else {}
    activation = collected.get("harness_activation_verified")
    if activation is None and cp1:
        activation = (cp1.get("harness") or {}).get("harness_activation_verified")
    ok = bool(cps) and activation is not False
    marker_path = write_smoke_marker(
        arm,
        problem=problem,
        experiment_id=experiment_id,
        run_dir=out_dir,
        ok=ok,
        activation_verified=activation if isinstance(activation, bool) else None,
        snapshot_analysis=analysis,
        extra={"checkpoints_completed": [cp.get("checkpoint") for cp in cps]},
    )
    collected["smoke_marker"] = str(marker_path)
    collected["smoke_ok"] = ok
    collected["smoke_snapshot_analysis"] = analysis
    return collected


def read_existing_collection(output_dir: Path) -> dict[str, Any] | None:
    """Reload ``metrics/run.json`` of a finished run (resume-skip path)."""
    return read_json_dict(Path(output_dir) / "metrics" / "run.json")


def run_matrix(
    *,
    arms: Sequence[str],
    problem: str = DEFAULT_PROBLEM,
    runs: int = 3,
    thinking: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    agent: str | None = None,
    experiment_id: str | None = None,
    jobs: int = 1,
    skip_smoke_check: bool = False,
    rework_attempts: int | None = None,
    transient_retries: int | None = None,
    feedback_strategy: str | None = None,
    resume: bool = False,
) -> list[dict[str, Any]]:
    """Run arm×run matrix. jobs=1 is serial; jobs>1 overlaps independent run_one calls.

    Each run already isolates SCBENCH_HOME / DOCKER_CONFIG / results dir.
    Concurrent Docker image builds can race — pre-build via scripts/build_images.sh.
    API/Docker resource exhaustion may fail some runs; others still finish.

    With ``resume``, each slot resolves against its ``state.json``: a finished
    trajectory reloads ``metrics/run.json`` and skips; an incomplete one
    continues through SCB's native ``run --resume``; a slot that never started
    launches fresh. Requires an explicit ``experiment_id`` and refuses ``runs``
    smaller than the highest recorded run index.
    """
    from benchmark.smoke import require_smoke_validated

    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    normalized_feedback_strategy = (
        _resolve_feedback_strategy(feedback_strategy, None)
        if not resume
        else (
            LEGACY_FEEDBACK_STRATEGY
            if feedback_strategy == "v1"
            else feedback_strategy
        )
    )
    resolved_by_arm: dict[str, tuple[str, str, str, str]] = {}
    for arm in arms:
        get_arm(arm)
        # Fail fast before scheduling work (OpenCode + skill arm, missing flags, …).
        # On resume, omitted flags are legitimate: run_one restores them from
        # state.json, so demanding them here would break flag-less resumes.
        if not resume:
            resolved_by_arm[arm] = resolve_run_selection(
                agent=agent,
                arm=arm,
                provider=provider,
                model=model,
                thinking=thinking,
            )
    require_smoke_validated(arms, skip=skip_smoke_check)
    if resume and not experiment_id:
        raise ValueError("--resume requires an explicit --experiment-id")
    if not resume and experiment_id:
        experiment_dir = RESULTS_DIR / experiment_id
        if experiment_dir.exists():
            resolved_by_arm = {
                arm: resolved_by_arm.get(arm)
                or resolve_run_selection(
                    agent=agent,
                    arm=arm,
                    provider=provider,
                    model=model,
                    thinking=thinking,
                )
                for arm in arms
            }
            _validate_existing_experiment(
                experiment_dir,
                arms=arms,
                problem=problem,
                selection_by_arm=resolved_by_arm,
                rework_attempts=(
                    rework_attempts
                    if rework_attempts is not None
                    else DEFAULT_REWORK_ATTEMPTS
                ),
                transient_retries=(
                    transient_retries
                    if transient_retries is not None
                    else DEFAULT_TRANSIENT_RETRIES
                ),
                feedback_strategy=(
                    normalized_feedback_strategy
                    if normalized_feedback_strategy is not None
                    else DEFAULT_FEEDBACK_STRATEGY
                ),
            )
    resume_defaults: dict[str, dict[str, Any]] = {}
    if resume and experiment_id:
        _resume_reference(
            RESULTS_DIR / experiment_id,
            arms=arms,
            problem=problem,
            agent=agent,
            provider=provider,
            model=model,
            thinking=thinking,
            rework_attempts=rework_attempts,
            transient_retries=transient_retries,
            feedback_strategy=normalized_feedback_strategy,
        )
        recorded_by_arm = {
            arm: max(
                (
                    int(path.name.removeprefix("run_"))
                    for path in run_dirs(RESULTS_DIR / experiment_id, arm)
                ),
                default=0,
            )
            for arm in arms
        }
        offenders = {
            arm: recorded
            for arm, recorded in recorded_by_arm.items()
            if recorded > runs
        }
        if offenders:
            required_runs = max(offenders.values())
            details = ", ".join(f"{arm}={recorded}" for arm, recorded in offenders.items())
            raise ValueError(
                f"--resume found recorded runs for selected arm(s) in {experiment_id}: "
                f"{details}; pass --runs {required_runs} (got {runs})"
            )
        resume_defaults = {
            arm: _resume_defaults(experiment_id, arm, problem) for arm in arms
        }
        shared_defaults = next(
            (state for state in resume_defaults.values() if state),
            {},
        )
        for arm, state in resume_defaults.items():
            if not state and shared_defaults:
                resume_defaults[arm] = shared_defaults
    experiment_id = experiment_id or new_experiment_id()
    first_run_index = (
        _next_append_index(RESULTS_DIR / experiment_id, arms)
        if not resume
        else 1
    )
    tasks = [
        (arm, first_run_index + offset)
        for arm in arms
        for offset in range(runs)
    ]

    def _one(arm: str, run_index: int) -> dict[str, Any]:
        saved = resume_defaults.get(arm, {})
        return run_one(
            arm=arm,
            problem=problem,
            thinking=thinking if thinking is not None else saved.get("thinking"),
            model=model if model is not None else saved.get("model"),
            provider=provider if provider is not None else saved.get("provider"),
            agent=agent if agent is not None else saved.get("agent"),
            run_index=run_index,
            experiment_id=experiment_id,
            rework_attempts=(
                rework_attempts
                if rework_attempts is not None
                else saved.get("rework_attempts")
            ),
            transient_retries=(
                transient_retries
                if transient_retries is not None
                else saved.get("transient_retries")
            ),
            feedback_strategy=(
                normalized_feedback_strategy
                if normalized_feedback_strategy is not None
                else saved.get("feedback_strategy")
            ),
            resume=resume,
        )

    if jobs == 1 or len(tasks) == 1:
        return [_one(arm, idx) for arm, idx in tasks]

    results: list[dict[str, Any]] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(_one, arm, idx): (arm, idx) for arm, idx in tasks}
        for fut in as_completed(futures):
            arm, idx = futures[fut]
            try:
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001 — surface all failures after join
                errors.append(f"{arm}/run_{idx}: {exc}")
    if errors:
        raise RuntimeError(f"{len(errors)}/{len(tasks)} run(s) failed: " + "; ".join(errors))
    return results


def run_arm_repeats(
    *,
    arm: str,
    problem: str = DEFAULT_PROBLEM,
    runs: int = 3,
    thinking: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    agent: str | None = None,
    experiment_id: str | None = None,
    jobs: int = 1,
    skip_smoke_check: bool = False,
    rework_attempts: int | None = None,
    transient_retries: int | None = None,
    feedback_strategy: str | None = None,
    resume: bool = False,
) -> list[dict[str, Any]]:
    return run_matrix(
        arms=(arm,),
        problem=problem,
        runs=runs,
        thinking=thinking,
        model=model,
        provider=provider,
        agent=agent,
        experiment_id=experiment_id,
        jobs=jobs,
        skip_smoke_check=skip_smoke_check,
        rework_attempts=rework_attempts,
        transient_retries=transient_retries,
        feedback_strategy=feedback_strategy,
        resume=resume,
    )


def default_arms() -> tuple[str, ...]:
    return DEFAULT_EXPERIMENT_ARMS

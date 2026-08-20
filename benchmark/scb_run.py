from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from benchmark.arms import DEFAULT_EXPERIMENT_ARMS, get_arm
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
from benchmark.versions import load_arm_meta, load_pins

# SCB ResolvedRunConfig accepts only none/disabled/low/medium/high/xhigh.
# Codex gpt-5.6-luna also supports effort=max; map + force via agent extra_args.
_SCB_THINKING_ALIASES = {
    "max": "xhigh",
}


def _scb_thinking(thinking: str) -> str:
    return _SCB_THINKING_ALIASES.get(thinking, thinking)


def resolve_run_selection(
    *,
    agent: str,
    arm: str,
    provider: str | None,
    model: str | None,
    thinking: str | None,
) -> tuple[str, str, str, str]:
    """Resolve agent/provider/model/thinking.

    Codex keeps historical defaults when flags are omitted.
    OpenCode requires explicit --provider and --model; thinking defaults to none.
    """
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
        provider or DEFAULT_PROVIDER,
        model or DEFAULT_MODEL,
        thinking or DEFAULT_THINKING,
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
    if arm == "supermemory":
        return CONFIGS_DIR / "environments" / "docker-python3.12-uv-hostnet.yaml"
    return SCB_DIR / "configs" / "environments" / "docker-python3.12-uv.yaml"


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
) -> Path:
    """Invoke SlopCodeBench run for one arm into output_dir."""
    spec = get_arm(arm)
    config = _resolve_config_paths(_arm_config(arm))
    prompt = _resolve_config_paths(spec.prompt_path)

    env = os.environ.copy()
    env["SCBENCH_PROBLEMS_PATH"] = str(problems_path or PROBLEMS_DIR)
    # Keep SCB cache separate per arm/run for isolation of catalog state.
    env["SCBENCH_HOME"] = str(output_dir / ".scbench_home")
    env["HB_ARM"] = arm
    env["HB_RUN_OUTPUT"] = str(output_dir)
    # supermemory container tag per problem: memory of one task must not leak
    # into another task's run (see versions.SUPERMEMORY_BENCHMARK_CONTAINER_TAG).
    if arm == "supermemory":
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

    output_dir.mkdir(parents=True, exist_ok=True)
    agent_cfg = _agent_config_for_thinking(agent, thinking, output_dir)

    # docker-py fails when host Docker config has broken credHelpers (e.g. yc).
    # Public base images used by SCB do not need those helpers.
    docker_config_dir = output_dir / ".docker"
    docker_config_dir.mkdir(parents=True, exist_ok=True)
    (docker_config_dir / "config.json").write_text('{"auths": {}}\n', encoding="utf-8")
    env["DOCKER_CONFIG"] = str(docker_config_dir)

    scb_thinking = _scb_thinking(thinking)
    environment = _resolve_config_paths(_environment_config(arm))
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "benchmark.scb_main",
        "run",
        "--config",
        str(config),
        "--agent",
        str(agent_cfg),
        "--prompt",
        str(prompt),
        "--environment",
        str(environment),
        "--model",
        f"{provider}/{model}",
        "--problem",
        problem,
        f"thinking={scb_thinking}",
        f"save_dir={output_dir}",
        "save_template=scb",
    ]
    if dry_run:
        return output_dir

    if spec.needs_hook:
        env["HB_ENABLE_HARNESS"] = "1"
        if arm == "ponytail":
            env["HB_ENABLE_PONYTAIL"] = "1"
        else:
            env.pop("HB_ENABLE_PONYTAIL", None)
    else:
        env.pop("HB_ENABLE_HARNESS", None)
        env.pop("HB_ENABLE_PONYTAIL", None)

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


def run_one(
    *,
    arm: str,
    problem: str = DEFAULT_PROBLEM,
    thinking: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    agent: str = DEFAULT_AGENT,
    run_index: int = 1,
    experiment_id: str | None = None,
    problems_path: Path | None = None,
) -> dict[str, Any]:
    agent, provider, model, thinking = resolve_run_selection(
        agent=agent,
        arm=arm,
        provider=provider,
        model=model,
        thinking=thinking,
    )
    experiment_id = experiment_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_id = f"{experiment_id}-{arm}-r{run_index}-{uuid.uuid4().hex[:8]}"
    out_dir = RESULTS_DIR / experiment_id / arm / f"run_{run_index}"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pins = load_pins()
    run_slop_code(
        arm=arm,
        problem=problem,
        thinking=thinking,
        model=model,
        provider=provider,
        agent=agent,
        output_dir=out_dir,
        problems_path=problems_path,
    )

    scb_problem_dir = find_scb_problem_dir(out_dir / "scb", problem)
    environment = {
        "agent": agent,
        "agent_version": _agent_version(agent, pins),
        "provider": provider,
        "model": model,
        "thinking": thinking,
        "slop_code_commit": pins.get("slop-code-bench"),
        "problems_commit": pins.get("scb-problems"),
        "harness_meta": load_arm_meta(arm),
        "ponytail_commit": pins.get("ponytail_version") if arm == "ponytail" else None,
        "harness": arm,
        "docker_image": "ghcr.io/astral-sh/uv:python3.12-trixie-slim",
    }
    collected = collect_run(
        scb_problem_dir=scb_problem_dir,
        run_id=run_id,
        arm=arm,
        problem=problem,
        environment=environment,
        pricing_path=CONFIGS_DIR / "pricing.yaml",
    )
    metrics_dir = out_dir / "metrics"
    write_checkpoint_jsons(collected, metrics_dir)

    # Activation gate for skill arms
    if get_arm(arm).needs_hook:
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
                            "verified": cp.get("harness", {}).get("harness_activation_verified"),
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
        experiment_id=experiment_id,
        arm=arm,
        problem=problem,
        model=model,
        thinking=thinking,
        provider=provider,
        agent=agent,
        runs=1,
        docker_image=environment["docker_image"],
        pricing_path=CONFIGS_DIR / "pricing.yaml",
        extra={"run_id": run_id, "run_index": run_index},
    )
    write_manifest(out_dir / "manifest.json", manifest)
    collected["manifest"] = manifest
    (metrics_dir / "run.json").write_text(
        json.dumps(collected, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return collected


def run_smoke(
    *,
    arm: str,
    problem: str = DEFAULT_PROBLEM,
    thinking: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    agent: str = DEFAULT_AGENT,
    experiment_id: str | None = None,
) -> dict[str, Any]:
    """Run a single-checkpoint (CP1) smoke for one harness arm and write SMOKE.json."""
    from benchmark.smoke import (
        analyze_smoke_snapshot,
        stage_cp1_only_problem,
        write_smoke_marker,
    )

    spec = get_arm(arm)
    if not spec.needs_hook:
        raise ValueError(f"arm {arm!r} is baseline — smoke is only for skill harnesses")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    experiment_id = experiment_id or f"smoke-{arm}-{stamp}"
    out_dir = RESULTS_DIR / experiment_id / arm / "run_1"
    problems_root = RESULTS_DIR / experiment_id / "_smoke_problems"
    staged = stage_cp1_only_problem(problem=problem, dest_root=problems_root)

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


def run_matrix(
    *,
    arms: Sequence[str],
    problem: str = DEFAULT_PROBLEM,
    runs: int = 3,
    thinking: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    agent: str = DEFAULT_AGENT,
    experiment_id: str | None = None,
    jobs: int = 1,
    skip_smoke_check: bool = False,
) -> list[dict[str, Any]]:
    """Run arm×run matrix. jobs=1 is serial; jobs>1 overlaps independent run_one calls.

    Each run already isolates SCBENCH_HOME / DOCKER_CONFIG / results dir.
    Concurrent Docker image builds can race — pre-build via scripts/build_images.sh.
    API/Docker resource exhaustion may fail some runs; others still finish.
    """
    from benchmark.smoke import require_smoke_validated

    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    for arm in arms:
        get_arm(arm)
        # Fail fast before scheduling work (OpenCode + skill arm, missing flags, …).
        resolve_run_selection(
            agent=agent,
            arm=arm,
            provider=provider,
            model=model,
            thinking=thinking,
        )
    require_smoke_validated(arms, skip=skip_smoke_check)
    experiment_id = experiment_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    tasks = [(arm, idx) for arm in arms for idx in range(1, runs + 1)]

    def _one(arm: str, run_index: int) -> dict[str, Any]:
        return run_one(
            arm=arm,
            problem=problem,
            thinking=thinking,
            model=model,
            provider=provider,
            agent=agent,
            run_index=run_index,
            experiment_id=experiment_id,
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
    agent: str = DEFAULT_AGENT,
    experiment_id: str | None = None,
    jobs: int = 1,
    skip_smoke_check: bool = False,
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
    )


def default_arms() -> tuple[str, ...]:
    return DEFAULT_EXPERIMENT_ARMS

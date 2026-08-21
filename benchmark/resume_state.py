"""Minimal outer state for SlopCodeBench native resume."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from slop_code.agent_runner.resume import (
    CheckpointStatus,
    InvalidationReason,
    ResumeInfo,
    detect_resume_point,
)
from slop_code.evaluation.config import CheckpointConfig, ConfigError, ProblemConfig

from benchmark.paths import PROBLEMS_DIR, RESULTS_DIR

STATE_FILENAME = "state.json"
IDENTITY_FIELDS = ("experiment_id", "arm", "run_index")
SELECTION_FIELDS = ("agent", "provider", "model", "thinking", "problem")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def run_dir_for(experiment_id: str, arm: str, run_index: int) -> Path:
    return RESULTS_DIR / experiment_id / arm / f"run_{run_index}"


def read_json_dict(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_state(run_dir: Path) -> dict[str, Any] | None:
    return read_json_dict(Path(run_dir) / STATE_FILENAME)


def run_dirs(experiment_dir: Path, arm: str | None = None) -> list[Path]:
    pattern = f"{arm}/run_*" if arm is not None else "*/run_*"
    def run_index(path: Path) -> int | None:
        try:
            return int(path.name.removeprefix("run_"))
        except ValueError:
            return None

    candidates = [path for path in experiment_dir.glob(pattern) if path.is_dir()]
    return sorted(
        (path for path in candidates if run_index(path) is not None),
        key=lambda path: (path.parent.name, run_index(path) or 0),
    )


def latest_state(
    experiment_dir: Path,
    arm: str,
    *,
    problem: str | None = None,
) -> dict[str, Any] | None:
    """Return the newest state for an arm, optionally limited to one problem."""
    for run_dir in reversed(run_dirs(experiment_dir, arm)):
        state = load_state(run_dir)
        if state is not None and (problem is None or state.get("problem") == problem):
            return state
    return None


def _native_inputs(
    problem: str,
    problems_path: Path | None = None,
) -> tuple[list[tuple[str, CheckpointConfig]], ProblemConfig] | None:
    config_path = (problems_path or PROBLEMS_DIR) / problem
    if not config_path.exists():
        return None
    try:
        config = ProblemConfig.from_yaml(config_path)
    except (OSError, ConfigError):
        return None
    return list(config.iterate_checkpoint_items()), config


def read_yaml_dict(path: Path) -> dict[str, Any] | None:
    """Read a YAML mapping without allowing malformed config to escape."""
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def _saved_native_inputs(
    run_dir: Path,
) -> tuple[str, Any] | None:
    """Load the prompt and environment snapshot used by native SCB resume."""
    scb_dir = Path(run_dir) / "scb"
    config = read_yaml_dict(scb_dir / "config.yaml")
    environment_data = read_yaml_dict(scb_dir / "environment.yaml")
    if config is None or environment_data is None:
        return None
    prompt = config.get("prompt_content")
    if not isinstance(prompt, str):
        return None
    environment_type = environment_data.get("type")
    try:
        if environment_type == "docker":
            from slop_code.execution.docker_runtime import DockerEnvironmentSpec

            environment = DockerEnvironmentSpec.model_validate(environment_data)
        elif environment_type == "local":
            from slop_code.execution.local_streaming import LocalEnvironmentSpec

            environment = LocalEnvironmentSpec.model_validate(environment_data)
        else:
            return None
    except (TypeError, ValueError):
        return None
    return prompt, environment


def detect_native_resume(
    run_dir: Path,
    problem: str,
    problems_path: Path | None = None,
) -> ResumeInfo | None:
    """Return SCB's resume decision for one problem output directory."""
    scb_problem_dir = Path(run_dir) / "scb" / problem
    inputs = _native_inputs(problem, problems_path)
    if inputs is None:
        return None
    items, config = inputs
    checkpoint_names = [name for name, _ in items]
    checkpoints = [checkpoint for _, checkpoint in items]
    saved_inputs = _saved_native_inputs(run_dir)
    native_kwargs: dict[str, Any] = {
        "problem_config": config,
        "checkpoints": checkpoints,
    }
    if saved_inputs is not None:
        prompt, environment = saved_inputs
        native_kwargs.update(
            prompt_template=prompt,
            environment=environment,
            entry_file=config.entry_file,
        )
    return detect_resume_point(
        scb_problem_dir,
        checkpoint_names,
        **native_kwargs,
    )


def _checkpoint_label(status: CheckpointStatus) -> str:
    if status.is_valid:
        return "done"
    reason = status.reason
    if reason is None:
        return "incomplete"
    if reason is InvalidationReason.MISSING_DIR:
        return "not_reached"
    return "incomplete"


def _checkpoint_statuses(info: ResumeInfo | None) -> dict[str, str]:
    if info is None:
        return {}
    return {status.name: _checkpoint_label(status) for status in info.checkpoint_statuses}


def _interrupt_reason(
    *,
    exit_code: int | None,
    phase: str,
    info: ResumeInfo | None,
    fully_completed: bool,
) -> str:
    if phase == "failed":
        return "crashed"
    if phase == "started":
        return "started"
    if phase == "interrupted":
        return "interrupted"
    if exit_code is not None and exit_code != 0:
        return "crashed"
    if fully_completed:
        return "ok"
    statuses = info.checkpoint_statuses if info else []
    first_invalid = next((status for status in statuses if not status.is_valid), None)
    if first_invalid and first_invalid.reason is InvalidationReason.MISSING_DIR:
        return "stopped_by_policy"
    return "interrupted"


def build_state(
    *,
    output_dir: Path,
    experiment_id: str,
    arm: str,
    run_index: int,
    problem: str,
    selection: dict[str, Any],
    problems_path: Path | None = None,
    rework_attempts: int | None = None,
    exit_code: int | None = None,
    phase: str = "started",
) -> dict[str, Any]:
    """Assemble lifecycle and native checkpoint state from disk."""
    info = detect_native_resume(output_dir, problem, problems_path)
    statuses = _checkpoint_statuses(info)
    completed = info.completed_checkpoints if info else []
    stopped_at = info.resume_from_checkpoint or None if info else None
    fully_completed = bool(info and not info.resume_from_checkpoint)
    state = {
        "version": 1,
        "phase": phase,
        "experiment_id": experiment_id,
        "arm": arm,
        "run_index": run_index,
        "problem": problem,
        "agent": selection.get("agent"),
        "model": selection.get("model"),
        "provider": selection.get("provider"),
        "thinking": selection.get("thinking"),
        "updated_at": _utc_now(),
        "exit_code": exit_code,
        "last_completed_checkpoint": completed[-1] if completed else None,
        "stopped_at_checkpoint": stopped_at,
        "interrupt_reason": _interrupt_reason(
            exit_code=exit_code,
            phase=phase,
            info=info,
            fully_completed=fully_completed,
        ),
        "checkpoints": statuses,
        "fully_completed": fully_completed,
    }
    if rework_attempts is not None:
        state["rework_attempts"] = rework_attempts
    return state


def write_state(
    *,
    output_dir: Path,
    experiment_id: str,
    arm: str,
    run_index: int,
    problem: str,
    selection: dict[str, Any],
    problems_path: Path | None = None,
    rework_attempts: int | None = None,
    exit_code: int | None = None,
    phase: str = "started",
) -> Path:
    """Persist the minimal outer state document."""
    document = build_state(
        output_dir=output_dir,
        experiment_id=experiment_id,
        arm=arm,
        run_index=run_index,
        problem=problem,
        selection=selection,
        problems_path=problems_path,
        rework_attempts=rework_attempts,
        exit_code=exit_code,
        phase=phase,
    )
    path = Path(output_dir) / STATE_FILENAME
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
    return path


def verify_selection_against_state(
    state: dict[str, Any],
    *,
    experiment_id: str,
    arm: str,
    run_index: int,
    agent: str,
    provider: str | None,
    model: str | None,
    thinking: str | None,
    problem: str,
) -> list[str]:
    """Return mismatches between recorded run identity and requested values."""
    requested = {
        "experiment_id": experiment_id,
        "arm": arm,
        "run_index": run_index,
        "agent": agent,
        "provider": provider,
        "model": model,
        "thinking": thinking,
        "problem": problem,
    }
    mismatches: list[str] = []
    for field in IDENTITY_FIELDS:
        current = requested[field]
        saved = state.get(field)
        if saved != current:
            mismatches.append(f"{field}: run={saved!r} requested={current!r}")
    for field in SELECTION_FIELDS:
        current = requested[field]
        saved = state.get(field)
        if current is not None and saved != current:
            mismatches.append(f"{field}: run={saved!r} requested={current!r}")
    return mismatches


def clear_stale_resume_artifacts(
    run_dir: Path,
    problem: str,
    info: ResumeInfo | None = None,
    problems_path: Path | None = None,
) -> list[str]:
    """Remove stale feedback from checkpoints SCB will invalidate."""
    info = (
        info
        if info is not None
        else detect_native_resume(run_dir, problem, problems_path)
    )
    removed: list[str] = []
    for checkpoint in info.invalidated_checkpoints if info else []:
        checkpoint_dir = Path(run_dir) / "scb" / problem / checkpoint
        for filename in ("rework.json", "evaluation.json"):
            artifact = checkpoint_dir / filename
            if artifact.exists():
                artifact.unlink()
                removed.append(str(artifact))
    return removed

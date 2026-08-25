"""Long-lived desired-state supervisor for benchmark experiments."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchmark.analyze import analyze_experiment, write_reports_and_publish
from benchmark.fleet.config import DesiredConfig, ExperimentTarget
from benchmark.fleet.locks import exclusive_lock
from benchmark.fleet.planner import FleetAction, FleetPlan, build_plan
from benchmark.notify import notify_experiment_completion, notify_human
from benchmark.onboard import onboard_arm
from benchmark.paths import REPO_ROOT, RESULTS_DIR


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_work(experiment_dir: Path, command: list[str], process: subprocess.Popen[Any], action: FleetAction) -> None:
    path = experiment_dir / ".fleet-work.json"
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(
            {
                "pid": process.pid,
                "experiment_id": action.experiment_id,
                "action": action.kind,
                "arm": action.arm,
                "run_index": action.run_index,
                "command": command,
                "started_at": _timestamp(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _read_work(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _work_live(path: Path) -> bool:
    work = _read_work(path)
    pid = work.get("pid") if work else None
    if not isinstance(pid, int):
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    try:
        command = (Path("/proc") / str(pid) / "cmdline").read_bytes().decode(errors="replace")
    except OSError:
        return False
    return "monitor_benchmark.py" in command and str(work.get("experiment_id", "")) in command


def _clear_dead_work(experiment_dir: Path) -> None:
    path = experiment_dir / ".fleet-work.json"
    if path.exists() and not _work_live(path):
        try:
            path.unlink()
        except OSError:
            pass


def _monitor_command(experiment: ExperimentTarget, *, log_path: Path) -> list[str]:
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "monitor_benchmark.py"),
        "--experiment-id",
        experiment.id,
        "--problem",
        experiment.problem,
        "--arms",
        ",".join(experiment.arms),
        "--runs",
        str(experiment.runs),
        "--jobs",
        str(experiment.jobs),
        "--agent",
        experiment.agent,
        "--provider",
        experiment.provider,
        "--model",
        experiment.model,
        "--thinking",
        experiment.thinking,
        "--rework-attempts",
        str(experiment.rework_attempts),
        "--transient-retries",
        str(experiment.transient_retries),
        "--log",
        str(log_path),
        "--max-restarts",
        str(experiment.max_restarts),
        "--desired-fingerprint",
        experiment.fingerprint(),
    ]
    if experiment.feedback_strategy:
        command.extend(["--feedback-strategy", experiment.feedback_strategy])
    return command


def _start_monitor(experiment: ExperimentTarget, *, results_dir: Path) -> FleetAction:
    experiment_dir = results_dir / experiment.id
    experiment_dir.mkdir(parents=True, exist_ok=True)
    log_path = experiment_dir / "fleet-monitor.log"
    command = _monitor_command(experiment, log_path=log_path)
    output = log_path.open("ab")
    try:
        process = subprocess.Popen(
            command,
            cwd=str(REPO_ROOT),
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    except BaseException:
        output.close()
        raise
    output.close()
    action = FleetAction(experiment.id, "monitor", reason="monitor started")
    _write_work(experiment_dir, command, process, action)
    return action


def _find_experiment(desired: DesiredConfig, experiment_id: str) -> ExperimentTarget:
    for experiment in desired.experiments:
        if experiment.id == experiment_id:
            return experiment
    raise KeyError(experiment_id)


def _notify_ticket_for_action(action: FleetAction, desired: DesiredConfig, *, ops_dir: Path) -> None:
    experiment = _find_experiment(desired, action.experiment_id)
    fingerprint = f"ticket:{experiment.id}:{action.arm or 'experiment'}:{action.reason}"
    notify_human(
        fingerprint=fingerprint,
        title=f"{experiment.id}: {action.arm or 'experiment'}",
        summary=action.reason,
        details=(
            f"experiment={experiment.id}\nproblem={experiment.problem}\narms={','.join(experiment.arms)}\n"
            f"arm={action.arm or 'experiment'}\n"
            f"desired fingerprint={experiment.fingerprint()}\n"
        ),
        ops_dir=ops_dir,
    )


def _onboard(action: FleetAction, desired: DesiredConfig, *, ops_dir: Path) -> None:
    experiment = _find_experiment(desired, action.experiment_id)
    result = onboard_arm(
        action.arm or "",
        target=desired.harness(action.arm or ""),
        experiment=experiment,
        max_attempts=3,
    )
    if not result.ok:
        notify_human(
            fingerprint=f"onboarding:{experiment.id}:{action.arm}:{result.reason}",
            title=f"Онбординг harness {action.arm} остановлен",
            summary=result.reason,
            details=f"attempts={result.attempts}\nexperiment={experiment.id}\narm={action.arm}\n",
            ops_dir=ops_dir,
        )


def _publish_completion(experiment: ExperimentTarget, plan: FleetPlan, *, results_dir: Path) -> None:
    experiment_dir = results_dir / experiment.id
    comparison = analyze_experiment(experiment_dir)
    write_reports_and_publish(experiment_dir, comparison, problem=experiment.problem)
    completed = sum(
        1 for key, status in plan.statuses.items()
        if key.startswith(f"{experiment.id}/") and status == "done"
    )
    notify_experiment_completion(
        experiment,
        completed_cells=completed,
        total_cells=len(experiment.arms) * experiment.runs,
        arms=experiment.arms,
        results_dir=results_dir,
    )


def fleet_cycle(
    desired: DesiredConfig,
    *,
    results_dir: Path = RESULTS_DIR,
    ops_dir: Path | None = None,
    start_monitors: bool = True,
) -> FleetPlan:
    """Run one idempotent reconciliation cycle and return its resulting plan."""
    ops_dir = ops_dir or results_dir.parent
    for experiment in desired.experiments:
        _clear_dead_work(results_dir / experiment.id)
    plan = build_plan(desired, results_dir=results_dir, ops_dir=ops_dir)

    for action in plan.actions:
        if action.kind == "ticket":
            _notify_ticket_for_action(action, desired, ops_dir=ops_dir)

    onboarded: set[str] = set()
    for action in plan.actions:
        if action.kind != "onboard" or action.arm in onboarded:
            continue
        _onboard(action, desired, ops_dir=ops_dir)
        onboarded.add(action.arm or "")

    if onboarded:
        # Onboarding writes the smoke marker; replan now so --once also starts
        # the monitor in the same cycle instead of waiting for a second tick.
        plan = build_plan(desired, results_dir=results_dir, ops_dir=ops_dir)

    if start_monitors:
        started: set[str] = set()
        for action in plan.actions:
            if action.kind not in {"new-slot", "new", "resume"} or action.experiment_id in started:
                continue
            experiment = _find_experiment(desired, action.experiment_id)
            try:
                _start_monitor(experiment, results_dir=results_dir)
            except OSError as exc:
                notify_human(
                    fingerprint=f"monitor:{experiment.id}:{exc}",
                    title=f"Не удалось запустить monitor {experiment.id}",
                    summary=str(exc),
                    details="Проверьте права на results/ и доступность Python/uv.",
                    ops_dir=ops_dir,
                )
            started.add(action.experiment_id)

    for experiment in desired.experiments:
        if experiment.id in plan.complete_experiments:
            try:
                _publish_completion(experiment, plan, results_dir=results_dir)
            except (OSError, ValueError, RuntimeError) as exc:
                notify_human(
                    fingerprint=f"report:{experiment.id}:{exc}",
                    title=f"Не удалось опубликовать отчёт {experiment.id}",
                    summary=str(exc),
                    details=f"results={results_dir / experiment.id}",
                    ops_dir=ops_dir,
                )
    return plan


def run_fleet(
    *,
    config_path: Path,
    interval: float,
    results_dir: Path = RESULTS_DIR,
    once: bool = False,
) -> int:
    """Run forever (or once in tests) while holding the machine-wide lock."""
    if interval <= 0:
        raise ValueError("interval must be > 0")
    lock_path = results_dir / ".fleet.lock"
    try:
        with exclusive_lock(lock_path):
            while True:
                from benchmark.fleet.config import load_desired

                desired = load_desired(config_path)
                fleet_cycle(desired, results_dir=results_dir)
                if once:
                    return 0
                time.sleep(interval)
    except KeyboardInterrupt:
        return 130

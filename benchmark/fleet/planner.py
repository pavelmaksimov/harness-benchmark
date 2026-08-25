"""Goal-minus-fact planner for unattended benchmark experiments."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmark.arms import get_arm
from benchmark.fleet.config import DesiredConfig, ExperimentTarget
from benchmark.paths import HARNESSES_DIR, RESULTS_DIR

CELL_STATUSES = frozenset({"done", "running", "queued", "blocked-human", "onboarding"})


@dataclass(frozen=True)
class FleetCell:
    experiment_id: str
    arm: str
    run_index: int

    @property
    def key(self) -> str:
        return f"{self.experiment_id}/{self.arm}/run_{self.run_index}"


@dataclass(frozen=True)
class FleetAction:
    experiment_id: str
    kind: str
    arm: str | None = None
    run_index: int | None = None
    reason: str = ""
    command: tuple[str, ...] = ()

    @property
    def cell(self) -> str | None:
        if self.arm is None or self.run_index is None:
            return None
        return FleetCell(self.experiment_id, self.arm, self.run_index).key


@dataclass(frozen=True)
class FleetPlan:
    desired: DesiredConfig
    actions: tuple[FleetAction, ...]
    statuses: dict[str, str]
    reasons: dict[str, str]
    complete_experiments: tuple[str, ...]

    @property
    def runnable(self) -> tuple[FleetAction, ...]:
        return tuple(action for action in self.actions if action.kind in {"resume", "new-slot", "onboard"})

    def as_dict(self) -> dict[str, Any]:
        return {
            "config": str(self.desired.path),
            "actions": [
                {
                    "experiment_id": action.experiment_id,
                    "kind": action.kind,
                    "arm": action.arm,
                    "run_index": action.run_index,
                    "reason": action.reason,
                }
                for action in self.actions
            ],
            "statuses": dict(self.statuses),
            "reasons": dict(self.reasons),
            "complete_experiments": list(self.complete_experiments),
        }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _run_dirs(experiment_dir: Path) -> list[Path]:
    candidates = [path for path in experiment_dir.glob("*/run_*") if path.is_dir()]
    return sorted(
        (path for path in candidates if path.name.removeprefix("run_").isdigit()),
        key=lambda path: (path.parent.name, int(path.name.removeprefix("run_"))),
    )


def _work_path(experiment_dir: Path) -> Path:
    return experiment_dir / ".fleet-work.json"


def _is_live_monitor_command(command: str, experiment_id: str) -> bool:
    return "monitor_benchmark.py" in command and experiment_id in command


def _work_is_live(experiment_dir: Path) -> bool:
    work = _read_json(_work_path(experiment_dir))
    if work:
        pid = work.get("pid")
        if isinstance(pid, int):
            try:
                os.kill(pid, 0)
                command = (Path("/proc") / str(pid) / "cmdline").read_bytes().decode(errors="replace")
                if _is_live_monitor_command(command, str(work.get("experiment_id", ""))):
                    return True
            except OSError:
                pass
    # A daemon restart can happen between Popen and .fleet-work.json.  The
    # command-line scan closes that race and also recognizes a monitor started
    # manually by the operator.
    for pid_dir in Path("/proc").glob("[0-9]*"):
        try:
            command = pid_dir.joinpath("cmdline").read_bytes().decode(errors="replace")
        except OSError:
            continue
        if _is_live_monitor_command(command, experiment_dir.name):
            return True
    return False


def _selection_mismatch(experiment: ExperimentTarget, experiment_dir: Path) -> str | None:
    """Return the first immutable identity mismatch found in old results."""
    expected = experiment.selection()
    for run_dir in _run_dirs(experiment_dir):
        state = _read_json(run_dir / "state.json")
        if state is None:
            continue
        for field, value in expected.items():
            if field in state and state.get(field) != value:
                return f"{field}: recorded={state.get(field)!r} desired={value!r} in {run_dir}"
    return None


def _slot_state(experiment: ExperimentTarget, arm: str, run_index: int, results_dir: Path) -> tuple[str, str]:
    run_dir = results_dir / experiment.id / arm / f"run_{run_index}"
    state = _read_json(run_dir / "state.json")
    if state is None:
        if run_dir.exists():
            return "blocked-human", "run directory exists without state.json; unsafe to overwrite"
        return "queued", "slot is missing"
    if (
        state.get("phase") == "completed"
        and state.get("exit_code") == 0
        and state.get("fully_completed") is True
        and _read_json(run_dir / "metrics" / "run.json") is not None
    ):
        return "done", "completed state and metrics/run.json are present"
    return "queued", f"resume phase={state.get('phase', '?')} stop={state.get('stopped_at_checkpoint', '?')}"


def _known_arm(arm: str) -> bool:
    try:
        get_arm(arm)
    except ValueError:
        return False
    return True


def _open_ticket_for(experiment_id: str, arm: str, ops_dir: Path) -> bool:
    return _ticket_for(experiment_id, arm, ops_dir, unresolved=True)


def _resolved_ticket_for(experiment_id: str, arm: str, ops_dir: Path) -> bool:
    return _ticket_for(experiment_id, arm, ops_dir, unresolved=False)


def _ticket_for(experiment_id: str, arm: str, ops_dir: Path, *, unresolved: bool) -> bool:
    root = ops_dir / "needs-human"
    if not root.is_dir():
        return False
    for path in root.glob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        matches = f"experiment={experiment_id}" in text and (
            f"arm={arm}" in text or f"harness {arm}" in text.lower() or f"{arm}" in text.splitlines()[0:8]
            or "arm=experiment" in text
        )
        is_unresolved = "resolved: true" not in text.lower()
        if matches and is_unresolved == unresolved:
            return True
    return False


def _monitor_terminal_reason(experiment: ExperimentTarget, experiment_dir: Path) -> str | None:
    result = _read_json(experiment_dir / ".monitor-result.json")
    if not result or result.get("status") != "needs-human":
        return None
    if result.get("desired_fingerprint") != experiment.fingerprint():
        return None
    reason = result.get("reason")
    return str(reason) if reason else "monitor repair budget exhausted"


def _arm_needs_onboarding(
    arm: str,
    desired: DesiredConfig,
) -> tuple[bool, str]:
    if not _known_arm(arm):
        target = desired.harness(arm)
        if target.source or (HARNESSES_DIR / arm).is_dir():
            return True, "arm is not registered; wiring/onboarding is required"
        return False, "arm is not registered and has no source in desired.yaml"
    try:
        spec = get_arm(arm)
    except ValueError:
        return False, "unknown arm"
    if not spec.needs_hook:
        return False, "baseline needs no onboarding"
    if not (HARNESSES_DIR / arm).is_dir():
        if desired.harness(arm).source:
            return True, "registered arm is missing its harness payload"
        return False, "registered arm has no harness directory"
    from benchmark.smoke import is_smoke_validated

    if not is_smoke_validated(arm):
        return True, "SMOKE.json is missing, stale, or failed"
    return False, "smoke gate is valid"


def build_plan(
    desired: DesiredConfig,
    *,
    results_dir: Path = RESULTS_DIR,
    ops_dir: Path | None = None,
) -> FleetPlan:
    """Compute all cell statuses without starting SCB, Docker, or an agent."""
    from benchmark.catalog import validate_desired

    validation = validate_desired(desired)
    if not validation.ok:
        raise ValueError("invalid fleet configuration:\n  " + "\n  ".join(issue.render() for issue in validation.issues))
    ops_dir = ops_dir or results_dir.parent
    actions: list[FleetAction] = []
    statuses: dict[str, str] = {}
    reasons: dict[str, str] = {}
    completed_experiments: list[str] = []

    for experiment in desired.experiments:
        experiment_dir = results_dir / experiment.id
        mismatch = _selection_mismatch(experiment, experiment_dir) if experiment_dir.exists() else None
        experiment_blocked = mismatch is not None
        experiment_running = _work_is_live(experiment_dir)
        experiment_complete = True

        onboarding_arms: set[str] = set()
        blocked_arms: set[str] = set()
        for arm in experiment.arms:
            if _open_ticket_for(experiment.id, arm, ops_dir):
                blocked_arms.add(arm)
                reason = "an open human ticket already blocks this arm"
                for run_index in range(1, experiment.runs + 1):
                    key = f"{experiment.id}/{arm}/run_{run_index}"
                    statuses[key] = "blocked-human"
                    reasons[key] = reason
                continue
            onboarding, onboarding_reason = _arm_needs_onboarding(arm, desired)
            if onboarding:
                onboarding_arms.add(arm)
                for run_index in range(1, experiment.runs + 1):
                    key = f"{experiment.id}/{arm}/run_{run_index}"
                    statuses[key] = "onboarding"
                    reasons[key] = onboarding_reason
                actions.append(FleetAction(experiment.id, "onboard", arm=arm, reason=onboarding_reason))
            elif not _known_arm(arm):
                for run_index in range(1, experiment.runs + 1):
                    key = f"{experiment.id}/{arm}/run_{run_index}"
                    statuses[key] = "blocked-human"
                    reasons[key] = onboarding_reason
                actions.append(FleetAction(experiment.id, "ticket", arm=arm, reason=onboarding_reason))

        if experiment_blocked:
            for arm in experiment.arms:
                for run_index in range(1, experiment.runs + 1):
                    key = f"{experiment.id}/{arm}/run_{run_index}"
                    statuses[key] = "blocked-human"
                    reasons[key] = mismatch or "selection mismatch"
            actions.append(FleetAction(experiment.id, "ticket", reason=mismatch or "selection mismatch"))
            continue

        terminal_reason = _monitor_terminal_reason(experiment, experiment_dir)
        if terminal_reason:
            unresolved_ticket = any(_open_ticket_for(experiment.id, arm, ops_dir) for arm in experiment.arms)
            resolved_ticket = any(_resolved_ticket_for(experiment.id, arm, ops_dir) for arm in experiment.arms)
            if not unresolved_ticket and not resolved_ticket:
                actions.append(FleetAction(experiment.id, "ticket", reason=terminal_reason))
            if unresolved_ticket or not resolved_ticket:
                for arm in experiment.arms:
                    for run_index in range(1, experiment.runs + 1):
                        key = f"{experiment.id}/{arm}/run_{run_index}"
                        statuses[key] = "blocked-human"
                        reasons[key] = terminal_reason
                continue

        for arm in experiment.arms:
            if arm in onboarding_arms or arm in blocked_arms or not _known_arm(arm):
                experiment_complete = False
                continue
            for run_index in range(1, experiment.runs + 1):
                key = f"{experiment.id}/{arm}/run_{run_index}"
                state, reason = _slot_state(experiment, arm, run_index, results_dir)
                if state == "done":
                    statuses[key] = "done"
                elif experiment_running:
                    statuses[key] = "running"
                    reasons[key] = "fleet monitor is live"
                else:
                    statuses[key] = "queued"
                    reasons[key] = reason
                if state != "done":
                    experiment_complete = False

        if experiment_complete:
            completed_experiments.append(experiment.id)
            continue
        if experiment_running:
            continue
        if onboarding_arms:
            continue
        pending = [
            key for key, status in statuses.items()
            if key.startswith(f"{experiment.id}/") and status == "queued"
        ]
        if pending:
            first = pending[0].split("/")
            arm = first[1]
            run_index = int(first[2].removeprefix("run_"))
            kind = "resume" if (results_dir / experiment.id / arm / f"run_{run_index}" / "state.json").exists() else "new-slot"
            actions.append(FleetAction(experiment.id, kind, arm=arm, run_index=run_index, reason=reasons[pending[0]]))

    return FleetPlan(
        desired=desired,
        actions=tuple(actions),
        statuses=statuses,
        reasons=reasons,
        complete_experiments=tuple(completed_experiments),
    )


def render_plan(plan: FleetPlan) -> str:
    lines = [f"desired={plan.desired.path}"]
    for action in plan.actions:
        cell = action.cell or action.experiment_id
        suffix = f" — {action.reason}" if action.reason else ""
        lines.append(f"{action.kind:10} {cell}{suffix}")
    if not plan.actions:
        lines.append("idle")
    return "\n".join(lines)


def render_status(plan: FleetPlan) -> str:
    lines = []
    for key in sorted(plan.statuses):
        reason = plan.reasons.get(key)
        lines.append(f"{plan.statuses[key]:14} {key}" + (f" — {reason}" if reason else ""))
    return "\n".join(lines) if lines else "no desired cells"

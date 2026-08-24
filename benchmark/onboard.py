"""Bounded harness onboarding used by the fleet daemon.

The daemon owns the state machine.  A model may be used only through the
explicit ``HB_FLEET_ONBOARD_COMMAND`` escape hatch and is never allowed to
start benchmark runs itself.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmark.arms import get_arm
from benchmark.fleet.config import ExperimentTarget, HarnessTarget
from benchmark.paths import HARNESSES_DIR, REPO_ROOT, RESULTS_DIR
from benchmark.scb_run import run_smoke
from benchmark.smoke import is_smoke_validated
from scripts.pin_harness import pin_arm


@dataclass(frozen=True)
class OnboardingResult:
    arm: str
    ok: bool
    attempts: int
    reason: str
    smoke_marker: str | None = None


def _run_agent(arm: str, target: HarnessTarget) -> bool:
    command_text = os.environ.get("HB_FLEET_ONBOARD_COMMAND")
    if not command_text:
        return False
    prompt = (
        "Onboard exactly one benchmark harness. Work only in the current repository and "
        f"only on harnesses/{arm}, its ArmSpec/config/prompt, and required docs/tests. "
        "Do not start full benchmark runs, do not edit results, TODO.md, .profile, or .bashrc. "
        "Follow docs/harness-onboarding.md, use non-interactive commands, pin the harness, "
        "and stop after the wiring is ready.\n\n"
        f"source:\n{target.source or '(none)'}\n\n"
        f"install guidance:\n{target.install or '(none)'}\n"
        f"documentation:\n{target.docs or '(none)'}\n"
    )
    command = [part.replace("{arm}", arm) for part in shlex.split(command_text)]
    if not command:
        return False
    try:
        result = subprocess.run(
            command + [prompt],
            cwd=str(REPO_ROOT),
            env={**os.environ, "HB_FLEET_ONBOARD_ARM": arm},
            check=False,
            timeout=1800,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _run_dir_from_collected(collected: dict[str, Any]) -> Path | None:
    checkpoints = collected.get("checkpoints") or []
    for checkpoint in checkpoints:
        path = (checkpoint.get("paths") or {}).get("run_dir")
        if isinstance(path, str):
            return Path(path)
        snapshot = (checkpoint.get("paths") or {}).get("snapshot_dir")
        if isinstance(snapshot, str):
            path = Path(snapshot)
            return path.parents[4] if len(path.parents) > 4 else None
    return None


def _all_run_text(run_dir: Path) -> str:
    chunks: list[str] = []
    if not run_dir.is_dir():
        return ""
    for path in run_dir.rglob("*"):
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        if path.suffix.lower() not in {".json", ".txt", ".log", ".md", ".yaml", ".yml"}:
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(chunks)


def _expectation_failures(target: HarnessTarget, run_dir: Path | None) -> list[str]:
    if not target.expect:
        return []
    text = _all_run_text(run_dir) if run_dir else ""
    snapshot = None
    if run_dir:
        snapshots = sorted(run_dir.glob("scb/*/checkpoint_*/snapshot"))
        snapshot = snapshots[-1] if snapshots else None
    failures: list[str] = []
    for expectation in target.expect:
        normalized = expectation.strip(" `")
        if snapshot and (snapshot / normalized).exists():
            continue
        if normalized in text or normalized.replace(" ", "") in text.replace(" ", ""):
            continue
        # A path-like token in free text is a useful deterministic check even
        # when the operator wrote prose around it.
        path_tokens = [token.strip("`'\".,()") for token in expectation.split() if "/" in token or token.endswith((".json", ".html", ".md"))]
        if snapshot and any((snapshot / token).exists() for token in path_tokens):
            continue
        failures.append(expectation)
    return failures


def _smoke_quality(collected: dict[str, Any], target: HarnessTarget) -> tuple[bool, str, Path | None]:
    run_dir = _run_dir_from_collected(collected)
    if not collected.get("smoke_ok"):
        return False, "smoke gate failed", run_dir
    if collected.get("harness_activation_verified") is False:
        return False, "harness_activation_verified=false", run_dir
    diagnostics = _all_run_text(run_dir) if run_dir else ""
    if '"infrastructure_failure": true' in diagnostics:
        return False, "runner infrastructure_failure=true", run_dir
    if re.search(r"ModuleNotFoundError|ImportError|ERROR at setup|collection error", diagnostics, re.IGNORECASE):
        return False, "bench setup/import ERROR", run_dir
    for checkpoint in collected.get("checkpoints") or []:
        correctness = checkpoint.get("correctness") or {}
        if int(correctness.get("core_failed") or 0) > 0:
            return False, "smoke Core assertions failed", run_dir
    failures = _expectation_failures(target, run_dir)
    if failures:
        return False, "expect not confirmed: " + "; ".join(failures), run_dir
    return True, "smoke and expectations passed", run_dir


def _expectation_record(arm: str, experiment: ExperimentTarget) -> Path:
    return RESULTS_DIR / experiment.id / ".fleet-onboarding" / f"{arm}.json"


def _expectations_already_checked(arm: str, experiment: ExperimentTarget, target: HarnessTarget) -> bool:
    path = _expectation_record(arm, experiment)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(value, dict) and value.get("expect") == list(target.expect)


def _record_expectations(arm: str, experiment: ExperimentTarget, target: HarnessTarget) -> None:
    path = _expectation_record(arm, experiment)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"arm": arm, "expect": list(target.expect), "checked_at": experiment.fingerprint()}) + "\n",
        encoding="utf-8",
    )


def onboard_arm(
    arm: str,
    *,
    target: HarnessTarget,
    experiment: ExperimentTarget,
    max_attempts: int = 3,
) -> OnboardingResult:
    """Pin and CP1+CP2-smoke one arm, with a hard repair-attempt ceiling."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    attempts = 0
    for attempts in range(1, max_attempts + 1):
        try:
            spec = get_arm(arm)
        except ValueError:
            if not _run_agent(arm, target):
                return OnboardingResult(arm, False, attempts, "arm is not registered; no onboarding agent succeeded")
            continue
        harness_dir = HARNESSES_DIR / arm
        if spec.needs_hook and not harness_dir.is_dir():
            if not _run_agent(arm, target):
                return OnboardingResult(arm, False, attempts, f"missing harness directory: {harness_dir}")
            continue
        if spec.needs_hook and spec.kind != "legacy_ponytail":
            try:
                pin_arm(arm)
            except (OSError, ValueError, SystemExit) as exc:
                if not _run_agent(arm, target):
                    return OnboardingResult(arm, False, attempts, f"pin failed: {exc}")
                continue
        if is_smoke_validated(arm) and (not target.expect or _expectations_already_checked(arm, experiment, target)):
            return OnboardingResult(arm, True, attempts, "existing smoke marker is valid")
        collected: dict[str, Any] | None = None
        try:
            collected = run_smoke(
                arm=arm,
                problem=experiment.problem,
                agent=experiment.agent,
                provider=experiment.provider,
                model=experiment.model,
                thinking=experiment.thinking,
                checkpoint_count=2,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            ok, reason, _ = False, f"smoke invocation failed: {exc}", None
        else:
            ok, reason, _ = _smoke_quality(collected, target)
        if ok:
            _record_expectations(arm, experiment, target)
            return OnboardingResult(
                arm, True, attempts, reason, str(collected.get("smoke_marker")) if collected else None
            )
        repairable = not reason.startswith(("runner infrastructure", "bench setup"))
        if repairable and attempts < max_attempts and _run_agent(arm, target):
            continue
        return OnboardingResult(arm, False, attempts, reason)
    return OnboardingResult(arm, False, attempts, "onboarding attempt ceiling reached")

"""Rework loop hook: when a checkpoint's tests fail, send the task back to
the agent with explicit feedback instead of stopping the trajectory.

Flow inside one SCB checkpoint:

1. ``AgentRunner._run_checkpoint`` runs solve + eval as usual.
2. If the eval failed the pass policy (Core tests), the hook re-invokes
   ``_run_checkpoint`` for the *same* checkpoint with the original prompt
   plus a ``[REWORK ATTEMPT N]`` feedback block listing the failing tests.
   The workspace keeps the previous attempt's code, so the agent fixes
   in place.
3. Each attempt re-evaluates; the loop stops when an attempt passes, when
   the agent errors / hits the rate limit, when the evaluation is an
   infrastructure failure (bench problem, not a model defect — see the
   failure-triage rule), or when ``max_attempts`` extra attempts are used.
4. Per-attempt outcomes are persisted to ``<checkpoint>/rework.json``;
   the harness-side ``benchmark/rework.py`` turns them into failure records
   and run-level statistics.

The hook is installed from ``benchmark/scb_main.py`` and
``harness_sitecustomize`` (so ProcessPool workers get it too) when
``HB_REWORK_ATTEMPTS`` is set to a positive integer.  The patch is a
runtime monkeypatch on the vendored SCB runner — the vendor tree itself
stays untouched (see benchmark-core rule: prefer overrides over forks).
"""

from __future__ import annotations

import functools
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("hb.rework")

REWORK_FILENAME = "rework.json"
HB_REWORK_ATTEMPTS = "HB_REWORK_ATTEMPTS"

_INSTALLED = False


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def failed_test_names(evaluation: dict[str, Any]) -> list[str]:
    """Collect failed test node names from the per-bucket tests dict."""
    tests = evaluation.get("tests") or {}
    failed: list[str] = []
    for bucket in tests.values():
        failed.extend(bucket.get("failed") or [])
    return failed


def _escape_jinja(text: str) -> str:
    """Neutralize Jinja delimiters so feedback can never be parsed as template.

    The feedback block is appended to the checkpoint prompt *template*; test
    names or messages containing ``{{``/``{%`` would otherwise break rendering.
    """
    return (
        text.replace("{{", "{ {")
        .replace("}}", "} }")
        .replace("{%", "{ %")
        .replace("%}", "% }")
    )


def build_feedback(checkpoint_dir: Path, attempt: int) -> str | None:
    """Build a rework feedback block from the checkpoint's evaluation.json.

    Returns ``None`` when there is nothing to fix: no evaluation, no failing
    tests, or an infrastructure failure (infra errors are runner/problem
    packaging defects and must not trigger rework).
    """
    evaluation = _read_json(checkpoint_dir / "evaluation.json")
    if not evaluation:
        return None
    if evaluation.get("infrastructure_failure"):
        return None
    failed = failed_test_names(evaluation)
    if not failed:
        return None
    lines = [
        f"[REWORK ATTEMPT {attempt}]",
        (
            "The solution did not pass the checkpoint test suite. Fix the code "
            "in this workspace so the failing tests pass while keeping the "
            "already-passing behavior intact."
        ),
        (
            "Results: "
            f"pass_counts={json.dumps(evaluation.get('pass_counts') or {})} "
            f"total_counts={json.dumps(evaluation.get('total_counts') or {})}"
        ),
        "Failing tests:",
        *(f"- {name}" for name in failed),
    ]
    return "\n".join(lines)


def _attempt_record(attempt: int, passed_policy: bool | None, checkpoint_dir: Path) -> dict[str, Any]:
    """Snapshot one attempt's outcome from the checkpoint artifacts."""
    evaluation = _read_json(checkpoint_dir / "evaluation.json") or {}
    return {
        "attempt": attempt,
        "passed_policy": passed_policy,
        "pass_counts": evaluation.get("pass_counts"),
        "total_counts": evaluation.get("total_counts"),
        "failed_tests": failed_test_names(evaluation),
        "infrastructure_failure": bool(evaluation.get("infrastructure_failure")),
        "duration": evaluation.get("duration"),
    }


class ReworkLog:
    """Accumulates per-attempt outcomes and persists them as rework.json."""

    def __init__(self, checkpoint_dir: Path, max_attempts: int) -> None:
        self.checkpoint_dir = Path(checkpoint_dir)
        self.max_attempts = max_attempts
        self.attempts: list[dict[str, Any]] = []

    def record(self, attempt: int, passed_policy: bool | None, checkpoint_dir: Path) -> None:
        self.attempts.append(_attempt_record(attempt, passed_policy, checkpoint_dir))

    @property
    def fixed(self) -> bool:
        return bool(self.attempts and self.attempts[-1].get("passed_policy"))

    def write(self) -> Path:
        data = {
            "checkpoint": self.checkpoint_dir.name,
            "max_additional_attempts": self.max_attempts,
            "attempts_total": len(self.attempts),
            "fixed": self.fixed,
            "attempts": self.attempts,
        }
        path = self.checkpoint_dir / REWORK_FILENAME
        path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return path


def install_rework_hook(max_attempts: int) -> None:
    """Wrap ``AgentRunner._run_checkpoint`` with the rework loop.

    Idempotent: the wrapper is installed once per process (sitecustomize may
    also install it in workers spawned before ``benchmark.scb_main`` ran).
    """
    global _INSTALLED
    if _INSTALLED or max_attempts <= 0:
        return
    _INSTALLED = True

    from slop_code.agent_runner.runner import AgentRunner, AgentStateEnum

    original: Callable[..., Any] = AgentRunner._run_checkpoint

    @functools.wraps(original)
    def _run_checkpoint_with_rework(
        self: Any,
        checkpoint: Any,
        checkpoint_save_dir: Path,
        is_first_checkpoint: bool,
    ) -> Any:
        summary = original(self, checkpoint, checkpoint_save_dir, is_first_checkpoint)
        # Only test failures trigger rework: no eval / agent errors / rate
        # limits / concurrent-eval mode are not reworkable.
        if summary.had_error:
            return summary
        if self.run_spec.skip_evaluation or self.run_spec.concurrent_evaluation:
            return summary
        if summary.passed_policy is not False:
            return summary
        if self.metrics_tracker.state in (
            AgentStateEnum.ERROR,
            AgentStateEnum.HIT_RATE_LIMITED,
        ):
            return summary

        checkpoint_dir = Path(checkpoint_save_dir)
        log = ReworkLog(checkpoint_dir, max_attempts)
        log.record(1, summary.passed_policy, checkpoint_dir)
        feedback = build_feedback(checkpoint_dir, attempt=1)
        if feedback is None:
            return summary

        for attempt in range(2, max_attempts + 2):
            original_template = self.run_spec.template
            self.run_spec.template = f"{original_template}\n\n{_escape_jinja(feedback)}"
            try:
                summary = original(self, checkpoint, checkpoint_save_dir, False)
            except BaseException:
                log.write()
                raise
            finally:
                self.run_spec.template = original_template
            log.record(attempt, summary.passed_policy, checkpoint_dir)
            if summary.passed_policy or summary.had_error:
                break
            if self.metrics_tracker.state in (
                AgentStateEnum.ERROR,
                AgentStateEnum.HIT_RATE_LIMITED,
            ):
                break
            feedback = build_feedback(checkpoint_dir, attempt=attempt)
            if feedback is None:
                break
        log.write()
        return summary

    AgentRunner._run_checkpoint = _run_checkpoint_with_rework
    logger.info(
        "rework hook installed",
        max_additional_attempts=max_attempts,
    )
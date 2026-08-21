"""Keep benchmark trajectories running after a test-only checkpoint failure."""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

_INSTALLED = False


def _checkpoint_has_infrastructure_failure(summary: Any) -> bool:
    checkpoint_dir = getattr(summary, "path", None)
    if checkpoint_dir is None:
        return False
    evaluation_path = Path(checkpoint_dir) / "evaluation.json"
    if not evaluation_path.exists():
        return False
    try:
        data = json.loads(evaluation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and bool(data.get("infrastructure_failure"))


def install_continue_after_test_failure() -> None:
    """Do not let a test failure prevent later checkpoints from running.

    Agent errors, rate limits, and infrastructure failures still go through
    SCB's original stop logic. The hook is process-local and idempotent
    because SCB also starts worker processes with ``harness_sitecustomize`` on
    ``PYTHONPATH``.
    """
    global _INSTALLED
    if _INSTALLED:
        return

    from slop_code.agent_runner.runner import AgentRunner, AgentStateEnum

    original = AgentRunner._should_early_stop

    @functools.wraps(original)
    def _should_early_stop(self: Any, summary: Any) -> bool:
        test_failure = (
            summary.passed_policy is False
            and not summary.had_error
            and not self.run_spec.skip_evaluation
            and not self.run_spec.concurrent_evaluation
        )
        if (
            test_failure
            and not _checkpoint_has_infrastructure_failure(summary)
            and self.metrics_tracker.state
            not in (
                AgentStateEnum.ERROR,
                AgentStateEnum.HIT_RATE_LIMITED,
            )
        ):
            return False
        return original(self, summary)

    AgentRunner._should_early_stop = _should_early_stop
    _INSTALLED = True

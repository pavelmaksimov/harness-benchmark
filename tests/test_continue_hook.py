from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from benchmark import continue_hook


class FakeState:
    ERROR = "error"
    HIT_RATE_LIMITED = "rate_limited"


def test_test_failure_does_not_stop_trajectory() -> None:
    calls: list[object] = []

    class FakeRunner:
        def _should_early_stop(self, summary):
            calls.append(summary)
            return True

    module = types.ModuleType("slop_code.agent_runner.runner")
    module.AgentRunner = FakeRunner
    module.AgentStateEnum = FakeState
    previous = continue_hook._INSTALLED
    continue_hook._INSTALLED = False
    try:
        with mock.patch.dict(sys.modules, {module.__name__: module}):
            continue_hook.install_continue_after_test_failure()
            runner = FakeRunner()
            runner.run_spec = SimpleNamespace(
                skip_evaluation=False, concurrent_evaluation=False
            )
            runner.metrics_tracker = SimpleNamespace(state="evaluating")
            assert (
                FakeRunner._should_early_stop(
                    runner, SimpleNamespace(passed_policy=False, had_error=False)
                )
                is False
            )
        assert calls == []
    finally:
        continue_hook._INSTALLED = previous


def test_infrastructure_failure_keeps_original_stop_logic(tmp_path: Path) -> None:
    cp_dir = tmp_path / "checkpoint_1"
    cp_dir.mkdir()
    (cp_dir / "evaluation.json").write_text(
        json.dumps({"infrastructure_failure": True, "pass_counts": {"Core": 0}}),
        encoding="utf-8",
    )

    class FakeRunner:
        def _should_early_stop(self, summary):
            return True

    module = types.ModuleType("slop_code.agent_runner.runner")
    module.AgentRunner = FakeRunner
    module.AgentStateEnum = FakeState
    previous = continue_hook._INSTALLED
    continue_hook._INSTALLED = False
    try:
        with mock.patch.dict(sys.modules, {module.__name__: module}):
            continue_hook.install_continue_after_test_failure()
            runner = FakeRunner()
            runner.run_spec = SimpleNamespace(
                skip_evaluation=False, concurrent_evaluation=False
            )
            runner.metrics_tracker = SimpleNamespace(state="evaluating")
            assert (
                FakeRunner._should_early_stop(
                    runner,
                    SimpleNamespace(
                        passed_policy=False,
                        had_error=False,
                        path=cp_dir,
                    ),
                )
                is True
            )
    finally:
        continue_hook._INSTALLED = previous


def test_agent_error_keeps_original_stop_logic() -> None:
    class FakeRunner:
        def _should_early_stop(self, summary):
            return True

    module = types.ModuleType("slop_code.agent_runner.runner")
    module.AgentRunner = FakeRunner
    module.AgentStateEnum = FakeState
    previous = continue_hook._INSTALLED
    continue_hook._INSTALLED = False
    try:
        with mock.patch.dict(sys.modules, {module.__name__: module}):
            continue_hook.install_continue_after_test_failure()
            runner = FakeRunner()
            runner.run_spec = SimpleNamespace(
                skip_evaluation=False, concurrent_evaluation=False
            )
            runner.metrics_tracker = SimpleNamespace(state="error")
            assert (
                FakeRunner._should_early_stop(
                    runner, SimpleNamespace(passed_policy=False, had_error=True)
                )
                is True
            )
    finally:
        continue_hook._INSTALLED = previous

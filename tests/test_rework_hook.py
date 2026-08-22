import json
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

from benchmark import rework_hook
from benchmark.rework_hook import (
    ReworkLog,
    build_feedback,
    failed_test_names,
    install_rework_hook,
)


class FakeState:
    ERROR = "error"
    HIT_RATE_LIMITED = "rate_limited"


def _write_eval(cp_dir: Path, *, failed: list[str] | None = None, infra: bool = False) -> None:
    data = {
        "pass_counts": {"Core": 2, "Functionality": 1},
        "total_counts": {"Core": 3, "Functionality": 1},
        "tests": {"checkpoint_1-Core": {"passed": [], "failed": failed or []}},
        "infrastructure_failure": infra,
        "duration": 12.5,
    }
    (cp_dir / "evaluation.json").write_text(json.dumps(data), encoding="utf-8")


def _write_inference(cp_dir: Path) -> None:
    data = {
        "elapsed": 4.5,
        "usage": {
            "net_tokens": {
                "input": 101,
                "output": 37,
                "cache_read": 11,
                "cache_write": 3,
                "reasoning": 19,
            },
            "steps": 6,
            "cost": 0.12,
        },
    }
    (cp_dir / "inference_result.json").write_text(json.dumps(data), encoding="utf-8")


class EscapeAndFeedbackTests(unittest.TestCase):
    def test_escape_jinja_neutralizes_delimiters(self) -> None:
        text = "{{danger}} {%if x%} {%endif%} done"
        out = rework_hook._escape_jinja(text)
        self.assertNotIn("{{", out)
        self.assertNotIn("{%", out)
        self.assertEqual(out, "{ {danger} } { %if x% } { %endif% } done")

    def test_failed_test_names_collects_across_buckets(self) -> None:
        evaluation = {
            "tests": {
                "checkpoint_1-Core": {"failed": ["a", "b"]},
                "checkpoint_1-Functionality": {"failed": ["c"]},
                "checkpoint_1-Error": {"failed": []},
            }
        }
        self.assertEqual(failed_test_names(evaluation), ["a", "b", "c"])

    def test_build_feedback_none_without_evaluation(self) -> None:
        with TemporaryDirectory() as td:
            self.assertIsNone(build_feedback(Path(td), attempt=1))

    def test_build_feedback_none_on_infrastructure_failure(self) -> None:
        with TemporaryDirectory() as td:
            cp_dir = Path(td)
            _write_eval(cp_dir, failed=["x"], infra=True)
            self.assertIsNone(build_feedback(cp_dir, attempt=1))

    def test_build_feedback_none_when_nothing_failed(self) -> None:
        with TemporaryDirectory() as td:
            cp_dir = Path(td)
            _write_eval(cp_dir, failed=[])
            self.assertIsNone(build_feedback(cp_dir, attempt=1))

    def test_build_feedback_lists_failing_tests(self) -> None:
        with TemporaryDirectory() as td:
            cp_dir = Path(td)
            _write_eval(cp_dir, failed=["test_a", "test_b"])
            feedback = build_feedback(cp_dir, attempt=2)
            self.assertIsNotNone(feedback)
            assert feedback is not None
            self.assertIn("[REWORK ATTEMPT 2]", feedback)
            self.assertIn("test_a", feedback)
            self.assertIn("test_b", feedback)
            self.assertIn("pass_counts={", feedback)
            self.assertIn("Core: passed=2 failed=1 total=3", feedback)


class ReworkLogTests(unittest.TestCase):
    def test_record_persists_group_and_usage_metrics(self) -> None:
        with TemporaryDirectory() as td:
            cp_dir = Path(td) / "checkpoint_1"
            cp_dir.mkdir()
            _write_eval(cp_dir, failed=["test_x"])
            _write_inference(cp_dir)

            log = ReworkLog(cp_dir, max_attempts=2)
            log.record(1, False, cp_dir)
            data = json.loads(log.write().read_text(encoding="utf-8"))
            attempt = data["attempts"][0]

            self.assertEqual(
                attempt["core"],
                {"passed": 2, "failed": 1, "total": 3, "failed_tests": ["test_x"]},
            )
            self.assertEqual(attempt["groups"]["Functionality"]["total"], 1)
            self.assertEqual(attempt["failed_tests_by_group"], {"Core": ["test_x"]})
            self.assertEqual(attempt["usage"]["input_tokens"], 101)
            self.assertEqual(attempt["usage"]["output_tokens"], 37)
            self.assertEqual(attempt["usage"]["cache_read_tokens"], 11)
            self.assertEqual(attempt["usage"]["cache_write_tokens"], 3)
            self.assertEqual(attempt["usage"]["reasoning_tokens"], 19)
            self.assertEqual(attempt["usage"]["steps"], 6)
            self.assertEqual(attempt["usage"]["elapsed_seconds"], 4.5)
            self.assertEqual(attempt["usage"]["reported_cost_usd"], 0.12)
            self.assertEqual(attempt["input_tokens"], 101)
            self.assertEqual(attempt["output_tokens"], 37)
            self.assertEqual(attempt["steps"], 6)
            self.assertEqual(attempt["elapsed_seconds"], 4.5)

    def test_write_persists_attempts_and_fixed(self) -> None:
        with TemporaryDirectory() as td:
            cp_dir = Path(td) / "checkpoint_1"
            cp_dir.mkdir()
            log = ReworkLog(cp_dir, max_attempts=2)
            log.record(1, False, cp_dir)
            log.record(2, True, cp_dir)
            path = log.write()
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["checkpoint"], "checkpoint_1")
            self.assertEqual(data["attempts_total"], 2)
            self.assertTrue(data["fixed"])
            self.assertEqual(data["attempts"][0]["attempt"], 1)
            self.assertFalse(data["attempts"][0]["passed_policy"])
            self.assertEqual(data["attempts"][1]["passed_policy"], True)
            self.assertEqual(data["attempts"][1]["failed_tests"], [])


class InstallHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self._was_installed = rework_hook._INSTALLED

    def tearDown(self) -> None:
        rework_hook._INSTALLED = self._was_installed

    def _fake_module(self, fake_runner_class: type) -> types.ModuleType:
        module = types.ModuleType("slop_code.agent_runner.runner")
        module.AgentRunner = fake_runner_class
        module.AgentStateEnum = FakeState
        return module

    def _install(self, fake_runner_class: type, max_attempts: int) -> None:
        rework_hook._INSTALLED = False
        with mock.patch.dict(sys.modules, {"slop_code.agent_runner.runner": self._fake_module(fake_runner_class)}):
            install_rework_hook(max_attempts)

    def test_loop_retries_with_feedback_and_writes_rework_json(self) -> None:
        with TemporaryDirectory() as td:
            cp_dir = Path(td) / "checkpoint_1"
            cp_dir.mkdir()
            calls: list[tuple] = []

            def fake_original(self, checkpoint, checkpoint_save_dir, is_first_checkpoint):
                template_at_call = self.run_spec.template
                calls.append((checkpoint_save_dir, is_first_checkpoint, template_at_call))
                if len(calls) == 1:
                    _write_eval(Path(checkpoint_save_dir), failed=["test_x"])
                    return SimpleNamespace(passed_policy=False, had_error=False)
                _write_eval(Path(checkpoint_save_dir), failed=[])
                return SimpleNamespace(passed_policy=True, had_error=False)

            class FakeRunner:
                pass

            FakeRunner._run_checkpoint = fake_original
            runner = FakeRunner()
            runner.run_spec = SimpleNamespace(
                template="ORIGINAL", skip_evaluation=False, concurrent_evaluation=False
            )
            runner.metrics_tracker = SimpleNamespace(state="evaluating")

            self._install(FakeRunner, max_attempts=2)
            summary = FakeRunner._run_checkpoint(runner, "checkpoint_1", str(cp_dir), True)

            self.assertTrue(summary.passed_policy)
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0][1], True)
            self.assertEqual(calls[1][1], False)  # rework attempt reuses checkpoint dir
            self.assertIn("REWORK ATTEMPT 1", calls[1][2])
            self.assertEqual(calls[1][2].startswith("ORIGINAL\n\n"), True)
            self.assertEqual(runner.run_spec.template, "ORIGINAL")  # restored

            rework = json.loads((cp_dir / "rework.json").read_text(encoding="utf-8"))
            self.assertEqual(rework["attempts_total"], 2)
            self.assertTrue(rework["fixed"])
            self.assertEqual(rework["attempts"][0]["stage"], "creation")
            self.assertEqual(rework["attempts"][1]["stage"], "rework")

    def test_stops_when_attempts_exhausted(self) -> None:
        with TemporaryDirectory() as td:
            cp_dir = Path(td) / "checkpoint_1"
            cp_dir.mkdir()
            calls: list[str] = []

            def fake_original(self, checkpoint, checkpoint_save_dir, is_first_checkpoint):
                calls.append(checkpoint_save_dir)
                body = "CANONICAL PROMPT" if len(calls) == 1 else f"CANONICAL PROMPT\n\n[REWORK ATTEMPT {len(calls) - 1}]"
                (Path(checkpoint_save_dir) / "prompt.txt").write_text(body, encoding="utf-8")
                _write_eval(Path(checkpoint_save_dir), failed=["test_x"])
                return SimpleNamespace(passed_policy=False, had_error=False)

            class FakeRunner:
                pass

            FakeRunner._run_checkpoint = fake_original
            runner = FakeRunner()
            runner.run_spec = SimpleNamespace(
                template="T", skip_evaluation=False, concurrent_evaluation=False
            )
            runner.metrics_tracker = SimpleNamespace(state="evaluating")

            self._install(FakeRunner, max_attempts=2)
            summary = FakeRunner._run_checkpoint(runner, "checkpoint_1", str(cp_dir), True)

            self.assertFalse(summary.passed_policy)
            self.assertEqual(len(calls), 3)  # initial + 2 rework attempts
            rework = json.loads((cp_dir / "rework.json").read_text(encoding="utf-8"))
            self.assertEqual(rework["attempts_total"], 3)
            self.assertFalse(rework["fixed"])
            self.assertEqual(
                (cp_dir / "prompt.txt").read_text(encoding="utf-8"),
                "CANONICAL PROMPT",
            )

    def test_no_rework_on_agent_error(self) -> None:
        with TemporaryDirectory() as td:
            cp_dir = Path(td) / "checkpoint_1"
            cp_dir.mkdir()
            calls: list[str] = []

            def fake_original(self, checkpoint, checkpoint_save_dir, is_first_checkpoint):
                calls.append(checkpoint_save_dir)
                _write_eval(Path(checkpoint_save_dir), failed=["test_x"])
                return SimpleNamespace(passed_policy=False, had_error=True)

            class FakeRunner:
                pass

            FakeRunner._run_checkpoint = fake_original
            runner = FakeRunner()
            runner.run_spec = SimpleNamespace(
                template="T", skip_evaluation=False, concurrent_evaluation=False
            )
            runner.metrics_tracker = SimpleNamespace(state="evaluating")

            self._install(FakeRunner, max_attempts=2)
            FakeRunner._run_checkpoint(runner, "checkpoint_1", str(cp_dir), True)

            self.assertEqual(len(calls), 1)
            self.assertFalse((cp_dir / "rework.json").exists())

    def test_no_rework_on_rate_limit(self) -> None:
        with TemporaryDirectory() as td:
            cp_dir = Path(td) / "checkpoint_1"
            cp_dir.mkdir()
            calls: list[str] = []

            def fake_original(self, checkpoint, checkpoint_save_dir, is_first_checkpoint):
                calls.append(checkpoint_save_dir)
                _write_eval(Path(checkpoint_save_dir), failed=["test_x"])
                return SimpleNamespace(passed_policy=False, had_error=False)

            class FakeRunner:
                pass

            FakeRunner._run_checkpoint = fake_original
            runner = FakeRunner()
            runner.run_spec = SimpleNamespace(
                template="T", skip_evaluation=False, concurrent_evaluation=False
            )
            runner.metrics_tracker = SimpleNamespace(state=FakeState.HIT_RATE_LIMITED)

            self._install(FakeRunner, max_attempts=2)
            FakeRunner._run_checkpoint(runner, "checkpoint_1", str(cp_dir), True)

            self.assertEqual(len(calls), 1)
            self.assertFalse((cp_dir / "rework.json").exists())

    def test_no_rework_on_infrastructure_failure(self) -> None:
        with TemporaryDirectory() as td:
            cp_dir = Path(td) / "checkpoint_1"
            cp_dir.mkdir()
            calls: list[str] = []

            def fake_original(self, checkpoint, checkpoint_save_dir, is_first_checkpoint):
                calls.append(checkpoint_save_dir)
                _write_eval(Path(checkpoint_save_dir), failed=["test_x"], infra=True)
                return SimpleNamespace(passed_policy=False, had_error=False)

            class FakeRunner:
                pass

            FakeRunner._run_checkpoint = fake_original
            runner = FakeRunner()
            runner.run_spec = SimpleNamespace(
                template="T", skip_evaluation=False, concurrent_evaluation=False
            )
            runner.metrics_tracker = SimpleNamespace(state="evaluating")

            self._install(FakeRunner, max_attempts=2)
            FakeRunner._run_checkpoint(runner, "checkpoint_1", str(cp_dir), True)

            self.assertEqual(len(calls), 1)
            self.assertFalse((cp_dir / "rework.json").exists())

    def test_install_zero_is_noop(self) -> None:
        with TemporaryDirectory() as td:
            cp_dir = Path(td) / "checkpoint_1"
            cp_dir.mkdir()
            calls: list[str] = []

            def fake_original(self, checkpoint, checkpoint_save_dir, is_first_checkpoint):
                calls.append(checkpoint_save_dir)
                _write_eval(Path(checkpoint_save_dir), failed=["test_x"])
                return SimpleNamespace(passed_policy=False, had_error=False)

            class FakeRunner:
                pass

            FakeRunner._run_checkpoint = fake_original
            runner = FakeRunner()
            runner.run_spec = SimpleNamespace(
                template="T", skip_evaluation=False, concurrent_evaluation=False
            )
            runner.metrics_tracker = SimpleNamespace(state="evaluating")

            self._install(FakeRunner, max_attempts=0)
            FakeRunner._run_checkpoint(runner, "checkpoint_1", str(cp_dir), True)

            self.assertEqual(len(calls), 1)
            self.assertFalse((cp_dir / "rework.json").exists())

    def test_install_is_idempotent(self) -> None:
        with TemporaryDirectory() as td:
            cp_dir = Path(td) / "checkpoint_1"
            cp_dir.mkdir()
            calls: list[str] = []

            def fake_original(self, checkpoint, checkpoint_save_dir, is_first_checkpoint):
                calls.append(checkpoint_save_dir)
                _write_eval(Path(checkpoint_save_dir), failed=["test_x"])
                return SimpleNamespace(passed_policy=False, had_error=False)

            class FakeRunner:
                pass

            FakeRunner._run_checkpoint = fake_original
            runner = FakeRunner()
            runner.run_spec = SimpleNamespace(
                template="T", skip_evaluation=False, concurrent_evaluation=False
            )
            runner.metrics_tracker = SimpleNamespace(state="evaluating")

            rework_hook._INSTALLED = False
            with mock.patch.dict(sys.modules, {"slop_code.agent_runner.runner": self._fake_module(FakeRunner)}):
                install_rework_hook(2)
                wrapped = FakeRunner._run_checkpoint
                install_rework_hook(2)
                self.assertIs(FakeRunner._run_checkpoint, wrapped)  # no double wrap

            FakeRunner._run_checkpoint(runner, "checkpoint_1", str(cp_dir), True)
            self.assertEqual(len(calls), 3)  # initial + 2 rework attempts
            self.assertTrue((cp_dir / "rework.json").exists())


if __name__ == "__main__":
    unittest.main()
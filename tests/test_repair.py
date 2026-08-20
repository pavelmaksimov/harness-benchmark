import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import benchmark.repair as repair
import benchmark.failures as failures


def _make_checkpoint(scb_problem_dir: Path, name: str, evaluation: dict) -> None:
    cp_dir = scb_problem_dir / name
    (cp_dir / "snapshot").mkdir(parents=True)
    (cp_dir / "evaluation.json").write_text(
        json.dumps(evaluation), encoding="utf-8"
    )
    (cp_dir / "inference_result.json").write_text(
        json.dumps({"usage": {}, "had_error": False}), encoding="utf-8"
    )


class FindFailedCheckpointTests(unittest.TestCase):
    def test_returns_first_core_failure(self) -> None:
        with TemporaryDirectory() as temp_dir:
            problem_dir = Path(temp_dir) / "task_manager"
            problem_dir.mkdir()
            _make_checkpoint(
                problem_dir,
                "checkpoint_1",
                {"pass_counts": {"Core": 7}, "total_counts": {"Core": 7}},
            )
            _make_checkpoint(
                problem_dir,
                "checkpoint_2",
                {"pass_counts": {"Core": 3}, "total_counts": {"Core": 3}},
            )
            _make_checkpoint(
                problem_dir,
                "checkpoint_3",
                {
                    "pass_counts": {"Core": 1, "Functionality": 1, "Regression": 17},
                    "total_counts": {"Core": 3, "Functionality": 1, "Regression": 18},
                    "tests": {
                        "checkpoint_3-Core": {
                            "passed": ["test_a"],
                            "failed": ["test_b", "test_c"],
                        }
                    },
                },
            )
            result = repair.find_failed_checkpoint(problem_dir)
            self.assertIsNotNone(result)
            name, evaluation = result
            self.assertEqual(name, "checkpoint_3")
            self.assertEqual(evaluation["pass_counts"]["Core"], 1)

    def test_infra_failure_counts_as_failed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            problem_dir = Path(temp_dir) / "task_manager"
            problem_dir.mkdir()
            _make_checkpoint(
                problem_dir,
                "checkpoint_1",
                {
                    "pass_counts": {},
                    "total_counts": {},
                    "infrastructure_failure": True,
                },
            )
            result = repair.find_failed_checkpoint(problem_dir)
            self.assertIsNotNone(result)
            self.assertEqual(result[0], "checkpoint_1")

    def test_all_passing_returns_none(self) -> None:
        with TemporaryDirectory() as temp_dir:
            problem_dir = Path(temp_dir) / "task_manager"
            problem_dir.mkdir()
            _make_checkpoint(
                problem_dir,
                "checkpoint_1",
                {"pass_counts": {"Core": 7}, "total_counts": {"Core": 7}},
            )
            self.assertIsNone(repair.find_failed_checkpoint(problem_dir))


class BuildFailureEntryTests(unittest.TestCase):
    def test_entry_carries_model_harness_agent_metadata(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = root / "run_1"
            (run_dir / "metrics").mkdir(parents=True)
            (run_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "problem": "task_manager",
                        "agent": "opencode",
                        "agent_version": "1.14.33",
                        "model": "deepseek-v4-flash-free",
                        "model_settings": {"provider": "opencode_auth", "thinking": "none"},
                    }
                ),
                encoding="utf-8",
            )
            scb_problem_dir = root / "scb" / "task_manager"
            scb_problem_dir.mkdir(parents=True)
            _make_checkpoint(
                scb_problem_dir,
                "checkpoint_3",
                {
                    "pass_counts": {"Core": 1},
                    "total_counts": {"Core": 3},
                    "tests": {"checkpoint_3-Core": {"failed": ["test_x"]}},
                },
            )
            entry = repair.build_failure_entry(
                experiment_id="exp-1",
                arm="baseline",
                run_index=1,
                problem="task_manager",
                checkpoint="checkpoint_3",
                evaluation={
                    "pass_counts": {"Core": 1},
                    "total_counts": {"Core": 3},
                    "tests": {"checkpoint_3-Core": {"failed": ["test_x"]}},
                },
                run_dir=run_dir,
                scb_problem_dir=scb_problem_dir,
                root_cause="JWT TTL",
                fix="verify_iat off",
            )
            self.assertEqual(entry["model"], "deepseek-v4-flash-free")
            self.assertEqual(entry["agent"], "opencode")
            self.assertEqual(entry["harness"], "baseline")
            self.assertEqual(entry["provider"], "opencode_auth")
            self.assertEqual(entry["thinking"], "none")
            self.assertEqual(entry["failed_tests"], ["test_x"])
            self.assertEqual(entry["root_cause"], "JWT TTL")
            self.assertIn("snapshot_dir", entry["paths"])


class ReplaceSnapshotTests(unittest.TestCase):
    def test_backs_up_original_and_copies_fixed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = root / "run_1"
            run_dir.mkdir()
            scb_problem_dir = root / "scb" / "task_manager"
            snapshot_dir = scb_problem_dir / "checkpoint_3" / "snapshot"
            snapshot_dir.mkdir(parents=True)
            (snapshot_dir / "security.py").write_text("OLD", encoding="utf-8")
            fixed = root / "fixed"
            fixed.mkdir()
            (fixed / "security.py").write_text("NEW", encoding="utf-8")

            backup = repair.replace_snapshot(
                scb_problem_dir=scb_problem_dir,
                checkpoint="checkpoint_3",
                fixed_snapshot_dir=fixed,
                run_dir=run_dir,
            )
            self.assertEqual((backup / "security.py").read_text(), "OLD")
            self.assertEqual((snapshot_dir / "security.py").read_text(), "NEW")


class FailureEntryRecordingTests(unittest.TestCase):
    def test_repair_run_record_only_writes_failures_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            old_results = repair.RESULTS_DIR
            old_failures = failures.FAILURES_DIR
            repair.RESULTS_DIR = Path(temp_dir) / "results"
            failures.FAILURES_DIR = Path(temp_dir) / "failures"
            try:
                run_dir = repair.RESULTS_DIR / "exp-1" / "baseline" / "run_1"
                (run_dir / "metrics").mkdir(parents=True)
                (run_dir / "manifest.json").write_text(
                    json.dumps({"problem": "task_manager", "model": "m", "agent": "a"}),
                    encoding="utf-8",
                )
                scb_problem_dir = run_dir / "scb" / "task_manager"
                _make_checkpoint(
                    scb_problem_dir,
                    "checkpoint_3",
                    {
                        "pass_counts": {"Core": 1},
                        "total_counts": {"Core": 3},
                        "tests": {"checkpoint_3-Core": {"failed": ["test_b"]}},
                    },
                )
                result = repair.repair_run(
                    experiment_id="exp-1",
                    arm="baseline",
                    run_index=1,
                    root_cause="JWT TTL",
                )
                self.assertEqual(result["status"], "recorded")
                self.assertEqual(result["checkpoint"], "checkpoint_3")
                entries = failures.load_failures("task_manager")
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]["experiment_id"], "exp-1")
            finally:
                repair.RESULTS_DIR = old_results
                failures.FAILURES_DIR = old_failures


if __name__ == "__main__":
    unittest.main()
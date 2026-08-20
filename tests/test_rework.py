import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmark import failures, rework


def _rework(attempts_total: int = 2, fixed: bool = True) -> dict:
    return {
        "checkpoint": "checkpoint_1",
        "max_additional_attempts": 1,
        "attempts_total": attempts_total,
        "fixed": fixed,
        "attempts": [
            {
                "attempt": 1,
                "passed_policy": False,
                "pass_counts": {"Core": 1},
                "total_counts": {"Core": 3},
                "failed_tests": ["test_a"],
                "infrastructure_failure": False,
                "duration": 10.0,
            },
            {
                "attempt": 2,
                "passed_policy": bool(fixed),
                "pass_counts": {"Core": 3} if fixed else {"Core": 1},
                "total_counts": {"Core": 3},
                "failed_tests": [] if fixed else ["test_a", "test_b"],
                "infrastructure_failure": False,
                "duration": 5.0,
            },
        ],
    }


def _record(checkpoint_name: str = "checkpoint_1", rework: dict | None = None) -> dict:
    return {
        "run_id": "r1",
        "arm": "baseline",
        "problem": "task_manager",
        "checkpoint": 1,
        "checkpoint_name": checkpoint_name,
        "paths": {
            "checkpoint_dir": f"/tmp/x/{checkpoint_name}",
            "snapshot_dir": f"/tmp/x/{checkpoint_name}/snapshot",
        },
        **({"rework": rework} if rework else {}),
    }


class ReworkStatsTests(unittest.TestCase):
    def test_empty_records(self) -> None:
        self.assertEqual(
            rework.rework_stats([]),
            {
                "rework_attempts_total": 0,
                "rework_fixed": 0,
                "rework_unresolved": 0,
                "reworked_checkpoints": 0,
            },
        )

    def test_counts_fixed_and_unresolved(self) -> None:
        records = [
            _record("checkpoint_1", _rework(attempts_total=2, fixed=True)),
            _record("checkpoint_2", _rework(attempts_total=3, fixed=False)),
            _record("checkpoint_3"),
        ]
        self.assertEqual(
            rework.rework_stats(records),
            {
                "rework_attempts_total": 5,
                "rework_fixed": 1,
                "rework_unresolved": 1,
                "reworked_checkpoints": 2,
            },
        )


class ScoreTests(unittest.TestCase):
    def test_score_from_counts(self) -> None:
        self.assertEqual(rework.score_from_counts({"Core": 3}, {"Core": 3}), "3/3")
        self.assertEqual(rework.score_from_counts({"Core": 1}, {"Core": 3}), "1/3")
        self.assertEqual(rework.score_from_counts(None, None), "0/0")


class BuildEntryTests(unittest.TestCase):
    def test_entry_mirrors_repair_schema(self) -> None:
        manifest = {
            "experiment_id": "exp-1",
            "arm": "baseline",
            "harness": "baseline",
            "agent": "codex",
            "agent_version": "1.0",
            "model": "gpt-x",
            "model_settings": {"provider": "codex_auth", "thinking": "medium"},
            "problem": "task_manager",
            "extra": {"run_id": "r1", "run_index": 2},
        }
        entry = rework.build_rework_entry(
            cp_record=_record("checkpoint_1", _rework(fixed=False)),
            rework=_rework(attempts_total=2, fixed=False),
            manifest=manifest,
            run_dir=Path("/tmp/run_2"),
        )
        self.assertEqual(entry["experiment_id"], "exp-1")
        self.assertEqual(entry["checkpoint"], "checkpoint_1")
        self.assertEqual(entry["run_index"], 2)
        self.assertEqual(entry["source"], "rework")
        self.assertEqual(entry["attempts_total"], 2)
        self.assertFalse(entry["fixed"])
        self.assertEqual(entry["post_fix_score"], "1/3")
        self.assertEqual(entry["failed_tests"], ["test_a", "test_b"])
        self.assertEqual(len(entry["attempts"]), 2)
        self.assertEqual(entry["paths"]["run_dir"], "/tmp/run_2")

    def test_entry_fixed_flag_and_score(self) -> None:
        manifest = {
            "experiment_id": "exp-1",
            "arm": "baseline",
            "model": "gpt-x",
            "extra": {"run_index": 1},
        }
        entry = rework.build_rework_entry(
            cp_record=_record("checkpoint_1", _rework(fixed=True)),
            rework=_rework(fixed=True),
            manifest=manifest,
            run_dir=Path("/tmp/run_1"),
        )
        self.assertTrue(entry["fixed"])
        self.assertEqual(entry["post_fix_score"], "3/3")
        self.assertEqual(entry["failed_tests"], [])


class RecordEventsTests(unittest.TestCase):
    def test_record_rework_events_writes_entries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            old_dir = failures.FAILURES_DIR
            failures.FAILURES_DIR = Path(temp_dir)
            try:
                collected = {
                    "problem": "task_manager",
                    "checkpoints": [
                        _record("checkpoint_1", _rework(fixed=True)),
                        _record("checkpoint_2", _rework(fixed=False)),
                        _record("checkpoint_3"),
                    ],
                }
                manifest = {
                    "experiment_id": "exp-1",
                    "arm": "baseline",
                    "agent": "opencode",
                    "agent_version": "1.2",
                    "model": "deepseek-x",
                    "model_settings": {"provider": "opencode_auth", "thinking": "none"},
                    "extra": {"run_id": "r1", "run_index": 1},
                }
                count = rework.record_rework_events(
                    collected=collected,
                    manifest=manifest,
                    run_dir=Path("/tmp/run_1"),
                )
                self.assertEqual(count, 2)
                entries = failures.load_failures("task_manager")
                self.assertEqual(len(entries), 2)
                checkpoints = {e["checkpoint"] for e in entries}
                self.assertEqual(checkpoints, {"checkpoint_1", "checkpoint_2"})
                self.assertTrue(all(e["source"] == "rework" for e in entries))
                self.assertTrue(all(e["run_index"] == 1 for e in entries))
            finally:
                failures.FAILURES_DIR = old_dir

    def test_no_rework_no_entries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            old_dir = failures.FAILURES_DIR
            failures.FAILURES_DIR = Path(temp_dir)
            try:
                collected = {"problem": "task_manager", "checkpoints": [_record("checkpoint_1")]}
                count = rework.record_rework_events(
                    collected=collected,
                    manifest={"extra": {"run_index": 1}},
                    run_dir=Path("/tmp/run_1"),
                )
                self.assertEqual(count, 0)
                self.assertFalse((Path(temp_dir) / "task_manager.json").exists())
            finally:
                failures.FAILURES_DIR = old_dir


class LoadReworkJsonTests(unittest.TestCase):
    def test_load_missing_returns_none(self) -> None:
        with TemporaryDirectory() as td:
            self.assertIsNone(rework.load_rework_json(Path(td)))

    def test_load_roundtrip(self) -> None:
        with TemporaryDirectory() as td:
            data = {"checkpoint": "checkpoint_1", "attempts_total": 2, "fixed": True}
            (Path(td) / "rework.json").write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(rework.load_rework_json(Path(td)), data)


if __name__ == "__main__":
    unittest.main()
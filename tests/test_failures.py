import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import benchmark.failures as failures


class FailuresRecorderTests(unittest.TestCase):
    def test_record_and_load_roundtrip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            old_dir = failures.FAILURES_DIR
            failures.FAILURES_DIR = Path(temp_dir)
            try:
                entry = {
                    "date": "2026-08-19T00:00:00+00:00",
                    "experiment_id": "exp-1",
                    "arm": "baseline",
                    "agent": "opencode",
                    "model": "deepseek-v4-flash-free",
                    "problem": "task_manager",
                    "checkpoint": "checkpoint_3",
                    "root_cause": "JWT TTL",
                    "fix": "verify_iat off",
                }
                path = failures.record_failure("task_manager", entry)
                self.assertEqual(path, failures.failures_path("task_manager"))
                entries = failures.load_failures("task_manager")
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]["experiment_id"], "exp-1")
            finally:
                failures.FAILURES_DIR = old_dir

    def test_replaces_entry_with_same_experiment_and_checkpoint(self) -> None:
        with TemporaryDirectory() as temp_dir:
            old_dir = failures.FAILURES_DIR
            failures.FAILURES_DIR = Path(temp_dir)
            try:
                failures.record_failure(
                    "task_manager",
                    {"experiment_id": "exp-1", "checkpoint": "checkpoint_3", "note": "first"},
                )
                failures.record_failure(
                    "task_manager",
                    {"experiment_id": "exp-1", "checkpoint": "checkpoint_3", "note": "second"},
                )
                failures.record_failure(
                    "task_manager",
                    {"experiment_id": "exp-1", "checkpoint": "checkpoint_2", "note": "other"},
                )
                entries = failures.load_failures("task_manager")
                self.assertEqual(len(entries), 2)
                notes = {e["checkpoint"]: e["note"] for e in entries}
                self.assertEqual(notes, {"checkpoint_3": "second", "checkpoint_2": "other"})
            finally:
                failures.FAILURES_DIR = old_dir

    def test_files_are_per_problem(self) -> None:
        with TemporaryDirectory() as temp_dir:
            old_dir = failures.FAILURES_DIR
            failures.FAILURES_DIR = Path(temp_dir)
            try:
                failures.record_failure(
                    "task_manager", {"experiment_id": "exp-1", "checkpoint": "checkpoint_3"}
                )
                failures.record_failure(
                    "file_backup", {"experiment_id": "exp-1", "checkpoint": "checkpoint_1"}
                )
                self.assertEqual(len(failures.load_failures("task_manager")), 1)
                self.assertEqual(len(failures.load_failures("file_backup")), 1)
                self.assertTrue((Path(temp_dir) / "task_manager.json").exists())
                self.assertTrue((Path(temp_dir) / "file_backup.json").exists())
            finally:
                failures.FAILURES_DIR = old_dir

    def test_missing_file_returns_empty_list(self) -> None:
        with TemporaryDirectory() as temp_dir:
            old_dir = failures.FAILURES_DIR
            failures.FAILURES_DIR = Path(temp_dir)
            try:
                self.assertEqual(failures.load_failures("nope"), [])
            finally:
                failures.FAILURES_DIR = old_dir


if __name__ == "__main__":
    unittest.main()
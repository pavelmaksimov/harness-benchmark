import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import benchmark.analyze as analyze


SUMMARY_KEYS = (
    "checkpoints_passed",
    "checkpoints_total",
    "regression_failures",
    "total_input_tokens",
    "total_output_tokens",
    "reasoning_tokens",
    "normalized_cost",
    "elapsed_time",
    "loc_final",
    "loc_changed",
    "files_touched",
    "dependencies_added",
    "complexity",
)


class ReportTests(unittest.TestCase):
    def test_write_reports_uses_requested_problem_in_title(self) -> None:
        comparison = {
            "arms": ["baseline"],
            "n_baseline": 0,
            "summary": {key: {} for key in SUMMARY_KEYS},
            "per_checkpoint": [],
        }

        with TemporaryDirectory() as temp_dir:
            old_reports_dir = analyze.REPORTS_DIR
            analyze.REPORTS_DIR = Path(temp_dir)
            try:
                _, text_path = analyze.write_reports(
                    Path(temp_dir) / "experiment",
                    comparison,
                    problem="task_manager",
                )
                title = text_path.read_text(encoding="utf-8").splitlines()[0]
            finally:
                analyze.REPORTS_DIR = old_reports_dir

        self.assertEqual(title, "TASK_MANAGER — multi-harness")


if __name__ == "__main__":
    unittest.main()

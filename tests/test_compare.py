from __future__ import annotations

import json
from pathlib import Path

from benchmark.compare import compare_arms, load_experiment_runs


def _write_metrics(run_dir: Path, run_id: str) -> None:
    (run_dir / "metrics").mkdir(parents=True)
    (run_dir / "metrics" / "run.json").write_text(
        json.dumps({"run_id": run_id, "arm": "baseline", "checkpoints": []}),
        encoding="utf-8",
    )


def test_incomplete_state_is_reported_but_not_averaged(tmp_path: Path) -> None:
    experiment = tmp_path / "exp"
    complete = experiment / "baseline" / "run_1"
    incomplete = experiment / "baseline" / "run_2"
    failed_before_collection = experiment / "baseline" / "run_3"
    _write_metrics(complete, "complete")
    _write_metrics(incomplete, "incomplete")
    (complete / "state.json").write_text(
        json.dumps({"fully_completed": True, "run_index": 1, "phase": "completed"}),
        encoding="utf-8",
    )
    (incomplete / "state.json").write_text(
        json.dumps(
            {
                "fully_completed": False,
                "run_index": 2,
                "phase": "incomplete",
                "stopped_at_checkpoint": "checkpoint_2",
            }
        ),
        encoding="utf-8",
    )
    failed_before_collection.mkdir(parents=True)
    (failed_before_collection / "state.json").write_text(
        json.dumps(
            {
                "fully_completed": False,
                "run_index": 3,
                "phase": "failed",
                "interrupt_reason": "crashed",
            }
        ),
        encoding="utf-8",
    )

    comparison = compare_arms(load_experiment_runs(experiment))

    assert comparison["n_baseline"] == 1
    assert comparison["incomplete_runs"]["baseline"] == [
        {
            "run_index": 2,
            "phase": "incomplete",
            "fully_completed": False,
            "interrupt_reason": None,
            "stopped_at_checkpoint": "checkpoint_2",
            "agent": None,
            "provider": None,
            "model": None,
            "thinking": None,
            "rework_attempts": None,
        },
        {
            "run_index": 3,
            "phase": "failed",
            "fully_completed": False,
            "interrupt_reason": "crashed",
            "stopped_at_checkpoint": None,
            "agent": None,
            "provider": None,
            "model": None,
            "thinking": None,
            "rework_attempts": None,
        },
    ]

from __future__ import annotations

import json
from pathlib import Path

from benchmark.compare import compare_arms, format_comparison_report, load_experiment_runs


def _write_metrics(run_dir: Path, run_id: str) -> None:
    (run_dir / "metrics").mkdir(parents=True)
    (run_dir / "metrics" / "run.json").write_text(
        json.dumps({"run_id": run_id, "arm": "baseline", "checkpoints": []}),
        encoding="utf-8",
    )


def test_compare_exposes_stage_tokens_and_raw_core_details() -> None:
    run = {
        "run_id": "run-1",
        "arm": "baseline",
        "checkpoints": [
            {
                "checkpoint": 1,
                "correctness": {
                    "checkpoint_success": False,
                    "core_passed": 2,
                    "core_failed": 1,
                    "core_total": 3,
                    "regression_failed": 0,
                },
                "usage": {
                    "input_tokens": 101,
                    "output_tokens": 37,
                    "creation_input_tokens": 70,
                    "creation_output_tokens": 20,
                    "rework_input_tokens": 31,
                    "rework_output_tokens": 17,
                    "cache_read_tokens": 123,
                    "steps": 7,
                    "reasoning_tokens": 19,
                    "normalized_cost_usd": 0.12,
                    "elapsed_seconds": 4.5,
                },
                "change": {"lines_changed": 2, "files_touched": 1},
                "code": {
                    "total_source_loc": 10,
                    "module_count": 2,
                    "cyclomatic_complexity_total": 3,
                    "dependencies_added": 0,
                },
            }
        ],
    }

    comparison = compare_arms({"baseline": [run]})

    totals = comparison["raw_totals"]["baseline"][0]
    assert totals["checkpoints_failed"] == 1
    assert totals["core_passed"] == 2
    assert totals["core_failed"] == 1
    assert totals["core_total"] == 3
    assert totals["module_count"] == 2
    assert totals["creation_input_tokens"] == 70
    assert totals["creation_output_tokens"] == 20
    assert totals["rework_input_tokens"] == 31
    assert totals["rework_output_tokens"] == 17
    assert totals["repeated_attempts"] == 0
    assert totals["total_input_tokens"] == 101
    assert totals["total_output_tokens"] == 37
    assert totals["cache_read_tokens"] == 123
    assert totals["llm_requests"] == 7
    assert comparison["summary"]["core_failed"]["baseline"]["mean"] == 1
    assert comparison["summary"]["checkpoints_failed"]["baseline"]["mean"] == 1
    assert comparison["summary"]["total_input_tokens"]["baseline"]["mean"] == 101
    assert comparison["summary"]["total_output_tokens"]["baseline"]["mean"] == 37
    assert comparison["summary"]["cache_read_tokens"]["baseline"]["mean"] == 123
    assert comparison["summary"]["llm_requests"]["baseline"]["mean"] == 7
    assert comparison["summary"]["creation_input_tokens"]["baseline"]["mean"] == 70
    assert comparison["summary"]["rework_output_tokens"]["baseline"]["mean"] == 17
    assert comparison["summary"]["module_count"]["baseline"]["mean"] == 2

    checkpoint = comparison["per_checkpoint"][0]
    assert checkpoint["core_failed"] == 1
    assert checkpoint["creation_input_tokens"] == 70
    assert checkpoint["rework_output_tokens"] == 17
    assert checkpoint["input_tokens"] == 101
    assert checkpoint["output_tokens"] == 37


def test_compare_separates_transient_dimensions() -> None:
    run = {
        "run_id": "run-1",
        "arm": "baseline",
        "checkpoints": [
            {
                "checkpoint": 1,
                "correctness": {
                    "checkpoint_success": True,
                    "core_passed": 1,
                    "core_failed": 0,
                    "core_total": 1,
                },
                "usage": {
                    "input_tokens": 101,
                    "output_tokens": 33,
                    "creation_input_tokens": 70,
                    "creation_output_tokens": 20,
                    "rework_input_tokens": 20,
                    "rework_output_tokens": 8,
                    "transient_input_tokens": 11,
                    "transient_output_tokens": 5,
                    "normalized_cost_usd": 0.15,
                    "elapsed_seconds": 7.0,
                },
                "change": {"lines_changed": 0, "files_touched": 0},
                "code": {"dependencies_added": 0},
                "rework": {
                    "attempts_total": 3,
                    "semantic_attempts_total": 2,
                    "transient_retries_total": 1,
                    "provider_truncation_attempts": 1,
                    "provider_truncation_recovered": True,
                    "provider_truncation_unresolved": False,
                    "fixed": True,
                    "attempts": [],
                },
            }
        ],
    }

    comparison = compare_arms({"baseline": [run]})
    totals = comparison["raw_totals"]["baseline"][0]
    text = format_comparison_report(comparison)

    assert totals["transient_retries"] == 1
    assert totals["provider_truncations"] == 1
    assert totals["transient_recoveries"] == 1
    assert totals["provider_truncation_unresolved"] == 0
    assert "Transient retries" in text
    assert "Provider truncations" in text
    assert "Transient input tokens" in text


def test_comparison_report_renders_rework_attempt_metrics() -> None:
    run = {
        "run_id": "run-1",
        "arm": "baseline",
        "checkpoints": [
            {
                "checkpoint": 1,
                "correctness": {
                    "checkpoint_success": False,
                    "core_passed": 2,
                    "core_failed": 1,
                    "core_total": 3,
                    "regression_failed": 0,
                },
                "usage": {
                    "input_tokens": 101,
                    "output_tokens": 37,
                    "reasoning_tokens": 19,
                    "normalized_cost_usd": 0.12,
                    "elapsed_seconds": 4.5,
                },
                "change": {"lines_changed": 2, "files_touched": 1},
                "code": {
                    "total_source_loc": 10,
                    "cyclomatic_complexity_total": 3,
                    "dependencies_added": 0,
                },
                "rework": {
                    "attempts_total": 1,
                    "fixed": False,
                    "attempts": [
                        {
                            "attempt": 1,
                            "core": {"passed": 2, "failed": 1, "total": 3},
                            "usage": {
                                "input_tokens": 11,
                                "output_tokens": 7,
                                "elapsed_seconds": 2.0,
                                "reported_cost_usd": 0.01,
                            },
                            "failed_tests": ["test_x"],
                        }
                    ],
                },
            }
        ],
    }

    text = format_comparison_report(compare_arms({"baseline": [run]}))

    assert "Creation input tokens" in text
    assert "Rework output tokens" in text
    assert "Failed checkpoints" in text
    assert "Repeated attempts" in text
    assert "Rework attempts (raw):" in text
    assert "2/1/3" in text
    assert "test_x" not in text


def test_compare_derives_rework_tokens_from_all_minus_creation() -> None:
    run = {
        "run_id": "run-1",
        "arm": "baseline",
        "checkpoints": [
            {
                "checkpoint": 1,
                "correctness": {"checkpoint_success": True},
                "usage": {
                    "input_tokens": 101,
                    "output_tokens": 37,
                    "creation_input_tokens": 70,
                    "creation_output_tokens": 20,
                    "normalized_cost_usd": 0.0,
                    "elapsed_seconds": 0.0,
                },
                "change": {"lines_changed": 0, "files_touched": 0},
                "code": {"dependencies_added": 0},
                "rework": {"attempts_total": 2, "fixed": True},
            }
        ],
    }

    totals = compare_arms({"baseline": [run]})["raw_totals"]["baseline"][0]

    assert totals["rework_input_tokens"] == 31
    assert totals["rework_output_tokens"] == 17
    assert totals["checkpoints_failed"] == 1
    assert totals["repeated_attempts"] == 1


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
            "transient_retries": None,
            "feedback_strategy": None,
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
            "transient_retries": None,
            "feedback_strategy": None,
        },
    ]

from __future__ import annotations

import json
from pathlib import Path

from benchmark.collect import (
    _cumulative_metrics,
    _stage_token_usage,
    collect_checkpoint_record,
)


def test_cumulative_metrics_include_core_groups_and_usage() -> None:
    records = [
        {
            "checkpoint": 1,
            "usage": {
                "input_tokens": 101,
                "output_tokens": 37,
                "creation_input_tokens": 70,
                "creation_output_tokens": 20,
                "rework_input_tokens": 31,
                "rework_output_tokens": 17,
                "cache_read_tokens": 11,
                "cache_write_tokens": 3,
                "reasoning_tokens": 19,
                "normalized_cost_usd": 0.1,
                "reported_cost_usd": 0.12,
                "elapsed_seconds": 4.5,
            },
            "correctness": {
                "checkpoint_success": False,
                "tests_passed": 3,
                "tests_failed": 1,
                "tests_total": 4,
                "core_passed": 2,
                "core_failed": 1,
                "core_total": 3,
                "functionality_passed": 1,
                "functionality_failed": 0,
                "functionality_total": 1,
                "error_passed": 0,
                "error_failed": 0,
                "error_total": 0,
                "regression_passed": 0,
                "regression_failed": 0,
                "regression_total": 0,
            },
            "change": {"lines_changed": 2},
        }
    ]

    cumulative = _cumulative_metrics(records)

    through_cp1 = cumulative["through_cp1"]
    assert through_cp1["input_tokens"] == 101
    assert through_cp1["output_tokens"] == 37
    assert through_cp1["creation_input_tokens"] == 70
    assert through_cp1["creation_output_tokens"] == 20
    assert through_cp1["rework_input_tokens"] == 31
    assert through_cp1["rework_output_tokens"] == 17
    assert through_cp1["cache_read_tokens"] == 11
    assert through_cp1["cache_write_tokens"] == 3
    assert through_cp1["core_passed"] == 2
    assert through_cp1["core_failed"] == 1
    assert through_cp1["core_total"] == 3
    assert through_cp1["tests_failed"] == 1
    assert through_cp1["checkpoints_failed"] == 1
    assert through_cp1["repeated_attempts"] == 0
    assert through_cp1["cumulative_reported_cost_usd"] == 0.12


def test_cumulative_metrics_keep_missing_values_null() -> None:
    cumulative = _cumulative_metrics(
        [{"checkpoint": 1, "usage": {}, "correctness": {}, "change": {}}]
    )

    through_cp1 = cumulative["through_cp1"]
    assert through_cp1["input_tokens"] is None
    assert through_cp1["output_tokens"] is None
    assert through_cp1["cache_read_tokens"] is None
    assert through_cp1["core_failed"] is None
    assert through_cp1["cumulative_reported_cost_usd"] is None


def test_stage_token_usage_separates_creation_and_rework() -> None:
    rework = {
        "attempts": [
            {
                "attempt": 1,
                "usage": {"input_tokens": 70, "output_tokens": 20},
            },
            {
                "attempt": 2,
                "usage": {"input_tokens": 31, "output_tokens": 17},
            },
            {
                "attempt": 3,
                "usage": {"input_tokens": 9, "output_tokens": 4},
            },
        ]
    }

    assert _stage_token_usage(rework, {"input_tokens": 101, "output_tokens": 37}) == {
        "creation_input_tokens": 70,
        "creation_output_tokens": 20,
        "rework_input_tokens": 40,
        "rework_output_tokens": 21,
        "transient_input_tokens": None,
        "transient_output_tokens": None,
    }


def test_stage_token_usage_uses_checkpoint_usage_without_rework() -> None:
    assert _stage_token_usage(
        None,
        {"input_tokens": 101, "output_tokens": 37},
    ) == {
        "creation_input_tokens": 101,
        "creation_output_tokens": 37,
        "rework_input_tokens": 0,
        "rework_output_tokens": 0,
        "transient_input_tokens": 0,
        "transient_output_tokens": 0,
    }


def test_stage_token_usage_derives_rework_from_all_usage() -> None:
    rework = {"attempts": [{"usage": {"input_tokens": 70, "output_tokens": 20}}]}

    assert _stage_token_usage(rework, {"input_tokens": 101, "output_tokens": 37}) == {
        "creation_input_tokens": 70,
        "creation_output_tokens": 20,
        "rework_input_tokens": 31,
        "rework_output_tokens": 17,
        "transient_input_tokens": None,
        "transient_output_tokens": None,
    }


def test_stage_token_usage_separates_transient_retry() -> None:
    rework = {
        "attempts": [
            {
                "attempt": 1,
                "stage": "creation",
                "usage": {"input_tokens": 70, "output_tokens": 20},
            },
            {
                "attempt": 2,
                "stage": "transient_retry",
                "usage": {"input_tokens": 11, "output_tokens": 5},
            },
            {
                "attempt": 3,
                "stage": "rework",
                "usage": {"input_tokens": 20, "output_tokens": 8},
            },
        ]
    }

    assert _stage_token_usage(
        rework,
        {"input_tokens": 101, "output_tokens": 33},
    ) == {
        "creation_input_tokens": 70,
        "creation_output_tokens": 20,
        "rework_input_tokens": 20,
        "rework_output_tokens": 8,
        "transient_input_tokens": 11,
        "transient_output_tokens": 5,
    }


def test_cumulative_metrics_report_transient_retry_dimensions() -> None:
    cumulative = _cumulative_metrics(
        [
            {
                "checkpoint": 1,
                "usage": {
                    "input_tokens": 101,
                    "output_tokens": 33,
                    "creation_input_tokens": 70,
                    "creation_output_tokens": 20,
                    "rework_input_tokens": 20,
                    "rework_output_tokens": 8,
                    "transient_input_tokens": 11,
                    "transient_output_tokens": 5,
                },
                "correctness": {
                    "checkpoint_success": True,
                    "core_passed": 1,
                    "core_failed": 0,
                    "core_total": 1,
                },
                "change": {},
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
        ]
    )

    through_cp1 = cumulative["through_cp1"]
    assert through_cp1["transient_retries"] == 1
    assert through_cp1["transient_input_tokens"] == 11
    assert through_cp1["transient_output_tokens"] == 5
    assert through_cp1["provider_truncations"] == 1
    assert through_cp1["transient_recoveries"] == 1
    assert through_cp1["provider_truncation_unresolved"] == 0
    assert cumulative["semantic_rework_attempts"] == 1


def test_collection_sums_per_attempt_usage_for_transient_retry(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint_1"
    (checkpoint / "snapshot").mkdir(parents=True)
    (checkpoint / "inference_result.json").write_text(
        json.dumps(
            {
                "elapsed": 2.0,
                "usage": {
                    "input": 20,
                    "output": 8,
                    "steps": 1,
                    "cost": 0.03,
                },
            }
        ),
        encoding="utf-8",
    )
    (checkpoint / "evaluation.json").write_text(
        json.dumps(
            {
                "pass_counts": {"Core": 1},
                "total_counts": {"Core": 1},
                "tests": {"checkpoint_1-Core": {"failed": []}},
            }
        ),
        encoding="utf-8",
    )
    (checkpoint / "rework.json").write_text(
        json.dumps(
            {
                "attempts_total": 3,
                "attempts": [
                    {
                        "attempt": 1,
                        "stage": "creation",
                        "usage": {
                            "input_tokens": 70,
                            "output_tokens": 20,
                            "steps": 2,
                            "elapsed_seconds": 4.0,
                            "reported_cost_usd": 0.10,
                        },
                    },
                    {
                        "attempt": 2,
                        "stage": "transient_retry",
                        "usage": {
                            "input_tokens": 11,
                            "output_tokens": 5,
                            "steps": 1,
                            "elapsed_seconds": 1.0,
                            "reported_cost_usd": 0.02,
                        },
                    },
                    {
                        "attempt": 3,
                        "stage": "rework",
                        "usage": {
                            "input_tokens": 20,
                            "output_tokens": 8,
                            "steps": 1,
                            "elapsed_seconds": 2.0,
                            "reported_cost_usd": 0.03,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    record, _ = collect_checkpoint_record(
        run_id="run-1",
        arm="baseline",
        problem="file_backup",
        checkpoint_dir=checkpoint,
        environment={"model": "model-x"},
        pricing={},
        prev_deps=None,
    )

    assert record["usage"]["input_tokens"] == 101
    assert record["usage"]["output_tokens"] == 33
    assert record["usage"]["elapsed_seconds"] == 7.0
    assert record["usage"]["reported_cost_usd"] == 0.15
    assert record["usage"]["transient_input_tokens"] == 11
    assert record["usage"]["rework_output_tokens"] == 8


def test_collection_falls_back_to_final_diagnostics_for_old_rework(
    tmp_path: Path,
) -> None:
    checkpoint = tmp_path / "checkpoint_2"
    (checkpoint / "snapshot").mkdir(parents=True)
    (checkpoint / "inference_result.json").write_text(
        json.dumps(
            {
                "had_error": False,
                "usage": {"net_tokens": {"input": 120, "output": 320}},
            }
        ),
        encoding="utf-8",
    )
    (checkpoint / "messages.jsonl").write_text(
        '{"type":"reasoning"}\n{"type":"step_finish","reason":"unknown"}\n',
        encoding="utf-8",
    )
    (checkpoint / "evaluation.json").write_text(
        json.dumps(
            {
                "pass_counts": {"Core": 0},
                "total_counts": {"Core": 1},
                "tests": {"checkpoint_2-Core": {"failed": ["test_core"]}},
            }
        ),
        encoding="utf-8",
    )
    (checkpoint / "rework.json").write_text(
        json.dumps(
            {
                "attempts_total": 2,
                "fixed": False,
                "attempts": [{"attempt": 1}, {"attempt": 2}],
            }
        ),
        encoding="utf-8",
    )

    record, _ = collect_checkpoint_record(
        run_id="run-1",
        arm="baseline",
        problem="file_backup",
        checkpoint_dir=checkpoint,
        environment={"model": "model-x"},
        pricing={},
        prev_deps=None,
    )

    assert record["attempt_diagnostics"]["provider_truncations"] == 1
    assert record["attempt_diagnostics"]["provider_truncation_unresolved"] is True

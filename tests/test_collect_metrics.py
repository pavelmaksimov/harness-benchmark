from __future__ import annotations

from benchmark.collect import _cumulative_metrics, _stage_token_usage


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
    }


def test_stage_token_usage_derives_rework_from_all_usage() -> None:
    rework = {"attempts": [{"usage": {"input_tokens": 70, "output_tokens": 20}}]}

    assert _stage_token_usage(rework, {"input_tokens": 101, "output_tokens": 37}) == {
        "creation_input_tokens": 70,
        "creation_output_tokens": 20,
        "rework_input_tokens": 31,
        "rework_output_tokens": 17,
    }

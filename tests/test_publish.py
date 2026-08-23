from __future__ import annotations

from pathlib import Path

from benchmark.publish import (
    METRIC_KEYS,
    _latest_cells,
    build_publish_payload,
    format_leaderboard,
    format_short_report,
)


def test_latest_cells_keeps_same_model_for_different_adapters() -> None:
    payloads = [
        {
            "date": "2026-08-21T10:00:00Z",
            "experiment_id": "codex-exp",
            "problem": "file_backup",
            "agent": "codex",
            "provider": "codex_auth",
            "model": "same-model",
            "arms": {"baseline": {}},
            "n_baseline": 3,
        },
        {
            "date": "2026-08-21T09:00:00Z",
            "experiment_id": "opencode-exp",
            "problem": "file_backup",
            "agent": "opencode",
            "provider": "opencode_auth",
            "model": "same-model",
            "arms": {"baseline": {}},
            "n_baseline": 3,
        },
    ]

    cells = _latest_cells(payloads)

    assert {(cell["agent"], cell["provider"]) for cell in cells} == {
        ("codex", "codex_auth"),
        ("opencode", "opencode_auth"),
    }


def test_leaderboard_shows_stage_tokens_without_diagnostic_columns() -> None:
    payload = {
        "date": "2026-08-21T10:00:00Z",
        "experiment_id": "exp-1",
        "problem": "file_backup",
        "agent": "opencode",
        "provider": "opencode_auth",
        "model": "model-x",
        "arms": {
            "baseline": {
                "checkpoints_passed": 1,
                "checkpoints_total": 1,
                "checkpoints_failed": 0,
                "repeated_attempts": 2,
                "regression_failures": 0,
                "creation_input_tokens": 1000,
                "creation_output_tokens": 400,
                "rework_input_tokens": 234,
                "rework_output_tokens": 167,
                "total_input_tokens": 1234,
                "total_output_tokens": 567,
                "normalized_cost": 0.0,
                "elapsed_time": 60.0,
                "loc_final": 10,
                "loc_changed": 3,
                "dependencies_added": 0,
                "complexity": 2,
            }
        },
        "n_baseline": 1,
    }

    text = format_leaderboard([payload])

    assert (
        "| Agent | Model | Harness | N | CP | Failed CP | Repeated | Reg | Create in | "
        "Create out | Rework in | Rework out | Cost | Time | LOC | ΔLOC | Deps | Cx |"
    ) in text
    assert "| Experiment | Date | Problem | Agent | Model | N | Report |" in text
    assert "| Problem | Agent | Harness | N | CP | Failed CP | Repeated | Reg | Create in | " in text
    assert "|---------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-----:|-----:|----:|-----:|-----:|---:|" in text
    assert "## Metric leaderboards" in text
    assert "### CP passed/total" in text
    assert "Higher is better." in text
    assert "1,000" in text
    assert "400" in text
    assert "234" in text
    assert "167" in text
    assert "| 2 |" in text
    assert "All in" not in text
    assert "All out" not in text
    assert "Transient in" not in text
    assert "Transient out" not in text
    assert "Trunc" not in text
    assert "Tr. retry" not in text
    assert "Recovery" not in text
    assert "Unresolved" not in text
    assert "Core fail" not in text
    assert "| Agent | Provider |" not in text
    assert "| Problem | Agent | Provider |" not in text


def test_short_report_shows_stage_tokens_without_core_failures() -> None:
    payload = {
        "experiment_id": "exp-1",
        "problem": "file_backup",
        "model": "model-x",
        "agent": "opencode",
        "provider": "opencode_auth",
        "arms": {
            "baseline": {
                "checkpoints_passed": 1,
                "checkpoints_total": 1,
                "checkpoints_failed": 0.0,
                "repeated_attempts": 2.0,
                "regression_failures": 0.0,
                "creation_input_tokens": 1234.0,
                "creation_output_tokens": 567.0,
                "rework_input_tokens": 12.0,
                "rework_output_tokens": 6.0,
                "total_input_tokens": 1252.0,
                "total_output_tokens": 573.0,
            }
        },
        "n_baseline": 1,
    }

    text = format_short_report(payload)

    assert "| Failed checkpoints | 0 |" in text
    assert "| Repeated attempts | 2 |" in text
    assert "| Creation input tokens | 1,234 |" in text
    assert "| Creation output tokens | 567 |" in text
    assert "| Rework input tokens | 12 |" in text
    assert "| Rework output tokens | 6 |" in text
    assert "Core failed" not in text


def test_short_report_shows_transient_dimensions() -> None:
    payload = {
        "experiment_id": "exp-transient",
        "problem": "file_backup",
        "model": "model-x",
        "agent": "opencode",
        "provider": "opencode_auth",
        "arms": {
            "baseline": {
                "checkpoints_passed": 1,
                "checkpoints_total": 1,
                "transient_retries": 1,
                "provider_truncations": 1,
                "transient_recoveries": 1,
                "provider_truncation_unresolved": 0,
            }
        },
        "n_baseline": 1,
    }

    text = format_short_report(payload)

    assert "| Transient retries | 1 |" in text
    assert "| Provider truncations | 1 |" in text
    assert "| Transient recoveries | 1 |" in text


def test_published_payload_keeps_rework_attempt_details() -> None:
    summary = {
        key: {"baseline": {"mean": 0.0}}
        for key in METRIC_KEYS
    }
    comparison = {
        "arms": ["baseline"],
        "n_baseline": 1,
        "summary": summary,
        "per_checkpoint": [
            {
                "cp": 1,
                "arm": "baseline",
                "rework": {
                    "attempts": [
                        {
                            "attempt": 1,
                            "core": {"passed": 2, "failed": 1, "total": 3},
                            "usage": {"input_tokens": 10, "output_tokens": 5},
                            "failed_tests": ["test_x"],
                        }
                    ]
                },
            }
        ],
    }

    payload = build_publish_payload(Path("/tmp/exp"), comparison)

    assert payload["arms"]["baseline"]["creation_input_tokens"] == 0.0
    assert payload["arms"]["baseline"]["rework_output_tokens"] == 0.0
    assert payload["arms"]["baseline"]["total_input_tokens"] == 0.0
    assert payload["rework_details"][0]["rework"]["attempts"][0]["failed_tests"] == ["test_x"]

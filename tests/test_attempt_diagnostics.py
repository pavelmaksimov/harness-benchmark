from __future__ import annotations

import json
from pathlib import Path

from benchmark.attempt_diagnostics import diagnose_attempt


def _write_inference(checkpoint: Path, *, output: int = 320, **extra) -> None:
    usage = {"net_tokens": {"input": 120, "output": output}}
    (checkpoint / "inference_result.json").write_text(
        json.dumps({"usage": usage, **extra}),
        encoding="utf-8",
    )


def _write_messages(checkpoint: Path, events: list[dict], *, nested: bool = False) -> None:
    path = checkpoint / "agent" / "messages.jsonl" if nested else checkpoint / "messages.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )


def test_high_confidence_truncation_reads_root_messages(tmp_path: Path) -> None:
    _write_inference(tmp_path)
    _write_messages(
        tmp_path,
        [
            {"type": "reasoning", "part": {"text": "starting"}},
            {"type": "step_finish", "part": {"reason": "unknown"}},
        ],
    )

    result = diagnose_attempt(tmp_path)

    assert result["failure_class"] == "provider_truncation"
    assert result["confidence"] == "high"
    assert result["detected"] is True
    assert result["message_path"] == str(tmp_path / "messages.jsonl")
    assert result["signals"]["no_explicit_error_or_limit"] is True
    assert result["output_threshold"] == 500


def test_high_confidence_truncation_reads_codex_agent_messages(tmp_path: Path) -> None:
    _write_inference(tmp_path)
    _write_messages(
        tmp_path,
        [
            {"type": "reasoning"},
            {"type": "step-finish", "reason": "unknown"},
        ],
        nested=True,
    )

    result = diagnose_attempt(tmp_path)

    assert result["detected"] is True
    assert result["message_path"] == str(tmp_path / "agent" / "messages.jsonl")


def test_truncation_after_tool_step_keeps_prior_reasoning_signal(tmp_path: Path) -> None:
    _write_inference(tmp_path)
    _write_messages(
        tmp_path,
        [
            {"type": "step_start"},
            {"type": "reasoning"},
            {"type": "tool_use"},
            {"type": "step_finish", "part": {"reason": "tool-calls"}},
            {"type": "step_start"},
            {"type": "step_finish", "part": {"reason": "unknown"}},
        ],
    )

    result = diagnose_attempt(tmp_path)

    assert result["detected"] is True
    assert result["signals"]["preceding_reasoning"] is True


def test_short_normal_completion_is_not_truncation(tmp_path: Path) -> None:
    _write_inference(tmp_path, output=120)
    _write_messages(
        tmp_path,
        [
            {"type": "reasoning"},
            {"type": "step_finish", "part": {"reason": "stop"}},
        ],
    )

    result = diagnose_attempt(tmp_path)

    assert result["failure_class"] == "none"
    assert result["detected"] is False
    assert result["finish_reason"] == "stop"


def test_explicit_length_limit_is_not_truncation(tmp_path: Path) -> None:
    _write_inference(tmp_path, output=320)
    _write_messages(
        tmp_path,
        [
            {"type": "reasoning"},
            {"type": "step_finish", "part": {"reason": "length"}},
        ],
    )

    result = diagnose_attempt(tmp_path)

    assert result["detected"] is False
    assert result["signals"]["no_explicit_limit"] is False


def test_malformed_or_missing_log_is_inconclusive(tmp_path: Path) -> None:
    _write_inference(tmp_path, output=0)
    (tmp_path / "messages.jsonl").write_text("{not-json}\n", encoding="utf-8")

    malformed = diagnose_attempt(tmp_path)
    missing = diagnose_attempt(tmp_path / "missing")

    assert malformed["detected"] is False
    assert malformed["parse_errors"] == 1
    assert missing["detected"] is False
    assert missing["message_path"] is None


def test_repeated_truncation_events_are_each_observable(tmp_path: Path) -> None:
    first = tmp_path / "checkpoint_1"
    second = tmp_path / "checkpoint_2"
    first.mkdir()
    second.mkdir()
    for checkpoint in (first, second):
        _write_inference(checkpoint)
        _write_messages(
            checkpoint,
            [{"type": "reasoning"}, {"type": "step_finish", "reason": "unknown"}],
        )

    results = [diagnose_attempt(checkpoint) for checkpoint in (first, second)]

    assert [result["failure_class"] for result in results] == [
        "provider_truncation",
        "provider_truncation",
    ]

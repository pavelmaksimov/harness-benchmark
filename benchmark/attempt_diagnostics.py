"""Adapter-neutral diagnostics for one agent checkpoint attempt.

The SCB agent artifacts are intentionally treated as evidence, not as a new
failure policy.  In particular, a provider truncation is recorded separately
from evaluator infrastructure failures and from a solution assertion failure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_TRUNCATION_OUTPUT_THRESHOLD = 500
MAX_MESSAGE_BYTES = 256 * 1024


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _token_field(usage: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = usage.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    for container_name in ("net_tokens", "current_tokens"):
        tokens = usage.get(container_name)
        if not isinstance(tokens, dict):
            continue
        aliases = {
            "input_tokens": "input",
            "output_tokens": "output",
            "cache_read_tokens": "cache_read",
            "cache_write_tokens": "cache_write",
            "reasoning_tokens": "reasoning",
        }
        for key in keys:
            value = tokens.get(key)
            if value is None:
                value = tokens.get(aliases.get(key, ""))
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
    return None


def _event_type(event: dict[str, Any]) -> str | None:
    raw = event.get("type") or event.get("event") or event.get("kind")
    if isinstance(raw, dict):
        raw = raw.get("type") or raw.get("name")
    if raw is None:
        return None
    normalized = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "stepfinish": "step_finish",
        "step_finished": "step_finish",
        "reason": "reasoning",
        "ratelimit": "rate_limit",
        "rate_limited": "rate_limit",
    }
    return aliases.get(normalized, normalized)


def _event_value(event: dict[str, Any], key: str) -> Any:
    for container in (
        event,
        event.get("part"),
        event.get("data"),
        event.get("payload"),
    ):
        if isinstance(container, dict) and key in container:
            return container[key]
    return None


def _read_message_events(checkpoint_dir: Path) -> tuple[Path | None, list[dict[str, Any]], int]:
    candidates = (
        checkpoint_dir / "agent" / "messages.jsonl",
        checkpoint_dir / "messages.jsonl",
    )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            return path, [], 1
        raw = raw[-MAX_MESSAGE_BYTES:]
        events: list[dict[str, Any]] = []
        parse_errors = 0
        for line in raw.splitlines():
            try:
                value = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                parse_errors += 1
                continue
            if isinstance(value, dict):
                events.append(value)
        return path, events, parse_errors
    return None, [], 0


def diagnose_attempt(
    checkpoint_dir: Path,
    *,
    inference: dict[str, Any] | None = None,
    evaluation: dict[str, Any] | None = None,
    output_threshold: int = DEFAULT_TRUNCATION_OUTPUT_THRESHOLD,
) -> dict[str, Any]:
    """Classify observable terminal signals for one checkpoint attempt.

    ``provider_truncation`` is deliberately high precision: all four primary
    signals must be present.  Missing artifacts produce an inconclusive result,
    never a positive truncation diagnosis.
    """

    checkpoint_dir = Path(checkpoint_dir)
    inference = inference if inference is not None else (
        _read_json(checkpoint_dir / "inference_result.json") or {}
    )
    evaluation = evaluation if evaluation is not None else (
        _read_json(checkpoint_dir / "evaluation.json") or {}
    )
    usage = inference.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}

    message_path, events, parse_errors = _read_message_events(checkpoint_dir)
    meaningful = [
        (_event_type(event), event)
        for event in events
        if _event_type(event) is not None
    ]
    last_type: str | None = None
    last_event: dict[str, Any] | None = None
    if meaningful:
        last_type, last_event = meaningful[-1]
    previous_type = meaningful[-2][0] if len(meaningful) >= 2 else None
    finish_reason = (
        str(_event_value(last_event, "reason")).strip().lower()
        if last_event is not None and _event_value(last_event, "reason") is not None
        else None
    )
    explicit_limit = bool(
        inference.get("limit_reached")
        or inference.get("max_tokens_reached")
        or (
            last_event is not None
            and (
                _event_value(last_event, "limit_reached")
                or _event_value(last_event, "max_tokens_reached")
            )
        )
        or finish_reason
        in {
            "length",
            "max_tokens",
            "max_output_tokens",
            "content_filter",
            "timeout",
            "cancelled",
            "canceled",
        }
    )
    output_tokens = _token_field(usage, "output_tokens", "output")
    steps = usage.get("steps")
    try:
        steps = int(steps) if steps is not None else None
    except (TypeError, ValueError):
        steps = None

    unknown_finish = last_type == "step_finish" and finish_reason == "unknown"
    preceding_reasoning = previous_type == "reasoning" or any(
        event_type == "reasoning" for event_type, _ in meaningful[:-1]
    )
    output_below_threshold = (
        output_tokens is not None and output_tokens < output_threshold
    )
    explicit_error = bool(
        inference.get("had_error")
        or inference.get("error")
        or inference.get("error_message")
        or inference.get("exception")
        or finish_reason in {"error", "rate_limit"}
    ) or any(event_type in {"error", "rate_limit"} for event_type, _ in meaningful)
    no_infrastructure_failure = not bool(evaluation.get("infrastructure_failure"))
    detected = bool(
        unknown_finish
        and preceding_reasoning
        and output_below_threshold
        and not explicit_error
        and not explicit_limit
        and no_infrastructure_failure
    )

    if evaluation.get("infrastructure_failure"):
        failure_class = "infrastructure_failure"
        confidence = "high"
    elif inference.get("had_error"):
        failure_class = "agent_error"
        confidence = "high"
    elif detected:
        failure_class = "provider_truncation"
        confidence = "high"
    else:
        failure_class = "none"
        confidence = "none"

    return {
        "failure_class": failure_class,
        "detected": detected,
        "confidence": confidence,
        "message_path": str(message_path) if message_path is not None else None,
        "message_count": len(events),
        "message_types": [event_type for event_type, _ in meaningful],
        "parse_errors": parse_errors,
        "finish_reason": finish_reason,
        "output_tokens": output_tokens,
        "output_threshold": output_threshold,
        "steps": steps,
        "signals": {
            "unknown_finish": unknown_finish,
            "preceding_reasoning": preceding_reasoning,
            "output_below_threshold": output_below_threshold,
            "no_explicit_error": not explicit_error,
            "no_explicit_limit": not explicit_limit,
            "no_explicit_error_or_limit": not (explicit_error or explicit_limit),
            "no_infrastructure_failure": no_infrastructure_failure,
        },
    }

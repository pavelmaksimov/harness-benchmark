"""Rework loop records: turn ``<checkpoint>/rework.json`` artifacts into
per-problem failure entries (failures/<problem>.json).

``benchmark/rework_hook.py`` re-invokes the agent when a checkpoint's tests
fail and writes rework.json with per-attempt outcomes. This module records
those events as failure entries (same file the manual repair mode writes to,
keyed by experiment_id + checkpoint + run_index) and aggregates run-level
rework statistics for the cumulative metrics.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchmark.failures import record_failure


def _sum_counts(counts: dict[str, Any] | None) -> int:
    return sum(int(v) for v in (counts or {}).values())


def score_from_counts(
    pass_counts: dict[str, Any] | None, total_counts: dict[str, Any] | None
) -> str:
    passed = _sum_counts(pass_counts)
    total = _sum_counts(total_counts)
    return f"{passed}/{total}" if total else "0/0"


def _semantic_attempt_count(rework: dict[str, Any]) -> int:
    attempts = [
        attempt
        for attempt in (rework.get("attempts") or [])
        if isinstance(attempt, dict)
    ]
    if rework.get("semantic_attempts_total") is not None:
        return int(rework.get("semantic_attempts_total") or 0)
    if any(isinstance(attempt.get("stage"), str) for attempt in attempts):
        return int(
            sum(1 for attempt in attempts if attempt.get("stage") != "transient_retry")
        )
    return int(rework.get("attempts_total") or len(attempts))


def _transient_attempt_count(rework: dict[str, Any]) -> int:
    if rework.get("transient_retries_total") is not None:
        return int(rework.get("transient_retries_total") or 0)
    return sum(
        1
        for attempt in (rework.get("attempts") or [])
        if isinstance(attempt, dict) and attempt.get("stage") == "transient_retry"
    )


def _provider_truncation_count(
    checkpoint: dict[str, Any],
    rework: dict[str, Any],
) -> int:
    recorded = rework.get("provider_truncation_attempts")
    if recorded is not None:
        return int(recorded or 0)
    return int(
        (checkpoint.get("attempt_diagnostics") or {}).get("provider_truncations")
        or 0
    )


def _truncation_recovered(
    checkpoint: dict[str, Any],
    rework: dict[str, Any],
) -> bool:
    recorded = rework.get("provider_truncation_recovered")
    if recorded is not None:
        return bool(recorded)
    return bool((checkpoint.get("attempt_diagnostics") or {}).get("transient_recovered"))


def _truncation_unresolved(
    checkpoint: dict[str, Any],
    rework: dict[str, Any],
) -> bool:
    recorded = rework.get("provider_truncation_unresolved")
    if recorded is not None:
        return bool(recorded)
    return bool(
        (checkpoint.get("attempt_diagnostics") or {}).get(
            "provider_truncation_unresolved"
        )
    )


def rework_stats(records: list[dict[str, Any]]) -> dict[str, int]:
    """Aggregate rework events across a run's checkpoint records."""
    reworked = [cp for cp in records if cp.get("rework")]
    truncation_checkpoints = [
        cp
        for cp in reworked
        if _provider_truncation_count(cp, cp["rework"]) > 0
    ]
    return {
        "rework_attempts_total": sum(
            int((cp["rework"] or {}).get("attempts_total") or 0) for cp in reworked
        ),
        "semantic_attempts_total": sum(
            _semantic_attempt_count(cp["rework"]) for cp in reworked
        ),
        "semantic_rework_attempts": sum(
            max(_semantic_attempt_count(cp["rework"]) - 1, 0) for cp in reworked
        ),
        "transient_retries": sum(
            _transient_attempt_count(cp["rework"]) for cp in reworked
        ),
        "repeated_attempts": sum(
            max(
                _semantic_attempt_count(cp["rework"]) - 1,
                0,
            )
            for cp in reworked
        ),
        "rework_fixed": sum(1 for cp in reworked if cp["rework"].get("fixed")),
        "rework_unresolved": sum(
            1 for cp in reworked if not cp["rework"].get("fixed")
        ),
        "reworked_checkpoints": len(reworked),
        "provider_truncations": sum(
            _provider_truncation_count(cp, cp["rework"])
            for cp in reworked
        ),
        "provider_truncation_checkpoints": len(truncation_checkpoints),
        "transient_recoveries": sum(
            1
            for cp in truncation_checkpoints
            if _truncation_recovered(cp, cp["rework"]) or cp["rework"].get("fixed")
        ),
        "provider_truncation_unresolved": sum(
            1
            for cp in truncation_checkpoints
            if _truncation_unresolved(cp, cp["rework"])
            or (not _truncation_recovered(cp, cp["rework"]) and not cp["rework"].get("fixed"))
        ),
    }


def build_rework_entry(
    *,
    cp_record: dict[str, Any],
    rework: dict[str, Any],
    manifest: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any]:
    """Build a failure entry mirroring repair.build_failure_entry's schema."""
    final_attempt = (rework.get("attempts") or [{}])[-1]
    model_settings = manifest.get("model_settings") or {}
    extra = manifest.get("extra") or {}
    checkpoint_usage = cp_record.get("usage") or {}
    semantic_attempts = _semantic_attempt_count(rework)
    transient_retries = _transient_attempt_count(rework)
    provider_truncations = _provider_truncation_count(cp_record, rework)
    truncation_recovered = _truncation_recovered(cp_record, rework)
    truncation_unresolved = _truncation_unresolved(cp_record, rework)
    return {
        "date": datetime.now(UTC).isoformat(),
        "experiment_id": manifest.get("experiment_id"),
        "arm": manifest.get("arm"),
        "harness": manifest.get("arm"),
        "agent": manifest.get("agent"),
        "agent_version": manifest.get("agent_version"),
        "provider": model_settings.get("provider"),
        "model": manifest.get("model"),
        "thinking": model_settings.get("thinking"),
        "problem": cp_record.get("problem") or manifest.get("problem"),
        "checkpoint": cp_record.get("checkpoint_name"),
        "run_index": extra.get("run_index"),
        "source": "rework",
        "attempts_total": int(rework.get("attempts_total") or 0),
        "semantic_attempts_total": semantic_attempts,
        "transient_retries": transient_retries,
        "provider_truncations": provider_truncations,
        "provider_truncation_recovered": truncation_recovered,
        "provider_truncation_unresolved": truncation_unresolved,
        "feedback_strategy": rework.get("feedback_strategy"),
        "fixed": bool(rework.get("fixed")),
        "attempts": rework.get("attempts") or [],
        "post_fix_score": score_from_counts(
            final_attempt.get("pass_counts"), final_attempt.get("total_counts")
        ),
        "pass_counts": final_attempt.get("pass_counts"),
        "total_counts": final_attempt.get("total_counts"),
        "failed_tests": final_attempt.get("failed_tests") or [],
        "failed_tests_by_group": final_attempt.get("failed_tests_by_group"),
        "groups": final_attempt.get("groups"),
        "failure_class": (
            "provider_truncation"
            if truncation_unresolved
            else final_attempt.get("failure_class")
        ),
        "diagnostics": final_attempt.get("diagnostics"),
        "feedback_context": final_attempt.get("feedback_context"),
        "core": final_attempt.get("core"),
        "usage": final_attempt.get("usage"),
        "creation_input_tokens": checkpoint_usage.get("creation_input_tokens"),
        "creation_output_tokens": checkpoint_usage.get("creation_output_tokens"),
        "rework_input_tokens": checkpoint_usage.get("rework_input_tokens"),
        "rework_output_tokens": checkpoint_usage.get("rework_output_tokens"),
        "infrastructure_failure": bool(final_attempt.get("infrastructure_failure")),
        "root_cause": (
            "provider_truncation"
            if truncation_unresolved
            else None
        ),
        "fix": (
            "transient-retry"
            if truncation_unresolved
            else "rework"
        ),
        "resumed": False,
        "paths": {
            "run_dir": str(run_dir),
            "checkpoint_dir": str((cp_record.get("paths") or {}).get("checkpoint_dir")),
            "snapshot_dir": str((cp_record.get("paths") or {}).get("snapshot_dir")),
        },
    }


def record_rework_events(
    *,
    collected: dict[str, Any],
    manifest: dict[str, Any],
    run_dir: Path,
) -> int:
    """Write failure entries for every checkpoint that needed rework.

    Returns the number of entries written.
    """
    count = 0
    for cp in collected.get("checkpoints") or []:
        rework = cp.get("rework")
        if not rework:
            continue
        entry = build_rework_entry(
            cp_record=cp,
            rework=rework,
            manifest=manifest,
            run_dir=Path(run_dir),
        )
        record_failure(str(entry["problem"]), entry)
        count += 1
    return count


def load_rework_json(checkpoint_dir: Path) -> dict[str, Any] | None:
    path = Path(checkpoint_dir) / "rework.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
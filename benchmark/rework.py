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


def rework_stats(records: list[dict[str, Any]]) -> dict[str, int]:
    """Aggregate rework events across a run's checkpoint records."""
    reworked = [cp for cp in records if cp.get("rework")]
    return {
        "rework_attempts_total": sum(
            int((cp["rework"] or {}).get("attempts_total") or 0) for cp in reworked
        ),
        "repeated_attempts": sum(
            max(int((cp["rework"] or {}).get("attempts_total") or 0) - 1, 0)
            for cp in reworked
        ),
        "rework_fixed": sum(1 for cp in reworked if cp["rework"].get("fixed")),
        "rework_unresolved": sum(
            1 for cp in reworked if not cp["rework"].get("fixed")
        ),
        "reworked_checkpoints": len(reworked),
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
        "core": final_attempt.get("core"),
        "usage": final_attempt.get("usage"),
        "creation_input_tokens": checkpoint_usage.get("creation_input_tokens"),
        "creation_output_tokens": checkpoint_usage.get("creation_output_tokens"),
        "rework_input_tokens": checkpoint_usage.get("rework_input_tokens"),
        "rework_output_tokens": checkpoint_usage.get("rework_output_tokens"),
        "infrastructure_failure": bool(final_attempt.get("infrastructure_failure")),
        "root_cause": None,
        "fix": "rework",
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
"""Per-problem failure records for repair-mode triage.

Each problem gets its own JSON file under ``failures/<problem>.json`` so that
error patterns per problem can be studied across harnesses and experiments.
Every entry records which model/harness/agent failed at which checkpoint, the
failing tests, an optional root-cause note, and the fix that was applied.

The recorder is deliberately dumb: it appends (or replaces, keyed by
experiment_id + checkpoint) a JSON object.  Analysis lives elsewhere.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.paths import REPO_ROOT

FAILURES_DIR = REPO_ROOT / "failures"


def failures_path(problem: str) -> Path:
    """Return the per-problem failure file path."""
    return FAILURES_DIR / f"{problem}.json"


def load_failures(problem: str) -> list[dict[str, Any]]:
    """Load all recorded failure entries for a problem ([] if none yet)."""
    path = failures_path(problem)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def record_failure(problem: str, entry: dict[str, Any]) -> Path:
    """Append a failure entry to the per-problem file (creating it if needed).

    Entries are keyed by ``(experiment_id, checkpoint, run_index)``: recording
    the same failure twice (e.g. after a fix was verified) replaces the
    previous entry instead of duplicating it.  Entries without a ``run_index``
    (written before the key was extended) keep keying on the first two fields,
    so legacy records are never dropped.
    """
    path = failures_path(problem)
    entries = load_failures(problem)
    key = (
        entry.get("experiment_id"),
        entry.get("checkpoint"),
        entry.get("run_index"),
    )
    entries = [
        existing
        for existing in entries
        if (
            existing.get("experiment_id"),
            existing.get("checkpoint"),
            existing.get("run_index"),
        )
        != key
    ]
    entries.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(entries, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path

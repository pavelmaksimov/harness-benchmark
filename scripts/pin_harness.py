#!/usr/bin/env python3
"""(Re)pin VERSION.json for `single`-kind harness arms.

Usage:
    uv run python scripts/pin_harness.py <arm> [<arm> ...]

For every arm it hashes ``harnesses/<arm>/skill``:

- ``skill_sha256``  — plain sha256 of SKILL.md bytes (verified at activation time);
- ``tree_sha256``   — sha256 over sorted files, each contributing
  ``relative/path\\n + file bytes`` (used for smoke-marker invalidation);
- plus ``skill_bytes``, ``file_count``, ``pinned_at`` (UTC).

The scheme is intentionally simple and re-computable offline; do not edit
VERSION.json by hand — rerun this script after any change under ``skill/``.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESSES_DIR = REPO_ROOT / "harnesses"


def _tree_sha256(skill_dir: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(p for p in skill_dir.rglob("*") if p.is_file())
    for path in files:
        rel = path.relative_to(skill_dir).as_posix()
        digest.update(rel.encode("utf-8") + b"\n")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def pin_arm(arm: str) -> Path:
    harness_dir = HARNESSES_DIR / arm
    skill_dir = harness_dir / "skill"
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise SystemExit(f"{arm}: expected {skill_md} (kind=single layout)")

    existing: dict = {}
    version_path = harness_dir / "VERSION.json"
    if version_path.is_file():
        existing = json.loads(version_path.read_text(encoding="utf-8"))

    files = sorted(p for p in skill_dir.rglob("*") if p.is_file())
    meta = {
        "name": arm,
        "skill_name": arm,
        "version": "pinned-local",
        "kind": "single",
        "skill_sha256": hashlib.sha256(skill_md.read_bytes()).hexdigest(),
        "tree_sha256": _tree_sha256(skill_dir),
        "skill_bytes": skill_md.stat().st_size,
        "file_count": len(files),
        "pinned_at": datetime.now(timezone.utc).isoformat(),
        "source": str(skill_dir),
    }
    # Preserve unknown extra keys an operator may have added previously.
    for key, value in existing.items():
        meta.setdefault(key, value)
    version_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return version_path


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    for arm in argv:
        if not (HARNESSES_DIR / arm).is_dir():
            print(f"unknown harness dir: harnesses/{arm}", file=sys.stderr)
            return 1
        path = pin_arm(arm)
        meta = json.loads(path.read_text(encoding="utf-8"))
        print(f"pinned {arm}: tree={meta['tree_sha256'][:12]} skill={meta['skill_sha256'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

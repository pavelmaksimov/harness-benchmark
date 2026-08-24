#!/usr/bin/env python3
"""(Re)pin VERSION.json for harness arms.

Usage:
    uv run python scripts/pin_harness.py <arm> [<arm> ...]

For a single arm it hashes ``harnesses/<arm>/skill`` and, when present, the
optional ``harnesses/<arm>/AGENTS.md`` payload. For a bundle it hashes
the payload under ``harnesses/<arm>/skills`` and ``harnesses/<arm>/home``:

- ``skill_sha256``  — plain sha256 of SKILL.md bytes (verified at activation time);
- ``tree_sha256``   — sha256 over sorted files, each contributing
  ``relative/path\\n + file bytes`` (used for smoke-marker invalidation);
- plus ``skill_bytes``, ``file_count``, ``pinned_at`` (UTC).

The scheme is intentionally simple and re-computable offline; do not edit
VERSION.json by hand — rerun this script after any change under the payload
directories.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESSES_DIR = REPO_ROOT / "harnesses"


def _tree_sha256(
    skill_dir: Path,
    extra_files: list[tuple[str, Path]] | None = None,
) -> str:
    digest = hashlib.sha256()
    files = sorted(p for p in skill_dir.rglob("*") if p.is_file())
    for path in files:
        rel = path.relative_to(skill_dir).as_posix()
        digest.update(rel.encode("utf-8") + b"\n")
        digest.update(path.read_bytes())
    for rel, path in sorted(extra_files or []):
        digest.update(rel.encode("utf-8") + b"\n")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _bundle_files(harness_dir: Path) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for root_name in ("skills", "home"):
        root = harness_dir / root_name
        if not root.is_dir():
            continue
        files.extend(
            (f"{root_name}/{path.relative_to(root).as_posix()}", path)
            for path in root.rglob("*")
            if path.is_file()
        )
    return sorted(files)


def _bundle_tree_sha256(files: list[tuple[str, Path]]) -> str:
    digest = hashlib.sha256()
    for rel, path in files:
        digest.update(rel.encode("utf-8") + b"\n")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def pin_arm(arm: str) -> Path:
    harness_dir = HARNESSES_DIR / arm
    skill_dir = harness_dir / "skill"
    skill_md = skill_dir / "SKILL.md"

    existing: dict = {}
    version_path = harness_dir / "VERSION.json"
    if version_path.is_file():
        existing = json.loads(version_path.read_text(encoding="utf-8"))

    if skill_md.is_file():
        files = sorted(p for p in skill_dir.rglob("*") if p.is_file())
        agents_md = harness_dir / "AGENTS.md"
        extra_files = [("AGENTS.md", agents_md)] if agents_md.is_file() else []
        meta = {
            "name": arm,
            "skill_name": arm,
            "version": "pinned-local",
            "kind": "single",
            "skill_sha256": hashlib.sha256(skill_md.read_bytes()).hexdigest(),
            "tree_sha256": _tree_sha256(skill_dir, extra_files),
            "skill_bytes": skill_md.stat().st_size,
            "file_count": len(files),
            "pinned_at": datetime.now(timezone.utc).isoformat(),
            "source": str(skill_dir),
        }
        if agents_md.is_file():
            meta["agents_sha256"] = hashlib.sha256(agents_md.read_bytes()).hexdigest()
            meta["agents_bytes"] = agents_md.stat().st_size
    else:
        bundle_files = _bundle_files(harness_dir)
        if not bundle_files:
            raise SystemExit(
                f"{arm}: expected {skill_md} or bundle payload under "
                f"{harness_dir / 'skills'} / {harness_dir / 'home'}"
            )
        meta = {
            "name": arm,
            "skill_names": sorted(
                path.name
                for path in (harness_dir / "skills").iterdir()
                if path.is_dir()
            )
            if (harness_dir / "skills").is_dir()
            else [],
            "version": "pinned-local",
            "kind": "bundle",
            "tree_sha256": _bundle_tree_sha256(bundle_files),
            "skill_bytes": sum(path.stat().st_size for _, path in bundle_files),
            "file_count": len(bundle_files),
            "pinned_at": datetime.now(timezone.utc).isoformat(),
            "source": f"{harness_dir / 'skills'} + {harness_dir / 'home'}",
        }
        if "component_arms" in existing:
            meta["component_arms"] = existing["component_arms"]
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
        skill_sha = meta.get("skill_sha256")
        skill_info = skill_sha[:12] if skill_sha else "bundle"
        print(f"pinned {arm}: tree={meta['tree_sha256'][:12]} skill={skill_info}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

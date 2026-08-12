from __future__ import annotations

import re
from pathlib import Path
from typing import Any

REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")


def _parse_requirements(path: Path) -> set[str]:
    if not path.exists():
        return set()
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        match = REQ_RE.match(stripped)
        if match:
            names.add(match.group(1).lower())
    return names


def _parse_pyproject_deps(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        import tomllib
    except ImportError:  # pragma: no cover
        return set()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies") or []
    names: set[str] = set()
    for dep in deps:
        match = REQ_RE.match(str(dep))
        if match:
            names.add(match.group(1).lower())
    return names


def collect_dependencies(snapshot_dir: Path) -> set[str]:
    names: set[str] = set()
    names |= _parse_requirements(snapshot_dir / "requirements.txt")
    names |= _parse_pyproject_deps(snapshot_dir / "pyproject.toml")
    return names


def dependency_delta(prev: set[str] | None, current: set[str]) -> dict[str, Any]:
    prev = prev or set()
    added = sorted(current - prev)
    removed = sorted(prev - current)
    return {
        "dependencies_added": len(added),
        "dependencies_removed": len(removed),
        "dependencies_added_list": added,
        "dependencies_removed_list": removed,
        "dependency_count": len(current),
    }

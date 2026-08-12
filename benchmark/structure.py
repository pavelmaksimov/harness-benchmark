from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from radon.complexity import cc_visit
from radon.visitors import Function as RadonFunction

SOURCE_SUFFIXES = {".py"}
EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    ".tox",
    "tests",
}


def _iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    if not root.exists():
        return files
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def _count_loc(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip() and not line.strip().startswith("#"))


def analyze_snapshot(snapshot_dir: Path) -> dict[str, Any]:
    """Deterministic structural metrics over Python sources in a snapshot."""
    files = _iter_source_files(snapshot_dir)
    function_count = 0
    class_count = 0
    complexities: list[int] = []
    largest_function_loc = 0
    largest_file_loc = 0
    total_loc = 0

    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        file_loc = _count_loc(text)
        total_loc += file_loc
        largest_file_loc = max(largest_file_loc, file_loc)

        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_count += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_count += 1
                try:
                    segment = ast.get_source_segment(text, node) or ""
                except Exception:  # noqa: BLE001
                    segment = ""
                largest_function_loc = max(largest_function_loc, _count_loc(segment))

        try:
            for block in cc_visit(text):
                if isinstance(block, RadonFunction):
                    complexities.append(int(block.complexity))
        except Exception:  # noqa: BLE001
            continue

    cc_total = sum(complexities) if complexities else 0
    cc_mean = (cc_total / len(complexities)) if complexities else 0.0
    cc_max = max(complexities) if complexities else 0

    return {
        "total_source_files": len(files),
        "total_source_loc": total_loc,
        "module_count": len(files),
        "function_count": function_count,
        "class_count": class_count,
        "cyclomatic_complexity_total": cc_total,
        "cyclomatic_complexity_mean": round(cc_mean, 4),
        "cyclomatic_complexity_max": cc_max,
        "largest_function_loc": largest_function_loc,
        "largest_file_loc": largest_file_loc,
    }

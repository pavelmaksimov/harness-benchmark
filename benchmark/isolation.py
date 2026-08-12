"""Baseline isolation checks: no Ponytail / extra harness files in workspace."""

from __future__ import annotations

from pathlib import Path
from typing import Any

FORBIDDEN_NAME_FRAGMENTS = (
    "ponytail",
    "AGENTS.md",
)
FORBIDDEN_DIR_NAMES = {
    "skills",
    ".agents",
    ".claude",
    ".codex",
    ".cursor",
}


def check_workspace_isolation(workspace: Path) -> dict[str, Any]:
    """Return isolation probe results for a workspace directory."""
    hits: list[str] = []
    if not workspace.exists():
        return {
            "workspace": str(workspace),
            "isolated": True,
            "hits": [],
            "note": "workspace_missing",
        }

    for path in workspace.rglob("*"):
        rel = str(path.relative_to(workspace))
        lower = rel.lower()
        if any(frag.lower() in lower for frag in FORBIDDEN_NAME_FRAGMENTS):
            hits.append(rel)
            continue
        if path.is_dir() and path.name in FORBIDDEN_DIR_NAMES:
            hits.append(rel)

    return {
        "workspace": str(workspace),
        "isolated": len(hits) == 0,
        "hits": hits[:50],
    }


def verify_baseline_prompt(prompt_text: str) -> bool:
    return "ponytail" not in prompt_text.lower()


def verify_ponytail_prompt(prompt_text: str) -> bool:
    return "ponytail" in prompt_text.lower()

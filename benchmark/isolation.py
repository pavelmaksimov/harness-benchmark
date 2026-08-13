"""Baseline isolation checks: no extra harness files in workspace."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from benchmark.arms import SKILL_ARMS, get_arm

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
    lower = prompt_text.lower()
    if "activate and follow the installed codex skill" in lower:
        return False
    if "ponytail" in lower:
        return False
    for arm in SKILL_ARMS:
        if arm.lower() in lower:
            return False
    return True


def verify_skill_prompt(arm: str, prompt_text: str) -> bool:
    spec = get_arm(arm)
    if spec.kind == "baseline":
        return verify_baseline_prompt(prompt_text)
    phrase = spec.activation_phrase or ""
    if phrase and phrase not in prompt_text:
        return False
    if spec.skill_name and spec.skill_name not in prompt_text:
        return False
    return True


def verify_ponytail_prompt(prompt_text: str) -> bool:
    return verify_skill_prompt("ponytail", prompt_text)

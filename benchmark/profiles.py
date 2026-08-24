"""Reusable, validated agent/provider/model selections."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from benchmark.catalog import ValidationIssue, ValidationReport, validate_selection
from benchmark.paths import CONFIGS_DIR, REPO_ROOT

DEFAULT_PROFILES_DIR = CONFIGS_DIR / "profiles"


def _text(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def resolve_profile_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else REPO_ROOT / path


@dataclass(frozen=True)
class RunProfile:
    """One tested agent/provider/model/thinking combination."""

    path: Path
    profile_id: str
    agent: str
    provider: str
    model: str
    thinking: str
    description: str = ""

    def selection(self) -> dict[str, str]:
        return {
            "agent": self.agent,
            "provider": self.provider,
            "model": self.model,
            "thinking": self.thinking,
        }


def load_profile(path: str | Path) -> RunProfile:
    """Load one profile from a repository-relative YAML path."""
    resolved = resolve_profile_path(path)
    if not resolved.is_file():
        raise FileNotFoundError(f"profile not found: {path}")
    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid profile YAML: {resolved}: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise TypeError(f"profile root must be a mapping: {resolved}")
    profile_id = _text(raw.get("id", resolved.stem), field_name="profile.id")
    return RunProfile(
        path=resolved,
        profile_id=profile_id,
        agent=_text(raw.get("agent"), field_name="profile.agent"),
        provider=_text(raw.get("provider"), field_name="profile.provider"),
        model=_text(raw.get("model"), field_name="profile.model"),
        thinking=_text(raw.get("thinking"), field_name="profile.thinking"),
        description=_text(raw["description"], field_name="profile.description")
        if raw.get("description") is not None
        else "",
    )


def list_profiles(directory: Path = DEFAULT_PROFILES_DIR) -> tuple[RunProfile, ...]:
    profiles: list[RunProfile] = []
    for path in sorted(directory.glob("*.yaml")):
        profiles.append(load_profile(path))
    return tuple(profiles)


def validate_profile(profile: RunProfile, *, check_credentials: bool = False) -> ValidationReport:
    """Validate the profile against the same catalogs used by SCB."""
    report = validate_selection(
        **profile.selection(),
        scope=f"profile {profile.path}",
        check_credentials=check_credentials,
    )
    issues = list(report.issues)
    agent_config = CONFIGS_DIR / f"agent_{profile.agent}.yaml"
    if profile.agent in {"codex", "opencode"} and not agent_config.is_file():
        issues.append(ValidationIssue(f"profile {profile.path}", f"agent config not found: {agent_config}"))
    return ValidationReport(tuple(issues))


def render_profiles(profiles: tuple[RunProfile, ...]) -> str:
    if not profiles:
        return "no profiles"
    return "\n".join(
        f"{profile.profile_id}: {profile.path} -> "
        f"{profile.agent}/{profile.provider}/{profile.model}/{profile.thinking}"
        for profile in profiles
    )

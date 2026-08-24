"""Desired-state configuration for the benchmark fleet.

The file is deliberately small and YAML-only.  It is an operator input, not
another benchmark manifest: a run's immutable identity still comes from its
``state.json``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from benchmark.paths import CONFIGS_DIR
from benchmark.profiles import load_profile

DEFAULT_DESIRED_PATH = CONFIGS_DIR / "desired.yaml"
SAFE_ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.:")
SELECTION_FIELDS = ("agent", "provider", "model", "thinking")


def _string(value: Any, *, field_name: str, default: str | None = None) -> str | None:
    if value is None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _positive_int(value: Any, *, field_name: str, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be an integer >= 1")
    return value


def _non_negative_int(value: Any, *, field_name: str, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be an integer >= 0")
    return value


def _as_expect(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("harnesses.<name>.expect must be a string or a list of strings")
    return tuple(item.strip() for item in value if item.strip())


@dataclass(frozen=True)
class HarnessTarget:
    """Operator notes for one harness onboarding attempt."""

    source: str | None = None
    install: str | list[str] | None = None
    expect: tuple[str, ...] = ()
    docs: str | None = None

    @classmethod
    def from_raw(cls, raw: Any) -> HarnessTarget:
        if raw is None:
            raw = {}
        if not isinstance(raw, Mapping):
            raise TypeError("harnesses.<name> must be a mapping")
        install = raw.get("install")
        if install is not None and not isinstance(install, (str, list)):
            raise ValueError("harnesses.<name>.install must be text or a list")
        if isinstance(install, list) and not all(isinstance(item, str) for item in install):
            raise ValueError("harnesses.<name>.install list must contain strings")
        return cls(
            source=_string(raw.get("source"), field_name="harnesses.<name>.source"),
            install=install,
            expect=_as_expect(raw.get("expect")),
            docs=_string(raw.get("docs"), field_name="harnesses.<name>.docs"),
        )


@dataclass(frozen=True)
class FleetDefaults:
    agent: str = "codex"
    provider: str = "codex_auth"
    model: str = "gpt-5.6-luna"
    thinking: str = "max"
    runs: int = 1
    jobs: int = 1
    rework_attempts: int = 2
    transient_retries: int = 0
    feedback_strategy: str | None = "current-first"
    interval: float = 30.0
    max_restarts: int = 3
    profile: str | None = None

    @classmethod
    def from_raw(cls, raw: Any) -> FleetDefaults:
        if raw is None:
            raw = {}
        if not isinstance(raw, Mapping):
            raise TypeError("defaults must be a mapping")
        interval = raw.get("interval", cls.interval)
        if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval <= 0:
            raise ValueError("defaults.interval must be a positive number")
        max_restarts = _non_negative_int(
            raw.get("max_restarts"), field_name="defaults.max_restarts", default=cls.max_restarts
        )
        profile_path = _string(raw.get("profile"), field_name="defaults.profile")
        if profile_path is not None:
            if any(field in raw for field in SELECTION_FIELDS):
                raise ValueError("defaults.profile cannot be combined with agent/provider/model/thinking")
            profile = load_profile(profile_path)
            selection = profile.selection()
        else:
            selection = {
                "agent": _string(raw.get("agent"), field_name="defaults.agent", default=cls.agent) or cls.agent,
                "provider": _string(raw.get("provider"), field_name="defaults.provider", default=cls.provider)
                or cls.provider,
                "model": _string(raw.get("model"), field_name="defaults.model", default=cls.model) or cls.model,
                "thinking": _string(raw.get("thinking"), field_name="defaults.thinking", default=cls.thinking)
                or cls.thinking,
            }
        return cls(
            **selection,
            runs=_positive_int(raw.get("runs"), field_name="defaults.runs", default=cls.runs),
            jobs=_positive_int(raw.get("jobs"), field_name="defaults.jobs", default=cls.jobs),
            rework_attempts=_non_negative_int(
                raw.get("rework_attempts"), field_name="defaults.rework_attempts", default=cls.rework_attempts
            ),
            transient_retries=_non_negative_int(
                raw.get("transient_retries"), field_name="defaults.transient_retries", default=cls.transient_retries
            ),
            feedback_strategy=_string(
                raw.get("feedback_strategy"), field_name="defaults.feedback_strategy", default=cls.feedback_strategy
            ),
            interval=float(interval),
            max_restarts=max_restarts,
            profile=profile_path,
        )


@dataclass(frozen=True)
class ExperimentTarget:
    id: str
    problem: str
    arms: tuple[str, ...]
    runs: int
    jobs: int
    agent: str
    provider: str
    model: str
    thinking: str
    rework_attempts: int
    transient_retries: int
    feedback_strategy: str | None
    max_restarts: int
    profile: str | None = None

    @classmethod
    def from_raw(cls, raw: Any, defaults: FleetDefaults) -> ExperimentTarget:
        if not isinstance(raw, Mapping):
            raise TypeError("experiments entries must be mappings")
        experiment_id = _string(raw.get("id"), field_name="experiments[].id")
        if experiment_id is None or not experiment_id.isascii() or not experiment_id[0].isalnum() or any(
            char not in SAFE_ID_CHARS for char in experiment_id
        ):
            raise ValueError(f"invalid experiment id: {experiment_id!r}")
        problem = _string(raw.get("problem"), field_name=f"experiments[{experiment_id}].problem")
        arms_raw = raw.get("arms")
        if not isinstance(arms_raw, list) or not arms_raw or not all(isinstance(item, str) for item in arms_raw):
            raise ValueError(f"experiments[{experiment_id}].arms must be a non-empty list")
        arms = tuple(item.strip() for item in arms_raw if item.strip())
        if not arms:
            raise ValueError(f"experiments[{experiment_id}].arms must contain a non-empty arm")
        if any(
            arm in {".", ".."}
            or not arm.isascii()
            or not arm[0].isalnum()
            or any(char not in SAFE_ID_CHARS for char in arm)
            for arm in arms
        ):
            raise ValueError(f"experiments[{experiment_id}].arms contains an unsafe name")
        if len(arms) != len(set(arms)):
            raise ValueError(f"experiments[{experiment_id}].arms contains duplicates")
        profile_path = _string(raw.get("profile"), field_name=f"experiments[{experiment_id}].profile")
        direct_fields = [field for field in SELECTION_FIELDS if field in raw]
        if profile_path is not None:
            if direct_fields:
                raise ValueError(
                    f"experiments[{experiment_id}].profile cannot be combined with "
                    "agent/provider/model/thinking"
                )
            profile = load_profile(profile_path)
            selection = profile.selection()
        elif defaults.profile is not None:
            if direct_fields:
                raise ValueError(
                    f"experiments[{experiment_id}] must use profile when defaults.profile is set"
                )
            profile_path = defaults.profile
            selection = {
                "agent": defaults.agent,
                "provider": defaults.provider,
                "model": defaults.model,
                "thinking": defaults.thinking,
            }
        else:
            selection = {
                "agent": _string(raw.get("agent"), field_name="experiment.agent", default=defaults.agent)
                or defaults.agent,
                "provider": _string(
                    raw.get("provider"), field_name="experiment.provider", default=defaults.provider
                )
                or defaults.provider,
                "model": _string(raw.get("model"), field_name="experiment.model", default=defaults.model)
                or defaults.model,
                "thinking": _string(
                    raw.get("thinking"), field_name="experiment.thinking", default=defaults.thinking
                )
                or defaults.thinking,
            }
        return cls(
            id=experiment_id,
            problem=problem or "",
            arms=arms,
            runs=_positive_int(raw.get("runs"), field_name=f"experiments[{experiment_id}].runs", default=defaults.runs),
            jobs=_positive_int(raw.get("jobs"), field_name=f"experiments[{experiment_id}].jobs", default=defaults.jobs),
            **selection,
            rework_attempts=_non_negative_int(
                raw.get("rework_attempts"), field_name="experiment.rework_attempts", default=defaults.rework_attempts
            ),
            transient_retries=_non_negative_int(
                raw.get("transient_retries"), field_name="experiment.transient_retries", default=defaults.transient_retries
            ),
            feedback_strategy=_string(
                raw.get("feedback_strategy"), field_name="experiment.feedback_strategy", default=defaults.feedback_strategy
            ),
            max_restarts=_non_negative_int(
                raw.get("max_restarts"), field_name="experiment.max_restarts", default=defaults.max_restarts
            ),
            profile=profile_path,
        )

    def selection(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "provider": self.provider,
            "model": self.model,
            "thinking": self.thinking,
            "problem": self.problem,
            "rework_attempts": self.rework_attempts,
            "transient_retries": self.transient_retries,
            "feedback_strategy": self.feedback_strategy,
            "profile": self.profile,
        }

    def identity_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "problem": self.problem,
            "arms": list(self.arms),
            **self.selection(),
        }

    def fingerprint(self) -> str:
        encoded = json.dumps(self.identity_payload(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DesiredConfig:
    path: Path
    defaults: FleetDefaults
    harnesses: dict[str, HarnessTarget] = field(default_factory=dict)
    experiments: tuple[ExperimentTarget, ...] = ()

    def harness(self, name: str) -> HarnessTarget:
        return self.harnesses.get(name, HarnessTarget())


def load_desired(path: Path = DEFAULT_DESIRED_PATH) -> DesiredConfig:
    """Load and validate the operator-owned desired state."""
    if not path.is_file():
        raise FileNotFoundError(f"desired config not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid desired YAML: {path}: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise TypeError("desired config root must be a mapping")
    defaults = FleetDefaults.from_raw(raw.get("defaults"))
    harness_raw = raw.get("harnesses") or {}
    if not isinstance(harness_raw, Mapping):
        raise TypeError("harnesses must be a mapping")
    harnesses: dict[str, HarnessTarget] = {}
    for name, value in harness_raw.items():
        name = str(name)
        if name in {".", ".."} or not name.isascii() or not name or not name[0].isalnum() or any(
            char not in SAFE_ID_CHARS for char in name
        ):
            raise ValueError(f"unsafe harness name: {name!r}")
        harnesses[name] = HarnessTarget.from_raw(value)
    experiments_raw = raw.get("experiments") or []
    if not isinstance(experiments_raw, list):
        raise TypeError("experiments must be a list")
    experiments = tuple(ExperimentTarget.from_raw(item, defaults) for item in experiments_raw)
    ids = [experiment.id for experiment in experiments]
    if len(ids) != len(set(ids)):
        raise ValueError("experiments contains duplicate ids")
    return DesiredConfig(path=Path(path), defaults=defaults, harnesses=harnesses, experiments=experiments)

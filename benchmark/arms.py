"""Registry of benchmark arms (baseline + skill harnesses)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from benchmark.paths import CONFIGS_DIR, HARNESSES_DIR


@dataclass(frozen=True)
class ArmSpec:
    """One experiment arm.

    kind:
      - baseline: no skill injection
      - single: one Codex skill directory
      - bundle: multiple skills (+ optional ~/.codex home extras)
      - legacy_ponytail: existing ponytail pin layout (SKILL.md at harness root)
    """

    name: str
    kind: str
    skill_name: str | None = None
    prompt_name: str | None = None
    config_name: str | None = None
    activation_phrase: str | None = None
    intensity_hint: str | None = None

    @property
    def config_path(self) -> Path:
        return CONFIGS_DIR / (self.config_name or f"{self.name}.yaml")

    @property
    def prompt_path(self) -> Path:
        if self.kind == "baseline":
            return CONFIGS_DIR / "prompts" / "just-solve.jinja"
        if self.prompt_name:
            return CONFIGS_DIR / "prompts" / self.prompt_name
        if self.name == "ponytail":
            return CONFIGS_DIR / "prompts" / "ponytail-solve.jinja"
        return CONFIGS_DIR / "prompts" / f"{self.name}-solve.jinja"

    @property
    def harness_dir(self) -> Path | None:
        if self.kind == "baseline":
            return None
        return HARNESSES_DIR / self.name

    @property
    def needs_hook(self) -> bool:
        return self.kind != "baseline"


BASELINE = ArmSpec(name="baseline", kind="baseline")

PONYTAIL = ArmSpec(
    name="ponytail",
    kind="legacy_ponytail",
    skill_name="ponytail",
    activation_phrase="Activate and follow the installed Codex skill `ponytail`",
    intensity_hint="full",
)

ARMS: dict[str, ArmSpec] = {
    "baseline": BASELINE,
    "ponytail": PONYTAIL,
    "thermo-nuclear-code-quality-review": ArmSpec(
        name="thermo-nuclear-code-quality-review",
        kind="single",
        skill_name="thermo-nuclear-code-quality-review",
        activation_phrase=(
            "Activate and follow the installed Codex skill "
            "`thermo-nuclear-code-quality-review`"
        ),
    ),
    "graphify": ArmSpec(
        name="graphify",
        kind="single",
        skill_name="graphify",
        activation_phrase="Activate and follow the installed Codex skill `graphify`",
    ),
    "supermemory": ArmSpec(
        name="supermemory",
        kind="bundle",
        skill_name="supermemory",
        activation_phrase=(
            "Activate and follow the installed Codex supermemory skills "
            "(`supermemory-search`, `supermemory-save`, `supermemory-add`, "
            "`supermemory-profile`, `supermemory-status`)"
        ),
    ),
    "tdd": ArmSpec(
        name="tdd",
        kind="single",
        skill_name="tdd",
        activation_phrase="Activate and follow the installed Codex skill `tdd`",
    ),
    "code-review": ArmSpec(
        name="code-review",
        kind="single",
        skill_name="code-review",
        activation_phrase="Activate and follow the installed Codex skill `code-review`",
    ),
    "review-agent": ArmSpec(
        name="review-agent",
        kind="single",
        skill_name="review-agent",
        activation_phrase="Activate and follow the installed Codex skill `review-agent`",
    ),
    "strictdoc": ArmSpec(
        name="strictdoc",
        kind="single",
        skill_name="strictdoc",
        activation_phrase="Activate and follow the installed Codex skill `strictdoc`",
    ),
    "doorstop": ArmSpec(
        name="doorstop",
        kind="single",
        skill_name="doorstop",
        activation_phrase="Activate and follow the installed Codex skill `doorstop`",
    ),
}

DEFAULT_EXPERIMENT_ARMS: tuple[str, ...] = (
    "baseline",
    "ponytail",
    "thermo-nuclear-code-quality-review",
    "graphify",
    "supermemory",
    "tdd",
    "code-review",
    "review-agent",
    "strictdoc",
    "doorstop",
)

SKILL_ARMS: tuple[str, ...] = tuple(a for a in DEFAULT_EXPERIMENT_ARMS if a != "baseline")


def get_arm(name: str) -> ArmSpec:
    try:
        return ARMS[name]
    except KeyError as exc:
        known = ", ".join(sorted(ARMS))
        raise ValueError(f"Unknown arm {name!r}; known: {known}") from exc


def known_arm_names() -> list[str]:
    return sorted(ARMS)

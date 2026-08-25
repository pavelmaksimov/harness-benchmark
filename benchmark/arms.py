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
    component_arms: tuple[str, ...] = ()

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


def _combo_phrase(components: tuple[str, ...]) -> str:
    names = ", ".join(f"`{component}`" for component in components)
    return f"Activate and follow the installed Codex skills {names}"


COMBO_SUPERMEMORY_GRAPHIFY_PONYTAIL_THERMO_DOORSTOP_TDD = (
    "combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd"
)
COMBO_SUPERMEMORY_GRAPHIFY_PONYTAIL_THERMO_TDD = (
    "combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd"
)
COMBO_SUPERMEMORY_GRAPHIFY_PONYTAIL_THERMO = (
    "combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review"
)
COMBO_SUPERMEMORY_GRAPHIFY = "combo-supermemory-graphify"
COMBO_REALWORLD_HARNESSES = (
    "python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy"
)
PYTHON_HARNESS_V123 = "python-harness-v1.2.3"
COMBO_PYTHON_HARNESS_V123_TDD = (
    "python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill"
)
COMBO_PYTHON_HARNESS_V123 = (
    "python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill"
)

COMBINATION_ARMS: dict[str, tuple[str, ...]] = {
    COMBO_SUPERMEMORY_GRAPHIFY_PONYTAIL_THERMO_DOORSTOP_TDD: (
        "supermemory",
        "graphify",
        "ponytail",
        "thermo-nuclear-code-quality-review",
        "doorstop",
        "tdd",
    ),
    COMBO_SUPERMEMORY_GRAPHIFY_PONYTAIL_THERMO_TDD: (
        "supermemory",
        "graphify",
        "ponytail",
        "thermo-nuclear-code-quality-review",
        "tdd",
    ),
    COMBO_SUPERMEMORY_GRAPHIFY_PONYTAIL_THERMO: (
        "supermemory",
        "graphify",
        "ponytail",
        "thermo-nuclear-code-quality-review",
    ),
    COMBO_SUPERMEMORY_GRAPHIFY: ("supermemory", "graphify"),
    COMBO_REALWORLD_HARNESSES: (
        "python-harness",
        "ponytail",
        "tdd",
        "graphify",
        "benjamin-plus-skill",
        "reclaim-code-entropy",
    ),
    COMBO_PYTHON_HARNESS_V123_TDD: (
        "python-harness",
        "ponytail",
        "tdd",
        "graphify",
        "benjamin-plus-skill",
    ),
    COMBO_PYTHON_HARNESS_V123: (
        "python-harness",
        "ponytail",
        "graphify",
        "benjamin-plus-skill",
    ),
}

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
    "python-harness": ArmSpec(
        name="python-harness",
        kind="single",
        skill_name="python-harness",
        activation_phrase="Activate and follow the installed Codex skill `python-harness`",
    ),
    PYTHON_HARNESS_V123: ArmSpec(
        name=PYTHON_HARNESS_V123,
        kind="single",
        skill_name="python-harness",
        activation_phrase="Activate and follow the installed Codex skill `python-harness`",
    ),
    "benjamin-plus-skill": ArmSpec(
        name="benjamin-plus-skill",
        kind="single",
        skill_name="benjamin-plus-skill",
        activation_phrase="Activate and follow the installed Codex skill `benjamin-plus-skill`",
    ),
    "reclaim-code-entropy": ArmSpec(
        name="reclaim-code-entropy",
        kind="single",
        skill_name="reclaim-code-entropy",
        activation_phrase="Activate and follow the installed Codex skill `reclaim-code-entropy`",
    ),
}
ARMS.update(
    {
        name: ArmSpec(
            name=name,
            kind="bundle",
            activation_phrase=_combo_phrase(components),
            component_arms=components,
        )
        for name, components in COMBINATION_ARMS.items()
    }
)

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
    "python-harness",
    PYTHON_HARNESS_V123,
    "benjamin-plus-skill",
    "reclaim-code-entropy",
    *COMBINATION_ARMS,
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


def arm_includes(arm: str | ArmSpec, component: str) -> bool:
    """Return whether an arm installs a component harness."""
    spec = get_arm(arm) if isinstance(arm, str) else arm
    return spec.name == component or component in spec.component_arms

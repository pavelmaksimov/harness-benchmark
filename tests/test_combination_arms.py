"""Tests for composed harness arms."""

from __future__ import annotations

from pathlib import Path

import pytest

from benchmark.arms import COMBINATION_ARMS, DEFAULT_EXPERIMENT_ARMS, arm_includes, get_arm
from benchmark.isolation import verify_skill_prompt
from benchmark.paths import HARNESSES_DIR
from benchmark.versions import copy_arm_skills, load_arm_meta


@pytest.mark.parametrize(("arm", "components"), list(COMBINATION_ARMS.items()))
def test_combination_arm_is_pinned_and_activatable(
    arm: str, components: tuple[str, ...]
) -> None:
    spec = get_arm(arm)
    assert spec.kind == "bundle"
    assert spec.component_arms == components
    assert arm in DEFAULT_EXPERIMENT_ARMS
    assert verify_skill_prompt(arm, spec.prompt_path.read_text(encoding="utf-8"))

    meta = load_arm_meta(arm)
    assert meta is not None
    assert meta["component_arms"] == list(components)
    assert meta["tree_sha256"]


@pytest.mark.parametrize("arm", list(COMBINATION_ARMS))
def test_combination_bundle_contains_component_payloads(arm: str) -> None:
    combo_dir = get_arm(arm).harness_dir
    assert combo_dir is not None
    skill_names = {
        path.name
        for path in (combo_dir / "skills").iterdir()
        if path.is_dir()
    }

    expected = set()
    for component in COMBINATION_ARMS[arm]:
        if component == "supermemory":
            source = HARNESSES_DIR / "supermemory" / "skills"
            expected.update(path.name for path in source.iterdir() if path.is_dir())
        elif component == "ponytail":
            expected.add("ponytail")
        else:
            expected.add(component)

    assert skill_names == expected
    if arm_includes(arm, "supermemory"):
        assert (combo_dir / "home" / "supermemory").is_dir()


def test_copy_combination_bundle_installs_runtime_and_all_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_calls: list[Path] = []

    def fake_runtime(codex_home: Path) -> dict[str, object]:
        runtime_calls.append(codex_home)
        return {"supermemory_credentials_injected": True}

    monkeypatch.setattr(
        "benchmark.versions.install_supermemory_runtime_config",
        fake_runtime,
    )
    arm = next(iter(COMBINATION_ARMS))
    codex_home = tmp_path / "home"
    marker = copy_arm_skills(arm, codex_home / "skills", codex_home)

    assert marker["harness_activation_verified"] is True
    assert marker["component_arms"] == list(COMBINATION_ARMS[arm])
    assert runtime_calls == [codex_home]
    assert (codex_home / "skills" / "graphify" / "SKILL.md").is_file()
    assert (codex_home / "skills" / "ponytail" / "SKILL.md").is_file()

from benchmark.arms import DEFAULT_EXPERIMENT_ARMS, get_arm
from benchmark.isolation import verify_skill_prompt
from benchmark.versions import copy_arm_agents_file, load_arm_meta, sha256_file


def test_benjamin_plus_skill_arm_is_registered_and_default() -> None:
    arm = get_arm("benjamin-plus-skill")

    assert arm.kind == "single"
    assert arm.skill_name == "benjamin-plus-skill"
    assert arm.prompt_path.name == "benjamin-plus-skill-solve.jinja"
    assert "benjamin-plus-skill" in DEFAULT_EXPERIMENT_ARMS
    assert verify_skill_prompt(arm.name, arm.prompt_path.read_text(encoding="utf-8"))


def test_benjamin_plus_skill_pin_tracks_upstream_commit() -> None:
    arm = get_arm("benjamin-plus-skill")
    meta = load_arm_meta(arm)

    assert meta is not None
    assert meta["source_commit"] == "532771be5687566b12a9f62e17fbe7ad3591518c"
    assert sha256_file(arm.harness_dir / "skill" / "SKILL.md") == meta["skill_sha256"]
    assert meta["agents_sha256"] == sha256_file(arm.harness_dir / "AGENTS.md")


def test_benjamin_plus_skill_exports_agents_rules_for_opencode(tmp_path) -> None:
    source = get_arm("benjamin-plus-skill").harness_dir / "AGENTS.md"
    destination = tmp_path / "workspace" / "AGENTS.md"

    marker = copy_arm_agents_file("benjamin-plus-skill", destination)

    assert marker["agents_file_present"] is True
    assert marker["agents_file_verified"] is True
    assert destination.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")

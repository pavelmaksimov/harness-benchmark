from benchmark.arms import DEFAULT_EXPERIMENT_ARMS, get_arm
from benchmark.versions import load_arm_meta, sha256_file
from benchmark.versions import copy_arm_agents_file


def test_python_harness_arm_is_registered_but_not_default_before_smoke() -> None:
    arm = get_arm("python-harness")

    assert arm.kind == "single"
    assert arm.skill_name == "python-harness"
    assert arm.prompt_path.name == "python-harness-solve.jinja"
    assert "python-harness" not in DEFAULT_EXPERIMENT_ARMS


def test_python_harness_pin_tracks_upstream_commit() -> None:
    arm = get_arm("python-harness")
    meta = load_arm_meta(arm)

    assert meta is not None
    assert meta["catalog_version"] == "1.2.3"
    assert meta["source_commit"] == "f96781a32da3481b90d24bc054d3c8e6a86fc29f"
    assert sha256_file(arm.harness_dir / "skill" / "SKILL.md") == meta["skill_sha256"]


def test_python_harness_exports_flattened_rules_for_opencode(tmp_path) -> None:
    source = get_arm("python-harness").harness_dir / "AGENTS.md"
    destination = tmp_path / "workspace" / "AGENTS.md"

    marker = copy_arm_agents_file("python-harness", destination)

    assert marker["agents_file_present"] is True
    assert marker["agents_file_verified"] is True
    assert destination.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert "python-tooling/python-tooling.mdc" in destination.read_text(encoding="utf-8")
    assert "python-fastapi/python-fastapi.mdc" in destination.read_text(encoding="utf-8")

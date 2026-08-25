from benchmark.arms import DEFAULT_EXPERIMENT_ARMS, get_arm
from benchmark.isolation import verify_skill_prompt
from benchmark.versions import load_arm_meta, sha256_file


def test_reclaim_code_entropy_arm_is_registered_and_default() -> None:
    arm = get_arm("reclaim-code-entropy")

    assert arm.kind == "single"
    assert arm.skill_name == "reclaim-code-entropy"
    assert arm.prompt_path.name == "reclaim-code-entropy-solve.jinja"
    assert "reclaim-code-entropy" in DEFAULT_EXPERIMENT_ARMS
    assert verify_skill_prompt(arm.name, arm.prompt_path.read_text(encoding="utf-8"))


def test_reclaim_code_entropy_pin_tracks_upstream_commit() -> None:
    arm = get_arm("reclaim-code-entropy")
    meta = load_arm_meta(arm)

    assert meta is not None
    assert meta["source_commit"] == "9e6482e45814076b9710b55c8dcbb064ba4b7977"
    assert sha256_file(arm.harness_dir / "skill" / "SKILL.md") == meta["skill_sha256"]
    assert (arm.harness_dir / "skill" / "agents" / "openai.yaml").is_file()

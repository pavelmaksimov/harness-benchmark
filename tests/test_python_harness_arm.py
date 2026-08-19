from benchmark.arms import DEFAULT_EXPERIMENT_ARMS, get_arm
from benchmark.versions import load_arm_meta, sha256_file


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
    assert meta["source_commit"] == "38ada37707ba31fea94ec852b3272b77364a88fd"
    assert sha256_file(arm.harness_dir / "skill" / "SKILL.md") == meta["skill_sha256"]

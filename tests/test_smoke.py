"""Offline unit tests for reduced-checkpoint problem staging (smoke gate)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from benchmark.smoke import stage_cp1_only_problem


@pytest.fixture()
def fake_problem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal problem catalog with three ordered checkpoints."""
    from benchmark import smoke as smoke_mod

    src = tmp_path / "src_problem"
    (src / "tests").mkdir(parents=True)
    checkpoints = {
        "checkpoint_2": {"version": 1, "order": 2, "state": "Core Tests"},
        "checkpoint_1": {"version": 1, "order": 1, "state": "Core Tests"},
        "checkpoint_3": {"version": 1, "order": 3, "state": "Core Tests"},
    }
    (src / "config.yaml").write_text(
        yaml.safe_dump({"version": 1, "name": "fake", "checkpoints": checkpoints}),
        encoding="utf-8",
    )
    monkeypatch.setattr(smoke_mod, "PROBLEMS_DIR", tmp_path)
    return src


def _staged_names(dest_root: Path) -> list[str]:
    cfg = yaml.safe_load(
        (dest_root / "src_problem" / "config.yaml").read_text(encoding="utf-8")
    )
    return list(cfg["checkpoints"])


def test_default_stages_cp1_only(fake_problem: Path, tmp_path: Path) -> None:
    dest = stage_cp1_only_problem(problem="src_problem", dest_root=tmp_path / "out")
    assert _staged_names(dest) == ["checkpoint_1"]


def test_checkpoint_count_keeps_leading_order(fake_problem: Path, tmp_path: Path) -> None:
    dest = stage_cp1_only_problem(
        problem="src_problem", dest_root=tmp_path / "out2", checkpoint_count=2
    )
    # order field wins over dict order in the source config
    assert _staged_names(dest) == ["checkpoint_1", "checkpoint_2"]


def test_checkpoint_count_capped_by_available(fake_problem: Path, tmp_path: Path) -> None:
    dest = stage_cp1_only_problem(
        problem="src_problem", dest_root=tmp_path / "out3", checkpoint_count=99
    )
    assert _staged_names(dest) == ["checkpoint_1", "checkpoint_2", "checkpoint_3"]


def test_invalid_count_rejected(fake_problem: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        stage_cp1_only_problem(
            problem="src_problem", dest_root=tmp_path / "out4", checkpoint_count=0
        )

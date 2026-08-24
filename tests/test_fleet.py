from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from benchmark.catalog import catalog_snapshot, validate_desired
from benchmark.fleet.config import load_desired
from benchmark.fleet.planner import build_plan
from benchmark.notify import DeliveryResult, notify_experiment_completion, notify_human
from benchmark.profiles import load_profile, validate_profile


def _desired(path: Path, *, runs: int = 2, arms: list[str] | None = None) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "defaults": {"runs": runs, "jobs": 2},
                "harnesses": {},
                "experiments": [
                    {"id": "exp", "problem": "file_backup", "arms": arms or ["baseline"]}
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _state(run_dir: Path, **overrides: object) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "phase": "failed",
        "exit_code": 1,
        "fully_completed": False,
        "experiment_id": "exp",
        "arm": "baseline",
        "run_index": int(run_dir.name.removeprefix("run_")),
        "problem": "file_backup",
        "agent": "codex",
        "provider": "codex_auth",
        "model": "gpt-5.6-luna",
        "thinking": "max",
        "rework_attempts": 2,
        "transient_retries": 0,
    }
    state.update(overrides)
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")


def test_planner_distinguishes_new_resume_and_done(tmp_path: Path) -> None:
    config_path = tmp_path / "desired.yaml"
    _desired(config_path)
    desired = load_desired(config_path)
    root = tmp_path / "results"
    run_1 = root / "exp" / "baseline" / "run_1"
    _state(run_1, phase="completed", exit_code=0, fully_completed=True)
    (run_1 / "metrics").mkdir()
    (run_1 / "metrics" / "run.json").write_text("{}", encoding="utf-8")
    _state(root / "exp" / "baseline" / "run_2")

    plan = build_plan(desired, results_dir=root, ops_dir=tmp_path / "ops")

    assert plan.statuses["exp/baseline/run_1"] == "done"
    assert plan.statuses["exp/baseline/run_2"] == "queued"
    assert {action.kind for action in plan.actions} == {"resume"}


def test_catalog_exposes_exact_provider_and_model_names() -> None:
    snapshot = catalog_snapshot()

    assert any(row["name"] == "opencode_auth" for row in snapshot["providers"])
    assert any(row["name"] == "x-preview-f-free" for row in snapshot["models"])


def test_desired_validation_rejects_unknown_provider_and_model(tmp_path: Path) -> None:
    config_path = tmp_path / "desired.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "defaults": {
                    "agent": "opencode",
                    "provider": "not-a-provider",
                    "model": "not-a-model",
                    "thinking": "high",
                },
                "experiments": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    report = validate_desired(load_desired(config_path))

    assert not report.ok
    rendered = report.render()
    assert "unknown provider 'not-a-provider'" in rendered
    assert "unknown model 'not-a-model'" in rendered


def test_desired_profile_resolves_and_validates_selection(tmp_path: Path) -> None:
    profile_path = tmp_path / "codex.yaml"
    profile_path.write_text(
        yaml.safe_dump(
            {
                "id": "codex-test",
                "agent": "codex",
                "provider": "codex_auth",
                "model": "gpt-5.6-luna",
                "thinking": "max",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "desired.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {"defaults": {"profile": str(profile_path)}, "experiments": []},
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    desired = load_desired(config_path)

    assert desired.defaults.profile == str(profile_path)
    assert desired.defaults.agent == "codex"
    assert validate_profile(load_profile(profile_path)).ok


def test_profile_cannot_be_mixed_with_direct_selection(tmp_path: Path) -> None:
    profile_path = tmp_path / "codex.yaml"
    profile_path.write_text(
        "agent: codex\nprovider: codex_auth\nmodel: gpt-5.6-luna\nthinking: max\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "desired.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {"defaults": {"profile": str(profile_path), "model": "other"}, "experiments": []},
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cannot be combined"):
        load_desired(config_path)


def test_planner_blocks_selection_change(tmp_path: Path) -> None:
    config_path = tmp_path / "desired.yaml"
    _desired(config_path, runs=1)
    desired = load_desired(config_path)
    root = tmp_path / "results"
    run_dir = root / "exp" / "baseline" / "run_1"
    _state(run_dir, model="different-model")

    plan = build_plan(desired, results_dir=root, ops_dir=tmp_path / "ops")

    assert plan.statuses["exp/baseline/run_1"] == "blocked-human"
    assert any(action.kind == "ticket" for action in plan.actions)


class _Notifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def deliver(self, message: str, *, key: str) -> DeliveryResult:
        self.calls.append((message, key))
        return DeliveryResult(True, key)


def test_human_ticket_and_completion_are_idempotent(tmp_path: Path) -> None:
    notifier = _Notifier()
    ticket, first = notify_human(
        fingerprint="same-problem",
        title="Needs operator",
        summary="blocked",
        details="experiment=exp\narm=baseline\n",
        ops_dir=tmp_path / "ops",
        notifier=notifier,
    )
    same_ticket, second = notify_human(
        fingerprint="same-problem",
        title="Needs operator",
        summary="blocked",
        details="experiment=exp\narm=baseline\n",
        ops_dir=tmp_path / "ops",
        notifier=notifier,
    )

    assert ticket == same_ticket
    assert first.delivered and second.reason == "cooldown"
    assert len(notifier.calls) == 1


def test_completion_notification_is_once_per_revision(tmp_path: Path) -> None:
    config_path = tmp_path / "desired.yaml"
    _desired(config_path, runs=1)
    experiment = load_desired(config_path).experiments[0]
    results = tmp_path / "results"
    run_dir = results / "exp" / "baseline" / "run_1"
    _state(run_dir, phase="completed", exit_code=0, fully_completed=True, updated_at="2026-08-24T12:00:00+00:00")
    notifier = _Notifier()

    first = notify_experiment_completion(
        experiment,
        completed_cells=1,
        total_cells=1,
        arms=("baseline",),
        notifier=notifier,
        results_dir=results,
        reports_dir=tmp_path / "reports",
    )
    second = notify_experiment_completion(
        experiment,
        completed_cells=1,
        total_cells=1,
        arms=("baseline",),
        notifier=notifier,
        results_dir=results,
        reports_dir=tmp_path / "reports",
    )

    assert first.delivered and second.reason == "already-sent"
    assert len(notifier.calls) == 1

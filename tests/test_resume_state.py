from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from benchmark import paths, resume_state, scb_run
from benchmark.cli import app

PROBLEM = "file_backup"
OK_RESULT = {"completed": True, "had_error": False, "usage": {"cost": 0.1}}


def _mk_cp(base: Path, name: str, *, result=None, snapshot=True, evaluation=None) -> Path:
    cp = base / name
    cp.mkdir(parents=True, exist_ok=True)
    if snapshot:
        (cp / "snapshot").mkdir(exist_ok=True)
    if result is not None:
        (cp / "inference_result.json").write_text(json.dumps(result), encoding="utf-8")
    if evaluation is not None:
        (cp / "evaluation.json").write_text(json.dumps(evaluation), encoding="utf-8")
    return cp


def _declare(problem_dir: Path, *names: str) -> None:
    problem_dir.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"  {name}: {{}}" for name in names)
    (problem_dir / "problem.yaml").write_text(
        "checkpoints:\n" + body + "\n", encoding="utf-8"
    )
    catalog = resume_state.PROBLEMS_DIR / PROBLEM
    catalog.mkdir(parents=True, exist_ok=True)
    checkpoints = "\n".join(
        f"  {name}:\n    version: 1\n    order: {index}\n    state: Core Tests"
        for index, name in enumerate(names, 1)
    )
    (catalog / "config.yaml").write_text(
        "version: 1\n"
        f"name: {PROBLEM}\n"
        "description: test\n"
        "entry_file: app/main\n"
        "checkpoints:\n"
        + checkpoints
        + "\n",
        encoding="utf-8",
    )


def _identity(exp: str, **overrides) -> dict:
    state = {
        "version": 1,
        "phase": "completed",
        "experiment_id": exp,
        "arm": "baseline",
        "run_index": 1,
        "problem": PROBLEM,
        "agent": paths.DEFAULT_AGENT,
        "model": paths.DEFAULT_MODEL,
        "provider": paths.DEFAULT_PROVIDER,
        "thinking": paths.DEFAULT_THINKING,
    }
    state.update(overrides)
    return state


class FakeScb:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.commands: list[list[str]] = []
        self.environments: list[dict[str, str]] = []
        self.plan: list = []
        self._real = subprocess.run

    def run(self, cmd, **kwargs):
        cmd = list(cmd)
        if "benchmark.scb_main" not in cmd:
            return self._real(cmd, **kwargs)
        env = kwargs.get("env") or {}
        out_dir = Path(env.get("HB_RUN_OUTPUT", "/tmp"))
        outcome = self.plan.pop(0)
        is_resume = "--resume" in cmd
        self.commands.append(cmd)
        self.environments.append(dict(env))
        self.calls.append(("run", out_dir, is_resume))
        return SimpleNamespace(returncode=outcome(out_dir, is_resume))


@pytest.fixture
def fake(monkeypatch):
    f = FakeScb()
    monkeypatch.setattr(subprocess, "run", f.run)
    return f


@pytest.fixture
def results(tmp_path, monkeypatch):
    root = tmp_path / "results"
    monkeypatch.setattr(scb_run, "RESULTS_DIR", root)
    monkeypatch.setattr(resume_state, "RESULTS_DIR", root)
    monkeypatch.setattr(
        scb_run,
        "collect_run",
        staticmethod(lambda **kw: {"arm": "baseline", "problem": PROBLEM, "checkpoints": []}),
    )
    return root


@pytest.fixture(autouse=True)
def problem_catalog(tmp_path, monkeypatch):
    monkeypatch.setattr(resume_state, "PROBLEMS_DIR", tmp_path / "problems")


def test_native_resume_uses_problem_order_and_ignores_evaluation(tmp_path):
    pdir = tmp_path / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1", "checkpoint_2", "checkpoint_3")
    _mk_cp(
        pdir,
        "checkpoint_1",
        result=OK_RESULT,
        evaluation={"pass_counts": {"Core": 0}, "total_counts": {"Core": 1}},
    )
    info = resume_state.detect_native_resume(tmp_path, PROBLEM)
    assert info is not None
    assert info.completed_checkpoints == ["checkpoint_1"]
    assert info.resume_from_checkpoint == "checkpoint_2"
    assert info.invalidated_checkpoints == ["checkpoint_2", "checkpoint_3"]


def test_native_resume_uses_saved_prompt_and_environment(tmp_path, monkeypatch):
    pdir = tmp_path / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1")
    scb_dir = tmp_path / "scb"
    (scb_dir / "config.yaml").write_text(
        "prompt_content: saved prompt\n", encoding="utf-8"
    )
    (scb_dir / "environment.yaml").write_text(
        "type: local\nname: test\n", encoding="utf-8"
    )
    seen = {}

    def fake_detect(output_path, checkpoint_names, **kwargs):
        seen.update(kwargs)
        return None

    monkeypatch.setattr(resume_state, "detect_resume_point", fake_detect)
    assert resume_state.detect_native_resume(tmp_path, PROBLEM) is None
    assert seen["prompt_template"] == "saved prompt"
    assert seen["environment"].type == "local"
    assert seen["entry_file"] == "app/main"


def test_build_state_maps_native_statuses(tmp_path):
    pdir = tmp_path / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1", "checkpoint_2", "checkpoint_3")
    _mk_cp(pdir, "checkpoint_1", result=OK_RESULT)
    state = resume_state.build_state(
        output_dir=tmp_path,
        experiment_id="exp",
        arm="baseline",
        run_index=1,
        problem=PROBLEM,
        selection={"agent": "codex"},
        exit_code=0,
        phase="completed",
    )
    assert state["last_completed_checkpoint"] == "checkpoint_1"
    assert state["stopped_at_checkpoint"] == "checkpoint_2"
    assert state["checkpoints"] == {
        "checkpoint_1": "done",
        "checkpoint_2": "not_reached",
        "checkpoint_3": "incomplete",
    }
    assert state["fully_completed"] is False
    assert state["interrupt_reason"] == "stopped_by_policy"


def test_build_state_uses_effective_problem_root(tmp_path):
    pdir = tmp_path / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1", "checkpoint_2")
    _mk_cp(pdir, "checkpoint_1", result=OK_RESULT)
    staged_root = tmp_path / "staged"
    staged_problem = staged_root / PROBLEM
    staged_problem.mkdir(parents=True)
    (staged_problem / "config.yaml").write_text(
        "version: 1\n"
        f"name: {PROBLEM}\n"
        "description: test\n"
        "entry_file: app/main\n"
        "checkpoints:\n"
        "  checkpoint_1:\n"
        "    version: 1\n"
        "    order: 1\n"
        "    state: Core Tests\n",
        encoding="utf-8",
    )
    state = resume_state.build_state(
        output_dir=tmp_path,
        experiment_id="exp",
        arm="baseline",
        run_index=1,
        problem=PROBLEM,
        selection={},
        problems_path=staged_root,
    )
    assert state["fully_completed"] is True


def test_completed_native_resume_is_complete_even_with_red_evaluation(tmp_path):
    pdir = tmp_path / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1")
    _mk_cp(
        pdir,
        "checkpoint_1",
        result=OK_RESULT,
        evaluation={"pass_counts": {"Core": 0}, "total_counts": {"Core": 1}},
    )
    state = resume_state.build_state(
        output_dir=tmp_path,
        experiment_id="exp",
        arm="baseline",
        run_index=1,
        problem=PROBLEM,
        selection={},
        exit_code=0,
        phase="completed",
    )
    assert state["fully_completed"] is True
    assert state["interrupt_reason"] == "ok"


def test_state_contains_no_probe_or_derived_fields(tmp_path):
    state = resume_state.build_state(
        output_dir=tmp_path,
        experiment_id="exp",
        arm="baseline",
        run_index=1,
        problem=PROBLEM,
        selection={},
    )
    assert not {
        "resume_probe_exit_code",
        "probe_hint",
        "resumed_from",
        "will_rerun",
        "evaluation",
        "notes",
        "pending_resume_cmd",
        "max_rework_attempts",
    } & state.keys()


def test_clear_stale_artifacts_uses_native_invalidated_checkpoints(tmp_path):
    pdir = tmp_path / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1", "checkpoint_2")
    _mk_cp(pdir, "checkpoint_1", result=OK_RESULT)
    cp2 = _mk_cp(pdir, "checkpoint_2", snapshot=False)
    (cp2 / "rework.json").write_text("{}", encoding="utf-8")
    (cp2 / "evaluation.json").write_text("{}", encoding="utf-8")
    removed = resume_state.clear_stale_resume_artifacts(tmp_path, PROBLEM)
    assert sorted(Path(path).name for path in removed) == ["evaluation.json", "rework.json"]
    assert not (cp2 / "rework.json").exists()


def test_verify_selection_reports_mismatch():
    mismatches = resume_state.verify_selection_against_state(
        _identity("exp", model="gpt-x"),
        experiment_id="exp",
        arm="baseline",
        run_index=1,
        agent=paths.DEFAULT_AGENT,
        provider=None,
        model="other",
        thinking=None,
        problem=PROBLEM,
    )
    assert mismatches == ["model: run='gpt-x' requested='other'"]


def test_feedback_v1_normalizes_to_legacy_strategy():
    assert (
        scb_run._resolve_feedback_strategy("v1", None)
        == scb_run.LEGACY_FEEDBACK_STRATEGY
    )


def test_run_dirs_uses_run_suffixes(tmp_path):
    (tmp_path / "baseline" / "run_10").mkdir(parents=True)
    (tmp_path / "baseline" / "run_2").mkdir()
    assert [path.name for path in resume_state.run_dirs(tmp_path)] == ["run_2", "run_10"]


def _crash_step(out_dir: Path, _resume: bool) -> int:
    pdir = out_dir / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1", "checkpoint_2")
    _mk_cp(pdir, "checkpoint_1", result=OK_RESULT)
    _mk_cp(pdir, "checkpoint_2", snapshot=False)
    return 3


def _finish_step(out_dir: Path, _resume: bool) -> int:
    pdir = out_dir / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1", "checkpoint_2")
    _mk_cp(pdir, "checkpoint_1", result=OK_RESULT)
    _mk_cp(pdir, "checkpoint_2", result=OK_RESULT)
    return 0


def _fail_collect(**kwargs):
    raise RuntimeError("collect failed")


def test_crash_then_resume_runs_native_once_and_keeps_workspace(results, fake):
    fake.plan = [_crash_step]
    exp = "exp-crash"
    with pytest.raises(RuntimeError, match="slop-code run failed"):
        scb_run.run_one(arm="baseline", problem=PROBLEM, experiment_id=exp, rework_attempts=0)
    out = results / exp / "baseline" / "run_1"
    failed = resume_state.load_state(out)
    assert failed["phase"] == "failed"
    assert failed["exit_code"] == 3
    assert failed["interrupt_reason"] == "crashed"
    assert not any(call[2] is False and "dry-run" in str(call) for call in fake.calls)

    fake.plan = [_finish_step]
    scb_run.run_one(
        arm="baseline", problem=PROBLEM, experiment_id=exp, resume=True, rework_attempts=0
    )
    assert ("run", out, True) in fake.calls
    final = resume_state.load_state(out)
    assert final["phase"] == "completed"
    assert final["fully_completed"] is True


def test_resume_refuses_identity_mismatch(results):
    out = results / "exp-id" / "baseline" / "run_1"
    out.mkdir(parents=True)
    (out / "state.json").write_text(json.dumps(_identity("exp-id", model="gpt-x")), encoding="utf-8")
    with pytest.raises(ValueError, match="resume refused"):
        scb_run.run_one(arm="baseline", problem=PROBLEM, experiment_id="exp-id", resume=True, model="other")


def test_matrix_requires_experiment_id_for_resume(fake):
    with pytest.raises(ValueError, match="explicit --experiment-id"):
        scb_run.run_matrix(arms=("baseline",), runs=1, resume=True)


def test_matrix_resume_skips_finished_slot(results, fake):
    out = results / "exp-mx" / "baseline" / "run_1"
    pdir = out / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1")
    _mk_cp(pdir, "checkpoint_1", result=OK_RESULT)
    (out / "metrics").mkdir(parents=True)
    saved = {"arm": "baseline", "loaded": True}
    (out / "metrics" / "run.json").write_text(json.dumps(saved), encoding="utf-8")
    (out / "state.json").write_text(
        json.dumps(_identity("exp-mx", phase="completed", exit_code=0)), encoding="utf-8"
    )
    collected = scb_run.run_matrix(
        arms=("baseline",),
        problem=PROBLEM,
        runs=1,
        experiment_id="exp-mx",
        skip_smoke_check=True,
        resume=True,
    )
    assert collected == [saved]
    assert not fake.calls


def test_matrix_resume_starts_missing_slot_fresh(results, fake):
    out = results / "exp-grow" / "baseline" / "run_1"
    pdir = out / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1")
    _mk_cp(pdir, "checkpoint_1", result=OK_RESULT)
    (out / "metrics").mkdir(parents=True)
    (out / "metrics" / "run.json").write_text("{}", encoding="utf-8")
    (out / "state.json").write_text(
        json.dumps(_identity("exp-grow", phase="completed", exit_code=0)), encoding="utf-8"
    )
    fake.plan = [_finish_step]
    scb_run.run_matrix(
        arms=("baseline",),
        problem=PROBLEM,
        runs=2,
        experiment_id="exp-grow",
        skip_smoke_check=True,
        resume=True,
    )
    assert fake.calls == [("run", results / "exp-grow" / "baseline" / "run_2", False)]


def test_matrix_resume_ignores_unselected_arm_runs(results, fake):
    other_arm = results / "exp-arms" / "ponytail" / "run_3"
    other_arm.mkdir(parents=True)
    (other_arm / "state.json").write_text(
        json.dumps(_identity("exp-arms", arm="ponytail", run_index=3)),
        encoding="utf-8",
    )
    fake.plan = [_finish_step]
    scb_run.run_matrix(
        arms=("baseline",),
        problem=PROBLEM,
        runs=1,
        experiment_id="exp-arms",
        skip_smoke_check=True,
        resume=True,
    )
    assert fake.calls == [("run", results / "exp-arms" / "baseline" / "run_1", False)]


def test_matrix_resume_inherits_selection_for_missing_slot(results, fake):
    out = results / "exp-selection" / "baseline" / "run_1"
    pdir = out / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1")
    _mk_cp(pdir, "checkpoint_1", result=OK_RESULT)
    (out / "metrics").mkdir(parents=True)
    (out / "metrics" / "run.json").write_text("{}", encoding="utf-8")
    (out / "state.json").write_text(
        json.dumps(
            _identity(
                "exp-selection",
                model="gpt-x",
                provider="provider-x",
                thinking="high",
                rework_attempts=1,
                exit_code=0,
            )
        ),
        encoding="utf-8",
    )
    fake.plan = [_finish_step]
    scb_run.run_matrix(
        arms=("baseline",),
        problem=PROBLEM,
        runs=2,
        experiment_id="exp-selection",
        skip_smoke_check=True,
        resume=True,
    )
    command = fake.commands[-1]
    assert "provider-x/gpt-x" in command
    assert fake.environments[-1]["HB_REWORK_ATTEMPTS"] == "1"


def test_matrix_resume_inherits_selection_for_arm_without_previous_slot(results, fake):
    out = results / "exp-shared-selection" / "baseline" / "run_1"
    pdir = out / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1")
    _mk_cp(pdir, "checkpoint_1", result=OK_RESULT)
    (out / "metrics").mkdir(parents=True)
    (out / "metrics" / "run.json").write_text("{}", encoding="utf-8")
    (out / "state.json").write_text(
        json.dumps(
            _identity(
                "exp-shared-selection",
                model="gpt-x",
                provider="provider-x",
                thinking="high",
                rework_attempts=1,
                exit_code=0,
            )
        ),
        encoding="utf-8",
    )
    fake.plan = [_finish_step]
    scb_run.run_matrix(
        arms=("baseline", "ponytail"),
        problem=PROBLEM,
        runs=1,
        experiment_id="exp-shared-selection",
        skip_smoke_check=True,
        resume=True,
    )
    assert "provider-x/gpt-x" in fake.commands[-1]
    assert fake.environments[-1]["HB_REWORK_ATTEMPTS"] == "1"


def test_resume_restores_rework_attempts(results, fake):
    fake.plan = [_crash_step]
    exp = "exp-rework-settings"
    with pytest.raises(RuntimeError, match="slop-code run failed"):
        scb_run.run_one(
            arm="baseline",
            problem=PROBLEM,
            experiment_id=exp,
            rework_attempts=0,
        )
    state = resume_state.load_state(results / exp / "baseline" / "run_1")
    assert state["rework_attempts"] == 0

    fake.plan = [_finish_step]
    scb_run.run_one(arm="baseline", problem=PROBLEM, experiment_id=exp, resume=True)
    assert fake.environments[-1]["HB_REWORK_ATTEMPTS"] == "0"


def test_resume_restores_transient_and_feedback_settings(results, fake):
    fake.plan = [_crash_step]
    exp = "exp-transient-settings"
    with pytest.raises(RuntimeError, match="slop-code run failed"):
        scb_run.run_one(
            arm="baseline",
            problem=PROBLEM,
            experiment_id=exp,
            rework_attempts=0,
            transient_retries=1,
            feedback_strategy="all-failures",
        )
    state = resume_state.load_state(results / exp / "baseline" / "run_1")
    assert state["transient_retries"] == 1
    assert state["feedback_strategy"] == "all-failures"

    fake.plan = [_finish_step]
    scb_run.run_one(arm="baseline", problem=PROBLEM, experiment_id=exp, resume=True)
    assert fake.environments[-1]["HB_TRANSIENT_RETRIES"] == "1"


def test_resume_rejects_explicit_rework_change(results, fake):
    fake.plan = [_crash_step]
    exp = "exp-rework-mismatch"
    with pytest.raises(RuntimeError, match="slop-code run failed"):
        scb_run.run_one(
            arm="baseline",
            problem=PROBLEM,
            experiment_id=exp,
            rework_attempts=0,
        )
    with pytest.raises(ValueError, match="rework_attempts"):
        scb_run.run_one(
            arm="baseline",
            problem=PROBLEM,
            experiment_id=exp,
            resume=True,
            rework_attempts=1,
        )


def test_resume_rejects_explicit_transient_change(results, fake):
    fake.plan = [_crash_step]
    exp = "exp-transient-mismatch"
    with pytest.raises(RuntimeError, match="slop-code run failed"):
        scb_run.run_one(
            arm="baseline",
            problem=PROBLEM,
            experiment_id=exp,
            rework_attempts=0,
            transient_retries=1,
        )
    with pytest.raises(ValueError, match="transient_retries"):
        scb_run.run_one(
            arm="baseline",
            problem=PROBLEM,
            experiment_id=exp,
            resume=True,
            transient_retries=2,
        )


def test_resume_rejects_explicit_agent_conflict(results):
    out = results / "exp-agent" / "baseline" / "run_1"
    out.mkdir(parents=True)
    (out / "state.json").write_text(
        json.dumps(
            _identity(
                "exp-agent",
                agent="opencode",
                provider="opencode_auth",
                model="model-x",
                thinking="none",
            )
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="agent"):
        scb_run.run_one(
            arm="baseline",
            problem=PROBLEM,
            experiment_id="exp-agent",
            resume=True,
            agent="codex",
            provider="opencode_auth",
            model="model-x",
        )


def test_postprocessing_failure_marks_run_failed(results, fake, monkeypatch):
    fake.plan = [_finish_step]
    monkeypatch.setattr(scb_run, "collect_run", _fail_collect)
    with pytest.raises(RuntimeError, match="collect failed"):
        scb_run.run_one(arm="baseline", problem=PROBLEM, experiment_id="exp-post")
    state = resume_state.load_state(results / "exp-post" / "baseline" / "run_1")
    assert state["phase"] == "failed"
    assert state["exit_code"] == 0
    assert state["interrupt_reason"] == "crashed"


def test_matrix_resume_refuses_legacy_run(results, fake):
    (results / "exp-old" / "baseline" / "run_1" / "scb").mkdir(parents=True)
    with pytest.raises(ValueError, match="no state.json"):
        scb_run.run_matrix(
            arms=("baseline",),
            problem=PROBLEM,
            runs=1,
            experiment_id="exp-old",
            skip_smoke_check=True,
            resume=True,
        )


def test_matrix_resume_refuses_shrunk_runs(results, fake):
    for index in (1, 2):
        run_dir = results / "exp-shrink" / "baseline" / f"run_{index}"
        run_dir.mkdir(parents=True)
        (run_dir / "state.json").write_text(
            json.dumps(_identity("exp-shrink", run_index=index)), encoding="utf-8"
        )
    with pytest.raises(ValueError, match="--runs 2"):
        scb_run.run_matrix(
            arms=("baseline",),
            problem=PROBLEM,
            runs=1,
            experiment_id="exp-shrink",
            skip_smoke_check=True,
            resume=True,
        )


def test_fresh_matrix_appends_runs_without_overwriting_previous_slot(results, fake):
    fake.plan = [_finish_step, _finish_step]
    exp = "exp-append"
    scb_run.run_matrix(
        arms=("baseline",),
        problem=PROBLEM,
        runs=1,
        experiment_id=exp,
        skip_smoke_check=True,
    )
    first = results / exp / "baseline" / "run_1"
    first_state = resume_state.load_state(first)
    first_metrics = (first / "metrics" / "run.json").read_text(encoding="utf-8")

    scb_run.run_matrix(
        arms=("baseline",),
        problem=PROBLEM,
        runs=1,
        experiment_id=exp,
        skip_smoke_check=True,
    )

    assert fake.calls[-1] == ("run", results / exp / "baseline" / "run_2", False)
    assert resume_state.load_state(first) == first_state
    assert (first / "metrics" / "run.json").read_text(encoding="utf-8") == first_metrics


def test_fresh_matrix_rejects_different_selection_in_existing_experiment(results, fake):
    fake.plan = [_finish_step]
    exp = "exp-selection-guard"
    scb_run.run_matrix(
        arms=("baseline",),
        problem=PROBLEM,
        runs=1,
        experiment_id=exp,
        skip_smoke_check=True,
    )
    with pytest.raises(ValueError, match="different selection"):
        scb_run.run_matrix(
            arms=("baseline",),
            problem=PROBLEM,
            runs=1,
            experiment_id=exp,
            model="other-model",
            skip_smoke_check=True,
        )


def _interrupt_step(out_dir: Path, _resume: bool) -> int:
    pdir = out_dir / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1", "checkpoint_2")
    _mk_cp(pdir, "checkpoint_1", result=OK_RESULT)
    raise KeyboardInterrupt


def test_keyboard_interrupt_marks_interrupted_then_resume_completes(results, fake):
    fake.plan = [_interrupt_step]
    exp = "exp-int"
    with pytest.raises(KeyboardInterrupt):
        scb_run.run_one(arm="baseline", problem=PROBLEM, experiment_id=exp, rework_attempts=0)
    out = results / exp / "baseline" / "run_1"
    state = resume_state.load_state(out)
    assert state["phase"] == "interrupted"
    assert state["interrupt_reason"] == "interrupted"
    assert state["exit_code"] is None
    assert state["last_completed_checkpoint"] == "checkpoint_1"

    fake.plan = [_finish_step]
    scb_run.run_one(
        arm="baseline", problem=PROBLEM, experiment_id=exp, resume=True, rework_attempts=0
    )
    final = resume_state.load_state(out)
    assert final["phase"] == "completed"
    assert final["fully_completed"] is True


def test_cli_resume_without_flags_restores_recorded_selection(results, fake):
    runner = CliRunner()
    exp = "exp-cli"
    out = results / exp / "baseline" / "run_1"
    pdir = out / "scb" / PROBLEM
    _declare(pdir, "checkpoint_1", "checkpoint_2")
    _mk_cp(pdir, "checkpoint_1", result=OK_RESULT)
    (out / "state.json").write_text(
        json.dumps(_identity(exp, phase="started", model="gpt-x")), encoding="utf-8"
    )
    fake.plan = [_finish_step]
    result = runner.invoke(
        app,
        [
            "run",
            "--arm",
            "baseline",
            "--problem",
            PROBLEM,
            "--experiment-id",
            exp,
            "--resume",
            "--skip-smoke-check",
        ],
    )
    assert result.exit_code == 0, result.output
    assert ("run", out, True) in fake.calls
    final = resume_state.load_state(out)
    assert final["phase"] == "completed"
    assert final["model"] == "gpt-x"


def test_cli_resume_with_explicit_mismatch_refuses(results):
    runner = CliRunner()
    exp = "exp-cli-bad"
    out = results / exp / "baseline" / "run_1"
    out.mkdir(parents=True)
    (out / "state.json").write_text(json.dumps(_identity(exp, model="gpt-x")), encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "run",
            "--arm",
            "baseline",
            "--problem",
            PROBLEM,
            "--experiment-id",
            exp,
            "--resume",
            "--model",
            "other",
        ],
    )
    assert result.exit_code != 0
    assert "resume refused" in result.output


def test_cli_run_all_resume_guard_has_no_traceback(monkeypatch):
    runner = CliRunner()

    def raise_guard(**kwargs):
        raise ValueError("--resume guard")

    monkeypatch.setattr("benchmark.cli.run_matrix", raise_guard)
    result = runner.invoke(
        app,
        [
            "run-all",
            "--arms",
            "baseline",
            "--experiment-id",
            "exp-cli-guard",
            "--runs",
            "1",
            "--resume",
            "--skip-smoke-check",
        ],
    )
    assert result.exit_code == 1
    assert "--resume guard" in result.output
    assert "Traceback" not in result.output

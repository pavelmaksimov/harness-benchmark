from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import monitor_benchmark as monitor


def _config(tmp_path: Path, *, max_restarts: int = 2) -> monitor.MonitorConfig:
    return monitor.MonitorConfig(
        experiment_id="exp-monitor",
        problem="file_backup",
        arms=("baseline",),
        runs=1,
        jobs=1,
        agent="codex",
        provider="codex_auth",
        model="gpt-5.6-luna",
        thinking="max",
        rework_attempts=2,
        skip_smoke_check=True,
        interval=0.01,
        restart_delay=0,
        max_restarts=max_restarts,
        orphan_timeout=0.01,
        log_path=tmp_path / "monitor.log",
    )


def _write_state(config: monitor.MonitorConfig, *, complete: bool) -> None:
    run_dir = monitor.RESULTS_DIR / config.experiment_id / "baseline" / "run_1"
    (run_dir / "metrics").mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps(
            {
                "experiment_id": config.experiment_id,
                "arm": "baseline",
                "run_index": 1,
                "problem": config.problem,
                "phase": "completed" if complete else "failed",
                "exit_code": 0 if complete else 3,
                "fully_completed": complete,
                "interrupt_reason": "ok" if complete else "crashed",
            }
        ),
        encoding="utf-8",
    )
    if complete:
        (run_dir / "metrics" / "run.json").write_text("{}", encoding="utf-8")


def test_resume_command_omits_selection_flags() -> None:
    config = _config(Path("/tmp"))

    fresh = monitor._benchmark_command(config, resume=False)
    resumed = monitor._benchmark_command(config, resume=True)

    assert "--resume" not in fresh
    assert "--rework-attempts" in fresh
    assert "--resume" in resumed
    assert "--rework-attempts" not in resumed
    assert "--model" not in resumed


def test_monitor_resumes_after_child_failure(tmp_path, monkeypatch) -> None:
    results_dir = tmp_path / "results"
    monkeypatch.setattr(monitor, "RESULTS_DIR", results_dir)
    config = _config(tmp_path)
    commands: list[list[str]] = []
    outcomes = [
        (3, lambda: _write_state(config, complete=False)),
        (0, lambda: _write_state(config, complete=True)),
    ]

    class FakePopen:
        _next_pid = 500_000

        def __init__(self, command, **_kwargs):
            commands.append(list(command))
            return_code, write_result = outcomes.pop(0)
            write_result()
            self.pid = FakePopen._next_pid
            FakePopen._next_pid += 1
            self.returncode = return_code

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            return self.returncode

    monkeypatch.setattr(monitor.subprocess, "Popen", FakePopen)

    assert monitor.run_monitor(config) == 0
    assert len(commands) == 2
    assert "--resume" not in commands[0]
    assert "--resume" in commands[1]
    assert monitor._is_complete(config, "baseline", 1)


def test_monitor_does_not_start_completed_experiment(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(monitor, "RESULTS_DIR", tmp_path / "results")
    config = _config(tmp_path, max_restarts=0)
    _write_state(config, complete=True)
    called = SimpleNamespace(value=False)

    def fail_if_started(*_args, **_kwargs):
        called.value = True
        raise AssertionError("completed experiment must not start another child")

    monkeypatch.setattr(monitor.subprocess, "Popen", fail_if_started)

    assert monitor.run_monitor(config) == 0
    assert called.value is False
    result = json.loads((monitor.RESULTS_DIR / config.experiment_id / ".monitor-result.json").read_text())
    assert result["status"] == "complete"


def test_monitor_maps_orphan_container_to_infer_workspace(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(monitor, "RESULTS_DIR", tmp_path / "results")
    config = _config(tmp_path)
    workspace = tmp_path / "temporary-workspace"
    workspace.mkdir()
    infer_log = (
        monitor.RESULTS_DIR
        / config.experiment_id
        / "baseline"
        / "run_1"
        / "scb"
        / config.problem
        / "checkpoint_1"
        / "infer.log"
    )
    infer_log.parent.mkdir(parents=True)
    infer_log.write_text(f"Workspace prepared working_dir={workspace}\n", encoding="utf-8")

    def fake_docker_output(arguments) -> str:
        if arguments[0] == "ps":
            return "container-id\n"
        return json.dumps(
            [
                {
                    "Name": "/benchmark-agent",
                    "Mounts": [{"Source": str(workspace), "Destination": "/workspace"}],
                }
            ]
        )

    monkeypatch.setattr(monitor, "_docker_output", fake_docker_output)

    containers = monitor._matching_docker_containers(config)

    assert [container.name for container in containers] == ["benchmark-agent"]
    assert containers[0].source == str(workspace)


def test_monitor_persists_human_required_after_restart_budget(tmp_path, monkeypatch) -> None:
    results_dir = tmp_path / "results"
    monkeypatch.setattr(monitor, "RESULTS_DIR", results_dir)
    config = _config(tmp_path, max_restarts=1)
    commands: list[list[str]] = []

    class FailedPopen:
        _next_pid = 510_000

        def __init__(self, command, **_kwargs):
            commands.append(list(command))
            _write_state(config, complete=False)
            self.pid = FailedPopen._next_pid
            FailedPopen._next_pid += 1
            self.returncode = 3

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            return self.returncode

    monkeypatch.setattr(monitor.subprocess, "Popen", FailedPopen)

    assert monitor.run_monitor(config) == 3
    result = json.loads((results_dir / config.experiment_id / ".monitor-result.json").read_text())
    assert result["status"] == "needs-human"
    assert result["return_code"] == 3
    assert len(commands) == 2

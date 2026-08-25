"""Keep a benchmark matrix running by resuming interrupted attempts."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.arms import DEFAULT_EXPERIMENT_ARMS, known_arm_names
from benchmark.paths import (
    DEFAULT_PROBLEM,
    DEFAULT_RUNS,
    RESULTS_DIR,
)


@dataclass(frozen=True)
class MonitorConfig:
    """Configuration for one unattended run-all supervisor."""

    experiment_id: str
    problem: str
    arms: tuple[str, ...]
    runs: int
    jobs: int
    agent: str | None
    provider: str | None
    model: str | None
    thinking: str | None
    rework_attempts: int | None
    skip_smoke_check: bool
    interval: float
    restart_delay: float
    max_restarts: int
    orphan_timeout: float
    log_path: Path
    transient_retries: int | None = None
    feedback_strategy: str | None = None
    desired_fingerprint: str | None = None


@dataclass(frozen=True)
class ProcessInfo:
    """A benchmark process discovered through /proc."""

    pid: int
    args: tuple[str, ...]

    @property
    def command(self) -> str:
        return " ".join(self.args)


@dataclass(frozen=True)
class DockerInfo:
    """A persistent agent container mapped to one benchmark workspace."""

    container_id: str
    name: str
    source: str

    @property
    def description(self) -> str:
        return f"{self.name} ({self.container_id[:12]}, source={self.source})"


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _log(path: Path, message: str) -> None:
    """Write a flushed message both to the terminal and the monitor log."""
    line = f"[{_timestamp()}] {message}"
    print(line, flush=True)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
    except OSError as exc:
        print(f"[{_timestamp()}] cannot write monitor log {path}: {exc}", flush=True)


def _monitor_result_path(config: MonitorConfig) -> Path:
    return RESULTS_DIR / config.experiment_id / ".monitor-result.json"


def _write_monitor_result(config: MonitorConfig, *, status: str, return_code: int, reason: str) -> None:
    path = _monitor_result_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(
            {
                "status": status,
                "return_code": return_code,
                "reason": reason,
                "experiment_id": config.experiment_id,
                "desired_fingerprint": config.desired_fingerprint,
                "updated_at": _timestamp(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _read_json_dict(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _run_dir(config: MonitorConfig, arm: str, run_index: int) -> Path:
    return RESULTS_DIR / config.experiment_id / arm / f"run_{run_index}"


def _is_complete(config: MonitorConfig, arm: str, run_index: int) -> bool:
    run_dir = _run_dir(config, arm, run_index)
    state = _read_json_dict(run_dir / "state.json")
    if state is None:
        return False
    identity = {
        "experiment_id": config.experiment_id,
        "arm": arm,
        "run_index": run_index,
        "problem": config.problem,
    }
    if any(state.get(field) != value for field, value in identity.items()):
        return False
    if (
        state.get("phase") != "completed"
        or state.get("exit_code") != 0
        or state.get("fully_completed") is not True
    ):
        return False
    return _read_json_dict(run_dir / "metrics" / "run.json") is not None


def _completion_status(config: MonitorConfig) -> tuple[int, int, list[str]]:
    """Return completed slots, total slots, and a short pending explanation."""
    completed = 0
    total = len(config.arms) * config.runs
    pending: list[str] = []
    for arm in config.arms:
        for run_index in range(1, config.runs + 1):
            if _is_complete(config, arm, run_index):
                completed += 1
                continue
            run_dir = _run_dir(config, arm, run_index)
            state = _read_json_dict(run_dir / "state.json")
            if state is None:
                reason = "no state.json"
            else:
                reason = f"phase={state.get('phase', '?')} stop={state.get('interrupt_reason', '?')}"
            pending.append(f"{arm}/run_{run_index}: {reason}")
    return completed, total, pending


def _has_recorded_state(config: MonitorConfig) -> bool:
    """Whether this experiment has a resumable run in one of the selected arms."""
    for arm in config.arms:
        arm_dir = RESULTS_DIR / config.experiment_id / arm
        if not arm_dir.is_dir():
            continue
        for run_dir in arm_dir.glob("run_*"):
            if run_dir.is_dir() and _read_json_dict(run_dir / "state.json") is not None:
                return True
    return False


def _benchmark_command(config: MonitorConfig, *, resume: bool) -> list[str]:
    """Build the exact child command, omitting immutable selection on resume."""
    command = [
        sys.executable,
        "-m",
        "benchmark",
        "run-all",
        "--experiment-id",
        config.experiment_id,
        "--problem",
        config.problem,
        "--arms",
        ",".join(config.arms),
        "--runs",
        str(config.runs),
        "--jobs",
        str(config.jobs),
    ]
    if not resume:
        for flag, value in (
            ("--agent", config.agent),
            ("--provider", config.provider),
            ("--model", config.model),
            ("--thinking", config.thinking),
        ):
            if value is not None:
                command.extend([flag, value])
        if config.rework_attempts is not None:
            command.extend(["--rework-attempts", str(config.rework_attempts)])
        if config.transient_retries is not None:
            command.extend(["--transient-retries", str(config.transient_retries)])
        if config.feedback_strategy is not None:
            command.extend(["--feedback-strategy", config.feedback_strategy])
    if config.skip_smoke_check:
        command.append("--skip-smoke-check")
    if resume:
        command.append("--resume")
    return command


def _read_process_args(pid_dir: Path) -> tuple[str, ...] | None:
    try:
        raw = (pid_dir / "cmdline").read_bytes()
    except OSError:
        return None
    return tuple(part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part)


def _is_benchmark_command(args: Sequence[str]) -> bool:
    if any("benchmark.scb_main" in arg for arg in args):
        return True
    return any(
        args[index] == "-m"
        and index + 1 < len(args)
        and args[index + 1] == "benchmark"
        for index in range(len(args))
    )


def _mentions_experiment(args: Sequence[str], experiment_id: str) -> bool:
    return any(
        argument == experiment_id
        or argument == f"--experiment-id={experiment_id}"
        or f"/{experiment_id}/" in argument
        or argument.endswith(f"/{experiment_id}")
        for argument in args
    )


def _matching_processes(experiment_id: str) -> list[ProcessInfo]:
    """Find this experiment's benchmark processes, including SCB workers."""
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return []
    matches: list[ProcessInfo] = []
    for pid_dir in proc_root.iterdir():
        if not pid_dir.name.isdigit():
            continue
        pid = int(pid_dir.name)
        if pid == os.getpid():
            continue
        args = _read_process_args(pid_dir)
        if args and _is_benchmark_command(args) and _mentions_experiment(args, experiment_id):
            matches.append(ProcessInfo(pid=pid, args=args))
    return matches


def _workspace_paths(config: MonitorConfig) -> set[str]:
    """Read temporary agent workspace paths from flushed infer logs."""
    paths: set[str] = set()
    experiment_dir = RESULTS_DIR / config.experiment_id
    for infer_log in experiment_dir.glob("**/infer.log"):
        try:
            text = infer_log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in re.finditer(
            r"""working_dir(?:["']?\s*[:=]\s*["']?)(/[^"'\s,})]+)""",
            text,
        ):
            paths.add(match.group(1))
    return paths


def _docker_output(arguments: Sequence[str]) -> str | None:
    """Run a read-only Docker query without making Docker a hard dependency."""
    try:
        result = subprocess.run(
            ["docker", *arguments],
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def _same_path(left: str, right: str) -> bool:
    try:
        return Path(left).resolve() == Path(right).resolve()
    except (OSError, RuntimeError):
        return left == right


def _matching_docker_containers(config: MonitorConfig) -> list[DockerInfo]:
    """Find running containers whose /workspace mount belongs to this experiment."""
    workspace_paths = _workspace_paths(config)
    if not workspace_paths:
        return []
    listed = _docker_output(("ps", "-q", "--no-trunc"))
    if not listed:
        return []

    matches: list[DockerInfo] = []
    for container_id in listed.splitlines():
        inspected = _docker_output(("inspect", container_id.strip()))
        if not inspected:
            continue
        try:
            documents = json.loads(inspected)
        except json.JSONDecodeError:
            continue
        if not isinstance(documents, list):
            continue
        for document in documents:
            if not isinstance(document, dict):
                continue
            name = str(document.get("Name") or container_id).lstrip("/")
            mounts = document.get("Mounts") or []
            if not isinstance(mounts, list):
                continue
            for mount in mounts:
                if not isinstance(mount, dict):
                    continue
                source = mount.get("Source")
                if (
                    mount.get("Destination") == "/workspace"
                    and isinstance(source, str)
                    and any(_same_path(source, path) for path in workspace_paths)
                ):
                    matches.append(
                        DockerInfo(
                            container_id=container_id.strip(),
                            name=name,
                            source=source,
                        )
                    )
                    break
    return matches


def _process_group_exists(process_group: int | None) -> bool:
    if process_group is None or process_group == os.getpgrp():
        return False
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _signal_processes(processes: Sequence[ProcessInfo], signum: int) -> None:
    for process in processes:
        if process.pid == os.getpid():
            continue
        try:
            os.kill(process.pid, signum)
        except (ProcessLookupError, PermissionError):
            pass


def _terminate_orphans(
    *,
    process_group: int | None,
    processes: Sequence[ProcessInfo],
    containers: Sequence[DockerInfo],
    log_path: Path,
) -> None:
    """Stop only processes identified as belonging to this monitor's run."""
    _log(log_path, "stale benchmark processes detected; sending SIGTERM before resume")
    if process_group is not None and process_group != os.getpgrp():
        try:
            os.killpg(process_group, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    _signal_processes(processes, signal.SIGTERM)
    for container in containers:
        _log(log_path, f"stopping orphan Docker container {container.description}")
        try:
            subprocess.run(
                ["docker", "stop", "--time", "1", container.container_id],
                capture_output=True,
                check=False,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if not _process_group_exists(process_group) and not _matching_processes_from(processes):
            return
        time.sleep(0.5)

    _log(log_path, "SIGTERM did not clear all stale processes; sending SIGKILL")
    if process_group is not None and process_group != os.getpgrp():
        try:
            os.killpg(process_group, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    _signal_processes(processes, signal.SIGKILL)


def _matching_processes_from(previous: Sequence[ProcessInfo]) -> list[ProcessInfo]:
    """Keep only still-live pids from a previously identified orphan set."""
    live: list[ProcessInfo] = []
    for process in previous:
        try:
            os.kill(process.pid, 0)
        except (ProcessLookupError, PermissionError):
            continue
        live.append(process)
    return live


def _activity_mtime(config: MonitorConfig) -> float:
    latest = 0.0
    experiment_dir = RESULTS_DIR / config.experiment_id
    for pattern in ("**/state.json", "**/infer.log", "**/scb_run.log", "**/run_info.yaml"):
        for path in experiment_dir.glob(pattern):
            try:
                latest = max(latest, path.stat().st_mtime)
            except OSError:
                continue
    return latest


def _wait_for_quiescence(
    config: MonitorConfig,
    *,
    process_group: int | None,
    log_path: Path,
) -> None:
    """Do not launch a resume while the old process tree is still alive."""
    poll_interval = min(config.interval, 300.0)
    deadline = time.monotonic() + config.orphan_timeout
    activity_mtime = _activity_mtime(config)
    warned = False
    while True:
        processes = _matching_processes(config.experiment_id)
        containers = _matching_docker_containers(config)
        group_alive = _process_group_exists(process_group)
        if not group_alive and not processes and not containers:
            return
        current_activity = _activity_mtime(config)
        if current_activity > activity_mtime:
            activity_mtime = current_activity
            deadline = time.monotonic() + config.orphan_timeout
            if warned:
                _log(log_path, "benchmark process tree is active; extending orphan grace period")
        if not warned:
            details = ", ".join(f"{item.pid}: {item.command}" for item in processes[:3])
            if containers:
                container_details = ", ".join(item.description for item in containers[:3])
                details = ", ".join(item for item in (details, container_details) if item)
            suffix = f" ({details})" if details else ""
            _log(log_path, f"waiting for old benchmark process tree to exit{suffix}")
            warned = True
        if time.monotonic() >= deadline:
            _terminate_orphans(
                process_group=process_group,
                processes=processes,
                containers=containers,
                log_path=log_path,
            )
            remaining = _matching_processes(config.experiment_id)
            remaining_containers = _matching_docker_containers(config)
            if _process_group_exists(process_group) or remaining or remaining_containers:
                raise RuntimeError(
                    "refusing to resume while stale benchmark processes remain: "
                    + ", ".join(
                        [
                            *(str(item.pid) for item in remaining),
                            *(item.name for item in remaining_containers),
                        ]
                    )
                )
            return
        time.sleep(min(poll_interval, max(0.1, deadline - time.monotonic())))


def _pending_summary(config: MonitorConfig) -> str:
    completed, total, pending = _completion_status(config)
    details = "; ".join(pending[:4])
    if len(pending) > 4:
        details += f"; +{len(pending) - 4} more"
    return f"{completed}/{total} slots complete" + (f"; pending: {details}" if details else "")


def _wait_for_child(
    process: subprocess.Popen[bytes],
    config: MonitorConfig,
    log_path: Path,
) -> int:
    """Wait with a heartbeat, then wait for escaped descendants as well."""
    poll_interval = min(config.interval, 300.0)
    try:
        while process.poll() is None:
            _log(
                log_path,
                f"heartbeat: {_pending_summary(config)}; "
                f"experiment processes={len(_matching_processes(config.experiment_id))}",
            )
            try:
                process.wait(timeout=poll_interval)
            except subprocess.TimeoutExpired:
                continue
    except KeyboardInterrupt:
        _log(log_path, "monitor interrupted; stopping its benchmark process group")
        _terminate_orphans(
            process_group=process.pid,
            processes=_matching_processes(config.experiment_id),
            containers=_matching_docker_containers(config),
            log_path=log_path,
        )
        raise

    return_code = process.wait()
    _wait_for_quiescence(config, process_group=process.pid, log_path=log_path)
    return return_code


@contextmanager
def _monitor_lock(path: Path) -> Iterator[None]:
    """Prevent two supervisors from resuming the same experiment concurrently."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another monitor already owns {path}") from exc
        stream.seek(0)
        stream.truncate()
        stream.write(f"pid={os.getpid()} started={_timestamp()}\n")
        stream.flush()
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def run_monitor(config: MonitorConfig) -> int:
    """Run until every requested slot is complete or the retry budget is spent."""
    experiment_dir = RESULTS_DIR / config.experiment_id
    lock_path = experiment_dir / ".monitor.lock"
    with _monitor_lock(lock_path):
        def finish(status: str, return_code: int, reason: str) -> int:
            _write_monitor_result(config, status=status, return_code=return_code, reason=reason)
            return return_code

        _log(
            config.log_path,
            f"monitor started: experiment={config.experiment_id} "
            f"arms={','.join(config.arms)} runs={config.runs} jobs={config.jobs} "
            f"rework_attempts={config.rework_attempts if config.rework_attempts is not None else 2}",
        )
        if _completion_status(config)[0] == len(config.arms) * config.runs:
            _log(config.log_path, "all requested slots are already complete; nothing to run")
            return finish("complete", 0, "all requested slots are complete")

        _wait_for_quiescence(config, process_group=None, log_path=config.log_path)
        restarts = 0
        attempt = 0
        while True:
            completed, total, _ = _completion_status(config)
            if completed == total:
                _log(config.log_path, "benchmark complete")
                return finish("complete", 0, "all requested slots are complete")

            _wait_for_quiescence(config, process_group=None, log_path=config.log_path)
            resume = _has_recorded_state(config)
            command = _benchmark_command(config, resume=resume)
            attempt += 1
            attempt_log = config.log_path.with_name(
                f"{config.log_path.stem}.attempt-{attempt:03d}{config.log_path.suffix or '.log'}"
            )
            _log(
                config.log_path,
                f"starting attempt {attempt} ({'resume' if resume else 'fresh'}): "
                + " ".join(command),
            )
            return_code: int
            try:
                environment = os.environ.copy()
                environment["PYTHONUNBUFFERED"] = "1"
                with attempt_log.open("ab") as output:
                    process = subprocess.Popen(
                        command,
                        cwd=str(REPO_ROOT),
                        env=environment,
                        stdout=output,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )
                return_code = _wait_for_child(process, config, config.log_path)
            except KeyboardInterrupt:
                return 130
            except OSError as exc:
                _log(config.log_path, f"attempt {attempt} could not run safely: {exc}")
                return_code = 127

            completed, total, _ = _completion_status(config)
            _log(
                config.log_path,
                f"attempt {attempt} ended with exit={return_code}; "
                f"{completed}/{total} slots complete",
            )
            if completed == total:
                _log(config.log_path, "benchmark complete")
                return finish("complete", 0, "all requested slots are complete")
            if config.max_restarts and restarts >= config.max_restarts:
                _log(
                    config.log_path,
                    f"restart limit reached ({config.max_restarts}); "
                    f"leaving incomplete results for manual triage",
                )
                return finish(
                    "needs-human",
                    return_code or 1,
                    f"restart limit reached ({config.max_restarts}); incomplete results require triage",
                )

            restarts += 1
            next_mode = "resume" if _has_recorded_state(config) else "fresh"
            _log(
                config.log_path,
                f"will retry in {config.restart_delay:g}s ({next_mode}); "
                f"restarts used={restarts}",
            )
            time.sleep(config.restart_delay)


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return parsed


def _parse_arms(value: str) -> tuple[str, ...]:
    arms = tuple(item.strip() for item in value.split(",") if item.strip())
    if not arms:
        raise argparse.ArgumentTypeError("at least one arm is required")
    if len(set(arms)) != len(arms):
        raise argparse.ArgumentTypeError("an arm may appear only once")
    unknown = sorted(set(arms) - set(known_arm_names()))
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown arm(s): {', '.join(unknown)}")
    return arms


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run benchmark run-all and resume it after process-level failures."
    )
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--problem", default=DEFAULT_PROBLEM)
    parser.add_argument(
        "--arms",
        type=_parse_arms,
        default=DEFAULT_EXPERIMENT_ARMS,
        help="comma-separated arms (default: all registered arms)",
    )
    parser.add_argument("--runs", type=_non_negative_int, default=DEFAULT_RUNS)
    parser.add_argument("--jobs", type=_non_negative_int, default=1)
    parser.add_argument("--agent", default=None, choices=("codex", "opencode"))
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--thinking", default=None)
    parser.add_argument("--rework-attempts", type=_non_negative_int, default=None)
    parser.add_argument("--transient-retries", type=_non_negative_int, default=None)
    parser.add_argument("--feedback-strategy", default=None)
    parser.add_argument("--desired-fingerprint", default=None)
    parser.add_argument("--skip-smoke-check", action="store_true")
    parser.add_argument(
        "--interval",
        type=_positive_float,
        default=60.0,
        help="heartbeat and process-tree polling interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--restart-delay",
        type=_non_negative_float,
        default=30.0,
        help="delay before a resume attempt (default: 30)",
    )
    parser.add_argument(
        "--max-restarts",
        type=_non_negative_int,
        default=3,
        help="number of retries after the first attempt; 0 means unlimited",
    )
    parser.add_argument(
        "--orphan-timeout",
        type=_positive_float,
        default=300.0,
        help="seconds to wait for escaped benchmark processes before killing them",
    )
    parser.add_argument("--log", type=Path, default=None, help="monitor log path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs must be >= 1")
    if args.jobs < 1:
        parser.error("--jobs must be >= 1")
    if args.experiment_id in {".", ".."} or Path(args.experiment_id).name != args.experiment_id:
        parser.error("--experiment-id must be a single safe path component")

    log_path = args.log.expanduser() if args.log else RESULTS_DIR / args.experiment_id / "monitor.log"
    if not log_path.is_absolute():
        log_path = (Path.cwd() / log_path).resolve()
    config = MonitorConfig(
        experiment_id=args.experiment_id,
        problem=args.problem,
        arms=tuple(args.arms),
        runs=args.runs,
        jobs=args.jobs,
        agent=args.agent,
        provider=args.provider,
        model=args.model,
        thinking=args.thinking,
        rework_attempts=args.rework_attempts,
        skip_smoke_check=args.skip_smoke_check,
        interval=args.interval,
        restart_delay=args.restart_delay,
        max_restarts=args.max_restarts,
        orphan_timeout=args.orphan_timeout,
        log_path=log_path,
        transient_retries=args.transient_retries,
        feedback_strategy=args.feedback_strategy,
        desired_fingerprint=args.desired_fingerprint,
    )
    try:
        return run_monitor(config)
    except KeyboardInterrupt:
        _log(config.log_path, "monitor interrupted")
        return 130
    except RuntimeError as exc:
        _log(config.log_path, f"monitor stopped: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

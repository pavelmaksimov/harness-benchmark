"""Repair mode: fix a failed checkpoint's snapshot and continue the run.

Flow (one ``repair`` invocation):

1. Locate the run dir and the SCB problem dir for an experiment.
2. Find the first failed checkpoint (Core failures, no infra error).
3. Record the failure into ``failures/<problem>.json`` with model/harness/agent
   metadata (see ``benchmark/failures.py``).
4. Fix the failed checkpoint's snapshot:
   - ``--fix-snapshot <dir>``: copy a provided fixed snapshot over it, or
   - ``--fixer-agent opencode``: run the OpenCode CLI on the snapshot with a
     fix prompt (loop until the offline re-score passes or attempts run out).
5. Verify the fixed snapshot offline: pytest against the problem's test files
   ``test_checkpoint_1..N.py`` with ``PYTHONPATH=<snapshot>``.
6. Resume the SCB run with ``run --resume <run_1/scb>`` — SCB detects the last
   completed checkpoint and continues from the next one using the (fixed)
   snapshot as the starting workspace.
7. Re-collect metrics and rewrite the manifest after the resumed run finishes.

``--no-resume`` stops after recording + fixing + verifying (no SCB run).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmark.failures import record_failure
from benchmark.paths import PROBLEMS_DIR, REPO_ROOT, RESULTS_DIR

CHECKPOINT_RE = re.compile(r"^checkpoint_(\d+)$")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _run_dir(experiment_id: str, arm: str, run_index: int) -> Path:
    return RESULTS_DIR / experiment_id / arm / f"run_{run_index}"


def _scb_problem_dir(run_dir: Path, problem: str) -> Path:
    candidate = run_dir / "scb" / problem
    if candidate.exists():
        return candidate
    matches = list((run_dir / "scb").rglob(problem))
    for match in matches:
        if match.is_dir() and (match / "checkpoint_1").exists():
            return match
    raise FileNotFoundError(
        f"Could not find SCB problem dir for {problem!r} under {run_dir / 'scb'}"
    )


def _checkpoint_number(name: str) -> int:
    match = CHECKPOINT_RE.match(name)
    if not match:
        raise ValueError(f"unexpected checkpoint dir name: {name!r}")
    return int(match.group(1))


def find_failed_checkpoint(
    scb_problem_dir: Path,
) -> tuple[str, dict[str, Any]] | None:
    """Return (checkpoint_name, evaluation) for the first failed checkpoint.

    A checkpoint counts as failed when its evaluation.json shows Core failures
    (or an infra failure) and it is not merely absent.  Traversal is in
    checkpoint-number order; later checkpoints are unreachable once an
    earlier one stopped the trajectory.
    """
    checkpoints = sorted(
        (
            p
            for p in scb_problem_dir.iterdir()
            if p.is_dir() and CHECKPOINT_RE.match(p.name)
        ),
        key=lambda p: _checkpoint_number(p.name),
    )
    for cp_dir in checkpoints:
        evaluation = _read_json(cp_dir / "evaluation.json")
        if evaluation is None:
            continue
        pass_counts = evaluation.get("pass_counts") or {}
        total_counts = evaluation.get("total_counts") or {}
        core_passed = int(pass_counts.get("Core") or 0)
        core_total = int(total_counts.get("Core") or 0)
        infra = bool(evaluation.get("infrastructure_failure"))
        if infra or (core_total > 0 and core_passed < core_total):
            return cp_dir.name, evaluation
    return None


def _failed_test_names(evaluation: dict[str, Any]) -> list[str]:
    """Collect failed test node names from the per-bucket tests dict."""
    tests = evaluation.get("tests") or {}
    failed: list[str] = []
    for bucket in tests.values():
        failed.extend(bucket.get("failed") or [])
    return failed


def load_manifest(run_dir: Path) -> dict[str, Any]:
    manifest = _read_json(run_dir / "manifest.json") or {}
    return manifest


def build_failure_entry(
    *,
    experiment_id: str,
    arm: str,
    run_index: int,
    problem: str,
    checkpoint: str,
    evaluation: dict[str, Any],
    run_dir: Path,
    scb_problem_dir: Path,
    root_cause: str | None = None,
    fix: str | None = None,
) -> dict[str, Any]:
    """Build a failure entry carrying model/harness/agent metadata."""
    manifest = load_manifest(run_dir)
    model_settings = manifest.get("model_settings") or {}
    return {
        "date": datetime.now(timezone.utc).isoformat(),
        "experiment_id": experiment_id,
        "arm": arm,
        "harness": arm,
        "agent": manifest.get("agent"),
        "agent_version": manifest.get("agent_version"),
        "provider": model_settings.get("provider"),
        "model": manifest.get("model"),
        "thinking": model_settings.get("thinking"),
        "problem": problem,
        "checkpoint": checkpoint,
        "run_index": run_index,
        "pass_counts": evaluation.get("pass_counts"),
        "total_counts": evaluation.get("total_counts"),
        "failed_tests": _failed_test_names(evaluation),
        "infrastructure_failure": bool(evaluation.get("infrastructure_failure")),
        "root_cause": root_cause,
        "fix": fix,
        "post_fix_score": None,
        "resumed": False,
        "paths": {
            "run_dir": str(run_dir),
            "scb_problem_dir": str(scb_problem_dir),
            "snapshot_dir": str(scb_problem_dir / checkpoint / "snapshot"),
        },
    }


def verify_snapshot(
    *,
    snapshot_dir: Path,
    problem: str,
    checkpoint: str,
    problems_dir: Path = PROBLEMS_DIR,
    venv_python: Path | None = None,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    """Offline re-score of a snapshot against test files checkpoint_1..N.

    Runs the same pytest entrypoint/checkpoint args the SCB evaluator uses,
    with ``PYTHONPATH=<snapshot>`` so the app resolves to the fixed code.
    Returns ``{passed, failed, exit_code, command}``.
    """
    cp_num = _checkpoint_number(checkpoint)
    tests_dir = problems_dir / problem / "tests"
    test_files = [
        tests_dir / f"test_checkpoint_{i}.py" for i in range(1, cp_num + 1)
    ]
    missing = [str(p) for p in test_files if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"missing test files for verification: {', '.join(missing)}"
        )

    python = venv_python or (REPO_ROOT / ".venv" / "bin" / "python")
    entrypoint = "uv run task_manager/main.py"
    cmd = [
        str(python),
        "-m",
        "pytest",
        *(str(p) for p in test_files),
        "--entrypoint",
        entrypoint,
        "--checkpoint",
        checkpoint,
        "-q",
        "-p",
        "no:cacheprovider",
        "--tb=no",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in [str(snapshot_dir), env.get("PYTHONPATH", "")] if p
    )
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    passed = failed = 0
    for line in proc.stdout.splitlines()[-5:]:
        match = re.search(r"(\d+) passed", line)
        if match:
            passed = int(match.group(1))
        match = re.search(r"(\d+) failed", line)
        if match:
            failed = int(match.group(1))
    return {
        "passed": passed,
        "failed": failed,
        "exit_code": proc.returncode,
        "command": " ".join(cmd),
        "stdout_tail": "\n".join(proc.stdout.splitlines()[-5:]),
        "stderr_tail": "\n".join(proc.stderr.splitlines()[-5:]),
    }


def replace_snapshot(
    *,
    scb_problem_dir: Path,
    checkpoint: str,
    fixed_snapshot_dir: Path,
    run_dir: Path,
) -> Path:
    """Back up the failed checkpoint's snapshot and copy the fixed one over.

    Returns the backup path.
    """
    cp_dir = scb_problem_dir / checkpoint
    snapshot_dir = cp_dir / "snapshot"
    backup_dir = (
        run_dir / "repair" / checkpoint / "snapshot.orig"
    )
    if snapshot_dir.exists():
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(snapshot_dir, backup_dir)
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    shutil.copytree(fixed_snapshot_dir, snapshot_dir)
    return backup_dir


def run_fixer_agent(
    *,
    snapshot_dir: Path,
    problem: str,
    checkpoint: str,
    model: str,
    attempts: int = 1,
) -> bool:
    """Run the OpenCode CLI on the snapshot to fix the failing tests.

    The agent edits code in place under ``snapshot_dir``; the caller verifies
    with ``verify_snapshot`` afterwards.  Returns True if the agent exited 0.
    """
    problems_dir = PROBLEMS_DIR / problem
    spec_path = problems_dir / f"{checkpoint}.md"
    spec = spec_path.read_text(encoding="utf-8") if spec_path.exists() else ""
    prompt = (
        "Fix the failing checkpoint in this task_manager solution. "
        f"Checkpoint spec:\n{spec}\n\n"
        "Edit the code in this workspace (task_manager/) so the failing tests "
        "pass while keeping the already-passing behavior intact. "
        "Do not change the project layout. Verify with the provided test suite "
        "if possible."
    )
    cmd = [
        "opencode",
        "run",
        "-m",
        model,
        "--dir",
        str(snapshot_dir),
        "--dangerously-skip-permissions",
        prompt,
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(snapshot_dir),
        check=False,
        capture_output=True,
        text=True,
        timeout=3600,
    )
    return proc.returncode == 0


def _resume_env(run_dir: Path, arm: str) -> dict[str, str]:
    env = os.environ.copy()
    env["SCBENCH_PROBLEMS_PATH"] = str(PROBLEMS_DIR)
    env["SCBENCH_HOME"] = str(run_dir / ".scbench_home")
    env["HB_ARM"] = arm
    env["HB_RUN_OUTPUT"] = str(run_dir)
    env["PYTHONPATH"] = os.pathsep.join(
        p
        for p in [
            str(REPO_ROOT / "harness_sitecustomize"),
            str(REPO_ROOT),
            env.get("PYTHONPATH", ""),
        ]
        if p
    )
    docker_config_dir = run_dir / ".docker"
    if docker_config_dir.is_dir():
        env["DOCKER_CONFIG"] = str(docker_config_dir)
    return env


def resume_scb_run(
    *,
    run_dir: Path,
    arm: str,
    dry_run: bool = False,
) -> Path:
    """Invoke SCB ``run --resume <run_dir/scb>`` and return the log path."""
    scb_root = run_dir / "scb"
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "benchmark.scb_main",
        "run",
        "--resume",
        str(scb_root),
    ]
    if dry_run:
        cmd.append("--dry-run")
    env = _resume_env(run_dir, arm)
    log_path = run_dir / "repair" / "resume.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            check=False,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
    (run_dir / "repair" / "resume_exit_code.txt").write_text(
        str(proc.returncode), encoding="utf-8"
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"SCB resume failed (exit {proc.returncode}); see {log_path}"
        )
    return log_path


def re_collect_run(
    *,
    run_dir: Path,
    arm: str,
    problem: str,
    experiment_id: str,
) -> None:
    """Re-collect metrics + manifest after a resumed run finished."""
    from benchmark.collect import collect_run, write_checkpoint_jsons
    from benchmark.manifest import build_manifest, write_manifest
    from benchmark.versions import load_pins

    scb_problem_dir = _scb_problem_dir(run_dir, problem)
    pins = load_pins()
    run_id = f"{experiment_id}-{arm}-r-resumed"
    environment = {
        "agent": "opencode",
        "agent_version": pins.get("opencode_cli_version"),
        "provider": None,
        "model": None,
        "thinking": None,
        "slop_code_commit": pins.get("slop-code-bench"),
        "problems_commit": pins.get("scb-problems"),
        "harness_meta": None,
        "ponytail_commit": None,
        "harness": arm,
        "docker_image": "ghcr.io/astral-sh/uv:python3.12-trixie-slim",
    }
    collected = collect_run(
        scb_problem_dir=scb_problem_dir,
        run_id=run_id,
        arm=arm,
        problem=problem,
        environment=environment,
        pricing_path=REPO_ROOT / "configs" / "pricing.yaml",
    )
    metrics_dir = run_dir / "metrics"
    write_checkpoint_jsons(collected, metrics_dir)
    (metrics_dir / "run.json").write_text(
        json.dumps(collected, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    # Preserve the original manifest, tagging the run as repaired/resumed.
    manifest = load_manifest(run_dir)
    extra = dict(manifest.get("extra") or {})
    extra["repaired"] = True
    extra["repaired_at"] = datetime.now(timezone.utc).isoformat()
    extra["run_id"] = run_id
    manifest["extra"] = extra
    write_manifest(run_dir / "manifest.json", manifest)


def repair_run(
    *,
    experiment_id: str,
    arm: str,
    run_index: int = 1,
    problem: str | None = None,
    fix_snapshot_dir: Path | None = None,
    fixer_agent: str | None = None,
    fixer_model: str | None = None,
    root_cause: str | None = None,
    fix: str | None = None,
    no_resume: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Orchestrate record → fix → verify → resume for one run."""
    run_dir = _run_dir(experiment_id, arm, run_index)
    if not run_dir.exists():
        raise FileNotFoundError(f"run dir not found: {run_dir}")

    manifest = load_manifest(run_dir)
    problem = problem or manifest.get("problem")
    if not problem:
        raise ValueError("problem not given and not found in manifest.json")

    scb_problem_dir = _scb_problem_dir(run_dir, problem)
    failed = find_failed_checkpoint(scb_problem_dir)
    if failed is None:
        return {"status": "no-failure", "problem": problem}

    checkpoint, evaluation = failed
    entry = build_failure_entry(
        experiment_id=experiment_id,
        arm=arm,
        run_index=run_index,
        problem=problem,
        checkpoint=checkpoint,
        evaluation=evaluation,
        run_dir=run_dir,
        scb_problem_dir=scb_problem_dir,
        root_cause=root_cause,
        fix=fix,
    )
    failures_path = record_failure(problem, entry)
    result: dict[str, Any] = {
        "status": "recorded",
        "problem": problem,
        "checkpoint": checkpoint,
        "failures_path": str(failures_path),
    }

    # --- Fix -----------------------------------------------------------------
    snapshot_dir = scb_problem_dir / checkpoint / "snapshot"
    fixed_dir: Path | None = None
    if fix_snapshot_dir is not None:
        if not fix_snapshot_dir.is_dir():
            raise FileNotFoundError(f"fixed snapshot dir not found: {fix_snapshot_dir}")
        fixed_dir = fix_snapshot_dir
    elif fixer_agent == "opencode":
        if not fixer_model:
            raise ValueError("--fixer-agent opencode requires --fixer-model")
        ok = run_fixer_agent(
            snapshot_dir=snapshot_dir,
            problem=problem,
            checkpoint=checkpoint,
            model=fixer_model,
        )
        if not ok:
            return {**result, "status": "fixer-failed"}
        fixed_dir = snapshot_dir
    else:
        # Record-only mode (no fix requested).
        return result

    if not dry_run:
        backup = replace_snapshot(
            scb_problem_dir=scb_problem_dir,
            checkpoint=checkpoint,
            fixed_snapshot_dir=fixed_dir,
            run_dir=run_dir,
        )
        result["backup_dir"] = str(backup)

        # --- Verify ----------------------------------------------------------
        verification = verify_snapshot(
            snapshot_dir=snapshot_dir,
            problem=problem,
            checkpoint=checkpoint,
        )
        result["verification"] = verification
        post_fix_score = (
            f"{verification['passed']}/{verification['passed'] + verification['failed']}"
            if verification["passed"] + verification["failed"] > 0
            else "0/0"
        )
        entry["post_fix_score"] = post_fix_score
        record_failure(problem, entry)

        if verification["failed"] > 0 or verification["exit_code"] != 0:
            return {**result, "status": "verify-failed"}

        if no_resume:
            return {**result, "status": "fixed", "post_fix_score": post_fix_score}

        # --- Resume ----------------------------------------------------------
        log_path = resume_scb_run(run_dir=run_dir, arm=arm, dry_run=False)
        result["resume_log"] = str(log_path)
        entry["resumed"] = True
        record_failure(problem, entry)

        re_collect_run(
            run_dir=run_dir,
            arm=arm,
            problem=problem,
            experiment_id=experiment_id,
        )
        return {**result, "status": "resumed", "post_fix_score": post_fix_score}

    return {**result, "status": "dry-run"}
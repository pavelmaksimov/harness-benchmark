"""Offline problem readiness checks (no Docker / Codex)."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from benchmark.arms import DEFAULT_EXPERIMENT_ARMS, get_arm, known_arm_names
from benchmark.paths import DEFAULT_PROBLEM, PROBLEMS_DIR, REPO_ROOT
from benchmark.smoke import is_smoke_validated, load_smoke_marker, stage_cp1_only_problem
from benchmark.structure import EXCLUDE_DIR_NAMES

SYNC_SCRIPT = REPO_ROOT / "scripts" / "sync_task_manager_problem.sh"
TRACKED_TASK_MANAGER = REPO_ROOT / "problems" / "task_manager"
VENDOR_FILE_BACKUP = PROBLEMS_DIR / "file_backup"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class ValidateReport:
    problem: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def as_dict(self) -> dict[str, Any]:
        return {
            "problem": self.problem,
            "ok": self.ok,
            "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in self.checks],
            "default_problem": DEFAULT_PROBLEM,
            "exclude_dir_names": sorted(EXCLUDE_DIR_NAMES),
        }


def ensure_task_manager_synced() -> CheckResult:
    if not TRACKED_TASK_MANAGER.is_dir():
        return CheckResult("tracked_tree", False, f"missing {TRACKED_TASK_MANAGER}")
    linked = PROBLEMS_DIR / "task_manager"
    if linked.is_symlink() and linked.resolve() == TRACKED_TASK_MANAGER.resolve():
        return CheckResult("sync_symlink", True, f"{linked} -> {TRACKED_TASK_MANAGER}")
    if not SYNC_SCRIPT.is_file():
        return CheckResult("sync_symlink", False, f"missing {SYNC_SCRIPT}")
    proc = subprocess.run(
        ["bash", str(SYNC_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return CheckResult(
            "sync_symlink",
            False,
            f"sync failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}",
        )
    if not linked.exists():
        return CheckResult("sync_symlink", False, f"still missing after sync: {linked}")
    return CheckResult("sync_symlink", True, (proc.stdout or "").strip() or str(linked))


def _load_checkpoints(problem_dir: Path) -> dict[str, Any]:
    raw = yaml.safe_load((problem_dir / "config.yaml").read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("invalid config.yaml")
    checkpoints = raw.get("checkpoints")
    if not isinstance(checkpoints, dict):
        raise ValueError("checkpoints missing")
    return checkpoints


def check_full_catalog(problem: str) -> CheckResult:
    problem_dir = PROBLEMS_DIR / problem
    if not problem_dir.is_dir():
        return CheckResult("catalog_present", False, f"missing {problem_dir}")
    try:
        checkpoints = _load_checkpoints(problem_dir)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return CheckResult("catalog_config", False, str(exc))
    ordered = sorted(
        checkpoints.items(),
        key=lambda item: int(item[1].get("order", 0)) if isinstance(item[1], dict) else 0,
    )
    names = [name for name, _ in ordered]
    if problem == "task_manager":
        expected = [f"checkpoint_{i}" for i in range(1, 16)]
        if names != expected:
            return CheckResult(
                "checkpoint_order",
                False,
                f"expected {expected}, got {names}",
            )
        prior_ok = all(
            isinstance(cfg, dict) and cfg.get("include_prior_tests", True)
            for name, cfg in ordered
            if name != "checkpoint_1"
        )
        if not prior_ok:
            return CheckResult(
                "include_prior_tests",
                False,
                "CP2+ must keep include_prior_tests enabled",
            )
        return CheckResult(
            "checkpoint_order",
            True,
            f"{len(names)} checkpoints in order; CP2+ include_prior_tests ok",
        )
    return CheckResult("catalog_config", True, f"{len(names)} checkpoints: {', '.join(names)}")


def check_cp1_staging(problem: str) -> CheckResult:
    with tempfile.TemporaryDirectory(prefix="hb-validate-") as tmp:
        staged_root = stage_cp1_only_problem(problem=problem, dest_root=Path(tmp))
        staged = staged_root / problem
        checkpoints = _load_checkpoints(staged)
        if list(checkpoints.keys()) != ["checkpoint_1"]:
            return CheckResult(
                "cp1_stage",
                False,
                f"staged checkpoints={list(checkpoints.keys())}",
            )
        return CheckResult("cp1_stage", True, f"staged only checkpoint_1 under {staged}")


def check_smoke_gates() -> CheckResult:
    details: list[str] = []
    for arm in known_arm_names():
        spec = get_arm(arm)
        ok = is_smoke_validated(arm)
        if not spec.needs_hook:
            details.append(f"{arm}: baseline (no smoke required)")
            continue
        marker = load_smoke_marker(arm) or {}
        kind = "grandfathered" if marker.get("grandfathered") else "live"
        details.append(f"{arm}: validated={ok} ({kind})")
        if not ok:
            return CheckResult("smoke_markers", False, "; ".join(details))
    # ADR comparison arms: baseline + ponytail
    for arm in DEFAULT_EXPERIMENT_ARMS:
        if not is_smoke_validated(arm):
            return CheckResult(
                "smoke_markers",
                False,
                f"experiment arm {arm} not smoke-validated",
            )
    return CheckResult(
        "smoke_markers",
        True,
        "no skill content changed for task_manager; existing markers valid. "
        + "; ".join(details),
    )


def check_file_backup_untouched() -> CheckResult:
    if DEFAULT_PROBLEM != "file_backup":
        return CheckResult(
            "file_backup_default",
            False,
            f"DEFAULT_PROBLEM={DEFAULT_PROBLEM!r}, expected 'file_backup'",
        )
    if not VENDOR_FILE_BACKUP.is_dir():
        return CheckResult("file_backup_present", False, f"missing {VENDOR_FILE_BACKUP}")
    # Symlink-only addition under vendor/scb-problems must not alter file_backup files.
    proc = subprocess.run(
        ["git", "-C", str(PROBLEMS_DIR), "status", "--porcelain", "file_backup"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return CheckResult(
            "file_backup_git",
            False,
            proc.stderr.strip() or f"git status exit {proc.returncode}",
        )
    dirty = proc.stdout.strip()
    if dirty:
        return CheckResult("file_backup_git", False, f"dirty:\n{dirty}")
    return CheckResult(
        "file_backup_untouched",
        True,
        f"DEFAULT_PROBLEM={DEFAULT_PROBLEM}; vendor file_backup clean",
    )


def check_exclude_policy() -> CheckResult:
    if "tests" in EXCLUDE_DIR_NAMES:
        return CheckResult("exclude_policy", False, "tests must not be excluded")
    if "snapshot" in EXCLUDE_DIR_NAMES:
        return CheckResult("exclude_policy", False, "snapshot parent segment must not be excluded")
    return CheckResult(
        "exclude_policy",
        True,
        "leaf excludes=" + ",".join(sorted(EXCLUDE_DIR_NAMES)),
    )


def validate_problem(problem: str, *, sync: bool = True) -> ValidateReport:
    report = ValidateReport(problem=problem)
    if problem == "task_manager" and sync:
        report.checks.append(ensure_task_manager_synced())
    report.checks.append(check_full_catalog(problem))
    if report.checks[-1].ok:
        report.checks.append(check_cp1_staging(problem))
    report.checks.append(check_smoke_gates())
    report.checks.append(check_file_backup_untouched())
    report.checks.append(check_exclude_policy())
    return report

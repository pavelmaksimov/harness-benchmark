"""CP1 smoke validation for new harness arms before full benchmark runs."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import yaml

from benchmark.arms import get_arm
from benchmark.paths import HARNESSES_DIR, PROBLEMS_DIR
from benchmark.structure import EXCLUDE_DIR_NAMES
from benchmark.versions import load_arm_meta

SMOKE_MARKER = "SMOKE.json"
SMOKE_CHECKPOINT = "checkpoint_1"


def smoke_marker_path(arm: str) -> Path:
    return HARNESSES_DIR / arm / SMOKE_MARKER


def harness_content_sha(arm: str) -> str | None:
    """Pin content fingerprint used to invalidate stale smoke markers."""
    meta = load_arm_meta(arm) or {}
    sha = meta.get("tree_sha256") or meta.get("skill_sha256")
    return sha if isinstance(sha, str) and sha else None


def load_smoke_marker(arm: str) -> dict[str, Any] | None:
    path = smoke_marker_path(arm)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def is_smoke_validated(arm: str) -> bool:
    """True if arm has a valid CP1 smoke marker matching current harness content."""
    spec = get_arm(arm)
    if not spec.needs_hook:
        return True
    marker = load_smoke_marker(arm)
    if not marker or not marker.get("ok"):
        return False
    expected = harness_content_sha(arm)
    recorded = marker.get("harness_content_sha")
    if expected and recorded and expected != recorded:
        return False
    checkpoints = marker.get("checkpoints") or []
    if SMOKE_CHECKPOINT not in checkpoints and marker.get("grandfathered"):
        # Pre-gate arms may lack a real CP1 list; still require content match when present.
        return True
    return SMOKE_CHECKPOINT in checkpoints or bool(marker.get("grandfathered"))


def arms_missing_smoke(arms: Sequence[str]) -> list[str]:
    missing: list[str] = []
    for arm in arms:
        get_arm(arm)
        if not is_smoke_validated(arm):
            missing.append(arm)
    return missing


def require_smoke_validated(arms: Sequence[str], *, skip: bool = False) -> None:
    """Raise before a full run if any skill arm lacks CP1 smoke validation."""
    if skip:
        return
    missing = arms_missing_smoke(arms)
    if not missing:
        return
    examples = ", ".join(missing)
    cmds = "\n".join(f"  uv run python -m benchmark smoke --arm {arm}" for arm in missing)
    raise RuntimeError(
        f"Refusing full benchmark: harness(es) missing CP1 smoke validation: {examples}.\n"
        f"Run a one-checkpoint smoke first (discovers extra files / verifies the arm works):\n"
        f"{cmds}\n"
        f"Then update EXCLUDE_DIR_NAMES if needed. Override only if intentional: --skip-smoke-check."
    )


def stage_cp1_only_problem(
    *,
    problem: str,
    dest_root: Path,
    checkpoint_count: int = 1,
) -> Path:
    """Copy problem catalog keeping only the first ``checkpoint_count`` checkpoints (no vendor/ touch).

    ``checkpoint_count=1`` is the classic CP1-only smoke used for the SMOKE.json gate;
    larger values validate a harness over several early checkpoints (e.g. CP1+CP2).
    """
    src = PROBLEMS_DIR / problem
    if not src.is_dir():
        raise FileNotFoundError(f"Problem not found: {src}")
    if checkpoint_count < 1:
        raise ValueError("checkpoint_count must be >= 1")
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / problem
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

    config_path = dest / "config.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid problem config: {config_path}")
    checkpoints = raw.get("checkpoints")
    if not isinstance(checkpoints, dict) or SMOKE_CHECKPOINT not in checkpoints:
        raise ValueError(f"{problem} has no {SMOKE_CHECKPOINT} in config.yaml")

    def _order(item: tuple[str, Any]) -> tuple[Any, str]:
        spec = item[1]
        order = spec.get("order") if isinstance(spec, dict) else None
        return (order if isinstance(order, int) else 10**9, item[0])

    selected = sorted(checkpoints.items(), key=_order)[:checkpoint_count]
    names = [name for name, _ in selected]
    if SMOKE_CHECKPOINT not in names:
        raise ValueError(
            f"{problem}: staged set {names} must include {SMOKE_CHECKPOINT}"
        )
    raw["checkpoints"] = {name: checkpoints[name] for name in names}
    config_path.write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return dest_root


def _top_level_snapshot_entries(snapshot_dir: Path) -> list[str]:
    if not snapshot_dir.is_dir():
        return []
    return sorted(p.name for p in snapshot_dir.iterdir())


def analyze_smoke_snapshot(snapshot_dir: Path) -> dict[str, Any]:
    """Classify top-level snapshot entries vs current EXCLUDE_DIR_NAMES."""
    top = _top_level_snapshot_entries(snapshot_dir)
    dirs = [name for name in top if (snapshot_dir / name).is_dir()]
    already_excluded = sorted(name for name in dirs if name in EXCLUDE_DIR_NAMES)
    # Heuristic: dirs that look like tooling / caches, not typical solution packages.
    suspicious_prefixes = (".",)
    suspicious_names = {
        "node_modules",
        "dist",
        "build",
        "coverage",
        "htmlcov",
        "vendor",
        "out",
        "output",
        "artifacts",
        "reports",
        "tmp",
        "temp",
        "cache",
        ".cache",
    }
    needs_review = []
    for name in dirs:
        if name in EXCLUDE_DIR_NAMES:
            continue
        if name.startswith(suspicious_prefixes) or name in suspicious_names or "-" in name:
            # Hyphenated top-level dirs are often tool dumps (e.g. graphify-out).
            needs_review.append(name)
    return {
        "top_level": top,
        "top_level_dirs": dirs,
        "already_excluded": already_excluded,
        "needs_exclude_review": sorted(needs_review),
    }


def write_smoke_marker(
    arm: str,
    *,
    problem: str,
    experiment_id: str,
    run_dir: Path,
    ok: bool,
    activation_verified: bool | None,
    snapshot_analysis: dict[str, Any] | None,
    extra: dict[str, Any] | None = None,
) -> Path:
    path = smoke_marker_path(arm)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "arm": arm,
        "ok": ok,
        "problem": problem,
        "checkpoints": [SMOKE_CHECKPOINT],
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "experiment_id": experiment_id,
        "run_dir": str(run_dir),
        "harness_content_sha": harness_content_sha(arm),
        "harness_activation_verified": activation_verified,
        "snapshot": snapshot_analysis or {},
        "exclude_dir_names": sorted(EXCLUDE_DIR_NAMES),
    }
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_grandfathered_smoke(arm: str, *, note: str) -> Path:
    """Mark a pre-existing arm as smoke-ok without a live CP1 run."""
    path = smoke_marker_path(arm)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "arm": arm,
        "ok": True,
        "grandfathered": True,
        "note": note,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "harness_content_sha": harness_content_sha(arm),
        "checkpoints": [SMOKE_CHECKPOINT],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path

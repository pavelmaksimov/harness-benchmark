from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from benchmark.cost import load_pricing, normalized_cost_usd
from benchmark.dependencies import collect_dependencies, dependency_delta
from benchmark.isolation import verify_baseline_prompt, verify_skill_prompt
from benchmark.paths import ACTIVATION_MARKER, CONFIGS_DIR
from benchmark.rework import rework_stats
from benchmark.structure import analyze_snapshot, path_is_excluded
from benchmark.versions import load_arm_meta, load_pins

CHECKPOINT_RE = re.compile(r"checkpoint_(\d+)$")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _token_field(usage: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        if key in usage and usage[key] is not None:
            return int(usage[key])
    tokens = usage.get("net_tokens") or usage.get("current_tokens") or {}
    if isinstance(tokens, dict):
        for key in keys:
            if key in tokens and tokens[key] is not None:
                return int(tokens[key])
            # TokenUsage uses input/output/cache_read/...
            alias = {
                "input_tokens": "input",
                "output_tokens": "output",
                "cache_read_tokens": "cache_read",
                "cache_write_tokens": "cache_write",
                "reasoning_tokens": "reasoning",
            }.get(key)
            if alias and alias in tokens and tokens[alias] is not None:
                return int(tokens[alias])
    return None


def _group_counts(evaluation: dict[str, Any] | None, group: str) -> tuple[int | None, int | None]:
    if not evaluation:
        return None, None
    passed = (evaluation.get("pass_counts") or {}).get(group)
    total = (evaluation.get("total_counts") or {}).get(group)
    if passed is None and total is None:
        return None, None
    passed_i = int(passed or 0)
    total_i = int(total or 0)
    failed_i = max(total_i - passed_i, 0)
    return passed_i, failed_i


def _attempt_usage(attempt: dict[str, Any]) -> dict[str, Any]:
    usage = attempt.get("usage")
    return usage if isinstance(usage, dict) else attempt


def _sum_attempt_tokens(attempts: list[dict[str, Any]], *keys: str) -> int | None:
    values: list[int] = []
    for attempt in attempts:
        value = _token_field(_attempt_usage(attempt), *keys)
        if value is not None:
            values.append(value)
    return sum(values) if values else None


def _stage_token_usage(
    rework: dict[str, Any] | None,
    checkpoint_usage: dict[str, int | None],
) -> dict[str, int | None]:
    """Split input/output tokens between the initial solve and rework calls."""
    if not rework:
        return {
            "creation_input_tokens": checkpoint_usage.get("input_tokens"),
            "creation_output_tokens": checkpoint_usage.get("output_tokens"),
            "rework_input_tokens": 0,
            "rework_output_tokens": 0,
        }

    attempts = [attempt for attempt in (rework.get("attempts") or []) if isinstance(attempt, dict)]
    initial = attempts[:1]
    additional = attempts[1:]
    creation_input = _sum_attempt_tokens(initial, "input_tokens", "input")
    creation_output = _sum_attempt_tokens(initial, "output_tokens", "output")
    rework_input = _sum_attempt_tokens(additional, "input_tokens", "input")
    rework_output = _sum_attempt_tokens(additional, "output_tokens", "output")
    if rework_input is None and creation_input is not None:
        total = checkpoint_usage.get("input_tokens")
        if total is not None and total >= creation_input:
            rework_input = total - creation_input
    if rework_output is None and creation_output is not None:
        total = checkpoint_usage.get("output_tokens")
        if total is not None and total >= creation_output:
            rework_output = total - creation_output
    return {
        "creation_input_tokens": creation_input,
        "creation_output_tokens": creation_output,
        "rework_input_tokens": rework_input,
        "rework_output_tokens": rework_output,
    }


def _diff_metrics(diff: dict[str, Any] | None) -> dict[str, Any]:
    empty = {
        "files_added": None,
        "files_deleted": None,
        "files_modified": None,
        "files_touched": None,
        "lines_added": None,
        "lines_deleted": None,
        "lines_changed": None,
    }
    if not diff:
        return empty

    file_diffs = diff.get("file_diffs") or {}
    added = deleted = modified = 0
    lines_added = 0
    lines_deleted = 0
    counted_any = False

    for relpath, meta in file_diffs.items():
        if path_is_excluded(relpath):
            continue
        if not isinstance(meta, dict):
            continue
        counted_any = True
        change = (meta.get("change_type") or meta.get("status") or "").lower()
        if change in {"created", "added", "filechangetype.created"}:
            added += 1
        elif change in {"deleted", "removed", "filechangetype.deleted"}:
            deleted += 1
        else:
            modified += 1
        lines_added += int(meta.get("lines_added") or meta.get("added") or 0)
        lines_deleted += int(meta.get("lines_removed") or meta.get("lines_deleted") or meta.get("removed") or 0)

    # Prefer SCB totals only when we did not filter any paths (no per-file list,
    # or every listed path counted). Otherwise totals would include harness junk
    # (.git, graphify-out, …).
    if not file_diffs:
        if "total_added" in diff:
            lines_added = int(diff.get("total_added") or 0)
        if "total_removed" in diff:
            lines_deleted = int(diff.get("total_removed") or 0)
    elif not counted_any and ("total_added" in diff or "total_removed" in diff):
        # All files were excluded — report zeros for change metrics, not raw totals.
        lines_added = 0
        lines_deleted = 0

    touched = added + deleted + modified
    return {
        "files_added": added,
        "files_deleted": deleted,
        "files_modified": modified,
        "files_touched": touched,
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "lines_changed": lines_added + lines_deleted,
    }


def _checkpoint_prompt_text(checkpoint_dir: Path) -> str:
    """Prompt text of a checkpoint.

    Codex adapters save ``agent/prompt.txt``; OpenCode saves ``prompt.txt`` at the
    checkpoint root. Accept both so skill-arm activation checks work for every agent.
    """
    for candidate in (checkpoint_dir / "agent" / "prompt.txt", checkpoint_dir / "prompt.txt"):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return ""


def _activation_status(arm: str, checkpoint_dir: Path) -> dict[str, Any]:
    prompt_text = _checkpoint_prompt_text(checkpoint_dir)
    marker_path = checkpoint_dir / "agent" / ACTIVATION_MARKER
    marker = _read_json(marker_path) if marker_path.exists() else None

    if arm == "baseline":
        isolated = verify_baseline_prompt(prompt_text) and marker is None
        return {
            "harness_activation_verified": isolated,
            "baseline_isolation_verified": isolated,
            "prompt_has_skill_activation": "activate and follow the installed codex skill"
            in prompt_text.lower(),
            "marker_present": marker is not None,
            "marker": marker,
        }

    prompt_ok = verify_skill_prompt(arm, prompt_text)
    marker_ok = bool(marker and marker.get("harness_activation_verified"))
    return {
        "harness_activation_verified": bool(prompt_ok and marker_ok),
        "prompt_ok": prompt_ok,
        "marker_present": marker is not None,
        "marker": marker,
    }


def discover_checkpoint_dirs(problem_dir: Path) -> list[Path]:
    dirs = [p for p in problem_dir.iterdir() if p.is_dir() and CHECKPOINT_RE.match(p.name)]
    return sorted(dirs, key=lambda p: int(CHECKPOINT_RE.match(p.name).group(1)))  # type: ignore[union-attr]


def collect_checkpoint_record(
    *,
    run_id: str,
    arm: str,
    problem: str,
    checkpoint_dir: Path,
    environment: dict[str, Any],
    pricing: dict[str, Any],
    prev_deps: set[str] | None,
) -> tuple[dict[str, Any], set[str]]:
    match = CHECKPOINT_RE.match(checkpoint_dir.name)
    checkpoint_num = int(match.group(1)) if match else None

    inference = _read_json(checkpoint_dir / "inference_result.json") or {}
    evaluation = _read_json(checkpoint_dir / "evaluation.json")
    diff = _read_json(checkpoint_dir / "diff.json")
    usage_raw = inference.get("usage") or {}

    input_tokens = _token_field(usage_raw, "input_tokens", "input")
    output_tokens = _token_field(usage_raw, "output_tokens", "output")
    cache_read = _token_field(usage_raw, "cache_read_tokens", "cache_read")
    cache_write = _token_field(usage_raw, "cache_write_tokens", "cache_write")
    reasoning = _token_field(usage_raw, "reasoning_tokens", "reasoning")
    steps = usage_raw.get("steps")
    reported_cost = usage_raw.get("cost")
    if reported_cost is not None:
        reported_cost = float(reported_cost)

    model_name = environment.get("model")
    norm_cost = normalized_cost_usd(
        model=str(model_name),
        pricing=pricing,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_write_tokens=cache_write,
        reasoning_tokens=reasoning,
    )

    core_p, core_f = _group_counts(evaluation, "Core")
    func_p, func_f = _group_counts(evaluation, "Functionality")
    err_p, err_f = _group_counts(evaluation, "Error")
    reg_p, reg_f = _group_counts(evaluation, "Regression")
    core_total = core_p + core_f if core_p is not None and core_f is not None else None
    func_total = func_p + func_f if func_p is not None and func_f is not None else None
    err_total = err_p + err_f if err_p is not None and err_f is not None else None
    reg_total = reg_p + reg_f if reg_p is not None and reg_f is not None else None

    tests_passed = None
    tests_failed = None
    tests_total = None
    if evaluation:
        pass_counts = evaluation.get("pass_counts") or {}
        total_counts = evaluation.get("total_counts") or {}
        tests_passed = int(sum(int(v) for v in pass_counts.values()))
        tests_total = int(sum(int(v) for v in total_counts.values()))
        tests_failed = max(tests_total - tests_passed, 0)

    checkpoint_success = None
    if evaluation is not None and core_p is not None and core_f is not None:
        checkpoint_success = core_f == 0 and (core_p + core_f) > 0

    snapshot_dir = checkpoint_dir / "snapshot"
    code_metrics = analyze_snapshot(snapshot_dir)
    deps = collect_dependencies(snapshot_dir)
    dep_metrics = dependency_delta(prev_deps, deps)
    change = _diff_metrics(diff)
    activation = _activation_status(arm, checkpoint_dir)
    rework = _read_json(checkpoint_dir / "rework.json")
    stage_tokens = _stage_token_usage(
        rework,
        {"input_tokens": input_tokens, "output_tokens": output_tokens},
    )

    record = {
        "run_id": run_id,
        "arm": arm,
        "problem": problem,
        "checkpoint": checkpoint_num,
        "checkpoint_name": checkpoint_dir.name,
        "environment": environment,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read,
            "cache_write_tokens": cache_write,
            "reasoning_tokens": reasoning,
            "steps": int(steps) if steps is not None else None,
            "elapsed_seconds": inference.get("elapsed"),
            "reported_cost_usd": reported_cost,
            "normalized_cost_usd": norm_cost,
            **stage_tokens,
        },
        "correctness": {
            "checkpoint_success": checkpoint_success,
            "tests_total": tests_total,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "core_passed": core_p,
            "core_failed": core_f,
            "core_total": core_total,
            "functionality_passed": func_p,
            "functionality_failed": func_f,
            "functionality_total": func_total,
            "error_passed": err_p,
            "error_failed": err_f,
            "error_total": err_total,
            "regression_passed": reg_p,
            "regression_failed": reg_f,
            "regression_total": reg_total,
            "had_error": inference.get("had_error"),
            "error_message": inference.get("error_message"),
        },
        "change": change,
        "code": {
            **code_metrics,
            **{k: dep_metrics[k] for k in (
                "dependencies_added",
                "dependencies_removed",
                "dependencies_added_list",
                "dependency_count",
            )},
        },
        "harness": activation,
        "paths": {
            "checkpoint_dir": str(checkpoint_dir),
            "snapshot_dir": str(snapshot_dir),
        },
    }
    if rework is not None:
        record["rework"] = rework
    return record, deps


def collect_run(
    *,
    scb_problem_dir: Path,
    run_id: str,
    arm: str,
    problem: str,
    environment: dict[str, Any],
    pricing_path: Path | None = None,
) -> dict[str, Any]:
    pricing_path = pricing_path or (CONFIGS_DIR / "pricing.yaml")
    pricing = load_pricing(pricing_path)

    records: list[dict[str, Any]] = []
    prev_deps: set[str] | None = None
    for checkpoint_dir in discover_checkpoint_dirs(scb_problem_dir):
        record, prev_deps = collect_checkpoint_record(
            run_id=run_id,
            arm=arm,
            problem=problem,
            checkpoint_dir=checkpoint_dir,
            environment=environment,
            pricing=pricing,
            prev_deps=prev_deps,
        )
        records.append(record)

    cumulative = _cumulative_metrics(records)
    return {
        "run_id": run_id,
        "arm": arm,
        "problem": problem,
        "environment": environment,
        "pricing_version": pricing.get("version"),
        "checkpoints": records,
        "cumulative": cumulative,
        "pins": load_pins(),
        "harness_meta": load_arm_meta(arm),
        "ponytail": load_arm_meta("ponytail") if arm == "ponytail" else None,
    }


def _cumulative_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    seen: set[str] = set()
    acc = {
        "input_tokens": 0,
        "output_tokens": 0,
        "creation_input_tokens": 0,
        "creation_output_tokens": 0,
        "rework_input_tokens": 0,
        "rework_output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "normalized_cost_usd": 0.0,
        "reported_cost_usd": 0.0,
        "elapsed_seconds": 0.0,
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_total": 0,
        "checkpoints_passed": 0,
        "checkpoints_failed": 0,
        "checkpoints_total": 0,
        "repeated_attempts": 0,
        "core_passed": 0,
        "core_failed": 0,
        "core_total": 0,
        "functionality_passed": 0,
        "functionality_failed": 0,
        "functionality_total": 0,
        "error_passed": 0,
        "error_failed": 0,
        "error_total": 0,
        "regression_passed": 0,
        "regression_failed": 0,
        "regression_total": 0,
        "regression_failures": 0,
        "lines_changed": 0,
    }

    def optional_metric(key: str) -> int | None:
        return acc[key] if key in seen else None

    for record in records:
        usage = record["usage"]
        correctness = record["correctness"]
        change = record["change"]
        checkpoint_success = correctness.get("checkpoint_success")
        if checkpoint_success is not None:
            acc["checkpoints_total"] += 1
            acc["checkpoints_passed"] += int(checkpoint_success)
        rework = record.get("rework") or {}
        if checkpoint_success is not None or rework:
            acc["checkpoints_failed"] += int(checkpoint_success is False or bool(rework))
            seen.add("checkpoints_failed")
        if checkpoint_success is not None:
            seen.update(("checkpoints_total", "checkpoints_passed"))
        attempts_total = int(rework.get("attempts_total") or 0)
        acc["repeated_attempts"] += max(attempts_total - 1, 0)
        seen.add("repeated_attempts")
        for key in (
            "input_tokens",
            "output_tokens",
            "creation_input_tokens",
            "creation_output_tokens",
            "rework_input_tokens",
            "rework_output_tokens",
            "cache_read_tokens",
            "cache_write_tokens",
            "reasoning_tokens",
        ):
            val = usage.get(key)
            if val is not None:
                acc[key] += int(val)
                seen.add(key)
        if usage.get("input_tokens") is not None and usage.get("output_tokens") is not None:
            acc["total_tokens"] += int(usage["input_tokens"]) + int(usage["output_tokens"])
            seen.add("total_tokens")
        if usage.get("normalized_cost_usd") is not None:
            acc["normalized_cost_usd"] += float(usage["normalized_cost_usd"])
        if usage.get("reported_cost_usd") is not None:
            acc["reported_cost_usd"] += float(usage["reported_cost_usd"])
            seen.add("reported_cost_usd")
        if usage.get("elapsed_seconds") is not None:
            acc["elapsed_seconds"] += float(usage["elapsed_seconds"])
        for key in (
            "tests_passed",
            "tests_failed",
            "tests_total",
            "core_passed",
            "core_failed",
            "core_total",
            "functionality_passed",
            "functionality_failed",
            "functionality_total",
            "error_passed",
            "error_failed",
            "error_total",
            "regression_passed",
            "regression_failed",
            "regression_total",
        ):
            val = correctness.get(key)
            if val is not None:
                acc[key] += int(val)
                seen.add(key)
        if correctness.get("regression_failed") is not None:
            acc["regression_failures"] += int(correctness["regression_failed"])
        if change.get("lines_changed") is not None:
            acc["lines_changed"] += int(change["lines_changed"])

        cp = record["checkpoint"]
        out[f"through_cp{cp}"] = {
            "input_tokens": optional_metric("input_tokens"),
            "output_tokens": optional_metric("output_tokens"),
            "creation_input_tokens": optional_metric("creation_input_tokens"),
            "creation_output_tokens": optional_metric("creation_output_tokens"),
            "rework_input_tokens": optional_metric("rework_input_tokens"),
            "rework_output_tokens": optional_metric("rework_output_tokens"),
            "cache_read_tokens": optional_metric("cache_read_tokens"),
            "cache_write_tokens": optional_metric("cache_write_tokens"),
            "reasoning_tokens": optional_metric("reasoning_tokens"),
            "total_tokens": optional_metric("total_tokens"),
            "cumulative_normalized_cost_usd": round(acc["normalized_cost_usd"], 6),
            "cumulative_reported_cost_usd": (
                round(acc["reported_cost_usd"], 6)
                if "reported_cost_usd" in seen
                else None
            ),
            "cumulative_elapsed_seconds": round(acc["elapsed_seconds"], 3),
            "tests_passed": optional_metric("tests_passed"),
            "tests_failed": optional_metric("tests_failed"),
            "tests_total": optional_metric("tests_total"),
            "checkpoints_passed": optional_metric("checkpoints_passed"),
            "checkpoints_failed": optional_metric("checkpoints_failed"),
            "checkpoints_total": optional_metric("checkpoints_total"),
            "repeated_attempts": optional_metric("repeated_attempts"),
            "core_passed": optional_metric("core_passed"),
            "core_failed": optional_metric("core_failed"),
            "core_total": optional_metric("core_total"),
            "functionality_passed": optional_metric("functionality_passed"),
            "functionality_failed": optional_metric("functionality_failed"),
            "functionality_total": optional_metric("functionality_total"),
            "error_passed": optional_metric("error_passed"),
            "error_failed": optional_metric("error_failed"),
            "error_total": optional_metric("error_total"),
            "regression_passed": optional_metric("regression_passed"),
            "regression_failed": optional_metric("regression_failed"),
            "regression_total": optional_metric("regression_total"),
            "regression_failures": acc["regression_failures"],
            "lines_changed": acc["lines_changed"],
        }
    out.update(rework_stats(records))
    return out


def write_checkpoint_jsons(collected: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for record in collected["checkpoints"]:
        path = out_dir / f"checkpoint_{record['checkpoint']}.json"
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "run.json").write_text(
        json.dumps(collected, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

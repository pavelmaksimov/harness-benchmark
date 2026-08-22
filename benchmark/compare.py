from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from benchmark.arms import DEFAULT_EXPERIMENT_ARMS
from benchmark.resume_state import load_state


Number = int | float


def _mean(xs: list[Number]) -> float | None:
    return statistics.mean(xs) if xs else None


def _median(xs: list[Number]) -> float | None:
    return statistics.median(xs) if xs else None


def _stdev(xs: list[Number]) -> float | None:
    return statistics.pstdev(xs) if len(xs) >= 1 else None


def summarize(values: list[Number | None]) -> dict[str, float | None]:
    xs = [float(v) for v in values if v is not None]
    if not xs:
        return {"mean": None, "median": None, "min": None, "max": None, "stddev": None}
    return {
        "mean": _mean(xs),
        "median": _median(xs),
        "min": min(xs),
        "max": max(xs),
        "stddev": _stdev(xs),
    }


def _final_checkpoint(run: dict[str, Any]) -> dict[str, Any] | None:
    cps = run.get("checkpoints") or []
    return cps[-1] if cps else None


def _sum_known(cps: list[dict[str, Any]], section: str, key: str) -> int | None:
    values = [
        (cp.get(section) or {}).get(key)
        for cp in cps
        if (cp.get(section) or {}).get(key) is not None
    ]
    return sum(int(value) for value in values) if values else None


def _checkpoint_stage_token(
    checkpoint: dict[str, Any],
    stage_key: str,
    total_key: str,
) -> int | None:
    usage = checkpoint.get("usage") or {}
    value = usage.get(stage_key)
    if value is not None:
        return int(value)
    if stage_key.startswith("transient_"):
        if not checkpoint.get("rework"):
            return 0
        token_key = stage_key.replace("transient_", "", 1)
        values = []
        for attempt in (checkpoint.get("rework") or {}).get("attempts") or []:
            if not isinstance(attempt, dict) or attempt.get("stage") != "transient_retry":
                continue
            usage = attempt.get("usage") or {}
            attempt_value = usage.get(token_key)
            if attempt_value is not None:
                values.append(int(attempt_value))
        return sum(values) if values else 0
    if stage_key.startswith("creation_") and not checkpoint.get("rework"):
        value = usage.get(total_key)
        return int(value) if value is not None else None
    if stage_key.startswith("rework_"):
        creation_key = stage_key.replace("rework_", "creation_", 1)
        creation = usage.get(creation_key)
        total = usage.get(total_key)
        if creation is not None and total is not None and total >= creation:
            return int(total) - int(creation)
        if not checkpoint.get("rework"):
            return 0
    return None


def _semantic_attempt_count(rework: dict[str, Any]) -> int:
    attempts = [
        attempt
        for attempt in (rework.get("attempts") or [])
        if isinstance(attempt, dict)
    ]
    if rework.get("semantic_attempts_total") is not None:
        return int(rework.get("semantic_attempts_total") or 0)
    if any(isinstance(attempt.get("stage"), str) for attempt in attempts):
        return sum(1 for attempt in attempts if attempt.get("stage") != "transient_retry")
    return int(rework.get("attempts_total") or len(attempts))


def _transient_attempt_count(rework: dict[str, Any]) -> int:
    attempts = [
        attempt
        for attempt in (rework.get("attempts") or [])
        if isinstance(attempt, dict)
    ]
    if rework.get("transient_retries_total") is not None:
        return int(rework.get("transient_retries_total") or 0)
    return sum(1 for attempt in attempts if attempt.get("stage") == "transient_retry")


def _sum_stage_tokens(
    cps: list[dict[str, Any]],
    stage_key: str,
    total_key: str,
) -> int | None:
    values: list[int] = []
    for cp in cps:
        value = _checkpoint_stage_token(cp, stage_key, total_key)
        if value is None:
            return None
        values.append(value)
    return sum(values) if values else None


def _sum_core_total(cps: list[dict[str, Any]]) -> int | None:
    values: list[int] = []
    for cp in cps:
        correctness = cp.get("correctness") or {}
        total = correctness.get("core_total")
        if total is None:
            passed = correctness.get("core_passed")
            failed = correctness.get("core_failed")
            if passed is not None and failed is not None:
                total = int(passed) + int(failed)
        if total is not None:
            values.append(int(total))
    return sum(values) if values else None


def _run_totals(run: dict[str, Any]) -> dict[str, Any]:
    cps = run.get("checkpoints") or []
    passed = sum(1 for cp in cps if cp.get("correctness", {}).get("checkpoint_success"))
    failed_checkpoints = sum(
        1
        for cp in cps
        if cp.get("correctness", {}).get("checkpoint_success") is False or cp.get("rework")
    )
    regressions = sum(
        int(cp.get("correctness", {}).get("regression_failed") or 0) for cp in cps
    )
    cost = sum(
        float(cp["usage"]["normalized_cost_usd"] or 0)
        for cp in cps
        if cp["usage"].get("normalized_cost_usd") is not None
    )
    elapsed = sum(
        float(cp["usage"]["elapsed_seconds"] or 0)
        for cp in cps
        if cp["usage"].get("elapsed_seconds") is not None
    )
    lines_changed = sum(
        int(cp["change"]["lines_changed"] or 0)
        for cp in cps
        if cp["change"].get("lines_changed") is not None
    )
    files_touched = sum(
        int(cp["change"]["files_touched"] or 0)
        for cp in cps
        if cp["change"].get("files_touched") is not None
    )
    deps_added = sum(
        int(cp["code"]["dependencies_added"] or 0)
        for cp in cps
        if cp["code"].get("dependencies_added") is not None
    )
    reworked = [cp for cp in cps if cp.get("rework")]
    rework_attempts = sum(
        int(cp["rework"]["attempts_total"] or 0) for cp in reworked
    )
    rework_fixed = sum(1 for cp in reworked if cp["rework"].get("fixed"))
    rework_unresolved = len(reworked) - rework_fixed
    repeated_attempts = sum(
        max(_semantic_attempt_count(cp["rework"]) - 1, 0)
        for cp in reworked
    )
    semantic_attempts_total = sum(
        _semantic_attempt_count(cp["rework"])
        for cp in reworked
    )
    transient_retries = sum(
        _transient_attempt_count(cp["rework"])
        for cp in reworked
    )
    provider_truncations = 0
    transient_recoveries = 0
    provider_truncation_unresolved = 0
    for cp in reworked:
        rework = cp["rework"] or {}
        diagnostics = cp.get("attempt_diagnostics") or {}
        recorded_truncations = rework.get("provider_truncation_attempts")
        provider_truncations += (
            int(recorded_truncations)
            if recorded_truncations is not None
            else int(diagnostics.get("provider_truncations") or 0)
        )
        recorded_recovered = rework.get("provider_truncation_recovered")
        transient_recoveries += int(
            bool(recorded_recovered)
            if recorded_recovered is not None
            else bool(diagnostics.get("transient_recovered"))
        )
        recorded_unresolved = rework.get("provider_truncation_unresolved")
        provider_truncation_unresolved += int(
            bool(recorded_unresolved)
            if recorded_unresolved is not None
            else bool(diagnostics.get("provider_truncation_unresolved"))
        )
    for cp in cps:
        if cp.get("rework"):
            continue
        diagnostics = cp.get("attempt_diagnostics") or {}
        provider_truncations += int(diagnostics.get("provider_truncations") or 0)
        transient_retries += int(diagnostics.get("transient_retries") or 0)
        transient_recoveries += int(bool(diagnostics.get("transient_recovered")))
        provider_truncation_unresolved += int(
            bool(diagnostics.get("provider_truncation_unresolved"))
        )
    core_passed = _sum_known(cps, "correctness", "core_passed")
    core_failed = _sum_known(cps, "correctness", "core_failed")
    core_total = _sum_core_total(cps)
    creation_input_tokens = _sum_stage_tokens(cps, "creation_input_tokens", "input_tokens")
    creation_output_tokens = _sum_stage_tokens(cps, "creation_output_tokens", "output_tokens")
    rework_input_tokens = _sum_stage_tokens(cps, "rework_input_tokens", "input_tokens")
    rework_output_tokens = _sum_stage_tokens(cps, "rework_output_tokens", "output_tokens")
    transient_input_tokens = _sum_stage_tokens(cps, "transient_input_tokens", "input_tokens")
    transient_output_tokens = _sum_stage_tokens(cps, "transient_output_tokens", "output_tokens")
    input_tokens = _sum_known(cps, "usage", "input_tokens")
    output_tokens = _sum_known(cps, "usage", "output_tokens")
    reasoning = _sum_known(cps, "usage", "reasoning_tokens")
    final = _final_checkpoint(run) or {}
    return {
        "checkpoints_passed": passed,
        "checkpoints_total": len(cps),
        "checkpoints_failed": failed_checkpoints,
        "core_passed": core_passed,
        "core_failed": core_failed,
        "core_total": core_total,
        "regression_failures": regressions,
        "creation_input_tokens": creation_input_tokens,
        "creation_output_tokens": creation_output_tokens,
        "rework_input_tokens": rework_input_tokens,
        "rework_output_tokens": rework_output_tokens,
        "transient_input_tokens": transient_input_tokens,
        "transient_output_tokens": transient_output_tokens,
        "total_input_tokens": input_tokens,
        "total_output_tokens": output_tokens,
        "reasoning_tokens": reasoning,
        "normalized_cost": cost,
        "elapsed_time": elapsed,
        "loc_final": (final.get("code") or {}).get("total_source_loc"),
        "loc_changed": lines_changed,
        "files_touched": files_touched,
        "dependencies_added": deps_added,
        "complexity": (final.get("code") or {}).get("cyclomatic_complexity_total"),
        "rework_attempts": rework_attempts,
        "semantic_attempts_total": semantic_attempts_total,
        "semantic_rework_attempts": max(semantic_attempts_total - len(reworked), 0),
        "repeated_attempts": repeated_attempts,
        "rework_fixed": rework_fixed,
        "rework_unresolved": rework_unresolved,
        "transient_retries": transient_retries,
        "provider_truncations": provider_truncations,
        "transient_recoveries": transient_recoveries,
        "provider_truncation_unresolved": provider_truncation_unresolved,
        "excluded_from_comparison": bool(run.get("excluded_from_comparison")),
    }


def _is_complete_run(run: dict[str, Any]) -> bool:
    """Only state-confirmed complete runs contribute to aggregate metrics."""
    if run.get("_has_metrics") is False:
        return False
    state = run.get("_state")
    return state is None or (
        state.get("phase") in (None, "completed") and bool(state.get("fully_completed"))
    )


def _state_summary(run: dict[str, Any]) -> dict[str, Any]:
    state = run.get("_state") or {}
    return {
        "run_index": state.get("run_index"),
        "phase": state.get("phase"),
        "fully_completed": bool(state.get("fully_completed")),
        "interrupt_reason": state.get("interrupt_reason"),
        "stopped_at_checkpoint": state.get("stopped_at_checkpoint"),
        "agent": state.get("agent"),
        "provider": state.get("provider"),
        "model": state.get("model"),
        "thinking": state.get("thinking"),
        "rework_attempts": state.get("rework_attempts"),
        "transient_retries": state.get("transient_retries"),
        "feedback_strategy": state.get("feedback_strategy"),
    }


def load_experiment_runs(experiment_dir: Path) -> dict[str, list[dict[str, Any]]]:
    by_arm: dict[str, list[dict[str, Any]]] = {}
    if not experiment_dir.exists():
        return by_arm
    for arm_dir in sorted(p for p in experiment_dir.iterdir() if p.is_dir()):
        arm = arm_dir.name
        runs: list[dict[str, Any]] = []
        for run_dir in sorted(arm_dir.glob("run_*")):
            run_json = run_dir / "metrics" / "run.json"
            state = load_state(run_dir)
            run: dict[str, Any] | None = None
            if run_json.exists():
                try:
                    loaded = json.loads(run_json.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    loaded = None
                if isinstance(loaded, dict):
                    run = loaded
            if run is None and state is None:
                continue
            has_metrics = run is not None
            run = run or {"arm": arm, "checkpoints": []}
            run["_has_metrics"] = has_metrics
            if state is not None:
                run["_state"] = state
            runs.append(run)
        if runs:
            by_arm[arm] = runs
    return by_arm


def compare_arms(by_arm: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    incomplete = {
        arm: [_state_summary(run) for run in runs if not _is_complete_run(run)]
        for arm, runs in by_arm.items()
    }
    usable = {
        arm: [
            r
            for r in runs
            if _is_complete_run(r) and not r.get("excluded_from_comparison")
        ]
        for arm, runs in by_arm.items()
    }
    totals = {arm: [_run_totals(r) for r in runs] for arm, runs in usable.items()}
    arms = sorted(usable.keys(), key=lambda a: (0 if a == "baseline" else 1, a))

    metric_keys = [
        "checkpoints_passed",
        "checkpoints_total",
        "checkpoints_failed",
        "core_passed",
        "core_failed",
        "core_total",
        "regression_failures",
        "creation_input_tokens",
        "creation_output_tokens",
        "rework_input_tokens",
        "rework_output_tokens",
        "transient_input_tokens",
        "transient_output_tokens",
        "total_input_tokens",
        "total_output_tokens",
        "reasoning_tokens",
        "normalized_cost",
        "elapsed_time",
        "loc_final",
        "loc_changed",
        "files_touched",
        "dependencies_added",
        "complexity",
        "rework_attempts",
        "semantic_attempts_total",
        "semantic_rework_attempts",
        "repeated_attempts",
        "rework_fixed",
        "rework_unresolved",
        "transient_retries",
        "provider_truncations",
        "transient_recoveries",
        "provider_truncation_unresolved",
    ]

    baseline_totals = totals.get("baseline", [])
    summary_table: dict[str, Any] = {}
    for key in metric_keys:
        row: dict[str, Any] = {}
        b = summarize([t.get(key) for t in baseline_totals])
        row["baseline"] = b
        for arm in arms:
            if arm == "baseline":
                continue
            stats = summarize([t.get(key) for t in totals.get(arm, [])])
            row[arm] = stats
            delta = None
            if b["mean"] is not None and stats["mean"] is not None:
                delta = stats["mean"] - b["mean"]
            row[f"delta_mean_{arm}"] = delta
        # Back-compat for older publish code that expects delta_mean vs ponytail.
        if "ponytail" in row:
            row["delta_mean"] = row.get("delta_mean_ponytail")
        summary_table[key] = row

    per_checkpoint_rows: list[dict[str, Any]] = []
    for arm, runs in usable.items():
        for run in runs:
            for cp in run.get("checkpoints") or []:
                correctness = cp.get("correctness") or {}
                core_passed = correctness.get("core_passed")
                core_failed = correctness.get("core_failed")
                core_total = correctness.get("core_total")
                if core_total is None and core_passed is not None and core_failed is not None:
                    core_total = int(core_passed) + int(core_failed)
                per_checkpoint_rows.append(
                    {
                        "cp": cp.get("checkpoint"),
                        "arm": arm,
                        "run_id": run.get("run_id"),
                        "pass": cp.get("correctness", {}).get("checkpoint_success"),
                        "core_passed": core_passed,
                        "core_failed": core_failed,
                        "core_total": core_total,
                        "creation_input_tokens": _checkpoint_stage_token(
                            cp, "creation_input_tokens", "input_tokens"
                        ),
                        "creation_output_tokens": _checkpoint_stage_token(
                            cp, "creation_output_tokens", "output_tokens"
                        ),
                        "rework_input_tokens": _checkpoint_stage_token(
                            cp, "rework_input_tokens", "input_tokens"
                        ),
                        "rework_output_tokens": _checkpoint_stage_token(
                            cp, "rework_output_tokens", "output_tokens"
                        ),
                        "transient_input_tokens": _checkpoint_stage_token(
                            cp, "transient_input_tokens", "input_tokens"
                        ),
                        "transient_output_tokens": _checkpoint_stage_token(
                            cp, "transient_output_tokens", "output_tokens"
                        ),
                        "input_tokens": cp.get("usage", {}).get("input_tokens"),
                        "output_tokens": cp.get("usage", {}).get("output_tokens"),
                        "cache_read_tokens": cp.get("usage", {}).get("cache_read_tokens"),
                        "cache_write_tokens": cp.get("usage", {}).get("cache_write_tokens"),
                        "reasoning_tokens": cp.get("usage", {}).get("reasoning_tokens"),
                        "steps": cp.get("usage", {}).get("steps"),
                        "reported_cost_usd": cp.get("usage", {}).get("reported_cost_usd"),
                        "cost": cp.get("usage", {}).get("normalized_cost_usd"),
                        "tokens": (
                            (cp.get("usage", {}).get("input_tokens") or 0)
                            + (cp.get("usage", {}).get("output_tokens") or 0)
                        )
                        if cp.get("usage", {}).get("input_tokens") is not None
                        else None,
                        "time": cp.get("usage", {}).get("elapsed_seconds"),
                        "loc_delta": cp.get("change", {}).get("lines_changed"),
                        "files_delta": cp.get("change", {}).get("files_touched"),
                        "regressions": cp.get("correctness", {}).get("regression_failed"),
                        "rework": cp.get("rework"),
                        "attempt_diagnostics": cp.get("attempt_diagnostics"),
                    }
                )

    out: dict[str, Any] = {
        "arms": arms,
        "summary": summary_table,
        "per_checkpoint": per_checkpoint_rows,
        "raw_totals": totals,
        "excluded_runs": {
            arm: sum(1 for r in runs if r.get("excluded_from_comparison"))
            for arm, runs in by_arm.items()
        },
        "incomplete_runs": {arm: states for arm, states in incomplete.items() if states},
    }
    for arm in set(DEFAULT_EXPERIMENT_ARMS) | set(by_arm):
        out[f"n_{arm}"] = len(usable.get(arm, []))
    out["excluded_ponytail_runs"] = out["excluded_runs"].get("ponytail", 0)
    return out


def format_comparison_report(comparison: dict[str, Any], problem: str = "file_backup") -> str:
    arms = comparison.get("arms") or []
    if not arms:
        arms = [a for a in DEFAULT_EXPERIMENT_ARMS if comparison.get(f"n_{a}", 0)]
    lines: list[str] = []
    lines.append(f"{problem.upper()} — multi-harness")
    lines.append("")
    n_parts = [f"{arm}={comparison.get(f'n_{arm}', 0)}" for arm in arms]
    lines.append("N " + "  ".join(n_parts))
    lines.append("Failed checkpoints includes checkpoints repaired by rework.")
    lines.append("Rework tokens are All tokens minus Creation tokens when per-attempt usage is unavailable.")
    lines.append("Transient retries are separate from semantic rework and require high-confidence truncation signals.")
    excluded = comparison.get("excluded_runs") or {}
    excluded_bits = [f"{arm}={n}" for arm, n in excluded.items() if n]
    if excluded_bits:
        lines.append("Excluded (activation unverified): " + ", ".join(excluded_bits))
    incomplete = comparison.get("incomplete_runs") or {}
    incomplete_bits = [f"{arm}={len(states)}" for arm, states in incomplete.items() if states]
    if incomplete_bits:
        lines.append("Incomplete (excluded from averages): " + ", ".join(incomplete_bits))
    lines.append("")

    labels = {
        "checkpoints_passed": "CP passed/total",
        "checkpoints_failed": "Failed checkpoints",
        "regression_failures": "Regressions",
        "creation_input_tokens": "Creation input tokens",
        "creation_output_tokens": "Creation output tokens",
        "rework_input_tokens": "Rework input tokens",
        "rework_output_tokens": "Rework output tokens",
        "transient_input_tokens": "Transient input tokens",
        "transient_output_tokens": "Transient output tokens",
        "total_input_tokens": "All input tokens",
        "total_output_tokens": "All output tokens",
        "reasoning_tokens": "Reasoning tokens",
        "normalized_cost": "Normalized cost",
        "elapsed_time": "Elapsed time",
        "loc_final": "Final LOC",
        "loc_changed": "Changed LOC",
        "files_touched": "Files touched",
        "dependencies_added": "Dependencies",
        "complexity": "Complexity",
        "semantic_rework_attempts": "Semantic rework attempts",
        "repeated_attempts": "Repeated attempts",
        "rework_fixed": "Rework fixed",
        "rework_unresolved": "Rework unresolved",
        "transient_retries": "Transient retries",
        "provider_truncations": "Provider truncations",
        "transient_recoveries": "Transient recoveries",
        "provider_truncation_unresolved": "Truncations unresolved",
    }

    col_w = max(12, max((len(a) for a in arms), default=12))
    header = f"{'Metric':<22}" + "".join(f" {a:>{col_w}}" for a in arms)
    lines.append(header)
    lines.append("-" * len(header))

    def fmt(key: str, v: float | None) -> str:
        if v is None:
            return "-"
        if key in {"normalized_cost"}:
            return f"${v:.2f}"
        if key in {"elapsed_time"}:
            return f"{v / 60:.1f}m"
        if key in {
            "creation_input_tokens",
            "creation_output_tokens",
            "rework_input_tokens",
            "rework_output_tokens",
            "transient_input_tokens",
            "transient_output_tokens",
            "total_input_tokens",
            "total_output_tokens",
            "reasoning_tokens",
        }:
            return f"{v:,.0f}"
        if isinstance(v, float) and not v.is_integer():
            return f"{v:.1f}"
        return f"{v:.0f}"

    for key, label in labels.items():
        row = (comparison.get("summary") or {}).get(key) or {}
        cells: list[str] = []
        for arm in arms:
            mean = (row.get(arm) or {}).get("mean")
            if key == "checkpoints_passed":
                totals = (comparison.get("summary") or {}).get("checkpoints_total") or {}
                cells.append(
                    f"{fmt(key, mean)}/{fmt(key, (totals.get(arm) or {}).get('mean'))}"
                )
            else:
                cells.append(fmt(key, mean))
        lines.append(f"{label:<22}" + "".join(f" {c:>{col_w}}" for c in cells))

    lines.append("")
    lines.append("Δ vs baseline (mean):")
    lines.append(f"{'Metric':<22}" + "".join(f" {a:>{col_w}}" for a in arms if a != "baseline"))
    for key, label in labels.items():
        row = (comparison.get("summary") or {}).get(key) or {}
        cells = []
        for arm in arms:
            if arm == "baseline":
                continue
            cells.append(fmt(key, row.get(f"delta_mean_{arm}")))
        lines.append(f"{label:<22}" + "".join(f" {c:>{col_w}}" for c in cells))

    lines.append("")
    lines.append("Per-checkpoint (raw):")
    lines.append(
        f"{'CP':<4} {'Arm':<36} {'Pass':<5} {'Create In':>10} {'Create Out':>10} "
        f"{'Rework In':>10} {'Rework Out':>10} {'Transient In':>10} {'Transient Out':>10} "
        f"{'All In':>10} {'All Out':>10} "
        f"{'Cost':>8} {'Time':>8} {'LOCΔ':>8} {'FilesΔ':>8} {'Reg':>5} {'Repeat':>6}"
    )
    for row in comparison["per_checkpoint"]:
        rework = row.get("rework") or {}
        semantic_attempts = _semantic_attempt_count(rework) if rework else 0
        repeated_attempts = max(semantic_attempts - 1, 0) if rework else 0
        creation_input = row.get("creation_input_tokens")
        creation_output = row.get("creation_output_tokens")
        rework_input = row.get("rework_input_tokens")
        rework_output = row.get("rework_output_tokens")
        transient_input = row.get("transient_input_tokens")
        transient_output = row.get("transient_output_tokens")
        all_input = row.get("input_tokens")
        all_output = row.get("output_tokens")
        cost = row.get("cost")
        time = row.get("time")
        creation_input_text = "-" if creation_input is None else f"{int(creation_input):,}"
        creation_output_text = "-" if creation_output is None else f"{int(creation_output):,}"
        rework_input_text = "-" if rework_input is None else f"{int(rework_input):,}"
        rework_output_text = "-" if rework_output is None else f"{int(rework_output):,}"
        transient_input_text = "-" if transient_input is None else f"{int(transient_input):,}"
        transient_output_text = "-" if transient_output is None else f"{int(transient_output):,}"
        all_input_text = "-" if all_input is None else f"{int(all_input):,}"
        all_output_text = "-" if all_output is None else f"{int(all_output):,}"
        cost_text = "-" if cost is None else f"{float(cost):.2f}"
        time_text = "-" if time is None else f"{float(time):.0f}"
        lines.append(
            f"{str(row['cp']):<4} {row['arm']:<36} {str(row['pass']):<5} "
            f"{creation_input_text:>10} "
            f"{creation_output_text:>10} "
            f"{rework_input_text:>10} "
            f"{rework_output_text:>10} "
            f"{transient_input_text:>12} "
            f"{transient_output_text:>13} "
            f"{all_input_text:>10} "
            f"{all_output_text:>10} "
            f"{cost_text:>8} "
            f"{time_text:>8} "
            f"{('-' if row.get('loc_delta') is None else str(row['loc_delta'])):>8} "
            f"{('-' if row.get('files_delta') is None else str(row['files_delta'])):>8} "
            f"{('-' if row.get('regressions') is None else str(row['regressions'])):>5} "
            f"{repeated_attempts:>6}"
        )

    rework_rows = [
        row
        for row in comparison["per_checkpoint"]
        if (row.get("rework") or {}).get("attempts")
    ]
    if rework_rows:
        lines.extend(["", "Rework attempts (raw):"])
        lines.append(
            f"{'CP':<4} {'Arm':<36} {'Stage':<8} {'#':>3} {'Core p/f/t':>11} "
            f"{'In':>10} {'Out':>10} {'Time':>8} {'Cost':>8} {'Failed':>6}"
        )
        for row in rework_rows:
            for attempt in (row.get("rework") or {}).get("attempts") or []:
                core = attempt.get("core") or {}
                usage = attempt.get("usage") or {}
                failed = attempt.get("failed_tests") or []
                attempt_number = attempt.get("attempt")
                stage = attempt.get("stage") or (
                    "creation" if attempt_number == 1 else "rework"
                )
                input_tokens = usage.get("input_tokens")
                output_tokens = usage.get("output_tokens")
                elapsed_seconds = usage.get("elapsed_seconds")
                reported_cost = usage.get("reported_cost_usd")
                core_score = (
                    f"{core.get('passed')}/{core.get('failed')}/{core.get('total')}"
                    if core
                    else "-"
                )
                input_text = "-" if input_tokens is None else f"{int(input_tokens):,}"
                output_text = "-" if output_tokens is None else f"{int(output_tokens):,}"
                elapsed_text = "-" if elapsed_seconds is None else f"{float(elapsed_seconds):.0f}"
                cost_text = "-" if reported_cost is None else f"{float(reported_cost):.2f}"
                lines.append(
                    f"{str(row['cp']):<4} {row['arm']:<36} "
                    f"{stage:<8} {str(attempt_number or '-'):>3} {core_score:>11} "
                    f"{input_text:>10} "
                    f"{output_text:>10} "
                    f"{elapsed_text:>8} "
                    f"{cost_text:>8} "
                    f"{len(failed):>6}"
                )

    lines.append("")
    lines.append("Stats per metric include mean/median/min/max/stddev in the JSON report.")
    return "\n".join(lines) + "\n"

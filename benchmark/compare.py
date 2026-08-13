from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from benchmark.arms import DEFAULT_EXPERIMENT_ARMS


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


def _run_totals(run: dict[str, Any]) -> dict[str, Any]:
    cps = run.get("checkpoints") or []
    passed = sum(1 for cp in cps if cp.get("correctness", {}).get("checkpoint_success"))
    regressions = sum(
        int(cp.get("correctness", {}).get("regression_failed") or 0) for cp in cps
    )
    input_tokens = sum(
        int(cp["usage"]["input_tokens"] or 0)
        for cp in cps
        if cp["usage"].get("input_tokens") is not None
    )
    output_tokens = sum(
        int(cp["usage"]["output_tokens"] or 0)
        for cp in cps
        if cp["usage"].get("output_tokens") is not None
    )
    reasoning = sum(
        int(cp["usage"]["reasoning_tokens"] or 0)
        for cp in cps
        if cp["usage"].get("reasoning_tokens") is not None
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
    final = _final_checkpoint(run) or {}
    return {
        "checkpoints_passed": passed,
        "checkpoints_total": len(cps),
        "regression_failures": regressions,
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
        "excluded_from_comparison": bool(run.get("excluded_from_comparison")),
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
            if not run_json.exists():
                continue
            runs.append(json.loads(run_json.read_text(encoding="utf-8")))
        if runs:
            by_arm[arm] = runs
    return by_arm


def compare_arms(by_arm: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    usable = {
        arm: [r for r in runs if not r.get("excluded_from_comparison")]
        for arm, runs in by_arm.items()
    }
    totals = {arm: [_run_totals(r) for r in runs] for arm, runs in usable.items()}
    arms = sorted(usable.keys(), key=lambda a: (0 if a == "baseline" else 1, a))

    metric_keys = [
        "checkpoints_passed",
        "checkpoints_total",
        "regression_failures",
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
                per_checkpoint_rows.append(
                    {
                        "cp": cp.get("checkpoint"),
                        "arm": arm,
                        "run_id": run.get("run_id"),
                        "pass": cp.get("correctness", {}).get("checkpoint_success"),
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
    excluded = comparison.get("excluded_runs") or {}
    excluded_bits = [f"{arm}={n}" for arm, n in excluded.items() if n]
    if excluded_bits:
        lines.append("Excluded (activation unverified): " + ", ".join(excluded_bits))
    lines.append("")

    labels = {
        "checkpoints_passed": "CP passed/total",
        "regression_failures": "Regressions",
        "total_input_tokens": "Input tokens",
        "total_output_tokens": "Output tokens",
        "reasoning_tokens": "Reasoning tokens",
        "normalized_cost": "Normalized cost",
        "elapsed_time": "Elapsed time",
        "loc_final": "Final LOC",
        "loc_changed": "Changed LOC",
        "files_touched": "Files touched",
        "dependencies_added": "Dependencies",
        "complexity": "Complexity",
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
        if isinstance(v, float) and not v.is_integer():
            return f"{v:.1f}"
        return f"{v:.0f}"

    for key, label in labels.items():
        row = comparison["summary"][key]
        cells: list[str] = []
        for arm in arms:
            mean = (row.get(arm) or {}).get("mean")
            if key == "checkpoints_passed":
                totals = comparison["summary"]["checkpoints_total"]
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
        row = comparison["summary"][key]
        cells = []
        for arm in arms:
            if arm == "baseline":
                continue
            cells.append(fmt(key, row.get(f"delta_mean_{arm}")))
        lines.append(f"{label:<22}" + "".join(f" {c:>{col_w}}" for c in cells))

    lines.append("")
    lines.append("Per-checkpoint (raw):")
    lines.append(
        f"{'CP':<4} {'Arm':<36} {'Pass':<5} {'Cost':>8} {'Tokens':>8} {'Time':>8} "
        f"{'LOCΔ':>8} {'FilesΔ':>8} {'Reg':>5}"
    )
    for row in comparison["per_checkpoint"]:
        lines.append(
            f"{str(row['cp']):<4} {row['arm']:<36} {str(row['pass']):<5} "
            f"{('-' if row['cost'] is None else f'{row['cost']:.2f}'):>8} "
            f"{('-' if row['tokens'] is None else str(row['tokens'])):>8} "
            f"{('-' if row['time'] is None else f'{row['time']:.0f}'):>8} "
            f"{('-' if row['loc_delta'] is None else str(row['loc_delta'])):>8} "
            f"{('-' if row['files_delta'] is None else str(row['files_delta'])):>8} "
            f"{('-' if row['regressions'] is None else str(row['regressions'])):>5}"
        )

    lines.append("")
    lines.append("Stats per metric include mean/median/min/max/stddev in the JSON report.")
    return "\n".join(lines) + "\n"

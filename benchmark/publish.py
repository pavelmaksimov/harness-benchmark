from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.arms import DEFAULT_EXPERIMENT_ARMS
from benchmark.paths import DOCS_DIR, DOCS_REPORTS_DIR

METRIC_KEYS = (
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
    "total_input_tokens",
    "total_output_tokens",
    "normalized_cost",
    "elapsed_time",
    "loc_final",
    "loc_changed",
    "dependencies_added",
    "complexity",
    "repeated_attempts",
)

SHORT_LABELS = {
    "checkpoints_passed": "CP passed/total",
    "checkpoints_failed": "Failed checkpoints",
    "repeated_attempts": "Repeated attempts",
    "regression_failures": "Regressions",
    "creation_input_tokens": "Creation input tokens",
    "creation_output_tokens": "Creation output tokens",
    "rework_input_tokens": "Rework input tokens",
    "rework_output_tokens": "Rework output tokens",
    "total_input_tokens": "All input tokens",
    "total_output_tokens": "All output tokens",
    "normalized_cost": "Normalized cost",
    "elapsed_time": "Elapsed",
    "loc_final": "Final LOC",
    "loc_changed": "Changed LOC",
    "dependencies_added": "Dependencies",
    "complexity": "Complexity",
}


def _load_manifest(experiment_dir: Path) -> dict[str, Any]:
    for path in sorted(experiment_dir.glob("*/run_*/manifest.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(manifest, dict):
            return manifest
    for path in sorted(experiment_dir.glob("*/run_*/state.json")):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(state, dict):
            continue
        return {
            "date": state.get("updated_at") or "",
            "experiment_id": state.get("experiment_id"),
            "problem": state.get("problem"),
            "arm": state.get("arm"),
            "agent": state.get("agent"),
            "model": state.get("model"),
            "model_settings": {
                "provider": state.get("provider"),
                "thinking": state.get("thinking"),
            },
        }
    return {}


def _arm_means(comparison: dict[str, Any], arm: str) -> dict[str, float | None]:
    summary = comparison.get("summary") or {}
    out: dict[str, float | None] = {}
    for key in METRIC_KEYS:
        row = summary.get(key) or {}
        arm_stats = row.get(arm) or {}
        out[key] = arm_stats.get("mean")
    return out


def _fmt_metric(key: str, value: float | None) -> str:
    if value is None:
        return "-"
    if key == "normalized_cost":
        return f"${value:.2f}"
    if key == "elapsed_time":
        return f"{value / 60:.1f}m"
    if key in {
        "creation_input_tokens",
        "creation_output_tokens",
        "rework_input_tokens",
        "rework_output_tokens",
        "total_input_tokens",
        "total_output_tokens",
    }:
        return f"{value:,.0f}"
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.1f}"
    return f"{value:.0f}"


def _fmt_checkpoints(metrics: dict[str, Any]) -> str:
    passed = _fmt_metric("checkpoints_passed", metrics.get("checkpoints_passed"))
    total = _fmt_metric("checkpoints_total", metrics.get("checkpoints_total"))
    return f"{passed}/{total}"


def _fmt_delta(key: str, value: float | None) -> str:
    if value is None:
        return "-"
    if key == "normalized_cost":
        sign = "+" if value > 0 else ""
        return f"{sign}${value:.2f}"
    if key == "elapsed_time":
        minutes = value / 60
        sign = "+" if minutes > 0 else ""
        return f"{sign}{minutes:.1f}m"
    if key in {
        "creation_input_tokens",
        "creation_output_tokens",
        "rework_input_tokens",
        "rework_output_tokens",
        "total_input_tokens",
        "total_output_tokens",
    }:
        sign = "+" if value > 0 else ""
        return f"{sign}{value:,.0f}"
    if isinstance(value, float) and not value.is_integer():
        sign = "+" if value > 0 else ""
        return f"{sign}{value:.1f}"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.0f}"


def _comparison_arms(comparison: dict[str, Any]) -> list[str]:
    arms = list(comparison.get("arms") or [])
    if arms:
        return arms
    found = []
    for arm in DEFAULT_EXPERIMENT_ARMS:
        if comparison.get(f"n_{arm}", 0):
            found.append(arm)
    return found


def build_publish_payload(experiment_dir: Path, comparison: dict[str, Any]) -> dict[str, Any]:
    manifest = _load_manifest(experiment_dir)
    arm_names = _comparison_arms(comparison)
    arms = {
        arm: _arm_means(comparison, arm)
        for arm in arm_names
        if comparison.get(f"n_{arm}", 0)
    }
    deltas = {
        arm: {
            key: (comparison.get("summary") or {}).get(key, {}).get(f"delta_mean_{arm}")
            for key in METRIC_KEYS
        }
        for arm in arm_names
        if arm != "baseline"
    }
    rework: dict[str, dict[str, int]] = {}
    raw_totals = comparison.get("raw_totals") or {}
    for arm, totals in raw_totals.items():
        attempts = sum(int(t.get("rework_attempts") or 0) for t in totals)
        repeated_attempts = sum(int(t.get("repeated_attempts") or 0) for t in totals)
        if attempts <= 0:
            continue
        rework[arm] = {
            "attempts": attempts,
            "repeated_attempts": repeated_attempts,
            "fixed": sum(int(t.get("rework_fixed") or 0) for t in totals),
            "unresolved": sum(int(t.get("rework_unresolved") or 0) for t in totals),
        }
    # Back-compat single delta map for ponytail-era reports.
    legacy_deltas = {
        key: (comparison.get("summary") or {}).get(key, {}).get("delta_mean") for key in METRIC_KEYS
    }
    rework_details = [
        row
        for row in comparison.get("per_checkpoint") or []
        if (row.get("rework") or {}).get("attempts")
    ]
    payload: dict[str, Any] = {
        "experiment_id": experiment_dir.name,
        "date": manifest.get("date") or "",
        "problem": manifest.get("problem") or "unknown",
        "model": manifest.get("model") or "unknown",
        "thinking": (manifest.get("model_settings") or {}).get("thinking"),
        "agent": manifest.get("agent"),
        "provider": (manifest.get("model_settings") or {}).get("provider"),
        "agent_version": manifest.get("agent_version"),
        "arms": arms,
        "deltas_by_arm": deltas,
        "deltas": legacy_deltas,
        "git_commits": manifest.get("git_commits") or {},
        "ponytail": manifest.get("ponytail"),
        "pricing_version": manifest.get("pricing_version"),
        "excluded_runs": comparison.get("excluded_runs") or {},
        "excluded_ponytail_runs": comparison.get("excluded_ponytail_runs", 0),
        "incomplete_runs": comparison.get("incomplete_runs") or {},
    }
    if rework:
        payload["rework"] = rework
    if rework_details:
        payload["rework_details"] = rework_details
    for arm in arm_names:
        payload[f"n_{arm}"] = comparison.get(f"n_{arm}", 0)
    payload["n_baseline"] = comparison.get("n_baseline", 0)
    payload["n_ponytail"] = comparison.get("n_ponytail", 0)
    return payload


def _notes_from_payload(payload: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    arms = payload.get("arms") or {}
    baseline = arms.get("baseline") or {}
    if not baseline:
        return notes
    for arm, metrics in arms.items():
        if arm == "baseline":
            continue
        cp_b, cp_p = baseline.get("checkpoints_passed"), metrics.get("checkpoints_passed")
        if cp_b is not None and cp_p is not None and cp_b != cp_p:
            notes.append(
                f"{arm} CP {_fmt_checkpoints(metrics)} vs baseline {_fmt_checkpoints(baseline)}."
            )
        for key, label in (
            ("loc_final", "final LOC"),
            ("normalized_cost", "cost"),
            ("elapsed_time", "time"),
        ):
            bv, pv = baseline.get(key), metrics.get(key)
            if bv is None or pv is None or bv == pv:
                continue
            direction = "lower" if pv < bv else "higher"
            notes.append(
                f"{arm} {direction} {label} ({_fmt_metric(key, pv)} vs {_fmt_metric(key, bv)})."
            )
            break
        if len(notes) >= 6:
            break
    return notes[:6]


def format_short_report(payload: dict[str, Any]) -> str:
    eid = payload["experiment_id"]
    thinking = payload.get("thinking") or "-"
    agent = payload.get("agent") or "-"
    provider = payload.get("provider") or "-"
    agent_version = payload.get("agent_version") or "-"
    arms = payload.get("arms") or {}
    arm_names = list(arms.keys()) or ["baseline"]
    n_bits = " · ".join(f"{a}={payload.get(f'n_{a}', 0)}" for a in arm_names)
    lines = [
        f"# {eid}",
        "",
        "| | |",
        "|---|---|",
        f"| Problem | `{payload.get('problem')}` |",
        f"| Model | `{payload.get('model')}` · thinking `{thinking}` |",
        f"| Agent | {agent} · provider `{provider}` · `{agent_version}` |",
        f"| N | {n_bits} |",
        "| Pins | SCB / problems / harness pins — see published JSON / local manifest |",
        "",
        "## Metrics (mean)",
        "",
        "Creation/Rework token metrics use per-attempt usage; `-` means unavailable.",
        "Failed checkpoints include checkpoints repaired by rework; Rework = All - Create when possible.",
        "",
    ]

    header = "| Metric | " + " | ".join(arm_names) + " |"
    sep = "|--------|" + "|".join(["---------:" for _ in arm_names]) + "|"
    lines.extend([header, sep])
    for key, label in SHORT_LABELS.items():
        cells = []
        for arm in arm_names:
            metrics = arms.get(arm) or {}
            if key == "checkpoints_passed":
                cells.append(_fmt_checkpoints(metrics))
            else:
                cells.append(_fmt_metric(key, metrics.get(key)))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    deltas_by_arm = payload.get("deltas_by_arm") or {}
    if deltas_by_arm:
        lines.extend(["", "## Δ vs baseline", ""])
        d_arms = [a for a in arm_names if a != "baseline" and a in deltas_by_arm]
        if d_arms:
            lines.append("| Metric | " + " | ".join(d_arms) + " |")
            lines.append("|--------|" + "|".join(["---------:" for _ in d_arms]) + "|")
            for key, label in SHORT_LABELS.items():
                cells = [_fmt_delta(key, (deltas_by_arm.get(a) or {}).get(key)) for a in d_arms]
                lines.append(f"| {label} | " + " | ".join(cells) + " |")

    notes = _notes_from_payload(payload)
    lines.extend(["", "## Notes", ""])
    if notes:
        lines.extend(f"- {n}" for n in notes)
    else:
        lines.append("- No paired baseline/harness means to summarize.")
    rework = payload.get("rework") or {}
    if rework:
        for arm, rw in rework.items():
            lines.append(
                f"- Rework {arm}: {rw.get('repeated_attempts', rw['attempts'])} repeated attempts "
                f"({rw['attempts']} total attempts), "
                f"{rw['fixed']} fixed, {rw['unresolved']} unresolved."
            )
    excluded = payload.get("excluded_runs") or {}
    excluded_bits = [f"{arm}={n}" for arm, n in excluded.items() if n]
    if excluded_bits:
        lines.append(f"- Excluded (activation unverified): {', '.join(excluded_bits)}.")
    incomplete = payload.get("incomplete_runs") or {}
    incomplete_bits = [f"{arm}={len(states)}" for arm, states in incomplete.items() if states]
    if incomplete_bits:
        lines.append(f"- Incomplete runs excluded from averages: {', '.join(incomplete_bits)}.")
    lines.extend(
        [
            "",
            f"Raw (local only): `results/{eid}/`, `reports/{eid}/`.",
            "",
        ]
    )
    return "\n".join(lines)


def _sort_key(payload: dict[str, Any]) -> tuple[str, str]:
    return (payload.get("date") or "", payload.get("experiment_id") or "")


def load_published_reports(docs_reports_dir: Path | None = None) -> list[dict[str, Any]]:
    root = docs_reports_dir or DOCS_REPORTS_DIR
    if not root.exists():
        return []
    payloads: list[dict[str, Any]] = []
    for path in root.glob("*.json"):
        payloads.append(json.loads(path.read_text(encoding="utf-8")))
    payloads.sort(key=_sort_key, reverse=True)
    return payloads


def _latest_cells(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten arm rows; keep newest experiment per full adapter/model cell."""
    cells: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for payload in payloads:  # already newest-first
        problem = payload.get("problem") or "unknown"
        agent = payload.get("agent") or "unknown"
        provider = payload.get("provider") or "unknown"
        model = payload.get("model") or "unknown"
        for harness, metrics in (payload.get("arms") or {}).items():
            key = (problem, agent, provider, model, harness)
            if key in seen:
                continue
            seen.add(key)
            cells.append(
                {
                    "date": payload.get("date") or "",
                    "experiment_id": payload.get("experiment_id"),
                    "problem": problem,
                    "agent": agent,
                    "provider": provider,
                    "model": model,
                    "harness": harness,
                    "n": payload.get(f"n_{harness}", 0),
                    "metrics": metrics,
                }
            )
    return cells


def _section_order(values: list[str], latest_date_by_value: dict[str, str]) -> list[str]:
    return sorted(values, key=lambda v: (latest_date_by_value.get(v, ""), v), reverse=True)


def _metric_cells(metrics: dict[str, Any]) -> str:
    parts = [
        _fmt_checkpoints(metrics),
        _fmt_metric("checkpoints_failed", metrics.get("checkpoints_failed")),
        _fmt_metric("repeated_attempts", metrics.get("repeated_attempts")),
        _fmt_metric("regression_failures", metrics.get("regression_failures")),
        _fmt_metric("creation_input_tokens", metrics.get("creation_input_tokens")),
        _fmt_metric("creation_output_tokens", metrics.get("creation_output_tokens")),
        _fmt_metric("rework_input_tokens", metrics.get("rework_input_tokens")),
        _fmt_metric("rework_output_tokens", metrics.get("rework_output_tokens")),
        _fmt_metric("total_input_tokens", metrics.get("total_input_tokens")),
        _fmt_metric("total_output_tokens", metrics.get("total_output_tokens")),
        _fmt_metric("normalized_cost", metrics.get("normalized_cost")),
        _fmt_metric("elapsed_time", metrics.get("elapsed_time")),
        _fmt_metric("loc_final", metrics.get("loc_final")),
        _fmt_metric("loc_changed", metrics.get("loc_changed")),
        _fmt_metric("dependencies_added", metrics.get("dependencies_added")),
        _fmt_metric("complexity", metrics.get("complexity")),
    ]
    return " | ".join(parts)


def _sort_table_rows(rows: list[dict[str, Any]], secondary: str) -> list[dict[str, Any]]:
    """Newest date first; within a date, secondary asc; baseline first."""
    ordered = sorted(
        rows,
        key=lambda c: (c[secondary], 0 if c["harness"] == "baseline" else 1, c["harness"]),
    )
    return sorted(ordered, key=lambda c: c["date"], reverse=True)


def format_leaderboard(payloads: list[dict[str, Any]]) -> str:
    cells = _latest_cells(payloads)
    lines = [
        "# Leaderboard",
        "",
        "No single score. Absolute metrics only. Δ vs baseline is only in short reports",
        "for the same `(problem, adapter, provider, model)` cell.",
        "",
        "Published from `docs/reports/*.json`. Rebuilt by `python -m benchmark report`.",
        "Newer experiments appear first.",
        "Create/Rework token columns use per-attempt usage; `-` means it is unavailable.",
        "All in/out columns preserve the aggregate usage for older runs.",
        "Failed CP counts checkpoints that failed at least once, including repaired ones.",
        "Rework in/out is calculated as All in/out minus Create in/out when possible.",
        "",
        "## By task",
        "",
    ]

    problems = sorted({c["problem"] for c in cells})
    latest_by_problem = {
        p: max((c["date"] for c in cells if c["problem"] == p), default="") for p in problems
    }
    for problem in _section_order(problems, latest_by_problem):
        lines.append(f"### `{problem}`")
        lines.append("")
        lines.append(
            "| Agent | Model | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | All in | All out | Cost | Time | LOC | ΔLOC | Deps | Cx |"
        )
        lines.append("|-------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|--------:|---------:|-----:|-----:|----:|-----:|-----:|---:|")
        rows = _sort_table_rows([c for c in cells if c["problem"] == problem], "model")
        for row in rows:
            lines.append(
                f"| {row['agent']} | {row['model']} | {row['harness']} | "
                f"{row['n']} | {_metric_cells(row['metrics'])} |"
            )
        lines.append("")

    lines.extend(["## By model", ""])
    models = sorted({c["model"] for c in cells})
    latest_by_model = {
        m: max((c["date"] for c in cells if c["model"] == m), default="") for m in models
    }
    for model in _section_order(models, latest_by_model):
        lines.append(f"### `{model}`")
        lines.append("")
        lines.append(
            "| Problem | Agent | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | All in | All out | Cost | Time | LOC | ΔLOC | Deps | Cx |"
        )
        lines.append("|---------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|--------:|---------:|-----:|-----:|----:|-----:|-----:|---:|")
        rows = _sort_table_rows([c for c in cells if c["model"] == model], "problem")
        for row in rows:
            lines.append(
                f"| {row['problem']} | {row['agent']} | {row['harness']} | "
                f"{row['n']} | {_metric_cells(row['metrics'])} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Experiments",
            "",
            "| Experiment | Date | Problem | Agent | Model | N | Report |",
            "|------------|------|---------|-------|-------|---|--------|",
        ]
    )
    for payload in payloads:
        eid = payload.get("experiment_id") or ""
        date = (payload.get("date") or "")[:10]
        arms = list((payload.get("arms") or {}).keys())
        if arms:
            n = "+".join(str(payload.get(f"n_{a}", 0)) for a in arms)
        else:
            n = f"{payload.get('n_baseline', 0)}+{payload.get('n_ponytail', 0)}"
        lines.append(
            f"| {eid} | {date} | {payload.get('problem')} | {payload.get('agent')} | "
            f"{payload.get('model')} | {n} | "
            f"[short](reports/{eid}.md) |"
        )
    lines.append("")
    return "\n".join(lines)


def rebuild_leaderboard(docs_dir: Path | None = None) -> Path:
    root = docs_dir or DOCS_DIR
    reports_dir = root / "reports"
    payloads = load_published_reports(reports_dir)
    out = root / "LEADERBOARD.md"
    root.mkdir(parents=True, exist_ok=True)
    out.write_text(format_leaderboard(payloads), encoding="utf-8")
    return out


def publish_short_report(
    experiment_dir: Path,
    comparison: dict[str, Any],
    *,
    docs_dir: Path | None = None,
) -> tuple[Path, Path, Path]:
    root = docs_dir or DOCS_DIR
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = build_publish_payload(experiment_dir, comparison)
    eid = payload["experiment_id"]
    json_path = reports_dir / f"{eid}.json"
    md_path = reports_dir / f"{eid}.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(format_short_report(payload), encoding="utf-8")
    board_path = rebuild_leaderboard(root)
    return md_path, json_path, board_path

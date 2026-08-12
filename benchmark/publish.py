from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.paths import DOCS_DIR, DOCS_REPORTS_DIR

METRIC_KEYS = (
    "checkpoints_passed",
    "checkpoints_total",
    "regression_failures",
    "normalized_cost",
    "elapsed_time",
    "loc_final",
    "loc_changed",
    "dependencies_added",
    "complexity",
)

SHORT_LABELS = {
    "checkpoints_passed": "CP passed/total",
    "regression_failures": "Regressions",
    "normalized_cost": "Normalized cost",
    "elapsed_time": "Elapsed",
    "loc_final": "Final LOC",
    "loc_changed": "Changed LOC",
    "dependencies_added": "Dependencies",
    "complexity": "Complexity",
}


def _load_manifest(experiment_dir: Path) -> dict[str, Any]:
    for path in sorted(experiment_dir.glob("*/run_*/manifest.json")):
        return json.loads(path.read_text(encoding="utf-8"))
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
    if isinstance(value, float) and not value.is_integer():
        sign = "+" if value > 0 else ""
        return f"{sign}{value:.1f}"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.0f}"


def build_publish_payload(experiment_dir: Path, comparison: dict[str, Any]) -> dict[str, Any]:
    manifest = _load_manifest(experiment_dir)
    arms = {
        arm: _arm_means(comparison, arm)
        for arm in ("baseline", "ponytail")
        if comparison.get(f"n_{arm}", 0)
    }
    deltas = {
        key: (comparison.get("summary") or {}).get(key, {}).get("delta_mean") for key in METRIC_KEYS
    }
    return {
        "experiment_id": experiment_dir.name,
        "date": manifest.get("date") or "",
        "problem": manifest.get("problem") or "unknown",
        "model": manifest.get("model") or "unknown",
        "thinking": (manifest.get("model_settings") or {}).get("thinking"),
        "agent": manifest.get("agent"),
        "agent_version": manifest.get("agent_version"),
        "n_baseline": comparison.get("n_baseline", 0),
        "n_ponytail": comparison.get("n_ponytail", 0),
        "excluded_ponytail_runs": comparison.get("excluded_ponytail_runs", 0),
        "arms": arms,
        "deltas": deltas,
        "git_commits": manifest.get("git_commits") or {},
        "ponytail": manifest.get("ponytail"),
        "pricing_version": manifest.get("pricing_version"),
    }


def _notes_from_payload(payload: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    b = (payload.get("arms") or {}).get("baseline") or {}
    p = (payload.get("arms") or {}).get("ponytail") or {}
    if not b or not p:
        return notes
    cp_b, cp_p = b.get("checkpoints_passed"), p.get("checkpoints_passed")
    if cp_b is not None and cp_p is not None:
        if cp_b == cp_p:
            notes.append(f"Same CP pass ({_fmt_checkpoints(b)}).")
        else:
            notes.append(
                f"CP pass baseline {_fmt_checkpoints(b)} vs ponytail {_fmt_checkpoints(p)}."
            )
    for key, label in (
        ("loc_final", "final LOC"),
        ("loc_changed", "changed LOC"),
        ("regression_failures", "regressions"),
        ("normalized_cost", "cost"),
        ("elapsed_time", "time"),
        ("complexity", "complexity"),
    ):
        bv, pv = b.get(key), p.get(key)
        if bv is None or pv is None:
            continue
        if pv < bv:
            notes.append(f"Ponytail lower {label} ({_fmt_metric(key, pv)} vs {_fmt_metric(key, bv)}).")
        elif pv > bv:
            notes.append(f"Ponytail higher {label} ({_fmt_metric(key, pv)} vs {_fmt_metric(key, bv)}).")
        if len(notes) >= 4:
            break
    return notes[:4]


def format_short_report(payload: dict[str, Any]) -> str:
    eid = payload["experiment_id"]
    thinking = payload.get("thinking") or "-"
    agent = payload.get("agent") or "-"
    agent_version = payload.get("agent_version") or "-"
    lines = [
        f"# {eid}",
        "",
        "| | |",
        "|---|---|",
        f"| Problem | `{payload.get('problem')}` |",
        f"| Model | `{payload.get('model')}` · thinking `{thinking}` |",
        f"| Agent | {agent} `{agent_version}` |",
        f"| N | baseline={payload.get('n_baseline')} · ponytail={payload.get('n_ponytail')} |",
        "| Pins | SCB / problems / ponytail — see published JSON / local manifest |",
        "",
        "## Metrics (mean)",
        "",
        "| Metric | Baseline | Ponytail | Δ |",
        "|--------|---------:|---------:|--:|",
    ]
    deltas = payload.get("deltas") or {}
    arms = payload.get("arms") or {}
    baseline = arms.get("baseline") or {}
    ponytail = arms.get("ponytail") or {}
    for key, label in SHORT_LABELS.items():
        baseline_value = (
            _fmt_checkpoints(baseline)
            if key == "checkpoints_passed"
            else _fmt_metric(key, baseline.get(key))
        )
        ponytail_value = (
            _fmt_checkpoints(ponytail)
            if key == "checkpoints_passed"
            else _fmt_metric(key, ponytail.get(key))
        )
        lines.append(
            f"| {label} | {baseline_value} | {ponytail_value} | "
            f"{_fmt_delta(key, deltas.get(key))} |"
        )
    notes = _notes_from_payload(payload)
    lines.extend(["", "## Notes", ""])
    if notes:
        lines.extend(f"- {n}" for n in notes)
    else:
        lines.append("- No paired baseline/ponytail means to summarize.")
    if payload.get("excluded_ponytail_runs"):
        lines.append(
            f"- Excluded ponytail runs (activation unverified): {payload['excluded_ponytail_runs']}."
        )
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
    """Flatten arm rows; keep newest experiment per (problem, model, harness)."""
    cells: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for payload in payloads:  # already newest-first
        problem = payload.get("problem") or "unknown"
        model = payload.get("model") or "unknown"
        for harness, metrics in (payload.get("arms") or {}).items():
            key = (problem, model, harness)
            if key in seen:
                continue
            seen.add(key)
            cells.append(
                {
                    "date": payload.get("date") or "",
                    "experiment_id": payload.get("experiment_id"),
                    "problem": problem,
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
        _fmt_metric("regression_failures", metrics.get("regression_failures")),
        _fmt_metric("normalized_cost", metrics.get("normalized_cost")),
        _fmt_metric("elapsed_time", metrics.get("elapsed_time")),
        _fmt_metric("loc_final", metrics.get("loc_final")),
        _fmt_metric("loc_changed", metrics.get("loc_changed")),
        _fmt_metric("dependencies_added", metrics.get("dependencies_added")),
        _fmt_metric("complexity", metrics.get("complexity")),
    ]
    return " | ".join(parts)


def _sort_table_rows(rows: list[dict[str, Any]], secondary: str) -> list[dict[str, Any]]:
    """Newest date first; within a date, secondary asc; baseline before ponytail."""
    ordered = sorted(
        rows,
        key=lambda c: (c[secondary], 0 if c["harness"] == "baseline" else 1),
    )
    return sorted(ordered, key=lambda c: c["date"], reverse=True)


def format_leaderboard(payloads: list[dict[str, Any]]) -> str:
    cells = _latest_cells(payloads)
    lines = [
        "# Leaderboard",
        "",
        "No single score. Absolute metrics only. Δ vs baseline is only in short reports",
        "for the same `(problem, model)` cell.",
        "",
        "Published from `docs/reports/*.json`. Rebuilt by `python -m benchmark report`.",
        "Newer experiments appear first.",
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
            "| Model | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |"
        )
        lines.append("|-------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|")
        rows = _sort_table_rows([c for c in cells if c["problem"] == problem], "model")
        for row in rows:
            lines.append(
                f"| {row['model']} | {row['harness']} | {row['n']} | {_metric_cells(row['metrics'])} |"
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
            "| Problem | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |"
        )
        lines.append("|---------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|")
        rows = _sort_table_rows([c for c in cells if c["model"] == model], "problem")
        for row in rows:
            lines.append(
                f"| {row['problem']} | {row['harness']} | {row['n']} | {_metric_cells(row['metrics'])} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Experiments",
            "",
            "| Experiment | Date | Problem | Model | N | Report |",
            "|------------|------|---------|-------|---|--------|",
        ]
    )
    for payload in payloads:
        eid = payload.get("experiment_id") or ""
        date = (payload.get("date") or "")[:10]
        n = f"{payload.get('n_baseline', 0)}+{payload.get('n_ponytail', 0)}"
        lines.append(
            f"| {eid} | {date} | {payload.get('problem')} | {payload.get('model')} | {n} | "
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

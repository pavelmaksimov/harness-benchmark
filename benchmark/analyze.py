from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.compare import compare_arms, format_comparison_report, load_experiment_runs
from benchmark.paths import DEFAULT_PROBLEM, REPORTS_DIR
from benchmark.publish import publish_short_report


def analyze_experiment(experiment_dir: Path) -> dict[str, Any]:
    by_arm = load_experiment_runs(experiment_dir)
    comparison = compare_arms(by_arm)
    comparison["experiment_dir"] = str(experiment_dir)
    return comparison


def write_reports(
    experiment_dir: Path,
    comparison: dict[str, Any] | None = None,
    *,
    problem: str = DEFAULT_PROBLEM,
) -> tuple[Path, Path]:
    comparison = comparison or analyze_experiment(experiment_dir)
    out_dir = REPORTS_DIR / experiment_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "comparison.json"
    txt_path = out_dir / "comparison.txt"
    json_path.write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(format_comparison_report(comparison, problem), encoding="utf-8")
    return json_path, txt_path


def write_reports_and_publish(
    experiment_dir: Path,
    comparison: dict[str, Any] | None = None,
    *,
    problem: str = DEFAULT_PROBLEM,
) -> tuple[Path, Path, Path, Path, Path]:
    comparison = comparison or analyze_experiment(experiment_dir)
    json_path, txt_path = write_reports(experiment_dir, comparison, problem=problem)
    short_md, short_json, board = publish_short_report(experiment_dir, comparison)
    return json_path, txt_path, short_md, short_json, board

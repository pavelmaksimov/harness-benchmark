from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from benchmark.analyze import analyze_experiment, write_reports_and_publish
from benchmark.arms import DEFAULT_EXPERIMENT_ARMS, known_arm_names
from benchmark.paths import (
    DEFAULT_MODEL,
    DEFAULT_PROBLEM,
    DEFAULT_RUNS,
    DEFAULT_THINKING,
    PROBLEMS_DIR,
    RESULTS_DIR,
    SCB_DIR,
)
from benchmark.scb_run import run_arm_repeats, run_matrix
from benchmark.versions import load_pins

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


@app.command("bootstrap")
def bootstrap() -> None:
    """Verify vendor pins and that file_backup is available."""
    pins = load_pins()
    console.print("pins:", pins)
    problem = PROBLEMS_DIR / "file_backup"
    if not problem.exists():
        raise typer.Exit(code=1)
    console.print(f"file_backup OK: {problem}")
    console.print(f"slop-code-bench: {SCB_DIR} @ {pins.get('slop-code-bench')}")
    console.print("Bootstrap checks passed.")


@app.command("run")
def run_cmd(
    arm: str = typer.Option(..., "--arm", help="|".join(known_arm_names())),
    problem: str = typer.Option(DEFAULT_PROBLEM, "--problem"),
    runs: int = typer.Option(1, "--runs", min=1),
    model: str = typer.Option(DEFAULT_MODEL, "--model"),
    thinking: str = typer.Option(DEFAULT_THINKING, "--thinking"),
    experiment_id: Optional[str] = typer.Option(None, "--experiment-id"),
    jobs: int = typer.Option(1, "--jobs", min=1, help="Max concurrent runs (1=serial)"),
) -> None:
    """Run one arm for N independent repetitions."""
    if arm not in known_arm_names():
        raise typer.BadParameter(f"arm must be one of: {', '.join(known_arm_names())}")
    experiment_id = experiment_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    console.print(
        f"experiment_id={experiment_id} arm={arm} runs={runs} jobs={jobs} "
        f"model={model} thinking={thinking}"
    )
    results = run_arm_repeats(
        arm=arm,
        problem=problem,
        runs=runs,
        model=model,
        thinking=thinking,
        experiment_id=experiment_id,
        jobs=jobs,
    )
    console.print(f"Completed {len(results)} runs → {RESULTS_DIR / experiment_id / arm}")


@app.command("run-all")
def run_all_cmd(
    problem: str = typer.Option(DEFAULT_PROBLEM, "--problem"),
    runs: int = typer.Option(DEFAULT_RUNS, "--runs", min=1),
    model: str = typer.Option(DEFAULT_MODEL, "--model"),
    thinking: str = typer.Option(DEFAULT_THINKING, "--thinking"),
    experiment_id: Optional[str] = typer.Option(None, "--experiment-id"),
    jobs: int = typer.Option(1, "--jobs", min=1, help="Max concurrent runs across arms (1=serial)"),
    arms: Optional[str] = typer.Option(
        None,
        "--arms",
        help="Comma-separated arms (default: all registered experiment arms)",
    ),
) -> None:
    """Run selected arms × N, then write comparison report."""
    experiment_id = experiment_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    selected = tuple(a.strip() for a in arms.split(",")) if arms else DEFAULT_EXPERIMENT_ARMS
    unknown = [a for a in selected if a not in known_arm_names()]
    if unknown:
        raise typer.BadParameter(f"unknown arms: {', '.join(unknown)}")
    console.print(
        f"=== run-all × {runs} jobs={jobs} model={model} thinking={thinking} "
        f"arms={','.join(selected)} experiment_id={experiment_id} ==="
    )
    run_matrix(
        arms=selected,
        problem=problem,
        runs=runs,
        model=model,
        thinking=thinking,
        experiment_id=experiment_id,
        jobs=jobs,
    )
    report_cmd(experiment_id=experiment_id, problem=problem)


@app.command("report")
def report_cmd(
    experiment_id: Optional[str] = typer.Option(None, "--experiment-id"),
    problem: str = typer.Option(DEFAULT_PROBLEM, "--problem"),
) -> None:
    """Build comparison report for an experiment directory."""
    if experiment_id is None:
        experiments = (
            sorted([p for p in RESULTS_DIR.iterdir() if p.is_dir()]) if RESULTS_DIR.exists() else []
        )
        if not experiments:
            console.print("No experiments found in results/")
            raise typer.Exit(code=1)
        experiment_dir = experiments[-1]
    else:
        experiment_dir = RESULTS_DIR / experiment_id
    comparison = analyze_experiment(experiment_dir)
    json_path, txt_path, short_md, short_json, board = write_reports_and_publish(
        experiment_dir, comparison
    )
    console.print(txt_path.read_text(encoding="utf-8"))
    console.print(f"Wrote {txt_path} and {json_path}")
    console.print(f"Published {short_md}, {short_json}, {board}")


@app.command("collect")
def collect_cmd(
    scb_problem_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    arm: str = typer.Option(..., "--arm"),
    run_id: str = typer.Option("manual", "--run-id"),
    problem: str = typer.Option(DEFAULT_PROBLEM, "--problem"),
    model: str = typer.Option(DEFAULT_MODEL, "--model"),
    out: Path = typer.Option(..., "--out", help="Directory for metrics JSON"),
) -> None:
    """Collect unified metrics from an existing SCB problem output directory."""
    from benchmark.collect import collect_run, write_checkpoint_jsons
    from benchmark.paths import CONFIGS_DIR
    from benchmark.versions import load_arm_meta, load_pins

    pins = load_pins()
    environment = {
        "agent": "codex",
        "agent_version": pins.get("codex_cli_host_version"),
        "model": model,
        "slop_code_commit": pins.get("slop-code-bench"),
        "problems_commit": pins.get("scb-problems"),
        "harness_meta": load_arm_meta(arm),
        "ponytail_commit": pins.get("ponytail_version") if arm == "ponytail" else None,
        "harness": arm,
    }
    collected = collect_run(
        scb_problem_dir=scb_problem_dir,
        run_id=run_id,
        arm=arm,
        problem=problem,
        environment=environment,
        pricing_path=CONFIGS_DIR / "pricing.yaml",
    )
    write_checkpoint_jsons(collected, out)
    console.print(f"Wrote metrics to {out}")


if __name__ == "__main__":
    app()

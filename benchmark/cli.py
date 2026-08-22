from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console

from benchmark.analyze import analyze_experiment, write_reports_and_publish
from benchmark.arms import DEFAULT_EXPERIMENT_ARMS, known_arm_names
from benchmark.paths import (
    DEFAULT_AGENT,
    DEFAULT_MODEL,
    DEFAULT_PROBLEM,
    DEFAULT_PROVIDER,
    DEFAULT_RUNS,
    DEFAULT_THINKING,
    PROBLEMS_DIR,
    RESULTS_DIR,
    SCB_DIR,
    SUPPORTED_AGENTS,
)
from benchmark.scb_run import (
    DEFAULT_FEEDBACK_STRATEGY,
    new_experiment_id,
    resolve_run_selection,
    run_arm_repeats,
    run_matrix,
    run_smoke,
)
from benchmark.versions import load_pins

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


def _validate_selection(
    *,
    agent: Optional[str],
    arm: str,
    provider: Optional[str],
    model: Optional[str],
    thinking: Optional[str],
) -> tuple[str, str, str, str]:
    try:
        return resolve_run_selection(
            agent=agent,
            arm=arm,
            provider=provider,
            model=model,
            thinking=thinking,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("bootstrap")
def bootstrap() -> None:
    """Verify vendor pins and that file_backup / task_manager are available."""
    pins = load_pins()
    console.print("pins:", pins)
    problem = PROBLEMS_DIR / "file_backup"
    if not problem.exists():
        raise typer.Exit(code=1)
    console.print(f"file_backup OK: {problem}")
    task_manager = PROBLEMS_DIR / "task_manager"
    if not task_manager.exists():
        console.print(
            "[yellow]task_manager missing under vendor/scb-problems; "
            "run bash scripts/sync_task_manager_problem.sh[/yellow]"
        )
        raise typer.Exit(code=1)
    console.print(f"task_manager OK: {task_manager}")
    console.print(f"slop-code-bench: {SCB_DIR} @ {pins.get('slop-code-bench')}")
    console.print("Bootstrap checks passed.")


@app.command("smoke")
def smoke_cmd(
    arm: str = typer.Option(..., "--arm", help="Skill harness arm to validate"),
    problem: str = typer.Option(DEFAULT_PROBLEM, "--problem"),
    agent: str = typer.Option(DEFAULT_AGENT, "--agent", help="|".join(SUPPORTED_AGENTS)),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        help=f"Credential provider (Codex default: {DEFAULT_PROVIDER}; required for OpenCode)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help=f"Model name (Codex default: {DEFAULT_MODEL}; required for OpenCode)",
    ),
    thinking: Optional[str] = typer.Option(
        None,
        "--thinking",
        help=f"Thinking preset (Codex default: {DEFAULT_THINKING})",
    ),
    checkpoints: int = typer.Option(
        1,
        "--checkpoints",
        min=1,
        help="How many leading checkpoints to run (1 = classic CP1 smoke gate)",
    ),
    experiment_id: Optional[str] = typer.Option(None, "--experiment-id"),
) -> None:
    """CP1-only smoke: verify harness runs and discover non-solution artifact dirs."""
    from benchmark.arms import get_arm
    from benchmark.smoke import is_smoke_validated

    if arm not in known_arm_names():
        raise typer.BadParameter(f"arm must be one of: {', '.join(known_arm_names())}")
    if not get_arm(arm).needs_hook:
        console.print("baseline does not need smoke validation.")
        raise typer.Exit(code=0)
    agent, provider, model, thinking = _validate_selection(
        agent=agent,
        arm=arm,
        provider=provider,
        model=model,
        thinking=thinking,
    )
    console.print(
        f"=== smoke CP{checkpoints} arm={arm} agent={agent} provider={provider} "
        f"model={model} thinking={thinking} ==="
    )
    collected = run_smoke(
        arm=arm,
        problem=problem,
        agent=agent,
        provider=provider,
        model=model,
        thinking=thinking,
        experiment_id=experiment_id,
        checkpoint_count=checkpoints,
    )
    analysis = collected.get("smoke_snapshot_analysis") or {}
    console.print(f"smoke_ok={collected.get('smoke_ok')} marker={collected.get('smoke_marker')}")
    console.print(f"activation_verified={collected.get('harness_activation_verified')}")
    console.print(f"snapshot top-level dirs: {analysis.get('top_level_dirs')}")
    needs = analysis.get("needs_exclude_review") or []
    if needs:
        console.print(
            "[yellow]Review these dirs for EXCLUDE_DIR_NAMES "
            f"(benchmark/structure.py): {needs}[/yellow]"
        )
    else:
        console.print("No obvious new artifact dirs flagged for exclusion review.")
    if not collected.get("smoke_ok") or not is_smoke_validated(arm):
        console.print("[red]Smoke failed — fix harness before full runs.[/red]")
        raise typer.Exit(code=1)
    console.print(
        "[green]Smoke passed. Commit harnesses/<arm>/SMOKE.json after updating exclusions.[/green]"
    )


@app.command("validate-problem")
def validate_problem_cmd(
    problem: str = typer.Option("task_manager", "--problem"),
    sync: bool = typer.Option(True, "--sync/--no-sync", help="Run task_manager symlink sync"),
) -> None:
    """Offline readiness: sync, catalog, CP1 staging, smoke markers (no Docker/Codex)."""
    from benchmark.validate_problem import validate_problem

    report = validate_problem(problem, sync=sync)
    for check in report.checks:
        mark = "[green]ok[/green]" if check.ok else "[red]FAIL[/red]"
        console.print(f"{mark} {check.name}: {check.detail}")
    if not report.ok:
        console.print("[red]validate-problem failed[/red]")
        raise typer.Exit(code=1)
    console.print(
        f"[green]validate-problem passed[/green] problem={problem} "
        f"default_problem={DEFAULT_PROBLEM} (unchanged)"
    )


@app.command("run")
def run_cmd(
    arm: str = typer.Option(..., "--arm", help="|".join(known_arm_names())),
    problem: str = typer.Option(DEFAULT_PROBLEM, "--problem"),
    runs: int = typer.Option(1, "--runs", min=1),
    agent: Optional[str] = typer.Option(None, "--agent", help="|".join(SUPPORTED_AGENTS)),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        help=f"Credential provider (Codex default: {DEFAULT_PROVIDER}; required for OpenCode)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help=f"Model name (Codex default: {DEFAULT_MODEL}; required for OpenCode)",
    ),
    thinking: Optional[str] = typer.Option(
        None,
        "--thinking",
        help=f"Thinking preset (Codex default: {DEFAULT_THINKING})",
    ),
    experiment_id: Optional[str] = typer.Option(None, "--experiment-id"),
    jobs: int = typer.Option(1, "--jobs", min=1, help="Max concurrent runs (1=serial)"),
    skip_smoke_check: bool = typer.Option(
        False,
        "--skip-smoke-check",
        help="Allow full run even if harness lacks CP1 smoke validation",
    ),
    rework_attempts: Optional[int] = typer.Option(
        None,
        "--rework-attempts",
        min=0,
        help="Extra agent attempts per checkpoint when tests fail (0 disables)",
    ),
    transient_retries: Optional[int] = typer.Option(
        None,
        "--transient-retries",
        min=0,
        help="Extra retries for high-confidence provider truncation (0 disables)",
    ),
    feedback_strategy: Optional[str] = typer.Option(
        None,
        "--feedback-strategy",
        help=f"Rework feedback strategy (default: {DEFAULT_FEEDBACK_STRATEGY})",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help="Continue interrupted runs via their state.json (requires --experiment-id)",
    ),
) -> None:
    """Run one arm for N independent repetitions."""
    if resume and experiment_id is None:
        raise typer.BadParameter("--resume requires an explicit --experiment-id")
    if arm not in known_arm_names():
        raise typer.BadParameter(f"arm must be one of: {', '.join(known_arm_names())}")
    # On --resume run_one restores flags from state.json; defaults here would shadow them.
    if not resume:
        agent, provider, model, thinking = _validate_selection(
            agent=agent,
            arm=arm,
            provider=provider,
            model=model,
            thinking=thinking,
        )
    experiment_id = experiment_id or new_experiment_id()
    console.print(
        f"experiment_id={experiment_id} arm={arm} runs={runs} jobs={jobs} "
        f"agent={agent or '(state.json)'} provider={provider or '(state.json)'} "
        f"model={model or '(state.json)'} thinking={thinking or '(state.json)'} "
        f"transient_retries={transient_retries if transient_retries is not None else '(state.json)'} "
        f"feedback_strategy={feedback_strategy or '(state.json)'}"
    )
    try:
        results = run_arm_repeats(
            arm=arm,
            problem=problem,
            runs=runs,
            agent=agent,
            provider=provider,
            model=model,
            thinking=thinking,
            experiment_id=experiment_id,
            jobs=jobs,
            skip_smoke_check=skip_smoke_check,
            rework_attempts=rework_attempts,
            transient_retries=transient_retries,
            feedback_strategy=feedback_strategy,
            resume=resume,
        )
    except (RuntimeError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    console.print(f"Completed {len(results)} runs → {RESULTS_DIR / experiment_id / arm}")


@app.command("run-all")
def run_all_cmd(
    problem: str = typer.Option(DEFAULT_PROBLEM, "--problem"),
    runs: int = typer.Option(DEFAULT_RUNS, "--runs", min=1),
    agent: Optional[str] = typer.Option(None, "--agent", help="|".join(SUPPORTED_AGENTS)),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        help=f"Credential provider (Codex default: {DEFAULT_PROVIDER}; required for OpenCode)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help=f"Model name (Codex default: {DEFAULT_MODEL}; required for OpenCode)",
    ),
    thinking: Optional[str] = typer.Option(
        None,
        "--thinking",
        help=f"Thinking preset (Codex default: {DEFAULT_THINKING})",
    ),
    experiment_id: Optional[str] = typer.Option(None, "--experiment-id"),
    jobs: int = typer.Option(1, "--jobs", min=1, help="Max concurrent runs across arms (1=serial)"),
    arms: Optional[str] = typer.Option(
        None,
        "--arms",
        help="Comma-separated arms (default: all registered experiment arms)",
    ),
    skip_smoke_check: bool = typer.Option(
        False,
        "--skip-smoke-check",
        help="Allow full run even if harness lacks CP1 smoke validation",
    ),
    rework_attempts: Optional[int] = typer.Option(
        None,
        "--rework-attempts",
        min=0,
        help="Extra agent attempts per checkpoint when tests fail (0 disables)",
    ),
    transient_retries: Optional[int] = typer.Option(
        None,
        "--transient-retries",
        min=0,
        help="Extra retries for high-confidence provider truncation (0 disables)",
    ),
    feedback_strategy: Optional[str] = typer.Option(
        None,
        "--feedback-strategy",
        help=f"Rework feedback strategy (default: {DEFAULT_FEEDBACK_STRATEGY})",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help="Continue interrupted runs via their state.json (requires --experiment-id)",
    ),
) -> None:
    """Run selected arms × N, then write comparison report."""
    if resume and experiment_id is None:
        raise typer.BadParameter("--resume requires an explicit --experiment-id")
    experiment_id = experiment_id or new_experiment_id()
    selected = tuple(a.strip() for a in arms.split(",")) if arms else DEFAULT_EXPERIMENT_ARMS
    unknown = [a for a in selected if a not in known_arm_names()]
    if unknown:
        raise typer.BadParameter(f"unknown arms: {', '.join(unknown)}")
    # Validate against first arm for shared agent/provider/model; matrix re-checks each arm.
    # On --resume, omitted flags are restored from state.json inside run_one.
    if not resume:
        agent, provider, model, thinking = _validate_selection(
            agent=agent,
            arm=selected[0],
            provider=provider,
            model=model,
            thinking=thinking,
        )
    console.print(
        f"=== run-all × {runs} jobs={jobs} agent={agent or '(state.json)'} "
        f"provider={provider or '(state.json)'} model={model or '(state.json)'} "
        f"thinking={thinking or '(state.json)'} "
        f"transient_retries={transient_retries if transient_retries is not None else '(state.json)'} "
        f"feedback_strategy={feedback_strategy or '(state.json)'} "
        f"arms={','.join(selected)} experiment_id={experiment_id} ==="
    )
    try:
        run_matrix(
            arms=selected,
            problem=problem,
            runs=runs,
            agent=agent,
            provider=provider,
            model=model,
            thinking=thinking,
            experiment_id=experiment_id,
            jobs=jobs,
            skip_smoke_check=skip_smoke_check,
            rework_attempts=rework_attempts,
            transient_retries=transient_retries,
            feedback_strategy=feedback_strategy,
            resume=resume,
        )
    except (RuntimeError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        if (RESULTS_DIR / experiment_id).is_dir():
            try:
                report_cmd(experiment_id=experiment_id, problem=problem)
            except (OSError, ValueError):
                pass
        raise typer.Exit(code=1) from exc
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
        experiment_dir, comparison, problem=problem
    )
    console.print(txt_path.read_text(encoding="utf-8"))
    console.print(f"Wrote {txt_path} and {json_path}")
    console.print(f"Published {short_md}, {short_json}, {board}")


def _format_status_line(state: dict[str, Any]) -> str:
    done = state.get("last_completed_checkpoint") or "-"
    if state.get("fully_completed"):
        endpoint = state.get("interrupt_reason") or "ok"
    elif state.get("stopped_at_checkpoint"):
        endpoint = f"-> {state['stopped_at_checkpoint']}"
    else:
        endpoint = state.get("interrupt_reason") or "?"
    bits = [
        f"{name}[{status}]"
        for name, status in (state.get("checkpoints") or {}).items()
        if status != "done"
    ]
    suffix = f"  rerun: {', '.join(bits)}" if bits else ""
    return (
        f"{state.get('experiment_id', '?')}/{state.get('arm', '?')}/"
        f"run_{state.get('run_index', '?')} done={done} stop={endpoint}{suffix}"
    )


@app.command("status")
def status_cmd(
    experiment_id: str | None = typer.Option(None, "--experiment-id"),
) -> None:
    """Read-only overview of runs via their state.json (no SCB/Docker)."""
    from benchmark.resume_state import load_state, run_dirs

    if RESULTS_DIR.is_dir():
        experiments = sorted(p.name for p in RESULTS_DIR.iterdir() if p.is_dir())
    else:
        experiments = []
    selected = [experiment_id] if experiment_id else experiments
    if not selected:
        console.print("No experiments found in results/")
        raise typer.Exit(code=1)
    lines: list[str] = []
    for exp in selected:
        exp_dir = RESULTS_DIR / exp
        if not exp_dir.is_dir():
            console.print(f"[red]experiment not found:[/red] {exp}")
            raise typer.Exit(code=1)
        states: list[dict[str, Any]] = []
        stale: list[str] = []
        for run_dir in run_dirs(exp_dir):
            state = load_state(run_dir)
            if state is None:
                stale.append(f"{run_dir.parent.name}/{run_dir.name}")
            else:
                states.append(state)
        lines.extend(_format_status_line(state) for state in states)
        if stale:
            lines.append("legacy (no state.json; start fresh, --resume unavailable): " + ", ".join(stale))
    if not lines:
        console.print("No state.json found under results/ — nothing tracked yet.")
        raise typer.Exit(code=0)
    for line in lines:
        console.print(line)


@app.command("repair")
def repair_cmd(
    experiment_id: str = typer.Option(..., "--experiment-id"),
    arm: str = typer.Option("baseline", "--arm", help="|".join(known_arm_names())),
    run_index: int = typer.Option(1, "--run", min=1),
    problem: Optional[str] = typer.Option(
        None, "--problem", help="Defaults to the problem in manifest.json"
    ),
    fix_snapshot: Optional[Path] = typer.Option(
        None,
        "--fix-snapshot",
        help="Fixed snapshot dir to copy over the failed checkpoint's snapshot",
    ),
    fixer_agent: Optional[str] = typer.Option(
        None,
        "--fixer-agent",
        help="Run a fixer agent on the snapshot (supported: opencode)",
    ),
    fixer_model: Optional[str] = typer.Option(
        None,
        "--fixer-model",
        help="Model for the fixer agent (e.g. deepseek-v4-flash-free)",
    ),
    root_cause: Optional[str] = typer.Option(
        None, "--root-cause", help="Root-cause note to record with the failure"
    ),
    fix: Optional[str] = typer.Option(
        None, "--fix", help="Description of the applied fix to record"
    ),
    no_resume: bool = typer.Option(
        False,
        "--no-resume",
        help="Record + fix + verify only; do not continue the SCB run",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Record the failure only (no snapshot change, no SCB run)",
    ),
) -> None:
    """Record a model failure and (optionally) fix + continue the run."""
    from benchmark.repair import repair_run

    try:
        result = repair_run(
            experiment_id=experiment_id,
            arm=arm,
            run_index=run_index,
            problem=problem,
            fix_snapshot_dir=Path(fix_snapshot) if fix_snapshot else None,
            fixer_agent=fixer_agent,
            fixer_model=fixer_model,
            root_cause=root_cause,
            fix=fix,
            no_resume=no_resume,
            dry_run=dry_run,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    console.print(f"status={result.get('status')} problem={result.get('problem')}")
    if result.get("checkpoint"):
        console.print(f"checkpoint={result['checkpoint']}")
    if result.get("failures_path"):
        console.print(f"failures_file={result['failures_path']}")
    if result.get("verification"):
        v = result["verification"]
        console.print(f"verification: {v['passed']} passed / {v['failed']} failed")
    if result.get("backup_dir"):
        console.print(f"backup_dir={result['backup_dir']}")
    if result.get("resume_log"):
        console.print(f"resume_log={result['resume_log']}")


@app.command("collect")
def collect_cmd(
    scb_problem_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    arm: str = typer.Option(..., "--arm"),
    run_id: str = typer.Option("manual", "--run-id"),
    problem: str = typer.Option(DEFAULT_PROBLEM, "--problem"),
    agent: str = typer.Option(DEFAULT_AGENT, "--agent", help="|".join(SUPPORTED_AGENTS)),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        help=f"Credential provider (default: {DEFAULT_PROVIDER})",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help=f"Model name (default: {DEFAULT_MODEL})",
    ),
    out: Path = typer.Option(..., "--out", help="Directory for metrics JSON"),
) -> None:
    """Collect unified metrics from an existing SCB problem output directory."""
    from benchmark.collect import collect_run, write_checkpoint_jsons
    from benchmark.paths import CONFIGS_DIR
    from benchmark.arms import arm_includes
    from benchmark.versions import load_arm_meta, load_pins

    pins = load_pins()
    resolved_provider = provider or DEFAULT_PROVIDER
    resolved_model = model or DEFAULT_MODEL
    if agent == "opencode":
        agent_version = pins.get("opencode_cli_version")
    else:
        agent_version = pins.get("codex_cli_host_version")
    environment = {
        "agent": agent,
        "agent_version": agent_version,
        "provider": resolved_provider,
        "model": resolved_model,
        "slop_code_commit": pins.get("slop-code-bench"),
        "problems_commit": pins.get("scb-problems"),
        "harness_meta": load_arm_meta(arm),
        "ponytail_commit": (
            pins.get("ponytail_version") if arm_includes(arm, "ponytail") else None
        ),
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

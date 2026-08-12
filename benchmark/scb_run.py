from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmark.collect import collect_run, write_checkpoint_jsons
from benchmark.manifest import build_manifest, write_manifest
from benchmark.paths import (
    CONFIGS_DIR,
    DEFAULT_MODEL,
    DEFAULT_PROBLEM,
    DEFAULT_THINKING,
    PROBLEMS_DIR,
    REPO_ROOT,
    RESULTS_DIR,
    SCB_DIR,
)
from benchmark.versions import load_pins


def _arm_config(arm: str) -> Path:
    if arm == "baseline":
        return CONFIGS_DIR / "baseline.yaml"
    if arm == "ponytail":
        return CONFIGS_DIR / "ponytail.yaml"
    raise ValueError(f"Unknown arm: {arm}")


def _resolve_config_paths(config_path: Path) -> Path:
    """Return absolute config path; SCB resolves relative paths from CWD."""
    return config_path if config_path.is_absolute() else (REPO_ROOT / config_path)


def run_slop_code(
    *,
    arm: str,
    problem: str = DEFAULT_PROBLEM,
    thinking: str = DEFAULT_THINKING,
    model: str = DEFAULT_MODEL,
    output_dir: Path,
    dry_run: bool = False,
) -> Path:
    """Invoke SlopCodeBench run for one arm into output_dir."""
    config = _resolve_config_paths(_arm_config(arm))
    agent = _resolve_config_paths(CONFIGS_DIR / "agent_codex.yaml")
    prompt = _resolve_config_paths(
        CONFIGS_DIR
        / "prompts"
        / ("ponytail-solve.jinja" if arm == "ponytail" else "just-solve.jinja")
    )

    env = os.environ.copy()
    env["SCBENCH_PROBLEMS_PATH"] = str(PROBLEMS_DIR)
    # Keep SCB cache separate per arm/run for isolation of catalog state.
    env["SCBENCH_HOME"] = str(output_dir / ".scbench_home")
    env["HB_ARM"] = arm
    env["HB_RUN_OUTPUT"] = str(output_dir)
    # Ensure sitecustomize runs inside ProcessPool workers too.
    env["PYTHONPATH"] = os.pathsep.join(
        p
        for p in [
            str(REPO_ROOT / "harness_sitecustomize"),
            str(REPO_ROOT),
            env.get("PYTHONPATH", ""),
        ]
        if p
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    # docker-py fails when host Docker config has broken credHelpers (e.g. yc).
    # Public base images used by SCB do not need those helpers.
    docker_config_dir = output_dir / ".docker"
    docker_config_dir.mkdir(parents=True, exist_ok=True)
    (docker_config_dir / "config.json").write_text('{"auths": {}}\n', encoding="utf-8")
    env["DOCKER_CONFIG"] = str(docker_config_dir)

    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "benchmark.scb_main",
        "run",
        "--config",
        str(config),
        "--agent",
        str(agent),
        "--prompt",
        str(prompt),
        "--environment",
        str(SCB_DIR / "configs" / "environments" / "docker-python3.12-uv.yaml"),
        "--model",
        f"codex_auth/{model}",
        "--problem",
        problem,
        f"thinking={thinking}",
        f"save_dir={output_dir}",
        "save_template=scb",
    ]
    if dry_run:
        return output_dir

    if arm == "ponytail":
        env["HB_ENABLE_PONYTAIL"] = "1"
    else:
        env.pop("HB_ENABLE_PONYTAIL", None)

    log_path = output_dir / "scb_run.log"
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            check=False,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
    (output_dir / "scb_exit_code.txt").write_text(str(proc.returncode), encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            f"slop-code run failed for arm={arm} (exit {proc.returncode}); see {log_path}"
        )
    return output_dir


def find_scb_problem_dir(scb_root: Path, problem: str) -> Path:
    direct = scb_root / problem
    if direct.exists():
        return direct
    matches = list(scb_root.rglob(problem))
    for match in matches:
        if match.is_dir() and (match / "checkpoint_1").exists():
            return match
    raise FileNotFoundError(f"Could not find SCB problem dir for {problem} under {scb_root}")


def run_one(
    *,
    arm: str,
    problem: str = DEFAULT_PROBLEM,
    thinking: str = DEFAULT_THINKING,
    model: str = DEFAULT_MODEL,
    run_index: int = 1,
    experiment_id: str | None = None,
) -> dict[str, Any]:
    experiment_id = experiment_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_id = f"{experiment_id}-{arm}-r{run_index}-{uuid.uuid4().hex[:8]}"
    out_dir = RESULTS_DIR / experiment_id / arm / f"run_{run_index}"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pins = load_pins()
    run_slop_code(
        arm=arm,
        problem=problem,
        thinking=thinking,
        model=model,
        output_dir=out_dir,
    )

    scb_problem_dir = find_scb_problem_dir(out_dir / "scb", problem)
    environment = {
        "agent": "codex",
        "agent_version": pins.get("codex_cli_host_version"),
        "model": model,
        "thinking": thinking,
        "slop_code_commit": pins.get("slop-code-bench"),
        "problems_commit": pins.get("scb-problems"),
        "ponytail_commit": pins.get("ponytail_version") if arm == "ponytail" else None,
        "harness": arm,
        "docker_image": "ghcr.io/astral-sh/uv:python3.12-trixie-slim",
    }
    collected = collect_run(
        scb_problem_dir=scb_problem_dir,
        run_id=run_id,
        arm=arm,
        problem=problem,
        environment=environment,
        pricing_path=CONFIGS_DIR / "pricing.yaml",
    )
    metrics_dir = out_dir / "metrics"
    write_checkpoint_jsons(collected, metrics_dir)

    # Activation gate for ponytail
    if arm == "ponytail":
        verified = all(
            cp.get("harness", {}).get("harness_activation_verified")
            for cp in collected["checkpoints"]
        )
        collected["harness_activation_verified"] = verified
        (metrics_dir / "activation.json").write_text(
            __import__("json").dumps(
                {
                    "harness_activation_verified": verified,
                    "checkpoints": [
                        {
                            "checkpoint": cp["checkpoint"],
                            "verified": cp.get("harness", {}).get("harness_activation_verified"),
                        }
                        for cp in collected["checkpoints"]
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if not verified:
            collected["excluded_from_comparison"] = True

    manifest = build_manifest(
        experiment_id=experiment_id,
        arm=arm,
        problem=problem,
        model=model,
        thinking=thinking,
        runs=1,
        docker_image=environment["docker_image"],
        pricing_path=CONFIGS_DIR / "pricing.yaml",
        extra={"run_id": run_id, "run_index": run_index},
    )
    write_manifest(out_dir / "manifest.json", manifest)
    collected["manifest"] = manifest
    (metrics_dir / "run.json").write_text(
        __import__("json").dumps(collected, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return collected


def run_arm_repeats(
    *,
    arm: str,
    problem: str = DEFAULT_PROBLEM,
    runs: int = 3,
    thinking: str = DEFAULT_THINKING,
    model: str = DEFAULT_MODEL,
    experiment_id: str | None = None,
) -> list[dict[str, Any]]:
    experiment_id = experiment_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    results = []
    for idx in range(1, runs + 1):
        results.append(
            run_one(
                arm=arm,
                problem=problem,
                thinking=thinking,
                model=model,
                run_index=idx,
                experiment_id=experiment_id,
            )
        )
    return results

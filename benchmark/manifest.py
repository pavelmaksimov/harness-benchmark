from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmark.paths import CONFIGS_DIR, REPO_ROOT
from benchmark.versions import (
    capture_codex_version,
    env_var_names,
    git_head,
    load_arm_meta,
    load_pins,
    load_ponytail_meta,
    sha256_file,
)


def build_manifest(
    *,
    experiment_id: str,
    arm: str,
    problem: str,
    model: str,
    thinking: str,
    runs: int,
    docker_image: str,
    pricing_path: Path,
    harness_version: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pins = load_pins()
    pricing_text = pricing_path.read_text(encoding="utf-8")
    import yaml

    pricing = yaml.safe_load(pricing_text)
    harness_meta = load_arm_meta(arm)
    ponytail = load_ponytail_meta() if arm == "ponytail" else None

    manifest = {
        "date": datetime.now(timezone.utc).isoformat(),
        "experiment_id": experiment_id,
        "problem": problem,
        "arm": arm,
        "harness": arm,
        "harness_version": harness_version
        or ((harness_meta or {}).get("version") if harness_meta else "none"),
        "number_of_runs": runs,
        "agent": "codex",
        "agent_version": pins.get("codex_cli_host_version") or capture_codex_version(),
        "codex_host_version": capture_codex_version(),
        "model": model,
        "model_settings": {
            "thinking": thinking,
            "provider": "codex_auth",
        },
        "git_commits": {
            "harness_benchmark": git_head(REPO_ROOT),
            "slop_code_bench": pins.get("slop-code-bench"),
            "scb_problems": pins.get("scb-problems"),
        },
        "harness_meta": harness_meta,
        "ponytail": ponytail,
        "docker_image": docker_image,
        "pricing_version": pricing.get("version") if isinstance(pricing, dict) else None,
        "pricing_sha256": sha256_file(pricing_path),
        "environment_variable_names": env_var_names(),
        "notes": (
            "Secrets/API keys are intentionally omitted; only env var names are listed."
        ),
    }
    if extra:
        manifest["extra"] = extra
    return manifest


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

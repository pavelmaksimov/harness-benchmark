"""Optional blind LLM architecture judge (does not affect correctness)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

JUDGE_PROMPT_VERSION = "v1"
JUDGE_SCHEMA = {
    "simplicity": "1-5",
    "maintainability": "1-5",
    "modularity": "1-5",
    "unnecessary_abstractions": "1-5 (5=many unnecessary)",
    "duplication": "1-5 (5=lots of duplication)",
    "change_locality": "1-5",
}


def build_judge_prompt(*, specs: list[str], source_files: dict[str, str]) -> str:
    files_blob = "\n\n".join(
        f"### {path}\n```\n{content}\n```" for path, content in sorted(source_files.items())
    )
    specs_blob = "\n\n".join(f"## Spec {i + 1}\n{spec}" for i, spec in enumerate(specs))
    return f"""You are a blind code architecture judge. You do NOT know which agent produced this code.
Score each dimension from 1 to 5 (integers only).

Dimensions:
{json.dumps(JUDGE_SCHEMA, indent=2)}

Return ONLY valid JSON:
{{
  "simplicity": 1,
  "maintainability": 1,
  "modularity": 1,
  "unnecessary_abstractions": 1,
  "duplication": 1,
  "change_locality": 1,
  "notes": "short"
}}

{specs_blob}

## Source
{files_blob}
"""


def collect_source_files(snapshot_dir: Path, limit: int = 40) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(snapshot_dir.rglob("*.py")):
        if any(part.startswith(".") for part in path.parts):
            continue
        if "tests" in path.parts:
            continue
        rel = str(path.relative_to(snapshot_dir))
        out[rel] = path.read_text(encoding="utf-8", errors="replace")[:20000]
        if len(out) >= limit:
            break
    return out


def run_judge_codex(
    *,
    snapshot_dir: Path,
    specs: list[str],
    model: str | None = None,
    workdir: Path | None = None,
) -> dict[str, Any]:
    """Run optional judge via `codex exec`. Failures return structured null scores."""
    prompt = build_judge_prompt(specs=specs, source_files=collect_source_files(snapshot_dir))
    out_file = (workdir or snapshot_dir) / "judge_last_message.md"
    log_file = (workdir or snapshot_dir) / "judge.log"
    cmd = [
        "codex",
        "exec",
        "-s",
        "read-only",
        "--skip-git-repo-check",
        "-o",
        str(out_file),
        prompt,
    ]
    if model:
        cmd.extend(["-m", model])

    proc = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=600,
    )
    log_file.write_text((proc.stdout or "") + "\n" + (proc.stderr or ""), encoding="utf-8")
    raw = out_file.read_text(encoding="utf-8") if out_file.exists() else ""
    scores = _parse_scores(raw)
    return {
        "judge_model": model or "codex-default",
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "judge_raw_response": raw,
        "judge_scores": scores,
        "judge_exit_code": proc.returncode,
    }


def _parse_scores(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        # Prefer fenced JSON if present.
        if "```" in raw:
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                raw = raw[start : end + 1]
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        return {k: data.get(k) for k in JUDGE_SCHEMA}
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start : end + 1])
                return {k: data.get(k) for k in JUDGE_SCHEMA}
            except json.JSONDecodeError:
                return None
        return None

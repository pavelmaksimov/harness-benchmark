from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from benchmark.paths import (
    ACTIVATION_MARKER,
    PONYTAIL_SKILL_PATH,
    PONYTAIL_VERSION_PATH,
    VENDOR_PINS_PATH,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_pins() -> dict[str, Any]:
    return load_json(VENDOR_PINS_PATH)


def load_ponytail_meta() -> dict[str, Any]:
    meta = load_json(PONYTAIL_VERSION_PATH)
    meta["skill_path"] = str(PONYTAIL_SKILL_PATH)
    meta["skill_sha256_actual"] = sha256_file(PONYTAIL_SKILL_PATH)
    return meta


def capture_codex_version() -> str | None:
    try:
        proc = subprocess.run(
            ["codex", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (proc.stdout or proc.stderr or "").strip()
    for line in text.splitlines():
        if "codex" in line.lower() or line.strip()[:1].isdigit():
            return line.strip()
    return text or None


def env_var_names() -> list[str]:
    names = []
    for key in sorted(os.environ):
        upper = key.upper()
        if any(
            token in upper
            for token in (
                "API_KEY",
                "TOKEN",
                "SECRET",
                "PASSWORD",
                "AUTH",
                "CREDENTIAL",
            )
        ):
            names.append(key)
        elif key.startswith(("SCBENCH_", "HB_", "OPENAI_", "ANTHROPIC_")):
            names.append(key)
    return names


def git_head(path: Path) -> str | None:
    if not (path / ".git").exists():
        return None
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def copy_ponytail_skill(dest_skills_root: Path) -> dict[str, Any]:
    """Install pinned ponytail skill into a Codex home skills directory."""
    dest = dest_skills_root / "ponytail"
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / "SKILL.md"
    shutil.copy2(PONYTAIL_SKILL_PATH, target)
    meta = load_ponytail_meta()
    actual = sha256_file(target)
    verified = actual == meta["skill_sha256"]
    marker = {
        "harness": "ponytail",
        "skill_name": "ponytail",
        "skill_version": meta["version"],
        "skill_sha256_expected": meta["skill_sha256"],
        "skill_sha256_actual": actual,
        "skill_installed_path": str(target),
        "harness_activation_verified": verified,
        "activation_mechanism": "codex_home_skills_copy+prompt_prefix",
    }
    (dest_skills_root.parent / ACTIVATION_MARKER).write_text(
        json.dumps(marker, indent=2) + "\n",
        encoding="utf-8",
    )
    return marker

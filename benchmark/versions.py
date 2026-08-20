from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from benchmark.arms import ArmSpec, get_arm
from benchmark.paths import (
    ACTIVATION_MARKER,
    HARNESSES_DIR,
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


def load_arm_meta(arm: str | ArmSpec) -> dict[str, Any] | None:
    spec = get_arm(arm) if isinstance(arm, str) else arm
    if spec.kind == "baseline":
        return None
    if spec.kind == "legacy_ponytail":
        return load_ponytail_meta()
    version_path = HARNESSES_DIR / spec.name / "VERSION.json"
    meta = load_json(version_path)
    meta["harness_dir"] = str(HARNESSES_DIR / spec.name)
    return meta


def _copy_tree(src: Path, dest: Path) -> list[str]:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return [str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file()]


SUPERMEMORY_LOCAL_BASE_URL = "http://127.0.0.1:6767"
# Dedicated container — never reuse host cursor_local / personal memory.
# scb_run.py sets SUPERMEMORY_BENCHMARK_TAG per problem for memory isolation.
SUPERMEMORY_BENCHMARK_CONTAINER_TAG = os.environ.get(
    "SUPERMEMORY_BENCHMARK_TAG", "hb_supermemory"
)
_SUPERMEMORY_API_KEY_CANDIDATES = (
    Path.home() / ".local" / "share" / "supermemory" / "api_key",
    Path.home() / ".local" / "share" / "supermemory" / "api-key",
)


def _read_secret_file(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def resolve_supermemory_runtime_config() -> dict[str, Any]:
    """Build SuperMemory client config for the Codex Docker home (no secrets logged).

    Prefer host ~/.codex/supermemory.json, then env, then local server api_key file.
    Always force baseUrl to the local supermemory-server (embeddings on localhost).
    """
    host_cfg_path = Path.home() / ".codex" / "supermemory.json"
    cfg: dict[str, Any] = {}
    source = "missing"
    if host_cfg_path.is_file():
        try:
            loaded = json.loads(host_cfg_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = {}
        if isinstance(loaded, dict):
            cfg = dict(loaded)
            source = "host_codex_supermemory_json"

    api_key = (
        os.environ.get("SUPERMEMORY_CODEX_API_KEY")
        or os.environ.get("SUPERMEMORY_API_KEY")
        or (cfg.get("apiKey") if isinstance(cfg.get("apiKey"), str) else None)
    )
    if not api_key:
        for candidate in _SUPERMEMORY_API_KEY_CANDIDATES:
            api_key = _read_secret_file(candidate)
            if api_key:
                source = f"api_key_file:{candidate.name}"
                break
    elif source == "missing":
        source = "env"

    if not api_key:
        return {
            "ok": False,
            "reason": "no_supermemory_api_key",
            "base_url": SUPERMEMORY_LOCAL_BASE_URL,
            "source": source,
        }

    out = dict(cfg)
    out["apiKey"] = api_key
    out["baseUrl"] = SUPERMEMORY_LOCAL_BASE_URL
    # Always isolate from the host personal store (e.g. cursor_local).
    out["userContainerTag"] = SUPERMEMORY_BENCHMARK_CONTAINER_TAG
    out["projectContainerTag"] = SUPERMEMORY_BENCHMARK_CONTAINER_TAG
    return {
        "ok": True,
        "config": out,
        "base_url": SUPERMEMORY_LOCAL_BASE_URL,
        "source": source,
        "user_container_tag": SUPERMEMORY_BENCHMARK_CONTAINER_TAG,
        "project_container_tag": SUPERMEMORY_BENCHMARK_CONTAINER_TAG,
    }


def install_supermemory_runtime_config(codex_home: Path) -> dict[str, Any]:
    """Write supermemory.json into the per-run Codex home mount."""
    resolved = resolve_supermemory_runtime_config()
    if not resolved.get("ok"):
        return {
            "supermemory_credentials_injected": False,
            "supermemory_base_url": SUPERMEMORY_LOCAL_BASE_URL,
            "supermemory_credential_source": resolved.get("source"),
            "reason": resolved.get("reason"),
        }
    cfg = resolved["config"]
    assert isinstance(cfg, dict)
    dest = codex_home / "supermemory.json"
    dest.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    try:
        dest.chmod(0o600)
    except OSError:
        pass
    return {
        "supermemory_credentials_injected": True,
        "supermemory_base_url": resolved["base_url"],
        "supermemory_credential_source": resolved["source"],
        "supermemory_user_container_tag": resolved.get("user_container_tag"),
        "supermemory_project_container_tag": resolved.get("project_container_tag"),
        "supermemory_config_path": str(dest),
    }


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
        elif key.startswith(("SCBENCH_", "HB_", "OPENAI_", "ANTHROPIC_", "SUPERMEMORY_")):
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
    return copy_arm_skills(get_arm("ponytail"), dest_skills_root, dest_skills_root.parent)


def copy_arm_skills(
    arm: ArmSpec | str,
    dest_skills_root: Path,
    codex_home: Path | None = None,
) -> dict[str, Any]:
    """Install pinned harness skill(s) into a Codex home skills directory."""
    spec = get_arm(arm) if isinstance(arm, str) else arm
    if not spec.needs_hook:
        raise ValueError(f"arm {spec.name} does not install skills")
    codex_home = codex_home or dest_skills_root.parent
    dest_skills_root.mkdir(parents=True, exist_ok=True)
    meta = load_arm_meta(spec) or {}
    installed: list[str] = []

    if spec.kind == "legacy_ponytail":
        dest = dest_skills_root / "ponytail"
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / "SKILL.md"
        shutil.copy2(PONYTAIL_SKILL_PATH, target)
        installed.append("ponytail/SKILL.md")
        actual = sha256_file(target)
        verified = actual == meta.get("skill_sha256")
        marker: dict[str, Any] = {
            "harness": "ponytail",
            "skill_name": "ponytail",
            "skill_version": meta.get("version"),
            "skill_sha256_expected": meta.get("skill_sha256"),
            "skill_sha256_actual": actual,
            "skill_installed_path": str(target),
            "installed_files": installed,
            "harness_activation_verified": verified,
            "activation_mechanism": "codex_home_skills_copy+prompt_prefix",
        }
    elif spec.kind == "single":
        assert spec.skill_name is not None
        src = HARNESSES_DIR / spec.name / "skill"
        dest = dest_skills_root / spec.skill_name
        installed = [f"{spec.skill_name}/{rel}" for rel in _copy_tree(src, dest)]
        skill_md = dest / "SKILL.md"
        actual = sha256_file(skill_md) if skill_md.exists() else None
        verified = bool(actual and actual == meta.get("skill_sha256") and skill_md.exists())
        marker = {
            "harness": spec.name,
            "skill_name": spec.skill_name,
            "skill_version": meta.get("version"),
            "skill_sha256_expected": meta.get("skill_sha256"),
            "skill_sha256_actual": actual,
            "tree_sha256_expected": meta.get("tree_sha256"),
            "skill_installed_path": str(skill_md),
            "installed_files": installed,
            "harness_activation_verified": verified,
            "activation_mechanism": "codex_home_skills_copy+prompt_prefix",
        }
    elif spec.kind == "bundle":
        src_skills = HARNESSES_DIR / spec.name / "skills"
        for skill_dir in sorted(p for p in src_skills.iterdir() if p.is_dir()):
            dest = dest_skills_root / skill_dir.name
            rels = _copy_tree(skill_dir, dest)
            installed.extend(f"{skill_dir.name}/{rel}" for rel in rels)
        src_home = HARNESSES_DIR / spec.name / "home"
        home_installed: list[str] = []
        if src_home.exists():
            for child in sorted(p for p in src_home.iterdir()):
                dest = codex_home / child.name
                if child.is_dir():
                    home_installed.extend(
                        f"home/{child.name}/{rel}" for rel in _copy_tree(child, dest)
                    )
                elif child.is_file():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(child, dest)
                    home_installed.append(f"home/{child.name}")
        expected_names = set(meta.get("skill_names") or [])
        present = {p.name for p in dest_skills_root.iterdir() if p.is_dir()} if dest_skills_root.exists() else set()
        verified = expected_names.issubset(present) and bool(installed)
        marker = {
            "harness": spec.name,
            "skill_name": spec.skill_name,
            "skill_names": sorted(expected_names),
            "skill_version": meta.get("version"),
            "tree_sha256_expected": meta.get("tree_sha256"),
            "installed_files": installed,
            "home_installed_files": home_installed,
            "harness_activation_verified": verified,
            "activation_mechanism": "codex_home_skills_copy+home_extras+prompt_prefix",
        }
        if spec.name == "supermemory":
            runtime = install_supermemory_runtime_config(codex_home)
            marker.update(runtime)
            if not runtime.get("supermemory_credentials_injected"):
                marker["harness_activation_verified"] = False
                marker["reason"] = runtime.get("reason") or "supermemory_credentials_missing"
    else:
        raise ValueError(f"unsupported arm kind: {spec.kind}")

    (codex_home / ACTIVATION_MARKER).write_text(
        json.dumps(marker, indent=2) + "\n",
        encoding="utf-8",
    )
    return marker

"""Install pinned harness skills into the Codex Docker home mount used by SlopCodeBench."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from benchmark.arms import get_arm
from benchmark.paths import ACTIVATION_MARKER
from benchmark.versions import copy_arm_agents_file, copy_arm_skills

_ORIG_SETUP = None
_ORIG_SAVE = None
_ORIG_OC_VOLUMES = None
_ORIG_OC_SAVE = None
_INSTALLED = False
_LAST_MARKER: dict[str, Any] | None = None


def install_skill_hook() -> None:
    """Monkeypatch CodexAgent.setup/save_artifacts and OpenCodeAgent volumes for skill injection."""
    global _ORIG_SETUP, _ORIG_SAVE, _ORIG_OC_VOLUMES, _ORIG_OC_SAVE, _INSTALLED
    if _INSTALLED:
        return

    from slop_code.agent_runner.agents.codex.agent import CodexAgent
    from slop_code.agent_runner.agents.opencode.agent import OpenCodeAgent
    from slop_code.agent_runner.agents.utils import HOME_PATH

    _ORIG_SETUP = CodexAgent.setup
    _ORIG_SAVE = CodexAgent.save_artifacts

    def setup(self, session):  # type: ignore[no-untyped-def]
        global _LAST_MARKER
        _ORIG_SETUP(self, session)
        arm_name = os.environ.get("HB_ARM") or os.environ.get("HB_ENABLE_HARNESS")
        if not arm_name:
            _LAST_MARKER = {
                "harness_activation_verified": False,
                "reason": "no_HB_ARM",
            }
            return
        arm = get_arm(arm_name)
        if not arm.needs_hook:
            _LAST_MARKER = None
            return
        if self._trace_dir is None:
            _LAST_MARKER = {
                "harness_activation_verified": False,
                "reason": "no_trace_dir",
                "harness": arm.name,
            }
            return
        skills_root = Path(self._trace_dir) / "skills"
        _LAST_MARKER = copy_arm_skills(arm, skills_root, codex_home=Path(self._trace_dir))
        self.log.info(
            "harness.skill_installed",
            **{k: v for k, v in _LAST_MARKER.items() if k != "skill_installed_path"},
        )

    def save_artifacts(self, path: Path) -> None:  # type: ignore[no-untyped-def]
        _ORIG_SAVE(self, path)
        marker = _LAST_MARKER
        if marker is None and self._trace_dir is not None:
            candidate = Path(self._trace_dir) / ACTIVATION_MARKER
            if candidate.exists():
                marker = json.loads(candidate.read_text(encoding="utf-8"))
        if marker is not None:
            (path / ACTIVATION_MARKER).write_text(
                json.dumps(marker, indent=2) + "\n",
                encoding="utf-8",
            )

    CodexAgent.setup = setup  # type: ignore[method-assign]
    CodexAgent.save_artifacts = save_artifacts  # type: ignore[method-assign]

    # ---- OpenCodeAgent: inject skills into the opencode home mount ----
    _ORIG_OC_VOLUMES = OpenCodeAgent._get_volumes
    _ORIG_OC_SAVE = OpenCodeAgent.save_artifacts

    def oc_get_volumes(self):  # type: ignore[no-untyped-def]
        global _LAST_MARKER
        volumes = _ORIG_OC_VOLUMES(self)
        arm_name = os.environ.get("HB_ARM") or os.environ.get("HB_ENABLE_HARNESS")
        if not arm_name:
            _LAST_MARKER = {
                "harness_activation_verified": False,
                "reason": "no_HB_ARM",
            }
            return volumes
        arm = get_arm(arm_name)
        if not arm.needs_hook:
            _LAST_MARKER = None
            return volumes
        if self._tmp_dir is None:
            _LAST_MARKER = {
                "harness_activation_verified": False,
                "reason": "no_tmp_dir",
                "harness": arm.name,
            }
            return volumes
        skills_root = self.tmp_dir / "skills"
        codex_home = self.tmp_dir / ".codex"
        codex_home.mkdir(parents=True, exist_ok=True)
        _LAST_MARKER = copy_arm_skills(arm, skills_root, codex_home=codex_home)
        agents_path = self.tmp_dir / "AGENTS.md"
        agents_marker = copy_arm_agents_file(arm, agents_path)
        if agents_marker.get("agents_file_present"):
            _LAST_MARKER.update(agents_marker)
            _LAST_MARKER["activation_mechanism"] = (
                f"{_LAST_MARKER['activation_mechanism']}+workspace_agents_mount"
            )
            if not agents_marker.get("agents_file_verified"):
                _LAST_MARKER["harness_activation_verified"] = False
            volumes[str(agents_path)] = {
                "bind": "/workspace/AGENTS.md",
                "mode": "ro",
            }
            (codex_home / ACTIVATION_MARKER).write_text(
                json.dumps(_LAST_MARKER, indent=2) + "\n",
                encoding="utf-8",
            )
        volumes[str(skills_root)] = {
            "bind": f"{HOME_PATH}/.config/opencode/skills",
            "mode": "rw",
        }
        volumes[str(codex_home)] = {
            "bind": f"{HOME_PATH}/.codex",
            "mode": "rw",
        }
        self.log.info(
            "harness.skill_installed",
            **{k: v for k, v in _LAST_MARKER.items() if k != "skill_installed_path"},
        )
        return volumes

    def oc_save_artifacts(self, path: Path) -> None:  # type: ignore[no-untyped-def]
        _ORIG_OC_SAVE(self, path)
        marker = _LAST_MARKER
        if marker is None and self._tmp_dir is not None:
            candidate = self.tmp_dir / ".codex" / ACTIVATION_MARKER
            if candidate.exists():
                marker = json.loads(candidate.read_text(encoding="utf-8"))
        if marker is not None:
            (path / ACTIVATION_MARKER).write_text(
                json.dumps(marker, indent=2) + "\n",
                encoding="utf-8",
            )

    OpenCodeAgent._get_volumes = oc_get_volumes  # type: ignore[method-assign]
    OpenCodeAgent.save_artifacts = oc_save_artifacts  # type: ignore[method-assign]
    _INSTALLED = True


def uninstall_skill_hook() -> None:
    global _INSTALLED, _LAST_MARKER
    if not _INSTALLED:
        return
    from slop_code.agent_runner.agents.codex.agent import CodexAgent
    from slop_code.agent_runner.agents.opencode.agent import OpenCodeAgent

    if _ORIG_SETUP is not None:
        CodexAgent.setup = _ORIG_SETUP  # type: ignore[method-assign]
    if _ORIG_SAVE is not None:
        CodexAgent.save_artifacts = _ORIG_SAVE  # type: ignore[method-assign]
    if _ORIG_OC_VOLUMES is not None:
        OpenCodeAgent._get_volumes = _ORIG_OC_VOLUMES  # type: ignore[method-assign]
    if _ORIG_OC_SAVE is not None:
        OpenCodeAgent.save_artifacts = _ORIG_OC_SAVE  # type: ignore[method-assign]
    _INSTALLED = False
    _LAST_MARKER = None


# Back-compat aliases used by older call sites / sitecustomize.
install_ponytail_hook = install_skill_hook
uninstall_ponytail_hook = uninstall_skill_hook

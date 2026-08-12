"""Install Ponytail into the Codex Docker home mount used by SlopCodeBench."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.paths import ACTIVATION_MARKER
from benchmark.versions import copy_ponytail_skill

_ORIG_SETUP = None
_ORIG_SAVE = None
_INSTALLED = False
_LAST_MARKER: dict[str, Any] | None = None


def install_ponytail_hook() -> None:
    """Monkeypatch CodexAgent.setup/save_artifacts for skill injection."""
    global _ORIG_SETUP, _ORIG_SAVE, _INSTALLED
    if _INSTALLED:
        return

    from slop_code.agent_runner.agents.codex.agent import CodexAgent

    _ORIG_SETUP = CodexAgent.setup
    _ORIG_SAVE = CodexAgent.save_artifacts

    def setup(self, session):  # type: ignore[no-untyped-def]
        global _LAST_MARKER
        _ORIG_SETUP(self, session)
        if self._trace_dir is None:
            _LAST_MARKER = {
                "harness_activation_verified": False,
                "reason": "no_trace_dir",
            }
            return
        skills_root = Path(self._trace_dir) / "skills"
        _LAST_MARKER = copy_ponytail_skill(skills_root)
        self.log.info(
            "harness.ponytail.skill_installed",
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
    _INSTALLED = True


def uninstall_ponytail_hook() -> None:
    global _INSTALLED, _LAST_MARKER
    if not _INSTALLED:
        return
    from slop_code.agent_runner.agents.codex.agent import CodexAgent

    if _ORIG_SETUP is not None:
        CodexAgent.setup = _ORIG_SETUP  # type: ignore[method-assign]
    if _ORIG_SAVE is not None:
        CodexAgent.save_artifacts = _ORIG_SAVE  # type: ignore[method-assign]
    _INSTALLED = False
    _LAST_MARKER = None

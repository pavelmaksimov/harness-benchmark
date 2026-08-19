"""Inject snapshot solution deps into SCB's isolated `uvx` pytest env.

SCB already runs environment `eval_commands` (`uv add -r requirements.txt`) into
the workspace uv project. Pytest then runs via `uvx --with=test_dependencies`,
which is a *new* ephemeral env and does not see that project or the agent's
`.venv`. Without this hook, any library the model adds (pwdlib, passlib, …)
is missing at TestClient import time unless it was copied into the problem
whitelist — which does not scale.

This module patches `PytestRunner` so eval also receives solution dependencies
without letting a solution-pinned pytest replace SCB's test runner.
Installed from `benchmark.scb_main` and from `harness_sitecustomize` so
ProcessPool workers get it too.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

REQUIREMENTS_NAME = "requirements.txt"
PYPROJECT_NAME = "pyproject.toml"

_ORIG_BUILD_WITH_FLAGS = None
_ORIG_RUN = None
_INSTALLED = False


def _is_eval_framework_requirement(line: str) -> bool:
    match = re.match(r"^\s*([A-Za-z0-9_.-]+)", line.split("#", 1)[0])
    if not match:
        return False
    name = match.group(1).lower().replace("_", "-")
    return name == "pytest" or name.startswith("pytest-")


def _without_eval_framework_requirements(text: str) -> str:
    return "".join(
        line
        for line in text.splitlines(keepends=True)
        if not _is_eval_framework_requirement(line)
    )


def solution_uvx_with_flags(workspace: Path) -> list[str]:
    """Return extra `uvx` flags for agent-declared solution dependencies.

    Preference: ``requirements.txt`` (what prompts tell the agent to keep) via
    ``--with-requirements`` so extras, pins, and git URLs stay in-file.
    Fallback: PEP 621 ``project.dependencies`` in ``pyproject.toml``.
    Missing manifest → no extra flags (undeclared imports fail as
    ``ModuleNotFoundError``). Malformed pyproject raises so eval fails clearly.
    """
    workspace = Path(workspace)
    requirements = workspace / REQUIREMENTS_NAME
    if requirements.is_file():
        # Relative name: uvx runs with cwd = workspace (/workspace in Docker).
        # Do not pass a host absolute path — the container would not see it.
        return [f"--with-requirements={REQUIREMENTS_NAME}"]

    pyproject = workspace / PYPROJECT_NAME
    if pyproject.is_file():
        return [
            f"--with={shlex.quote(dep)}"
            for dep in _pep508_from_pyproject(pyproject)
            if not _is_eval_framework_requirement(dep)
        ]
    return []


def _pep508_from_pyproject(path: Path) -> list[str]:
    """Read PEP 621 project.dependencies; raises if the TOML is unreadable."""
    import tomllib

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"malformed {PYPROJECT_NAME} at {path}: {exc}") from exc

    deps = data.get("project", {}).get("dependencies") or []
    if not isinstance(deps, list):
        raise ValueError(f"{path}: project.dependencies must be a list")
    out: list[str] = []
    for dep in deps:
        text = str(dep).strip()
        if text:
            out.append(text)
    return out


def install_eval_deps_hook() -> None:
    """Install solution dependencies while keeping SCB's pytest runner intact."""
    global _ORIG_BUILD_WITH_FLAGS, _ORIG_RUN, _INSTALLED
    if _INSTALLED:
        return

    from slop_code.evaluation.pytest_runner import PytestRunner

    _ORIG_BUILD_WITH_FLAGS = PytestRunner._build_with_flags
    _ORIG_RUN = PytestRunner.run

    def _run(self: Any, pytest_args: list[str] | None = None) -> Any:
        requirements = Path(self.submission_path) / REQUIREMENTS_NAME
        original = None
        if requirements.is_file():
            text = requirements.read_text(encoding="utf-8")
            filtered = _without_eval_framework_requirements(text)
            if filtered != text:
                requirements.write_text(filtered, encoding="utf-8")
                original = text
        try:
            return _ORIG_RUN(self, pytest_args)
        finally:
            if original is not None:
                requirements.write_text(original, encoding="utf-8")

    def _build_with_flags(self: Any) -> list[str]:
        flags = list(_ORIG_BUILD_WITH_FLAGS(self))
        extra = solution_uvx_with_flags(Path(self.submission_path))
        if extra:
            flags.extend(extra)
        return flags

    PytestRunner._build_with_flags = _build_with_flags  # type: ignore[method-assign]
    PytestRunner.run = _run  # type: ignore[method-assign]
    _INSTALLED = True


def uninstall_eval_deps_hook() -> None:
    global _ORIG_BUILD_WITH_FLAGS, _ORIG_RUN, _INSTALLED
    if not _INSTALLED:
        return
    from slop_code.evaluation.pytest_runner import PytestRunner

    if _ORIG_BUILD_WITH_FLAGS is not None:
        PytestRunner._build_with_flags = _ORIG_BUILD_WITH_FLAGS  # type: ignore[method-assign]
    if _ORIG_RUN is not None:
        PytestRunner.run = _ORIG_RUN  # type: ignore[method-assign]
    _ORIG_BUILD_WITH_FLAGS = None
    _ORIG_RUN = None
    _INSTALLED = False

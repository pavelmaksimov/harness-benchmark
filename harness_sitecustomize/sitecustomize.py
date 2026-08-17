"""Loaded automatically when this directory is on PYTHONPATH."""

from __future__ import annotations

import os
import sys


def _install_eval_deps_hook() -> None:
    """Always-on: snapshot requirements.txt must reach uvx in ProcessPool workers."""
    try:
        from benchmark.eval_deps_hook import install_eval_deps_hook

        install_eval_deps_hook()
    except Exception as exc:  # noqa: BLE001
        print(f"[hb] eval deps hook install failed: {exc}", file=sys.stderr)


def _load_hb_models() -> None:
    """Overlay harness-benchmark model YAMLs onto SCB ModelCatalog (ProcessPool-safe)."""
    try:
        from benchmark.paths import MODELS_DIR
        from slop_code.agent_runner.credentials import ProviderCatalog
        from slop_code.common.llms import ModelCatalog

        ProviderCatalog.ensure_loaded()
        ModelCatalog.ensure_loaded()
        if MODELS_DIR.is_dir():
            ModelCatalog.load_from_directory(MODELS_DIR)
    except Exception as exc:  # noqa: BLE001
        print(f"[hb] model catalog overlay failed: {exc}", file=sys.stderr)


def _maybe_install_skill_hook() -> None:
    if os.environ.get("HB_ENABLE_HARNESS") != "1" and os.environ.get("HB_ENABLE_PONYTAIL") != "1":
        return
    arm = os.environ.get("HB_ARM", "")
    if arm == "baseline":
        return
    try:
        from benchmark.skill_hook import install_skill_hook

        install_skill_hook()
    except Exception as exc:  # noqa: BLE001
        print(f"[hb] skill hook install failed: {exc}", file=sys.stderr)


_install_eval_deps_hook()
_load_hb_models()
_maybe_install_skill_hook()

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
        from slop_code.agent_runner.credentials import ProviderCatalog
        from slop_code.common.llms import ModelCatalog

        import benchmark.omp_agent  # noqa: F401  (registers omp_auth provider)
        from benchmark.paths import MODELS_DIR

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


def _maybe_install_rework_hook() -> None:
    raw = os.environ.get("HB_REWORK_ATTEMPTS", "0") or "0"
    try:
        attempts = int(raw)
    except ValueError:
        attempts = 0
    transient_raw = os.environ.get("HB_TRANSIENT_RETRIES", "0") or "0"
    try:
        transient_retries = int(transient_raw)
    except ValueError:
        transient_retries = 0
    if attempts <= 0 and transient_retries <= 0:
        return
    try:
        from benchmark.rework_hook import install_rework_hook

        install_rework_hook(
            attempts,
            transient_retries=transient_retries,
            feedback_strategy=os.environ.get("HB_REWORK_FEEDBACK"),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[hb] rework hook install failed: {exc}", file=sys.stderr)


def _install_continue_hook() -> None:
    try:
        from benchmark.continue_hook import install_continue_after_test_failure

        install_continue_after_test_failure()
    except Exception as exc:  # noqa: BLE001
        print(f"[hb] continue hook install failed: {exc}", file=sys.stderr)


_install_eval_deps_hook()
_load_hb_models()
_maybe_install_skill_hook()
_maybe_install_rework_hook()
_install_continue_hook()

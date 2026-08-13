"""Loaded automatically when this directory is on PYTHONPATH."""

from __future__ import annotations

import os


def _maybe_install() -> None:
    if os.environ.get("HB_ENABLE_HARNESS") != "1" and os.environ.get("HB_ENABLE_PONYTAIL") != "1":
        return
    arm = os.environ.get("HB_ARM", "")
    if arm == "baseline":
        return
    try:
        from benchmark.skill_hook import install_skill_hook

        install_skill_hook()
    except Exception as exc:  # noqa: BLE001
        import sys

        print(f"[hb] skill hook install failed: {exc}", file=sys.stderr)


_maybe_install()

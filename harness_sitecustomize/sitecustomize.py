"""Loaded automatically when this directory is on PYTHONPATH."""

from __future__ import annotations

import os


def _maybe_install() -> None:
    if os.environ.get("HB_ENABLE_PONYTAIL") != "1":
        return
    try:
        from benchmark.ponytail_hook import install_ponytail_hook

        install_ponytail_hook()
    except Exception as exc:  # noqa: BLE001
        import sys

        print(f"[hb] ponytail hook install failed: {exc}", file=sys.stderr)


_maybe_install()

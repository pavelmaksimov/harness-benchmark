"""Entrypoint used inside `uv run` so skill hooks can be applied before SCB CLI."""

from __future__ import annotations

import os
import sys


def main() -> None:
    from benchmark.catalog import load_catalogs
    from benchmark.eval_deps_hook import install_eval_deps_hook

    install_eval_deps_hook()

    arm = os.environ.get("HB_ARM", "")
    if (
        os.environ.get("HB_ENABLE_HARNESS") == "1"
        or os.environ.get("HB_ENABLE_PONYTAIL") == "1"
        or (arm and arm != "baseline")
    ):
        from benchmark.skill_hook import install_skill_hook

        install_skill_hook()

    from benchmark.continue_hook import install_continue_after_test_failure
    from benchmark.rework_hook import (
        DEFAULT_FEEDBACK_STRATEGY,
        HB_REWORK_ATTEMPTS,
        HB_REWORK_FEEDBACK,
        HB_TRANSIENT_RETRIES,
        install_rework_hook,
    )

    install_continue_after_test_failure()
    try:
        rework_attempts = int(os.environ.get(HB_REWORK_ATTEMPTS, "0") or "0")
    except ValueError:
        rework_attempts = 0
    try:
        transient_retries = int(os.environ.get(HB_TRANSIENT_RETRIES, "0") or "0")
    except ValueError:
        transient_retries = 0
    feedback_strategy = os.environ.get(HB_REWORK_FEEDBACK, DEFAULT_FEEDBACK_STRATEGY)
    if rework_attempts > 0 or transient_retries > 0:
        install_rework_hook(
            rework_attempts,
            transient_retries=transient_retries,
            feedback_strategy=feedback_strategy,
        )

    # SCB catalog first, then harness-benchmark overlays (e.g. free OpenCode models).
    load_catalogs()

    from slop_code.entrypoints.cli import app

    # Typer apps expect argv without the module name.
    sys.argv = ["slop-code", *sys.argv[1:]]
    app()


if __name__ == "__main__":
    main()

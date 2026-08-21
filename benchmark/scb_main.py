"""Entrypoint used inside `uv run` so skill hooks can be applied before SCB CLI."""

from __future__ import annotations

import os
import sys


def main() -> None:
    from benchmark.eval_deps_hook import install_eval_deps_hook
    from benchmark.paths import MODELS_DIR

    install_eval_deps_hook()

    arm = os.environ.get("HB_ARM", "")
    if (
        os.environ.get("HB_ENABLE_HARNESS") == "1"
        or os.environ.get("HB_ENABLE_PONYTAIL") == "1"
        or (arm and arm != "baseline")
    ):
        from benchmark.skill_hook import install_skill_hook

        install_skill_hook()

    from benchmark.rework_hook import HB_REWORK_ATTEMPTS, install_rework_hook
    from benchmark.continue_hook import install_continue_after_test_failure

    install_continue_after_test_failure()
    try:
        rework_attempts = int(os.environ.get(HB_REWORK_ATTEMPTS, "0") or "0")
    except ValueError:
        rework_attempts = 0
    if rework_attempts > 0:
        install_rework_hook(rework_attempts)

    # Ensure agent registrations load.
    import slop_code.agent_runner.agents  # noqa: F401
    from slop_code.agent_runner.credentials import ProviderCatalog
    from slop_code.common.llms import ModelCatalog

    # SCB catalog first, then harness-benchmark overlays (e.g. free OpenCode models).
    ProviderCatalog.ensure_loaded()
    ModelCatalog.ensure_loaded()
    if MODELS_DIR.is_dir():
        ModelCatalog.load_from_directory(MODELS_DIR)

    from slop_code.entrypoints.cli import app

    # Typer apps expect argv without the module name.
    sys.argv = ["slop-code", *sys.argv[1:]]
    app()


if __name__ == "__main__":
    main()

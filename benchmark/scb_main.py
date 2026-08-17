"""Entrypoint used inside `uv run` so skill hooks can be applied before SCB CLI."""

from __future__ import annotations

import os
import sys


def main() -> None:
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

    # Ensure agent registrations load.
    import slop_code.agent_runner.agents  # noqa: F401
    from slop_code.entrypoints.cli import app

    # Typer apps expect argv without the module name.
    sys.argv = ["slop-code", *sys.argv[1:]]
    app()


if __name__ == "__main__":
    main()

"""Entrypoint used inside `uv run` so Ponytail hook can be applied before SCB CLI."""

from __future__ import annotations

import os
import sys


def main() -> None:
    if os.environ.get("HB_ENABLE_PONYTAIL") == "1":
        from benchmark.ponytail_hook import install_ponytail_hook

        install_ponytail_hook()

    # Ensure agent registrations load.
    import slop_code.agent_runner.agents  # noqa: F401
    from slop_code.entrypoints.cli import app

    # Typer apps expect argv without the module name.
    sys.argv = ["slop-code", *sys.argv[1:]]
    app()


if __name__ == "__main__":
    main()

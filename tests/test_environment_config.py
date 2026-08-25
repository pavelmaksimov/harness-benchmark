from pathlib import Path

import yaml

from benchmark.paths import CONFIGS_DIR
from benchmark.scb_run import _environment_config


def test_benchmark_environment_runs_workspace_commands_as_agent() -> None:
    for arm in ("python-harness", "supermemory"):
        path = _environment_config(arm)

        assert path.is_relative_to(CONFIGS_DIR)
        assert yaml.safe_load(Path(path).read_text(encoding="utf-8"))["docker"]["user"] == "1000:1000"

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/vendor"
cd "$ROOT/vendor"

if [[ ! -d slop-code-bench/.git ]]; then
  git clone https://github.com/SprocketLab/slop-code-bench.git
fi
if [[ ! -d scb-problems/.git ]]; then
  git clone https://github.com/gabeorlanski/scb-problems.git
fi

SCB_COMMIT="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("pins.json").read_text())["slop-code-bench"])
PY
)"
PROB_COMMIT="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("pins.json").read_text())["scb-problems"])
PY
)"

git -C slop-code-bench fetch --depth 1 origin "$SCB_COMMIT"
git -C slop-code-bench checkout --detach "$SCB_COMMIT"
git -C scb-problems fetch --depth 1 origin "$PROB_COMMIT"
git -C scb-problems checkout --detach "$PROB_COMMIT"

cd "$ROOT"
uv sync
bash "$ROOT/scripts/sync_task_manager_problem.sh"
bash "$ROOT/scripts/sync_realworld_problem.sh"
uv run python -m benchmark bootstrap

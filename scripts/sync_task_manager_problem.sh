#!/usr/bin/env bash
# Link the tracked task_manager problem into the vendored SCB problems tree
# so SCBENCH_PROBLEMS_PATH=vendor/scb-problems discovers it without modifying
# upstream problems such as file_backup.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/problems/task_manager"
DST_ROOT="$ROOT/vendor/scb-problems"
DST="$DST_ROOT/task_manager"

if [[ ! -d "$SRC" ]]; then
  echo "error: missing tracked problem at $SRC" >&2
  exit 1
fi
if [[ ! -d "$DST_ROOT" ]]; then
  echo "error: missing $DST_ROOT — run bash scripts/bootstrap_vendor.sh first" >&2
  exit 1
fi
if [[ -e "$DST" && ! -L "$DST" ]]; then
  echo "error: $DST exists and is not a symlink; refuse to overwrite" >&2
  exit 1
fi

ln -sfn "$SRC" "$DST"
echo "linked $DST -> $SRC"

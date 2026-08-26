#!/usr/bin/env bash
# Read-only status snapshot for the three target experiments (runbook-style).
cd /home/user/my/harness-benchmark || exit 1
echo "=== $(date '+%F %T') processes ==="
pgrep -af 'benchmark.scb_main' | grep -v pgrep | wc -l
docker ps --format '{{.Names}} {{.Status}}' | head -10
echo "=== state.json of target slots ==="
for s in \
  results/realworld-opencode-x-preview-f-free-high-all-20260822-1838/baseline/run_2 \
  results/realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-20260826/python-harness-v1.3.0/run_1 \
  results/realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-20260826/python-harness-v1.3.0/run_2 \
  results/realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-combos-20260826/python-harness-v1.3.0+graphify/run_1 \
  results/realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-combos-20260826/python-harness-v1.3.0+graphify/run_2 \
  results/realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-combos-20260826/python-harness-v1.3.0+doorstop/run_1 \
  results/realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-combos-20260826/python-harness-v1.3.0+doorstop/run_2 \
  results/realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-combos-20260826/python-harness-v1.3.0+strictdoc/run_1 \
  results/realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-combos-20260826/python-harness-v1.3.0+strictdoc/run_2 ; do
  n=$(find "$s/scb" -name evaluation.json 2>/dev/null | wc -l)
  st=$(jq -rc '[.phase, (.fully_completed//false)] | join("|")' "$s/state.json" 2>/dev/null)
  echo "$(echo "$s" | cut -d/ -f2-4) $st evals=$n"
  [ "$n" -gt 0 ] || true
done

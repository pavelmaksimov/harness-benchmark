#!/usr/bin/env bash
# Backs up the opencode log from the live qwen/neuraldeep agent container
# so the cause of session death survives container removal and resume rotation.
set -u
OUT=/home/user/my/harness-benchmark/logs/qwen-opencode-snapshots
mkdir -p "$OUT"
while true; do
  C=$(docker ps --format '{{.Names}}' | grep -viE 'gitlab|maildev' | head -1)
  if [ -n "$C" ]; then
    L=$(docker exec "$C" sh -c 'ls -t ~/.local/share/opencode/log/ 2>/dev/null | head -1' 2>/dev/null)
    if [ -n "$L" ]; then
      docker exec "$C" cat "/tmp/agent_home/.local/share/opencode/log/$L" > "$OUT/${C}.log" 2>/dev/null
      docker exec "$C" cat /tmp/agent_home/.local/share/opencode/opencode.db-wal > "$OUT/${C}.db-wal" 2>/dev/null || true
    fi
  fi
  sleep 60
done

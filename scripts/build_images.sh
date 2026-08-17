#!/usr/bin/env bash
# Pre-build SlopCodeBench Docker images (base + Codex + OpenCode agents).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DOCKER_CFG="${TMPDIR:-/tmp}/hb-docker-cfg"
mkdir -p "$DOCKER_CFG"
printf '%s\n' '{"auths": {}}' > "$DOCKER_CFG/config.json"
export DOCKER_CONFIG="$DOCKER_CFG"
export SCBENCH_PROBLEMS_PATH="$ROOT/vendor/scb-problems"

echo "Building base image..."
uv run python -m benchmark.scb_main docker build-base \
  vendor/slop-code-bench/configs/environments/docker-python3.12-uv.yaml

echo "Building Codex agent image..."
uv run python -m benchmark.scb_main docker build-agent \
  configs/agent_codex.yaml \
  vendor/slop-code-bench/configs/environments/docker-python3.12-uv.yaml

echo "Building OpenCode agent image..."
uv run python -m benchmark.scb_main docker build-agent \
  configs/agent_opencode.yaml \
  vendor/slop-code-bench/configs/environments/docker-python3.12-uv.yaml

docker images | grep -E 'slop-code|sc-opencode|opencode' || true
echo "Done."

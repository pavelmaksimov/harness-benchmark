# Combined harness: agent-memory stack

This pin combines four open-source agent-memory systems as co-existing skills:

- `ontoship` — md+git knowledge base with `gitmark` FTS5 search (vendored, stdlib-only)
- `mempalace` — verbatim memory palace, ChromaDB + local ONNX embeddings (CLI via ephemeral `uvx`, `--no-llm`)
- `openviking` — `viking://` context database; server runs on the HOST (local GGUF embedding via llama-cpp-python, which cannot build inside the slim container), agent uses the CLI client over `docker-python3.12-uv-hostnet` (same pattern as the supermemory arm's host-local server)
- `baron` — Baron Munchausen memory-graph server (vendored, stdlib-only, JSON-RPC on 127.0.0.1:8765 inside the container)

Memory state roots (all inside the workspace so they survive between checkpoints):
`kb/` + `.gitmark/` (ontoship), `.mempalace/` (mempalace palace + notes), `.openviking/` (openviking client config + notes), `.baron/` (baron store).
Tool CLIs are ephemeral (`uvx`, container-local uv cache) or vendored in the skill dir — never installed into the workspace (a venv there bloats every checkpoint snapshot and pollutes LOC metrics; incident 2026-09-16).

Sources (upstream repos, cloned 2026-09-16):
`vakovalskii/ontoship`, `MemPalace/mempalace` (PyPI 3.10.0), `volcengine/OpenViking` (PyPI 0.4.20 client), `shinegang/baron` (0.6.1).

The payload is copied from the individual pinned harnesses into `skills/`.
Rebuild this directory and rerun `scripts/pin_harness.py` when one of the
component harnesses is intentionally updated.

Requires a host-side OpenViking server listening on 127.0.0.1:8790
(see `ops/openviking-host-server/README.md`).

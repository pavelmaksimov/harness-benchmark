---
name: baron
description: Baron Munchausen local memory harness. Run a zero-dependency local memory graph server (JSON-RPC on 127.0.0.1:8765, ships next to this SKILL.md) while implementing a benchmark checkpoint task — checkpoint at session start, add durable facts, ground answers against the graph. Use when activated by the benchmark prompt prefix ("Activate and follow the installed Codex skill `baron`").
---

# Baron Munchausen local memory harness

You keep a project memory graph while you implement the task. The server is pure Python stdlib (no pip installs, no API keys) and ships next to this SKILL.md. Facts live in a JSON store inside the workspace, so memory survives between checkpoints even though the server process does not. **A failing solution is never acceptable because memory bookkeeping passed.**

## Non-negotiable rules

1. **Solution first.** Memory work is capped at a small fraction of your effort; if time is tight, cut memory calls, never code.
2. **The store lives at `.baron/nodes.json`** in the workspace (plus `.baron/server.log`). Never store it in `$HOME` or `/tmp` — it must survive between checkpoints.
3. **Zero installs.** Run the server from the skill directory via `PYTHONPATH`. Never add anything baron-related to the project `requirements.txt`.
4. **Server is disposable.** If it is already running, reuse it; if it died, restart it. It listens on 127.0.0.1:8765 inside this machine only. Do not run it in the foreground.

## Locate the skill dir and start the server (each session)

```bash
SKB="$HOME/.config/opencode/skills/baron"
[ -d "$SKB" ] || SKB="$(find / -type d -name baron -path '*opencode*skills*' 2>/dev/null | head -1)"
mkdir -p /workspace/.baron
if [ -f /workspace/.baron/nodes.json ]; then STORE=/workspace/.baron/nodes.json; else STORE=blank; fi
# blank provisions a fresh graph once; existing store is reused as-is
( PYTHONPATH="$SKB" nohup python3 -m baron --host 127.0.0.1 --port 8765 \
    --store /workspace/.baron/nodes.json >> /workspace/.baron/server.log 2>&1 & )
sleep 2
curl -s http://127.0.0.1:8765/health
```

On first start pass `--store blank` instead of a path (it refuses to overwrite an existing file); afterwards pass the path. If `nodes.json` already exists, never pass `blank` again. Confirm the health output reports `"ok": true`; if it does not, check `.baron/server.log` once, then continue without memory.

## Core calls (JSON-RPC via curl)

Helper shape — every call is:

```bash
rpc() { curl -sX POST 127.0.0.1:8765/rpc -H content-type:application/json -d "$1"; }
```

1. **Open the session (once per checkpoint, right after the server is up):**

   ```bash
   rpc '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"memory_checkpoint",
        "arguments":{"query":"where did the task_manager work stop","session_id":"cp-N","agent":"glm"}}}'
   ```

   Returns the head of the project thread, last sessions, open loose ends, last decisions.
2. **Search before implementing a feature:**

   ```bash
   rpc '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"memory_search",
        "arguments":{"query":"error envelope contract","limit":5}}}'
   ```
3. **Add durable facts (decisions, contracts, fixes) as you go:**

   ```bash
   rpc '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"memory_add",
        "arguments":{"items":[{"claim":"Error body must be {\"error\":{\"code\",\"message\"}}",
        "source":"checkpoint-2 tests","kind":"rule","tags":["api","errors"]}],
        "session_id":"cp-N"}}}'
   ```

   `kind`: `rule` (hard constraint) | `decision` | `fact` | `lesson`. Keep claims one sentence.
4. **End of checkpoint (optional, cheap):** `memory_stats` to sanity-check the graph grew; fix duplicates with `memory_rewrite`/`memory_retract`.

Useful extras: `memory_graph` (op=neighbors/hub), `memory_recent` (last activity digest), `memory_export`. Full list: `rpc '{"jsonrpc":"2.0","id":0,"method":"tools/list","params":{}}'`.

## Anti-patterns

- Adding baron to `requirements.txt` or pip-installing anything.
- `--store blank` on an existing store (it refuses) or storing outside `/workspace/.baron`.
- Long prose in `claim` — one sentence per node, link with `memory_link` if needed.
- Memory calls before the current checkpoint's code is green.

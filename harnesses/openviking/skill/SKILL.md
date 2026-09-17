---
name: openviking
description: OpenViking context-database harness. Recall and persist long-term memory through a local OpenViking server (viking:// URIs, semantic retrieval over an AGFS virtual filesystem) while implementing a benchmark checkpoint task — find/read prior knowledge at task start, add-resource durable notes as you learn. Use when activated by the benchmark prompt prefix ("Activate and follow the installed Codex skill `openviking`").
---

# OpenViking context-database harness

You use a local OpenViking context database as long-term memory across checkpoints. Knowledge lives behind `viking://` URIs; retrieval is semantic (`find`), persistence is file import (`add-resource`). The server runs outside your sandbox at `http://127.0.0.1:8790` (already provisioned — embedding is local, no API keys). **A failing solution is never acceptable because memory bookkeeping passed.**

## Non-negotiable rules

1. **Solution first.** Memory work is capped at a small fraction of your effort; if time is tight, cut memory calls, never code.
2. **Server is a given, not your job.** Never try to install, start, stop or configure the server. Client-only.
3. **The CLI runs ephemerally via `uvx`** (container-local cache, no workspace writes). NEVER create virtualenvs or install packages into `/workspace` — the workspace is snapshotted per checkpoint and any `.py` files there would pollute the solution. NEVER add `openviking` to the project `requirements.txt` — that file feeds the evaluator and must stay app-only.
4. **No `remember` extraction and no VLM.** This server runs without a VLM: persist knowledge by importing short markdown notes with `add-resource`. Do not look for MCP tools; the CLI is the interface.
5. **Only memory DATA lives in the workspace**, under `.openviking/` (client config + notes).

## Invocation (every command)

```bash
export OPENVIKING_CLI_CONFIG_FILE=/workspace/.openviking/ovcli.conf
uvx --from openviking openviking <command>
```

Agent shells do not persist exports — repeat the env var on every invocation. The first call downloads wheels into the container uv cache (1–2 min); later calls are fast.

## One-time setup (first checkpoint)

```bash
mkdir -p /workspace/.openviking/notes
uvx --from openviking openviking config add custom --name local \
  --url http://127.0.0.1:8790 --activate
OPENVIKING_CLI_CONFIG_FILE=/workspace/.openviking/ovcli.conf \
  uvx --from openviking openviking health
```

Note: `config add` writes `ovcli.conf` under `~/.openviking/` — copy it to the workspace once so later checkpoints can reuse it:

```bash
cp ~/.openviking/ovcli.conf /workspace/.openviking/ovcli.conf
```

If the config already exists in the workspace and `health` is ok, skip setup. If the server is unreachable, note it once and continue WITHOUT memory — do not debug the server.

## Per-checkpoint loop

1. **Recall at task start.** One concise query per area you are about to touch:

   ```bash
   $OV find "task board API contracts" -n 5
   $OV read "viking://resources/notes/<hit>.md"
   ```

   Judge by content, not title; read at most 1–3 files. Nothing relevant → proceed without memory.
2. **Persist while working.** Keep short notes in `.openviking/notes/` and import them as you learn durable things (decision + why, contract, failure + fix):

   ```bash
   $OV add-resource /workspace/.openviking/notes/cp3-decisions.md \
       --to viking://resources/notes/cp3-decisions.md --wait
   ```

   `--to` must not already exist — one file per checkpoint is a clean convention. Use `--parent viking://resources/notes` (which you created first) when appending many files.
3. **Keep notes small and factual**: headings + bullets, conclusions not transcripts. No secrets, no code dumps.

## Anti-patterns

- Installing or restarting the server; using MCP tools; trying `remember`.
- Adding `openviking` to `requirements.txt`, or creating a venv/`uv venv`/`uv pip install` inside `/workspace`.
- Importing venvs, `.git`, logs or binary junk into the database.
- Re-importing the same file twice (`--to` fails on existing URIs — that is your guard).
- Letting memory work delay or replace a working solution.

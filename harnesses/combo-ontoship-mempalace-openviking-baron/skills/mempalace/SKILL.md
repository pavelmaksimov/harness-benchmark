---
name: mempalace
description: MemPalace verbatim memory harness. Maintain a local "memory palace" (verbatim drawers, ChromaDB + ONNX embeddings, zero API calls) while implementing a benchmark checkpoint task — mine session notes and search them before answering/coding. Use when activated by the benchmark prompt prefix ("Activate and follow the installed Codex skill `mempalace`").
---

# MemPalace verbatim memory harness

You keep a local memory palace while you implement the task. Everything you learn that must survive into later checkpoints — decisions, contracts, failure lessons, environment quirks — is written as a short note file and mined verbatim into the palace; anything you need to recall is searched, not guessed. **A failing solution is never acceptable because memory bookkeeping passed.**

## Non-negotiable rules

1. **Solution first.** Memory work is capped at a small fraction of your effort; if time is tight, cut memory polish, never code.
2. **Only memory DATA lives in the workspace**, under `.mempalace/` (palace store + notes). NEVER create virtualenvs or install packages into `/workspace` — the workspace is snapshotted per checkpoint and any `.py` files there would pollute the solution.
3. **The CLI runs ephemerally via `uvx`** (container-local cache, no workspace writes). NEVER add `mempalace` to the project `requirements.txt` — that file feeds the evaluator and must stay app-only.
4. **Non-interactive, no-LLM mode only.** Always pass `--yes` where offered and init with `--no-llm`. Never configure an LLM provider, never ask the user anything.
5. **Mine notes, not the venv.** Mine only `.mempalace/notes/` (and, if useful, a specific docs dir). Never mine the palace directory itself or dependency caches.

## Invocation (every command)

```bash
export MEMPALACE_CONFIG_DIR=/workspace/.mempalace/config HF_HOME=/tmp/mempalace-hf
uvx --from mempalace==3.10.0 mempalace --palace /workspace/.mempalace/palace <command>
```

Agent shells do not persist exports — repeat the env vars on every invocation (or prefix each command). The first call downloads wheels into the container uv cache (1–2 min); later calls are fast.

## One-time setup (first checkpoint)

```bash
mkdir -p /workspace/.mempalace/notes
$MP init --yes --no-llm /workspace/.mempalace/notes
```

(where `$MP` is the invocation above). Verify:

```bash
$MP status
```

## Per-checkpoint loop

1. **Recall before coding.** For each area you are about to touch:

   ```bash
   $MP search "<topic>"
   ```

   Read the top hits (they are your own verbatim notes from earlier checkpoints).
2. **Journal while working.** Append short factual notes to `.mempalace/notes/YYYY-MM-DD-checkpoint-<N>.md` as you make decisions or hit surprises:

   ```markdown
   ## Decision: store for tasks
   Chose dict keyed by int id over list — O(1) lookup for the board API.

   ## Gotcha: error envelope
   Tests require {"error": {...}} body; FastAPI default `detail` fails CP1 tests.
   ```
3. **Mine after coding (cheap pass):**

   ```bash
   $MP mine /workspace/.mempalace/notes
   $MP status
   ```

   Mining is incremental; already-mined files are not duplicated.

## Conventions

- One note file per checkpoint per session; short factual bullets with headings, no transcripts.
- What to store: decisions + why, API contracts, error patterns, environment facts, worked procedures.
- What NOT to store: secrets/credentials, bulk code dumps, transient TODOs, speculation.

## Anti-patterns

- Adding `mempalace` to `requirements.txt`, or creating a venv/`uv venv`/`uv pip install` inside `/workspace`.
- Running without `--no-llm` / trying to configure providers or MCP.
- Pointing `--palace` outside `/workspace/.mempalace/`, or mining the whole workspace.
- Letting memory work delay or replace a working solution.

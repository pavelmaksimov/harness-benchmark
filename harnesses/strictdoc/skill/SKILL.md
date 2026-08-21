---
name: strictdoc
description: Requirements-management harness for coding agents. Maintain specification documents with StrictDoc (SDoc format) while implementing a benchmark checkpoint task. Use when activated by the benchmark prompt prefix ("Activate and follow the installed Codex skill `strictdoc`").
---

# StrictDoc requirements harness

You maintain a live requirement specification with [StrictDoc](https://strictdoc.readthedocs.io/) while you implement the task. The spec is your working memory across checkpoints: before coding a feature you record WHAT it must do as a requirement, then you implement it, then you prove the docs still build. Docs are a discipline device, not a deliverable — **a failing solution is never acceptable because docs passed**.

## Non-negotiable rules

1. **Solution first.** Every checkpoint's code must fully solve the spec. Doc work is capped at a small fraction of your effort; if time is tight, cut doc polish, never code.
2. **Everything lives in `strictdoc-docs/`** at the workspace root: `.sdoc` sources, config, and exports. Never scatter `.sdoc` files elsewhere; never modify hidden evaluator tests or problem data.
3. **Doc tooling is local-only.** Install StrictDoc with `uv tool install strictdoc` (isolated tool env). NEVER add `strictdoc` to the project `requirements.txt` — that file feeds the evaluator and must stay app-only.
4. **Non-interactive only.** No web UI, no server mode. CLI: `strictdoc` (v0.28.x console script; there is no `sdoc` binary).
5. **Docs gate:** `strictdoc export` exits non-zero on broken docs. Run it after every docs change; fix errors immediately. An empty/missing docs tree silently passes — always confirm your document appears in the export output.

## One-time setup (first checkpoint)

```bash
uv tool install strictdoc          # isolated env, binary on PATH
mkdir -p strictdoc-docs/docs
```

Create `strictdoc-docs/docs/SPEC.sdoc` covering the checkpoint spec (see format below), then validate:

```bash
cd strictdoc-docs
strictdoc export docs --output-dir sdoc-export --formats html || true   # first sanity run
grep -q "YOUR-FIRST-REQ-UID" sdoc-export/html/index.html sdoc-export/html/docs/*.html \
  && echo SPEC_OK || echo SPEC_MISSING
```

## SDoc format that actually parses (verified on strictdoc 0.28.1)

```text
[DOCUMENT]
TITLE: Backup Scheduler Specification
PREFIX: REQ-

[REQUIREMENT]
UID: REQ-BACKUP-001
TITLE: YAML config input
STATEMENT: >>>
The system shall read backup job definitions from a YAML config file.
<<<

[REQUIREMENT]
UID: REQ-BACKUP-002
TITLE: Incremental backups
STATEMENT: >>>
The system shall skip files unchanged since the last verified backup.
<<<
RELATIONS:
- TYPE: Parent
  VALUE: REQ-BACKUP-001
```

Grammar traps (all hit in practice):

- `[DOCUMENT]` has **no `UID:` field**; it needs `TITLE:` (plus optional `PREFIX:`).
- Relations are spelled **`RELATIONS:`** (`REFS:` is the old name — parse error here), placed after other fields; reference items use `TYPE:` + `VALUE:` with the target UID.
- Multiline fields open with `>>>` on the same line and close with `<<<` at line start.
- The file **must end with a newline** (missing final EOL = confusing TextXSyntaxError).
- Duplicate UIDs and dangling relation targets fail the export with a non-zero exit — treat that as your lint.

See [references/workflow.md](references/workflow.md) for the per-checkpoint loop and UID conventions.

## Per-checkpoint loop

1. **Read the new checkpoint spec.** Diff it against existing requirements: new features → new `REQ-*` items; changed behavior → edit the item (keep the UID stable, bump nothing else).
2. **Update `SPEC.sdoc`**, run the export gate until it exits 0 and your UIDs appear in the HTML.
3. **Implement** the checkpoint exactly per spec (entry file, tests, packaging as the task demands).
4. **Self-check**: run your own quick smoke of the implemented behavior, then re-run the export gate if you touched docs during implementation.
5. Only then claim done.

## UID conventions

- Prefix reflects kind: `REQ-*` functional requirements. One stable UID per distinct behavior; never renumber existing UIDs between checkpoints — traceability depends on stability.
- Link derived work with `RELATIONS: TYPE: Parent` chains so the traceability screen shows coverage.

## Anti-patterns

- Writing prose essays instead of atomic `The system shall …` statements.
- Regenerating UIDs every checkpoint (breaks traceability and review).
- Putting docs outside `strictdoc-docs/` or tool deps into `requirements.txt`.
- Spending more effort on HTML polish than on the actual implementation.

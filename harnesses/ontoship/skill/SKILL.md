---
name: ontoship
description: OntoShip knowledge-base harness (gitmark). Maintain a markdown knowledge base (md + README index + git ontology) of the project while implementing a benchmark checkpoint task, and search it with the gitmark CLI (SQLite FTS5, zero dependencies) instead of grepping blind. Use when activated by the benchmark prompt prefix ("Activate and follow the installed Codex skill `ontoship`").
---

# OntoShip knowledge-base harness (gitmark)

You maintain a live project knowledge base while you implement the task. The KB is your working memory across checkpoints: decisions, gotchas, and service notes are written down once as markdown and recalled by search, not by re-reading the whole codebase. **A failing solution is never acceptable because the KB passed.**

The CLI is `gitmark.py` — pure Python stdlib, zero dependencies, already installed next to this SKILL.md.

## Non-negotiable rules

1. **Solution first.** Every checkpoint's code must fully solve the spec. KB work is capped at a small fraction of your effort; if time is tight, cut KB polish, never code.
2. **Everything lives in `kb/`** at the workspace root. Never scatter KB files elsewhere; never touch hidden evaluator tests or problem data.
3. **Tooling is local-only.** Run `gitmark.py` with the system `python3`. NEVER add anything KB-related to the project `requirements.txt` — that file feeds the evaluator and must stay app-only.
4. **Markdown is the source of truth.** The index (`.gitmark/`) is a derived cache; regenerate it, never hand-edit it.
5. **Non-interactive only.** No `serve` in the background, no HTML map unless explicitly useful — `index`, `search`, `lint`, `stat` are enough.

## Locate the tool (once per session)

```bash
GM="$HOME/.config/opencode/skills/ontoship/gitmark.py"
[ -f "$GM" ] || GM="$(find / -name gitmark.py -path '*ontoship*' 2>/dev/null | head -1)"
python3 "$GM" version
```

If the script cannot be found, continue the task without the KB (write plain markdown into `kb/` anyway).

## One-time setup (first checkpoint)

```bash
mkdir -p kb/reference kb/decisions kb/plans
```

Create `kb/README.md` (master index) and one doc per area as you learn the codebase:

```markdown
---
node_type: reference
title: HTTP error envelope
status: active
updated: 2026-01-01
links:
  documents: [../app/errors.py]
---

# HTTP error envelope
All 4xx/5xx responses use {"error": {"code", "message", "details"?}} ...
```

Validate:

```bash
python3 "$GM" --root . index && python3 "$GM" --root . search "error envelope"
```

## Per-checkpoint loop

1. **Before coding:** `python3 "$GM" --root . index` (refresh the cache), then `search "<topic>"` for every area you are about to touch. Open the returned `file:line` hits and re-read the exact decision/gotcha docs.
2. **While implementing:** when you learn something durable (a design decision + why, a tricky failure + fix, an API contract), write it as a doc in `kb/` (see types below).
3. **After coding (cheap pass):** add ≥1 link per new doc, add a line to the folder's `README.md` index, then `python3 "$GM" --root . index && python3 "$GM" --root . lint` and fix what lint flags (orphans, broken links, missing frontmatter).

## Document ontology (keep it small)

- `node_type`: `service` | `reference` | `runbook` | `gotcha` | `decision` | `plan` | `guide` | `report` | `index`
- `status`: `active` | `draft` | `deprecated` | `archived`
- Folder by type: `kb/decisions/` for `decision`, `kb/reference/` for contracts/schemas, `kb/plans/` for `plan`; per-service docs under `kb/services/<svc>/`.
- Frontmatter minimum: `node_type`, `title`, `status: active`, `updated: YYYY-MM-DD`, plus a `links:` section with at least one `documents:` (code path) or `depends_on:`/`relates_to:` (sibling doc) entry. No orphans.
- Before creating a doc, `search` first — edit the existing doc instead of duplicating it.

## Anti-patterns

- Writing KB prose instead of code when the checkpoint is red — never.
- Putting `gitmark.py` or anything else into `requirements.txt`.
- Storing the KB outside `kb/`, or editing `.gitmark/` by hand.
- Skipping `lint` and leaving broken links/orphans behind for the next checkpoint.

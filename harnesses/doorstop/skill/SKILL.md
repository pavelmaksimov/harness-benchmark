---
name: doorstop
description: Requirements-management harness for coding agents. Maintain specification documents with Doorstop (YAML items in version control) while implementing a benchmark checkpoint task. Use when activated by the benchmark prompt prefix ("Activate and follow the installed Codex skill `doorstop`").
---

# Doorstop requirements harness

You maintain a live requirement specification with [Doorstop](https://doorstop.readthedocs.io/) while you implement the task. Doorstop stores requirements as YAML files in version control — the tree of items IS your spec. Before coding a feature you record WHAT it must do as an item, then you implement it, then you prove the document tree still validates. Docs are a discipline device, not a deliverable — **a failing solution is never acceptable because docs passed**.

## Non-negotiable rules

1. **Solution first.** Every checkpoint's code must fully solve the spec. Doc work is capped at a small fraction of your effort; if time is tight, cut doc polish, never code.
2. **Everything lives in `doorstop-docs/`** at the workspace root: documents, items, exports. Never scatter item YAML elsewhere; never modify hidden evaluator tests or problem data.
3. **Always pass the project root explicitly: `doorstop -j .`** (or `-j doorstop-docs`). Without `-j` doorstop resolves the default root to `/tmp` and silently creates/reads docs outside your workspace — this is the #1 headless trap.
4. **Run inside a git repo.** Doorstop integrates git; run `git init -q .` once at the workspace root if `.git` is missing, or commands print fatal git errors.
5. **Non-interactive only.** Export `EDITOR=true` in every shell that touches doorstop; never call `edit`; no server/GUI (`doorstop-server` / `doorstop-gui` are forbidden).
6. **Doc tooling is local-only.** Install with `uv tool install doorstop`. NEVER add `doorstop` to the project `requirements.txt` — that file feeds the evaluator and must stay app-only.

## One-time setup (first checkpoint)

```bash
uv tool install doorstop          # isolated env, binary on PATH
git init -q . 2>/dev/null || true # doorstop expects a VCS root
export EDITOR=true                # keep every operation non-interactive

mkdir doorstop-docs && cd doorstop-docs
doorstop -j . create REQ reqs                 # parent document (prefix REQ)
```

Child documents need an explicit parent (verified on doorstop 3.2):

```bash
doorstop -j . create TST tsts -p REQ          # ERROR "no parent specified" otherwise
doorstop -j . add REQ                          # → reqs/REQ001.yml
doorstop -j . add TST                          # → tsts/TST001.yml
```

Fill item text by editing the YAML directly with your file tools (not `doorstop edit`):

```yaml
active: true
derived: false
header: ''
level: 1.0
links: []
normative: true
ref: ''
reviewed: null
text: |
  The system shall read backup job definitions from a YAML config file.
```

## Per-checkpoint loop

1. **Read the new checkpoint spec.** Diff against existing items: new behavior → `doorstop -j . add <PREFIX>` + write `text:`; changed behavior → edit the same item file (UID = filename, keep stable).
2. **Link coverage**: `doorstop -j . link <child> <parent>` (e.g. `link TST1 REQ1`) so validation shows the tree.
3. **Validate the tree**:

```bash
cd doorstop-docs
doorstop -j .
echo "gate=$?"        # 0 = structurally valid; fix any WARNING like "no text"
```

4. **Implement** the checkpoint exactly per spec.
5. Only then claim done.

See [references/workflow.md](references/workflow.md) for command reference, publishing, and failure signatures.

## UID conventions

- Item UIDs come from the document prefix: `REQ001`, `REQ002`, `TST001`, … Never rename/reorder existing item files between checkpoints.
- Prefixes reflect kind: `REQ-*` requirements from the task spec, `TST-*` verification items when you want explicit test coverage links.

## Anti-patterns

- Forgetting `-j .` → docs materialize under `/tmp/doorstop/…` and your workspace tree stays empty.
- Running without git repo → `fatal: not a git repository` noise on document ops.
- Creating a second document without `-p <PARENT>` → `ERROR: no parent specified`.
- Items left with empty `text:` → permanent `WARNING: …: no text` on validation.
- Spending more effort on doc bookkeeping than on the actual implementation.

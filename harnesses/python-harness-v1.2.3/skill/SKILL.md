---
name: python-harness
description: Apply the pinned pavelmaksimov/python-harness catalog to Python implementation tasks. Benchmark mode is non-interactive and chooses the smallest compatible rule set from repository evidence.
---

# Python Harness — benchmark mode

This skill adapts `pavelmaksimov/python-harness` for a reproducible Codex benchmark run.

## Pinned source

- Repository: `https://github.com/pavelmaksimov/python-harness`
- Commit: `f96781a32da3481b90d24bc054d3c8e6a86fc29f`
- Catalog version: `1.2.3`

The commit is the source of truth for every rule/template used in this run. Do not use the moving `master`/`main` branch.

## Benchmark-specific contract

The upstream setup skill is interactive by design. Benchmark runs must not be.

- Do **not** ask the user which bands, adapters, install scope, or optional rules to select.
- Infer the smallest compatible set from the task specification and the repository as it exists at the start of the checkpoint.
- Make the same choice from the same evidence; do not choose randomly or from personal preferences.
- Task requirements and existing repository conventions outrank this harness.
- The harness constrains *how* to implement the requested behavior. It must not expand product scope or add unrelated infrastructure.
- Keep the source checkout outside the solution workspace so harness files do not pollute LOC/diff metrics.
- Never modify hidden/evaluator tests.

## Load the pinned catalog

Before implementation, obtain and verify the exact catalog in a temporary directory:

```bash
commit=f96781a32da3481b90d24bc054d3c8e6a86fc29f
catalog_dir="${TMPDIR:-/tmp}/hb-python-harness-${commit}"

if [ ! -d "$catalog_dir/.git" ]; then
  rm -rf "$catalog_dir"
  git clone --quiet https://github.com/pavelmaksimov/python-harness.git "$catalog_dir"
fi

git -C "$catalog_dir" fetch --quiet origin "$commit"
git -C "$catalog_dir" checkout --quiet --detach "$commit"

test "$(git -C "$catalog_dir" rev-parse HEAD)" = "$commit"
test "$(tr -d '\r\n' < "$catalog_dir/VERSION")" = "1.2.3"
```

If the pinned commit cannot be fetched or verified, report that the harness source could not be loaded. Do not silently substitute a different revision.

Read the Catalog section of `$catalog_dir/README.md` before selecting rules.

## Deterministic rule selection

### Core

Read and apply these for every Python task:

- `python-tooling`
- `python-structure`
- `python-exceptions`
- `python-settings`
- `python-logging`
- `python-di`
- `python-fsm`
- `python-retry`
- `python-tests`

Read these only when repository/task evidence makes them relevant:

- `python-freezegun` — time-dependent behavior/tests
- `python-polyfactory` — Pydantic/ORM models benefit from factories
- `python-semver` — publishable library/public API versioning

### Adapters

Select only when the corresponding technology/boundary exists or is required by the task:

- `python-fastapi` — inbound FastAPI HTTP API
- `python-base-client` — outbound HTTP adapter; infer async vs sync from the codebase
- `python-sqlalchemy` — SQLAlchemy persistence
- `python-alembic` — Alembic migrations
- `python-redis` — Redis cache/storage
- `python-telegram` — python-telegram-bot
- `python-monitoring` — Prometheus/`llm_common` monitoring

### Enforcement

Use the catalog guidance for:

- `layers-linter`
- `domain-types-linter`
- `patch-linter`

Add `di-linter` only when the repository uses the Container/LazyInit DI style or the selected changes introduce it.

Do not install a linter merely to satisfy this list if the task environment cannot support it. The rules still apply as review criteria.

## Applying selected entries

For each selected rule under `harnesses/rules/<id>/`:

1. Read its `.mdc` file completely before implementing code in that area.
2. Read sibling `.md` templates only when the task needs the structure they describe.
3. Treat templates as canonical examples, not permission to overwrite existing project files.
4. Adapt the catalog's default `project/` package root to the actual package root.
5. Preserve existing public APIs and repository conventions unless the task explicitly changes them.

For selected enforcement entries under `harnesses/skills/<id>/`, read `SKILL.md` before the final verification pass. Use their CLI checks when applicable and available.

Do not copy `.cursor/` files into the solution merely to activate the harness: Codex is already consuming the rules through this skill, and benchmark snapshots should contain only solution/process files that the implementation itself needs.

## Work sequence

1. Inspect the task and current repository.
2. Load and verify the pinned catalog.
3. Select rules deterministically using the mapping above.
4. Read the selected rule files and relevant templates.
5. Implement the requested feature completely, keeping the design proportional to the task.
6. Add or update tests according to `python-tests`; tests must validate behavior, not evaluator internals.
7. Run the repository's normal tests/checks.
8. Run selected enforcement checks when they are applicable and available.
9. Re-read the selected rules for a short compliance pass and fix violations that do not conflict with the task.

The goal is a correct solution shaped by the pinned Python Harness, not a demonstration project containing every pattern in the catalog.

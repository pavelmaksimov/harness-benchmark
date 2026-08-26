# python-harness-v1.3.0 benchmark arm

Benchmark adapter for [`pavelmaksimov/python-harness`](https://github.com/pavelmaksimov/python-harness),
pinned to catalog version `1.3.0`.

Pinned source:

- catalog version: `1.3.0`
- commit: `86952fdb7160388f7a0fb742e45e58d5def9cac6`

Same activation contract as `python-harness` / `python-harness-v1.2.3`: the Codex
skill fetches the exact pinned commit into a temporary directory outside the
solution workspace, selects the smallest compatible rule set from
repository/task evidence without asking questions, and applies the upstream
rules directly. No `.cursor/` files are copied into the solution workspace.

For OpenCode, the pinned catalog rules are flattened into
`harnesses/python-harness-v1.3.0/AGENTS.md` and mounted read-only as the
workspace `AGENTS.md`. This is an activation transport only.

## Changes vs v1.2.3

Upstream v1.3.0 adds core rules `python-workflow`,
`python-development-rules`, and adapters `python-db-sessions` (installed
together with `python-sqlalchemy`) and `python-speech`; several existing rules
(SQLAlchemy N+1-safe repositories, structure split into
`python-module-structure`, polyfactory ORM factories, redis cache repository)
were reworked. The flattened `AGENTS.md` and the skill selection lists track
the v1.3.0 catalog.

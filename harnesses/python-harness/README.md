# python-harness benchmark arm

Benchmark adapter for [`pavelmaksimov/python-harness`](https://github.com/pavelmaksimov/python-harness).

Pinned source:

- catalog version: `1.2.3`
- commit: `f96781a32da3481b90d24bc054d3c8e6a86fc29f`

The upstream setup workflow asks the user to choose bands and optional entries. That is useful interactively but makes benchmark runs nondeterministic. This arm keeps the upstream catalog as the source of truth and changes only the activation workflow:

1. the Codex skill fetches the exact pinned commit into a temporary directory outside the solution workspace;
2. it selects the smallest compatible set from repository/task evidence without asking questions;
3. it reads and applies the selected upstream rules directly;
4. task/repository constraints override catalog defaults;
5. no `.cursor/` harness files are copied into the solution just for activation.

For OpenCode, the pinned catalog rules are also flattened into
`harnesses/python-harness/AGENTS.md` and mounted read-only as the workspace
`AGENTS.md`. This is an activation transport only: the file is not copied into
the stored solution snapshot.

## First validation

This arm intentionally has no `SMOKE.json` yet: it has never been exercised.
Run CP1 smoke for each agent you intend to compare before any full experiment:

```bash
uv run python -m benchmark smoke --arm python-harness --problem file_backup
uv run python -m benchmark smoke --arm python-harness --agent opencode \
  --provider opencode_auth --model <model> --thinking none
```

After the smoke, triage any failed evaluator setup separately from solution defects, inspect the snapshot for non-solution artifacts, update `EXCLUDE_DIR_NAMES` only if needed, and commit the generated `SMOKE.json`.

The arm is deliberately not added to `DEFAULT_EXPERIMENT_ARMS` until that smoke passes, so existing `run-all` commands remain usable.

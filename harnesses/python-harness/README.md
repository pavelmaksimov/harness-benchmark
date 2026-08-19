# python-harness benchmark arm

Benchmark adapter for [`pavelmaksimov/python-harness`](https://github.com/pavelmaksimov/python-harness).

Pinned source:

- catalog version: `1.2.3`
- commit: `38ada37707ba31fea94ec852b3272b77364a88fd`

The upstream setup workflow asks the user to choose bands and optional entries. That is useful interactively but makes benchmark runs nondeterministic. This arm keeps the upstream catalog as the source of truth and changes only the activation workflow:

1. the Codex skill fetches the exact pinned commit into a temporary directory outside the solution workspace;
2. it selects the smallest compatible set from repository/task evidence without asking questions;
3. it reads and applies the selected upstream rules directly;
4. task/repository constraints override catalog defaults;
5. no `.cursor/` harness files are copied into the solution just for activation.

## First validation

This arm intentionally has no `SMOKE.json` yet: it has never been exercised. Run the required CP1 smoke before any full experiment:

```bash
uv run python -m benchmark smoke --arm python-harness --problem file_backup
```

After the smoke, triage any failed evaluator setup separately from solution defects, inspect the snapshot for non-solution artifacts, update `EXCLUDE_DIR_NAMES` only if needed, and commit the generated `SMOKE.json`.

The arm is deliberately not added to `DEFAULT_EXPERIMENT_ARMS` until that smoke passes, so existing `run-all` commands remain usable.

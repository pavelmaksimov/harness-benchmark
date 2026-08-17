# Task Manager CP1 experiment readiness

Date: 2026-08-17  
Scope: cheap offline path (no Docker / Codex smoke).

## Reference solutions policy

Only `problems/task_manager/solutions/checkpoint_1/` is retained for a cheap offline CP1 check.  
CP2–CP15 have **no** cumulative reference apps: evaluation tests + checkpoint prompts grade the **agent** solution at run time. CP13–CP15 prompts/tests are ready under that policy.

## Proven

### Reference CP1 tests

```bash
bash scripts/sync_task_manager_problem.sh
cd problems/task_manager
PYTHONPATH=solutions/checkpoint_1 uv run pytest tests/test_checkpoint_1.py -q \
  --entrypoint='python -m uvicorn task_manager.main:app' \
  --checkpoint=checkpoint_1 --confcutdir=tests
```

| Group | Passed |
|-------|--------|
| Core (unmarked) | 7 |
| Functionality | 2 |
| Error | 3 |
| **Total** | **12** |

### Offline harness wiring

`uv run python -m benchmark validate-problem --problem task_manager`

- Symlink `vendor/scb-problems/task_manager` → `problems/task_manager`
- Catalog: 15 checkpoints in order; CP2+ `include_prior_tests`
- CP1-only staging leaves a single checkpoint (same helper as smoke)
- `DEFAULT_PROBLEM` remains `file_backup`; CLI `--problem task_manager` is additive
- `vendor/scb-problems/file_backup` git-clean (only untracked vendor entry is the `task_manager` symlink)

### Skill smoke gate (no re-smoke)

No skill arm content was changed for `task_manager`. Offline check: `is_smoke_validated` is true for all registered arms (baseline needs none; others grandfathered with matching `harness_content_sha`). **Docker Codex smoke was not run** (no local slop-code agent images).

## Metrics excludes

Current `EXCLUDE_DIR_NAMES` leaf names (do not add `tests` or `snapshot`):

`.git`, `.venv`, `venv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `node_modules`, `dist`, `build`, `.tox`, `graphify-out`

Expected non-solution dirs in future Docker smokes (already excluded or review then): `.git`, `.venv`, caches, `graphify-out`. Agent-authored `tests/` must keep counting. No new leaf names added without a live smoke snapshot.

## Deferred

- `bash scripts/build_images.sh` and full `benchmark smoke --arm ponytail --problem task_manager` once images exist (see issue 18 / pre-full-run checklist).

# Agent notes (harness-benchmark)

## `task_manager`: workspace must be on `sys.path` for eval

SCB runs pytest via `uvx` with cwd `/workspace`. That directory is **not** always on Python’s `sys.path`, so `import task_manager` fails in TestClient fixtures even when the agent’s package is present under `/workspace/task_manager/`.

**Required fix** (already in problem tests — keep it):

- `problems/task_manager/tests/conftest.py` — `_ensure_workspace_on_sys_path()` in `pytest_configure` and before reload/import of `task_manager.main`
- `problems/task_manager/tests/helpers.py` — put cwd on `PYTHONPATH` for the Uvicorn subprocess the same way

Only insert cwd when `(cwd / "task_manager").is_dir()`, so local offline runs with `PYTHONPATH=solutions/checkpoint_N` still work.

**Symptom if the path fix is missing or removed:** almost all CP tests ERROR at setup with `ModuleNotFoundError: No module named 'task_manager'`; only `test_uvicorn_serves_same_app` may PASS. That score is invalid — re-score the same snapshot after restoring the path fix (see `.cursor/rules/benchmark-failure-triage.mdc`).

Do not treat such scores as model failure or as a harness-arm result.

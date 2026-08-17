# Agent notes (harness-benchmark)

## `task_manager`: workspace must be on `sys.path` for eval

SCB runs pytest via `uvx` with cwd `/workspace`. That directory is **not** always on Python’s `sys.path`, so `import task_manager` fails in TestClient fixtures even when the agent’s package is present under `/workspace/task_manager/`.

**Required fix** (already in problem tests — keep it):

- `problems/task_manager/tests/conftest.py` — `_ensure_workspace_on_sys_path()` in `pytest_configure` and before reload/import of `task_manager.main`
- `problems/task_manager/tests/helpers.py` — put cwd on `PYTHONPATH` for the Uvicorn subprocess the same way

Only insert cwd when `(cwd / "task_manager").is_dir()`, so local offline runs with `PYTHONPATH=solutions/checkpoint_N` still work.

**Symptom if the path fix is missing or removed:** almost all CP tests ERROR at setup with `ModuleNotFoundError: No module named 'task_manager'`; only `test_uvicorn_serves_same_app` may PASS. That score is invalid — re-score the same snapshot after restoring the path fix (see `.cursor/rules/benchmark-failure-triage.mdc`).

Do not treat such scores as model failure or as a harness-arm result.

## Eval deps: tests vs solution (do not whitelist every app library)

SCB runs pytest via `uvx` in an **isolated** env. That env is **not** the agent’s `.venv` (usually absent from the snapshot anyway).

Two sources of packages:

| Source | What it is for |
|--------|----------------|
| `problems/<name>/config.yaml` → `test_dependencies` | What **tests** (and the baseline stack they import) need: `fastapi`, `httpx`, `pytest` plugins already added by SCB, … |
| Snapshot `requirements.txt` (else PEP 621 `pyproject.toml`) | What the **app** needs: anything the agent installed (`pwdlib`, `passlib`, …) |

`test_dependencies` is **not** a growing whitelist of every library a model might pip-install. Do not add app-only packages there.

**How solution deps reach eval:** environment `eval_commands` already do `uv add -r requirements.txt` into the workspace uv project (helps the `uv run` Uvicorn subprocess). TestClient imports still happen **inside `uvx`**, which would otherwise ignore that project. HB patches `PytestRunner._build_with_flags` (`benchmark/eval_deps_hook.py`, loaded from `benchmark.scb_main` and `harness_sitecustomize` so ProcessPool workers get it) and appends:

- `--with-requirements=requirements.txt` when that file exists in the snapshot (extras like `pwdlib[argon2]`, pins, and typical git URLs stay in the file; `uvx` installs them).
- otherwise `--with=<PEP 508>` for each `project.dependencies` entry in `pyproject.toml`.

**Limits**

- Not read: Poetry-only / Pipenv / Conda manifests, the agent `.venv`.
- Missing `requirements.txt` and no PEP 621 deps: no extra `uvx` packages. Undeclared `import pwdlib` → `ModuleNotFoundError` (agent did not declare deps — valid miss, not a reason to grow `test_dependencies`).
- Malformed `requirements.txt`: `uvx` fails while building the test env (visible in eval stderr; SCB may set `infrastructure_failure`).
- Malformed `pyproject.toml`: hook raises `ValueError` so eval fails clearly.
- `-e .` / exotic index flags in requirements may fail at install time; that failure is the signal, not a whitelist gap.

**Known case (2026-08-17):** agent used `pwdlib[argon2]` in-session; eval `uvx` lacked it and tests ERROR’d on import. Fix is the snapshot `requirements.txt` path above, not adding `pwdlib` to `test_dependencies`.

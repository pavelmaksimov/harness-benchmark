# Agent notes (harness-benchmark)

## Cursor rules (обязательные к прочтению)

Правила из `.cursor/rules/` — они применяются Cursor, но агенты вне Cursor должны читать их напрямую. Ключевые для работы с бенчмарком:

| Правило | О чём |
|---------|-------|
| [benchmark-core](.cursor/rules/benchmark-core.mdc) | Инварианты репозитория: layout, arms, параллельные прогоны (`--jobs`), do-not |
| [benchmark-failure-triage](.cursor/rules/benchmark-failure-triage.mdc) | Триаж упавших smoke/run: bench vs модель, re-score снапшота |
| [benchmark-git-cleanup](.cursor/rules/benchmark-git-cleanup.mdc) | Удаление агентских `.git` внутри снапшотов после прогонов |
| [benchmark-metrics](.cursor/rules/benchmark-metrics.mdc) | Метрики: источники, exclusions (`EXCLUDE_DIR_NAMES`), сравнение |
| [benchmark-new-harness](.cursor/rules/benchmark-new-harness.mdc) | Чеклист нового skill arm: smoke CP1 → `SMOKE.json` → full-run gate |
| [benchmark-pitfalls](.cursor/rules/benchmark-pitfalls.mdc) | Известные грабли MVP: Docker credHelpers, `save_dir`, ProcessPool hook, sandbox |
| [benchmark-runner](.cursor/rules/benchmark-runner.mdc) | Конвенции правки runner/хуков/SCB-инвокации, model/provider флаги |
| [benchmark-wait](.cursor/rules/benchmark-wait.mdc) | Ожидание длинных прогонов: поллинг каждые 5 минут |
| [conventional-commits](.cursor/rules/conventional-commits.mdc) | Формат commit-сообщений (предлагать, не коммитить) |
| [graphify](.cursor/rules/graphify.mdc) | Навигация по графу зависимостей и связям файлов |

## `task_manager`: workspace must be on `sys.path` for eval

SCB runs pytest via `uvx` with cwd `/workspace`. That directory is **not** always on Python’s `sys.path`, so `import task_manager` fails in TestClient fixtures even when the agent’s package is present under `/workspace/task_manager/`.

**Required fix** (already in problem tests — keep it):

- `problems/task_manager/tests/conftest.py` — `_ensure_workspace_on_sys_path()` in `pytest_configure` and before reload/import of `task_manager.main`
- `problems/task_manager/tests/helpers.py` — put cwd on `PYTHONPATH` for the Uvicorn subprocess the same way

Only insert cwd when `(cwd / "task_manager").is_dir()`, so local offline runs with `PYTHONPATH=solutions/checkpoint_N` still work.

**Symptom if the path fix is missing or removed:** almost all CP tests ERROR at setup with `ModuleNotFoundError: No module named 'task_manager'`; only `test_uvicorn_serves_same_app` may PASS. That score is invalid — re-score the same snapshot after restoring the path fix (see `.cursor/rules/benchmark-failure-triage.mdc`).

Do not treat such scores as model failure or as a harness-arm result.

## `task_manager` CP7: version only for intentional edits

`version` grows for tasks the request **meant** to change (target patch/place, tasks explicitly moved by a multi-task op such as state delete + replacement).

Do **not** bump `version` on neighbors only because the board reflowed their `board_position` after another card left the column. That side effect caused a false CP12 Core fail when a test patched two occurrences with versions taken before the first move (`VERSION_CONFLICT` → missing `title` in the error body).

Locked by `test_neighbor_version_unchanged_when_other_task_leaves_column` in `problems/task_manager/tests/test_checkpoint_7.py`.

## `task_manager`: controlled clock — read `TASK_MANAGER_NOW` per request

Tests freeze/advance time via env `TASK_MANAGER_NOW` **without** restarting the app process (`controlled_clock` in conftest).

The app must resolve “now” on **every** HTTP request (or every call into overdue / maintenance / horizon logic), not once at import or lifespan startup. Caching the clock at boot → wrong overdue, reminders, recurrence horizon after `freeze()`.

Stated in `checkpoint_1.md` / `checkpoint_3.md` / `checkpoint_11.md`.

## `task_manager`: error JSON shape (not FastAPI `detail`)

Eval asserts `{"error": {"code": "...", "message": "...", "details"?}}` via `assert_error_contract`.

Default FastAPI/Starlette bodies with top-level `detail` fail even when status codes are right. Override validation/HTTP exception handlers so `422` / `401` / `404` / `409` (and similar) use the `error` envelope. See CP1 Shared HTTP contract.

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

## Rework loop: test-failure retries (`--rework-attempts` / `HB_REWORK_ATTEMPTS`)

`run` / `run-all` принимают `--rework-attempts N` (default `2`, min `0`; smoke всегда `0`).
Внутри одного чекпоинта при падении Core-тестов (не ошибка агента, не rate-limit,
не `infrastructure_failure`, не skip/concurrent eval) агент пере-вызывается с тем же
промптом + блоком `[REWORK ATTEMPT k]` со списком упавших тестов; workspace
сохраняет код предыдущей попытки (`Session.finish_checkpoint` не сбрасывает workspace),
попытка пере-оценивается обычным пайплайном.

- Хук: `benchmark/rework_hook.py` — monkeypatch `AgentRunner._run_checkpoint`
  (установка из `benchmark.scb_main.py` и `harness_sitecustomize` для ProcessPool-воркеров,
  идемпотентно). Vendor SCB не трогаем.
- Артефакт: `<checkpoint>/rework.json` (`attempts_total`, `fixed`, `attempts[]`).
- Метрики: `cumulative.rework_*` (collect.py), строки `Rework attempts/fixed/unresolved`
  в comparison (compare.py), Notes в short report (publish.py), записи
  `source: "rework"` в `failures/<problem>.json` (rework.py).
- `failures.py` ключует записи по `(experiment_id, checkpoint, run_index)` —
  backward compatible (записи без `run_index` не выпадают).
- **Триаж:** чекпоинт, упавший после реворка, — по-прежнему валидный failure;
  `usage`/cost агента кумулятивны по попыткам (это намеренно — цена включает доработку).
  `infrastructure_failure` внутри реворка не считается моделью — см.
  `benchmark-failure-triage.mdc`.

## Resume invariants

`benchmark/resume_state.py` is a thin adapter over SCB's native
`detect_resume_point()`. It persists only run identity, lifecycle, checkpoint
statuses, completion, and the native stop point. Native SCB owns checkpoint
ordering and validity; red evaluations do not invalidate an agent-finished
checkpoint. The outer wrapper still requires explicit `--experiment-id`,
rejects legacy runs without `state.json`, and skips only completed runs with
readable `metrics/run.json`. The effective `rework_attempts` is persisted as
part of the run configuration so resume cannot silently change retry behavior.
Fresh repetitions never delete an existing `run_N`; they append new slots only
after validating the adapter/model/harness selection. Incomplete states remain
visible in reports but are excluded from averages until the run is complete.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

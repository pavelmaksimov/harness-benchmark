# Agent notes (harness-benchmark)

Ошибки, которые возникли в результате выполнения задачи, добавь инструкции по ним в AGENTS.md, 
чтоб в дальнейшем не возникали или агент понимал ситуацию и знал как исправить.
Если проблема имеет тематический характер, создай выделенный документ на эту тему
и записывай туда встречающиеся ошибки и их решения, оставив ссылку на этот документ в AGENTS.md

Запуск автоматического benchmark fleet - docs/fleet-autopilot.md

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

## Локальные проверки

В текущей среде тесты запускай через
`uv run pytest ...`, а не через `python -m pytest`. прогоняй `uv run ruff ...`;
Не запускай `uv run pytest` из корня без пути: он подхватывает `problems/` и
игнорируемые результаты со снапшотами, что приводит к конфликту pytest-опций и
ошибкам импорта чужих приложений. Полный набор тестов проекта запускай как
`uv run pytest tests -q`.

В текущей среде обычный `uv run pytest tests -q` работает без ручного пути к кэшу.
Если отдельный `uv run python -m benchmark ...` неожиданно падает на
`Read-only file system` внутри `/home/user/.cache/uv/sdists-v8/.git`, это локальная
проблема uv-кэша, а не benchmark; для такой диагностической команды используй
временный `UV_CACHE_DIR=/tmp/harness-benchmark-uv-cache`.

## Онбординг новых харнесов

Добавление/тестирование нового skill-arm (strictdoc, doorstop, …): чеклист внедрения,
известные проблемы/решения и советы по смоук-тестам — в
[docs/harness-onboarding.md](docs/harness-onboarding.md). Кратко: изучи инструмент руками на
ground truth → SKILL.md с non-interactive командами → arms.py + configs + prompt →
`scripts/pin_harness.py <name>` → `benchmark smoke --arm <name> --checkpoints 2` → триаж
снапшота → эксклюзии при необходимости → commit SMOKE.json. Смоук-гейт для skill-arm обязателен
перед полными прогонами.

### Инциденты внедрения strictdoc/doorstop (2026-08-21): проблемы → решения

Детальные таблицы грабель инструментов — в [docs/harness-onboarding.md](docs/harness-onboarding.md) (§3).

1. **Ложная `harness_activation_verified=false` у OpenCode skill-arm'ов.** OpenCode сохраняет
   промпт как `checkpoint_N/prompt.txt`, Codex — `checkpoint_N/agent/prompt.txt`; collect читал
   только второй путь. Симптом: маркер верифицирован (`marker.harness_activation_verified=true`),
   но итог false из-за `prompt_ok=false`. Фикс: `_checkpoint_prompt_text()` в
   `benchmark/collect.py` принимает оба пути. Новый адаптер с третьим путём даст тот же симптом —
   добавлять путь туда.

2. **Перепиннинг чужого арма инвалидирует его SMOKE.json.** Схема `tree_sha256` в исторических
   VERSION.json отличается от скриптовой; тестовый пересчёт tdd сменил бы хеш → рассинхрон
   `harness_content_sha` с маркером → `run-all` отказал бы. Правило: `scripts/pin_harness.py`
   для новых армов; после правок существующего `skill/` — перепиннить и ОБЯЗАТЕЛЬНО
   пересмокать этот арм.

3. **Код возврата после пайпа — код последней команды.** `strictdoc export … | tail; echo $?`
   возвращал код `tail`, из-за чего почти записали в скилл неверный вывод «экспорт всегда 0».
   Гейты проверять без пайпа либо с `set -o pipefail`.

4. **Запуск двух смоуков фоном из shell.** Редирект лога второго прогона упал («No such file or
   directory»), tool-timeout убил обёртку, дети выжили. Рабочий порядок: заранее создать
   лог-файл (абсолютный путь), `( setsid nohup … > log 2>&1 < /dev/null & )`, живость по
   `pgrep -af scb_main`; перед повторным запуском убедиться в отсутствии дублей процессов,
   иначе фантомный run_N.

5. **Удалённый `/tmp/tmp*` под живым контейнером** → потеря попытки doorstop-смоука. Симптомы:
   ws-source `[MISSING]` при живом контейнере; любой `docker exec` падает с «container breakout
   detected». Лечение: `docker rm -f <c>`, дождаться `phase=incomplete/interrupted` в state.json,
   перезапустить smoke начисто. Не чистить `/tmp` во время прогонов.

6. **Медленный free-tier ≠ зависание.** CP шёл часы против обычных ~40 минут; прогресс
   подтверждали mtimes файлов workspace на хосте (маунт-сурс из `docker inspect`). CPU агента
   почти не растёт (сетевые ожидания), логи SCB буферизуются — не убивать работающий прогон по
   «тишине» в tail лога или низкому CPU.

7. **Грамматика SDoc 0.28 и Doorstop 3.2 headless** — кратко: бинарь `strictdoc` (не `sdoc`),
   связи `RELATIONS:` (не `REFS:`), в `[DOCUMENT]` нет UID, файлу нужен завершающий `\n`,
   экспорт пустой директории выходит 0 → гейт = exit 0 И grep UID в HTML; doorstop — всегда
   `-j .` (дефолтный корень `/tmp!`), `git init`, дочерний документ `-p PARENT`, `EDITOR=true`.
   Полные таблицы и рабочие последовательности команд — §3.3/3.4 онбординг-дока.

8. **Пин комбинированного bundle-arm.** У bundle нет единственного `skill_sha256`: `pin_harness.py`
   хеширует payload из `skills/` и `home/`, поэтому вывод скрипта должен обращаться к этому полю
   через `meta.get(...)`, а не через `meta["skill_sha256"]`. Иначе VERSION.json успевает записаться,
   но сам скрипт завершается с `KeyError`.

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

## Инцидент `realworld` / bundle-arm (2026-08-22)

В эксперименте `realworld-opencode-x-preview-f-free-high-all-20260822-1838`
у арма
`combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd`
CP1 не прошёл не из-за кода модели: агент записал в снапшот
`uvicorn==0.38.1`, но такой версии не было в индексе evaluator. Изолированный
`uvx` завершился на разрешении зависимостей до запуска pytest:
`No solution found when resolving dependencies`. Поэтому CP1 имеет
`infrastructure_failure: true`, а его нулевой результат нельзя считать ошибкой
модели.

После resume CP2–CP14 действительно выполнились; итоговые артефакты содержат
13 успешных чекпоинтов из 14. Затем SCB завершился ошибкой очистки временного
окружения (`PermissionError: Operation not permitted` для
`/tmp/.../.venv`). Из-за этого `state.json` остался `phase=incomplete`, и
агрегатор правильно исключил весь run из обычных средних. Наличие каталогов и
`evaluation.json` поздних чекпоинтов не отменяет неполный статус run.

### Как предотвращать и разбирать

1. До полного запуска проверять все версии из snapshot `requirements.txt` тем
   же изолированным evaluator-путём, что использует `uvx`; в этом случае
   доступной заменой была `uvicorn==0.38.0`.
2. Ошибку установки зависимостей классифицировать как
   `infrastructure_failure`, открыть `evaluation/stderr.txt` и не включать
   этот CP в оценку качества модели.
3. После ошибки очистки не помечать run вручную завершённым. Сначала устранить
   проблему временного `.venv`, затем повторить run в чистом слоте и проверить
   `state.json`, `run_info.yaml` и наличие `evaluation.json` для каждого CP.

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

## Rework feedback and provider truncation

`--feedback-strategy current-first` prioritizes current checkpoint Core failures,
then other current failures, new regressions, and finally persistent regression
context. `v1` is a compatibility alias for `all-failures`; the complete failure
inventory remains in `rework.json` even when the prompt is shortened.

`--transient-retries N` / `HB_TRANSIENT_RETRIES=N` is disabled by default. A
retry is spent only for a high-confidence `provider_truncation` diagnosis:
`step_finish(reason=unknown)`, prior reasoning, output below 500 tokens, and no
explicit error, limit, or evaluator infrastructure failure. Transient retries
are recorded separately from semantic rework and are included in total usage,
elapsed time, and cost. They do not change `checkpoint_success` or Core scores.
Keep `transient_retries` and `feedback_strategy` unchanged when resuming a run;
the persisted values are part of run identity validation.

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

## Запуск длинных прогонов из агентского shell (грабли 2026-08-21)

Фоновый запуск `python -m benchmark run ...` из agent-shell имеет два режима отказа,
которые внешне выглядят как «запуск не удался», но оставляют живые процессы.

**1. Tool-timeout убивает процесс-группу, но не всё дерево.** Обёртка
`uv run python -m benchmark run` погибает, а внутренние `benchmark.scb_main`
воркеры выживают — их cmdline (`-m benchmark.scb_main run --config …`) **не**
совпадает с grep-паттерном `benchmark run`, так что проверка «процесс умер» через
`ps | grep "benchmark run"` даёт ложноотрицательный результат. Выжившее дерево
успевает создать `results/<exp>/<arm>/run_1/` (state.json `phase=started`) и
Docker-контейнер агента, который продолжает жечь квоту модели вхолостую
(headless opencode, никто не читает его stdout).

**2. Повторный запуск с тем же `--experiment-id` не падает громко.**
Обёртка молча создаёт следующий свободный слот `run_2` («новые прогоны не
удаляют старые run_N, а добавляют следующие индексы»). Признак двойного запуска:
«фантомный» `run_1` без прогресса + реальный прогресс в `run_2`.

**3. `&&` перед фоновым `... &` ломает область переменных и PID-файл.** В инциденте
2026-08-22 составная команда вида `подготовка && EXP=... && setsid nohup ... & PID=$!`
увела в фон всю цепочку; в родительской оболочке `EXP` оказался пустым. В результате
монитор продолжил работать, но PID записался в `logs/.monitor.pid`, а записанное
значение указывало на оболочку-обёртку, а не на наблюдатель. Исправление: подготовку
(`ls`, `mkdir`, проверки и присваивание `EXP`) выполнять отдельной командой, запуск
`setsid nohup ... > log 2>&1 < /dev/null &` оставить отдельной фоновой командой,
сразу сохранить `$!`, затем выполнить `disown`; после запуска проверить `/proc/$PID`,
`kill -0 "$PID"` и наличие monitor log. Если ошибка уже произошла, не запускать второй
benchmark: найти полное дерево через `pgrep -af scb_main`, определить PID процесса
`uv run python scripts/monitor_benchmark.py`/`setsid` и исправить только PID-файл.

Правила:

- Запускайте так: сначала отдельной командой создать каталоги логов, затем
  `setsid nohup uv run python -m benchmark run … > log 2>&1 < /dev/null & disown`.
  После запуска проверять живость по **полному** дереву: `pgrep -af scb_main`.
- Если запуск был прерван (timeout, Ctrl-C, kill) — перед повторным запуском с тем
  же `--experiment-id` проверить и прибрать: `pgrep -af scb_main`,
  `docker ps` (осиротевшие контейнеры агентов), свежие `results/<exp>/<arm>/run_N`.
- Осиротевший контейнер → `docker stop <name>`; фантомный `run_N` без оценок —
  убрать из `results/` (архивировать), иначе он попадёт в отчёты как incomplete.
- Сопоставление контейнер→run: source mount `/workspace`
  (`docker inspect <c> --format '{{range .Mounts}}{{if eq .Destination "/workspace"}}{{.Source}}{{end}}{{end}}'`)
  должен совпадать с `working_dir=` из строки `Workspace prepared` в `infer.log` прогона.

## Логи SCB буферизуются: истиной является диск, не tail

structlog пишет в файлы с блочной буферизацией: `scb_run.log` / `infer.log` /
`run_agent.log` могут отставать от реальности на десятки минут. «steps=0 в течение
20 минут» в хвосте лога — ещё не зависание. Истинное состояние:

- диск: наличие `scb/<problem>/checkpoint_N/` и `evaluation.json` в них;
- `state.json` (`phase`, `stopped_at_checkpoint`);
- живые процессы внутри контейнера: `docker top <container>` (активный `opencode …`
  = агент работает; только `sleep infinity` + осиротевший `uvicorn` = поток мёртв).

Прежде чем «чинить зависание», сверьте минимум два из трёх источников.

## Новый OpenCode-модели нужен catalog overlay (+ variants для thinking)

Чтобы запустить модель через `--agent opencode --provider opencode_auth --model X`:

1. Добавьте `configs/models/X.yaml`: `internal_name`, `provider: opencode_auth`,
   нулевой pricing для free-tier, `agent_specific.opencode.provider_name: opencode`.
2. Для `--thinking high|max|low` SCB передаёт `--variant=<имя>`. Каталог models.dev
   может объявлять `reasoning_options` (low/high/max), но **не иметь именованных
   variants** (пример: `x-preview-f-free`, релиз 2026-08-21) — тогда варианта нет и
   флаг бесполезен. Определите варианты прямо в overlay:

```yaml
agent_specific:
  opencode:
    provider_name: opencode
    config:
      provider:
        opencode:
          models:
            X:
              variants:
                low:  { reasoningEffort: low }
                high: { reasoningEffort: high }
                max:  { reasoningEffort: max }
```

3. Перед долгим прогоном dry-проверьте цепочку (без Docker): загрузка каталога как в
   `benchmark.scb_main` → `ModelCatalog.get("X")` → `OpenCodeAgent._from_config(...,
   thinking_preset="high")` → `_get_variant_flag()` == `--variant=high` и содержимое
   `_make_opencode_config()` с вариантами.
4. Одна и та же модель может быть доступна на нескольких маршрутах провайдера
   (`opencode/x-preview-f-free` и `opencode-go/ox-alpha-free` — один и тот же
   «Ox Alpha Free»). Конвенция репозитория — маршрут `opencode`
   (`provider_name: opencode`).

## Free-tier: тихая обрезка первой попытки (reason=unknown, 0 токенов)

Известный паттерн бесплатных маршрутов OpenCode Zen: первая попытка чекпоинта
отдаёт один `reasoning`-шаг, затем `step_finish` c `reason="unknown"`, нулями во
всех токенах и пустым снапшотом → все Core-тесты падают. Это флейк провайдера, а не
приговор модели и не инфраструктура: rework-цикл пере-вызывает агента, и вторая
попытка обычно проходит (пример: task_manager CP1 у x-preview-f-free, 2026-08-21 —
после реворка 7p/0f). Диагностика: `checkpoint_N/agent/messages.jsonl` (1–3 события)
+ нули в `inference_result.json`. Не списывайте такой CP модели без учёта реворка.

## Rework-промпты и resume: не редактируйте артефакты прогона руками

`prompt.txt` чекпоинта сравнивается нативным resume с заново отрендеренным
ожидаемым промптом (`_check_prompt_mismatch`; сравнение через `strip()`,
т.е. нормализовано по краям, но не по содержимому). Любое содержимое,
которого нет в каноническом рендере — в том числе оставленный блок
`[REWORK ATTEMPT]` — инвалидирует этот чекпоинт **и все последующие**
(SPEC_CHANGED): SCB при `--resume` перезапустит их с началом цепочки и
удалит протухшие каталоги, а finalize классифицирует весь run как
`incomplete`.

- Правильное лечение причины — в коде (`rework_hook.py` восстанавливает
  канонический промпт всегда, не только при успехе реворка).
- Если run уже завершён со старым багом: НЕ запускайте `--resume`, чтобы
  «починить» фазу, — при invalidated-цепочке это удалит готовые результаты.
  Либо примите `incomplete` (такой run не попадёт в средние отчёта), либо
  сначала почините артефакты (см. следующий раздел) и **обязательно
  прогоните детектор до запуска resume**.

## Восстановление прогона после внешней гибели контейнера (рецепт 2026-08-21)

Если агентский runtime-контейнер убит извне (например, массовое удаление
docker-контейнеров посреди чекпоинта):

1. Симптомы фатального выхода SCB: `ExecutionError` про workspace
   (`expected … got: /tmp/tmpXXXX`), а `run_info.yaml` помечает **ВСЕ**
   чекпоинты `skipped` (summary пишется из пустого in-memory списка
   результатов). finalize ставит `phase=incomplete`.
2. Наивный `--resume` в таком состоянии инвалидирует ВСЕ чекпоинты
   (MISSING_RESULT) → удалит все `evaluation.json`/`rework.json` и начнёт
   задачу с нуля. Не запускайте его до починки.
3. Починка (проверено на healthchecks 2026-08-21):
   - регенерируйте `prompt.txt` **рендерером SCB**, а не ручной резкой:
     `_generate_expected_prompt(config, checkpoint, template, environment,
     entry_file, is_first_checkpoint=…)` c входами из
     `benchmark.resume_state._native_inputs(problem)` +
     `_saved_native_inputs(run_dir)` (это `prompt_content` из
     `scb/config.yaml` и `scb/environment.yaml`);
   - приведите `run_info.yaml` `summary.checkpoints` к факту: завершённые
     чекпоинты → `ran`, оборванный → `error`;
   - проверка перед запуском: `detect_native_resume(run_dir, problem)`
     должен показать `invalidated == [целевой чекпоинт]` и ничего больше.
4. Гард слотов в CLI: `--resume` требует `--runs >= max(индекс run_N)`
   («baseline=2; pass --runs 2»), а увеличение `--runs` создаст **полный
   новый прогон** в отсутствующем слоте. Обход — прямой вызов одного слота
   в обход матрицы:

```python
from benchmark.scb_run import run_one
run_one(arm="baseline", problem=<problem>, run_index=<slot>,
        experiment_id=<id>, agent="opencode",
        provider="opencode_auth", model=<model>, thinking=<thinking>,
        resume=True)
```

   (`thinking` передавайте явно: дефолт для opencode — `none`.)

## Time в лидерборде — это время инференса, не wall-clock

Колонка `Time` = сумма `elapsed_seconds` по чекпоинтам (чистое время
агентских сессий). Wall-clock больше за счёт: eval'а тестов в Docker после
каждого чекпоинта/реворк-попытки (~2–6 мин каждая), снапшотов/diff/сбора
метрик, параллельной конкуренции прогонов за Docker/CPU и простоев по
инцидентам. Ожидайте wall ≈ 2–4× от `Time`.

## Rework-фидбек на поздних чекпоинтах: хвост регрессий демотивирует агента

`evaluation` каждого чекпоинта гоняет весь накопленный тестовый сет: тесты
непройденных прошлых чекпоинтов попадают в Regression-бакет текущей оценки.
`rework_hook.failed_test_names()` собирает упавшие тесты из ВСЕХ бакетов,
поэтому реворк-промпт на поздних чекпоинтах перечисляет ~20+ тестов,
большинство из которых — исторически нереализованные фичи, не исправимые в
одной попытке. Наблюдение (healthchecks/x-preview-f-free, 2026-08-21): 3
попытки подряд дают идентичные pass_counts — агент тонет в списке. Улучшение:
в фидбеке отделять тесты текущего чекпоинта (политика) от регрессионного
хвоста или ранжировать по бакетам.

## Free-tier обрезки повторяются и внутри реворка

Тихая обрезка (`step_finish reason=unknown`, 300–400 output-токенов, один
reasoning-шаг) поражает не только первые попытки: зафиксированы случаи в
реворк-попытках и в финальной попытке чекпоинта (healthchecks CP18, три
независимых сета попыток). Признак для диагностики: `messages.jsonl`
заканчивается парой `reasoning → step_finish(reason=unknown)`,
`inference_result.usage.net_tokens.output < 500`. Отличать от реального
провала модели: чистые (необрезанные) попытки того же агента на том же
чекпоинте дают стабильный результат.

## Автопилот fleet

Целевое состояние для unattended-прогонов хранится в [configs/desired.yaml](configs/desired.yaml).
План и read-only статус проверяются командами `uv run python -m benchmark fleet plan` и
`uv run python -m benchmark fleet status`; демон запускается через `uv run python -m benchmark fleet`.
Точные имена можно узнать командами `uv run python -m benchmark catalog providers` и
`uv run python -m benchmark catalog models`; перед запуском проверяйте конфиг через
`uv run python -m benchmark fleet validate --config configs/desired.yaml`. Для
воспроизводимого выбора используйте профиль из `configs/profiles/` и сначала
проверьте его через `uv run python -m benchmark profile validate --config <path>`.
Тикеты, требующие человека, пишутся в `ops/needs-human/`; после исправления причины в тикете
нужно выставить `resolved: true`. Полная инструкция — в
[docs/fleet-autopilot.md](docs/fleet-autopilot.md); чеклист нового arm — в
[docs/harness-onboarding.md](docs/harness-onboarding.md).

## Запрос на новый профиль запуска benchmark

Когда пользователь просит добавить профиль для новой модели, агента или провайдера, проходи этот workflow:

1. **Проверь существующие идентификаторы.** Выполни `uv run python -m benchmark catalog providers` и
   `uv run python -m benchmark catalog models`. Не угадывай имена и не подставляй произвольный API id.
2. **Раздели случай.** Если agent/provider/model уже есть в каталогах — создай только
   `configs/profiles/<profile-id>.yaml`. Если отсутствует модель — сначала добавь и проверь её overlay в
   `configs/models/`. Если отсутствует provider — сначала подключи его к каталогу credentials по правилам
   `benchmark-runner`. Если отсутствует agent — сначала добавь его adapter, регистрацию и `configs/agent_<name>.yaml`;
   один профиль не регистрирует новый agent/provider/model.
3. **Создай профиль** с полями `id`, `agent`, `provider`, `model`, `thinking` и, при необходимости,
   `description`. Пути к профилям в `desired.yaml` задаются относительно корня репозитория.
4. **Проверь профиль до desired-конфига:**

   ```bash
   uv run python -m benchmark profile validate \
     --config configs/profiles/<profile-id>.yaml \
     --check-credentials
   ```

   Проверка должна завершиться с кодом `0`; credentials не выводи и не добавляй в YAML.
5. **Проведи реальный smoke** на нужном arm:

   ```bash
   uv run python -m benchmark profile smoke \
     --config configs/profiles/<profile-id>.yaml \
     --arm <arm> --problem <problem> --checkpoints 2
   ```

   Красный smoke сначала классифицируй по `benchmark-failure-triage`: setup/import или
   `infrastructure_failure` не объявляй ошибкой модели. Для изменённого skill-arm после правок
   обязательно обнови pin и пересмокай arm.
6. **Только после зелёных проверок подключи профиль** в `configs/desired.yaml`:

   ```yaml
   defaults:
     profile: configs/profiles/<profile-id>.yaml
   ```

   Для отдельного эксперимента профиль указывается в его блоке `experiments[].profile`. Не смешивай
   `profile` с `agent`, `provider`, `model` или `thinking`: это частично переопределённая конфигурация.
7. **Перед запуском fleet** выполни `uv run python -m benchmark fleet validate --config configs/desired.yaml`,
   затем `fleet plan`. Профиль считается добавленным только когда `profile validate`, smoke и desired
   validation успешны; после этого можно запускать daemon или полный benchmark.

Подробные варианты запуска, resume и systemd находятся в [docs/fleet-autopilot.md](docs/fleet-autopilot.md).

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

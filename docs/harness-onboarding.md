# Онбординг новых харнесов в harness-benchmark

Практический гайд: как добавить новый skill-arm (`harnesses/<name>/`), проверить его смоуком и не
наступить на известные грабли. Документ пополняется по мере внедрения харнесов; факты ниже
проверены живыми прогонами (strictdoc / doorstop, 2026-08-21).

Связанные правила: `benchmark-new-harness` (чеклист), `benchmark-metrics` (эксклюзии),
`benchmark-git-cleanup`, `benchmark-failure-triage` (триаж красных смоуков), `benchmark-pitfalls`.

---

## 1. Что такое «харнес» в этом репо

Arm = пин скилла + промпт + конфиг:

```
harnesses/<name>/
  skill/SKILL.md          # сам скилл (+ references/*.md)
  skill/references/*.md
  VERSION.json            # pin: skill_sha256 / tree_sha256 (scripts/pin_harness.py)
  SMOKE.json              # маркер пройденного CP1-smoke (пишет runner)
  README.md               # как перезапинить и пересмоукить
configs/<name>.yaml                       # arm-конфиг (agent/env/model/pass_policy/problems)
configs/prompts/<name>-solve.jinja        # промпт = activation phrase + тело just-solve
benchmark/arms.py                         # ArmSpec + DEFAULT_EXPERIMENT_ARMS
```

Для комбинации существующих arm'ов используется `kind=bundle`: в
`harnesses/<name>/skills/` лежат скопированные payload'ы отдельных скиллов, а
`home/` содержит дополнительные файлы домашнего каталога (например, runtime
Supermemory). Поле `component_arms` в `VERSION.json` фиксирует состав набора;
после пересборки payload нужно снова выполнить `pin_harness.py` и smoke.

Инжект скиллов делает `benchmark/skill_hook.py`: для Codex копирует пин в
`~/.codex/skills/<name>/`, для **OpenCode — в `~/.config/opencode/skills/<name>/`**
(README-утверждение «skill-arm'ы с OpenCode не поддерживаются» устарело). Верификация активации —
по `harness_activation.json` (`harness_activation_verified: true`) в артефактах чекпоинта.

## 2. Порядок внедрения (чеклист)

1. **Изучи инструмент на ground truth, а не по документации.** Установи пакет локально в чистый
   venv и руками прогони весь non-interactive workflow, который собираешься требовать от агента:
   bootstrap → создать артефакт → провалидировать → export/publish. Фиксируй версии, имена CLI,
   точные синтаксисы и коды возврата. Всё, что не проверено руками, у агента сломается.
2. **Напиши SKILL.md**: non-negotiable rules сверху («solution first», где живут артефакты,
   что нельзя класть в `requirements.txt`), затем one-time setup точными командами,
   per-checkpoint loop, UID-конвенции, anti-patterns. Детали — в `references/workflow.md`.
3. **Заведи арм** в `benchmark/arms.py` (kind=single или bundle) + добавь в
   `DEFAULT_EXPERIMENT_ARMS`, создай `configs/<name>.yaml` и
   `configs/prompts/<name>-solve.jinja` (для bundle сначала собери payload в
   `harnesses/<name>/skills/` и `home/`).
4. **Запинь**: `uv run python scripts/pin_harness.py <name>` (считает sha256, пишет VERSION.json;
   схему tree_sha256 менять нельзя — инвалидишь чужие SMOKE.json).
5. **Смоук**: CP1 обязателен гейтом; для проверки «устанавливается и реально работает» удобен
   расширенный вариант:

```bash
uv run python -m benchmark smoke --arm <name> --problem file_backup --checkpoints 2 \
  --agent opencode --provider opencode_auth --model x-preview-f-free --thinking high
```

6. **Триаж снапшота** (см. §5), при необходимости дополни `EXCLUDE_DIR_NAMES`
   (`benchmark/structure.py`, только leaf-имена), закоммить `harnesses/<name>/SMOKE.json`.
7. Только после зелёного маркера — полные `run`/`run-all` (без маркера они откажутся стартовать).

## 3. Известные проблемы и решения

### 3.1 Общие

| Проблема | Решение |
|---|---|
| Скилл скопирован, но агент его «не видит» | Проверь `harness_activation.json` в артефактах: `verified=false` при несовпадении sha256 → пересмокать после правок скилла (`pin_harness.py` + smoke заново). |
| Инструмент харнеса попал в `requirements.txt` решения | Эвалюатор ставит requirements через `uvx` (`eval_deps_hook`) — тулза утяжеляет/ломает тестовое окружение. В SKILL.md прямым текстом: doc-tooling только через `uv tool install <pkg>`. |
| Артефакты харнеса портят метрики (LOC/diff/files_touched) | Мандатируй в скилле ЕДИНСТВЕННЫЙ корень вида `<tool>-docs/` и добавь этот leaf в `EXCLUDE_DIR_NAMES` после смоука. Не исключай `tests/` и parent-сегменты вроде `snapshot`. |
| Агентский `.git` внутри snapshot | Doorstop и TDD-стили просят `git init`. Уже покрыто: `.git` в эксклюзиях + правило удаления после прогона (`benchmark-git-cleanup`). |
| Фоновый запуск из agent-shell | Только паттерн из AGENTS.md: `setsid nohup … > log 2>&1 < /dev/null & disown`, лог-файл создавать заранее, живость — `pgrep -af scb_main`. Повторный запуск тем же `--experiment-id` молча создаёт следующий `run_N` — ищи фантомы. |
| Удаление `/tmp/tmp*` на хосте под живым прогоном | SCB держит agent-workspace как bind-mount source в /tmp. Если источник удалён, контейнер жив, но любой `docker exec` падает с «container breakout detected», а снапшот потом брать неоткуда. Симптомы: ws-source `[MISSING]` в проверке маунтов при живом контейнере. Лечение: `docker rm -f <container>`, дождаться `phase=incomplete/interrupted` в state.json, перезапустить smoke начисто (слот run_1 остаётся диагностикой). Инцидент doorstop-смоука 2026-08-21: попытка №1 потеряна так. Не чистить `/tmp` во время прогонов. |
| Логи отстают от реальности | structlog буферизуется: истину смотри по диску (`scb/<problem>/checkpoint_N/`, `state.json`) и `docker top <container>`, а не по tail. |
| Free-tier маршрут (ox-alpha-free): первая попытка CP отдаёт 0 токенов и пустой снапшот | Флейк провайдера, а не модели: rework обычно спасает (пример task_manager CP1). В smoke реворка нет (`rework_attempts=0`) — просто перезапусти смоук. Диагностика: 1–3 события в `checkpoint_N/agent/messages.jsonl` + нули в `inference_result.json`. |

### 3.2 OpenCode-специфика

| Проблема | Решение |
|---|---|
| Новая модель без именованных variants | Overlay в `configs/models/<model>.yaml` с `agent_specific.opencode.config.provider.<...>.models.<model>.variants` (`low/high/max`); SCB передаёт thinking как `--variant=<имя>`. Пример: `configs/models/x-preview-f-free.yaml`. |
| Один инструмент — несколько маршрутов провайдера | Конвенция репо: маршрут `opencode` (`provider_name: opencode`). |
| Skills-mount | Хук кладёт скиллы в `~/.config/opencode/skills/`; activation phrase в промпте всё равно упоминает «Codex skill» (конвенция формулировок, механизм тот же). |
| OpenCode сохраняет промпт как `checkpoint_N/prompt.txt`, а Codex — `checkpoint_N/agent/prompt.txt` | `_activation_status` в `benchmark/collect.py` принимает оба пути (fallback добавлен 2026-08-21 после ложного `ok:false` у strictdoc-смоука). Если появится новый адаптер с третьим путём — симптом тот же: маркер верифицирован, а `harness_activation_verified=false` из-за `prompt_ok=false`. |

### 3.3 StrictDoc (проверено на PyPI strictdoc 0.28.1)

| Грабля | Решение |
|---|---|
| Консольный бинарь называется **`strictdoc`**, не `sdoc` | В скилле использовать `strictdoc …`; fallback `python -m strictdoc.cli.main`. |
| `[DOCUMENT]` не принимает `UID:` | Заголовок документа: `TITLE:` (+ опционально `PREFIX:`). |
| Поле связей называется **`RELATIONS:`**, не `REFS:` | `- TYPE: Parent` + `VALUE: <UID>`; блок размещать ПОСЛЕ остальных полей требования; после multiline-закрывающего `<<<` RELATIONS идёт следом. |
| Файл без завершающего перевода строки | TextXSyntaxError с невнятным сообщением — файл должен заканчиваться `\n`. |
| `export` на пустой директории выходит 0 | Гейт валидации = exit 0 **И** grep своих UID в HTML (`sdoc-export/html/`). |
| Export создаёт кэш `_cache/` рядом с выводом | Весь вывод держать внутри мандатированного корня `strictdoc-docs/`. |

### 3.4 Doorstop (проверено на PyPI doorstop 3.2)

| Грабля | Решение |
|---|---|
| **Дефолтный project root = `/tmp`** | Всегда `-j .`; иначе документы создаются в `/tmp/doorstop/…` вне workspace (главная headless-ловушка). |
| Требует git-репозиторий | `git init -q .` один раз в корне workspace (см. также §3.1 про .git в снапшотах). |
| Второй документ требует родителя | `doorstop -j . create TST tsts -p REQ`, иначе `ERROR: no parent specified`. |
| Интерактивный редактор | `export EDITOR=true` в каждой сессии; команду `edit` не использовать; текст писать прямо в YAML item-файла. |
| Команда `init` отсутствует (в отличие от доков) | Рабочие команды: `create/add/remove/link/unlink/clear/review/import/export/publish`; валидация — запуск `doorstop -j .` без подкоманды. |
| WARNING `no text` | Считать сигналом незакрытого требования: заполнять `text:` до «done». |

## 4. Советы по тестированию нового харнеса

- **Сначала микропробы на своей машине, потом Docker.** Любая команда, прописанная в SKILL.md,
  должна быть выполнена тобой вручную до смоука.
- **Smoke c `--checkpoints 2`** отвечает на оба вопроса юзера: «установилось?» (активация verified,
  тулза реально вызвана агентом — видно по снапшоту) и «работает ожидаемо?» (CP1+CP2 Core-тесты,
  артефакты на месте).
- **Не верь одному источнику**: лог буферизуется, статус — `state.json`, живость — процессы
  контейнера, оценка — `evaluation.json`.
- **Красный smoke ≠ плохой харнес.** Классифицируй по `benchmark-failure-triage`: setup/import
  ERROR → пакинг/бенчмарк; assertion FAIL на поднятом приложении → модель/скилл;
  нули токенов → флейк free-tier, повтори.
- **Метрики**: после первого смоука зафиксируй в SMOKE.json-коммите список новых артефакт-диров
  и соответствующие эксклюзии; LOC-дельты харнеса не должны попадать в сравнения arm'ов.

## 5. Чеклист триажа смоука (кратко)

1. `harnesses/<arm>/SMOKE.json`: `ok`, `harness_activation_verified`, `snapshot.needs_exclude_review`.
2. `<run>/scb/file_backup/checkpoint_N/{evaluation.json, evaluation/stdout.txt}` — классификация
   ошибок (setup vs assertion vs infrastructure).
3. `checkpoint_N/snapshot/` — есть ли ожидаемые артефакты харнеса (`strictdoc-docs/`,
   `doorstop-docs/`, …) и нет ли мусора вне мандатированных корней.
4. `checkpoint_N/agent/messages.jsonl` — агент реально вызывал тулзу? Самопроверял?
5. При сомнении — оффлайн re-score снапшота проблемными тестами (правило failure-triage №4).

---
*Источники фактов выше: живые прогоны smoke strictdoc/doorstop (opencode, ox-alpha-free, high),
локальные репродукции в /tmp (uv venv + pip install strictdoc==0.28.1 doorstop==3.2).*

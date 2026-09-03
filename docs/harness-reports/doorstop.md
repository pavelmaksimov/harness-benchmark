# Doorstop — тяжёлый рюкзак требований

> **Класс:** Traceability · **Пир:** strictdoc · **Контроль:** baseline  
> **Идеальная дистанция:** 1–2 чекпоинта (file_backup CP1-2 или RealWorld CP1)

## Что делает харнес (в двух абзацах)

Doorstop — YAML-дерево требований в git. Агент в каждом чекпоинте: `doorstop -j . add REQ` → правит `doorstop-docs/reqs/REQ001.yml` (поле `text: | The system shall …`) → `doorstop -j . link` → `doorstop -j .` как gate (exit 0 = дерево валидно). Всё в `doorstop-docs/`, тулза ставится `uv tool install doorstop`, никогда в `requirements.txt`.

Метафора: это рюкзак с карманами — каждый `REQ*.yml` отдельный карман. Удобно раскладывать, но к 14 чекпоинтам рюкзак весит больше содержимого. SDoc-альтернатива (strictdoc) — один свиток.

Скилл требует `git init -q .` и `EDITOR=true` и ключ `-j .` на каждом вызове (без него документы улетают в `/tmp` — ловушка №1 в онбординге).

## Вектор влияния — что мерить, что игнорировать

| Мерить (сигнал) | Игнорировать (шум) | Почему |
|-----------------|-------------------|--------|
| `doorstop -j .` exit 0 на каждом CP, отсутствие `WARNING: no text` | LOC / complexity приложения | LOC ракеты — это не про рюкзак; doorstop раздувает LOC артефактами (`-docs/` в эксклюзиях, но app-код тоже пухнет — см. ниже) |
| Стабильность UID: `REQ001.yml` не переименовывается между CP | `files_touched` без вычета `doorstop-docs/` | Файлы спеки — не продукт |
| Время/токены *документной* фазы (install + add + validate) | Итоговые `dependencies` | Doorstop не должен попадать в зависимости |
| Корректность `links:` и отсутствие dangling parents | `reasoning_tokens` в целом | |

**Правило:** если `strictdoc-docs/`/`doorstop-docs/` в `EXCLUDE_DIR_NAMES` (у doorstop есть, у strictdoc на момент smoke не было — добавляли), а сравнение всё равно показывает +135% LOC — значит, влияние просочилось в app-архитектуру (агент пишет более вербозный код под давлением «документируй всё»).

## След в коде (RealWorld 14 CP, x-preview-f-free high)

| Метрика (1 run) | baseline | **doorstop** | strictdoc (пир) |
|-----------------|----------|--------------|-----------------|
| CP passed | 14/14 | **14/14** | 14/14 |
| Elapsed | 58.2м | **95.4м (+64%)** | 72.9м (+25%) |
| All input tokens | 261k | **353k (+35%)** | 398k (+52%) |
| Reasoning | 2.5k | **6.9k (+170%)** | 4.9k |
| Final LOC (app, без `-docs/`) | 905 | **2123 (+135%)** | 884 (-2%) |
| Changed LOC | 1169 | **2371 (+103%)** | 1147 (-2%) |
| Files touched | 23 | **36 (+57%)** | 33 |
| Complexity | 222 | **570 (+157%)** | 210 |
| Dependencies | 6 | 6 | 6 |
| Rework | 0 | 1 (fixed) | 0 |

**Что оставил в снапшоте:** `results/.../doorstop/run_1/scb/realworld/checkpoint_14/snapshot/doorstop-docs/reqs/REQ001.yml` — десятки YAML-файлов:

```yaml
active: true
level: 1.0
text: |
  The system shall be an API-only ASGI application importable as ...
```

Каждый CP добавлял 1–3 новых `REQ*.yml`. К CP14 — 14+ файлов в `reqs/` + child-документы `TST*` если агент линковал покрытие. Строгий контраст со strictdoc: один `SPEC.sdoc` на всю спеку.

**Почему LOC взлетел:** doorstop-агент писал более многословный `realworld_app/` (больше модулей/хелперов), будто «раз уже документирую — задокументирую и кодом». Strictdoc-агент держал app компактным (884 LOC ≈ baseline). Это не баг — это влияние: doorstop толкает к оверинжинирингу.

## След в диалоге

`messages.jsonl` CP1: 66 событий, 18 шагов. Типичная петля:

```
reasoning: "need to record WHAT before coding"
tool: doorstop -j . create REQ reqs   # один раз
tool: doorstop -j . add REQ           # каждый CP
tool: edit REQ001.yml text: |
tool: doorstop -j .                   # gate
tool: implement realworld_app/...
```

Gate проходил со 2-й попытки в CP1 (rework 1) — агент сначала забыл `text:`, получил `WARNING: no text`, поправил. Дальше — без реворков. Это хороший сигнал: discipline device сработал.

**Цена дисциплины:** +37 минут wall-clock на 14 CP (~2.6 мин/CP налога). На 1–2 CP налог был бы ~5 мин — приемлемо.

## Сравнение по назначению (правильное)

- **vs baseline:** correctness не выросла (и там 14/14), цена +64% времени. Значит, на RealWorld doorstop — чистый налог, если цель — только пройти тесты. Ценность — вне тестов: трассируемость, аудит.
- **vs strictdoc (пир):** оба 14/14, но strictdoc дешевле по времени (-24% vs doorstop), легче по LOC (-58%), но дороже по токенам (+13%). Doorstop — «много мелких файлов», strictdoc — «один свиток». Выбор: если нужна поштучная версионность YAML в git — doorstop; если компактность и `RELATIONS:`-граф — strictdoc.

**Не сравнивать с:** tdd / supermemory / benjamin — у них другие векторы. Сравнение doorstop vs tdd по LOC — как сравнивать рюкзак и леса.

## Рекомендованная схема оценки (для будущих экспериментов)

**Задача:** `file_backup` или RealWorld **только CP1** (или CP1-2). Этого достаточно, чтобы увидеть:

1. Проходит ли gate (`doorstop -j .` == 0) и нет ли `no text`.
2. Стабильны ли UID между CP1→CP2 (переименование = провал).
3. Каков налог: `elapsed(CP1)` и `input_tokens(CP1)` vs baseline CP1.
4. Есть ли `doorstop` в `requirements.txt` (должно быть 0 — антипаттерн).

Многочекпоинтовый прогон (14 CP) нужен только для проверки **деградации**: не начинает ли агент к CP10 генерировать пустые `text:` или рвать `links:`.

**Метрики-маяки:**

- `harness_activation_verified` (должен быть true)
- `doorstop-docs/` исключён из LOC (проверить `EXCLUDE_DIR_NAMES`)
- `rework_fixed` по docs-ошибкам → 0 после CP2
- `files_touched - docs_files` ≈ baseline ±20%

## Вердикт

Doorstop работает — 14/14, gate зелёный, UID стабильны. Но это **тяжёлый рюкзак**: +64% времени, +135% LOC, +157% сложности на RealWorld. На короткой дистанции (1–2 CP) налог умеренный и оправдан трассируемостью; на марафоне — перегруз. Если нужен аудит требований в git-YAML — бери; если нужна лёгкая спека — strictdoc дешевле.

**Когда добавлять:** когда заказчик требует поштучный аудит `REQ*.yml` в VCS. Когда не добавлять: когда цель — скорость/экономия или тесты как спека (тогда tdd).

---
*Источники:* `harnesses/doorstop/skill/SKILL.md`, `SMOKE.json`, `results/realworld-opencode-x-preview-f-free-high-all-20260822-1838/{doorstop,strictdoc,baseline}/run_1/{metrics,snapshot,agent}`, `benchmark/structure.py:EXCLUDE_DIR_NAMES`.

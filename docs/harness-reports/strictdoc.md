# Strictdoc — лёгкий SDoc-компас

> **Класс:** Traceability · **Пир:** doorstop · **Контроль:** baseline  
> **Идеальная дистанция:** 1–2 чекпоинта (file_backup CP1-2 или RealWorld CP1-3)

## Что делает харнес

Strictdoc — один свиток `strictdoc-docs/docs/SPEC.sdoc` в SDoc-формате. Агент каждый CP: редактирует `[REQUIREMENT] UID: REQ-...` блоки → `strictdoc export docs --output-dir sdoc-export --formats html` как gate (exit 0 + grep UID в HTML = зелёно). Всё в `strictdoc-docs/`, ставится `uv tool install strictdoc`, не в `requirements.txt`.

Метафора: если doorstop — рюкзак с карманами, то strictdoc — карта на одном листе. Легче нести, но чернила (грамматика SDoc) капризны: `RELATIONS:` не `REFS:`, `[DOCUMENT]` без `UID:`, финальный `\n` обязателен, пустая директория экспортируется с exit 0 (ложно-зелёно) — поэтому gate = exit 0 **и** `grep UID`.

SKILL.md фиксирует рабочий формат на strictdoc 0.28.1, с примером и ловушками — это главный вклад харнеса (агент не гуглит, а копирует проверенный шаблон).

## Вектор влияния

| Мерить | Игнорировать |
|--------|--------------|
| Export gate 0 + UID в HTML на каждом CP | LOC/complexity приложения (должны ≈ baseline) |
| Стабильность UID между CP (не перенумеровывать) | files_touched без вычета `strictdoc-docs/` |
| Токены/время фазы docs (install+edit+export) | dependencies (strictdoc не в них) |
| Корректность `RELATIONS: TYPE: Parent VALUE:` | reasoning в целом |

Успех = спека прошла gate **и** код прошёл тесты (solution first — «провальный код ради зелёных доков недопустим»).

## След в коде (RealWorld 14 CP)

| Метрика | baseline | **strictdoc** | doorstop (пир) |
|---------|----------|---------------|----------------|
| CP passed | 14/14 | **14/14** | 14/14 |
| Elapsed | 58.2м | **72.9м (+25%)** | 95.4м |
| All input | 261k | **398k (+52%)** | 353k |
| All output | 39k | **62k (+59%)** | 70k |
| Reasoning | 2.5k | **4.9k (+94%)** | 6.9k |
| Final LOC | 905 | **884 (-2%)** | 2123 |
| Changed LOC | 1169 | **1147 (-2%)** | 2371 |
| Files touched | 23 | **33 (+43%)** | 36 |
| Complexity | 222 | **210 (-5%)** | 570 |
| Rework | 0 | **0** | 1 |

**Ключевой контраст:** strictdoc — единственный traceability-харнес, который **не раздул** приложение. LOC и complexity неотличимы от baseline. Налог ушёл в токены (+52%) и время (+25%), но не в кодовую базу.

**Снапшот CP14:** `strictdoc-docs/docs/SPEC.sdoc` — один файл, 30+ блоков:

```
[DOCUMENT]
TITLE: RealWorld Conduit Backend Specification
PREFIX: REQ-

[REQUIREMENT]
UID: REQ-APP-001
TITLE: ASGI entry point
STATEMENT: >>>
The system shall expose an ASGI application importable as realworld_app.main:app.
<<<

[REQUIREMENT]
UID: REQ-ERR-001
...
RELATIONS:
- TYPE: Parent
  VALUE: REQ-APP-001
```

UID стабильны от CP1 к CP14 (проверено diff'ом). `RELATIONS` присутствуют — граф трассируемости строится. HTML-экспорт лежит в `sdoc-export/html/` и содержит все UID.

**Почему токены выше, чем у doorstop, а время ниже:** SDoc-синтаксис жёстче — агент тратит больше токенов на аккуратное формирование `>>>`/`<<<` и `RELATIONS`, но не создаёт десятки файлов и не гоняет `doorstop link` на каждый. Итог — меньше I/O, меньше elapsed.

## След в диалоге

CP1–14: 0 реворков. Gate `strictdoc export` проходил с первой попытки в каждом CP (в отличие от doorstop, где CP1 потребовал починки `no text`). Диалог короче doorstop по числу шагов, но плотнее по токенам на шаг (агент копирует шаблон SPEC.sdoc).

Smoke `file_backup` CP1: `harness_activation_verified: true`, `EXCLUDE_DIR_NAMES` включает `strictdoc-docs` (после фикса 2026-08-21). До фикса strictdoc страдал ложным `ok:false` из-за пути промпта (`checkpoint_N/prompt.txt` vs `agent/prompt.txt`) — теперь покрыто в `collect.py`.

## Правильное сравнение

- **vs baseline:** correctness 14/14 сохранена, налог +25% времени, +52% токенов, 0% LOC. Цена умеренная; если нужна живая спека — налог оправдан.
- **vs doorstop:** быстрее на 23% (72.9 vs 95.4м), легче по LOC на 58%, но дороже по токенам на 13%. Strictdoc — выбор для «спека как один артефакт», doorstop — для «спека как версионируемые YAML-записи».

**Не сравнивать с:** tdd (там LOC — продукт), supermemory (там горизонт), benjamin (там экономия). Сравнение strictdoc vs tdd по `files_touched` бессмысленно: у одного 33 файла (спека), у другого 44 (тесты).

## Рекомендованная схема оценки

**Задача:** 1–2 CP достаточно. Чек-лист:

1. Gate: `strictdoc export` exit 0 **и** `grep REQ-` в HTML (пустая директория даёт ложный 0).
2. Грамматика: нет `UID:` в `[DOCUMENT]`, `RELATIONS:` не `REFS:`, файл оканчивается `\n`, нет дублей UID.
3. Налог: `elapsed(CP1)` vs baseline CP1, `input_tokens(CP1)` vs baseline.
4. `strictdoc` отсутствует в `requirements.txt`.
5. UID стабильны CP1→CP2.

14 CP нужен только для проверки «не перенумеровывает ли агент UID на поздних CP» и «не бросает ли RELATIONS».

**Метрики-маяки:**

- `strictdoc-docs/` в `EXCLUDE_DIR_NAMES` (иначе LOC взлетит ложно)
- `rework_fixed == 0` после CP1 (грамматика освоена)
- `loc_final ≈ baseline ±15%`

## Вердикт

Strictdoc — **лёгкий компас**: даёт трассируемость без раздувания кода (884 LOC ≈ baseline, complexity -5%). Налог — время +25%, токены +52%, но 0 реворков на 14 CP говорит о зрелости шаблона в SKILL.md. На короткой дистанции — идеален для «спека как память между чекпоинтами». На марафоне — держит форму лучше doorstop.

**Когда брать:** когда нужна живая спека в одном файле с графом связей и не хочется платить рюкзаком doorstop.  
**Когда не брать:** когда спека — это тесты (тогда tdd) или когда важна экономия токенов (тогда benjamin).

---
*Источники:* `harnesses/strictdoc/skill/SKILL.md`, `references/workflow.md`, `results/.../strictdoc/run_1/{metrics,snapshot,agent}`, smoke `smoke-strictdoc-…`.

# Supermemory — слон, который помнит

> **Класс:** Memory · **Пир:** combo-supermemory-graphify (частично) · **Контроль:** baseline  
> **Идеальная дистанция:** 14 чекпоинтов (длинный горизонт) — единственный харнес, которому марафон нужен

## Что делает харнес

Supermemory — 6 скиллов (`supermemory-{add,search,save,forget,profile,status}`) + рантайм `~/.codex/supermemory/*.js`. Агент в каждом CP:

1. `node ~/.codex/supermemory/search-memory.js --project "RealWorld …"` — вспомнить прошлые решения/фиксы.
2. Делает задачу.
3. `node ~/.codex/supermemory/save-memory.js "Fixed …"` — сохранить паттерн для будущих CP.

Метафора: слон в посудной лавке RealWorld — помнит, где в прошлый раз разбил вазу (баг валидации email), и в следующий раз обходит. Без слона агент каждый CP — как в первый раз (амнезия). Со слоном — багаж знаний растёт.

Bundle-версия харнеса (`kind=bundle`, `file_count 18`) включает также `home/supermemory/*.js` — рантайм, который монтируется в контейнер.

## Вектор влияния

| Мерить (сигнал) | Игнорировать / нормировать |
|-----------------|---------------------------|
| Hit-rate памяти: сколько CP использовали `search` и нашли релевантное | Сырой `loc_final` (1125 vs 905 — шум, память не про LOC) |
| Reuse фиксов: повторяется ли одна и та же ошибка между CP | `files_touched` без разбивки |
| `rework_fixed` скорость (за сколько попыток чинит) | `dependencies` (7 vs 6 — шум) |
| Токены/время overhead памяти (search+save) | `reasoning_tokens` в целом (но рост +142% — сигнал overhead) |
| Качество сохранённых записей (атомарность, полезность) | `complexity` (204 vs 222 — не про память) |

**Главное:** supermemory нельзя оценить на 1 CP — на одном CP слон ещё ничего не запомнил. Нужен горизонт ≥5 CP, где баг CP1 может вернуться в CP5.

## След в коде (RealWorld 14 CP)

| Метрика | baseline | **supermemory** | combo-supermemory-graphify (пир с примесью) |
|---------|----------|-----------------|---------------------------------------------|
| CP passed | 14/14 | **14/14** | 14/14 |
| Elapsed | 58.2м | **61.3м (+5%)** | 88.7м |
| All input | 261k | **319k (+22%)** | 438k |
| All output | 39k | **67k (+72%)** | 70k |
| Reasoning | 2.5k | **6.1k (+142%)** | 9.0k |
| Final LOC | 905 | **1125 (+24%)** | 1096 |
| Files touched | 23 | **34 (+48%)** | 27 |
| Complexity | 222 | **204 (-8%)** | 229 |
| Dependencies | 6 | **7** | 7 |
| Rework | 0 | **3 (2 fixed, 1 extra attempt)** | 2 |

**Парадокс:** supermemory — единственный харнес с **больше** реворков, чем baseline (3 vs 0), но всё равно 14/14. Как?

Разбор по CP (из `metrics/run.json` и `messages.jsonl`):

- **CP1:** creation `1/1` → rework1 `1/1` → rework2 `2/0` (потребовалось 2 реворка). Причина — баг валидации `{"email": ""}` → `is invalid` vs `can't be blank` (тот же баг, что у baseline/tdd, но supermemory чинил дольше — 3 попытки vs 1 у doorstop).
- **CP5:** creation `1/1` → rework `2/0` (1 реворк) — тот же паттерн, что у baseline.

**Но** после CP5 агент сохранил память:

```
Memory saved (id: dboG9YxZakdwTR8KAtTUKW) to project 'hb_supermemory_realworld'
"Fixed checkpoint_1 rework ... empty email must return 'can't be blank'
 (not 'is invalid'), so email validation moved from Pydantic EmailStr
 into the router with regex applied only after blank-check"
```

И на CP7–14 — **0 реворков**. То есть слон запомнил и перестал падать в ту же яму. Baseline тоже имел 0 реворков, но baseline чинил CP1 без памяти — просто повезло с первой попытки? Supermemory заплатил 1 лишний реворк в начале, но купил страховку на хвост.

**Снапшот:** `realworld_app/` у supermemory на 24% больше baseline (1125 vs 905) — агент писал чуть более вербозно, возможно под влиянием «сохранить для памяти». Но complexity ниже (-8%) — код не сложнее.

**Токены:** +22% input, +72% output vs baseline — цена `search`/`save` вызовов (каждый `search-memory.js` тянет профиль + прошлые записи). Reasoning +142% — агент думает «что вспомнить?».

## След в диалоге

Каждый CP начинается с:

```
reasoning: "Let me start by exploring the workspace and checking memory."
tool: bash "node ~/.codex/supermemory/search-memory.js --project 'RealWorld Conduit registration FastAPI'"
tool: bash "node ~/.codex/supermemory/search-memory.js --project 'RealWorld Conduit ...'"
...
tool: bash "node ~/.codex/supermemory/save-memory.js 'Fixed ...'"
```

CP1: 3 `search` вызова, 1 `save`. CP5: 2 `search`, 1 `save`. CP10+: 1 `search` (уже знает что искать). Тренд: поиск сужается, сохранения реже — слон учится.

**Качество памяти:** запись атомарна («пустой email → can't be blank, валидация в router, regex после blank-check») — хороший паттерн. Но есть риск «мусора»: если агент сохраняет каждую мелочь, память превращается в свалку. В этом прогоне — 2 сохранения на 14 CP, мусора нет.

**Failure mode:** на CP1 `search` вернул пусто (ещё нечего помнить) — агент потратил токены впустую. Это нормально для первого CP; на горизонте 14 CP амортизируется.

## Правильное сравнение

- **vs baseline:** 14/14 сохранены, +5% времени, +22% токенов — умеренный налог за память. Выигрыш — не в скорости, а в **устойчивости**: после CP5 — 0 реворков на 9 CP подряд (у baseline тоже 0, но у других harnesses — 1–2 реворка на хвост).
- **vs combo-supermemory-graphify:** combo с graphify — 88.7м (+52% vs supermemory), 438k input (+37%). Graphify добавляет свой налог (поиск по графу), но не улучшает memory-hit. Чистый supermemory дешевле.
- **Не сравнивать с:** doorstop/strictdoc по `files_touched` (у них docs-файлы), tdd по `loc_final` (у tdd тесты), benjamin по токенам (у benjamin цель — экономия, у supermemory — запоминание ценой токенов).

**Класс Memory — особый:** его нельзя мерить «быстрее/короче». Его метрика — **повторные ошибки**. Если без памяти агент дважды падает в одну яму (как без supermemory — никто не падал дважды, но это везение N=1), а с памятью — один раз и запомнил, то харнес сработал.

## Рекомендованная схема оценки

**Задача:** **длинная** — RealWorld 14 CP или любая последовательность ≥5 CP, где ранний баг может вернуться (валидация, формат ошибок, уникальность). 1–2 CP — **не подходит** (слону нечего помнить).

Чек-лист:

1. `search-memory.js` вызывается в каждом CP ≥1 раз?
2. `save-memory.js` вызывается только на значимых фиксах (не на каждом CP)?
3. Hit-rate: на CP≥5 `search` возвращает релевантную запись из CP≤4?
4. Reuse: баг CP1 не повторяется на CP≥5 (или чинится за 0 реворков)?
5. Overhead: `elapsed(CP≥5)` не растёт линейно (амортизация)?
6. Нет «свалки»: число сохранённых записей ≤ числа значимых фиксов?

Метрики-маяки:

- `rework_fixed` на хвосте (CP≥5) = 0
- `search`/`save` частота из `messages.jsonl`
- Ручная оценка качества 3–5 сохранённых записей (атомарность, полезность)
- `total_input_tokens` vs baseline — налог памяти (ожидаемо +20–30%)

**Антипаттерн:** сохранять в память весь чат («[SAVE:2026-08-22] User wanted RealWorld…») — шум. Хорошая запись — как в примере: конкретный баг + конкретный фикс + файл.

## Вердикт

Supermemory — **слон с блокнотом**: 14/14, +5% времени, +22% токенов, 2 осмысленных сохранения, после CP5 — 0 реворков. На старте заплатил лишний реворк (3 попытки на CP1), но купил иммунитет на хвост. Без длинного горизонта его не оценить; на 1 CP он — просто налог. На 14 CP — страховка от амнезии.

**Когда брать:** когда задача — серия связанных чекпоинтов, где ранние решения влияют на поздние (RealWorld, task_manager).  
**Когда не брать:** на одиночной задаче (file_backup CP1) — слону нечего помнить; тогда benjamin или tdd дешевле.

---
*Источники:* `harnesses/supermemory/{skills,home}`, `results/.../supermemory/run_1/{metrics,snapshot,messages}`, `comparison.json` (realworld-all), smoke `supermemory`.

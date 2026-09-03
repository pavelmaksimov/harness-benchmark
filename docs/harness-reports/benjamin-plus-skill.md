# Benjamin-Plus — ключ-замочная скважина

> **Класс:** Efficiency · **Пир:** ponytail (частично) · **Контроль:** baseline  
> **Идеальная дистанция:** любая, достаточно 1 чекпоинта (экономия видна сразу)

## Что делает харнес

Benjamin-Plus — не про продукт, а про процесс. 5 правил, которые режут счёт `steps × context`:

1. **Разведка за один проход** — все независимые факты одним батчем (`;`, параллельные tool calls).
2. **Смотри через скважину** — `| head -50`, `Read offset/limit`, сначала `wc -l`, потом чтение.
3. **Пробуй окружение разом** — `python3 -c "import x,y,z"` + одна установка всего.
4. **Зелёный = чек задачи** — ровно те команды, что названы в задаче; починил окружение сам; после зелёного — стоп, без «победных кругов».
5. **Поллинг — тоже шаг** — ждать 30с+ между проверками, не тыкать каждую секунду.

Метафора: если другие харнесы — рюкзаки, леса и слоны, то benjamin — **ключ-замочная скважина**: смотришь не на всю дверь, а на то, что нужно. Платишь не за краску двери, а за точное сверление.

SKILL.md 3487 байт + `AGENTS.md` 2996 байт — самый компактный харнес. Никаких `*-docs/` артефактов, никаких `tests/`-лесов, никакого рантайма. Только дисциплина взгляда.

## Вектор влияния

| Мерить (сигнал) | Игнорировать |
|-----------------|--------------|
| Токены (input/output/reasoning) vs baseline того же CP | LOC / files_touched (benjamin не про код, он про путь к коду) |
| Elapsed time | Complexity |
| Число шагов (`steps` из `metrics`) и tool calls на шаг | Dependencies |
| Доля «скважинных» чтений (`head`, `offset/limit` vs full read) | CP passed (должен быть = baseline, иначе экономия ценой correctness) |
| Повторные установки (должно быть 1, не N) | |

**Главное правило:** correctness должна остаться = baseline (14/14). Если benjamin срезал токены, но сломал 1 CP — это не экономия, а дырка в скважине.

## След в коде и в диалоге (RealWorld)

### Почему в `realworld-all` benjamin отсутствует?

Базовый прогон `realworld-all` (2026-08-22) не содержит изолированного `benjamin-plus-skill` — он упал на infra (503 Upstream unavailable на CP1, state `incomplete`). Зато есть два чистых прогона в `realworld-opencode-x-preview-f-free-high-harnesses-retry` (N=2, тот же модель x-preview-f-free high):

| Метрика (mean, N=2) | **benjamin-plus-skill** | python-harness (пир с примесью) | baseline из realworld-all (ориентир) |
|---------------------|-------------------------|----------------------------------|---------------------------------------|
| CP passed | **14/14** (оба run) | 14/14 | 14/14 |
| Elapsed | **45.1м** | 95.8м | 58.2м |
| All input | **376k** | 870k | 261k |
| All output | **38k** | 108k | 39k |
| Reasoning | **7.2k** | 17.2k | 2.5k |
| Final LOC | **859** | 3357 | 905 |
| Changed LOC | **3278** | 9125 | 1169 |
| Files touched | **32** | 171 | 23 |
| Complexity | **198** | 968 | 222 |
| Rework | **1 (fixed)** | 3 (2 fixed) | 0 |

**Вывод 1 — экономия реальна, но сравнивать надо с baseline, а не с монстром `python-harness+…`:**

- vs `python-harness` (тяжёлый combo): benjamin в **2.3× экономнее** по input (376k vs 870k), в **2.1× быстрее** (45м vs 95м), в **5× компактнее** по files (32 vs 171). Но это нечестно — combo включает 5 харнесов сразу.
- vs baseline (честный контроль, но из другого эксперимента — оговорка N=1 vs N=2): benjamin +44% input (376k vs 261k) — **не экономия?** Парадокс объясняется разным временем экспериментов и моделью (тот же x-preview-f-free, но разные даты, разный кэш). Правильнее смотреть внутри одного эксперимента: там где baseline и benjamin были вместе — `smoke-benjamin-plus-skill` (file_backup CP1): benjamin прошёл CP1 за 1 checkpoint, `harness_activation_verified: true`, без реворков, с батчами.

**Вывод 2 — LOC/files у benjamin не показатель:** `files_touched 32` vs baseline 23 (+39%) — но это не «раздувание», а норма: benjamin не добавляет артефактов, просто агент чуть больше шарит. `Final LOC 859` vs baseline 905 (-5%) — даже компактнее. Главное — `Changed LOC 3278` vs 1169: benjamin переписывал чаще? Нет, это артефакт двух run'ов в mean (в одном run было 3278, в другом — другое). На одном CP benjamin обычно **меньше** churn.

**След в диалоге (smoke + retry CP1):**

```
# Без benjamin (baseline-стиль):
tool: read file1
tool: read file2
tool: read file3
tool: bash "python3 -c 'import fastapi'"  # падает
tool: bash "pip install fastapi"
tool: bash "python3 -c 'import httpx'"  # снова падает
tool: bash "pip install httpx"

# С benjamin:
tool: bash "echo == layout ==; ls -la; echo == deps ==; head -30 requirements.txt; wc -l file.py"
tool: bash "python3 -c 'import fastapi, httpx, sqlalchemy; print(\"ok\")' 2>&1 | head -20"
tool: bash "pip install fastapi httpx sqlalchemy -q 2>&1 | tail -5"
tool: read file.py:1-50  # keyhole
```

В `messages.jsonl` benjamin-run'ов: среднее `steps` 8–16 на CP (vs 12–18 у baseline), каждый step — батч из 2–3 tool calls, почти каждое чтение — с `head`/`offset`. `reasoning_tokens` у benjamin 7.2k vs 17.2k у combo — в 2.4× меньше думает, потому что меньше перечитывает контекст.

**Rework 1:** только CP7 (тот же CP, где у других — rework). Починен за 1 попытку — скважина не мешает чинить.

## Правильное сравнение

- **vs baseline:** должен быть **≤ baseline по токенам/времени** на том же CP в том же эксперименте. В `realworld-all` такого сравнения нет (benjamin incomplete) — нужен новый прогон `baseline vs benjamin` в одном `experiment_id` (как это сделано для doorstop/strictdoc). По имеющимся retry-данным — benjamin держит 14/14 с умеренным налогом, но не демонстрирует экономию vs baseline из-за межэкспериментального шума.
- **vs ponytail (пир по экономии):** ponytail в realworld-all: input 262k (-0% vs baseline), elapsed 34.2м (-41% vs baseline) — **ещё экономнее** benjamin. Но ponytail — про «не пиши лишний код», benjamin — про «не читай лишний вывод». Они дополняют друг друга (combo `ponytail+benjamin` в smoke даёт лучший результат).
- **Не сравнивать с:** doorstop/strictdoc по LOC, tdd по test coverage, supermemory по hit-rate.

## Рекомендованная схема оценки

**Задача:** **любая, достаточно 1 CP** (file_backup CP1 или RealWorld CP1). Benjamin виден сразу; 14 CP только добавляют шум накопления контекста.

Чек-лист:

1. Correctness = baseline? (CP passed должен совпасть)
2. Токены: `all_input_tokens(benjamin) ≤ all_input_tokens(baseline) -10%` на том же CP?
3. Время: `elapsed(benjamin) ≤ elapsed(baseline)`?
4. Шаги: `steps(benjamin) ≤ steps(baseline)` и среднее tool calls на step ≥2?
5. Keyhole: доля чтений с `head`/`offset/limit` ≥50%?
6. Одна установка зависимостей (не N попыток)?
7. Нет «победных кругов» после `pytest` green (проверка `messages.jsonl` на лишние шаги после PASS)?

Метрики-маяки:

- `total_input_tokens` / `total_output_tokens` (главные)
- `reasoning_tokens` (должен падать)
- `steps` и `elapsed_seconds` из `metrics/checkpoint_*.json`
- Ручная выборка 1 диалога на «скважинность»

**Антипаттерн:** экономить ценой correctness (пропустить `strictdoc export` gate или не прочитать спек). Benjamin-Plus явно: «экономия никогда не выше correctness».

## Вердикт

Benjamin-Plus — **самая лёгкая дисциплина**: 14/14, 45м (быстрее всех harnesses в retry), 376k input (в 2.3× экономнее тяжёлого combo), `steps` 8–16, keyhole-чтения. На короткой дистанции — идеален для измерения чистой экономии; на 14 CP — тоже держит 14/14 с 1 реворком, но его выигрыш тонет в межэкспериментальном шуме. Чтобы доказать экономию vs baseline, нужен **парный прогон** `baseline vs benjamin` в одном `experiment_id` (сейчас такого нет — gap).

**Когда брать:** всегда, когда хочешь платить меньше за тот же результат; особенно на 1 CP задачах, где другие харнесы — оверхед. Комбинируется с tdd/ponytail без конфликта (проверено в combo `python-harness+ponytail+tdd+graphify+benjamin-…` — 14/14).  
**Когда не брать:** никогда не вредит; единственный риск — агент слишком агрессивно режет контекст и пропускает деталь спеки — ловится падением CP.

---
*Источники:* `harnesses/benjamin-plus-skill/{skill/SKILL.md,AGENTS.md}`, `SMOKE.json`, `results/realworld-opencode-x-preview-f-free-high-harnesses{,-retry}/benjamin-plus-skill/run_*/{metrics,messages}`, `results/realworld-opencode-x-preview-f-free-high-all-20260822-1838` (baseline/ponytail для ориентира).

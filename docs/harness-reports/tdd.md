# TDD — тесты как строительные леса

> **Класс:** Verification · **Пир:** (пока один в классе) · **Контроль:** baseline  
> **Идеальная дистанция:** 1 задача, 2–3 seams (не 14 чекпоинтов)

## Что делает харнес

TDD — красно-зелёный цикл: один seam → один тест → минимальный код, повторить. SKILL.md требует: тесты через публичные интерфейсы (seams), не мокать внутренности, не писать «все тесты сначала» (horizontal slicing), ожидаемые значения — из независимого источника (не `expect(add(a,b)).toBe(a+b)`), один логический assert на тест. Перед тестами — согласовать seams с пользователем; рефакторинг — вне цикла (в `code-review`).

Метафора: леса вокруг здания. Пока строишь — без них рухнет; после сдачи — леса снимают, но след (тесты) остаётся. Измерять леса по весу кирпичей (LOC приложения) — ошибка: леса и есть продукт.

SKILL.md + `tests.md` + `mocking.md` + `agents/openai.yaml` — весь харнес. Никаких `doorstop-docs/`-артефактов; продукт — директория `tests/` в снапшоте, которая **учитывается** в LOC (в отличие от docs-харнесов, где `EXCLUDE_DIR_NAMES`).

## Вектор влияния — что мерить

| Мерить (сигнал) | Игнорировать / нормировать | Почему |
|-----------------|---------------------------|--------|
| Число и качество тестов (seam coverage, vertical slices, independent literals) | Сырой `loc_final` / `complexity` без вычета `tests/` | LOC взлетает на 1856 строк тестов — это не раздувание, а леса |
| `files_touched` с разбивкой `tests/` vs `app/` | `elapsed` в изоляции (tdd может быть быстрее baseline — см. ниже) | tdd пишет тесты вместо доков — время сопоставимо |
| Rework fixed rate (тесты ловят регрессии рано) | `dependencies` сырые (30 vs 6 — туда попали pytest-зависимости?) | Часть deps — `pytest` из `requirements.txt`, которую eval-хук вырезает, но в метриках остаётся |
| Test survival при рефакторе (переживут ли тесты смену внутренностей) | Токены в целом без разбивки | Токены у tdd скромные (+17%) |

**Главное правило:** сравнивай `app LOC` (без `tests/`) с baseline, а `tests LOC` — отдельно. Иначе tdd всегда «проиграет» по LOC, хотя это его победа.

## След в коде (RealWorld 14 CP)

| Метрика | baseline | **tdd** | Примечание |
|---------|----------|---------|------------|
| CP passed | 14/14 | **14/14** | correctness сохранена |
| Elapsed | 58.2м | **55.3м (-5%)** | быстрее baseline несмотря на тесты! |
| All input | 261k | **305k (+17%)** | скромный налог |
| All output | 39k | **48k (+23%)** | |
| Reasoning | 2.5k | **3.5k (+40%)** | |
| Final LOC (app+tests) | 905 | **2460 (+172%)** | **из них 1856 — `tests/`** |
| App LOC (оценка, без tests) | ~905 | **~604 (-33%)** | app компактнее baseline! |
| Changed LOC | 1169 | **2732 (+134%)** | леса учтены |
| Files touched | 23 | **44 (+91%)** | 16 файлов в `tests/` + app |
| Complexity (app+tests) | 222 | **676 (+205%)** | тесты добавляют ветвления |
| Dependencies | 6 | **30 (+400%)** | `pytest`/`httpx` в requirements? |
| Rework | 0 | **2 (оба fixed)** | CP4 и CP5 |

**Снапшот CP14 `tests/`:**

```
tests/conftest.py (22 строки)
tests/test_article_feed.py (157)
tests/test_authentication.py (164)
tests/test_comments.py (168)
tests/test_create_article.py (142)
tests/test_delete_article.py (72)
tests/test_favorite_article.py (150)
tests/test_follow_unfollow.py (178)
tests/test_get_article.py (78)
tests/test_list_articles.py (193)
tests/test_profile_public_fields.py (68)
tests/test_profiles.py (59)
tests/test_registration.py (72)
tests/test_tags.py (69)
tests/test_update_article.py (140)
tests/test_user_update.py (124)
—— итого 1856 строк тестов
```

Это не «мусор» — это 16 вертикальных срезов, по одному на seam (registration, auth, articles, comments, favorites…). Имена тестов — поведенческие (`test_registration`, `test_follow_unfollow`), не `test_calls_service`.

**App без тестов** (~604 LOC) компактнее baseline (905) — tdd заставил писать минимально достаточный код (правило «only enough to pass»). Doorstop/strictdoc так не умеют — они раздувают.

**Dependencies 30** — аномалия: в `requirements.txt` попали `pytest`, `httpx` и т.д. (агент следовал «тестам нужны зависимости» буквально). `eval_deps_hook` вырезает `pytest` перед `uvx`, но в метриках `dependencies_added` остаётся 30. Это шум метрики, не влияние на correctness (все 14/14 прошли).

**Rework 2:** CP4 (`test_list_articles`?) и CP5 — оба починены за одну попытку. Логика tdd: тест упал → агент дописал минимальный код → зелёно. Без tdd эти же баги могли бы всплыть на поздних CP как регрессии.

## След в диалоге

CP1: 158 событий (самый длинный диалог среди harnesses — леса требуют слов). Петля:

```
reasoning: "seam = POST /api/users, public interface"
tool: write tests/test_registration.py  # RED — failing test
tool: run pytest tests/test_registration.py  # видит FAIL
tool: edit realworld_app/routers/users.py  # GREEN — minimal
tool: run pytest  # PASS
repeat для следующего seam
```

Ключевое: агент не писал «все тесты сразу» (что `tests.md` называет horizontal slicing), а шёл вертикально — один тест → один кусок app. Это видно по чередованию `write tests/` и `edit app/` в `messages.jsonl`.

Smoke tdd — grandfathered (до введения smoke-gate), но в `realworld-all` activation_verified = true.

## Правильное сравнение

- **vs baseline:** 14/14 сохранены, время -5% (быстрее!), токены +17% — налог минимален. Если вычесть тесты, app даже компактнее. Вывод: tdd не замедляет, а дисциплинирует.
- **vs другие классы:** не сравнивать с doorstop/strictdoc по LOC (у них артефакты исключены, у tdd — нет), не сравнивать с benjamin по токенам (у benjamin цель — экономия, у tdd — покрытие). Единственный честный пир для tdd — будущий `code-review` или второй test-харнес.
- **Внутри класса:** если появится `tdd-v2` или `bdd`, сравнивать по: покрытие seams, tautological-rate, mock-rate, survival.

**Ловушка leaderboard:** `loc_final 2460` выглядит «хуже» baseline 905 — но это как сказать «дом с лесами тяжелее дома без лесов». Леса — продукт, не мусор. Правильная метрика: `app_loc ≈ 604` (победа) + `test_loc 1856` (покрытие).

## Рекомендованная схема оценки

**Задача:** **одна** задача с 2–3 чёткими seams (например, `file_backup` CP1: seams = "read YAML", "incremental skip", "verify"). Не 14 CP — леса нужны на одном здании, не на 14.

Чек-лист:

1. Агент согласовал seams до первого теста? (в диалоге должен быть `Ask: What's the public interface...`)
2. Тесты — через публичный интерфейс? (нет `db.query` в тестах, нет моков внутренностей)
3. Ожидаемые значения — литералы из спеки, не `reduce(sum)`?
4. Вертикальные срезы? (чередование `tests/` ↔ `app/`, не «все тесты потом весь код»)
5. `tests/` не содержит `detail`-обёрток, а проверяет `{"errors": …}` как в `test_registration.py`?
6. После зелёного — тесты переживают рефактор? (прогнать `code-review` поверх — не ломаются)

Метрики-маяки:

- `tests/*.py` count и LOC (покрытие)
- `app_loc = total_loc - test_loc` vs baseline
- `rework_fixed / rework_attempts` (ловля багов рано)
- Ручная выборка 3 тестов на tautological/mock признаки

**Не мерить:** `complexity` суммарную, `dependencies` сырые, `files_touched` без разбивки.

## Вердикт

TDD — **леса, которые ускоряют**: 14/14, -5% времени vs baseline, app компактнее на 33%, +1856 строк поведенческих тестов. Налог токенов +17% — самый низкий среди всех harnesses. Цена — 30 зависимостей в метриках (шум) и +91% файлов (леса). На короткой задаче (1 задача, 2–3 seams) — идеален для измерения качества тестов; на 14 CP — тоже держит форму, но 14 CP скрывают его главное — качество одного среза.

**Когда брать:** когда нужен executable spec и защита от регрессий.  
**Когда не брать:** когда задача — аудит требований (тогда strictdoc/doorstop) или экономия токенов любой ценой (тогда benjamin — но без тестов).

---
*Источники:* `harnesses/tdd/skill/SKILL.md`, `tests.md`, `mocking.md`, `results/.../tdd/run_1/{metrics,snapshot/tests,messages}`, `realworld-all` comparison.

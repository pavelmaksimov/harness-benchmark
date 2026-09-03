# Методика анализа влияния harness

> **Цель:** за 1 проход разведки + 1 проход выборок собрать достаточно улик (кодовый след + диалоговый след + метрики), чтобы написать отчёт, не сравнивая тёплое с мягким и не тратя токены впустую.  
> **Откуда взялась:** 5 отчётов `doorstop / strictdoc / tdd / supermemory / benjamin-plus-skill` на `realworld-opencode-x-preview-f-free-high-all-20260822-1838` (14 CP, x-preview-f-free high).

---

## 1. Рамка — 3 правила, без них отчёт врёт

1. **Дистанция разная.** Traceability (doorstop/strictdoc) и Efficiency (benjamin) — витрина 1–2 CP. Verification (tdd) — 1 задача на 2–3 seams. Memory (supermemory) — только марафон ≥5 CP. Мерить лодку в пустыне нельзя.
2. **Сравнивать только внутри класса + baseline.** Требования с требованиями, тесты с тестами, память с памятью, экономия с экономией. Всё остальное — с baseline как контролем.
3. **Вектор влияния свой.** Токены/LOC — не валюта. У кого-то LOC — мусор (docs-артефакты), у кого-то продукт (tests/), у кого-то шум. Сигнал = `кодовый след` (что осталось в snapshot) + `диалоговый след` (как агент вызывал скилл).

Карта классов — в `docs/harness-reports/README.md`. Сверяйся с ней до любого сравнения.

---

## 2. Классификация за 10 секунд

| Класс | Харнесы | Дистанция | Главный вектор |
|-------|---------|-----------|----------------|
| Traceability | doorstop, strictdoc | 1–2 CP | gate валидности спеки, стабильность UID, налог времени/токенов |
| Verification | tdd | 1 задача, 2–3 seams | покрытие seams, вертикальные срезы, отсутствие tautological/mocks |
| Memory | supermemory (+ combo с graphify) | 14 CP | hit-rate `search`/`save`, реюз фиксов, реворки на хвосте |
| Efficiency | benjamin-plus-skill, ponytail | 1 CP достаточно | токены, `elapsed`, `steps`, доля keyhole-чтений |

Если харнес не в таблице — классифицируй по `harnesses/<name>/skill/SKILL.md:description` + наличию `*-docs/` / `tests/` / `supermemory/*.js`.

---

## 3. Источники — что читать, что пропускать

### 3.1 Обязательно (дают 90% сигнала)

| Файл | Зачем | Как читать экономно |
|------|-------|---------------------|
| `harnesses/<name>/skill/SKILL.md` | Вектор, non-negotiable rules, one-time setup, per-checkpoint loop | `read` первые 80 строк; `references/workflow.md` — только если в SKILL ссылка |
| `harnesses/<name>/SMOKE.json` | `harness_activation_verified`, `EXCLUDE_DIR_NAMES`, `checkpoints_completed` | `read` целиком (≤40 строк) |
| `harnesses/<name>/VERSION.json` | pin, `skill_sha256`, bundle-состав | `read` целиком |
| `reports/<exp>/comparison.json` | агрегаты по всем arms (mean, но N=1 — это 1 run) | `python3 -c "import json; d=json.load(open('...')); print(d['raw_totals']['<arm>'])"` — не грузи весь JSON в контекст |
| `reports/<exp>/comparison.txt` | та же таблица, но читаема глазами; `Per-checkpoint (raw)` — налог на CP | `read :1-120` + `read :185-250` (середина — 58 строк повторов) |
| `results/<exp>/<arm>/run_1/metrics/run.json` | истина по arm: `checkpoints_passed`, `elapsed`, `loc_final/changed`, `complexity`, `rework` | `python3 -c` выборка 1–2 полей, `grep -E '"checkpoint_success"|"loc_final"'` |
| `results/<exp>/<arm>/run_1/scb/<problem>/checkpoint_14/snapshot/` | кодовый след: что осталось | `ls` (не `ls -R`), затем `wc -l snapshot/tests/*.py` или `cat snapshot/strictdoc-docs/docs/SPEC.sdoc | head -n 60` — 1 файл-образец |
| `results/.../checkpoint_N/agent/messages.jsonl` | диалоговый след: как агент вызывал скилл | `head -n 30` + `grep -c "tool_use"` + `grep -m 5 "doorstop\|strictdoc\|search-memory\|head -"` — не читай 150 строк подряд |

### 3.2 Опционально (по необходимости)

| Файл | Когда нужен |
|------|-------------|
| `results/.../checkpoint_N/agent/harness_activation.json` | `SMOKE.json` показал `verified:false` — проверить `prompt_ok` |
| `results/.../checkpoint_N/evaluation/stderr.txt` | `checkpoint_success:false` — триаж (см. `benchmark-failure-triage`) |
| `benchmark/structure.py:EXCLUDE_DIR_NAMES` | понять, вычтены ли `*-docs/`/`graphify-out`/`.git` из LOC |
| `harnesses/<name>/skill/references/*.md` | SKILL ссылается и без него gate непонятен |
| `configs/<name>.yaml` + `configs/prompts/<name>-solve.jinja` | проверить activation phrase |

### 3.3 Не читать (сжигают токены, не дают сигнала)

- `vendor/**`, `graphify-out/graph.json` (10136 nodes), `graphify-out/GRAPH_REPORT.md` целиком — только `graphify query` если нужен граф.
- `results/**/scb/**/evaluation/stdout.txt` при `checkpoint_success:true`.
- `results/**/scb/**/snapshot/sdoc-export/html/**`, `snapshot/.venv/**`, `snapshot/__pycache__/**`, `snapshot/.git/**`.
- `logs/**`, `scb_run.log`, `infer.log` целиком — только `tail -20` при диагностике зависания.
- `results/**/metrics/checkpoint_*.json` все 14 штук — бери `run.json` (агрегат) + 1–2 checkpoint выборочно.
- `problems/**` целиком — только 1 чекпоинт-спека если нужна.

---

## 4. Как искать — экономно (benjamin-plus для аналитика)

### 4.1 Разведка за один проход

Собери все независимые факты параллельно, второй проход — только по вопросам первого.

```bash
# Один батч вместо 5 последовательных read
cat harnesses/<name>/skill/SKILL.md | head -n 80; echo "=="
cat harnesses/<name>/SMOKE.json; echo "=="
cat reports/<exp>/comparison.txt | head -n 120; echo "=="
ls results/<exp>/<arm>/run_1/scb/<problem>/checkpoint_14/snapshot/ 2>&1 | head -n 30
```

В агенте: несколько `read`/`bash` в одном `turn`, не по одному.

### 4.2 Скважина (keyhole)

- `ls` перед `cat`, `wc -l` перед `read`, `grep -m 5` перед `grep`.
- `read` с `offset/limit`: `:1-80`, `:50-120`, не весь файл 600 строк.
- `head -n 30 snapshot/file` вместо `cat file` на 500 строк.
- Размер неизвестен? `wc -l file` → затем `read :1-60`.

Правило: инспекция — всегда с лимитером (`| head`, `grep -m`, `read :limit`). Трансформация данных — без усечения.

### 4.3 JSON без загрузки всего

```bash
# Не читай 300-строчный comparison.json в контекст
python3 -c "
import json
d=json.load(open('reports/<exp>/comparison.json'))
for arm in ['baseline','doorstop','strictdoc','tdd','supermemory']:
    v=d['raw_totals'][arm][0]
    print(f\"{arm:12} CP {v['checkpoints_passed']}/{v['checkpoints_total']}  elapsed {v['elapsed_time']/60:.1f}m  LOC {v['loc_final']}  in {v['total_input_tokens']}\")
"
```

### 4.4 Диалог — сэмплируй

```bash
head -n 40 results/.../checkpoint_1/agent/messages.jsonl | cat
grep -c '"tool_use"' results/.../checkpoint_*/agent/messages.jsonl
grep -m 5 'doorstop -j\|strictdoc export\|search-memory\|save-memory' results/.../checkpoint_1/agent/messages.jsonl
```

Достаточно 30–40 строк головы + 5 хитов скилла, чтобы понять петлю. 150 строк — только если петля неясна.

### 4.5 Снапшот — один образец

```bash
ls results/<exp>/doorstop/run_1/scb/realworld/checkpoint_14/snapshot/          # что есть
cat results/.../checkpoint_14/snapshot/doorstop-docs/reqs/REQ001.yml | head -n 20  # как выглядит
ls results/.../tdd/run_1/scb/realworld/checkpoint_14/snapshot/tests/ | head -n 20
wc -l results/.../tdd/run_1/scb/realworld/checkpoint_14/snapshot/tests/*.py | tail -n 1
cat results/.../strictdoc/run_1/scb/realworld/checkpoint_14/snapshot/strictdoc-docs/docs/SPEC.sdoc | head -n 60
```

Не делай `find snapshot -type f | xargs cat`.

---

## 5. Алгоритм — 6 шагов от вопроса к отчёту

**Вход:** `harness=<name>`, `problem` (обычно `realworld` или `file_backup`), `exp` (напр. `realworld-opencode-x-preview-f-free-high-all-20260822-1838`).

1. **Классифицируй** — табл. из §2 → дистанция, пир, вектор.
2. **Разведка (1 батч)** — параллельно: `SKILL.md:1-80` + `SMOKE.json` + `comparison.txt:1-120` + `ls snapshot/` для пира и baseline.
3. **Метрики (1 команда)** — `python3 -c` вытащи `checkpoints_passed`, `elapsed`, `loc_final/changed`, `files_touched`, `complexity`, `rework`, `total_input/output`, `reasoning` для `{harness, peer, baseline}`.
4. **Кодовый след (1 команда)** — `ls snapshot/` + `head` 1 образца (`REQ001.yml` / `SPEC.sdoc` / `tests/*.py` / отсутствие `*-docs/`).
5. **Диалоговый след (1 команда)** — `head messages.jsonl` + `grep` скилл-команд; зафиксируй gate результат и число шагов.
6. **Заполни шаблон** (§6) — только внутриклассовое сравнение, LOC нормируй через `EXCLUDE_DIR_NAMES` (docs — вычет, tests — продукт), токены — только где вектор = Efficiency.

После правки отчётов: `uv run graphify update .` (AST-only, ~15с) — граф не LLM.

---

## 6. Шаблон отчёта

Скопируй `docs/harness-reports/TEMPLATE.md`, замени `{{…}}`. Ниже — тот же шаблон inline.

```markdown
# {{HARNESS}} — {{метафора в 3 слова}}

> **Класс:** {{Traceability|Verification|Memory|Efficiency}} · **Пир:** {{peer}} · **Контроль:** baseline  
> **Идеальная дистанция:** {{1–2 CP | 1 задача 2–3 seams | 14 CP}}

## Что делает харнес

{{2 абзаца: что агент делает каждый CP, где артефакты, как ставит тулзу, метафора (рюкзак/свиток/леса/слон/скважина). Ссылка на SKILL.md + ловушки.}}

## Вектор влияния

| Мерить (сигнал) | Игнорировать (шум) | Почему |
|-----------------|-------------------|--------|
| {{gate / UID / seams / hit-rate / токены}} | {{LOC без нормировки / files без вычета / dependencies сырые}} | {{1 строка}} |

Главное правило: {{одно предложение — что считать успехом}}.

## След в коде ({{problem}} {{N}} CP, {{model}})

| Метрика | baseline | **{{harness}}** | {{peer}} |
|---------|----------|-----------------|----------|
| CP passed | {{n}}/{{m}} | **{{n}}/{{m}}** | {{n}}/{{m}} |
| Elapsed | {{m}} | **{{m}} ({{±%}})** | {{m}} |
| All input / output | {{k}} / {{k}} | **{{k}} ({{±%}}) / {{k}}** | {{k}} |
| Final LOC | {{n}} | **{{n}} ({{±%}})** | {{n}} |
| Files / Complexity | {{n}} / {{n}} | **{{n}} / {{n}}** | {{n}} |
| Rework | {{n}} | **{{n}} (fixed {{n}})** | {{n}} |

**Снапшот CP{{last}}:** `results/.../{{harness}}/run_1/scb/{{problem}}/checkpoint_{{last}}/snapshot/{{path}}` — {{что лежит, сколько файлов, пример 5 строк}}.

**Почему так:** {{1–2 строки интерпретации — раздул/не раздул, где налог осел}}.

## След в диалоге

CP{{n}}: {{steps}} шагов, {{tool_use}} tool_use. Петля: `{{команда скилла}} → {{gate}} → {{implement}}`. Gate {{с 1-й попытки / со 2-й (причина)}}. Smoke `verified:{{true/false}}`.

## Правильное сравнение

- **vs baseline:** {{correctness сохранена/нет, цена ±% времени/токенов, вывод — налог оправдан/нет}}.
- **vs {{peer}}:** {{кто быстрее/легче/дороже, выбор когда}}.
- **Не сравнивать с:** {{перечислить классы, где LOC/токены — шум}}.

## Рекомендованная схема оценки

**Задача:** {{какая дистанция достаточна}}. Чек-лист:
1. {{gate == 0 + grep UID / seams согласованы / search/save частота / keyhole доля}}
2. {{стабильность UID / отсутствие tautological / отсутствие свалки / одна установка}}
3. {{налог CP1 vs baseline}}
4. {{отсутствие тулзы в requirements.txt}}
5. {{специфичное для класса}}

Метрики-маяки: `{{harness_activation_verified, EXCLUDE_DIR_NAMES, rework_fixed, …}}`

## Вердикт

{{3–4 строки: работает ли, тяжёлый/лëгкий, когда брать, когда не брать. Без воды.}}

---
*Источники:* `harnesses/{{harness}}/skill/SKILL.md`, `SMOKE.json`, `results/.../{{harness}}/run_1/{metrics,snapshot,agent}`, `reports/<exp>/comparison.json`.
```

---

## 7. Чек-лист перед публикацией

- [ ] Сравнение только внутри класса + baseline (нет `doorstop LOC vs tdd LOC`).
- [ ] LOC нормирован: docs-артефакты вычтены (`EXCLUDE_DIR_NAMES` проверен), `tests/` — учтён как продукт.
- [ ] Каждый факт — из файла (путь указан в «Источниках»), нет выдумок.
- [ ] Диалоговый след — по `messages.jsonl`, не по памяти.
- [ ] N=1 оговорён как «не наука, но вектор виден».
- [ ] Отчёт ≤130 строк, таблицы — без `| |` мусора, примеры — `head -n 20`.
- [ ] `graphify update .` запущен после правки.

---

## 8. Частые ошибки (из 5 отчётов)

| Ошибка | Как избежать |
|--------|--------------|
| Читать весь `comparison.json` в контекст | `python3 -c` выборка 1 физической строкой |
| Сравнивать `loc_final 2460 (tdd)` vs `905 (baseline)` как «раздувание» | Вычесть `tests/` LOC, сравнить `app_loc` |
| Мерить `files_touched` без вычета `*-docs/` | Проверить `benchmark/structure.py:EXCLUDE_DIR_NAMES` |
| Читать все `messages.jsonl` (14 CP × 150 строк) | `head -n 30` CP1 + `grep -m 5` скилл-команд |
| `ls -R snapshot/` на 300 файлов | `ls snapshot/` + `wc -l snapshot/tests/*.py` |
| Считать `dependencies 30 (tdd)` провалом | Это `pytest` в `requirements.txt`, `eval_deps_hook` вырезает — шум метрики |
| Сравнивать benjamin токены из разных `exp` | Только внутри одного `experiment_id` |
| Делать общий leaderboard-скор | Запрещено `benchmark-core` — только раздельные измерения |

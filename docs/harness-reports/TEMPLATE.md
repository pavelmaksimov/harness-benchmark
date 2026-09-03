# {{HARNESS}} — {{метафора в 3 слова}}

> **Класс:** {{Traceability | Verification | Memory | Efficiency}} · **Пир:** {{peer-harness}} · **Контроль:** baseline  
> **Идеальная дистанция:** {{1–2 CP | 1 задача 2–3 seams | 14 CP}}  
> **Проблема:** {{realworld | file_backup | task_manager}} · **Эксперимент:** `{{experiment_id}}` ({{model}} {{thinking}})

## Что делает харнес

{{2 абзаца: что агент делает каждый CP, куда кладёт артефакты (`*-docs/` / `tests/` / `supermemory/*.js`), как ставит тулзу (`uv tool install …`, не в requirements.txt), ключевые ловушки. Закончи метафорой: рюкзак / свиток / леса / слон / скважина.}}

SKILL: `harnesses/{{harness}}/skill/SKILL.md` + `{{references/workflow.md}}`

## Вектор влияния — что мерить, что игнорировать

| Мерить (сигнал) | Игнорировать (шум) | Почему |
|-----------------|-------------------|--------|
| {{gate валидности / стабильность UID / покрытие seams / hit-rate памяти / токены}} | {{сырой LOC без нормировки / files без вычета / dependencies сырые / reasoning в целом}} | {{1 строка}} |
| {{…}} | {{…}} | {{…}} |

Главное правило: {{одно предложение — что считать успехом (solution first, gate + тесты, etc.)}}.

## След в коде ({{problem}} {{N}} CP)

| Метрика | baseline | **{{harness}}** | {{peer}} |
|---------|----------|-----------------|----------|
| CP passed |  /  | ** / ** |  /  |
| Elapsed |  | ** ( ±% )** |  |
| All input / output |  /  | ** / ( ±% )** |  /  |
| Reasoning |  | ** ( ±% )** |  |
| Final LOC |  | ** ( ±% )** |  |
| Changed LOC |  | ** ( ±% )** |  |
| Files touched |  | ** ( + )** |  |
| Complexity |  | ** ( ±% )** |  |
| Dependencies |  | ** ** |  |
| Rework (fixed / attempts) |  /  | ** / ** |  /  |

**Снапшот CP{{last}}:** `results/{{exp}}/{{harness}}/run_1/scb/{{problem}}/checkpoint_{{last}}/snapshot/{{path}}`

```
{{5–10 строк образца: REQ001.yml / SPEC.sdoc / ls tests/ + wc -l / отсутствие *-docs/}}
```

**Почему так:** {{1–2 строки интерпретации — куда ушёл налог, раздул ли app}}.

## След в диалоге

- CP{{n}}: {{steps}} шагов, {{tool_use}} tool calls. Петля: `{{команда скилла}} → {{gate}} → {{implement}}`.
- Gate: {{с 1-й попытки / со 2-й, причина (WARNING: no text / RELATIONS vs REFS)}}.
- Smoke: `harness_activation_verified: {{true/false}}`, `EXCLUDE_DIR_NAMES` включает `{{*-docs}}`.
- Характерный `messages.jsonl` фрагмент (head 5 строк):

```
{{reasoning: "…"}}
{{tool: …}}
```

## Правильное сравнение

- **vs baseline:** {{correctness сохранена/нет, цена ±% времени/токенов, налог оправдан?}}
- **vs {{peer}}:** {{кто быстрее/легче/дороже на сколько %, выбор когда}}.
- **Не сравнивать с:** {{классы, где эта метрика — шум (напр. не сравнивать traceability LOC с tdd LOC)}}.

## Рекомендованная схема оценки (для будущих прогонов)

**Задача:** {{какая дистанция достаточна и почему}}.

Чек-лист:
1. {{gate == 0 + grep UID / seams согласованы / search/save ≥1 на CP / keyhole ≥50%}}
2. {{стабильность UID / отсутствие tautological / нет свалки памяти / одна установка deps}}
3. {{налог CP1 vs baseline (elapsed / input)}}
4. {{тулза отсутствует в requirements.txt}}
5. {{специфичное: RELATIONS / vertical slices / hit-rate / steps}}

Метрики-маяки: `{{harness_activation_verified, EXCLUDE_DIR_NAMES, rework_fixed, …}}`

## Вердикт

{{3–4 строки: работает ли, тяжёлый/лёгкий, когда брать, когда не брать. Без воды.}}

---
*Источники:* `harnesses/{{harness}}/skill/SKILL.md`, `harnesses/{{harness}}/SMOKE.json`, `results/{{exp}}/{{harness}}/run_1/{metrics,snapshot,agent}`, `reports/{{exp}}/comparison.{json,txt}`

<!-- Заполни, затем: uv run graphify update . -->

# Быстрый статус и результаты benchmark

Используй этот runbook при запросах `status`, `results`, `progress`, `slow` или
`stuck`. Он рассчитан на read-only проверку с минимальным расходом времени и
токенов.

## Источники истины

Проверяй в таком порядке:

1. `results/<experiment>/<arm>/run_N/state.json` — жизненный цикл слота.
2. `scb/<problem>/checkpoint_N/evaluation.json` — факт оценки и Core-результат.
3. Время изменения `prompt.txt`, `inference_result.json`, `diff.json` — живой
   прогресс текущего checkpoint.
4. `fleet-monitor.log` — причина resume/retry и число завершённых слотов.
5. `docker ps`/`docker top` — действительно ли агент или evaluator жив.
6. `reports/<experiment>/comparison.{txt,json}` — итог только завершённых
   прогонов; `N=0` означает, что сравнивать пока нечего.

Хвост `infer.log` сам по себе не является источником истины: записи могут быть
буферизованы.

## Tight-проверка за несколько чтений

Выполняй из корня репозитория. Сначала найди свежие слоты:

```bash
find results -path '*/run_*/state.json' -printf '%T@ %p\n' | sort -nr | head -30
```

Для интересующего `state.json` прочитай только нужные поля:

```bash
jq '{experiment_id,arm,run_index,phase,last_completed_checkpoint,stopped_at_checkpoint,interrupt_reason,updated_at,checkpoints}' \
  results/<experiment>/<arm>/run_N/state.json
```

Затем посчитай фактически оценённые checkpoint по диску:

```bash
find results/<experiment>/<arm>/run_N/scb/<problem> \
  -mindepth 2 -maxdepth 2 -name evaluation.json \
  -printf '%TY-%Tm-%TdT%TH:%TM:%TS%Tz %h\n' | sort
```

Если непонятно, идёт ли работа прямо сейчас, только тогда проверь процессы:

```bash
pgrep -af 'monitor_benchmark.py|benchmark.scb_main'
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

При `permission denied` у Docker запроси read-only escalation; не делай вывод,
что Docker выключен. Для конкретного контейнера:

```bash
docker top <container>
```

`opencode ... run` означает работу агента; `uvx ... pytest` — evaluator; один
`sleep infinity` без дочернего процесса — подозрение на осиротевший контейнер.

## Если checkpoint кажется медленным

Не жди по тишине лога. Сверь mtimes и последние значимые события:

```bash
find results/<experiment>/<arm>/run_N/scb/<problem>/checkpoint_N -maxdepth 1 \
  -type f -printf '%TY-%Tm-%TdT%TH:%TM:%TS%Tz %f\n' | sort
rg -n 'Running checkpoint|Starting OpenCode|OpenCode error|retry_attempt|Starting pytest|Single-shot docker run completed|Completed checkpoint|Agent reached terminal' \
  results/<experiment>/<arm>/run_N/scb/<problem>/infer.log | tail -40
```

Интерпретация:

- свежие `inference_result.json`/`diff.json` и живой `opencode` → checkpoint
  жив, подожди следующий poll;
- `OpenCode error`/`retry_attempt` → задержка провайдера или CLI retry;
- `Starting pytest` и живой `uvx`/evaluator → идёт оценка, а не агент;
- `phase=started`, но `last_completed_checkpoint` не меняется → смотри mtime
  файлов и контейнер, не только `state.json`;
- `phase=incomplete` + новый `monitor` attempt → слотовый run перезапускается;
  прежний красный checkpoint может быть удалён native resume и запущен заново.

После завершения читай только сводку:

```bash
jq '{arms,incomplete_runs,excluded_runs,summary}' \
  reports/<experiment>/comparison.json
sed -n '1,45p' reports/<experiment>/comparison.txt
```

Красный checkpoint сначала триажь по `evaluation.json` и `evaluation/stdout.txt`
или `stderr.txt`: setup/import и `infrastructure_failure` не считаются ошибкой
модели. Не удаляй `/tmp/tmp*` во время живого прогона.

## Политика ожидания

Для долгого живого прогона повторяй эту короткую проверку раз в 5 минут. Не
запускай `fleet plan`, полный `run`, Graphify или пересборку отчёта, если нужен
только статус: это лишняя работа и токены. Завершённым считай только слот, у
которого `state.phase=completed`, `fully_completed=true` и существует читаемый
`metrics/run.json`.

В итоговом сообщении укажи timestamp, experiment/arm, последний checkpoint с
`evaluation.json`, фазу, активный процесс/его отсутствие, `N` отчёта и отдельно
неполные или невалидные результаты.

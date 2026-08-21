# Harness benchmark

Сравнение harness-траекторий на одной задаче: в одном эксперименте одинаковые агент, модель, thinking, среда и бюджеты; меняется только закреплённый harness.

Построено поверх SlopCodeBench (вендор в `vendor/slop-code-bench`). Агент подключается через адаптер (`--agent` / configs); сейчас есть Codex и OpenCode — это не идентичность бенчмарка.

| Arm | Harness |
|-----|---------|
| **baseline** | нет skill и extra `AGENTS.md` |
| **skill-arm** | pin из `harnesses/<arm>/` + prompt |

Состав pin’а — свойство конкретного arm (`VERSION.json` + файлы в его каталоге), а не каталог скиллов этого репозитория. Список arm’ов — `benchmark/arms.py`.

`pass_policy: all-core-cases` определяет correctness чекпоинта. Тестовый
провал не обрывает траекторию: benchmark hook доводит CP1→CP4 до конца,
а ошибки агента, rate-limit и инфраструктурные сбои оставляют run
`incomplete` для resume.

## Pins

См. `vendor/pins.json` и `harnesses/<arm>/VERSION.json`.

Текущие значения (зафиксированы при bootstrap):

- `slop-code-bench`: см. pins
- `scb-problems`: см. pins
- Skill pins: `harnesses/<arm>/VERSION.json`
- Codex image version: `0.145.0` (`configs/agent_codex.yaml`)
- OpenCode image version: см. `opencode_cli_version` в pins (`configs/agent_opencode.yaml`)

## Setup

```bash
# 1) Vendor + deps
bash scripts/bootstrap_vendor.sh

# 2) Auth for Codex inside SCB Docker: ~/.codex/auth.json
#    (provider: codex_auth)
#    Optional OpenCode: ~/.local/share/opencode/auth.json
#    (provider: opencode_auth; `opencode auth login`)

# 3) Docker должен быть запущен
docker ps

# 4) Pre-build images (base + Codex + OpenCode; 10–30 мин первый раз)
bash scripts/build_images.sh
```

Runner автоматически выставляет изолированный `DOCKER_CONFIG` без broken
`docker-credential-yc` helpers (иначе docker-py падает на build).

## Reproduce experiment

### Один baseline run (CP1→CP4)

```bash
uv run python -m benchmark run --arm baseline --problem file_backup --runs 1
```

По умолчанию: `--agent codex`, `--provider codex_auth`, модель/thinking из дефолтов.
Модель и провайдер можно задать явно: `--provider … --model …`.

### OpenCode (baseline only; модель и провайдер обязательны)

```bash
uv run python -m benchmark run --arm baseline \
  --agent opencode \
  --provider opencode_auth \
  --model deepseek-v4-flash-free \
  --thinking none
```

Skill-arm’ы с OpenCode не поддерживаются (хуки skills заточены под Codex).

### Один ponytail run

```bash
uv run python -m benchmark run --arm ponytail --problem file_backup --runs 1
```

### Несколько повторов по всем DEFAULT_EXPERIMENT_ARMS + report

```bash
uv run python -m benchmark run-all --problem file_backup --runs 3
# подмножество: --arms baseline,ponytail
```

### Report по последнему / заданному experiment

```bash
uv run python -m benchmark report
uv run python -m benchmark report --experiment-id YYYYMMDDTHHMMSS
```

Результаты:

- raw SCB outputs: `results/<experiment>/<arm>/run_N/scb/` (gitignored)
- unified metrics: `results/<experiment>/<arm>/run_N/metrics/`
- `manifest.json` на каждый run
- full comparison: `reports/<experiment>/comparison.{txt,json}` (gitignored)
- short report + leaderboard: `docs/reports/<id>.md`, `docs/LEADERBOARD.md` (committed)

`report` / `run-all` всегда публикуют short report и пересобирают leaderboard.

## Results guide

- [Leaderboard](docs/LEADERBOARD.md) — срезы by task / by model / experiments (новые сверху)
- [Short reports](docs/reports/) — один экран на эксперимент

## Skill activation (доказательная)

Для skill-arm’а (пример: `ponytail`):

1. Перед каждым checkpoint pin копируется в Codex home mount (`~/.codex/skills/<name>/`)
2. Prompt начинается с явной активации (`configs/prompts/<arm>-solve.jinja`)
3. В artifacts пишется `harness_activation.json` (sha256 skill + verified flag)

Если verification fails → `harness_activation_verified=false` и run исключается из сравнения.

Baseline проверяется на отсутствие skill-активации в prompt и отсутствие activation marker.

## Smoke experiment (N=1)

Первый smoke уже в гайде: [mvp-smoke-baseline](docs/reports/mvp-smoke-baseline.md)
(Codex `0.145.0`, `gpt-5.5`, thinking `medium`, `file_backup`).

Перед полным прогоном **нового** skill-harness — обязательный CP1-only smoke
(проверяет, что arm стартует, и показывает лишние файлы для `EXCLUDE_DIR_NAMES`):

```bash
uv run python -m benchmark smoke --arm graphify --problem file_backup
```

`run` / `run-all` отказываются запускать arm без валидного `harnesses/<arm>/SMOKE.json`
(override: `--skip-smoke-check`).

Для статистики MVP после проверки pipeline:

```bash
uv run python -m benchmark run-all --problem file_backup --runs 3
```

## Rework loop (test-failure retries)

По умолчанию падение Core-тестов чекпоинта останавливает траекторию
(`pass_policy: all-core-cases`). Флаг `--rework-attempts N` (run/run-all,
по умолчанию `2`) вместо остановки возвращает задачу агенту на доработку:
промпт чекпоинта дополняется блоком `[REWORK ATTEMPT k]` со списком упавших
тестов, а workspace сохраняет код предыдущей попытки, так что агент правит
в месте. Попытка пере-оценивается тем же пайплайном.

- Лимит `N` — это **дополнительные** попытки сверх первой; `--rework-attempts 0` выключает реворк (поведение SCB как раньше).
- Реворк не запускается, если попытка завершилась ошибкой агента, rate-limit'ом
  или `infrastructure_failure` (это проблемы раннера, а не модели).
- Каждая попытка пишет `rework.json` в каталог чекпоинта:
  `{checkpoint, attempts_total, fixed, attempts: [{passed_policy, pass_counts,
  total_counts, failed_tests, ...}]}`.
- Статистика попадает в метрики (`cumulative.rework_*`), comparison report
  (строки `Rework attempts/fixed/unresolved`), short report (Notes) и в
  `failures/<problem>.json` как записи с `source: "rework"` — по ним видно,
  какие модели на какие тесты попадают и как часто исправляются.
- Smoke (CP1 gate) всегда идёт с `rework_attempts=0`.

```bash
uv run python -m benchmark run --arm baseline --problem file_backup --runs 1 --rework-attempts 2
uv run python -m benchmark run-all --problem file_backup --runs 3 --rework-attempts 0
```

## Resume прерванных прогонов (`--resume`, `state.json`)

Каждый run пишет `state.json` в каталог `results/<experiment>/<arm>/run_N/`
(рядом с `manifest.json`). Файл пишется до старта SCB (маркер `started`
с identity), после успеха/краша и при Ctrl-C (`phase: interrupted` с
фактическим местом остановки). Одна читка отвечает на вопрос
«что перезапускать»: последний пройденный чекпоинт, точка остановки и причина.

```bash
# Где остановился эксперимент (read-only, без SCB/Docker)
uv run python -m benchmark status
uv run python -m benchmark status --experiment-id <id>

# Продолжить с места остановки
uv run python -m benchmark run-all --problem file_backup \
  --experiment-id <id> --runs 3 --jobs 2 --resume
# То же для одиночного run: ... --arm baseline --runs 1 --resume
```

Как это работает:

- Под капотом включается нативный resume SlopCodeBench — SCB сам определяет,
  какие чекпоинты выжили (агент завершил без ошибки), и запускает только
  оставшиеся. Метка/среду берут из сохранённого конфигурационного снапшота;
  флаги `--model/--agent/...` при resume не передаются.
- Опущенные при `--resume` флаги `--provider/--model/--thinking` (и `--agent`
  по умолчанию) восстанавливаются из `state.json` — повторять исходный запуск
  не требуется; явно переданный флаг, отличающийся от записанного, отклоняется.
- Опущенный `--rework-attempts` также восстанавливается из `state.json`; явно
  переданное отличающееся значение отклоняется. Новые слоты при расширении
  матрицы наследуют сохранённый выбор своего arm.
- Завершённые слоты матрицы (все чекпоинты `done`, exit 0, `metrics/run.json`
  на месте) прогоняются мимо — метрики перечитываются с диска, SCB не стартует.
  `incomplete` runs сохраняются для диагностики, но не попадают в средние
  значения отчета.
- Workspace агентского каталога между попытками сохраняется (prompt.txt /
  черновики — как были); устаревшие `rework.json`/`evaluation.json` за
  чекпоинтами, которые реально перезапустятся, удаляются до старта.
- `--resume` требует явный `--experiment-id`, отказывается, если identity
  запроса отличается от записанной в `state.json`, и отклоняет `--runs N`,
  меньше чем уже записанных слотов (перезапись готовых прогонов запрещена).
- Новый запуск с тем же `--experiment-id` не удаляет старые `run_N`: он
  проверяет identity и добавляет следующие свободные индексы. Для другого
  adapter/model/harness используется новый `experiment_id`.

Поля `state.json`, useful for automation: identity (`experiment_id`, `arm`,
`run_index`, `problem`, `agent`, `provider`, `model`, `thinking`), lifecycle
(`phase`, `exit_code`, `interrupt_reason`) и native checkpoint state
(`checkpoints`, `last_completed_checkpoint`, `stopped_at_checkpoint`,
`fully_completed`), а также конфигурация rework (`rework_attempts`).

Лимитации (семантика SCB, а не обёртки):

- Агентовский чекпоинт с красными тестами считается завершённым и НЕ
  перезапускается: resume идёт дальше него. Прошедший pass-policy early stop
  возобновляется с первого **не начатого** чекпоинта.
- `SIGKILL` обновить `state.json` не может в принципе; resume всё равно
  продолжит корректно — выжившие чекпоинты SCB определяет по диску, а
  записанный до старта маркер `started` сохраняет identity прогона.
- Прогон, начатый до введения `state.json`, резюмабельностью не обладает:
  `status` пометит его `legacy (no state.json; start fresh)`, `--resume`
  откажется продолжать — перезапустите такой run без флага.
- Сбой самого runner'а (Docker/API) во время первой попытки нужно сначала
  триажить по правилам failure-triage, прежде чем верить `interrupt_reason`.

## Optional judge

Не влияет на correctness. Пример (после run):

```python
from pathlib import Path
from benchmark.judge import run_judge_codex

run_judge_codex(
    snapshot_dir=Path("results/.../checkpoint_4/snapshot"),
    specs=[Path("vendor/scb-problems/file_backup/checkpoint_1.md").read_text()],
)
```

## Layout

```text
benchmark/          # orchestration + metrics/report
configs/            # arm YAML / pricing / agent / prompts
harnesses/          # pinned skill trees per arm
vendor/             # slop-code-bench + scb-problems (pinned commits)
docs/               # LEADERBOARD + short reports (committed)
results/            # experiment outputs (gitignored)
reports/            # full comparison tables (gitignored)
```

## Acceptance mapping

См. план MVP §23: pipeline, telemetry, normalized cost, diff/LOC/deps/complexity,
cumulative metrics, JSON results, comparison report, N=3, manifests, README commands.

# SlopCodeBench × Ponytail MVP (agent = Codex)

Сравнение двух harness-траекторий на задаче `file_backup` из SlopCodeBench:

| Arm | Agent | Model | Harness |
|-----|-------|-------|---------|
| **baseline** | Codex CLI | pinned | none |
| **ponytail** | Codex CLI | same | pinned Ponytail coding skill only |

Меняется только harness. Claude Code не используется.

`pass_policy: all-core-cases` — early-stop только если падают Core-тесты,
чтобы траектория CP1→CP4 доходила до конца; Functionality/Regression всё равно
собираются в метриках.

## Pins

См. `vendor/pins.json` и `harnesses/ponytail/VERSION.json`.

Текущие значения (зафиксированы при bootstrap):

- `slop-code-bench`: см. pins
- `scb-problems`: см. pins
- Ponytail skill: `4.8.4` (только `skills/ponytail/SKILL.md`)
- Codex image version: `0.145.0` (`configs/agent_codex.yaml`)

## Setup

```bash
# 1) Vendor + deps
bash scripts/bootstrap_vendor.sh

# 2) Auth for Codex inside SCB Docker: ~/.codex/auth.json
#    (provider: codex_auth)

# 3) Docker должен быть запущен
docker ps

# 4) Pre-build images (apt/nvm/rust/codex; 10–30 мин первый раз)
bash scripts/build_images.sh
```

Runner автоматически выставляет изолированный `DOCKER_CONFIG` без broken
`docker-credential-yc` helpers (иначе docker-py падает на build).

## Reproduce experiment

### Один baseline run (CP1→CP4)

```bash
uv run python -m benchmark run --arm baseline --problem file_backup --runs 1
```

### Один ponytail run

```bash
uv run python -m benchmark run --arm ponytail --problem file_backup --runs 1
```

### Полный MVP: 3×baseline + 3×ponytail + report

```bash
uv run python -m benchmark run-all --problem file_backup --runs 3
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

## Ponytail activation (доказательная)

Для arm=`ponytail`:

1. Перед каждым checkpoint skill копируется в Codex home mount: `~/.codex/skills/ponytail/SKILL.md`
2. Prompt начинается с явной активации (`configs/prompts/ponytail-solve.jinja`)
3. В artifacts пишется `harness_activation.json` (sha256 skill + verified flag)

Если verification fails → `harness_activation_verified=false` и run исключается из сравнения.

Baseline проверяется на отсутствие ponytail в prompt и отсутствие activation marker.

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
configs/            # baseline/ponytail/pricing/agent/prompts
harnesses/ponytail/ # pinned SKILL.md
vendor/             # slop-code-bench + scb-problems (pinned commits)
docs/               # LEADERBOARD + short reports (committed)
results/            # experiment outputs (gitignored)
reports/            # full comparison tables (gitignored)
```

## Acceptance mapping

См. план MVP §23: pipeline, telemetry, normalized cost, diff/LOC/deps/complexity,
cumulative metrics, JSON results, comparison report, N=3, manifests, README commands.

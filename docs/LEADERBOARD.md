# Leaderboard

No single score. Absolute metrics only. Δ vs baseline is only in short reports
for the same `(problem, model)` cell.

Published from `docs/reports/*.json`. Rebuilt by `python -m benchmark report`.
Newer experiments appear first.

## By task

### `file_backup`

| Model | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| gpt-5.5 | baseline | 1 | 4 | 100 | $2.15 | 11.1m | 581 | 732 | 1 | 151 |
| gpt-5.5 | ponytail | 1 | 4 | 49 | $2.41 | 12.2m | 485 | 560 | 1 | 133 |

## By model

### `gpt-5.5`

| Problem | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| file_backup | baseline | 1 | 4 | 100 | $2.15 | 11.1m | 581 | 732 | 1 | 151 |
| file_backup | ponytail | 1 | 4 | 49 | $2.41 | 12.2m | 485 | 560 | 1 | 133 |

## Experiments

| Experiment | Date | Problem | Model | N | Report |
|------------|------|---------|-------|---|--------|
| mvp-smoke-baseline | 2026-08-12 | file_backup | gpt-5.5 | 1+1 | [short](reports/mvp-smoke-baseline.md) |

# Leaderboard

No single score. Absolute metrics only. Δ vs baseline is only in short reports
for the same `(problem, model)` cell.

Published from `docs/reports/*.json`. Rebuilt by `python -m benchmark report`.
Newer experiments appear first.

## By task

### `file_backup`

| Model | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| gpt-5.6-luna | baseline | 1 | 3/4 | 106 | $2.19 | 41.7m | 1065 | 1455 | 1 | 230 |
| gpt-5.6-luna | code-review | 1 | 4/4 | 106 | $2.04 | 78.3m | 986 | 1276 | 2 | 235 |
| gpt-5.6-luna | graphify | 1 | 4/4 | 100 | $2.34 | 46.0m | 796 | 1025 | 1 | 199 |
| gpt-5.6-luna | ponytail | 1 | 4/4 | 106 | $1.67 | 30.5m | 515 | 751 | 1 | 176 |
| gpt-5.6-luna | review-agent | 1 | 4/4 | 100 | $2.79 | 49.8m | 884 | 1355 | 1 | 221 |
| gpt-5.6-luna | supermemory | 1 | 4/4 | 106 | $2.42 | 43.0m | 838 | 1257 | 1 | 194 |
| gpt-5.6-luna | tdd | 1 | 4/4 | 49 | $2.90 | 50.2m | 1669 | 1848 | 1 | 213 |
| gpt-5.6-luna | thermo-nuclear-code-quality-review | 1 | 4/4 | 106 | $2.72 | 48.8m | 679 | 918 | 1 | 172 |
| gpt-5.5 | baseline | 1 | 4/- | 100 | $2.15 | 11.1m | 581 | 732 | 1 | 151 |
| gpt-5.5 | ponytail | 1 | 4/- | 49 | $2.41 | 12.2m | 485 | 560 | 1 | 133 |

## By model

### `gpt-5.6-luna`

| Problem | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| file_backup | baseline | 1 | 3/4 | 106 | $2.19 | 41.7m | 1065 | 1455 | 1 | 230 |
| file_backup | code-review | 1 | 4/4 | 106 | $2.04 | 78.3m | 986 | 1276 | 2 | 235 |
| file_backup | graphify | 1 | 4/4 | 100 | $2.34 | 46.0m | 796 | 1025 | 1 | 199 |
| file_backup | ponytail | 1 | 4/4 | 106 | $1.67 | 30.5m | 515 | 751 | 1 | 176 |
| file_backup | review-agent | 1 | 4/4 | 100 | $2.79 | 49.8m | 884 | 1355 | 1 | 221 |
| file_backup | supermemory | 1 | 4/4 | 106 | $2.42 | 43.0m | 838 | 1257 | 1 | 194 |
| file_backup | tdd | 1 | 4/4 | 49 | $2.90 | 50.2m | 1669 | 1848 | 1 | 213 |
| file_backup | thermo-nuclear-code-quality-review | 1 | 4/4 | 106 | $2.72 | 48.8m | 679 | 918 | 1 | 172 |

### `gpt-5.5`

| Problem | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| file_backup | baseline | 1 | 4/- | 100 | $2.15 | 11.1m | 581 | 732 | 1 | 151 |
| file_backup | ponytail | 1 | 4/- | 49 | $2.41 | 12.2m | 485 | 560 | 1 | 133 |

## Experiments

| Experiment | Date | Problem | Model | N | Report |
|------------|------|---------|-------|---|--------|
| luna-max-multi-harness-20260812T133624 | 2026-08-12 | file_backup | gpt-5.6-luna | 1+1+1+1+1+1+1+1 | [short](reports/luna-max-multi-harness-20260812T133624.md) |
| mvp-smoke-baseline | 2026-08-12 | file_backup | gpt-5.5 | 1+1 | [short](reports/mvp-smoke-baseline.md) |

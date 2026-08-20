# Leaderboard

No single score. Absolute metrics only. Δ vs baseline is only in short reports
for the same `(problem, model)` cell.

Published from `docs/reports/*.json`. Rebuilt by `python -m benchmark report`.
Newer experiments appear first.

## By task

### `task_manager`

| Model | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| deepseek-v4-flash-free | baseline | 1 | 8/10 | 8 | $0.00 | 139.3m | 1754 | 3263 | 6 | 434 |
| gpt-5.5 | baseline | 1 | 2/3 | 2 | $2.22 | 15.3m | 706 | 915 | 6 | 176 |
| gpt-5.5 | graphify | 1 | 2/3 | 0 | $2.64 | 17.0m | 674 | 884 | 4 | 153 |
| gpt-5.5 | supermemory | 1 | 2/3 | 2 | $2.61 | 15.5m | 675 | 912 | 6 | 159 |

### `healthchecks`

| Model | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| gpt-5.5 | tdd | 1 | 1/2 | 0 | $1.70 | 12.0m | 638 | 814 | 5 | 185 |

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

### `unknown`

| Model | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| unknown | gpt55-medium | 1 | 15/15 | 14 | $14.64 | 64.8m | 2820 | 3590 | 5 | 778 |
| unknown | gpt56-luna-xhigh | 1 | 15/15 | 0 | $11.02 | 184.3m | 4768 | 6054 | 4 | 978 |

## By model

### `deepseek-v4-flash-free`

| Problem | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| task_manager | baseline | 1 | 8/10 | 8 | $0.00 | 139.3m | 1754 | 3263 | 6 | 434 |

### `gpt-5.5`

| Problem | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| task_manager | baseline | 1 | 2/3 | 2 | $2.22 | 15.3m | 706 | 915 | 6 | 176 |
| task_manager | graphify | 1 | 2/3 | 0 | $2.64 | 17.0m | 674 | 884 | 4 | 153 |
| task_manager | supermemory | 1 | 2/3 | 2 | $2.61 | 15.5m | 675 | 912 | 6 | 159 |
| healthchecks | tdd | 1 | 1/2 | 0 | $1.70 | 12.0m | 638 | 814 | 5 | 185 |
| file_backup | baseline | 1 | 4/- | 100 | $2.15 | 11.1m | 581 | 732 | 1 | 151 |
| file_backup | ponytail | 1 | 4/- | 49 | $2.41 | 12.2m | 485 | 560 | 1 | 133 |

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

### `unknown`

| Problem | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| unknown | gpt55-medium | 1 | 15/15 | 14 | $14.64 | 64.8m | 2820 | 3590 | 5 | 778 |
| unknown | gpt56-luna-xhigh | 1 | 15/15 | 0 | $11.02 | 184.3m | 4768 | 6054 | 4 | 978 |

## Experiments

| Experiment | Date | Problem | Model | N | Report |
|------------|------|---------|-------|---|--------|
| tm-opencode-dsflash-20260819T161858 | 2026-08-19 | task_manager | deepseek-v4-flash-free | 1 | [short](reports/tm-opencode-dsflash-20260819T161858.md) |
| gpt55-med-codex-task-manager-20260819T1330 | 2026-08-19 | task_manager | gpt-5.5 | 1+1+1 | [short](reports/gpt55-med-codex-task-manager-20260819T1330.md) |
| healthchecks-gpt55-med-tdd-full-20260819T075005 | 2026-08-19 | healthchecks | gpt-5.5 | 1 | [short](reports/healthchecks-gpt55-med-tdd-full-20260819T075005.md) |
| luna-max-multi-harness-20260812T133624 | 2026-08-12 | file_backup | gpt-5.6-luna | 1+1+1+1+1+1+1+1 | [short](reports/luna-max-multi-harness-20260812T133624.md) |
| mvp-smoke-baseline | 2026-08-12 | file_backup | gpt-5.5 | 1+1 | [short](reports/mvp-smoke-baseline.md) |
| tm-gpt-models |  | unknown | unknown | 1+1 | [short](reports/tm-gpt-models.md) |
| task_manager-multi-harness-20260819T203814 |  | unknown | unknown | 0+0 | [short](reports/task_manager-multi-harness-20260819T203814.md) |
| realworld-multi-harness-20260819T204314 |  | unknown | unknown | 0+0 | [short](reports/realworld-multi-harness-20260819T204314.md) |
| healthchecks-multi-harness-20260819T204815 |  | unknown | unknown | 0+0 | [short](reports/healthchecks-multi-harness-20260819T204815.md) |

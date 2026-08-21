# Leaderboard

No single score. Absolute metrics only. Δ vs baseline is only in short reports
for the same `(problem, adapter, provider, model)` cell.

Published from `docs/reports/*.json`. Rebuilt by `python -m benchmark report`.
Newer experiments appear first.

## By task

### `task_manager`

| Agent | Provider | Model | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|----------|-------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | opencode_auth | x-preview-f-free | baseline | 1 | 15/15 | 4 | $0.00 | 96.1m | 3533 | 3922 | 7 | 827 |

### `realworld`

| Agent | Provider | Model | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|----------|-------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | opencode_auth | x-preview-f-free | baseline | 1 | 14/14 | 0 | $0.00 | 37.5m | 976 | 1053 | 5 | 197 |

## By model

### `x-preview-f-free`

| Problem | Agent | Provider | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| task_manager | opencode | opencode_auth | baseline | 1 | 15/15 | 4 | $0.00 | 96.1m | 3533 | 3922 | 7 | 827 |
| realworld | opencode | opencode_auth | baseline | 1 | 14/14 | 0 | $0.00 | 37.5m | 976 | 1053 | 5 | 197 |

## Experiments

| Experiment | Date | Problem | Agent | Provider | Model | N | Report |
|------------|------|---------|-------|----------|-------|---|--------|
| hc-opencode-oxalpha-high | 2026-08-21 | healthchecks | opencode | opencode_auth | x-preview-f-free | 0+0 | [short](reports/hc-opencode-oxalpha-high.md) |
| tm-opencode-oxalpha-high | 2026-08-21 | task_manager | opencode | opencode_auth | x-preview-f-free | 1 | [short](reports/tm-opencode-oxalpha-high.md) |
| rw-opencode-oxalpha-high | 2026-08-21 | realworld | opencode | opencode_auth | x-preview-f-free | 1 | [short](reports/rw-opencode-oxalpha-high.md) |

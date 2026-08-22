# Leaderboard

No single score. Absolute metrics only. Δ vs baseline is only in short reports
for the same `(problem, adapter, provider, model)` cell.

Published from `docs/reports/*.json`. Rebuilt by `python -m benchmark report`.
Newer experiments appear first.

## By task

### `realworld`

| Agent | Provider | Model | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|----------|-------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | opencode_auth | x-preview-f-free | doorstop | 1 | 14/14 | 0 | $0.00 | 49.5m | 727 | 975 | 5 | 185 |
| opencode | opencode_auth | x-preview-f-free | graphify | 1 | 14/14 | 0 | $0.00 | 40.0m | 997 | 1380 | 5 | 178 |
| opencode | opencode_auth | x-preview-f-free | ponytail | 1 | 13/14 | 0 | $0.00 | 27.9m | 495 | 484 | 5 | 118 |
| opencode | opencode_auth | x-preview-f-free | strictdoc | 1 | 14/14 | 0 | $0.00 | 57.3m | 857 | 1102 | 5 | 192 |
| opencode | opencode_auth | x-preview-f-free | supermemory | 1 | 14/14 | 0 | $0.00 | 33.2m | 1032 | 1138 | 22 | 211 |
| opencode | opencode_auth | x-preview-f-free | tdd | 1 | 14/14 | 0 | $0.00 | 31.6m | 2613 | 2862 | 7 | 821 |
| opencode | opencode_auth | x-preview-f-free | thermo-nuclear-code-quality-review | 1 | 6/14 | 0 | $0.00 | 71.0m | 640 | 287 | 6 | 101 |
| opencode | opencode_auth | x-preview-f-free | baseline | 1 | 14/14 | 0 | $0.00 | 37.5m | 976 | 1053 | 5 | 197 |

### `task_manager`

| Agent | Provider | Model | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|----------|-------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | opencode_auth | x-preview-f-free | baseline | 1 | 15/15 | 4 | $0.00 | 96.1m | 3533 | 3922 | 7 | 827 |

## By model

### `x-preview-f-free`

| Problem | Agent | Provider | Harness | N | CP | Reg | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|--:|--:|----:|-----:|-----:|----:|-----:|-----:|---:|
| realworld | opencode | opencode_auth | doorstop | 1 | 14/14 | 0 | $0.00 | 49.5m | 727 | 975 | 5 | 185 |
| realworld | opencode | opencode_auth | graphify | 1 | 14/14 | 0 | $0.00 | 40.0m | 997 | 1380 | 5 | 178 |
| realworld | opencode | opencode_auth | ponytail | 1 | 13/14 | 0 | $0.00 | 27.9m | 495 | 484 | 5 | 118 |
| realworld | opencode | opencode_auth | strictdoc | 1 | 14/14 | 0 | $0.00 | 57.3m | 857 | 1102 | 5 | 192 |
| realworld | opencode | opencode_auth | supermemory | 1 | 14/14 | 0 | $0.00 | 33.2m | 1032 | 1138 | 22 | 211 |
| realworld | opencode | opencode_auth | tdd | 1 | 14/14 | 0 | $0.00 | 31.6m | 2613 | 2862 | 7 | 821 |
| realworld | opencode | opencode_auth | thermo-nuclear-code-quality-review | 1 | 6/14 | 0 | $0.00 | 71.0m | 640 | 287 | 6 | 101 |
| task_manager | opencode | opencode_auth | baseline | 1 | 15/15 | 4 | $0.00 | 96.1m | 3533 | 3922 | 7 | 827 |
| realworld | opencode | opencode_auth | baseline | 1 | 14/14 | 0 | $0.00 | 37.5m | 976 | 1053 | 5 | 197 |

## Experiments

| Experiment | Date | Problem | Agent | Provider | Model | N | Report |
|------------|------|---------|-------|----------|-------|---|--------|
| realworld-opencode-x-preview-f-free-high-20260821-1928 | 2026-08-21 | realworld | opencode | opencode_auth | x-preview-f-free | 1+1+1+1+1+1+1 | [short](reports/realworld-opencode-x-preview-f-free-high-20260821-1928.md) |
| hc-opencode-oxalpha-high | 2026-08-21 | healthchecks | opencode | opencode_auth | x-preview-f-free | 0+0 | [short](reports/hc-opencode-oxalpha-high.md) |
| tm-opencode-oxalpha-high | 2026-08-21 | task_manager | opencode | opencode_auth | x-preview-f-free | 1 | [short](reports/tm-opencode-oxalpha-high.md) |
| rw-opencode-oxalpha-high | 2026-08-21 | realworld | opencode | opencode_auth | x-preview-f-free | 1 | [short](reports/rw-opencode-oxalpha-high.md) |

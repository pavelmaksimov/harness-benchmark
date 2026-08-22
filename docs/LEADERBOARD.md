# Leaderboard

No single score. Absolute metrics only. Δ vs baseline is only in short reports
for the same `(problem, adapter, provider, model)` cell.

Published from `docs/reports/*.json`. Rebuilt by `python -m benchmark report`.
Newer experiments appear first.
Create/Rework token columns use per-attempt usage; `-` means it is unavailable.
All in/out columns preserve the aggregate usage for older runs.
Failed CP counts checkpoints that failed at least once, including repaired ones.
Rework in/out is calculated as All in/out minus Create in/out when possible.

## By task

### `realworld`

| Agent | Model | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | All in | All out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|--------:|---------:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | x-preview-f-free | doorstop | 1 | 14/14 | 2 | 3 | 0 | - | - | - | - | 383,992 | 53,534 | $0.00 | 49.5m | 727 | 975 | 5 | 185 |
| opencode | x-preview-f-free | graphify | 1 | 14/14 | 1 | 1 | 0 | - | - | - | - | 591,912 | 45,805 | $0.00 | 40.0m | 997 | 1380 | 5 | 178 |
| opencode | x-preview-f-free | ponytail | 1 | 13/14 | 2 | 4 | 0 | - | - | - | - | 294,683 | 25,333 | $0.00 | 27.9m | 495 | 484 | 5 | 118 |
| opencode | x-preview-f-free | strictdoc | 1 | 14/14 | 5 | 8 | 0 | - | - | - | - | 431,917 | 59,943 | $0.00 | 57.3m | 857 | 1102 | 5 | 192 |
| opencode | x-preview-f-free | supermemory | 1 | 14/14 | 1 | 2 | 0 | - | - | - | - | 473,208 | 48,053 | $0.00 | 33.2m | 1032 | 1138 | 22 | 211 |
| opencode | x-preview-f-free | tdd | 1 | 14/14 | 2 | 3 | 0 | - | - | - | - | 302,511 | 40,629 | $0.00 | 31.6m | 2613 | 2862 | 7 | 821 |
| opencode | x-preview-f-free | thermo-nuclear-code-quality-review | 1 | 6/14 | 10 | 27 | 0 | - | - | - | - | 389,073 | 69,573 | $0.00 | 71.0m | 640 | 287 | 6 | 101 |
| opencode | x-preview-f-free | baseline | 1 | 14/14 | 3 | 3 | 0 | - | - | - | - | 250,689 | 42,406 | $0.00 | 37.5m | 976 | 1053 | 5 | 197 |

### `task_manager`

| Agent | Model | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | All in | All out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|--------:|---------:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | x-preview-f-free | baseline | 1 | 15/15 | 7 | 8 | 4 | - | - | - | - | 614,233 | 149,797 | $0.00 | 96.1m | 3533 | 3922 | 7 | 827 |

## By model

### `x-preview-f-free`

| Problem | Agent | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | All in | All out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|--------:|---------:|-----:|-----:|----:|-----:|-----:|---:|
| realworld | opencode | doorstop | 1 | 14/14 | 2 | 3 | 0 | - | - | - | - | 383,992 | 53,534 | $0.00 | 49.5m | 727 | 975 | 5 | 185 |
| realworld | opencode | graphify | 1 | 14/14 | 1 | 1 | 0 | - | - | - | - | 591,912 | 45,805 | $0.00 | 40.0m | 997 | 1380 | 5 | 178 |
| realworld | opencode | ponytail | 1 | 13/14 | 2 | 4 | 0 | - | - | - | - | 294,683 | 25,333 | $0.00 | 27.9m | 495 | 484 | 5 | 118 |
| realworld | opencode | strictdoc | 1 | 14/14 | 5 | 8 | 0 | - | - | - | - | 431,917 | 59,943 | $0.00 | 57.3m | 857 | 1102 | 5 | 192 |
| realworld | opencode | supermemory | 1 | 14/14 | 1 | 2 | 0 | - | - | - | - | 473,208 | 48,053 | $0.00 | 33.2m | 1032 | 1138 | 22 | 211 |
| realworld | opencode | tdd | 1 | 14/14 | 2 | 3 | 0 | - | - | - | - | 302,511 | 40,629 | $0.00 | 31.6m | 2613 | 2862 | 7 | 821 |
| realworld | opencode | thermo-nuclear-code-quality-review | 1 | 6/14 | 10 | 27 | 0 | - | - | - | - | 389,073 | 69,573 | $0.00 | 71.0m | 640 | 287 | 6 | 101 |
| task_manager | opencode | baseline | 1 | 15/15 | 7 | 8 | 4 | - | - | - | - | 614,233 | 149,797 | $0.00 | 96.1m | 3533 | 3922 | 7 | 827 |
| realworld | opencode | baseline | 1 | 14/14 | 3 | 3 | 0 | - | - | - | - | 250,689 | 42,406 | $0.00 | 37.5m | 976 | 1053 | 5 | 197 |

## Experiments

| Experiment | Date | Problem | Agent | Model | N | Report |
|------------|------|---------|-------|-------|---|--------|
| realworld-opencode-x-preview-f-free-high-20260821-1928 | 2026-08-21 | realworld | opencode | x-preview-f-free | 1+1+1+1+1+1+1 | [short](reports/realworld-opencode-x-preview-f-free-high-20260821-1928.md) |
| hc-opencode-oxalpha-high | 2026-08-21 | healthchecks | opencode | x-preview-f-free | 0+0 | [short](reports/hc-opencode-oxalpha-high.md) |
| tm-opencode-oxalpha-high | 2026-08-21 | task_manager | opencode | x-preview-f-free | 1 | [short](reports/tm-opencode-oxalpha-high.md) |
| rw-opencode-oxalpha-high | 2026-08-21 | realworld | opencode | x-preview-f-free | 1 | [short](reports/rw-opencode-oxalpha-high.md) |

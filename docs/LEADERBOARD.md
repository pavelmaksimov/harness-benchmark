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

### `task_manager`

| Agent | Model | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | Transient in | Transient out | Trunc | Tr. retry | Recovery | Unresolved | All in | All out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|------------:|-------------:|-----:|----------:|---------:|----------:|--------:|---------:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | x-preview-f-free | baseline | 2 | 15/15 | 0.5 | 0.5 | 0.5 | 900,910 | 202,798 | 10,562 | 2,472 | 0 | 0 | 0 | 0 | 0 | 0 | 911,472 | 205,270 | $0.00 | 275.3m | 5263.5 | 6646.5 | 5 | 984 |

### `realworld`

| Agent | Model | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | Transient in | Transient out | Trunc | Tr. retry | Recovery | Unresolved | All in | All out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|------------:|-------------:|-----:|----------:|---------:|----------:|--------:|---------:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | x-preview-f-free | combo-supermemory-graphify | 1 | 14/14 | 2 | 3 | 0 | 366,900 | 47,075 | 49,295 | 9,531 | 0 | 0 | 0 | 0 | 0 | 0 | 416,195 | 56,606 | $0.00 | 61.9m | 1092 | 1220 | 5 | 227 |
| opencode | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 | 14/14 | 0 | 0 | 0 | 296,812 | 44,506 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 296,812 | 44,506 | $0.00 | 48.3m | 868 | 1147 | 5 | 251 |
| opencode | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1 | 13/14 | 3 | 6 | 0 | 706,788 | 59,699 | 309,366 | 39,710 | 0 | 0 | 0 | 0 | 0 | 0 | 1,016,154 | 99,409 | $0.00 | 161.6m | 1861 | 1832 | 4 | 653 |
| opencode | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1 | 14/14 | 1 | 1 | 0 | 446,258 | 40,607 | 47,037 | 1,843 | 0 | 0 | 0 | 0 | 0 | 0 | 493,295 | 42,450 | $0.00 | 58.1m | 1870 | 2276 | 6 | 636 |
| opencode | x-preview-f-free | doorstop | 1 | 14/14 | 2 | 3 | 0 | - | - | - | - | - | - | - | - | - | - | 383,992 | 53,534 | $0.00 | 49.5m | 727 | 975 | 5 | 185 |
| opencode | x-preview-f-free | graphify | 1 | 14/14 | 1 | 1 | 0 | - | - | - | - | - | - | - | - | - | - | 591,912 | 45,805 | $0.00 | 40.0m | 997 | 1380 | 5 | 178 |
| opencode | x-preview-f-free | ponytail | 1 | 13/14 | 2 | 4 | 0 | - | - | - | - | - | - | - | - | - | - | 294,683 | 25,333 | $0.00 | 27.9m | 495 | 484 | 5 | 118 |
| opencode | x-preview-f-free | strictdoc | 1 | 14/14 | 5 | 8 | 0 | - | - | - | - | - | - | - | - | - | - | 431,917 | 59,943 | $0.00 | 57.3m | 857 | 1102 | 5 | 192 |
| opencode | x-preview-f-free | supermemory | 1 | 14/14 | 1 | 2 | 0 | - | - | - | - | - | - | - | - | - | - | 473,208 | 48,053 | $0.00 | 33.2m | 1032 | 1138 | 22 | 211 |
| opencode | x-preview-f-free | tdd | 1 | 14/14 | 2 | 3 | 0 | - | - | - | - | - | - | - | - | - | - | 302,511 | 40,629 | $0.00 | 31.6m | 2613 | 2862 | 7 | 821 |
| opencode | x-preview-f-free | thermo-nuclear-code-quality-review | 1 | 6/14 | 10 | 27 | 0 | - | - | - | - | - | - | - | - | - | - | 389,073 | 69,573 | $0.00 | 71.0m | 640 | 287 | 6 | 101 |
| opencode | x-preview-f-free | baseline | 1 | 14/14 | 3 | 3 | 0 | - | - | - | - | - | - | - | - | - | - | 250,689 | 42,406 | $0.00 | 37.5m | 976 | 1053 | 5 | 197 |

## By model

### `x-preview-f-free`

| Problem | Agent | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | Transient in | Transient out | Trunc | Tr. retry | Recovery | Unresolved | All in | All out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|------------:|-------------:|-----:|----------:|---------:|----------:|--------:|---------:|-----:|-----:|----:|-----:|-----:|---:|
| task_manager | opencode | baseline | 2 | 15/15 | 0.5 | 0.5 | 0.5 | 900,910 | 202,798 | 10,562 | 2,472 | 0 | 0 | 0 | 0 | 0 | 0 | 911,472 | 205,270 | $0.00 | 275.3m | 5263.5 | 6646.5 | 5 | 984 |
| realworld | opencode | combo-supermemory-graphify | 1 | 14/14 | 2 | 3 | 0 | 366,900 | 47,075 | 49,295 | 9,531 | 0 | 0 | 0 | 0 | 0 | 0 | 416,195 | 56,606 | $0.00 | 61.9m | 1092 | 1220 | 5 | 227 |
| realworld | opencode | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 | 14/14 | 0 | 0 | 0 | 296,812 | 44,506 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 296,812 | 44,506 | $0.00 | 48.3m | 868 | 1147 | 5 | 251 |
| realworld | opencode | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1 | 13/14 | 3 | 6 | 0 | 706,788 | 59,699 | 309,366 | 39,710 | 0 | 0 | 0 | 0 | 0 | 0 | 1,016,154 | 99,409 | $0.00 | 161.6m | 1861 | 1832 | 4 | 653 |
| realworld | opencode | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1 | 14/14 | 1 | 1 | 0 | 446,258 | 40,607 | 47,037 | 1,843 | 0 | 0 | 0 | 0 | 0 | 0 | 493,295 | 42,450 | $0.00 | 58.1m | 1870 | 2276 | 6 | 636 |
| realworld | opencode | doorstop | 1 | 14/14 | 2 | 3 | 0 | - | - | - | - | - | - | - | - | - | - | 383,992 | 53,534 | $0.00 | 49.5m | 727 | 975 | 5 | 185 |
| realworld | opencode | graphify | 1 | 14/14 | 1 | 1 | 0 | - | - | - | - | - | - | - | - | - | - | 591,912 | 45,805 | $0.00 | 40.0m | 997 | 1380 | 5 | 178 |
| realworld | opencode | ponytail | 1 | 13/14 | 2 | 4 | 0 | - | - | - | - | - | - | - | - | - | - | 294,683 | 25,333 | $0.00 | 27.9m | 495 | 484 | 5 | 118 |
| realworld | opencode | strictdoc | 1 | 14/14 | 5 | 8 | 0 | - | - | - | - | - | - | - | - | - | - | 431,917 | 59,943 | $0.00 | 57.3m | 857 | 1102 | 5 | 192 |
| realworld | opencode | supermemory | 1 | 14/14 | 1 | 2 | 0 | - | - | - | - | - | - | - | - | - | - | 473,208 | 48,053 | $0.00 | 33.2m | 1032 | 1138 | 22 | 211 |
| realworld | opencode | tdd | 1 | 14/14 | 2 | 3 | 0 | - | - | - | - | - | - | - | - | - | - | 302,511 | 40,629 | $0.00 | 31.6m | 2613 | 2862 | 7 | 821 |
| realworld | opencode | thermo-nuclear-code-quality-review | 1 | 6/14 | 10 | 27 | 0 | - | - | - | - | - | - | - | - | - | - | 389,073 | 69,573 | $0.00 | 71.0m | 640 | 287 | 6 | 101 |
| realworld | opencode | baseline | 1 | 14/14 | 3 | 3 | 0 | - | - | - | - | - | - | - | - | - | - | 250,689 | 42,406 | $0.00 | 37.5m | 976 | 1053 | 5 | 197 |

## Experiments

| Experiment | Date | Problem | Agent | Model | N | Report |
|------------|------|---------|-------|-------|---|--------|
| pilot-feedback-v1-task_manager-20260822 | 2026-08-22 | task_manager | opencode | x-preview-f-free | 2 | [short](reports/pilot-feedback-v1-task_manager-20260822.md) |
| realworld-opencode-x-preview-f-free-high-combinations-20260822 | 2026-08-22 | realworld | opencode | x-preview-f-free | 1+1+1+1 | [short](reports/realworld-opencode-x-preview-f-free-high-combinations-20260822.md) |
| realworld-opencode-x-preview-f-free-high-20260821-1928 | 2026-08-21 | realworld | opencode | x-preview-f-free | 1+1+1+1+1+1+1 | [short](reports/realworld-opencode-x-preview-f-free-high-20260821-1928.md) |
| hc-opencode-oxalpha-high | 2026-08-21 | healthchecks | opencode | x-preview-f-free | 0+0 | [short](reports/hc-opencode-oxalpha-high.md) |
| tm-opencode-oxalpha-high | 2026-08-21 | task_manager | opencode | x-preview-f-free | 1 | [short](reports/tm-opencode-oxalpha-high.md) |
| rw-opencode-oxalpha-high | 2026-08-21 | realworld | opencode | x-preview-f-free | 1 | [short](reports/rw-opencode-oxalpha-high.md) |

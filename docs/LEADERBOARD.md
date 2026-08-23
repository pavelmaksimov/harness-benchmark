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

| Agent | Model | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | Transient in | Transient out | Trunc | Tr. retry | Recovery | Unresolved | All in | All out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|------------:|-------------:|-----:|----------:|---------:|----------:|--------:|---------:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | x-preview-f-free | baseline | 1 | 14/14 | 0 | 0 | 0 | 261,474 | 39,124 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 261,474 | 39,124 | $0.00 | 58.2m | 905 | 1169 | 6 | 222 |
| opencode | x-preview-f-free | combo-supermemory-graphify | 1 | 14/14 | 2 | 2 | 0 | 389,947 | 62,963 | 48,615 | 7,593 | 0 | 0 | 0 | 0 | 0 | 0 | 438,562 | 70,556 | $0.00 | 88.7m | 1096 | 909 | 7 | 229 |
| opencode | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 | 14/14 | 2 | 2 | 0 | 286,932 | 40,490 | 25,102 | 6,783 | 0 | 0 | 0 | 0 | 0 | 0 | 312,034 | 47,273 | $0.00 | 60.8m | 968 | 945 | 5 | 245 |
| opencode | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1 | 14/14 | 2 | 2 | 0 | 317,407 | 53,728 | 33,752 | 4,320 | 0 | 0 | 0 | 0 | 0 | 0 | 351,159 | 58,048 | $0.00 | 59.7m | 1620 | 1726 | 6 | 606 |
| opencode | x-preview-f-free | doorstop | 1 | 14/14 | 1 | 1 | 0 | 333,660 | 66,256 | 19,770 | 3,926 | 0 | 0 | 0 | 0 | 0 | 0 | 353,430 | 70,182 | $0.00 | 95.4m | 2123 | 2371 | 6 | 570 |
| opencode | x-preview-f-free | graphify | 1 | 14/14 | 1 | 1 | 0 | 484,474 | 59,561 | 12,504 | 1,964 | 0 | 0 | 0 | 0 | 0 | 0 | 496,978 | 61,525 | $0.00 | 99.5m | 869 | 963 | 6 | 179 |
| opencode | x-preview-f-free | ponytail | 1 | 14/14 | 2 | 2 | 0 | 234,726 | 29,180 | 27,967 | 4,879 | 0 | 0 | 0 | 0 | 0 | 0 | 262,693 | 34,059 | $0.00 | 34.2m | 729 | 752 | 25 | 168 |
| opencode | x-preview-f-free | strictdoc | 1 | 14/14 | 0 | 0 | 0 | 398,588 | 62,940 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 398,588 | 62,940 | $0.00 | 72.9m | 884 | 1147 | 6 | 210 |
| opencode | x-preview-f-free | supermemory | 1 | 14/14 | 2 | 3 | 0 | 270,951 | 55,271 | 48,913 | 12,466 | 0 | 0 | 0 | 0 | 0 | 0 | 319,864 | 67,737 | $0.00 | 61.3m | 1125 | 1169 | 7 | 204 |
| opencode | x-preview-f-free | tdd | 1 | 14/14 | 2 | 2 | 0 | 275,550 | 43,670 | 30,196 | 4,356 | 0 | 0 | 0 | 0 | 0 | 0 | 305,746 | 48,026 | $0.00 | 55.4m | 2460 | 2732 | 30 | 676 |
| opencode | x-preview-f-free | thermo-nuclear-code-quality-review | 1 | 13/14 | 3 | 4 | 0 | 380,970 | 62,509 | 90,941 | 18,577 | 0 | 0 | 0 | 0 | 0 | 0 | 471,911 | 81,086 | $0.00 | 96.0m | 747 | 724 | 6 | 131 |
| opencode | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1 | 13/14 | 3 | 6 | 0 | 706,788 | 59,699 | 309,366 | 39,710 | 0 | 0 | 0 | 0 | 0 | 0 | 1,016,154 | 99,409 | $0.00 | 161.6m | 1861 | 1832 | 4 | 653 |

### `task_manager`

| Agent | Model | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | Transient in | Transient out | Trunc | Tr. retry | Recovery | Unresolved | All in | All out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|------------:|-------------:|-----:|----------:|---------:|----------:|--------:|---------:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | x-preview-f-free | baseline | 2 | 15/15 | 0.5 | 0.5 | 0.5 | 900,910 | 202,798 | 10,562 | 2,472 | 0 | 0 | 0 | 0 | 0 | 0 | 911,472 | 205,270 | $0.00 | 275.3m | 5263.5 | 6646.5 | 5 | 984 |

## By model

### `x-preview-f-free`

| Problem | Agent | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | Transient in | Transient out | Trunc | Tr. retry | Recovery | Unresolved | All in | All out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|------------:|-------------:|-----:|----------:|---------:|----------:|--------:|---------:|-----:|-----:|----:|-----:|-----:|---:|
| realworld | opencode | baseline | 1 | 14/14 | 0 | 0 | 0 | 261,474 | 39,124 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 261,474 | 39,124 | $0.00 | 58.2m | 905 | 1169 | 6 | 222 |
| realworld | opencode | combo-supermemory-graphify | 1 | 14/14 | 2 | 2 | 0 | 389,947 | 62,963 | 48,615 | 7,593 | 0 | 0 | 0 | 0 | 0 | 0 | 438,562 | 70,556 | $0.00 | 88.7m | 1096 | 909 | 7 | 229 |
| realworld | opencode | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 | 14/14 | 2 | 2 | 0 | 286,932 | 40,490 | 25,102 | 6,783 | 0 | 0 | 0 | 0 | 0 | 0 | 312,034 | 47,273 | $0.00 | 60.8m | 968 | 945 | 5 | 245 |
| realworld | opencode | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1 | 14/14 | 2 | 2 | 0 | 317,407 | 53,728 | 33,752 | 4,320 | 0 | 0 | 0 | 0 | 0 | 0 | 351,159 | 58,048 | $0.00 | 59.7m | 1620 | 1726 | 6 | 606 |
| realworld | opencode | doorstop | 1 | 14/14 | 1 | 1 | 0 | 333,660 | 66,256 | 19,770 | 3,926 | 0 | 0 | 0 | 0 | 0 | 0 | 353,430 | 70,182 | $0.00 | 95.4m | 2123 | 2371 | 6 | 570 |
| realworld | opencode | graphify | 1 | 14/14 | 1 | 1 | 0 | 484,474 | 59,561 | 12,504 | 1,964 | 0 | 0 | 0 | 0 | 0 | 0 | 496,978 | 61,525 | $0.00 | 99.5m | 869 | 963 | 6 | 179 |
| realworld | opencode | ponytail | 1 | 14/14 | 2 | 2 | 0 | 234,726 | 29,180 | 27,967 | 4,879 | 0 | 0 | 0 | 0 | 0 | 0 | 262,693 | 34,059 | $0.00 | 34.2m | 729 | 752 | 25 | 168 |
| realworld | opencode | strictdoc | 1 | 14/14 | 0 | 0 | 0 | 398,588 | 62,940 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 398,588 | 62,940 | $0.00 | 72.9m | 884 | 1147 | 6 | 210 |
| realworld | opencode | supermemory | 1 | 14/14 | 2 | 3 | 0 | 270,951 | 55,271 | 48,913 | 12,466 | 0 | 0 | 0 | 0 | 0 | 0 | 319,864 | 67,737 | $0.00 | 61.3m | 1125 | 1169 | 7 | 204 |
| realworld | opencode | tdd | 1 | 14/14 | 2 | 2 | 0 | 275,550 | 43,670 | 30,196 | 4,356 | 0 | 0 | 0 | 0 | 0 | 0 | 305,746 | 48,026 | $0.00 | 55.4m | 2460 | 2732 | 30 | 676 |
| realworld | opencode | thermo-nuclear-code-quality-review | 1 | 13/14 | 3 | 4 | 0 | 380,970 | 62,509 | 90,941 | 18,577 | 0 | 0 | 0 | 0 | 0 | 0 | 471,911 | 81,086 | $0.00 | 96.0m | 747 | 724 | 6 | 131 |
| task_manager | opencode | baseline | 2 | 15/15 | 0.5 | 0.5 | 0.5 | 900,910 | 202,798 | 10,562 | 2,472 | 0 | 0 | 0 | 0 | 0 | 0 | 911,472 | 205,270 | $0.00 | 275.3m | 5263.5 | 6646.5 | 5 | 984 |
| realworld | opencode | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1 | 13/14 | 3 | 6 | 0 | 706,788 | 59,699 | 309,366 | 39,710 | 0 | 0 | 0 | 0 | 0 | 0 | 1,016,154 | 99,409 | $0.00 | 161.6m | 1861 | 1832 | 4 | 653 |

## Experiments

| Experiment | Date | Problem | Agent | Model | N | Report |
|------------|------|---------|-------|-------|---|--------|
| realworld-opencode-x-preview-f-free-high-all-20260822-1838 | 2026-08-22 | realworld | opencode | x-preview-f-free | 1+1+1+1+1+1+1+1+1+1+1 | [short](reports/realworld-opencode-x-preview-f-free-high-all-20260822-1838.md) |
| pilot-feedback-v1-task_manager-20260822 | 2026-08-22 | task_manager | opencode | x-preview-f-free | 2 | [short](reports/pilot-feedback-v1-task_manager-20260822.md) |
| realworld-opencode-x-preview-f-free-high-combinations-20260822 | 2026-08-22 | realworld | opencode | x-preview-f-free | 1+1+1+1 | [short](reports/realworld-opencode-x-preview-f-free-high-combinations-20260822.md) |
| realworld-opencode-x-preview-f-free-high-20260821-1928 | 2026-08-21 | realworld | opencode | x-preview-f-free | 1+1+1+1+1+1+1 | [short](reports/realworld-opencode-x-preview-f-free-high-20260821-1928.md) |
| hc-opencode-oxalpha-high | 2026-08-21 | healthchecks | opencode | x-preview-f-free | 0+0 | [short](reports/hc-opencode-oxalpha-high.md) |
| tm-opencode-oxalpha-high | 2026-08-21 | task_manager | opencode | x-preview-f-free | 1 | [short](reports/tm-opencode-oxalpha-high.md) |
| rw-opencode-oxalpha-high | 2026-08-21 | realworld | opencode | x-preview-f-free | 1 | [short](reports/rw-opencode-oxalpha-high.md) |

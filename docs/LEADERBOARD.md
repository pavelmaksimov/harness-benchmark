# Leaderboard

No single score. Absolute metrics only. Δ vs baseline is only in short reports
for the same `(problem, adapter, provider, model)` cell.

Published from `docs/reports/*.json`. Rebuilt by `python -m benchmark report`.
Newer experiments appear first.
Create/Rework token columns use per-attempt usage; `-` means it is unavailable.
Failed CP counts checkpoints that failed at least once, including repaired ones.

## By task

### `realworld`

| Agent | Model | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | x-preview-f-free | baseline | 1 | 14/14 | 0 | 0 | 0 | 261,474 | 39,124 | 0 | 0 | $0.00 | 58.2m | 905 | 1169 | 6 | 222 |
| opencode | x-preview-f-free | combo-supermemory-graphify | 1 | 14/14 | 2 | 2 | 0 | 389,947 | 62,963 | 48,615 | 7,593 | $0.00 | 88.7m | 1096 | 909 | 7 | 229 |
| opencode | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 | 14/14 | 2 | 2 | 0 | 286,932 | 40,490 | 25,102 | 6,783 | $0.00 | 60.8m | 968 | 945 | 5 | 245 |
| opencode | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1 | 14/14 | 2 | 2 | 0 | 317,407 | 53,728 | 33,752 | 4,320 | $0.00 | 59.7m | 1620 | 1726 | 6 | 606 |
| opencode | x-preview-f-free | doorstop | 1 | 14/14 | 1 | 1 | 0 | 333,660 | 66,256 | 19,770 | 3,926 | $0.00 | 95.4m | 2123 | 2371 | 6 | 570 |
| opencode | x-preview-f-free | graphify | 1 | 14/14 | 1 | 1 | 0 | 484,474 | 59,561 | 12,504 | 1,964 | $0.00 | 99.5m | 869 | 963 | 6 | 179 |
| opencode | x-preview-f-free | ponytail | 1 | 14/14 | 2 | 2 | 0 | 234,726 | 29,180 | 27,967 | 4,879 | $0.00 | 34.2m | 729 | 752 | 25 | 168 |
| opencode | x-preview-f-free | strictdoc | 1 | 14/14 | 0 | 0 | 0 | 398,588 | 62,940 | 0 | 0 | $0.00 | 72.9m | 884 | 1147 | 6 | 210 |
| opencode | x-preview-f-free | supermemory | 1 | 14/14 | 2 | 3 | 0 | 270,951 | 55,271 | 48,913 | 12,466 | $0.00 | 61.3m | 1125 | 1169 | 7 | 204 |
| opencode | x-preview-f-free | tdd | 1 | 14/14 | 2 | 2 | 0 | 275,550 | 43,670 | 30,196 | 4,356 | $0.00 | 55.4m | 2460 | 2732 | 30 | 676 |
| opencode | x-preview-f-free | thermo-nuclear-code-quality-review | 1 | 13/14 | 3 | 4 | 0 | 380,970 | 62,509 | 90,941 | 18,577 | $0.00 | 96.0m | 747 | 724 | 6 | 131 |
| opencode | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1 | 13/14 | 3 | 6 | 0 | 706,788 | 59,699 | 309,366 | 39,710 | $0.00 | 161.6m | 1861 | 1832 | 4 | 653 |

### `task_manager`

| Agent | Model | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | x-preview-f-free | baseline | 2 | 15/15 | 0.5 | 0.5 | 0.5 | 900,910 | 202,798 | 10,562 | 2,472 | $0.00 | 275.3m | 5263.5 | 6646.5 | 5 | 984 |

## By model

### `x-preview-f-free`

| Problem | Agent | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-----:|-----:|----:|-----:|-----:|---:|
| realworld | opencode | baseline | 1 | 14/14 | 0 | 0 | 0 | 261,474 | 39,124 | 0 | 0 | $0.00 | 58.2m | 905 | 1169 | 6 | 222 |
| realworld | opencode | combo-supermemory-graphify | 1 | 14/14 | 2 | 2 | 0 | 389,947 | 62,963 | 48,615 | 7,593 | $0.00 | 88.7m | 1096 | 909 | 7 | 229 |
| realworld | opencode | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 | 14/14 | 2 | 2 | 0 | 286,932 | 40,490 | 25,102 | 6,783 | $0.00 | 60.8m | 968 | 945 | 5 | 245 |
| realworld | opencode | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1 | 14/14 | 2 | 2 | 0 | 317,407 | 53,728 | 33,752 | 4,320 | $0.00 | 59.7m | 1620 | 1726 | 6 | 606 |
| realworld | opencode | doorstop | 1 | 14/14 | 1 | 1 | 0 | 333,660 | 66,256 | 19,770 | 3,926 | $0.00 | 95.4m | 2123 | 2371 | 6 | 570 |
| realworld | opencode | graphify | 1 | 14/14 | 1 | 1 | 0 | 484,474 | 59,561 | 12,504 | 1,964 | $0.00 | 99.5m | 869 | 963 | 6 | 179 |
| realworld | opencode | ponytail | 1 | 14/14 | 2 | 2 | 0 | 234,726 | 29,180 | 27,967 | 4,879 | $0.00 | 34.2m | 729 | 752 | 25 | 168 |
| realworld | opencode | strictdoc | 1 | 14/14 | 0 | 0 | 0 | 398,588 | 62,940 | 0 | 0 | $0.00 | 72.9m | 884 | 1147 | 6 | 210 |
| realworld | opencode | supermemory | 1 | 14/14 | 2 | 3 | 0 | 270,951 | 55,271 | 48,913 | 12,466 | $0.00 | 61.3m | 1125 | 1169 | 7 | 204 |
| realworld | opencode | tdd | 1 | 14/14 | 2 | 2 | 0 | 275,550 | 43,670 | 30,196 | 4,356 | $0.00 | 55.4m | 2460 | 2732 | 30 | 676 |
| realworld | opencode | thermo-nuclear-code-quality-review | 1 | 13/14 | 3 | 4 | 0 | 380,970 | 62,509 | 90,941 | 18,577 | $0.00 | 96.0m | 747 | 724 | 6 | 131 |
| task_manager | opencode | baseline | 2 | 15/15 | 0.5 | 0.5 | 0.5 | 900,910 | 202,798 | 10,562 | 2,472 | $0.00 | 275.3m | 5263.5 | 6646.5 | 5 | 984 |
| realworld | opencode | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1 | 13/14 | 3 | 6 | 0 | 706,788 | 59,699 | 309,366 | 39,710 | $0.00 | 161.6m | 1861 | 1832 | 4 | 653 |

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

## Metric leaderboards

Each ranking uses the newest published cell for each `(problem, adapter, provider, model, harness)`.
Values are means when a cell contains multiple runs. Ties are ordered alphabetically.

### CP passed/total

Higher is better. Passed and total checkpoints for the latest published cell.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | task_manager | x-preview-f-free | baseline | 15/15 |
| 2 | realworld | x-preview-f-free | baseline | 14/14 |
| 3 | realworld | x-preview-f-free | combo-supermemory-graphify | 14/14 |
| 4 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 14/14 |
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 14/14 |
| 6 | realworld | x-preview-f-free | doorstop | 14/14 |
| 7 | realworld | x-preview-f-free | graphify | 14/14 |
| 8 | realworld | x-preview-f-free | ponytail | 14/14 |
| 9 | realworld | x-preview-f-free | strictdoc | 14/14 |
| 10 | realworld | x-preview-f-free | supermemory | 14/14 |
| 11 | realworld | x-preview-f-free | tdd | 14/14 |
| 12 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 13/14 |
| 13 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 13/14 |

### Failed checkpoints

Lower is better. Number of checkpoints that failed at least once, including repaired ones.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | baseline | 0 |
| 2 | realworld | x-preview-f-free | strictdoc | 0 |
| 3 | task_manager | x-preview-f-free | baseline | 0.5 |
| 4 | realworld | x-preview-f-free | doorstop | 1 |
| 5 | realworld | x-preview-f-free | graphify | 1 |
| 6 | realworld | x-preview-f-free | combo-supermemory-graphify | 2 |
| 7 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 2 |
| 8 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 2 |
| 9 | realworld | x-preview-f-free | ponytail | 2 |
| 10 | realworld | x-preview-f-free | supermemory | 2 |
| 11 | realworld | x-preview-f-free | tdd | 2 |
| 12 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 3 |
| 13 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 3 |

### Repeated attempts

Lower is better. Additional semantic attempts after the initial attempt.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | baseline | 0 |
| 2 | realworld | x-preview-f-free | strictdoc | 0 |
| 3 | task_manager | x-preview-f-free | baseline | 0.5 |
| 4 | realworld | x-preview-f-free | doorstop | 1 |
| 5 | realworld | x-preview-f-free | graphify | 1 |
| 6 | realworld | x-preview-f-free | combo-supermemory-graphify | 2 |
| 7 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 2 |
| 8 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 2 |
| 9 | realworld | x-preview-f-free | ponytail | 2 |
| 10 | realworld | x-preview-f-free | tdd | 2 |
| 11 | realworld | x-preview-f-free | supermemory | 3 |
| 12 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 4 |
| 13 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 6 |

### Regressions

Lower is better. Regression tests failing in the final checkpoint evaluations.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | baseline | 0 |
| 2 | realworld | x-preview-f-free | combo-supermemory-graphify | 0 |
| 3 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 4 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 6 | realworld | x-preview-f-free | doorstop | 0 |
| 7 | realworld | x-preview-f-free | graphify | 0 |
| 8 | realworld | x-preview-f-free | ponytail | 0 |
| 9 | realworld | x-preview-f-free | strictdoc | 0 |
| 10 | realworld | x-preview-f-free | supermemory | 0 |
| 11 | realworld | x-preview-f-free | tdd | 0 |
| 12 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 0 |
| 13 | task_manager | x-preview-f-free | baseline | 0.5 |

### Creation input tokens

Lower is better. Input tokens used by initial checkpoint attempts.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | ponytail | 234,726 |
| 2 | realworld | x-preview-f-free | baseline | 261,474 |
| 3 | realworld | x-preview-f-free | supermemory | 270,951 |
| 4 | realworld | x-preview-f-free | tdd | 275,550 |
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 286,932 |
| 6 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 317,407 |
| 7 | realworld | x-preview-f-free | doorstop | 333,660 |
| 8 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 380,970 |
| 9 | realworld | x-preview-f-free | combo-supermemory-graphify | 389,947 |
| 10 | realworld | x-preview-f-free | strictdoc | 398,588 |
| 11 | realworld | x-preview-f-free | graphify | 484,474 |
| 12 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 706,788 |
| 13 | task_manager | x-preview-f-free | baseline | 900,910 |

### Creation output tokens

Lower is better. Output tokens used by initial checkpoint attempts.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | ponytail | 29,180 |
| 2 | realworld | x-preview-f-free | baseline | 39,124 |
| 3 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 40,490 |
| 4 | realworld | x-preview-f-free | tdd | 43,670 |
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 53,728 |
| 6 | realworld | x-preview-f-free | supermemory | 55,271 |
| 7 | realworld | x-preview-f-free | graphify | 59,561 |
| 8 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 59,699 |
| 9 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 62,509 |
| 10 | realworld | x-preview-f-free | strictdoc | 62,940 |
| 11 | realworld | x-preview-f-free | combo-supermemory-graphify | 62,963 |
| 12 | realworld | x-preview-f-free | doorstop | 66,256 |
| 13 | task_manager | x-preview-f-free | baseline | 202,798 |

### Rework input tokens

Lower is better. Input tokens used by semantic rework attempts.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | baseline | 0 |
| 2 | realworld | x-preview-f-free | strictdoc | 0 |
| 3 | task_manager | x-preview-f-free | baseline | 10,562 |
| 4 | realworld | x-preview-f-free | graphify | 12,504 |
| 5 | realworld | x-preview-f-free | doorstop | 19,770 |
| 6 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 25,102 |
| 7 | realworld | x-preview-f-free | ponytail | 27,967 |
| 8 | realworld | x-preview-f-free | tdd | 30,196 |
| 9 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 33,752 |
| 10 | realworld | x-preview-f-free | combo-supermemory-graphify | 48,615 |
| 11 | realworld | x-preview-f-free | supermemory | 48,913 |
| 12 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 90,941 |
| 13 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 309,366 |

### Rework output tokens

Lower is better. Output tokens used by semantic rework attempts.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | baseline | 0 |
| 2 | realworld | x-preview-f-free | strictdoc | 0 |
| 3 | realworld | x-preview-f-free | graphify | 1,964 |
| 4 | task_manager | x-preview-f-free | baseline | 2,472 |
| 5 | realworld | x-preview-f-free | doorstop | 3,926 |
| 6 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 4,320 |
| 7 | realworld | x-preview-f-free | tdd | 4,356 |
| 8 | realworld | x-preview-f-free | ponytail | 4,879 |
| 9 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 6,783 |
| 10 | realworld | x-preview-f-free | combo-supermemory-graphify | 7,593 |
| 11 | realworld | x-preview-f-free | supermemory | 12,466 |
| 12 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 18,577 |
| 13 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 39,710 |

### Normalized cost

Lower is better. Cost normalized with the versioned pricing configuration.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | baseline | $0.00 |
| 2 | realworld | x-preview-f-free | combo-supermemory-graphify | $0.00 |
| 3 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | $0.00 |
| 4 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | $0.00 |
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | $0.00 |
| 6 | realworld | x-preview-f-free | doorstop | $0.00 |
| 7 | realworld | x-preview-f-free | graphify | $0.00 |
| 8 | realworld | x-preview-f-free | ponytail | $0.00 |
| 9 | realworld | x-preview-f-free | strictdoc | $0.00 |
| 10 | realworld | x-preview-f-free | supermemory | $0.00 |
| 11 | realworld | x-preview-f-free | tdd | $0.00 |
| 12 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | $0.00 |
| 13 | task_manager | x-preview-f-free | baseline | $0.00 |

### Elapsed time

Lower is better. Sum of agent inference time across checkpoints.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | ponytail | 34.2m |
| 2 | realworld | x-preview-f-free | tdd | 55.4m |
| 3 | realworld | x-preview-f-free | baseline | 58.2m |
| 4 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 59.7m |
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 60.8m |
| 6 | realworld | x-preview-f-free | supermemory | 61.3m |
| 7 | realworld | x-preview-f-free | strictdoc | 72.9m |
| 8 | realworld | x-preview-f-free | combo-supermemory-graphify | 88.7m |
| 9 | realworld | x-preview-f-free | doorstop | 95.4m |
| 10 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 96.0m |
| 11 | realworld | x-preview-f-free | graphify | 99.5m |
| 12 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 161.6m |
| 13 | task_manager | x-preview-f-free | baseline | 275.3m |

### Final LOC

Descriptive. Lines of solution code in the final snapshot.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | ponytail | 729 |
| 2 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 747 |
| 3 | realworld | x-preview-f-free | graphify | 869 |
| 4 | realworld | x-preview-f-free | strictdoc | 884 |
| 5 | realworld | x-preview-f-free | baseline | 905 |
| 6 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 968 |
| 7 | realworld | x-preview-f-free | combo-supermemory-graphify | 1096 |
| 8 | realworld | x-preview-f-free | supermemory | 1125 |
| 9 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1620 |
| 10 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1861 |
| 11 | realworld | x-preview-f-free | doorstop | 2123 |
| 12 | realworld | x-preview-f-free | tdd | 2460 |
| 13 | task_manager | x-preview-f-free | baseline | 5263.5 |

### Changed LOC

Lower is better as a churn measure. Lines changed from the initial snapshot.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 724 |
| 2 | realworld | x-preview-f-free | ponytail | 752 |
| 3 | realworld | x-preview-f-free | combo-supermemory-graphify | 909 |
| 4 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 945 |
| 5 | realworld | x-preview-f-free | graphify | 963 |
| 6 | realworld | x-preview-f-free | strictdoc | 1147 |
| 7 | realworld | x-preview-f-free | baseline | 1169 |
| 8 | realworld | x-preview-f-free | supermemory | 1169 |
| 9 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1726 |
| 10 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1832 |
| 11 | realworld | x-preview-f-free | doorstop | 2371 |
| 12 | realworld | x-preview-f-free | tdd | 2732 |
| 13 | task_manager | x-preview-f-free | baseline | 6646.5 |

### Dependencies

Lower is better as a complexity measure. Dependencies added by the solution.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 4 |
| 2 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 5 |
| 3 | task_manager | x-preview-f-free | baseline | 5 |
| 4 | realworld | x-preview-f-free | baseline | 6 |
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 6 |
| 6 | realworld | x-preview-f-free | doorstop | 6 |
| 7 | realworld | x-preview-f-free | graphify | 6 |
| 8 | realworld | x-preview-f-free | strictdoc | 6 |
| 9 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 6 |
| 10 | realworld | x-preview-f-free | combo-supermemory-graphify | 7 |
| 11 | realworld | x-preview-f-free | supermemory | 7 |
| 12 | realworld | x-preview-f-free | ponytail | 25 |
| 13 | realworld | x-preview-f-free | tdd | 30 |

### Complexity

Lower is better. Measured code complexity in the final snapshot.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 131 |
| 2 | realworld | x-preview-f-free | ponytail | 168 |
| 3 | realworld | x-preview-f-free | graphify | 179 |
| 4 | realworld | x-preview-f-free | supermemory | 204 |
| 5 | realworld | x-preview-f-free | strictdoc | 210 |
| 6 | realworld | x-preview-f-free | baseline | 222 |
| 7 | realworld | x-preview-f-free | combo-supermemory-graphify | 229 |
| 8 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 245 |
| 9 | realworld | x-preview-f-free | doorstop | 570 |
| 10 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 606 |
| 11 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 653 |
| 12 | realworld | x-preview-f-free | tdd | 676 |
| 13 | task_manager | x-preview-f-free | baseline | 984 |

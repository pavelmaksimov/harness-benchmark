# Leaderboard

No single score. Absolute metrics only. Δ vs baseline is only in short reports
for the same `(problem, adapter, provider, model)` cell.

Published from `docs/reports/*.json`. Rebuilt by `python -m benchmark report`.
Experiment reports appear newest first; leaderboard rows aggregate all compatible published runs.
Create/Rework token columns use per-attempt usage; `-` means it is unavailable.
Failed CP counts checkpoints that failed at least once, including repaired ones.

## By task

### `realworld`

| Agent | Model | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | x-preview-f-free | baseline | 2 | 14/14 | 1.5 | 1.5 | 0 | 261,474 | 39,124 | 0 | 0 | $0.00 | 47.8m | 940.5 | 1111 | 5.5 | 209.5 |
| opencode | x-preview-f-free | combo-supermemory-graphify | 2 | 14/14 | 2 | 2.5 | 0 | 378,424 | 55,019 | 48,955 | 8,562 | $0.00 | 75.3m | 1094 | 1064.5 | 6 | 228 |
| opencode | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 2 | 14/14 | 1 | 1 | 0 | 291,872 | 42,498 | 12,551 | 3,392 | $0.00 | 54.6m | 918 | 1046 | 5 | 248 |
| opencode | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 2 | 14/14 | 1.5 | 1.5 | 0 | 381,832 | 47,168 | 40,394 | 3,082 | $0.00 | 58.9m | 1745 | 2001 | 6 | 621 |
| opencode | x-preview-f-free | doorstop | 2 | 14/14 | 1.5 | 2 | 0 | 333,660 | 66,256 | 19,770 | 3,926 | $0.00 | 72.5m | 1425 | 1673 | 5.5 | 377.5 |
| opencode | x-preview-f-free | graphify | 2 | 14/14 | 1 | 1 | 0 | 484,474 | 59,561 | 12,504 | 1,964 | $0.00 | 69.8m | 933 | 1171.5 | 5.5 | 178.5 |
| opencode | x-preview-f-free | ponytail | 2 | 13.5/14 | 2 | 3 | 0 | 234,726 | 29,180 | 27,967 | 4,879 | $0.00 | 31.1m | 612 | 618 | 15 | 143 |
| opencode | x-preview-f-free | strictdoc | 2 | 14/14 | 2.5 | 4 | 0 | 398,588 | 62,940 | 0 | 0 | $0.00 | 65.1m | 870.5 | 1124.5 | 5.5 | 201 |
| opencode | x-preview-f-free | supermemory | 2 | 14/14 | 1.5 | 2.5 | 0 | 270,951 | 55,271 | 48,913 | 12,466 | $0.00 | 47.3m | 1078.5 | 1153.5 | 14.5 | 207.5 |
| opencode | x-preview-f-free | tdd | 2 | 14/14 | 2 | 2.5 | 0 | 275,550 | 43,670 | 30,196 | 4,356 | $0.00 | 43.5m | 2536.5 | 2797 | 18.5 | 748.5 |
| opencode | x-preview-f-free | thermo-nuclear-code-quality-review | 2 | 9.5/14 | 6.5 | 15.5 | 0 | 380,970 | 62,509 | 90,941 | 18,577 | $0.00 | 83.5m | 693.5 | 505.5 | 6 | 116 |
| opencode | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1 | 13/14 | 3 | 6 | 0 | 706,788 | 59,699 | 309,366 | 39,710 | $0.00 | 161.6m | 1861 | 1832 | 4 | 653 |

### `task_manager`

| Agent | Model | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|-------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-----:|-----:|----:|-----:|-----:|---:|
| opencode | x-preview-f-free | baseline | 3 | 15/15 | 2.7 | 3 | 1.7 | 900,910 | 202,798 | 10,562 | 2,472 | $0.00 | 215.6m | 4686.7 | 5738.3 | 5.7 | 931.7 |

## By model

### `x-preview-f-free`

| Problem | Agent | Harness | N | CP | Failed CP | Repeated | Reg | Create in | Create out | Rework in | Rework out | Cost | Time | LOC | ΔLOC | Deps | Cx |
|---------|-------|---------|--:|--:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-----:|-----:|----:|-----:|-----:|---:|
| realworld | opencode | baseline | 2 | 14/14 | 1.5 | 1.5 | 0 | 261,474 | 39,124 | 0 | 0 | $0.00 | 47.8m | 940.5 | 1111 | 5.5 | 209.5 |
| realworld | opencode | combo-supermemory-graphify | 2 | 14/14 | 2 | 2.5 | 0 | 378,424 | 55,019 | 48,955 | 8,562 | $0.00 | 75.3m | 1094 | 1064.5 | 6 | 228 |
| realworld | opencode | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 2 | 14/14 | 1 | 1 | 0 | 291,872 | 42,498 | 12,551 | 3,392 | $0.00 | 54.6m | 918 | 1046 | 5 | 248 |
| realworld | opencode | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 2 | 14/14 | 1.5 | 1.5 | 0 | 381,832 | 47,168 | 40,394 | 3,082 | $0.00 | 58.9m | 1745 | 2001 | 6 | 621 |
| realworld | opencode | doorstop | 2 | 14/14 | 1.5 | 2 | 0 | 333,660 | 66,256 | 19,770 | 3,926 | $0.00 | 72.5m | 1425 | 1673 | 5.5 | 377.5 |
| realworld | opencode | graphify | 2 | 14/14 | 1 | 1 | 0 | 484,474 | 59,561 | 12,504 | 1,964 | $0.00 | 69.8m | 933 | 1171.5 | 5.5 | 178.5 |
| realworld | opencode | ponytail | 2 | 13.5/14 | 2 | 3 | 0 | 234,726 | 29,180 | 27,967 | 4,879 | $0.00 | 31.1m | 612 | 618 | 15 | 143 |
| realworld | opencode | strictdoc | 2 | 14/14 | 2.5 | 4 | 0 | 398,588 | 62,940 | 0 | 0 | $0.00 | 65.1m | 870.5 | 1124.5 | 5.5 | 201 |
| realworld | opencode | supermemory | 2 | 14/14 | 1.5 | 2.5 | 0 | 270,951 | 55,271 | 48,913 | 12,466 | $0.00 | 47.3m | 1078.5 | 1153.5 | 14.5 | 207.5 |
| realworld | opencode | tdd | 2 | 14/14 | 2 | 2.5 | 0 | 275,550 | 43,670 | 30,196 | 4,356 | $0.00 | 43.5m | 2536.5 | 2797 | 18.5 | 748.5 |
| realworld | opencode | thermo-nuclear-code-quality-review | 2 | 9.5/14 | 6.5 | 15.5 | 0 | 380,970 | 62,509 | 90,941 | 18,577 | $0.00 | 83.5m | 693.5 | 505.5 | 6 | 116 |
| task_manager | opencode | baseline | 3 | 15/15 | 2.7 | 3 | 1.7 | 900,910 | 202,798 | 10,562 | 2,472 | $0.00 | 215.6m | 4686.7 | 5738.3 | 5.7 | 931.7 |
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

Each ranking aggregates all published runs for each `(problem, adapter, provider, model, harness)`.
Values are means across runs, including runs from different experiments. Ties are ordered alphabetically.

### CP passed/total

Higher is better. Passed and total checkpoints for the published cell.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | task_manager | x-preview-f-free | baseline | 15/15 |
| 2 | realworld | x-preview-f-free | baseline | 14/14 |
| 3 | realworld | x-preview-f-free | combo-supermemory-graphify | 14/14 |
| 4 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 14/14 |
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 14/14 |
| 6 | realworld | x-preview-f-free | doorstop | 14/14 |
| 7 | realworld | x-preview-f-free | graphify | 14/14 |
| 8 | realworld | x-preview-f-free | strictdoc | 14/14 |
| 9 | realworld | x-preview-f-free | supermemory | 14/14 |
| 10 | realworld | x-preview-f-free | tdd | 14/14 |
| 11 | realworld | x-preview-f-free | ponytail | 13.5/14 |
| 12 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 13/14 |
| 13 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 9.5/14 |

### Failed checkpoints

Lower is better. Number of checkpoints that failed at least once, including repaired ones.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 |
| 2 | realworld | x-preview-f-free | graphify | 1 |
| 3 | realworld | x-preview-f-free | baseline | 1.5 |
| 4 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1.5 |
| 5 | realworld | x-preview-f-free | doorstop | 1.5 |
| 6 | realworld | x-preview-f-free | supermemory | 1.5 |
| 7 | realworld | x-preview-f-free | combo-supermemory-graphify | 2 |
| 8 | realworld | x-preview-f-free | ponytail | 2 |
| 9 | realworld | x-preview-f-free | tdd | 2 |
| 10 | realworld | x-preview-f-free | strictdoc | 2.5 |
| 11 | task_manager | x-preview-f-free | baseline | 2.7 |
| 12 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 3 |
| 13 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 6.5 |

### Repeated attempts

Lower is better. Additional semantic attempts after the initial attempt.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 |
| 2 | realworld | x-preview-f-free | graphify | 1 |
| 3 | realworld | x-preview-f-free | baseline | 1.5 |
| 4 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1.5 |
| 5 | realworld | x-preview-f-free | doorstop | 2 |
| 6 | realworld | x-preview-f-free | combo-supermemory-graphify | 2.5 |
| 7 | realworld | x-preview-f-free | supermemory | 2.5 |
| 8 | realworld | x-preview-f-free | tdd | 2.5 |
| 9 | realworld | x-preview-f-free | ponytail | 3 |
| 10 | task_manager | x-preview-f-free | baseline | 3 |
| 11 | realworld | x-preview-f-free | strictdoc | 4 |
| 12 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 6 |
| 13 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 15.5 |

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
| 13 | task_manager | x-preview-f-free | baseline | 1.7 |

### Creation input tokens

Lower is better. Input tokens used by initial checkpoint attempts.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | ponytail | 234,726 |
| 2 | realworld | x-preview-f-free | baseline | 261,474 |
| 3 | realworld | x-preview-f-free | supermemory | 270,951 |
| 4 | realworld | x-preview-f-free | tdd | 275,550 |
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 291,872 |
| 6 | realworld | x-preview-f-free | doorstop | 333,660 |
| 7 | realworld | x-preview-f-free | combo-supermemory-graphify | 378,424 |
| 8 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 380,970 |
| 9 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 381,832 |
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
| 3 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 42,498 |
| 4 | realworld | x-preview-f-free | tdd | 43,670 |
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 47,168 |
| 6 | realworld | x-preview-f-free | combo-supermemory-graphify | 55,019 |
| 7 | realworld | x-preview-f-free | supermemory | 55,271 |
| 8 | realworld | x-preview-f-free | graphify | 59,561 |
| 9 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 59,699 |
| 10 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 62,509 |
| 11 | realworld | x-preview-f-free | strictdoc | 62,940 |
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
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 12,551 |
| 6 | realworld | x-preview-f-free | doorstop | 19,770 |
| 7 | realworld | x-preview-f-free | ponytail | 27,967 |
| 8 | realworld | x-preview-f-free | tdd | 30,196 |
| 9 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 40,394 |
| 10 | realworld | x-preview-f-free | supermemory | 48,913 |
| 11 | realworld | x-preview-f-free | combo-supermemory-graphify | 48,955 |
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
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 3,082 |
| 6 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 3,392 |
| 7 | realworld | x-preview-f-free | doorstop | 3,926 |
| 8 | realworld | x-preview-f-free | tdd | 4,356 |
| 9 | realworld | x-preview-f-free | ponytail | 4,879 |
| 10 | realworld | x-preview-f-free | combo-supermemory-graphify | 8,562 |
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
| 1 | realworld | x-preview-f-free | ponytail | 31.1m |
| 2 | realworld | x-preview-f-free | tdd | 43.5m |
| 3 | realworld | x-preview-f-free | supermemory | 47.3m |
| 4 | realworld | x-preview-f-free | baseline | 47.8m |
| 5 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 54.6m |
| 6 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 58.9m |
| 7 | realworld | x-preview-f-free | strictdoc | 65.1m |
| 8 | realworld | x-preview-f-free | graphify | 69.8m |
| 9 | realworld | x-preview-f-free | doorstop | 72.5m |
| 10 | realworld | x-preview-f-free | combo-supermemory-graphify | 75.3m |
| 11 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 83.5m |
| 12 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 161.6m |
| 13 | task_manager | x-preview-f-free | baseline | 215.6m |

### Final LOC

Descriptive. Lines of solution code in the final snapshot.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | ponytail | 612 |
| 2 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 693.5 |
| 3 | realworld | x-preview-f-free | strictdoc | 870.5 |
| 4 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 918 |
| 5 | realworld | x-preview-f-free | graphify | 933 |
| 6 | realworld | x-preview-f-free | baseline | 940.5 |
| 7 | realworld | x-preview-f-free | supermemory | 1078.5 |
| 8 | realworld | x-preview-f-free | combo-supermemory-graphify | 1094 |
| 9 | realworld | x-preview-f-free | doorstop | 1425 |
| 10 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1745 |
| 11 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1861 |
| 12 | realworld | x-preview-f-free | tdd | 2536.5 |
| 13 | task_manager | x-preview-f-free | baseline | 4686.7 |

### Changed LOC

Lower is better as a churn measure. Lines changed from the initial snapshot.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 505.5 |
| 2 | realworld | x-preview-f-free | ponytail | 618 |
| 3 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1046 |
| 4 | realworld | x-preview-f-free | combo-supermemory-graphify | 1064.5 |
| 5 | realworld | x-preview-f-free | baseline | 1111 |
| 6 | realworld | x-preview-f-free | strictdoc | 1124.5 |
| 7 | realworld | x-preview-f-free | supermemory | 1153.5 |
| 8 | realworld | x-preview-f-free | graphify | 1171.5 |
| 9 | realworld | x-preview-f-free | doorstop | 1673 |
| 10 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1832 |
| 11 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 2001 |
| 12 | realworld | x-preview-f-free | tdd | 2797 |
| 13 | task_manager | x-preview-f-free | baseline | 5738.3 |

### Dependencies

Lower is better as a complexity measure. Dependencies added by the solution.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 4 |
| 2 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 5 |
| 3 | realworld | x-preview-f-free | baseline | 5.5 |
| 4 | realworld | x-preview-f-free | doorstop | 5.5 |
| 5 | realworld | x-preview-f-free | graphify | 5.5 |
| 6 | realworld | x-preview-f-free | strictdoc | 5.5 |
| 7 | task_manager | x-preview-f-free | baseline | 5.7 |
| 8 | realworld | x-preview-f-free | combo-supermemory-graphify | 6 |
| 9 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 6 |
| 10 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 6 |
| 11 | realworld | x-preview-f-free | supermemory | 14.5 |
| 12 | realworld | x-preview-f-free | ponytail | 15 |
| 13 | realworld | x-preview-f-free | tdd | 18.5 |

### Complexity

Lower is better. Measured code complexity in the final snapshot.

| Rank | Problem | Model | Harness | Value |
|----:|---------|-------|---------|------:|
| 1 | realworld | x-preview-f-free | thermo-nuclear-code-quality-review | 116 |
| 2 | realworld | x-preview-f-free | ponytail | 143 |
| 3 | realworld | x-preview-f-free | graphify | 178.5 |
| 4 | realworld | x-preview-f-free | strictdoc | 201 |
| 5 | realworld | x-preview-f-free | supermemory | 207.5 |
| 6 | realworld | x-preview-f-free | baseline | 209.5 |
| 7 | realworld | x-preview-f-free | combo-supermemory-graphify | 228 |
| 8 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 248 |
| 9 | realworld | x-preview-f-free | doorstop | 377.5 |
| 10 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 621 |
| 11 | realworld | x-preview-f-free | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 653 |
| 12 | realworld | x-preview-f-free | tdd | 748.5 |
| 13 | task_manager | x-preview-f-free | baseline | 931.7 |

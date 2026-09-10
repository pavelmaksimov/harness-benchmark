# Leaderboard

No single score. Absolute metrics only. Δ vs baseline is only in short reports
for the same `(problem, adapter, provider, model, thinking)` cell.

Published from `docs/reports/*.json`. Rebuilt by `python -m benchmark report`.
Input/Output tokens are prompt and completion totals across all attempts on one scale:
cache reads are folded into input and reasoning into output, which OpenCode reports separately.
`-` means a metric is unavailable.
Failed CP counts checkpoints that failed at least once, including repaired ones.

## By task

### `realworld`

| Agent | Model | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Input tokens | Output tokens | Reasoning | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|-------|-------|----------|---------|---:|---:|----------:|----------:|----:|-------------:|--------------:|----------:|-------------:|-----:|-----:|----:|----------:|-----:|---:|---:|
| opencode | deepseek-flash-v4.1 | high | baseline | 1 | 14/14 | 1 | 1 | 0 | 6,222,456 | 102,302 | 46,081 | 270 | $0.00 | 20.8m | 1122 | 13 | 1320 | 5 | 202 |
| opencode | deepseek-v4-flash | high | baseline | 1 | 14/14 | 1 | 1 | 0 | 4,677,899 | 147,302 | 69,085 | 208 | $0.00 | 37.3m | 1631 | 6 | 1627 | 8 | 407 |
| opencode | deepseek-v4-flash | max | baseline | 1 | 14/14 | 1 | 1 | 0 | 6,614,517 | 170,222 | 74,460 | 252 | $0.00 | 39.9m | 1811 | 16 | 1904 | 5 | 514 |
| opencode | glm-5.3-flash | high | baseline | 1 | 14/14 | 1 | 1 | 0 | 5,381,091 | 122,138 | 56,413 | 281 | $0.00 | 85.2m | 1324 | 14 | 1535 | 4 | 242 |
| codex | gpt-5.6-luna | max | baseline | 1 | 14/14 | 1 | 1 | 0 | 5,826,534 | 145,133 | 80,615 | 355 | $2.79 | 53.8m | 1093 | 7 | 1306 | 5 | 184 |
| opencode | muse-spark-1.2-contributor | medium | baseline | 1 | 14/14 | 0 | 0 | 0 | 6,803,246 | 134,181 | 48,686 | 266 | $0.00 | 51.6m | 1502 | 2 | 1929 | 6 | 458 |
| opencode | muse-spark-1.3-contributor | medium | baseline | 1 | 14/14 | 0 | 0 | 0 | 3,260,611 | 79,783 | 27,421 | 170 | $0.00 | 25.1m | 1632 | 2 | 2104 | 6 | 487 |
| opencode | omen-alpha | high | baseline | 1 | 14/14 | 2 | 3 | 0 | 3,713,575 | 79,627 | 26,581 | 232 | $0.00 | 51.2m | 1188 | 7 | 1112 | 22 | 190 |
| opencode | x-preview-f-free | high | baseline | 3 | 14/14 | 1.3 | 1.7 | 0 | 2,900,005 | 54,418 | 8,932 | 196 | $0.00 | 58.1m | 1041 | 5 | 1239 | 10.7 | 212.7 |
| opencode | x-preview-f-free | high | benjamin-plus-skill | 2 | 14/14 | 1 | 1 | 0 | 2,313,688 | 45,894 | 7,262 | 156 | $0.00 | 45.1m | 859 | 3 | 3278.5 | 11.5 | 198.5 |
| opencode | x-preview-f-free | high | combo-supermemory-graphify | 2 | 14/14 | 2 | 2.5 | 0 | 6,177,074 | 71,334 | 7,752 | 286 | $0.00 | 75.3m | 1094 | 6.5 | 1064.5 | 6 | 228 |
| opencode | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 2 | 14/14 | 1 | 1 | 0 | 3,624,071 | 53,134 | 7,245 | 229 | $0.00 | 54.6m | 918 | 5.5 | 1046 | 5 | 248 |
| opencode | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1 | 13/14 | 3 | 6 | 0 | 14,649,626 | 119,845 | 20,436 | 509 | $0.00 | 161.6m | 1861 | 16 | 1832 | 4 | 653 |
| opencode | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 2 | 14/14 | 1.5 | 1.5 | 0 | 4,353,683 | 56,848 | 6,599 | 244 | $0.00 | 58.9m | 1745 | 16.5 | 2001 | 6 | 621 |
| opencode | x-preview-f-free | high | doorstop | 2 | 14/14 | 1.5 | 2 | 0 | 6,111,847 | 68,122 | 6,264 | 352 | $0.00 | 72.5m | 1425 | 11.5 | 1673 | 5.5 | 377.5 |
| opencode | x-preview-f-free | high | graphify | 2 | 14/14 | 1 | 1 | 0 | 5,231,453 | 59,099 | 5,434 | 243 | $0.00 | 69.8m | 933 | 12 | 1171.5 | 5.5 | 178.5 |
| opencode | x-preview-f-free | high | ponytail | 2 | 13.5/14 | 2 | 3 | 0 | 1,866,208 | 32,398 | 2,702 | 144 | $0.00 | 31.1m | 612 | 2.5 | 618 | 15 | 143 |
| opencode | x-preview-f-free | high | python-harness | 1 | 14/14 | 2 | 3 | 0 | 15,284,129 | 125,247 | 17,223 | 440 | $0.00 | 95.8m | 3357 | 49 | 9125 | 10 | 968 |
| opencode | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 1 | 14/14 | 1 | 1 | 0 | 3,786,389 | 48,696 | 6,640 | 195 | $0.00 | 43.9m | 1841 | 19 | 11422 | 7 | 552 |
| opencode | x-preview-f-free | high | python-harness-v1.2.3 | 2 | 13/14 | 2.5 | 4 | 0 | 18,584,117 | 161,967 | 70,656 | 483 | $0.00 | 118.2m | 3581.5 | 44.5 | 3683.5 | 26.5 | 992.5 |
| opencode | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 2 | 14/14 | 1 | 1.5 | 0 | 5,861,789 | 66,026 | 21,024 | 267 | $0.00 | 51.2m | 1404 | 24 | 1720.5 | 7.5 | 403 |
| opencode | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 2 | 13.5/14 | 2 | 3 | 0 | 5,192,132 | 62,948 | 21,156 | 229 | $0.00 | 50.7m | 1841.5 | 19 | 1944 | 6.5 | 595.5 |
| opencode | x-preview-f-free | high | python-harness-v1.3.0 | 2 | 14/14 | 1 | 1.5 | 0 | 14,339,992 | 116,788 | 38,972 | 393 | $0.00 | 102.0m | 3487 | 54.5 | 4000 | 10 | 941.5 |
| opencode | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 1 | 13/14 | 1 | 2 | 0 | 16,906,855 | 150,307 | 49,827 | 617 | $0.00 | 156.0m | 3612 | 54 | 4070 | 11 | 838 |
| opencode | x-preview-f-free | high | python-harness-v1.3.0+graphify | 1 | 14/14 | 1 | 1 | 0 | 16,701,979 | 131,216 | 40,985 | 461 | $0.00 | 123.9m | 3047 | 49 | 3782 | 7 | 834 |
| opencode | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 1 | 14/14 | 1 | 2 | 0 | 10,443,660 | 98,094 | 24,656 | 421 | $0.00 | 99.2m | 2654 | 24 | 3133 | 9 | 825 |
| opencode | x-preview-f-free | high | reclaim-code-entropy | 2 | 14/14 | 1 | 1 | 0 | 3,619,170 | 60,625 | 14,196 | 222 | $0.00 | 49.5m | 1394 | 9 | 9221 | 6 | 332.5 |
| opencode | x-preview-f-free | high | strictdoc | 2 | 14/14 | 2.5 | 4 | 0 | 6,201,588 | 66,840 | 5,399 | 298 | $0.00 | 65.1m | 870.5 | 12 | 1124.5 | 5.5 | 201 |
| opencode | x-preview-f-free | high | supermemory | 2 | 14/14 | 1.5 | 2.5 | 0 | 3,764,984 | 63,640 | 5,744 | 252 | $0.00 | 47.3m | 1078.5 | 8.5 | 1153.5 | 14.5 | 207.5 |
| opencode | x-preview-f-free | high | tdd | 2 | 14/14 | 2 | 2.5 | 0 | 3,491,264 | 48,091 | 3,764 | 226 | $0.00 | 43.5m | 2536.5 | 19 | 2797 | 18.5 | 748.5 |
| opencode | x-preview-f-free | high | thermo-nuclear-code-quality-review | 2 | 9.5/14 | 6.5 | 15.5 | 0 | 5,275,612 | 92,840 | 17,510 | 306 | $0.00 | 83.5m | 693.5 | 9.5 | 505.5 | 6 | 116 |

### `task_manager`

| Agent | Model | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Input tokens | Output tokens | Reasoning | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|-------|-------|----------|---------|---:|---:|----------:|----------:|----:|-------------:|--------------:|----------:|-------------:|-----:|-----:|----:|----------:|-----:|---:|---:|
| opencode | x-preview-f-free | high | baseline | 3 | 15/15 | 2.7 | 3 | 1.7 | 18,291,688 | 215,230 | 28,451 | 496 | $0.00 | 215.6m | 4686.7 | 8.3 | 5738.3 | 5.7 | 931.7 |

## By model

### `deepseek-flash-v4.1`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Input tokens | Output tokens | Reasoning | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|-------------:|--------------:|----------:|-------------:|-----:|-----:|----:|----------:|-----:|---:|---:|
| realworld | opencode | high | baseline | 1 | 14/14 | 1 | 1 | 0 | 6,222,456 | 102,302 | 46,081 | 270 | $0.00 | 20.8m | 1122 | 13 | 1320 | 5 | 202 |

### `deepseek-v4-flash`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Input tokens | Output tokens | Reasoning | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|-------------:|--------------:|----------:|-------------:|-----:|-----:|----:|----------:|-----:|---:|---:|
| realworld | opencode | high | baseline | 1 | 14/14 | 1 | 1 | 0 | 4,677,899 | 147,302 | 69,085 | 208 | $0.00 | 37.3m | 1631 | 6 | 1627 | 8 | 407 |
| realworld | opencode | max | baseline | 1 | 14/14 | 1 | 1 | 0 | 6,614,517 | 170,222 | 74,460 | 252 | $0.00 | 39.9m | 1811 | 16 | 1904 | 5 | 514 |

### `omen-alpha`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Input tokens | Output tokens | Reasoning | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|-------------:|--------------:|----------:|-------------:|-----:|-----:|----:|----------:|-----:|---:|---:|
| realworld | opencode | high | baseline | 1 | 14/14 | 2 | 3 | 0 | 3,713,575 | 79,627 | 26,581 | 232 | $0.00 | 51.2m | 1188 | 7 | 1112 | 22 | 190 |

### `glm-5.3-flash`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Input tokens | Output tokens | Reasoning | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|-------------:|--------------:|----------:|-------------:|-----:|-----:|----:|----------:|-----:|---:|---:|
| realworld | opencode | high | baseline | 1 | 14/14 | 1 | 1 | 0 | 5,381,091 | 122,138 | 56,413 | 281 | $0.00 | 85.2m | 1324 | 14 | 1535 | 4 | 242 |

### `muse-spark-1.2-contributor`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Input tokens | Output tokens | Reasoning | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|-------------:|--------------:|----------:|-------------:|-----:|-----:|----:|----------:|-----:|---:|---:|
| realworld | opencode | medium | baseline | 1 | 14/14 | 0 | 0 | 0 | 6,803,246 | 134,181 | 48,686 | 266 | $0.00 | 51.6m | 1502 | 2 | 1929 | 6 | 458 |

### `muse-spark-1.3-contributor`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Input tokens | Output tokens | Reasoning | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|-------------:|--------------:|----------:|-------------:|-----:|-----:|----:|----------:|-----:|---:|---:|
| realworld | opencode | medium | baseline | 1 | 14/14 | 0 | 0 | 0 | 3,260,611 | 79,783 | 27,421 | 170 | $0.00 | 25.1m | 1632 | 2 | 2104 | 6 | 487 |

### `gpt-5.6-luna`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Input tokens | Output tokens | Reasoning | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|-------------:|--------------:|----------:|-------------:|-----:|-----:|----:|----------:|-----:|---:|---:|
| realworld | codex | max | baseline | 1 | 14/14 | 1 | 1 | 0 | 5,826,534 | 145,133 | 80,615 | 355 | $2.79 | 53.8m | 1093 | 7 | 1306 | 5 | 184 |

### `x-preview-f-free`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Input tokens | Output tokens | Reasoning | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|-------------:|--------------:|----------:|-------------:|-----:|-----:|----:|----------:|-----:|---:|---:|
| realworld | opencode | high | python-harness-v1.3.0+doorstop | 1 | 13/14 | 1 | 2 | 0 | 16,906,855 | 150,307 | 49,827 | 617 | $0.00 | 156.0m | 3612 | 54 | 4070 | 11 | 838 |
| realworld | opencode | high | python-harness-v1.3.0+graphify | 1 | 14/14 | 1 | 1 | 0 | 16,701,979 | 131,216 | 40,985 | 461 | $0.00 | 123.9m | 3047 | 49 | 3782 | 7 | 834 |
| realworld | opencode | high | python-harness-v1.3.0+strictdoc | 1 | 14/14 | 1 | 2 | 0 | 10,443,660 | 98,094 | 24,656 | 421 | $0.00 | 99.2m | 2654 | 24 | 3133 | 9 | 825 |
| realworld | opencode | high | python-harness-v1.3.0 | 2 | 14/14 | 1 | 1.5 | 0 | 14,339,992 | 116,788 | 38,972 | 393 | $0.00 | 102.0m | 3487 | 54.5 | 4000 | 10 | 941.5 |
| realworld | opencode | high | python-harness-v1.2.3 | 2 | 13/14 | 2.5 | 4 | 0 | 18,584,117 | 161,967 | 70,656 | 483 | $0.00 | 118.2m | 3581.5 | 44.5 | 3683.5 | 26.5 | 992.5 |
| realworld | opencode | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 2 | 14/14 | 1 | 1.5 | 0 | 5,861,789 | 66,026 | 21,024 | 267 | $0.00 | 51.2m | 1404 | 24 | 1720.5 | 7.5 | 403 |
| realworld | opencode | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 2 | 13.5/14 | 2 | 3 | 0 | 5,192,132 | 62,948 | 21,156 | 229 | $0.00 | 50.7m | 1841.5 | 19 | 1944 | 6.5 | 595.5 |
| realworld | opencode | high | benjamin-plus-skill | 2 | 14/14 | 1 | 1 | 0 | 2,313,688 | 45,894 | 7,262 | 156 | $0.00 | 45.1m | 859 | 3 | 3278.5 | 11.5 | 198.5 |
| realworld | opencode | high | python-harness | 1 | 14/14 | 2 | 3 | 0 | 15,284,129 | 125,247 | 17,223 | 440 | $0.00 | 95.8m | 3357 | 49 | 9125 | 10 | 968 |
| realworld | opencode | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 1 | 14/14 | 1 | 1 | 0 | 3,786,389 | 48,696 | 6,640 | 195 | $0.00 | 43.9m | 1841 | 19 | 11422 | 7 | 552 |
| realworld | opencode | high | reclaim-code-entropy | 2 | 14/14 | 1 | 1 | 0 | 3,619,170 | 60,625 | 14,196 | 222 | $0.00 | 49.5m | 1394 | 9 | 9221 | 6 | 332.5 |
| realworld | opencode | high | baseline | 3 | 14/14 | 1.3 | 1.7 | 0 | 2,900,005 | 54,418 | 8,932 | 196 | $0.00 | 58.1m | 1041 | 5 | 1239 | 10.7 | 212.7 |
| realworld | opencode | high | combo-supermemory-graphify | 2 | 14/14 | 2 | 2.5 | 0 | 6,177,074 | 71,334 | 7,752 | 286 | $0.00 | 75.3m | 1094 | 6.5 | 1064.5 | 6 | 228 |
| realworld | opencode | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 2 | 14/14 | 1 | 1 | 0 | 3,624,071 | 53,134 | 7,245 | 229 | $0.00 | 54.6m | 918 | 5.5 | 1046 | 5 | 248 |
| realworld | opencode | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 2 | 14/14 | 1.5 | 1.5 | 0 | 4,353,683 | 56,848 | 6,599 | 244 | $0.00 | 58.9m | 1745 | 16.5 | 2001 | 6 | 621 |
| realworld | opencode | high | doorstop | 2 | 14/14 | 1.5 | 2 | 0 | 6,111,847 | 68,122 | 6,264 | 352 | $0.00 | 72.5m | 1425 | 11.5 | 1673 | 5.5 | 377.5 |
| realworld | opencode | high | graphify | 2 | 14/14 | 1 | 1 | 0 | 5,231,453 | 59,099 | 5,434 | 243 | $0.00 | 69.8m | 933 | 12 | 1171.5 | 5.5 | 178.5 |
| realworld | opencode | high | ponytail | 2 | 13.5/14 | 2 | 3 | 0 | 1,866,208 | 32,398 | 2,702 | 144 | $0.00 | 31.1m | 612 | 2.5 | 618 | 15 | 143 |
| realworld | opencode | high | strictdoc | 2 | 14/14 | 2.5 | 4 | 0 | 6,201,588 | 66,840 | 5,399 | 298 | $0.00 | 65.1m | 870.5 | 12 | 1124.5 | 5.5 | 201 |
| realworld | opencode | high | supermemory | 2 | 14/14 | 1.5 | 2.5 | 0 | 3,764,984 | 63,640 | 5,744 | 252 | $0.00 | 47.3m | 1078.5 | 8.5 | 1153.5 | 14.5 | 207.5 |
| realworld | opencode | high | tdd | 2 | 14/14 | 2 | 2.5 | 0 | 3,491,264 | 48,091 | 3,764 | 226 | $0.00 | 43.5m | 2536.5 | 19 | 2797 | 18.5 | 748.5 |
| realworld | opencode | high | thermo-nuclear-code-quality-review | 2 | 9.5/14 | 6.5 | 15.5 | 0 | 5,275,612 | 92,840 | 17,510 | 306 | $0.00 | 83.5m | 693.5 | 9.5 | 505.5 | 6 | 116 |
| task_manager | opencode | high | baseline | 3 | 15/15 | 2.7 | 3 | 1.7 | 18,291,688 | 215,230 | 28,451 | 496 | $0.00 | 215.6m | 4686.7 | 8.3 | 5738.3 | 5.7 | 931.7 |
| realworld | opencode | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1 | 13/14 | 3 | 6 | 0 | 14,649,626 | 119,845 | 20,436 | 509 | $0.00 | 161.6m | 1861 | 16 | 1832 | 4 | 653 |

## Experiments

| Experiment | Date | Problem | Agent | Model | Thinking | N | Report |
|------------|------|---------|-------|-------|----------|---|--------|
| realworld-opencode-go-dsflash-v41-high-baseline-20260910 | 2026-09-10 | realworld | opencode | deepseek-flash-v4.1 | high | 1 | [short](reports/realworld-opencode-go-dsflash-v41-high-baseline-20260910.md) |
| realworld-neuraldeep-qwen3827b-baseline-20260908 | 2026-09-08 | realworld | opencode | qwen3.8-27b | none | 0+0 | [short](reports/realworld-neuraldeep-qwen3827b-baseline-20260908.md) |
| realworld-opencode-go-dsflash-high-baseline-20260908 | 2026-09-08 | realworld | opencode | deepseek-v4-flash | high | 1 | [short](reports/realworld-opencode-go-dsflash-high-baseline-20260908.md) |
| realworld-opencode-go-omenalpha-high-baseline-20260907 | 2026-09-07 | realworld | opencode | omen-alpha | high | 1 | [short](reports/realworld-opencode-go-omenalpha-high-baseline-20260907.md) |
| realworld-opencode-go-dsflash-max-baseline-20260907 | 2026-09-07 | realworld | opencode | deepseek-v4-flash | max | 1 | [short](reports/realworld-opencode-go-dsflash-max-baseline-20260907.md) |
| realworld-opencode-zai-glm53flash-high-baseline-20260903 | 2026-09-03 | realworld | opencode | glm-5.3-flash | high | 1 | [short](reports/realworld-opencode-zai-glm53flash-high-baseline-20260903.md) |
| realworld-opencode-go-muse12-medium-baseline-20260903 | 2026-09-03 | realworld | opencode | muse-spark-1.2-contributor | medium | 1 | [short](reports/realworld-opencode-go-muse12-medium-baseline-20260903.md) |
| realworld-opencode-go-muse13-medium-baseline-20260903 | 2026-09-03 | realworld | opencode | muse-spark-1.3-contributor | medium | 1 | [short](reports/realworld-opencode-go-muse13-medium-baseline-20260903.md) |
| 2026-09-01-realworld-codex-gpt-5.6-luna-max-baseline | 2026-09-01 | realworld | codex | gpt-5.6-luna | max | 1 | [short](reports/2026-09-01-realworld-codex-gpt-5.6-luna-max-baseline.md) |
| realworld-omp-stealthoxalpha-high-baseline-pythonharness-20260826 | 2026-08-26 | realworld | omp | stealth-ox-alpha | high | 0+0 | [short](reports/realworld-omp-stealthoxalpha-high-baseline-pythonharness-20260826.md) |
| realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-combos-20260826 | 2026-08-26 | realworld | opencode | x-preview-f-free | high | 1+1+1 | [short](reports/realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-combos-20260826.md) |
| realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-20260826 | 2026-08-26 | realworld | opencode | x-preview-f-free | high | 2 | [short](reports/realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-20260826.md) |
| realworld-opencode-x-preview-f-free-high-python-harness-v1.2.3-20260825 | 2026-08-25 | realworld | opencode | x-preview-f-free | high | 2+2+2 | [short](reports/realworld-opencode-x-preview-f-free-high-python-harness-v1.2.3-20260825.md) |
| realworld-opencode-x-preview-f-free-high-harnesses-retry | 2026-08-25 | realworld | opencode | x-preview-f-free | high | 2+1 | [short](reports/realworld-opencode-x-preview-f-free-high-harnesses-retry.md) |
| realworld-opencode-x-preview-f-free-high-harnesses-retry-b | 2026-08-25 | realworld | opencode | x-preview-f-free | high | 1+2 | [short](reports/realworld-opencode-x-preview-f-free-high-harnesses-retry-b.md) |
| realworld-opencode-x-preview-f-free-high-harnesses | 2026-08-24 | realworld | opencode | x-preview-f-free | high | 0+0 | [short](reports/realworld-opencode-x-preview-f-free-high-harnesses.md) |
| realworld-opencode-x-preview-f-free-high-all-20260822-1838 | 2026-08-22 | realworld | opencode | x-preview-f-free | high | 2+1+1+1+1+1+1+1+1+1+1 | [short](reports/realworld-opencode-x-preview-f-free-high-all-20260822-1838.md) |
| pilot-feedback-v1-task_manager-20260822 | 2026-08-22 | task_manager | opencode | x-preview-f-free | high | 2 | [short](reports/pilot-feedback-v1-task_manager-20260822.md) |
| realworld-opencode-x-preview-f-free-high-combinations-20260822 | 2026-08-22 | realworld | opencode | x-preview-f-free | high | 1+1+1+1 | [short](reports/realworld-opencode-x-preview-f-free-high-combinations-20260822.md) |
| realworld-opencode-x-preview-f-free-high-20260821-1928 | 2026-08-21 | realworld | opencode | x-preview-f-free | high | 1+1+1+1+1+1+1 | [short](reports/realworld-opencode-x-preview-f-free-high-20260821-1928.md) |
| hc-opencode-oxalpha-high | 2026-08-21 | healthchecks | opencode | x-preview-f-free | high | 0+0 | [short](reports/hc-opencode-oxalpha-high.md) |
| tm-opencode-oxalpha-high | 2026-08-21 | task_manager | opencode | x-preview-f-free | high | 1 | [short](reports/tm-opencode-oxalpha-high.md) |
| rw-opencode-oxalpha-high | 2026-08-21 | realworld | opencode | x-preview-f-free | high | 1 | [short](reports/rw-opencode-oxalpha-high.md) |

## Metric leaderboards

Each ranking aggregates all published runs for each `(problem, adapter, provider, model, thinking, harness)`.
Values are means across runs, including runs from different experiments. Ties are ordered alphabetically.

### CP passed/total

Higher is better. Passed and total checkpoints for the published cell.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | task_manager | x-preview-f-free | high | baseline | 15/15 |
| 2 | realworld | deepseek-flash-v4.1 | high | baseline | 14/14 |
| 3 | realworld | deepseek-v4-flash | high | baseline | 14/14 |
| 4 | realworld | deepseek-v4-flash | max | baseline | 14/14 |
| 5 | realworld | glm-5.3-flash | high | baseline | 14/14 |
| 6 | realworld | gpt-5.6-luna | max | baseline | 14/14 |
| 7 | realworld | muse-spark-1.2-contributor | medium | baseline | 14/14 |
| 8 | realworld | muse-spark-1.3-contributor | medium | baseline | 14/14 |
| 9 | realworld | omen-alpha | high | baseline | 14/14 |
| 10 | realworld | x-preview-f-free | high | baseline | 14/14 |
| 11 | realworld | x-preview-f-free | high | benjamin-plus-skill | 14/14 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 14/14 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 14/14 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 14/14 |
| 15 | realworld | x-preview-f-free | high | doorstop | 14/14 |
| 16 | realworld | x-preview-f-free | high | graphify | 14/14 |
| 17 | realworld | x-preview-f-free | high | python-harness | 14/14 |
| 18 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 14/14 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 14/14 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 14/14 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 14/14 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 14/14 |
| 23 | realworld | x-preview-f-free | high | reclaim-code-entropy | 14/14 |
| 24 | realworld | x-preview-f-free | high | strictdoc | 14/14 |
| 25 | realworld | x-preview-f-free | high | supermemory | 14/14 |
| 26 | realworld | x-preview-f-free | high | tdd | 14/14 |
| 27 | realworld | x-preview-f-free | high | ponytail | 13.5/14 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 13.5/14 |
| 29 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 13/14 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 13/14 |
| 31 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 13/14 |
| 32 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 9.5/14 |

### Failed checkpoints

Lower is better. Number of checkpoints that failed at least once, including repaired ones.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 2 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 3 | realworld | deepseek-flash-v4.1 | high | baseline | 1 |
| 4 | realworld | deepseek-v4-flash | high | baseline | 1 |
| 5 | realworld | deepseek-v4-flash | max | baseline | 1 |
| 6 | realworld | glm-5.3-flash | high | baseline | 1 |
| 7 | realworld | gpt-5.6-luna | max | baseline | 1 |
| 8 | realworld | x-preview-f-free | high | benjamin-plus-skill | 1 |
| 9 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 |
| 10 | realworld | x-preview-f-free | high | graphify | 1 |
| 11 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 1 |
| 12 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 1 |
| 13 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 1 |
| 14 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 1 |
| 15 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 1 |
| 16 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 1 |
| 17 | realworld | x-preview-f-free | high | reclaim-code-entropy | 1 |
| 18 | realworld | x-preview-f-free | high | baseline | 1.3 |
| 19 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1.5 |
| 20 | realworld | x-preview-f-free | high | doorstop | 1.5 |
| 21 | realworld | x-preview-f-free | high | supermemory | 1.5 |
| 22 | realworld | omen-alpha | high | baseline | 2 |
| 23 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 2 |
| 24 | realworld | x-preview-f-free | high | ponytail | 2 |
| 25 | realworld | x-preview-f-free | high | python-harness | 2 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 2 |
| 27 | realworld | x-preview-f-free | high | tdd | 2 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 2.5 |
| 29 | realworld | x-preview-f-free | high | strictdoc | 2.5 |
| 30 | task_manager | x-preview-f-free | high | baseline | 2.7 |
| 31 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 3 |
| 32 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 6.5 |

### Repeated attempts

Lower is better. Additional semantic attempts after the initial attempt.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 2 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 3 | realworld | deepseek-flash-v4.1 | high | baseline | 1 |
| 4 | realworld | deepseek-v4-flash | high | baseline | 1 |
| 5 | realworld | deepseek-v4-flash | max | baseline | 1 |
| 6 | realworld | glm-5.3-flash | high | baseline | 1 |
| 7 | realworld | gpt-5.6-luna | max | baseline | 1 |
| 8 | realworld | x-preview-f-free | high | benjamin-plus-skill | 1 |
| 9 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 |
| 10 | realworld | x-preview-f-free | high | graphify | 1 |
| 11 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 1 |
| 12 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 1 |
| 13 | realworld | x-preview-f-free | high | reclaim-code-entropy | 1 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1.5 |
| 15 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 1.5 |
| 16 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 1.5 |
| 17 | realworld | x-preview-f-free | high | baseline | 1.7 |
| 18 | realworld | x-preview-f-free | high | doorstop | 2 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 2 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 2 |
| 21 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 2.5 |
| 22 | realworld | x-preview-f-free | high | supermemory | 2.5 |
| 23 | realworld | x-preview-f-free | high | tdd | 2.5 |
| 24 | realworld | omen-alpha | high | baseline | 3 |
| 25 | realworld | x-preview-f-free | high | ponytail | 3 |
| 26 | realworld | x-preview-f-free | high | python-harness | 3 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 3 |
| 28 | task_manager | x-preview-f-free | high | baseline | 3 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 4 |
| 30 | realworld | x-preview-f-free | high | strictdoc | 4 |
| 31 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 6 |
| 32 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 15.5 |

### Regressions

Lower is better. Regression tests failing in the final checkpoint evaluations.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-flash-v4.1 | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 3 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 4 | realworld | glm-5.3-flash | high | baseline | 0 |
| 5 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 6 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 7 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 8 | realworld | omen-alpha | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | baseline | 0 |
| 10 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 15 | realworld | x-preview-f-free | high | doorstop | 0 |
| 16 | realworld | x-preview-f-free | high | graphify | 0 |
| 17 | realworld | x-preview-f-free | high | ponytail | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 27 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 28 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 29 | realworld | x-preview-f-free | high | supermemory | 0 |
| 30 | realworld | x-preview-f-free | high | tdd | 0 |
| 31 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 32 | task_manager | x-preview-f-free | high | baseline | 1.7 |

### Rework input tokens

Lower is better. Input tokens used by semantic rework attempts.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 2 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 3 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 4 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 10,099 |
| 5 | task_manager | x-preview-f-free | high | baseline | 10,562 |
| 6 | realworld | x-preview-f-free | high | graphify | 12,504 |
| 7 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 12,551 |
| 8 | realworld | x-preview-f-free | high | baseline | 19,209 |
| 9 | realworld | x-preview-f-free | high | doorstop | 19,770 |
| 10 | realworld | x-preview-f-free | high | benjamin-plus-skill | 24,868 |
| 11 | realworld | x-preview-f-free | high | ponytail | 27,967 |
| 12 | realworld | glm-5.3-flash | high | baseline | 29,752 |
| 13 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 29,885 |
| 14 | realworld | x-preview-f-free | high | tdd | 30,196 |
| 15 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 32,560 |
| 16 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 40,394 |
| 17 | realworld | deepseek-v4-flash | high | baseline | 42,351 |
| 18 | realworld | x-preview-f-free | high | supermemory | 48,913 |
| 19 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 48,955 |
| 20 | realworld | x-preview-f-free | high | reclaim-code-entropy | 49,825 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 57,108 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 68,132 |
| 23 | realworld | omen-alpha | high | baseline | 73,181 |
| 24 | realworld | deepseek-flash-v4.1 | high | baseline | 75,623 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 81,140 |
| 26 | realworld | deepseek-v4-flash | max | baseline | 86,585 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 87,569 |
| 28 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 90,941 |
| 29 | realworld | x-preview-f-free | high | python-harness | 144,495 |
| 30 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 309,366 |
| 31 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 340,264 |
| 32 | realworld | gpt-5.6-luna | max | baseline | 405,590 |

### Rework output tokens

Lower is better. Output tokens used by semantic rework attempts.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 2 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 3 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 4 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 1,717 |
| 5 | realworld | x-preview-f-free | high | graphify | 1,964 |
| 6 | task_manager | x-preview-f-free | high | baseline | 2,472 |
| 7 | realworld | x-preview-f-free | high | benjamin-plus-skill | 2,830 |
| 8 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 2,865 |
| 9 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 3,082 |
| 10 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 3,275 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 3,392 |
| 12 | realworld | x-preview-f-free | high | baseline | 3,847 |
| 13 | realworld | x-preview-f-free | high | doorstop | 3,926 |
| 14 | realworld | x-preview-f-free | high | reclaim-code-entropy | 4,236 |
| 15 | realworld | x-preview-f-free | high | tdd | 4,356 |
| 16 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 4,551 |
| 17 | realworld | glm-5.3-flash | high | baseline | 4,686 |
| 18 | realworld | x-preview-f-free | high | ponytail | 4,879 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 5,108 |
| 20 | realworld | deepseek-flash-v4.1 | high | baseline | 5,790 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 6,034 |
| 22 | realworld | deepseek-v4-flash | high | baseline | 7,724 |
| 23 | realworld | gpt-5.6-luna | max | baseline | 7,853 |
| 24 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 8,562 |
| 25 | realworld | omen-alpha | high | baseline | 8,797 |
| 26 | realworld | x-preview-f-free | high | supermemory | 12,466 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 12,637 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 17,608 |
| 29 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 18,577 |
| 30 | realworld | deepseek-v4-flash | max | baseline | 25,778 |
| 31 | realworld | x-preview-f-free | high | python-harness | 27,421 |
| 32 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 39,710 |

### Reasoning tokens

Lower is better. Reasoning tokens reported by the provider across checkpoints.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | x-preview-f-free | high | ponytail | 2,702 |
| 2 | realworld | x-preview-f-free | high | tdd | 3,764 |
| 3 | realworld | x-preview-f-free | high | strictdoc | 5,399 |
| 4 | realworld | x-preview-f-free | high | graphify | 5,434 |
| 5 | realworld | x-preview-f-free | high | supermemory | 5,744 |
| 6 | realworld | x-preview-f-free | high | doorstop | 6,264 |
| 7 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 6,599 |
| 8 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 6,640 |
| 9 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 7,245 |
| 10 | realworld | x-preview-f-free | high | benjamin-plus-skill | 7,262 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 7,752 |
| 12 | realworld | x-preview-f-free | high | baseline | 8,932 |
| 13 | realworld | x-preview-f-free | high | reclaim-code-entropy | 14,196 |
| 14 | realworld | x-preview-f-free | high | python-harness | 17,223 |
| 15 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 17,510 |
| 16 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 20,436 |
| 17 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 21,024 |
| 18 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 21,156 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 24,656 |
| 20 | realworld | omen-alpha | high | baseline | 26,581 |
| 21 | realworld | muse-spark-1.3-contributor | medium | baseline | 27,421 |
| 22 | task_manager | x-preview-f-free | high | baseline | 28,451 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 38,972 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 40,985 |
| 25 | realworld | deepseek-flash-v4.1 | high | baseline | 46,081 |
| 26 | realworld | muse-spark-1.2-contributor | medium | baseline | 48,686 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 49,827 |
| 28 | realworld | glm-5.3-flash | high | baseline | 56,413 |
| 29 | realworld | deepseek-v4-flash | high | baseline | 69,085 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 70,656 |
| 31 | realworld | deepseek-v4-flash | max | baseline | 74,460 |
| 32 | realworld | gpt-5.6-luna | max | baseline | 80,615 |

### Input tokens

Lower is better. Prompt tokens across checkpoints, cached reads included.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | x-preview-f-free | high | ponytail | 1,866,208 |
| 2 | realworld | x-preview-f-free | high | benjamin-plus-skill | 2,313,688 |
| 3 | realworld | x-preview-f-free | high | baseline | 2,900,005 |
| 4 | realworld | muse-spark-1.3-contributor | medium | baseline | 3,260,611 |
| 5 | realworld | x-preview-f-free | high | tdd | 3,491,264 |
| 6 | realworld | x-preview-f-free | high | reclaim-code-entropy | 3,619,170 |
| 7 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 3,624,071 |
| 8 | realworld | omen-alpha | high | baseline | 3,713,575 |
| 9 | realworld | x-preview-f-free | high | supermemory | 3,764,984 |
| 10 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 3,786,389 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 4,353,683 |
| 12 | realworld | deepseek-v4-flash | high | baseline | 4,677,899 |
| 13 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 5,192,132 |
| 14 | realworld | x-preview-f-free | high | graphify | 5,231,453 |
| 15 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 5,275,612 |
| 16 | realworld | glm-5.3-flash | high | baseline | 5,381,091 |
| 17 | realworld | gpt-5.6-luna | max | baseline | 5,826,534 |
| 18 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 5,861,789 |
| 19 | realworld | x-preview-f-free | high | doorstop | 6,111,847 |
| 20 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 6,177,074 |
| 21 | realworld | x-preview-f-free | high | strictdoc | 6,201,588 |
| 22 | realworld | deepseek-flash-v4.1 | high | baseline | 6,222,456 |
| 23 | realworld | deepseek-v4-flash | max | baseline | 6,614,517 |
| 24 | realworld | muse-spark-1.2-contributor | medium | baseline | 6,803,246 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 10,443,660 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 14,339,992 |
| 27 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 14,649,626 |
| 28 | realworld | x-preview-f-free | high | python-harness | 15,284,129 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 16,701,979 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 16,906,855 |
| 31 | task_manager | x-preview-f-free | high | baseline | 18,291,688 |
| 32 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 18,584,117 |

### Output tokens

Lower is better. Completion tokens across checkpoints, reasoning included.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | x-preview-f-free | high | ponytail | 32,398 |
| 2 | realworld | x-preview-f-free | high | benjamin-plus-skill | 45,894 |
| 3 | realworld | x-preview-f-free | high | tdd | 48,091 |
| 4 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 48,696 |
| 5 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 53,134 |
| 6 | realworld | x-preview-f-free | high | baseline | 54,418 |
| 7 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 56,848 |
| 8 | realworld | x-preview-f-free | high | graphify | 59,099 |
| 9 | realworld | x-preview-f-free | high | reclaim-code-entropy | 60,625 |
| 10 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 62,948 |
| 11 | realworld | x-preview-f-free | high | supermemory | 63,640 |
| 12 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 66,026 |
| 13 | realworld | x-preview-f-free | high | strictdoc | 66,840 |
| 14 | realworld | x-preview-f-free | high | doorstop | 68,122 |
| 15 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 71,334 |
| 16 | realworld | omen-alpha | high | baseline | 79,627 |
| 17 | realworld | muse-spark-1.3-contributor | medium | baseline | 79,783 |
| 18 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 92,840 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 98,094 |
| 20 | realworld | deepseek-flash-v4.1 | high | baseline | 102,302 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 116,788 |
| 22 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 119,845 |
| 23 | realworld | glm-5.3-flash | high | baseline | 122,138 |
| 24 | realworld | x-preview-f-free | high | python-harness | 125,247 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 131,216 |
| 26 | realworld | muse-spark-1.2-contributor | medium | baseline | 134,181 |
| 27 | realworld | gpt-5.6-luna | max | baseline | 145,133 |
| 28 | realworld | deepseek-v4-flash | high | baseline | 147,302 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 150,307 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 161,967 |
| 31 | realworld | deepseek-v4-flash | max | baseline | 170,222 |
| 32 | task_manager | x-preview-f-free | high | baseline | 215,230 |

### Transient input tokens

Lower is better. Input tokens used by transient retry attempts.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-flash-v4.1 | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 3 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 4 | realworld | glm-5.3-flash | high | baseline | 0 |
| 5 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 6 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 7 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 8 | realworld | omen-alpha | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | baseline | 0 |
| 10 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 15 | realworld | x-preview-f-free | high | doorstop | 0 |
| 16 | realworld | x-preview-f-free | high | graphify | 0 |
| 17 | realworld | x-preview-f-free | high | ponytail | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 27 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 28 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 29 | realworld | x-preview-f-free | high | supermemory | 0 |
| 30 | realworld | x-preview-f-free | high | tdd | 0 |
| 31 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 32 | task_manager | x-preview-f-free | high | baseline | 0 |

### Transient output tokens

Lower is better. Output tokens used by transient retry attempts.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-flash-v4.1 | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 3 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 4 | realworld | glm-5.3-flash | high | baseline | 0 |
| 5 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 6 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 7 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 8 | realworld | omen-alpha | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | baseline | 0 |
| 10 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 15 | realworld | x-preview-f-free | high | doorstop | 0 |
| 16 | realworld | x-preview-f-free | high | graphify | 0 |
| 17 | realworld | x-preview-f-free | high | ponytail | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 27 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 28 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 29 | realworld | x-preview-f-free | high | supermemory | 0 |
| 30 | realworld | x-preview-f-free | high | tdd | 0 |
| 31 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 32 | task_manager | x-preview-f-free | high | baseline | 0 |

### LLM requests

Lower is better. Sum of SCB agent steps (LLM requests) across checkpoints.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | x-preview-f-free | high | ponytail | 144 |
| 2 | realworld | x-preview-f-free | high | benjamin-plus-skill | 156 |
| 3 | realworld | muse-spark-1.3-contributor | medium | baseline | 170 |
| 4 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 195 |
| 5 | realworld | x-preview-f-free | high | baseline | 196 |
| 6 | realworld | deepseek-v4-flash | high | baseline | 208 |
| 7 | realworld | x-preview-f-free | high | reclaim-code-entropy | 222 |
| 8 | realworld | x-preview-f-free | high | tdd | 226 |
| 9 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 229 |
| 10 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 229 |
| 11 | realworld | omen-alpha | high | baseline | 232 |
| 12 | realworld | x-preview-f-free | high | graphify | 243 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 244 |
| 14 | realworld | deepseek-v4-flash | max | baseline | 252 |
| 15 | realworld | x-preview-f-free | high | supermemory | 252 |
| 16 | realworld | muse-spark-1.2-contributor | medium | baseline | 266 |
| 17 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 267 |
| 18 | realworld | deepseek-flash-v4.1 | high | baseline | 270 |
| 19 | realworld | glm-5.3-flash | high | baseline | 281 |
| 20 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 286 |
| 21 | realworld | x-preview-f-free | high | strictdoc | 298 |
| 22 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 306 |
| 23 | realworld | x-preview-f-free | high | doorstop | 352 |
| 24 | realworld | gpt-5.6-luna | max | baseline | 355 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 393 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 421 |
| 27 | realworld | x-preview-f-free | high | python-harness | 440 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 461 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 483 |
| 30 | task_manager | x-preview-f-free | high | baseline | 496 |
| 31 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 509 |
| 32 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 617 |

### Semantic rework attempts

Lower is better. Additional semantic attempts after the initial solve, per run.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 2 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 3 | realworld | deepseek-flash-v4.1 | high | baseline | 1 |
| 4 | realworld | deepseek-v4-flash | high | baseline | 1 |
| 5 | realworld | deepseek-v4-flash | max | baseline | 1 |
| 6 | realworld | glm-5.3-flash | high | baseline | 1 |
| 7 | realworld | gpt-5.6-luna | max | baseline | 1 |
| 8 | realworld | x-preview-f-free | high | benjamin-plus-skill | 1 |
| 9 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 |
| 10 | realworld | x-preview-f-free | high | graphify | 1 |
| 11 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 1 |
| 12 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 1 |
| 13 | realworld | x-preview-f-free | high | reclaim-code-entropy | 1 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1.5 |
| 15 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 1.5 |
| 16 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 1.5 |
| 17 | realworld | x-preview-f-free | high | baseline | 1.7 |
| 18 | realworld | x-preview-f-free | high | doorstop | 2 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 2 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 2 |
| 21 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 2.5 |
| 22 | realworld | x-preview-f-free | high | supermemory | 2.5 |
| 23 | realworld | x-preview-f-free | high | tdd | 2.5 |
| 24 | realworld | omen-alpha | high | baseline | 3 |
| 25 | realworld | x-preview-f-free | high | ponytail | 3 |
| 26 | realworld | x-preview-f-free | high | python-harness | 3 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 3 |
| 28 | task_manager | x-preview-f-free | high | baseline | 3 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 4 |
| 30 | realworld | x-preview-f-free | high | strictdoc | 4 |
| 31 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 6 |
| 32 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 15.5 |

### Transient retries

Lower is better. High-confidence provider truncation retries, per run.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-flash-v4.1 | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 3 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 4 | realworld | glm-5.3-flash | high | baseline | 0 |
| 5 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 6 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 7 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 8 | realworld | omen-alpha | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | baseline | 0 |
| 10 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 15 | realworld | x-preview-f-free | high | doorstop | 0 |
| 16 | realworld | x-preview-f-free | high | graphify | 0 |
| 17 | realworld | x-preview-f-free | high | ponytail | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 27 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 28 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 29 | realworld | x-preview-f-free | high | supermemory | 0 |
| 30 | realworld | x-preview-f-free | high | tdd | 0 |
| 31 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 32 | task_manager | x-preview-f-free | high | baseline | 0 |

### Provider truncations

Lower is better. Observed provider truncation events, per run.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-flash-v4.1 | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 3 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 4 | realworld | glm-5.3-flash | high | baseline | 0 |
| 5 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 6 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 7 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 8 | realworld | omen-alpha | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | baseline | 0 |
| 10 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 15 | realworld | x-preview-f-free | high | doorstop | 0 |
| 16 | realworld | x-preview-f-free | high | graphify | 0 |
| 17 | realworld | x-preview-f-free | high | ponytail | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 27 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 28 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 29 | realworld | x-preview-f-free | high | supermemory | 0 |
| 30 | realworld | x-preview-f-free | high | tdd | 0 |
| 31 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 32 | task_manager | x-preview-f-free | high | baseline | 0 |

### Transient recoveries

Lower is better. Truncation retries that resolved the checkpoint, per run.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-flash-v4.1 | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 3 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 4 | realworld | glm-5.3-flash | high | baseline | 0 |
| 5 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 6 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 7 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 8 | realworld | omen-alpha | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | baseline | 0 |
| 10 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 15 | realworld | x-preview-f-free | high | doorstop | 0 |
| 16 | realworld | x-preview-f-free | high | graphify | 0 |
| 17 | realworld | x-preview-f-free | high | ponytail | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 27 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 28 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 29 | realworld | x-preview-f-free | high | supermemory | 0 |
| 30 | realworld | x-preview-f-free | high | tdd | 0 |
| 31 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 32 | task_manager | x-preview-f-free | high | baseline | 0 |

### Truncations unresolved

Lower is better. Checkpoints still truncated after retries, per run.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-flash-v4.1 | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 3 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 4 | realworld | glm-5.3-flash | high | baseline | 0 |
| 5 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 6 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 7 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 8 | realworld | omen-alpha | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | baseline | 0 |
| 10 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 15 | realworld | x-preview-f-free | high | doorstop | 0 |
| 16 | realworld | x-preview-f-free | high | graphify | 0 |
| 17 | realworld | x-preview-f-free | high | ponytail | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 27 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 28 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 29 | realworld | x-preview-f-free | high | supermemory | 0 |
| 30 | realworld | x-preview-f-free | high | tdd | 0 |
| 31 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 32 | task_manager | x-preview-f-free | high | baseline | 0 |

### Normalized cost

Lower is better. Cost normalized with the versioned pricing configuration.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-flash-v4.1 | high | baseline | $0.00 |
| 2 | realworld | deepseek-v4-flash | high | baseline | $0.00 |
| 3 | realworld | deepseek-v4-flash | max | baseline | $0.00 |
| 4 | realworld | glm-5.3-flash | high | baseline | $0.00 |
| 5 | realworld | muse-spark-1.2-contributor | medium | baseline | $0.00 |
| 6 | realworld | muse-spark-1.3-contributor | medium | baseline | $0.00 |
| 7 | realworld | omen-alpha | high | baseline | $0.00 |
| 8 | realworld | x-preview-f-free | high | baseline | $0.00 |
| 9 | realworld | x-preview-f-free | high | benjamin-plus-skill | $0.00 |
| 10 | realworld | x-preview-f-free | high | combo-supermemory-graphify | $0.00 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | $0.00 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | $0.00 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | $0.00 |
| 14 | realworld | x-preview-f-free | high | doorstop | $0.00 |
| 15 | realworld | x-preview-f-free | high | graphify | $0.00 |
| 16 | realworld | x-preview-f-free | high | ponytail | $0.00 |
| 17 | realworld | x-preview-f-free | high | python-harness | $0.00 |
| 18 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | $0.00 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | $0.00 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | $0.00 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | $0.00 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | $0.00 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | $0.00 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | $0.00 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | $0.00 |
| 26 | realworld | x-preview-f-free | high | reclaim-code-entropy | $0.00 |
| 27 | realworld | x-preview-f-free | high | strictdoc | $0.00 |
| 28 | realworld | x-preview-f-free | high | supermemory | $0.00 |
| 29 | realworld | x-preview-f-free | high | tdd | $0.00 |
| 30 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | $0.00 |
| 31 | task_manager | x-preview-f-free | high | baseline | $0.00 |
| 32 | realworld | gpt-5.6-luna | max | baseline | $2.79 |

### Elapsed time

Lower is better. Sum of agent inference time across checkpoints.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-flash-v4.1 | high | baseline | 20.8m |
| 2 | realworld | muse-spark-1.3-contributor | medium | baseline | 25.1m |
| 3 | realworld | x-preview-f-free | high | ponytail | 31.1m |
| 4 | realworld | deepseek-v4-flash | high | baseline | 37.3m |
| 5 | realworld | deepseek-v4-flash | max | baseline | 39.9m |
| 6 | realworld | x-preview-f-free | high | tdd | 43.5m |
| 7 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 43.9m |
| 8 | realworld | x-preview-f-free | high | benjamin-plus-skill | 45.1m |
| 9 | realworld | x-preview-f-free | high | supermemory | 47.3m |
| 10 | realworld | x-preview-f-free | high | reclaim-code-entropy | 49.5m |
| 11 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 50.7m |
| 12 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 51.2m |
| 13 | realworld | omen-alpha | high | baseline | 51.2m |
| 14 | realworld | muse-spark-1.2-contributor | medium | baseline | 51.6m |
| 15 | realworld | gpt-5.6-luna | max | baseline | 53.8m |
| 16 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 54.6m |
| 17 | realworld | x-preview-f-free | high | baseline | 58.1m |
| 18 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 58.9m |
| 19 | realworld | x-preview-f-free | high | strictdoc | 65.1m |
| 20 | realworld | x-preview-f-free | high | graphify | 69.8m |
| 21 | realworld | x-preview-f-free | high | doorstop | 72.5m |
| 22 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 75.3m |
| 23 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 83.5m |
| 24 | realworld | glm-5.3-flash | high | baseline | 85.2m |
| 25 | realworld | x-preview-f-free | high | python-harness | 95.8m |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 99.2m |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 102.0m |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 118.2m |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 123.9m |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 156.0m |
| 31 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 161.6m |
| 32 | task_manager | x-preview-f-free | high | baseline | 215.6m |

### Final LOC

Descriptive. Lines of solution code in the final snapshot.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | x-preview-f-free | high | ponytail | 612 |
| 2 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 693.5 |
| 3 | realworld | x-preview-f-free | high | benjamin-plus-skill | 859 |
| 4 | realworld | x-preview-f-free | high | strictdoc | 870.5 |
| 5 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 918 |
| 6 | realworld | x-preview-f-free | high | graphify | 933 |
| 7 | realworld | x-preview-f-free | high | baseline | 1041 |
| 8 | realworld | x-preview-f-free | high | supermemory | 1078.5 |
| 9 | realworld | gpt-5.6-luna | max | baseline | 1093 |
| 10 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 1094 |
| 11 | realworld | deepseek-flash-v4.1 | high | baseline | 1122 |
| 12 | realworld | omen-alpha | high | baseline | 1188 |
| 13 | realworld | glm-5.3-flash | high | baseline | 1324 |
| 14 | realworld | x-preview-f-free | high | reclaim-code-entropy | 1394 |
| 15 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 1404 |
| 16 | realworld | x-preview-f-free | high | doorstop | 1425 |
| 17 | realworld | muse-spark-1.2-contributor | medium | baseline | 1502 |
| 18 | realworld | deepseek-v4-flash | high | baseline | 1631 |
| 19 | realworld | muse-spark-1.3-contributor | medium | baseline | 1632 |
| 20 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1745 |
| 21 | realworld | deepseek-v4-flash | max | baseline | 1811 |
| 22 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 1841 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 1841.5 |
| 24 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1861 |
| 25 | realworld | x-preview-f-free | high | tdd | 2536.5 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 2654 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 3047 |
| 28 | realworld | x-preview-f-free | high | python-harness | 3357 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 3487 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 3581.5 |
| 31 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 3612 |
| 32 | task_manager | x-preview-f-free | high | baseline | 4686.7 |

### Python modules

Descriptive. Python source modules in the final snapshot.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | muse-spark-1.2-contributor | medium | baseline | 2 |
| 2 | realworld | muse-spark-1.3-contributor | medium | baseline | 2 |
| 3 | realworld | x-preview-f-free | high | ponytail | 2.5 |
| 4 | realworld | x-preview-f-free | high | benjamin-plus-skill | 3 |
| 5 | realworld | x-preview-f-free | high | baseline | 5 |
| 6 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 5.5 |
| 7 | realworld | deepseek-v4-flash | high | baseline | 6 |
| 8 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 6.5 |
| 9 | realworld | gpt-5.6-luna | max | baseline | 7 |
| 10 | realworld | omen-alpha | high | baseline | 7 |
| 11 | task_manager | x-preview-f-free | high | baseline | 8.3 |
| 12 | realworld | x-preview-f-free | high | supermemory | 8.5 |
| 13 | realworld | x-preview-f-free | high | reclaim-code-entropy | 9 |
| 14 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 9.5 |
| 15 | realworld | x-preview-f-free | high | doorstop | 11.5 |
| 16 | realworld | x-preview-f-free | high | graphify | 12 |
| 17 | realworld | x-preview-f-free | high | strictdoc | 12 |
| 18 | realworld | deepseek-flash-v4.1 | high | baseline | 13 |
| 19 | realworld | glm-5.3-flash | high | baseline | 14 |
| 20 | realworld | deepseek-v4-flash | max | baseline | 16 |
| 21 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 16 |
| 22 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 16.5 |
| 23 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 19 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 19 |
| 25 | realworld | x-preview-f-free | high | tdd | 19 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 24 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 24 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 44.5 |
| 29 | realworld | x-preview-f-free | high | python-harness | 49 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 49 |
| 31 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 54 |
| 32 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 54.5 |

### Changed LOC

Lower is better as a churn measure. Lines changed from the initial snapshot.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 505.5 |
| 2 | realworld | x-preview-f-free | high | ponytail | 618 |
| 3 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1046 |
| 4 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 1064.5 |
| 5 | realworld | omen-alpha | high | baseline | 1112 |
| 6 | realworld | x-preview-f-free | high | strictdoc | 1124.5 |
| 7 | realworld | x-preview-f-free | high | supermemory | 1153.5 |
| 8 | realworld | x-preview-f-free | high | graphify | 1171.5 |
| 9 | realworld | x-preview-f-free | high | baseline | 1239 |
| 10 | realworld | gpt-5.6-luna | max | baseline | 1306 |
| 11 | realworld | deepseek-flash-v4.1 | high | baseline | 1320 |
| 12 | realworld | glm-5.3-flash | high | baseline | 1535 |
| 13 | realworld | deepseek-v4-flash | high | baseline | 1627 |
| 14 | realworld | x-preview-f-free | high | doorstop | 1673 |
| 15 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 1720.5 |
| 16 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1832 |
| 17 | realworld | deepseek-v4-flash | max | baseline | 1904 |
| 18 | realworld | muse-spark-1.2-contributor | medium | baseline | 1929 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 1944 |
| 20 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 2001 |
| 21 | realworld | muse-spark-1.3-contributor | medium | baseline | 2104 |
| 22 | realworld | x-preview-f-free | high | tdd | 2797 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 3133 |
| 24 | realworld | x-preview-f-free | high | benjamin-plus-skill | 3278.5 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 3683.5 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 3782 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 4000 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 4070 |
| 29 | task_manager | x-preview-f-free | high | baseline | 5738.3 |
| 30 | realworld | x-preview-f-free | high | python-harness | 9125 |
| 31 | realworld | x-preview-f-free | high | reclaim-code-entropy | 9221 |
| 32 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 11422 |

### Dependencies

Lower is better as a complexity measure. Dependencies added by the solution.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | glm-5.3-flash | high | baseline | 4 |
| 2 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 4 |
| 3 | realworld | deepseek-flash-v4.1 | high | baseline | 5 |
| 4 | realworld | deepseek-v4-flash | max | baseline | 5 |
| 5 | realworld | gpt-5.6-luna | max | baseline | 5 |
| 6 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 5 |
| 7 | realworld | x-preview-f-free | high | doorstop | 5.5 |
| 8 | realworld | x-preview-f-free | high | graphify | 5.5 |
| 9 | realworld | x-preview-f-free | high | strictdoc | 5.5 |
| 10 | task_manager | x-preview-f-free | high | baseline | 5.7 |
| 11 | realworld | muse-spark-1.2-contributor | medium | baseline | 6 |
| 12 | realworld | muse-spark-1.3-contributor | medium | baseline | 6 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 6 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 6 |
| 15 | realworld | x-preview-f-free | high | reclaim-code-entropy | 6 |
| 16 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 6 |
| 17 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 6.5 |
| 18 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 7 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 7 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 7.5 |
| 21 | realworld | deepseek-v4-flash | high | baseline | 8 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 9 |
| 23 | realworld | x-preview-f-free | high | python-harness | 10 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 10 |
| 25 | realworld | x-preview-f-free | high | baseline | 10.7 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 11 |
| 27 | realworld | x-preview-f-free | high | benjamin-plus-skill | 11.5 |
| 28 | realworld | x-preview-f-free | high | supermemory | 14.5 |
| 29 | realworld | x-preview-f-free | high | ponytail | 15 |
| 30 | realworld | x-preview-f-free | high | tdd | 18.5 |
| 31 | realworld | omen-alpha | high | baseline | 22 |
| 32 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 26.5 |

### Complexity

Lower is better. Measured code complexity in the final snapshot.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 116 |
| 2 | realworld | x-preview-f-free | high | ponytail | 143 |
| 3 | realworld | x-preview-f-free | high | graphify | 178.5 |
| 4 | realworld | gpt-5.6-luna | max | baseline | 184 |
| 5 | realworld | omen-alpha | high | baseline | 190 |
| 6 | realworld | x-preview-f-free | high | benjamin-plus-skill | 198.5 |
| 7 | realworld | x-preview-f-free | high | strictdoc | 201 |
| 8 | realworld | deepseek-flash-v4.1 | high | baseline | 202 |
| 9 | realworld | x-preview-f-free | high | supermemory | 207.5 |
| 10 | realworld | x-preview-f-free | high | baseline | 212.7 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 228 |
| 12 | realworld | glm-5.3-flash | high | baseline | 242 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 248 |
| 14 | realworld | x-preview-f-free | high | reclaim-code-entropy | 332.5 |
| 15 | realworld | x-preview-f-free | high | doorstop | 377.5 |
| 16 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 403 |
| 17 | realworld | deepseek-v4-flash | high | baseline | 407 |
| 18 | realworld | muse-spark-1.2-contributor | medium | baseline | 458 |
| 19 | realworld | muse-spark-1.3-contributor | medium | baseline | 487 |
| 20 | realworld | deepseek-v4-flash | max | baseline | 514 |
| 21 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 552 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 595.5 |
| 23 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 621 |
| 24 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 653 |
| 25 | realworld | x-preview-f-free | high | tdd | 748.5 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 825 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 834 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 838 |
| 29 | task_manager | x-preview-f-free | high | baseline | 931.7 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 941.5 |
| 31 | realworld | x-preview-f-free | high | python-harness | 968 |
| 32 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 992.5 |

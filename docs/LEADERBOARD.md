# Leaderboard

No single score. Absolute metrics only. Δ vs baseline is only in short reports
for the same `(problem, adapter, provider, model, thinking)` cell.

Published from `docs/reports/*.json`. Rebuilt by `python -m benchmark report`.
Create/Rework columns are per-attempt token usage split by stage (create = initial attempts);
Cached/Reasoning/Output tokens cover all attempts; `-` means it is unavailable.
Failed CP counts checkpoints that failed at least once, including repaired ones.

## By task

### `realworld`

| Agent | Model | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Create input | Create output | Rework input | Rework output | Cached tokens | Reasoning | Output tokens | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|-------|-------|----------|---------|---:|---:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-------------:|------------:|----------:|-----------:|------------:|-----:|-----:|----:|----------:|-----:|---:|
| opencode | deepseek-v4-flash | high | baseline | 1 | 14/14 | 1 | 1 | 0 | 349,724 | 70,493 | 42,351 | 7,724 | 4,285,824 | 69,085 | 78,217 | 208 | $0.00 | 37.3m | 1631 | 6 | 1627 | 8 | 407 |
| opencode | deepseek-v4-flash | max | baseline | 1 | 14/14 | 1 | 1 | 0 | 556,860 | 69,984 | 86,585 | 25,778 | 5,971,072 | 74,460 | 95,762 | 252 | $0.00 | 39.9m | 1811 | 16 | 1904 | 5 | 514 |
| opencode | glm-5.3-flash | high | baseline | 1 | 14/14 | 1 | 1 | 0 | 354,603 | 61,039 | 29,752 | 4,686 | 4,996,736 | 56,413 | 65,725 | 281 | $0.00 | 85.2m | 1324 | 14 | 1535 | 4 | 242 |
| codex | gpt-5.6-luna | max | baseline | 1 | 14/14 | 1 | 1 | 0 | 5,420,944 | 137,280 | 405,590 | 7,853 | 5,285,888 | 80,615 | 145,133 | 355 | $2.79 | 53.8m | 1093 | 7 | 1306 | 5 | 184 |
| opencode | muse-spark-1.2-contributor | medium | baseline | 1 | 14/14 | 0 | 0 | 0 | 580,285 | 85,495 | 0 | 0 | 6,222,961 | 48,686 | 85,495 | 266 | $0.00 | 51.6m | 1502 | 2 | 1929 | 6 | 458 |
| opencode | muse-spark-1.3-contributor | medium | baseline | 1 | 14/14 | 0 | 0 | 0 | 376,686 | 52,362 | 0 | 0 | 2,883,925 | 27,421 | 52,362 | 170 | $0.00 | 25.1m | 1632 | 2 | 2104 | 6 | 487 |
| opencode | omen-alpha | high | baseline | 1 | 14/14 | 2 | 3 | 0 | 454,922 | 44,249 | 73,181 | 8,797 | 3,185,472 | 26,581 | 53,046 | 232 | $0.00 | 51.2m | 1188 | 7 | 1112 | 22 | 190 |
| opencode | x-preview-f-free | high | baseline | 3 | 14/14 | 1.3 | 1.7 | 0 | 296,046 | 43,178 | 19,209 | 3,847 | 2,606,272 | 8,932 | 45,486 | 196 | $0.00 | 58.1m | 1041 | 5 | 1239 | 10.7 | 212.7 |
| opencode | x-preview-f-free | high | benjamin-plus-skill | 2 | 14/14 | 1 | 1 | 0 | 351,220 | 35,802 | 24,868 | 2,830 | 1,937,600 | 7,262 | 38,632 | 156 | $0.00 | 45.1m | 859 | 3 | 3278.5 | 11.5 | 198.5 |
| opencode | x-preview-f-free | high | combo-supermemory-graphify | 2 | 14/14 | 2 | 2.5 | 0 | 378,424 | 55,019 | 48,955 | 8,562 | 5,749,696 | 7,752 | 63,581 | 286 | $0.00 | 75.3m | 1094 | 6.5 | 1064.5 | 6 | 228 |
| opencode | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 2 | 14/14 | 1 | 1 | 0 | 291,872 | 42,498 | 12,551 | 3,392 | 3,319,648 | 7,245 | 45,890 | 229 | $0.00 | 54.6m | 918 | 5.5 | 1046 | 5 | 248 |
| opencode | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1 | 13/14 | 3 | 6 | 0 | 706,788 | 59,699 | 309,366 | 39,710 | 13,633,472 | 20,436 | 99,409 | 509 | $0.00 | 161.6m | 1861 | 16 | 1832 | 4 | 653 |
| opencode | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 2 | 14/14 | 1.5 | 1.5 | 0 | 381,832 | 47,168 | 40,394 | 3,082 | 3,931,456 | 6,599 | 50,249 | 244 | $0.00 | 58.9m | 1745 | 16.5 | 2001 | 6 | 621 |
| opencode | x-preview-f-free | high | doorstop | 2 | 14/14 | 1.5 | 2 | 0 | 333,660 | 66,256 | 19,770 | 3,926 | 5,743,136 | 6,264 | 61,858 | 352 | $0.00 | 72.5m | 1425 | 11.5 | 1673 | 5.5 | 377.5 |
| opencode | x-preview-f-free | high | graphify | 2 | 14/14 | 1 | 1 | 0 | 484,474 | 59,561 | 12,504 | 1,964 | 4,687,008 | 5,434 | 53,665 | 243 | $0.00 | 69.8m | 933 | 12 | 1171.5 | 5.5 | 178.5 |
| opencode | x-preview-f-free | high | ponytail | 2 | 13.5/14 | 2 | 3 | 0 | 234,726 | 29,180 | 27,967 | 4,879 | 1,587,520 | 2,702 | 29,696 | 144 | $0.00 | 31.1m | 612 | 2.5 | 618 | 15 | 143 |
| opencode | x-preview-f-free | high | python-harness | 1 | 14/14 | 2 | 3 | 0 | 725,810 | 80,603 | 144,495 | 27,421 | 14,413,824 | 17,223 | 108,024 | 440 | $0.00 | 95.8m | 3357 | 49 | 9125 | 10 | 968 |
| opencode | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 1 | 14/14 | 1 | 1 | 0 | 317,730 | 39,191 | 10,099 | 2,865 | 3,458,560 | 6,640 | 42,056 | 195 | $0.00 | 43.9m | 1841 | 19 | 11422 | 7 | 552 |
| opencode | x-preview-f-free | high | python-harness-v1.2.3 | 2 | 13/14 | 2.5 | 4 | 0 | 885,262 | 73,702 | 340,264 | 17,608 | 17,358,592 | 70,656 | 91,310 | 483 | $0.00 | 118.2m | 3581.5 | 44.5 | 3683.5 | 26.5 | 992.5 |
| opencode | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 2 | 14/14 | 1 | 1.5 | 0 | 668,908 | 41,727 | 32,560 | 3,275 | 5,160,320 | 21,024 | 45,002 | 267 | $0.00 | 51.2m | 1404 | 24 | 1720.5 | 7.5 | 403 |
| opencode | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 2 | 13.5/14 | 2 | 3 | 0 | 582,129 | 35,758 | 81,140 | 6,034 | 4,528,864 | 21,156 | 41,792 | 229 | $0.00 | 50.7m | 1841.5 | 19 | 1944 | 6.5 | 595.5 |
| opencode | x-preview-f-free | high | python-harness-v1.3.0 | 2 | 14/14 | 1 | 1.5 | 0 | 651,188 | 72,708 | 68,132 | 5,108 | 13,620,672 | 38,972 | 77,816 | 393 | $0.00 | 102.0m | 3487 | 54.5 | 4000 | 10 | 941.5 |
| opencode | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 1 | 13/14 | 1 | 2 | 0 | 534,486 | 87,843 | 87,569 | 12,637 | 16,284,800 | 49,827 | 100,480 | 617 | $0.00 | 156.0m | 3612 | 54 | 4070 | 11 | 838 |
| opencode | x-preview-f-free | high | python-harness-v1.3.0+graphify | 1 | 14/14 | 1 | 1 | 0 | 718,174 | 88,514 | 29,885 | 1,717 | 15,953,920 | 40,985 | 90,231 | 461 | $0.00 | 123.9m | 3047 | 49 | 3782 | 7 | 834 |
| opencode | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 1 | 14/14 | 1 | 2 | 0 | 465,912 | 68,887 | 57,108 | 4,551 | 9,920,640 | 24,656 | 73,438 | 421 | $0.00 | 99.2m | 2654 | 24 | 3133 | 9 | 825 |
| opencode | x-preview-f-free | high | reclaim-code-entropy | 2 | 14/14 | 1 | 1 | 0 | 388,386 | 42,193 | 49,825 | 4,236 | 3,180,960 | 14,196 | 46,428 | 222 | $0.00 | 49.5m | 1394 | 9 | 9221 | 6 | 332.5 |
| opencode | x-preview-f-free | high | strictdoc | 2 | 14/14 | 2.5 | 4 | 0 | 398,588 | 62,940 | 0 | 0 | 5,786,336 | 5,399 | 61,442 | 298 | $0.00 | 65.1m | 870.5 | 12 | 1124.5 | 5.5 | 201 |
| opencode | x-preview-f-free | high | supermemory | 2 | 14/14 | 1.5 | 2.5 | 0 | 270,951 | 55,271 | 48,913 | 12,466 | 3,368,448 | 5,744 | 57,895 | 252 | $0.00 | 47.3m | 1078.5 | 8.5 | 1153.5 | 14.5 | 207.5 |
| opencode | x-preview-f-free | high | tdd | 2 | 14/14 | 2 | 2.5 | 0 | 275,550 | 43,670 | 30,196 | 4,356 | 3,187,136 | 3,764 | 44,328 | 226 | $0.00 | 43.5m | 2536.5 | 19 | 2797 | 18.5 | 748.5 |
| opencode | x-preview-f-free | high | thermo-nuclear-code-quality-review | 2 | 9.5/14 | 6.5 | 15.5 | 0 | 380,970 | 62,509 | 90,941 | 18,577 | 4,845,120 | 17,510 | 75,330 | 306 | $0.00 | 83.5m | 693.5 | 9.5 | 505.5 | 6 | 116 |

### `task_manager`

| Agent | Model | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Create input | Create output | Rework input | Rework output | Cached tokens | Reasoning | Output tokens | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|-------|-------|----------|---------|---:|---:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-------------:|------------:|----------:|-----------:|------------:|-----:|-----:|----:|----------:|-----:|---:|
| opencode | x-preview-f-free | high | baseline | 3 | 15/15 | 2.7 | 3 | 1.7 | 900,910 | 202,798 | 10,562 | 2,472 | 17,479,296 | 28,451 | 186,779 | 496 | $0.00 | 215.6m | 4686.7 | 8.3 | 5738.3 | 5.7 | 931.7 |

## By model

### `deepseek-v4-flash`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Create input | Create output | Rework input | Rework output | Cached tokens | Reasoning | Output tokens | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-------------:|------------:|----------:|-----------:|------------:|-----:|-----:|----:|----------:|-----:|---:|
| realworld | opencode | high | baseline | 1 | 14/14 | 1 | 1 | 0 | 349,724 | 70,493 | 42,351 | 7,724 | 4,285,824 | 69,085 | 78,217 | 208 | $0.00 | 37.3m | 1631 | 6 | 1627 | 8 | 407 |
| realworld | opencode | max | baseline | 1 | 14/14 | 1 | 1 | 0 | 556,860 | 69,984 | 86,585 | 25,778 | 5,971,072 | 74,460 | 95,762 | 252 | $0.00 | 39.9m | 1811 | 16 | 1904 | 5 | 514 |

### `omen-alpha`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Create input | Create output | Rework input | Rework output | Cached tokens | Reasoning | Output tokens | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-------------:|------------:|----------:|-----------:|------------:|-----:|-----:|----:|----------:|-----:|---:|
| realworld | opencode | high | baseline | 1 | 14/14 | 2 | 3 | 0 | 454,922 | 44,249 | 73,181 | 8,797 | 3,185,472 | 26,581 | 53,046 | 232 | $0.00 | 51.2m | 1188 | 7 | 1112 | 22 | 190 |

### `glm-5.3-flash`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Create input | Create output | Rework input | Rework output | Cached tokens | Reasoning | Output tokens | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-------------:|------------:|----------:|-----------:|------------:|-----:|-----:|----:|----------:|-----:|---:|
| realworld | opencode | high | baseline | 1 | 14/14 | 1 | 1 | 0 | 354,603 | 61,039 | 29,752 | 4,686 | 4,996,736 | 56,413 | 65,725 | 281 | $0.00 | 85.2m | 1324 | 14 | 1535 | 4 | 242 |

### `muse-spark-1.2-contributor`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Create input | Create output | Rework input | Rework output | Cached tokens | Reasoning | Output tokens | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-------------:|------------:|----------:|-----------:|------------:|-----:|-----:|----:|----------:|-----:|---:|
| realworld | opencode | medium | baseline | 1 | 14/14 | 0 | 0 | 0 | 580,285 | 85,495 | 0 | 0 | 6,222,961 | 48,686 | 85,495 | 266 | $0.00 | 51.6m | 1502 | 2 | 1929 | 6 | 458 |

### `muse-spark-1.3-contributor`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Create input | Create output | Rework input | Rework output | Cached tokens | Reasoning | Output tokens | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-------------:|------------:|----------:|-----------:|------------:|-----:|-----:|----:|----------:|-----:|---:|
| realworld | opencode | medium | baseline | 1 | 14/14 | 0 | 0 | 0 | 376,686 | 52,362 | 0 | 0 | 2,883,925 | 27,421 | 52,362 | 170 | $0.00 | 25.1m | 1632 | 2 | 2104 | 6 | 487 |

### `gpt-5.6-luna`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Create input | Create output | Rework input | Rework output | Cached tokens | Reasoning | Output tokens | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-------------:|------------:|----------:|-----------:|------------:|-----:|-----:|----:|----------:|-----:|---:|
| realworld | codex | max | baseline | 1 | 14/14 | 1 | 1 | 0 | 5,420,944 | 137,280 | 405,590 | 7,853 | 5,285,888 | 80,615 | 145,133 | 355 | $2.79 | 53.8m | 1093 | 7 | 1306 | 5 | 184 |

### `x-preview-f-free`

| Problem | Agent | Thinking | Harness | N | CP | Failed CP | Repeated | Reg | Create input | Create output | Rework input | Rework output | Cached tokens | Reasoning | Output tokens | LLM requests | Cost | Time | LOC | Py modules | ΔLOC | Deps | Cx |
|---------|-------|----------|---------|---:|---:|----------:|----------:|----:|----------:|-----------:|----------:|-----------:|-------------:|------------:|----------:|-----------:|------------:|-----:|-----:|----:|----------:|-----:|---:|
| realworld | opencode | high | python-harness-v1.3.0+doorstop | 1 | 13/14 | 1 | 2 | 0 | 534,486 | 87,843 | 87,569 | 12,637 | 16,284,800 | 49,827 | 100,480 | 617 | $0.00 | 156.0m | 3612 | 54 | 4070 | 11 | 838 |
| realworld | opencode | high | python-harness-v1.3.0+graphify | 1 | 14/14 | 1 | 1 | 0 | 718,174 | 88,514 | 29,885 | 1,717 | 15,953,920 | 40,985 | 90,231 | 461 | $0.00 | 123.9m | 3047 | 49 | 3782 | 7 | 834 |
| realworld | opencode | high | python-harness-v1.3.0+strictdoc | 1 | 14/14 | 1 | 2 | 0 | 465,912 | 68,887 | 57,108 | 4,551 | 9,920,640 | 24,656 | 73,438 | 421 | $0.00 | 99.2m | 2654 | 24 | 3133 | 9 | 825 |
| realworld | opencode | high | python-harness-v1.3.0 | 2 | 14/14 | 1 | 1.5 | 0 | 651,188 | 72,708 | 68,132 | 5,108 | 13,620,672 | 38,972 | 77,816 | 393 | $0.00 | 102.0m | 3487 | 54.5 | 4000 | 10 | 941.5 |
| realworld | opencode | high | python-harness-v1.2.3 | 2 | 13/14 | 2.5 | 4 | 0 | 885,262 | 73,702 | 340,264 | 17,608 | 17,358,592 | 70,656 | 91,310 | 483 | $0.00 | 118.2m | 3581.5 | 44.5 | 3683.5 | 26.5 | 992.5 |
| realworld | opencode | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 2 | 14/14 | 1 | 1.5 | 0 | 668,908 | 41,727 | 32,560 | 3,275 | 5,160,320 | 21,024 | 45,002 | 267 | $0.00 | 51.2m | 1404 | 24 | 1720.5 | 7.5 | 403 |
| realworld | opencode | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 2 | 13.5/14 | 2 | 3 | 0 | 582,129 | 35,758 | 81,140 | 6,034 | 4,528,864 | 21,156 | 41,792 | 229 | $0.00 | 50.7m | 1841.5 | 19 | 1944 | 6.5 | 595.5 |
| realworld | opencode | high | benjamin-plus-skill | 2 | 14/14 | 1 | 1 | 0 | 351,220 | 35,802 | 24,868 | 2,830 | 1,937,600 | 7,262 | 38,632 | 156 | $0.00 | 45.1m | 859 | 3 | 3278.5 | 11.5 | 198.5 |
| realworld | opencode | high | python-harness | 1 | 14/14 | 2 | 3 | 0 | 725,810 | 80,603 | 144,495 | 27,421 | 14,413,824 | 17,223 | 108,024 | 440 | $0.00 | 95.8m | 3357 | 49 | 9125 | 10 | 968 |
| realworld | opencode | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 1 | 14/14 | 1 | 1 | 0 | 317,730 | 39,191 | 10,099 | 2,865 | 3,458,560 | 6,640 | 42,056 | 195 | $0.00 | 43.9m | 1841 | 19 | 11422 | 7 | 552 |
| realworld | opencode | high | reclaim-code-entropy | 2 | 14/14 | 1 | 1 | 0 | 388,386 | 42,193 | 49,825 | 4,236 | 3,180,960 | 14,196 | 46,428 | 222 | $0.00 | 49.5m | 1394 | 9 | 9221 | 6 | 332.5 |
| realworld | opencode | high | baseline | 3 | 14/14 | 1.3 | 1.7 | 0 | 296,046 | 43,178 | 19,209 | 3,847 | 2,606,272 | 8,932 | 45,486 | 196 | $0.00 | 58.1m | 1041 | 5 | 1239 | 10.7 | 212.7 |
| realworld | opencode | high | combo-supermemory-graphify | 2 | 14/14 | 2 | 2.5 | 0 | 378,424 | 55,019 | 48,955 | 8,562 | 5,749,696 | 7,752 | 63,581 | 286 | $0.00 | 75.3m | 1094 | 6.5 | 1064.5 | 6 | 228 |
| realworld | opencode | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 2 | 14/14 | 1 | 1 | 0 | 291,872 | 42,498 | 12,551 | 3,392 | 3,319,648 | 7,245 | 45,890 | 229 | $0.00 | 54.6m | 918 | 5.5 | 1046 | 5 | 248 |
| realworld | opencode | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 2 | 14/14 | 1.5 | 1.5 | 0 | 381,832 | 47,168 | 40,394 | 3,082 | 3,931,456 | 6,599 | 50,249 | 244 | $0.00 | 58.9m | 1745 | 16.5 | 2001 | 6 | 621 |
| realworld | opencode | high | doorstop | 2 | 14/14 | 1.5 | 2 | 0 | 333,660 | 66,256 | 19,770 | 3,926 | 5,743,136 | 6,264 | 61,858 | 352 | $0.00 | 72.5m | 1425 | 11.5 | 1673 | 5.5 | 377.5 |
| realworld | opencode | high | graphify | 2 | 14/14 | 1 | 1 | 0 | 484,474 | 59,561 | 12,504 | 1,964 | 4,687,008 | 5,434 | 53,665 | 243 | $0.00 | 69.8m | 933 | 12 | 1171.5 | 5.5 | 178.5 |
| realworld | opencode | high | ponytail | 2 | 13.5/14 | 2 | 3 | 0 | 234,726 | 29,180 | 27,967 | 4,879 | 1,587,520 | 2,702 | 29,696 | 144 | $0.00 | 31.1m | 612 | 2.5 | 618 | 15 | 143 |
| realworld | opencode | high | strictdoc | 2 | 14/14 | 2.5 | 4 | 0 | 398,588 | 62,940 | 0 | 0 | 5,786,336 | 5,399 | 61,442 | 298 | $0.00 | 65.1m | 870.5 | 12 | 1124.5 | 5.5 | 201 |
| realworld | opencode | high | supermemory | 2 | 14/14 | 1.5 | 2.5 | 0 | 270,951 | 55,271 | 48,913 | 12,466 | 3,368,448 | 5,744 | 57,895 | 252 | $0.00 | 47.3m | 1078.5 | 8.5 | 1153.5 | 14.5 | 207.5 |
| realworld | opencode | high | tdd | 2 | 14/14 | 2 | 2.5 | 0 | 275,550 | 43,670 | 30,196 | 4,356 | 3,187,136 | 3,764 | 44,328 | 226 | $0.00 | 43.5m | 2536.5 | 19 | 2797 | 18.5 | 748.5 |
| realworld | opencode | high | thermo-nuclear-code-quality-review | 2 | 9.5/14 | 6.5 | 15.5 | 0 | 380,970 | 62,509 | 90,941 | 18,577 | 4,845,120 | 17,510 | 75,330 | 306 | $0.00 | 83.5m | 693.5 | 9.5 | 505.5 | 6 | 116 |
| task_manager | opencode | high | baseline | 3 | 15/15 | 2.7 | 3 | 1.7 | 900,910 | 202,798 | 10,562 | 2,472 | 17,479,296 | 28,451 | 186,779 | 496 | $0.00 | 215.6m | 4686.7 | 8.3 | 5738.3 | 5.7 | 931.7 |
| realworld | opencode | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1 | 13/14 | 3 | 6 | 0 | 706,788 | 59,699 | 309,366 | 39,710 | 13,633,472 | 20,436 | 99,409 | 509 | $0.00 | 161.6m | 1861 | 16 | 1832 | 4 | 653 |

## Experiments

| Experiment | Date | Problem | Agent | Model | Thinking | N | Report |
|------------|------|---------|-------|-------|----------|---|--------|
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
| 2 | realworld | deepseek-v4-flash | high | baseline | 14/14 |
| 3 | realworld | deepseek-v4-flash | max | baseline | 14/14 |
| 4 | realworld | glm-5.3-flash | high | baseline | 14/14 |
| 5 | realworld | gpt-5.6-luna | max | baseline | 14/14 |
| 6 | realworld | muse-spark-1.2-contributor | medium | baseline | 14/14 |
| 7 | realworld | muse-spark-1.3-contributor | medium | baseline | 14/14 |
| 8 | realworld | omen-alpha | high | baseline | 14/14 |
| 9 | realworld | x-preview-f-free | high | baseline | 14/14 |
| 10 | realworld | x-preview-f-free | high | benjamin-plus-skill | 14/14 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 14/14 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 14/14 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 14/14 |
| 14 | realworld | x-preview-f-free | high | doorstop | 14/14 |
| 15 | realworld | x-preview-f-free | high | graphify | 14/14 |
| 16 | realworld | x-preview-f-free | high | python-harness | 14/14 |
| 17 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 14/14 |
| 18 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 14/14 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 14/14 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 14/14 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 14/14 |
| 22 | realworld | x-preview-f-free | high | reclaim-code-entropy | 14/14 |
| 23 | realworld | x-preview-f-free | high | strictdoc | 14/14 |
| 24 | realworld | x-preview-f-free | high | supermemory | 14/14 |
| 25 | realworld | x-preview-f-free | high | tdd | 14/14 |
| 26 | realworld | x-preview-f-free | high | ponytail | 13.5/14 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 13.5/14 |
| 28 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 13/14 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 13/14 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 13/14 |
| 31 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 9.5/14 |

### Failed checkpoints

Lower is better. Number of checkpoints that failed at least once, including repaired ones.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 2 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 3 | realworld | deepseek-v4-flash | high | baseline | 1 |
| 4 | realworld | deepseek-v4-flash | max | baseline | 1 |
| 5 | realworld | glm-5.3-flash | high | baseline | 1 |
| 6 | realworld | gpt-5.6-luna | max | baseline | 1 |
| 7 | realworld | x-preview-f-free | high | benjamin-plus-skill | 1 |
| 8 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 |
| 9 | realworld | x-preview-f-free | high | graphify | 1 |
| 10 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 1 |
| 11 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 1 |
| 12 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 1 |
| 13 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 1 |
| 14 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 1 |
| 15 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 1 |
| 16 | realworld | x-preview-f-free | high | reclaim-code-entropy | 1 |
| 17 | realworld | x-preview-f-free | high | baseline | 1.3 |
| 18 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1.5 |
| 19 | realworld | x-preview-f-free | high | doorstop | 1.5 |
| 20 | realworld | x-preview-f-free | high | supermemory | 1.5 |
| 21 | realworld | omen-alpha | high | baseline | 2 |
| 22 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 2 |
| 23 | realworld | x-preview-f-free | high | ponytail | 2 |
| 24 | realworld | x-preview-f-free | high | python-harness | 2 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 2 |
| 26 | realworld | x-preview-f-free | high | tdd | 2 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 2.5 |
| 28 | realworld | x-preview-f-free | high | strictdoc | 2.5 |
| 29 | task_manager | x-preview-f-free | high | baseline | 2.7 |
| 30 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 3 |
| 31 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 6.5 |

### Repeated attempts

Lower is better. Additional semantic attempts after the initial attempt.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 2 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 3 | realworld | deepseek-v4-flash | high | baseline | 1 |
| 4 | realworld | deepseek-v4-flash | max | baseline | 1 |
| 5 | realworld | glm-5.3-flash | high | baseline | 1 |
| 6 | realworld | gpt-5.6-luna | max | baseline | 1 |
| 7 | realworld | x-preview-f-free | high | benjamin-plus-skill | 1 |
| 8 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 |
| 9 | realworld | x-preview-f-free | high | graphify | 1 |
| 10 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 1 |
| 11 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 1 |
| 12 | realworld | x-preview-f-free | high | reclaim-code-entropy | 1 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1.5 |
| 14 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 1.5 |
| 15 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 1.5 |
| 16 | realworld | x-preview-f-free | high | baseline | 1.7 |
| 17 | realworld | x-preview-f-free | high | doorstop | 2 |
| 18 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 2 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 2 |
| 20 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 2.5 |
| 21 | realworld | x-preview-f-free | high | supermemory | 2.5 |
| 22 | realworld | x-preview-f-free | high | tdd | 2.5 |
| 23 | realworld | omen-alpha | high | baseline | 3 |
| 24 | realworld | x-preview-f-free | high | ponytail | 3 |
| 25 | realworld | x-preview-f-free | high | python-harness | 3 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 3 |
| 27 | task_manager | x-preview-f-free | high | baseline | 3 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 4 |
| 29 | realworld | x-preview-f-free | high | strictdoc | 4 |
| 30 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 6 |
| 31 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 15.5 |

### Regressions

Lower is better. Regression tests failing in the final checkpoint evaluations.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 3 | realworld | glm-5.3-flash | high | baseline | 0 |
| 4 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 5 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 6 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 7 | realworld | omen-alpha | high | baseline | 0 |
| 8 | realworld | x-preview-f-free | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 10 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | doorstop | 0 |
| 15 | realworld | x-preview-f-free | high | graphify | 0 |
| 16 | realworld | x-preview-f-free | high | ponytail | 0 |
| 17 | realworld | x-preview-f-free | high | python-harness | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 26 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 27 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 28 | realworld | x-preview-f-free | high | supermemory | 0 |
| 29 | realworld | x-preview-f-free | high | tdd | 0 |
| 30 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 31 | task_manager | x-preview-f-free | high | baseline | 1.7 |

### Creation input tokens

Lower is better. Input tokens used by initial checkpoint attempts.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | x-preview-f-free | high | ponytail | 234,726 |
| 2 | realworld | x-preview-f-free | high | supermemory | 270,951 |
| 3 | realworld | x-preview-f-free | high | tdd | 275,550 |
| 4 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 291,872 |
| 5 | realworld | x-preview-f-free | high | baseline | 296,046 |
| 6 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 317,730 |
| 7 | realworld | x-preview-f-free | high | doorstop | 333,660 |
| 8 | realworld | deepseek-v4-flash | high | baseline | 349,724 |
| 9 | realworld | x-preview-f-free | high | benjamin-plus-skill | 351,220 |
| 10 | realworld | glm-5.3-flash | high | baseline | 354,603 |
| 11 | realworld | muse-spark-1.3-contributor | medium | baseline | 376,686 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 378,424 |
| 13 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 380,970 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 381,832 |
| 15 | realworld | x-preview-f-free | high | reclaim-code-entropy | 388,386 |
| 16 | realworld | x-preview-f-free | high | strictdoc | 398,588 |
| 17 | realworld | omen-alpha | high | baseline | 454,922 |
| 18 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 465,912 |
| 19 | realworld | x-preview-f-free | high | graphify | 484,474 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 534,486 |
| 21 | realworld | deepseek-v4-flash | max | baseline | 556,860 |
| 22 | realworld | muse-spark-1.2-contributor | medium | baseline | 580,285 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 582,129 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 651,188 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 668,908 |
| 26 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 706,788 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 718,174 |
| 28 | realworld | x-preview-f-free | high | python-harness | 725,810 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 885,262 |
| 30 | task_manager | x-preview-f-free | high | baseline | 900,910 |
| 31 | realworld | gpt-5.6-luna | max | baseline | 5,420,944 |

### Creation output tokens

Lower is better. Output tokens used by initial checkpoint attempts.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | x-preview-f-free | high | ponytail | 29,180 |
| 2 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 35,758 |
| 3 | realworld | x-preview-f-free | high | benjamin-plus-skill | 35,802 |
| 4 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 39,191 |
| 5 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 41,727 |
| 6 | realworld | x-preview-f-free | high | reclaim-code-entropy | 42,193 |
| 7 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 42,498 |
| 8 | realworld | x-preview-f-free | high | baseline | 43,178 |
| 9 | realworld | x-preview-f-free | high | tdd | 43,670 |
| 10 | realworld | omen-alpha | high | baseline | 44,249 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 47,168 |
| 12 | realworld | muse-spark-1.3-contributor | medium | baseline | 52,362 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 55,019 |
| 14 | realworld | x-preview-f-free | high | supermemory | 55,271 |
| 15 | realworld | x-preview-f-free | high | graphify | 59,561 |
| 16 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 59,699 |
| 17 | realworld | glm-5.3-flash | high | baseline | 61,039 |
| 18 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 62,509 |
| 19 | realworld | x-preview-f-free | high | strictdoc | 62,940 |
| 20 | realworld | x-preview-f-free | high | doorstop | 66,256 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 68,887 |
| 22 | realworld | deepseek-v4-flash | max | baseline | 69,984 |
| 23 | realworld | deepseek-v4-flash | high | baseline | 70,493 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 72,708 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 73,702 |
| 26 | realworld | x-preview-f-free | high | python-harness | 80,603 |
| 27 | realworld | muse-spark-1.2-contributor | medium | baseline | 85,495 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 87,843 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 88,514 |
| 30 | realworld | gpt-5.6-luna | max | baseline | 137,280 |
| 31 | task_manager | x-preview-f-free | high | baseline | 202,798 |

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
| 24 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 81,140 |
| 25 | realworld | deepseek-v4-flash | max | baseline | 86,585 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 87,569 |
| 27 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 90,941 |
| 28 | realworld | x-preview-f-free | high | python-harness | 144,495 |
| 29 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 309,366 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 340,264 |
| 31 | realworld | gpt-5.6-luna | max | baseline | 405,590 |

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
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 6,034 |
| 21 | realworld | deepseek-v4-flash | high | baseline | 7,724 |
| 22 | realworld | gpt-5.6-luna | max | baseline | 7,853 |
| 23 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 8,562 |
| 24 | realworld | omen-alpha | high | baseline | 8,797 |
| 25 | realworld | x-preview-f-free | high | supermemory | 12,466 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 12,637 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 17,608 |
| 28 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 18,577 |
| 29 | realworld | deepseek-v4-flash | max | baseline | 25,778 |
| 30 | realworld | x-preview-f-free | high | python-harness | 27,421 |
| 31 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 39,710 |

### Cached tokens

Lower is better. Prompt tokens read from the provider cache.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | x-preview-f-free | high | ponytail | 1,587,520 |
| 2 | realworld | x-preview-f-free | high | benjamin-plus-skill | 1,937,600 |
| 3 | realworld | x-preview-f-free | high | baseline | 2,606,272 |
| 4 | realworld | muse-spark-1.3-contributor | medium | baseline | 2,883,925 |
| 5 | realworld | x-preview-f-free | high | reclaim-code-entropy | 3,180,960 |
| 6 | realworld | omen-alpha | high | baseline | 3,185,472 |
| 7 | realworld | x-preview-f-free | high | tdd | 3,187,136 |
| 8 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 3,319,648 |
| 9 | realworld | x-preview-f-free | high | supermemory | 3,368,448 |
| 10 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 3,458,560 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 3,931,456 |
| 12 | realworld | deepseek-v4-flash | high | baseline | 4,285,824 |
| 13 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 4,528,864 |
| 14 | realworld | x-preview-f-free | high | graphify | 4,687,008 |
| 15 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 4,845,120 |
| 16 | realworld | glm-5.3-flash | high | baseline | 4,996,736 |
| 17 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 5,160,320 |
| 18 | realworld | gpt-5.6-luna | max | baseline | 5,285,888 |
| 19 | realworld | x-preview-f-free | high | doorstop | 5,743,136 |
| 20 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 5,749,696 |
| 21 | realworld | x-preview-f-free | high | strictdoc | 5,786,336 |
| 22 | realworld | deepseek-v4-flash | max | baseline | 5,971,072 |
| 23 | realworld | muse-spark-1.2-contributor | medium | baseline | 6,222,961 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 9,920,640 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 13,620,672 |
| 26 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 13,633,472 |
| 27 | realworld | x-preview-f-free | high | python-harness | 14,413,824 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 15,953,920 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 16,284,800 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 17,358,592 |
| 31 | task_manager | x-preview-f-free | high | baseline | 17,479,296 |

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
| 25 | realworld | muse-spark-1.2-contributor | medium | baseline | 48,686 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 49,827 |
| 27 | realworld | glm-5.3-flash | high | baseline | 56,413 |
| 28 | realworld | deepseek-v4-flash | high | baseline | 69,085 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 70,656 |
| 30 | realworld | deepseek-v4-flash | max | baseline | 74,460 |
| 31 | realworld | gpt-5.6-luna | max | baseline | 80,615 |

### All input tokens

Lower is better. Total input tokens across checkpoints, including rework and retries.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | x-preview-f-free | high | ponytail | 278,688 |
| 2 | realworld | x-preview-f-free | high | baseline | 293,733 |
| 3 | realworld | x-preview-f-free | high | tdd | 304,128 |
| 4 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 304,423 |
| 5 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 327,829 |
| 6 | realworld | x-preview-f-free | high | doorstop | 368,711 |
| 7 | realworld | x-preview-f-free | high | benjamin-plus-skill | 376,088 |
| 8 | realworld | muse-spark-1.3-contributor | medium | baseline | 376,686 |
| 9 | realworld | glm-5.3-flash | high | baseline | 384,355 |
| 10 | realworld | deepseek-v4-flash | high | baseline | 392,075 |
| 11 | realworld | x-preview-f-free | high | supermemory | 396,536 |
| 12 | realworld | x-preview-f-free | high | strictdoc | 415,252 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 422,227 |
| 14 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 427,378 |
| 15 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 430,492 |
| 16 | realworld | x-preview-f-free | high | reclaim-code-entropy | 438,210 |
| 17 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 523,020 |
| 18 | realworld | omen-alpha | high | baseline | 528,103 |
| 19 | realworld | x-preview-f-free | high | graphify | 544,445 |
| 20 | realworld | muse-spark-1.2-contributor | medium | baseline | 580,285 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 622,055 |
| 22 | realworld | deepseek-v4-flash | max | baseline | 643,445 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 663,268 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 701,469 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 719,320 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 748,059 |
| 27 | task_manager | x-preview-f-free | high | baseline | 812,392 |
| 28 | realworld | x-preview-f-free | high | python-harness | 870,305 |
| 29 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1,016,154 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 1,225,525 |
| 31 | realworld | gpt-5.6-luna | max | baseline | 5,826,534 |

### All output tokens

Lower is better. Total output tokens across checkpoints, including rework.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | x-preview-f-free | high | ponytail | 29,696 |
| 2 | realworld | x-preview-f-free | high | benjamin-plus-skill | 38,632 |
| 3 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 41,792 |
| 4 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 42,056 |
| 5 | realworld | x-preview-f-free | high | tdd | 44,328 |
| 6 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 45,002 |
| 7 | realworld | x-preview-f-free | high | baseline | 45,486 |
| 8 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 45,890 |
| 9 | realworld | x-preview-f-free | high | reclaim-code-entropy | 46,428 |
| 10 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 50,249 |
| 11 | realworld | muse-spark-1.3-contributor | medium | baseline | 52,362 |
| 12 | realworld | omen-alpha | high | baseline | 53,046 |
| 13 | realworld | x-preview-f-free | high | graphify | 53,665 |
| 14 | realworld | x-preview-f-free | high | supermemory | 57,895 |
| 15 | realworld | x-preview-f-free | high | strictdoc | 61,442 |
| 16 | realworld | x-preview-f-free | high | doorstop | 61,858 |
| 17 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 63,581 |
| 18 | realworld | glm-5.3-flash | high | baseline | 65,725 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 73,438 |
| 20 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 75,330 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 77,816 |
| 22 | realworld | deepseek-v4-flash | high | baseline | 78,217 |
| 23 | realworld | muse-spark-1.2-contributor | medium | baseline | 85,495 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 90,231 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 91,310 |
| 26 | realworld | deepseek-v4-flash | max | baseline | 95,762 |
| 27 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 99,409 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 100,480 |
| 29 | realworld | x-preview-f-free | high | python-harness | 108,024 |
| 30 | realworld | gpt-5.6-luna | max | baseline | 145,133 |
| 31 | task_manager | x-preview-f-free | high | baseline | 186,779 |

### Transient input tokens

Lower is better. Input tokens used by transient retry attempts.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 3 | realworld | glm-5.3-flash | high | baseline | 0 |
| 4 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 5 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 6 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 7 | realworld | omen-alpha | high | baseline | 0 |
| 8 | realworld | x-preview-f-free | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 10 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | doorstop | 0 |
| 15 | realworld | x-preview-f-free | high | graphify | 0 |
| 16 | realworld | x-preview-f-free | high | ponytail | 0 |
| 17 | realworld | x-preview-f-free | high | python-harness | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 26 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 27 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 28 | realworld | x-preview-f-free | high | supermemory | 0 |
| 29 | realworld | x-preview-f-free | high | tdd | 0 |
| 30 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 31 | task_manager | x-preview-f-free | high | baseline | 0 |

### Transient output tokens

Lower is better. Output tokens used by transient retry attempts.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 3 | realworld | glm-5.3-flash | high | baseline | 0 |
| 4 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 5 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 6 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 7 | realworld | omen-alpha | high | baseline | 0 |
| 8 | realworld | x-preview-f-free | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 10 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | doorstop | 0 |
| 15 | realworld | x-preview-f-free | high | graphify | 0 |
| 16 | realworld | x-preview-f-free | high | ponytail | 0 |
| 17 | realworld | x-preview-f-free | high | python-harness | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 26 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 27 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 28 | realworld | x-preview-f-free | high | supermemory | 0 |
| 29 | realworld | x-preview-f-free | high | tdd | 0 |
| 30 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 31 | task_manager | x-preview-f-free | high | baseline | 0 |

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
| 18 | realworld | glm-5.3-flash | high | baseline | 281 |
| 19 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 286 |
| 20 | realworld | x-preview-f-free | high | strictdoc | 298 |
| 21 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 306 |
| 22 | realworld | x-preview-f-free | high | doorstop | 352 |
| 23 | realworld | gpt-5.6-luna | max | baseline | 355 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 393 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 421 |
| 26 | realworld | x-preview-f-free | high | python-harness | 440 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 461 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 483 |
| 29 | task_manager | x-preview-f-free | high | baseline | 496 |
| 30 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 509 |
| 31 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 617 |

### Semantic rework attempts

Lower is better. Additional semantic attempts after the initial solve, per run.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 2 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 3 | realworld | deepseek-v4-flash | high | baseline | 1 |
| 4 | realworld | deepseek-v4-flash | max | baseline | 1 |
| 5 | realworld | glm-5.3-flash | high | baseline | 1 |
| 6 | realworld | gpt-5.6-luna | max | baseline | 1 |
| 7 | realworld | x-preview-f-free | high | benjamin-plus-skill | 1 |
| 8 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 1 |
| 9 | realworld | x-preview-f-free | high | graphify | 1 |
| 10 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 1 |
| 11 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 1 |
| 12 | realworld | x-preview-f-free | high | reclaim-code-entropy | 1 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1.5 |
| 14 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 1.5 |
| 15 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 1.5 |
| 16 | realworld | x-preview-f-free | high | baseline | 1.7 |
| 17 | realworld | x-preview-f-free | high | doorstop | 2 |
| 18 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 2 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 2 |
| 20 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 2.5 |
| 21 | realworld | x-preview-f-free | high | supermemory | 2.5 |
| 22 | realworld | x-preview-f-free | high | tdd | 2.5 |
| 23 | realworld | omen-alpha | high | baseline | 3 |
| 24 | realworld | x-preview-f-free | high | ponytail | 3 |
| 25 | realworld | x-preview-f-free | high | python-harness | 3 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 3 |
| 27 | task_manager | x-preview-f-free | high | baseline | 3 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 4 |
| 29 | realworld | x-preview-f-free | high | strictdoc | 4 |
| 30 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 6 |
| 31 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 15.5 |

### Transient retries

Lower is better. High-confidence provider truncation retries, per run.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 3 | realworld | glm-5.3-flash | high | baseline | 0 |
| 4 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 5 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 6 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 7 | realworld | omen-alpha | high | baseline | 0 |
| 8 | realworld | x-preview-f-free | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 10 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | doorstop | 0 |
| 15 | realworld | x-preview-f-free | high | graphify | 0 |
| 16 | realworld | x-preview-f-free | high | ponytail | 0 |
| 17 | realworld | x-preview-f-free | high | python-harness | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 26 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 27 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 28 | realworld | x-preview-f-free | high | supermemory | 0 |
| 29 | realworld | x-preview-f-free | high | tdd | 0 |
| 30 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 31 | task_manager | x-preview-f-free | high | baseline | 0 |

### Provider truncations

Lower is better. Observed provider truncation events, per run.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 3 | realworld | glm-5.3-flash | high | baseline | 0 |
| 4 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 5 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 6 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 7 | realworld | omen-alpha | high | baseline | 0 |
| 8 | realworld | x-preview-f-free | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 10 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | doorstop | 0 |
| 15 | realworld | x-preview-f-free | high | graphify | 0 |
| 16 | realworld | x-preview-f-free | high | ponytail | 0 |
| 17 | realworld | x-preview-f-free | high | python-harness | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 26 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 27 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 28 | realworld | x-preview-f-free | high | supermemory | 0 |
| 29 | realworld | x-preview-f-free | high | tdd | 0 |
| 30 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 31 | task_manager | x-preview-f-free | high | baseline | 0 |

### Transient recoveries

Lower is better. Truncation retries that resolved the checkpoint, per run.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 3 | realworld | glm-5.3-flash | high | baseline | 0 |
| 4 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 5 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 6 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 7 | realworld | omen-alpha | high | baseline | 0 |
| 8 | realworld | x-preview-f-free | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 10 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | doorstop | 0 |
| 15 | realworld | x-preview-f-free | high | graphify | 0 |
| 16 | realworld | x-preview-f-free | high | ponytail | 0 |
| 17 | realworld | x-preview-f-free | high | python-harness | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 26 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 27 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 28 | realworld | x-preview-f-free | high | supermemory | 0 |
| 29 | realworld | x-preview-f-free | high | tdd | 0 |
| 30 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 31 | task_manager | x-preview-f-free | high | baseline | 0 |

### Truncations unresolved

Lower is better. Checkpoints still truncated after retries, per run.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-v4-flash | high | baseline | 0 |
| 2 | realworld | deepseek-v4-flash | max | baseline | 0 |
| 3 | realworld | glm-5.3-flash | high | baseline | 0 |
| 4 | realworld | gpt-5.6-luna | max | baseline | 0 |
| 5 | realworld | muse-spark-1.2-contributor | medium | baseline | 0 |
| 6 | realworld | muse-spark-1.3-contributor | medium | baseline | 0 |
| 7 | realworld | omen-alpha | high | baseline | 0 |
| 8 | realworld | x-preview-f-free | high | baseline | 0 |
| 9 | realworld | x-preview-f-free | high | benjamin-plus-skill | 0 |
| 10 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 0 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 0 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 0 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 0 |
| 14 | realworld | x-preview-f-free | high | doorstop | 0 |
| 15 | realworld | x-preview-f-free | high | graphify | 0 |
| 16 | realworld | x-preview-f-free | high | ponytail | 0 |
| 17 | realworld | x-preview-f-free | high | python-harness | 0 |
| 18 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 0 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 0 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 0 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 0 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 0 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 0 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 0 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 0 |
| 26 | realworld | x-preview-f-free | high | reclaim-code-entropy | 0 |
| 27 | realworld | x-preview-f-free | high | strictdoc | 0 |
| 28 | realworld | x-preview-f-free | high | supermemory | 0 |
| 29 | realworld | x-preview-f-free | high | tdd | 0 |
| 30 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 0 |
| 31 | task_manager | x-preview-f-free | high | baseline | 0 |

### Normalized cost

Lower is better. Cost normalized with the versioned pricing configuration.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | deepseek-v4-flash | high | baseline | $0.00 |
| 2 | realworld | deepseek-v4-flash | max | baseline | $0.00 |
| 3 | realworld | glm-5.3-flash | high | baseline | $0.00 |
| 4 | realworld | muse-spark-1.2-contributor | medium | baseline | $0.00 |
| 5 | realworld | muse-spark-1.3-contributor | medium | baseline | $0.00 |
| 6 | realworld | omen-alpha | high | baseline | $0.00 |
| 7 | realworld | x-preview-f-free | high | baseline | $0.00 |
| 8 | realworld | x-preview-f-free | high | benjamin-plus-skill | $0.00 |
| 9 | realworld | x-preview-f-free | high | combo-supermemory-graphify | $0.00 |
| 10 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | $0.00 |
| 11 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | $0.00 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | $0.00 |
| 13 | realworld | x-preview-f-free | high | doorstop | $0.00 |
| 14 | realworld | x-preview-f-free | high | graphify | $0.00 |
| 15 | realworld | x-preview-f-free | high | ponytail | $0.00 |
| 16 | realworld | x-preview-f-free | high | python-harness | $0.00 |
| 17 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | $0.00 |
| 18 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | $0.00 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | $0.00 |
| 20 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | $0.00 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | $0.00 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | $0.00 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | $0.00 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | $0.00 |
| 25 | realworld | x-preview-f-free | high | reclaim-code-entropy | $0.00 |
| 26 | realworld | x-preview-f-free | high | strictdoc | $0.00 |
| 27 | realworld | x-preview-f-free | high | supermemory | $0.00 |
| 28 | realworld | x-preview-f-free | high | tdd | $0.00 |
| 29 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | $0.00 |
| 30 | task_manager | x-preview-f-free | high | baseline | $0.00 |
| 31 | realworld | gpt-5.6-luna | max | baseline | $2.79 |

### Elapsed time

Lower is better. Sum of agent inference time across checkpoints.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | muse-spark-1.3-contributor | medium | baseline | 25.1m |
| 2 | realworld | x-preview-f-free | high | ponytail | 31.1m |
| 3 | realworld | deepseek-v4-flash | high | baseline | 37.3m |
| 4 | realworld | deepseek-v4-flash | max | baseline | 39.9m |
| 5 | realworld | x-preview-f-free | high | tdd | 43.5m |
| 6 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 43.9m |
| 7 | realworld | x-preview-f-free | high | benjamin-plus-skill | 45.1m |
| 8 | realworld | x-preview-f-free | high | supermemory | 47.3m |
| 9 | realworld | x-preview-f-free | high | reclaim-code-entropy | 49.5m |
| 10 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 50.7m |
| 11 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 51.2m |
| 12 | realworld | omen-alpha | high | baseline | 51.2m |
| 13 | realworld | muse-spark-1.2-contributor | medium | baseline | 51.6m |
| 14 | realworld | gpt-5.6-luna | max | baseline | 53.8m |
| 15 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 54.6m |
| 16 | realworld | x-preview-f-free | high | baseline | 58.1m |
| 17 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 58.9m |
| 18 | realworld | x-preview-f-free | high | strictdoc | 65.1m |
| 19 | realworld | x-preview-f-free | high | graphify | 69.8m |
| 20 | realworld | x-preview-f-free | high | doorstop | 72.5m |
| 21 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 75.3m |
| 22 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 83.5m |
| 23 | realworld | glm-5.3-flash | high | baseline | 85.2m |
| 24 | realworld | x-preview-f-free | high | python-harness | 95.8m |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 99.2m |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 102.0m |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 118.2m |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 123.9m |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 156.0m |
| 30 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 161.6m |
| 31 | task_manager | x-preview-f-free | high | baseline | 215.6m |

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
| 11 | realworld | omen-alpha | high | baseline | 1188 |
| 12 | realworld | glm-5.3-flash | high | baseline | 1324 |
| 13 | realworld | x-preview-f-free | high | reclaim-code-entropy | 1394 |
| 14 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 1404 |
| 15 | realworld | x-preview-f-free | high | doorstop | 1425 |
| 16 | realworld | muse-spark-1.2-contributor | medium | baseline | 1502 |
| 17 | realworld | deepseek-v4-flash | high | baseline | 1631 |
| 18 | realworld | muse-spark-1.3-contributor | medium | baseline | 1632 |
| 19 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 1745 |
| 20 | realworld | deepseek-v4-flash | max | baseline | 1811 |
| 21 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 1841 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 1841.5 |
| 23 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1861 |
| 24 | realworld | x-preview-f-free | high | tdd | 2536.5 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 2654 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 3047 |
| 27 | realworld | x-preview-f-free | high | python-harness | 3357 |
| 28 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 3487 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 3581.5 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 3612 |
| 31 | task_manager | x-preview-f-free | high | baseline | 4686.7 |

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
| 18 | realworld | glm-5.3-flash | high | baseline | 14 |
| 19 | realworld | deepseek-v4-flash | max | baseline | 16 |
| 20 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 16 |
| 21 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 16.5 |
| 22 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 19 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 19 |
| 24 | realworld | x-preview-f-free | high | tdd | 19 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 24 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 24 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 44.5 |
| 28 | realworld | x-preview-f-free | high | python-harness | 49 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 49 |
| 30 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 54 |
| 31 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 54.5 |

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
| 11 | realworld | glm-5.3-flash | high | baseline | 1535 |
| 12 | realworld | deepseek-v4-flash | high | baseline | 1627 |
| 13 | realworld | x-preview-f-free | high | doorstop | 1673 |
| 14 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 1720.5 |
| 15 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 1832 |
| 16 | realworld | deepseek-v4-flash | max | baseline | 1904 |
| 17 | realworld | muse-spark-1.2-contributor | medium | baseline | 1929 |
| 18 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 1944 |
| 19 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 2001 |
| 20 | realworld | muse-spark-1.3-contributor | medium | baseline | 2104 |
| 21 | realworld | x-preview-f-free | high | tdd | 2797 |
| 22 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 3133 |
| 23 | realworld | x-preview-f-free | high | benjamin-plus-skill | 3278.5 |
| 24 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 3683.5 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 3782 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 4000 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 4070 |
| 28 | task_manager | x-preview-f-free | high | baseline | 5738.3 |
| 29 | realworld | x-preview-f-free | high | python-harness | 9125 |
| 30 | realworld | x-preview-f-free | high | reclaim-code-entropy | 9221 |
| 31 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 11422 |

### Dependencies

Lower is better as a complexity measure. Dependencies added by the solution.

| Rank | Problem | Model | Thinking | Harness | Value |
|----:|---------|-------|----------|---------|------:|
| 1 | realworld | glm-5.3-flash | high | baseline | 4 |
| 2 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 4 |
| 3 | realworld | deepseek-v4-flash | max | baseline | 5 |
| 4 | realworld | gpt-5.6-luna | max | baseline | 5 |
| 5 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 5 |
| 6 | realworld | x-preview-f-free | high | doorstop | 5.5 |
| 7 | realworld | x-preview-f-free | high | graphify | 5.5 |
| 8 | realworld | x-preview-f-free | high | strictdoc | 5.5 |
| 9 | task_manager | x-preview-f-free | high | baseline | 5.7 |
| 10 | realworld | muse-spark-1.2-contributor | medium | baseline | 6 |
| 11 | realworld | muse-spark-1.3-contributor | medium | baseline | 6 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 6 |
| 13 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 6 |
| 14 | realworld | x-preview-f-free | high | reclaim-code-entropy | 6 |
| 15 | realworld | x-preview-f-free | high | thermo-nuclear-code-quality-review | 6 |
| 16 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 6.5 |
| 17 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 7 |
| 18 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 7 |
| 19 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 7.5 |
| 20 | realworld | deepseek-v4-flash | high | baseline | 8 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 9 |
| 22 | realworld | x-preview-f-free | high | python-harness | 10 |
| 23 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 10 |
| 24 | realworld | x-preview-f-free | high | baseline | 10.7 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 11 |
| 26 | realworld | x-preview-f-free | high | benjamin-plus-skill | 11.5 |
| 27 | realworld | x-preview-f-free | high | supermemory | 14.5 |
| 28 | realworld | x-preview-f-free | high | ponytail | 15 |
| 29 | realworld | x-preview-f-free | high | tdd | 18.5 |
| 30 | realworld | omen-alpha | high | baseline | 22 |
| 31 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 26.5 |

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
| 8 | realworld | x-preview-f-free | high | supermemory | 207.5 |
| 9 | realworld | x-preview-f-free | high | baseline | 212.7 |
| 10 | realworld | x-preview-f-free | high | combo-supermemory-graphify | 228 |
| 11 | realworld | glm-5.3-flash | high | baseline | 242 |
| 12 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | 248 |
| 13 | realworld | x-preview-f-free | high | reclaim-code-entropy | 332.5 |
| 14 | realworld | x-preview-f-free | high | doorstop | 377.5 |
| 15 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | 403 |
| 16 | realworld | deepseek-v4-flash | high | baseline | 407 |
| 17 | realworld | muse-spark-1.2-contributor | medium | baseline | 458 |
| 18 | realworld | muse-spark-1.3-contributor | medium | baseline | 487 |
| 19 | realworld | deepseek-v4-flash | max | baseline | 514 |
| 20 | realworld | x-preview-f-free | high | python-harness+ponytail+tdd+graphify+benjamin-plus-skill+reclaim-code-entropy | 552 |
| 21 | realworld | x-preview-f-free | high | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill | 595.5 |
| 22 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | 621 |
| 23 | realworld | x-preview-f-free | high | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd | 653 |
| 24 | realworld | x-preview-f-free | high | tdd | 748.5 |
| 25 | realworld | x-preview-f-free | high | python-harness-v1.3.0+strictdoc | 825 |
| 26 | realworld | x-preview-f-free | high | python-harness-v1.3.0+graphify | 834 |
| 27 | realworld | x-preview-f-free | high | python-harness-v1.3.0+doorstop | 838 |
| 28 | task_manager | x-preview-f-free | high | baseline | 931.7 |
| 29 | realworld | x-preview-f-free | high | python-harness-v1.3.0 | 941.5 |
| 30 | realworld | x-preview-f-free | high | python-harness | 968 |
| 31 | realworld | x-preview-f-free | high | python-harness-v1.2.3 | 992.5 |

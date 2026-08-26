# realworld-opencode-x-preview-f-free-high-python-harness-v1.2.3-20260825

| | |
|---|---|
| Problem | `realworld` |
| Model | `x-preview-f-free` · thinking `high` |
| Agent | opencode · provider `opencode_auth` · `1.14.33` |
| N | python-harness-v1.2.3=2 · python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill=2 · python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill=2 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

Creation/Rework token metrics use per-attempt usage; `-` means unavailable.
Failed checkpoints include checkpoints repaired by rework; Rework = All - Create when possible.

| Metric | python-harness-v1.2.3 | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill |
|--------|---------:|---------:|---------:|
| CP passed/total | 13/14 | 14/14 | 13.5/14 |
| Failed checkpoints | 2.5 | 1 | 2 |
| Repeated attempts | 4 | 1.5 | 3 |
| Regressions | 0 | 0 | 0 |
| Creation input tokens | 885,262 | 668,908 | 582,129 |
| Creation output tokens | 73,702 | 41,727 | 35,758 |
| Rework input tokens | 340,264 | 32,560 | 81,140 |
| Rework output tokens | 17,608 | 3,275 | 6,034 |
| Transient input tokens | 0 | 0 | 0 |
| Transient output tokens | 0 | 0 | 0 |
| Semantic rework attempts | 4 | 1.5 | 3 |
| Transient retries | 0 | 0 | 0 |
| Provider truncations | 0 | 0 | 0 |
| Transient recoveries | 0 | 0 | 0 |
| Truncations unresolved | 0 | 0 | 0 |
| All input tokens | 1,225,525 | 701,469 | 663,268 |
| All output tokens | 91,310 | 45,002 | 41,792 |
| Cached tokens | 17,358,592 | 5,160,320 | 4,528,864 |
| LLM requests | 483 | 267 | 229 |
| Normalized cost | $0.00 | $0.00 | $0.00 |
| Elapsed | 118.2m | 51.2m | 50.7m |
| Final LOC | 3581.5 | 1404 | 1841.5 |
| Python modules | 44.5 | 24 | 19 |
| Changed LOC | 3683.5 | 1720.5 | 1944 |
| Dependencies | 26.5 | 7.5 | 6.5 |
| Complexity | 992.5 | 403 | 595.5 |

## Δ vs baseline

| Metric | python-harness-v1.2.3 | python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill | python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill |
|--------|---------:|---------:|---------:|
| CP passed/total | - | - | - |
| Failed checkpoints | - | - | - |
| Repeated attempts | - | - | - |
| Regressions | - | - | - |
| Creation input tokens | - | - | - |
| Creation output tokens | - | - | - |
| Rework input tokens | - | - | - |
| Rework output tokens | - | - | - |
| Transient input tokens | - | - | - |
| Transient output tokens | - | - | - |
| Semantic rework attempts | - | - | - |
| Transient retries | - | - | - |
| Provider truncations | - | - | - |
| Transient recoveries | - | - | - |
| Truncations unresolved | - | - | - |
| All input tokens | - | - | - |
| All output tokens | - | - | - |
| Cached tokens | - | - | - |
| LLM requests | - | - | - |
| Normalized cost | - | - | - |
| Elapsed | - | - | - |
| Final LOC | - | - | - |
| Python modules | - | - | - |
| Changed LOC | - | - | - |
| Dependencies | - | - | - |
| Complexity | - | - | - |

## Notes

- No paired baseline/harness means to summarize.
- Rework python-harness-v1.2.3: 8 semantic retries (13 total attempts), 3 fixed, 2 unresolved.
- Rework python-harness-v1.2.3+ponytail+graphify+benjamin-plus-skill: 3 semantic retries (5 total attempts), 2 fixed, 0 unresolved.
- Rework python-harness-v1.2.3+ponytail+tdd+graphify+benjamin-plus-skill: 6 semantic retries (10 total attempts), 3 fixed, 1 unresolved.

Raw (local only): `results/realworld-opencode-x-preview-f-free-high-python-harness-v1.2.3-20260825/`, `reports/realworld-opencode-x-preview-f-free-high-python-harness-v1.2.3-20260825/`.

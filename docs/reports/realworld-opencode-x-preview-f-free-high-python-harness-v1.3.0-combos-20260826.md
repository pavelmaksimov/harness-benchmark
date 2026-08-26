# realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-combos-20260826

| | |
|---|---|
| Problem | `realworld` |
| Model | `x-preview-f-free` · thinking `high` |
| Agent | opencode · provider `opencode_auth` · `1.14.33` |
| N | python-harness-v1.3.0+doorstop=1 · python-harness-v1.3.0+graphify=1 · python-harness-v1.3.0+strictdoc=1 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

Creation/Rework token metrics use per-attempt usage; `-` means unavailable.
Failed checkpoints include checkpoints repaired by rework; Rework = All - Create when possible.

| Metric | python-harness-v1.3.0+doorstop | python-harness-v1.3.0+graphify | python-harness-v1.3.0+strictdoc |
|--------|---------:|---------:|---------:|
| CP passed/total | 13/14 | 14/14 | 14/14 |
| Failed checkpoints | 1 | 1 | 1 |
| Repeated attempts | 2 | 1 | 2 |
| Regressions | 0 | 0 | 0 |
| Creation input tokens | 534,486 | 718,174 | 465,912 |
| Creation output tokens | 87,843 | 88,514 | 68,887 |
| Rework input tokens | 87,569 | 29,885 | 57,108 |
| Rework output tokens | 12,637 | 1,717 | 4,551 |
| Transient input tokens | 0 | 0 | 0 |
| Transient output tokens | 0 | 0 | 0 |
| Semantic rework attempts | 2 | 1 | 2 |
| Transient retries | 0 | 0 | 0 |
| Provider truncations | 0 | 0 | 0 |
| Transient recoveries | 0 | 0 | 0 |
| Truncations unresolved | 0 | 0 | 0 |
| All input tokens | 622,055 | 748,059 | 523,020 |
| All output tokens | 100,480 | 90,231 | 73,438 |
| Cached tokens | 16,284,800 | 15,953,920 | 9,920,640 |
| LLM requests | 617 | 461 | 421 |
| Normalized cost | $0.00 | $0.00 | $0.00 |
| Elapsed | 156.0m | 123.9m | 99.2m |
| Final LOC | 3612 | 3047 | 2654 |
| Python modules | 54 | 49 | 24 |
| Changed LOC | 4070 | 3782 | 3133 |
| Dependencies | 11 | 7 | 9 |
| Complexity | 838 | 834 | 825 |

## Δ vs baseline

| Metric | python-harness-v1.3.0+doorstop | python-harness-v1.3.0+graphify | python-harness-v1.3.0+strictdoc |
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
- Rework python-harness-v1.3.0+doorstop: 2 semantic retries (3 total attempts), 0 fixed, 1 unresolved.
- Rework python-harness-v1.3.0+graphify: 1 semantic retries (2 total attempts), 1 fixed, 0 unresolved.
- Rework python-harness-v1.3.0+strictdoc: 2 semantic retries (3 total attempts), 1 fixed, 0 unresolved.
- Incomplete runs excluded from averages: python-harness-v1.3.0+strictdoc=1.

Raw (local only): `results/realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-combos-20260826/`, `reports/realworld-opencode-x-preview-f-free-high-python-harness-v1.3.0-combos-20260826/`.

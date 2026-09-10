# realworld-opencode-go-dsflash-v41-high-baseline-20260910

| | |
|---|---|
| Problem | `realworld` |
| Model | `deepseek-flash` · thinking `high` |
| Agent | opencode · provider `opencode_auth` · `1.14.33` |
| N | baseline=1 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

Creation/Rework token metrics use per-attempt usage; `-` means unavailable.
Failed checkpoints include checkpoints repaired by rework; Rework = All - Create when possible.

| Metric | baseline |
|--------|---------:|
| CP passed/total | 14/14 |
| Failed checkpoints | 1 |
| Repeated attempts | 1 |
| Regressions | 0 |
| Creation input tokens | 264,081 |
| Creation output tokens | 50,431 |
| Rework input tokens | 75,623 |
| Rework output tokens | 5,790 |
| Transient input tokens | 0 |
| Transient output tokens | 0 |
| Semantic rework attempts | 1 |
| Transient retries | 0 |
| Provider truncations | 0 |
| Transient recoveries | 0 |
| Truncations unresolved | 0 |
| All input tokens | 339,704 |
| All output tokens | 56,221 |
| Cached tokens | 5,882,752 |
| Reasoning tokens | 46,081 |
| LLM requests | 270 |
| Normalized cost | $0.00 |
| Elapsed | 20.8m |
| Final LOC | 1122 |
| Python modules | 13 |
| Changed LOC | 1320 |
| Dependencies | 5 |
| Complexity | 202 |

## Notes

- No paired baseline/harness means to summarize.
- Rework baseline: 1 semantic retries (2 total attempts), 1 fixed, 0 unresolved.

Raw (local only): `results/realworld-opencode-go-dsflash-v41-high-baseline-20260910/`, `reports/realworld-opencode-go-dsflash-v41-high-baseline-20260910/`.

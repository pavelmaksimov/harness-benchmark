# realworld-opencode-go-dsflash-max-baseline-20260907

| | |
|---|---|
| Problem | `realworld` |
| Model | `deepseek-v4-flash` · thinking `max` |
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
| Creation input tokens | 556,860 |
| Creation output tokens | 69,984 |
| Rework input tokens | 86,585 |
| Rework output tokens | 25,778 |
| Transient input tokens | 0 |
| Transient output tokens | 0 |
| Semantic rework attempts | 1 |
| Transient retries | 0 |
| Provider truncations | 0 |
| Transient recoveries | 0 |
| Truncations unresolved | 0 |
| All input tokens | 643,445 |
| All output tokens | 95,762 |
| Cached tokens | 5,971,072 |
| Reasoning tokens | 74,460 |
| LLM requests | 252 |
| Normalized cost | $0.00 |
| Elapsed | 39.9m |
| Final LOC | 1811 |
| Python modules | 16 |
| Changed LOC | 1904 |
| Dependencies | 5 |
| Complexity | 514 |

## Notes

- No paired baseline/harness means to summarize.
- Rework baseline: 1 semantic retries (2 total attempts), 1 fixed, 0 unresolved.

Raw (local only): `results/realworld-opencode-go-dsflash-max-baseline-20260907/`, `reports/realworld-opencode-go-dsflash-max-baseline-20260907/`.

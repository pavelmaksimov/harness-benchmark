# realworld-opencode-go-dsflash-high-baseline-20260908

| | |
|---|---|
| Problem | `realworld` |
| Model | `deepseek-v4-flash` · thinking `high` |
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
| Creation input tokens | 349,724 |
| Creation output tokens | 70,493 |
| Rework input tokens | 42,351 |
| Rework output tokens | 7,724 |
| Transient input tokens | 0 |
| Transient output tokens | 0 |
| Semantic rework attempts | 1 |
| Transient retries | 0 |
| Provider truncations | 0 |
| Transient recoveries | 0 |
| Truncations unresolved | 0 |
| All input tokens | 392,075 |
| All output tokens | 78,217 |
| Cached tokens | 4,285,824 |
| Reasoning tokens | 69,085 |
| LLM requests | 208 |
| Normalized cost | $0.00 |
| Elapsed | 37.3m |
| Final LOC | 1631 |
| Python modules | 6 |
| Changed LOC | 1627 |
| Dependencies | 8 |
| Complexity | 407 |

## Notes

- No paired baseline/harness means to summarize.
- Rework baseline: 1 semantic retries (2 total attempts), 1 fixed, 0 unresolved.

Raw (local only): `results/realworld-opencode-go-dsflash-high-baseline-20260908/`, `reports/realworld-opencode-go-dsflash-high-baseline-20260908/`.

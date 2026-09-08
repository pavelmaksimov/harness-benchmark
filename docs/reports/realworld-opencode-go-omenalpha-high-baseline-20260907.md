# realworld-opencode-go-omenalpha-high-baseline-20260907

| | |
|---|---|
| Problem | `realworld` |
| Model | `omen-alpha` · thinking `high` |
| Agent | opencode · provider `opencode_auth` · `1.14.33` |
| N | baseline=1 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

Creation/Rework token metrics use per-attempt usage; `-` means unavailable.
Failed checkpoints include checkpoints repaired by rework; Rework = All - Create when possible.

| Metric | baseline |
|--------|---------:|
| CP passed/total | 14/14 |
| Failed checkpoints | 2 |
| Repeated attempts | 3 |
| Regressions | 0 |
| Creation input tokens | 454,922 |
| Creation output tokens | 44,249 |
| Rework input tokens | 73,181 |
| Rework output tokens | 8,797 |
| Transient input tokens | 0 |
| Transient output tokens | 0 |
| Semantic rework attempts | 3 |
| Transient retries | 0 |
| Provider truncations | 0 |
| Transient recoveries | 0 |
| Truncations unresolved | 0 |
| All input tokens | 528,103 |
| All output tokens | 53,046 |
| Cached tokens | 3,185,472 |
| Reasoning tokens | 26,581 |
| LLM requests | 232 |
| Normalized cost | $0.00 |
| Elapsed | 51.2m |
| Final LOC | 1188 |
| Python modules | 7 |
| Changed LOC | 1112 |
| Dependencies | 22 |
| Complexity | 190 |

## Notes

- No paired baseline/harness means to summarize.
- Rework baseline: 3 semantic retries (5 total attempts), 2 fixed, 0 unresolved.

Raw (local only): `results/realworld-opencode-go-omenalpha-high-baseline-20260907/`, `reports/realworld-opencode-go-omenalpha-high-baseline-20260907/`.

# rw-opencode-oxalpha-high

| | |
|---|---|
| Problem | `realworld` |
| Model | `x-preview-f-free` · thinking `high` |
| Agent | opencode · provider `opencode_auth` · `1.14.33` |
| N | baseline=1 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

Creation/Rework token metrics use per-attempt usage; `-` means unavailable.
Failed checkpoints include checkpoints repaired by rework; Rework = All - Create when possible.

| Metric | baseline |
|--------|---------:|
| CP passed/total | 14/14 |
| Failed checkpoints | 3 |
| Repeated attempts | 3 |
| Regressions | 0 |
| Creation input tokens | - |
| Creation output tokens | - |
| Rework input tokens | - |
| Rework output tokens | - |
| Transient input tokens | 0 |
| Transient output tokens | 0 |
| Semantic rework attempts | 3 |
| Transient retries | 0 |
| Provider truncations | 0 |
| Transient recoveries | 0 |
| Truncations unresolved | 0 |
| All input tokens | 250,689 |
| All output tokens | 42,406 |
| Cached tokens | 2,396,224 |
| LLM requests | 186 |
| Normalized cost | $0.00 |
| Elapsed | 37.5m |
| Final LOC | 976 |
| Python modules | 5 |
| Changed LOC | 1053 |
| Dependencies | 5 |
| Complexity | 197 |

## Notes

- No paired baseline/harness means to summarize.
- Rework baseline: 3 semantic retries (6 total attempts), 3 fixed, 0 unresolved.

Raw (local only): `results/rw-opencode-oxalpha-high/`, `reports/rw-opencode-oxalpha-high/`.

# tm-opencode-oxalpha-high

| | |
|---|---|
| Problem | `task_manager` |
| Model | `x-preview-f-free` · thinking `high` |
| Agent | opencode · provider `opencode_auth` · `1.14.33` |
| N | baseline=1 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

Creation/Rework token metrics use per-attempt usage; `-` means unavailable.
Failed checkpoints include checkpoints repaired by rework; Rework = All - Create when possible.

| Metric | baseline |
|--------|---------:|
| CP passed/total | 15/15 |
| Failed checkpoints | 7 |
| Repeated attempts | 8 |
| Regressions | 4 |
| Creation input tokens | - |
| Creation output tokens | - |
| Rework input tokens | - |
| Rework output tokens | - |
| Transient input tokens | 0 |
| Transient output tokens | 0 |
| Semantic rework attempts | 8 |
| Transient retries | 0 |
| Provider truncations | 0 |
| Transient recoveries | 0 |
| Truncations unresolved | 0 |
| All input tokens | 614,233 |
| All output tokens | 149,797 |
| Normalized cost | $0.00 |
| Elapsed | 96.1m |
| Final LOC | 3533 |
| Python modules | 9 |
| Changed LOC | 3922 |
| Dependencies | 7 |
| Complexity | 827 |

## Notes

- No paired baseline/harness means to summarize.
- Rework baseline: 8 semantic retries (15 total attempts), 7 fixed, 0 unresolved.

Raw (local only): `results/tm-opencode-oxalpha-high/`, `reports/tm-opencode-oxalpha-high/`.

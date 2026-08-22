# pilot-feedback-v1-task_manager-20260822

| | |
|---|---|
| Problem | `task_manager` |
| Model | `x-preview-f-free` · thinking `high` |
| Agent | opencode · provider `opencode_auth` · `1.14.33` |
| N | baseline=2 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

Creation/Rework token metrics use per-attempt usage; `-` means unavailable.
Failed checkpoints include checkpoints repaired by rework; Rework = All - Create when possible.

| Metric | baseline |
|--------|---------:|
| CP passed/total | 15/15 |
| Failed checkpoints | 0.5 |
| Repeated attempts | 0.5 |
| Regressions | 0.5 |
| Creation input tokens | 900,910 |
| Creation output tokens | 202,798 |
| Rework input tokens | 10,562 |
| Rework output tokens | 2,472 |
| Transient input tokens | 0 |
| Transient output tokens | 0 |
| Semantic rework attempts | 0.5 |
| Transient retries | 0 |
| Provider truncations | 0 |
| Transient recoveries | 0 |
| Truncations unresolved | 0 |
| All input tokens | 911,472 |
| All output tokens | 205,270 |
| Normalized cost | $0.00 |
| Elapsed | 275.3m |
| Final LOC | 5263.5 |
| Changed LOC | 6646.5 |
| Dependencies | 5 |
| Complexity | 984 |

## Notes

- No paired baseline/harness means to summarize.
- Rework baseline: 1 semantic retries (2 total attempts), 1 fixed, 0 unresolved.
- Incomplete runs excluded from averages: baseline=1.

Raw (local only): `results/pilot-feedback-v1-task_manager-20260822/`, `reports/pilot-feedback-v1-task_manager-20260822/`.

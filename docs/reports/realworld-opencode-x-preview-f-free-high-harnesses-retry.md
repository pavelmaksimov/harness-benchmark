# realworld-opencode-x-preview-f-free-high-harnesses-retry

| | |
|---|---|
| Problem | `realworld` |
| Model | `x-preview-f-free` · thinking `high` |
| Agent | opencode · provider `opencode_auth` · `1.14.33` |
| N | python-harness=1 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

Creation/Rework token metrics use per-attempt usage; `-` means unavailable.
Failed checkpoints include checkpoints repaired by rework; Rework = All - Create when possible.

| Metric | python-harness |
|--------|---------:|
| CP passed/total | 14/14 |
| Failed checkpoints | 2 |
| Repeated attempts | 3 |
| Regressions | 0 |
| Creation input tokens | 725,810 |
| Creation output tokens | 80,603 |
| Rework input tokens | 144,495 |
| Rework output tokens | 27,421 |
| Transient input tokens | 0 |
| Transient output tokens | 0 |
| Semantic rework attempts | 3 |
| Transient retries | 0 |
| Provider truncations | 0 |
| Transient recoveries | 0 |
| Truncations unresolved | 0 |
| All input tokens | 870,305 |
| All output tokens | 108,024 |
| Normalized cost | $0.00 |
| Elapsed | 95.8m |
| Final LOC | 3357 |
| Python modules | 49 |
| Changed LOC | 9125 |
| Dependencies | 10 |
| Complexity | 968 |

## Δ vs baseline

| Metric | python-harness |
|--------|---------:|
| CP passed/total | - |
| Failed checkpoints | - |
| Repeated attempts | - |
| Regressions | - |
| Creation input tokens | - |
| Creation output tokens | - |
| Rework input tokens | - |
| Rework output tokens | - |
| Transient input tokens | - |
| Transient output tokens | - |
| Semantic rework attempts | - |
| Transient retries | - |
| Provider truncations | - |
| Transient recoveries | - |
| Truncations unresolved | - |
| All input tokens | - |
| All output tokens | - |
| Normalized cost | - |
| Elapsed | - |
| Final LOC | - |
| Python modules | - |
| Changed LOC | - |
| Dependencies | - |
| Complexity | - |

## Notes

- No paired baseline/harness means to summarize.
- Rework python-harness: 3 semantic retries (5 total attempts), 2 fixed, 0 unresolved.
- Incomplete runs excluded from averages: benjamin-plus-skill=1.

Raw (local only): `results/realworld-opencode-x-preview-f-free-high-harnesses-retry/`, `reports/realworld-opencode-x-preview-f-free-high-harnesses-retry/`.

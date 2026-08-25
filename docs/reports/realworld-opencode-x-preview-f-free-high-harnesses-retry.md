# realworld-opencode-x-preview-f-free-high-harnesses-retry

| | |
|---|---|
| Problem | `realworld` |
| Model | `x-preview-f-free` · thinking `high` |
| Agent | opencode · provider `opencode_auth` · `1.14.33` |
| N | benjamin-plus-skill=1 · python-harness=1 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

Creation/Rework token metrics use per-attempt usage; `-` means unavailable.
Failed checkpoints include checkpoints repaired by rework; Rework = All - Create when possible.

| Metric | benjamin-plus-skill | python-harness |
|--------|---------:|---------:|
| CP passed/total | 14/14 | 14/14 |
| Failed checkpoints | 1 | 2 |
| Repeated attempts | 1 | 3 |
| Regressions | 0 | 0 |
| Creation input tokens | 297,858 | 725,810 |
| Creation output tokens | 40,046 | 80,603 |
| Rework input tokens | 20,858 | 144,495 |
| Rework output tokens | 2,593 | 27,421 |
| Transient input tokens | 0 | 0 |
| Transient output tokens | 0 | 0 |
| Semantic rework attempts | 1 | 3 |
| Transient retries | 0 | 0 |
| Provider truncations | 0 | 0 |
| Transient recoveries | 0 | 0 |
| Truncations unresolved | 0 | 0 |
| All input tokens | 318,716 | 870,305 |
| All output tokens | 42,639 | 108,024 |
| Normalized cost | $0.00 | $0.00 |
| Elapsed | 52.2m | 95.8m |
| Final LOC | 879 | 3357 |
| Python modules | 2 | 49 |
| Changed LOC | 5511 | 9125 |
| Dependencies | 18 | 10 |
| Complexity | 185 | 968 |

## Δ vs baseline

| Metric | benjamin-plus-skill | python-harness |
|--------|---------:|---------:|
| CP passed/total | - | - |
| Failed checkpoints | - | - |
| Repeated attempts | - | - |
| Regressions | - | - |
| Creation input tokens | - | - |
| Creation output tokens | - | - |
| Rework input tokens | - | - |
| Rework output tokens | - | - |
| Transient input tokens | - | - |
| Transient output tokens | - | - |
| Semantic rework attempts | - | - |
| Transient retries | - | - |
| Provider truncations | - | - |
| Transient recoveries | - | - |
| Truncations unresolved | - | - |
| All input tokens | - | - |
| All output tokens | - | - |
| Normalized cost | - | - |
| Elapsed | - | - |
| Final LOC | - | - |
| Python modules | - | - |
| Changed LOC | - | - |
| Dependencies | - | - |
| Complexity | - | - |

## Notes

- No paired baseline/harness means to summarize.
- Rework benjamin-plus-skill: 1 semantic retries (2 total attempts), 1 fixed, 0 unresolved.
- Rework python-harness: 3 semantic retries (5 total attempts), 2 fixed, 0 unresolved.

Raw (local only): `results/realworld-opencode-x-preview-f-free-high-harnesses-retry/`, `reports/realworld-opencode-x-preview-f-free-high-harnesses-retry/`.

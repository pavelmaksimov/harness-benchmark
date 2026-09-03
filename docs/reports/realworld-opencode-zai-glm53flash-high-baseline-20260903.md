# realworld-opencode-zai-glm53flash-high-baseline-20260903

| | |
|---|---|
| Problem | `realworld` |
| Model | `glm-5.3-flash` · thinking `high` |
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
| Creation input tokens | 354,603 |
| Creation output tokens | 61,039 |
| Rework input tokens | 29,752 |
| Rework output tokens | 4,686 |
| Transient input tokens | 0 |
| Transient output tokens | 0 |
| Semantic rework attempts | 1 |
| Transient retries | 0 |
| Provider truncations | 0 |
| Transient recoveries | 0 |
| Truncations unresolved | 0 |
| All input tokens | 384,355 |
| All output tokens | 65,725 |
| Cached tokens | 4,996,736 |
| Reasoning tokens | 56,413 |
| LLM requests | 281 |
| Normalized cost | $0.00 |
| Elapsed | 85.2m |
| Final LOC | 1324 |
| Python modules | 14 |
| Changed LOC | 1535 |
| Dependencies | 4 |
| Complexity | 242 |

## Notes

- No paired baseline/harness means to summarize.
- Rework baseline: 1 semantic retries (2 total attempts), 1 fixed, 0 unresolved.

Raw (local only): `results/realworld-opencode-zai-glm53flash-high-baseline-20260903/`, `reports/realworld-opencode-zai-glm53flash-high-baseline-20260903/`.

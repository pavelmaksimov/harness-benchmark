# 2026-09-01-realworld-codex-gpt-5.6-luna-max-baseline

| | |
|---|---|
| Problem | `realworld` |
| Model | `gpt-5.6-luna` · thinking `max` |
| Agent | codex · provider `codex_auth` · `0.145.0` |
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
| Creation input tokens | 5,420,944 |
| Creation output tokens | 137,280 |
| Rework input tokens | 405,590 |
| Rework output tokens | 7,853 |
| Transient input tokens | 0 |
| Transient output tokens | 0 |
| Semantic rework attempts | 1 |
| Transient retries | 0 |
| Provider truncations | 0 |
| Transient recoveries | 0 |
| Truncations unresolved | 0 |
| All input tokens | 5,826,534 |
| All output tokens | 145,133 |
| Cached tokens | 5,285,888 |
| Reasoning tokens | 80,615 |
| LLM requests | 355 |
| Normalized cost | $2.79 |
| Elapsed | 53.8m |
| Final LOC | 1093 |
| Python modules | 7 |
| Changed LOC | 1306 |
| Dependencies | 5 |
| Complexity | 184 |

## Notes

- No paired baseline/harness means to summarize.
- Rework baseline: 1 semantic retries (2 total attempts), 1 fixed, 0 unresolved.

Raw (local only): `results/2026-09-01-realworld-codex-gpt-5.6-luna-max-baseline/`, `reports/2026-09-01-realworld-codex-gpt-5.6-luna-max-baseline/`.

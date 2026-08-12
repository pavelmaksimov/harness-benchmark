# mvp-smoke-baseline

| | |
|---|---|
| Problem | `file_backup` |
| Model | `gpt-5.5` · thinking `medium` |
| Agent | codex `0.145.0` |
| N | baseline=1 · ponytail=1 |
| Pins | SCB / problems / ponytail — see published JSON / local manifest |

## Metrics (mean)

| Metric | Baseline | Ponytail | Δ |
|--------|---------:|---------:|--:|
| CP passed | 4 | 4 | 0 |
| Regressions | 100 | 49 | -51 |
| Normalized cost | $2.15 | $2.41 | +$0.26 |
| Elapsed | 11.1m | 12.2m | +1.1m |
| Final LOC | 581 | 485 | -96 |
| Changed LOC | 732 | 560 | -172 |
| Dependencies | 1 | 1 | 0 |
| Complexity | 151 | 133 | -18 |

## Notes

- Same CP pass (4).
- Ponytail lower final LOC (485 vs 581).
- Ponytail lower changed LOC (560 vs 732).
- Ponytail lower regressions (49 vs 100).

Raw (local only): `results/mvp-smoke-baseline/`, `reports/mvp-smoke-baseline/`.

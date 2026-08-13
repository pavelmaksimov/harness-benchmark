# luna-max-multi-harness-20260812T133624

| | |
|---|---|
| Problem | `file_backup` |
| Model | `gpt-5.6-luna` · thinking `max` |
| Agent | codex `0.145.0` |
| N | baseline=1 · code-review=1 · graphify=1 · ponytail=1 · review-agent=1 · supermemory=1 · tdd=1 · thermo-nuclear-code-quality-review=1 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

| Metric | baseline | code-review | graphify | ponytail | review-agent | supermemory | tdd | thermo-nuclear-code-quality-review |
|--------|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|
| CP passed/total | 3/4 | 4/4 | 4/4 | 4/4 | 4/4 | 3/4 | 4/4 | 4/4 |
| Regressions | 106 | 106 | 100 | 106 | 100 | 106 | 49 | 106 |
| Normalized cost | $2.19 | $2.04 | $2.34 | $1.67 | $2.79 | $2.19 | $2.90 | $2.72 |
| Elapsed | 41.7m | 78.3m | 46.0m | 30.5m | 49.8m | 41.6m | 50.2m | 48.8m |
| Final LOC | 1065 | 986 | 796 | 515 | 884 | 1047 | 1669 | 679 |
| Changed LOC | 1455 | 1276 | 1025 | 751 | 1355 | 1287 | 1848 | 918 |
| Dependencies | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 |
| Complexity | 230 | 235 | 199 | 176 | 221 | 228 | 213 | 172 |

## Δ vs baseline

| Metric | code-review | graphify | ponytail | review-agent | supermemory | tdd | thermo-nuclear-code-quality-review |
|--------|---------:|---------:|---------:|---------:|---------:|---------:|---------:|
| CP passed/total | +1 | +1 | +1 | +1 | 0 | +1 | +1 |
| Regressions | 0 | -6 | 0 | -6 | 0 | -57 | 0 |
| Normalized cost | $-0.14 | +$0.15 | $-0.52 | +$0.60 | +$0.00 | +$0.71 | +$0.53 |
| Elapsed | +36.6m | +4.3m | -11.2m | +8.1m | -0.1m | +8.5m | +7.1m |
| Final LOC | -79 | -269 | -550 | -181 | -18 | +604 | -386 |
| Changed LOC | -179 | -430 | -704 | -100 | -168 | +393 | -537 |
| Dependencies | +1 | 0 | 0 | 0 | 0 | 0 | 0 |
| Complexity | +5 | -31 | -54 | -9 | -2 | -17 | -58 |

## Notes

- code-review CP 4/4 vs baseline 3/4.
- code-review lower final LOC (986 vs 1065).
- graphify CP 4/4 vs baseline 3/4.
- graphify lower final LOC (796 vs 1065).
- ponytail CP 4/4 vs baseline 3/4.
- ponytail lower final LOC (515 vs 1065).

Raw (local only): `results/luna-max-multi-harness-20260812T133624/`, `reports/luna-max-multi-harness-20260812T133624/`.

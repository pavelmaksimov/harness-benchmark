# gpt55-med-codex-task-manager-20260819T1330

| | |
|---|---|
| Problem | `task_manager` |
| Model | `gpt-5.5` · thinking `medium` |
| Agent | codex `0.145.0` |
| N | baseline=1 · graphify=1 · supermemory=1 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

| Metric | baseline | graphify | supermemory |
|--------|---------:|---------:|---------:|
| CP passed/total | 2/3 | 2/3 | 2/3 |
| Regressions | 2 | 0 | 2 |
| Normalized cost | $2.22 | $2.64 | $2.61 |
| Elapsed | 15.3m | 17.0m | 15.5m |
| Final LOC | 706 | 674 | 675 |
| Changed LOC | 915 | 884 | 912 |
| Dependencies | 6 | 4 | 6 |
| Complexity | 176 | 153 | 159 |

## Δ vs baseline

| Metric | graphify | supermemory |
|--------|---------:|---------:|
| CP passed/total | 0 | 0 |
| Regressions | -2 | 0 |
| Normalized cost | +$0.42 | +$0.38 |
| Elapsed | +1.7m | +0.3m |
| Final LOC | -32 | -31 |
| Changed LOC | -31 | -3 |
| Dependencies | -2 | 0 |
| Complexity | -23 | -17 |

## Notes

- graphify lower final LOC (674 vs 706).
- supermemory lower final LOC (675 vs 706).
- Excluded (activation unverified): code-review=1, ponytail=1, review-agent=1, tdd=1, thermo-nuclear-code-quality-review=1.

Raw (local only): `results/gpt55-med-codex-task-manager-20260819T1330/`, `reports/gpt55-med-codex-task-manager-20260819T1330/`.

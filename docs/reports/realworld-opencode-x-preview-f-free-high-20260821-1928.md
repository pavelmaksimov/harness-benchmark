# realworld-opencode-x-preview-f-free-high-20260821-1928

| | |
|---|---|
| Problem | `realworld` |
| Model | `x-preview-f-free` · thinking `high` |
| Agent | opencode · provider `opencode_auth` · `1.14.33` |
| N | doorstop=1 · graphify=1 · ponytail=1 · strictdoc=1 · supermemory=1 · tdd=1 · thermo-nuclear-code-quality-review=1 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

Creation/Rework token metrics use per-attempt usage; `-` means unavailable.
Failed checkpoints include checkpoints repaired by rework; Rework = All - Create when possible.

| Metric | doorstop | graphify | ponytail | strictdoc | supermemory | tdd | thermo-nuclear-code-quality-review |
|--------|---------:|---------:|---------:|---------:|---------:|---------:|---------:|
| CP passed/total | 14/14 | 14/14 | 13/14 | 14/14 | 14/14 | 14/14 | 6/14 |
| Failed checkpoints | 2 | 1 | 2 | 5 | 1 | 2 | 10 |
| Repeated attempts | 3 | 1 | 4 | 8 | 2 | 3 | 27 |
| Regressions | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Creation input tokens | - | - | - | - | - | - | - |
| Creation output tokens | - | - | - | - | - | - | - |
| Rework input tokens | - | - | - | - | - | - | - |
| Rework output tokens | - | - | - | - | - | - | - |
| Transient input tokens | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Transient output tokens | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Semantic rework attempts | 3 | 1 | 4 | 8 | 2 | 3 | 27 |
| Transient retries | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Provider truncations | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Transient recoveries | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Truncations unresolved | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| All input tokens | 383,992 | 591,912 | 294,683 | 431,917 | 473,208 | 302,511 | 389,073 |
| All output tokens | 53,534 | 45,805 | 25,333 | 59,943 | 48,053 | 40,629 | 69,573 |
| Cached tokens | 4,656,384 | 3,680,512 | 1,207,872 | 6,009,152 | 2,696,640 | 2,555,520 | 4,323,520 |
| LLM requests | 295 | 210 | 124 | 305 | 198 | 180 | 251 |
| Normalized cost | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 |
| Elapsed | 49.5m | 40.0m | 27.9m | 57.3m | 33.2m | 31.6m | 71.0m |
| Final LOC | 727 | 997 | 495 | 857 | 1032 | 2613 | 640 |
| Python modules | 6 | 13 | 2 | 12 | 6 | 17 | 8 |
| Changed LOC | 975 | 1380 | 484 | 1102 | 1138 | 2862 | 287 |
| Dependencies | 5 | 5 | 5 | 5 | 22 | 7 | 6 |
| Complexity | 185 | 178 | 118 | 192 | 211 | 821 | 101 |

## Δ vs baseline

| Metric | doorstop | graphify | ponytail | strictdoc | supermemory | tdd | thermo-nuclear-code-quality-review |
|--------|---------:|---------:|---------:|---------:|---------:|---------:|---------:|
| CP passed/total | - | - | - | - | - | - | - |
| Failed checkpoints | - | - | - | - | - | - | - |
| Repeated attempts | - | - | - | - | - | - | - |
| Regressions | - | - | - | - | - | - | - |
| Creation input tokens | - | - | - | - | - | - | - |
| Creation output tokens | - | - | - | - | - | - | - |
| Rework input tokens | - | - | - | - | - | - | - |
| Rework output tokens | - | - | - | - | - | - | - |
| Transient input tokens | - | - | - | - | - | - | - |
| Transient output tokens | - | - | - | - | - | - | - |
| Semantic rework attempts | - | - | - | - | - | - | - |
| Transient retries | - | - | - | - | - | - | - |
| Provider truncations | - | - | - | - | - | - | - |
| Transient recoveries | - | - | - | - | - | - | - |
| Truncations unresolved | - | - | - | - | - | - | - |
| All input tokens | - | - | - | - | - | - | - |
| All output tokens | - | - | - | - | - | - | - |
| Cached tokens | - | - | - | - | - | - | - |
| LLM requests | - | - | - | - | - | - | - |
| Normalized cost | - | - | - | - | - | - | - |
| Elapsed | - | - | - | - | - | - | - |
| Final LOC | - | - | - | - | - | - | - |
| Python modules | - | - | - | - | - | - | - |
| Changed LOC | - | - | - | - | - | - | - |
| Dependencies | - | - | - | - | - | - | - |
| Complexity | - | - | - | - | - | - | - |

## Notes

- No paired baseline/harness means to summarize.
- Rework doorstop: 3 semantic retries (5 total attempts), 2 fixed, 0 unresolved.
- Rework graphify: 1 semantic retries (2 total attempts), 1 fixed, 0 unresolved.
- Rework ponytail: 4 semantic retries (6 total attempts), 1 fixed, 1 unresolved.
- Rework strictdoc: 8 semantic retries (13 total attempts), 5 fixed, 0 unresolved.
- Rework supermemory: 2 semantic retries (3 total attempts), 1 fixed, 0 unresolved.
- Rework tdd: 3 semantic retries (5 total attempts), 2 fixed, 0 unresolved.
- Rework thermo-nuclear-code-quality-review: 27 semantic retries (37 total attempts), 2 fixed, 8 unresolved.

Raw (local only): `results/realworld-opencode-x-preview-f-free-high-20260821-1928/`, `reports/realworld-opencode-x-preview-f-free-high-20260821-1928/`.

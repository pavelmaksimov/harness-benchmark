# realworld-opencode-x-preview-f-free-high-all-20260822-1838

| | |
|---|---|
| Problem | `realworld` |
| Model | `x-preview-f-free` · thinking `high` |
| Agent | opencode · provider `opencode_auth` · `1.14.33` |
| N | baseline=1 · combo-supermemory-graphify=1 · combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review=1 · combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd=1 · doorstop=1 · graphify=1 · ponytail=1 · strictdoc=1 · supermemory=1 · tdd=1 · thermo-nuclear-code-quality-review=1 |
| Pins | SCB / problems / harness pins — see published JSON / local manifest |

## Metrics (mean)

Creation/Rework token metrics use per-attempt usage; `-` means unavailable.
Failed checkpoints include checkpoints repaired by rework; Rework = All - Create when possible.

| Metric | baseline | combo-supermemory-graphify | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | doorstop | graphify | ponytail | strictdoc | supermemory | tdd | thermo-nuclear-code-quality-review |
|--------|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|
| CP passed/total | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 13/14 |
| Failed checkpoints | 0 | 2 | 2 | 2 | 1 | 1 | 2 | 0 | 2 | 2 | 3 |
| Repeated attempts | 0 | 2 | 2 | 2 | 1 | 1 | 2 | 0 | 3 | 2 | 4 |
| Regressions | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Creation input tokens | 261,474 | 389,947 | 286,932 | 317,407 | 333,660 | 484,474 | 234,726 | 398,588 | 270,951 | 275,550 | 380,970 |
| Creation output tokens | 39,124 | 62,963 | 40,490 | 53,728 | 66,256 | 59,561 | 29,180 | 62,940 | 55,271 | 43,670 | 62,509 |
| Rework input tokens | 0 | 48,615 | 25,102 | 33,752 | 19,770 | 12,504 | 27,967 | 0 | 48,913 | 30,196 | 90,941 |
| Rework output tokens | 0 | 7,593 | 6,783 | 4,320 | 3,926 | 1,964 | 4,879 | 0 | 12,466 | 4,356 | 18,577 |
| Transient input tokens | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Transient output tokens | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Semantic rework attempts | 0 | 2 | 2 | 2 | 1 | 1 | 2 | 0 | 3 | 2 | 4 |
| Transient retries | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Provider truncations | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Transient recoveries | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Truncations unresolved | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| All input tokens | 261,474 | 438,562 | 312,034 | 351,159 | 353,430 | 496,978 | 262,693 | 398,588 | 319,864 | 305,746 | 471,911 |
| All output tokens | 39,124 | 70,556 | 47,273 | 58,048 | 70,182 | 61,525 | 34,059 | 62,940 | 67,737 | 48,026 | 81,086 |
| Cached tokens | 2,056,896 | 6,618,496 | 3,034,304 | 5,146,496 | 6,829,888 | 5,693,504 | 1,967,168 | 5,563,520 | 4,040,256 | 3,818,752 | 5,366,720 |
| LLM requests | 170 | 315 | 215 | 288 | 410 | 276 | 164 | 292 | 307 | 273 | 361 |
| Normalized cost | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 |
| Elapsed | 58.2m | 88.7m | 60.8m | 59.7m | 95.4m | 99.5m | 34.2m | 72.9m | 61.3m | 55.4m | 96.0m |
| Final LOC | 905 | 1096 | 968 | 1620 | 2123 | 869 | 729 | 884 | 1125 | 2460 | 747 |
| Python modules | 4 | 7 | 5 | 17 | 17 | 11 | 3 | 12 | 11 | 21 | 11 |
| Changed LOC | 1169 | 909 | 945 | 1726 | 2371 | 963 | 752 | 1147 | 1169 | 2732 | 724 |
| Dependencies | 6 | 7 | 5 | 6 | 6 | 6 | 25 | 6 | 7 | 30 | 6 |
| Complexity | 222 | 229 | 245 | 606 | 570 | 179 | 168 | 210 | 204 | 676 | 131 |

## Δ vs baseline

| Metric | combo-supermemory-graphify | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review | combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd | doorstop | graphify | ponytail | strictdoc | supermemory | tdd | thermo-nuclear-code-quality-review |
|--------|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|
| CP passed/total | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -1 |
| Failed checkpoints | +2 | +2 | +2 | +1 | +1 | +2 | 0 | +2 | +2 | +3 |
| Repeated attempts | +2 | +2 | +2 | +1 | +1 | +2 | 0 | +3 | +2 | +4 |
| Regressions | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Creation input tokens | +128,473 | +25,458 | +55,933 | +72,186 | +223,000 | -26,748 | +137,114 | +9,477 | +14,076 | +119,496 |
| Creation output tokens | +23,839 | +1,366 | +14,604 | +27,132 | +20,437 | -9,944 | +23,816 | +16,147 | +4,546 | +23,385 |
| Rework input tokens | +48,615 | +25,102 | +33,752 | +19,770 | +12,504 | +27,967 | 0 | +48,913 | +30,196 | +90,941 |
| Rework output tokens | +7,593 | +6,783 | +4,320 | +3,926 | +1,964 | +4,879 | 0 | +12,466 | +4,356 | +18,577 |
| Transient input tokens | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Transient output tokens | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Semantic rework attempts | +2 | +2 | +2 | +1 | +1 | +2 | 0 | +3 | +2 | +4 |
| Transient retries | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Provider truncations | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Transient recoveries | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Truncations unresolved | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| All input tokens | +177,088 | +50,560 | +89,685 | +91,956 | +235,504 | +1,219 | +137,114 | +58,390 | +44,272 | +210,437 |
| All output tokens | +31,432 | +8,149 | +18,924 | +31,058 | +22,401 | -5,065 | +23,816 | +28,613 | +8,902 | +41,962 |
| Cached tokens | +4,561,600 | +977,408 | +3,089,600 | +4,772,992 | +3,636,608 | -89,728 | +3,506,624 | +1,983,360 | +1,761,856 | +3,309,824 |
| LLM requests | +145 | +45 | +118 | +240 | +106 | -6 | +122 | +137 | +103 | +191 |
| Normalized cost | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 |
| Elapsed | +30.6m | +2.6m | +1.6m | +37.2m | +41.4m | -23.9m | +14.7m | +3.1m | -2.8m | +37.8m |
| Final LOC | +191 | +63 | +715 | +1218 | -36 | -176 | -21 | +220 | +1555 | -158 |
| Python modules | +3 | +1 | +13 | +13 | +7 | -1 | +8 | +7 | +17 | +7 |
| Changed LOC | -260 | -224 | +557 | +1202 | -206 | -417 | -22 | 0 | +1563 | -445 |
| Dependencies | +1 | -1 | 0 | 0 | 0 | +19 | 0 | +1 | +24 | 0 |
| Complexity | +7 | +23 | +384 | +348 | -43 | -54 | -12 | -18 | +454 | -91 |

## Notes

- combo-supermemory-graphify higher final LOC (1096 vs 905).
- combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review higher final LOC (968 vs 905).
- combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd higher final LOC (1620 vs 905).
- doorstop higher final LOC (2123 vs 905).
- graphify lower final LOC (869 vs 905).
- ponytail lower final LOC (729 vs 905).
- Rework combo-supermemory-graphify: 2 semantic retries (4 total attempts), 2 fixed, 0 unresolved.
- Rework combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review: 2 semantic retries (4 total attempts), 2 fixed, 0 unresolved.
- Rework combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-tdd: 2 semantic retries (4 total attempts), 2 fixed, 0 unresolved.
- Rework doorstop: 1 semantic retries (2 total attempts), 1 fixed, 0 unresolved.
- Rework graphify: 1 semantic retries (2 total attempts), 1 fixed, 0 unresolved.
- Rework ponytail: 2 semantic retries (4 total attempts), 2 fixed, 0 unresolved.
- Rework supermemory: 3 semantic retries (5 total attempts), 2 fixed, 0 unresolved.
- Rework tdd: 2 semantic retries (4 total attempts), 2 fixed, 0 unresolved.
- Rework thermo-nuclear-code-quality-review: 4 semantic retries (7 total attempts), 2 fixed, 1 unresolved.
- Incomplete runs excluded from averages: combo-supermemory-graphify-ponytail-thermo-nuclear-code-quality-review-doorstop-tdd=1.

Raw (local only): `results/realworld-opencode-x-preview-f-free-high-all-20260822-1838/`, `reports/realworld-opencode-x-preview-f-free-high-all-20260822-1838/`.

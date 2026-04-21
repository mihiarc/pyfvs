# Forest-rents pipeline parity sweep

Configuration: TPA=400, SI=70, rotation=25yr, pyfvs n_seeds=5 (base=42); native single-seed. Pass band ≤5%, warn band ≤15%, fail above.
Ran in 6.6s.

**Summary** — PASS: 4, WARN: 8, FAIL: 40, ERROR: 0

| Region | Variant | Species | FIA | Status | ΔBA | ΔQMD | ΔTopH | ΔVol | |Δ|max |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| southern | SN | LP | 131 | WARN | +4.4% | +2.1% | +1.7% | +6.2% | 6.2% |
| southern | SN | SA | 111 | WARN | +5.0% | +2.4% | +2.8% | +9.3% | 9.3% |
| southern | SN | LL | 121 | PASS | +1.4% | +0.6% | +2.5% | +4.0% | 4.0% |
| southern | SN | SP | 110 | WARN | +3.5% | +1.6% | +1.9% | +5.8% | 5.8% |
| southern | SN | WO | 802 | PASS | +1.0% | +0.8% | +2.0% | +3.4% | 3.4% |
| southern | SN | RO | 833 | WARN | -0.4% | -0.0% | +2.6% | -9.7% | 9.7% |
| southern | SN | YP | 621 | PASS | -0.7% | -0.1% | +4.9% | +4.3% | 4.9% |
| southern | SN | SU | 611 | WARN | -6.7% | -3.2% | +2.5% | -4.8% | 6.7% |
| southern | SN | HI | 400 | WARN | +6.1% | +3.1% | +1.4% | -4.3% | 6.1% |
| northeast | NE | WP | 129 | FAIL | +84.9% | +36.8% | +22.2% | +134.4% | 134.4% |
| northeast | NE | RS | 97 | FAIL | +2.0% | +1.1% | +12.8% | +19.1% | 19.1% |
| northeast | NE | BF | 12 | WARN | -6.8% | -2.6% | +1.8% | -1.5% | 6.8% |
| northeast | NE | SM | 318 | FAIL | +21.1% | +10.9% | +16.2% | +56.8% | 56.8% |
| northeast | NE | RM | 316 | FAIL | +9.5% | +5.4% | +3.9% | +20.2% | 20.2% |
| northeast | NE | RO | 833 | FAIL | +7.1% | +4.0% | +0.7% | +19.9% | 19.9% |
| northeast | NE | YB | 371 | FAIL | +44.1% | +20.6% | +14.5% | +66.0% | 66.0% |
| northeast | NE | BC | 762 | WARN | +0.6% | +0.6% | -1.4% | +13.1% | 13.1% |
| lake_states | LS | RP | 125 | FAIL | +81.0% | +35.5% | +26.3% | +127.1% | 127.1% |
| lake_states | LS | JP | 105 | FAIL | +21.0% | +10.8% | +11.4% | +42.5% | 42.5% |
| lake_states | LS | WP | 129 | FAIL | +200.9% | +74.5% | +49.1% | +361.4% | 361.4% |
| lake_states | LS | WS | 94 | FAIL | +84.1% | +36.9% | +22.8% | +131.7% | 131.7% |
| lake_states | LS | BF | 12 | PASS | -2.4% | -0.3% | -3.2% | +0.6% | 3.2% |
| lake_states | LS | QA | 746 | FAIL | +24.6% | +12.1% | +8.9% | +58.7% | 58.7% |
| lake_states | LS | SM | 318 | FAIL | +50.8% | +23.7% | +16.9% | +90.2% | 90.2% |
| lake_states | LS | RO | 833 | FAIL | +70.5% | +31.2% | +23.9% | +148.3% | 148.3% |
| lake_states | LS | YB | 371 | FAIL | +68.6% | +30.4% | +15.4% | +93.3% | 93.3% |
| lake_states | LS | PB | 375 | FAIL | +105.4% | +44.0% | +23.3% | +184.1% | 184.1% |
| lake_states | LS | WA | 541 | FAIL | +30.9% | +14.9% | +7.7% | +73.9% | 73.9% |
| central_states | CS | WO | 802 | FAIL | +68.8% | +30.5% | +22.4% | +108.1% | 108.1% |
| central_states | CS | WN | 602 | FAIL | +41.7% | +19.6% | +12.0% | +66.3% | 66.3% |
| central_states | CS | BC | 762 | FAIL | +103.2% | +43.2% | +25.1% | +230.7% | 230.7% |
| central_states | CS | RO | 833 | FAIL | +46.8% | +21.7% | +15.5% | +98.9% | 98.9% |
| central_states | CS | SM | 318 | FAIL | +32.0% | +15.7% | +11.5% | +57.1% | 57.1% |
| central_states | CS | SH | 402 | FAIL | +45.2% | +20.9% | +15.5% | +73.8% | 73.8% |
| central_states | CS | YP | 621 | FAIL | +54.6% | +25.4% | +15.2% | +315.4% | 315.4% |
| central_states | CS | RM | 316 | FAIL | +58.4% | +26.8% | +15.7% | +87.4% | 87.4% |
| pacific_northwest | PN | DF | 202 | FAIL | +189.9% | +69.4% | +17.6% | +227.9% | 227.9% |
| pacific_northwest | PN | WH | 263 | FAIL | +163.7% | +61.6% | +21.8% | +249.3% | 249.3% |
| pacific_northwest | PN | SS | 98 | FAIL | +184.6% | +70.5% | -5.9% | +61.3% | 184.6% |
| pacific_northwest | PN | RC | 242 | FAIL | +147.5% | +56.6% | +6.4% | +202.6% | 202.6% |
| pacific_northwest | PN | PP | 122 | FAIL | +142.5% | +54.9% | +15.8% | +211.4% | 211.4% |
| pacific_northwest | PN | LP | 108 | FAIL | +97.4% | +39.8% | +23.6% | +123.9% | 123.9% |
| pacific_northwest | PN | GF | 17 | FAIL | +89.3% | +36.9% | +19.9% | +100.8% | 100.8% |
| pacific_northwest | EC | WL | 73 | FAIL | +184.4% | +72.8% | +67.8% | +380.6% | 380.6% |
| mountain | CA | DF | 202 | FAIL | +723.8% | +198.5% | +108.9% | +1328.1% | 1328.1% |
| mountain | CA | PP | 122 | FAIL | +146.2% | +75.0% | +136.5% | +496.3% | 496.3% |
| mountain | CA | LP | 108 | FAIL | +312.4% | +107.5% | +116.4% | +794.7% | 794.7% |
| mountain | CA | WF | 15 | FAIL | +160.6% | +63.7% | +109.0% | +486.7% | 486.7% |
| mountain | PN | ES | 93 | FAIL | +71.8% | +30.4% | +17.9% | +73.4% | 73.4% |
| mountain | PN | AF | 19 | FAIL | +58.9% | +25.4% | +21.0% | -71.4% | 71.4% |
| mountain | PN | GF | 17 | FAIL | +89.3% | +36.9% | +19.9% | +100.8% | 100.8% |
| mountain | EC | WL | 73 | FAIL | +184.4% | +72.8% | +67.8% | +380.6% | 380.6% |

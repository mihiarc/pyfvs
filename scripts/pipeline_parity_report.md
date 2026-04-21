# Forest-rents pipeline parity sweep

Configuration: TPA=400, SI=70, rotation=50yr, pyfvs n_seeds=5 (base=42); native single-seed. Pass band ≤5%, warn band ≤15%, fail above.
Ran in 11.8s.

**Summary** — PASS: 5, WARN: 10, FAIL: 37, ERROR: 0

| Region | Variant | Species | FIA | Status | ΔBA | ΔQMD | ΔTopH | ΔVol | |Δ|max |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| southern | SN | LP | 131 | WARN | +3.1% | +1.8% | +1.8% | +6.2% | 6.2% |
| southern | SN | SA | 111 | WARN | +1.9% | +2.0% | +3.9% | +7.8% | 7.8% |
| southern | SN | LL | 121 | PASS | +0.2% | -0.6% | +2.9% | +3.4% | 3.4% |
| southern | SN | SP | 110 | PASS | +0.0% | -0.1% | +2.9% | +2.9% | 2.9% |
| southern | SN | WO | 802 | PASS | +0.3% | +0.7% | +3.9% | +3.8% | 3.9% |
| southern | SN | RO | 833 | PASS | -0.5% | -0.0% | +3.6% | -1.8% | 3.6% |
| southern | SN | YP | 621 | WARN | -0.7% | -0.9% | +11.7% | +11.4% | 11.7% |
| southern | SN | SU | 611 | WARN | -13.8% | -8.7% | +3.3% | -11.4% | 13.8% |
| southern | SN | HI | 400 | WARN | +12.9% | +9.5% | +1.3% | +14.9% | 14.9% |
| northeast | NE | WP | 129 | FAIL | +5.3% | +9.1% | +6.3% | +28.8% | 28.8% |
| northeast | NE | RS | 97 | FAIL | +20.9% | +10.4% | +9.2% | +41.3% | 41.3% |
| northeast | NE | BF | 12 | FAIL | +12.9% | +11.9% | +9.4% | +31.3% | 31.3% |
| northeast | NE | SM | 318 | FAIL | +16.3% | +7.8% | +6.4% | +36.4% | 36.4% |
| northeast | NE | RM | 316 | FAIL | +20.4% | +9.4% | +5.2% | +38.5% | 38.5% |
| northeast | NE | RO | 833 | FAIL | +12.3% | +9.6% | +3.6% | +35.1% | 35.1% |
| northeast | NE | YB | 371 | FAIL | +16.5% | +9.6% | +5.1% | +31.9% | 31.9% |
| northeast | NE | BC | 762 | FAIL | +12.2% | +7.8% | +4.9% | +32.2% | 32.2% |
| lake_states | LS | RP | 125 | FAIL | +7.2% | +4.9% | -19.1% | +16.9% | 19.1% |
| lake_states | LS | JP | 105 | FAIL | +13.4% | +6.8% | -17.6% | +23.8% | 23.8% |
| lake_states | LS | WP | 129 | FAIL | +3.4% | +7.4% | -14.8% | +15.3% | 15.3% |
| lake_states | LS | WS | 94 | FAIL | +28.7% | +15.3% | -20.2% | +34.7% | 34.7% |
| lake_states | LS | BF | 12 | WARN | -2.8% | +5.3% | -11.2% | +7.4% | 11.2% |
| lake_states | LS | QA | 746 | WARN | -10.2% | +6.7% | -13.6% | -1.2% | 13.6% |
| lake_states | LS | SM | 318 | FAIL | +22.9% | +10.3% | -16.8% | +27.6% | 27.6% |
| lake_states | LS | RO | 833 | FAIL | +12.3% | +11.0% | -16.5% | +22.6% | 22.6% |
| lake_states | LS | YB | 371 | WARN | +8.8% | +4.5% | -13.0% | +14.7% | 14.7% |
| lake_states | LS | PB | 375 | FAIL | +9.7% | +11.2% | -14.6% | +17.1% | 17.1% |
| lake_states | LS | WA | 541 | FAIL | +2.7% | +7.9% | -14.8% | +17.4% | 17.4% |
| central_states | CS | WO | 802 | FAIL | +21.4% | +11.3% | -10.5% | +40.5% | 40.5% |
| central_states | CS | WN | 602 | FAIL | +62.9% | -7.5% | -9.4% | +74.4% | 74.4% |
| central_states | CS | BC | 762 | FAIL | +27.1% | +18.9% | -14.1% | +40.3% | 40.3% |
| central_states | CS | RO | 833 | WARN | -3.3% | -2.4% | -11.7% | +8.7% | 11.7% |
| central_states | CS | SM | 318 | FAIL | +15.8% | +5.7% | -11.6% | +25.0% | 25.0% |
| central_states | CS | SH | 402 | FAIL | +38.9% | +19.2% | -8.8% | +51.9% | 51.9% |
| central_states | CS | YP | 621 | FAIL | -16.6% | -11.1% | -6.5% | -9.2% | 16.6% |
| central_states | CS | RM | 316 | FAIL | +17.8% | +14.1% | -12.0% | +28.6% | 28.6% |
| pacific_northwest | PN | DF | 202 | WARN | -8.2% | +7.3% | +0.6% | -3.9% | 8.2% |
| pacific_northwest | PN | WH | 263 | PASS | -0.1% | +3.5% | -0.5% | +4.0% | 4.0% |
| pacific_northwest | PN | SS | 98 | FAIL | -17.4% | +9.1% | -61.4% | -74.7% | 74.7% |
| pacific_northwest | PN | RC | 242 | FAIL | -3.5% | +0.0% | -54.1% | -28.3% | 54.1% |
| pacific_northwest | PN | PP | 122 | FAIL | -13.7% | +2.1% | +0.5% | -39.1% | 39.1% |
| pacific_northwest | PN | LP | 108 | FAIL | +9.4% | +5.2% | -7.0% | -33.0% | 33.0% |
| pacific_northwest | PN | GF | 17 | FAIL | +13.0% | +6.2% | -47.9% | -53.8% | 53.8% |
| pacific_northwest | EC | WL | 73 | FAIL | +60.1% | +2.7% | -3.9% | +17.2% | 60.1% |
| mountain | CA | DF | 202 | FAIL | +24.1% | +40.6% | +8.2% | +33.4% | 40.6% |
| mountain | CA | PP | 122 | FAIL | -14.3% | +21.9% | +13.3% | +9.9% | 21.9% |
| mountain | CA | LP | 108 | FAIL | +50.7% | +31.5% | +3.0% | +6.7% | 50.7% |
| mountain | CA | WF | 15 | FAIL | -24.0% | -9.9% | +6.3% | -11.0% | 24.0% |
| mountain | PN | ES | 93 | FAIL | +1.0% | +0.5% | -0.7% | -33.0% | 33.0% |
| mountain | PN | AF | 19 | FAIL | +17.5% | +4.6% | +0.3% | -7.0% | 17.5% |
| mountain | PN | GF | 17 | FAIL | +13.0% | +6.2% | -47.9% | -53.8% | 53.8% |
| mountain | EC | WL | 73 | FAIL | +60.1% | +2.7% | -3.9% | +17.2% | 60.1% |

# Forest-rents pipeline parity sweep

Configuration: TPA=400, SI=70, rotation=50yr, pyfvs n_seeds=5 (base=42); native single-seed. Pass band ≤5%, warn band ≤15%, fail above.
Ran in 12.4s.

**Summary** — PASS: 5, WARN: 16, FAIL: 31, ERROR: 0

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
| lake_states | LS | RP | 125 | FAIL | +6.5% | +4.9% | -2.0% | +21.1% | 21.1% |
| lake_states | LS | JP | 105 | FAIL | +8.2% | +2.6% | +0.8% | +22.3% | 22.3% |
| lake_states | LS | WP | 129 | FAIL | +5.0% | +8.4% | +2.8% | +22.1% | 22.1% |
| lake_states | LS | WS | 94 | FAIL | +17.5% | +6.7% | -1.7% | +26.5% | 26.5% |
| lake_states | LS | BF | 12 | WARN | -1.7% | +6.0% | +8.8% | +10.7% | 10.7% |
| lake_states | LS | QA | 746 | WARN | -9.2% | +7.8% | -0.5% | +4.0% | 9.2% |
| lake_states | LS | SM | 318 | WARN | +1.3% | +0.5% | -0.2% | +8.7% | 8.7% |
| lake_states | LS | RO | 833 | WARN | +0.8% | +2.2% | -0.9% | +12.9% | 12.9% |
| lake_states | LS | YB | 371 | WARN | +5.8% | +2.2% | +1.8% | +14.0% | 14.0% |
| lake_states | LS | PB | 375 | WARN | +1.6% | +5.7% | +0.3% | +11.7% | 11.7% |
| lake_states | LS | WA | 541 | FAIL | +0.8% | +3.9% | +3.1% | +20.2% | 20.2% |
| central_states | CS | WO | 802 | FAIL | +21.3% | +11.4% | -10.4% | +40.4% | 40.4% |
| central_states | CS | WN | 602 | FAIL | +63.5% | -7.5% | -9.4% | +75.2% | 75.2% |
| central_states | CS | BC | 762 | FAIL | +27.1% | +18.8% | -14.1% | +40.3% | 40.3% |
| central_states | CS | RO | 833 | WARN | -3.0% | -2.2% | -11.9% | +9.1% | 11.9% |
| central_states | CS | SM | 318 | FAIL | +16.0% | +5.9% | -11.7% | +25.2% | 25.2% |
| central_states | CS | SH | 402 | FAIL | +38.9% | +19.3% | -9.1% | +51.9% | 51.9% |
| central_states | CS | YP | 621 | FAIL | -16.7% | -11.1% | -6.5% | -9.3% | 16.7% |
| central_states | CS | RM | 316 | FAIL | +17.9% | +14.2% | -11.9% | +28.9% | 28.9% |
| pacific_northwest | PN | DF | 202 | WARN | -8.2% | +7.3% | +0.6% | -3.9% | 8.2% |
| pacific_northwest | PN | WH | 263 | PASS | -0.1% | +3.5% | -0.5% | +4.0% | 4.0% |
| pacific_northwest | PN | SS | 98 | FAIL | -17.4% | +9.1% | -1.7% | -34.6% | 34.6% |
| pacific_northwest | PN | RC | 242 | WARN | -3.5% | +0.0% | +0.3% | +7.4% | 7.4% |
| pacific_northwest | PN | PP | 122 | FAIL | -13.7% | +2.1% | +0.5% | -39.1% | 39.1% |
| pacific_northwest | PN | LP | 108 | FAIL | +9.4% | +5.2% | +1.7% | -27.9% | 27.9% |
| pacific_northwest | PN | GF | 17 | WARN | +13.0% | +6.2% | -1.4% | -11.9% | 13.0% |
| pacific_northwest | EC | WL | 73 | FAIL | +19.2% | -16.0% | -1.8% | -11.1% | 19.2% |
| mountain | CA | DF | 202 | FAIL | +15.0% | +27.7% | +5.4% | +22.9% | 27.7% |
| mountain | CA | PP | 122 | FAIL | -16.3% | +15.9% | +10.1% | +3.9% | 16.3% |
| mountain | CA | LP | 108 | FAIL | +45.9% | +28.9% | +0.3% | +0.3% | 45.9% |
| mountain | CA | WF | 15 | FAIL | -15.6% | -5.1% | +3.7% | -4.1% | 15.6% |
| mountain | PN | ES | 93 | FAIL | +1.0% | +0.5% | -0.7% | -33.0% | 33.0% |
| mountain | PN | AF | 19 | FAIL | +17.5% | +4.6% | +0.3% | -7.0% | 17.5% |
| mountain | PN | GF | 17 | WARN | +13.0% | +6.2% | -1.4% | -11.9% | 13.0% |
| mountain | EC | WL | 73 | FAIL | +19.2% | -16.0% | -1.8% | -11.1% | 19.2% |

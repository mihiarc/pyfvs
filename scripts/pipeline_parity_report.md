# Forest-rents pipeline parity sweep

Configuration: TPA=400, SI=70, rotation=50yr, pyfvs n_seeds=5 (base=42); native single-seed. Pass band ≤5%, warn band ≤15%, fail above.
Ran in 11.3s.

**Summary** — PASS: 16, WARN: 18, FAIL: 18, ERROR: 0

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
| northeast | NE | WP | 129 | PASS | -4.2% | +1.4% | -2.0% | -2.1% | 4.2% |
| northeast | NE | RS | 97 | WARN | +8.0% | +1.0% | -2.7% | +8.1% | 8.1% |
| northeast | NE | BF | 12 | PASS | -1.2% | +1.2% | -0.1% | -1.0% | 1.2% |
| northeast | NE | SM | 318 | PASS | -2.1% | -1.1% | -0.8% | -1.5% | 2.1% |
| northeast | NE | RM | 316 | PASS | +1.7% | +0.8% | -2.6% | +1.3% | 2.6% |
| northeast | NE | RO | 833 | PASS | -1.1% | +0.5% | -3.9% | -1.4% | 3.9% |
| northeast | NE | YB | 371 | PASS | +1.6% | +1.1% | -0.7% | +2.1% | 2.1% |
| northeast | NE | BC | 762 | PASS | +1.1% | -0.2% | -2.8% | -0.2% | 2.8% |
| lake_states | LS | RP | 125 | WARN | +6.5% | +4.9% | -2.0% | +8.6% | 8.6% |
| lake_states | LS | JP | 105 | WARN | +8.2% | +2.6% | +0.8% | +10.0% | 10.0% |
| lake_states | LS | WP | 129 | WARN | +5.0% | +8.4% | +2.8% | +9.3% | 9.3% |
| lake_states | LS | WS | 94 | FAIL | +17.5% | +6.7% | -1.7% | +19.8% | 19.8% |
| lake_states | LS | BF | 12 | WARN | -1.7% | +6.0% | +8.8% | +2.9% | 8.8% |
| lake_states | LS | QA | 746 | WARN | -9.2% | +7.8% | -0.5% | -6.1% | 9.2% |
| lake_states | LS | SM | 318 | PASS | +1.3% | +0.5% | -0.2% | +0.1% | 1.3% |
| lake_states | LS | RO | 833 | PASS | +0.8% | +2.2% | -0.9% | +1.0% | 2.2% |
| lake_states | LS | YB | 371 | WARN | +5.8% | +2.2% | +1.8% | +5.5% | 5.8% |
| lake_states | LS | PB | 375 | WARN | +1.6% | +5.7% | +0.3% | +2.8% | 5.7% |
| lake_states | LS | WA | 541 | PASS | +0.8% | +3.9% | +3.1% | +4.5% | 4.5% |
| central_states | CS | WO | 802 | FAIL | +21.1% | +11.1% | -10.0% | +26.7% | 26.7% |
| central_states | CS | WN | 602 | FAIL | +66.9% | -2.5% | -7.8% | +65.0% | 66.9% |
| central_states | CS | BC | 762 | FAIL | +26.1% | +18.1% | -13.8% | +28.3% | 28.3% |
| central_states | CS | RO | 833 | WARN | +3.0% | +1.6% | -9.5% | +6.2% | 9.5% |
| central_states | CS | SM | 318 | FAIL | +19.2% | +8.0% | -9.4% | +21.8% | 21.8% |
| central_states | CS | SH | 402 | FAIL | +56.0% | +30.5% | -5.6% | +56.6% | 56.6% |
| central_states | CS | YP | 621 | PASS | -3.7% | -1.8% | -4.7% | -1.1% | 4.7% |
| central_states | CS | RM | 316 | FAIL | +31.6% | +24.4% | -9.3% | +36.2% | 36.2% |
| pacific_northwest | PN | DF | 202 | WARN | -8.2% | +7.3% | +0.6% | -3.9% | 8.2% |
| pacific_northwest | PN | WH | 263 | PASS | -0.1% | +3.5% | -0.5% | +4.0% | 4.0% |
| pacific_northwest | PN | SS | 98 | FAIL | -17.4% | +9.1% | -1.7% | -34.6% | 34.6% |
| pacific_northwest | PN | RC | 242 | WARN | -3.5% | +0.0% | +0.3% | +7.4% | 7.4% |
| pacific_northwest | PN | PP | 122 | FAIL | -13.7% | +2.1% | +0.5% | -39.1% | 39.1% |
| pacific_northwest | PN | LP | 108 | FAIL | +9.4% | +5.2% | +1.7% | -27.9% | 27.9% |
| pacific_northwest | PN | GF | 17 | WARN | +13.0% | +6.2% | -1.4% | -11.9% | 13.0% |
| pacific_northwest | EC | WL | 73 | FAIL | +13.3% | -15.5% | -1.7% | -15.5% | 15.5% |
| mountain | CA | DF | 202 | FAIL | +15.0% | +27.7% | +5.4% | +22.9% | 27.7% |
| mountain | CA | PP | 122 | FAIL | -16.3% | +15.9% | +10.1% | +3.9% | 16.3% |
| mountain | CA | LP | 108 | FAIL | +45.9% | +28.9% | +0.3% | +0.3% | 45.9% |
| mountain | CA | WF | 15 | FAIL | -15.6% | -5.1% | +3.7% | -4.1% | 15.6% |
| mountain | PN | ES | 93 | FAIL | +1.0% | +0.5% | -0.7% | -33.0% | 33.0% |
| mountain | PN | AF | 19 | FAIL | +17.5% | +4.6% | +0.3% | -7.0% | 17.5% |
| mountain | PN | GF | 17 | WARN | +13.0% | +6.2% | -1.4% | -11.9% | 13.0% |
| mountain | EC | WL | 73 | FAIL | +13.3% | -15.5% | -1.7% | -15.5% | 15.5% |

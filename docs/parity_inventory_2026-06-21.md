# pyfvs Parity Inventory — 2026-06-21 (post-normalization strict-xfail baseline)

Authoritative inventory of all **51 strict-xfail** parity tests under the normalized tolerance regime (`docs/parity_tolerances.md`): deterministic floor 0.5% (1.0% volume), stochastic band `min(cap, max(floor, 3×SEM))`, n_seeds=10. One row per **variant × test × metric** with the **measured** relative divergence vs the pinned native build (FVS 58a97520 / NVEL d6bbbf1), the applied band, and the pass/fail verdict. Figures regenerated from `PARITY_EMIT_SEM=1 uv run pytest tests/parity/ -m parity -s` — measured, not estimated. Within each variant, tests appear in suite order and **metrics are sorted worst-divergence-first**. `[SKIP]` = volume excluded for a documented volume-library gap (LS/PN/WC; see `docs/parity_tolerances.md`). DET = deterministic comparison (EC/OP/OC); STOCH = 10-seed-mean comparison.

Suite: **14 passed (structural/smoke only) · 51 xfailed · 0 xpass · 0 fail**. Every one of the 51 metric-comparison tests fails at least one metric against the tightened band.


## M1 — Eastern (SN, LS, CS, NE)


### CS

| test | metric | measured Δ | band | verdict |
|---|---|--:|--:|:--:|
| `test_cs_gold_standard_wo_si60_30yr` (STOCH) | volume | 4.6070% | 1.0000% | FAIL |
| `test_cs_gold_standard_wo_si60_30yr` (STOCH) | basal_area | 3.5244% | 0.5000% | FAIL |
| `test_cs_gold_standard_wo_si60_30yr` (STOCH) | qmd | 1.8047% | 0.5000% | FAIL |
| `test_cs_gold_standard_wo_si60_30yr` (STOCH) | top_height | 0.5460% | 0.5000% | FAIL |
| `test_cs_gold_standard_wo_si60_30yr` (STOCH) | tpa | 0.1165% | 0.5000% | PASS |
| `test_cs_expanded_species_parity[ro-si65-30yr]` (STOCH) | volume | 3.4885% | 1.0000% | FAIL |
| `test_cs_expanded_species_parity[ro-si65-30yr]` (STOCH) | basal_area | 2.6889% | 0.5000% | FAIL |
| `test_cs_expanded_species_parity[ro-si65-30yr]` (STOCH) | top_height | 2.2303% | 0.5000% | FAIL |
| `test_cs_expanded_species_parity[ro-si65-30yr]` (STOCH) | qmd | 1.3057% | 0.5000% | FAIL |
| `test_cs_expanded_species_parity[ro-si65-30yr]` (STOCH) | tpa | 0.1000% | 0.5000% | PASS |
| `test_cs_expanded_species_parity[sm-si60-30yr]` (STOCH) | top_height | 1.0600% | 0.5000% | FAIL |
| `test_cs_expanded_species_parity[sm-si60-30yr]` (STOCH) | volume | 0.8544% | 1.0000% | PASS |
| `test_cs_expanded_species_parity[sm-si60-30yr]` (STOCH) | basal_area | 0.4724% | 0.5000% | PASS |
| `test_cs_expanded_species_parity[sm-si60-30yr]` (STOCH) | qmd | 0.2420% | 0.5000% | PASS |
| `test_cs_expanded_species_parity[sm-si60-30yr]` (STOCH) | tpa | 0.0151% | 0.5000% | PASS |
| `test_cs_expanded_species_parity[yp-si70-30yr]` (STOCH) | volume | 3.0877% | 1.0000% | FAIL |
| `test_cs_expanded_species_parity[yp-si70-30yr]` (STOCH) | basal_area | 1.9323% | 0.5000% | FAIL |
| `test_cs_expanded_species_parity[yp-si70-30yr]` (STOCH) | qmd | 1.4269% | 0.5000% | FAIL |
| `test_cs_expanded_species_parity[yp-si70-30yr]` (STOCH) | tpa | 0.9185% | 0.5000% | FAIL |
| `test_cs_expanded_species_parity[yp-si70-30yr]` (STOCH) | top_height | 0.7927% | 0.5000% | FAIL |

### LS

| test | metric | measured Δ | band | verdict |
|---|---|--:|--:|:--:|
| `test_ls_gold_standard_rn_si60_30yr` (STOCH) | volume | 6.3289% | 1.0000% | SKIP |
| `test_ls_gold_standard_rn_si60_30yr` (STOCH) | basal_area | 6.0369% | 0.5000% | FAIL |
| `test_ls_gold_standard_rn_si60_30yr` (STOCH) | qmd | 2.9634% | 0.5000% | FAIL |
| `test_ls_gold_standard_rn_si60_30yr` (STOCH) | top_height | 0.9934% | 0.5000% | FAIL |
| `test_ls_gold_standard_rn_si60_30yr` (STOCH) | tpa | 0.0176% | 0.5000% | PASS |
| `test_ls_off_baseline_parity[wa-si60-30yr]` (STOCH) | volume | 1.2865% | 1.0000% | SKIP |
| `test_ls_off_baseline_parity[wa-si60-30yr]` (STOCH) | top_height | 0.9435% | 0.5000% | FAIL |
| `test_ls_off_baseline_parity[wa-si60-30yr]` (STOCH) | basal_area | 0.5758% | 0.5000% | FAIL |
| `test_ls_off_baseline_parity[wa-si60-30yr]` (STOCH) | qmd | 0.1977% | 0.5000% | PASS |
| `test_ls_off_baseline_parity[wa-si60-30yr]` (STOCH) | tpa | 0.1850% | 0.5000% | PASS |
| `test_ls_expanded_species_parity[jp-si60-30yr]` (STOCH) | volume | 4.1979% | 1.0000% | SKIP |
| `test_ls_expanded_species_parity[jp-si60-30yr]` (STOCH) | basal_area | 3.4314% | 0.5000% | FAIL |
| `test_ls_expanded_species_parity[jp-si60-30yr]` (STOCH) | qmd | 1.6905% | 0.5000% | FAIL |
| `test_ls_expanded_species_parity[jp-si60-30yr]` (STOCH) | top_height | 0.2231% | 0.5000% | PASS |
| `test_ls_expanded_species_parity[jp-si60-30yr]` (STOCH) | tpa | 0.0181% | 0.5000% | PASS |
| `test_ls_expanded_species_parity[sm-si55-30yr]` (STOCH) | volume | 1.3302% | 1.0000% | SKIP |
| `test_ls_expanded_species_parity[sm-si55-30yr]` (STOCH) | basal_area | 1.2270% | 0.5000% | FAIL |
| `test_ls_expanded_species_parity[sm-si55-30yr]` (STOCH) | top_height | 1.2087% | 0.5000% | FAIL |
| `test_ls_expanded_species_parity[sm-si55-30yr]` (STOCH) | qmd | 0.6055% | 0.5000% | FAIL |
| `test_ls_expanded_species_parity[sm-si55-30yr]` (STOCH) | tpa | 0.0227% | 0.5000% | PASS |
| `test_ls_expanded_species_parity[qa-si70-30yr]` (STOCH) | volume | 2.7431% | 1.0000% | SKIP |
| `test_ls_expanded_species_parity[qa-si70-30yr]` (STOCH) | basal_area | 2.5232% | 0.5000% | FAIL |
| `test_ls_expanded_species_parity[qa-si70-30yr]` (STOCH) | qmd | 2.1076% | 0.5000% | FAIL |
| `test_ls_expanded_species_parity[qa-si70-30yr]` (STOCH) | tpa | 1.6680% | 0.5000% | FAIL |
| `test_ls_expanded_species_parity[qa-si70-30yr]` (STOCH) | top_height | 0.5346% | 0.5000% | FAIL |

### NE

| test | metric | measured Δ | band | verdict |
|---|---|--:|--:|:--:|
| `test_ne_gold_standard_rm_si60_30yr` (STOCH) | top_height | 1.7679% | 0.5000% | FAIL |
| `test_ne_gold_standard_rm_si60_30yr` (STOCH) | basal_area | 0.7000% | 0.5000% | FAIL |
| `test_ne_gold_standard_rm_si60_30yr` (STOCH) | qmd | 0.3577% | 0.5000% | PASS |
| `test_ne_gold_standard_rm_si60_30yr` (STOCH) | volume | 0.1826% | 1.0000% | PASS |
| `test_ne_gold_standard_rm_si60_30yr` (STOCH) | tpa | 0.0196% | 0.5000% | PASS |
| `test_ne_expanded_species_parity[ro-si60-30yr]` (STOCH) | top_height | 2.5608% | 0.5000% | FAIL |
| `test_ne_expanded_species_parity[ro-si60-30yr]` (STOCH) | volume | 1.0223% | 1.0000% | FAIL |
| `test_ne_expanded_species_parity[ro-si60-30yr]` (STOCH) | basal_area | 0.1862% | 0.5000% | PASS |
| `test_ne_expanded_species_parity[ro-si60-30yr]` (STOCH) | qmd | 0.1336% | 0.5000% | PASS |
| `test_ne_expanded_species_parity[ro-si60-30yr]` (STOCH) | tpa | 0.0840% | 0.5000% | PASS |
| `test_ne_expanded_species_parity[sm-si60-30yr]` (STOCH) | top_height | 1.5200% | 0.5000% | FAIL |
| `test_ne_expanded_species_parity[sm-si60-30yr]` (STOCH) | volume | 0.6692% | 1.0000% | PASS |
| `test_ne_expanded_species_parity[sm-si60-30yr]` (STOCH) | basal_area | 0.3487% | 0.5000% | PASS |
| `test_ne_expanded_species_parity[sm-si60-30yr]` (STOCH) | qmd | 0.1753% | 0.5000% | PASS |
| `test_ne_expanded_species_parity[sm-si60-30yr]` (STOCH) | tpa | 0.0014% | 0.5000% | PASS |
| `test_ne_expanded_species_parity[yb-si60-30yr]` (STOCH) | volume | 5.7525% | 1.0000% | FAIL |
| `test_ne_expanded_species_parity[yb-si60-30yr]` (STOCH) | basal_area | 5.1907% | 0.5000% | FAIL |
| `test_ne_expanded_species_parity[yb-si60-30yr]` (STOCH) | qmd | 2.5999% | 0.5000% | FAIL |
| `test_ne_expanded_species_parity[yb-si60-30yr]` (STOCH) | top_height | 0.2245% | 0.5000% | PASS |
| `test_ne_expanded_species_parity[yb-si60-30yr]` (STOCH) | tpa | 0.0757% | 0.5000% | PASS |

### SN

| test | metric | measured Δ | band | verdict |
|---|---|--:|--:|:--:|
| `test_sn_gold_standard_lp_si70_25yr` (STOCH) | volume | 3.3696% | 1.0000% | FAIL |
| `test_sn_gold_standard_lp_si70_25yr` (STOCH) | top_height | 2.1085% | 0.5000% | FAIL |
| `test_sn_gold_standard_lp_si70_25yr` (STOCH) | basal_area | 1.3743% | 0.5185% | FAIL |
| `test_sn_gold_standard_lp_si70_25yr` (STOCH) | qmd | 1.0948% | 0.5000% | FAIL |
| `test_sn_gold_standard_lp_si70_25yr` (STOCH) | tpa | 0.8118% | 0.5000% | FAIL |
| `test_sn_off_baseline_parity[lp-si90-50yr]` (STOCH) | top_height | 3.0801% | 0.5000% | FAIL |
| `test_sn_off_baseline_parity[lp-si90-50yr]` (STOCH) | basal_area | 2.7801% | 0.5926% | FAIL |
| `test_sn_off_baseline_parity[lp-si90-50yr]` (STOCH) | qmd | 1.5789% | 0.5000% | FAIL |
| `test_sn_off_baseline_parity[lp-si90-50yr]` (STOCH) | volume | 1.3122% | 1.0000% | FAIL |
| `test_sn_off_baseline_parity[lp-si90-50yr]` (STOCH) | tpa | 0.3924% | 0.5000% | PASS |
| `test_sn_off_baseline_parity[sp-si65-25yr]` (STOCH) | volume | 6.1161% | 1.0000% | FAIL |
| `test_sn_off_baseline_parity[sp-si65-25yr]` (STOCH) | basal_area | 4.0157% | 0.7385% | FAIL |
| `test_sn_off_baseline_parity[sp-si65-25yr]` (STOCH) | qmd | 1.9326% | 0.5000% | FAIL |
| `test_sn_off_baseline_parity[sp-si65-25yr]` (STOCH) | top_height | 0.7280% | 0.5000% | FAIL |
| `test_sn_off_baseline_parity[sp-si65-25yr]` (STOCH) | tpa | 0.1047% | 0.5000% | PASS |
| `test_sn_off_baseline_parity[sa-si75-25yr]` (STOCH) | volume | 5.9210% | 1.4565% | FAIL |
| `test_sn_off_baseline_parity[sa-si75-25yr]` (STOCH) | top_height | 3.5941% | 0.5000% | FAIL |
| `test_sn_off_baseline_parity[sa-si75-25yr]` (STOCH) | basal_area | 1.8473% | 1.3983% | FAIL |
| `test_sn_off_baseline_parity[sa-si75-25yr]` (STOCH) | qmd | 1.0567% | 0.6301% | FAIL |
| `test_sn_off_baseline_parity[sa-si75-25yr]` (STOCH) | tpa | 0.2792% | 0.5000% | PASS |
| `test_sn_expanded_species_parity[ll-si70-25yr]` (STOCH) | volume | 5.3469% | 1.0000% | FAIL |
| `test_sn_expanded_species_parity[ll-si70-25yr]` (STOCH) | basal_area | 2.8601% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[ll-si70-25yr]` (STOCH) | tpa | 1.6412% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[ll-si70-25yr]` (STOCH) | top_height | 1.6014% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[ll-si70-25yr]` (STOCH) | qmd | 0.5964% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[vp-si60-25yr]` (STOCH) | volume | 4.8133% | 1.0000% | FAIL |
| `test_sn_expanded_species_parity[vp-si60-25yr]` (STOCH) | basal_area | 3.8108% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[vp-si60-25yr]` (STOCH) | qmd | 1.8420% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[vp-si60-25yr]` (STOCH) | top_height | 1.7274% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[vp-si60-25yr]` (STOCH) | tpa | 0.0863% | 0.5000% | PASS |
| `test_sn_expanded_species_parity[wp-si70-25yr]` (STOCH) | volume | 7.9908% | 1.0000% | FAIL |
| `test_sn_expanded_species_parity[wp-si70-25yr]` (STOCH) | basal_area | 7.0308% | 0.7497% | FAIL |
| `test_sn_expanded_species_parity[wp-si70-25yr]` (STOCH) | qmd | 3.6153% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[wp-si70-25yr]` (STOCH) | top_height | 1.5184% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[wp-si70-25yr]` (STOCH) | tpa | 0.0702% | 0.5000% | PASS |
| `test_sn_expanded_species_parity[yp-si80-25yr]` (STOCH) | volume | 3.1121% | 1.0000% | FAIL |
| `test_sn_expanded_species_parity[yp-si80-25yr]` (STOCH) | top_height | 3.0787% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[yp-si80-25yr]` (STOCH) | tpa | 0.3858% | 0.5000% | PASS |
| `test_sn_expanded_species_parity[yp-si80-25yr]` (STOCH) | qmd | 0.2293% | 0.5000% | PASS |
| `test_sn_expanded_species_parity[yp-si80-25yr]` (STOCH) | basal_area | 0.0765% | 0.9144% | PASS |
| `test_sn_expanded_species_parity[su-si75-25yr]` (STOCH) | basal_area | 4.2680% | 0.8532% | FAIL |
| `test_sn_expanded_species_parity[su-si75-25yr]` (STOCH) | qmd | 2.1415% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[su-si75-25yr]` (STOCH) | volume | 2.0621% | 1.0000% | FAIL |
| `test_sn_expanded_species_parity[su-si75-25yr]` (STOCH) | top_height | 2.0410% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[su-si75-25yr]` (STOCH) | tpa | 0.0369% | 0.5000% | PASS |
| `test_sn_expanded_species_parity[wo-si65-25yr]` (STOCH) | top_height | 2.9642% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[wo-si65-25yr]` (STOCH) | basal_area | 0.9414% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[wo-si65-25yr]` (STOCH) | qmd | 0.3221% | 0.5000% | PASS |
| `test_sn_expanded_species_parity[wo-si65-25yr]` (STOCH) | tpa | 0.3033% | 0.5000% | PASS |
| `test_sn_expanded_species_parity[wo-si65-25yr]` (STOCH) | volume | 0.2276% | 1.0000% | PASS |
| `test_sn_expanded_species_parity[rm-si65-25yr]` (STOCH) | basal_area | 5.5844% | 0.8124% | FAIL |
| `test_sn_expanded_species_parity[rm-si65-25yr]` (STOCH) | qmd | 2.8079% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[rm-si65-25yr]` (STOCH) | volume | 1.3210% | 1.0000% | FAIL |
| `test_sn_expanded_species_parity[rm-si65-25yr]` (STOCH) | top_height | 0.3253% | 0.5000% | PASS |
| `test_sn_expanded_species_parity[rm-si65-25yr]` (STOCH) | tpa | 0.1087% | 0.5000% | PASS |
| `test_sn_expanded_species_parity[by-si70-25yr]` (STOCH) | volume | 9.8896% | 1.2286% | FAIL |
| `test_sn_expanded_species_parity[by-si70-25yr]` (STOCH) | basal_area | 8.7361% | 1.7190% | FAIL |
| `test_sn_expanded_species_parity[by-si70-25yr]` (STOCH) | qmd | 4.2317% | 0.8584% | FAIL |
| `test_sn_expanded_species_parity[by-si70-25yr]` (STOCH) | top_height | 2.0400% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[by-si70-25yr]` (STOCH) | tpa | 0.0759% | 0.5000% | PASS |
| `test_sn_expanded_species_parity[hm-si55-25yr]` (STOCH) | volume | 5.4126% | 1.0000% | FAIL |
| `test_sn_expanded_species_parity[hm-si55-25yr]` (STOCH) | top_height | 0.9010% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[hm-si55-25yr]` (STOCH) | basal_area | 0.8500% | 0.5000% | FAIL |
| `test_sn_expanded_species_parity[hm-si55-25yr]` (STOCH) | qmd | 0.4938% | 0.5000% | PASS |
| `test_sn_expanded_species_parity[hm-si55-25yr]` (STOCH) | tpa | 0.1419% | 0.5000% | PASS |

## M2 — PNW (PN, WC, EC)


### EC

| test | metric | measured Δ | band | verdict |
|---|---|--:|--:|:--:|
| `test_ec_planted_parity[df-si80-25yr]` (DET) | volume | 52.7132% | 1.000% | FAIL |
| `test_ec_planted_parity[df-si80-25yr]` (DET) | basal_area | 19.2077% | 0.500% | FAIL |
| `test_ec_planted_parity[df-si80-25yr]` (DET) | top_height | 16.3011% | 0.500% | FAIL |
| `test_ec_planted_parity[df-si80-25yr]` (DET) | tpa | 12.5789% | 0.500% | FAIL |
| `test_ec_planted_parity[df-si80-25yr]` (DET) | qmd | 2.9005% | 0.500% | FAIL |
| `test_ec_planted_parity[pp-si70-25yr]` (DET) | volume | 43.0450% | 1.000% | FAIL |
| `test_ec_planted_parity[pp-si70-25yr]` (DET) | basal_area | 28.8653% | 0.500% | FAIL |
| `test_ec_planted_parity[pp-si70-25yr]` (DET) | top_height | 23.9439% | 0.500% | FAIL |
| `test_ec_planted_parity[pp-si70-25yr]` (DET) | qmd | 16.1793% | 0.500% | FAIL |
| `test_ec_planted_parity[pp-si70-25yr]` (DET) | tpa | 1.2435% | 0.500% | FAIL |
| `test_ec_planted_parity[lp-si70-25yr]` (DET) | volume | 30.1156% | 1.000% | FAIL |
| `test_ec_planted_parity[lp-si70-25yr]` (DET) | top_height | 21.8286% | 0.500% | FAIL |
| `test_ec_planted_parity[lp-si70-25yr]` (DET) | basal_area | 14.8325% | 0.500% | FAIL |
| `test_ec_planted_parity[lp-si70-25yr]` (DET) | tpa | 13.6108% | 0.500% | FAIL |
| `test_ec_planted_parity[lp-si70-25yr]` (DET) | qmd | 13.4193% | 0.500% | FAIL |

### PN

| test | metric | measured Δ | band | verdict |
|---|---|--:|--:|:--:|
| `test_pn_gold_standard_df_si100_30yr` (STOCH) | volume | 15.9202% | 1.0000% | SKIP |
| `test_pn_gold_standard_df_si100_30yr` (STOCH) | basal_area | 9.7818% | 0.5000% | FAIL |
| `test_pn_gold_standard_df_si100_30yr` (STOCH) | qmd | 5.0740% | 0.5000% | FAIL |
| `test_pn_gold_standard_df_si100_30yr` (STOCH) | top_height | 3.0019% | 0.5000% | FAIL |
| `test_pn_gold_standard_df_si100_30yr` (STOCH) | tpa | 0.5676% | 0.5000% | FAIL |
| `test_pn_expanded_species_parity[wh-si100-30yr]` (STOCH) | volume | 6.0450% | 1.0000% | SKIP |
| `test_pn_expanded_species_parity[wh-si100-30yr]` (STOCH) | basal_area | 1.8729% | 0.5000% | FAIL |
| `test_pn_expanded_species_parity[wh-si100-30yr]` (STOCH) | top_height | 1.0387% | 0.5000% | FAIL |
| `test_pn_expanded_species_parity[wh-si100-30yr]` (STOCH) | qmd | 1.0275% | 0.5000% | FAIL |
| `test_pn_expanded_species_parity[wh-si100-30yr]` (STOCH) | tpa | 0.1921% | 0.5000% | PASS |
| `test_pn_expanded_species_parity[rc-si100-30yr]` (STOCH) | volume | 21.2511% | 1.0000% | SKIP |
| `test_pn_expanded_species_parity[rc-si100-30yr]` (STOCH) | basal_area | 2.6121% | 1.0990% | FAIL |
| `test_pn_expanded_species_parity[rc-si100-30yr]` (STOCH) | qmd | 1.0870% | 0.5499% | FAIL |
| `test_pn_expanded_species_parity[rc-si100-30yr]` (STOCH) | tpa | 0.4113% | 0.5000% | PASS |
| `test_pn_expanded_species_parity[rc-si100-30yr]` (STOCH) | top_height | 0.3447% | 0.5000% | PASS |
| `test_pn_expanded_species_parity[ra-si80-30yr]` (STOCH) | top_height | 14.5647% | 0.5000% | FAIL |
| `test_pn_expanded_species_parity[ra-si80-30yr]` (STOCH) | volume | 12.3063% | 1.0000% | SKIP |
| `test_pn_expanded_species_parity[ra-si80-30yr]` (STOCH) | basal_area | 2.8241% | 0.6229% | FAIL |
| `test_pn_expanded_species_parity[ra-si80-30yr]` (STOCH) | tpa | 2.0592% | 0.5000% | FAIL |
| `test_pn_expanded_species_parity[ra-si80-30yr]` (STOCH) | qmd | 0.3931% | 0.5000% | PASS |

### WC

| test | metric | measured Δ | band | verdict |
|---|---|--:|--:|:--:|
| `test_wc_gold_standard_df_si100_30yr` (STOCH) | volume | 5.6630% | 1.0000% | SKIP |
| `test_wc_gold_standard_df_si100_30yr` (STOCH) | basal_area | 3.7696% | 0.6012% | FAIL |
| `test_wc_gold_standard_df_si100_30yr` (STOCH) | qmd | 1.4312% | 0.5000% | FAIL |
| `test_wc_gold_standard_df_si100_30yr` (STOCH) | top_height | 0.9011% | 0.5000% | FAIL |
| `test_wc_gold_standard_df_si100_30yr` (STOCH) | tpa | 0.8580% | 0.5000% | FAIL |
| `test_wc_expanded_species_parity[wh-si100-30yr]` (STOCH) | volume | 2.9444% | 1.0000% | SKIP |
| `test_wc_expanded_species_parity[wh-si100-30yr]` (STOCH) | top_height | 0.9919% | 0.5000% | FAIL |
| `test_wc_expanded_species_parity[wh-si100-30yr]` (STOCH) | basal_area | 0.2805% | 0.5377% | PASS |
| `test_wc_expanded_species_parity[wh-si100-30yr]` (STOCH) | qmd | 0.1537% | 0.5000% | PASS |
| `test_wc_expanded_species_parity[wh-si100-30yr]` (STOCH) | tpa | 0.0232% | 0.5000% | PASS |
| `test_wc_expanded_species_parity[rc-si100-30yr]` (STOCH) | volume | 23.6126% | 1.0000% | SKIP |
| `test_wc_expanded_species_parity[rc-si100-30yr]` (STOCH) | basal_area | 0.8072% | 0.6434% | FAIL |
| `test_wc_expanded_species_parity[rc-si100-30yr]` (STOCH) | top_height | 0.6550% | 0.5000% | FAIL |
| `test_wc_expanded_species_parity[rc-si100-30yr]` (STOCH) | qmd | 0.4108% | 0.5000% | PASS |
| `test_wc_expanded_species_parity[rc-si100-30yr]` (STOCH) | tpa | 0.0198% | 0.5000% | PASS |
| `test_wc_expanded_species_parity[ra-si80-30yr]` (STOCH) | volume | 15.8499% | 1.0000% | SKIP |
| `test_wc_expanded_species_parity[ra-si80-30yr]` (STOCH) | top_height | 14.6056% | 0.5000% | FAIL |
| `test_wc_expanded_species_parity[ra-si80-30yr]` (STOCH) | basal_area | 11.2298% | 0.6229% | FAIL |
| `test_wc_expanded_species_parity[ra-si80-30yr]` (STOCH) | qmd | 4.3346% | 0.5000% | FAIL |
| `test_wc_expanded_species_parity[ra-si80-30yr]` (STOCH) | tpa | 3.0069% | 0.5000% | FAIL |

## M3 — Hard tier (CA, WS, OP, OC)


### CA

| test | metric | measured Δ | band | verdict |
|---|---|--:|--:|:--:|
| `test_ca_gold_standard_pp_si90_30yr` (STOCH) | volume | 44.8514% | 1.0000% | FAIL |
| `test_ca_gold_standard_pp_si90_30yr` (STOCH) | top_height | 42.4133% | 0.5000% | FAIL |
| `test_ca_gold_standard_pp_si90_30yr` (STOCH) | tpa | 39.7058% | 0.5695% | FAIL |
| `test_ca_gold_standard_pp_si90_30yr` (STOCH) | qmd | 20.1264% | 0.5704% | FAIL |
| `test_ca_gold_standard_pp_si90_30yr` (STOCH) | basal_area | 12.9932% | 0.6573% | FAIL |
| `test_ca_expanded_species_parity[df-si80-30yr]` (STOCH) | volume | 103.6040% | 1.0000% | FAIL |
| `test_ca_expanded_species_parity[df-si80-30yr]` (STOCH) | basal_area | 52.0266% | 0.9299% | FAIL |
| `test_ca_expanded_species_parity[df-si80-30yr]` (STOCH) | qmd | 36.6046% | 0.6500% | FAIL |
| `test_ca_expanded_species_parity[df-si80-30yr]` (STOCH) | top_height | 36.2004% | 0.5000% | FAIL |
| `test_ca_expanded_species_parity[df-si80-30yr]` (STOCH) | tpa | 18.5333% | 0.5000% | FAIL |
| `test_ca_expanded_species_parity[wf-si70-30yr]` (STOCH) | volume | 89.6449% | 1.0000% | FAIL |
| `test_ca_expanded_species_parity[wf-si70-30yr]` (STOCH) | basal_area | 34.7051% | 0.6930% | FAIL |
| `test_ca_expanded_species_parity[wf-si70-30yr]` (STOCH) | top_height | 34.6156% | 0.5000% | FAIL |
| `test_ca_expanded_species_parity[wf-si70-30yr]` (STOCH) | qmd | 17.1645% | 0.5000% | FAIL |
| `test_ca_expanded_species_parity[wf-si70-30yr]` (STOCH) | tpa | 1.8762% | 0.5000% | FAIL |
| `test_ca_expanded_species_parity[jp-si70-30yr]` (STOCH) | top_height | 43.8100% | 0.5000% | FAIL |
| `test_ca_expanded_species_parity[jp-si70-30yr]` (STOCH) | tpa | 41.6370% | 0.7021% | FAIL |
| `test_ca_expanded_species_parity[jp-si70-30yr]` (STOCH) | qmd | 37.5554% | 0.5119% | FAIL |
| `test_ca_expanded_species_parity[jp-si70-30yr]` (STOCH) | basal_area | 10.4307% | 0.5233% | FAIL |
| `test_ca_expanded_species_parity[jp-si70-30yr]` (STOCH) | volume | 5.0756% | 1.0000% | FAIL |

### OC

| test | metric | measured Δ | band | verdict |
|---|---|--:|--:|:--:|
| `test_oc_planted_parity[pp-si70-25yr]` (DET) | volume | 87.3175% | 1.000% | FAIL |
| `test_oc_planted_parity[pp-si70-25yr]` (DET) | basal_area | 48.4630% | 0.500% | FAIL |
| `test_oc_planted_parity[pp-si70-25yr]` (DET) | top_height | 24.1251% | 0.500% | FAIL |
| `test_oc_planted_parity[pp-si70-25yr]` (DET) | qmd | 20.9483% | 0.500% | FAIL |
| `test_oc_planted_parity[pp-si70-25yr]` (DET) | tpa | 1.4861% | 0.500% | FAIL |
| `test_oc_planted_parity_df[df-si80-25yr]` (DET) | volume | 471.0633% | 1.000% | FAIL |
| `test_oc_planted_parity_df[df-si80-25yr]` (DET) | basal_area | 255.8201% | 0.500% | FAIL |
| `test_oc_planted_parity_df[df-si80-25yr]` (DET) | qmd | 87.9138% | 0.500% | FAIL |
| `test_oc_planted_parity_df[df-si80-25yr]` (DET) | top_height | 58.6572% | 0.500% | FAIL |
| `test_oc_planted_parity_df[df-si80-25yr]` (DET) | tpa | 0.7629% | 0.500% | FAIL |
| `test_oc_planted_parity_df[df-si100-50yr]` (DET) | volume | 84.1579% | 1.000% | FAIL |
| `test_oc_planted_parity_df[df-si100-50yr]` (DET) | basal_area | 82.8822% | 0.500% | FAIL |
| `test_oc_planted_parity_df[df-si100-50yr]` (DET) | qmd | 37.3111% | 0.500% | FAIL |
| `test_oc_planted_parity_df[df-si100-50yr]` (DET) | top_height | 20.6924% | 0.500% | FAIL |
| `test_oc_planted_parity_df[df-si100-50yr]` (DET) | tpa | 3.0053% | 0.500% | FAIL |

### OP

| test | metric | measured Δ | band | verdict |
|---|---|--:|--:|:--:|
| `test_op_gold_standard_df[df-si120-25yr]` (DET) | volume | inf% | 1.000% | FAIL |
| `test_op_gold_standard_df[df-si120-25yr]` (DET) | basal_area | 1316899184.2198% | 0.500% | FAIL |
| `test_op_gold_standard_df[df-si120-25yr]` (DET) | tpa | 860925.1541% | 0.500% | FAIL |
| `test_op_gold_standard_df[df-si120-25yr]` (DET) | qmd | 3810.7696% | 0.500% | FAIL |
| `test_op_gold_standard_df[df-si120-25yr]` (DET) | top_height | 468.1839% | 0.500% | FAIL |
| `test_op_expanded_species_parity[wh-si120-25yr]` (DET) | basal_area | 44.3528% | 0.500% | FAIL |
| `test_op_expanded_species_parity[wh-si120-25yr]` (DET) | volume | 33.5631% | 1.000% | FAIL |
| `test_op_expanded_species_parity[wh-si120-25yr]` (DET) | qmd | 20.6081% | 0.500% | FAIL |
| `test_op_expanded_species_parity[wh-si120-25yr]` (DET) | top_height | 17.9921% | 0.500% | FAIL |
| `test_op_expanded_species_parity[wh-si120-25yr]` (DET) | tpa | 0.7662% | 0.500% | FAIL |
| `test_op_expanded_species_parity[rc-si120-25yr]` (DET) | volume | 86.5170% | 1.000% | FAIL |
| `test_op_expanded_species_parity[rc-si120-25yr]` (DET) | top_height | 38.6506% | 0.500% | FAIL |
| `test_op_expanded_species_parity[rc-si120-25yr]` (DET) | basal_area | 37.6918% | 0.500% | FAIL |
| `test_op_expanded_species_parity[rc-si120-25yr]` (DET) | qmd | 17.5838% | 0.500% | FAIL |
| `test_op_expanded_species_parity[rc-si120-25yr]` (DET) | tpa | 0.4134% | 0.500% | PASS |
| `test_op_expanded_species_parity[ra-si120-25yr]` (DET) | basal_area | 201.0233% | 0.500% | FAIL |
| `test_op_expanded_species_parity[ra-si120-25yr]` (DET) | volume | 110.0978% | 1.000% | FAIL |
| `test_op_expanded_species_parity[ra-si120-25yr]` (DET) | qmd | 74.4142% | 0.500% | FAIL |
| `test_op_expanded_species_parity[ra-si120-25yr]` (DET) | top_height | 2.3583% | 0.500% | FAIL |
| `test_op_expanded_species_parity[ra-si120-25yr]` (DET) | tpa | 1.0481% | 0.500% | FAIL |

### WS

| test | metric | measured Δ | band | verdict |
|---|---|--:|--:|:--:|
| `test_ws_gold_standard_pp_si90_30yr` (STOCH) | volume | 305.7766% | 1.0000% | FAIL |
| `test_ws_gold_standard_pp_si90_30yr` (STOCH) | basal_area | 101.9117% | 0.5000% | FAIL |
| `test_ws_gold_standard_pp_si90_30yr` (STOCH) | top_height | 72.4892% | 0.5000% | FAIL |
| `test_ws_gold_standard_pp_si90_30yr` (STOCH) | qmd | 55.1745% | 0.5000% | FAIL |
| `test_ws_gold_standard_pp_si90_30yr` (STOCH) | tpa | 16.1477% | 0.5306% | FAIL |
| `test_ws_expanded_species_parity[df-si80-30yr]` (STOCH) | volume | 418.5013% | 1.0000% | FAIL |
| `test_ws_expanded_species_parity[df-si80-30yr]` (STOCH) | basal_area | 160.0719% | 0.5000% | FAIL |
| `test_ws_expanded_species_parity[df-si80-30yr]` (STOCH) | qmd | 90.9054% | 0.5000% | FAIL |
| `test_ws_expanded_species_parity[df-si80-30yr]` (STOCH) | top_height | 85.1290% | 0.5000% | FAIL |
| `test_ws_expanded_species_parity[df-si80-30yr]` (STOCH) | tpa | 28.6417% | 0.5000% | FAIL |
| `test_ws_expanded_species_parity[lp-si70-30yr]` (STOCH) | volume | 493.0297% | 1.0000% | FAIL |
| `test_ws_expanded_species_parity[lp-si70-30yr]` (STOCH) | basal_area | 254.7091% | 0.5000% | FAIL |
| `test_ws_expanded_species_parity[lp-si70-30yr]` (STOCH) | qmd | 107.6057% | 0.5000% | FAIL |
| `test_ws_expanded_species_parity[lp-si70-30yr]` (STOCH) | top_height | 74.9058% | 0.5000% | FAIL |
| `test_ws_expanded_species_parity[lp-si70-30yr]` (STOCH) | tpa | 17.7031% | 0.5000% | FAIL |

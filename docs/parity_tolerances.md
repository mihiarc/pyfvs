# pyfvs Parity Tolerance Regime

Normalized 2026-06-21. One principled tolerance regime for the whole parity
suite (`tests/parity/`), replacing the ad-hoc per-test bands. This round
**undoes earlier tolerance corner-cutting**: it tightens (never loosens) the
bands and reclassifies every test that the loose band was masking. Implemented
in `tests/parity/conftest.py::parity_tolerance` (the bands) and
`tests/parity/_helpers.py` (`assert_metrics_close`, `assert_metrics_close_mean`).

## The regime

### Deterministic variants — EC, OP, OC
These run `stochastic=False` against the deterministic native run, so there is
no sampling noise to absorb. They are held to the **floor** directly:

| metric | floor band |
|---|---|
| TPA, BA, QMD, top_height, DBH, per-tree height | **0.5%** relative |
| volume | **1.0%** relative |

Volume carries exactly one extra band-width because it compounds DBH² × height;
nothing more.

### Stochastic multi-seed variants — SN, LS, PN, WC, NE, CS, CA
Parity here is stochastic-vs-stochastic (native FVS defaults DGSD > 0). pyfvs is
run at **`n_seeds = 10`** sequential seeds (base 42) and the *mean* is compared.
Per metric:

```
band = min( cap , max( floor , 3 × relative_SEM ) )
```

* `relative_SEM = (stdev_across_seeds / sqrt(n_seeds)) / |mean|` — the standard
  error of the N-seed mean, **measured live from the same seeds**, never chosen.
* `3 × SEM` ≈ a 3-σ (~99.7%) containment of the sampling noise of the mean.
* `floor` is the deterministic floor above (lower bound — the band is never
  tighter than the deterministic case).
* `cap` is the absolute ceiling (below) — the band may **never** exceed it.

### Cap (absolute ceiling — the pre-normalization values)
| metric | cap |
|---|---|
| TPA | 2% |
| BA, QMD, top_height, DBH, per-tree height | 5% |
| volume | 10% |

**The regime can only tighten or hold, never loosen** (every band ≤ cap). If
`3×SEM` would exceed the cap for a metric, that is a *finding* — n_seeds is too
low or the stochastic process is mis-scaled — to be fixed by raising n_seeds
(which shrinks SEM ∝ 1/√N) or flagged; a looser-than-cap band is never adopted.

### n_seeds
`PARITY_N_SEEDS = 10`, a **single shared constant** in
`tests/parity/_helpers.py` (the default of `run_pyfvs_multi_seed`); no
per-variant copies. Chosen because at N = 10 the measured `3×SEM` stays under
the cap for every metric (below), so the cap is never the binding constraint
from sampling noise.

## Cap-guard result (measured, n_seeds = 10)

Across all 41 stochastic scenarios, the **maximum** measured `3×SEM` per metric:

| metric | max 3×SEM | cap | under cap? |
|---|--:|--:|:--:|
| TPA | 0.70% | 2% | ✅ |
| BA | 1.72% | 5% | ✅ |
| QMD | 0.86% | 5% | ✅ |
| top_height | 0.36% | 5% | ✅ |
| volume | 1.46% | 10% | ✅ |

Zero metrics hit the cap (`capped=True` count = 0), so n_seeds = 10 is
sufficient; no bump required. Because `3×SEM` is well below the floor for most
metrics, the stochastic band is the **floor (0.5% / 1.0%)** in the large
majority of cases — i.e. stochastic variants are held to essentially the same
tightness as deterministic ones.

## Volume handling (uniform, per-variant decision)

Volume is compared for **every** variant unless a *real volume-library gap*
exists, in which case `skip_keys=("volume",)` carries a variant-specific reason
and a tracking item. No unexplained skips.

| variant | volume | decision / reason |
|---|---|---|
| SN, EC, OC, CA, WS, OP | **compared** | No separately-tracked cubic-volume-library gap distinct from growth; volume is part of each comparison (and of the xfail finding where it diverges). |
| NE | **compared** (skip removed) | Cubic volume tracks native (gold RM +0.18%); the previously *unexplained* skip is removed. NE board-foot `logs.f` is a separate item but cubic volume is gated. |
| CS | **compared** (skip removed) | No MISSING volume row in `docs/cs_fidelity_map.md`; the previously *unexplained* skip is removed. |
| LS | **skipped** | Real volume-library gap: `cfvol.f`/`bfvol.f` MISSING (`docs/ls_fidelity_map.md` VOLUME); measured drift +1.3–6.3%. Tracked there. |
| PN | **skipped** | Real volume-library gap: `bfvol.f`/`logs.f` MISSING (`docs/pn_fidelity_map.md` VOLUME); measured drift up to +21% (RC). Tracked there. |
| WC | **skipped** | Real volume-library gap: `bfvol.f`/`logs.f` MISSING (`docs/wc_fidelity_map.md` VOLUME); measured drift up to +24% (RC). Tracked there. |

## Pre/post tally diff

Reproduce: `uv run pytest tests/parity/ -m parity`.

| | pre (loose band) | post (this regime) |
|---|---|---|
| pass | 40 | **14** |
| xfail | 25 | **51** |
| xpass | 0 | 0 |
| fail | 0 | 0 |

The 14 remaining passes are all **structural/smoke** tests (EC registry /
coefficient-shape / reasonable-growth-range / grows-without-crashing; OC
cycle-length / tanoak / dds-halving) — none is a native-metric comparison.
**Every stochastic/deterministic metric comparison now either xfails (documented
divergence) or — there are none — passes the 0.5% floor.** That the entire suite
of metric comparisons fails the tightened band is the finding: the old 5%/10%
band was masking 0.5–250% divergence across every variant. All 51 xfails are
`strict=True`.

### Tests that changed state (26 pass → strict xfail)

Each was within the old 5%/10% band and exceeds the tightened band; the
measured divergence is recorded in the test's xfail reason. Volume shown only
where it is compared (not skipped).

**SN** (volume compared):
- `gold lp-si70-25yr` — BA +1.37%, QMD +1.09%, topH +2.11%, vol +3.37%, TPA +0.81%
- `lp-si90-50yr` — BA +2.78%, QMD +1.58%, topH +3.08%, vol +1.31%
- `sp-si65-25yr` — BA +4.02%, QMD +1.93%, vol +6.12%
- `sa-si75-25yr` — BA +1.85%, QMD +1.06%, topH +3.59%, vol +5.92%
- `ll-si70-25yr` — TPA +1.64%, BA +2.86%, topH +1.60%, vol +5.35%
- `vp-si60-25yr` — BA +3.81%, QMD +1.84%, topH +1.73%, vol +4.81%
- `yp-si80-25yr` — topH +3.08%, vol +3.11%
- `su-si75-25yr` — BA +4.27%, QMD +2.14%, topH +2.04%, vol +2.06%
- `wo-si65-25yr` — BA +0.94%, topH +2.96%
- `hm-si55-25yr` — BA +0.85%, topH +0.90%, vol +5.41%

**LS** (volume skipped): `wa` BA +0.58%/topH +0.94%; `jp` BA +3.43%/QMD +1.69%;
`sm` BA +1.23%/topH +1.21%; `qa` TPA +1.67%/BA +2.52%/QMD +2.11% (had been
un-xfailed 2026-06-21 under the loose band — re-xfailed here).

**CS** (volume compared): `gold wo` BA +3.52%/QMD +1.80%/vol +4.61% (CS was
"4/4 clean" only under the loose band); `ro` BA +2.69%/topH +2.23%/vol +3.49%;
`sm` topH +1.06%; `yp` BA +1.93%/QMD +1.43%/vol +3.09%.

**NE** (volume now compared): `gold rm` BA +0.70%/topH +1.77%; `ro` topH
+2.56%/vol +1.02%; `sm` topH +1.52%.

**PN** (volume skipped): `wh` BA +1.87%/QMD +1.03%/topH +1.04%; `rc` BA
+2.61%/QMD +1.09% (both had been un-xfailed 2026-06-21 — re-xfailed here).

**WC** (volume skipped): `gold df` TPA +0.86%/BA +3.77%/QMD +1.43%/topH +0.90%;
`wh` topH +0.99%; `rc` BA +0.81%/topH +0.66% (gold + wh/rc had been un-xfailed
2026-06-21 — re-xfailed here).

The 14 pre-existing `strict=False` xfails (CA ×4, WS ×3, OP ×4, PN gold + ra,
WC ra) were flipped to `strict=True`; their pass/fail state is unchanged (still
xfail). The 11 already-`strict=True` xfails (EC ×3, LS gold, NE yb, OC ×3,
SN wp/rm/by) are unchanged.

## Raw measured-SEM table (n_seeds = 10, base seed 42)

`3×SEM` per metric per stochastic scenario, measured live during the suite run
(`PARITY_EMIT_SEM=1`). The applied band for a metric is `min(cap, max(floor,
3×SEM))`; since these are mostly below the 0.5%/1.0% floor, the floor binds.

| scenario | 3xSEM tpa | 3xSEM ba | 3xSEM qmd | 3xSEM topH | 3xSEM vol |
|---|--:|--:|--:|--:|--:|
| test_ca_gold_standard_pp_si90_30yr | 0.5695% | 0.6573% | 0.5704% | 0.0915% | 0.7116% |
| test_ca_expanded_species_parity[df-si80-30yr] | 0.4024% | 0.9299% | 0.6500% | 0.1233% | 0.8265% |
| test_ca_expanded_species_parity[wf-si70-30yr] | 0.0000% | 0.6930% | 0.3472% | 0.3018% | 0.7068% |
| test_ca_expanded_species_parity[jp-si70-30yr] | 0.7021% | 0.5233% | 0.5119% | 0.1586% | 0.5949% |
| test_cs_gold_standard_wo_si60_30yr | 0.0000% | 0.2464% | 0.1232% | 0.1993% | 0.3107% |
| test_cs_expanded_species_parity[ro-si65-30yr] | 0.0000% | 0.2744% | 0.1372% | 0.1501% | 0.3726% |
| test_cs_expanded_species_parity[sm-si60-30yr] | 0.0000% | 0.2631% | 0.1316% | 0.1785% | 0.3521% |
| test_cs_expanded_species_parity[yp-si70-30yr] | 0.0000% | 0.2816% | 0.1408% | 0.1507% | 0.3804% |
| test_ls_gold_standard_rn_si60_30yr | 0.0000% | 0.4839% | 0.2418% | 0.3415% | 0.6270% |
| test_ls_off_baseline_parity[wa-si60-30yr] | 0.0000% | 0.4655% | 0.2329% | 0.3629% | 0.6707% |
| test_ls_expanded_species_parity[jp-si60-30yr] | 0.0000% | 0.3179% | 0.1589% | 0.3324% | 0.4434% |
| test_ls_expanded_species_parity[sm-si55-30yr] | 0.0000% | 0.2528% | 0.1264% | 0.1850% | 0.3463% |
| test_ls_expanded_species_parity[qa-si70-30yr] | 0.1737% | 0.3081% | 0.2376% | 0.2873% | 0.4644% |
| test_ne_gold_standard_rm_si60_30yr | 0.0000% | 0.3096% | 0.1548% | 0.1822% | 0.3710% |
| test_ne_expanded_species_parity[ro-si60-30yr] | 0.0000% | 0.2059% | 0.1029% | 0.1529% | 0.2886% |
| test_ne_expanded_species_parity[sm-si60-30yr] | 0.0000% | 0.1832% | 0.0916% | 0.0983% | 0.2487% |
| test_ne_expanded_species_parity[yb-si60-30yr] | 0.0000% | 0.1840% | 0.0920% | 0.1055% | 0.2112% |
| test_pn_gold_standard_df_si100_30yr | 0.1342% | 0.1672% | 0.1371% | 0.0548% | 0.1324% |
| test_pn_expanded_species_parity[wh-si100-30yr] | 0.0000% | 0.4864% | 0.2436% | 0.0798% | 0.4350% |
| test_pn_expanded_species_parity[rc-si100-30yr] | 0.0000% | 1.0990% | 0.5499% | 0.0870% | 0.9608% |
| test_pn_expanded_species_parity[ra-si80-30yr] | 0.0000% | 0.6229% | 0.3116% | 0.0696% | 0.6246% |
| test_sn_gold_standard_lp_si70_25yr | 0.2534% | 0.5185% | 0.3761% | 0.0671% | 0.5143% |
| test_sn_off_baseline_parity[lp-si90-50yr] | 0.3105% | 0.5926% | 0.4279% | 0.0897% | 0.5928% |
| test_sn_off_baseline_parity[sp-si65-25yr] | 0.0000% | 0.7385% | 0.3693% | 0.1375% | 0.7878% |
| test_sn_off_baseline_parity[sa-si75-25yr] | 0.4279% | 1.3983% | 0.6301% | 0.0992% | 1.4565% |
| test_sn_expanded_species_parity[ll-si70-25yr] | 0.1645% | 0.4171% | 0.2856% | 0.1748% | 0.4437% |
| test_sn_expanded_species_parity[vp-si60-25yr] | 0.0000% | 0.3848% | 0.1924% | 0.2356% | 0.4055% |
| test_sn_expanded_species_parity[wp-si70-25yr] | 0.0000% | 0.7497% | 0.3748% | 0.3571% | 0.7866% |
| test_sn_expanded_species_parity[yp-si80-25yr] | 0.0000% | 0.9144% | 0.4577% | 0.1581% | 0.9349% |
| test_sn_expanded_species_parity[su-si75-25yr] | 0.0000% | 0.8532% | 0.4261% | 0.1955% | 0.8761% |
| test_sn_expanded_species_parity[wo-si65-25yr] | 0.0000% | 0.3239% | 0.1619% | 0.1532% | 0.3037% |
| test_sn_expanded_species_parity[rm-si65-25yr] | 0.0000% | 0.8124% | 0.4065% | 0.1603% | 0.6785% |
| test_sn_expanded_species_parity[by-si70-25yr] | 0.0000% | 1.7190% | 0.8584% | 0.1251% | 1.2286% |
| test_sn_expanded_species_parity[hm-si55-25yr] | 0.0000% | 0.4325% | 0.2162% | 0.1353% | 0.4007% |
| test_wc_gold_standard_df_si100_30yr | 0.0000% | 0.6012% | 0.3007% | 0.0789% | 0.5515% |
| test_wc_expanded_species_parity[wh-si100-30yr] | 0.0000% | 0.5377% | 0.2690% | 0.0779% | 0.4865% |
| test_wc_expanded_species_parity[rc-si100-30yr] | 0.0000% | 0.6434% | 0.3219% | 0.1442% | 0.6577% |
| test_wc_expanded_species_parity[ra-si80-30yr] | 0.0000% | 0.6229% | 0.3116% | 0.0696% | 0.6246% |
| test_ws_gold_standard_pp_si90_30yr | 0.5306% | 0.2982% | 0.2567% | 0.2313% | 0.3825% |
| test_ws_expanded_species_parity[df-si80-30yr] | 0.1293% | 0.4030% | 0.2521% | 0.2119% | 0.4480% |
| test_ws_expanded_species_parity[lp-si70-30yr] | 0.2448% | 0.3134% | 0.2646% | 0.1669% | 0.3534% |

(`3xSEM tpa = 0.0000%` rows are scenarios whose 10 seeds produced an identical
surviving TPA — mortality kill-counts are deterministic per cycle, so TPA has
zero seed-to-seed variance and its band is the 0.5% floor.)

*Regenerate this table:* `PARITY_EMIT_SEM=1 uv run pytest tests/parity/ -m parity -s`
then collect the `SEMROW` lines.

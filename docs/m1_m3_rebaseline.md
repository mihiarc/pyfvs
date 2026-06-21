# M1–M3 Re-baseline + Floor-Calibration Finding — 2026-06-21

Re-baselines the milestone scoping against the **post-normalization** parity
inventory (`docs/parity_inventory_2026-06-21.md`), replacing the stale pre-regime
"clear N xfails" counts, and reports a floor-calibration finding. **Measurement
and diagnosis only — no model code and no tolerance/regime change** (the 0.5%/1.0%
floor, 3×SEM bands, and cap stay exactly as committed in `docs/parity_tolerances.md`).
All divergence figures are measured (regenerated via
`PARITY_EMIT_SEM=1 uv run pytest tests/parity/ -m parity -s`), never estimated.

## 1. Old vs. new per-variant counts

The old milestone "clear N parity xfails" numbers came from the April string-grep
snapshot, against the **loose** 5%/10% band and a different test basis. Under the
tightened regime the meaningful count is **the number of metric-comparison tests
that fail ≥1 metric against the floor** (= the xfailed tests per variant). They
diverge sharply from the old numbers — the old counts are superseded.

| Variant | Tier | Old "clear N" | New (xfail metric-tests) | Note |
|---|---|--:|--:|---|
| SN | M1 | 5 | **13** | loose band hid SN gold + all off-baseline/expanded |
| LS | M1 | 7 | **5** | old count was per-species-sweep basis; 5 scenario tests |
| CS | M1 | 3 | **4** | was "4/4 clean" under the loose band — all 4 now fail |
| NE | M1 | 1 | **4** | |
| PN | M2 | 4 | **4** | |
| WC | M2 | 4 | **4** | |
| EC | M2 | 4 | **3** | 3 native-comparison planted tests (other "EC" were structural) |
| CA | M3 | (thin) | **4** | no prior count; coverage added 2026-06-21 |
| WS | M3 | (thin) | **3** | no prior count |
| OP | M3 | (thin) | **4** | no prior count |
| OC | M3 | 5 | **3** | 3 native-comparison planted tests |
| **Total** | | | **51** | |

## 2. Per-variant re-baselined scoping

"Failing metric-instances" counts metric×test comparisons that exceed the band
(of the 5 metrics per test; volume is `[SKIP]` for LS/PN/WC — a documented
volume-library gap, not gated). "Closest to floor" is the smallest failing
divergence (the nearest-to-parity gap); "worst (gated)" excludes skipped volume.

| Variant | Tier | xfail tests | failing metric-instances | closest-to-floor (gated) | worst (gated) | how far from the floor |
|---|---|--:|--:|---|---|---|
| **SN** | M1 | 13 | 48 | qmd +0.60% (ll) | volume +9.89% (by) | Whole suite off-floor; BA/QMD ~1–9%, volume worst. Largest M1 gap by test count. |
| **LS** | M1 | 5 | 14 (+5 vol skip) | top_height +0.53% (qa) | basal_area +6.04% (gold RN) | TPA matches (<0.03%); BA/QMD drift 1–6%; top_height bias is the parity frontier (closest case below). |
| **CS** | M1 | 4 | 14 | top_height +0.55% (gold) | volume +4.61% (gold) | TPA matches; BA/QMD/topH/vol all 0.5–4.6%. "Clean" was a loose-band artifact. |
| **NE** | M1 | 4 | 8 | basal_area +0.70% (gold RM) | volume +5.75% (yb) | TPA & most BA/QMD within floor; top_height (1.5–2.6%) and one BA/vol species (yb) are the gaps. Closest M1 variant to the floor overall. |
| **PN** | M2 | 4 | 12 (+4 vol skip) | tpa +0.57% (gold DF) | basal_area +9.78% (gold DF) | TPA near-floor; BA/QMD 1–10% (gold DF worst); RA top_height +14.6% outlier. Volume +6–21% (skipped, lib gap). |
| **WC** | M2 | 4 | 11 (+4 vol skip) | top_height +0.66% (rc) | top_height +14.61% (ra) | WH/RC near-floor (BA/topH <1%); RA is the outlier (BA +11%, topH +15%). Volume +3–24% (skipped, lib gap). |
| **EC** | M2 | 3 | 15 | tpa +1.24% (pp) | volume +52.7% (df) | **Deterministic.** Far off-floor on every metric (TPA 1–14%, BA 15–29%, vol 30–53%) — EC sub-models still PN/SN fallbacks. |
| **CA** | M3 | 4 | 20 | tpa +1.88% (wf) | volume +103.6% (df) | Every metric fails every test; top_height +34–44%, volume to +104%. SN-fallback / non-faithful HG. |
| **WS** | M3 | 3 | 15 | tpa +16.1% (gold) | volume +493% (lp) | Farthest from floor of all variants — stub-YAML scaffold (BA +100–255%, vol +300–493%). |
| **OP** | M3 | 4 | 19 | tpa +0.77% (wh) | volume +∞ (gold DF) | **Deterministic.** WH/RC/RA TPA near-floor (RC TPA +0.41% *passes*); growth 17–201%. Gold DF is the native-degenerate-DF blocker (∞). |
| **OC** | M3 | 3 | 15 | tpa +0.76% (df-si80) | volume +471% (df-si80) | **Deterministic.** TPA near-floor (mortality matches); ORGANON *growth* drives BA/QMD/topH/vol 20–471%. |

**Plain-language summary of distance from the floor:**
- **Near the floor** (frontier ~0.5–1%): LS, CS, NE, PN, WC — TPA already within floor; the gap is sub-2% BA/QMD/top_height drift. These are the realistic M1/M2 targets.
- **Mid (deterministic, 1–53%):** EC, OC, OP — TPA near/at floor but growth (and ORGANON/fallback sub-models) far off.
- **Far (10–490%+):** CA, WS — fallback/stub scaffolds; structural variant work, not fine-tuning.

## 3. Floor-calibration finding

### Parity frontier (every metric comparison, ascending measured divergence)

The smallest divergences are **TPA** comparisons that *pass* — down to **+0.0014%**
(NE sm-si60 TPA) — because per-cycle mortality kill-counts are deterministic, so
TPA carries near-zero seed-to-seed variance. In **deterministic** mode the closest
comparison, **OP rc-si120 TPA = +0.4134%, *passes* the 0.5% floor**. The frontier
of *failing* comparisons (nearest-to-parity gaps) is:

| rank | comparison | metric | measured Δ | band | kind |
|--:|---|---|--:|--:|---|
| 1 | LS `qa-si70-30yr` | top_height | **+0.5346%** | 0.5000% | STOCH |
| 2 | CS `gold wo-si60-30yr` | top_height | +0.5460% | 0.5000% | STOCH |
| 3 | LS `wa-si60-30yr` | basal_area | +0.5758% | 0.5000% | STOCH |
| 4 | SN `ll-si70-25yr` | qmd | +0.5964% | 0.5000% | STOCH |
| 5 | LS `sm-si55-30yr` | qmd | +0.6055% | 0.5000% | STOCH |
| 6 | WC `rc-si100-30yr` | top_height | +0.6550% | 0.5000% | STOCH |
| 7 | NE `gold rm-si60-30yr` | basal_area | +0.7000% | 0.5000% | STOCH |

### Single closest failing case — diagnosis

**LS `test_ls_expanded_species_parity[qa-si70-30yr]` · top_height · +0.5346%**
(band 0.5000%; 10-seed mean; quaking aspen, SI 70, 30 yr).

- **Not sampling noise.** The measured `3×SEM` for this comparison is **0.2873%**
  (`docs/parity_tolerances.md` raw table), well below the +0.5346% mean divergence
  — this is a real mean bias, not seed scatter.
- **Not floating-point.** A 0.5346% relative bias is ≈ 5.3×10⁻³. Floating-point
  intrinsic-function and order-of-operations error in the height path — the
  Chapman-Richards site curve (`exp`/`pow`) plus the `GMOD` modifier, accumulated
  over 3 LS cycles — is O(10⁻¹²) per operation and O(10⁻⁹) compounded: **six to
  seven orders of magnitude below** the observed residual. The top-height
  aggregation (`stand_metrics.py::calculate_top_height`, FVS `avht40.f`, exact
  mean of the 40 largest by DBH) introduces no model divergence.
- **STRUCTURAL.** The residual lives in the LS large-tree **height-growth** port:
  `large_tree_height_growth.py::calculate_height_growth` (LS branch,
  `ls/htgf.f:104-109`: `HTG = POTHTG · GMOD`, `GMOD = (1−(1−BALMOD)(1−RELHTA))·0.8`),
  specifically the **omitted OLDRN height-growth autocorrelation** (`ls/htgf.f:108`
  applies `HTG·(1+OLDRN)·GMOD`; pyfvs omits the `OLDRN` term). This is the *same*
  documented gap that drives the LS gold-standard RN top_height xfail (−8% there);
  for QA it surfaces as a small +0.53% top-height bias. A coefficient/algorithm
  difference — not FP.

### Recommendation on the 0.5% deterministic floor

**KEEP 0.5%. — RATIFIED by maintainer 2026-06-21.** The floor stays at 0.5%
(1.0% volume); no change to `tests/parity/conftest.py` / `_helpers.py`. The
recommendation below stands as the rationale of record.

Rationale, resting on an identified physical source — never on the pass/fail
outcome:
1. The single closest failing case (LS qa top_height +0.5346%) is **structural**
   (LS `htgf.f` OLDRN omission), ~6–7 orders of magnitude above FP noise. There is
   **no concrete floating-point source that legitimately exceeds 0.5%** for it.
2. Positive bound on FP: when the model logic agrees, pyfvs reproduces native far
   *below* 0.5% — **OP rc TPA = +0.41% deterministically (passes)**, and stochastic
   TPA means reach **+0.0014%**. So FP intrinsic-function + order-of-operations
   accumulation across these stand-level aggregates is empirically **well under
   0.5%**; 0.5% is not an FP-floor artifact, it sits comfortably between FP noise
   (<0.1%) and the structural divergences (≥0.53%).
3. Therefore 0.5% correctly separates "matches the Fortran" from "real model
   divergence." Loosening it would re-mask exactly the structural gaps this round
   exposed; tightening below ~0.1% would start catching FP. Keep 0.5%.

Per the goal's rule: a floor change would be recommended **only** if a concrete FP
source legitimately exceeded 0.5% for the closest case. None was found (the closest
case is structural), so the recommendation is **keep 0.5%**.

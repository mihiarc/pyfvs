# pyfvs Parity Scorecard — 2026-06-21

Baseline measurement of the pyfvs parity suite against **freshly compiled native
FVS libraries**. This is a **measurement-only** baseline: no growth, mortality,
or volume model code was changed to produce it. Failing tests are recorded as
failures, not "fixed."

## How this was produced

```bash
uv run pytest tests/parity/ -m parity -v
```

- **Native libraries:** all 11 variant `.so` files built today via
  `scripts/build_native_fvs.sh` and installed to `~/.fvs/lib/`
  (`FVS{ca,cs,ec,ls,ne,oc,op,pn,sn,wc,ws}.so`, timestamps 2026-06-21 06:50–06:52).
- **Discovery:** the parity `conftest.py` resolves libraries via
  `FVS_LIB_PATH` → `~/.fvs/lib` → `/usr/local/lib` → `./lib` (and auto-locates a
  sibling `ForestVegetationSimulator/bin` build). `FVS_LIB_PATH` was unset, so
  every library resolved from `~/.fvs/lib`.
- **Environment:** macOS arm64 (Darwin 25.5.0), Python 3.14.3, pytest 9.0.3,
  gfortran 15.2 (Homebrew). Run completed in ~16s.

### Proof: zero tests skipped or deselected for "native build not found"

The parity `conftest.py` will `pytest.skip(...)` an individual test with the
message *"FVS {variant} native library not found"* (and skip the whole module if
no libraries are available). The run produced **0 skips**:

```
collecting ... collected 54 items
...
============= 1 failed, 34 passed, 13 xfailed, 6 xpassed in 15.85s =============
```

`54 collected` = `1 failed + 34 passed + 13 xfailed + 6 xpassed` (54). There are
**no SKIPPED and no deselected** parity tests — every collected parity test
executed against a present native library. (The only "skip" strings in the
output are the test *name* `test_oc_tanoak_skips_conversion`, which **passed**,
and a `skip_keys` helper parameter — neither is a library-missing skip.)

## Scorecard — by variant

`pass` / `xfail` / `xpass` / `FAIL` are raw pytest outcomes. `xpass` =
unexpectedly passed (annotated `xfail`, `strict=False`) — a candidate to
un-xfail. `tests` is the count of collected parity tests for that variant.

| Variant | Region | tests | pass | xfail | xpass | FAIL | Note |
|---------|--------|------:|-----:|------:|------:|-----:|------|
| **SN** | Southern US | 13 | 10 | 3 | 0 | 0 | Reference variant. |
| **LS** | Lake States | 5 | 3 | 1 | 1 | 0 | 1 xpass (QA si70). |
| **CS** | Central States | 4 | 4 | 0 | 0 | 0 | Clean. |
| **NE** | Northeast | 4 | 3 | 1 | 0 | 0 | |
| **PN** | PNW Coast | 4 | 0 | 2 | 2 | 0 | Every case is xfail-annotated; 2 now xpass. |
| **WC** | West Cascades | 4 | 0 | 1 | 3 | 0 | 3 now xpass, incl. gold-standard DF. |
| **EC** | East Cascades | 13 | 10 | 3 | 0 | 0 | 3 native-comparison parity tests (all xfail); other 10 are structural/smoke. |
| **CA** | Inland California | 0 | — | — | — | — | **No parity test file.** Not covered (see Coverage gaps). |
| **WS** | Western Sierra | 0 | — | — | — | — | **No parity test file.** Not covered. |
| **OP** | ORGANON PNW | 0 | — | — | — | — | **No parity test file.** Not covered. |
| **OC** | SW Oregon (ORGANON) | 7 | 4 | 2 | 1F | 1 | **1 FAIL** (pp-si70). 4 passes are structural; 2 DF parity xfail. |
| **TOTAL** | | **54** | **34** | **13** | **6** | **1** | |

> **Note on EC/OC "pass" counts:** several EC and OC "passes" are structural or
> smoke tests (registry registration, coefficient-shape, reasonable-growth-range,
> "grows without crashing", DDS-conversion unit tests), not native-vs-pyfvs
> stand-metric comparisons. The actual native-comparison parity cases are: EC =
> 3 (`test_ec_planted_parity`, all xfail), OC = 3 (1 `test_oc_planted_parity`
> FAIL + 2 `test_oc_planted_parity_df` xfail). All other variants' counts are
> native-comparison parity tests.

## The 1 failure

**`tests/parity/test_oc_parity.py::test_oc_planted_parity[pp-si70-25yr]`** —
OC ponderosa pine, SI 70, 25 yr. pyfvs over-predicts on every metric:

| Metric | pyfvs | native | rel. diff | tol |
|--------|------:|-------:|----------:|----:|
| basal_area | 78.0646 | 52.5819 | **+48.46%** | 5% |
| qmd | 6.5560 | 5.4205 | **+20.95%** | 5% |
| top_height | 36.0814 | 29.0686 | **+24.13%** | 5% |
| volume | 1018.6621 | 543.8158 | **+87.32%** | 10% |

This case was an `xfail`→pass annotation calibrated in April against a
non-reproducible native build that agreed with pyfvs. The rebuilt `FVSoc.so`
(ORGANON-driven mortality) diverges sharply, so it is now a hard **FAIL**.
Recorded here as the M0 baseline signal for the open **OC ORGANON** gap —
**not modified to pass** (constraint: measurement-only). TPA matches closely
(per prior diagnosis ~333 vs ~328), so the divergence is diameter growth, not
tree count.

## The 6 xpasses (candidates to un-xfail)

These are annotated `xfail` but **passed** against the rebuilt native libs.
Confirm they are not native-build-version artifacts before flipping to plain
asserts (per the project journal's M0 reconciliation item):

| Test | Annotation date |
|------|-----------------|
| `test_ls_parity.py::test_ls_expanded_species_parity[qa-si70-30yr]` | 2026-04-21 (post linear-XWT fix) |
| `test_pn_parity.py::test_pn_expanded_species_parity[wh-si100-30yr]` | 2026-04-17 |
| `test_pn_parity.py::test_pn_expanded_species_parity[rc-si100-30yr]` | 2026-04-17 |
| `test_wc_parity.py::test_wc_gold_standard_df_si100_30yr` | 2026-04-17 (gold standard) |
| `test_wc_parity.py::test_wc_expanded_species_parity[wh-si100-30yr]` | 2026-04-17 |
| `test_wc_parity.py::test_wc_expanded_species_parity[rc-si100-30yr]` | 2026-04-17 |

## The 13 xfails (expected gaps)

| Test | Recorded reason (abbreviated) |
|------|-------------------------------|
| `test_ec_parity.py::test_ec_planted_parity[df-si80-25yr]` | EC Phase-1: only DG is variant-specific; HG/mort/bark/crown/small-tree fall back to PN/SN+LP defaults until ec/htgf.f, morts.f, bratio.f, crown.f, smhtgf.f port. |
| `test_ec_parity.py::test_ec_planted_parity[pp-si70-25yr]` | (same EC Phase-1 reason) |
| `test_ec_parity.py::test_ec_planted_parity[lp-si70-25yr]` | (same EC Phase-1 reason) |
| `test_ls_parity.py::test_ls_gold_standard_rn_si60_30yr` | BA passes (+0.39%) but top_height −8% (38.58 vs 41.97 @30yr); needs OLDRN HG autocorrelation port (ls/htgf.f:108). |
| `test_ne_parity.py::test_ne_expanded_species_parity[yb-si60-30yr]` | Baseline 2026-04-16: pre-fix NE over-prediction. |
| `test_oc_parity.py::test_oc_planted_parity_df[df-si80-25yr]` | OC DF: BA (9.8%) & vol (11.3%) exceed tol; QMD gap likely Weibull CR vs ORGANON CR2. |
| `test_oc_parity.py::test_oc_planted_parity_df[df-si100-50yr]` | OC DF: per-cycle error compounds over 10 cycles. |
| `test_pn_parity.py::test_pn_gold_standard_df_si100_30yr` | Baseline 2026-04-17: PN scaffold; DF smoke BA +9%, vol +12% (warn-band). |
| `test_pn_parity.py::test_pn_expanded_species_parity[ra-si80-30yr]` | Baseline 2026-04-17: pre-fix PN expected drift. |
| `test_sn_parity.py::test_sn_expanded_species_parity[wp-si70-25yr]` | 10-seed mean BA −7.03%; DET-mode under-prediction (−9.92%); root cause needs native traces. |
| `test_sn_parity.py::test_sn_expanded_species_parity[rm-si65-25yr]` | 10-seed mean BA +5.58%; pure Jensen-lift mismatch (+5.98pp excess). |
| `test_sn_parity.py::test_sn_expanded_species_parity[by-si70-25yr]` | 10-seed mean BA +8.74%; mixed DET (+4.49%) + Jensen (+4.20pp) bias. |
| `test_wc_parity.py::test_wc_expanded_species_parity[ra-si80-30yr]` | Baseline 2026-04-17: pre-fix WC expected drift. |

## Coverage gaps / blockers

- **CA, WS, OP have no parity test file** (`tests/parity/` contains only
  `test_{cs,ec,ls,ne,oc,pn,sn,wc}_parity.py`). Their native libraries are built
  and present in `~/.fvs/lib`, but no parity tests are collected for them, so
  they contribute 0 to this baseline. Recorded as `—` above. Adding parity
  coverage for CA/WS/OP is an open M0 item; it is **out of scope for this
  measurement-only baseline** (writing new scenario tests is deferred so as not
  to manufacture pass/fail data). `CA`, `WS`, `OP` are already listed in
  `conftest.PARITY_VARIANTS`, so only test files are missing.
- **EC is not in `conftest.PARITY_VARIANTS`** (which lists SN, LS, PN, WC, NE,
  CS, OP, CA, OC, WS) yet `test_ec_parity.py` runs and gates independently.
  Harmless for this baseline (EC tests ran and are tallied) but worth noting for
  the eventual coverage cleanup.

## Reconciliation vs. prior baseline

Result (`34 pass / 13 xfail / 6 xpass / 1 fail`) **matches** the journal's
2026-06-21 native-rebuild baseline exactly. Per that note, ~7 of 54 April
annotations no longer match the reproducible build (the 6 xpasses + the OC
failure); `scripts/build_native_fvs.sh` is the canonical native source of truth.

---

*Measurement-only baseline. No growth/mortality/volume model code modified to
produce these numbers.*

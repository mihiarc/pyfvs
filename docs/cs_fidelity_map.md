# CS Fortran → pyfvs Fidelity Map

**Source**: `/Users/cmihiar/Projects/ForestVegetationSimulator/cs/`

Map of every CS-variant (Central States) Fortran file to its pyfvs counterpart, classified by fidelity status. Built 2026-06-21 from the 19 `.f` files in the `cs/` source directory (5,596 LOC). Companion to `docs/sn_fidelity_map.md` and `docs/ls_fidelity_map.md`; follows the LS per-variant-directory scope.

## Status legend

- **PORTED** — pyfvs has a full semantic equivalent; the named pyfvs module ports it
- **PARTIAL** — some pieces ported; specific gaps documented
- **MISSING** — no pyfvs equivalent
- **UNKNOWN** — needs investigation (target: zero)
- **N/A** — intentionally not ported (Fortran marshaling, keyword infra, DATA blocks, NVEL-substituted volume, etc.)

## Scope

This map classifies the Fortran files in the variant's own `cs/` directory, matching the LS companion map. CORE functionality that CS draws from **shared base code** (not present as a `cs/*.f` file) is out of per-variant scope and is classified in `docs/sn_fidelity_map.md`: the Chapman-Richards site curve (`htcalc.f`), the NVEL volume/taper library, crown-width (`cwcalc.f`) and CCF (`ccfcal.f`), and the stochastic-DG autocorrelation (`autcor.f`/`dgscor.f`). Unlike LS, the CS directory has **no** `bratio.f`, `estab.f`, `htcalc.f`, `cfvol.f`/`bfvol.f`, `cwcalc.f`/`ccfcal.f`, `habtyp.f`, or `pvref9.f` — those functions are either shared base code or fold into `blkdat.f` DATA / `regent.f`. `cs/common/*.F77` are COMMON-block parameter includes (not CORE algorithm files): **N/A**.

## Fidelity Summary by Category

| Category | Files | LOC | PORTED | PARTIAL | MISSING | UNKNOWN | N/A |
|---|---|---|---|---|---|---|---|
| CORE_DG | 2 | 1339 | 1 | 1 | 0 | 0 | 0 |
| CORE_HT | 3 | 704 | 1 | 2 | 0 | 0 | 0 |
| CORE_MORT | 1 | 215 | 0 | 1 | 0 | 0 | 0 |
| CORE_CROWN | 2 | 921 | 1 | 0 | 0 | 0 | 1 |
| CORE_COMP | 1 | 108 | 1 | 0 | 0 | 0 | 0 |
| CORE_REGEN | 1 | 630 | 0 | 1 | 0 | 0 | 0 |
| CORE_ESTAB | 1 | 98 | 1 | 0 | 0 | 0 | 0 |
| CORE_SITE | 1 | 302 | 0 | 1 | 0 | 0 | 0 |
| CORE_INIT | 4 | 948 | 0 | 0 | 0 | 0 | 4 |
| CORE_CUTS | 1 | 145 | 0 | 0 | 0 | 0 | 1 |
| VOLUME | 2 | 186 | 0 | 1 | 0 | 0 | 1 |
| **TOTAL** | **19** | **5596** | **5** | **7** | **0** | **0** | **7** |

**19 CORE files · 0 UNKNOWN / unclassified.** 12 of 19 (63%) PORTED or PARTIAL; 7 N/A (intentional); 0 MISSING. (Zero-MISSING is an M1 target, not the bar for this map.)

## CORE_DG (2 files, 1339 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `dgf.f` | 602 | `cs_diameter_growth.py::CSDiameterGrowthModel` | **PORTED** | CS ln(DDS) equation (same form as LS: linear DBH + RELDBH + CR + BA + BAL + SI), MTU-2012 coefficients in `cfg/cs/`. `CSDiameterGrowthModel` subclasses `LSDiameterGrowthModel`, overriding coefficient file + default species (WO). Coefficients match Fortran per CS Phase-1 audit; residual CS sweep gaps are upstream (establishment/HG), not the DG equation. |
| `dgdriv.f` | 737 | `cs_diameter_growth.py` + `tree.py::_grow_large_tree_standard` | **PARTIAL** | DG driver. Runtime DG call dispatched via `_grow_large_tree_standard`; the FVS calibration loop (LSTART / RESLOG self-calibration against input growth data) is NOT ported — pyfvs has no growth-sample fixture. Same gap as SN/LS. |

## CORE_HT (3 files, 704 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `htgf.f` | 177 | `large_tree_height_growth.py::calculate_height_growth` (LS/CS/NE branch) + `cs_balmod.py` | **PARTIAL** | GMOD = (1-(1-BALMOD)*(1-RELHTA))*0.8 modifier applied via the shared LS/CS/NE branch; BALMOD from `cs_balmod.py`. **Gap**: the OLDRN stochastic-autocorrelation lift carried into HG in Fortran (`HTG*(1+OLDRN)*GMOD`) is not reproduced — same documented gap as LS htgf. Potential height growth itself comes from the shared Chapman-Richards site curve. |
| `htdbh.f` | 445 | `height_diameter.py` (Wykoff/IWYKCA dispatch) + `cfg/cs` H-D coefficients | **PARTIAL** | Wykoff height-DBH; CS `IWYKCA`/`HT1`/`HT2` arrays transcribed from `cs/htdbh.f`+`blkdat.f` into the CS H-D config (closed AE −68%→−4%). H-D *relationship* ported; line-by-line dubbing of arbitrary input-tree heights and any special cases not fully reproduced. |
| `findag.f` | 82 | `tree.py::_effective_age_from_height` | **PORTED** | Inverse Chapman-Richards — effective stand age from current height. Shared pattern with SN/LS. |

## CORE_MORT (1 file, 215 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `varmrt.f` | 215 | `mortality.py::CSMortalityModel` | **PARTIAL** | 4-group background + SDI density model (TWIGS family); `CSMortalityModel` subclasses `LSMortalityModel` with CS coefficients (`cfg/cs/cs_mortality_coefficients.json`), species-group mappings, shade tolerances, SDI maximums. CS-specific PEFF/VARADJ coefficients and the stochastic survivor-selection path not independently verified against the Fortran DATA blocks. |

## CORE_CROWN (2 files, 921 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `crown.f` | 294 | `crown_ratio.py::CSCrownRatioModel` | **PORTED** | TWIGS crown-ratio equation `ACR = 10*(BCR1/(1+BCR2*BA) + BCR3*(1-exp(BCR4*D)))`; `CSCrownRatioModel` subclasses `LSCrownRatioModel` with CS BCR1..BCR4 coefficients. |
| `cratet.f` | 627 | N/A | **N/A** | Pre-cycle orchestrator (calls RCON, CROWN, REGENT). pyfvs doesn't use this control path; the growth loop is driven directly in `Stand`/`Tree`. |

## CORE_COMP (1 file, 108 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `balmod.f` | 108 | `cs_balmod.py::cs_balmod` | **PORTED** | BALMOD competition modifier (CHECK, B1..B4, C1, C2, BAMAX1 per-species arrays). Used by the CS HG path. |

## CORE_REGEN (1 file, 630 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `regent.f` | 630 | `stand.py::_grow_establishment_cycle_cs_lestb` + `establishment.py::compute_cs_essubh_initial_height` + `tree.py` (3–5" XWT blend) | **PARTIAL** | LESTB bare-ground establishment path (FNT−5 growth shortening) ported — closed WO yr30 BA +46%→−3.8%. Small-tree → large-tree XWT blend zone (3–5") applied. Full Fortran TWIGS small-tree DG/HG increment model is approximated by the shared small-tree growth, not ported line-by-line. |

## CORE_ESTAB (1 file, 98 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `essubh.f` | 98 | `establishment.py::compute_cs_essubh_initial_height` | **PORTED** | Establishment sub-record height `HHT = (HTCALC(CARAGE)/CARAGE)*5.0` with the species-specific Carmean reference age (MAPCS). Ports the CS-specific behavior of NOT pre-clamping H(CARAGE) at HHTMAX before interpolation (closed YP FAIL→PASS). |

## CORE_SITE (1 file, 302 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `sitset.f` | 302 | `Stand` constructor (`site_index`) | **PARTIAL** | Loads the SITELG per-species site-index array from keyword/default. pyfvs carries a single SI per stand; the per-species site-index transformation matrices are not ported. |

## CORE_INIT (4 files, 948 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `blkdat.f` | 377 | (expanded into `cfg/cs/*.json`) | **N/A** | COMMON-block DATA initialization. Preprocessed into build-dir DATA and transcribed into pyfvs CS JSON configs per model (DG, crown, mortality, bark, H-D). |
| `grinit.f` | 335 | N/A | **N/A** | Variant initialization boilerplate; `Stand`/`Tree` constructors do equivalent setup. |
| `forkod.f` | 198 | N/A | **N/A** | Forest-type code keyword translation. |
| `grohed.f` | 38 | N/A | **N/A** | Output header formatting. |

## CORE_CUTS (1 file, 145 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `cutstk.f` | 145 | N/A | **N/A** | Thinning stocking-level keyword infrastructure. pyfvs has `harvest.py` but does not mimic the keyword path. |

## VOLUME (2 files, 186 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `nbolt.f` | 127 | `taper.py` + `merchandising.py` | **PARTIAL** | 8-foot bolt counting to sawtimber/pulpwood top diameters. pyfvs has Clark taper + merchandising; CS-specific nbolt parameters not verified. |
| `cubrds.f` | 59 | N/A | **N/A** | `BLOCK DATA` default coefficients for FVS's native cubic/board-foot equations. pyfvs computes volume via the NVEL library (`volume_library.py`), so these defaults are intentionally not transcribed. |

## Remaining work priority order (M1)

1. **CORE_HT** — carry OLDRN-type autocorrelation lift into `htgf.f` HG; close any residual CS top-height drift.
2. **CORE_MORT** — verify `varmrt.f` CS background/density coefficients against the Fortran DATA blocks.
3. **CORE_REGEN** — `regent.f` full TWIGS small-tree increment model beyond the LESTB establishment + blend.
4. **CORE_SITE** — per-species `sitset.f` transformation if multi-species CS parity is pursued.
5. **VOLUME** — verify `nbolt.f` CS merchandising parameters.

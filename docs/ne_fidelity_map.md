# NE Fortran → pyfvs Fidelity Map

**Source**: `/Users/cmihiar/Projects/ForestVegetationSimulator/ne/`

Map of every NE-variant (Northeast) Fortran file to its pyfvs counterpart, classified by fidelity status. Built 2026-06-21 from the 21 `.f` files in the `ne/` source directory (5,722 LOC). Companion to `docs/sn_fidelity_map.md` and `docs/ls_fidelity_map.md`; follows the LS per-variant-directory scope.

## Status legend

- **PORTED** — pyfvs has a full semantic equivalent; the named pyfvs module ports it
- **PARTIAL** — some pieces ported; specific gaps documented
- **MISSING** — no pyfvs equivalent
- **UNKNOWN** — needs investigation (target: zero)
- **N/A** — intentionally not ported (Fortran marshaling, keyword infra, DATA blocks, NVEL-substituted volume, etc.)

## Scope

This map classifies the Fortran files in the variant's own `ne/` directory, matching the LS companion map. CORE functionality that NE draws from **shared base code** (not present as a `ne/*.f` file) is out of per-variant scope and is classified in `docs/sn_fidelity_map.md`: the Chapman-Richards site curve (`htcalc.f`), the NVEL volume/taper library, crown-width (`cwcalc.f`) and CCF (`ccfcal.f`). NE has no `bratio.f`, `estab.f`, `htcalc.f`, `cfvol.f`/`bfvol.f`, `cwcalc.f`/`ccfcal.f`, `habtyp.f`, or `pvref9.f` in its directory; bark-ratio coefficients fold into `blkdat.f` DATA (`bark_ratio.py::NEBarkRatioModel` reads `cfg/ne/ne_bark_ratio_coefficients.json`). NE adds two files absent from CS/LS: `badist.f` (BA-by-DBH-class distribution) and `logs.f` (R5 board-foot volume). `ne/common/*.F77` are COMMON-block parameter includes (not CORE algorithm files): **N/A**.

## Fidelity Summary by Category

| Category | Files | LOC | PORTED | PARTIAL | MISSING | UNKNOWN | N/A |
|---|---|---|---|---|---|---|---|
| CORE_DG | 2 | 936 | 1 | 1 | 0 | 0 | 0 |
| CORE_HT | 3 | 733 | 1 | 2 | 0 | 0 | 0 |
| CORE_MORT | 1 | 216 | 0 | 1 | 0 | 0 | 0 |
| CORE_CROWN | 2 | 908 | 1 | 0 | 0 | 0 | 1 |
| CORE_COMP | 2 | 108 | 2 | 0 | 0 | 0 | 0 |
| CORE_REGEN | 1 | 629 | 0 | 1 | 0 | 0 | 0 |
| CORE_ESTAB | 1 | 99 | 0 | 1 | 0 | 0 | 0 |
| CORE_SITE | 1 | 646 | 0 | 1 | 0 | 0 | 0 |
| CORE_INIT | 4 | 948 | 0 | 0 | 0 | 0 | 4 |
| CORE_CUTS | 1 | 167 | 0 | 0 | 0 | 0 | 1 |
| VOLUME | 3 | 332 | 0 | 1 | 1 | 0 | 1 |
| **TOTAL** | **21** | **5722** | **5** | **8** | **1** | **0** | **7** |

**21 CORE files · 0 UNKNOWN / unclassified.** 13 of 21 (62%) PORTED or PARTIAL; 7 N/A (intentional); 1 MISSING (board-foot volume). (Zero-MISSING is an M1 target, not the bar for this map.)

## CORE_DG (2 files, 936 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `dgf.f` | 199 | `ne_diameter_growth.py::NEDiameterGrowthModel` | **PORTED** | NE-TWIGS v3.01 basal-area-increment model: `POTBAG = B1*SI*(1-exp(-B2*DBH))`, `growth = POTBAG*0.7*BAGMOD`, BA→diameter conversion, 10 annual iterations. Per-species B1/B2 from `cfg/ne/`; competition via BAL-based BAGMOD. Distinct model form from the SN/LS ln(DDS) family. |
| `dgdriv.f` | 737 | `ne_diameter_growth.py` + `tree.py` | **PARTIAL** | DG driver. Runtime DG call dispatched per-tree; the FVS calibration loop (LSTART / RESLOG) is NOT ported (no growth-sample fixture). Same gap as SN/LS/CS. |

## CORE_HT (3 files, 733 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `htgf.f` | 177 | `large_tree_height_growth.py::calculate_height_growth` (NE branch) + `stand_metrics.py::calculate_ne_bal_all` | **PARTIAL** | Ported `ne/htgf.f:102-108`: NE BALMOD (shifted EBAU BAL) + RELHTA blend + ×0.8 damping as the HG modifier (flipped 7 NE species WARN→PASS). **Gap**: potential height growth itself comes from the shared Chapman-Richards site curve; any OLDRN-type stochastic lift not carried. |
| `htdbh.f` | 484 | `height_diameter.py` (Wykoff/IWYKCA dispatch) + `cfg/ne` H-D coefficients | **PARTIAL** | Wykoff height-DBH; NE `IWYKCA`/`HT1`/`HT2` arrays transcribed from `ne/htdbh.f`+`sitset.f`. H-D *relationship* ported; line-by-line dubbing of arbitrary input-tree heights not fully reproduced. |
| `findag.f` | 72 | `tree.py::_effective_age_from_height` | **PORTED** | Inverse Chapman-Richards — effective stand age from current height. Shared pattern with SN/LS/CS. |

## CORE_MORT (1 file, 216 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `varmrt.f` | 216 | `mortality.py::NEMortalityModel` | **PARTIAL** | 4-group background + SDI density model (TWIGS family); `NEMortalityModel` subclasses `LSMortalityModel` with NE coefficients (`cfg/ne/ne_mortality_coefficients.json`), species-group mappings, shade tolerances, SDI maximums. NE-specific coefficients and the stochastic survivor-selection path not independently verified against the Fortran DATA blocks. |

## CORE_CROWN (2 files, 908 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `crown.f` | 286 | `crown_ratio.py::NECrownRatioModel` | **PORTED** | TWIGS crown-ratio equation `ACR = 10*(BCR1/(1+BCR2*BA) + BCR3*(1-exp(BCR4*D)))`; `NECrownRatioModel` subclasses `LSCrownRatioModel` with NE BCR1..BCR4 coefficients. |
| `cratet.f` | 622 | N/A | **N/A** | Pre-cycle orchestrator (calls RCON, CROWN, REGENT). pyfvs drives the growth loop directly in `Stand`/`Tree`. |

## CORE_COMP (2 files, 108 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `balmod.f` | 52 | `stand_metrics.py::calculate_ne_bal_all` + `ne_diameter_growth.py` (B3) | **PORTED** | NE BALMOD competition: per-tree BAL = `EBAU(ICLS-2)` (shifted basal-area-in-larger), B3 species coefficients in `ne_diameter_growth.py`. Closed the NE BALMOD shifted-BAL gap (pyfvs previously used standard PBAL = half the Fortran value). |
| `badist.f` | 56 | `stand_metrics.py::calculate_ne_bal_all` | **PORTED** | Computes BA by DBH class (`EBAU` cumulative array, `ICLS = IFIX(DBH+1.0)`, DBH clamped to 1.0). Ported inline into `calculate_ne_bal_all` (cites `ne/balmod.f` + `badist.f:53-55`). |

## CORE_REGEN (1 file, 629 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `regent.f` | 629 | `establishment.py` (LESTB) + `tree.py` (linear XWT blend) | **PARTIAL** | LESTB bare-ground establishment dispatch extended to NE; the linear XWT small-tree→large-tree blend (`ne/regent.f:373`) ported NE-only in `tree.py` plus the 3–5" blend zone. Full Fortran TWIGS small-tree increment model is approximated by the shared small-tree growth, not ported line-by-line. |

## CORE_ESTAB (1 file, 99 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `essubh.f` | 99 | `establishment.py::get_essubh_height` | **PARTIAL** | Establishment sub-record height lookup. pyfvs has an `essubh` height function used by the NE LESTB establishment path; NE-specific HHT values approximate the Fortran defaults but are not all independently verified (CS got a dedicated `compute_cs_essubh_initial_height`; NE still uses the shared lookup). |

## CORE_SITE (1 file, 646 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `sitset.f` | 646 | `Stand` constructor (`site_index`) | **PARTIAL** | Loads the SITEAR per-species site-index array (Hilt NE site-index conversion equations). pyfvs carries a single SI per stand; the per-species conversion equations are not ported. (NE IWYKCA H-D constants partially sourced from here — see `htdbh.f`.) |

## CORE_INIT (4 files, 948 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `grinit.f` | 344 | N/A | **N/A** | Variant initialization boilerplate; `Stand`/`Tree` constructors do equivalent setup. |
| `blkdat.f` | 351 | (expanded into `cfg/ne/*.json`) | **N/A** | COMMON-block DATA initialization. Transcribed into pyfvs NE JSON configs per model (DG, crown, mortality, bark, H-D). |
| `forkod.f` | 216 | N/A | **N/A** | Forest-type code keyword translation. |
| `grohed.f` | 37 | N/A | **N/A** | Output header formatting. |

## CORE_CUTS (1 file, 167 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `cutstk.f` | 167 | N/A | **N/A** | Thinning stocking-level keyword infrastructure. pyfvs has `harvest.py` but does not mimic the keyword path. |

## VOLUME (3 files, 332 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `nbolt.f` | 146 | `taper.py` + `merchandising.py` | **PARTIAL** | 8-foot bolt counting to sawtimber/pulpwood top diameters. pyfvs has Clark taper + merchandising; NE-specific nbolt parameters not verified. |
| `cubrds.f` | 58 | N/A | **N/A** | `BLOCK DATA` default coefficients for FVS's native cubic/board-foot equations. pyfvs computes volume via the NVEL library (`volume_library.py`), so these defaults are intentionally not transcribed. |
| `logs.f` | 128 | N/A | **MISSING** | Region-5 board-foot volume with Biging taper equations. pyfvs derives board-foot volume from the NVEL library rather than this model, but the R5 Biging board-foot algorithm itself is not ported. Not exercised by the cubic-volume parity metric. |

## Remaining work priority order (M1)

1. **CORE_HT** — confirm `htgf.f` potential-HG path and any stochastic lift; close residual NE top-height drift.
2. **CORE_MORT** — verify `varmrt.f` NE background/density coefficients against the Fortran DATA blocks.
3. **CORE_ESTAB** — give NE a dedicated `essubh` port (as CS has) instead of the shared lookup.
4. **CORE_REGEN** — `regent.f` full TWIGS small-tree increment model beyond LESTB + XWT blend.
5. **VOLUME** — `logs.f` board-foot (MISSING) and `nbolt.f` NE merchandising parameters, if board-foot parity is pursued.

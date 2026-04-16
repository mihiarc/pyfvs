# LS Fortran → pyfvs Fidelity Map

**Source**: `/Users/cmihiar/Projects/ForestVegetationSimulator/ls/` + `bin/FVSls_buildDir/`

Map of every LS-variant Fortran file to its pyfvs counterpart, classified by fidelity status. Built 2026-04-16 from 29 Fortran files (~10,371 LOC). Companion to `docs/sn_fidelity_map.md`.

## Status legend

- **PORTED** — pyfvs has full semantic equivalent verified
- **PARTIAL** — some pieces ported; specific gaps documented
- **MISSING** — no pyfvs equivalent
- **N/A** — intentionally not ported (Fortran-specific marshaling, keyword infra, etc.)


## Fidelity Summary by Category

| Category | Files | LOC | PORTED | PARTIAL | MISSING | N/A |
|---|---|---|---|---|---|---|
| CORE_DG | 2 | 1265 | 0 | 1 | 1 | 0 |
| CORE_HT | 4 | 1037 | 1 | 2 | 1 | 0 |
| CORE_MORT | 1 | 212 | 0 | 1 | 0 | 0 |
| CORE_BARK | 1 | 36 | 1 | 0 | 0 | 0 |
| CORE_CROWN | 4 | 3444 | 1 | 1 | 1 | 1 |
| CORE_STAND | 2 | 479 | 0 | 0 | 0 | 2 |
| CORE_REGEN | 2 | 1449 | 0 | 0 | 2 | 0 |
| CORE_INIT | 5 | 983 | 0 | 0 | 0 | 5 |
| CORE_SITE | 1 | 470 | 0 | 1 | 0 | 0 |
| VOLUME | 5 | 778 | 0 | 1 | 4 | 0 |
| UTILITY | 2 | 214 | 1 | 0 | 0 | 1 |
| **TOTAL** | **29** | **10371** | **4** | **7** | **9** | **9** |

Currently 38% PORTED or PARTIAL, 31% MISSING, 31% N/A. Highest-value open items by order of BA-parity impact:
1. CORE_DG (dgf.f, dgdriv.f) — LS BA drift +15% to +190% across 54 species
2. CORE_REGEN (estab.f, regent.f) — bare-ground regeneration paths
3. VOLUME (cfvol.f, bfvol.f) — LS volume over-predicts ~25% vs native


## CORE_DG (2 files, 1265 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `dgf.f` | 508 | `ls_diameter_growth.py::LSDiameterGrowthModel` | **PARTIAL** | LS ln(DDS) equation with linear DBH + RELDBH (relative DBH). 67 species covered in `cfg/ls/ls_diameter_growth_coefficients.json`. Coefficient values not yet cross-verified against Fortran buildDir DGCOEF/DGSPEC arrays — sweep shows systematic over-prediction (+15% to +190% BA across 54/67 species, 2026-04-16) strongly suggesting coefficient mismatches or missing terms. |
| `dgdriv.f` | 757 | `ls_diameter_growth.py + tree.py::_grow_large_tree_standard` | **MISSING** | Calibration driver (LSTART / RESLOG). Pyfvs has no calibration loop (no growth-data fixture). Runtime DG equation call is through `_grow_large_tree_standard`; calibration itself not ported. |


## CORE_HT (4 files, 1037 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `htgf.f` | 179 | `large_tree_height_growth.py::calculate_height_growth` (LS branch) | **PARTIAL** | GMOD = (1 - (1-BALMOD)*(1-RELHTA)) * 0.8 ported 2026-04-16 (LS branch). BALMOD via `ls_balmod.py::ls_balmod`. **Gap**: OLDRN stochastic autocorrelation from dgf.f is NOT carried into HG — Fortran's `HTG(I) * (1+OLDRN(I)) * GMOD` is approximated as `POTHTG * GMOD`, so dominant trees (RELHTA=1.0) are capped at 0.8× without the ~25% stochastic lift. Causes RN top-height -8% systematic under-prediction. |
| `htdbh.f` | 352 | N/A | **MISSING** | Wykoff height-DBH dubbing for initial heights. pyfvs uses Curtis-Arney (H-D) directly via `height_diameter.py` — functionally equivalent but not a line-by-line port. Fort Bragg specials (IFOR=20) not implemented (same gap as SN). |
| `htcalc.f` | 425 | `large_tree_height_growth.py::calculate_potential_height_growth` + `tree.py::_grow_small_tree` | **PARTIAL** | Chapman-Richards site curve + FINDAG inversion. LS/CS/NE branch (base_age=50, scale_factor) ported. Gap: MODE=9 is called twice in Fortran (once for AGET, once for HTG) — pyfvs uses a single backward-difference instead of two invocations. |
| `findag.f` | 81 | `tree.py::_effective_age_from_height` (inline) | **PORTED** | Inverse Chapman-Richards for effective age from current height. Shared pattern with SN. |


## CORE_MORT (1 file, 212 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `varmrt.f` | 212 | `mortality.py::LSMortalityModel` + shared `_apply_density_mortality` | **PARTIAL** | 67-species LS-specific background mortality coefficients in `cfg/ls/ls_mortality_coefficients.json`. Density mortality distribution shares pattern with SN. LS-specific PEFF and VARADJ shade-tolerance coefficients need verification against Fortran build-dir DATA blocks. |


## CORE_BARK (1 file, 36 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `bratio.f` | 36 | `bark_ratio.py::LSBarkRatioModel` | **PORTED** | Linear DIB = a + b*DBH. 67 LS species covered in `cfg/ls/ls_bark_ratio_coefficients.json`. |


## CORE_CROWN (4 files, 3444 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `crown.f` | 289 | `crown_ratio.py::LSCrownRatioModel` | **PORTED** | TWIGS equation `ACR = 10 * (BCR1/(1+BCR2*BA) + BCR3*(1-exp(BCR4*D)))`. All 67 species BCR1..BCR4 replaced with Fortran source values 2026-04-16 (previously held TWIGS-Belcher-1982 values that diverged). |
| `cratet.f` | 628 | N/A | **N/A** | Pre-cycle orchestrator (calls RCON, CROWN, REGENT). pyfvs doesn't use this code path; growth loops directly in Stand. |
| `ccfcal.f` | 65 | `crown_competition_factor.py::CrownCompetitionFactor` | **PARTIAL** | Crown width + CCF for individual trees. LS-specific CCF coefficients not verified against Fortran. |
| `cwcalc.f` | 2462 | `crown_width.py::CrownWidthModel` | **MISSING** | Multi-equation crown-width library (Bechtold, Bragg, Ek, Krajicek, Smith) with Hopkins Index geographic adjustment. pyfvs has the class but LS species dispatch and coefficient set not verified. Largest single file in LS variant; output-only, no feedback into growth loops. |


## CORE_STAND (2 files, 479 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `grinit.f` | 335 | N/A | **N/A** | Variant initialization boilerplate. Stand/Tree constructors do equivalent work. |
| `cutstk.f` | 144 | N/A | **N/A** | Thinning stocking-level keyword infrastructure. pyfvs has `harvest.py` but doesn't mimic the keyword path. |


## CORE_REGEN (2 files, 1449 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `estab.f` | 820 | N/A | **MISSING** | Establishment / regeneration model for LS. pyfvs uses a simplified bare-ground seedling-planting path (`Stand(bare_ground=True)`) rather than Fortran's keyword-driven establishment. Needed for Fortran-faithful bare-ground parity of rare species. |
| `regent.f` | 629 | N/A | **MISSING** | Small-tree growth (DBH < 5"). pyfvs uses generic small-tree Chapman-Richards from `large_tree_height_growth.py::calculate_potential_height_growth` rather than LS-specific small-tree DG/HG. Likely a factor in JP/RP early-cycle DBH drift. |


## CORE_INIT (5 files, 983 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `blkdat.f` | 310 | (expanded to each `cfg/ls/*.json`) | **N/A** | COMMON block DATA initialization. Preprocessed into build-dir DATA statements and transcribed into pyfvs JSON configs per model (bark, crown, mortality, etc.). |
| `grohed.f` | 37 | N/A | **N/A** | Output header formatting. |
| `forkod.f` | 332 | N/A | **N/A** | Forest-type code keyword translation. |
| `habtyp.f` | 139 | N/A | **N/A** | Habitat-type code keyword translation. |
| `pvref9.f` | 169 | N/A | **N/A** | PV/reference code mapping for eco-class keywords. |


## CORE_SITE (1 file, 470 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `sitset.f` | 470 | `site_index_transformation.yaml` + Stand constructor | **PARTIAL** | Site-index assignment (SICOEF1/SICOEF2 translation matrices). pyfvs uses a single SI value per stand rather than per-species; Fortran per-species transformation not ported. LS `sitset.f:259` default SI=60 matches pyfvs sweep default. |


## VOLUME (5 files, 778 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `cfvol.f` | 244 | `volume_library.py` (combined-variable) | **MISSING** | Cubic-foot volume with transition-size + allometric equations. pyfvs uses simplified combined-variable volume — produces ~+25% over-prediction for LS (RN gold-standard volume test skipped because of this). |
| `bfvol.f` | 132 | N/A | **MISSING** | Board-foot volume with sawing algorithm. |
| `gvrvol.f` | 210 | N/A | **MISSING** | Gevorkiantz legacy volume. Retained in Fortran for compatibility; not required for pyfvs. |
| `cubrds.f` | 58 | N/A | **MISSING** | Cubic/board-foot coefficient defaults. |
| `nbolt.f` | 134 | `taper.py + merchandising.py` | **PARTIAL** | Bolt/stacking geometry for sawtimber/pulpwood. pyfvs has Clark taper + merchandising; LS-specific nbolt parameters not verified. |


## UTILITY (2 files, 214 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `balmod.f` | 120 | `ls_balmod.py::ls_balmod` | **PORTED** | BALMOD competition modifier. Ported 2026-04-16 with full 8-array coefficient transcription (CHECK, B1..B4, C1, C2, BAMAX1) for all 67 species + position-44 blank guard. Called from HG (htgf.f); DG and RGNTHW call sites not yet wired up (DG uses its own effective formulation). |
| `essubh.f` | 94 | `establishment.py::get_essubh_height` | **N/A** | Establishment sub-record height. pyfvs has an `essubh` lookup for establishment; LS specific values not fully verified but approximately match Fortran defaults. |


## Remaining work priority order

1. **CORE_DG** (dgf.f coefficient cross-check) — biggest BA impact, 54 species over-predict.
2. **OLDRN HG autocorrelation** — close RN top-height gap; documented in `htgf.f` notes above.
3. **CORE_REGEN** (estab.f + regent.f) — small-tree dynamics and bare-ground regeneration.
4. **VOLUME** (cfvol.f + bfvol.f) — close the +25% volume drift; currently skipped in parity tests.
5. **CORE_CROWN** (cwcalc.f) — output-only; low growth-parity impact but important for downstream consumers.

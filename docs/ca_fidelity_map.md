# CA Fortran → pyfvs Fidelity Map

**Source**: `/Users/cmihiar/Projects/ForestVegetationSimulator/ca/`

Map of every CA-variant (Inland California) Fortran file to its pyfvs counterpart,
classified by fidelity status. Built 2026-06-21 from the 31 `.f` files in the
`ca/` source directory (11,984 LOC). Companion to `docs/sn_fidelity_map.md` /
`docs/cs_fidelity_map.md`; per-variant-directory scope.

## Status legend

- **PORTED** — pyfvs has a full semantic equivalent; the named pyfvs module ports it
- **PARTIAL** — some pieces ported; specific gaps documented
- **MISSING** — no pyfvs equivalent
- **UNKNOWN** — needs investigation (target: zero)
- **N/A** — intentionally not ported (keyword infra, DATA blocks, NVEL-substituted volume, etc.)

## Scope

Classifies the files in the `ca/` directory. CA is a topographic variant with a
variant-specific diameter-growth model + CA bark/crown/H-D JSON coefficients;
**mortality uses the generic `MortalityModel`** (registry `mortality_class=MortalityModel`),
and large-tree height growth / topographic dispatch is not yet CA-faithful (parity
shows top-height +34–44%). `ca/common/*.F77` are COMMON-block parameter includes
(not CORE algorithm): N/A. Volume maps to the shared NVEL library (`volume_library.py`).

## Fidelity Summary by Category

| Category | Files | LOC | PORTED | PARTIAL | MISSING | UNKNOWN | N/A |
|---|---|---|---|---|---|---|---|
| CORE_DG | 2 | 1219 | 1 | 1 | 0 | 0 | 0 |
| CORE_HT | 5 | 1011 | 2 | 3 | 0 | 0 | 0 |
| CORE_CROWN | 4 | 1361 | 1 | 2 | 0 | 0 | 1 |
| CORE_BARK | 1 | 118 | 1 | 0 | 0 | 0 | 0 |
| CORE_REGEN | 3 | 948 | 0 | 1 | 2 | 0 | 0 |
| CORE_ESTAB | 1 | 90 | 0 | 1 | 0 | 0 | 0 |
| CORE_MORT | 2 | 1277 | 0 | 2 | 0 | 0 | 0 |
| CORE_SITE | 4 | 1082 | 0 | 2 | 0 | 0 | 2 |
| VOLUME | 2 | 212 | 0 | 0 | 0 | 0 | 2 |
| CORE_INIT | 7 | 4666 | 0 | 0 | 0 | 0 | 7 |
| **TOTAL** | **31** | **11984** | **5** | **12** | **2** | **0** | **12** |

**31 CORE files · 0 UNKNOWN / unclassified.** 17 of 31 PORTED or PARTIAL; 12 N/A;
2 MISSING (sprout regen ×2).

## CORE_DG (2 files, 1219 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `dgf.f` | 477 | `ca_diameter_growth.py::CADiameterGrowthModel` | **PORTED** | CA ln(DDS) equation with topographic effects; per-species coefficients in `cfg/ca/`. |
| `dgdriv.f` | 742 | `ca_diameter_growth.py` + `tree.py` | **PARTIAL** | DG driver; runtime dispatch ported, FVS calibration loop (LSTART/RESLOG) not ported. |

## CORE_HT (5 files, 1011 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `findag.f` | 130 | `tree.py::_effective_age_from_height` | **PORTED** | Inverse Chapman-Richards effective age. |
| `smhtgf.f` | 206 | `ca_small_tree_growth.py` | **PORTED** | CA small-tree height growth (5-equation port, 2026-04-21; closed yr10 drift). |
| `htgf.f` | 310 | `large_tree_height_growth.py` (CA branch) | **PARTIAL** | Large-tree HG + topographic dispatch. **Gap**: parity shows top-height +34–44%; CA HG not yet faithful. |
| `htcalc.f` | 186 | `large_tree_height_growth.py` / `tree.py` (Chapman-Richards site curve) | **PARTIAL** | Site-curve height; CA-specific height trajectory diverges (see `htgf.f`). |
| `htdbh.f` | 179 | `height_diameter.py` + `cfg/ca` H-D | **PARTIAL** | Wykoff/Curtis-Arney H-D; relationship ported, dubbing not line-by-line. |

## CORE_CROWN (4 files, 1361 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `crown.f` | 525 | `crown_ratio.py::CACrownRatioModel` | **PORTED** | CA Weibull crown-ratio, 17 species groups from `ca/crown.f`. |
| `ccfcal.f` | 95 | `crown_competition_factor.py` | **PARTIAL** | Crown width + CCF; CA coefficients not independently verified. |
| `dubscr.f` | 127 | `crown_ratio.py` (initial-CR dubbing) | **PARTIAL** | Dubs CR for input trees < 1" lacking a measurement; pyfvs assigns CR via the model/establishment. |
| `cratet.f` | 614 | N/A | **N/A** | Pre-cycle orchestrator; pyfvs drives growth directly in `Stand`/`Tree`. |

## CORE_BARK (1 file, 118 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `bratio.f` | 118 | `bark_ratio.py::CABarkRatioModel` | **PORTED** | CA bark-ratio, 3 equation types / 28 species groups from `ca/bratio.f`. |

## CORE_REGEN (3 files, 948 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `regent.f` | 536 | `establishment.py` (CA establishment) + `tree.py` | **PARTIAL** | CA LESTB bare-ground establishment (`ca/essubh.f` species-group HHT + `ca/smhtgf.f`) + blend ported; full small-tree increment model approximated. |
| `esuckr.f` | 344 | N/A | **MISSING** | Root-sucker / sprout regeneration; not modeled in pyfvs. |
| `estump.f` | 68 | N/A | **MISSING** | Stump-sprout regeneration; not modeled in pyfvs. |

## CORE_ESTAB (1 file, 90 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `essubh.f` | 90 | `establishment.py` (CA species-group HHT) | **PARTIAL** | CA establishment sub-record height; species-group HHT ported (2026-04-21), values not all independently verified. |

## CORE_MORT (2 files, 1277 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `morts.f` | 1062 | `mortality.py::MortalityModel` (generic) | **PARTIAL** | CA uses the **generic** `MortalityModel` (registry `mortality_class=MortalityModel`), not a CA-faithful mortality port. Contributes to the parity TPA divergence (CA SN-fallback open item). |
| `varmrt.f` | 215 | `mortality.py` (percentile/tolerance distribution) | **PARTIAL** | Mortality distribution by percentile + tolerance; shared distribution path, CA coefficients not verified. |

## CORE_SITE (4 files, 1082 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `sitset.f` | 295 | `Stand` constructor | **PARTIAL** | Site-index assignment; single SI per stand, per-species transform not ported. |
| `ecocls.f` | 564 | `stand_metrics.py` (SDI maximums) | **PARTIAL** | Per-variant SDI maximums ported; ecoclass-association SI/species defaults not ported (pyfvs takes SI as input). |
| `sichg.f` | 162 | N/A | **N/A** | Inter-species site-index conversion; pyfvs uses a single stand SI. |
| `dunn.f` | 61 | N/A | **N/A** | Dunning site-class code keyword processing; pyfvs takes SI directly. |

## VOLUME (2 files, 212 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `formcl.f` | 156 | N/A | **N/A** | Form factors for FVS native volume; pyfvs uses NVEL (`volume_library.py`). |
| `cubrds.f` | 56 | N/A | **N/A** | BLOCK DATA cubic/board-foot defaults; superseded by NVEL. |

## CORE_INIT (7 files, 4666 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `pvref6.f` | 2873 | N/A | **N/A** | PV/reference → habitat/ecoclass mapping (HABTYP). Keyword/habitat infrastructure. |
| `pvref5.f` | 583 | N/A | **N/A** | Older PV/reference → habitat/ecoclass mapping (HABTYP). Keyword infrastructure. |
| `grinit.f` | 338 | N/A | **N/A** | Variant initialization boilerplate. |
| `habtyp.f` | 341 | N/A | **N/A** | Habitat-type code keyword translation. |
| `blkdat.f` | 265 | (expanded into `cfg/ca/*.json`) | **N/A** | COMMON-block DATA; transcribed to pyfvs CA JSON configs. |
| `forkod.f` | 228 | N/A | **N/A** | Forest-type code keyword translation. |
| `grohed.f` | 38 | N/A | **N/A** | Output header formatting. |

## Remaining work priority order (M3)

1. **CORE_HT** — close `htgf.f`/`htcalc.f` height-growth drift (top-height +34–44% is the dominant CA parity gap).
2. **CORE_MORT** — replace the generic `MortalityModel` with a CA-faithful `morts.f`/`varmrt.f` port.
3. **CORE_DG** — verify CA `dgf.f` coefficients against the Fortran DATA blocks.
4. **CORE_REGEN** — `esuckr.f`/`estump.f` sprouting (only matters for sprouting species).

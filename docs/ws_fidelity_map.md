# WS Fortran → pyfvs Fidelity Map

**Source**: `/Users/cmihiar/Projects/ForestVegetationSimulator/ws/`

Map of every WS-variant (Western Sierra Nevada) Fortran file to its pyfvs
counterpart, classified by fidelity status. Built 2026-06-21 from the 29 `.f`
files in the `ws/` source directory (12,039 LOC). Companion to
`docs/sn_fidelity_map.md` / `docs/cs_fidelity_map.md`; per-variant-directory scope.

## Status legend

- **PORTED** — pyfvs has a full semantic equivalent; the named pyfvs module ports it
- **PARTIAL** — some pieces ported; specific gaps documented
- **MISSING** — no pyfvs equivalent
- **UNKNOWN** — needs investigation (target: zero)
- **N/A** — intentionally not ported (keyword infra, DATA blocks, NVEL-substituted volume, etc.)

## Scope

Classifies the files in the `ws/` directory. WS is a **stub-scaffold** variant:
the model classes exist (`ws_diameter_growth.py`, `WSBarkRatioModel`,
`WSCrownRatioModel`) but the per-species metadata is generic (all species share
`cfg/ws/species/sp.yaml`) and stand-level growth over-predicts severely (parity:
BA +100% to +255%). Mortality uses the generic `MortalityModel`. `ws/common/*.F77`
are COMMON-block parameter includes: N/A. Volume maps to NVEL (`volume_library.py`).

## Fidelity Summary by Category

| Category | Files | LOC | PORTED | PARTIAL | MISSING | UNKNOWN | N/A |
|---|---|---|---|---|---|---|---|
| CORE_DG | 3 | 1834 | 0 | 2 | 1 | 0 | 0 |
| CORE_HT | 5 | 1942 | 1 | 4 | 0 | 0 | 0 |
| CORE_CROWN | 4 | 2101 | 1 | 2 | 0 | 0 | 1 |
| CORE_BARK | 1 | 147 | 1 | 0 | 0 | 0 | 0 |
| CORE_REGEN | 1 | 910 | 0 | 1 | 0 | 0 | 0 |
| CORE_ESTAB | 1 | 217 | 0 | 1 | 0 | 0 | 0 |
| CORE_MORT | 2 | 1430 | 0 | 2 | 0 | 0 | 0 |
| CORE_SITE | 3 | 559 | 0 | 1 | 0 | 0 | 2 |
| VOLUME | 3 | 947 | 0 | 0 | 2 | 0 | 1 |
| CORE_INIT | 6 | 1952 | 0 | 0 | 0 | 0 | 6 |
| **TOTAL** | **29** | **12039** | **3** | **13** | **3** | **0** | **10** |

**29 CORE files · 0 UNKNOWN / unclassified.** 16 of 29 PORTED or PARTIAL; 10 N/A;
3 MISSING (DG cap, board-foot volume ×2).

## CORE_DG (3 files, 1834 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `dgf.f` | 859 | `ws_diameter_growth.py` | **PARTIAL** | WS ln(DDS) DG form ported, but generic/stub per-species coefficients drive +100–255% BA over-prediction vs native — not a verified equivalence. |
| `dgdriv.f` | 826 | `ws_diameter_growth.py` + `tree.py` | **PARTIAL** | DG driver; runtime dispatch ported, FVS calibration loop not ported. |
| `dgbnd.f` | 149 | N/A | **MISSING** | DG upper-bound cap (Dolph & Dixon 1993). Not ported; inactive for normal sizes. |

## CORE_HT (5 files, 1942 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `findag.f` | 269 | `tree.py::_effective_age_from_height` | **PORTED** | Inverse Chapman-Richards effective age. |
| `htgf.f` | 1127 | `large_tree_height_growth.py` (WS branch) | **PARTIAL** | Large-tree HG + topographic dispatch; over-predicts with the stub coefficients. |
| `htcalc.f` | 182 | `large_tree_height_growth.py` / `tree.py` (site curve) | **PARTIAL** | Chapman-Richards site curve; WS trajectory not verified. |
| `htdbh.f` | 175 | `height_diameter.py` + `cfg/ws` H-D | **PARTIAL** | Wykoff/Curtis-Arney H-D; relationship ported, dubbing not line-by-line. |
| `smhtgf.f` | 189 | shared small-tree growth (`large_tree_height_growth.py` / `tree.py`) | **PARTIAL** | WS-specific small-tree HG equations not ported; the shared small-tree path approximates. |

## CORE_CROWN (4 files, 2101 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `crown.f` | 707 | `crown_ratio.py::WSCrownRatioModel` | **PORTED** | WS crown-ratio model ported (Weibull); per-species data generic (stub-YAML caveat). |
| `ccfcal.f` | 282 | `crown_competition_factor.py` | **PARTIAL** | Crown width + CCF; WS coefficients not verified. |
| `dubscr.f` | 299 | `crown_ratio.py` (initial-CR dubbing) | **PARTIAL** | Dubs CR for input trees < 1"; pyfvs assigns CR via the model/establishment. |
| `cratet.f` | 813 | N/A | **N/A** | Pre-cycle orchestrator; pyfvs drives growth directly in `Stand`/`Tree`. |

## CORE_BARK (1 file, 147 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `bratio.f` | 147 | `bark_ratio.py::WSBarkRatioModel` | **PORTED** | WS bark-ratio `BRATIO = BARK1 + BARK2/D` (GB diameter-dependent), bounded [0.80, 0.99], from `ws/bratio.f`. |

## CORE_REGEN (1 file, 910 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `regent.f` | 910 | `establishment.py` + `tree.py` | **PARTIAL** | LESTB bare-ground establishment + small-tree blend via the shared establishment path; WS-specific increment model not fully ported. |

## CORE_ESTAB (1 file, 217 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `essubh.f` | 217 | `establishment.py::get_essubh_height` | **PARTIAL** | Establishment sub-record height; shared lookup, WS-specific values not verified (generic species metadata). |

## CORE_MORT (2 files, 1430 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `morts.f` | 1136 | `mortality.py::MortalityModel` (generic) | **PARTIAL** | WS uses the **generic** `MortalityModel` (registry `mortality_class=MortalityModel`), not a WS-faithful port. |
| `varmrt.f` | 294 | `mortality.py` (percentile/tolerance distribution) | **PARTIAL** | Mortality distribution; shared path, WS coefficients not verified. |

## CORE_SITE (3 files, 559 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `sitset.f` | 234 | `Stand` constructor | **PARTIAL** | Site-index assignment; single SI per stand, per-species transform not ported. |
| `sichg.f` | 161 | N/A | **N/A** | Inter-species site-index conversion; pyfvs uses a single stand SI. |
| `dunn.f` | 164 | N/A | **N/A** | Dunning site-class code keyword processing; pyfvs takes SI directly. |

## VOLUME (3 files, 947 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `bfvol.f` | 390 | N/A | **MISSING** | Board-foot volume; pyfvs derives volume from NVEL, FVS board-foot not ported. |
| `logs.f` | 212 | N/A | **MISSING** | R5 Biging board-foot taper; not ported (pyfvs uses NVEL/Clark). |
| `cubrds.f` | 345 | N/A | **N/A** | BLOCK DATA cubic/board-foot defaults; superseded by NVEL. |

## CORE_INIT (6 files, 1952 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `pvref5.f` | 586 | N/A | **N/A** | PV/reference → habitat/ecoclass mapping (HABTYP). Keyword/habitat infrastructure. |
| `grinit.f` | 437 | N/A | **N/A** | Variant initialization boilerplate. |
| `forkod.f` | 364 | N/A | **N/A** | Forest-type code keyword translation. |
| `blkdat.f` | 279 | (expanded into `cfg/ws/*.json`) | **N/A** | COMMON-block DATA; transcribed to pyfvs WS JSON configs. |
| `habtyp.f` | 249 | N/A | **N/A** | Habitat-type code keyword translation. |
| `grohed.f` | 37 | N/A | **N/A** | Output header formatting. |

## Remaining work priority order (M3)

1. **Per-species metadata** — replace the generic `cfg/ws/species/sp.yaml` stub with real per-species WS data; this is the root of the +100–255% over-prediction (affects `dgf.f` and `htgf.f`).
2. **CORE_MORT** — replace the generic `MortalityModel` with a WS-faithful `morts.f`/`varmrt.f` port.
3. **CORE_HT** — verify `htgf.f`/`smhtgf.f` once coefficients are real.
4. **VOLUME** — `bfvol.f`/`logs.f` board-foot if board-foot parity is pursued.

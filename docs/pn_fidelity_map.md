# PN Fortran → pyfvs Fidelity Map

**Source**: `/Users/cmihiar/Projects/ForestVegetationSimulator/pn/`

Map of every PN-variant (Pacific Northwest Coast) Fortran file to its pyfvs
counterpart, classified by fidelity status. Built 2026-06-21 from the 16 `.f`
files in the `pn/` source directory (6,019 LOC). Companion to
`docs/sn_fidelity_map.md` / `docs/cs_fidelity_map.md`; per-variant-directory scope.

## Status legend

- **PORTED** — pyfvs has a full semantic equivalent; the named pyfvs module ports it
- **PARTIAL** — some pieces ported; specific gaps documented
- **MISSING** — no pyfvs equivalent
- **UNKNOWN** — needs investigation (target: zero)
- **N/A** — intentionally not ported (keyword infra, DATA blocks, NVEL-substituted volume, etc.)

## Scope

Classifies the files in the `pn/` directory. **PN shares its growth-driver Fortran
with WC** (PN/WC share models — `pn_diameter_growth.py` is the base that
`wc_diameter_growth.py` subclasses): the `pn/` directory has **no** `dgdriv.f`,
`htgf.f`, `regent.f`, `findag.f`, `essubh.f`, `cratet.f`, or `varmrt.f` — those
live in shared base / WC sources and are classified in `docs/wc_fidelity_map.md`
(and the SN map for shared base routines). Large-tree height growth for PN is in
`large_tree_height_growth.py` (PN branch) but has no `pn/htgf.f` to classify here.
`pn/common/*.F77` are COMMON-block parameter includes (not CORE algorithm): N/A.

## Fidelity Summary by Category

| Category | Files | LOC | PORTED | PARTIAL | MISSING | UNKNOWN | N/A |
|---|---|---|---|---|---|---|---|
| CORE_DG | 1 | 558 | 1 | 0 | 0 | 0 | 0 |
| CORE_HT | 2 | 470 | 1 | 1 | 0 | 0 | 0 |
| CORE_CROWN | 2 | 660 | 1 | 1 | 0 | 0 | 0 |
| CORE_BARK | 1 | 98 | 1 | 0 | 0 | 0 | 0 |
| CORE_SITE | 3 | 816 | 0 | 2 | 0 | 0 | 1 |
| VOLUME | 1 | 134 | 0 | 0 | 0 | 0 | 1 |
| CORE_INIT | 6 | 3283 | 0 | 0 | 0 | 0 | 6 |
| **TOTAL** | **16** | **6019** | **4** | **4** | **0** | **0** | **8** |

**16 CORE files · 0 UNKNOWN / unclassified.** 8 of 16 PORTED or PARTIAL; 8 N/A.

## CORE_DG (1 file, 558 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `dgf.f` | 558 | `pn_diameter_growth.py::PNDiameterGrowthModel` | **PORTED** | PN ln(DDS) equation with topographic effects; per-species coefficients in `cfg/pn/`. MAPLOC/MAPDSQ forest remapping ported. (The DG *driver* `dgdriv.f` is shared with WC — see WC map.) |

## CORE_HT (2 files, 470 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `htcalc.f` | 200 | `pn_height_age.py` | **PORTED** | Species-specific height-age site curves (15 equation types covering all PN species) + ascending-branch `age_from_height` inverse (fixed 2026-04-21). |
| `htdbh.f` | 270 | `height_diameter.py` | **PARTIAL** | Wykoff / Curtis-Arney height-DBH. H-D relationship ported; line-by-line dubbing of arbitrary input-tree heights not fully reproduced. |

## CORE_CROWN (2 files, 660 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `crown.f` | 535 | `crown_ratio.py::PNCrownRatioModel` | **PORTED** | PN crown-ratio model; WC/OP/CA/OC/WS dispatch to this PN class via factories. |
| `ccfcal.f` | 125 | `crown_competition_factor.py::CrownCompetitionFactor` | **PARTIAL** | Crown width + CCF; PN-specific CCF coefficients not independently verified. |

## CORE_BARK (1 file, 98 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `bratio.f` | 98 | `bark_ratio.py::PNBarkRatioModel` | **PORTED** | PN bark-ratio (DIB/DOB) model; shared by WC/OP/CA/OC/WS via factories. |

## CORE_SITE (3 files, 816 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `sitset.f` | 268 | `Stand` constructor (`site_index`) | **PARTIAL** | Site-index assignment. pyfvs carries a single SI per stand; per-species transform not ported. |
| `ecocls.f` | 486 | `stand_metrics.py` (SDI maximums) | **PARTIAL** | Default max-SDI / site-index / site-species by plant association. pyfvs ports per-variant SDI maximums (Reineke for PN); the ecoclass-association lookup that *derives* SI/species defaults is not ported (pyfvs takes SI as input). |
| `sichg.f` | 62 | N/A | **N/A** | Inter-species site-index *conversion* (SICHG). pyfvs uses a single stand SI, so no per-species SI translation is needed. |

## VOLUME (1 file, 134 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `formcl.f` | 134 | N/A | **N/A** | Form factors for FVS's native cubic/board-foot volume equations. pyfvs computes volume via the NVEL library (`volume_library.py`), so FVS form factors are intentionally unused. |

## CORE_INIT (6 files, 3283 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `pvref6.f` | 2298 | N/A | **N/A** | Maps PV/reference codes → FVS habitat/ecoclass code (called from HABTYP). Keyword/habitat-inventory infrastructure. |
| `grinit.f` | 336 | N/A | **N/A** | Variant initialization boilerplate; `Stand`/`Tree` constructors do equivalent setup. |
| `blkdat.f` | 250 | (expanded into `cfg/pn/*.json`) | **N/A** | COMMON-block DATA; transcribed into pyfvs PN JSON configs. |
| `forkod.f` | 218 | N/A | **N/A** | Forest-type code keyword translation. |
| `habtyp.f` | 144 | N/A | **N/A** | Habitat-type code keyword translation. |
| `grohed.f` | 37 | N/A | **N/A** | Output header formatting. |

## Remaining work priority order (M2)

1. **CORE_HT** — verify `htdbh.f` Wykoff/Curtis-Arney coverage; PN top-height parity.
2. **CORE_SITE** — `ecocls.f` ecoclass-association SI/species defaults if multi-association PN parity is pursued.
3. **CORE_CROWN** — verify `ccfcal.f` PN CCF coefficients.
4. Shared growth-driver fidelity (`dgdriv.f`/`htgf.f`/`regent.f`) is tracked in `docs/wc_fidelity_map.md`.

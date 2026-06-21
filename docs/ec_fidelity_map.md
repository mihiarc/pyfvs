# EC Fortran → pyfvs Fidelity Map

**Source**: `/Users/cmihiar/Projects/ForestVegetationSimulator/ec/`

Map of every EC-variant (East Cascades) Fortran file to its pyfvs counterpart,
classified by fidelity status. Built 2026-06-21 from the 28 `.f` files in the
`ec/` source directory (13,836 LOC). Companion to `docs/sn_fidelity_map.md` /
`docs/cs_fidelity_map.md`; per-variant-directory scope.

## Status legend

- **PORTED** — pyfvs has a full semantic equivalent; the named pyfvs module ports it
- **PARTIAL** — some pieces ported; specific gaps documented
- **MISSING** — no pyfvs equivalent
- **UNKNOWN** — needs investigation (target: zero)
- **N/A** — intentionally not ported (keyword infra, DATA blocks, NVEL-substituted volume, etc.)

## Scope

Classifies the files in the `ec/` directory. EC is a self-contained variant with
its own diameter growth, height growth, small-tree growth, crown, bark, and
mortality models in pyfvs (Phase 2–4 port, 2026-04-20/21). Volume routines map to
the shared NVEL library (`volume_library.py`). `ec/common/*.F77` are COMMON-block
parameter includes (not CORE algorithm): N/A.

## Fidelity Summary by Category

| Category | Files | LOC | PORTED | PARTIAL | MISSING | UNKNOWN | N/A |
|---|---|---|---|---|---|---|---|
| CORE_DG | 2 | 1471 | 1 | 1 | 0 | 0 | 0 |
| CORE_HT | 5 | 1585 | 3 | 2 | 0 | 0 | 0 |
| CORE_CROWN | 4 | 1777 | 1 | 2 | 0 | 0 | 1 |
| CORE_BARK | 1 | 144 | 1 | 0 | 0 | 0 | 0 |
| CORE_REGEN | 1 | 734 | 0 | 1 | 0 | 0 | 0 |
| CORE_ESTAB | 1 | 72 | 0 | 1 | 0 | 0 | 0 |
| CORE_MORT | 2 | 1383 | 0 | 2 | 0 | 0 | 0 |
| CORE_SITE | 3 | 1393 | 0 | 2 | 1 | 0 | 0 |
| VOLUME | 3 | 803 | 0 | 0 | 1 | 0 | 2 |
| CORE_INIT | 6 | 4474 | 0 | 0 | 0 | 0 | 6 |
| **TOTAL** | **28** | **13836** | **6** | **10** | **2** | **0** | **10** |

**28 CORE files · 0 UNKNOWN / unclassified.** 16 of 28 PORTED or PARTIAL; 10 N/A;
2 MISSING (`ecocls.f` Phase-5 open item, board-foot volume).

## CORE_DG (2 files, 1471 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `dgf.f` | 658 | `ec_diameter_growth.py::ECDiameterGrowthModel` | **PORTED** | EC ln(DDS) equation with topographic effects + per-species coefficients; WP RELHT bonus + red-alder special equation handled. |
| `dgdriv.f` | 813 | `ec_diameter_growth.py` + `tree.py` | **PARTIAL** | DG driver; runtime DG dispatched per-tree. FVS calibration loop (LSTART/RESLOG) not ported. |

## CORE_HT (5 files, 1585 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `htcalc.f` | 248 | `ec_height_age.py` | **PORTED** | EC height-age site curves (Phase-3 port, 2026-04-21). |
| `findag.f` | 248 | `tree.py::_effective_age_from_height` / `ec_height_age` inverse | **PORTED** | Inverse site curve / effective age. |
| `smhtgf.f` | 253 | `ec_small_tree_growth.py` | **PORTED** | Small-tree (D<3") height growth; Phase-3 port closed EC/WL TH −29%→−2%. |
| `htgf.f` | 475 | `large_tree_height_growth.py::calculate_height_growth` (EC branch) | **PARTIAL** | Large-tree height growth + topographic dispatch (Phase-3). Residual height-growth drift contributes to remaining EC xfails. |
| `htdbh.f` | 361 | `height_diameter.py` | **PARTIAL** | Wykoff / Curtis-Arney height-DBH; relationship ported, input-tree dubbing not line-by-line. |

## CORE_CROWN (4 files, 1777 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `crown.f` | 492 | `crown_ratio.py::ECCrownRatioModel` | **PORTED** | EC crown-ratio model (subclasses PNCrownRatioModel with EC coefficients). |
| `ccfcal.f` | 249 | `crown_competition_factor.py` | **PARTIAL** | Crown width + CCF; EC coefficients not independently verified. |
| `dubscr.f` | 267 | `crown_ratio.py` (initial-CR dubbing) | **PARTIAL** | Dubs CR for input trees < 1" DBH lacking a measurement; pyfvs assigns CR via the model / establishment, not this exact dub. |
| `cratet.f` | 769 | N/A | **N/A** | Pre-cycle orchestrator (RCON/CROWN/REGENT). pyfvs drives growth directly in `Stand`/`Tree`. |

## CORE_BARK (1 file, 144 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `bratio.f` | 144 | `bark_ratio.py::ECBarkRatioModel` | **PORTED** | EC bark-ratio model (Phase-2 port). |

## CORE_REGEN (1 file, 734 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `regent.f` | 734 | `establishment.py` (EC LESTB) + `tree.py` | **PARTIAL** | EC LESTB bare-ground establishment cycle (Phase-3) + small-tree blend ported; full small-tree increment model approximated. |

## CORE_ESTAB (1 file, 72 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `essubh.f` | 72 | `establishment.py::get_essubh_height` | **PARTIAL** | Establishment sub-record height; pyfvs lookup used by the EC LESTB path, EC-specific values not all independently verified. |

## CORE_MORT (2 files, 1383 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `morts.f` | 1128 | `mortality.py::ECMortalityModel` | **PARTIAL** | EC periodic mortality (Phase-4 port): per-species Hamilton + halved rate + SN-convention VARADJ. Closed EC/WL 19.2%→15.5% max\|Δ\|; residual needs `ecocls.f` Phase-5 ecological-class handling. |
| `varmrt.f` | 255 | `mortality.py` (percentile/tolerance distribution) | **PARTIAL** | Distributes the mortality rate by percentile + species tolerance; shared distribution path used by `ECMortalityModel`. |

## CORE_SITE (3 files, 1393 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `sitset.f` | 334 | `Stand` constructor | **PARTIAL** | Site-index assignment; single SI per stand, per-species transform not ported. |
| `sichg.f` | 154 | N/A | **N/A** | Inter-species site-index conversion; pyfvs uses a single stand SI. |
| `ecocls.f` | 905 | N/A | **MISSING** | EC ecological-class defaults (max-SDI / SI / site-species by plant association). **EC Phase-5 open item** — not yet ported; tracked in `docs/parity_scorecard_2026-06-21.md` / Context Journal. |

## VOLUME (3 files, 803 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `bfvol.f` | 367 | N/A | **MISSING** | Board-foot volume; pyfvs derives volume from NVEL, the FVS board-foot algorithm is not ported. |
| `formcl.f` | 232 | N/A | **N/A** | Form factors for FVS native volume; pyfvs uses NVEL (`volume_library.py`). |
| `cubrds.f` | 204 | N/A | **N/A** | BLOCK DATA cubic/board-foot defaults; superseded by NVEL. |

## CORE_INIT (6 files, 4474 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `pvref6.f` | 3403 | N/A | **N/A** | PV/reference → habitat/ecoclass mapping (HABTYP). Keyword/habitat infrastructure. |
| `grinit.f` | 399 | N/A | **N/A** | Variant initialization boilerplate. |
| `blkdat.f` | 331 | (expanded into `cfg/ec/*.json`) | **N/A** | COMMON-block DATA; transcribed to pyfvs EC JSON configs. |
| `habtyp.f` | 166 | N/A | **N/A** | Habitat-type code keyword translation. |
| `forkod.f` | 139 | N/A | **N/A** | Forest-type code keyword translation. |
| `grohed.f` | 36 | N/A | **N/A** | Output header formatting. |

## Remaining work priority order (M2)

1. **CORE_SITE** — port `ecocls.f` (EC Phase-5 open item): ecological-class max-SDI / SI / site-species defaults; the largest remaining EC fidelity gap.
2. **CORE_HT** — close `htgf.f` residual height-growth drift (remaining EC xfails).
3. **CORE_MORT** — verify `morts.f`/`varmrt.f` EC coefficients against the Fortran DATA blocks.
4. **VOLUME** — `bfvol.f` board-foot if board-foot parity is pursued.

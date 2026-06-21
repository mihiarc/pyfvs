# WC Fortran → pyfvs Fidelity Map

**Source**: `/Users/cmihiar/Projects/ForestVegetationSimulator/wc/`

Map of every WC-variant (West Cascades) Fortran file to its pyfvs counterpart,
classified by fidelity status. Built 2026-06-21 from the 29 `.f` files in the
`wc/` source directory (10,227 LOC). Companion to `docs/sn_fidelity_map.md` /
`docs/cs_fidelity_map.md`; per-variant-directory scope.

## Status legend

- **PORTED** — pyfvs has a full semantic equivalent; the named pyfvs module ports it
- **PARTIAL** — some pieces ported; specific gaps documented
- **MISSING** — no pyfvs equivalent
- **UNKNOWN** — needs investigation (target: zero)
- **N/A** — intentionally not ported (keyword infra, DATA blocks, NVEL-substituted volume, etc.)

## Scope

Classifies the files in the `wc/` directory. **WC shares its growth models with
PN** (`wc_diameter_growth.py` subclasses `pn_diameter_growth.py`; WC reuses
`PNBarkRatioModel` / `PNCrownRatioModel`); the WC directory carries the full
growth driver (`dgdriv.f`, `htgf.f`, `regent.f`), which PN's directory lacks, so
WC also covers the shared PN/WC driver. `wc/common/*.F77` are COMMON-block
parameter includes (not CORE algorithm): N/A. Volume routines map to the shared
NVEL library (`volume_library.py` / `taper.py` / `merchandising.py`).

## Fidelity Summary by Category

| Category | Files | LOC | PORTED | PARTIAL | MISSING | UNKNOWN | N/A |
|---|---|---|---|---|---|---|---|
| CORE_DG | 3 | 1332 | 1 | 1 | 1 | 0 | 0 |
| CORE_HT | 4 | 1143 | 2 | 2 | 0 | 0 | 0 |
| CORE_CROWN | 4 | 1444 | 1 | 2 | 0 | 0 | 1 |
| CORE_BARK | 1 | 81 | 1 | 0 | 0 | 0 | 0 |
| CORE_REGEN | 3 | 1063 | 0 | 1 | 2 | 0 | 0 |
| CORE_ESTAB | 1 | 100 | 0 | 1 | 0 | 0 | 0 |
| CORE_SITE | 3 | 1144 | 0 | 2 | 0 | 0 | 1 |
| VOLUME | 4 | 709 | 0 | 0 | 2 | 0 | 2 |
| CORE_INIT | 6 | 3211 | 0 | 0 | 0 | 0 | 6 |
| **TOTAL** | **29** | **10227** | **5** | **9** | **5** | **0** | **10** |

**29 CORE files · 0 UNKNOWN / unclassified.** 14 of 29 PORTED or PARTIAL; 10 N/A;
5 MISSING (DG cap, sprout regen ×2, board-foot volume ×2).

## CORE_DG (3 files, 1332 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `dgf.f` | 543 | `wc_diameter_growth.py::WCDiameterGrowthModel` | **PORTED** | WC ln(DDS) equation (subclasses PN); WC coefficients + MAPLOC/MAPDSQ forest remapping ported. |
| `dgdriv.f` | 740 | `wc_diameter_growth.py` + `tree.py` | **PARTIAL** | DG driver (shared PN/WC). Runtime DG dispatched per-tree; FVS calibration loop (LSTART/RESLOG) not ported (no growth-sample fixture). |
| `dgbnd.f` | 49 | N/A | **MISSING** | DG upper-bound cap (DF bounding function for all but redwood). Not ported; inactive for normal-size trees (same gap as SN `dgbnd.f`). |

## CORE_HT (4 files, 1143 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `htgf.f` | 495 | `large_tree_height_growth.py::calculate_height_growth` (PN/WC branch) | **PARTIAL** | Large-tree height growth with topographic modifiers. Ported for PN/WC; potential-HG path + residual drift not fully closed. |
| `htcalc.f` | 185 | `pn_height_age.py` (WC overrides) | **PORTED** | Height-age site curves; WC overrides DF/SS/RC to the Curtis base-age-100 curve (`_WC_EQUATION_MAP`). |
| `htdbh.f` | 322 | `height_diameter.py` | **PARTIAL** | Wykoff / Curtis-Arney height-DBH; relationship ported, input-tree dubbing not line-by-line. |
| `findag.f` | 141 | `tree.py::_effective_age_from_height` / `pn_height_age.age_from_height` | **PORTED** | Inverse Chapman-Richards / site-curve effective age. |

## CORE_CROWN (4 files, 1444 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `crown.f` | 521 | `crown_ratio.py::PNCrownRatioModel` | **PORTED** | WC shares the PN crown-ratio model via the crown-ratio factory. |
| `ccfcal.f` | 133 | `crown_competition_factor.py` | **PARTIAL** | Crown width + CCF; WC coefficients not independently verified. |
| `dubscr.f` | 131 | `crown_ratio.py` (initial-CR dubbing) | **PARTIAL** | Dubs crown ratio for input trees < 1" DBH that lack a CR measurement. pyfvs assigns CR via the crown-ratio model / establishment, not this exact small-tree dub. |
| `cratet.f` | 659 | N/A | **N/A** | Pre-cycle orchestrator (calls RCON/CROWN/REGENT). pyfvs drives growth directly in `Stand`/`Tree`. |

## CORE_BARK (1 file, 81 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `bratio.f` | 81 | `bark_ratio.py::PNBarkRatioModel` | **PORTED** | WC shares the PN bark-ratio model via the factory. |

## CORE_REGEN (3 files, 1063 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `regent.f` | 662 | `establishment.py::_grow_establishment_cycle_pnwc` + `tree.py` | **PARTIAL** | PN/WC LESTB bare-ground establishment (ESSUBH + 2×SMHGDG, SCALE=0.5, DBH-overwrite) + small-tree blend ported; full small-tree increment model approximated. |
| `esuckr.f` | 332 | N/A | **MISSING** | Root-sucker / sprout regeneration (e.g., red alder). Sprouting regeneration not modeled in pyfvs. |
| `estump.f` | 69 | N/A | **MISSING** | Stump-sprout regeneration setup. Sprouting not modeled in pyfvs. |

## CORE_ESTAB (1 file, 100 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `essubh.f` | 100 | `establishment.py::get_essubh_height` | **PARTIAL** | Establishment sub-record height (ESSUBH). pyfvs has the lookup used by the PN/WC LESTB path; WC-specific values not all independently verified. |

## CORE_SITE (3 files, 1144 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `sitset.f` | 261 | `Stand` constructor | **PARTIAL** | Site-index assignment; single SI per stand, per-species transform not ported. |
| `ecocls.f` | 821 | `stand_metrics.py` (SDI maximums) | **PARTIAL** | Per-variant SDI maximums ported (Reineke for WC); ecoclass-association SI/species defaults not ported (pyfvs takes SI as input). |
| `sichg.f` | 62 | N/A | **N/A** | Inter-species site-index conversion; pyfvs uses a single stand SI. |

## VOLUME (4 files, 709 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `bfvol.f` | 250 | N/A | **MISSING** | Board-foot volume. pyfvs derives volume from NVEL; the FVS board-foot algorithm is not ported. |
| `logs.f` | 133 | N/A | **MISSING** | R5 Biging board-foot taper. Not ported; pyfvs uses NVEL/Clark taper. |
| `formcl.f` | 270 | N/A | **N/A** | Form factors for FVS native volume; pyfvs uses NVEL (`volume_library.py`). |
| `cubrds.f` | 56 | N/A | **N/A** | BLOCK DATA cubic/board-foot defaults; superseded by NVEL. |

## CORE_INIT (6 files, 3211 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `pvref6.f` | 2315 | N/A | **N/A** | PV/reference → habitat/ecoclass mapping (HABTYP). Keyword/habitat infrastructure. |
| `grinit.f` | 335 | N/A | **N/A** | Variant initialization boilerplate. |
| `blkdat.f` | 250 | (expanded into `cfg/wc/*.json`) | **N/A** | COMMON-block DATA; transcribed to pyfvs WC JSON configs. |
| `habtyp.f` | 164 | N/A | **N/A** | Habitat-type code keyword translation. |
| `forkod.f` | 110 | N/A | **N/A** | Forest-type code keyword translation. |
| `grohed.f` | 37 | N/A | **N/A** | Output header formatting. |

## Remaining work priority order (M2)

1. **CORE_HT** — close `htgf.f` residual height-growth drift; verify `htdbh.f`.
2. **CORE_DG** — `dgdriv.f` calibration; `dgbnd.f` cap (low priority — inactive at normal sizes).
3. **VOLUME** — `bfvol.f`/`logs.f` board-foot if board-foot parity is pursued.
4. **CORE_REGEN** — `esuckr.f`/`estump.f` sprout regeneration (only matters for sprouting species).
5. **CORE_SITE** — `ecocls.f` ecoclass-association defaults for multi-association parity.

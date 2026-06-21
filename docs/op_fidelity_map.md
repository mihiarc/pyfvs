# OP Fortran → pyfvs Fidelity Map

**Source**: `/Users/cmihiar/Projects/ForestVegetationSimulator/op/`

Map of every OP-variant (ORGANON Pacific Northwest) Fortran file to its pyfvs
counterpart, classified by fidelity status. Built 2026-06-21 from the 12 `.f`
files in the `op/` source directory (6,400 LOC). Companion to
`docs/sn_fidelity_map.md` / `docs/cs_fidelity_map.md`; per-variant-directory scope.

## Status legend

- **PORTED** — pyfvs has a full semantic equivalent; the named pyfvs module ports it
- **PARTIAL** — some pieces ported; specific gaps documented
- **MISSING** — no pyfvs equivalent
- **UNKNOWN** — needs investigation (target: zero)
- **N/A** — intentionally not ported (keyword infra, DATA blocks, etc.)

## Scope

OP is the least-documented pyfvs variant. The native `op/` directory is a **thin
FVS-side wrapper around the ORGANON growth library** (only 12 files; no
`htcalc`/`htdbh`/`bratio`/`ccfcal`/`varmrt`/`sitset`-companions — those live in the
linked ORGANON code). pyfvs reimplements the OP diameter growth directly
(`op_diameter_growth.py`) with a direct ln(DG) form; **bark/crown fall back to the
PN models** and **mortality uses the generic `MortalityModel`** (registry).
`op/common/*.F77` are COMMON-block parameter includes: N/A.

## Fidelity Summary by Category

| Category | Files | LOC | PORTED | PARTIAL | MISSING | UNKNOWN | N/A |
|---|---|---|---|---|---|---|---|
| CORE_DG | 2 | 1636 | 1 | 1 | 0 | 0 | 0 |
| CORE_HT | 1 | 519 | 0 | 1 | 0 | 0 | 0 |
| CORE_CROWN | 2 | 1550 | 0 | 1 | 0 | 0 | 1 |
| CORE_REGEN | 1 | 688 | 0 | 1 | 0 | 0 | 0 |
| CORE_MORT | 1 | 864 | 0 | 1 | 0 | 0 | 0 |
| CORE_SITE | 1 | 343 | 0 | 1 | 0 | 0 | 0 |
| CORE_SPECIES | 1 | 60 | 0 | 1 | 0 | 0 | 0 |
| CORE_INIT | 3 | 740 | 0 | 0 | 0 | 0 | 3 |
| **TOTAL** | **12** | **6400** | **1** | **7** | **0** | **0** | **4** |

**12 CORE files · 0 UNKNOWN / unclassified.** 8 of 12 PORTED or PARTIAL; 4 N/A;
0 MISSING.

## CORE_DG (2 files, 1636 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `dgf.f` | 565 | `op_diameter_growth.py::OPDiameterGrowthModel` | **PORTED** | OP direct ln(DG) diameter-growth model; per-species coefficients in `cfg/op/`. |
| `dgdriv.f` | 1071 | `op_diameter_growth.py` + `tree.py::_grow_large_tree_op` | **PARTIAL** | DG driver (ORGANON wrapper). Runtime dispatch ported; calibration / full ORGANON driver semantics not reproduced. |

## CORE_HT (1 file, 519 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `htgf.f` | 519 | `tree.py::_grow_large_tree_op` | **PARTIAL** | OP height increment (from species/habitat/DBH/DBH-increment). pyfvs grows OP height via the large-tree path; the ORGANON HG is not separately verified line-by-line. |

## CORE_CROWN (2 files, 1550 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `crown.f` | 557 | `crown_ratio.py::PNCrownRatioModel` (fallback) | **PARTIAL** | OP uses the **PN crown-ratio model** as a fallback (registry `crown_ratio_class=PNCrownRatioModel`), not an OP/ORGANON-faithful crown port. |
| `cratet.f` | 993 | N/A | **N/A** | Pre-cycle orchestrator (calls ORGANON EXECUTE / CROWN / REGENT). pyfvs drives growth directly in `Stand`/`Tree`. |

## CORE_REGEN (1 file, 688 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `regent.f` | 688 | `establishment.py` + `tree.py` | **PARTIAL** | Establishment / small-tree blend via the shared path; OP-specific ORGANON regeneration not fully ported. |

## CORE_MORT (1 file, 864 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `morts.f` | 864 | `mortality.py::MortalityModel` (generic) | **PARTIAL** | OP uses the **generic** `MortalityModel` (registry `mortality_class=MortalityModel`), not the OP/ORGANON mortality. |

## CORE_SITE (1 file, 343 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `sitset.f` | 343 | `Stand` constructor | **PARTIAL** | Site-index assignment; single SI per stand, per-species transform not ported. |

## CORE_SPECIES (1 file, 60 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `orgspc.f` | 60 | `op_diameter_growth.py` (species handling) | **PARTIAL** | FVS-sequence → ORGANON-FIA species conversion. pyfvs selects OP species coefficients directly; the exact FVS→ORGANON FIA conversion table is not separately verified. |

## CORE_INIT (3 files, 740 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `grinit.f` | 452 | N/A | **N/A** | Variant initialization boilerplate. |
| `blkdat.f` | 250 | (expanded into `cfg/op/*.json`) | **N/A** | COMMON-block DATA; transcribed to pyfvs OP JSON configs. |
| `grohed.f` | 38 | N/A | **N/A** | Output header formatting. |

## Remaining work priority order (M3)

1. **CORE_CROWN / CORE_MORT** — replace the PN-crown and generic-mortality fallbacks with OP/ORGANON-faithful models.
2. **CORE_HT** — verify `htgf.f` ORGANON height growth.
3. **CORE_DG** — verify OP `dgf.f` coefficients and the `dgdriv.f` ORGANON driver semantics.
4. **CORE_SPECIES** — verify the `orgspc.f` FVS→ORGANON species mapping.

*Note: a separate native-side blocker (FVSop produces a degenerate stand for
planted Douglas-fir) is documented in `docs/parity_scorecard_2026-06-21.md`; it
affects parity measurement, not this source-fidelity classification.*

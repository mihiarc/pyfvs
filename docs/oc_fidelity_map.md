# OC Fortran → pyfvs Fidelity Map

**Source**: `/Users/cmihiar/Projects/ForestVegetationSimulator/oc/`

Map of every OC-variant (Southwest Oregon, ORGANON) Fortran file to its pyfvs
counterpart, classified by fidelity status. Built 2026-06-21 from the 12 `.f`
files in the `oc/` source directory (6,251 LOC). Companion to
`docs/sn_fidelity_map.md` / `docs/cs_fidelity_map.md`; per-variant-directory scope.

## Status legend

- **PORTED** — pyfvs has a full semantic equivalent; the named pyfvs module ports it
- **PARTIAL** — some pieces ported; specific gaps documented
- **MISSING** — no pyfvs equivalent
- **UNKNOWN** — needs investigation (target: zero)
- **N/A** — intentionally not ported (keyword infra, DATA blocks, etc.)

## Scope

OC's native `oc/` directory is a **thin FVS-side wrapper around the ORGANON SWO
library** (12 files; ORGANON does the growth). pyfvs reimplements the ORGANON SWO
equations directly: `oc_diameter_growth.py` (`organon_swo_diameter_growth`),
`oc_height_growth.py` (`organon_swo_height_growth`), `OCCrownRatioModel`,
`OCBarkRatioModel`, and `OrganonSwoMortalityModel`. **Open item:** native OC drives
mortality through the ORGANON DLL, which the pyfvs mortality port approximates
(tracked in `docs/parity_scorecard_2026-06-21.md`). `oc/common/*.F77` are
COMMON-block parameter includes: N/A. (OC bark coefficients live in `blkdat.f`;
there is no `oc/bratio.f`.)

## Fidelity Summary by Category

| Category | Files | LOC | PORTED | PARTIAL | MISSING | UNKNOWN | N/A |
|---|---|---|---|---|---|---|---|
| CORE_DG | 2 | 1563 | 1 | 1 | 0 | 0 | 0 |
| CORE_HT | 1 | 329 | 1 | 0 | 0 | 0 | 0 |
| CORE_CROWN | 2 | 1519 | 1 | 0 | 0 | 0 | 1 |
| CORE_REGEN | 1 | 578 | 0 | 1 | 0 | 0 | 0 |
| CORE_MORT | 1 | 1096 | 0 | 1 | 0 | 0 | 0 |
| CORE_SITE | 1 | 345 | 0 | 1 | 0 | 0 | 0 |
| CORE_SPECIES | 1 | 70 | 1 | 0 | 0 | 0 | 0 |
| CORE_INIT | 3 | 751 | 0 | 0 | 0 | 0 | 3 |
| **TOTAL** | **12** | **6251** | **4** | **4** | **0** | **0** | **4** |

**12 CORE files · 0 UNKNOWN / unclassified.** 8 of 12 PORTED or PARTIAL; 4 N/A;
0 MISSING.

## CORE_DG (2 files, 1563 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `dgf.f` | 480 | `oc_diameter_growth.py::organon_swo_diameter_growth` | **PORTED** | ORGANON SWO diameter growth (DG_SWO, 18 species groups); runtime applies the −ln(2) 10→5yr conversion (except tanoak). |
| `dgdriv.f` | 1083 | `oc_diameter_growth.py` + `tree.py` | **PARTIAL** | DG driver. The `regent.f` IORG=1 blend-weight bypass (XDWT=XWT=1.0) is ported; full ORGANON EXECUTE driver semantics not reproduced; calibration not ported. |

## CORE_HT (1 file, 329 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `htgf.f` | 329 | `oc_height_growth.py::organon_swo_height_growth` | **PORTED** | ORGANON SWO height growth (HS_HG + HG_SWO, 5 major conifer groups). |

## CORE_CROWN (2 files, 1519 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `crown.f` | 560 | `crown_ratio.py::OCCrownRatioModel` | **PORTED** | OC per-species Weibull crown ratio, 33 species, from `oc/crown.f`. |
| `cratet.f` | 959 | N/A | **N/A** | Pre-cycle orchestrator (calls ORGANON EXECUTE / CROWN / REGENT). pyfvs drives growth directly in `Stand`/`Tree`. |

## CORE_REGEN (1 file, 578 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `regent.f` | 578 | `tree.py::_grow_small_tree_oc` + `establishment.py` | **PARTIAL** | OC small-tree growth + LESTB establishment + the IORG blend-weight override ported; full ORGANON regeneration not fully reproduced. |

## CORE_MORT (1 file, 1096 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `morts.f` | 1096 | `mortality.py::OrganonSwoMortalityModel` | **PARTIAL** | ORGANON SWO mortality (PM_SWO + MORTAL_RUN density caps) ported. **Native OC drives mortality through the ORGANON DLL**, which differs — the open **OC-ORGANON** item (parity scorecard). For PP, TPA matches native within tolerance; the residual OC parity gap is ORGANON *growth*, not mortality. |

## CORE_SITE (1 file, 345 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `sitset.f` | 345 | `Stand` constructor | **PARTIAL** | Site-index assignment; single SI per stand, per-species transform not ported. |

## CORE_SPECIES (1 file, 70 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `orgspc.f` | 70 | `oc_diameter_growth.py::_IORG_SPECIES` | **PORTED** | FVS-sequence → ORGANON-FIA species conversion; pyfvs carries the IORG species map used by the SWO DG/HG/mortality models. |

## CORE_INIT (3 files, 751 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---|---|---|---|---|
| `grinit.f` | 454 | N/A | **N/A** | Variant initialization boilerplate. |
| `blkdat.f` | 260 | (expanded into `cfg/oc/*.json`) | **N/A** | COMMON-block DATA (incl. OC bark coefficients); transcribed to pyfvs OC JSON configs. |
| `grohed.f` | 37 | N/A | **N/A** | Output header formatting. |

## Remaining work priority order (M3)

1. **CORE_MORT** — resolve the ORGANON-DLL mortality difference (`morts.f`): decide port vs. approximate vs. documented gap (OC-ORGANON open item).
2. **CORE_DG** — close the ORGANON-growth over-prediction surfaced for PP (BA/QMD high while TPA matches) against the pinned native build.
3. **CORE_REGEN** — verify the `regent.f` ORGANON regeneration / blend-weight path.

# Forest-rents pipeline parity remediation plan

Generated 2026-04-21 after the cycle-aligned 50yr sweep (5 PASS / 9 WARN /
38 FAIL). Each FAIL case below lists the dominant metric driving the
divergence and the probable lever for closing it.

## Summary of root-cause patterns

| Pattern | Variants | Species | Lever |
|---|---|---|---|
| LS TopH under-prediction (-13% to -21%) | LS | BF, QA, SM, WS, RP, JP, RO, YB, PB, WA | Port `ls/htgf.f` large-tree HG with full BALMOD + crown modifiers; current Chapman-Richards-only path under-predicts by ~15% systematically. Confirmed structural: 55yr pyfvs still trails 50yr native by 11% so not just a cycle mismatch. |
| NE volume +20-35% with small BA/QMD/topH deltas | NE | WP, RS, SM, RM, YB | Volume calibration: growth metrics align to ±5–10% but volume drifts +25%. Candidate: NE Clark taper coefficients or merchandising top-diameter differences between R9 pyfvs and native. |
| CS scattered BA +15-63% | CS | WO, WN, BC, SM, SH, YP, RM | CS large-tree HG + DG calibration. WN is an outlier (+63%); others roughly uniform overgrowth. |
| PN species-specific TopH -47% to -61% | PN | SS, RC, GF | SS/RC/GF fall outside the height-age curves `_calculate_potential_height_growth_pnwc` handles for the common species. Need to verify these three species' height-age curves match Fortran `pn/htcalc.f`. |
| CA BA drift +14% to +51% | CA | DF, PP, LP, WF | CA has DG coefficients ported but no large-tree HG. LP is the worst (+51% BA). Requires `ca/htgf.f` port. |
| EC WL +60% BA | EC | WL | Phase 3 of EC port: `ec/htgf.f` (large-tree HG) and `ec/smhtgf.f` (small-tree HG) not yet ported. |
| NE uniform BA +8-24% | NE | WP, RS, SM, YB | Same NE HG issue as LS; `ne/htgf.f` port. |

## Per-species FAIL table with probable lever

| Variant | Species | ΔBA | ΔQMD | ΔTopH | ΔVol | Driver | Lever |
|---|---|---:|---:|---:|---:|---|---|
| NE | WP | +2% | +6% | +5% | +23% | Volume | NE volume library audit |
| NE | RS | +21% | +10% | +4% | +35% | Growth + volume | ne/htgf.f + volume audit |
| NE | BF | +6% | +6% | +3% | +16% | Volume | NE volume library audit |
| NE | SM | +13% | +7% | +5% | +31% | Volume | NE volume library audit |
| NE | RM | +10% | +5% | -1% | +21% | Volume | NE volume library audit |
| NE | YB | +16% | +9% | +5% | +31% | Volume | NE volume library audit |
| LS | RP | +2% | +2% | -20% | +10% | HG | ls/htgf.f |
| LS | JP | +4% | 0% | -20% | +10% | HG | ls/htgf.f |
| LS | WP | +12% | +14% | -13% | +27% | DG + HG + volume | Multi-phase |
| LS | WS | +25% | +13% | -21% | +30% | DG + HG | ls/dgf.f + ls/htgf.f |
| LS | BF | +5% | +10% | -17% | +10% | HG | ls/htgf.f |
| LS | QA | -16% | 0% | -16% | -10% | HG | ls/htgf.f (QA is intolerant, different modifier) |
| LS | SM | +26% | +13% | -17% | +29% | DG + HG | ls/dgf.f + ls/htgf.f |
| LS | RO | +9% | +8% | -17% | +17% | HG + volume | ls/htgf.f + volume |
| LS | YB | +10% | +6% | -13% | +16% | HG + volume | ls/htgf.f |
| LS | PB | +8% | +10% | -13% | +17% | HG + volume | ls/htgf.f |
| LS | WA | +1% | +5% | -16% | +15% | HG | ls/htgf.f |
| CS | WO | +21% | +11% | -10% | +40% | HG + DG | cs/htgf.f + cs/dgf.f |
| CS | WN | +63% | -8% | -9% | +74% | BA + volume outlier | WN-specific check |
| CS | BC | +27% | +19% | -14% | +40% | All | cs/htgf.f + cs/dgf.f |
| CS | RO | -3% | -2% | -12% | +9% | Near-WARN | Small HG nudge |
| CS | SM | +16% | +6% | -12% | +25% | HG | cs/htgf.f |
| CS | SH | +39% | +19% | -9% | +52% | All | cs/htgf.f + cs/dgf.f |
| CS | YP | -17% | -11% | -6% | -9% | BA + QMD | cs/dgf.f YP-specific |
| CS | RM | +18% | +14% | -12% | +29% | All | cs/htgf.f + cs/dgf.f |
| PN | DF | -8% | +7% | +1% | -4% | Near-WARN | Minor nudge |
| PN | SS | -17% | +9% | -61% | -75% | HG (severe) | SS height-age curve audit |
| PN | RC | -4% | 0% | -54% | -28% | HG | RC height-age curve audit |
| PN | PP | -14% | +2% | +1% | -39% | Volume | PN volume for PP |
| PN | LP | +9% | +5% | -7% | -33% | Volume | PN volume for LP |
| PN | GF | +13% | +6% | -48% | -54% | HG | GF height-age curve audit |
| EC | WL | +60% | +3% | -4% | +17% | BA only | ec/htgf.f + DG calibration |
| CA | DF | +24% | +41% | +8% | +33% | DG | ca/dgf.f calibration |
| CA | PP | -14% | +22% | +13% | +10% | QMD | ca/dgf.f |
| CA | LP | +51% | +32% | +3% | +7% | DG | ca/dgf.f LP calibration |
| CA | WF | -24% | -10% | +6% | -11% | BA | ca/dgf.f WF calibration |
| PN | ES | +1% | 0% | -1% | -33% | Volume | PN volume for ES |
| PN | AF | +17% | +5% | 0% | -7% | BA | Minor DG nudge |

## Effort estimates to reach WARN

- **Easy (<1hr each, ~8 species)**: LS/RP, LS/JP, LS/BF, LS/WA, LS/YB, LS/PB, PN/DF, PN/AF, CS/RO — need small HG nudges or are already within 1-3pp of WARN.
- **Medium (2-4hr each, ~12 species)**: LS HG refinement (closes 5+ species if done as one pass), NE volume audit (closes 4-5 species), CA DG calibration for outliers.
- **Hard (full port, 4-8hr each, ~18 species)**: `ls/htgf.f`, `cs/htgf.f`, `ne/htgf.f`, `ca/htgf.f`, `ec/htgf.f` Fortran-faithful ports. Each closes multiple species in its variant.

Cumulative estimate: **~40-60 focused dev-hours** to move all 38 FAIL cases
to WARN.

## Not attempted this session (and why)

- LS htgf.f port: requires deep trace vs Fortran implementation; multi-hour work. Tried diagnosing via 55yr experiment; deficit is structural, not a simple cycle-count bug.
- Speculative calibration factors: explicitly ruled out by `feedback_oc_parity` memory — "never use compensating fixes that mask divergence".

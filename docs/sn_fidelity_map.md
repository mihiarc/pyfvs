# SN Fortran → pyfvs Fidelity Map

**Source**: `/Users/cmihiar/Projects/ForestVegetationSimulator/bin/FVSsn_buildDir/`

Comprehensive map of every SN-variant Fortran subroutine to its pyfvs counterpart, classified by fidelity status. Built 2026-04-15 from 512 Fortran files (~159k LOC), of which ~175 (~74k LOC) are CORE algorithm files requiring port for simulation fidelity. Remaining ~337 files are infrastructure (DB, FFE, SVS, region-specific volume, etc.) intentionally not ported.

## Status legend

- **PORTED** — pyfvs has full semantic equivalent verified
- **PARTIAL** — some pieces ported; specific gaps documented
- **MISSING** — no pyfvs equivalent
- **UNKNOWN** — needs investigation
- **N/A** — intentionally not ported (Fortran-specific marshaling, etc.)


## Fidelity Summary by Category

| Category | Files | LOC | PORTED | PARTIAL | MISSING | UNKNOWN | N/A |
|---|---|---|---|---|---|---|---|
| CORE_DG | 5 | 2220 | 3 | 1 | 1 | 0 | 0 |
| CORE_HT | 6 | 1162 | 3 | 2 | 0 | 0 | 1 |
| CORE_MORT | 3 | 1418 | 2 | 0 | 1 | 0 | 0 |
| CORE_BARK | 1 | 178 | 1 | 0 | 0 | 0 | 0 |
| CORE_CROWN | 5 | 3404 | 3 | 1 | 0 | 0 | 1 |
| CORE_STAND | 12 | 4148 | 3 | 1 | 0 | 0 | 8 |
| CORE_REGEN | 2 | 649 | 0 | 1 | 0 | 0 | 1 |
| CORE_ESTAB | 22 | 5437 | 2 | 1 | 3 | 0 | 16 |
| CORE_INIT | 12 | 10193 | 1 | 5 | 0 | 0 | 6 |
| CORE_TREE_OPS | 11 | 1042 | 2 | 2 | 1 | 0 | 6 |
| CORE_RNG | 2 | 159 | 2 | 0 | 0 | 0 | 0 |
| CORE_DATA_IO | 2 | 1796 | 0 | 0 | 0 | 0 | 2 |
| CORE_SITE | 7 | 3836 | 0 | 5 | 0 | 0 | 2 |
| CORE_CUTS | 3 | 2496 | 0 | 1 | 2 | 0 | 0 |
| VOLUME_R8 | 12 | 9261 | 1 | 9 | 2 | 0 | 0 |
| VOLUME_TAPER | 13 | 2367 | 0 | 13 | 0 | 0 | 0 |
| VOLUME_INFRA | 38 | 15701 | 0 | 11 | 0 | 0 | 27 |
| CORE_BIOMASS | 9 | 3917 | 0 | 0 | 6 | 0 | 3 |
| CONFIG_FIA | 10 | 5024 | 0 | 1 | 0 | 0 | 9 |
| **TOTAL** | **175** | **74408** | **23** | **54** | **16** | **0** | **82** |

## CORE_DG (5 files, 2220 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `dgf.f` | 1172 | `sn_diameter_growth.py::SNDiameterGrowthModel.calculate_dds` | **PORTED** | SN ln(DDS) equation; ecounit/forest-type loaded externally. Coefficients verified match. |
| `dgdriv.f` | 749 | `sn_diameter_growth.py + tree.py::_grow_large_tree_sn` | **PARTIAL** | Main DG driver. AR(1) / RHO/RHOCP via model_base._stochastic_multiplier (now ported). Calibration loop (LSTART/RESLOG) NOT ported (no growth-data fixture). |
| `dgbnd.f` | 153 | N/A | **MISSING** | DG upper bound (DLODHI per-species; for trees in [DLODHI(1), DLODHI(2)] linear taper to 0.048 multiplier; for trees > DLODHI(2) DDG=0.048). DLODHI=998 for most species; only triggers for very large trees (>30"). Inactive for all current parity scenarios. SIZCAP also enforced here. |
| `autcor.f` | 95 | `model_base.py::_autcor + _bjrho_table + _ar1_weights` | **PORTED** | BJPHI/BJTHET ARMA(1,1) coefficients & VMLT/COVMLT ported 2026-04-15. |
| `dgscor.f` | 51 | `model_base.py::_stochastic_multiplier` | **PORTED** | AR(1) carry + tail attenuation ported 2026-04-15. |

## CORE_HT (6 files, 1162 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `htgf.f` | 337 | `large_tree_height_growth.py::calculate_height_growth` | **PORTED** | HGMDCR + HGMDRH modifiers via shade-tolerance lookup. RHK/RHM/RHB/RHYXS tables match Fortran by class (all 90 species RHR/RHB/RHYXS verified internally consistent). Pyfvs per-species shade-tolerance mapping matches Fortran RHR for all 89 species pyfvs supports; only BW (Basswood, species 83) is absent from pyfvs species list. |
| `htdbh.f` | 311 | `height_diameter.py + crown_ratio.py?` | **PARTIAL** | Wykoff height-DBH with Fort Bragg specials (IFOR=20 SA/LL/PD/LP). Fort Bragg branch likely missing. |
| `htcalc.f` | 200 | `establishment.py::compute_establishment_height + tree.py::_grow_small_tree` | **PARTIAL** | Chapman-Richards site curve. YP nonmountain branch ported 2026-04-15. Other PCOM/species branches? |
| `htgstp.f` | 200 | N/A | **N/A** | HTGSTOP / TOPKILL keyword damage simulation. Pyfvs has no keyword infrastructure; Fortran returns immediately when no keyword set. |
| `findag.f` | 70 | `tree.py::_effective_age_from_height (within _grow_small_tree)` | **PORTED** | Inverse Chapman-Richards. |
| `avht40.f` | 44 | `stand_metrics.py::calculate_top_height` | **PORTED** | AVH = avg height of top 40 TPA (top height proxy). |

## CORE_MORT (3 files, 1418 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `morts.f` | 1069 | `mortality.py::MortalityModel` | **PORTED** | Background mortality formula RI = 1/(1+exp(p0+p1*D)) matches; RIP = 1-(1-RI)^FINT matches. Background coefficients PMSC(90 species) verified match Fortran (LP/SP/SA/LL/WP/BY at 5.5877, YP/SU/WO at 5.9617, RM/HM at 5.1677). Density mortality trigger (T > TEM = CONST*D10^-1.605*PMSDIL) + VARMRT distribution (via varmrt.f PORTED). Stochastic fixed in two stages: 2026-04-14 (expected-value for stochastic=False) and 2026-04-16 (weighted-sampling-without-replacement / Efraimidis-Spirakis for stochastic=True — cycle-level kill count deterministic, selection randomized but rip-weighted). Remaining gap: Fortran fractional PROB preserves every tree-record at reduced weight; pyfvs integer Trees can't fully replicate this without fractional-TPA refactor. XMORT bracket (X=XMORT for D in [D1,D2]) not yet verified — typically inactive in planted-stand. |
| `varmrt.f` | 229 | `mortality.py::MortalityModel._apply_density_mortality` | **PORTED** | Distributes mortality (TOKILL) across trees by PEFF=0.84525-0.01074*PCT+2e-7*PCT^3 and VARADJ shade-tolerance table. Both PEFF formula and 90-species VARADJ table present in pyfvs. |
| `msbmrt.f` | 120 | `?` | **MISSING** | Mountain-pine-beetle mortality (likely IFOR-conditional). Possibly N/A for SN planted stand. |

## CORE_BARK (1 files, 178 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `bratio.f` | 178 | `bark_ratio.py::BarkRatioModel` | **PORTED** | Linear DIB = a + b*DBH. SN values verified. |

## CORE_CROWN (5 files, 3404 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `cwcalc.f` | 2463 | `crown_width.py::CrownWidthModel` | **PARTIAL** | Crown width equation library (Bechtold, Bragg, Ek, Krajicek, Smith) with Hopkins Index geographic adjustment. Pyfvs has Bechtold/Bragg/Smith/Hopkins; verify per-species equation selection and all 90 species coefficients match Fortran selections (pyfvs 556 LOC vs Fortran 2462 LOC suggests gaps). |
| `crown.f` | 628 | `crown_ratio.py + tree.py::_update_crown_ratio` | **PORTED** | MCR via 5 species-specific eq forms (Hoerl/Power/Linear/Log/Hyperbolic) matches MCREQN dispatch. 3-param Weibull individual-CR assignment by stand-position rank. LESTB establishment CR ported 2026-04-14. Mid-life change bounded to 1%/yr proportion of current CR (matches crown.f:310-314). Utility `update_crown_ratio_change` fixed from absolute to proportional 2026-04-15. |
| `cwidth.f` | 188 | `crown_width.py::CrownWidthModel` | **PORTED** | Crown width allometry. |
| `ccfcal.f` | 65 | `stand_metrics.py::calculate_ccf + crown_width.py::calculate_open_grown_crown_width` | **PORTED** | CCFt = 0.001803 * OCW² * TPA_per_tree (pyfvs per-Tree TPA implicit 1). OCW via species-specific equation (89 SN species in cfg JSON). Small-tree linear scaling DBH<3 matches Fortran CWCALC OMIND=3. |
| `covolp.f` | 60 | N/A | **N/A** | Percent cover accounting for overlap: 100*(1-exp(-CCCOEF*sum_CA/43560)). Output statistic; doesn't feed back into growth or mortality. |

## CORE_STAND (12 files, 4148 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `comprs.f` | 1010 | N/A | **N/A** | Tree-list array compression (Fortran fixed-size MAXTRE arrays). Pyfvs uses Python lists with no fixed bound. |
| `sstage.f` | 943 | N/A | **N/A** | Crookston/Stage stand structural-stage classification — output only, no simulation effect. |
| `sdical.f` | 772 | `stand_metrics.py::get_max_sdi + _load_sn_sdi_maximums` | **PORTED** | BA-weighted avg of per-species SDIDEF (matches XMAX = sum(SDIDEF*BA)/TOTBA). All 90 SN SDI maximums match Fortran SDICON table (verified LP=480, SP=490, SA=385, LL=332, WP=529, YP=478, SU=430, RM=421, WO=361, BY=692, HM=518, VP=499). CLMAXDEN (climate) + BAMAX user-override + per-point XMAXPT are N/A (extension / keyword / multi-plot infrastructure). |
| `gradd.f` | 367 | `stand.py::_grow_single_cycle (core pieces)` | **N/A** | Master end-of-cycle orchestrator: calls beetle/budworm/fire/blister-rust/root-disease extensions plus UPDATE. Core UPDATE + DG-scaling pieces in pyfvs; extensions out of scope. |
| `dense.f` | 306 | `stand_metrics.py + competition.py + ccfcal.f port` | **PARTIAL** | End-of-cycle stand density: BA, QMD, CCF, SDI (Zeide 2026-04-15), PCT, AVH. All ported. Verify ZEIDE DBHZEIDE filter (pyfvs hardcodes 0). |
| `ptbal.f` | 174 | `stand_metrics.py::calculate_pbal_all` | **PORTED** | Plot basal-area-larger via PCTILE. |
| `sdefet.f` | 167 | N/A | **N/A** | BFDEFECT/MCDEFECT keyword (board-feet defect adjustment). Pyfvs has no keyword infrastructure. |
| `sdichk.f` | 106 | N/A | **N/A** | Initial-SDI vs max-SDI sanity check (informational message only); no simulation effect. |
| `ksstag.f` | 96 | N/A | **N/A** | SSTAGE keyword toggle (turns on stage classification — output only). |
| `sdefln.f` | 79 | N/A | **N/A** | BFFDLN/MCFDLN keyword (defect-line input). Pyfvs has no keyword infrastructure. |
| `pctile.f` | 75 | `stand_metrics.py::calculate_pbal_all` | **PORTED** | Stable desc-sort with cumulative BA-above. Single-tree calculate_pbal also fixed 2026-04-15 to use same path. |
| `isstag.f` | 53 | N/A | **N/A** | SSTAGE init helper. |

## CORE_REGEN (2 files, 649 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `regent.f` | 588 | `stand.py::_grow_establishment_cycle + establishment.py` | **PARTIAL** | LESTB + non-LESTB branches. LESTB (establishment) ported. Mid-cycle regen (post-est sprouts) likely missing. |
| `rcon.f` | 61 | N/A | **N/A** | Dispatcher calling DGCONS/HTCONS/REGCON/MORCON/CRCONS to pre-compute site-constant coefficients. Pyfvs does equivalent via module-level JSON load + SNDiameterGrowthModel CONSPP. |

## CORE_ESTAB (22 files, 5437 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `essprt.f` | 1482 | N/A | **MISSING** | Stump-sprouting computations per species/parent-DBH. Not triggered for planted-stand (no stumps). Needed for NATURAL regen or post-cut sprout simulation. |
| `estab.f` | 817 | `establishment.py::compute_establishment_tree_state + stand.py` | **PARTIAL** | Main establishment driver. BACHLO variation ported 2026-04-14. Verify HHTMAX, sprouting (calls ESSPRT), plant codes. |
| `esin.f` | 748 | N/A | **N/A** | ESTAB option/keyword processor (PLANT, NATURAL, RSTKGOAL, etc.). Pyfvs has no keyword infrastructure; establishment is driven by Stand.initialize_planted or FIA import. |
| `esuckr.f` | 382 | N/A | **MISSING** | Sprout/sucker establishment (clonal regen). Not invoked in planted-stand parity tests. |
| `esnutr.f` | 350 | N/A | **N/A** | Extension coupling regen model with nutrients/soil. Pyfvs doesn't model nutrients. |
| `esplt2.f` | 290 | N/A | **N/A** | Plot-specific variable translation (INITRE-call time). Fortran multi-plot infrastructure; pyfvs has single-stand model. |
| `esaddt.f` | 202 | N/A | **N/A** | Add trees from external file/DB. Pyfvs uses in-memory Tree objects and FIA import hook. |
| `esfltr.f` | 195 | N/A | **N/A** | Flag "best" inventory trees for CALBSTAT calibration output. Informational, no simulation effect. |
| `estump.f` | 115 | N/A | **MISSING** | Stores stump info for subsequent sprouting via ESSPRT. Not triggered for planted-stand. Needed for post-cut sprout simulation. |
| `escprs.f` | 113 | N/A | **N/A** | Establishment tree-list compression (Fortran MAXTRE array management). Pyfvs uses Python lists. |
| `esplt1.f` | 97 | N/A | **N/A** | Plot-specific input pass (INTREE). Multi-plot infrastructure. |
| `esetpr.f` | 94 | N/A | **N/A** | SITEPREP keyword processor (site preparation for regen). Pyfvs has no keyword infrastructure. |
| `esinit.f` | 83 | `(implicit in pyfvs module imports)` | **N/A** | One-time ESTAB init (registers defaults). Pyfvs inits via module load + JSON config. |
| `esgent.f` | 75 | `stand.py::_grow_establishment_cycle` | **PORTED** | Calls REGENT(LESTB=TRUE) to grow regen trees to cycle end + applies HHTMAX. Pyfvs _grow_establishment_cycle encapsulates this behavior. |
| `esout.f` | 72 | N/A | **N/A** | Copies print data to output. No simulation effect. |
| `essubh.f` | 72 | `establishment.py::compute_establishment_height` | **PORTED** | Calls HTCALC for site-curve height. |
| `estime.f` | 63 | N/A | **N/A** | Computes years-since-disturbance for keyword events. Keyword infrastructure. |
| `esrann.f` | 59 | `Python random.Random (via rng)` | **N/A** | ESTAB-specific IMSL-derived uniform RNG. Pyfvs uses Python RNG; distributional equivalence is what matters. |
| `esprep.f` | 45 | N/A | **N/A** | Default site-prep probabilities for keyword. Keyword infrastructure. |
| `esprin.f` | 45 | N/A | **N/A** | Enter site-prep options into activity schedule (keyword output). |
| `esblkd.f` | 20 | `cfg/sn_*.json + establishment.py constants` | **N/A** | BLOCK DATA for ESTAB defaults. Pyfvs reads from JSON/module constants. |
| `esmsgs.f` | 18 | N/A | **N/A** | Error message text for ESTAB keyword errors. |

## CORE_INIT (12 files, 10193 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `initre.f` | 6477 | N/A | **N/A** | 6477 lines — keyword/option processor called from MAIN to initialize a FVS run. Reads input cards, dispatches keyword handlers, initializes all extensions. Pyfvs replaces this with `Stand.initialize_planted()` + `stand.grow()` + YAML/JSON config. |
| `spctrn.f` | 871 | `species.py + fia_integration.py` | **PARTIAL** | Species-code translator: maps unrecognized FVS alpha / FIA / USDA-PLANTS codes to variant species. Pyfvs has species.py enum + fia mapping; verify completeness vs Fortran's ASPT/FIAT tables. |
| `intree.f` | 661 | N/A | **N/A** | Read tree data from input file and initialize tree-record arrays. Pyfvs uses Tree objects with constructors. |
| `grincr.f` | 567 | `stand.py::_grow_single_cycle (implicit)` | **PARTIAL** | Cycle increment driver. OLDFNT carry not yet implemented (assumes constant cycle). |
| `fwinit.f` | 367 | `volume_library.py + taper.py::initialize_tree` | **PARTIAL** | Per-tree volume calculation setup (VOLEQ, DBHOB, HTTOT, merch top, upper-stem heights). Pyfvs has per-tree initialize_tree in taper models. |
| `grinit.f` | 340 | `partly via constants in tree.py / model_base.py` | **PARTIAL** | Initialize global state: BJPHI, BJTHET, DGSD, FINT, default flags. BJPHI/BJTHET now used. |
| `blkdat.f` | 331 | `cfg/sn_*.json + establishment.py constants` | **PARTIAL** | BLOCK DATA for all SN coefficients. Most coefficients ported. HHTMAX, SIZCAP partially. |
| `fvshannbare.f` | 244 | `stand.py::Stand.initialize_planted (bare_ground=True)` | **PORTED** | Bare-ground initialization helper. |
| `spdecd.f` | 128 | N/A | **N/A** | Decode species text-code from KEYWORD input card. Pyfvs uses Python SpeciesCode enum and string keys directly. |
| `sgdecd.f` | 88 | N/A | **N/A** | Decode species-group text-code from KEYWORD input card. Pyfvs uses Python lookups. |
| `setup.f` | 60 | N/A | **N/A** | One-time Fortran program setup (file units, scratch arrays). Pyfvs initializes via module imports. |
| `ffin.f` | 59 | N/A | **N/A** | FERTILIZE keyword handler; fertilizer extension. Pyfvs doesn't model fertilization effects on growth. |

## CORE_TREE_OPS (11 files, 1042 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `tremov.f` | 198 | `harvest.py` | **PARTIAL** | Tree removal (cuts). May need cutkey ported. |
| `triple.f` | 154 | N/A | **N/A** | Record tripling: partition each tree into 3 records with lower/mean/upper growth fractiles. Alternative to per-tree stochastic noise. LTRIP=FALSE default in grinit.f; activated only via DGTRIP keyword. Pyfvs uses AR(1) per-tree noise instead. |
| `tredel.f` | 124 | `stand.py::trees.remove (mortality)` | **PORTED** | Tree deletion. |
| `update.f` | 118 | `tree.py + stand.py::_grow_single_cycle` | **PARTIAL** | Apply growth increments to tree state. Verify scaling/conversion vs Fortran update.f |
| `tvalue.f` | 91 | N/A | **N/A** | Student's-t distribution lookup utility. Used in FVS calibration statistics (CALBSTAT keyword). Not triggered by planted-stand simulation. |
| `mults.f` | 90 | N/A | **MISSING** | User-provided growth multipliers (XDMULT, XHMULT, etc.). pyfvs has no equivalent keyword interface. |
| `reass.f` | 81 | N/A | **N/A** | Realigns IND1/IND/ISCT pointer arrays after record tripling. Fortran array management; pyfvs uses Python lists. |
| `tregro.f` | 61 | `stand.py + tree.py::grow` | **PORTED** | Tree growth driver (subset). |
| `evage.f` | 60 | N/A | **N/A** | Age scheduled events for reoccurrence (EVMON activity schedule). Keyword infrastructure. |
| `resage.f` | 41 | N/A | **N/A** | RESETAGE keyword: resets stand age. Not used in parity tests. |
| `tresor.f` | 24 | N/A | **N/A** | Sort/match tree IDs to internal indices for extension data mapping. Extension infrastructure. |

## CORE_RNG (2 files, 159 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `bachlo.f` | 90 | `Python random.Random.gauss (in _stochastic_multiplier and _grow_establishment_cycle)` | **PORTED** | N(mean, std) via rejection. Pyfvs uses NumPy/random Box-Muller; distributionally equivalent. |
| `rann.f` | 69 | `Python random.Random` | **PORTED** | Uniform [0,1] generator. |

## CORE_DATA_IO (2 files, 1796 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `getstd.f` | 900 | `N/A — pyfvs uses Stand object` | **N/A** | Marshal Fortran arrays from stand record. |
| `putstd.f` | 896 | `N/A — pyfvs uses Stand object` | **N/A** | Marshal Fortran arrays to stand record. |

## CORE_SITE (7 files, 3836 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `fortyp.f` | 1175 | `forest_type.py` | **PARTIAL** | 1175 lines — full forest-type assignment from species mix. |
| `formclas.f` | 887 | N/A | **N/A** | Region-6 (Blue Mountains: Malheur, Ochoco, Umatilla, Wallowa-Whitman) form-class tables. Not applicable to SN variant despite being compiled in SN buildDir. |
| `sitset.f` | 879 | `site_index_params (config) + species.py site curve groups` | **PARTIAL** | 879 lines — site-index transformations between species. PCOM-conditional branches not all ported. |
| `forkod.f` | 610 | `forest_type.py` | **PARTIAL** | Forest type code lookup. |
| `habtyp.f` | 154 | `ecological_unit.py` | **PARTIAL** | Habitat type ↔ ecounit mapping. |
| `hbdecd.f` | 90 | N/A | **N/A** | Decode habitat type text-code from KEYWORD input card. Pyfvs uses ecological_unit strings directly. |
| `formcl.f` | 41 | `taper.py + cfg/sn_*.json FRMCLS` | **PARTIAL** | Vanilla form-class lookup: `FC = FRMCLS(ISPC)`. Pyfvs stores per-species form class in coefficient JSON and reads via taper/volume paths. |

## CORE_CUTS (3 files, 2496 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `cuts.f` | 2048 | `harvest.py::HarvestManager` | **PARTIAL** | 2048 lines — covers thinning, regen cuts, etc. Pyfvs has thin_from_below/above/clear, but not full TARGETBA, BAONLY, ATSDIMX, etc. |
| `cutqfa.f` | 338 | `?` | **MISSING** | Cut by QMD-from-above/below. |
| `cutstk.f` | 110 | `?` | **MISSING** | Stocking-target cut. |

## VOLUME_R8 (12 files, 9261 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `profile.f` | 2297 | `clark_profile.py?` | **PARTIAL** | 2297 lines — Clark profile equation segments. |
| `r8vol2.f` | 2000 | `volume_library.py` | **PARTIAL** | 1999 lines — major R8 volume implementation. |
| `r8vlist.f` | 1031 | `?` | **MISSING** | 1030 lines — R8 species-volume aliases? |
| `profile2.f` | 880 | `?` | **MISSING** | 879 lines — alternate profile. |
| `r8init.f` | 823 | `volume_library.py + cfg/sn_*r8*` | **PARTIAL** | 823 lines — initialize R8 volume coefficients. |
| `r8dib.f` | 605 | `taper.py::ClarkTaperModel.diameter_inside_bark` | **PARTIAL** | DIB at any height. |
| `r8prep.f` | 515 | `taper.py::ClarkTaperModel.initialize_tree + _apply_r8_fcmin_clamp + volume_library.py STUMP_HEIGHT` | **PORTED** | FCMIN clamp ported. STUMP_HEIGHT fixed 2026-04-15 (STMP=0.5 for PROD='02' total cubic, was 1.0). Missing COEFFSO%DIB17 outside-bark update after clamp (line 366) is only used by r9totHt merch-height query, not main volume integration — effectively N/A for SN default VOLEQ path. |
| `r8clkdib.f` | 449 | `taper.py::ClarkTaperModel` | **PARTIAL** | DIB17 calculation. Verify vs r8clkdib.f line-by-line. |
| `segmnt.f` | 287 | `merchandising.py (log-length assignment)` | **PARTIAL** | Splits merchantable stem length into segment lengths per FSH segmentation rules (min/max/trim). Pyfvs merchandising.py has log-length logic; verify segmentation-rule matching. |
| `r8vol.f` | 180 | `volume_library.py` | **PARTIAL** | R8 cubic-foot volume integrator. |
| `r8vol1.f` | 178 | `volume_library.py` | **PARTIAL** | R8 alternate volume. |
| `clkcoef_mod.f` | 16 | `clark_profile.py?` | **PARTIAL** | Clark coefficient module. |

## VOLUME_TAPER (13 files, 2367 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `sf_zero.f` | 1090 | `taper.py (numerical helpers)` | **PARTIAL** | Bounded zero-finder for taper integration / root-finding. Pyfvs uses Python math / scipy equivalents inline where needed; no dedicated port. |
| `sf_2pth.f` | 199 | `clark_profile.py` | **PARTIAL** | 2-point taper at specified heights (JSP/GEOSUB dispatch). Covered by ClarkTaperModel DIB-at-height path. |
| `sf_hs.f` | 196 | `taper.py::ClarkTaperModel.height_at_dib` | **PARTIAL** | Height at which specified DIB occurs (inverse taper). Covered when computing merch lengths. |
| `sf_yhat.f` | 175 | `clark_profile.py` | **PARTIAL** | Clark taper ordinate Y-hat (relative height → DIB fraction). Core predictor inside Clark profile. |
| `sf_3pt.f` | 166 | `taper.py` | **PARTIAL** | 3-point taper. |
| `sf_taper.f` | 102 | `taper.py` | **PARTIAL** | Special-function taper. |
| `sf_2pt.f` | 86 | `taper.py` | **PARTIAL** | 2-point taper integration. |
| `sf_3z.f` | 84 | `clark_profile.py` | **PARTIAL** | 3-zone Clark taper (butt/middle/top zones with different shape). |
| `sf_ds.f` | 64 | `clark_profile.py` | **PARTIAL** | Diameter-series helper for taper evaluation. |
| `sf_dfz.f` | 55 | `clark_profile.py` | **PARTIAL** | DIB-at-Z (relative height) evaluator for Clark profile. |
| `sf_shp.f` | 55 | `clark_profile.py` | **PARTIAL** | Shape-function parameters for Clark taper (RFLW/RHFW/DBTBH). |
| `sf_yhat3.f` | 52 | `clark_profile.py` | **PARTIAL** | 3-zone variant of sf_yhat ordinate. |
| `sf_corr.f` | 43 | `clark_profile.py` | **PARTIAL** | Correlation utility (COR_C2/COR_OT/COR_BH/COR_WS internal helpers). |

## VOLUME_INFRA (38 files, 15701 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `voleqdef.f` | 2830 | `cfg/*volume*.json + volume_library.py` | **PARTIAL** | Default volume-equation code mappings per region/forest/species (R1-R10 + FIA). Pyfvs encodes the SN-relevant subset in volume JSON config. Most entries are for non-SN regions (R1, R3, R5, R6). |
| `volumelibrary.f` | 1351 | `volume_library.py::VolumeLibrary` | **PARTIAL** | Main NVEL (National Volume Estimator Library) entry point — dispatches to region-specific equations by VOLEQ code prefix. Pyfvs covers the R8 path; other region entry points absent. |
| `blmvol.f` | 1133 | N/A | **N/A** | BLM (Bureau of Land Management) volume equations for western PNW forests. Not used by SN. |
| `volinit.f` | 1060 | `volume_library.py::initialize_tree` | **PARTIAL** | Per-tree volume initialization wrapping CALCVOL dispatch. Pyfvs ClarkTaperModel.initialize_tree covers the R8 path. |
| `vollibcs.f` | 809 | `volume_library.py` | **PARTIAL** | C#/.NET DLL entry point for volume library. Pyfvs volume_library.py is native Python, no DLL bridge. |
| `fvsvol.f` | 666 | `volume_library.py::compute_volumes (called from stand_metrics)` | **PARTIAL** | FVS-specific volume orchestrator (called per cycle). Pyfvs computes via stand_metrics + volume_library on demand. |
| `cratet.f` | 631 | `tree.py::Tree.__init__ (height dubbing)` | **PARTIAL** | "Create Tree" — dubs missing heights via HTDBH, DGs, initial DBH calibration. Pyfvs Tree constructor + FIA import hook handle this; verify calibration branches. |
| `vollibfia.f` | 545 | N/A | **N/A** | FIA-specific NVEL volume entry (region/forest/species → FIA-standard equation). Pyfvs uses R8CF directly; FIA-compat shim not ported. |
| `vols.f` | 507 | `stand_metrics.py::calculate_volumes (via volume_library)` | **PARTIAL** | Stand-level volume aggregator — loops trees calling CFVOL/BFVOL. Pyfvs aggregates in stand_metrics/stand_output. |
| `pnwtarif.f` | 476 | N/A | **N/A** | PNW Tarif volume equations (FIA Pacific Northwest). Not used by SN. |
| `twigcf.f` | 458 | N/A | **N/A** | Cubic-foot twig (branch) volume beyond merch top. Refinement pyfvs doesn't compute. |
| `volinit2.f` | 413 | `volume_library.py::initialize_tree` | **PARTIAL** | Variant of VOLINIT that accepts user-specified merch rules. Pyfvs taper model accepts form_class override analogously. |
| `honer.f` | 401 | N/A | **N/A** | Honer (Canadian) volume equation. Not used by SN. |
| `ht2topd.f` | 367 | `taper.py::ClarkTaperModel.height_at_dib` | **PARTIAL** | Height-to-top-diameter inverse taper lookup. Covered by ClarkTaperModel. |
| `nbolt.f` | 364 | N/A | **N/A** | Number of merchantable bolts (short logs). Merchandising refinement. |
| `blmtap.f` | 316 | N/A | **N/A** | BLM taper (paired with blmvol.f). Not used by SN. |
| `twigbf.f` | 307 | N/A | **N/A** | Board-foot twig volume beyond merch top. Same as twigcf but BF. |
| `volapss.f` | 276 | N/A | **N/A** | Volume API pass-through wrapper. pyfvs exposes Python-native API. |
| `scrib.f` | 263 | N/A | **N/A** | Scribner board-foot volume table. Pyfvs doesn't compute Scribner. |
| `getvoleq.f` | 257 | `variant_registry.py::get_volume_equation_code` | **PARTIAL** | Look up default VOLEQ code for region/forest/species. Pyfvs variant-dispatch handles SN R8CF selection. |
| `volkey.f` | 247 | N/A | **N/A** | VOLUME keyword processor. Pyfvs has no keyword infrastructure. |
| `cfvol.f` | 244 | `volume_library.py::compute_cubic_volume` | **PARTIAL** | Cubic-foot volume per tree (uses VMAX cap + TKILL flag). Pyfvs computes cubic volume via taper integration. |
| `comcup.f` | 208 | N/A | **N/A** | "Common cup" — stump cubic volume lookup. Pyfvs integrates from stump height in taper. |
| `vollib09.f` | 203 | N/A | **N/A** | Legacy 2009 volume library dispatcher. Superseded by volumelibrary.f in Fortran; pyfvs doesn't need. |
| `logs.f` | 181 | N/A | **N/A** | Log cutting/length calculations (merchandising). Pyfvs merchandising.py has equivalent. |
| `pmtprofile.f` | 177 | N/A | **N/A** | Profile-model tutorial version of taper. Documentation/example code. |
| `dvest.f` | 151 | N/A | **N/A** | Division-based volume estimation (legacy). |
| `cftopk.f` | 136 | N/A | **N/A** | Cubic-foot volume to a specified top DIB (merchandising). |
| `bfvol.f` | 132 | N/A | **N/A** | Board-foot volume shim. |
| `numlog.f` | 101 | N/A | **N/A** | Number-of-logs merchandising. |
| `doyal78.f` | 90 | N/A | **N/A** | Doyle board-foot form-class 78 equation. |
| `intl78.f` | 89 | N/A | **N/A** | International 1/4" board-foot form-class 78 equation. |
| `comp.f` | 81 | N/A | **N/A** | Generic attribute comparator utility. |
| `bftopk.f` | 70 | N/A | **N/A** | Board-foot volume to specified top DIB. |
| `volumelib.f` | 69 | N/A | **N/A** | Legacy volume library stub (superseded by volumelibrary.f). |
| `cubrds.f` | 58 | N/A | **N/A** | Cubic-foot rounding/defect adjustment. |
| `dunn.f` | 22 | N/A | **N/A** | Dunn's test utility (statistical helper). |
| `volinput_mod.f` | 12 | N/A | **N/A** | Empty module stub. |

## CORE_BIOMASS (9 files, 3917 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `nsvb.f` | 1511 | `?` | **MISSING** | 1510 lines — NSVB national biomass (NEW). |
| `calcbiomass.f` | 557 | `?` | **MISSING** | Calculate biomass per tree. |
| `calcdia.f` | 552 | N/A | **N/A** | Diameter calculation helpers exported from NVEL VOLLIB.dll. Internal to volume library dispatch. Pyfvs computes directly in ClarkTaperModel. |
| `setcubicdflts.f` | 511 | `?` | **MISSING** | Set cubic-foot merch defaults (stump, min top DIB, min BF top). Pyfvs has defaults in taper/merchandising; verify vs Fortran per-region defaults. |
| `crzbiomass.f` | 378 | `?` | **MISSING** | Crown biomass (branches/foliage) per species. Pyfvs doesn't compute crown biomass separately. |
| `jenkins.f` | 174 | `?` | **MISSING** | Jenkins (2003) aboveground biomass allometric equations by species group. Pyfvs doesn't compute biomass. |
| `biomassformula.f` | 129 | `?` | **MISSING** | Biomass calculation formula dispatcher. Pyfvs doesn't compute biomass. |
| `nvbeqdef.f` | 72 | N/A | **N/A** | NVB (National Volume/Biomass) equation default lookup (SPCD → VOLEQ). Pyfvs doesn't use NVB. |
| `nvb_region_check.f` | 33 | N/A | **N/A** | NVB region validation check. N/A without NVB. |

## CONFIG_FIA (10 files, 5024 LOC)

| Fortran | LOC | pyfvs | Status | Notes |
|---------|-----|-------|--------|-------|
| `f_ingy.f` | 1415 | N/A | **N/A** | Clark profile SHP_C2/COR_C2/VAR_C2/BRK_UP* for COOP #2 INGY (Intermountain/east-side PNW): Douglas-fir, ponderosa pine, grand fir, western larch, Engelmann spruce. Not used by SN. |
| `f_west.f` | 1040 | N/A | **N/A** | Clark profile SHP_W3/SHP_W4 for western US species groups. Not used by SN. |
| `f_other.f` | 905 | N/A | **N/A** | Clark profile BRK_OT/SHP_OT/COR_OT/VAR_OT + SHP_BH for R2 species (Black Hills, San Juan, Dixie NFs; lodgepole, DF, WF). Not used by SN. |
| `f_alaska.f` | 514 | N/A | **N/A** | Clark profile SHP_AK for Alaska species. Not used by SN. |
| `fia_rm.f` | 294 | N/A | **N/A** | FIA Rocky Mountain volume/biomass equations. Not used by SN. |
| `fia_nw.f` | 281 | N/A | **N/A** | FIA Northwest volume/biomass equations. Not used by SN. |
| `fia_pi.f` | 162 | N/A | **N/A** | FIA Pacific Islands ASNER_AGT biomass. Not used by SN. |
| `fia_nc.f` | 148 | N/A | **N/A** | FIA North Central volume/biomass. Not used by SN. |
| `fia_ne.f` | 148 | N/A | **N/A** | FIA Northeast volume/biomass. Not used by SN. |
| `fia_se.f` | 117 | `volume_library.py (alternate path, not default)` | **PARTIAL** | FIA Southeast volume/biomass equation — 30 species coefficient tables (LP, SP, SU, YP, WO, RM, BY, etc.). Pyfvs default uses R8CF Clark profile; FIA_SE is an alternate VOLEQ path not currently dispatched. Optional for future FIA-compat. |

## Skipped categories

Files in these categories are intentionally not ported (FVS infrastructure, extensions, or unused regions for SN). Listed for completeness.

| Category | Files | LOC | Reason |
|----------|-------|-----|--------|
| SKIP_DAMAGE | 3 | 168 | Damage-code processing (storms, etc.) |
| SKIP_DB | 5 | 181 | Database utilities |
| SKIP_DBS | 49 | 11662 | Database integration (FVS reads/writes SQLite) |
| SKIP_DRIVER | 9 | 1425 | FVS main driver, command-line entry |
| SKIP_ECON | 11 | 3155 | Economic-output extension |
| SKIP_EVAL | 12 | 3220 | Event-evaluation language for keywords |
| SKIP_EXT | 14 | 1930 | Other extensions (ORGANON, fertilizer, prescribed fire, etc.) |
| SKIP_FFE | 65 | 25442 | Fire and Fuels Extension — separate ecosystem |
| SKIP_FIRE_INTERFACE | 6 | 1215 | Fire behavior interfaces (BehavePlus, etc.) |
| SKIP_IO | 19 | 2115 | File I/O, character handling |
| SKIP_KEYWORDS | 7 | 2247 | KEYWORD-file parsing (pyfvs uses YAML/JSON config) |
| SKIP_LB | 11 | 952 | Linked-base memory management (Fortran data structure) |
| SKIP_OPS | 20 | 2677 | Operations cycle linked-list manager (Fortran data structure) |
| SKIP_REPORT | 9 | 1813 | Report headers, summary tables (pyfvs has Python equivalents) |
| SKIP_SVS | 32 | 6671 | Stand Visualization System |
| SKIP_UTIL | 30 | 6155 | Misc Fortran utilities (sorts, debug, errors) |
| SKIP_VARGET | 4 | 525 | COMMON-block variable get/put |
| SKIP_VOL_LEGACY | 2 | 468 | Legacy volume code |
| SKIP_VOL_OTHER_REGION | 29 | 12566 | Volume libraries for non-Region-8 (Western, Lake States, etc.) |

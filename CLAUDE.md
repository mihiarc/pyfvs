# CLAUDE.md

## Project Overview

Python implementation of the Forest Vegetation Simulator (FVS) supporting 7 regional variants for simulating forest growth and yield across the US. ~24,000 LOC, object-oriented with modular growth models.

## Key Commands

```bash
uv pip install -e .                    # Install dev mode
uv run pytest                          # All tests (~1000)
uv run pytest tests/test_tree.py -v    # Specific test file
uv run pytest -m "not native"          # Exclude native FVS tests
uv run black src/pyfvs tests           # Format code
uv run python -m pyfvs.main            # Example simulation
```

## Architecture

```
Stand.initialize_planted(tpa, si, species, variant) -> Tree objects -> grow() -> apply_mortality()
```

**Stand composition** (stand.py delegates to):
- `StandMetricsCalculator` (stand_metrics.py) - CCF, QMD, SDI, BA, top height
- `MortalityModel` (mortality.py) - background + density-dependent
- `HarvestManager` (harvest.py) - thinning operations
- `CompetitionCalculator` (competition.py) - PBAL, rank, relative height
- `StandOutputGenerator` (stand_output.py) - yield tables, exports

**Growth model transition** (tree.py):
- DBH < 1.0": small-tree only (height-driven)
- 1.0" <= DBH <= 3.0": weighted blend
- DBH > 3.0": large-tree only (diameter-driven)

**Key modules**: model_base.py (ParameterizedModel ABC), growth_parameters.py (GrowthParameters dataclass), species.py (SpeciesCode enum), config_loader.py (JSON/YAML with caching), taper.py + merchandising.py (NVEL taper models)

**Variant-specific diameter growth**: ls_diameter_growth.py, pn_diameter_growth.py, wc_diameter_growth.py, ne_diameter_growth.py, cs_diameter_growth.py, op_diameter_growth.py

**Variant-specific models** dispatched via factory functions: `create_bark_ratio_model()`, `create_crown_ratio_model()`, `create_mortality_model()`, `create_taper_model()`

**Config**: `src/pyfvs/cfg/` with variant subdirectories (sn/, ls/, pn/, wc/, ne/, cs/, op/)

**Native FVS** (optional): `pyfvs.native` subpackage — ctypes bindings to USDA Fortran library. Lazy imports, never fails when absent. `NativeStand` mirrors `Stand` API.

## Supported Variants

| Variant | Region | Species | Default | Cycle | DDS Equation |
|---------|--------|---------|---------|-------|--------------|
| **SN** | Southern US | 90 | LP | 5yr | ln(DDS) with RELHT + ecounit |
| **LS** | Lake States | 67 | RN | 10yr | linear DDS with RELDBH |
| **PN** | PNW Coast | 39 | DF | 10yr | ln(DDS) with topo effects |
| **WC** | West Cascades | 37 | DF | 10yr | ln(DDS) with topo effects (shares PN code) |
| **NE** | Northeast | 108 | RM | 10yr | BA growth = B1*SI*(1-exp(-B2*DBH)) |
| **CS** | Central States | 96 | WO | 10yr | ln(DDS) with RELDBH (shares LS structure) |
| **OP** | ORGANON PNW | 18 | DF | 5yr | ln(DG) direct diameter growth |
| **WS** | Western Sierra | 43 | PP | 10yr | ln(DDS) with topo effects (14 eq sets) |
| **CA** | Inland California | 49 | PP | 10yr | ln(DDS) with topo effects (13 eq sets) |
| **OC** | Southwest Oregon | 33 | DF | 5yr | ln(DDS) with topo effects (13 eq sets) — coefficients are 10yr, runtime applies -ln(2) conversion (except tanoak) |

## API Patterns

```python
from pyfvs import Stand, GrowthParameters

# Basic usage (stochastic by default, non-reproducible)
stand = Stand.initialize_planted(500, 70, 'LP', variant='SN', ecounit='M231')
stand.grow(50)
metrics = stand.get_metrics()  # keys: tpa, basal_area, qmd, volume, top_height

# Reproducible stochastic run
stand = Stand.initialize_planted(500, 70, 'LP', random_seed=42)

# Deterministic mode (Baskerville correction, no randomness)
stand = Stand.initialize_planted(500, 70, 'LP', stochastic=False)

# Thinning
stand.thin_from_below(target_tpa=200)

# GrowthParameters
params = GrowthParameters.from_stand(stand, target_tree_index=0)
tree = stand.trees[0]
tree.grow(params)  # uses time_step= kwarg (not cycle_length=)

# Native FVS (optional)
from pyfvs.native import NativeStand, fvs_library_available
if fvs_library_available('SN'):
    with NativeStand(variant='SN') as ns:
        ns.initialize_planted(500, 70, 'LP')
        ns.grow(50)
        native_metrics = ns.get_metrics()  # same keys as Stand
```

## Key Gotchas

- `get_metrics()` returns `basal_area` (not `ba`), `tpa` (not `trees_per_acre`), `volume` (not `total_cubic_volume`)
- `Tree()` requires `variant='LS'` for LS species like RN, JP, SM
- `Tree.grow()` uses `time_step=` (not `cycle_length=`)
- **Stochastic is default**: `Stand` uses `stochastic=True` by default. Pass `random_seed=N` for reproducibility or `stochastic=False` for deterministic mode.
- Stochastic applies to SN, LS, PN, WC, CS, WS, CA, OC diameter growth. NE and OP are unaffected (different model forms).
- Factory functions use `create_*_diameter_growth_model()` naming (no `get_*` aliases)
- SN ecounit effects are large: M231 adds +0.790 to ln(DDS), 232 (base) adds 0.0
- FVS calibrated for 5yr cycles; `stand.grow()` auto-subdivides longer periods
- DDS applies to inside-bark diameter (bark ratio conversion in tree.py)
- PN/WC share models; WC/OP dispatch to PN bark ratio/crown ratio factories
- Native FVS: NUMCYCLE must be inline (cols 11-20), NOT on supplemental record
- Native FVS: GCC hidden string lengths appended at END of ctypes arg list

## Known Issues

1. Small trees don't respond to competition until transitioning to large-tree model
2. CA/OC variants fall back to SN models for bark/crown/mortality (DG coefficients are variant-specific)
3. Flewelling inland species (JSP 11-21) not yet implemented
4. Fort Bragg special equations (IFOR=20) not implemented

## Adding New Variants

1. Create `cfg/<variant>/` with coefficient JSON + species YAML files
2. Add to `SUPPORTED_VARIANTS` in config_loader.py
3. Add growth method to tree.py (`_grow_large_tree_<variant>()`)
4. Add to height_diameter.py `VARIANT_COEFFICIENT_FILES`
5. Add bark ratio/crown ratio/mortality models + factory dispatch
6. Add SDI maximums to stand_metrics.py
7. Add volume coefficients to volume_library.py

## Testing

- Unit tests in `tests/` for each module
- Shared fixtures in `tests/conftest.py` (30+ fixtures: trees, stands, parameters)
- Native FVS tests: `tests/test_native.py` (skip gracefully when library absent)
- Test outputs saved to `test_output/`

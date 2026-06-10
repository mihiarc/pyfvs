# API Reference

This section provides detailed documentation for the PyFVS Python API.

## Core Classes

The primary interface for PyFVS simulations:

| Class | Description |
|-------|-------------|
| [`Stand`](stand.md) | Forest stand management - initialization, growth, harvest operations |
| [`Tree`](tree.md) | Individual tree with growth models and attributes |
| [`SimulationEngine`](simulation-engine.md) | High-level simulation orchestration and batch processing |

## Quick Reference

### Stand Initialization

```python
from pyfvs import Stand

# Planted stand (most common)
stand = Stand.initialize_planted(
    trees_per_acre=500,
    site_index=70,
    species='LP',
    ecounit='M231'
)

# Build a stand from explicit Tree objects
from pyfvs import Tree

trees = [Tree(dbh=6.0, height=45.0, species='LP', age=10)]
stand = Stand(trees=trees, site_index=70, species='LP')
```

### Growth Simulation

```python
# Grow for 25 years
stand.grow(years=25)

# Periods longer than the variant's base cycle (5 yr for SN/OP, 10 yr otherwise)
# are automatically subdivided into base-cycle sub-cycles
stand.grow(years=30)
```

### Harvest Operations

```python
# Thin from below to target TPA
stand.thin_from_below(target_tpa=200)

# Thin from above
stand.thin_from_above(target_tpa=300)

# Selection harvest to target basal area
stand.selection_harvest(target_basal_area=80)
```

### Output Methods

```python
# Get current metrics
metrics = stand.get_metrics()

# Get yield table (growth history) as a DataFrame
yield_table = stand.get_yield_table_dataframe(years=50, period_length=5)

# Get individual tree data as a DataFrame
tree_list = stand.get_tree_list_dataframe()
```

## Return Value Schema

### Stand Metrics Dictionary

The `get_metrics()` method returns:

| Key | Type | Description |
|-----|------|-------------|
| `tpa` | float | Trees per acre |
| `basal_area` | float | Basal area (ft²/acre) |
| `volume` | float | Volume (ft³/acre) |
| `qmd` | float | Quadratic mean diameter (inches) |
| `top_height` | float | Top height / dominant height (feet) |
| `ccf` | float | Crown competition factor |
| `sdi` | float | Stand density index |

### Yield Table DataFrame

The `get_yield_table_dataframe()` method returns a pandas DataFrame with
FVS_Summary-style columns (one row per period):

| Column | Description |
|--------|-------------|
| `Year` | Calendar year of projection |
| `Age` | Stand age (years) |
| `TPA` | Trees per acre |
| `BA` | Basal area (ft²/acre) |
| `SDI` | Stand density index |
| `CCF` | Crown competition factor |
| `TopHt` | Dominant height (feet) |
| `QMD` | Quadratic mean diameter (inches) |
| `TCuFt` | Total cubic volume (ft³/acre) |
| `MCuFt` | Merchantable cubic volume (ft³/acre) |
| `BdFt` | Board-foot volume (Doyle) |
| `Mort` | Mortality (ft³/acre/year) |

Removal and after-thin columns (`RTpa`, `RTCuFt`, `AThinBA`, …) are also included.

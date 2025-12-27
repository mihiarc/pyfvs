# Stand

The `Stand` class is the primary interface for forest stand simulation in PyFVS. It manages a collection of trees and provides methods for growth simulation, harvest operations, and metrics calculation.

## Overview

A stand represents a forest area with trees of one or more species. The `Stand` class handles:

- **Initialization**: Create planted stands or build custom stands
- **Growth**: Simulate individual tree growth over time
- **Competition**: Calculate stand-level competition metrics
- **Mortality**: Apply background and density-dependent mortality
- **Harvest**: Perform thinning and harvest operations
- **Output**: Generate yield tables and tree lists

## Quick Start

```python
from pyfvs import Stand

# Create a planted loblolly pine stand
stand = Stand.initialize_planted(
    trees_per_acre=500,
    site_index=70,
    species='LP',
    ecounit='M231'
)

# Simulate 25 years of growth
stand.grow(years=25)

# Get current metrics
metrics = stand.get_metrics()
print(f"Volume: {metrics['volume']:.0f} ft³/acre")
print(f"Basal area: {metrics['basal_area']:.1f} ft²/acre")
```

!!! example "Expected output"
    ```
    Volume: 10621 ft³/acre
    Basal area: 353.9 ft²/acre
    ```

## Creating Stands

### Planted Stand (Recommended)

Use `initialize_planted()` for typical plantation scenarios:

```python
stand = Stand.initialize_planted(
    trees_per_acre=500,    # Initial planting density
    site_index=70,         # Site index (base age 25)
    species='LP',          # Species code
    ecounit='M231',        # Ecological unit (optional)
    initial_age=0          # Starting age (default: 0)
)
```

### Custom Stand

Build a stand with specific trees:

```python
stand = Stand(site_index=70, species='LP')

# Add individual trees
stand.add_tree(dbh=8.0, height=55.0, age=15)
stand.add_tree(dbh=6.5, height=48.0, age=15)
stand.add_tree(dbh=10.2, height=62.0, age=15)
```

## Growth Simulation

### Basic Growth

```python
# Grow for 30 years using default 5-year time steps
stand.grow(years=30)
```

### Custom Time Steps

```python
# Grow with 10-year time steps
yield_data = stand.grow(years=50, time_step=10)
```

!!! note "Time Step Consistency"
    FVS was calibrated for 5-year cycles. PyFVS internally subdivides longer time steps into 5-year sub-cycles to maintain consistent growth dynamics.

## Harvest Operations

### Thin from Below

Remove the smallest trees first:

```python
# Thin to 200 trees per acre
stand.thin_from_below(target_tpa=200)
```

### Thin from Above

Remove the largest trees first (high-grade):

```python
stand.thin_from_above(target_tpa=300)
```

### Thin by DBH Range

Remove trees within a specific diameter range:

```python
# Remove trees between 4" and 8" DBH
stand.thin_by_dbh_range(min_dbh=4.0, max_dbh=8.0, proportion=0.5)
```

### Selection Harvest

Harvest to a target basal area:

```python
# Reduce basal area to 80 ft²/acre
stand.selection_harvest(target_basal_area=80)
```

## Output Methods

### Current Metrics

```python
metrics = stand.get_metrics()
# Returns: {'tpa': 450, 'basal_area': 120.5, 'volume': 3500, ...}
```

### Yield Table

```python
df = stand.get_yield_table_dataframe()
print(df[['age', 'tpa', 'volume', 'basal_area']])
```

### Tree List

```python
tree_df = stand.get_tree_list_dataframe()
print(tree_df[['dbh', 'height', 'volume', 'crown_ratio']])
```

## Class Reference

::: pyfvs.Stand
    options:
      show_root_heading: true
      show_source: false
      members:
        - initialize_planted
        - grow
        - get_metrics
        - get_yield_table_dataframe
        - get_tree_list_dataframe
        - thin_from_below
        - thin_from_above
        - thin_by_dbh_range
        - selection_harvest
        - add_tree
        - age
        - site_index
        - species
        - trees

# Tree

The `Tree` class represents an individual tree with growth models, attributes, and volume calculations. Trees are typically managed through a `Stand`, but can be used directly for individual tree modeling.

## Overview

Each tree maintains:

- **Dimensions**: DBH, height, crown ratio
- **Growth state**: Age, growth model selection
- **Species parameters**: Loaded from configuration files
- **Volume**: Calculated using combined-variable equations

## Tree Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `dbh` | float | Diameter at breast height (inches) |
| `height` | float | Total height (feet) |
| `age` | int | Tree age (years) |
| `crown_ratio` | float | Crown ratio (0-1) |
| `species` | str | Species code (LP, SP, SA, LL) |

## Quick Start

```python
from pyfvs import Tree

# Create a tree
tree = Tree(
    dbh=6.0,
    height=45.0,
    species='LP',
    age=10
)

# Get volume
volume = tree.get_volume()
print(f"Volume: {volume:.2f} ft³")

# Grow one cycle
tree.grow(
    time_step=5,
    site_index=70,
    competition_factor=0.3,
    pbal=50.0
)

print(f"New DBH: {tree.dbh:.2f} inches")
print(f"New height: {tree.height:.1f} feet")
```

!!! example "Expected output"
    ```
    Volume: 4.24 ft³
    New DBH: 7.23 inches
    New height: 56.5 feet
    ```

## Growth Models

PyFVS uses two growth models based on tree size:

### Small-Tree Model (DBH < 1.0")

Height-driven growth using Chapman-Richards equation:

```
height = c1 × SI^c2 × (1 - exp(c3 × age))^(c4 × SI^c5)
```

DBH is derived from the height-diameter relationship.

### Large-Tree Model (DBH > 3.0")

Diameter-driven growth using the DDS (diameter squared increment) equation:

```
ln(DDS) = β₁ + β₂×ln(DBH) + β₃×DBH² + β₄×ln(CR) + β₅×RH + β₆×SI + ...
```

Height growth is calculated from potential height growth modified by crown ratio and relative height.

### Transition Zone (1.0" ≤ DBH ≤ 3.0")

A smooth blend of both models using a smoothstep function prevents discontinuities.

## Volume Calculation

Volume is calculated using combined-variable equations from Amateis & Burkhart (1987):

```python
volume = tree.get_volume()  # Total cubic feet
```

The equation form is:

```
V = a + b × DBH² × H
```

Where coefficients vary by species and have R² > 0.97 against published research.

## Working with Trees

### Direct Tree Creation

```python
from pyfvs import Tree

# Mature tree
tree = Tree(
    dbh=12.0,
    height=75.0,
    species='LP',
    age=25,
    crown_ratio=0.35  # Optional, will be estimated if not provided
)
```

### Growing a Tree

The `grow()` method requires stand-level context:

```python
tree.grow(
    time_step=5,           # Years to grow
    site_index=70,         # Stand site index
    competition_factor=0.3, # Competition metric (0-1)
    pbal=50.0,             # Basal area in larger trees
    relsdi=0.6,            # Relative stand density index
    ecounit='M231',        # Ecological unit
    forest_type='FTYLPN'   # Forest type
)
```

!!! tip "Use Stand for Growth"
    For most applications, use `Stand.grow()` which automatically provides the correct competition metrics to each tree.

### Getting Tree Information

```python
# Volume (cubic feet)
volume = tree.get_volume()

# Basal area (ft² for this tree)
ba = tree.get_basal_area()
```

## Species Codes

| Code | Common Name | Scientific Name |
|------|-------------|-----------------|
| LP | Loblolly Pine | *Pinus taeda* |
| SP | Shortleaf Pine | *Pinus echinata* |
| SA | Slash Pine | *Pinus elliottii* |
| LL | Longleaf Pine | *Pinus palustris* |

## Class Reference

::: pyfvs.Tree
    options:
      show_root_heading: true
      show_source: false
      members:
        - __init__
        - grow
        - get_volume
        - get_basal_area
        - dbh
        - height
        - age
        - crown_ratio
        - species

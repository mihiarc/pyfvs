# Ecological Units

Ecological units (ecounits) modify growth rates based on geographic region. This accounts for climate, soil, and other environmental differences across the landscape.

!!! note "Southern variant feature"
    Ecological units are specific to the **Southern (`SN`)** variant. Pass
    `ecounit=` to `Stand.initialize_planted()` (other variants ignore it), and
    note that [`SimulationEngine`](../api/simulation-engine.md) does not expose
    this argument — use `Stand` directly.

## Overview

The FVS Southern variant uses ecological province codes to adjust diameter growth. Province 232 (Georgia Piedmont) is the baseline for loblolly pine.

## Available Ecounits

| Code | Region | Effect on Diameter Growth |
|------|--------|---------------------------|
| 232 | Georgia (baseline) | 1.0x |
| 231L | Lowland Coastal Plain | ~1.3x |
| 255 | Prairie Parkland | ~1.3x |
| M231 | Southern Appalachian | ~2.2x |

## Using Ecounits

### At Stand Initialization

```python
from pyfvs import Stand

# Use M231 for higher growth rates
stand = Stand.initialize_planted(
    trees_per_acre=500,
    site_index=70,
    species='LP',
    ecounit='M231'
)
```

### Effect on Growth

The ecounit effect is applied to the diameter growth equation:

```
ln(DDS) = base_terms + ecounit_coefficient
```

For M231, the coefficient is +0.790, which translates to approximately 2.2x diameter growth.

## Choosing an Ecounit

### For Validation Against Published Yield Tables

Use M231 to achieve growth rates similar to published yield tables:

```python
# This configuration produces yields comparable to
# traditional yield tables like Schumacher & Coile (1960)
stand = Stand.initialize_planted(
    trees_per_acre=500,
    site_index=70,
    species='LP',
    ecounit='M231'
)
```

### For Regional Accuracy

Match the ecounit to your geographic area:

- **Piedmont Georgia/Carolinas**: 232 (baseline)
- **Coastal Plain lowlands**: 231L
- **Mountain regions**: M231
- **Western edge of range**: 255

## Yield Comparison by Ecounit

Simulation results at age 25 for loblolly pine, SI=55, 500 TPA:

| Ecounit | Final Volume (ft³/acre) | Relative Yield |
|---------|-------------------------|----------------|
| 232 | ~2,500 | 1.0x |
| 231L | ~3,700 | 1.5x |
| 255 | ~3,900 | 1.6x |
| M231 | ~7,800 | 3.1x |

## Technical Details

### How Ecounit Effects Work

The ecounit coefficient is added to the natural log of diameter squared increment (DDS):

```
ln(DDS) = INTERC + LDBH×ln(DBH) + ... + ECOUNIT_COEF
```

This multiplicative effect compounds over time, leading to large differences in long-term yields.

### Small-Tree vs Large-Tree Models

Ecounit effects apply to diameter growth in both models:

- **Small trees**: Applied to the DBH increment derived from height growth
- **Large trees**: Applied directly to the DDS equation

### Coefficients by Species

| Species | Province | Coefficient |
|---------|----------|-------------|
| LP | M231 | +0.790 |
| LP | 231L | +0.256 |
| LP | 255 | +0.275 |
| LP | 232 | 0.0 (base) |

Other species have similar patterns but different specific coefficients.

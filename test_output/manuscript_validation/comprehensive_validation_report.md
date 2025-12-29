# FVS-Python Manuscript Validation Report

## Overview

This report validates fvs-python yield predictions against the
timber asset account manuscript data.

### Source
- **Manuscript**: 'Toward a timber asset account for the United States'
- **Authors**: Bruck, Mihiar, Mei, Brandeis, Chambers, Hass, Wentland, Warziniack
- **FVS Version**: FS2025.1

## Species Simulated

- **LP** (Loblolly Pine): SI=55 (North), SI=65 (South)
- **SA** (Slash Pine): SI=55 (North), SI=65 (South)
- **SP** (Shortleaf Pine): SI=55 (North), SI=65 (South)
- **LL** (Longleaf Pine): SI=55 (North), SI=65 (South)

## Summary Statistics

### Yields at Age 25

| Species   | Region   |   Site_Index |   Volume_Tons |   Mean_DBH |   TPA |
|:----------|:---------|-------------:|--------------:|-----------:|------:|
| LP        | North    |           55 |          76.1 |       7.77 |   468 |
| LP        | South    |           65 |          98.3 |       8.25 |   462 |
| SA        | North    |           55 |          63   |       6.72 |   464 |
| SA        | South    |           65 |          83.9 |       7.29 |   453 |
| SP        | North    |           55 |          72.2 |       7.17 |   454 |
| SP        | South    |           65 |          95.3 |       7.65 |   454 |
| LL        | North    |           55 |          54.6 |       6.36 |   457 |
| LL        | South    |           65 |          73.7 |       6.91 |   451 |

### Files Generated

- `full_yield_simulation.csv`: Complete simulation results
- `yield_summary_by_species_age.csv`: Summary by species and age
- `table1_full_comparison.csv`: Table 1 validation details
- `lev_mai_comparison.csv`: LEV vs MAI rotation ages

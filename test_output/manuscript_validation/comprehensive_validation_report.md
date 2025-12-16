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
| LP        | North    |           55 |          36.6 |       6.4  |   452 |
| LP        | South    |           65 |          49   |       6.81 |   449 |
| SA        | North    |           55 |          26.1 |       5.42 |   462 |
| SA        | South    |           65 |          36.5 |       5.86 |   463 |
| SP        | North    |           55 |          30.9 |       5.92 |   452 |
| SP        | South    |           65 |          42.9 |       6.38 |   451 |
| LL        | North    |           55 |          22.2 |       5.06 |   459 |
| LL        | South    |           65 |          31.2 |       5.46 |   461 |

### Files Generated

- `full_yield_simulation.csv`: Complete simulation results
- `yield_summary_by_species_age.csv`: Summary by species and age
- `table1_full_comparison.csv`: Table 1 validation details
- `lev_mai_comparison.csv`: LEV vs MAI rotation ages

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
| LP        | North    |           55 |           3.1 |       2.86 |   453 |
| LP        | South    |           65 |           5.2 |       3.29 |   457 |
| SA        | North    |           55 |          13.2 |       4.4  |   464 |
| SA        | South    |           65 |          20.7 |       5.09 |   456 |
| SP        | North    |           55 |           7.7 |       3.62 |   462 |
| SP        | South    |           65 |          14   |       4.38 |   453 |
| LL        | North    |           55 |          12.1 |       4.2  |   460 |
| LL        | South    |           65 |          17.3 |       4.7  |   447 |

### Files Generated

- `full_yield_simulation.csv`: Complete simulation results
- `yield_summary_by_species_age.csv`: Summary by species and age
- `table1_full_comparison.csv`: Table 1 validation details
- `lev_mai_comparison.csv`: LEV vs MAI rotation ages

# FVS-Python Validation

This directory contains the validation infrastructure for comparing FVS-Python
predictions against the official USDA Forest Service FVS Southern (SN) variant.

## Overview

FVS-Python is a pure Python reimplementation of the FVS-SN growth equations.
Validation confirms functional equivalence with the original Fortran implementation.

## Directory Structure

```
validation/
├── README.md                # This file
├── fvs_version.txt          # Reference FVS version info
├── run_validation.py        # Main validation runner
│
├── reference_data/          # FVS-generated reference outputs
│   ├── LP_SI70_T500/        # Loblolly Pine, SI=70, TPA=500
│   │   ├── summary.csv      # Parsed summary table
│   │   └── treelist.csv     # Parsed tree lists
│   └── ...
│
├── test_cases/              # Test case definitions
│   ├── component_tests.yaml # Height-diameter, bark ratio, etc.
│   ├── single_tree_tests.yaml
│   └── stand_tests.yaml     # Full stand simulations
│
├── scripts/                 # Utility scripts
│   ├── generate_test_data.py
│   ├── compare_results.py
│   └── visualize.py
│
├── results/                 # Validation run outputs
│   ├── figures/             # Comparison plots
│   └── metrics.json         # Pass/fail metrics
│
└── notebooks/               # Analysis notebooks
    └── validation_analysis.ipynb
```

## Acceptance Criteria

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Diameter growth (5-yr) | ±5% or ±0.1 inches | Primary driver of FVS predictions |
| Height growth (5-yr) | ±5% or ±0.5 feet | Secondary, derived from diameter |
| Basal area (stand) | ±3% | Cumulative metric, tighter tolerance |
| Trees per acre | ±2% | Integer counts, should match closely |
| Volume | ±10% | Compounds diameter/height errors |

## Running Validation

### Quick Start

```bash
# Run full validation suite
uv run python validation/run_validation.py

# Run specific validation level
uv run python validation/run_validation.py --level component
uv run python validation/run_validation.py --level tree
uv run python validation/run_validation.py --level stand

# Run with verbose output
uv run python validation/run_validation.py -v
```

### Via pytest

```bash
# Run validation tests
uv run pytest tests/test_validation.py -v

# Run component model tests only
uv run pytest tests/test_validation.py::TestComponentModels -v
```

## Validation Levels

### Level 1: Component Model Validation
- Height-diameter relationships (Curtis-Arney, Wykoff)
- Bark ratio (Clark 1991)
- Crown ratio (Weibull-based)
- Crown width (forest-grown, open-grown)
- Crown Competition Factor (CCF)

### Level 2: Single-Tree Growth Validation
- Small tree height growth (Chapman-Richards)
- Large tree diameter growth (ln(DDS) equation)
- Growth model transition zone (1-3" DBH)

### Level 3: Stand-Level Validation
- Bare ground planting verification
- Bakuzis Matrix relationships
- Long-term stand dynamics

### Level 4: Sensitivity Analysis
- Parameter sensitivity via Latin Hypercube Sampling
- Edge case testing

## References

1. FVS Model Validation Protocols. USFS Forest Management Service Center. 2009.
   https://www.fs.usda.gov/fmsc/ftp/fvs/docs/steering/FVS_Model_Validation_Protocols.pdf

2. Southern (SN) Variant Overview. FVS Staff. 2008 (revised 2025).
   https://www.fs.usda.gov/sites/default/files/forest-management/fvs-sn-overview.pdf

3. Essential FVS: A User's Guide. Gary E. Dixon.
   https://www.fs.usda.gov/sites/default/files/forest-management/essential-fvs.pdf

---
title: PyFVS - Python Forest Vegetation Simulator
description: Python implementation of the Forest Vegetation Simulator (FVS) for southern pine growth modeling. Simulate growth and yield for loblolly, shortleaf, longleaf, and slash pine.
---

# PyFVS Documentation

[![FIAtools Ecosystem](https://img.shields.io/badge/FIAtools-Ecosystem-2E7D32)](https://fiatools.org)
[![PyPI version](https://img.shields.io/pypi/v/pyfvs-fia?color=006D6D&label=PyPI)](https://pypi.org/project/pyfvs-fia/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-006D6D.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-006D6D.svg)](https://opensource.org/licenses/MIT)

!!! tip "Part of the FIAtools Ecosystem"
    PyFVS is part of the [FIAtools Python ecosystem](https://fiatools.org) - a unified suite of open-source tools for forest inventory analysis. Visit [fiatools.org](https://fiatools.org) to explore all tools.

**PyFVS** is a Python implementation of the Forest Vegetation Simulator (FVS) Southern variant for simulating growth and yield of southern yellow pine species.

## Quick Example

```python
from pyfvs import Stand

# Create a planted loblolly pine stand
stand = Stand.initialize_planted(
    trees_per_acre=500,
    site_index=70,
    species='LP',
    ecounit='M231'  # Mountain province for realistic growth
)

# Simulate 25 years of growth
stand.grow(years=25)

# Get stand metrics
metrics = stand.get_metrics()
print(f"Volume: {metrics['volume']:.0f} ft³/acre")
print(f"Trees/acre: {metrics['tpa']:.0f}")
print(f"Mean DBH: {metrics['qmd']:.1f} inches")
```

## Documentation Overview

<div class="grid cards" markdown>

-   :material-rocket-launch: **[Getting Started](getting-started.md)**

    Installation and your first simulation

-   :material-tree: **[Stand Class](api/stand.md)**

    Manage forest stands and growth cycles

-   :material-pine-tree: **[Tree Class](api/tree.md)**

    Individual tree growth models

-   :material-cog: **[SimulationEngine](api/simulation-engine.md)**

    High-level simulation orchestration

</div>

## Features

| Feature | Description |
|---------|-------------|
| **Individual Tree Models** | Small-tree (height-driven) and large-tree (DBH-driven) growth |
| **Stand Dynamics** | Mortality, competition, crown competition factor |
| **Harvest Operations** | Thin from below/above, selection harvest, clearcut |
| **Volume Calculations** | Combined-variable equations (Amateis & Burkhart 1987) |
| **Ecological Effects** | Regional growth modifiers by ecological province |
| **Multi-format Output** | CSV, JSON, Excel exports with yield tables |

## Supported Species

| Code | Species | Scientific Name |
|------|---------|-----------------|
| LP | Loblolly Pine | *Pinus taeda* |
| SP | Shortleaf Pine | *Pinus echinata* |
| SA | Slash Pine | *Pinus elliottii* |
| LL | Longleaf Pine | *Pinus palustris* |

## Installation

```bash
pip install pyfvs-fia
```

Or with uv:

```bash
uv add pyfvs-fia
```

## The FIAtools Ecosystem

PyFVS is part of the [FIAtools Python ecosystem](https://fiatools.org) - a unified suite of open-source tools for forest inventory analysis:

| Tool | Purpose | Key Features |
|------|---------|--------------|
| [**PyFIA**](https://fiatools.org) | Survey & plot data | DuckDB backend, 10-100x faster than EVALIDator |
| [**GridFIA**](https://fiatools.org) | Spatial raster analysis | 327 species at 30m resolution, Zarr storage |
| [**PyFVS**](https://fiatools.org) | Growth simulation | Chapman-Richards curves, yield projections |
| [**AskFIA**](https://fiatools.org) | AI interface | Natural language queries for forest data |

---

<div align="center">
<strong><a href="https://fiatools.org">fiatools.org</a></strong> - Python Ecosystem for Forest Inventory Analysis
</div>

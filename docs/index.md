---
title: PyFVS - Python Forest Vegetation Simulator
description: Python implementation of the USDA Forest Vegetation Simulator (FVS) supporting 11 regional variants for simulating individual-tree forest growth and yield across the United States.
---

# PyFVS

[![PyPI version](https://img.shields.io/pypi/v/fvs-python?color=006D6D&label=PyPI)](https://pypi.org/project/fvs-python/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-006D6D.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-006D6D.svg)](https://opensource.org/licenses/MIT)

**PyFVS** is a Python implementation of the USDA [Forest Vegetation Simulator](https://www.fs.usda.gov/fmsc/fvs/)
(FVS) — an individual-tree, distance-independent growth and yield model. It
supports **11 regional variants** and **600+ species configurations** for
projecting forest stands across the United States.

```python
from pyfvs import Stand

# A planted loblolly pine stand in the Southern variant
stand = Stand.initialize_planted(
    trees_per_acre=500,
    site_index=70,
    species="LP",
    variant="SN",
)
stand.grow(years=50)

m = stand.get_metrics()
print(f"TPA {m['tpa']:.0f}  QMD {m['qmd']:.1f}\"  BA {m['basal_area']:.0f} ft²  Vol {m['volume']:.0f} ft³/ac")
```

## Where to go next

<div class="grid cards" markdown>

-   :material-rocket-launch: **[Getting Started](getting-started.md)**

    Install PyFVS and run your first simulation.

-   :material-book-open-variant: **[Core Concepts](concepts/index.md)**

    How growth, competition, mortality, and volume are modeled.

-   :material-map: **[Variants](variants/index.md)**

    The 11 supported regions, species, and growth equations.

-   :material-code-tags: **[API Reference](api/index.md)**

    `Stand`, `Tree`, and `SimulationEngine`.

-   :material-tools: **[Cookbook](cookbook.md)**

    Task-oriented recipes: thinning, yield tables, exports.

-   :material-pine-tree: **[Ecological Units](guides/ecological-units.md)**

    Regional growth modifiers (Southern variant).

</div>

## What PyFVS models

| Capability | Description |
|------------|-------------|
| **Individual-tree growth** | Diameter, height, and crown ratio modeled per tree per cycle |
| **Size-dependent models** | Small-tree (height-driven), large-tree (diameter-driven), and a blended transition |
| **Stand dynamics** | Competition (CCF, PBAL, SDI), background and density-dependent mortality |
| **Taper-based volume** | Clark (Eastern) and Flewelling (Western) profiles, NVEL-compatible merchandising |
| **Stand management** | Thin from below/above, thin by DBH range, selection harvest |
| **FIA integration** | Initialize stands directly from Forest Inventory and Analysis plot data |
| **Outputs** | Yield tables, tree lists, CSV/JSON/Excel exports |

## Supported variants

| Variant | Region | Species | Default | Cycle |
|---------|--------|---------|---------|-------|
| **SN** | Southern US | 90 | Loblolly Pine | 5 yr |
| **LS** | Lake States (MI, WI, MN) | 67 | Red Pine | 10 yr |
| **NE** | Northeast (13 states) | 108 | Red Maple | 10 yr |
| **CS** | Central States (IL, IN, IA, MO) | 96 | White Oak | 10 yr |
| **PN** | Pacific NW Coast (WA, OR) | 39 | Douglas-fir | 10 yr |
| **WC** | West Cascades (OR, WA) | 37 | Douglas-fir | 10 yr |
| **EC** | East Cascades (OR, WA) | 32 | Douglas-fir | 10 yr |
| **CA** | Inland California | 50 | Ponderosa Pine | 10 yr |
| **WS** | Western Sierra Nevada | 43 | Ponderosa Pine | 10 yr |
| **OP** | ORGANON Pacific NW | 18 | Douglas-fir | 5 yr |
| **OC** | Southwest Oregon | 50 | Douglas-fir | 5 yr |

See the [Variants reference](variants/index.md) for equation forms and implementation notes.

## Installation

```bash
pip install fvs-python
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add fvs-python
```

PyFVS requires Python 3.12 or newer.

## License

Released under the [MIT License](https://opensource.org/licenses/MIT).
Built by [Chris Mihiar](https://github.com/mihiarc).

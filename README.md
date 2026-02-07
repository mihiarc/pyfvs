<div align="center">
  <h1>pyFVS</h1>

  <p><strong>Forest growth and yield simulation in Python</strong></p>

  <p>
    <a href="https://pypi.org/project/fvs-python/"><img src="https://img.shields.io/pypi/v/fvs-python?color=006D6D&label=PyPI" alt="PyPI"></a>
    <a href="https://mihiarc.github.io/pyfvs/"><img src="https://img.shields.io/badge/docs-GitHub%20Pages-006D6D" alt="Documentation"></a>
    <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-006D6D" alt="License: MIT"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-006D6D" alt="Python 3.12+"></a>
  </p>
</div>

---

A Python implementation of the USDA [Forest Vegetation Simulator](https://www.fs.usda.gov/fmsc/fvs/) (FVS) supporting **10 regional variants**, **taper-based volume calculations**, and **500+ species configurations** for simulating individual tree growth and yield across the United States.

## Features

- **10 Regional Variants** &mdash; Southern, Lake States, Pacific Northwest, West Cascades, Northeast, Central States, ORGANON, and more
- **Taper-Based Volume** &mdash; Clark (Eastern) and Flewelling (Western) taper models with NVEL-compatible merchandising
- **500+ Species Configs** &mdash; Individual species parameters for height-diameter, bark ratio, crown ratio, and growth
- **Individual Tree Growth** &mdash; Diameter, height, crown ratio, and mortality modeled per tree per cycle
- **Stand Management** &mdash; Thinning from below/above, selection harvest, clearcut, and custom prescriptions
- **FIA Integration** &mdash; Initialize stands directly from Forest Inventory and Analysis plot data
- **Export Formats** &mdash; Yield tables, CSV, Excel, and tree lists

## Supported Variants

| Variant | Region | Species | Key Species | Volume Model |
|---------|--------|---------|-------------|--------------|
| **SN** | Southern US | 90 | Loblolly Pine, Longleaf Pine, Slash Pine | Clark (R8) |
| **LS** | Lake States (MI, WI, MN) | 67 | Red Pine, Jack Pine, Sugar Maple | Clark (R9) |
| **NE** | Northeast (13 states) | 108 | Red Maple, Sugar Maple, Northern Red Oak | Clark (R9) |
| **CS** | Central States (IL, IN, IA, MO) | 96 | White Oak, Black Walnut, Yellow-Poplar | Clark (R9) |
| **PN** | Pacific NW Coast (WA, OR) | 39 | Douglas-fir, Western Hemlock, Sitka Spruce | Flewelling |
| **WC** | West Cascades (OR, WA) | 37 | Douglas-fir, Western Hemlock, Western Red Cedar | Flewelling |
| **OP** | ORGANON Pacific NW | 18 | Douglas-fir, Red Alder | Flewelling |
| **CA** | Inland California | &mdash; | White Fir, Ponderosa Pine | &mdash; |
| **OC** | ORGANON SW Oregon | &mdash; | Douglas-fir, Tanoak | &mdash; |
| **WS** | Western Sierra Nevada | &mdash; | White Fir, Giant Sequoia | &mdash; |

Variants marked with &mdash; use default (SN) infrastructure and are pending full implementation.

## Installation

```bash
pip install fvs-python
```

## Quick Start

```python
from pyfvs import Stand

# Southern loblolly pine plantation
stand = Stand.initialize_planted(
    trees_per_acre=500,
    site_index=70,
    species="LP",
    ecounit="M231"
)
stand.grow(years=50)
metrics = stand.get_metrics()
print(f"TPA: {metrics['tpa']:.0f}  QMD: {metrics['qmd']:.1f}\"  "
      f"BA: {metrics['basal_area']:.0f} ft²  Volume: {metrics['volume']:.0f} ft³/ac")
```

### Multi-Variant Examples

```python
from pyfvs import Stand

# Pacific Northwest Douglas-fir (PN variant)
stand = Stand.initialize_planted(400, 120, "DF", variant="PN")
stand.grow(years=50)
# ~333 TPA, 14.5" QMD, 383 BA, 15,029 ft³/ac

# Lake States Red Pine (LS variant)
stand = Stand.initialize_planted(500, 65, "RN", variant="LS")
stand.grow(years=50)
# ~459 TPA, 10.4" QMD, 270 BA, 7,774 ft³/ac

# Northeast Red Maple (NE variant)
stand = Stand.initialize_planted(500, 60, "RM", variant="NE")
stand.grow(years=50)
# ~89 BA, 7.4" QMD

# Central States White Oak (CS variant)
stand = Stand.initialize_planted(500, 65, "WO", variant="CS")
stand.grow(years=50)
# ~283 TPA, 8.7" QMD, 117 BA

# ORGANON Douglas-fir (OP variant - highest yield)
stand = Stand.initialize_planted(400, 120, "DF", variant="OP")
stand.grow(years=50)
# ~323 TPA, 18.5" QMD, 601 BA, 28,395 ft³/ac
```

### Native FVS Integration (New!)

For applications requiring exact parity with official USDA FVS output, use `NativeStand` which calls the compiled Fortran library directly:

```python
from pyfvs.native_stand import NativeStand

# Same API, but uses official USDA Fortran code underneath
stand = NativeStand.initialize_planted(500, site_index=70, species="LP", variant="sn")
stand.grow(years=25)
metrics = stand.get_metrics()
# Results guaranteed to match official FVS output
```

Requires building the FVS shared library. See [docs/native_fvs_integration.md](docs/native_fvs_integration.md) for setup instructions.

**Supported variants:** SN, CA, WS, NC, SO (more can be built from [official FVS source](https://github.com/USDAForestService/ForestVegetationSimulator))

### Thinning

```python
stand = Stand.initialize_planted(500, 70, "LP", ecounit="M231")
stand.grow(years=15)
stand.thin_from_below(target_tpa=200)
stand.grow(years=35)
```

### Yield Tables

```python
from pyfvs import Stand

stand = Stand.initialize_planted(500, 70, "LP", ecounit="M231")
table = stand.grow(years=50, yield_table=True)
print(table)
```

| Age | TPA | QMD | Height | BA | Volume |
|-----|-----|-----|--------|-----|--------|
| 0 | 500 | 0.5 | 1.0 | 0.7 | 0 |
| 10 | 485 | 4.2 | 28.5 | 47 | 892 |
| 20 | 420 | 7.8 | 52.1 | 140 | 3,241 |
| 30 | 310 | 10.4 | 68.3 | 183 | 5,128 |

## Volume System

pyFVS uses a taper-based volume system matching NVEL (National Volume Estimator Library):

| Model | Region | Method |
|-------|--------|--------|
| **Clark** | Eastern (SN, NE, CS, LS) | 3-segment profile with analytic integration |
| **Flewelling** | Western (PN, WC, OP) | 4-segment variable-shape profile |
| **Combined-variable** | Fallback | V = a + b * D²H (Amateis & Burkhart 1987) |

Merchandising supports Scribner Decimal C, International 1/4", and Doyle board-foot rules with per-log bucking.

## Architecture

```
Stand.initialize_planted() --> Tree objects --> grow() cycles --> mortality / harvest
         |                         |
    StandMetrics              GrowthModels
    Competition               HeightDiameter
    Mortality                 CrownRatio
    HarvestManager            BarkRatio
    OutputGenerator           TaperVolume
```

Each `Tree` uses a size-dependent growth model:
- **Small trees** (DBH < 1"): Height-driven growth via Chapman-Richards
- **Transition** (1" - 3"): Weighted blend of small and large tree models
- **Large trees** (DBH > 3"): Diameter-driven growth via variant-specific DDS equations

Variant-specific diameter growth equations:

| Variant | Equation | Variables |
|---------|----------|-----------|
| SN | ln(DDS) | DBH, CR, RELHT, SI, BA, ecounit |
| LS, CS | DDS (linear) | DBH, CR, RELDBH, SI, BA, BAL |
| PN, WC | ln(DDS) | DBH, CR, RELHT, SI, BA, BAL, elevation, slope, aspect |
| NE | BA growth (iterative) | DBH, SI, BAL, CR |
| OP | ln(DG) direct | DBH, CR, SI, BA, BAL |

## Configuration

Species parameters stored in YAML with variant-specific coefficient files in JSON:

```
src/pyfvs/cfg/
  species/*.yaml              # SN species configs (90 species)
  sn_*.json                   # SN variant coefficients
  ls/species/*.yaml           # LS species configs (67 species)
  ls/ls_*.json                # LS variant coefficients
  pn/, wc/, ne/, cs/, op/     # Other variant directories
  taper/                      # Taper model coefficients
    clark_r8_coefficients.json
    clark_r9_coefficients.json
    flewelling_coefficients.json
```

## Testing

```bash
# Run all tests (~1000 tests)
uv run pytest

# Run specific variant tests
uv run pytest tests/test_ls_variant.py
uv run pytest tests/test_pn_variant.py
uv run pytest tests/test_taper.py
```

## References

- [FVS Documentation](https://www.fs.usda.gov/fmsc/fvs/) &mdash; USDA Forest Service
- [FVS Essential Guide (GTR-WO-102)](https://www.fs.usda.gov/research/treesearch/62574) &mdash; Dixon (2023)
- Clark, A. et al. (1991). Stem profile equations for southern tree species. USDA-FS Research Paper SE-282.
- Flewelling, J.W. (1994). Stem form equation development notes. USDA-FS.
- Amateis, R.L. & Burkhart, H.E. (1987). Tree volume and taper. *Forest Science* 33(2).

## Citation

```bibtex
@software{pyfvs2025,
  title = {pyFVS: Python Implementation of the Forest Vegetation Simulator},
  author = {Mihiar, Christopher},
  year = {2025},
  url = {https://github.com/mihiarc/pyfvs}
}
```

## License

MIT

---

<div align="center">
  <sub>Built by <a href="https://github.com/mihiarc">Chris Mihiar</a></sub>
</div>

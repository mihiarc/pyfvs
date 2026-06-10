# Getting Started

This guide installs PyFVS and walks through your first simulation.

## Installation

```bash
pip install fvs-python
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add fvs-python
```

For development from source:

```bash
git clone https://github.com/mihiarc/pyfvs.git
cd pyfvs
uv pip install -e .
```

PyFVS requires Python 3.12 or newer. The import name is `pyfvs` (the
distribution on PyPI is `fvs-python`).

## Your first simulation

A `Stand` is the primary entry point. `initialize_planted()` creates a
bare-ground plantation, `grow()` advances it, and `get_metrics()` returns
stand-level summaries.

```python
from pyfvs import Stand

stand = Stand.initialize_planted(
    trees_per_acre=500,
    site_index=70,
    species="LP",
    variant="SN",
)

stand.grow(years=30)

m = stand.get_metrics()
print(f"Age:        {m['age']} years")
print(f"Trees/acre: {m['tpa']:.0f}")
print(f"Basal area: {m['basal_area']:.1f} ft²/acre")
print(f"QMD:        {m['qmd']:.1f} inches")
print(f"Volume:     {m['volume']:.0f} ft³/acre")
```

### What `get_metrics()` returns

The metrics dictionary includes:

| Key | Description |
|-----|-------------|
| `tpa` | Trees per acre |
| `basal_area` | Basal area (ft²/acre) |
| `qmd` | Quadratic mean diameter (inches) |
| `mean_dbh` | Arithmetic mean DBH (inches) |
| `top_height` | Dominant/top height (feet) |
| `mean_height` | Arithmetic mean height (feet) |
| `ccf` | Crown competition factor |
| `sdi` | Stand density index |
| `max_sdi` | Maximum SDI for the species |
| `relsdi` | Relative SDI (`sdi / max_sdi`) |
| `volume` | Total cubic volume (ft³/acre) |
| `merchantable_volume` | Merchantable cubic volume (ft³/acre) |
| `board_feet` | Board-foot volume (Doyle) |
| `age` | Stand age (years) |

!!! note "`get_metrics()` vs the yield table"
    `get_metrics()` returns the stand's **current** state. For a time series
    across the rotation, use
    [`get_yield_table_dataframe()`](api/stand.md) — its columns follow the
    FVS_Summary convention (`Age`, `TPA`, `BA`, `QMD`, `TCuFt`, …).

## Choosing a variant

PyFVS supports 11 regional variants. Pass `variant=` and a species code valid
for that region:

```python
from pyfvs import Stand

# Pacific Northwest Coast Douglas-fir
pn = Stand.initialize_planted(400, 120, "DF", variant="PN")

# Lake States red pine
ls = Stand.initialize_planted(500, 65, "RN", variant="LS")

# Northeast red maple
ne = Stand.initialize_planted(500, 60, "RM", variant="NE")

for s in (pn, ls, ne):
    s.grow(years=50)
    print(s.variant, s.get_metrics()["qmd"])
```

If you omit `variant`, PyFVS uses the Southern (`SN`) variant by default. See
the [Variants reference](variants/index.md) for the species and growth
equations of each region.

## Site index

Site index is the expected dominant height (feet) at a variant-specific base
age — base age 25 for the Southern variant. Higher site index means a more
productive site:

| Site index (SN) | Quality | Typical conditions |
|-----------------|---------|--------------------|
| 50–60 | Poor | Dry ridges, poor soils |
| 60–70 | Average | Typical upland sites |
| 70–80 | Good | Moist lowlands, good soils |
| 80–90 | Excellent | River bottoms, best sites |

## Stochastic vs. deterministic growth

Diameter growth is **stochastic by default**, matching the native FVS Fortran
behavior (`DGSD ≥ 1.0`). Each run draws different per-tree growth noise, so
results vary unless you fix a seed:

```python
from pyfvs import Stand

# Stochastic (default) — different every run
stand = Stand.initialize_planted(500, 70, "LP", variant="SN")

# Reproducible stochastic — same result every run
seeded = Stand.initialize_planted(500, 70, "LP", variant="SN", random_seed=42)

# Deterministic — no per-tree growth noise (Fortran DGSD<1.0 branch)
flat = Stand.initialize_planted(500, 70, "LP", variant="SN", stochastic=False)
```

!!! tip "Use a seed for tests and tables"
    For reproducible yield tables or regression tests, always pass
    `random_seed=`. Deterministic mode (`stochastic=False`) removes the
    ecological variance in the diameter distribution and is best reserved for
    debugging against the Fortran deterministic branch.

## Next steps

- [Core Concepts](concepts/index.md) — how the models fit together
- [Variants](variants/index.md) — regions, species, and equations
- [Cookbook](cookbook.md) — thinning, yield tables, exports, comparisons
- [API Reference](api/index.md) — `Stand`, `Tree`, `SimulationEngine`

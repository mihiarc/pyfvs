# Getting Started

This guide will help you install PyFVS and run your first forest growth simulation.

## Installation

### Using pip

```bash
pip install pyfvs-fia
```

### Using uv (recommended)

```bash
uv add pyfvs-fia
```

### Development Installation

```bash
git clone https://github.com/mihiarc/pyfvs.git
cd pyfvs
uv pip install -e .
```

## Your First Simulation

### Basic Stand Simulation

The simplest way to simulate forest growth is using the `Stand` class:

```python
from pyfvs import Stand

# Create a planted stand of loblolly pine
stand = Stand.initialize_planted(
    trees_per_acre=500,
    site_index=70,
    species='LP'
)

# Simulate 30 years of growth
stand.grow(years=30)

# View results
metrics = stand.get_metrics()
print(f"Age: {stand.age} years")
print(f"Trees per acre: {metrics['tpa']:.0f}")
print(f"Basal area: {metrics['basal_area']:.1f} ft²/acre")
print(f"Volume: {metrics['volume']:.0f} ft³/acre")
```

!!! example "Expected output"
    ```
    Age: 30 years
    Trees per acre: 430
    Basal area: 205.5 ft²/acre
    Volume: 6881 ft³/acre
    ```

### Understanding Site Index

Site index represents the expected height of dominant trees at a base age of 25 years. Higher site index means better growing conditions:

| Site Index | Quality | Typical Conditions |
|------------|---------|-------------------|
| 50-60 | Poor | Dry ridges, poor soils |
| 60-70 | Average | Typical upland sites |
| 70-80 | Good | Moist lowlands, good soils |
| 80-90 | Excellent | River bottoms, best sites |

### Using Ecological Units

Ecological units (ecounits) modify growth rates based on geographic region. The M231 (Southern Appalachian) province produces the highest growth rates:

```python
from pyfvs import Stand

# High-productivity simulation with M231 ecounit
stand = Stand.initialize_planted(
    trees_per_acre=500,
    site_index=70,
    species='LP',
    ecounit='M231'  # Mountain province - highest growth
)

stand.grow(years=25)
print(f"Volume: {stand.get_metrics()['volume']:.0f} ft³/acre")
```

!!! example "Expected output"
    ```
    Volume: 10729 ft³/acre
    ```

Available ecounits and their effects on diameter growth:

| Ecounit | Region | Effect on Growth |
|---------|--------|------------------|
| 232 | Georgia (base) | 1.0x (baseline) |
| 231L | Lowland | 1.3x |
| 255 | Prairie | 1.3x |
| M231 | Mountain | 2.2x |

## Harvest Operations

PyFVS supports common silvicultural operations:

### Thinning from Below

Remove the smallest trees to a target density:

```python
from pyfvs import Stand

stand = Stand.initialize_planted(trees_per_acre=800, site_index=70, species='LP')
stand.grow(years=15)

# Thin to 200 trees per acre, removing smallest first
stand.thin_from_below(target_tpa=200)

stand.grow(years=15)
print(f"Final TPA: {stand.get_metrics()['tpa']:.0f}")
```

!!! example "Expected output"
    ```
    Final TPA: 189
    ```

### Thinning from Above

Remove the largest trees (high-grade harvest):

```python
stand.thin_from_above(target_tpa=300)
```

### Selection Harvest

Remove trees to achieve a target basal area:

```python
stand.selection_harvest(target_basal_area=80)  # Target 80 ft²/acre
```

## Working with Results

### Get Yield Table

Generate a time series of stand metrics:

```python
from pyfvs import Stand

stand = Stand.initialize_planted(trees_per_acre=500, site_index=70, species='LP')
yield_table = stand.get_yield_table_dataframe(years=50, period_length=5)

# Display key columns (Age, TPA, QMD, TCuFt=total cubic feet)
print(yield_table[['Age', 'TPA', 'QMD', 'TCuFt']])
```

!!! example "Expected output"
    ```
     Age  TPA       QMD        TCuFt
       0  500  0.506281    93.610400
       5  480  2.878952   314.004340
      10  472  4.519664   956.536667
      15  466  6.112528  2187.534923
      20  461  7.414849  3759.174794
      25  448  8.463868  5362.540417
      30  436  9.332694  6935.371646
      35  429 10.065301  8495.195330
      40  423 10.691508  9963.346609
      45  413 11.237817 11196.221399
      50  406 11.726117 12371.302295
    ```

### Export to CSV

```python
# Get yield table as DataFrame
df = stand.get_yield_table()
df.to_csv('simulation_results.csv', index=False)
```

### Get Individual Tree Data

```python
tree_list = stand.get_tree_list()
print(tree_list.head())
```

## Using SimulationEngine

For more complex simulations, use the `SimulationEngine`:

```python
from pyfvs import SimulationEngine
from pathlib import Path

engine = SimulationEngine(output_dir=Path('./output'))

# Run simulation with automatic output generation
results = engine.simulate_stand(
    species='LP',
    trees_per_acre=500,
    site_index=70,
    years=50,
    time_step=5
)

# Generate comparative yield tables
yield_table = engine.simulate_yield_table(
    species=['LP', 'SP'],
    site_indices=[60, 70, 80],
    planting_densities=[300, 500, 700],
    years=40
)
```

## Next Steps

- Learn about [Stand](api/stand.md) class methods
- Understand [Tree](api/tree.md) growth models
- Explore [SimulationEngine](api/simulation-engine.md) for batch simulations
- Read about [Growth Models](guides/growth-models.md) and equations

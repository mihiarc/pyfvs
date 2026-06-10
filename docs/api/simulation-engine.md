# SimulationEngine

The `SimulationEngine` class provides high-level orchestration for running simulations, generating yield tables, and comparing scenarios. It handles output file generation, logging, and batch processing.

## Overview

Use `SimulationEngine` when you need to:

- Run multiple simulations with different parameters
- Generate comparative yield tables
- Automatically save results to files
- Compare management scenarios

For simple single-stand simulations, the `Stand` class is often sufficient.

!!! warning "Southern variant only"
    `SimulationEngine` initializes stands with the default (Southern, `SN`)
    variant and does not accept a `variant=` or `ecounit=` argument. To run
    other variants — or to use ecological units — drive [`Stand`](stand.md)
    directly.

## Quick Start

```python
from pyfvs.simulation_engine import SimulationEngine
from pathlib import Path

# Create engine with output directory
engine = SimulationEngine(output_dir=Path('./output'))

# Run a single simulation
results = engine.simulate_stand(
    species='LP',
    trees_per_acre=500,
    site_index=70,
    years=50
)

print(results.tail())
```

Example output:

```text
   age  tpa  basal_area   volume  mean_dbh  mean_height    qmd  top_height
8   40  395       308.2   9143.5     11.85        82.14  11.93       85.67
9   45  380       332.1  10621.8     12.59        87.04  12.66       90.11
10  50  367       352.7  12045.3     13.27        91.23  13.33       93.89
```

## Single Stand Simulation

```python
from pyfvs.simulation_engine import SimulationEngine

engine = SimulationEngine(output_dir='./output')

results = engine.simulate_stand(
    species='LP',
    trees_per_acre=500,
    site_index=70,
    years=50,
    time_step=5,
    save_outputs=True,    # Save CSV/JSON files
    plot_results=True     # Generate plots
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `species` | str | `'LP'` | Species code (Southern variant) |
| `trees_per_acre` | int | `500` | Initial planting density |
| `site_index` | float | `70` | Site index (base age 25) |
| `years` | int | `50` | Total simulation years |
| `time_step` | int | `5` | Years between outputs |
| `save_outputs` | bool | `True` | Save results to files |
| `plot_results` | bool | `True` | Generate matplotlib plots |

### Returns

A pandas DataFrame with one row per output period. The columns are the keys of
`Stand.get_metrics()`:

- `age`, `tpa`, `basal_area`, `qmd`, `mean_dbh`
- `top_height`, `mean_height`, `ccf`, `sdi`, `max_sdi`, `relsdi`
- `volume`, `merchantable_volume`, `board_feet`

## Yield Table Generation

Generate yield tables across multiple scenarios:

```python
yield_table = engine.simulate_yield_table(
    species=['LP', 'SP'],
    site_indices=[60, 70, 80],
    planting_densities=[300, 500, 700],
    years=40
)

# Result has columns: species, site_index, initial_tpa, age, ...
print(yield_table.groupby(['species', 'site_index']).tail(1))
```

This generates a factorial combination of all parameters, running each scenario and combining results.

## Scenario Comparison

Compare different management scenarios:

```python
scenarios = [
    {
        'name': 'Low Density',
        'species': 'LP',
        'trees_per_acre': 300,
        'site_index': 70
    },
    {
        'name': 'High Density',
        'species': 'LP',
        'trees_per_acre': 700,
        'site_index': 70
    },
    {
        'name': 'Poor Site',
        'species': 'LP',
        'trees_per_acre': 500,
        'site_index': 55
    },
    {
        'name': 'Good Site',
        'species': 'LP',
        'trees_per_acre': 500,
        'site_index': 85
    }
]

comparison = engine.compare_scenarios(scenarios, years=30)

# View final results
final = comparison[comparison['age'] == 30]
print(final[['scenario', 'volume', 'basal_area', 'tpa']])
```

## Output Files

When `save_outputs=True`, the engine creates:

```text
output/
├── simulation_LP_SI70_TPA500.csv    # Yield table
├── simulation_LP_SI70_TPA500.json   # Metadata
├── trajectory_LP_SI70_TPA500.png    # Growth trajectory plot
└── fvs-python.log                   # Log file
```

## Example: Complete Workflow

```python
from pyfvs.simulation_engine import SimulationEngine
from pathlib import Path

# Setup
output_dir = Path('./simulation_output')
engine = SimulationEngine(output_dir)

# 1. Single simulation
print("Running single simulation...")
single = engine.simulate_stand(
    species='LP',
    trees_per_acre=500,
    site_index=70,
    years=50
)
print(f"Final volume: {single.iloc[-1]['volume']:.0f} ft³/acre")

# 2. Yield table for multiple scenarios
print("\nGenerating yield table...")
yield_table = engine.simulate_yield_table(
    species=['LP'],
    site_indices=[60, 70, 80],
    planting_densities=[400, 600],
    years=40
)
yield_table.to_csv(output_dir / 'yield_table.csv')

# 3. Scenario comparison
print("\nComparing management scenarios...")
scenarios = [
    {'name': 'Unthinned', 'species': 'LP', 'trees_per_acre': 600, 'site_index': 70},
    {'name': 'Thinned', 'species': 'LP', 'trees_per_acre': 600, 'site_index': 70},
]
comparison = engine.compare_scenarios(scenarios, years=30)

print("\nDone! Results saved to:", output_dir)
```

## Class Reference

::: pyfvs.simulation_engine.SimulationEngine
    options:
      show_root_heading: true
      show_source: false
      members:
        - __init__
        - simulate_stand
        - simulate_yield_table
        - compare_scenarios

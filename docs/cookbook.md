# Cookbook

Task-oriented recipes. All examples pass `random_seed=` so they reproduce;
remove it for an unseeded (default stochastic) run.

## Run a basic simulation

```python
from pyfvs import Stand

stand = Stand.initialize_planted(500, 70, "LP", variant="SN", random_seed=42)
stand.grow(years=30)

m = stand.get_metrics()
print(f"Age {m['age']}  TPA {m['tpa']:.0f}  QMD {m['qmd']:.1f}\"  Vol {m['volume']:.0f} ft³/ac")
```

## Compare species or variants

Run several stands and collect their final metrics into a table.

```python
import pandas as pd
from pyfvs import Stand

runs = [
    ("SN", "LP", 500, 70),    # Southern loblolly pine
    ("PN", "DF", 400, 120),   # Pacific NW Douglas-fir
    ("LS", "RN", 500, 65),    # Lake States red pine
    ("NE", "RM", 500, 60),    # Northeast red maple
]

rows = []
for variant, species, tpa, si in runs:
    stand = Stand.initialize_planted(tpa, si, species, variant=variant, random_seed=42)
    stand.grow(years=50)
    m = stand.get_metrics()
    rows.append({
        "variant": variant,
        "species": species,
        "tpa": round(m["tpa"]),
        "qmd": round(m["qmd"], 1),
        "basal_area": round(m["basal_area"]),
        "volume": round(m["volume"]),
    })

print(pd.DataFrame(rows).to_string(index=False))
```

## Build a yield table

`get_yield_table_dataframe()` returns one row per period with FVS_Summary-style
columns (`Age`, `TPA`, `BA`, `SDI`, `CCF`, `TopHt`, `QMD`, `TCuFt`, …).

```python
from pyfvs import Stand

stand = Stand.initialize_planted(500, 70, "LP", variant="SN", random_seed=42)
table = stand.get_yield_table_dataframe(years=50, period_length=5)

print(table[["Age", "TPA", "QMD", "TopHt", "BA", "TCuFt"]].to_string(index=False))
```

## Thin a stand

```python
from pyfvs import Stand

stand = Stand.initialize_planted(700, 70, "LP", variant="SN", random_seed=42)

stand.grow(years=15)
stand.thin_from_below(target_tpa=300)
stand.grow(years=15)

m = stand.get_metrics()
print(f"Final: {m['tpa']:.0f} TPA, {m['qmd']:.1f}\" QMD, {m['volume']:.0f} ft³/ac")
```

See [Harvest Operations](guides/harvesting.md) for thin-from-above, thin-by-DBH,
and selection harvests.

## Sweep site index and density

```python
import pandas as pd
from pyfvs import Stand

rows = []
for si in (60, 70, 80):
    for tpa in (400, 600):
        stand = Stand.initialize_planted(tpa, si, "LP", variant="SN", random_seed=42)
        stand.grow(years=30)
        m = stand.get_metrics()
        rows.append({
            "site_index": si,
            "initial_tpa": tpa,
            "final_tpa": round(m["tpa"]),
            "final_qmd": round(m["qmd"], 1),
            "final_volume": round(m["volume"]),
        })

print(pd.DataFrame(rows).to_string(index=False))
```

## Use the SimulationEngine

For batch runs with automatic file output, use
[`SimulationEngine`](api/simulation-engine.md). It runs the Southern variant.

```python
from pyfvs.simulation_engine import SimulationEngine
from pathlib import Path

engine = SimulationEngine(output_dir=Path("./output"))

# Single stand
results = engine.simulate_stand(species="LP", trees_per_acre=500, site_index=70, years=50)

# Factorial yield table
yield_table = engine.simulate_yield_table(
    species=["LP", "SP"],
    site_indices=[60, 70, 80],
    planting_densities=[400, 600],
    years=40,
)
print(yield_table.groupby(["species", "site_index", "initial_tpa"]).last())
```

## Export results

```python
from pyfvs import Stand

stand = Stand.initialize_planted(500, 70, "LP", variant="SN", random_seed=42)
stand.grow(years=50)

yield_table = stand.get_yield_table_dataframe(years=50, period_length=5)
tree_list = stand.get_tree_list_dataframe()

# CSV
yield_table.to_csv("yield_table.csv", index=False)
tree_list.to_csv("tree_list.csv", index=False)

# Excel (one workbook, two sheets)
import pandas as pd
with pd.ExcelWriter("simulation_results.xlsx") as writer:
    yield_table.to_excel(writer, sheet_name="Yield Table", index=False)
    tree_list.to_excel(writer, sheet_name="Tree List", index=False)
```

## Inspect individual trees

`get_tree_list_dataframe()` returns FVS-style per-tree columns (`DBH`, `Ht`,
`PctCr`, `TcuFt`, …).

```python
from pyfvs import Stand

stand = Stand.initialize_planted(500, 70, "LP", variant="SN", random_seed=42)
stand.grow(years=25)

trees = stand.get_tree_list_dataframe()
print(trees[["DBH", "Ht", "PctCr", "TcuFt"]].describe())
```

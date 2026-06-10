# Core Concepts

PyFVS is an individual-tree, distance-independent growth model. A **stand** is
a list of **trees** on a per-acre basis; growth advances each tree one cycle at
a time, then competition and mortality are re-evaluated at the stand level.

## The simulation pipeline

```text
Stand.initialize_planted()   ->  build Tree objects on bare ground
        |
        v
Stand.grow(years)            ->  for each base-cycle sub-period:
        |                          1. compute competition (CCF, PBAL, SDI, rank)
        |                          2. grow each tree (DBH, height, crown ratio)
        |                          3. apply mortality
        v
Stand.get_metrics()          ->  stand-level summary (TPA, BA, QMD, volume, ...)
```

The same object also produces [yield tables](../api/stand.md) and
[tree lists](../api/stand.md), and supports
[harvest operations](../guides/harvesting.md) between `grow()` calls.

## Composition

The `Stand` class delegates to focused components rather than doing everything
itself:

| Component | Responsibility |
|-----------|----------------|
| `StandMetricsCalculator` | CCF, QMD, SDI, basal area, top height |
| `CompetitionCalculator` | PBAL, rank, relative height |
| `MortalityModel` | Background and density-dependent mortality |
| `HarvestManager` | Thinning and selection harvest |
| `StandOutputGenerator` | Yield tables, tree lists, exports |

Each `Tree` carries its own dimensions (DBH, height, crown ratio), species
parameters, and the growth logic for its variant.

## Three ideas to start with

- **[Growth Models](growth-models.md)** — trees switch between a height-driven
  small-tree model and a diameter-driven large-tree model, with a blended
  transition in between. The large-tree diameter equation is what differs most
  between variants.
- **[Stand Dynamics](stand-dynamics.md)** — competition metrics feed the growth
  equations, and mortality removes trees each cycle. Growth is stochastic by
  default.
- **[Volume & Taper](volume.md)** — volume is integrated from a taper profile
  (Clark in the East, Flewelling in the West), then merchandised into products.

For region-specific details — species lists, cycle lengths, and the exact
diameter-growth equation form — see the [Variants reference](../variants/index.md).

# Harvest Operations

PyFVS supports common silvicultural operations for managing stand density and
structure. Call them on a `Stand` between `grow()` calls. They work for any
variant; the examples below use the Southern variant with loblolly pine.

!!! tip "Reproducible examples"
    Growth is [stochastic by default](../concepts/stand-dynamics.md#stochastic-vs-deterministic-growth),
    so exact numbers vary between runs. The examples pass `random_seed=` so they
    reproduce; remove it for an unseeded run.

## Thinning methods

### Thin from below

Removes the smallest trees first — the most common thinning, used to reduce
competition and concentrate growth on the best trees.

```python
from pyfvs import Stand

stand = Stand.initialize_planted(800, 70, "LP", variant="SN", random_seed=42)
stand.grow(years=15)

stand.thin_from_below(target_tpa=300)   # keep the 300 largest trees
stand.grow(years=15)
```

**Effects:** increases average DBH, reduces competition, concentrates growth on
the largest stems.

### Thin from above

Removes the largest trees first, simulating a high-grade harvest.

```python
stand.thin_from_above(target_tpa=400)
```

**Effects:** generates immediate revenue from large trees but can reduce future
stand quality.

### Thin by DBH range

Removes a proportion of trees within a diameter range.

```python
# Remove 50% of trees between 6" and 10" DBH
stand.thin_by_dbh_range(min_dbh=6.0, max_dbh=10.0, proportion=0.5)
```

**Use cases:** removing pulpwood-sized stems, salvage, or shaping a target
structure.

### Selection harvest

Reduces the stand to a target basal area, removing trees across size classes.

```python
# Reduce to 80 ft²/acre
stand.selection_harvest(target_basal_area=80)
```

**Effects:** maintains stand structure; common in uneven-aged management.

## A multi-entry schedule

```python
from pyfvs import Stand

stand = Stand.initialize_planted(700, 70, "LP", variant="SN", random_seed=42)

# Grow to the first thin
stand.grow(years=12)
print(f"Pre-thin:  {stand.get_metrics()['tpa']:.0f} TPA, "
      f"{stand.get_metrics()['qmd']:.1f}\" QMD")

# First thin — remove roughly half
stand.thin_from_below(target_tpa=350)

# Grow to a second thin
stand.grow(years=8)
stand.thin_from_below(target_tpa=180)

# Grow to final harvest
stand.grow(years=10)

m = stand.get_metrics()
print(f"Final:     {m['volume']:.0f} ft³/acre, {m['qmd']:.1f}\" QMD")
```

## Inspecting the result

Harvest operations mutate the stand in place. Read the new state with
`get_metrics()`:

```python
stand.thin_from_below(target_tpa=200)
m = stand.get_metrics()
print(f"Remaining: {m['tpa']:.0f} TPA, {m['basal_area']:.0f} ft²/acre")
```

## Best practices

1. **Time the first thin appropriately** — often when crown closure occurs
   (CCF > 100).
2. **Don't over-thin** — keep enough trees to occupy the site.
3. **Match intensity to objectives** — pulpwood vs. sawtimber.
4. **Consider residual spacing** — e.g. 12–15 ft for pine sawtimber.

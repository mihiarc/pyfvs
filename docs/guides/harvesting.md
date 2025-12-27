# Harvest Operations

PyFVS supports common silvicultural operations for managing stand density and structure.

## Thinning Methods

### Thin from Below

Removes the smallest trees first, commonly used to reduce competition and improve growth of remaining trees.

```python
from pyfvs import Stand

stand = Stand.initialize_planted(trees_per_acre=800, site_index=70, species='LP')
stand.grow(years=15)

# Thin to 300 TPA, removing smallest trees
stand.thin_from_below(target_tpa=300)

stand.grow(years=15)
```

**Effects:**
- Increases average DBH
- Reduces competition
- Concentrates growth on best trees

### Thin from Above

Removes the largest trees first, simulating high-grade harvesting.

```python
# Remove largest trees, keep 400 TPA
stand.thin_from_above(target_tpa=400)
```

**Effects:**
- Generates immediate revenue from large trees
- May reduce stand quality over time
- Opens canopy for understory

### Thin by DBH Range

Removes trees within a specific diameter range.

```python
# Remove 50% of trees between 6" and 10" DBH
stand.thin_by_dbh_range(min_dbh=6.0, max_dbh=10.0, proportion=0.5)
```

**Use cases:**
- Remove pulpwood-sized trees
- Create specific stand structure
- Salvage operations

### Selection Harvest

Reduces stand to a target basal area, removing trees proportionally across size classes.

```python
# Reduce to 80 ft²/acre basal area
stand.selection_harvest(target_basal_area=80)
```

**Effects:**
- Maintains stand structure
- Sustainable harvest method
- Common in uneven-aged management

## Thinning Schedules

### Commercial Thin Example

```python
from pyfvs import Stand

# Establish stand
stand = Stand.initialize_planted(
    trees_per_acre=700,
    site_index=70,
    species='LP',
    ecounit='M231'
)

# Grow to first thin (age 12-15)
stand.grow(years=12)
print(f"Pre-thin: {stand.get_metrics()['tpa']:.0f} TPA, {stand.get_metrics()['qmd']:.1f}\" QMD")

# First thin - remove ~50%
stand.thin_from_below(target_tpa=350)
print(f"Post-thin: {stand.get_metrics()['tpa']:.0f} TPA")

# Grow to second thin
stand.grow(years=8)  # Age 20
stand.thin_from_below(target_tpa=180)

# Grow to final harvest
stand.grow(years=10)  # Age 30

print(f"Final: {stand.get_metrics()['volume']:.0f} ft³/acre, {stand.get_metrics()['qmd']:.1f}\" QMD")
```

!!! example "Expected output"
    ```
    Pre-thin: 661 TPA, 8.6" QMD
    Post-thin: 350 TPA
    Final: 7988 ft³/acre, 16.0" QMD
    ```

### Sawtimber Rotation

```python
# Long rotation for large sawtimber
stand = Stand.initialize_planted(trees_per_acre=600, site_index=75, species='LP')

stand.grow(years=15)
stand.thin_from_below(target_tpa=250)

stand.grow(years=10)
stand.thin_from_below(target_tpa=120)

stand.grow(years=15)  # Final harvest at age 40

metrics = stand.get_metrics()
print(f"Final DBH: {metrics['qmd']:.1f} inches")
print(f"Final volume: {metrics['volume']:.0f} ft³/acre")
```

!!! example "Expected output"
    ```
    Final DBH: 13.9 inches
    Final volume: 4819 ft³/acre
    ```

## Tracking Harvest Volume

Harvest operations return information about removed trees:

```python
# Get harvest results (if method returns them)
stand.thin_from_below(target_tpa=200)

# Check remaining stand
metrics = stand.get_metrics()
print(f"Remaining: {metrics['tpa']:.0f} TPA, {metrics['volume']:.0f} ft³/acre")
```

## Best Practices

1. **Time first thin appropriately** - Usually when crown closure occurs (CCF > 100)
2. **Don't over-thin** - Maintain enough trees for site occupancy
3. **Match thin intensity to objectives** - Pulpwood vs sawtimber
4. **Consider residual spacing** - Target 12-15' spacing for pine sawtimber

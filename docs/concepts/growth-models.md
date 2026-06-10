# Growth Models

PyFVS models each tree with one of two growth forms, chosen by size, plus a
blended transition between them. This structure is shared across all variants;
what changes between variants is mainly the **large-tree diameter-growth
equation**.

## Size-based model selection

| DBH | Model | Driver |
|-----|-------|--------|
| `< 1.0"` | Small-tree | Height growth drives DBH |
| transition band | Blended | Weighted mix of both |
| above the band | Large-tree | DBH growth drives height |

The transition band is variant-specific. The Southern variant blends from
**1.0″ to 3.0″**; some variants (e.g. Lake States and Central States) blend
from **3.0″ to 5.0″**. The growth model for a tree is selected at the **start**
of each cycle and held constant through it, matching the Fortran `regent.f`
behavior.

## Small-tree model

For seedlings and saplings, height growth follows a Chapman-Richards curve and
DBH is then derived from the height–diameter relationship:

```text
H(t) = c1 · SI^c2 · (1 - exp(c3 · t))^(c4 · SI^c5)
```

where `SI` is site index and `t` is age. Height growth over a cycle is the
forward increment `H(age + cycle) - H(age)`. Because the curve is concave,
computing it as a true forward difference (rather than scaling a per-year rate)
matters for longer cycles.

## Large-tree model

For established trees, the engine predicts a **diameter-squared increment**
(DDS) and converts it to a diameter increment. The general Southern form is:

```text
ln(DDS) = b0 + b1·ln(DBH) + b2·DBH² + b3·CR + b4·CR²
        + b5·RELHT + b6·SI + b7·BA + (ecological-unit term)
```

| Variable | Meaning |
|----------|---------|
| `DBH` | Diameter at breast height (inches) |
| `CR` | Crown ratio (0–1) |
| `RELHT` | Relative height (tree height ÷ dominant height) |
| `SI` | Site index |
| `BA` | Stand basal area (ft²/acre) |
| `PBAL` / `BAL` | Basal area in larger trees (ft²/acre) |

DDS applies to the **inside-bark** diameter; PyFVS converts to and from
outside-bark using a species bark ratio.

### Diameter-growth forms by variant

The equation *form* — and therefore which competition and topographic terms
appear — varies by region:

| Variant(s) | Form | Distinctive terms |
|------------|------|-------------------|
| SN | `ln(DDS)` | `RELHT`, ecological unit |
| LS, CS | `ln(DDS)` (linear-in-DBH) | `RELDBH`, `BAL` |
| PN, WC, EC | `ln(DDS)` | topographic: elevation, slope, aspect |
| CA, WS, OC | `ln(DDS)` | `PCCF`, topographic, multiple equation sets |
| NE | basal-area growth | iterative NE-TWIGS `POTBAG = B1·SI·(1 - e^(-B2·DBH))` |
| OP | `ln(DG)` (direct) | ORGANON diameter growth, not DDS |

The full per-variant equations are listed in the
[Variants reference](../variants/index.md).

## Height growth (large trees)

Once a tree is in the large-tree model, height growth is driven by potential
height growth from the site curves, modified by crown ratio and relative
height. The Southern form is:

```text
HTG = POTHTG · (0.25 · HGMDCR + 0.75 · HGMDRH)
```

- `POTHTG` — potential height growth from the site-index curve
- `HGMDCR` — crown-ratio modifier
- `HGMDRH` — relative-height modifier

Other variants apply region-specific modifiers (for example, the Northeast
variant blends a BAL-based modifier and damps the result).

## The transition blend

Inside the transition band, the small- and large-tree predictions are combined
so growth is continuous across the boundary. The Southern variant uses a
**smoothstep** weight:

```python
t = (dbh - xmin) / (xmax - xmin)      # 0 at xmin, 1 at xmax
weight = 3 * t**2 - 2 * t**3          # smooth 0 -> 1
growth = (1 - weight) * small_tree_growth + weight * large_tree_growth
```

Some variants (e.g. the Northeast) use a linear weight (`XWT`) instead. Either
way, the blend prevents a discontinuity in predicted growth as trees cross out
of the small-tree model.

## Cycle length

FVS variants are calibrated for a fixed cycle length — **5 years** for SN and
OP, **10 years** for all other variants. `Stand.grow(years=N)` subdivides
longer periods into base-cycle sub-cycles, recomputing competition between
them. See [Stand Dynamics](stand-dynamics.md) for what happens between cycles.

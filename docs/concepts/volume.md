# Volume & Taper

PyFVS estimates volume by integrating a **stem taper profile** — a curve of
stem diameter as a function of height — and then merchandising that profile
into products. This matches the approach of the National Volume Estimator
Library (NVEL).

## Taper models

| Model | Region / variants | Profile |
|-------|-------------------|---------|
| **Clark** | Eastern: SN (R8), and NE, CS, LS (R9) | 3-segment profile with analytic integration |
| **Flewelling** | Western coast: PN, WC, OP | 4-segment variable-shape profile |
| **Combined-variable** | Fallback | `V = a + b · DBH² · H` (Amateis & Burkhart 1987) |

Variants without a region-specific taper model fall back to the
combined-variable equation or the nearest regional profile. The taper
coefficients live in `src/pyfvs/cfg/taper/` (`clark_r8_coefficients.json`,
`clark_r9_coefficients.json`, `flewelling_coefficients.json`).

## Getting volume from a tree

```python
from pyfvs import Tree

tree = Tree(dbh=12.0, height=75.0, species="LP", age=25, variant="SN")

total = tree.get_volume()                        # total cubic feet (default)
merch = tree.get_volume(volume_type="merchantable")
detail = tree.get_volume_detailed()              # dict: total/merch cubic + board feet
```

`get_volume()` defaults to `volume_type="total_cubic"`. Volume is integrated
from a stump height upward; the Southern variant integrates total cubic volume
from a **0.5 ft** stump (FVS `PROD='02'`), consistent with the native model.

## Merchandising

Once the taper profile is known, the stem is bucked into logs and scaled with a
configurable log rule:

- **Scribner Decimal C**
- **International 1/4″**
- **Doyle** board-foot rule

Merchandising honors a merchantable top diameter and minimum log lengths, so
the same tree yields different product volumes depending on the rule and
specifications.

## Stand-level volume

`Stand.get_metrics()` reports volume aggregated to a per-acre basis:

| Key | Description |
|-----|-------------|
| `volume` | Total cubic volume (ft³/acre) |
| `merchantable_volume` | Merchantable cubic volume (ft³/acre) |
| `board_feet` | Board-foot volume (Doyle), per acre |

Because volume depends on `DBH²`, it is sensitive to the spread of the diameter
distribution — two stands with the same QMD but different variance can have
measurably different volume. This is one reason
[stochastic growth](stand-dynamics.md#stochastic-vs-deterministic-growth) (the
default) produces more realistic volumes than deterministic mode.

## References

- Clark, A. III, Souter, R.A., Schlaegel, B.E. (1991). *Stem profile equations
  for southern tree species.* USDA-FS Research Paper SE-282.
- Flewelling, J.W. (1994). *Stem form equation development notes.* USDA-FS.
- Amateis, R.L. & Burkhart, H.E. (1987). Tree volume and taper equations.
  *Forest Science* 33(2).

# Stand Dynamics

Between growing individual trees, PyFVS evaluates the stand as a whole:
competition metrics feed the growth equations, and mortality removes trees each
cycle.

## Competition

Growth is density-dependent. Each cycle, the stand computes the metrics that
the diameter- and height-growth equations consume:

| Metric | Meaning | Used for |
|--------|---------|----------|
| **BA** | Total basal area (ft²/acre) | Density term in growth equations |
| **PBAL / BAL** | Basal area in trees larger than the subject | One-sided competition |
| **CCF** | Crown competition factor (≈ % of an acre the crowns would cover) | Crown closure, crown ratio |
| **SDI** | Stand density index | Density-dependent mortality, `relsdi` |
| **rank** | Tree's position in the diameter distribution (0–1) | Relative height/diameter |
| **RELHT / RELDBH** | Tree size relative to the stand | Growth modifiers |

These are recomputed at the start of every base cycle, so a long `grow()` call
responds to changing density as the stand develops.

### Stand density index

SDI is computed two ways depending on the variant, matching the Fortran
`grinit.f` `LZEIDE` flag:

- **Zeide summation form** — SN, LS, CS, NE, WS, CA
- **Reineke QMD form** — PN, WC, EC, OC, OP

The two are identical for a perfectly uniform stand and diverge as the diameter
distribution spreads.

## Mortality

Each cycle applies two kinds of mortality:

- **Background mortality** — a low baseline rate applied regardless of density.
- **Density-dependent mortality** — increases as the stand approaches its
  maximum SDI, thinning the stand toward the self-thinning limit.

The **number** of trees that die in a cycle is deterministic (an
expected-value calculation). In stochastic mode the engine then chooses *which*
trees die by weighted sampling without replacement — larger, more competitive
trees are less likely to be removed — but the count itself does not vary with
the random seed.

## Stochastic vs. deterministic growth

Diameter growth is **stochastic by default** (matching native FVS with
`DGSD ≥ 1.0`). Per-tree growth noise produces an ecologically realistic spread
in the diameter distribution, which in turn affects volume through Jensen's
inequality.

```python
from pyfvs import Stand

# Reproducible stochastic run
stand = Stand.initialize_planted(500, 70, "LP", variant="SN", random_seed=42)

# Deterministic run (no per-tree growth noise)
flat = Stand.initialize_planted(500, 70, "LP", variant="SN", stochastic=False)
```

Stochastic growth applies to the variants whose diameter model supports it
(SN, LS, PN, WC, EC, CS, WS, CA, OC). The NE and OP model forms are
unaffected by the stochastic switch.

!!! note "Reproducibility"
    Pass `random_seed=` for runs you need to repeat (tests, published yield
    tables). Without a seed, each run draws fresh noise and results differ.

## Cycles and time steps

Each variant has a base cycle length — 5 years (SN, OP) or 10 years (all
others). `Stand.grow(years=N)`:

1. subdivides `N` into base-cycle sub-cycles,
2. selects each tree's growth model at the start of a sub-cycle,
3. grows trees, then
4. recomputes competition and applies mortality before the next sub-cycle.

This keeps long projections consistent with the model's calibration regardless
of how the total period is specified.

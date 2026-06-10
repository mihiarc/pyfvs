---
title: FVS Variants
description: The 11 regional FVS variants supported by PyFVS, with species counts, base cycle lengths, and diameter-growth equation forms.
---

# Variants

The Forest Vegetation Simulator is organized into **geographic variants**, each
calibrated to a region's species and growing conditions. PyFVS implements **11**
of them. Select one with the `variant=` argument:

```python
from pyfvs import Stand

stand = Stand.initialize_planted(500, 65, "RN", variant="LS")
```

If `variant` is omitted, the Southern (`SN`) variant is used.

## Supported variants

| Variant | Region | Species | Representative species | Base cycle | Diameter growth |
|---------|--------|---------|------------------------|------------|-----------------|
| **SN** | Southern US | 90 | Loblolly Pine (LP) | 5 yr | `ln(DDS)`, RELHT + ecounit |
| **LS** | Lake States (MI, WI, MN) | 67 | Red Pine (RN) | 10 yr | `ln(DDS)`, RELDBH + BAL |
| **CS** | Central States (IL, IN, IA, MO) | 96 | White Oak (WO) | 10 yr | `ln(DDS)`, RELDBH + BAL |
| **NE** | Northeast (13 states) | 108 | Red Maple (RM) | 10 yr | NE-TWIGS basal-area growth |
| **PN** | Pacific NW Coast (WA, OR) | 39 | Douglas-fir (DF) | 10 yr | `ln(DDS)`, topographic |
| **WC** | West Cascades (OR, WA) | 37 | Douglas-fir (DF) | 10 yr | `ln(DDS)`, topographic |
| **EC** | East Cascades (OR, WA) | 32 | Douglas-fir (DF) | 10 yr | `ln(DDS)`, topographic |
| **CA** | Inland California | 50 | Ponderosa Pine (PP) | 10 yr | `ln(DDS)`, topographic + PCCF |
| **WS** | Western Sierra Nevada | 43 | Ponderosa Pine (PP) | 10 yr | `ln(DDS)`, topographic + PCCF |
| **OP** | ORGANON Pacific NW | 18 | Douglas-fir (DF) | 5 yr | `ln(DG)` direct (ORGANON) |
| **OC** | Southwest Oregon | 50 | Douglas-fir (DF) | 5 yr | `ln(DDS)`, topographic + PCCF |

Species counts are configured-coefficient coverage; some variants provide
per-species parameter files for a subset of those species.

## Diameter-growth equation forms

The biggest structural difference between variants is the large-tree
diameter-growth equation. There are four broad forms.

### `ln(DDS)` with ecological units — SN

```text
ln(DDS) = b0 + b1·ln(DBH) + b2·DBH² + b3·CR + b4·CR²
        + b5·RELHT + b6·SI + b7·BA + ECOUNIT
```

Ecological-unit modifiers are large for the Southern variant — see
[Ecological Units](../guides/ecological-units.md).

### `ln(DDS)` linear-in-DBH with RELDBH — LS, CS

```text
ln(DDS) = INTERC + b1/DBH + b2·DBH + b3·DBH² + b4·RELDBH + b5·RELDBH²
        + b6·CR + b7·CR² + b8·BA + b9·BAL + b10·SI
```

### `ln(DDS)` with topographic effects — PN, WC, EC, CA, WS, OC

```text
ln(DDS) = CONSPP + b1·ln(DBH) + b2·DBH² + b3·CR + b4·CR² + b5·RELHT
        + b6·SI + b7·BA + b8·BAL
        + (elevation, slope, aspect terms)
```

The California, Western Sierra, and Southwest Oregon variants add a point
crown-competition term (`PCCF`) and select among multiple equation sets.
Southwest Oregon (OC) stores 10-year coefficients and applies a `-ln(2)`
conversion at runtime to produce 5-year growth.

### NE-TWIGS basal-area growth — NE

The Northeast variant predicts basal-area growth directly and iterates it
annually over the cycle:

```text
POTBAG = B1 · SI · (1 - exp(-B2 · DBH))
```

### ORGANON direct diameter growth — OP

The ORGANON Pacific Northwest variant predicts a diameter increment directly
(`ln(DG)`) rather than a diameter-squared increment, following the ORGANON
model (Hann et al.).

## Height–diameter relationships

| Variant | Form |
|---------|------|
| SN, OC, WS | Wykoff |
| LS, CS, NE, PN, WC, EC, CA, OP | Curtis-Arney |

Several variants dispatch between Wykoff and Curtis-Arney per species via the
Fortran `IWYKCA` flag.

## Volume

Volume is taper-based and region-dependent — Clark in the East, Flewelling on
the Western coast, with a combined-variable fallback elsewhere. See
[Volume & Taper](../concepts/volume.md) for the mapping.

## Known limitations

- Small trees do not respond to competition until they transition to the
  large-tree model.
- The CA, WS, and OC variants reuse Southern-variant bark-ratio, crown-ratio,
  and mortality models where region-specific coefficients are not yet ported
  (their diameter-growth coefficients are variant-specific).
- Some western species groups (e.g. Flewelling inland species) and a few
  special-case equations are not yet implemented.

For region-by-region parity status against the native Fortran model, see the
fidelity maps in the project repository.

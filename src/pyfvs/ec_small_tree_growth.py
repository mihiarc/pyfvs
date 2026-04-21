"""SMHTGF small-tree height growth for the EC (East Cascades) variant.

Faithful port of Fortran ec/smhtgf.f. Twelve equation groups covering 32
species. Unlike CA's smhtgf (which returns a 5-yr increment directly),
EC's smhtgf has two modes:

- MODE=0 (ESSUBH): DTIME = total seedling age; returns total height at
  that age (starting from zero).
- MODE=1 (REGENT): DTIME = time interval; returns the height increment
  over that interval starting from current tree height H.

For linear equations (most EC species, e.g., WL/DF/GF/LP/PP), both modes
produce HHT = rate(SI) * DTIME. For non-linear equations (WP/RC), MODE=1
first solves for the effective age corresponding to the current height
then subtracts curve(EFFAGE) from curve(EFFAGE + DTIME).

Called from Stand._grow_establishment_cycle_ec and from Tree small-tree
growth paths.
"""
from __future__ import annotations

import math
from typing import Dict


# Fortran EC species ordering (1-indexed) per ec/blkdat.f
_EC_SPECIES_INDEX: Dict[str, int] = {
    'WP': 1, 'WL': 2, 'DF': 3, 'SF': 4, 'RC': 5, 'GF': 6, 'LP': 7,
    'ES': 8, 'AF': 9, 'PP': 10, 'WH': 11, 'MH': 12, 'PY': 13, 'WB': 14,
    'NF': 15, 'WF': 16, 'LL': 17, 'YC': 18, 'WJ': 19, 'BM': 20, 'VN': 21,
    'RA': 22, 'PB': 23, 'GC': 24, 'DG': 25, 'AS': 26, 'CW': 27, 'WO': 28,
    'PL': 29, 'WI': 30, 'OS': 31, 'OH': 32,
}


def _wp_height(mode: int, dtime: float, si: float, h: float) -> float:
    """Species 1 (WP) — non-linear Chapman-Richards-like curve."""
    c1, c2, c3, c4 = 0.375045, 0.92503, -0.020796, 2.48811
    if mode == 0:
        effage = 0.0
    else:
        # Invert: H = (SI/c1)*(1 - c2*exp(c3*effage))^c4
        inner = (c1 / si * h) ** (1.0 / c4)
        arg = (1.0 - inner) / c2
        if arg <= 0:
            effage = 100.0
        else:
            effage = math.log(arg) / c3
    agepdt = effage + dtime
    hht1 = (si / c1) * (1.0 - c2 * math.exp(c3 * effage)) ** c4
    hht2 = (si / c1) * (1.0 - c2 * math.exp(c3 * agepdt)) ** c4
    return hht2 - hht1


def _rc_height(mode: int, dtime: float, si: float, h: float) -> float:
    """Species 5 (RC) — non-linear Chapman-Richards."""
    c1, c2, c3, c4 = 0.752842, 1.0, -0.0174, 1.4711
    if mode == 0:
        effage = 0.0
    else:
        inner = (c1 / si * h) ** (1.0 / c4)
        arg = (1.0 - inner) / c2
        if arg <= 0:
            effage = 100.0
        else:
            effage = math.log(arg) / c3
    agepdt = effage + dtime
    hht1 = (si / c1) * (1.0 - c2 * math.exp(c3 * effage)) ** c4
    hht2 = (si / c1) * (1.0 - c2 * math.exp(c3 * agepdt)) ** c4
    return hht2 - hht1


def calculate_ec_small_tree_height(
    species: str,
    mode: int,
    dtime: float,
    site_index: float,
    height: float = 0.0,
) -> float:
    """Port of Fortran ec/smhtgf.f.

    Args:
        species: Two-letter species code.
        mode: 0 for ESSUBH (DTIME is total age; returns height at that age),
              1 for REGENT (DTIME is interval; returns increment).
        dtime: Time parameter (years). See mode.
        site_index: Site index for the species (feet).
        height: Current tree height (feet). Used only for mode=1 non-linear
            equations (WP, RC) to solve for effective age.

    Returns:
        For mode=0: total height at age DTIME (feet).
        For mode=1: height increment over DTIME years (feet).
    """
    if dtime <= 0.0:
        return 0.0

    si = site_index
    idx = _EC_SPECIES_INDEX.get(species, 0)

    if idx == 1:  # WP
        return _wp_height(mode, dtime, si, height)
    elif idx in (2, 17):  # WL, LL
        return ((-3.97245 + 0.50995 * si) / (28.11668 - 0.05661 * si)) * dtime
    elif idx == 3:  # DF
        return ((2.0 + 0.420 * si) / (28.5 - 0.05 * si)) * dtime
    elif idx == 4:  # SF
        return ((-0.6667 + 0.4333 * si) / (28.5 - 0.05 * si)) * dtime
    elif idx == 5:  # RC
        return _rc_height(mode, dtime, si, height)
    elif idx in (6, 16):  # GF, WF
        return ((-1.0470 + 0.4220 * si) / (28.7739 - 0.0597 * si)) * dtime
    elif idx == 7:  # LP
        return (0.3277 + 0.01296 * si) * dtime
    elif idx == 8:  # ES
        return ((-8.0 + 0.35 * si) / (53.72545 - 0.274509 * si)) * dtime
    elif idx == 9:  # AF
        return ((6.0 + 0.14 * si) / (33.882 - 0.06588 * si)) * dtime
    elif idx == 10:  # PP
        return ((-1.0 + 0.32857 * si) / (28.0 - 0.042857 * si)) * dtime
    elif idx == 11:  # WH
        return ((-5.74874 + 0.54576 * si) / (26.15767 - 0.03596 * si)) * dtime
    elif idx in (12, 31):  # MH, OS (metric→feet conversion)
        return (((0.965758 + 0.082969 * si) / (55.249612 - 1.288852 * si))
                * dtime * 3.280833)
    elif idx in (13, 14, 18, 19, 20, 21, 23, 24, 25, 26, 27, 29, 30, 32):
        # PY, WB, YC, WJ, BM, VN, PB, GC, DG, AS, CW, PL, WI, OH
        return ((1.47043 + 0.23317 * si) / (31.56252 - 0.05586 * si)) * dtime
    elif idx == 15:  # NF
        return ((11.26677 + 0.12027 * si) / (27.93806 - 0.02873 * si)) * dtime
    elif idx == 22:  # RA
        return (-0.007025 + 0.056794 * si) * dtime
    elif idx == 28:  # WO
        return (((-37.60812 * math.log(1.0 - (si / 114.24569) ** 0.44444))
                 * 0.01) - 0.1) * dtime
    else:
        # Unknown species — use a conservative default (PY group).
        return ((1.47043 + 0.23317 * si) / (31.56252 - 0.05586 * si)) * dtime


# Fortran ec/blkdat.f:247-263 DATA HT1/HT2 Wykoff-form H-D coefficients
# for small-tree DBH dubbing (when D < 3.0). Formula:
#   HT = 4.5 + exp(HT1 + HT2/(DBH+1))
# Inverse:
#   DBH = HT2/(ln(HT-4.5) - HT1) - 1
_EC_WYKOFF_HT1: Dict[str, float] = {
    'WP': 5.035,  'WL': 4.961,  'DF': 4.920,  'SF': 5.032,  'RC': 4.896,
    'GF': 5.032,  'LP': 4.854,  'ES': 4.948,  'AF': 4.834,  'PP': 4.884,
    'WH': 5.298,  'MH': 3.9715, 'PY': 5.188,  'WB': 5.188,  'NF': 5.327,
    'WF': 5.032,  'LL': 5.188,  'YC': 5.143,  'WJ': 5.152,  'BM': 4.700,
    'VN': 4.700,  'RA': 4.886,  'PB': 5.152,  'GC': 5.152,  'DG': 5.152,
    'AS': 5.152,  'CW': 5.152,  'WO': 5.152,  'PL': 5.152,  'WI': 5.152,
    'OS': 3.9715, 'OH': 5.152,
}
_EC_WYKOFF_HT2: Dict[str, float] = {
    'WP': -10.674, 'WL':  -8.247, 'DF':  -9.003, 'SF': -10.482,
    'RC':  -8.391, 'GF': -10.482, 'LP':  -8.296, 'ES':  -9.041,
    'AF':  -9.042, 'PP':  -9.741, 'WH': -13.240, 'MH':  -6.7145,
    'PY': -13.801, 'WB': -13.801, 'NF': -15.450, 'WF': -10.482,
    'LL': -13.801, 'YC': -13.497, 'WJ': -13.576, 'BM':  -6.326,
    'VN':  -6.326, 'RA':  -8.792, 'PB': -13.576, 'GC': -13.576,
    'DG': -13.576, 'AS': -13.576, 'CW': -13.576, 'WO': -13.576,
    'PL': -13.576, 'WI': -13.576, 'OS':  -6.7145,'OH': -13.576,
}


def ec_wykoff_dbh_from_height(species: str, height: float) -> float:
    """Fortran ec/regent.f small-tree Wykoff H-D inverse for D < 3.

    DBH = HT2 / (ln(H - 4.5) - HT1) - 1. Returns 0.1 minimum for trees at
    or below breast height.
    """
    if height <= 4.5:
        return 0.1 + 0.001 * height
    ht1 = _EC_WYKOFF_HT1.get(species, 4.6618)
    ht2 = _EC_WYKOFF_HT2.get(species, -8.3312)
    denom = math.log(height - 4.5) - ht1
    if abs(denom) < 1e-9:
        return 0.1
    dbh = ht2 / denom - 1.0
    return max(0.1, dbh + 0.001 * height)

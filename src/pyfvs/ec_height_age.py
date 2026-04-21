"""EC (East Cascades) species-specific height-age curves from ec/htcalc.f.

Implements the per-species height-age equations used by ec/htgf.f (large-
tree height growth) via FINDAG + HTCALC. Many equations overlap with
PN/WC htcalc.f (Cochran PNW-252 for firs, Barrett PNW-232 for PP, etc.)
and a few are EC-unique (Cochran PNW-424 for WL/LL, Hegyi RC, Alexander
RM-29 LP polynomial).

Public API:
  height_at_age(species, age, site_index) -> height in feet
  age_from_height(species, height, site_index) -> age in years

Age convention: the Fortran htcalc.f passes AG = SITAGE + 10 from
htgf.f's FINDAG, where SITAGE is the effective age derived from the
species-specific height-age curve. The age is total age (not BH age)
in most equations; breast-height adjustments are baked into each
closed-form equation.
"""
from __future__ import annotations

import math

__all__ = ['height_at_age', 'age_from_height']


def _wp_height(ag: float, si: float) -> float:
    """Species 1 (WP) — Brickell INT-75. Base age 50."""
    if ag <= 0 or si <= 0:
        return 0.5
    denom = 0.37504453 * (1.0 - 0.92503 * math.exp(-0.0207959 * ag)) ** (-2.4881068)
    if denom <= 0:
        return 0.5
    return si / denom


def _wl_height(ag: float, si: float) -> float:
    """Species 2, 17 (WL, LL) — Cochran PNW-424. Polynomial in AG."""
    if ag <= 0 or si <= 0:
        return 0.5
    si_mod = si - 4.5
    ag2 = ag * ag
    ag3 = ag2 * ag
    ag4 = ag3 * ag
    fa = -0.12528 + 0.039636 * ag - 0.0004278 * ag2 + 1.7039e-6 * ag3
    return (
        4.5
        + 1.46897 * ag
        + 0.0092466 * ag2
        - 0.00023957 * ag3
        + 1.1122e-6 * ag4
        + si_mod * fa
        - 73.57 * fa
    )


def _df_height(ag: float, si: float) -> float:
    """Species 3 (DF) — Cochran PNW-251."""
    if ag <= 1.0 or si <= 4.5:
        return 4.5
    lna = math.log(ag)
    si_mod = si - 4.5
    return (
        4.5
        + math.exp(-0.37496 + 1.36164 * lna - 0.00243434 * lna ** 4)
        - 79.97 * (-0.2828 + 1.87947 * (1.0 - math.exp(-0.022399 * ag)) ** 0.966998)
        + si_mod * (
            -0.2828
            + 1.87947 * (1.0 - math.exp(-0.022399 * ag) ** 0.966998)
        )
    )


def _sf_gf_wf_height(ag: float, si: float) -> float:
    """Species 4, 6, 16 (SF, GF, WF) — Cochran PNW-252 log-polynomial."""
    if ag <= 1.0 or si <= 4.5:
        return 4.5
    lna = math.log(ag)
    lna2 = lna * lna
    lna4 = lna2 * lna2
    lna7 = lna4 * lna2 * lna
    lna9 = lna7 * lna2
    lna11 = lna9 * lna2
    lna16 = lna9 * lna7
    lna18 = lna16 * lna2
    lna24 = lna16 * lna4 * lna4
    x2 = (
        -0.30935 + 1.2383 * lna + 0.001762 * lna4
        - 5.4e-6 * lna9 + 2.046e-7 * lna11 - 4.04e-13 * lna18
    )
    x3 = (
        -6.2056 + 2.097 * lna - 0.09411 * lna2
        - 4.382e-5 * lna7 + 2.007e-11 * lna16 - 2.054e-17 * lna24
    )
    return math.exp(x2) - 84.73 * math.exp(x3) + (si - 4.5) * math.exp(x3) + 4.5


def _rc_height(ag: float, si: float) -> float:
    """Species 5 (RC) — Hegyi/Jelinek/Viszlai 1981."""
    if ag <= 0 or si <= 0:
        return 0.5
    return 1.3283 * si * (1.0 - math.exp(-0.0174 * ag)) ** 1.4711


def _lp_height(ag: float, si: float) -> float:
    """Species 7 (LP) — Alexander/Tackle/Dahms CCF 100, RM-29. Polynomial."""
    if ag <= 0 or si <= 0:
        return 0.5
    return (
        9.89331
        - 0.19177 * ag
        + 0.00124 * ag * ag
        + 0.01387 * ag * si
        - 0.0000455 * ag * ag * si
    )


def _es_height(ag: float, si: float) -> float:
    """Species 8 (ES) — Alexander RM-32."""
    if ag <= 0 or si <= 0:
        return 4.5
    try:
        asymptote = 2.75780 * (si ** 0.83312)
        exponent = 22.71944 * (si ** -0.63557)
        return 4.5 + asymptote * (1.0 - math.exp(-0.015701 * ag)) ** exponent
    except (ValueError, OverflowError):
        return 4.5


def _af_height(ag: float, si: float) -> float:
    """Species 9 (AF) — Johnson's equivalent of DeMars PNW-119."""
    if ag <= 0 or si <= 0:
        return 0.5
    return si * (-0.07831 + 0.0149 * ag - 4.0818e-5 * ag * ag)


def _pp_height(ag: float, si: float) -> float:
    """Species 10 (PP) — Barrett PNW-232. Same as PN/WC PP curve."""
    if ag <= 0 or si <= 4.5:
        return 4.5
    ft = -0.7864 + 2.49717 * (1.0 - math.exp(-0.004504 * ag)) ** 0.33022
    return (
        128.8952205 * (1.0 - math.exp(-0.016959 * ag)) ** 1.23114
        - ft * 100.43
        + ft * (si - 4.5)
        + 4.5
    )


def _wh_height(ag: float, si: float) -> float:
    """Species 11 (WH) — Wiley 1978."""
    if ag <= 0 or si <= 4.5:
        return 4.5
    z = 2500.0 / (si - 4.5)
    denom = (
        -1.7307 + 0.1394 * z
        + (-0.0616 + 0.0137 * z) * ag
        + (0.00192 + 0.00007 * z) * ag * ag
    )
    if abs(denom) < 1e-9:
        return 4.5
    return ag * ag / denom + 4.5


def _mh_os_height(ag: float, si: float) -> float:
    """Species 12, 31 (MH, OS) — Means metric converted to feet."""
    if ag <= 0 or si <= 0:
        return 0.5
    base = (22.8741 + 0.950234 * si) * (
        1.0 - math.exp(-0.00206465 * math.sqrt(si) * ag)
    ) ** (1.365566 + 2.045963 / si)
    return (base + 1.37) * 3.281


def _curtis_height(ag: float, si: float) -> float:
    """Species 13, 14, 18-21, 23-27, 29-30, 32 — Curtis For. Sci. 20."""
    if ag <= 0 or si <= 4.5:
        return 4.5
    denom = (
        0.6192
        - 5.3394 / (si - 4.5)
        + 240.29 * ag ** (-1.4)
        + (3368.9 / (si - 4.5)) * ag ** (-1.4)
    )
    if abs(denom) < 1e-9:
        return 4.5
    return (si - 4.5) / denom + 4.5


def _nf_height(ag: float, si: float) -> float:
    """Species 15 (NF) — Herman PNW-243."""
    if ag <= 0 or si <= 4.5:
        return 4.5
    si_mod = si - 4.5
    x1 = -564.38 + 22.25 * si_mod - 0.04995 * si_mod ** 2
    x2 = 6.80 + 2843.21 / si_mod + 34735.54 / (si_mod * si_mod)
    denom = x1 * (1.0 / ag) ** 2 + x2 * (1.0 / ag) + 1.0 - 0.0001 * x1 - 0.01 * x2
    if abs(denom) < 1e-9:
        return 4.5
    return 4.5 + si_mod / denom


def _ra_height(ag: float, si: float) -> float:
    """Species 22 (RA) — Harrington PNW-358."""
    if ag <= 0 or si <= 0:
        return 0.5
    term_a = (59.5864 + 0.7953 * si) * (
        1.0 - math.exp((0.00194 - 0.00074 * si) * ag)
    ) ** 0.9198
    term_b = (59.5864 + 0.7953 * si) * (
        1.0 - math.exp((0.00194 - 0.00074 * si) * 20.0)
    ) ** 0.9198
    return si + term_a - term_b


def _wo_height(ag: float, si: float) -> float:
    """Species 28 (WO) — King DF, Weyerhaeuser Forestry Paper No. 8."""
    if ag <= 0 or si <= 4.5:
        return 4.5
    z = 2500.0 / (si - 4.5)
    denom = (
        -0.954038
        + 0.109757 * z
        + (5.58178e-2 + 7.92236e-3 * z) * ag
        + (-7.33819e-4 + 1.97693e-4 * z) * ag * ag
    )
    if abs(denom) < 1e-9:
        return 4.5
    return ag * ag / denom + 4.5


_EC_SPECIES_INDEX = {
    'WP': 1, 'WL': 2, 'DF': 3, 'SF': 4, 'RC': 5, 'GF': 6, 'LP': 7,
    'ES': 8, 'AF': 9, 'PP': 10, 'WH': 11, 'MH': 12, 'PY': 13, 'WB': 14,
    'NF': 15, 'WF': 16, 'LL': 17, 'YC': 18, 'WJ': 19, 'BM': 20, 'VN': 21,
    'RA': 22, 'PB': 23, 'GC': 24, 'DG': 25, 'AS': 26, 'CW': 27, 'WO': 28,
    'PL': 29, 'WI': 30, 'OS': 31, 'OH': 32,
}


def height_at_age(species: str, age: float, site_index: float) -> float:
    """Predict total height at a given total age using ec/htcalc.f curves."""
    if age <= 0:
        return 0.5
    if site_index <= 0:
        return 0.5

    idx = _EC_SPECIES_INDEX.get(species, 0)
    if idx == 1:
        return max(0.5, _wp_height(age, site_index))
    elif idx in (2, 17):
        return max(0.5, _wl_height(age, site_index))
    elif idx == 3:
        return max(0.5, _df_height(age, site_index))
    elif idx in (4, 6, 16):
        return max(0.5, _sf_gf_wf_height(age, site_index))
    elif idx == 5:
        return max(0.5, _rc_height(age, site_index))
    elif idx == 7:
        return max(0.5, _lp_height(age, site_index))
    elif idx == 8:
        return max(0.5, _es_height(age, site_index))
    elif idx == 9:
        return max(0.5, _af_height(age, site_index))
    elif idx == 10:
        return max(0.5, _pp_height(age, site_index))
    elif idx == 11:
        return max(0.5, _wh_height(age, site_index))
    elif idx in (12, 31):
        return max(0.5, _mh_os_height(age, site_index))
    elif idx in (13, 14, 18, 19, 20, 21, 23, 24, 25, 26, 27, 29, 30, 32):
        return max(0.5, _curtis_height(age, site_index))
    elif idx == 15:
        return max(0.5, _nf_height(age, site_index))
    elif idx == 22:
        return max(0.5, _ra_height(age, site_index))
    elif idx == 28:
        return max(0.5, _wo_height(age, site_index))
    else:
        return max(0.5, _curtis_height(age, site_index))


def age_from_height(species: str, height: float, site_index: float) -> float:
    """Find total age corresponding to a given height.

    Dense-scan for ascending-branch crossings (same algorithm as
    pn_height_age.age_from_height — some EC curves are non-monotone in
    [0, 500]).
    """
    if height <= 0.5:
        return 0.1
    if site_index <= 0:
        return 0.1

    start_age = 1.0
    step = 2.0
    max_age = 300.0
    lo_age = start_age
    lo_h = height_at_age(species, lo_age, site_index)
    hi_age = lo_age
    hi_h = lo_h
    peak_h = lo_h
    peak_age = lo_age
    found = False
    while hi_age < max_age:
        nxt_age = hi_age + step
        nxt_h = height_at_age(species, nxt_age, site_index)
        if nxt_h > peak_h:
            peak_h = nxt_h
            peak_age = nxt_age
        if hi_h < height <= nxt_h:
            lo_age, lo_h = hi_age, hi_h
            hi_age, hi_h = nxt_age, nxt_h
            found = True
            break
        hi_age, hi_h = nxt_age, nxt_h

    if not found:
        if height > peak_h:
            return peak_age
        return start_age

    for _ in range(60):
        mid = (lo_age + hi_age) / 2.0
        h = height_at_age(species, mid, site_index)
        if abs(h - height) < 0.01:
            return mid
        if h < height:
            lo_age = mid
        else:
            hi_age = mid
    return (lo_age + hi_age) / 2.0

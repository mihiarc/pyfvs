"""PN/WC species-specific height-age curves from Fortran htcalc.f.

Implements 15 equation types covering all 39 PN/WC species. Each equation
predicts total height (feet) as a function of total age and site index.

Equations were extracted from the USDA Forest Service FVS Fortran source:
  pn/htcalc.f (Pacific Northwest Coast variant)

WC (West Cascades) overrides: DF, SS, RC use Curtis misc instead of their
PN-specific equations (King, Farr respectively).

Public API:
  height_at_age(species, age, site_index, variant) -> height in feet
  age_from_height(species, height, site_index, variant) -> age in years
"""
import math
from typing import Optional

__all__ = ['height_at_age', 'age_from_height']


# ============================================================================
# Years to breast height conversion coefficients (from sichg.f)
# years_to_bh = A + B * SI (minimum 1.0 year)
# ============================================================================

_YEARS_TO_BH = {
    'SF': (21.35000, -0.10290),
    'WF': (9.01840, -0.05700),
    'GF': (9.01840, -0.05700),
    'AF': (33.72545, -0.27451),
    'RF': (14.81367, -0.11174),
    'SS': (6.01954, -0.03636),
    'NF': (7.93806, -0.02873),
    'YC': (11.56252, -0.05586),
    'IC': (8.00000, -0.04286),
    'ES': (33.72545, -0.27451),
    'LP': (10.65724, -0.10667),
    'JP': (8.00000, -0.04259),
    'SP': (21.02281, -0.15978),
    'WP': (21.02281, -0.15978),
    'PP': (8.00000, -0.04286),
    'DF': (4.94166, -0.02419),
    'RW': (11.56252, -0.05586),
    'RC': (6.01954, -0.03636),
    'WH': (6.15767, -0.03596),
    'MH': (45.24969, -1.28885),
    'BM': (11.56252, -0.05586),
    'RA': (3.28241, -0.02987),
    'WA': (11.56252, -0.05586),
    'PB': (11.56252, -0.05586),
    'GC': (11.56252, -0.05586),
    'AS': (11.56252, -0.05586),
    'CW': (11.56252, -0.05586),
    'WO': (4.94166, -0.02419),
    'WJ': (11.56252, -0.05586),
    'LL': (8.11668, -0.05661),
    'WB': (11.56252, -0.05586),
    'KP': (11.56252, -0.05586),
    'PY': (11.56252, -0.05586),
    'DG': (11.56252, -0.05586),
    'HT': (11.56252, -0.05586),
    'CH': (11.56252, -0.05586),
    'WI': (11.56252, -0.05586),
    'OT': (11.56252, -0.05586),
}

_DEFAULT_YEARS_TO_BH = (11.56252, -0.05586)

# Species whose equations use total age (not breast height age)
_TOTAL_AGE_SPECIES = {'LP', 'RA'}


def _get_years_to_bh(species: str, site_index: float) -> float:
    """Compute years from planting to breast height."""
    a, b = _YEARS_TO_BH.get(species, _DEFAULT_YEARS_TO_BH)
    return max(1.0, a + b * site_index)


# ============================================================================
# Equation dispatch maps
# ============================================================================

_PN_EQUATION_MAP = {
    'SF': 'hoyer',
    'WF': 'cochran252', 'GF': 'cochran252',
    'AF': 'alexander', 'ES': 'alexander',
    'RF': 'dolph',
    'SS': 'farr',
    'NF': 'herman',
    'IC': 'barrett', 'JP': 'barrett', 'PP': 'barrett',
    'LP': 'dahms',
    'SP': 'curtis423', 'WP': 'curtis423',
    'DF': 'king', 'WO': 'king',
    'WH': 'wiley',
    'RC': 'farr',
    'MH': 'means',
    'RA': 'harrington',
    'LL': 'cochran424',
    # All others default to 'curtis_misc'
}

_WC_EQUATION_MAP = dict(_PN_EQUATION_MAP)
_WC_EQUATION_MAP['DF'] = 'curtis_misc'
_WC_EQUATION_MAP['SS'] = 'curtis_misc'
_WC_EQUATION_MAP['RC'] = 'curtis_misc'


# ============================================================================
# Individual equation implementations
# Each function takes (age, site_index) where age is breast-height age
# for most species, or total age for LP and RA.
# Returns total height in feet.
# ============================================================================

def _hoyer_height(bh_age: float, si: float) -> float:
    """Hoyer PNW-418: Pacific Silver Fir (SF). Base age 100 BH.

    H = (SI-4.5) * [(1-exp(-(k1+k2*SM45)*A))^p / (1-exp(-(k1+k2*SM45)*100))^p] + 4.5
    """
    sm45 = si - 4.5
    if sm45 <= 0 or bh_age <= 0:
        return 4.5
    rate = 0.0071839 + 0.0000571 * sm45
    p = 1.39005
    num = (1.0 - math.exp(-rate * bh_age)) ** p
    den = (1.0 - math.exp(-rate * 100.0)) ** p
    if den <= 0:
        return 4.5
    return sm45 * num / den + 4.5


def _cochran252_height(bh_age: float, si: float) -> float:
    """Cochran PNW-252: White Fir, Grand Fir (WF, GF). Base age 50 BH.

    Uses polynomial in ln(age) with anamorphic + polymorphic components.
    H = exp(X2) + (SI - 4.5 - 84.93) * exp(X3) + 4.5
    """
    if bh_age <= 0:
        return 4.5
    lg = math.log(max(0.1, bh_age))
    lg2 = lg * lg
    lg4 = lg2 * lg2
    lg7 = lg4 * lg2 * lg
    lg9 = lg7 * lg2
    lg11 = lg9 * lg2
    lg16 = lg9 * lg7
    lg18 = lg16 * lg2
    lg24 = lg16 * lg4 * lg4

    x2 = (-0.30935 + 1.2383 * lg + 0.001762 * lg4
           - 5.4e-6 * lg9 + 2.046e-7 * lg11 - 4.04e-13 * lg18)
    x3 = (-6.2056 + 2.097 * lg - 0.09411 * lg2
           - 4.382e-5 * lg7 + 2.007e-11 * lg16 - 2.054e-17 * lg24)

    return math.exp(x2) + (si - 4.5 - 84.93) * math.exp(x3) + 4.5


def _alexander_height(bh_age: float, si: float) -> float:
    """Alexander RM-32: Subalpine Fir, Engelmann Spruce (AF, ES). Base age 100 BH.

    H = 4.5 + 2.75780 * SI^0.83312 * (1 - exp(-0.015701*A))^(22.71944 * SI^-0.63557)
    """
    if bh_age <= 0 or si <= 4.5:
        return 4.5
    asymptote = 2.75780 * (si ** 0.83312)
    exponent = 22.71944 * (si ** -0.63557)
    return 4.5 + asymptote * (1.0 - math.exp(-0.015701 * bh_age)) ** exponent


def _dolph_height(bh_age: float, si: float) -> float:
    """Dolph PSW-206: California Red Fir (RF). Base age 50 BH.

    Variable-rate Chapman-Richards with age-dependent rate parameter.
    """
    if bh_age <= 0 or si <= 4.5:
        return 4.5
    sm45 = si - 4.5

    def _term(a):
        return a * math.exp(-0.0440853 * a) * 1.4151e-6

    def _b(a):
        t = _term(a)
        return si * t - 3.0495e6 * t * t + 5.72474e-4

    b_age = _b(bh_age)
    b_50 = _b(50.0)

    try:
        num = 1.0 - math.exp(-b_age * (bh_age ** 1.51744))
        den = 1.0 - math.exp(-b_50 * (50.0 ** 1.51744))
    except (OverflowError, ValueError):
        return 4.5

    if den <= 0:
        return 4.5
    return sm45 * num / den + 4.5


def _farr_height(bh_age: float, si: float) -> float:
    """Farr PNW-326: Sitka Spruce, W. Redcedar (SS, RC). Base age 50 BH.

    Polynomial in ln(age), same functional form as Cochran PNW-252.
    H = 4.5 + exp(AZ) + (SI - 4.5 - 86.43) * exp(BZ)
    """
    if bh_age <= 0:
        return 4.5
    lg = math.log(max(0.1, bh_age))
    lg2 = lg * lg
    lg3 = lg2 * lg
    lg5 = lg3 * lg2
    lg16 = lg5 * lg5 * lg5 * lg
    lg30 = lg16 * lg5 * lg5 * lg3 * lg
    lg36 = lg30 * lg3 * lg3

    az = (-0.2050542 + 1.449615 * lg - 0.01780992 * lg3
          + 6.519748e-5 * lg5 - 1.095593e-23 * lg30)
    bz = (-5.611879 + 2.418604 * lg - 0.2593110 * lg2
          + 1.351445e-4 * lg5 - 1.701139e-12 * lg16
          + 7.964197e-27 * lg36)

    return 4.5 + math.exp(az) + (si - 4.5 - 86.43) * math.exp(bz)


def _herman_height(bh_age: float, si: float) -> float:
    """Herman PNW-243: Noble Fir (NF). Base age 100 BH.

    Rational function: H = 4.5 + S / (X1/A^2 + X2/A + 1 - 0.0001*X1 - 0.01*X2)
    """
    if bh_age <= 0 or si <= 4.5:
        return 4.5
    s = si - 4.5
    x1 = -564.38 + 22.25 * s - 0.04995 * s * s
    x2 = 6.80 + 2843.21 / s + 34735.54 / (s * s)
    inv_a = 1.0 / bh_age
    den = x1 * inv_a * inv_a + x2 * inv_a + 1.0 - 0.0001 * x1 - 0.01 * x2
    if den <= 0:
        return 4.5
    return 4.5 + s / den


def _barrett_height(bh_age: float, si: float) -> float:
    """Barrett PNW-232: IC, JP, PP. Base age 100 BH.

    Chapman-Richards + linear SI modifier:
    H = 128.8952205*(1-exp(-0.016959*A))^1.23114 + F(A)*(SI-4.5-100.43) + 4.5
    where F(A) = -0.7864 + 2.49717*(1-exp(-0.0045042*A))^0.33022
    """
    if bh_age <= 0:
        return 4.5
    base_curve = 128.8952205 * (1.0 - math.exp(-0.016959 * bh_age)) ** 1.23114
    f_a = -0.7864 + 2.49717 * (1.0 - math.exp(-0.0045042 * bh_age)) ** 0.33022
    return base_curve + f_a * (si - 4.5 - 100.43) + 4.5


def _dahms_height(total_age: float, si: float) -> float:
    """Dahms PNW-8: Lodgepole Pine (LP). Base age 50 TOTAL.

    Simple quadratic: H = SI * (-0.0968 + 0.02679*A - 0.00009309*A^2)
    """
    if total_age <= 0 or si <= 0:
        return 0.5
    h = si * (-0.0968 + 0.02679 * total_age - 0.00009309 * total_age * total_age)
    return max(0.5, h)


def _curtis423_height(bh_age: float, si: float) -> float:
    """Curtis PNW-423: Sugar Pine, W. White Pine (SP, WP). Base age 100 BH.

    Double exponential: G(A) = 1 - exp(-exp(-4.62536 + 1.346399*ln(A) - 135.354483/SI))
    H = G(A)/G(100) * (SI-4.5) + 4.5
    """
    if bh_age <= 0.1 or si <= 4.5:
        return 4.5
    sm45 = si - 4.5
    ln_a = math.log(bh_age)
    ln_100 = math.log(100.0)  # 4.60517

    def _g(ln_age):
        try:
            inner = -4.62536 + 1.346399 * ln_age - 135.354483 / si
            return 1.0 - math.exp(-math.exp(inner))
        except (OverflowError, ValueError):
            return 1.0

    g_a = _g(ln_a)
    g_100 = _g(ln_100)
    if g_100 <= 0:
        return 4.5
    return sm45 * g_a / g_100 + 4.5


def _king_height(bh_age: float, si: float) -> float:
    """King 1966: Douglas-fir, Oregon White Oak (DF, WO). Base age 50 BH.

    Rational function:
    H = A^2 / (a0 + a1*Z + (b0+b1*Z)*A + (c0+c1*Z)*A^2) + 4.5
    where Z = 2500/(SI-4.5)
    """
    if bh_age <= 0 or si <= 4.5:
        return 4.5
    z = 2500.0 / (si - 4.5)
    a_sq = bh_age * bh_age
    den = (-0.954038 + 0.109757 * z
           + (0.0558178 + 0.00792236 * z) * bh_age
           + (-0.000733819 + 0.000197693 * z) * a_sq)
    if den <= 0:
        return 4.5
    return a_sq / den + 4.5


def _wiley_height(bh_age: float, si: float) -> float:
    """Wiley 1978: Western Hemlock (WH). Base age 50 BH.

    Same rational form as King:
    H = A^2 / (a0 + a1*Z + (b0+b1*Z)*A + (c0+c1*Z)*A^2) + 4.5
    """
    if bh_age <= 0 or si <= 4.5:
        return 4.5
    z = 2500.0 / (si - 4.5)
    a_sq = bh_age * bh_age
    den = (-1.7307 + 0.1394 * z
           + (-0.0616 + 0.0137 * z) * bh_age
           + (0.00192 + 0.00007 * z) * a_sq)
    if den <= 0:
        return 4.5
    return a_sq / den + 4.5


def _means_height(bh_age: float, si: float) -> float:
    """Means (unpublished): Mountain Hemlock (MH). Base age 100 BH.

    Equation calibrated in metric; SI converted from feet to meters internally.
    H_m = (22.8741 + 0.950234*SI_m) * (1-exp(-0.00206465*sqrt(SI_m)*A))^(1.365566+2.045963/SI_m)
    H_ft = (H_m + 1.37) * 3.281
    """
    if bh_age <= 0 or si <= 4.5:
        return 4.5
    si_m = si / 3.281
    if si_m <= 0:
        return 4.5
    asymptote = 22.8741 + 0.950234 * si_m
    rate = 0.00206465 * math.sqrt(si_m)
    exponent = 1.365566 + 2.045963 / si_m
    try:
        h_m = asymptote * (1.0 - math.exp(-rate * bh_age)) ** exponent
    except (OverflowError, ValueError):
        h_m = asymptote
    return (h_m + 1.37) * 3.281


def _harrington_height(total_age: float, si: float) -> float:
    """Harrington PNW-358: Red Alder (RA). Base age 20 TOTAL.

    Difference form: H = SI + F(A) - F(20)
    where F(A) = (59.5864 + 0.7953*SI) * (1-exp((0.00194-0.0007403*SI)*A))^0.9198
    """
    if total_age <= 0 or si <= 0:
        return 0.5
    coeff = 59.5864 + 0.7953 * si
    rate = 0.00194 - 0.0007403 * si  # typically negative for SI > 2.6

    def _f(a):
        try:
            return coeff * (1.0 - math.exp(rate * a)) ** 0.9198
        except (OverflowError, ValueError):
            return coeff

    return max(0.5, si + _f(total_age) - _f(20.0))


def _cochran424_height(bh_age: float, si: float) -> float:
    """Cochran PNW-424: Subalpine Larch (LL). Base age 50 BH.

    Polynomial + SI modifier:
    H = 4.5 + P(A) + (SI - 4.5 - 73.57) * G(A)
    P(A) = 1.46897*A + 0.0092466*A^2 - 2.3957e-4*A^3 + 1.1122e-6*A^4
    G(A) = -0.12528 + 0.039636*A - 4.278e-4*A^2 + 1.7039e-6*A^3
    """
    if bh_age <= 0:
        return 4.5
    a = bh_age
    a2 = a * a
    a3 = a2 * a
    a4 = a3 * a
    p_a = 1.46897 * a + 0.0092466 * a2 - 2.3957e-4 * a3 + 1.1122e-6 * a4
    g_a = -0.12528 + 0.039636 * a - 4.278e-4 * a2 + 1.7039e-6 * a3
    return 4.5 + p_a + (si - 4.5 - 73.57) * g_a


def _curtis_misc_height(bh_age: float, si: float) -> float:
    """Curtis misc (1974): Miscellaneous species. Base age ~100 BH.

    H = S / (0.6192 - 5.3394/S + (240.29 + 3368.9/S) * A^-1.4) + 4.5
    where S = SI - 4.5
    """
    if bh_age <= 0 or si <= 4.5:
        return 4.5
    s = si - 4.5
    try:
        a_pow = bh_age ** (-1.4)
    except (ZeroDivisionError, ValueError):
        return 4.5
    den = 0.6192 - 5.3394 / s + (240.29 + 3368.9 / s) * a_pow
    if den <= 0:
        return 4.5
    return s / den + 4.5


# ============================================================================
# Dispatch table
# ============================================================================

_EQUATION_FUNCS = {
    'hoyer': _hoyer_height,
    'cochran252': _cochran252_height,
    'alexander': _alexander_height,
    'dolph': _dolph_height,
    'farr': _farr_height,
    'herman': _herman_height,
    'barrett': _barrett_height,
    'dahms': _dahms_height,
    'curtis423': _curtis423_height,
    'king': _king_height,
    'wiley': _wiley_height,
    'means': _means_height,
    'harrington': _harrington_height,
    'cochran424': _cochran424_height,
    'curtis_misc': _curtis_misc_height,
}


def _get_equation(species: str, variant: str):
    """Get the equation function for a species and variant."""
    eq_map = _WC_EQUATION_MAP if variant == 'WC' else _PN_EQUATION_MAP
    eq_name = eq_map.get(species, 'curtis_misc')
    return _EQUATION_FUNCS[eq_name]


# ============================================================================
# Public API
# ============================================================================

def height_at_age(species: str, age: float, site_index: float,
                  variant: str = 'PN') -> float:
    """Predict total height at a given total age using species-specific curves.

    Dispatches to the appropriate height-age equation for the species and
    variant. Handles breast-height-age conversion internally.

    Args:
        species: PN/WC species code (e.g., 'DF', 'WH', 'RC')
        age: Total age in years (not breast height age)
        site_index: Site index in feet (base age varies by species/equation)
        variant: 'PN' or 'WC' (affects equation selection for DF, SS, RC)

    Returns:
        Total height in feet (minimum 0.5)
    """
    if age <= 0:
        return 0.5
    if site_index <= 0:
        return 0.5

    eq_func = _get_equation(species, variant)

    if species in _TOTAL_AGE_SPECIES:
        # LP (Dahms) and RA (Harrington) use total age directly
        return max(0.5, eq_func(age, site_index))
    else:
        # All other species use breast height age
        ytbh = _get_years_to_bh(species, site_index)
        bh_age = age - ytbh
        if bh_age <= 0:
            # Sub-breast-height: linear from 0.5 at age 0 to 4.5 at age ytbh
            return 0.5 + 4.0 * (age / ytbh)
        return max(4.5, eq_func(bh_age, site_index))


def age_from_height(species: str, height: float, site_index: float,
                    variant: str = 'PN') -> float:
    """Find total age corresponding to a given height via bisection.

    Most FVS height-age equations are concave and eventually saturate,
    but the Cochran PNW-252 polynomial (WF/GF) is a log-polynomial that
    peaks near age 150 and decays afterwards. Naive bisection in
    [0.1, 500] walks past the peak onto the decaying branch and returns
    the sentinel upper bound. Scan to find the ascending-branch bracket
    before bisecting.

    Args:
        species: PN/WC species code
        height: Total height in feet
        site_index: Site index in feet
        variant: 'PN' or 'WC'

    Returns:
        Estimated total age in years (minimum 0.1)
    """
    if height <= 0.5:
        return 0.1
    if site_index <= 0:
        return 0.1

    # Analytical inverse for sub-breast-height trees (BH-age species only)
    if species not in _TOTAL_AGE_SPECIES and height < 4.5:
        ytbh = _get_years_to_bh(species, site_index)
        return max(0.1, (height - 0.5) * ytbh / 4.0)

    # Find the ASCENDING-BRANCH crossing age.
    #
    # Some Fortran height-age equations are non-monotone over [0, 500]:
    #   - Barrett PNW-232 (IC/JP/PP) has an off-base-SI artifact at
    #     bh_age→0 that produces a local max then a dip before climbing
    #     monotonically through the target.
    #   - Cochran PNW-252 (WF/GF) is a log-polynomial that peaks near
    #     age=150 and decays afterwards.
    #
    # A simulated tree grows monotonically up through the curve, so the
    # correct answer is always the rightmost ascending-branch crossing
    # where the curve transitions from below to at-or-above the target.
    # Dense-scan to find that crossing.
    if species in _TOTAL_AGE_SPECIES:
        start_age = 1.0
    else:
        ytbh = _get_years_to_bh(species, site_index)
        start_age = max(1.0, ytbh + 0.5)
    step = 2.0
    max_age = 300.0  # upper bound for any realistic tree
    lo_age = start_age
    lo_h = height_at_age(species, lo_age, site_index, variant)
    hi_age = lo_age
    hi_h = lo_h
    peak_h = lo_h
    peak_age = lo_age
    found = False
    while hi_age < max_age:
        nxt_age = hi_age + step
        nxt_h = height_at_age(species, nxt_age, site_index, variant)
        if nxt_h > peak_h:
            peak_h = nxt_h
            peak_age = nxt_age
        # Detect ascending transition across the target:
        if hi_h < height <= nxt_h:
            lo_age, lo_h = hi_age, hi_h
            hi_age, hi_h = nxt_age, nxt_h
            found = True
            break
        hi_age, hi_h = nxt_age, nxt_h
    if not found:
        # Target above curve's max: return peak age. Target above the
        # start_age but below h at start and never reached: return
        # start_age (ascending bracket starts there).
        if height > peak_h:
            return peak_age
        return start_age

    # Bisection within the confirmed ascending bracket [lo_age, hi_age].
    for _ in range(60):
        mid = (lo_age + hi_age) / 2.0
        h = height_at_age(species, mid, site_index, variant)
        if abs(h - height) < 0.01:
            return mid
        if h < height:
            lo_age = mid
        else:
            hi_age = mid
    return (lo_age + hi_age) / 2.0

"""
Clark Profile Volume Equations for Southern Species.

Implements the segmented taper model from Clark et al. (1991) SE-282.
Ported from USDA Forest Service NVEL Fortran source (r8vol2.f).

Reference:
    Clark, A., Souter, R.A., & Schlaegel, B.E. (1991). Stem Profile Equations
    for Southern Tree Species. Research Paper SE-282. USDA Forest Service.
"""
from typing import Dict, Tuple
from dataclasses import dataclass


@dataclass
class ClarkCoefficients:
    """Coefficients for Clark profile model.

    Source: NVEL r8vol2.f TOTAL array (inside-bark taper) and
    r8dib.inc R8CF array (bark ratio, form class).
    """
    # Total height equation coefficients (inside bark, from TOTAL array)
    R: float  # Butt taper exponent
    C: float  # Butt taper coefficient
    E: float  # Butt taper DBH adjustment
    P: float  # Middle taper exponent
    B: float  # Upper taper coefficient
    A: float  # Upper taper transition point

    # Bark ratio at BH (from R8CF cols 4-5)
    AD: float  # Intercept for DIB = AD + BD * DOB
    BD: float  # Slope for DIB calculation

    # Form class coefficients (diameter at 17.3 ft, from R8CF cols 14-15)
    AF: float  # Form class intercept: FCLSS = DBH * (AF + BF * (17.3/THT)^2)
    BF: float  # Form class slope (negative for most species)

    # Species group (from R8CF col 3): 100=softwood, 200=hardwood, 300=cypress
    SPGRP: int = 100

    # Inverse bark ratio for form class (from R8CF cols 6-7)
    # Used to convert FCLSS (DIB) to FCDOB (DOB): FCDOB = (FCLSS - AFI) / BFI
    AFI: float = 0.0
    BFI: float = 1.0


# Clark profile coefficients for southern pines
# Taper (R,C,E,P,B,A): from NVEL r8vol2.f TOTAL(49,7)
# Bark/form class (AD,BD,AF,BF,AFI,BFI): from NVEL r8dib.inc R8CF(182,18)
# Geographic area 1 used (default for Region 8)
CLARK_COEFFICIENTS: Dict[str, ClarkCoefficients] = {
    # Loblolly Pine (FIA 131) — r8vol2.f line 106, r8dib.inc area 1
    'LP': ClarkCoefficients(
        R=31.66250, C=0.57402, E=110.96000, P=8.57300, B=2.36238, A=0.68464,
        AD=-0.49634, BD=0.91369,
        AF=0.84885, BF=-1.30374,
        SPGRP=100, AFI=-0.28939, BFI=0.93389,
    ),
    # Shortleaf Pine (FIA 110) — r8vol2.f line 98, r8dib.inc area 2
    'SP': ClarkCoefficients(
        R=25.43531, C=0.45525, E=28.38927, P=8.21438, B=2.86552, A=0.72623,
        AD=-0.52087, BD=0.93222,
        AF=0.87910, BF=-1.30480,
        SPGRP=100, AFI=-0.23829, BFI=0.93332,
    ),
    # Slash Pine (FIA 111) — r8vol2.f line 99, r8dib.inc area 1
    'SA': ClarkCoefficients(
        R=32.39761, C=0.77487, E=-2.25836, P=4.80100, B=2.52226, A=0.73935,
        AD=-0.42543, BD=0.90211,
        AF=0.85504, BF=-1.52260,
        SPGRP=100, AFI=-0.40470, BFI=0.92183,
    ),
    # Longleaf Pine (FIA 121) — r8vol2.f line 101, r8dib.inc area 1
    'LL': ClarkCoefficients(
        R=24.40837, C=0.46799, E=10.67266, P=3.59700, B=2.03709, A=0.65814,
        AD=-0.50845, BD=0.93246,
        AF=0.84822, BF=-0.94775,
        SPGRP=100, AFI=-0.38680, BFI=0.93848,
    ),
}


def calculate_dib(dbh: float, ad: float, bd: float) -> float:
    """Calculate diameter inside bark at breast height.

    Args:
        dbh: Diameter at breast height outside bark (inches)
        ad: Intercept coefficient
        bd: Slope coefficient

    Returns:
        Diameter inside bark (inches)
    """
    dib = ad + bd * dbh
    return max(dib, 0.1)  # Ensure positive


def _get_fcmin(spgrp: int, tht: float) -> int:
    """Get minimum form class percentage from NVEL r8vol2.f TOTHT lines 745-764.

    Args:
        spgrp: Species group (100=softwood, 200/500=hardwood, 300=cypress)
        tht: Total tree height (feet)

    Returns:
        Minimum form class as integer percentage (56-69)
    """
    if spgrp == 100:  # Softwood
        if tht < 32.5:
            return 56
        elif tht < 37.5:
            return 64
        elif tht < 42.5:
            return 66
        else:
            return 67
    elif spgrp == 300:  # Cypress
        if tht < 32.5:
            return 57
        elif tht < 37.5:
            return 60
        elif tht < 42.5:
            return 64
        else:
            return 67
    else:  # Hardwood / default (200, 500)
        if tht < 32.5:
            return 58
        elif tht < 37.5:
            return 65
        elif tht < 42.5:
            return 67
        else:
            return 69


def calculate_form_class(dbh: float, total_height: float, af: float, bf: float,
                         spgrp: int = 100) -> float:
    """Calculate form class (diameter inside bark at 17.3 feet).

    Matches NVEL r8vol2.f TOTHT: computes FCLSS from the AF/BF regression,
    then enforces the species-group/height minimum form class (FCMIN).

    Args:
        dbh: DBH outside bark (inches)
        total_height: Total tree height (feet)
        af: Form class intercept (from R8CF col 14)
        bf: Form class slope (from R8CF col 15, typically negative)
        spgrp: Species group (100, 200/500, 300)

    Returns:
        Form class diameter inside bark (inches)
    """
    if total_height <= 17.3:
        return dbh * 0.7

    fclss = dbh * (af + bf * (17.3 / total_height) ** 2)
    if fclss < 0.0:
        fclss = 0.0

    # Apply species-group/height minimum (r8vol2.f lines 745-764)
    fcmin = _get_fcmin(spgrp, total_height)
    fcdib = dbh * fcmin * 0.01
    if total_height < 47.5 and fclss < fcdib:
        fclss = fcdib

    return max(fclss, 0.1)


def _compute_clark_volume(dbh: float, tht: float, coef: ClarkCoefficients,
                          fclss: float, upper: float) -> float:
    """Core Clark volume integration (NVEL r8vol2.f TOTHT lines 835-887).

    Computes cubic foot volume from stump (0.5 ft) to `upper` height using
    the three-segment Clark profile model.

    Args:
        dbh: DBH outside bark (inches)
        tht: Total tree height (feet) — defines the profile shape
        coef: Clark profile coefficients
        fclss: Form class diameter inside bark at 17.3 ft
        upper: Upper integration limit (feet)

    Returns:
        Cubic foot volume (inside bark)
    """
    dib = calculate_dib(dbh, coef.AD, coef.BD)
    dib2 = dib ** 2
    dib3 = dib ** 3
    fclss2 = fclss ** 2

    V = (1 - 4.5 / tht) ** coef.R
    W = (coef.C + coef.E / dib3) / (1 - V) if V < 1 else 0
    X = (1 - 4.5 / tht) ** coef.P
    Y = (1 - 17.3 / tht) ** coef.P if tht > 17.3 else 0
    Z = (dib2 - fclss2) / (X - Y) if abs(X - Y) > 0.001 else 0
    T = dib2 - Z * X

    L1, U1 = 0.5, min(4.5, upper)
    L2 = 4.5
    U2 = min(17.3, upper)
    L3, U3 = 17.3, min(tht, upper)

    # Segment 1: Butt (0.5 to 4.5 ft)
    S1 = 0.0
    if tht > 0.5:
        t_l1 = (1 - L1 / tht) ** coef.R * (tht - L1) if L1 < tht else 0
        t_u1 = (1 - U1 / tht) ** coef.R * (tht - U1) if U1 < tht else 0
        S1 = dib2 * ((1 - V * W) * (U1 - L1) + W * (t_l1 - t_u1) / (coef.R + 1))

    # Segment 2: Middle (4.5 to 17.3 ft)
    S2 = 0.0
    if upper > 4.5:
        t_l2 = (1 - L2 / tht) ** coef.P * (tht - L2) if L2 < tht else 0
        t_u2 = (1 - U2 / tht) ** coef.P * (tht - U2) if U2 < tht else 0
        S2 = T * (U2 - L2) + Z * (t_l2 - t_u2) / (coef.P + 1)

    # Segment 3: Upper (17.3 ft to tip/upper)
    S3 = 0.0
    if upper > 17.3:
        A, B = coef.A, coef.B
        tht_17 = tht - 17.3
        I5 = 1 if (L3 - 17.3) < A * tht_17 else 0
        I6 = 1 if (U3 - 17.3) < A * tht_17 else 0

        S3_b = B * (U3 - L3)
        S3_b -= B * ((U3 - 17.3) ** 2 - (L3 - 17.3) ** 2) / tht_17
        S3_b += (B / 3) * ((U3 - 17.3) ** 3 - (L3 - 17.3) ** 3) / tht_17 ** 2
        if I5:
            S3_b += (1 / 3) * ((1 - B) / A ** 2) * (A * tht_17 - (L3 - 17.3)) ** 3 / tht_17 ** 2
        if I6:
            S3_b -= (1 / 3) * ((1 - B) / A ** 2) * (A * tht_17 - (U3 - 17.3)) ** 3 / tht_17 ** 2
        S3 = fclss2 * S3_b

    return 0.005454 * (S1 + S2 + S3)


def clark_total_cubic_volume(dbh: float, total_height: float,
                             coef: ClarkCoefficients) -> float:
    """Calculate total cubic volume using Clark profile model.

    Implements the TOTHT subroutine from NVEL r8vol2.f, including:
    - Species-group/height minimum form class (FCMIN)
    - Iterative correction for trees >= 47.5 ft (lines 889-895)

    Args:
        dbh: Diameter at breast height outside bark (inches)
        total_height: Total tree height (feet)
        coef: Clark profile coefficients

    Returns:
        Total cubic foot volume (inside bark)
    """
    if dbh <= 0 or total_height <= 4.5:
        return 0.0

    tht = total_height
    fclss = calculate_form_class(dbh, tht, coef.AF, coef.BF, coef.SPGRP)

    # Compute FCDIB for iterative correction check
    fcmin = _get_fcmin(coef.SPGRP, tht)
    fcdib = dbh * fcmin * 0.01

    vol = _compute_clark_volume(dbh, tht, coef, fclss, tht)

    # Iterative correction (r8vol2.f lines 889-895):
    # For tall trees where form class fell below minimum, recalculate
    # at THT=47.49 and take the higher volume.
    if tht >= 47.5 and fclss < fcdib:
        volini = vol
        fclss2 = calculate_form_class(dbh, 47.49, coef.AF, coef.BF, coef.SPGRP)
        vol2 = _compute_clark_volume(dbh, 47.49, coef, fclss2, 47.49)
        if volini > vol2:
            vol = volini

    return max(vol, 0.0)


def clark_merchantable_volume(dbh: float, total_height: float,
                              coef: ClarkCoefficients,
                              top_dib: float = 4.0,
                              stump_height: float = 0.5) -> float:
    """Calculate merchantable cubic volume to a specified top diameter.

    Args:
        dbh: DBH outside bark (inches)
        total_height: Total tree height (feet)
        coef: Clark coefficients
        top_dib: Minimum top diameter inside bark (inches), default 4"
        stump_height: Stump height (feet), default 0.5

    Returns:
        Merchantable cubic foot volume
    """
    if dbh <= 0 or total_height <= 4.5:
        return 0.0

    # Calculate DIB
    dib = calculate_dib(dbh, coef.AD, coef.BD)

    # If DIB is less than top diameter, no merchantable volume
    if dib <= top_dib:
        return 0.0

    # Estimate merchantable height using simplified taper
    # Height where diameter equals top_dib
    merch_ratio = 1 - (top_dib / dib)
    merch_height = total_height * merch_ratio

    # Ensure reasonable bounds
    merch_height = max(stump_height + 1, min(merch_height, total_height - 4))

    # Calculate total volume to merchantable height
    # Use ratio adjustment (simplified approach)
    total_vol = clark_total_cubic_volume(dbh, total_height, coef)

    # Merchantable ratio based on height
    if total_height > 0:
        vol_ratio = merch_height / total_height
        # Adjust for volume concentration in lower stem
        vol_ratio = min(0.92, vol_ratio * 1.05)
    else:
        vol_ratio = 0.85

    return total_vol * vol_ratio


def calculate_volume_clark(dbh: float, height: float, species: str) -> Tuple[float, float]:
    """Calculate volume using Clark profile equations.

    Args:
        dbh: Diameter at breast height (inches)
        height: Total tree height (feet)
        species: FVS species code ('LP', 'SP', 'SA', 'LL')

    Returns:
        Tuple of (total_cubic_volume, merchantable_cubic_volume)
    """
    coef = CLARK_COEFFICIENTS.get(species)
    if coef is None:
        # Fall back to loblolly pine coefficients
        coef = CLARK_COEFFICIENTS['LP']

    total_vol = clark_total_cubic_volume(dbh, height, coef)
    merch_vol = clark_merchantable_volume(dbh, height, coef)

    return total_vol, merch_vol


# Comparison function for validation
def compare_volume_methods(dbh: float, height: float, species: str = 'LP') -> Dict[str, float]:
    """Compare Clark profile vs combined-variable volume equations.

    Args:
        dbh: DBH (inches)
        height: Total height (feet)
        species: Species code

    Returns:
        Dictionary with volume comparisons
    """
    # Clark profile
    clark_total, clark_merch = calculate_volume_clark(dbh, height, species)

    # Combined-variable (Amateis & Burkhart 1987)
    d2h = dbh * dbh * height
    ab_total = 0.00828 + 0.00205 * d2h  # Outside bark
    ab_inside = max(0, -0.09653 + 0.00210 * d2h)  # Inside bark

    # Current FVS-Python
    fvs_total = 0.18658 + 0.00250 * d2h

    return {
        'dbh': dbh,
        'height': height,
        'd2h': d2h,
        'clark_total': clark_total,
        'clark_merch': clark_merch,
        'amateis_burkhart_ob': ab_total,
        'amateis_burkhart_ib': ab_inside,
        'fvs_python_current': fvs_total,
        'clark_vs_ab': (clark_total / ab_total - 1) * 100 if ab_total > 0 else 0,
        'clark_vs_fvs': (clark_total / fvs_total - 1) * 100 if fvs_total > 0 else 0,
    }


if __name__ == "__main__":
    # Test comparison
    print("Clark Profile vs Combined-Variable Volume Equations")
    print("=" * 80)
    print(f"{'DBH':>6} {'Ht':>5} {'D²H':>8} | {'Clark':>8} {'A&B OB':>8} {'FVS-Py':>8} | {'Clk/AB':>7} {'Clk/FVS':>7}")
    print("-" * 80)

    test_trees = [
        (5, 30), (8, 50), (10, 60), (12, 70), (15, 80), (18, 85), (20, 90)
    ]

    for dbh, ht in test_trees:
        result = compare_volume_methods(dbh, ht, 'LP')
        print(f"{dbh:>6.1f} {ht:>5.0f} {result['d2h']:>8.0f} | "
              f"{result['clark_total']:>8.2f} {result['amateis_burkhart_ob']:>8.2f} "
              f"{result['fvs_python_current']:>8.2f} | "
              f"{result['clark_vs_ab']:>+6.1f}% {result['clark_vs_fvs']:>+6.1f}%")

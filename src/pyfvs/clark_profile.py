"""
Clark Profile Volume Equations for Southern Species.

Implements the segmented taper model from Clark et al. (1991) SE-282.
Ported from USDA Forest Service NVEL Fortran source (r8vol2.f).

Reference:
    Clark, A., Souter, R.A., & Schlaegel, B.E. (1991). Stem Profile Equations
    for Southern Tree Species. Research Paper SE-282. USDA Forest Service.
"""
import math
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ClarkCoefficients:
    """Coefficients for Clark profile model."""
    # Total height equation coefficients (inside bark)
    R: float  # Butt taper exponent
    C: float  # Butt taper coefficient
    E: float  # Butt taper DBH adjustment
    P: float  # Middle taper exponent
    B: float  # Upper taper coefficient
    A: float  # Upper taper transition point

    # Bark ratio coefficients
    AD: float  # Intercept for DIB = AD + BD * DOB
    BD: float  # Slope for DIB calculation

    # Form class coefficients (diameter at 17.3 ft)
    AF: float  # Form class intercept
    BF: float  # Form class slope


# Clark profile coefficients for southern pines
# Extracted from NVEL r8vol2.f TOTAL array (inside bark, total height)
CLARK_COEFFICIENTS: Dict[str, ClarkCoefficients] = {
    # Loblolly Pine (131) - from r8vol2.f line 106
    'LP': ClarkCoefficients(
        R=31.66250, C=0.57402, E=110.96000, P=8.57300, B=2.36238, A=0.68464,
        AD=-0.48140, BD=0.91413,  # From bark ratio coefficients
        AF=0.7618, BF=0.1596      # Form class from r8dib.inc
    ),
    # Shortleaf Pine (132) - from r8vol2.f line 107
    'SP': ClarkCoefficients(
        R=8.77959, C=0.30226, E=27.58681, P=7.18305, B=2.07630, A=0.61061,
        AD=-0.56870, BD=0.92470,
        AF=0.7618, BF=0.1596
    ),
    # Slash Pine (121) - from r8vol2.f line 101
    'SA': ClarkCoefficients(
        R=24.40837, C=0.46799, E=10.67266, P=3.59700, B=2.03709, A=0.65814,
        AD=-0.40380, BD=0.91430,
        AF=0.7618, BF=0.1596
    ),
    # Longleaf Pine (121 approximated by 129 - Sand Pine closest)
    'LL': ClarkCoefficients(
        R=12.19768, C=0.35840, E=19.63087, P=10.31373, B=1.74982, A=0.60458,
        AD=-0.39470, BD=0.90970,
        AF=0.7618, BF=0.1596
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


def calculate_form_class(dbh: float, total_height: float, af: float, bf: float) -> float:
    """Calculate form class (diameter at 17.3 feet).

    Args:
        dbh: DBH outside bark (inches)
        total_height: Total tree height (feet)
        af: Form class intercept
        bf: Form class slope

    Returns:
        Form class diameter (inches)
    """
    if total_height <= 17.3:
        return dbh * 0.7  # Approximate for short trees

    fclss = dbh * (af + bf * (17.3 / total_height) ** 2)
    return max(fclss, 0.1)


def clark_total_cubic_volume(dbh: float, total_height: float,
                             coef: ClarkCoefficients) -> float:
    """Calculate total cubic volume using Clark profile model.

    Implements the TOTHT subroutine from NVEL r8vol2.f.

    Args:
        dbh: Diameter at breast height outside bark (inches)
        total_height: Total tree height (feet)
        coef: Clark profile coefficients

    Returns:
        Total cubic foot volume (inside bark)
    """
    if dbh <= 0 or total_height <= 4.5:
        return 0.0

    # Calculate DIB and form class
    dib = calculate_dib(dbh, coef.AD, coef.BD)
    fclss = calculate_form_class(dbh, total_height, coef.AF, coef.BF)

    # Ensure form class is reasonable
    if fclss < 0.1:
        fclss = dib * 0.8

    # Pre-compute powers
    dib2 = dib ** 2
    dib3 = dib ** 3
    fclss2 = fclss ** 2
    tht = total_height

    # Calculate taper variables
    # V, W for butt section (0.5 to 4.5 ft)
    V = (1 - 4.5 / tht) ** coef.R
    W = (coef.C + coef.E / dib3) / (1 - V) if V < 1 else 0

    # X, Y, Z, T for middle section (4.5 to 17.3 ft)
    X = (1 - 4.5 / tht) ** coef.P
    Y = (1 - 17.3 / tht) ** coef.P if tht > 17.3 else 0
    Z = (dib2 - fclss2) / (X - Y) if abs(X - Y) > 0.001 else 0
    T = dib2 - Z * X

    # Segment boundaries
    L1, U1 = 0.5, min(4.5, tht)
    L2, U2 = 4.5, min(17.3, tht)
    L3, U3 = 17.3, tht

    # Indicator variables
    I1 = 1
    I2 = 1 if tht > 4.5 else 0
    I3 = 1 if tht > 4.5 else 0
    I4 = 1 if tht > 17.3 else 0

    # Calculate segment volumes
    # Segment 1: Butt (0.5 to 4.5 ft)
    if I1 and tht > 0.5:
        term_l1 = (1 - L1/tht) ** coef.R * (tht - L1) if L1 < tht else 0
        term_u1 = (1 - U1/tht) ** coef.R * (tht - U1) if U1 < tht else 0
        S1 = dib2 * ((1 - V * W) * (U1 - L1) + W * (term_l1 - term_u1) / (coef.R + 1))
    else:
        S1 = 0

    # Segment 2: Middle (4.5 to 17.3 ft)
    if I2 and I3 and tht > 4.5:
        term_l2 = (1 - L2/tht) ** coef.P * (tht - L2) if L2 < tht else 0
        term_u2 = (1 - U2/tht) ** coef.P * (tht - U2) if U2 < tht else 0
        S2 = T * (U2 - L2) + Z * (term_l2 - term_u2) / (coef.P + 1)
    else:
        S2 = 0

    # Segment 3: Upper (17.3 ft to tip)
    if I4 and tht > 17.3:
        A = coef.A
        B = coef.B
        tht_17 = tht - 17.3

        # Check indicator variables for upper section transitions
        I5 = 1 if (L3 - 17.3) < A * tht_17 else 0
        I6 = 1 if (U3 - 17.3) < A * tht_17 else 0

        S3_base = B * (U3 - L3)
        S3_base -= B * ((U3 - 17.3)**2 - (L3 - 17.3)**2) / tht_17
        S3_base += (B / 3) * ((U3 - 17.3)**3 - (L3 - 17.3)**3) / tht_17**2

        if I5:
            S3_base += (1/3) * ((1 - B) / A**2) * (A * tht_17 - (L3 - 17.3))**3 / tht_17**2
        if I6:
            S3_base -= (1/3) * ((1 - B) / A**2) * (A * tht_17 - (U3 - 17.3))**3 / tht_17**2

        S3 = fclss2 * S3_base
    else:
        S3 = 0

    # Total volume (0.005454 converts to cubic feet)
    volume = 0.005454 * (S1 + S2 + S3)

    return max(volume, 0.0)


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

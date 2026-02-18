"""
Establishment height and DBH computation for planted stands.

Extracted from stand.py to isolate the ~430 lines of establishment utility code
that supports Stand.initialize_planted(). These functions compute initial tree
heights and diameters using variant-specific Fortran algorithms:

- Chapman-Richards site curves (NC-128 coefficients)
- ESSUBH linear interpolation + regent half-cycle growth (LS/CS/NE)
- SMHGDG small-tree growth model (PN/WC)
- Curtis-Arney H-D inverse for DBH estimation
- HHTMAX establishment height caps from blkdat.f

No dependency on Stand — these are pure functions of species, site index, and variant.

Source: FVS estab.f, regent.f, essubh.f, blkdat.f
"""
import math
from typing import Tuple

from .config_loader import load_coefficient_file


# =============================================================================
# Carmean Reference Age (CARAGE) for ESSUBH establishment
# =============================================================================
# Fortran ESSUBH (estab.f) computes establishment height by interpolating the
# NC-128 Chapman-Richards curve at a reference age (CARAGE), then linearly
# scaling to 5 years. Default CARAGE = 20 for most species.
ESSUBH_DEFAULT_CARAGE = 20


# =============================================================================
# HHTMAX — maximum establishment height per species (from blkdat.f)
# =============================================================================

# SN HHTMAX values from blkdat.f — maximum establishment height per species.
# Species 1-11 have variant-specific values; species 12-90 all use 20.0.
_SN_HHTMAX = {
    'LB': 23.0, 'SA': 27.0, 'SP': 21.0, 'LL': 21.0, 'SB': 22.0,
    'VP': 20.0, 'SR': 24.0, 'LO': 18.0, 'TB': 18.0, 'PP': 17.0,
    'RC': 22.0,
}
_SN_HHTMAX_DEFAULT = 20.0

# NE HHTMAX values from blkdat.f DATA (HHTMAX(I),I=1,108) — 108 species
_NE_HHTMAX = {
    'BF': 20, 'TA': 24, 'WS': 18, 'RS': 16, 'NS': 18, 'BS': 16, 'PI': 16, 'RN': 18,
    'WP': 20, 'LP': 14, 'VP': 14, 'WC': 16, 'AW': 16, 'RC': 16, 'JU': 16, 'EH': 16,
    'HM': 16, 'OP': 16, 'JP': 14, 'SP': 14, 'TM': 16, 'PP': 18, 'PD': 12, 'SC': 20,
    'OS': 16, 'RM': 20, 'SM': 16, 'BM': 16, 'SV': 18, 'YB': 22, 'SB': 20, 'RB': 18,
    'PB': 18, 'GB': 18, 'HI': 14, 'PH': 14, 'SL': 14, 'SH': 14, 'MH': 18, 'AB': 14,
    'AS': 24, 'WA': 24, 'BA': 18, 'GA': 24, 'PA': 28, 'YP': 24, 'SU': 18, 'CT': 20,
    'QA': 20, 'BP': 24, 'EC': 24, 'BT': 20, 'PY': 20, 'BC': 26, 'WO': 16, 'BR': 14,
    'CK': 12, 'PO': 12, 'OK': 16, 'SO': 16, 'QI': 14, 'WK': 16, 'PN': 14, 'CO': 16,
    'SW': 16, 'SN': 12, 'RO': 20, 'SK': 16, 'BO': 16, 'CB': 14, 'BU': 12, 'YY': 12,
    'WR': 12, 'HK': 12, 'PS': 12, 'HY': 12, 'BN': 18, 'WN': 20, 'OO': 12, 'MG': 20,
    'MV': 20, 'AP': 20, 'WT': 20, 'BG': 16, 'SD': 16, 'PW': 16, 'SY': 24, 'WL': 14,
    'BK': 24, 'BL': 32, 'SS': 18, 'BW': 16, 'WB': 16, 'EL': 16, 'AE': 16, 'RL': 12,
    'OH': 10, 'BE': 16, 'ST': 18, 'AI': 30, 'SE': 20, 'AH': 20, 'DW': 18, 'HT': 16,
    'HH': 20, 'PL': 20, 'PR': 30,
}
_NE_HHTMAX_DEFAULT = 16.0

# CS HHTMAX values from blkdat.f DATA (HHTMAX(I),I=1,96) — 96 species
_CS_HHTMAX = {
    'RC': 16, 'JU': 27, 'SP': 14, 'VP': 14, 'LP': 14, 'OS': 16, 'WP': 20, 'WN': 20,
    'BN': 18, 'TL': 16, 'TS': 20, 'WT': 20, 'BG': 16, 'HS': 14, 'SH': 14, 'SL': 14,
    'MH': 18, 'PH': 14, 'HI': 14, 'WH': 14, 'BH': 14, 'PE': 14, 'BI': 14, 'AB': 14,
    'BA': 18, 'PA': 28, 'UA': 20, 'EC': 24, 'RM': 20, 'BE': 16, 'SV': 18, 'BC': 26,
    'AE': 16, 'SG': 14, 'HK': 12, 'WE': 20, 'EL': 16, 'SI': 20, 'RL': 12, 'RE': 20,
    'YP': 24, 'BW': 16, 'SM': 16, 'AS': 24, 'WA': 24, 'GA': 24, 'WO': 16, 'RO': 20,
    'SK': 16, 'BO': 16, 'SO': 16, 'BJ': 20, 'CK': 12, 'SW': 16, 'BR': 14, 'SN': 12,
    'PO': 12, 'DO': 20, 'CO': 16, 'PN': 20, 'CB': 14, 'QI': 14, 'OV': 20, 'WK': 16,
    'NK': 20, 'WL': 14, 'QS': 20, 'UH': 20, 'SS': 18, 'OB': 20, 'CA': 20, 'PS': 12,
    'HL': 20, 'BP': 24, 'BT': 20, 'QA': 20, 'BK': 24, 'OL': 20, 'SY': 24, 'BY': 20,
    'RB': 18, 'SU': 18, 'WI': 20, 'BL': 32, 'NC': 10, 'AH': 20, 'RD': 20, 'DW': 18,
    'HT': 16, 'KC': 20, 'OO': 12, 'CT': 20, 'MV': 20, 'MB': 20, 'HH': 20, 'SD': 16,
}
_CS_HHTMAX_DEFAULT = 16.0

# LS HHTMAX values from blkdat.f DATA (HHTMAX(I),I=1,68) — 68 species
_LS_HHTMAX = {
    'JP': 14, 'SC': 20, 'RN': 18, 'RP': 18, 'WP': 20, 'WS': 18, 'NS': 18, 'BF': 20,
    'BS': 16, 'TA': 24, 'WC': 16, 'EH': 16, 'OS': 16, 'RC': 16, 'BA': 18, 'GA': 24,
    'EC': 24, 'SV': 18, 'RM': 20, 'BC': 26, 'AE': 16, 'RL': 12, 'RE': 20, 'YB': 22,
    'BW': 16, 'SM': 16, 'BM': 16, 'AB': 14, 'WA': 24, 'WO': 16, 'SW': 16, 'BR': 14,
    'CK': 12, 'RO': 20, 'BO': 16, 'NP': 20, 'BH': 20, 'PH': 14, 'SH': 14, 'BT': 20,
    'QA': 20, 'BP': 24, 'PB': 18, 'BN': 18, 'WN': 20, 'HH': 20, 'BK': 24, 'OH': 10,
    'BE': 16, 'ST': 18, 'MM': 20, 'AH': 20, 'AC': 20, 'HK': 12, 'DW': 18, 'HT': 16,
    'AP': 20, 'BG': 16, 'SY': 24, 'PR': 30, 'CC': 20, 'PL': 20, 'WI': 20, 'BL': 32,
    'DM': 20, 'SS': 18, 'MA': 20,
}
_LS_HHTMAX_DEFAULT = 20.0


def get_hhtmax(species: str, variant: str) -> float:
    """Get the maximum establishment height for a species.

    From Fortran blkdat.f HHTMAX array. Applied in estab.f after HTCALC
    to prevent unrealistically tall establishment heights.

    Args:
        species: Species code
        variant: FVS variant code

    Returns:
        Maximum establishment height in feet, or 0 if no cap applies.
    """
    from .variant_registry import get_variant_config
    config = get_variant_config(variant)
    if config.hhtmax:
        return config.hhtmax.get(species, config.hhtmax_default)
    return config.hhtmax_default


def load_small_tree_coefficients(species: str, variant: str) -> dict:
    """Load variant-specific NC-128 small tree height growth coefficients.

    Replicates Tree._load_variant_small_tree_coefficients() at module level
    so it can be called before Tree objects exist.

    Args:
        species: Species code (e.g., 'LP', 'DF')
        variant: FVS variant code (e.g., 'SN', 'LS')

    Returns:
        Coefficient dict with keys c1-c5 and bh, or empty dict if not found.
    """
    variant_lower = variant.lower()
    filenames = [
        f'{variant_lower}_small_tree_height_growth.json',
        'sn_small_tree_height_growth.json',
    ]
    for filename in filenames:
        try:
            data = load_coefficient_file(filename, variant=variant)
            coeffs = data.get('nc128_height_growth_coefficients', {})
            if species in coeffs:
                return coeffs[species]
        except (FileNotFoundError, Exception):
            continue
    return {}


def compute_establishment_height(species: str, site_index: float,
                                  age: float, variant: str) -> float:
    """Compute tree height from Chapman-Richards at a given age.

    Matches Fortran ESSUBH -> HTCALC(MODE1=1): place tree on the site curve
    at the establishment age, then apply HHTMAX cap from estab.f.

    Args:
        species: Species code (e.g., 'LP', 'DF')
        site_index: Site index in feet
        age: Establishment age in years
        variant: FVS variant code

    Returns:
        Height in feet at the given age on the site curve.
    """
    p = load_small_tree_coefficients(species, variant)
    if not p:
        # Fallback: use default SN LP coefficients
        p = {'c1': 1.1421, 'c2': 1.0042, 'c3': -0.0374,
             'c4': 0.7632, 'c5': 0.0358, 'bh': 0.0}

    bh = p.get('bh', 0.0)
    raw_height = bh + p['c1'] * (site_index ** p['c2']) * \
        (1.0 - math.exp(p['c3'] * age)) ** (p['c4'] * (site_index ** p['c5']))

    # Scale factor: anchor Height(base_age) = SI for non-SN variants
    if variant == 'SN':
        height = max(0.5, raw_height)
    else:
        base_age = 50 if variant in ('LS', 'PN', 'WC', 'NE', 'CS', 'CA', 'OP') else 25
        raw_at_base = bh + p['c1'] * (site_index ** p['c2']) * \
            (1.0 - math.exp(p['c3'] * base_age)) ** (p['c4'] * (site_index ** p['c5']))
        scale = site_index / raw_at_base if raw_at_base > 0 else 1.0
        height = max(0.5, raw_height * scale)

    # Apply HHTMAX cap (estab.f line 1040: IF(HHT.GT.HHTMAX(IPNSPE)) HHT=HHTMAX(IPNSPE))
    hhtmax = get_hhtmax(species, variant)
    if hhtmax > 0 and height > hhtmax:
        height = hhtmax

    return height


def compute_essubh_height(species: str, site_index: float,
                           variant: str, cycle_length: int) -> float:
    """Compute establishment height for 10-year eastern variants (LS/CS/NE).

    Replicates Fortran ESSUBH + regent establishment sequence:
    1. Compute Chapman-Richards height at CARAGE (default 20 years)
       with HHTMAX cap (estab.f clips HTCALC output to HHTMAX)
    2. Linear interpolation to get 5 years of establishment growth
    3. Add half-cycle regent growth (5yr increment scaled by 0.5)

    The HHTMAX cap applied to h_at_carage normalizes the intermediate
    height for species whose CR curves overshoot at CARAGE. For most
    eastern species, CR(20) > HHTMAX=20, so essubh = (20/20)*5 = 5 ft.

    Args:
        species: Species code (e.g., 'RN', 'WO', 'RM')
        site_index: Site index in feet (base age 50)
        variant: FVS variant code ('LS', 'CS', or 'NE')
        cycle_length: Variant cycle length in years (10)

    Returns:
        Establishment height in feet.
    """
    carmean_age = ESSUBH_DEFAULT_CARAGE  # 20 years

    # Step 1: Height at CARAGE from Chapman-Richards (includes HHTMAX cap,
    # matching estab.f which clips HTCALC output before linear interp)
    h_at_carage = compute_establishment_height(
        species, site_index, carmean_age, variant
    )

    # Step 2: ESSUBH linear interpolation to 5 years
    # Fortran: HHT = (HTHT / CARAGE) * 5.0
    essubh_height = (h_at_carage / carmean_age) * 5.0

    # Step 3: Regent growth for remaining half-cycle
    # Load CR coefficients for regent growth computation
    p = load_small_tree_coefficients(species, variant)
    if not p:
        p = {'c1': 1.1421, 'c2': 1.0042, 'c3': -0.0374,
             'c4': 0.7632, 'c5': 0.0358, 'bh': 0.0}

    bh = p.get('bh', 0.0)

    # Scale factor: anchor Height(base_age=50) = SI
    base_age = 50
    raw_at_base = bh + p['c1'] * (site_index ** p['c2']) * \
        (1.0 - math.exp(p['c3'] * base_age)) ** (p['c4'] * (site_index ** p['c5']))
    scale = site_index / raw_at_base if raw_at_base > 0 else 1.0

    def _scaled_cr(age):
        if age <= 0:
            return (bh + 0.1) * scale
        raw = bh + p['c1'] * (site_index ** p['c2']) * \
            (1.0 - math.exp(p['c3'] * age)) ** (p['c4'] * (site_index ** p['c5']))
        return raw * scale

    # Inverse CR: find effective age from essubh_height
    max_height = bh + p['c1'] * (site_index ** p['c2'])
    exponent = p['c4'] * (site_index ** p['c5'])
    raw_essubh = essubh_height / scale if scale > 0 else essubh_height

    if raw_essubh >= max_height - 0.1:
        effective_age = 200.0
    elif raw_essubh <= bh + 0.1:
        effective_age = 0.1
    else:
        ratio = (raw_essubh - bh) / (p['c1'] * (site_index ** p['c2']))
        if ratio <= 0 or ratio >= 1.0 or exponent <= 0:
            effective_age = 0.1
        else:
            inner = ratio ** (1.0 / exponent)
            if inner >= 1.0:
                effective_age = 0.1
            else:
                effective_age = max(0.1, math.log(1.0 - inner) / p['c3'])

    # Regent: 5yr growth increment from site curve.
    # Fortran regent.f computes a FULL cycle (REGYR=10yr) of growth, then
    # scales by SCALE=FNT/REGYR=5/10=0.5 to get 5yr of regent growth.
    # Since we compute the 5yr increment directly from the site curve,
    # no additional scaling is needed (equivalent to 10yr*0.5 = 5yr*1.0).
    regent_5yr = _scaled_cr(effective_age + 5.0) - _scaled_cr(effective_age)
    regent_growth = regent_5yr

    total_height = essubh_height + regent_growth

    # Apply HHTMAX cap to final height
    hhtmax = get_hhtmax(species, variant)
    if hhtmax > 0 and total_height > hhtmax:
        total_height = hhtmax

    return max(0.5, total_height)


def compute_western_establishment_height(species: str, site_index: float,
                                          variant: str) -> Tuple[float, float]:
    """Compute establishment height and DBH for western variants (PN/WC).

    Matches the combined Fortran ESSUBH + first REGENT cycle output.
    Native FVS cycle 1 metrics include both ESSUBH initialization AND
    the first REGENT growth cycle (with LESTB SCALE=0.5), so PyFVS
    establishment must include both to align cycle 1 comparisons.

    Flow (matching Fortran):
    1. ESSUBH (essubh.f): ONE SMHGDG call from H=1.0, DD=0.1 -> height only
    2. Set DBH = DIAM(ISPC) -- species-specific minimum from regent.f
    3. REGENT first cycle (regent.f LESTB): TWO SMHGDG calls that ACCUMULATE
       growth totals (HTGR, DGR), then SCALE=0.5 applied once to totals.
       DBH is SET to DG (not D+DG) per regent.f:385.

    Args:
        species: Species code (e.g., 'DF', 'WH', 'RC')
        site_index: Site index in feet (base age varies by species)
        variant: FVS variant code ('PN' or 'WC')

    Returns:
        Tuple of (establishment_height, establishment_dbh) in feet and inches.
    """
    from .pn_small_tree_growth import calculate_small_tree_growth, get_smhgdg_coefficients

    # --- Phase 1: ESSUBH (essubh.f) ---
    # ONE 5yr SMHGDG call from H=1.0, DD=0.1 with zero competition (MODE=0)
    hg5_essubh, _ = calculate_small_tree_growth(
        species=species, height=1.0, dbh=0.1,
        site_index=site_index, variant=variant,
        ptba=0.0, ptbal=0.0, crown_ratio=0.5, avg_height=0.0
    )
    height = 1.0 + hg5_essubh

    # Apply HHTMAX cap after ESSUBH
    hhtmax = get_hhtmax(species, variant)
    if hhtmax > 0 and height > hhtmax:
        height = hhtmax

    # Set DBH to species-specific DIAM from regent.f DATA statement
    coeffs = get_smhgdg_coefficients(species)
    diam = coeffs.get('diam', 0.3) if coeffs else 0.3
    dbh = diam

    # --- Phase 2: First REGENT cycle (regent.f LESTB) ---
    # Fortran regent.f calls SMHGDG twice, ACCUMULATES growth totals,
    # then applies SCALE once. DBH is SET to DG (not D+DG). See:
    #   regent.f:237-249 (two SMHGDG calls with accumulation)
    #   regent.f:371     (DG(K) = DGR * SCALE * WK4)
    #   regent.f:385     (DBH(K) = DG(K) -- SET, not increment)
    avg_h = height  # Stand average stays fixed at ESSUBH height

    # Call 1: SMHGDG with post-ESSUBH state
    hg5_1, dgr5_1 = calculate_small_tree_growth(
        species=species, height=height, dbh=diam,
        site_index=site_index, variant=variant,
        ptba=0.0, ptbal=0.0, crown_ratio=0.5, avg_height=avg_h
    )
    # Accumulate tree state for call 2 (regent.f: HK=H+HTGR, DK=D+DGR)
    hk = height + hg5_1
    dk = diam + dgr5_1

    # Call 2: SMHGDG with accumulated state (same stand avg_height)
    hg5_2, dgr5_2 = calculate_small_tree_growth(
        species=species, height=hk, dbh=dk,
        site_index=site_index, variant=variant,
        ptba=0.0, ptbal=0.0, crown_ratio=0.5, avg_height=avg_h
    )

    # Accumulate totals (regent.f: HTGR=HTGR+HG5, DGR=DGR+DGR5)
    total_htgr = hg5_1 + hg5_2
    total_dgr = dgr5_1 + dgr5_2

    # Apply SCALE once to totals (regent.f:371: DG(K)=DGR*SCALE*WK4)
    scale = 0.5
    dg = total_dgr * scale
    htgr_scaled = total_htgr * scale

    # SET: DBH = DG (regent.f:385: DBH(K)=DG(K), NOT D+DG!)
    establishment_dbh = max(diam, dg)
    establishment_height = height + htgr_scaled

    # Apply HHTMAX cap after REGENT
    if hhtmax > 0 and establishment_height > hhtmax:
        establishment_height = hhtmax

    return max(0.5, establishment_height), establishment_dbh


def estimate_dbh_from_height(height: float, species: str, variant: str) -> float:
    """Estimate DBH from height using Curtis-Arney H-D inverse.

    For sub-breast-height trees, uses the Fortran rule: DBH = 0.1 + 0.001*HT.
    For taller trees, uses the analytical inverse of the Curtis-Arney model.

    Args:
        height: Tree height in feet
        species: Species code
        variant: FVS variant code

    Returns:
        Estimated DBH in inches.
    """
    if height <= 4.5:
        return 0.1 + 0.001 * height

    from .height_diameter import create_height_diameter_model
    hd_model = create_height_diameter_model(species, variant=variant)
    dbh = hd_model.solve_dbh_from_height(target_height=height)
    return max(0.1, dbh)

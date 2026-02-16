"""SMHGDG small-tree height and diameter growth for PN/WC variants.

Implements the Gould & Harrington (2011) logistic model from Fortran smhgdg.f.
Predicts both height growth and diameter growth simultaneously for trees below
the large-tree transition threshold.

Key differences from the NC-128 Chapman-Richards used by SN/LS/CS/NE:
- Predicts diameter growth directly (not derived from H-D inverse)
- Includes competition effects (PTBA, PTBAL, RELHT)
- Species-specific DMAX caps prevent unrealistic growth
- Height growth = DGS / BETA (proportional to diameter growth)

Redwood (RW) uses a Chapman-Richards age-based curve instead of the logistic.

Public API:
    calculate_small_tree_growth(species, height, dbh, site_index, variant, ...)
        -> (height_growth_5yr, diameter_growth_5yr)
"""
import math
import json
from functools import lru_cache
from pathlib import Path
from typing import Tuple, Dict, Optional

__all__ = ['calculate_small_tree_growth', 'get_smhgdg_coefficients']


@lru_cache(maxsize=1)
def _load_smhgdg_data() -> Dict:
    """Load SMHGDG coefficients from JSON file (cached)."""
    cfg_path = Path(__file__).parent / 'cfg' / 'pn' / 'pn_smhgdg_coefficients.json'
    with open(cfg_path) as f:
        return json.load(f)


def get_smhgdg_coefficients(species: str) -> Optional[Dict]:
    """Get SMHGDG coefficients for a species.

    Args:
        species: Two-letter species code (e.g., 'DF', 'WH')

    Returns:
        Coefficient dict with dmax, beta, alpha, xmin, xmax, dgmin, diam.
        None if species not found.
    """
    data = _load_smhgdg_data()
    coeffs = data.get('coefficients', {})
    return coeffs.get(species)


def _calculate_rw_growth(height: float, site_index: float) -> Tuple[float, float]:
    """Redwood (RW) special case: Chapman-Richards age-based curve.

    From smhgdg.f lines 207-231. RW uses a simple age-height curve
    instead of the logistic model. Diameter growth is always 0 (handled
    by regent.f separately).

    Args:
        height: Current tree height (feet)
        site_index: Site index (feet)

    Returns:
        (height_growth_5yr, diameter_growth_5yr) where dg5 is always 0.
    """
    htmax_coeff = 2.242202
    rate = -0.010742
    power = 0.919076

    htmax = htmax_coeff * site_index
    if htmax - height <= 1.0:
        return 0.0, 0.0

    # Inverse: find effective age from current height
    ratio = height / (htmax_coeff * site_index)
    if ratio >= 1.0 or ratio <= 0:
        return 0.0, 0.0

    try:
        inner = ratio ** (1.0 / power)
        if inner >= 1.0:
            return 0.0, 0.0
        age1 = (1.0 / rate) * math.log(1.0 - inner)
    except (ValueError, ZeroDivisionError):
        return 0.0, 0.0

    age2 = age1 + 5.0

    # Heights at age1 and age2
    h1 = htmax_coeff * site_index * (1.0 - math.exp(rate * age1)) ** power
    h2 = htmax_coeff * site_index * (1.0 - math.exp(rate * age2)) ** power

    hg5 = max(0.0, h2 - h1)
    return hg5, 0.0


def calculate_small_tree_growth(
    species: str,
    height: float,
    dbh: float,
    site_index: float,
    variant: str = 'PN',
    ptba: float = 0.0,
    ptbal: float = 0.0,
    crown_ratio: float = 0.5,
    avg_height: float = 0.0
) -> Tuple[float, float]:
    """Calculate 5-year height and diameter growth for small trees.

    Implements the SMHGDG logistic model from Fortran smhgdg.f.

    Args:
        species: Two-letter species code (e.g., 'DF', 'WH')
        height: Current tree height (feet)
        dbh: Current DBH (inches)
        site_index: Site index (feet, base age varies by species)
        variant: FVS variant code ('PN' or 'WC')
        ptba: Plot total basal area (sq ft/acre)
        ptbal: Plot basal area in larger trees (sq ft/acre)
        crown_ratio: Crown ratio as proportion (0-1)
        avg_height: Average tree height in the stand (feet)

    Returns:
        Tuple of (height_growth_5yr, diameter_growth_5yr) in feet and inches.
    """
    # Get coefficients for species
    coeffs = get_smhgdg_coefficients(species)
    if coeffs is None:
        # Fall back to OT (Other) which uses DF-like coefficients
        coeffs = get_smhgdg_coefficients('OT')
        if coeffs is None:
            return 0.5, 0.0  # Absolute fallback

    # RW special case: Chapman-Richards, not logistic
    if species == 'RW':
        return _calculate_rw_growth(height, site_index)

    dmax = coeffs['dmax']
    beta = coeffs['beta']
    alpha = coeffs['alpha']

    # Handle species with zero coefficients (species 38 blank slot)
    if dmax <= 0 or beta <= 0:
        return 0.0, 0.0

    # WC DF site index conversion: Curtis -> King (smhgdg.f line 260-262)
    si = site_index
    if species == 'DF' and variant == 'WC':
        si = 5.21486 + 0.66486 * site_index

    # Transformed variables (smhgdg.f lines 263-270)
    ptba2 = math.log(ptba + 2.71)
    ptbal2 = math.log(ptbal + 2.71)

    # Relative height
    relht = 0.0
    if avg_height > 0.0:
        relht = min(1.5, height / avg_height)
    relht2 = math.sqrt(relht)

    # Boost factor (low-density growth enhancement)
    if ptba < 100.0:
        boost = 1.0 / (1.0 + math.exp(-3.1 + 0.18 * ptba))
    else:
        boost = 0.0

    # DGS logistic model (smhgdg.f lines 275-278)
    logistic_sum = (
        alpha[0]
        + alpha[1] * ptba
        + alpha[2] * ptba2
        + alpha[3] * ptbal
        + alpha[4] * ptbal2
        + alpha[5] * boost
        + alpha[6] * crown_ratio
        + alpha[7] * relht
        + alpha[8] * relht2
        + alpha[9] * si
    )

    # Clamp to prevent overflow in exp()
    logistic_sum = max(-50.0, min(50.0, logistic_sum))

    dgs = dmax / (1.0 + math.exp(logistic_sum))

    # Height growth from diameter growth (smhgdg.f line 279)
    hg5 = dgs / beta

    # Diameter growth depends on breast height (smhgdg.f lines 280-288)
    if height < 4.5:
        if (height + hg5) >= 4.5:
            dg5 = beta * (height + hg5 - 4.5)
        else:
            dg5 = 0.0
    else:
        dg5 = dgs

    return max(0.0, hg5), max(0.0, dg5)

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
from .exceptions import FVSError


# =============================================================================
# Carmean Reference Age (CARAGE) for ESSUBH establishment
# =============================================================================
# Fortran ESSUBH (estab.f) computes establishment height by interpolating the
# NC-128 Chapman-Richards curve at a reference age (CARAGE), then linearly
# scaling to 5 years. Default CARAGE = 20 for most species.
ESSUBH_DEFAULT_CARAGE = 20


# Per-species CARAGE for the CS variant, from Fortran cs/essubh.f:33-43 DATA
# MAPCS. Ordered by FVS species position (1..96). Keys are the pyfvs species
# code used in cs_species_config.yaml; Fortran slot 85 ('OH') is labelled
# 'NC' here to match config.
_CS_MAPCS = {
    # 1-10
    'RC': 10, 'JU': 10, 'SP': 10, 'VP': 15, 'LP': 20, 'OS': 10, 'WP': 5,
    'WN': 20, 'BN': 20, 'TL': 25,
    # 11-20 (HS=14 is Fortran blank slot; CARAGE=20 from DATA)
    'TS': 25, 'WT': 25, 'BG': 25, 'HS': 20, 'SH': 20, 'SL': 20, 'MH': 20,
    'PH': 20, 'HI': 20, 'WH': 20,
    # 21-30
    'BH': 20, 'PE': 10, 'BI': 20, 'AB': 20, 'BA': 20, 'PA': 35, 'UA': 20,
    'EC': 15, 'RM': 20, 'BE': 10,
    # 31-40
    'SV': 15, 'BC': 20, 'AE': 20, 'SG': 20, 'HK': 10, 'WE': 20, 'EL': 20,
    'SI': 20, 'RL': 20, 'RE': 20,
    # 41-50
    'YP': 20, 'BW': 20, 'SM': 20, 'AS': 20, 'WA': 20, 'GA': 35, 'WO': 10,
    'RO': 20, 'SK': 10, 'BO': 10,
    # 51-60
    'SO': 10, 'BJ': 10, 'CK': 10, 'SW': 30, 'BR': 10, 'SN': 30, 'PO': 10,
    'DO': 10, 'CO': 10, 'PN': 10,
    # 61-70 (UH=68 is Fortran blank slot)
    'CB': 20, 'QI': 10, 'OV': 35, 'WK': 30, 'NK': 10, 'WL': 10, 'QS': 20,
    'UH': 10, 'SS': 10, 'OB': 20,
    # 71-80 (OL=78 is Fortran blank slot)
    'CA': 20, 'PS': 10, 'HL': 10, 'BP': 20, 'BT': 20, 'QA': 20, 'BK': 10,
    'OL': 20, 'SY': 20, 'BY': 20,
    # 81-90 (NC=85 is Fortran 'OH' slot)
    'RB': 20, 'SU': 10, 'WI': 10, 'BL': 10, 'NC': 10, 'AH': 10, 'RD': 10,
    'DW': 10, 'HT': 10, 'KC': 20,
    # 91-96
    'OO': 10, 'CT': 20, 'MV': 25, 'MB': 20, 'HH': 10, 'SD': 10,
}


# Per-species CARAGE for the LS variant, from Fortran ls/essubh.f DATA MAPLS.
# Ordered by FVS species position (1..68). Fortran blank slots are omitted.
_LS_MAPCS = {
    'JP': 20, 'SC': 15, 'RN': 20, 'RP': 20, 'WP':  5,
    'WS': 15, 'NS': 15, 'BF': 20, 'BS': 20, 'TA': 10,
    'WC': 20, 'EH': 20, 'OS': 10, 'RC': 10, 'BA': 20,
    'GA': 35, 'EC': 15, 'SV': 15, 'RM': 20, 'BC': 20,
    'AE': 20, 'RL': 20, 'RE': 20, 'YB': 20, 'BW': 20,
    'SM': 20, 'BM': 20, 'AB': 20, 'WA': 20, 'WO': 10,
    'SW': 30, 'BR': 10, 'CK': 10, 'RO': 20, 'BO': 10,
    'NP': 10, 'BH': 20, 'PH': 20, 'SH': 20, 'BT': 20,
    'QA': 20, 'BP': 20, 'PB': 20, 'BN': 20, 'WN': 20,
    'HH': 10, 'BK': 10, 'OH': 10, 'BE': 10, 'ST': 10,
    'MM': 10, 'AH': 10, 'AC': 20, 'HK': 10, 'DW': 10,
    'HT': 10, 'AP': 10, 'BG': 25, 'SY': 20, 'PR': 10,
    'CC': 10, 'PL': 10, 'WI': 10, 'BL': 10, 'DM': 10,
    'SS': 10, 'MA': 10,
}


# Per-species CARAGE for the NE variant, from Fortran ne/essubh.f DATA MAPNE.
# Ordered by FVS species position (1..108). Fortran blank slots are omitted.
_NE_MAPCS = {
    'BF': 20, 'TA': 10, 'WS': 15, 'RS': 20, 'NS': 15,
    'BS': 20, 'PI': 20, 'RN': 20, 'WP':  5, 'LP': 20,
    'VP': 15, 'WC': 20, 'AW': 20, 'RC': 10, 'JU': 20,
    'EH': 20, 'HM': 20, 'OP': 20, 'JP': 20, 'SP': 10,
    'TM': 10, 'PP': 15, 'PD': 20, 'SC': 15, 'OS': 10,
    'RM': 20, 'SM': 20, 'BM': 20, 'SV': 20, 'YB': 20,
    'SB': 20, 'RB': 20, 'PB': 20, 'GB': 20, 'HI': 20,
    'PH': 20, 'SL': 20, 'SH': 20, 'MH': 20, 'AB': 20,
    'AS': 20, 'WA': 20, 'BA': 20, 'GA': 35, 'PA': 35,
    'YP': 20, 'SU': 10, 'CT': 20, 'QA': 20, 'BP': 20,
    'EC': 10, 'BT': 20, 'PY': 15, 'BC': 20, 'WO': 10,
    'BR': 10, 'CK': 10, 'PO': 10, 'OK': 10, 'SO': 10,
    'QI': 10, 'WK': 30, 'PN': 10, 'CO': 10, 'SW': 30,
    'SN': 30, 'RO': 20, 'SK': 10, 'BO': 10, 'CB': 20,
    'BU': 10, 'YY': 10, 'WR': 20, 'HK': 10, 'PS': 10,
    'HY': 10, 'BN': 20, 'WN': 20, 'OO': 10, 'MG': 25,
    'MV': 25, 'AP': 10, 'WT': 25, 'BG': 25, 'SD': 10,
    'PW': 10, 'SY': 20, 'WL': 10, 'BK': 10, 'BL': 10,
    'SS': 10, 'BW': 20, 'WB': 20, 'EL': 20, 'AE': 20,
    'RL': 20, 'OH': 10, 'BE': 10, 'ST': 10, 'AI': 10,
    'SE': 10, 'AH': 10, 'DW': 10, 'HT': 10, 'HH': 10,
    'PL': 10, 'PR': 10,
}


def _get_essubh_carage(species: str, variant: str) -> int:
    """Return species-specific ESSUBH Carmean reference age (MAPCS value).

    From Fortran {variant}/essubh.f DATA MAP{VARIANT}. Falls back to
    ESSUBH_DEFAULT_CARAGE when the species is missing from the variant's
    table (which happens only for species outside the variant's native
    range, where MAPCS position is a blank/sentinel slot).
    """
    if variant == 'CS':
        return _CS_MAPCS.get(species, ESSUBH_DEFAULT_CARAGE)
    if variant == 'LS':
        return _LS_MAPCS.get(species, ESSUBH_DEFAULT_CARAGE)
    if variant == 'NE':
        return _NE_MAPCS.get(species, ESSUBH_DEFAULT_CARAGE)
    return ESSUBH_DEFAULT_CARAGE


def compute_cs_essubh_initial_height(species: str, site_index: float) -> float:
    """Fortran cs/essubh.f HHT = (HTCALC(CARAGE) / CARAGE) * 5.0.

    Computes the establishment starting height (before regent's 5-yr growth
    phase) using the species-specific Carmean reference age from MAPCS.
    Used by the LS/CS LESTB establishment path in stand.py.
    """
    carage = _get_essubh_carage(species, 'CS')
    h_at_carage = compute_establishment_height(
        species, site_index, float(carage), 'CS'
    )
    # Fortran: HHT = (H/CARAGE) * MIN(5.0, TIME-DELAY). With TIME=cycle=10
    # and DELAY=0 (the default for PLANT immediate) MIN = 5.0.
    return (h_at_carage / carage) * 5.0


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

# WS HHTMAX values from blkdat.f DATA (HHTMAX(I),I=1,43) — 43 species
_WS_HHTMAX = {
    'SP': 27.0, 'DF': 21.0, 'WF': 21.0, 'GS': 22.0, 'IC': 20.0,
    'JP': 18.0, 'RF': 18.0, 'PP': 17.0, 'LP': 20.0, 'WB': 20.0,
    'WP': 27.0, 'PM': 20.0, 'SF': 21.0, 'KP': 20.0, 'FP': 20.0,
    'CP': 20.0, 'LM': 20.0, 'MP': 17.0, 'GP': 20.0, 'WE': 20.0,
    'GB': 9.0, 'BD': 21.0, 'RW': 22.0, 'MH': 27.0, 'WJ': 20.0,
    'UJ': 20.0, 'CJ': 20.0, 'LO': 24.0, 'CY': 24.0, 'BL': 24.0,
    'BO': 24.0, 'VO': 24.0, 'IO': 24.0, 'TO': 22.0, 'GC': 22.0,
    'AS': 22.0, 'CL': 22.0, 'MA': 22.0, 'DG': 22.0, 'BM': 24.0,
    'MC': 20.0, 'OS': 23.0, 'OH': 24.0,
}
_WS_HHTMAX_DEFAULT = 20.0

# CA HHTMAX values from blkdat.f — all 49 CA species use 20.0 ft
_CA_HHTMAX = {}  # Empty dict = all species use the default
_CA_HHTMAX_DEFAULT = 20.0

# OC HHTMAX values from blkdat.f DATA (HHTMAX(I),I=1,33) — 33 species
_OC_HHTMAX = {
    'WP': 23.0, 'SP': 27.0, 'DF': 21.0, 'WF': 21.0, 'MH': 22.0,
    'IC': 20.0, 'LP': 20.0, 'ES': 18.0, 'SH': 20.0, 'PP': 17.0,
    'WJ': 6.0, 'GF': 21.0, 'AF': 20.0, 'SF': 21.0, 'NF': 20.0,
    'WB': 23.0, 'WL': 27.0, 'RC': 22.0, 'WH': 20.0, 'PY': 20.0,
    'WA': 20.0, 'RA': 50.0, 'BM': 20.0, 'AS': 16.0, 'CW': 20.0,
    'CH': 20.0, 'WO': 20.0, 'WI': 20.0, 'GC': 20.0, 'MC': 20.0,
    'MB': 20.0, 'OS': 21.0, 'OH': 20.0,
}
_OC_HHTMAX_DEFAULT = 20.0

# EC HHTMAX values from ec/blkdat.f:153-157 DATA HHTMAX (32 species).
_EC_HHTMAX = {
    'WP': 23.0, 'WL': 27.0, 'DF': 21.0, 'SF': 21.0, 'RC': 22.0,
    'GF': 20.0, 'LP': 24.0, 'ES': 18.0, 'AF': 18.0, 'PP': 17.0,
    'WH': 20.0, 'MH': 22.0, 'PY': 20.0, 'WB': 20.0, 'NF': 20.0,
    'WF': 20.0, 'LL': 20.0, 'YC': 20.0, 'WJ': 20.0, 'BM': 20.0,
    'VN': 20.0, 'RA': 50.0, 'PB': 20.0, 'GC': 20.0, 'DG': 20.0,
    'AS': 20.0, 'CW': 20.0, 'WO': 20.0, 'PL': 20.0, 'WI': 20.0,
    'OS': 22.0, 'OH': 20.0,
}
_EC_HHTMAX_DEFAULT = 20.0


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


def get_essubh_height(species: str, variant: str) -> float:
    """Initial seedling height from Fortran essubh.f for bare-ground PLANT.

    Each variant's essubh.f assigns species-specific heights to newly
    planted trees.  These values must match for parity tests that start
    from the same bare-ground state as native FVS.

    Currently only OC/CA (shared essubh.f) is implemented.  Other
    variants fall back to 1.0 ft.
    """
    # OC/CA essubh.f (bin/FVSoc_buildDir/essubh.f lines 52-86):
    #   Species 5,6,9 (RF,SH,MH): 1.0 ft
    #   Species 1-4,7,8,15-20,22,23,25,50 (DF, conifers, RW): 2.0 ft
    #   Species 10-14,21 (LP, pines, JU): 3.0 ft
    #   Species 24,30-32,35,39,40 (oaks, BU, DG, FL): 1.0 ft
    #   Species 26-29,33,34,36-39,41-49 (hardwoods, MA): 2.0 ft
    _OC_ESSUBH = {
        'RF': 1.0, 'SH': 1.0, 'MH': 1.0,
        'WB': 3.0, 'KP': 3.0, 'LP': 3.0, 'CP': 3.0, 'LM': 3.0, 'WJ': 3.0,
        'PY': 1.0, 'WO': 1.0, 'BO': 1.0, 'VO': 1.0, 'BU': 1.0, 'DG': 1.0, 'FL': 1.0,
    }
    if variant in ('OC', 'CA'):
        return _OC_ESSUBH.get(species, 2.0)  # Default 2.0 (DF, most conifers/hardwoods)
    return 1.0  # Generic fallback for other variants


def _is_mountain_ecounit(ecounit: str) -> bool:
    """Fortran htcalc.f convention: PCOM starts with 'M' = mountain ecounit."""
    return bool(ecounit) and ecounit.startswith('M')


# Fortran sn/htcalc.f:147-156 — when ISPC=45 (YP) and PCOM doesn't start
# with 'M' (non-mountain), use a different Chapman-Richards coefficient set.
# Default LTBHEC table value for YP is the mountain set.
_SN_YP_NONMOUNTAIN = {
    'c1': 1.1789, 'c2': 1.0, 'c3': -0.0339,
    'c4': 0.8117, 'c5': -0.0001, 'bh': 0.0,
}


def _apply_ecounit_overrides(coeffs: dict, species: str, variant: str,
                             ecounit: str = None) -> dict:
    """Swap NC-128 coefficients for ecounit-conditional Fortran branches.

    Currently handles SN YP nonmountain (htcalc.f:150). Returns a fresh
    dict if a swap applies, else the original `coeffs`.
    """
    if variant == 'SN' and species == 'YP' and not _is_mountain_ecounit(ecounit):
        return _SN_YP_NONMOUNTAIN.copy()
    return coeffs


def load_small_tree_coefficients(species: str, variant: str,
                                 ecounit: str = None) -> dict:
    """Load variant-specific NC-128 small tree height growth coefficients.

    Replicates Tree._load_variant_small_tree_coefficients() at module level
    so it can be called before Tree objects exist.

    Args:
        species: Species code (e.g., 'LP', 'DF')
        variant: FVS variant code (e.g., 'SN', 'LS')
        ecounit: Ecological unit code (e.g., 'M231', '232', None). Used
            for Fortran htcalc.f branches that swap coefficients based
            on mountain vs non-mountain ecounit (currently only SN YP).

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
                return _apply_ecounit_overrides(coeffs[species], species, variant, ecounit)
        except FVSError:
            continue
    return {}


def compute_establishment_height(species: str, site_index: float,
                                  age: float, variant: str,
                                  ecounit: str = None) -> float:
    """Compute tree height from Chapman-Richards at a given age.

    Matches Fortran ESSUBH -> HTCALC(MODE1=1): place tree on the site curve
    at the establishment age, then apply HHTMAX cap from estab.f.

    Args:
        species: Species code (e.g., 'LP', 'DF')
        site_index: Site index in feet
        age: Establishment age in years
        variant: FVS variant code
        ecounit: Ecological unit code; used for SN YP nonmountain branch
            in htcalc.f.

    Returns:
        Height in feet at the given age on the site curve.
    """
    p = load_small_tree_coefficients(species, variant, ecounit=ecounit)
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
        base_age = 50 if variant in ('LS', 'PN', 'WC', 'NE', 'CS', 'CA', 'OC', 'OP') else 25
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
    # NOTE: This hardcoded CARAGE=20 does NOT match Fortran essubh.f's
    # species-specific MAPCS table. Switching to _get_essubh_carage(species,
    # variant) was tried and reverted — it exposed a compound drift in the
    # downstream regent_growth computation that was silently compensated by
    # the CARAGE=20 default. A proper fix requires porting the full REGENT
    # LESTB scale/CON/BALMOD chain, not just the CARAGE dispatch. See
    # memory/project_cs_wo_lestb_audit.md for the audit notes.
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


def compute_establishment_tree_state(
    species: str, site_index: float, variant: str, cycle_length: int,
    height_multiplier: float = 1.0, ecounit: str = None,
) -> Tuple[float, float]:
    """Compute (height, dbh) for a tree at the end of the establishment cycle.

    Encapsulates the variant-dispatched logic that both initialize_planted()
    and _grow_establishment_cycle() need.  Replicates the Fortran ESTAB ->
    ESGENT -> REGENT(TRUE) pipeline: place the tree on the site curve at the
    establishment age, apply HHTMAX cap and height variation, then derive DBH
    from the resulting height using the variant-appropriate allometric strategy.

    Args:
        species: Species code (e.g., 'LP', 'DF')
        site_index: Site index in feet
        variant: FVS variant code (e.g., 'SN', 'LS', 'PN')
        cycle_length: Variant base cycle in years (5 or 10)
        height_multiplier: Lognormal variation factor (default 1.0 = no variation)

    Returns:
        (height, dbh) in feet and inches.
    """
    # --- Variant-dispatched establishment height ---
    pnwc_establishment_dbh = None
    csne_essubh_height = None

    if variant in ('SN', 'OP', 'CA', 'OC', 'WS', 'LS'):
        # Fortran regent.f:118-124 (LESTB branch) shortens the establishment
        # cycle height growth period by 5 years: FNT = FINT - 5, or
        # LSKIPH=TRUE when FINT<=5. For 5-yr cycle variants (SN/OP/CA/OC/WS)
        # the net end-of-cycle state is site curve at cycle+2 (matches SN
        # ESSUBH age=TIME+TRAGE=5+2=7).
        # For LS (10-yr cycle), the tree effectively grows FNT=5 years, so
        # the equivalent site-curve age at end of cycle 1 is cycle_length-5
        # (= 5), not cycle_length+2 (= 12). The prior (cycle+2) formula
        # placed LS plantation trees ~2x too tall after cycle 1, compounding
        # to +70-300% BA drift vs native FVSls (SY yr10 BA was +372%).
        if variant == 'LS':
            establishment_age = max(1, cycle_length - 4)
        else:
            establishment_age = cycle_length + 2
        base_height = compute_establishment_height(
            species, site_index, establishment_age, variant, ecounit=ecounit
        )
    elif variant in ('CS', 'NE'):
        base_height = compute_essubh_height(
            species, site_index, variant, cycle_length
        )
        carmean_age = ESSUBH_DEFAULT_CARAGE
        h_at_carage = compute_establishment_height(
            species, site_index, carmean_age, variant, ecounit=ecounit
        )
        csne_essubh_height = (h_at_carage / carmean_age) * 5.0
    elif variant in ('PN', 'WC'):
        base_height, pnwc_establishment_dbh = compute_western_establishment_height(
            species, site_index, variant
        )
    else:
        establishment_age = cycle_length + 2
        base_height = compute_establishment_height(
            species, site_index, establishment_age, variant, ecounit=ecounit
        )

    # --- Apply HHTMAX cap and height variation ---
    hhtmax = get_hhtmax(species, variant)
    tree_height = base_height * height_multiplier
    if hhtmax > 0 and tree_height > hhtmax:
        tree_height = hhtmax

    # --- Variant-dispatched DBH computation ---
    if variant in ('PN', 'WC'):
        dbh_multiplier = tree_height / base_height if base_height > 0 else 1.0
        tree_dbh = max(0.0, pnwc_establishment_dbh * dbh_multiplier)
    elif variant in ('CS', 'NE'):
        estab_frac = 0.75 if variant == 'CS' else 0.50
        midpoint_height = csne_essubh_height + estab_frac * (
            tree_height - csne_essubh_height
        )
        tree_dbh = estimate_dbh_from_height(midpoint_height, species, variant)
    elif variant in ('SN', 'CA', 'OC', 'WS'):
        uncapped_height = base_height * height_multiplier
        estab_frac = 0.25
        hd_height = tree_height + estab_frac * (uncapped_height - tree_height)
        tree_dbh = estimate_dbh_from_height(hd_height, species, variant)
    else:
        tree_dbh = estimate_dbh_from_height(tree_height, species, variant)

    return tree_height, tree_dbh


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

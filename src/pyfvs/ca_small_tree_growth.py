"""SMHTGF small-tree height growth for the CA (Inland California) variant.

Faithful port of Fortran ca/smhtgf.f. Five equation groups
(pines, firs, blackoak, tanoak, redwood) with per-species MAPSP dispatch and
SPADJF adjustment factors from ca/smhtgf.f DATA blocks.

Unlike the NC-128 Chapman-Richards model used by SN/LS/CS/NE, CA's SMHTGF
returns a 5-year height growth increment directly as a function of
BAL/CR/SI/RELHT — no site-curve inversion, no effective-age machinery.

Called from Stand._grow_establishment_cycle_ca during the establishment
cycle. Not yet wired into Tree._grow_small_tree for post-establishment
growth (the large-tree DG path dominates once DBH crosses the blend zone).
"""
from __future__ import annotations

import math
from typing import Dict


# Fortran ca/smhtgf.f DATA MAPSP (species index 1..50 → equation group 1..5)
# 1 = pines, 2 = firs (incl. DF), 3 = blackoak, 4 = tanoak, 5 = redwood
_CA_MAPSP: Dict[str, int] = {
    # Group 2 (firs + DF-like): PC IC RC WF RF SH DF WH MH BR PY CL
    'PC': 2, 'IC': 2, 'RC': 2, 'WF': 2, 'RF': 2, 'SH': 2, 'DF': 2, 'WH': 2,
    'MH': 2, 'BR': 2, 'PY': 2, 'CL': 2,
    # Group 1 (pines): WB KP LP CP LM JP SP WP PP MP GP WJ OS
    'WB': 1, 'KP': 1, 'LP': 1, 'CP': 1, 'LM': 1, 'JP': 1, 'SP': 1, 'WP': 1,
    'PP': 1, 'MP': 1, 'GP': 1, 'WJ': 1, 'OS': 1,
    # Group 5 (redwood): GS (Giant Sequoia) and RW (Coast Redwood)
    'GS': 5, 'RW': 5,
    # Group 3 (blackoak): LO CY BL EO WO BO VO IO BM BU RA MA DG WN SY AS
    #                    CW WI CN OH
    'LO': 3, 'CY': 3, 'BL': 3, 'EO': 3, 'WO': 3, 'BO': 3, 'VO': 3, 'IO': 3,
    'BM': 3, 'BU': 3, 'RA': 3, 'MA': 3, 'DG': 3, 'WN': 3, 'SY': 3, 'AS': 3,
    'CW': 3, 'WI': 3, 'CN': 3, 'OH': 3,
    # Group 4 (tanoak): BM-index34 GC FL TO CN47 (per MAPSP line 4)
    # Fortran positions with MAPSP=4: 34 (BM-but that's group-3 per source)
    # Actual MAPSP=4 per source: 34=BM→3, 37=MA→4, 39=DG→4, 42=TO→4, 48=CL→4
    # Re-mapping based on Fortran: MA=4, DG=4, TO=4, CL=4
    'TO': 4,
}
# Correct MAPSP per Fortran (re-resolve exact Fortran indices):
# Line 4 (indices 31-40): 3,3,3,4,3,3,4,3,4,3  → idx 34=BM→4, idx 37=MA→4, idx 39=DG→4
# Line 5 (indices 41-50): 3,4,3,3,3,3,2,4,3,5  → idx 42=TO→4, idx 48=CL→4
# Overrides so the entries above don't leak wrong groups:
_CA_MAPSP['BM'] = 4  # bigleaf maple
_CA_MAPSP['MA'] = 4  # pacific madrone
_CA_MAPSP['DG'] = 4  # pacific dogwood
_CA_MAPSP['TO'] = 4
_CA_MAPSP['CL'] = 4  # california laurel
# Default for unknown species: firs group (DF-like behavior is a reasonable default)


# Fortran ca/smhtgf.f DATA SPADJF (species multiplier 1..50)
_CA_SPADJF: Dict[str, float] = {
    # indices 1-10
    'PC': 1.0, 'IC': 1.0, 'RC': 0.9, 'WF': 1.1, 'RF': 1.1, 'SH': 1.1,
    'DF': 1.1, 'WH': 0.8, 'MH': 0.9, 'WB': 0.9,
    # indices 11-20
    'KP': 1.0, 'LP': 1.0, 'CP': 1.0, 'LM': 1.0, 'JP': 1.0, 'SP': 1.1,
    'WP': 1.1, 'PP': 1.0, 'MP': 1.1, 'GP': 0.9,
    # indices 21-30
    'WJ': 1.0, 'BR': 0.9, 'GS': 1.0, 'PY': 0.8, 'OS': 1.0, 'LO': 1.1,
    'CY': 0.9, 'BL': 1.1, 'EO': 1.1, 'WO': 1.0,
    # indices 31-40
    'BO': 1.1, 'VO': 1.0, 'IO': 1.1, 'BM': 1.0, 'BU': 1.0, 'RA': 1.0,
    'MA': 1.0, 'GC': 1.0, 'DG': 1.0, 'FL': 1.0,
    # indices 41-50
    'WN': 1.1, 'TO': 1.0, 'SY': 1.1, 'AS': 1.2, 'CW': 1.2, 'WI': 1.1,
    'CN': 0.8, 'CL': 1.0, 'OH': 1.0, 'RW': 1.0,
}


def calculate_ca_small_tree_htgr(
    species: str,
    height: float,
    crown_ratio: float,
    basal_area_larger: float,
    site_index: float,
    relative_height: float = 1.0,
) -> float:
    """Fortran ca/smhtgf.f: 5-year small-tree height growth increment.

    Args:
        species: Two-letter species code (e.g., 'DF', 'PP').
        height: Current tree height (ft). Only used by redwood.
        crown_ratio: Crown ratio in percent (0..100), as Fortran passes it.
        basal_area_larger: BAL for the tree (sq ft/acre).
        site_index: Site index (ft).
        relative_height: H / AVH, clamped [0, 1.05] per regent.f:187.

    Returns:
        5-year height growth increment (ft), floored at 0.1.
    """
    # FACTOR = SPADJF(NSPC) * (0.80 + 0.004*(SI - 50))
    spadjf = _CA_SPADJF.get(species, 1.0)
    factor = spadjf * (0.80 + 0.004 * (site_index - 50.0))

    tembal = max(basal_area_larger, 5.0)
    group = _CA_MAPSP.get(species, 2)  # default to firs

    cr = crown_ratio

    if group == 1:
        # Pines (regent.f:122-124)
        htgr = (
            math.exp(
                0.7452 - 0.003271 * basal_area_larger
                - 0.1632 * cr + 0.0217 * cr * cr
                + 0.00536 * site_index
            ) * factor * 1.75
        )
    elif group == 2:
        # Firs incl. DF (regent.f:149-158)
        domhtgr = 5.0 * (2.2227 + 0.4314 * site_index) / (29.0 - 0.05 * site_index)
        cr10 = cr / 10.0
        crmod = 1.0 - math.exp(-4.26558 * cr10)
        rhmod = math.exp(2.54119 * (max(relative_height, 1e-6) ** 0.250537 - 1.0))
        smhmod = 1.016605 * crmod * rhmod
        htgr = domhtgr * smhmod
    elif group == 3:
        # Black oak (regent.f:163-165)
        htgr = math.exp(3.817 - 0.7829 * math.log(tembal)) * factor
    elif group == 4:
        # Tanoak (regent.f:170-172)
        htgr = math.exp(3.385 - 0.5898 * math.log(tembal)) * factor
    elif group == 5:
        # Coast redwood / giant sequoia: 5-yr forward growth via
        # Chapman-Richards age inversion (smhtgf.f:176-192).
        htmax = 2.242202 * site_index
        if htmax - height <= 1.0:
            htgr = 0.0
        else:
            ratio = height / (2.242202 * site_index)
            ratio = max(min(ratio, 0.9999), 1e-6)
            age1 = (1.0 / -0.010742) * math.log(
                1.0 - ratio ** (1.0 / 0.919076)
            )
            age2 = age1 + 5.0
            h1 = 2.242202 * site_index * (
                1.0 - math.exp(-0.010742 * age1)
            ) ** 0.919076
            h2 = 2.242202 * site_index * (
                1.0 - math.exp(-0.010742 * age2)
            ) ** 0.919076
            htgr = h2 - h1
    else:
        htgr = 0.1

    if htgr < 0.1:
        htgr = 0.1
    return htgr


# Fortran ca/blkdat.f:212-232 DATA HT1/HT2. Wykoff-style HT-DBH
# coefficients applied in ca/regent.f:264-274 for small-tree DBH dubbing
# (when D < DGMIN). Formula: HT = 4.5 + exp(HT1 + HT2/(DBH+1)), so
# DBH = HT2/(ln(HT-4.5) - HT1) - 1.
_CA_WYKOFF_HT1: Dict[str, float] = {
    'PC': 4.7874, 'IC': 5.2052, 'RC': 4.7874, 'WF': 5.2180, 'RF': 5.2973,
    'SH': 5.2973, 'DF': 5.3076, 'WH': 4.7874, 'MH': 4.7874, 'WB': 4.7874,
    'KP': 4.6843, 'LP': 4.8358, 'CP': 4.7874, 'LM': 4.7874, 'JP': 5.1419,
    'SP': 5.3371, 'WP': 5.2649, 'PP': 5.3820, 'MP': 4.7874, 'GP': 4.6236,
    'WJ': 4.7874, 'BR': 4.7874, 'GS': 5.3401, 'PY': 4.7874, 'OS': 4.7874,
    'LO': 4.6618, 'CY': 4.6618, 'BL': 4.6618, 'EO': 4.6618, 'WO': 3.8314,
    'BO': 4.4907, 'VO': 4.6618, 'IO': 4.6618, 'BM': 4.6618, 'BU': 4.6618,
    'RA': 4.6618, 'MA': 4.4809, 'GC': 4.6618, 'DG': 4.6618, 'FL': 4.6618,
    'WN': 4.6618, 'TO': 4.6618, 'SY': 4.6618, 'AS': 4.6618, 'CW': 4.6618,
    'WI': 4.6618, 'CN': 4.6618, 'CL': 4.6618, 'OH': 4.6618, 'RW': 5.3401,
}
_CA_WYKOFF_HT2: Dict[str, float] = {
    'PC': -7.3170, 'IC': -20.1443, 'RC': -7.3170, 'WF': -14.8682,
    'RF': -17.2042, 'SH': -17.2042, 'DF': -14.4740, 'WH': -7.3170,
    'MH': -7.3170, 'WB': -7.3170, 'KP': -6.5516, 'LP': -9.2077,
    'CP': -7.3170, 'LM': -7.3170, 'JP': -19.8143, 'SP': -19.3151,
    'WP': -15.5907, 'PP': -20.4097, 'MP': -7.3170, 'GP': -13.0049,
    'WJ': -7.3170, 'BR': -7.3170, 'GS': -15.9354, 'PY': -7.3170,
    'OS': -7.3170, 'LO': -8.3312, 'CY': -8.3312, 'BL': -8.3312,
    'EO': -8.3312, 'WO': -4.8221, 'BO': -7.7030, 'VO': -8.3312,
    'IO': -8.3312, 'BM': -8.3312, 'BU': -8.3312, 'RA': -8.3312,
    'MA': -7.5989, 'GC': -8.3312, 'DG': -8.3312, 'FL': -8.3312,
    'WN': -8.3312, 'TO': -8.3312, 'SY': -8.3312, 'AS': -8.3312,
    'CW': -8.3312, 'WI': -8.3312, 'CN': -8.3312, 'CL': -8.3312,
    'OH': -8.3312, 'RW': -15.9354,
}


def ca_wykoff_dbh_from_height(species: str, height: float) -> float:
    """Fortran ca/regent.f:264-274 small-tree Wykoff H-D inverse.

    DBH = HT2 / (ln(H - 4.5) - HT1) - 1, used during the establishment
    cycle (LESTB=TRUE) and for any small tree with DBH < DGMIN.
    Returns 0.1 minimum for sub-breast-height trees (matches Fortran
    regent.f:262 `DBH = D + 0.001*HK`).

    Args:
        species: Two-letter species code.
        height: Tree height in feet.

    Returns:
        DBH in inches (>= 0.1).
    """
    if height <= 4.5:
        return 0.1 + 0.001 * height
    ht1 = _CA_WYKOFF_HT1.get(species, 4.6618)
    ht2 = _CA_WYKOFF_HT2.get(species, -8.3312)
    denom = math.log(height - 4.5) - ht1
    if abs(denom) < 1e-9:
        return 0.1
    dbh = ht2 / denom - 1.0
    # Fortran applies `DBH(K) = DBH(K) + 0.001*HK` after the Wykoff dub
    # (ca/regent.f:305) for LESTB paths.
    dbh = dbh + 0.001 * height
    return max(0.1, dbh)

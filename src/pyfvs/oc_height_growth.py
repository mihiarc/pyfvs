"""FVS Southwest Oregon (OC) variant height growth.

Port of the OC height-growth Fortran routines:

- htcalc.f  → :func:`oc_htcalc`              (site-curve evaluator)
- findag.f  → :func:`oc_findag`              (age inversion / FINDAG)
- htgf.f    → :func:`calculate_oc_large_tree_height_growth`
- smhtgf.f  → :func:`calculate_oc_small_tree_height_growth`

OC large-tree height growth is structurally different from variants like SN.
SN uses a per-species ln(DDS)-style regression. OC instead inverts a site
curve to find an effective age, projects the curve forward 5 years, and
multiplies the resulting potential height growth by a CR/RELHT modifier.

CA (Inland California) shares htcalc.f, findag.f, and smhtgf.f with OC at
build time — the OC build directory copies these files from the CA source
tree. Coefficients here therefore apply to both variants.

The OC variant runs natively on 5-year cycles (oc/blkdat.f: DATA YR / 5.0 /).
All increments returned by this module are 5-year increments unless the
caller scales them.

Source files (verbatim line references):
    /Users/cmihiar/Projects/ForestVegetationSimulator/oc/htgf.f
    /Users/cmihiar/Projects/ForestVegetationSimulator/bin/FVSoc_buildDir/htcalc.f
    /Users/cmihiar/Projects/ForestVegetationSimulator/bin/FVSoc_buildDir/findag.f
    /Users/cmihiar/Projects/ForestVegetationSimulator/bin/FVSoc_buildDir/smhtgf.f
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

__all__ = [
    "oc_htcalc",
    "oc_findag",
    "calculate_oc_large_tree_height_growth",
    "calculate_oc_small_tree_height_growth",
    "OC_SPECIES_TO_FVS_INDEX",
    "OC_FVS_INDEX_TO_SPECIES",
]


# ---------------------------------------------------------------------------
# Species index mapping (oc/blkdat.f, JSP array, lines 149-157)
# ---------------------------------------------------------------------------

OC_SPECIES_TO_FVS_INDEX: dict[str, int] = {
    "PC": 1,  "IC": 2,  "RC": 3,  "GF": 4,  "RF": 5,
    "SH": 6,  "DF": 7,  "WH": 8,  "MH": 9,  "WB": 10,
    "KP": 11, "LP": 12, "CP": 13, "LM": 14, "JP": 15,
    "SP": 16, "WP": 17, "PP": 18, "MP": 19, "GP": 20,
    "WJ": 21, "BR": 22, "GS": 23, "PY": 24, "OS": 25,
    "LO": 26, "CY": 27, "BL": 28, "EO": 29, "WO": 30,
    "BO": 31, "VO": 32, "IO": 33, "BM": 34, "BU": 35,
    "RA": 36, "MA": 37, "GC": 38, "DG": 39, "FL": 40,
    "WN": 41, "TO": 42, "SY": 43, "AS": 44, "CW": 45,
    "WI": 46, "CN": 47, "CL": 48, "OH": 49, "RW": 50,
}

OC_FVS_INDEX_TO_SPECIES: dict[int, str] = {
    v: k for k, v in OC_SPECIES_TO_FVS_INDEX.items()
}


def _ispc_for(species_code: str) -> int:
    """Look up the OC Fortran species index (1..50) for a species code."""
    code = (species_code or "").upper()
    return OC_SPECIES_TO_FVS_INDEX.get(code, OC_SPECIES_TO_FVS_INDEX["DF"])


# ---------------------------------------------------------------------------
# HTCALC — site curve evaluator (htcalc.f)
# ---------------------------------------------------------------------------

# Region 5 Dunning/Levitan site curve table (htcalc.f:24-27).
# Six site classes (INDX 1..6) keyed by site index value range.
_DUNL1 = (-88.9, -82.2, -78.3, -82.1, -56.0, -33.8)
_DUNL2 = (49.7067, 44.1147, 39.1441, 35.4160, 26.7173, 18.6400)
_DUNL3 = (2.375, 2.025, 1.650, 1.225, 1.075, 0.875)


def _dunning_levitan_index(site_index: float) -> int:
    """Map site index to Dunning/Levitan curve index 0..5 (htcalc.f:44-56).

    Returns Python 0-based index into _DUNL1/_DUNL2/_DUNL3 (Fortran INDX 1..6).
    """
    if site_index <= 44.0:
        return 5
    if site_index <= 52.0:
        return 4
    if site_index <= 65.0:
        return 3
    if site_index <= 82.0:
        return 2
    if site_index <= 98.0:
        return 1
    return 0


def oc_htcalc(jfor: int, sindx: float, kspec: int, age: float) -> float:
    """Compute potential height at age for a given species and site index.

    Direct port of HTCALC (htcalc.f). Returns the predicted height (feet)
    of a tree of the given species growing at the given site index when
    its age is ``age`` years.

    Args:
        jfor: National forest code. ``jfor <= 5`` selects the R5
            Dunning/Levitan logic; otherwise R6 species-specific curves
            are used. SW Oregon (the OC range) is R6, so callers should
            normally pass ``jfor=6``.
        sindx: Site index (feet, base age 50 in R6).
        kspec: OC species index 1..50 (see OC_SPECIES_TO_FVS_INDEX).
        age: Tree age (years).

    Returns:
        Predicted height (feet). Returns 0.0 for unmapped species.
    """
    # ---- Region 5: Dunning/Levitan (htcalc.f:39-62) ----
    if jfor <= 5:
        idx = _dunning_levitan_index(sindx)
        if age <= 40.0:
            return _DUNL3[idx] * age
        if age <= 0.0:
            return 0.0
        return _DUNL1[idx] + _DUNL2[idx] * math.log(age)

    # ---- Region 6: species-specific curves (htcalc.f:72-181) ----
    if age <= 0.0:
        return 0.0

    # Hann-Scrivani (Res Bull 59, Feb 1987): PC, IC, RC, WF/GF, DF, WH, SP,
    # BR, GS, OS, RW. htcalc.f:77-85
    if kspec in (1, 2, 3, 4, 7, 8, 16, 22, 23, 25, 50):
        if sindx <= 4.5:
            return 4.5
        log_si = math.log(sindx - 4.5)
        toptrm = 1.0 - math.exp(
            -math.exp(-6.21693 + 0.281176 * log_si + 1.14354 * math.log(age))
        )
        bottrm = 1.0 - math.exp(
            -math.exp(-6.21693 + 0.281176 * log_si + 1.14354 * math.log(50.0))
        )
        if bottrm == 0.0:
            return 4.5
        hguess = (sindx - 4.5) * toptrm / bottrm + 4.5
        return hguess * 1.05  # htcalc.f:83

    # Hann-Scrivani pines: JP, WP, PP, MP, GP. htcalc.f:90-98
    if kspec in (15, 17, 18, 19, 20):
        if sindx <= 4.5:
            return 4.5
        log_si = math.log(sindx - 4.5)
        toptrm = 1.0 - math.exp(
            -math.exp(-6.54707 + 0.288169 * log_si + 1.21297 * math.log(age))
        )
        bottrm = 1.0 - math.exp(
            -math.exp(-6.54707 + 0.288169 * log_si + 1.21297 * math.log(50.0))
        )
        if bottrm == 0.0:
            return 4.5
        hguess = (sindx - 4.5) * toptrm / bottrm + 4.5
        return hguess * 1.05  # htcalc.f:96

    # Dolph red fir (Res Pap PSW-206): RF, SH, MH. htcalc.f:103-112
    if kspec in (5, 6, 9):
        term = age * math.exp(age * (-0.0440853)) * 1.41512e-6
        b = sindx * term - 3.04951e6 * term * term + 5.72474e-4
        term2 = 50.0 * math.exp(50.0 * (-0.0440853)) * 1.41512e-6
        b50 = sindx * term2 - 3.04951e6 * term2 * term2 + 5.72474e-4
        denom = 1.0 - math.exp(-b50 * (50.0 ** 1.51744))
        if denom == 0.0:
            return 4.5
        hguess = (sindx - 4.5) * (1.0 - math.exp(-b * (age ** 1.51744))) / denom
        return hguess + 4.5  # htcalc.f:110

    # Dahms lodgepole pine (Res Pap PNW-8): WB, KP, LP, CP, LM, WJ.
    # htcalc.f:117-120
    if kspec in (10, 11, 12, 13, 14, 21):
        hguess = sindx * (-0.0968 + 0.02679 * age - 0.00009309 * age * age)
        return hguess * 1.10  # htcalc.f:119

    # Powers black oak (Res Note PSW-262): PY, WO, BO, VO, BU, DG, FL.
    # htcalc.f:125-130
    if kspec in (24, 30, 31, 32, 35, 39, 40):
        term = math.sqrt(age) - math.sqrt(50.0)
        hguess = (sindx * (1 + 0.322 * term)) - 6.413 * term
        return hguess * 0.70  # htcalc.f:128

    # Porter & Wiant tanoak: TO. htcalc.f:135-138
    if kspec == 42:
        denom = 0.204 + 39.787 / age
        if denom == 0.0:
            return 0.0
        return (sindx / denom) * 0.80  # htcalc.f:137

    # Porter & Wiant madrone: LO, CY, BL, EO, IO, MA, GC. htcalc.f:143-146
    if kspec in (26, 27, 28, 29, 33, 37, 38):
        denom = 0.375 + 31.233 / age
        if denom == 0.0:
            return 0.0
        return (sindx / denom) * 0.80  # htcalc.f:145

    # Porter & Wiant red alder: BM, RA, WN, SY, AS, CW, WI, CN, CL, OH.
    # htcalc.f:151-154
    if kspec in (34, 36, 41, 43, 44, 45, 46, 47, 48, 49):
        denom = 0.649 + 17.556 / age
        if denom == 0.0:
            return 0.0
        return (sindx / denom) * 0.80  # htcalc.f:153

    # Unmapped species (htcalc.f:178-179, CASE DEFAULT)
    return 0.0


# ---------------------------------------------------------------------------
# FINDAG — age inversion (findag.f)
# ---------------------------------------------------------------------------


def oc_findag(
    kspec: int,
    height: float,
    site_index: float,
    jfor: int = 6,
) -> Tuple[float, float, float]:
    """Iteratively find the site-curve age that matches a tree's height.

    Direct port of FINDAG (findag.f). Walks age in 2-year steps from age=2,
    calling :func:`oc_htcalc` until the predicted height matches ``height``
    within 2 ft, with the flat-curve detection logic from findag.f:96-108.

    Args:
        kspec: OC species index 1..50.
        height: Current tree height (feet).
        site_index: Site index (feet).
        jfor: National forest code (1-5 = R5, otherwise R6).

    Returns:
        Tuple ``(sitage, sitht, agmax)``:
            sitage — effective age (years) where the curve matches the tree.
            sitht  — site-curve height at sitage (feet).
            agmax  — maximum age allowed (200 for R6, 400 for R5).
    """
    toler = 2.0
    agmax = 400.0 if jfor <= 5 else 200.0
    age = 2.0
    incrng = 0
    hguess = 0.0
    oldhg = 0.0

    while True:
        oldhg = hguess
        hguess = oc_htcalc(jfor, site_index, kspec, age)

        # Avoid negative predicted heights at small ages from some SI curves
        # (findag.f:79, GED 4/20/18)
        if hguess >= 1.0:
            diff = abs(hguess - height)
            if diff <= toler or height < hguess:
                return age, hguess, agmax

            # Some site curves decrease at the start before increasing.
            # If decreasing, keep going; if curve was increasing but flattened,
            # stop the iteration. findag.f:96-108
            inc = hguess - oldhg
            if oldhg != 0.0 and inc >= 0.05:
                incrng = 1
            if incrng == 1 and inc < 0.05:
                return age, hguess, agmax

        age += 2.0
        if age > agmax:
            # H is too great; max age exceeded. findag.f:113-119
            return agmax, height, agmax


# ---------------------------------------------------------------------------
# HTGF — large-tree height growth (htgf.f)
# ---------------------------------------------------------------------------


def calculate_oc_large_tree_height_growth(
    species_code: str,
    dbh: float,
    height: float,
    crown_ratio: float,
    relative_height: float,
    site_index: float,
    diameter_growth_inside_bark: float,
    bark_ratio: float,
    time_step: float = 5.0,
    jfor: int = 6,
) -> float:
    """Compute periodic height growth for a large OC tree.

    Direct port of subroutine HTGF (htgf.f). Two execution paths:

    1. Redwood (RW, ispc=50) and Giant Sequoia (GS, ispc=23) use a direct
       equation (htgf.f:155-156) with bark-ratio conversion of the 10-year
       outside-bark diameter growth and a height-bounding scheme (htgf.f:177-184).
    2. All other species use the FINDAG → HTCALC → POTHTG approach with a
       crown-ratio + relative-height modifier (htgf.f:196-247).

    Args:
        species_code: pyfvs species code (e.g. ``"DF"``, ``"PP"``).
        dbh: Diameter at breast height (inches).
        height: Current tree height (feet).
        crown_ratio: Crown ratio (proportion 0-1).
        relative_height: Tree height / average stand height. Bounded to
            ``relht <= 1.0`` per htgf.f:228-230.
        site_index: Site index (feet, base age 50 for R6).
        diameter_growth_inside_bark: 5-year inside-bark diameter growth
            (inches). HTGF stores DG(I) as inside-bark, so the caller should
            pass the same value used in DDS calculations.
        bark_ratio: Inside-bark / outside-bark ratio for this tree. Used only
            on the RW/GS path to convert DGLT to outside-bark for the equation.
        time_step: Cycle length in years (default 5 = OC native).
        jfor: National forest code (default 6 = R6).

    Returns:
        Periodic height growth (feet). Floored at 0.1 ft (htgf.f:251).
    """
    ispc = _ispc_for(species_code)
    scale = time_step / 5.0  # Fortran: SCALE = FINT/YR (htgf.f:66)

    # ---- Special path for RW (50) and GS (23): htgf.f:123-193 ----
    if ispc in (50, 23):
        return _oc_large_tree_height_rwgs(
            dbh=dbh,
            height=height,
            site_index=site_index,
            diameter_growth_inside_bark=diameter_growth_inside_bark,
            bark_ratio=bark_ratio,
            scale=scale,
        )

    # ---- General path: FINDAG + HTCALC + CRMOD/RHMOD modifier ----
    sitage, sitht, agmax = oc_findag(ispc, height, site_index, jfor=jfor)

    if sitage > agmax:
        pothtg = 0.10  # htgf.f:204-206
    else:
        agp10 = sitage + 5.0  # htgf.f:208 (5-year projection)
        hguess = oc_htcalc(jfor, site_index, ispc, agp10)
        pothtg = hguess - sitht

    # Crown ratio + relative height modifier (htgf.f:226-243).
    # XMOD = 1.016605 * CRMOD * RHMOD where CRMOD/RHMOD use the Ritchie-Hann
    # coefficients (4.26558, 2.54119, 0.250537).
    cratio = max(0.0, min(1.0, crown_ratio))
    relht = max(1e-6, min(1.0, relative_height))  # htgf.f:228-229
    crmod = 1.0 - math.exp(-4.26558 * cratio)
    rhmod = math.exp(2.54119 * (relht ** 0.250537 - 1.0))
    xmod = 1.016605 * crmod * rhmod
    htg = pothtg * xmod

    # Enforce minimum height growth (htgf.f:251)
    htg = max(htg, 0.1)
    # SCALE multiplier from FINT/YR (htgf.f:256). XHT and HTCON multipliers
    # are user-supplied calibration knobs that default to 1.0 — we omit them.
    htg *= scale
    return max(htg, 0.1)


def _oc_large_tree_height_rwgs(
    dbh: float,
    height: float,
    site_index: float,
    diameter_growth_inside_bark: float,
    bark_ratio: float,
    scale: float,
) -> float:
    """Special-case RW/GS height growth (htgf.f:123-193).

    Functional form (htgf.f:155-156):

        LTHTG = exp(1.412947
                    - 0.000204*D^2
                    + 0.31971 * ln(D)
                    + 0.394005 * ln(SI)
                    + 0.399888 * ln(DG10_OB)
                    - 0.451708 * ln(H))

    The equation is fit on a **10-year outside-bark** diameter increment.
    Internally Fortran scales DGLT to 10 years (`DGLT = DGLT * 2.0`), then
    converts to outside-bark via the bark ratio.

    The result is a 10-year height increment, which is then halved to get
    the 5-year value (htgf.f:159), bounded by tree height (htgf.f:177-184),
    and finally scaled by SCALE = FINT/YR.
    """
    if dbh <= 0.0 or height <= 0.0 or site_index <= 0.0:
        return 0.1

    # Scale 5-year inside-bark DG to 10-year outside-bark DG (htgf.f:141-145).
    # The caller passes a 5-year inside-bark DG (matching DG(I) in Fortran),
    # so we multiply by 2 then divide by bark_ratio to get OB.
    dglt_10 = diameter_growth_inside_bark * 2.0
    if bark_ratio > 0:
        dg10 = dglt_10 / bark_ratio
    else:
        dg10 = dglt_10

    # Constraint: if H < 4.5, force DG10 = 0.1 (htgf.f:148-149)
    if height < 4.5:
        dg10 = 0.1

    if dg10 <= 0.0:
        dg10 = 0.1

    # Equation (htgf.f:155-156)
    log_h = math.log(max(height, 1.0))  # avoid log(0); h < 4.5 path uses dg10=0.1
    lthtg_10 = math.exp(
        1.412947
        - 0.000204 * dbh * dbh
        + 0.31971 * math.log(dbh)
        + 0.394005 * math.log(site_index)
        + 0.399888 * math.log(dg10)
        - 0.451708 * log_h
    )

    # Scale 10-year increment to 5 years (htgf.f:159)
    lthtg = lthtg_10 * 0.5

    # Height bounding (htgf.f:177-184). Trees between 217 ft and 380 ft
    # have growth proportionally reduced; above 380 ft growth is forced
    # to 0.1; below 217 ft full growth is allowed.
    if 217.0 <= height < 380.0:
        hgbnd = 1.0 - ((height - 217.0) / (380.0 - 217.0))
        if hgbnd < 0.1:
            hgbnd = 0.1
    elif height < 217.0:
        hgbnd = 1.0
    else:
        hgbnd = 0.1

    htg = lthtg * hgbnd

    # Floor + cycle scaling (htgf.f:251, 256)
    htg = max(htg, 0.1)
    htg *= scale
    return max(htg, 0.1)


# ---------------------------------------------------------------------------
# SMHTGF — small-tree height growth (smhtgf.f)
# ---------------------------------------------------------------------------

# Per-species adjustment factor (smhtgf.f:92-97). Indexed by Fortran 1..50.
# Note: position 0 is a sentinel; use 1-based indexing throughout.
_OC_SPADJF: Tuple[float, ...] = (
    0.0,  # sentinel for index 0
    1.0, 1.0, 0.9, 1.1, 1.1, 1.1, 1.1, 0.8, 0.9, 0.9,
    1.0, 1.0, 1.0, 1.0, 1.0, 1.1, 1.1, 1.0, 1.1, 0.9,
    1.0, 0.9, 1.0, 0.8, 1.0, 1.1, 0.9, 1.1, 1.1, 1.0,
    1.1, 1.0, 1.1, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
    1.1, 1.0, 1.1, 1.2, 1.2, 1.1, 0.8, 1.0, 1.0, 1.0,
)

# Species → equation group mapping (smhtgf.f:99-104). Group meaning:
#   1 = pines, 2 = firs (incl. Douglas-fir), 3 = black oak,
#   4 = tanoak, 5 = coast redwood
_OC_SMHTGF_MAPSP: Tuple[int, ...] = (
    0,  # sentinel for index 0
    2, 2, 2, 2, 2, 2, 2, 2, 2, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 2, 5, 2, 1, 3, 3, 3, 3, 3,
    3, 3, 3, 4, 3, 3, 4, 3, 4, 3,
    3, 4, 3, 3, 3, 3, 2, 4, 3, 5,
)


def calculate_oc_small_tree_height_growth(
    species_code: str,
    height: float,
    crown_ratio: float,
    site_index: float,
    bal: float,
    relative_height: float,
    time_step: float = 5.0,
) -> float:
    """Compute 5-year small-tree height growth for an OC tree.

    Direct port of subroutine SMHTGF (smhtgf.f). Five species groups via
    the MAPSP table (smhtgf.f:99-104). The pine, black oak, and tanoak
    forms use a basal-area-larger competition term; the fir/Douglas-fir
    form uses the same Ritchie-Hann CR/RELHT modifier as large-tree HTGF;
    coast redwood uses an age-based Chapman-Richards inversion.

    Args:
        species_code: pyfvs species code.
        height: Current tree height (feet).
        crown_ratio: Crown ratio (proportion 0-1; converted to 0-10 inside
            the fir branch, matching smhtgf.f:151).
        site_index: Site index (feet, base age 50).
        bal: Basal area in larger trees (sq ft/acre). Floored at 5.0
            (smhtgf.f:115-116).
        relative_height: Tree height / dominant-stand height (used by the
            fir branch only).
        time_step: Cycle length in years (default 5 = OC native). Increments
            for time steps other than 5 are scaled linearly.

    Returns:
        Height growth (feet) over the cycle. Floored at 0.1 ft (smhtgf.f:204).
    """
    ispc = _ispc_for(species_code)
    if ispc < 1 or ispc > 50:
        return 0.1

    spadjf = _OC_SPADJF[ispc]
    group = _OC_SMHTGF_MAPSP[ispc]

    # smhtgf.f:113 — site-index adjustment factor
    factor = spadjf * (0.80 + 0.004 * (site_index - 50.0))

    tembal = max(bal, 5.0)  # smhtgf.f:115-116

    if group == 1:
        # PINES — smhtgf.f:122-125
        cr = max(0.0, min(1.0, crown_ratio))
        htgr = math.exp(
            0.7452
            - 0.003271 * bal
            - 0.1632 * cr
            + 0.0217 * cr * cr
            + 0.00536 * site_index
        ) * factor * 1.75

    elif group == 2:
        # FIRS (incl. Douglas-fir) — smhtgf.f:149-156
        # DOMHTGR is a 5-year dominant-height increment fit by Hann-Scrivani
        # (Res Bull 59); SMHMOD adjusts via crown ratio and relative height.
        domhtgr = 5.0 * (2.2227 + 0.4314 * site_index) / (29.0 - 0.05 * site_index)
        # Fortran converts CR (0-100 percent) to 0-10 by /10. Our crown_ratio
        # is already 0-1, so multiply by 10 to match the 0-10 input.
        cr10 = max(0.0, min(10.0, crown_ratio * 10.0))
        crmod = 1.0 - math.exp(-4.26558 * cr10)
        relht = max(1e-6, relative_height)
        rhmod = math.exp(2.54119 * (relht ** 0.250537 - 1.0))
        smhmod = 1.016605 * crmod * rhmod
        htgr = domhtgr * smhmod

    elif group == 3:
        # BLACK OAK — smhtgf.f:163-164
        htgr = math.exp(3.817 - 0.7829 * math.log(tembal)) * factor

    elif group == 4:
        # TANOAK — smhtgf.f:170-171
        htgr = math.exp(3.385 - 0.5898 * math.log(tembal)) * factor

    else:
        # COAST REDWOOD — smhtgf.f:176-198. Uses an age-based Chapman-Richards
        # form: invert H to get age, project age+5, take the difference.
        htgr = _oc_small_tree_height_redwood(height, site_index)

    htgr = max(htgr, 0.1)  # smhtgf.f:204

    if time_step != 5.0:
        htgr *= time_step / 5.0

    return htgr


def _oc_small_tree_height_redwood(height: float, site_index: float) -> float:
    """Small-tree height growth for Coast Redwood (smhtgf.f:176-198)."""
    htmax = 2.242202 * site_index
    if htmax - height <= 1.0:
        return 0.0
    if site_index <= 0:
        return 0.1

    # Invert the Chapman-Richards relationship to get current age.
    # H = 2.242202 * SI * (1 - exp(-0.010742 * AGE))^0.919076
    ratio = height / (2.242202 * site_index)
    if ratio >= 1.0:
        return 0.0
    inner = ratio ** (1.0 / 0.919076)
    if inner >= 1.0 or inner <= 0.0:
        return 0.0
    age1 = (1.0 / -0.010742) * math.log(1.0 - inner)
    age2 = age1 + 5.0

    h1 = 2.242202 * site_index * (1.0 - math.exp(-0.010742 * age1)) ** 0.919076
    h2 = 2.242202 * site_index * (1.0 - math.exp(-0.010742 * age2)) ** 0.919076
    return h2 - h1

"""LS variant BALMOD competition modifier.

Port of `ForestVegetationSimulator/ls/balmod.f` (SUBROUTINE BALMOD).

Fortran comment:
    THIS SUBROUTINE COMPUTES THE VALUE OF A GROWTH MODIFIER BASED ON BAL.
    ORIGINALLY THIS WAS JUST PART OF THE LARGE TREE DIAMETER GROWTH
    SEQUENCE. HOWEVER, THERE NEEDS TO BE A SIMILAR ACCOUNTING OF STAND
    POSITION IN THE LARGE TREE AND SMALL TREE HEIGHT GROWTH ESTIMATION
    SEQUENCE. THIS ROUTINE IS CALLED BY DGF, HTGF, AND RGNTHW.

Equation form:
    OMEGA = B1 * (1 - exp(-B2 * D/RMSQD))^B3 + B4   if D/RMSQD >= CHECK
          = B4                                       otherwise
    BETA  = C1 * (RMSQD + 1)^C2
    GM    = 1 - exp(-OMEGA * BETA * sqrt(BAMAX1/BA - 1))
    GM    = max(0.2, GM)

Fortran balmod.f line 97-98 clamps the EXP argument to avoid underflow:
    IF (EXPVAL .GT. 86) EXPVAL = 86.0
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Dict

from .config_loader import load_coefficient_file


_BALMOD_COEFFS_CACHE: Dict[str, Dict[str, float]] | None = None


def _load_coefficients() -> Dict[str, Dict[str, float]]:
    """Load the full BALMOD coefficient table once and cache it."""
    global _BALMOD_COEFFS_CACHE
    if _BALMOD_COEFFS_CACHE is None:
        data = load_coefficient_file('ls/ls_balmod_coefficients.json')
        _BALMOD_COEFFS_CACHE = data['species_coefficients']
    return _BALMOD_COEFFS_CACHE


@lru_cache(maxsize=128)
def _coeffs_for(species: str) -> Dict[str, float]:
    table = _load_coefficients()
    sp = species.upper()
    if sp not in table:
        # Fortran position 44 is blank; anything else should be an error
        # for LS, but fall back to the Fortran 25*X tail values (copied
        # from position 68 = MA) for unknown species to keep the pipeline
        # running during ports. Log at caller site if needed.
        sp = 'MA'
    return table[sp]


def ls_balmod(species: str, dbh: float, ba: float, rmsqd: float) -> float:
    """Compute the LS BALMOD growth modifier GM for a single tree.

    Args:
        species: LS species code (2-letter).
        dbh: Tree DBH (inches).
        ba: Stand basal area (sq ft / acre).
        rmsqd: Root-mean-square diameter of the stand (inches).

    Returns:
        Growth modifier GM in [0.2, 1.0]. Caller applies it to DG or HG.
    """
    c = _coeffs_for(species)
    check = c['check']
    b1, b2, b3, b4 = c['b1'], c['b2'], c['b3'], c['b4']
    c1, c2 = c['c1'], c['c2']
    bamax1 = c['bamax1']

    # OMEGA — Fortran balmod.f:84-100
    if rmsqd <= 0.0 or dbh / rmsqd < check:
        omega = b4
    else:
        expval = b2 * dbh / rmsqd
        if expval > 86.0:
            expval = 86.0
        omega = b1 * (1.0 - math.exp(-expval)) ** b3 + b4

    # BETA — balmod.f:106
    beta = c1 * (rmsqd + 1.0) ** c2

    # BA clamp — balmod.f:107-111
    batemp = 1.0 if ba <= 1.0 else ba

    # ARG = (BAMAX1/BA) - 1 — balmod.f:112-113
    arg = (bamax1 / batemp) - 1.0
    if arg < 0.0:
        arg = 0.0

    # GM — balmod.f:117-118
    gm = 1.0 - math.exp(-omega * beta * math.sqrt(arg))
    if gm < 0.2:
        gm = 0.2
    return gm


def clear_cache() -> None:
    """Drop cached coefficients (useful for tests that reload configs)."""
    global _BALMOD_COEFFS_CACHE
    _BALMOD_COEFFS_CACHE = None
    _coeffs_for.cache_clear()

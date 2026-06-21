"""Parity tests: pyfvs CS (Central States) variant vs native FVScs.

CS is a 10-year-cycle variant covering 96 species across IL, IN, IA, MO
(Midwest hardwood forests). The variant inherits the LS DG equation form
(linear DDS with RELDBH) but uses CS-specific coefficients and a Wykoff-vs-
Curtis-Arney H-D dispatch (per `cs/htdbh.f` IWYKCA flag, 87/96 species use
Wykoff).

These tests cover a small number of representative scenarios. The
exhaustive 96-species sweep lives at `scripts/cs_species_sweep.py` and is
the discovery tool for coefficient or algorithm gaps.
"""

from __future__ import annotations

import pytest

from tests.parity._helpers import (
    assert_metrics_close_mean,
    run_native,
    run_pyfvs_multi_seed,
)




@pytest.mark.xfail(strict=True, reason="Tightened tolerance regime 2026-06-21 (floor 0.5%, vol 1.0%; prior 5%/10% band masked this). BA +3.52%, QMD +1.80%, topH +0.55%, vol +4.61% exceed band (CS was 4/4 'clean' only under the loose band). CS DG/HG+volume residual.")
def test_cs_gold_standard_wo_si60_30yr(require_native_variant, parity_tolerance):
    """Gold-standard CS scenario: 500 WO at SI=60 grown 30 years (3 cycles).

    White oak (WO) is the CS default species and the dominant hardwood
    across the Central States region. SI=60 is a typical Midwest oak-
    hickory site. 30yr is 3 CS cycles — enough for trees to fully exit
    the small-tree regime.
    """
    require_native_variant("CS")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="CS",
        species="WO",
        site_index=60,
        trees_per_acre=500,
        years=30,
        bare_ground=True,
    )
    native_result = run_native(
        variant="CS",
        species="WO",
        site_index=60,
        trees_per_acre=500,
        years=30,
    )
    assert_metrics_close_mean(
        pyfvs_result, native_result, parity_tolerance,
    )


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        # Major CS commercial species at productive sites. All currently
        # expected to fail until blend zone, Wykoff, and establishment
        # fixes land. Strict xfail catches silent improvements.
        # Closed 2026-04-21 by cs/essubh.f HHTMAX-clamp fix — pyfvs was
        # clamping H(CARAGE) at HHTMAX before the (H/CARAGE)*5 linear
        # interpolation, while native applies HHTMAX only after final
        # REGENT LESTB growth. Closed RO, SM, YP at 30yr.
        pytest.param("RO", 65, 500, 30, id="ro-si65-30yr", marks=pytest.mark.xfail(strict=True, reason='Tightened tolerance regime 2026-06-21 (floor 0.5%, vol 1.0%; prior 5%/10% band masked this). BA +2.69%, QMD +1.31%, topH +2.23%, vol +3.49% exceed band. CS DG/HG+volume residual.')),
        pytest.param("SM", 60, 500, 30, id="sm-si60-30yr", marks=pytest.mark.xfail(strict=True, reason='Tightened tolerance regime 2026-06-21 (floor 0.5%, vol 1.0%; prior 5%/10% band masked this). topH +1.06% exceeds band (others incl. vol +0.85% within). CS HG residual.')),
        pytest.param("YP", 70, 500, 30, id="yp-si70-30yr", marks=pytest.mark.xfail(strict=True, reason='Tightened tolerance regime 2026-06-21 (floor 0.5%, vol 1.0%; prior 5%/10% band masked this). TPA +0.92%, BA +1.93%, QMD +1.43%, topH +0.79%, vol +3.09% exceed band. CS DG/HG+volume residual.')),
    ],
)
def test_cs_expanded_species_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    """Expanded CS species parity — commercial species beyond WO.

    All currently xfail pending CS-specific Fortran-faithful fixes.
    Strict xfail protects against silent improvements going unnoticed
    and provides canonical scenarios to regression-gate against.
    """
    require_native_variant("CS")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="CS",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
    )
    native_result = run_native(
        variant="CS",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close_mean(
        pyfvs_result, native_result, parity_tolerance,
    )

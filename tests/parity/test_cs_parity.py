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


CS_PARITY_N_SEEDS = 10


@pytest.mark.xfail(
    reason="Baseline 2026-04-16: BA +22.9%, vol +46.2% over native at "
    "WO SI=60 30yr. Same pattern as pre-fix LS — pyfvs missing CS-specific "
    "blend zone (cs/regent.f:98 XMIN=3, XMAX=5), Wykoff H-D dispatch "
    "(cs/htdbh.f IWYKCA, 87/96 species), and LS-style establishment-cycle "
    "shortening (cs/regent.f:118-124 LESTB FNT-5). Tracking parity through "
    "a sequence of Fortran-faithful fixes mirroring LS Phase 1-7.",
    strict=True,
)
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
        n_seeds=CS_PARITY_N_SEEDS,
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
        skip_keys=("volume",),  # CS uses simplified volume library; track separately.
    )


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        # Major CS commercial species at productive sites. All currently
        # expected to fail until blend zone, Wykoff, and establishment
        # fixes land. Strict xfail catches silent improvements.
        pytest.param(
            "RO", 65, 500, 30, id="ro-si65-30yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Baseline 2026-04-16: pre-fix CS over-prediction. "
                "Northern red oak — second most planted CS species after WO.",
            ),
        ),
        pytest.param(
            "SM", 60, 500, 30, id="sm-si60-30yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Baseline 2026-04-16: pre-fix CS over-prediction. "
                "Sugar maple — high tolerance hardwood.",
            ),
        ),
        pytest.param(
            "YP", 70, 500, 30, id="yp-si70-30yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Baseline 2026-04-16: pre-fix CS over-prediction. "
                "Yellow-poplar — fast-grower, distinct CS DG coefficients.",
            ),
        ),
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
        n_seeds=CS_PARITY_N_SEEDS,
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
        skip_keys=("volume",),
    )

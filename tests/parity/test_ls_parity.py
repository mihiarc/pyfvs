"""Parity tests: pyfvs LS (Lake States) variant vs native FVSls.

LS is a 10-year-cycle variant covering 67 species across the Lake States
region (MN, WI, MI). The variant diverges from SN in three major ways:

  - Diameter growth: linear DDS with RELDBH (vs SN's ln(DDS) with RELHT)
  - Height growth: Fortran htgf.f uses a BALMOD competition modifier
    (ported in `ls_balmod.py`) rather than SN's shade-tolerance modifier
  - Crown ratio: TWIGS equation with Fortran ls/crown.f BCR coefficients

Parity status as of 2026-04-16 (sweep run after Phase 1+2):
  - 5 species pass baseline (RN, WA, ST, PR, WI)
  - 8 warn, 54 fail (primary residual: diameter growth coefficient drift)

These tests cover a small number of representative scenarios. The
exhaustive 67-species sweep lives at `scripts/ls_species_sweep.py` and
is the discovery tool for coefficient or algorithm gaps.
"""

from __future__ import annotations

import pytest

from tests.parity._helpers import (
    assert_metrics_close_mean,
    run_native,
    run_pyfvs_multi_seed,
)


# 10 seeds matches the SN suite — balances sampling noise against runtime.
LS_PARITY_N_SEEDS = 10


@pytest.mark.xfail(
    reason="BA passes (+0.39%) but top_height under-predicts by ~8% (pyfvs 38.58 "
    "vs native 41.97 @ 30yr). Root cause: Fortran ls/htgf.f:108 applies "
    "HTG(I)*(1.0+OLDRN(I))*GMOD where OLDRN is per-tree stochastic autocorrelation "
    "from dgf.f. pyfvs Phase 1 (2026-04-16) ported GMOD faithfully but not OLDRN, "
    "so dominant trees (RELHTA=1.0) are capped at 0.8× POTHTG without the ~25% "
    "stochastic lift that compensates in native. Fix requires porting OLDRN HG "
    "autocorrelation — separate work item.",
    strict=True,
)
def test_ls_gold_standard_rn_si60_30yr(require_native_variant, parity_tolerance):
    """Gold-standard LS scenario: 500 RN at SI=60 grown 30 years (3 cycles).

    Red pine (RN) is the LS default species and the most-planted timber species
    in the Lake States. SI=60 is a typical productive site. 30yr is 3 LS cycles
    — enough for trees to fully exit the small-tree regime.

    Multi-seed pyfvs mean vs single native run. Strict 5% BA tolerance matches
    SN gold-standard criterion.
    """
    require_native_variant("LS")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="LS",
        species="RN",
        site_index=60,
        trees_per_acre=500,
        years=30,
        bare_ground=True,
        n_seeds=LS_PARITY_N_SEEDS,
    )
    native_result = run_native(
        variant="LS",
        species="RN",
        site_index=60,
        trees_per_acre=500,
        years=30,
    )
    assert_metrics_close_mean(
        pyfvs_result, native_result, parity_tolerance,
        skip_keys=("volume",),  # LS uses simplified volume library (Phase 5 open).
    )


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        # WA was a coincidental pre-Wykoff-fix pass: Curtis-Arney H-D inverse
        # under-predicted DBH during the small-tree phase by just enough to
        # offset downstream LS DG over-prediction. The 2026-04-16 IWYKCA port
        # (Wykoff inverse for species WHERE Fortran htdbh.f flags IWYKCA=0,
        # including WA at species_index=29) removed the masking and exposed
        # the real LS DG over-prediction (+17% BA on the sweep). Xfail until
        # the species-level LS DG coefficient drift is resolved — same root
        # cause family as jp/sm/qa xfails below.
        pytest.param(
            "WA", 60, 500, 30, id="wa-si60-30yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason=(
                    "Sweep 2026-04-16: BA +17.22% after Fortran-faithful "
                    "IWYKCA Wykoff-inverse port. Prior Curtis-Arney inverse "
                    "coincidentally masked LS DG over-prediction. Gap is now "
                    "visible and tracks the JP/SM/QA DG coefficient residual."
                ),
            ),
        ),
    ],
)
def test_ls_off_baseline_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    """LS off-baseline scenarios currently within tolerance on the sweep."""
    require_native_variant("LS")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="LS",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
        n_seeds=LS_PARITY_N_SEEDS,
    )
    native_result = run_native(
        variant="LS",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close_mean(
        pyfvs_result, native_result, parity_tolerance,
        skip_keys=("volume",),  # LS uses simplified volume library (Phase 5 open).
    )


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        # Commercial species currently fail >5%. Keeping as xfail documents the
        # residual gap (primarily LS diameter-growth coefficient drift, not
        # crown-ratio or height-growth — Phase 1+2 ported those faithfully).
        pytest.param(
            "JP", 60, 500, 30, id="jp-si60-30yr",
            marks=pytest.mark.xfail(
                reason="Sweep 2026-04-16: BA +15.16% (>5% tol). Root cause is "
                "the LS large-tree DG model over-predicting — ls_diameter_growth.py "
                "needs Fortran dgf.f cross-check against buildDir DGCOEF/DGSPEC "
                "DATA blocks. Crown ratio (Phase 2) and height growth (Phase 1 "
                "BALMOD) are now Fortran-faithful so the residual is DG-specific.",
                strict=True,
            ),
        ),
        pytest.param("SM", 55, 500, 30, id="sm-si55-30yr"),
        pytest.param(
            "QA", 70, 500, 30, id="qa-si70-30yr",
            marks=pytest.mark.xfail(
                reason="Sweep 2026-04-16: BA +46.13% (>5% tol). Quaking aspen (QA) "
                "is the largest LS BA drift among commercial species. Extreme "
                "over-prediction suggests QA-specific DG coefficient issue "
                "(possibly the 25*X tail-species default fallback in Fortran "
                "DATA blocks being mis-mapped). Requires ls_diameter_growth.py "
                "inspection against Fortran dgf.f.",
                strict=True,
            ),
        ),
    ],
)
def test_ls_expanded_species_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    """Expanded LS species parity — commercial species beyond RN.

    All currently xfail due to LS diameter-growth drift. Leaving them here (as
    strict xfail) protects against silent improvements being unnoticed and
    provides canonical scenarios to regression-gate once DG is fixed.
    """
    require_native_variant("LS")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="LS",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
        n_seeds=LS_PARITY_N_SEEDS,
    )
    native_result = run_native(
        variant="LS",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close_mean(
        pyfvs_result, native_result, parity_tolerance,
        skip_keys=("volume",),  # LS uses simplified volume library (Phase 5 open).
    )

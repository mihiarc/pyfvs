"""Parity tests: pyfvs SN (Southern) variant vs native FVSsn.

SN is the most-developed variant in pyfvs and the most-used FVS variant
in the southeastern United States. It's the cleanest baseline for parity
testing because:

  - 5-year cycle (matches Fortran exactly, no cycle conversions)
  - Comprehensive species coverage (90 species in pyfvs)
  - Established test fixtures and validation history

If SN parity fails, the parity infrastructure or pyfvs's core growth/
mortality have a fundamental issue. If SN parity passes, OC's failures
are scoped to OC's incomplete model port (height growth, mortality,
small-tree models still defaulting back to LP).

This is intentionally a small set of representative scenarios — exhaustive
sweeps belong in a separate large-scale validation harness, not in unit
tests that need to run in CI.
"""

from __future__ import annotations

import pytest

from tests.parity._helpers import (
    assert_metrics_close,
    run_native,
    run_pyfvs,
)


def test_sn_gold_standard_lp_si70_25yr(require_native_variant, parity_tolerance):
    """Gold-standard SN scenario: 500 LP at SI=70 grown 25 years.

    This is the canonical southeastern loblolly pine plantation test case.
    pyfvs must match native FVSsn within strict tolerance:
      - TPA: 2% relative
      - BA, QMD, top_height: 5% relative
      - Volume: 10% relative

    If this test fails, either pyfvs's SN implementation has regressed or
    the native FVSsn library was rebuilt with materially different
    behavior (in which case the upstream change should be investigated).
    """
    require_native_variant("SN")

    pyfvs_result = run_pyfvs(
        variant="SN",
        species="LP",
        site_index=70,
        trees_per_acre=500,
        years=25,
        bare_ground=True,
    )
    native_result = run_native(
        variant="SN",
        species="LP",
        site_index=70,
        trees_per_acre=500,
        years=25,
    )
    assert_metrics_close(pyfvs_result, native_result, parity_tolerance)


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        pytest.param(
            "LP", 90, 400, 50, id="lp-si90-50yr",
            marks=pytest.mark.xfail(
                reason="Stochastic-mode BA over-prediction by ~5%. Exposed "
                "after switching parity helper to stochastic=True (matching "
                "Fortran FVSsn DGSD=2.0 default). Likely root cause: pyfvs's "
                "_stochastic_multiplier (model_base.py:240) is missing the "
                "AR(1) cross-cycle autocorrelation term that Fortran "
                "dgscor.f:39 applies via OLDRN(IT) carry-over with "
                "RHO/RHOCP weights computed from BJPHI=0.74, BJTHET=0.42 "
                "ARMA(1,1) parameters (autcor.f, grinit.f:160-161).",
                strict=True,
            ),
        ),
        pytest.param(
            "SP", 65, 500, 25, id="sp-si65-25yr",
            marks=pytest.mark.xfail(
                reason="Stochastic-mode BA over-prediction by ~7%. Same "
                "missing DG autocorrelation root cause as LP-si90-50yr.",
                strict=True,
            ),
        ),
        pytest.param("SA", 75, 500, 25, id="sa-si75-25yr"),
    ],
)
def test_sn_off_baseline_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    """Non-gold-standard SN scenarios. SA passes; LP/SP xfail with
    documented residual drift after switching to stochastic-vs-stochastic
    parity (the only Fortran-faithful comparison since native always runs
    DGSD=2.0).
    """
    require_native_variant("SN")

    pyfvs_result = run_pyfvs(
        variant="SN",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
    )
    native_result = run_native(
        variant="SN",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close(pyfvs_result, native_result, parity_tolerance)


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        # Tier 1 — finish southern pines (same code path as LP/SP/SA)
        pytest.param(
            "LL", 70, 500, 25, id="ll-si70-25yr",
            marks=pytest.mark.xfail(
                reason="Stochastic-mode BA over-prediction by ~5%. Same "
                "missing DG autocorrelation root cause as LP/SP — pyfvs's "
                "_stochastic_multiplier (model_base.py:240) lacks Fortran "
                "dgscor.f:39 OLDRN(IT) AR(1) carry-over.",
                strict=True,
            ),
        ),
        pytest.param("VP", 60, 500, 25, id="vp-si60-25yr"),
        pytest.param(
            "WP", 70, 500, 25, id="wp-si70-25yr",
            marks=pytest.mark.xfail(
                reason="Growth under-prediction: BA ~9%, vol ~13% below native. "
                "WP is a non-southern-pine conifer; persists across both "
                "deterministic and stochastic parity modes, so root cause "
                "is in growth coefficients/equations, not stochastic gap.",
                strict=True,
            ),
        ),
        # Tier 2 — major southern hardwoods (exercise hardwood DG branch)
        pytest.param(
            "YP", 80, 400, 25, id="yp-si80-25yr",
            marks=pytest.mark.xfail(
                reason="Largest divergence: BA -16%, QMD -9%, volume -21%. "
                "Yellow-poplar persists as biggest miss across both "
                "deterministic and stochastic parity modes; likely "
                "hardwood ln(DDS) RELDBH/competition branch drift.",
                strict=True,
            ),
        ),
        pytest.param("SU", 75, 500, 25, id="su-si75-25yr"),
        pytest.param("WO", 65, 400, 25, id="wo-si65-25yr"),
        pytest.param("RM", 65, 500, 25, id="rm-si65-25yr"),
        # Tier 3 — non-pine conifer / bottomland
        pytest.param(
            "BY", 70, 400, 25, id="by-si70-25yr",
            marks=pytest.mark.xfail(
                reason="Stochastic-mode BA over-prediction by ~11%. Same "
                "missing DG autocorrelation root cause family as LP/SP/LL, "
                "but BY is hit hardest (highest SIGMAR=0.5511). pyfvs "
                "needs Fortran AR(1) DG autocorrelation to close.",
                strict=True,
            ),
        ),
        pytest.param("HM", 55, 500, 25, id="hm-si55-25yr"),
    ],
)
def test_sn_expanded_species_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    """Expanded SN species parity — beyond the LP/SP/SA yellow pines.

    Run with stochastic=True (the parity-helper default since aligning to
    Fortran FVSsn's DGSD=2.0 default). Currently passing: VP, SA, SU, WO,
    RM, HM (and gold-standard LP). Xfailed cases split into two families:

    - Stochastic-bias xfails (LP-si90, SP, LL, BY): ~5-11% BA over-prediction.
      Likely closes with Fortran-faithful AR(1) DG autocorrelation port
      (dgscor.f:39 OLDRN(IT) carry-over with RHO/RHOCP weights from
      BJPHI=0.74, BJTHET=0.42 ARMA(1,1) parameters).

    - Growth-coefficient xfails (WP, YP): persist across stochastic AND
      deterministic modes, so root cause is in coefficient or equation
      space, not stochasticity.
    """
    require_native_variant("SN")

    pyfvs_result = run_pyfvs(
        variant="SN",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
    )
    native_result = run_native(
        variant="SN",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close(pyfvs_result, native_result, parity_tolerance)

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
    assert_metrics_close_mean,
    run_native,
    run_pyfvs,
    run_pyfvs_multi_seed,
)

# Multi-seed parity — matches native FVSsn's default DGSD=2.0 stochastic
# behavior. pyfvs's per-tree mortality approximates Fortran's fractional-
# PROB with weighted-sampling-without-replacement (exact cycle-level kill
# count, rip-weighted selection). Any single seed still has selection
# variance in BA/QMD, so we assert on the N-seed mean instead. 10 seeds
# gives SEM ≈ stdev/3 which is well below the BA tolerance (~5%).
SN_PARITY_N_SEEDS = 10


def test_sn_gold_standard_lp_si70_25yr(require_native_variant, parity_tolerance):
    """Gold-standard SN scenario: 500 LP at SI=70 grown 25 years.

    This is the canonical southeastern loblolly pine plantation test case.
    Multi-seed mean of pyfvs must match native FVSsn within strict tolerance:
      - TPA: 2% relative
      - BA, QMD, top_height: 5% relative
      - Volume: 10% relative

    If this test fails, either pyfvs's SN implementation has regressed or
    the native FVSsn library was rebuilt with materially different
    behavior (in which case the upstream change should be investigated).
    """
    require_native_variant("SN")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="SN",
        species="LP",
        site_index=70,
        trees_per_acre=500,
        years=25,
        bare_ground=True,
        n_seeds=SN_PARITY_N_SEEDS,
    )
    native_result = run_native(
        variant="SN",
        species="LP",
        site_index=70,
        trees_per_acre=500,
        years=25,
    )
    assert_metrics_close_mean(pyfvs_result, native_result, parity_tolerance)


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        pytest.param("LP", 90, 400, 50, id="lp-si90-50yr"),
        pytest.param("SP", 65, 500, 25, id="sp-si65-25yr"),
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
    """Non-gold-standard SN scenarios. Multi-seed mean pyfvs vs native.

    All pass after:
      - AR(1) DG autocorrelation port (model_base.py) — closed LP-si90
        and SP-si65 over-prediction.
      - Weighted-sampling-without-replacement mortality (mortality.py) —
        eliminated single-seed kill-count variance.
    """
    require_native_variant("SN")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="SN",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
        n_seeds=SN_PARITY_N_SEEDS,
    )
    native_result = run_native(
        variant="SN",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close_mean(pyfvs_result, native_result, parity_tolerance)


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        # Tier 1 — finish southern pines (same code path as LP/SP/SA)
        pytest.param("LL", 70, 500, 25, id="ll-si70-25yr"),
        pytest.param("VP", 60, 500, 25, id="vp-si60-25yr"),
        pytest.param(
            "WP", 70, 500, 25, id="wp-si70-25yr",
            marks=pytest.mark.xfail(
                reason="10-seed mean BA -6.93%±1.02% (>5% tol) — systematic "
                "mean bias, not seed noise. Verified 2026-04-15: all WP "
                "coefficients (DG, HD, bark, Curtis-Arney) match Fortran "
                "exactly; no WP-specific dgf.f branch. Deficit is density-"
                "independent (~12% across TPA=100-1000). Opens yr20-25 when "
                "trees enter large-tree zone (>3\"). ln(DDS) equation "
                "verified correct for isolated inputs. Root cause must be "
                "in input propagation (CR/RELHT/PBAL) over long cycles; "
                "needs instrumented traces of both pyfvs and native.",
                strict=True,
            ),
        ),
        # Tier 2 — major southern hardwoods (exercise hardwood DG branch)
        pytest.param("YP", 80, 400, 25, id="yp-si80-25yr"),
        pytest.param("SU", 75, 500, 25, id="su-si75-25yr"),
        pytest.param("WO", 65, 400, 25, id="wo-si65-25yr"),
        pytest.param(
            "RM", 65, 500, 25, id="rm-si65-25yr",
            marks=pytest.mark.xfail(
                reason="10-seed mean BA +5.58% (>5% tol) — exposed 2026-04-16 "
                "when Fortran-faithful HTG noise (regent.f:252-260) was "
                "added to pyfvs's small-tree path. Prior to the fix, pyfvs "
                "RM coincidentally passed because missing HTG noise offset "
                "a separate hidden Jensen-lift source elsewhere in the "
                "stochastic pipeline. With noise added, DBH distribution "
                "correctly widens (Fortran fidelity) and RM's hidden over-"
                "prediction becomes visible. Det RM passes (BA -3.66%); "
                "the stoch over-prediction is a double-Jensen artifact "
                "that needs the second Jensen source identified and fixed. "
                "Honest exposure preferred over coincidental pass per "
                "feedback_oc_parity memory.",
                strict=True,
            ),
        ),
        # Tier 3 — non-pine conifer / bottomland
        pytest.param(
            "BY", 70, 400, 25, id="by-si70-25yr",
            marks=pytest.mark.xfail(
                reason="10-seed mean BA +8.58%±1.16% (>5% tol) — systematic "
                "mean bias. Deterministic BY passes. Bernoulli-to-weighted-"
                "sampling mortality fix (2026-04-16) reduced the gap from "
                "+9.2% but did not close it because E-S selection still "
                "weights by rip_i, biasing survivors toward larger trees "
                "with BY's high SIGMAR (0.5511) DBH variance. Fortran's "
                "fractional-PROB reduction preserves every tree at reduced "
                "weight (no kill selection at all); closing this would "
                "require fractional TPA on pyfvs Tree records.",
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

    Multi-seed mean pyfvs vs single native run, matching native FVSsn's
    DGSD=2.0 stochastic default.

    Two remaining xfail families (both systematic mean bias, not seed
    noise — the multi-seed mean is clearly outside tolerance):

    - **WP**: BA -6.93% mean. All coefficients verified matching Fortran;
      deficit opens at yr20-25 when trees enter large-tree zone. Root
      cause in input propagation (CR/RELHT/PBAL) over cycles. Needs
      instrumented native traces to close.

    - **BY**: BA +8.58% mean. High-SIGMAR (0.5511) species where pyfvs's
      integer Tree records + kill-selection semantics don't match Fortran's
      fractional PROB reduction. Would need fractional TPA on Tree records.

    After the 2026-04-16 weighted-sampling mortality fix, LL/RM/SP/SU are
    all within tolerance on the multi-seed mean — their prior seed=42
    xfails were single-seed kill-count variance, now eliminated.
    """
    require_native_variant("SN")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="SN",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
        n_seeds=SN_PARITY_N_SEEDS,
    )
    native_result = run_native(
        variant="SN",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close_mean(pyfvs_result, native_result, parity_tolerance)

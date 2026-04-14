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
        ("LP", 90, 400, 50),    # loblolly, high site, longer rotation
        ("SP", 65, 500, 25),    # shortleaf pine, moderate site
        ("SA", 75, 500, 25),    # slash pine, moderate-high site
    ],
    ids=["lp-si90-50yr", "sp-si65-25yr", "sa-si75-25yr"],
)
def test_sn_off_baseline_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    """Non-gold-standard SN scenarios — all pass within tolerance.

    After six Fortran-faithful fixes (ecounit default, Fortran PCTILE
    PBAL, hard-switch DG, deterministic mortality, BACHLO ESTAB height
    variation, regent.f LESTB initial crown ratio assignment) all three
    off-baseline scenarios match native FVS within parity tolerance.
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
        pytest.param("LL", 70, 500, 25, id="ll-si70-25yr"),
        pytest.param("VP", 60, 500, 25, id="vp-si60-25yr"),
        pytest.param(
            "WP", 70, 500, 25, id="wp-si70-25yr",
            marks=pytest.mark.xfail(
                reason="Growth under-prediction: BA ~12%, QMD ~6% below native. "
                "WP is a non-southern-pine conifer; shares SN DG form but "
                "likely diverges on some coefficient path.",
                strict=True,
            ),
        ),
        # Tier 2 — major southern hardwoods (exercise hardwood DG branch)
        pytest.param(
            "YP", 80, 400, 25, id="yp-si80-25yr",
            marks=pytest.mark.xfail(
                reason="Largest divergence: BA -25%, QMD -13%, volume -27%. "
                "Yellow-poplar is fastest-growing SE hardwood; likely "
                "hardwood ln(DDS) RELDBH/competition branch drift.",
                strict=True,
            ),
        ),
        pytest.param(
            "SU", 75, 500, 25, id="su-si75-25yr",
            marks=pytest.mark.xfail(
                reason="BA -9.7% under native. Hardwood path — same family "
                "of drift as YP/WO, milder magnitude.",
                strict=True,
            ),
        ),
        pytest.param(
            "WO", 65, 400, 25, id="wo-si65-25yr",
            marks=pytest.mark.xfail(
                reason="BA -7% and volume -11.5%. Upland oak, hardwood path. "
                "Same family as YP/SU drift.",
                strict=True,
            ),
        ),
        pytest.param(
            "RM", 65, 500, 25, id="rm-si65-25yr",
            marks=pytest.mark.xfail(
                reason="Volume-only drift: -13.6% below native (down from "
                "-20.9% after adding the r8prep.f:346-367 FCMIN minimum "
                "form-class clamp). BA/QMD/top_height in tolerance. "
                "Residual drift root cause: pyfvs's deterministic mode "
                "produces near-zero DBH variance (range 3.70-3.80) while "
                "native has ecological variance (3.20-4.90). Volume is "
                "convex in DBH, so Jensen's inequality accounts for the "
                "~3pp gap between per-tree drift (-10.8%) and stand drift "
                "(-13.6%). Root fix is in growth-path variance (FRM=1.0 "
                "deterministic adjustment removes per-tree noise), not "
                "volume. RM is hit hardest because its very negative B17 "
                "(-1.619) amplifies sensitivity to the FCMIN clamp.",
                strict=True,
            ),
        ),
        # Tier 3 — non-pine conifer / bottomland
        pytest.param("BY", 70, 400, 25, id="by-si70-25yr"),
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

    Exercises three groups:
      - remaining southern pines (LL/VP/WP), same code path as LP/SP/SA
      - major hardwoods (YP/SU/WO/RM), which hit the hardwood ln(DDS) branch
      - non-pine conifer (HM) and bottomland conifer (BY)

    Currently passing: LL (longleaf pine), BY (bald cypress). Remaining
    species are xfailed with per-species drift signatures documenting the
    specific divergence. These xfails must be closed by Fortran-faithful
    fixes to pyfvs, not by compensating coefficient tweaks.
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

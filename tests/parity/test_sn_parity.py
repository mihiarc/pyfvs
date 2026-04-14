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

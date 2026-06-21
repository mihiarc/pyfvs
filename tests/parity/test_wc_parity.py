"""Parity tests: pyfvs WC (West Cascades) variant vs native FVSwc.

WC is a 10-year-cycle variant covering 37 species along the western
Cascade slopes in WA and OR. WC shares most Fortran modules with PN
(Pacific Northwest Coast); species list overlaps 37 of 38 (WC lacks SS).

Exhaustive species audit lives at `scripts/wc_species_sweep.py`.
"""

from __future__ import annotations

import pytest

from tests.parity._helpers import (
    assert_metrics_close_mean,
    run_native,
    run_pyfvs_multi_seed,
)


WC_PARITY_N_SEEDS = 10


# Reconciled 2026-06-21 against the pinned native build (FVS 58a97520 /
# NVEL d6bbbf1, see docs/native_build_provenance.md): multi-seed mean PASS on
# all compared metrics (TPA +0.86%, BA +3.77%, QMD +1.43%, topH +0.90%; volume
# excluded). Prior xfail removed. See docs/parity_scorecard_2026-06-21.md.
def test_wc_gold_standard_df_si100_30yr(require_native_variant, parity_tolerance):
    """Gold-standard WC scenario: 500 DF at SI=100 grown 30 years.

    Douglas-fir (DF) is the WC default species. SI=100 is typical for
    West Cascade productive sites.
    """
    require_native_variant("WC")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="WC",
        species="DF",
        site_index=100,
        trees_per_acre=500,
        years=30,
        bare_ground=True,
        n_seeds=WC_PARITY_N_SEEDS,
    )
    native_result = run_native(
        variant="WC",
        species="DF",
        site_index=100,
        trees_per_acre=500,
        years=30,
    )
    assert_metrics_close_mean(
        pyfvs_result, native_result, parity_tolerance,
        skip_keys=("volume",),
    )


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        # WH/RC reconciled 2026-06-21 vs pinned native build (FVS 58a97520 /
        # NVEL d6bbbf1): multi-seed mean PASS on all compared metrics. xfail removed.
        pytest.param(
            "WH", 100, 500, 30, id="wh-si100-30yr",
        ),
        pytest.param(
            "RC", 100, 500, 30, id="rc-si100-30yr",
        ),
        pytest.param(
            "RA", 80, 500, 30, id="ra-si80-30yr",
            marks=pytest.mark.xfail(
                strict=False,
                reason="Baseline 2026-04-17: pre-fix WC expected drift.",
            ),
        ),
    ],
)
def test_wc_expanded_species_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    require_native_variant("WC")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="WC",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
        n_seeds=WC_PARITY_N_SEEDS,
    )
    native_result = run_native(
        variant="WC",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close_mean(
        pyfvs_result, native_result, parity_tolerance,
        skip_keys=("volume",),
    )

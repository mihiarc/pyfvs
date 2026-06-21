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




# WC gold: un-xfailed 2026-06-21 under the loose 5% band; the tightened regime
# re-exposes the divergence, so re-xfailed here. See docs/parity_tolerances.md.
@pytest.mark.xfail(
    strict=True,
    reason="Tightened tolerance regime 2026-06-21 (floor 0.5%; prior 5%/2% band masked this). TPA +0.86%, BA +3.77%, QMD +1.43%, topH +0.90% exceed band. WC DG/HG residual; volume skipped (real library gap).",
)
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
        skip_keys=("volume",),  # WC real volume-library gap: bfvol/logs MISSING (docs/wc_fidelity_map.md VOLUME); measured vol drift up to +24% (RC). Tracked there.
    )


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        # WH/RC: un-xfailed 2026-06-21 under the loose 5% band; the tightened
        # regime re-exposes the divergence, so re-xfailed here (volume skipped).
        pytest.param(
            "WH", 100, 500, 30, id="wh-si100-30yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Tightened tolerance regime 2026-06-21 (floor 0.5%; prior 5% band masked this). topH +0.99% exceeds band (others within). WC HG residual; volume skipped (real library gap).",
            ),
        ),
        pytest.param(
            "RC", 100, 500, 30, id="rc-si100-30yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Tightened tolerance regime 2026-06-21 (floor 0.5%; prior 5% band masked this). BA +0.81%, topH +0.66% exceed band. WC DG/HG residual; volume skipped.",
            ),
        ),
        pytest.param(
            "RA", 80, 500, 30, id="ra-si80-30yr",
            marks=pytest.mark.xfail(
                strict=True,
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
        skip_keys=("volume",),  # WC real volume-library gap: bfvol/logs MISSING (docs/wc_fidelity_map.md VOLUME); measured vol drift up to +24% (RC). Tracked there.
    )

"""Parity tests: pyfvs PN (Pacific Northwest Coast) variant vs native FVSpn.

PN is a 10-year-cycle variant covering 39 species in western WA, OR, and
northern CA coast. Uses ln(DDS) diameter growth with topographic effects
(slope, aspect, elevation) per Fortran pn/dgf.f.

PN and WC (West Cascades) share most Fortran modules. Parity work on PN
tends to translate directly to WC; species list overlap is 37 of 38.

Exhaustive 39-species audit lives at `scripts/pn_species_sweep.py`.
"""

from __future__ import annotations

import pytest

from tests.parity._helpers import (
    assert_metrics_close_mean,
    run_native,
    run_pyfvs_multi_seed,
)




@pytest.mark.xfail(
    reason="Baseline 2026-04-17: PN scaffold landing. Phase 1 tests establish "
    "which scenarios already pass pre-fix and which will need investigation. "
    "DF smoke (SI=120, 30yr) showed BA +9%, vol +12% — warn-band, likely "
    "Jensen-inequality stochastic lift or coefficient path needs audit.",
    strict=True,
)
def test_pn_gold_standard_df_si100_30yr(require_native_variant, parity_tolerance):
    """Gold-standard PN scenario: 500 DF at SI=100 grown 30 years.

    Douglas-fir (DF) is the PN default species and the dominant commercial
    species in the PNW. SI=100 is a typical productive coastal site.
    """
    require_native_variant("PN")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="PN",
        species="DF",
        site_index=100,
        trees_per_acre=500,
        years=30,
        bare_ground=True,
    )
    native_result = run_native(
        variant="PN",
        species="DF",
        site_index=100,
        trees_per_acre=500,
        years=30,
    )
    assert_metrics_close_mean(
        pyfvs_result, native_result, parity_tolerance,
        skip_keys=("volume",),  # PN real volume-library gap: bfvol/logs MISSING (docs/pn_fidelity_map.md VOLUME); measured vol drift up to +21% (RC). Tracked there.
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
                reason="Tightened tolerance regime 2026-06-21 (floor 0.5%; prior 5% band masked this). BA +1.87%, QMD +1.03%, topH +1.04% exceed band. PN DG/HG residual; volume skipped (real library gap).",
            ),
        ),
        pytest.param(
            "RC", 100, 500, 30, id="rc-si100-30yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Tightened tolerance regime 2026-06-21 (floor 0.5%; prior 5% band masked this). BA +2.61%, QMD +1.09% exceed band. PN DG/HG residual; volume skipped.",
            ),
        ),
        pytest.param(
            "RA", 80, 500, 30, id="ra-si80-30yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Baseline 2026-04-17: pre-fix PN expected drift.",
            ),
        ),
    ],
)
def test_pn_expanded_species_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    require_native_variant("PN")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="PN",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
    )
    native_result = run_native(
        variant="PN",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close_mean(
        pyfvs_result, native_result, parity_tolerance,
        skip_keys=("volume",),  # PN real volume-library gap: bfvol/logs MISSING (docs/pn_fidelity_map.md VOLUME); measured vol drift up to +21% (RC). Tracked there.
    )

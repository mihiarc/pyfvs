"""Parity tests: pyfvs WS (Western Sierra Nevada) variant vs native FVSws.

WS is a 10-year-cycle variant covering ~43 species in the western Sierra. pyfvs
WS is a **stub-scaffold**: all species point at one generic `cfg/ws/species/sp.yaml`
and the WS coefficient JSONs are generic rather than per-species, so the variant
runs (pipeline species work via the JSON coefficients) but stand-level growth
diverges sharply from native — WS over-predicts dramatically.

Each test runs pyfvs WS against the freshly built native FVSws (pinned build FVS
58a97520 / NVEL d6bbbf1; see docs/native_build_provenance.md) and compares the
standard stand metrics at standard parity tolerances — same multi-seed-mean
machinery and rigor as the SN/WC suites (WS diameter growth is stochastic). All
cases are currently xfail with the *measured* divergence recorded; they should be
revisited once WS gets real per-species metadata and coefficients (tracked as the
"WS stub YAMLs" open item in docs/parity_scorecard_2026-06-21.md).
"""

from __future__ import annotations

import pytest

from tests.parity._helpers import (
    assert_metrics_close_mean,
    run_native,
    run_pyfvs_multi_seed,
)




@pytest.mark.xfail(
    strict=True,
    reason=(
        "WS stub-YAML gap (measured 2026-06-21 vs pinned native FVSws, 10-seed "
        "mean, PP si90 30yr): BA +101.9%, QMD +55.2%, top_height +72.5%, "
        "volume +305.8%, TPA -16.1% — generic stub coefficients over-predict "
        "growth severely. Tracked: WS stub YAMLs."
    ),
)
def test_ws_gold_standard_pp_si90_30yr(require_native_variant, parity_tolerance):
    """Gold-standard WS scenario: 500 PP at SI=90 grown 30 years.

    Ponderosa pine (PP) is the WS default species.
    """
    require_native_variant("WS")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="WS",
        species="PP",
        site_index=90,
        trees_per_acre=500,
        years=30,
        bare_ground=True,
    )
    native_result = run_native(
        variant="WS",
        species="PP",
        site_index=90,
        trees_per_acre=500,
        years=30,
    )
    assert_metrics_close_mean(pyfvs_result, native_result, parity_tolerance)


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        pytest.param(
            "DF", 80, 500, 30, id="df-si80-30yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="WS stub-YAML gap (2026-06-21, 10-seed mean): BA +160.1%, "
                "QMD +90.9%, top_height +85.1%, volume +418.5%, TPA -28.6%.",
            ),
        ),
        pytest.param(
            "LP", 70, 500, 30, id="lp-si70-30yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="WS stub-YAML gap (2026-06-21, 10-seed mean): BA +254.7%, "
                "QMD +107.6%, top_height +74.9%, volume +493.0%, TPA -17.7%.",
            ),
        ),
    ],
)
def test_ws_expanded_species_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    """WS across species and size classes vs native FVSws.

    All currently xfail (WS stub-YAML over-prediction). Full metrics compared at
    standard tolerances — no metric is skipped or weakened.
    """
    require_native_variant("WS")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="WS",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
    )
    native_result = run_native(
        variant="WS",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close_mean(pyfvs_result, native_result, parity_tolerance)

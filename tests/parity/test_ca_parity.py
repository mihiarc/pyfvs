"""Parity tests: pyfvs CA (Inland California) variant vs native FVSca.

CA is a 10-year-cycle variant covering ~49 species in inland California and the
southern Cascades. pyfvs CA has a variant-specific diameter-growth model plus CA
bark/crown/H-D JSON coefficients, but **falls back to SN models** for mortality
(and several sub-models), and the large-tree height-growth / topographic dispatch
is not yet CA-faithful — so stand-level parity does not hold yet.

Each test runs pyfvs CA against the freshly built native FVSca (pinned build FVS
58a97520 / NVEL d6bbbf1; see docs/native_build_provenance.md) and compares the
standard stand metrics (TPA, BA, QMD, top height, volume) at the standard parity
tolerances — same multi-seed-mean machinery and rigor as the SN/WC suites (CA
diameter growth is stochastic). All cases are currently xfail with the *measured*
divergence recorded in each reason; when the CA sub-models are made
variant-faithful the relevant case should flip to XPASS and be un-xfailed
(tracked as the "CA SN-fallback" open item in docs/parity_scorecard_2026-06-21.md).
"""

from __future__ import annotations

import pytest

from tests.parity._helpers import (
    assert_metrics_close_mean,
    run_native,
    run_pyfvs_multi_seed,
)


CA_PARITY_N_SEEDS = 10


@pytest.mark.xfail(
    strict=False,
    reason=(
        "CA SN-fallback gap (measured 2026-06-21 vs pinned native FVSca, "
        "10-seed mean, PP si90 30yr): top_height +42.4%, QMD +20.1%, BA -13.0%, "
        "TPA -39.7%, volume +44.9% — CA height-growth / topographic dispatch and "
        "SN-fallback mortality are not yet CA-faithful. Tracked: CA SN-fallback."
    ),
)
def test_ca_gold_standard_pp_si90_30yr(require_native_variant, parity_tolerance):
    """Gold-standard CA scenario: 500 PP at SI=90 grown 30 years.

    Ponderosa pine (PP) is the CA default species; SI=90 is a typical
    productive inland-California site.
    """
    require_native_variant("CA")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="CA",
        species="PP",
        site_index=90,
        trees_per_acre=500,
        years=30,
        bare_ground=True,
        n_seeds=CA_PARITY_N_SEEDS,
    )
    native_result = run_native(
        variant="CA",
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
                strict=False,
                reason="CA SN-fallback gap (2026-06-21, 10-seed mean): BA +52.0%, "
                "QMD +36.6%, top_height +36.2%, volume +103.6%, TPA -18.5%.",
            ),
        ),
        pytest.param(
            "WF", 70, 500, 30, id="wf-si70-30yr",
            marks=pytest.mark.xfail(
                strict=False,
                reason="CA SN-fallback gap (2026-06-21, 10-seed mean): BA +34.7%, "
                "QMD +17.2%, top_height +34.6%, volume +89.6% (TPA -1.9% passes).",
            ),
        ),
        pytest.param(
            "JP", 70, 500, 30, id="jp-si70-30yr",
            marks=pytest.mark.xfail(
                strict=False,
                reason="CA SN-fallback gap (2026-06-21, 10-seed mean): top_height "
                "+43.8%, QMD +37.6%, TPA -41.6%, BA +10.4% (volume -5.1% passes).",
            ),
        ),
    ],
)
def test_ca_expanded_species_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    """CA across species and size classes vs native FVSca.

    All currently xfail (CA SN-fallback / non-faithful height-growth gap). Full
    metrics compared at standard tolerances — no metric is skipped or weakened.
    """
    require_native_variant("CA")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="CA",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
        n_seeds=CA_PARITY_N_SEEDS,
    )
    native_result = run_native(
        variant="CA",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close_mean(pyfvs_result, native_result, parity_tolerance)

"""Parity tests: pyfvs NE (Northeast) variant vs native FVSne.

NE is a 10-year-cycle variant covering 107 species across the Northeast US.
Unlike SN/LS/CS (ln(DDS) equation), NE uses a BA-growth form:
    BA_growth = B1 * SI * (1 - exp(-B2 * DBH))
(per `ne/dgf.f` and `ne_diameter_growth_coefficients.json`).

Establishment and blend zone handling match LS/CS per Fortran `ne/regent.f`
(LESTB FNT-5, XMIN=1.5 / XMAX=5.0 per ne/regent.f:98).

Exhaustive 107-species audit lives at `scripts/ne_species_sweep.py`.
"""

from __future__ import annotations

import pytest

from tests.parity._helpers import (
    assert_metrics_close_mean,
    run_native,
    run_pyfvs_multi_seed,
)


NE_PARITY_N_SEEDS = 10


def test_ne_gold_standard_rm_si60_30yr(require_native_variant, parity_tolerance):
    """Gold-standard NE scenario: 500 RM at SI=60 grown 30 years.

    Red maple (RM) is the NE default species and one of the most widespread
    hardwoods in the eastern US. SI=60 is a typical productive site.
    """
    require_native_variant("NE")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="NE",
        species="RM",
        site_index=60,
        trees_per_acre=500,
        years=30,
        bare_ground=True,
        n_seeds=NE_PARITY_N_SEEDS,
    )
    native_result = run_native(
        variant="NE",
        species="RM",
        site_index=60,
        trees_per_acre=500,
        years=30,
    )
    assert_metrics_close_mean(
        pyfvs_result, native_result, parity_tolerance,
        skip_keys=("volume",),  # NE volume library separate work item.
    )


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        # Closed 2026-04-21 by Fortran-faithful NE BALMOD (ne/balmod.f
        # EBAU(ICLS-2) shifted-BAL per-tree substitute for standard PBAL).
        pytest.param("RO", 60, 500, 30, id="ro-si60-30yr"),
        pytest.param("SM", 60, 500, 30, id="sm-si60-30yr"),
        pytest.param(
            "YB", 60, 500, 30, id="yb-si60-30yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Baseline 2026-04-16: pre-fix NE over-prediction.",
            ),
        ),
    ],
)
def test_ne_expanded_species_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    require_native_variant("NE")

    pyfvs_result = run_pyfvs_multi_seed(
        variant="NE",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
        n_seeds=NE_PARITY_N_SEEDS,
    )
    native_result = run_native(
        variant="NE",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close_mean(
        pyfvs_result, native_result, parity_tolerance,
        skip_keys=("volume",),
    )

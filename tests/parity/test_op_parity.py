"""Parity tests: pyfvs OP (ORGANON Pacific Northwest) variant vs native FVSop.

OP is a 5-year-cycle ORGANON-based variant covering ~18 modeled species. It is
the least-documented pyfvs variant: it carries OP diameter-growth and H-D JSON
coefficients but no OP-specific bark/crown/mortality configs (those fall back to
shared defaults). OP diameter growth uses a direct ln(DG) form and is **not
stochastic**, so these tests compare a single deterministic pyfvs run against the
freshly built native FVSop (pinned build FVS 58a97520 / NVEL d6bbbf1; see
docs/native_build_provenance.md) at standard parity tolerances.

Two findings drive the annotations (measured 2026-06-21):
  * Native FVSop produces a **degenerate stand for planted Douglas-fir** (the OP
    default): DF seedlings do not gain diameter (QMD frozen ~0.3–0.7"), TPA
    collapses toward 1, BA ~0 — across all site indices. This is a native-side
    ORGANON planted-DF quirk, not a pyfvs fidelity gap, and makes DF parity
    comparison meaningless until the native DF planting path is understood
    (BLOCKER, recorded in docs/parity_scorecard_2026-06-21.md).
  * For species native simulates normally (WH, RC, RA) TPA matches within
    tolerance (mortality parity holds) but pyfvs over-predicts diameter growth.

All cases are currently xfail with the measured divergence recorded; full metrics
are compared at standard tolerances (no metric skipped or weakened).
"""

from __future__ import annotations

import pytest

from tests.parity._helpers import (
    assert_metrics_close,
    run_native,
    run_pyfvs,
)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "OP native DEGENERATE-DF blocker (measured 2026-06-21 vs pinned native "
        "FVSop): native planted Douglas-fir does not grow (QMD frozen ~0.3-0.7\", "
        "TPA collapses toward 1, BA~0) across site indices, while pyfvs grows a "
        "normal DF stand — so the comparison is not meaningful. Native-side "
        "ORGANON planted-DF quirk, NOT a pyfvs model gap. Blocker tracked in "
        "docs/parity_scorecard_2026-06-21.md; do not 'fix' pyfvs to match a "
        "degenerate native stand."
    ),
)
@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        ("DF", 120, 300, 25),
    ],
    ids=["df-si120-25yr"],
)
def test_op_gold_standard_df(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    """Gold-standard OP scenario: 300 DF at SI=120 grown 25 years (DF is the OP default).

    XFAIL: native FVSop returns a degenerate DF stand (see module docstring /
    xfail reason). Deterministic (OP diameter growth is not stochastic).
    """
    require_native_variant("OP")

    pyfvs_result = run_pyfvs(
        variant="OP",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
        stochastic=False,
    )
    native_result = run_native(
        variant="OP",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close(pyfvs_result, native_result, parity_tolerance)


@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        pytest.param(
            "WH", 120, 300, 25, id="wh-si120-25yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="OP DG over-prediction (2026-06-21, deterministic): BA "
                "+44.4%, QMD +20.6%, top_height +18.0%, volume +33.6% "
                "(TPA -0.8% passes — mortality matches).",
            ),
        ),
        pytest.param(
            "RC", 120, 300, 25, id="rc-si120-25yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="OP DG over-prediction (2026-06-21, deterministic): BA "
                "+37.7%, QMD +17.6%, top_height +38.7%, volume +86.5% "
                "(TPA -0.4% passes — mortality matches).",
            ),
        ),
        pytest.param(
            "RA", 120, 300, 25, id="ra-si120-25yr",
            marks=pytest.mark.xfail(
                strict=True,
                reason="OP DG over-prediction (2026-06-21, deterministic): BA "
                "+201.0%, QMD +74.4%, volume +110.1% (TPA -1.0% and top_height "
                "+2.4% pass — mortality and height match; diameter diverges).",
            ),
        ),
    ],
)
def test_op_expanded_species_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    """OP across species and size classes vs native FVSop (species native simulates).

    All currently xfail (OP diameter-growth over-prediction). TPA matches for
    these species, so the native baseline is valid. Full metrics compared at
    standard tolerances — no metric is skipped or weakened.
    """
    require_native_variant("OP")

    pyfvs_result = run_pyfvs(
        variant="OP",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
        stochastic=False,
    )
    native_result = run_native(
        variant="OP",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close(pyfvs_result, native_result, parity_tolerance)

"""Parity tests: pyfvs EC (East Cascades) variant vs native FVSec.

EC was the first variant translated as part of the systematic backfill of
missing variants. This is a Phase-1 port: only the diameter growth model
(ec/dgf.f) has been fully translated. Height growth, mortality, bark
ratio, crown ratio, and small-tree growth currently fall back to PN-family
defaults. Stand-level parity will not pass until those components are
also ported.

The tests below are structured so that:

  - Unit tests on ECDiameterGrowthModel run anywhere (no FVSec needed).
  - Stand-level parity against native FVSec is xfailed with a
    detailed reason so the known divergence is visible but non-blocking.

When the remaining EC components land, flipping the xfail decorators to
strict=True should turn these tests green (or surface any remaining gap).
"""

from __future__ import annotations

import math

import pytest

from tests.parity._helpers import (
    assert_metrics_close,
    run_native,
    run_pyfvs,
)


# ---------------------------------------------------------------------------
# Unit tests (no native FVS needed)
# ---------------------------------------------------------------------------

def test_ec_registered_in_variant_registry():
    """EC must be registered with the correct metadata.

    Guards against a regression where future edits to variant_registry
    silently drop or mis-wire EC.
    """
    from pyfvs.variant_registry import get_variant_config

    config = get_variant_config("EC")
    assert config.code == "EC"
    assert config.name == "East Cascades"
    assert config.cycle_length == 10
    assert config.default_species == "DF"
    assert config.growth_category == "topographic"
    assert config.dg_module == "ec_diameter_growth"
    assert config.dg_factory == "create_ec_diameter_growth_model"


def test_ec_coefficient_file_shape():
    """EC coefficient file must have all 32 species with required keys.

    This catches accidental coefficient-file corruption (e.g., re-running
    the extractor with a broken parser).
    """
    import json
    from pathlib import Path

    import pyfvs

    cfg_path = Path(pyfvs.__file__).parent / "cfg" / "ec" / "ec_diameter_growth_coefficients.json"
    data = json.loads(cfg_path.read_text())

    assert data["_metadata"]["variant"] == "EC"
    assert data["_metadata"]["num_species"] == 32
    assert data["_metadata"]["native_cycle_years"] == 10

    species = data["species_coefficients"]
    assert len(species) == 32

    # Spot-check DF (the default species)
    df = species["DF"]
    assert df["fortran_index"] == 3
    assert df["equation_class"] == "ec_native"
    # DGLD for DF is 0.855516 per Fortran ec/dgf.f:142
    assert df["DGLD"] == pytest.approx(0.855516)
    # DGCRSQ for DF is -0.44082 per Fortran ec/dgf.f:160
    assert df["DGCRSQ"] == pytest.approx(-0.44082)

    # Red alder must be in its own class
    ra = species["RA"]
    assert ra["equation_class"] == "red_alder"

    # All 32 species must have SIGMAR (variance parameter) for stochastic mode
    variance = data["variance_parameters"]
    assert len(variance) == 32
    for sp, sigma in variance.items():
        assert sigma > 0, f"Species {sp} has non-positive sigma {sigma}"


@pytest.mark.parametrize(
    "species,expected_delta_range",
    [
        # Species, (min_dbh_delta_10yr, max_dbh_delta_10yr) — generous
        # ranges derived from PNW inventory yield tables at comparable
        # sites. These are guard rails, not precision targets.
        ("DF", (0.6, 2.0)),
        ("WH", (0.6, 2.5)),   # Western hemlock, WC-derived
        ("PP", (0.4, 2.0)),   # Ponderosa pine
        ("AF", (0.3, 2.0)),   # Subalpine fir (+0.3835 DGCON tweak)
        ("WP", (0.5, 2.5)),   # White pine (+0.49649*RELHT tweak)
    ],
)
def test_ec_reasonable_growth_range(species, expected_delta_range):
    """EC DDS values must produce biologically plausible 10-year DBH changes.

    Starting tree: DBH=10", CR=0.5, SI=80, BA=120, BAL=60. This is a
    mid-rotation Douglas-fir country scenario. A healthy 10" tree at this
    site should gain between 0.3" and 2.5" DBH over 10 years depending on
    species.
    """
    from pyfvs.ec_diameter_growth import create_ec_diameter_growth_model

    model = create_ec_diameter_growth_model(species)
    dds = model.calculate_dds(
        dbh=10.0, crown_ratio=0.5, site_index=80.0,
        ba=120.0, bal=60.0, pccf=100.0, relht=1.0,
        elevation=20.0, slope=0.1, aspect=0.0, location_class=0,
        time_step=10.0,
    )
    dbh_new = math.sqrt(10.0 ** 2 + dds)
    dbh_delta = dbh_new - 10.0

    lo, hi = expected_delta_range
    assert lo <= dbh_delta <= hi, (
        f"{species} 10yr DBH delta {dbh_delta:.3f}\" outside plausible "
        f"range [{lo}, {hi}]. DDS={dds:.3f}"
    )


def test_ec_wp_relht_bonus_is_applied():
    """WP (western white pine) adds 0.49649*RELHT to ln(DDS) per ec/dgf.f:525.

    This tests the species-specific tweak — a tree with high RELHT should
    grow faster than the same tree with lower RELHT, all else equal.
    """
    from pyfvs.ec_diameter_growth import create_ec_diameter_growth_model

    model = create_ec_diameter_growth_model("WP")
    kwargs = dict(
        dbh=10.0, crown_ratio=0.5, site_index=80.0,
        ba=120.0, bal=60.0, pccf=100.0,
        elevation=20.0, slope=0.1, aspect=0.0, location_class=0,
        time_step=10.0,
    )
    dds_high = model.calculate_dds(relht=1.5, **kwargs)
    dds_low = model.calculate_dds(relht=0.5, **kwargs)
    assert dds_high > dds_low, (
        f"WP RELHT bonus not firing: dds(RELHT=1.5)={dds_high:.4f} "
        f"should exceed dds(RELHT=0.5)={dds_low:.4f}"
    )


def test_ec_red_alder_uses_special_equation():
    """RA must use the red-alder special equation, not the standard form.

    The standard form would give RA DDS=0 since its DGLD/DGCR/DGSITE
    coefficients are all zero in the coefficient file.
    """
    from pyfvs.ec_diameter_growth import create_ec_diameter_growth_model

    model = create_ec_diameter_growth_model("RA")
    dds = model.calculate_dds(
        dbh=10.0, crown_ratio=0.5, site_index=80.0,
        ba=120.0, bal=60.0, pccf=100.0, relht=1.0,
        elevation=20.0, slope=0.1, aspect=0.0, location_class=0,
        time_step=10.0,
    )
    # Red alder should grow noticeably — if the special equation isn't
    # running, DDS would round to ~0 or collapse to the stochastic floor.
    assert dds > 1.0, (
        f"RA DDS={dds:.4f} is too small — red-alder special equation "
        f"may not be dispatching correctly"
    )


def test_ec_pyfvs_stand_grows_without_crashing():
    """pyfvs Stand with variant='EC' must grow a full cycle without errors.

    Sanity check that the Stand -> Tree -> ec_diameter_growth dispatch
    path is wired up. Doesn't assert correctness (that's what parity
    tests are for), just that nothing raises.
    """
    from pyfvs import Stand
    from pyfvs.tree import Tree

    trees = [
        Tree(dbh=0.1, height=1.0, age=1, species="DF", variant="EC")
        for _ in range(50)
    ]
    stand = Stand(
        trees,
        site_index=80,
        species="DF",
        variant="EC",
        stochastic=False,
    )
    stand.age = 1
    stand.grow(years=20)
    metrics = stand.get_metrics()

    assert metrics["tpa"] > 0
    assert metrics["qmd"] > 0
    assert metrics["basal_area"] >= 0


# ---------------------------------------------------------------------------
# Native parity tests (require FVSec shared library)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason=(
        "EC Phase-1 port: only ec_diameter_growth is variant-specific. "
        "Height growth, mortality, bark ratio, crown ratio, and small-tree "
        "growth currently fall back to PN-family SN+LP defaults. Stand-"
        "level parity cannot pass until ec/htgf.f, ec/morts.f, ec/bratio.f, "
        "ec/crown.f, and ec/smhtgf.f are also ported. When all EC "
        "components land, flip this to strict=True."
    ),
)
@pytest.mark.parametrize(
    "species,site_index,trees_per_acre,years",
    [
        ("DF", 80, 400, 25),
        ("PP", 70, 350, 25),
        ("LP", 70, 500, 25),
    ],
    ids=["df-si80-25yr", "pp-si70-25yr", "lp-si70-25yr"],
)
def test_ec_planted_parity(
    require_native_variant,
    parity_tolerance,
    species,
    site_index,
    trees_per_acre,
    years,
):
    """pyfvs EC and native FVSec planted-stand metrics — XFAIL.

    See xfail reason. Phase-1 EC port only has the diameter growth
    equation; other model components are PN fallbacks.
    """
    require_native_variant("EC")

    pyfvs_result = run_pyfvs(
        variant="EC",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
        bare_ground=True,
    )
    native_result = run_native(
        variant="EC",
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        years=years,
    )
    assert_metrics_close(pyfvs_result, native_result, parity_tolerance)

"""Smoke tests for the East Cascades (EC) variant port.

Unblocks the forest-rents pipeline's Mountain and pacific_northwest regions
for Western Larch (WL) and verifies the Phase-2 EC port (bark ratio, crown
ratio, HD, HHTMAX) produces plausible growth metrics for the pipeline's
primary species set.
"""
import pytest

from pyfvs import Stand, set_default_variant
from pyfvs.config_loader import get_default_variant
from pyfvs.bark_ratio import ECBarkRatioModel, create_bark_ratio_model
from pyfvs.crown_ratio import ECCrownRatioModel, create_crown_ratio_model
from pyfvs.variant_registry import get_variant_config


@pytest.fixture(autouse=True)
def _restore_default_variant():
    """Reset the module-global default variant after each test so EC
    defaults don't leak into the rest of the suite."""
    saved = get_default_variant()
    yield
    set_default_variant(saved)


PIPELINE_METRIC_KEYS = {
    'volume', 'basal_area', 'qmd', 'merchantable_volume', 'board_feet',
    'tpa', 'mean_height', 'top_height',
}

# Species the forest-rents pipeline cares about under EC.
PIPELINE_SPECIES = ['WL', 'DF', 'PP', 'GF', 'ES', 'AF']


class TestECBarkRatio:
    """Fortran-faithful EC bark ratio coefficients from ec/bratio.f."""

    def test_wl_constant_ratio(self):
        m = ECBarkRatioModel('WL')
        assert m._eq_type == 3
        assert m._a == pytest.approx(0.851, abs=1e-4)

    def test_wo_power_form(self):
        m = ECBarkRatioModel('WO')
        assert m._eq_type == 1
        assert m._a == pytest.approx(0.8558, abs=1e-4)
        assert m._b == pytest.approx(1.0213, abs=1e-4)

    def test_ra_linear_form(self):
        m = ECBarkRatioModel('RA')
        assert m._eq_type == 2
        assert m._a == pytest.approx(0.075256, abs=1e-5)
        assert m._b == pytest.approx(0.94967, abs=1e-5)

    def test_factory_dispatch_returns_ec_model(self):
        m = create_bark_ratio_model('WL', variant='EC')
        assert isinstance(m, ECBarkRatioModel)

    def test_bark_ratio_within_bounds(self):
        m = ECBarkRatioModel('WL')
        for dob in [1.0, 5.0, 15.0, 30.0]:
            ratio = m.calculate_bark_ratio(dob)
            assert 0.50 <= ratio <= 1.0, f"DBH={dob}: ratio={ratio}"


class TestECCrownRatio:
    """Fortran-faithful EC crown ratio (Weibull) from ec/crown.f."""

    def test_wl_coefficients(self):
        m = ECCrownRatioModel('WL')
        assert m._weibb0 == pytest.approx(0.00603, abs=1e-5)
        assert m._weibb1 == pytest.approx(1.12276, abs=1e-5)
        assert m._weibc0 == pytest.approx(2.73400, abs=1e-4)
        assert m._mean_cr_c0 == pytest.approx(4.98675, abs=1e-4)

    def test_factory_dispatch_returns_ec_model(self):
        m = create_crown_ratio_model('WL', variant='EC')
        assert isinstance(m, ECCrownRatioModel)

    def test_cr_within_bounds(self):
        m = ECCrownRatioModel('WL')
        cr = m.predict_individual_crown_ratio(
            tree_rank=0.5, relsdi=5.0, dbh=8.0, ba=120.0,
        )
        assert 0.10 <= cr <= 0.95


class TestECVariantConfig:
    """Variant registry wiring."""

    def test_ec_registered(self):
        cfg = get_variant_config('EC')
        assert cfg.code == 'EC'
        assert cfg.growth_category == 'topographic'

    def test_ec_uses_ec_models(self):
        cfg = get_variant_config('EC')
        assert cfg.bark_ratio_class is ECBarkRatioModel
        assert cfg.crown_ratio_class is ECCrownRatioModel

    def test_ec_hhtmax_populated(self):
        cfg = get_variant_config('EC')
        assert cfg.hhtmax.get('WL') == pytest.approx(27.0)
        assert cfg.hhtmax.get('AF') == pytest.approx(18.0)


@pytest.mark.parametrize("species", PIPELINE_SPECIES)
def test_ec_pipeline_species_grows_without_fallback(species):
    """Each pipeline species runs a 25-year EC simulation and returns all 8 metrics."""
    set_default_variant('EC')
    stand = Stand.initialize_planted(
        trees_per_acre=400, site_index=70, species=species,
        variant='EC', random_seed=42,
    )
    stand.grow(years=25)
    m = stand.get_metrics()

    assert PIPELINE_METRIC_KEYS.issubset(m.keys())
    for key in PIPELINE_METRIC_KEYS:
        assert m[key] >= 0, f"{species}: {key} = {m[key]}"
    # Sanity ranges for a 25-yr rotation on SI=70
    assert m['tpa'] > 0
    assert 50 < m['basal_area'] < 350, f"{species}: BA={m['basal_area']}"
    assert 30 < m['top_height'] < 120, f"{species}: top_height={m['top_height']}"
    assert m['qmd'] > 3.0, f"{species}: QMD={m['qmd']}"


def test_ec_wl_reproducible():
    """Same seed produces identical metrics."""
    set_default_variant('EC')

    def run():
        s = Stand.initialize_planted(
            trees_per_acre=400, site_index=70, species='WL',
            variant='EC', random_seed=99,
        )
        s.grow(years=20)
        return s.get_metrics()

    a = run()
    b = run()
    for k in PIPELINE_METRIC_KEYS:
        assert a[k] == b[k], f"{k}: {a[k]} vs {b[k]}"


def test_ec_natural_regen_works():
    """Pipeline's natural-regen path works under EC for hardwoods."""
    set_default_variant('EC')
    stand = Stand.initialize_natural(
        trees_per_acre=400, site_index=65, species='AS',
        variant='EC', random_seed=42,
    )
    assert stand._establishment_pending is True
    stand.grow(years=30)
    m = stand.get_metrics()
    assert PIPELINE_METRIC_KEYS.issubset(m.keys())
    assert m['tpa'] > 0
    assert m['basal_area'] > 0

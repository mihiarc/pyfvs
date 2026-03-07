"""Tests for the CA (Inland California) variant implementation.

Tests cover:
- Bark ratio (3 equation types: power, linear, constant)
- Crown ratio (Weibull with 17 species groups)
- SDI maximums (CA-specific per species from sitset.f)
- HHTMAX establishment height caps (all 20 ft)
- Diameter growth (13 equation sets, GS/RW special equation, stochastic)
- Stochastic diameter growth
- Mortality (SN model with CA SDI maximums and VARADJ)
- Integration (full stand simulation with variant='CA')
"""
import math
import random
import pytest

from pyfvs import Stand
from pyfvs.bark_ratio import (
    CABarkRatioModel,
    create_bark_ratio_model,
)
from pyfvs.crown_ratio import (
    CACrownRatioModel,
    create_crown_ratio_model,
)
from pyfvs.stand_metrics import StandMetricsCalculator
from pyfvs.ca_diameter_growth import (
    CADiameterGrowthModel,
    create_ca_diameter_growth_model,
)
from pyfvs.variant_registry import get_variant_config
from pyfvs.establishment import get_hhtmax


# ===========================================================================
# CA Bark Ratio Tests
# ===========================================================================

class TestCABarkRatio:
    """Tests for CABarkRatioModel with 3 equation types."""

    def test_factory_creates_ca_model(self):
        """Factory returns CABarkRatioModel for variant='CA'."""
        model = create_bark_ratio_model('PP', variant='CA')
        assert isinstance(model, CABarkRatioModel)

    def test_power_equation_df(self):
        """DF (group 1) uses power equation: DIB = a * DOB^b."""
        model = CABarkRatioModel('DF')
        coeffs = model.get_species_coefficients()
        assert coeffs['type'] == 1
        ratio = model.calculate_bark_ratio(10.0)
        assert 0.80 <= ratio <= 0.99

    def test_linear_equation_wf(self):
        """WF (group 2) uses linear equation: DIB = a + b * DOB."""
        model = CABarkRatioModel('WF')
        coeffs = model.get_species_coefficients()
        assert coeffs['type'] == 2
        ratio = model.calculate_bark_ratio(10.0)
        assert 0.80 <= ratio <= 0.99

    def test_constant_equation_br(self):
        """BR (group 9) uses constant: BRATIO = 0.9."""
        model = CABarkRatioModel('BR')
        coeffs = model.get_species_coefficients()
        assert coeffs['type'] == 3
        ratio_small = model.calculate_bark_ratio(5.0)
        ratio_large = model.calculate_bark_ratio(20.0)
        assert abs(ratio_small - ratio_large) < 0.001

    def test_dib_from_dob(self):
        """DIB < DOB for all species."""
        for sp in ['PP', 'DF', 'WF', 'IC', 'BR', 'LO', 'TO']:
            model = CABarkRatioModel(sp)
            dob = 12.0
            dib = model.calculate_dib_from_dob(dob)
            assert 0 < dib < dob, f"{sp}: DIB={dib} not in (0, {dob})"

    def test_bark_ratio_bounded(self):
        """All bark ratios bounded [0.80, 0.99]."""
        for sp in ['PP', 'DF', 'WF', 'IC', 'BR', 'LO', 'TO', 'MA', 'GC']:
            model = CABarkRatioModel(sp)
            for dob in [1.0, 5.0, 10.0, 30.0]:
                ratio = model.calculate_bark_ratio(dob)
                assert 0.80 <= ratio <= 0.99, f"{sp} at DOB={dob}: ratio={ratio}"

    def test_roundtrip_dib_dob(self):
        """DOB -> DIB -> DOB roundtrip within tolerance."""
        model = CABarkRatioModel('PP')
        dob = 12.0
        dib = model.calculate_dib_from_dob(dob)
        dob_back = model.calculate_dob_from_dib(dib)
        assert abs(dob - dob_back) < 0.1


# ===========================================================================
# CA Crown Ratio Tests
# ===========================================================================

class TestCACrownRatio:
    """Tests for CACrownRatioModel with 17 species groups."""

    def test_factory_creates_ca_model(self):
        """Factory returns CACrownRatioModel for variant='CA'."""
        model = create_crown_ratio_model('PP', variant='CA')
        assert isinstance(model, CACrownRatioModel)

    def test_acr_decreases_with_density(self):
        """Average crown ratio decreases as stand density increases."""
        model = CACrownRatioModel('PP')
        acr_low = model.calculate_average_crown_ratio(2.0)
        acr_high = model.calculate_average_crown_ratio(8.0)
        assert acr_low > acr_high, f"ACR should decrease: {acr_low} <= {acr_high}"

    def test_acr_bounded(self):
        """ACR bounded [0.05, 0.95]."""
        model = CACrownRatioModel('DF')
        for relsdi in [1.0, 5.0, 10.0, 12.0]:
            acr = model.calculate_average_crown_ratio(relsdi)
            assert 0.05 <= acr <= 0.95, f"ACR={acr} at RELSDI={relsdi}"

    def test_individual_cr_bounded(self):
        """Individual tree CR bounded [0.10, 0.95]."""
        model = CACrownRatioModel('PP')
        for rank in [0.1, 0.5, 0.9]:
            cr = model.predict_individual_crown_ratio(rank, 5.0)
            assert 0.10 <= cr <= 0.95, f"CR={cr} at rank={rank}"

    def test_bm_has_weiba(self):
        """BM (Big-leaf Maple, group 14) has WEIBA=1.0."""
        model = CACrownRatioModel('BM')
        assert model._weiba == 1.0

    def test_dominant_vs_suppressed(self):
        """Dominant trees (high rank) should have higher CR than suppressed (low rank)."""
        model = CACrownRatioModel('DF')
        cr_suppressed = model.predict_individual_crown_ratio(0.1, 5.0)
        cr_dominant = model.predict_individual_crown_ratio(0.9, 5.0)
        assert cr_dominant > cr_suppressed

    def test_multiple_species(self):
        """Multiple common CA species produce reasonable crown ratios."""
        for sp in ['PP', 'DF', 'WF', 'IC', 'JP', 'RF', 'LP', 'WO']:
            model = CACrownRatioModel(sp)
            cr = model.predict_individual_crown_ratio(0.5, 5.0)
            assert 0.20 <= cr <= 0.80, f"{sp}: CR={cr} outside reasonable range"

    def test_group_count(self):
        """CA has 17 Weibull groups."""
        assert len(CACrownRatioModel._FALLBACK_WEIBULL) == 17
        assert len(CACrownRatioModel._FALLBACK_MEAN_CR) == 17


# ===========================================================================
# CA SDI Maximum Tests
# ===========================================================================

class TestCASDIMaximums:
    """Tests for CA-specific SDI maximum values."""

    def test_sdi_table_has_49_species(self):
        """CA SDI maximums table has all 49 species."""
        assert len(StandMetricsCalculator.CA_SDI_MAXIMUMS) == 49

    def test_key_species_values(self):
        """Verify key species SDI maximums from sitset.f R5SDI."""
        sdi = StandMetricsCalculator.CA_SDI_MAXIMUMS
        assert sdi['PP'] == 430
        assert sdi['DF'] == 600
        assert sdi['RF'] == 800  # Highest conifer SDI
        assert sdi['WJ'] == 330  # Lowest SDI
        assert sdi['WF'] == 760
        assert sdi['GS'] == 570

    def test_all_positive(self):
        """All SDI maximums are positive."""
        for sp, val in StandMetricsCalculator.CA_SDI_MAXIMUMS.items():
            assert val > 0, f"{sp} SDI max {val} <= 0"

    def test_variant_config_has_sdi(self):
        """Variant config includes SDI maximums."""
        config = get_variant_config('CA')
        assert len(config.sdi_maximums) == 49
        assert config.sdi_maximums['PP'] == 430


# ===========================================================================
# CA HHTMAX Tests
# ===========================================================================

class TestCAHHTMAX:
    """Tests for CA establishment height caps."""

    def test_hhtmax_default_20(self):
        """CA HHTMAX is 20 ft for all species."""
        config = get_variant_config('CA')
        assert config.hhtmax_default == 20.0

    def test_all_species_get_20(self):
        """All CA species get HHTMAX of 20."""
        for sp in ['PP', 'DF', 'WF', 'IC', 'JP', 'LP', 'WO', 'TO']:
            assert get_hhtmax(sp, 'CA') == 20.0

    def test_empty_override_dict(self):
        """CA has empty HHTMAX dict (all use default)."""
        config = get_variant_config('CA')
        assert len(config.hhtmax) == 0


# ===========================================================================
# CA Diameter Growth Tests
# ===========================================================================

class TestCADiameterGrowth:
    """Tests for CADiameterGrowthModel with 13 equation sets."""

    def test_factory_creates_model(self):
        """Factory creates cached model instances."""
        m1 = create_ca_diameter_growth_model('PP')
        m2 = create_ca_diameter_growth_model('PP')
        assert m1 is m2  # Cached

    def test_positive_growth(self):
        """Standard conditions produce positive diameter growth."""
        model = create_ca_diameter_growth_model('PP')
        dg = model.calculate_diameter_growth(
            dbh=8.0, crown_ratio=0.5, site_index=90,
            ba=150, bal=50, elevation=3000
        )
        assert dg > 0, f"PP growth {dg} should be positive"

    def test_growth_increases_with_site_index(self):
        """Higher site index produces more growth."""
        model = create_ca_diameter_growth_model('PP')
        dg_low = model.calculate_diameter_growth(
            dbh=8.0, crown_ratio=0.5, site_index=60, ba=150, bal=50
        )
        dg_high = model.calculate_diameter_growth(
            dbh=8.0, crown_ratio=0.5, site_index=120, ba=150, bal=50
        )
        assert dg_high > dg_low, f"SI 120 growth {dg_high} <= SI 60 {dg_low}"

    def test_growth_decreases_with_competition(self):
        """More competition (higher BAL) reduces growth."""
        model = create_ca_diameter_growth_model('DF')
        dg_low_comp = model.calculate_diameter_growth(
            dbh=8.0, crown_ratio=0.5, site_index=80, ba=100, bal=10
        )
        dg_high_comp = model.calculate_diameter_growth(
            dbh=8.0, crown_ratio=0.5, site_index=80, ba=200, bal=150
        )
        assert dg_low_comp > dg_high_comp

    def test_gs_rw_special_equation(self):
        """GS uses special site-index-only equation (equation 12)."""
        model = create_ca_diameter_growth_model('GS')
        dg = model.calculate_diameter_growth(
            dbh=20.0, crown_ratio=0.5, site_index=100, ba=150, bal=50
        )
        assert dg > 0

    def test_time_step_scaling(self):
        """Growth scales linearly with time step."""
        model = create_ca_diameter_growth_model('PP')
        dds_10 = model.calculate_dds(
            dbh=8.0, crown_ratio=0.5, site_index=90, ba=150, bal=50
        )
        dds_5 = model.calculate_dds(
            dbh=8.0, crown_ratio=0.5, site_index=90, ba=150, bal=50,
            time_step=5.0
        )
        assert abs(dds_5 - dds_10 / 2.0) < 0.01

    def test_multiple_species_positive_growth(self):
        """All common species produce positive growth."""
        for sp in ['PP', 'DF', 'WF', 'IC', 'JP', 'LP', 'WO', 'TO']:
            model = create_ca_diameter_growth_model(sp)
            dg = model.calculate_diameter_growth(
                dbh=8.0, crown_ratio=0.5, site_index=80,
                ba=120, bal=40, elevation=3000
            )
            assert dg > 0, f"{sp}: growth {dg} should be positive"

    def test_sigma_values_exist(self):
        """All common CA species have SIGMAR values."""
        for sp in ['PP', 'DF', 'WF', 'IC', 'JP', 'LP', 'WO', 'TO', 'MA']:
            assert sp in CADiameterGrowthModel._SIGMA


# ===========================================================================
# CA Stochastic Growth Tests
# ===========================================================================

class TestCAStochasticGrowth:
    """Tests for stochastic diameter growth in CA variant."""

    def test_deterministic_baskerville(self):
        """Deterministic mode applies Baskerville correction (rng=None)."""
        model = create_ca_diameter_growth_model('PP')
        dds_det = model.calculate_dds(
            dbh=8.0, crown_ratio=0.5, site_index=90, ba=150, bal=50
        )
        # Should be positive (Baskerville adds to ln(DDS))
        assert dds_det > 0

    def test_stochastic_varies(self):
        """Stochastic mode produces different results with different seeds."""
        model = create_ca_diameter_growth_model('PP')
        rng1 = random.Random(42)
        rng2 = random.Random(99)
        dds1 = model.calculate_dds(
            dbh=8.0, crown_ratio=0.5, site_index=90, ba=150, bal=50,
            rng=rng1
        )
        dds2 = model.calculate_dds(
            dbh=8.0, crown_ratio=0.5, site_index=90, ba=150, bal=50,
            rng=rng2
        )
        assert dds1 != dds2

    def test_stochastic_mean_near_deterministic(self):
        """Average of many stochastic runs near deterministic value."""
        model = create_ca_diameter_growth_model('PP')
        dds_det = model.calculate_dds(
            dbh=8.0, crown_ratio=0.5, site_index=90, ba=150, bal=50
        )
        stochastic_values = []
        for seed in range(100):
            rng = random.Random(seed)
            dds = model.calculate_dds(
                dbh=8.0, crown_ratio=0.5, site_index=90, ba=150, bal=50,
                rng=rng
            )
            stochastic_values.append(dds)
        stochastic_mean = sum(stochastic_values) / len(stochastic_values)
        ratio = stochastic_mean / dds_det
        assert 0.7 < ratio < 1.3, f"Stochastic mean ratio {ratio} too far from 1.0"

    def test_stochastic_all_positive(self):
        """All stochastic DDS values should be positive."""
        model = create_ca_diameter_growth_model('PP')
        for seed in range(50):
            rng = random.Random(seed)
            dds = model.calculate_dds(
                dbh=8.0, crown_ratio=0.5, site_index=90, ba=150, bal=50,
                rng=rng
            )
            assert dds > 0, f"Negative DDS at seed {seed}"


# ===========================================================================
# CA Variant Configuration Tests
# ===========================================================================

class TestCAVariantConfig:
    """Tests for CA entry in variant registry."""

    def test_variant_registered(self):
        """CA variant exists in registry."""
        config = get_variant_config('CA')
        assert config.code == 'CA'

    def test_cycle_length(self):
        """CA has 10-year cycle."""
        config = get_variant_config('CA')
        assert config.cycle_length == 10

    def test_growth_category(self):
        """CA uses topographic growth category."""
        config = get_variant_config('CA')
        assert config.growth_category == 'topographic'

    def test_default_species(self):
        """CA default species is PP."""
        config = get_variant_config('CA')
        assert config.default_species == 'PP'

    def test_bark_ratio_class(self):
        """CA uses CABarkRatioModel."""
        config = get_variant_config('CA')
        assert config.bark_ratio_class is CABarkRatioModel

    def test_crown_ratio_class(self):
        """CA uses CACrownRatioModel."""
        config = get_variant_config('CA')
        assert config.crown_ratio_class is CACrownRatioModel

    def test_default_elevation(self):
        """CA default elevation is 30 (hundreds of feet = 3000 ft)."""
        config = get_variant_config('CA')
        assert config.default_elevation == 30.0


# ===========================================================================
# CA Integration Tests
# ===========================================================================

class TestCAIntegration:
    """Integration tests for CA variant stand simulation."""

    def test_stand_initializes(self):
        """Can initialize a planted stand with variant='CA'."""
        stand = Stand.initialize_planted(300, 80, 'PP', variant='CA')
        assert stand is not None
        assert len(stand.trees) > 0

    def test_stand_grows(self):
        """Stand grows for multiple cycles without errors."""
        stand = Stand.initialize_planted(300, 80, 'PP', variant='CA', stochastic=False)
        stand.grow(10)
        metrics = stand.get_metrics()
        assert metrics['basal_area'] > 0
        assert metrics['qmd'] > 0

    def test_growth_produces_reasonable_metrics(self):
        """50-year growth produces metrics in expected ranges."""
        stand = Stand.initialize_planted(300, 80, 'PP', variant='CA', stochastic=False)
        stand.grow(50)
        metrics = stand.get_metrics()
        # After 50 years: expect some growth
        assert metrics['qmd'] > 3.0, f"QMD {metrics['qmd']} too small after 50 years"
        assert metrics['basal_area'] > 10, f"BA {metrics['basal_area']} too low"
        assert metrics['top_height'] > 30, f"TopHt {metrics['top_height']} too low"

    def test_df_species(self):
        """DF (Douglas-fir) grows in CA variant."""
        stand = Stand.initialize_planted(300, 80, 'DF', variant='CA', stochastic=False)
        stand.grow(20)
        metrics = stand.get_metrics()
        assert metrics['basal_area'] > 0

    def test_wf_species(self):
        """WF (White Fir) grows in CA variant."""
        stand = Stand.initialize_planted(300, 80, 'WF', variant='CA', stochastic=False)
        stand.grow(20)
        metrics = stand.get_metrics()
        assert metrics['basal_area'] > 0

    def test_stochastic_mode(self):
        """Stochastic mode with random seed runs without errors."""
        stand = Stand.initialize_planted(
            300, 80, 'PP', variant='CA', stochastic=True, random_seed=42
        )
        stand.grow(20)
        metrics = stand.get_metrics()
        assert metrics['basal_area'] > 0

    def test_stochastic_different_seeds(self):
        """Different seeds produce different growth."""
        metrics_list = []
        for seed in [42, 99]:
            stand = Stand.initialize_planted(
                300, 80, 'PP', variant='CA', stochastic=True, random_seed=seed
            )
            stand.grow(30)
            metrics_list.append(stand.get_metrics())
        # Different seeds should produce slightly different results
        assert metrics_list[0]['basal_area'] != metrics_list[1]['basal_area']

    @pytest.mark.slow
    def test_full_rotation(self):
        """Full 100-year rotation completes without errors."""
        stand = Stand.initialize_planted(300, 80, 'PP', variant='CA', stochastic=False)
        stand.grow(100)
        metrics = stand.get_metrics()
        assert metrics['qmd'] > 5.0
        assert metrics['tpa'] > 0

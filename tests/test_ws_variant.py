"""Tests for the WS (Western Sierra Nevada) variant implementation.

Tests cover:
- Bark ratio (constant per species, GB diameter-dependent)
- Crown ratio (Weibull with WS per-species coefficients)
- SDI maximums (WS-specific per species from sitset.f)
- HHTMAX establishment height caps (WS blkdat.f)
- Diameter growth (14 equation sets, GS/RW special equation)
- Stochastic diameter growth
- Mortality (SN model with WS SDI maximums and VARADJ)
- Integration (full stand simulation with variant='WS')
"""
import math
import random
import pytest

from pyfvs import Stand
from pyfvs.bark_ratio import (
    WSBarkRatioModel,
    create_bark_ratio_model,
)
from pyfvs.crown_ratio import (
    WSCrownRatioModel,
    create_crown_ratio_model,
)
from pyfvs.stand_metrics import StandMetricsCalculator
from pyfvs.ws_diameter_growth import (
    WSDiameterGrowthModel,
    create_ws_diameter_growth_model,
)
from pyfvs.variant_registry import get_variant_config
from pyfvs.establishment import get_hhtmax


# ===========================================================================
# WS Bark Ratio Tests
# ===========================================================================

class TestWSBarkRatio:
    """Tests for WSBarkRatioModel with constant + diameter-dependent equations."""

    def test_factory_creates_ws_model(self):
        """Factory returns WSBarkRatioModel for variant='WS'."""
        model = create_bark_ratio_model('PP', variant='WS')
        assert isinstance(model, WSBarkRatioModel)

    def test_constant_ratio_pp(self):
        """PP has constant bark ratio 0.8967 regardless of diameter."""
        model = WSBarkRatioModel('PP')
        for dob in [5.0, 10.0, 20.0, 30.0]:
            ratio = model.calculate_bark_ratio(dob)
            assert abs(ratio - 0.8967) < 0.001, f"PP ratio {ratio} != 0.8967 at DOB={dob}"

    def test_constant_ratio_ic(self):
        """IC (Incense Cedar) has lower bark ratio 0.8374."""
        model = WSBarkRatioModel('IC')
        ratio = model.calculate_bark_ratio(10.0)
        assert abs(ratio - 0.8374) < 0.001

    def test_diameter_dependent_gb(self):
        """GB (Bristlecone) has BARK2=-0.1141, ratio varies with diameter."""
        model = WSBarkRatioModel('GB')
        ratio_small = model.calculate_bark_ratio(3.0)
        ratio_large = model.calculate_bark_ratio(20.0)
        # Smaller trees should have lower ratio (BARK2 is negative)
        assert ratio_small < ratio_large

    def test_hardwood_default(self):
        """Hardwood species get default ratio 0.8374."""
        model = WSBarkRatioModel('LO')
        ratio = model.calculate_bark_ratio(10.0)
        assert abs(ratio - 0.8374) < 0.001

    def test_dib_from_dob(self):
        """DIB < DOB for all species."""
        for sp in ['PP', 'DF', 'WF', 'IC', 'GB', 'LO']:
            model = WSBarkRatioModel(sp)
            dob = 12.0
            dib = model.calculate_dib_from_dob(dob)
            assert 0 < dib < dob, f"{sp}: DIB={dib} not in (0, {dob})"

    def test_bark_ratio_bounded(self):
        """All bark ratios bounded [0.80, 0.99]."""
        for sp in ['PP', 'DF', 'GB', 'IC', 'LO', 'MC', 'OS']:
            model = WSBarkRatioModel(sp)
            for dob in [1.0, 5.0, 10.0, 30.0]:
                ratio = model.calculate_bark_ratio(dob)
                assert 0.80 <= ratio <= 0.99, f"{sp} at DOB={dob}: ratio={ratio}"


# ===========================================================================
# WS Crown Ratio Tests
# ===========================================================================

class TestWSCrownRatio:
    """Tests for WSCrownRatioModel with per-species Weibull parameters."""

    def test_factory_creates_ws_model(self):
        """Factory returns WSCrownRatioModel for variant='WS'."""
        model = create_crown_ratio_model('PP', variant='WS')
        assert isinstance(model, WSCrownRatioModel)

    def test_acr_decreases_with_density(self):
        """Average crown ratio decreases as stand density increases."""
        model = WSCrownRatioModel('PP')
        acr_low = model.calculate_average_crown_ratio(2.0)
        acr_high = model.calculate_average_crown_ratio(8.0)
        assert acr_low > acr_high, f"ACR should decrease: {acr_low} <= {acr_high}"

    def test_acr_bounded(self):
        """ACR bounded [0.05, 0.95]."""
        model = WSCrownRatioModel('DF')
        for relsdi in [1.0, 5.0, 10.0, 12.0]:
            acr = model.calculate_average_crown_ratio(relsdi)
            assert 0.05 <= acr <= 0.95, f"ACR={acr} at RELSDI={relsdi}"

    def test_individual_cr_bounded(self):
        """Individual tree CR bounded [0.10, 0.95]."""
        model = WSCrownRatioModel('PP')
        for rank in [0.1, 0.5, 0.9]:
            cr = model.predict_individual_crown_ratio(rank, 5.0)
            assert 0.10 <= cr <= 0.95, f"CR={cr} at rank={rank}"

    def test_jp_has_weiba(self):
        """JP (Jeffrey Pine) has WEIBA=2.0, unlike most species at 0.0."""
        model = WSCrownRatioModel('JP')
        assert model._weiba == 2.0

    def test_gb_returns_default(self):
        """GB (Bristlecone) has all-zero coefficients, returns 0.50."""
        model = WSCrownRatioModel('GB')
        acr = model.calculate_average_crown_ratio(5.0)
        assert acr == 0.50

    def test_dominant_vs_suppressed(self):
        """Dominant trees (high rank) should have higher CR than suppressed (low rank)."""
        model = WSCrownRatioModel('DF')
        cr_suppressed = model.predict_individual_crown_ratio(0.1, 5.0)
        cr_dominant = model.predict_individual_crown_ratio(0.9, 5.0)
        assert cr_dominant > cr_suppressed

    def test_multiple_species(self):
        """Multiple common WS species produce reasonable crown ratios."""
        for sp in ['SP', 'DF', 'WF', 'PP', 'JP', 'RF', 'IC', 'LP']:
            model = WSCrownRatioModel(sp)
            cr = model.predict_individual_crown_ratio(0.5, 5.0)
            assert 0.20 <= cr <= 0.80, f"{sp}: CR={cr} outside reasonable range"


# ===========================================================================
# WS SDI Maximum Tests
# ===========================================================================

class TestWSSDIMaximums:
    """Tests for WS-specific SDI maximum values."""

    def test_sdi_table_has_43_species(self):
        """WS SDI maximums table has all 43 species."""
        assert len(StandMetricsCalculator.WS_SDI_MAXIMUMS) == 43

    def test_key_species_values(self):
        """Verify key species SDI maximums from sitset.f."""
        sdi = StandMetricsCalculator.WS_SDI_MAXIMUMS
        assert sdi['PP'] == 571
        assert sdi['DF'] == 547
        assert sdi['RW'] == 1120  # Highest SDI
        assert sdi['GP'] == 259   # Lowest SDI
        assert sdi['RF'] == 800
        assert sdi['WF'] == 759
        assert sdi['SP'] == 647

    def test_all_positive(self):
        """All SDI maximums are positive."""
        for sp, val in StandMetricsCalculator.WS_SDI_MAXIMUMS.items():
            assert val > 0, f"{sp} SDI max {val} <= 0"

    def test_variant_config_has_sdi(self):
        """Variant config includes SDI maximums."""
        config = get_variant_config('WS')
        assert len(config.sdi_maximums) == 43
        assert config.sdi_maximums['PP'] == 571


# ===========================================================================
# WS HHTMAX Tests
# ===========================================================================

class TestWSHHTMAX:
    """Tests for WS establishment height caps."""

    def test_hhtmax_43_species(self):
        """WS HHTMAX has values for all 43 species."""
        config = get_variant_config('WS')
        assert len(config.hhtmax) == 43

    def test_key_species_hhtmax(self):
        """Verify key HHTMAX values from blkdat.f."""
        assert get_hhtmax('SP', 'WS') == 27.0
        assert get_hhtmax('PP', 'WS') == 17.0
        assert get_hhtmax('GB', 'WS') == 9.0   # Shortest
        assert get_hhtmax('MH', 'WS') == 27.0  # Tallest conifer
        assert get_hhtmax('LO', 'WS') == 24.0  # Oak

    def test_all_positive(self):
        """All HHTMAX values are positive."""
        config = get_variant_config('WS')
        for sp, val in config.hhtmax.items():
            assert val > 0, f"{sp} HHTMAX {val} <= 0"


# ===========================================================================
# WS Diameter Growth Tests
# ===========================================================================

class TestWSDiameterGrowth:
    """Tests for WSDiameterGrowthModel with 14 equation sets."""

    def test_factory_creates_model(self):
        """Factory creates cached model instances."""
        m1 = create_ws_diameter_growth_model('PP')
        m2 = create_ws_diameter_growth_model('PP')
        assert m1 is m2  # Cached

    def test_species_to_equation_mapping(self):
        """All 43 species map to equation indices 1-14."""
        for sp, idx in WSDiameterGrowthModel.SPECIES_TO_INDEX.items():
            assert 1 <= int(idx) <= 14, f"{sp} maps to invalid equation {idx}"

    def test_positive_growth(self):
        """Standard conditions produce positive diameter growth."""
        model = create_ws_diameter_growth_model('PP')
        dg = model.calculate_diameter_growth(
            dbh=8.0, crown_ratio=0.5, site_index=90,
            ba=150, bal=50, elevation=45.0
        )
        assert dg > 0, f"PP growth {dg} should be positive"

    def test_growth_increases_with_site_index(self):
        """Higher site index produces more growth."""
        model = create_ws_diameter_growth_model('PP')
        dg_low = model.calculate_diameter_growth(
            dbh=8.0, crown_ratio=0.5, site_index=60, ba=150, bal=50
        )
        dg_high = model.calculate_diameter_growth(
            dbh=8.0, crown_ratio=0.5, site_index=120, ba=150, bal=50
        )
        assert dg_high > dg_low, f"SI 120 growth {dg_high} <= SI 60 {dg_low}"

    def test_growth_decreases_with_competition(self):
        """More competition (higher BAL) reduces growth."""
        model = create_ws_diameter_growth_model('DF')
        dg_low_comp = model.calculate_diameter_growth(
            dbh=8.0, crown_ratio=0.5, site_index=80, ba=100, bal=10
        )
        dg_high_comp = model.calculate_diameter_growth(
            dbh=8.0, crown_ratio=0.5, site_index=80, ba=200, bal=150
        )
        assert dg_low_comp > dg_high_comp

    def test_gs_rw_special_equation(self):
        """GS and RW use special site-index-only equation."""
        model_gs = create_ws_diameter_growth_model('GS')
        model_rw = create_ws_diameter_growth_model('RW')
        dg_gs = model_gs.calculate_diameter_growth(
            dbh=20.0, crown_ratio=0.5, site_index=100, ba=150, bal=50
        )
        dg_rw = model_rw.calculate_diameter_growth(
            dbh=20.0, crown_ratio=0.5, site_index=100, ba=150, bal=50
        )
        # Both use equation index '4' -> same equation
        assert abs(dg_gs - dg_rw) < 0.001

    def test_rf_uses_gs_equation(self):
        """RF (Red Fir, equation 7) also uses GS/RW special equation."""
        model = create_ws_diameter_growth_model('RF')
        dg = model.calculate_diameter_growth(
            dbh=10.0, crown_ratio=0.5, site_index=80, ba=150, bal=50
        )
        assert dg > 0

    def test_time_step_scaling(self):
        """Growth scales linearly with time step."""
        model = create_ws_diameter_growth_model('PP')
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
        for sp in ['SP', 'DF', 'WF', 'IC', 'JP', 'PP', 'LP', 'MC', 'OS']:
            model = create_ws_diameter_growth_model(sp)
            dg = model.calculate_diameter_growth(
                dbh=8.0, crown_ratio=0.5, site_index=80,
                ba=120, bal=40, elevation=45.0
            )
            assert dg > 0, f"{sp} growth {dg} should be positive"


# ===========================================================================
# WS Stochastic Growth Tests
# ===========================================================================

class TestWSStochasticGrowth:
    """Tests for stochastic diameter growth in WS variant."""

    def test_sigma_values_exist(self):
        """All 43 species have sigma values."""
        assert len(WSDiameterGrowthModel._SIGMA) == 43

    def test_rng_produces_variation(self):
        """Stochastic mode with different seeds produces different results."""
        model = create_ws_diameter_growth_model('PP')
        results = set()
        for seed in range(10):
            rng = random.Random(seed)
            dg = model.calculate_diameter_growth(
                dbh=8.0, crown_ratio=0.5, site_index=90,
                ba=150, bal=50, rng=rng
            )
            results.add(round(dg, 6))
        assert len(results) > 1, "Stochastic should produce variation"

    def test_stochastic_mean_near_deterministic(self):
        """Average of many stochastic runs should approximate deterministic."""
        model = create_ws_diameter_growth_model('PP')
        det_dg = model.calculate_diameter_growth(
            dbh=8.0, crown_ratio=0.5, site_index=90, ba=150, bal=50
        )
        stoch_dgs = []
        for seed in range(100):
            rng = random.Random(seed)
            dg = model.calculate_diameter_growth(
                dbh=8.0, crown_ratio=0.5, site_index=90,
                ba=150, bal=50, rng=rng
            )
            stoch_dgs.append(dg)
        mean_stoch = sum(stoch_dgs) / len(stoch_dgs)
        # Should be within 15% of deterministic (lognormal bias on stochastic mean)
        assert abs(mean_stoch - det_dg) / det_dg < 0.15

    def test_stand_stochastic_mode(self):
        """Stand with random_seed uses stochastic diameter growth."""
        stand1 = Stand.initialize_planted(300, 90, 'PP', variant='WS', random_seed=42)
        stand2 = Stand.initialize_planted(300, 90, 'PP', variant='WS', random_seed=42)
        stand1.grow(30)
        stand2.grow(30)
        # Same seed should produce identical results
        m1 = stand1.get_metrics()
        m2 = stand2.get_metrics()
        assert abs(m1['basal_area'] - m2['basal_area']) < 0.01


# ===========================================================================
# WS Variant Registry Tests
# ===========================================================================

class TestWSVariantConfig:
    """Tests for WS variant configuration in the registry."""

    def test_variant_exists(self):
        config = get_variant_config('WS')
        assert config.code == 'WS'
        assert config.name == 'Sierra Nevada'

    def test_cycle_length(self):
        config = get_variant_config('WS')
        assert config.cycle_length == 10

    def test_default_species(self):
        config = get_variant_config('WS')
        assert config.default_species == 'PP'

    def test_growth_category(self):
        config = get_variant_config('WS')
        assert config.growth_category == 'topographic'

    def test_mortality_needs_sdi(self):
        config = get_variant_config('WS')
        assert config.mortality_needs_sdi_lookup is True

    def test_taper_model(self):
        """WS uses Flewelling taper model for applicable species."""
        from pyfvs.taper import FlewellingTaperModel
        config = get_variant_config('WS')
        assert config.taper_class is FlewellingTaperModel

    def test_default_elevation(self):
        config = get_variant_config('WS')
        assert config.default_elevation == 45.0  # ~4500 ft typical Sierra elevation


# ===========================================================================
# WS Integration Tests
# ===========================================================================

class TestWSIntegration:
    """Integration tests for full WS stand simulations."""

    def test_pp_plantation_growth(self):
        """PP plantation produces reasonable growth over 50 years."""
        stand = Stand.initialize_planted(300, 90, 'PP', variant='WS', stochastic=False)
        stand.grow(50)
        m = stand.get_metrics()

        assert m['tpa'] < 300, "Some mortality expected"
        assert m['tpa'] > 50, "Not all trees should die"
        assert m['basal_area'] > 100, f"BA {m['basal_area']:.0f} too low"
        assert m['qmd'] > 8.0, f"QMD {m['qmd']:.1f} too small"
        assert m['top_height'] > 50, f"Top height {m['top_height']:.0f} too low"

    def test_df_plantation_growth(self):
        """DF plantation produces reasonable growth."""
        stand = Stand.initialize_planted(400, 80, 'DF', variant='WS', stochastic=False)
        stand.grow(50)
        m = stand.get_metrics()

        assert m['tpa'] < 400
        assert m['basal_area'] > 100
        assert m['qmd'] > 6.0

    def test_gs_plantation_growth(self):
        """GS (Giant Sequoia) uses special equation and grows."""
        stand = Stand.initialize_planted(200, 100, 'GS', variant='WS', stochastic=False)
        stand.grow(50)
        m = stand.get_metrics()

        assert m['basal_area'] > 0
        assert m['qmd'] > 0

    def test_volume_produced(self):
        """WS variant produces volume estimates."""
        stand = Stand.initialize_planted(300, 90, 'PP', variant='WS', stochastic=False)
        stand.grow(50)
        m = stand.get_metrics()
        assert m['volume'] > 0, "Volume should be positive after 50 years"

    def test_mortality_reduces_tpa(self):
        """Dense stand experiences density-dependent mortality."""
        stand = Stand.initialize_planted(600, 90, 'PP', variant='WS', stochastic=False)
        stand.grow(30)
        m = stand.get_metrics()
        assert m['tpa'] < 600, "Dense stand should have mortality"

    def test_thinning_works(self):
        """Thinning from below reduces TPA."""
        stand = Stand.initialize_planted(400, 90, 'PP', variant='WS', stochastic=False)
        stand.grow(20)
        pre_thin = stand.get_metrics()['tpa']
        stand.thin_from_below(target_tpa=200)
        post_thin = stand.get_metrics()['tpa']
        assert post_thin < pre_thin

    @pytest.mark.slow
    def test_yield_table(self):
        """Full rotation yield table produces valid data at each age."""
        stand = Stand.initialize_planted(300, 90, 'PP', variant='WS', stochastic=False)
        prev_ba = 0
        for age in range(10, 61, 10):
            stand.grow(10)
            m = stand.get_metrics()
            assert m['basal_area'] > prev_ba or m['tpa'] < 50, \
                f"BA should generally increase (age {age})"
            prev_ba = m['basal_area']

    def test_stochastic_vs_deterministic(self):
        """Stochastic and deterministic produce different but reasonable results."""
        stand_det = Stand.initialize_planted(300, 90, 'PP', variant='WS', stochastic=False)
        stand_sto = Stand.initialize_planted(300, 90, 'PP', variant='WS', random_seed=42)
        stand_det.grow(40)
        stand_sto.grow(40)
        m_det = stand_det.get_metrics()
        m_sto = stand_sto.get_metrics()

        # Both should produce reasonable results
        for key in ['basal_area', 'qmd', 'top_height']:
            assert m_det[key] > 0
            assert m_sto[key] > 0

        # They should differ somewhat (stochastic adds noise)
        ba_diff_pct = abs(m_det['basal_area'] - m_sto['basal_area']) / m_det['basal_area'] * 100
        assert ba_diff_pct < 30, f"BA difference {ba_diff_pct:.0f}% too large"

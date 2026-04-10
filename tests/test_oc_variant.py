"""Tests for the OC (Southwest Oregon) variant implementation.

Tests cover:
- Bark ratio (4 equation types: constant, power, linear, WJ special)
- Crown ratio (per-species Weibull with 33 species)
- SDI maximums (OC-specific per species from sitset.f C5 array)
- HHTMAX establishment height caps (33 species, RA=50, WJ=6)
- Diameter growth (13 equation sets, GS/RW special equation, stochastic)
- Stochastic diameter growth
- Mortality (SN model with OC SDI maximums and VARADJ)
- Integration (full stand simulation with variant='OC')
"""
import math
import random
import pytest

from pyfvs import Stand
from pyfvs.bark_ratio import (
    OCBarkRatioModel,
    create_bark_ratio_model,
)
from pyfvs.crown_ratio import (
    OCCrownRatioModel,
    create_crown_ratio_model,
)
from pyfvs.stand_metrics import StandMetricsCalculator
from pyfvs.oc_diameter_growth import (
    OCDiameterGrowthModel,
    create_oc_diameter_growth_model,
)
from pyfvs.variant_registry import get_variant_config
from pyfvs.establishment import get_hhtmax


# ===========================================================================
# OC Bark Ratio Tests
# ===========================================================================

class TestOCBarkRatio:
    """Tests for OCBarkRatioModel with 4 equation types."""

    def test_factory_creates_oc_model(self):
        """Factory returns OCBarkRatioModel for variant='OC'."""
        model = create_bark_ratio_model('DF', variant='OC')
        assert isinstance(model, OCBarkRatioModel)

    def test_constant_equation_df(self):
        """DF uses constant bark ratio: BRDAT=0.867."""
        model = OCBarkRatioModel('DF')
        coeffs = model.get_species_coefficients()
        assert coeffs['type'] == 'constant'
        assert coeffs['brdat'] == pytest.approx(0.867)
        ratio = model.calculate_bark_ratio(10.0)
        assert ratio == pytest.approx(0.867, abs=0.001)

    def test_power_equation_wh(self):
        """WH uses power equation: DIB = 0.93371 * DOB^1.0."""
        model = OCBarkRatioModel('WH')
        coeffs = model.get_species_coefficients()
        assert coeffs['type'] == 'barkb'
        assert coeffs['eq_type'] == 1
        ratio = model.calculate_bark_ratio(10.0)
        assert 0.80 <= ratio <= 0.99

    def test_linear_equation_wo(self):
        """WO uses linear equation: DIB = -0.30722 + 0.95956*DOB."""
        model = OCBarkRatioModel('WO')
        coeffs = model.get_species_coefficients()
        assert coeffs['type'] == 'barkb'
        assert coeffs['eq_type'] == 2
        ratio = model.calculate_bark_ratio(10.0)
        assert 0.80 <= ratio <= 0.99

    def test_wj_special_equation(self):
        """WJ uses special equation: BRATIO = 0.9002 - 0.3089/D."""
        model = OCBarkRatioModel('WJ')
        coeffs = model.get_species_coefficients()
        assert coeffs['type'] == 'wj_special'
        # At D=10: 0.9002 - 0.3089/10 = 0.8693
        ratio_10 = model.calculate_bark_ratio(10.0)
        assert ratio_10 == pytest.approx(0.8693, abs=0.001)
        # At D=5: 0.9002 - 0.3089/5 = 0.8384
        ratio_5 = model.calculate_bark_ratio(5.0)
        assert ratio_5 < ratio_10  # Smaller trees have thicker relative bark

    def test_dib_from_dob(self):
        """DIB < DOB for all species."""
        for sp in ['DF', 'PP', 'WH', 'WO', 'WJ', 'RA', 'BM']:
            model = OCBarkRatioModel(sp)
            dob = 12.0
            dib = model.calculate_dib_from_dob(dob)
            assert 0 < dib < dob, f"{sp}: DIB={dib} not in (0, {dob})"

    def test_bark_ratio_bounded(self):
        """All bark ratios bounded [0.80, 0.99]."""
        for sp in ['DF', 'PP', 'WH', 'WO', 'WJ', 'RA', 'BM', 'GF', 'IC']:
            model = OCBarkRatioModel(sp)
            for dob in [1.0, 5.0, 10.0, 30.0]:
                ratio = model.calculate_bark_ratio(dob)
                assert 0.80 <= ratio <= 0.99, f"{sp} at DOB={dob}: ratio={ratio}"

    def test_roundtrip_dib_dob_constant(self):
        """DOB -> DIB -> DOB roundtrip for constant species."""
        model = OCBarkRatioModel('DF')
        dob = 12.0
        dib = model.calculate_dib_from_dob(dob)
        dob_back = model.calculate_dob_from_dib(dib)
        assert abs(dob - dob_back) < 0.1


# ===========================================================================
# OC Crown Ratio Tests
# ===========================================================================

class TestOCCrownRatio:
    """Tests for OCCrownRatioModel with per-species Weibull."""

    def test_factory_creates_oc_model(self):
        """Factory returns OCCrownRatioModel for variant='OC'."""
        model = create_crown_ratio_model('DF', variant='OC')
        assert isinstance(model, OCCrownRatioModel)

    def test_average_cr_decreases_with_density(self):
        """Average crown ratio decreases as SDI increases."""
        model = OCCrownRatioModel('DF')
        cr_low = model.calculate_average_crown_ratio(3.0)
        cr_high = model.calculate_average_crown_ratio(9.0)
        # DF has C1=0 so no SDI effect; check at least it's bounded
        assert 0.05 <= cr_low <= 0.95
        assert 0.05 <= cr_high <= 0.95

    def test_average_cr_sdi_sensitive_species(self):
        """Species with C1 < 0 show CR decrease with SDI."""
        model = OCCrownRatioModel('PP')  # PP has C1=-0.02041
        cr_low = model.calculate_average_crown_ratio(2.0)
        cr_high = model.calculate_average_crown_ratio(10.0)
        assert cr_low > cr_high

    def test_individual_cr_bounded(self):
        """Individual crown ratios bounded [0.10, 0.95]."""
        for sp in ['DF', 'PP', 'WO', 'RA', 'WH', 'GF']:
            model = OCCrownRatioModel(sp)
            for rank in [0.1, 0.3, 0.5, 0.7, 0.9]:
                cr = model.predict_individual_crown_ratio(rank, 5.0)
                assert 0.10 <= cr <= 0.95, f"{sp} rank={rank}: CR={cr}"

    def test_cr_increases_with_rank(self):
        """Larger trees (higher rank) tend to have higher crown ratios."""
        model = OCCrownRatioModel('PP')
        cr_low = model.predict_individual_crown_ratio(0.2, 5.0)
        cr_high = model.predict_individual_crown_ratio(0.8, 5.0)
        assert cr_high > cr_low

    def test_shifted_weibull_species(self):
        """Species with WEIBA > 0 (shifted Weibull) still produce valid CRs."""
        for sp in ['WP', 'SP', 'DF', 'MH', 'IC', 'ES', 'RA', 'OS']:
            model = OCCrownRatioModel(sp)
            cr = model.predict_individual_crown_ratio(0.5, 5.0)
            assert 0.10 <= cr <= 0.95, f"{sp}: CR={cr}"

    def test_update_crown_ratio_change(self):
        """Crown ratio change is bounded to 1% per year."""
        model = OCCrownRatioModel('DF')
        new_cr = model.update_crown_ratio_change(0.40, 0.60, 2.0, cycle_length=10)
        assert abs(new_cr - 0.40) <= 0.10 + 0.001  # 1% per year * 10 years

    def test_all_33_species_load(self):
        """All 33 SO species load without error."""
        species_list = [
            'WP', 'SP', 'DF', 'WF', 'MH', 'IC', 'LP', 'ES', 'SH', 'PP',
            'WJ', 'GF', 'AF', 'SF', 'NF', 'WB', 'WL', 'RC', 'WH', 'PY',
            'WA', 'RA', 'BM', 'AS', 'CW', 'CH', 'WO', 'WI', 'GC', 'MC',
            'MB', 'OS', 'OH',
        ]
        for sp in species_list:
            model = OCCrownRatioModel(sp)
            cr = model.predict_individual_crown_ratio(0.5, 5.0)
            assert 0.10 <= cr <= 0.95, f"{sp}: CR={cr}"


# ===========================================================================
# OC SDI Maximums Tests
# ===========================================================================

class TestOCSDIMaximums:
    """Tests for OC variant SDI maximums from sitset.f C5 array."""

    def test_sdi_max_count(self):
        """OC has SDI maximums for 33 species."""
        assert len(StandMetricsCalculator.OC_SDI_MAXIMUMS) == 33

    def test_sdi_max_df(self):
        """DF SDI maximum is 570."""
        assert StandMetricsCalculator.OC_SDI_MAXIMUMS['DF'] == 570

    def test_sdi_max_sh(self):
        """SH has highest SDI max at 1000."""
        assert StandMetricsCalculator.OC_SDI_MAXIMUMS['SH'] == 1000

    def test_sdi_max_range(self):
        """All SDI maximums in reasonable range [200, 1100]."""
        for sp, sdi in StandMetricsCalculator.OC_SDI_MAXIMUMS.items():
            assert 200 <= sdi <= 1100, f"{sp}: SDI={sdi}"


# ===========================================================================
# OC HHTMAX Tests
# ===========================================================================

class TestOCHHTMAX:
    """Tests for OC variant establishment height caps from blkdat.f."""

    def test_hhtmax_ra_highest(self):
        """RA has the highest HHTMAX at 50.0 ft."""
        assert get_hhtmax('RA', 'OC') == 50.0

    def test_hhtmax_wj_lowest(self):
        """WJ has the lowest HHTMAX at 6.0 ft."""
        assert get_hhtmax('WJ', 'OC') == 6.0

    def test_hhtmax_df(self):
        """DF HHTMAX is 21.0 ft."""
        assert get_hhtmax('DF', 'OC') == 21.0

    def test_hhtmax_unknown_species_uses_default(self):
        """Unknown species gets default HHTMAX of 20.0 ft."""
        assert get_hhtmax('ZZ', 'OC') == 20.0


# ===========================================================================
# OC Diameter Growth Tests
# ===========================================================================

class TestOCDiameterGrowth:
    """Tests for OCDiameterGrowthModel with 13 equation sets."""

    def test_factory_creates_model(self):
        """Factory creates cached model instance."""
        model = create_oc_diameter_growth_model('DF')
        assert isinstance(model, OCDiameterGrowthModel)

    def test_dds_positive(self):
        """DDS is positive for typical inputs."""
        model = create_oc_diameter_growth_model('DF')
        dds = model.calculate_dds(10.0, 0.5, 100.0, 150.0, 50.0)
        assert dds > 0

    def test_dds_increases_with_si(self):
        """Higher site index produces more growth."""
        model = create_oc_diameter_growth_model('DF')
        dds_low = model.calculate_dds(10.0, 0.5, 60.0, 150.0, 50.0)
        dds_high = model.calculate_dds(10.0, 0.5, 120.0, 150.0, 50.0)
        assert dds_high > dds_low

    def test_dds_decreases_with_competition(self):
        """Higher BAL reduces growth."""
        model = create_oc_diameter_growth_model('DF')
        dds_low_comp = model.calculate_dds(10.0, 0.5, 100.0, 150.0, 10.0)
        dds_high_comp = model.calculate_dds(10.0, 0.5, 100.0, 150.0, 100.0)
        assert dds_low_comp > dds_high_comp

    def test_gs_rw_special_equation(self):
        """GS/RW (equation 12) uses special equation form."""
        model = create_oc_diameter_growth_model('GS')
        assert model.equation_index == '12'
        dds = model.calculate_dds(15.0, 0.6, 100.0, 200.0, 80.0)
        assert dds > 0

    def test_diameter_growth_from_dds(self):
        """Diameter growth converts DDS to diameter increment."""
        model = create_oc_diameter_growth_model('DF')
        dg = model.calculate_diameter_growth(10.0, 0.5, 100.0, 150.0, 50.0)
        assert dg > 0
        assert dg < 5.0  # Reasonable bound for 5-year growth

    def test_time_step_scaling(self):
        """DDS scales linearly with time step."""
        model = create_oc_diameter_growth_model('DF')
        dds_5 = model.calculate_dds(10.0, 0.5, 100.0, 150.0, 50.0, time_step=5.0)
        dds_10 = model.calculate_dds(10.0, 0.5, 100.0, 150.0, 50.0, time_step=10.0)
        assert dds_10 == pytest.approx(dds_5 * 2.0, rel=0.01)

    def test_multiple_species(self):
        """Multiple species produce positive DDS."""
        for sp in ['DF', 'PP', 'WH', 'GF', 'IC', 'WO', 'TO']:
            model = create_oc_diameter_growth_model(sp)
            dds = model.calculate_dds(10.0, 0.5, 100.0, 150.0, 50.0)
            assert dds > 0, f"{sp}: DDS={dds}"


# ===========================================================================
# OC Stochastic Growth Tests
# ===========================================================================

class TestOCStochasticGrowth:
    """Tests for stochastic diameter growth in OC variant."""

    def test_stochastic_differs_from_deterministic(self):
        """Stochastic DDS differs from deterministic."""
        model = create_oc_diameter_growth_model('DF')
        rng = random.Random(42)
        dds_stoch = model.calculate_dds(10.0, 0.5, 100.0, 150.0, 50.0, rng=rng)
        dds_det = model.calculate_dds(10.0, 0.5, 100.0, 150.0, 50.0, rng=None)
        assert dds_stoch != dds_det

    def test_stochastic_reproducible_with_seed(self):
        """Same seed produces same result."""
        model = create_oc_diameter_growth_model('DF')
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        dds1 = model.calculate_dds(10.0, 0.5, 100.0, 150.0, 50.0, rng=rng1)
        dds2 = model.calculate_dds(10.0, 0.5, 100.0, 150.0, 50.0, rng=rng2)
        assert dds1 == dds2

    def test_stochastic_mean_near_deterministic(self):
        """Mean of many stochastic runs should be near deterministic."""
        model = create_oc_diameter_growth_model('DF')
        det = model.calculate_dds(10.0, 0.5, 100.0, 150.0, 50.0, rng=None)
        stoch_values = []
        for seed in range(100):
            rng = random.Random(seed)
            val = model.calculate_dds(10.0, 0.5, 100.0, 150.0, 50.0, rng=rng)
            stoch_values.append(val)
        stoch_mean = sum(stoch_values) / len(stoch_values)
        # Within 20% of deterministic (Baskerville correction brings them close)
        assert abs(stoch_mean - det) / det < 0.20

    def test_gs_rw_stochastic(self):
        """GS/RW special equation also supports stochastic."""
        model = create_oc_diameter_growth_model('GS')
        rng = random.Random(42)
        dds_stoch = model.calculate_dds(15.0, 0.6, 100.0, 200.0, 80.0, rng=rng)
        dds_det = model.calculate_dds(15.0, 0.6, 100.0, 200.0, 80.0, rng=None)
        assert dds_stoch != dds_det
        assert dds_stoch > 0


# ===========================================================================
# OC Variant Config Tests
# ===========================================================================

class TestOCVariantConfig:
    """Tests for OC variant configuration in the registry."""

    def test_oc_registered(self):
        """OC is in the variant registry."""
        config = get_variant_config('OC')
        assert config.code == 'OC'

    def test_oc_properties(self):
        """OC has correct basic properties.

        cycle_length is 5, not 10: Fortran oc/blkdat.f sets DATA YR / 5.0 /,
        and oc/dgf.f converts the underlying 10-year coefficients to 5-year
        at lines 402-403 (TDDS=EXP(DDS); DDS=ALOG(TDDS/2.0)).
        """
        config = get_variant_config('OC')
        assert config.name == 'Southwest Oregon'
        assert config.cycle_length == 5
        assert config.default_species == 'DF'
        assert config.growth_category == 'topographic'

    def test_oc_model_classes(self):
        """OC uses proper model classes."""
        config = get_variant_config('OC')
        assert config.bark_ratio_class.__name__ == 'OCBarkRatioModel'
        assert config.crown_ratio_class.__name__ == 'OCCrownRatioModel'
        # OCMortalityModel handles its own SDI lookup from the variant's
        # JSON config (sdi_maximums in oc_mortality_defaults.json), so the
        # registry doesn't need to inject one at construction time.
        assert config.mortality_class.__name__ == 'OCMortalityModel'
        assert config.mortality_needs_sdi_lookup is False

    def test_oc_taper_model(self):
        """OC uses Flewelling taper model."""
        config = get_variant_config('OC')
        assert config.taper_class is not None
        assert config.taper_class.__name__ == 'FlewellingTaperModel'

    def test_oc_sdi_maximums(self):
        """OC has SDI maximums in config."""
        config = get_variant_config('OC')
        assert len(config.sdi_maximums) == 33
        assert config.sdi_maximums['DF'] == 570

    def test_oc_hhtmax(self):
        """OC has HHTMAX in config."""
        config = get_variant_config('OC')
        assert len(config.hhtmax) == 33
        assert config.hhtmax['RA'] == 50.0
        assert config.hhtmax['WJ'] == 6.0

    def test_oc_elevation(self):
        """OC default elevation is 35.0 (hundreds of feet) per oc/grinit.f:174."""
        config = get_variant_config('OC')
        assert config.default_elevation == 35.0


# ===========================================================================
# OC Integration Tests
# ===========================================================================

class TestOCIntegration:
    """Integration tests for the OC variant with Stand simulation."""

    def test_stand_initialize_oc(self):
        """Stand initializes with variant='OC'."""
        stand = Stand.initialize_planted(300, 100, 'DF', variant='OC')
        assert stand is not None
        assert len(stand.trees) > 0

    def test_stand_grow_one_cycle(self):
        """Stand grows one cycle without error."""
        stand = Stand.initialize_planted(300, 100, 'DF', variant='OC')
        initial_ba = stand.get_metrics()['basal_area']
        stand.grow(10)
        final_ba = stand.get_metrics()['basal_area']
        assert final_ba > initial_ba

    def test_stand_metrics_reasonable(self):
        """Stand metrics are in reasonable ranges after growth."""
        stand = Stand.initialize_planted(300, 100, 'DF', variant='OC')
        stand.grow(10)
        metrics = stand.get_metrics()
        assert 0 < metrics['tpa'] <= 300
        assert 0 < metrics['basal_area'] < 500
        assert 0 < metrics['qmd'] < 30
        assert 0 < metrics['top_height'] < 200
        assert 0 < metrics['volume']

    def test_stochastic_stand_varies(self):
        """Two different seeds produce different results."""
        stand1 = Stand.initialize_planted(300, 100, 'DF', variant='OC', random_seed=42)
        stand2 = Stand.initialize_planted(300, 100, 'DF', variant='OC', random_seed=99)
        stand1.grow(20)
        stand2.grow(20)
        ba1 = stand1.get_metrics()['basal_area']
        ba2 = stand2.get_metrics()['basal_area']
        assert ba1 != ba2

    def test_deterministic_stand(self):
        """Deterministic mode produces reasonable results."""
        stand = Stand.initialize_planted(300, 100, 'DF', variant='OC', stochastic=False)
        stand.grow(20)
        metrics = stand.get_metrics()
        # Just verify deterministic mode runs and produces plausible output
        assert metrics['basal_area'] > 100
        assert metrics['qmd'] > 3.0

    def test_pp_species(self):
        """PP (second most common OC species) grows without error."""
        stand = Stand.initialize_planted(300, 90, 'PP', variant='OC')
        stand.grow(10)
        metrics = stand.get_metrics()
        assert metrics['basal_area'] > 0

    def test_mortality_applies(self):
        """Mortality reduces TPA over multiple cycles."""
        stand = Stand.initialize_planted(500, 100, 'DF', variant='OC', stochastic=False)
        initial_tpa = stand.get_metrics()['tpa']
        stand.grow(50)
        final_tpa = stand.get_metrics()['tpa']
        assert final_tpa < initial_tpa

    @pytest.mark.slow
    def test_long_rotation(self):
        """Full 80-year rotation produces plausible results."""
        stand = Stand.initialize_planted(300, 100, 'DF', variant='OC', stochastic=False)
        stand.grow(80)
        metrics = stand.get_metrics()
        assert metrics['qmd'] > 8.0
        assert metrics['top_height'] > 60.0
        assert metrics['volume'] > 1000

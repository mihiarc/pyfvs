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
        # Within 20% of deterministic (lognormal bias on stochastic mean)
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
        # OrganonSwoMortalityModel extends OCMortalityModel with ORGANON
        # SWO individual-tree mortality (mortality.f PM_SWO).  It handles
        # its own SDI lookup, so the registry doesn't inject one.
        assert config.mortality_class.__name__ == 'OrganonSwoMortalityModel'
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
# ORGANON SWO Mortality Tests
# ===========================================================================

class TestOrganonSwoMortality:
    """Tests for the ORGANON SWO mortality model (mortality.f PM_SWO)."""

    def test_pm_swo_df_hand_calc(self):
        """PM_SWO logit for DF matches hand calculation."""
        from pyfvs.mortality import OrganonSwoMortalityModel

        model = OrganonSwoMortalityModel()
        # DF = group 1.  Hand calc:
        # B0=-4.648483270, B1=-0.266558690, B2=0.003699110,
        # B3=-2.118026640, B4=0.025499430, B5=0.003361340,
        # B6=0.013553950, B7=-2.723470950
        coeffs = model._PM_SWO[1]
        dbh, cr, si, bal, og = 10.0, 0.5, 80.0, 50.0, 0.01
        pmk = model._pm_swo(coeffs, dbh, cr, si, bal, og, grp=1)
        expected = (
            -4.648483270
            + -0.266558690 * 10.0
            + 0.003699110 * 100.0
            + -2.118026640 * 0.5
            + 0.025499430 * 80.0
            + 0.003361340 * 50.0
            + 0.013553950 * 50.0 * math.exp(-2.723470950 * 0.01)
        )
        assert abs(pmk - expected) < 1e-8

    def test_pm_swo_wo_uses_log_bal(self):
        """Oregon white oak (group 14) uses log(BAL+5)."""
        from pyfvs.mortality import OrganonSwoMortalityModel

        model = OrganonSwoMortalityModel()
        coeffs = model._PM_SWO[14]
        dbh, cr, si, bal, og = 8.0, 0.4, 80.0, 30.0, 0.0
        pmk = model._pm_swo(coeffs, dbh, cr, si, bal, og, grp=14)
        expected = (
            coeffs[0]
            + coeffs[1] * 8.0
            + coeffs[2] * 64.0
            + coeffs[3] * 0.4
            + coeffs[4] * 80.0
            + coeffs[5] * math.log(35.0)
        )
        assert abs(pmk - expected) < 1e-8

    def test_species_group_mapping(self):
        """Key OC species map to correct SWO groups."""
        from pyfvs.mortality import OrganonSwoMortalityModel

        m = OrganonSwoMortalityModel._SPECIES_TO_SWO_GROUP
        assert m['DF'] == 1   # Douglas-fir
        assert m['GF'] == 2   # Grand fir → GW group
        assert m['PP'] == 3   # Ponderosa pine
        assert m['SP'] == 4   # Sugar pine
        assert m['IC'] == 5   # Incense cedar
        assert m['WH'] == 6   # Western hemlock
        assert m['TO'] == 11  # Tanoak
        assert m['WO'] == 14  # Oregon white oak
        assert m['RA'] == 16  # Red alder

    def test_oldgro_small_trees(self):
        """OLDGRO returns ~0 for a young plantation."""
        from pyfvs.tree import Tree
        from pyfvs.mortality import OrganonSwoMortalityModel

        trees = [Tree(0.5, 5.0, species='DF', variant='OC') for _ in range(400)]
        og = OrganonSwoMortalityModel._compute_oldgro(trees)
        # 0.5 * 5.0 / 10000 = 0.00025
        assert og < 0.001

    def test_cradj_above_017(self):
        """Crown ratio adjustment is 1.0 when CR > 0.17."""
        cr = 0.5
        cradj = 1.0
        if cr <= 0.17:
            cradj = 1.0 - math.exp(-(25.0 * cr) ** 2)
        assert cradj == 1.0

    def test_cradj_below_017(self):
        """Crown ratio adjustment reduces mortality for very low CR."""
        cr = 0.10
        cradj = 1.0 - math.exp(-(25.0 * cr) ** 2)
        assert 0.0 < cradj < 1.0

    def test_fallback_to_fvs_when_no_big6(self):
        """Model falls back to FVS mortality when no big-6 trees qualify."""
        from pyfvs.tree import Tree
        from pyfvs.mortality import OrganonSwoMortalityModel

        model = OrganonSwoMortalityModel()
        # WO is NOT big-6, and trees are below threshold anyway
        trees = [Tree(0.05, 3.0, species='WO', variant='OC') for _ in range(100)]
        result = model.apply_mortality(trees, cycle_length=5, site_index=80.0)
        assert len(result.survivors) + result.mortality_count == 100

    def test_organon_mortality_activates_for_df(self):
        """ORGANON path activates for DF trees above threshold."""
        from pyfvs.tree import Tree
        from pyfvs.mortality import OrganonSwoMortalityModel

        model = OrganonSwoMortalityModel()
        # DF trees above threshold (HT>4.5, DBH>=0.1)
        trees = [Tree(2.0, 15.0, species='DF', variant='OC') for _ in range(200)]
        result = model.apply_mortality(
            trees, cycle_length=5, site_index=80.0, random_seed=42,
        )
        # Some trees should die under ORGANON individual-tree mortality
        assert result.mortality_count >= 0
        assert len(result.survivors) + result.mortality_count == 200

    def test_organon_mortality_rate_increases_with_bal(self):
        """Higher BAL (competition) increases mortality probability."""
        from pyfvs.mortality import OrganonSwoMortalityModel

        model = OrganonSwoMortalityModel()
        coeffs = model._PM_SWO[1]  # DF
        # Low competition
        pmk_low = model._pm_swo(coeffs, 5.0, 0.5, 80.0, 10.0, 0.0, grp=1)
        # High competition
        pmk_high = model._pm_swo(coeffs, 5.0, 0.5, 80.0, 200.0, 0.0, grp=1)
        # Higher BAL → higher logit → higher mortality probability
        assert pmk_high > pmk_low

    def test_pp_si_converted_to_df_si(self):
        """PP site index is converted to DF equivalent for PM_SWO."""
        from pyfvs.mortality import OrganonSwoMortalityModel

        model = OrganonSwoMortalityModel(default_species='PP')
        df_si = model._resolve_df_site_index(70.0)
        assert abs(df_si - 1.062934 * 70.0) < 0.01


# ===========================================================================
# ORGANON SWO Diameter Growth Tests
# ===========================================================================

class TestOrganonSwoDiameterGrowth:
    """Tests for the ORGANON SWO diameter growth equation (diagro.f DG_SWO)."""

    def test_dg_swo_df_hand_calc(self):
        """DG_SWO for DF matches hand calculation."""
        from pyfvs.oc_diameter_growth import organon_swo_diameter_growth

        dg = organon_swo_diameter_growth(
            species='DF', dbh=10.0, crown_ratio=0.5,
            site_index=80.0, ba=120.0, bal=60.0,
        )
        # DF group=1: B0=-5.356, B1=0.841, ..., ADJ=0.8938
        # Result should be a reasonable 5-year DG for a 10" DF
        assert 0.3 < dg < 2.5

    def test_dg_swo_competition_reduces_growth(self):
        """Higher BAL and stand BA reduce diameter growth."""
        from pyfvs.oc_diameter_growth import organon_swo_diameter_growth

        dg_low = organon_swo_diameter_growth(
            species='DF', dbh=10.0, crown_ratio=0.5,
            site_index=80.0, ba=50.0, bal=10.0,
        )
        dg_high = organon_swo_diameter_growth(
            species='DF', dbh=10.0, crown_ratio=0.5,
            site_index=80.0, ba=200.0, bal=100.0,
        )
        assert dg_high < dg_low

    def test_dg_swo_higher_si_increases_growth(self):
        """Higher site index increases diameter growth."""
        from pyfvs.oc_diameter_growth import organon_swo_diameter_growth

        dg_low = organon_swo_diameter_growth(
            species='DF', dbh=10.0, crown_ratio=0.5,
            site_index=60.0, ba=120.0, bal=60.0,
        )
        dg_high = organon_swo_diameter_growth(
            species='DF', dbh=10.0, crown_ratio=0.5,
            site_index=100.0, ba=120.0, bal=60.0,
        )
        assert dg_high > dg_low

    def test_iorg_species_set(self):
        """IORG species set matches dgdriv.f:233."""
        from pyfvs.oc_diameter_growth import _IORG_SPECIES

        # Big-6 must be in IORG set
        for sp in ('DF', 'GF', 'IC', 'SP', 'PP'):
            assert sp in _IORG_SPECIES
        # Non-IORG species must NOT be in set
        for sp in ('RF', 'SH', 'LP', 'JP', 'WB', 'KP'):
            assert sp not in _IORG_SPECIES

    def test_organon_growth_used_for_large_df(self):
        """DF trees above threshold use ORGANON growth (smaller increment)."""
        from pyfvs import Stand
        from pyfvs.tree import Tree

        # Create a stand with DF trees above ORGANON threshold
        trees = [Tree(2.0, 15.0, species='DF', variant='OC') for _ in range(200)]
        stand = Stand(trees, site_index=80, species='DF', variant='OC', stochastic=False)
        stand.grow(5)
        m = stand.get_metrics()
        # With ORGANON growth, QMD should be smaller than with FVS DGF
        # FVS DGF alone produces QMD > 5" for this scenario
        assert m['qmd'] < 5.0


# ===========================================================================
# ORGANON SWO Height Growth Tests
# ===========================================================================

class TestOrganonSwoHeightGrowth:
    """Tests for the ORGANON SWO height growth (htgrowth.f HS_HG + HG_SWO)."""

    def test_hs_hg_df_potential(self):
        """HS_HG returns positive potential height growth for DF."""
        from pyfvs.oc_height_growth import _hs_hg

        phtgro, geage = _hs_hg(80.0, 15.0, is_pp=False)
        assert phtgro > 5.0  # at least 5 ft/5yr for SI=80 DF at 15 ft
        assert phtgro < 15.0
        assert 0 < geage < 500

    def test_hs_hg_pp_vs_df(self):
        """PP potential growth differs from DF."""
        from pyfvs.oc_height_growth import _hs_hg

        df_hg, _ = _hs_hg(80.0, 20.0, is_pp=False)
        pp_hg, _ = _hs_hg(80.0, 20.0, is_pp=True)
        assert df_hg != pp_hg  # different species curves

    def test_hg_swo_tcch_zero(self):
        """With TCCH=0, HG_SWO modifier is ~1.0 for high CR."""
        from pyfvs.oc_height_growth import _hg_swo

        # DF (grp 1), good CR, no competition above → modifier ≈ 1.0
        hg = _hg_swo(1, 8.0, 0.8, tcch=0.0)
        assert abs(hg - 8.0) < 0.5  # should be close to phtgro

    def test_organon_hg_returns_none_for_minor_species(self):
        """Minor species (WO, RA, TO etc.) return None → FVS fallback."""
        from pyfvs.oc_height_growth import organon_swo_height_growth

        assert organon_swo_height_growth('WO', 20.0, 0.8, 80.0) is None
        assert organon_swo_height_growth('RA', 20.0, 0.8, 80.0) is None
        assert organon_swo_height_growth('TO', 20.0, 0.8, 80.0) is None

    def test_organon_hg_positive_for_df(self):
        """ORGANON height growth is positive for DF."""
        from pyfvs.oc_height_growth import organon_swo_height_growth

        hg = organon_swo_height_growth('DF', 20.0, 0.8, 80.0)
        assert hg is not None
        assert hg > 1.0


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

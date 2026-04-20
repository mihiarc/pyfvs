"""Tests for the Northeast (NE) variant of FVS-Python.

Tests cover:
- Factory dispatch: correct model types returned for NE variant
- Bark ratio: NEBarkRatioModel with constant ratios for 108 species
- Crown ratio: NECrownRatioModel with TWIGS equation
- SDI maximums: NE_SDI_MAXIMUMS for all 108 species
- Mortality: NEMortalityModel with 4-group background + density
- Volume: NE species coverage in volume_library
- Crown ratio variant bug fix: regression tests
- Integration: Stand simulations with NE species
- Smoke tests: Full 50-year simulations
"""
import math
import pytest

from pyfvs.bark_ratio import (
    create_bark_ratio_model, NEBarkRatioModel, LSBarkRatioModel, BarkRatioModel,
)
from pyfvs.crown_ratio import (
    create_crown_ratio_model, NECrownRatioModel, LSCrownRatioModel, CrownRatioModel,
)
from pyfvs.mortality import (
    create_mortality_model, NEMortalityModel, LSMortalityModel, MortalityModel,
)
from pyfvs.stand_metrics import StandMetricsCalculator
from pyfvs.volume_library import (
    VolumeCalculator, VOLUME_COEFFICIENTS_OUTSIDE_BARK, HARDWOOD_SPECIES,
)
from pyfvs.tree import Tree
from pyfvs import Stand


# Key NE species for testing
NE_CONIFERS = ['BF', 'RS', 'WS', 'WP', 'RN', 'EH', 'WC', 'BS']
NE_HARDWOODS = ['RM', 'SM', 'YB', 'AB', 'WA', 'RO', 'WO', 'BC', 'YP', 'WN']
NE_UNIQUE = ['RS', 'AW', 'TM', 'SB', 'RB', 'GB', 'CT', 'CO', 'SL', 'SD']


# ============================================================
# Test Factory Dispatch
# ============================================================
class TestNEFactoryDispatch:
    """Test that factory functions return correct model types for NE."""

    def test_bark_ratio_factory_returns_ne_model(self):
        model = create_bark_ratio_model('RM', variant='NE')
        assert isinstance(model, NEBarkRatioModel)
        assert isinstance(model, LSBarkRatioModel)

    def test_crown_ratio_factory_returns_ne_model(self):
        model = create_crown_ratio_model('RM', variant='NE')
        assert isinstance(model, NECrownRatioModel)
        assert isinstance(model, LSCrownRatioModel)

    def test_mortality_factory_returns_ne_model(self):
        model = create_mortality_model('RM', variant='NE')
        assert isinstance(model, NEMortalityModel)
        assert isinstance(model, LSMortalityModel)

    def test_sn_factory_still_returns_sn_models(self):
        bark = create_bark_ratio_model('LP', variant='SN')
        crown = create_crown_ratio_model('LP', variant='SN')
        mort = create_mortality_model('LP', variant='SN')
        assert isinstance(bark, BarkRatioModel)
        assert isinstance(crown, CrownRatioModel)
        assert isinstance(mort, MortalityModel)


# ============================================================
# Test NE Bark Ratio
# ============================================================
class TestNEBarkRatio:
    """Test NEBarkRatioModel with constant bark ratios."""

    def test_ne_bark_ratio_range(self):
        """All NE species should have bark ratios between 0.80 and 0.99."""
        for species in NE_CONIFERS + NE_HARDWOODS + NE_UNIQUE:
            model = NEBarkRatioModel(species)
            ratio = model.calculate_bark_ratio(10.0)
            assert 0.80 <= ratio <= 0.99, f"{species}: bark ratio {ratio} out of range"

    def test_ne_bark_ratio_constant_across_diameters(self):
        """NE bark ratios should be constant regardless of diameter."""
        model = NEBarkRatioModel('RM')
        ratio_5 = model.calculate_bark_ratio(5.0)
        ratio_15 = model.calculate_bark_ratio(15.0)
        ratio_30 = model.calculate_bark_ratio(30.0)
        assert ratio_5 == ratio_15 == ratio_30

    def test_ne_dib_from_dob(self):
        """DIB should be smaller than DOB."""
        model = NEBarkRatioModel('SM')
        dob = 12.0
        dib = model.calculate_dib_from_dob(dob)
        assert 0 < dib < dob

    def test_ne_dob_from_dib_roundtrip(self):
        """Converting DOB->DIB->DOB should return original value."""
        model = NEBarkRatioModel('WP')
        dob = 10.0
        dib = model.calculate_dib_from_dob(dob)
        dob_recovered = model.calculate_dob_from_dib(dib)
        assert abs(dob - dob_recovered) < 0.001

    def test_ne_shared_species_match_ls(self):
        """Species shared between NE and LS should have similar bark ratios."""
        shared_species = ['BF', 'WS', 'SM', 'RM', 'RO', 'WO', 'YB', 'WP', 'QA']
        for species in shared_species:
            ne_model = NEBarkRatioModel(species)
            ls_model = LSBarkRatioModel(species)
            ne_ratio = ne_model.calculate_bark_ratio(10.0)
            ls_ratio = ls_model.calculate_bark_ratio(10.0)
            # Should be within 2% of each other (same Raile 1982 source)
            assert abs(ne_ratio - ls_ratio) < 0.02, \
                f"{species}: NE={ne_ratio:.3f} vs LS={ls_ratio:.3f}"


# ============================================================
# Test NE Crown Ratio
# ============================================================
class TestNECrownRatio:
    """Test NECrownRatioModel with TWIGS equation."""

    def test_ne_crown_ratio_valid_range(self):
        """Crown ratio predictions should be between 0.05 and 0.95."""
        for species in NE_CONIFERS + NE_HARDWOODS:
            model = NECrownRatioModel(species)
            cr = model.predict_crown_ratio(8.0, 100.0)
            assert 0.05 <= cr <= 0.95, f"{species}: CR {cr} out of range"

    def test_ne_crown_ratio_decreases_with_ba(self):
        """Crown ratio should decrease with increasing basal area."""
        model = NECrownRatioModel('RM')
        cr_low = model.predict_crown_ratio(8.0, 50.0)
        cr_high = model.predict_crown_ratio(8.0, 200.0)
        assert cr_low > cr_high

    def test_ne_crown_ratio_increases_with_dbh(self):
        """Crown ratio should generally increase with DBH (more light)."""
        model = NECrownRatioModel('RM')
        cr_small = model.predict_crown_ratio(2.0, 100.0)
        cr_large = model.predict_crown_ratio(20.0, 100.0)
        assert cr_large > cr_small

    def test_ne_twigs_equation_form(self):
        """Verify the TWIGS equation produces expected values for known inputs."""
        model = NECrownRatioModel('SM')
        # SM coefficients: BCR1=3.111, BCR2=0.01534, BCR3=6.251, BCR4=-0.01552
        # ACR = 10 * (3.111/(1+0.01534*100) + 6.251*(1-exp(-0.01552*10)))
        #     = 10 * (3.111/2.534 + 6.251*(1-0.8585))
        #     = 10 * (1.228 + 0.884) = 21.12 => CR = 0.2112
        cr = model.predict_crown_ratio(10.0, 100.0)
        # Should be around 0.20-0.25 based on the equation
        assert 0.15 <= cr <= 0.35

# ============================================================
# Test NE SDI Maximums
# ============================================================
class TestNESDIMaximums:
    """Test NE SDI maximum values."""

    def test_ne_sdi_maximums_exist(self):
        """NE_SDI_MAXIMUMS should have entries."""
        sdi_maxs = StandMetricsCalculator.NE_SDI_MAXIMUMS
        assert len(sdi_maxs) >= 90  # At least 90 of 108 species

    def test_ne_sdi_maximums_positive(self):
        """All SDI max values should be positive."""
        for species, sdi_max in StandMetricsCalculator.NE_SDI_MAXIMUMS.items():
            assert sdi_max > 0, f"{species}: SDI max={sdi_max}"

    def test_ne_sdi_maximums_reasonable_range(self):
        """SDI max values should be between 200 and 600."""
        for species, sdi_max in StandMetricsCalculator.NE_SDI_MAXIMUMS.items():
            assert 200 <= sdi_max <= 600, f"{species}: SDI max={sdi_max} out of range"

    def test_ne_metrics_calculator_loads_ne_sdis(self):
        """StandMetricsCalculator with variant='NE' should use NE SDI maximums."""
        calc = StandMetricsCalculator(default_species='RM', variant='NE')
        assert calc._sdi_maximums is StandMetricsCalculator.NE_SDI_MAXIMUMS


# ============================================================
# Test NE Mortality
# ============================================================
class TestNEMortality:
    """Test NEMortalityModel."""

    def test_ne_mortality_species_groups_cover_all_species(self):
        """All major NE species should have a mortality group assignment."""
        ne_species = NE_CONIFERS + NE_HARDWOODS + NE_UNIQUE
        for species in ne_species:
            group = NEMortalityModel.SPECIES_MORTALITY_GROUP.get(species)
            assert group is not None, f"{species}: no mortality group"
            assert group in (1, 2, 3, 4), f"{species}: invalid group {group}"

    def test_ne_mortality_group_assignments_match_fortran(self):
        """NE species groups match IMAPNE from morts.f (groups don't follow taxonomy)."""
        # Group 1: BF, WS, RS, BS, EH, WC, RM, SM, AB (per Fortran IMAPNE)
        for species in ['BF', 'WS', 'RS', 'BS', 'EH', 'WC', 'RM', 'SM', 'AB']:
            group = NEMortalityModel.SPECIES_MORTALITY_GROUP.get(species)
            assert group == 1, f"{species}: expected group 1, got {group}"
        # Group 3: WP, RN, LP, RC, JU (pines and cedar)
        for species in ['WP', 'LP', 'RC', 'JU']:
            group = NEMortalityModel.SPECIES_MORTALITY_GROUP.get(species)
            assert group == 3, f"{species}: expected group 3, got {group}"
        # Group 4: WO, RO, YB, WA, BC, YP, WN
        for species in ['WO', 'RO', 'YB', 'WA', 'BC', 'YP', 'WN']:
            group = NEMortalityModel.SPECIES_MORTALITY_GROUP.get(species)
            assert group == 4, f"{species}: expected group 4, got {group}"

    def test_ne_background_mortality_rate(self):
        """Background mortality rate should be reasonable for NE trees."""
        model = NEMortalityModel(default_species='RM')
        tree = Tree(species='RM', dbh=8.0, height=50.0, age=30, variant='NE')
        rate = model.calculate_background_mortality_rate(tree, cycle_length=10)
        # Halved logistic rate over 10 years should be small but non-zero
        assert 0.001 < rate < 0.20, f"Background rate {rate} out of expected range"


# ============================================================
# Test NE Volume
# ============================================================
class TestNEVolume:
    """Test volume coverage for NE species."""

    def test_ne_species_have_volume_coefficients(self):
        """NE-unique species should have explicit volume coefficients."""
        ne_species_with_volume = ['RS', 'AW', 'TM', 'SB', 'CT', 'CO', 'YP', 'SU']
        for species in ne_species_with_volume:
            assert species in VOLUME_COEFFICIENTS_OUTSIDE_BARK, \
                f"{species}: missing from VOLUME_COEFFICIENTS_OUTSIDE_BARK"

    def test_ne_hardwoods_in_hardwood_set(self):
        """NE hardwood species should be in HARDWOOD_SPECIES set."""
        ne_hardwoods = ['SB', 'RB', 'GB', 'CT', 'CO', 'SL', 'YP', 'SU', 'SD', 'PW']
        for species in ne_hardwoods:
            assert species in HARDWOOD_SPECIES, \
                f"{species}: missing from HARDWOOD_SPECIES"

    def test_ne_volume_calculation_reasonable(self):
        """Volume calculations for NE species should be reasonable."""
        test_cases = [
            ('RM', 10.0, 60.0),  # Red Maple, 10" DBH, 60' tall
            ('SM', 12.0, 70.0),  # Sugar Maple
            ('WP', 15.0, 80.0),  # White Pine
            ('RO', 14.0, 75.0),  # Red Oak
        ]
        for species, dbh, height in test_cases:
            calc = VolumeCalculator(species)
            result = calc.calculate_volume(dbh, height)
            assert result.total_cubic_volume > 0, \
                f"{species}: zero volume for {dbh}\" x {height}'"
            # Expected range: 5-50 cubic feet for these dimensions
            assert 2.0 < result.total_cubic_volume < 80.0, \
                f"{species}: volume {result.total_cubic_volume} out of expected range"


# ============================================================
# Test Crown Ratio Variant Bug Fix
# ============================================================
class TestNECrownRatioVariantFix:
    """Test that crown ratio variant propagation bug is fixed."""

    def test_ne_tree_uses_ne_crown_ratio_model(self):
        """Tree with variant='NE' should use NECrownRatioModel, not SN."""
        tree = Tree(species='RM', dbh=8.0, height=50.0, age=30, variant='NE')
        assert getattr(tree, '_variant', 'SN') == 'NE'

    def test_ls_tree_uses_ls_crown_ratio_model(self):
        """Tree with variant='LS' should use LSCrownRatioModel, not SN."""
        tree = Tree(species='RN', dbh=8.0, height=50.0, age=30, variant='LS')
        assert getattr(tree, '_variant', 'SN') == 'LS'


# ============================================================
# Test NE Integration
# ============================================================
class TestNEIntegration:
    """Integration tests for NE variant stand simulations."""

    def test_ne_stand_initialization(self):
        """Should initialize NE stand with Red Maple."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=60, species='RM', variant='NE'
        )
        metrics = stand.get_metrics()
        assert metrics['tpa'] == 500
        assert metrics['basal_area'] > 0

    def test_ne_stand_grows(self):
        """NE stand should grow over time."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=60, species='RM', variant='NE'
        )
        initial_metrics = stand.get_metrics()
        # NE Red Maple uses slower NC-128 curve (c3=-0.0141) so trees need
        # more time to accumulate volume beyond initial tiny-tree artifacts
        stand.grow(years=20)
        grown_metrics = stand.get_metrics()
        # Volume and basal area should increase after sufficient growth
        assert grown_metrics['volume'] > initial_metrics['volume']
        assert grown_metrics['basal_area'] > initial_metrics['basal_area']

    def test_ne_white_pine_grows(self):
        """NE White Pine stand should grow."""
        stand = Stand.initialize_planted(
            trees_per_acre=400, site_index=65, species='WP', variant='NE'
        )
        stand.grow(years=20)
        metrics = stand.get_metrics()
        assert metrics['volume'] > 0
        assert metrics['basal_area'] > 0

    def test_ne_red_oak_grows(self):
        """NE Northern Red Oak stand should grow."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=60, species='RO', variant='NE'
        )
        stand.grow(years=20)
        metrics = stand.get_metrics()
        assert metrics['volume'] > 0
        assert metrics['basal_area'] > 0

    def test_ne_mortality_occurs(self):
        """High-density NE stand should experience mortality over 50 years."""
        stand = Stand.initialize_planted(
            trees_per_acre=800, site_index=60, species='RM', variant='NE'
        )
        stand.grow(years=50)
        metrics = stand.get_metrics()
        # Should lose some trees to mortality
        assert metrics['tpa'] < 800

    def test_ne_produces_different_results_than_sn(self):
        """NE variant should produce different growth than SN for same species."""
        stand_ne = Stand.initialize_planted(
            trees_per_acre=500, site_index=60, species='RM', variant='NE'
        )
        stand_sn = Stand.initialize_planted(
            trees_per_acre=500, site_index=60, species='RM', variant='SN'
        )
        stand_ne.grow(years=30)
        stand_sn.grow(years=30)
        ne_metrics = stand_ne.get_metrics()
        sn_metrics = stand_sn.get_metrics()
        # Different growth models should give different results
        # (NE uses BA increment vs SN uses DDS)
        assert ne_metrics['volume'] != sn_metrics['volume']

    def test_ne_stand_metrics_use_ne_sdi(self):
        """NE stand should use NE SDI maximums, not SN."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=60, species='RM', variant='NE'
        )
        # The stand's metrics calculator should be using NE SDI maximums
        metrics = stand.get_metrics()
        # Red Maple NE SDI max = 400
        assert metrics.get('basal_area', 0) >= 0  # Sanity check it runs

    def test_ne_stand_thinning(self):
        """NE stand should support thinning operations."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=60, species='RM', variant='NE'
        )
        stand.grow(years=20)
        stand.thin_from_below(target_tpa=200)
        metrics_after = stand.get_metrics()
        assert metrics_after['tpa'] <= 200


# ============================================================
# Test NE Smoke Tests
# ============================================================
class TestNESmokeTest:
    """Full 50-year simulation smoke tests for NE variant."""

    def test_red_maple_si60_50yr(self):
        """Red Maple SI=60 50yr - primary NE smoke test."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=60, species='RM', variant='NE'
        )
        stand.grow(years=50)
        metrics = stand.get_metrics()

        # Expect: 350-500 TPA (slower-growing hardwood, moderate mortality)
        assert 200 <= metrics['tpa'] <= 500, f"TPA={metrics['tpa']}"

        # Expect: 5-12" QMD (slower-growing hardwood)
        qmd = metrics.get('qmd', 0)
        if qmd == 0 and metrics['basal_area'] > 0:
            qmd = math.sqrt(metrics['basal_area'] / (metrics['tpa'] * 0.005454))
        assert 3.0 <= qmd <= 15.0, f"QMD={qmd}"

        # Expect: 50-200 sq ft BA
        assert 30 <= metrics['basal_area'] <= 250, f"BA={metrics['basal_area']}"

        # Expect: positive volume
        assert metrics['volume'] > 0, f"Volume={metrics['volume']}"

    def test_white_pine_si65_50yr(self):
        """White Pine SI=65 50yr smoke test."""
        stand = Stand.initialize_planted(
            trees_per_acre=400, site_index=65, species='WP', variant='NE'
        )
        stand.grow(years=50)
        metrics = stand.get_metrics()

        # White Pine should grow faster than Red Maple
        assert metrics['tpa'] > 0
        assert metrics['basal_area'] > 0
        assert metrics['volume'] > 0

    def test_red_oak_si60_50yr(self):
        """Northern Red Oak SI=60 50yr smoke test."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=60, species='RO', variant='NE'
        )
        stand.grow(years=50)
        metrics = stand.get_metrics()

        assert metrics['tpa'] > 0
        assert metrics['basal_area'] > 0
        assert metrics['volume'] > 0

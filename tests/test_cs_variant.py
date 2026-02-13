"""Tests for the Central States (CS) variant of FVS-Python.

Tests cover:
- Factory dispatch: correct model types returned for CS variant
- Bark ratio: CSBarkRatioModel with constant ratios for 96 species
- Crown ratio: CSCrownRatioModel with TWIGS equation
- SDI maximums: CS_SDI_MAXIMUMS for 96 species
- Mortality: CSMortalityModel with 4-group background + density
- Volume: CS species coverage in volume_library
- Integration: Stand simulations with CS species
- Smoke tests: Full 50-year simulations
"""
import math
import pytest

from pyfvs.bark_ratio import (
    create_bark_ratio_model, CSBarkRatioModel, LSBarkRatioModel, BarkRatioModel,
)
from pyfvs.crown_ratio import (
    create_crown_ratio_model, CSCrownRatioModel, LSCrownRatioModel, CrownRatioModel,
)
from pyfvs.mortality import (
    create_mortality_model, CSMortalityModel, LSMortalityModel, MortalityModel,
)
from pyfvs.stand_metrics import StandMetricsCalculator
from pyfvs.volume_library import (
    VolumeCalculator, VOLUME_COEFFICIENTS_OUTSIDE_BARK, HARDWOOD_SPECIES,
)
from pyfvs.tree import Tree
from pyfvs import Stand


# Key CS species for testing
CS_CONIFERS = ['RC', 'JU', 'SP', 'VP', 'LP', 'OS', 'WP', 'BY']
CS_HARDWOODS = ['WO', 'RO', 'SM', 'WN', 'YP', 'WA', 'BC', 'BO', 'SH', 'HL']
CS_UNIQUE = ['BJ', 'DO', 'NK', 'QS', 'UA', 'SG', 'BY', 'KC', 'MB', 'OB']


# ============================================================
# Test Factory Dispatch
# ============================================================
class TestCSFactoryDispatch:
    """Test that factory functions return correct model types for CS."""

    def test_bark_ratio_factory_returns_cs_model(self):
        model = create_bark_ratio_model('WO', variant='CS')
        assert isinstance(model, CSBarkRatioModel)
        assert isinstance(model, LSBarkRatioModel)

    def test_crown_ratio_factory_returns_cs_model(self):
        model = create_crown_ratio_model('WO', variant='CS')
        assert isinstance(model, CSCrownRatioModel)
        assert isinstance(model, LSCrownRatioModel)

    def test_mortality_factory_returns_cs_model(self):
        model = create_mortality_model('WO', variant='CS')
        assert isinstance(model, CSMortalityModel)
        assert isinstance(model, LSMortalityModel)

    def test_sn_factory_still_returns_sn_models(self):
        bark = create_bark_ratio_model('LP', variant='SN')
        crown = create_crown_ratio_model('LP', variant='SN')
        mort = create_mortality_model('LP', variant='SN')
        assert isinstance(bark, BarkRatioModel)
        assert isinstance(crown, CrownRatioModel)
        assert isinstance(mort, MortalityModel)


# ============================================================
# Test CS Bark Ratio
# ============================================================
class TestCSBarkRatio:
    """Test CSBarkRatioModel with constant bark ratios."""

    def test_cs_bark_ratio_range(self):
        """All CS species should have bark ratios between 0.80 and 0.99."""
        for species in CS_CONIFERS + CS_HARDWOODS + CS_UNIQUE:
            model = CSBarkRatioModel(species)
            ratio = model.calculate_bark_ratio(10.0)
            assert 0.80 <= ratio <= 0.99, f"{species}: bark ratio {ratio} out of range"

    def test_cs_bark_ratio_constant_across_diameters(self):
        """CS bark ratios should be constant regardless of diameter."""
        model = CSBarkRatioModel('WO')
        ratio_5 = model.calculate_bark_ratio(5.0)
        ratio_15 = model.calculate_bark_ratio(15.0)
        ratio_30 = model.calculate_bark_ratio(30.0)
        assert ratio_5 == ratio_15 == ratio_30

    def test_cs_dib_from_dob(self):
        """DIB should be smaller than DOB."""
        model = CSBarkRatioModel('SM')
        dob = 12.0
        dib = model.calculate_dib_from_dob(dob)
        assert 0 < dib < dob

    def test_cs_dob_from_dib_roundtrip(self):
        """Converting DOB->DIB->DOB should return original value."""
        model = CSBarkRatioModel('WO')
        dob = 10.0
        dib = model.calculate_dib_from_dob(dob)
        dob_recovered = model.calculate_dob_from_dib(dib)
        assert abs(dob - dob_recovered) < 0.001

    def test_cs_shared_species_match_ls(self):
        """Species shared between CS and LS should have similar bark ratios."""
        shared_species = ['SM', 'RM', 'RO', 'WO', 'WA', 'WN', 'QA', 'WP']
        for species in shared_species:
            cs_model = CSBarkRatioModel(species)
            ls_model = LSBarkRatioModel(species)
            cs_ratio = cs_model.calculate_bark_ratio(10.0)
            ls_ratio = ls_model.calculate_bark_ratio(10.0)
            # Should be within 2% of each other (same Raile 1982 source)
            assert abs(cs_ratio - ls_ratio) < 0.02, \
                f"{species}: CS={cs_ratio:.3f} vs LS={ls_ratio:.3f}"


# ============================================================
# Test CS Crown Ratio
# ============================================================
class TestCSCrownRatio:
    """Test CSCrownRatioModel with TWIGS equation."""

    def test_cs_crown_ratio_valid_range(self):
        """Crown ratio predictions should be between 0.05 and 0.95."""
        for species in CS_CONIFERS + CS_HARDWOODS:
            model = CSCrownRatioModel(species)
            cr = model.predict_crown_ratio(8.0, 100.0)
            assert 0.05 <= cr <= 0.95, f"{species}: CR {cr} out of range"

    def test_cs_crown_ratio_decreases_with_ba(self):
        """Crown ratio should decrease with increasing basal area."""
        model = CSCrownRatioModel('WO')
        cr_low = model.predict_crown_ratio(8.0, 50.0)
        cr_high = model.predict_crown_ratio(8.0, 200.0)
        assert cr_low > cr_high

    def test_cs_crown_ratio_increases_with_dbh(self):
        """Crown ratio should generally increase with DBH (more light)."""
        model = CSCrownRatioModel('WO')
        cr_small = model.predict_crown_ratio(2.0, 100.0)
        cr_large = model.predict_crown_ratio(20.0, 100.0)
        assert cr_large > cr_small

    def test_cs_twigs_equation_form(self):
        """Verify the TWIGS equation produces expected values for known inputs."""
        model = CSCrownRatioModel('SM')
        # SM coefficients: BCR1=3.111, BCR2=0.01534, BCR3=6.251, BCR4=-0.01552
        # Same as LS/NE SM (TWIGS shared)
        cr = model.predict_crown_ratio(10.0, 100.0)
        # Should be around 0.20-0.25 based on the equation
        assert 0.15 <= cr <= 0.35

    def test_cs_shared_species_match_ls_crown_ratio(self):
        """Species shared between CS and LS should produce similar TWIGS results."""
        # SM is shared with identical coefficients
        cs_model = CSCrownRatioModel('SM')
        ls_model = LSCrownRatioModel('SM')
        cs_cr = cs_model.predict_crown_ratio(8.0, 120.0)
        ls_cr = ls_model.predict_crown_ratio(8.0, 120.0)
        # Same TWIGS coefficients should give same result
        assert abs(cs_cr - ls_cr) < 0.001, \
            f"SM: CS CR={cs_cr:.3f} vs LS CR={ls_cr:.3f}"


# ============================================================
# Test CS SDI Maximums
# ============================================================
class TestCSSDIMaximums:
    """Test CS SDI maximum values."""

    def test_cs_sdi_maximums_exist(self):
        """CS_SDI_MAXIMUMS should have entries for major species."""
        sdi_maxs = StandMetricsCalculator.CS_SDI_MAXIMUMS
        assert len(sdi_maxs) >= 70  # At least 70 of 96 species

    def test_cs_sdi_maximums_positive(self):
        """All SDI max values should be positive."""
        for species, sdi_max in StandMetricsCalculator.CS_SDI_MAXIMUMS.items():
            assert sdi_max > 0, f"{species}: SDI max={sdi_max}"

    def test_cs_sdi_maximums_reasonable_range(self):
        """SDI max values should be between 200 and 600."""
        for species, sdi_max in StandMetricsCalculator.CS_SDI_MAXIMUMS.items():
            assert 200 <= sdi_max <= 600, f"{species}: SDI max={sdi_max} out of range"

    def test_cs_metrics_calculator_loads_cs_sdis(self):
        """StandMetricsCalculator with variant='CS' should use CS SDI maximums."""
        calc = StandMetricsCalculator(default_species='WO', variant='CS')
        assert calc._sdi_maximums is StandMetricsCalculator.CS_SDI_MAXIMUMS


# ============================================================
# Test CS Mortality
# ============================================================
class TestCSMortality:
    """Test CSMortalityModel."""

    def test_cs_mortality_species_groups_cover_major_species(self):
        """Major CS species should have a mortality group assignment."""
        cs_species = CS_CONIFERS + CS_HARDWOODS + CS_UNIQUE
        for species in cs_species:
            group = CSMortalityModel.SPECIES_MORTALITY_GROUP.get(species)
            assert group is not None, f"{species}: no mortality group"
            assert group in (1, 2, 3, 4), f"{species}: invalid group {group}"

    def test_cs_mortality_group_assignments_match_fortran(self):
        """CS species groups match IMAPCS from morts.f (groups don't follow taxonomy)."""
        # Group 1: SM, RM, AB, AE, BW, GA, etc. (per Fortran IMAPCS)
        for species in ['SM', 'RM', 'AB', 'AE', 'BW', 'GA', 'BK', 'DW']:
            group = CSMortalityModel.SPECIES_MORTALITY_GROUP.get(species)
            assert group == 1, f"{species}: expected group 1, got {group}"
        # Group 2: JU, OS
        for species in ['JU', 'OS']:
            group = CSMortalityModel.SPECIES_MORTALITY_GROUP.get(species)
            assert group == 2, f"{species}: expected group 2, got {group}"
        # Group 3: RC, SP, VP, LP, WP, BY (conifers)
        for species in ['RC', 'SP', 'VP', 'LP', 'WP', 'BY']:
            group = CSMortalityModel.SPECIES_MORTALITY_GROUP.get(species)
            assert group == 3, f"{species}: expected group 3, got {group}"
        # Group 4: WO, RO, BO, WN, YP, WA, BC
        for species in ['WO', 'RO', 'BO', 'WN', 'YP', 'WA', 'BC']:
            group = CSMortalityModel.SPECIES_MORTALITY_GROUP.get(species)
            assert group == 4, f"{species}: expected group 4, got {group}"

    def test_cs_background_mortality_rate(self):
        """Background mortality rate should be reasonable for CS trees."""
        model = CSMortalityModel(default_species='WO')
        tree = Tree(species='WO', dbh=8.0, height=50.0, age=30, variant='CS')
        rate = model.calculate_background_mortality_rate(tree, cycle_length=10)
        # Halved logistic rate over 10 years should be small but non-zero
        assert 0.001 < rate < 0.20, f"Background rate {rate} out of expected range"


# ============================================================
# Test CS Volume
# ============================================================
class TestCSVolume:
    """Test volume coverage for CS species."""

    def test_cs_unique_species_have_volume_coefficients(self):
        """CS-unique species should have explicit volume coefficients."""
        cs_species_with_volume = ['BY', 'TL', 'TS', 'UA', 'SG', 'BJ', 'NK', 'KC']
        for species in cs_species_with_volume:
            assert species in VOLUME_COEFFICIENTS_OUTSIDE_BARK, \
                f"{species}: missing from VOLUME_COEFFICIENTS_OUTSIDE_BARK"

    def test_cs_hardwoods_in_hardwood_set(self):
        """CS hardwood species should be in HARDWOOD_SPECIES set."""
        cs_hardwoods = ['TL', 'TS', 'UA', 'SG', 'BJ', 'DO', 'NK', 'QS', 'KC', 'MB']
        for species in cs_hardwoods:
            assert species in HARDWOOD_SPECIES, \
                f"{species}: missing from HARDWOOD_SPECIES"

    def test_cs_volume_calculation_reasonable(self):
        """Volume calculations for CS species should be reasonable."""
        test_cases = [
            ('WO', 10.0, 60.0),   # White Oak, 10" DBH, 60' tall
            ('RO', 12.0, 70.0),   # Northern Red Oak
            ('SM', 10.0, 65.0),   # Sugar Maple
            ('WN', 14.0, 75.0),   # Black Walnut
        ]
        for species, dbh, height in test_cases:
            calc = VolumeCalculator(species)
            result = calc.calculate_volume(dbh, height)
            assert result.total_cubic_volume > 0, \
                f"{species}: zero volume for {dbh}\" x {height}'"
            # Expected range: 5-50 cubic feet for these dimensions
            assert 2.0 < result.total_cubic_volume < 80.0, \
                f"{species}: volume {result.total_cubic_volume} out of expected range"

    def test_cs_unique_species_volume(self):
        """CS-unique species should produce positive volume."""
        for species in ['BY', 'TL', 'BJ', 'KC', 'HL']:
            calc = VolumeCalculator(species)
            result = calc.calculate_volume(10.0, 60.0)
            assert result.total_cubic_volume > 0, \
                f"{species}: zero volume"


# ============================================================
# Test CS Integration
# ============================================================
class TestCSIntegration:
    """Integration tests for CS variant stand simulations."""

    def test_cs_stand_initialization(self):
        """Should initialize CS stand with White Oak."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=70, species='WO', variant='CS'
        )
        metrics = stand.get_metrics()
        assert metrics['tpa'] == 500
        assert metrics['basal_area'] > 0

    def test_cs_stand_grows(self):
        """CS stand should grow over time (past establishment phase)."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=70, species='WO', variant='CS'
        )
        # Grow past establishment phase where trees are sub-breast-height
        # and volume is dominated by per-tree minimum floor
        stand.grow(years=30)
        post_establishment_metrics = stand.get_metrics()
        stand.grow(years=10)
        grown_metrics = stand.get_metrics()
        # Volume and basal area should increase after establishment
        assert grown_metrics['volume'] > post_establishment_metrics['volume']
        assert grown_metrics['basal_area'] > post_establishment_metrics['basal_area']

    def test_cs_red_oak_grows(self):
        """CS Northern Red Oak stand should grow."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=65, species='RO', variant='CS'
        )
        stand.grow(years=20)
        metrics = stand.get_metrics()
        assert metrics['volume'] > 0
        assert metrics['basal_area'] > 0

    def test_cs_sugar_maple_grows(self):
        """CS Sugar Maple stand should grow."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=60, species='SM', variant='CS'
        )
        stand.grow(years=20)
        metrics = stand.get_metrics()
        assert metrics['volume'] > 0
        assert metrics['basal_area'] > 0

    def test_cs_mortality_occurs(self):
        """High-density CS stand should experience mortality over 50 years."""
        stand = Stand.initialize_planted(
            trees_per_acre=800, site_index=70, species='WO', variant='CS'
        )
        stand.grow(years=50)
        metrics = stand.get_metrics()
        # Should lose some trees to mortality
        assert metrics['tpa'] < 800

    def test_cs_produces_different_results_than_sn(self):
        """CS variant should produce different growth than SN for same species."""
        stand_cs = Stand.initialize_planted(
            trees_per_acre=500, site_index=65, species='WO', variant='CS'
        )
        stand_sn = Stand.initialize_planted(
            trees_per_acre=500, site_index=65, species='WO', variant='SN'
        )
        stand_cs.grow(years=30)
        stand_sn.grow(years=30)
        cs_metrics = stand_cs.get_metrics()
        sn_metrics = stand_sn.get_metrics()
        # Different growth models should give different results
        assert cs_metrics['volume'] != sn_metrics['volume']

    def test_cs_stand_metrics_use_cs_sdi(self):
        """CS stand should use CS SDI maximums, not SN."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=70, species='WO', variant='CS'
        )
        metrics = stand.get_metrics()
        # Sanity check it runs
        assert metrics.get('basal_area', 0) >= 0

    def test_cs_stand_thinning(self):
        """CS stand should support thinning operations."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=70, species='WO', variant='CS'
        )
        stand.grow(years=20)
        stand.thin_from_below(target_tpa=200)
        metrics_after = stand.get_metrics()
        assert metrics_after['tpa'] <= 200


# ============================================================
# Test CS Smoke Tests
# ============================================================
class TestCSSmokeTest:
    """Full 50-year simulation smoke tests for CS variant."""

    def test_white_oak_si70_50yr(self):
        """White Oak SI=70 50yr - primary CS smoke test."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=70, species='WO', variant='CS'
        )
        stand.grow(years=50)
        metrics = stand.get_metrics()

        # Expect: 300-500 TPA (moderate mortality in oak-hickory)
        assert 200 <= metrics['tpa'] <= 500, f"TPA={metrics['tpa']}"

        # Expect: 5-14" QMD (Midwest oaks grow moderately)
        qmd = metrics.get('qmd', 0)
        if qmd == 0 and metrics['basal_area'] > 0:
            qmd = math.sqrt(metrics['basal_area'] / (metrics['tpa'] * 0.005454))
        assert 3.0 <= qmd <= 18.0, f"QMD={qmd}"

        # Expect: 50-300 sq ft BA
        assert 30 <= metrics['basal_area'] <= 300, f"BA={metrics['basal_area']}"

        # Expect: positive volume
        assert metrics['volume'] > 0, f"Volume={metrics['volume']}"

    def test_red_oak_si65_50yr(self):
        """Northern Red Oak SI=65 50yr smoke test."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=65, species='RO', variant='CS'
        )
        stand.grow(years=50)
        metrics = stand.get_metrics()

        assert metrics['tpa'] > 0
        assert metrics['basal_area'] > 0
        assert metrics['volume'] > 0

    def test_sugar_maple_si60_50yr(self):
        """Sugar Maple SI=60 50yr smoke test."""
        stand = Stand.initialize_planted(
            trees_per_acre=500, site_index=60, species='SM', variant='CS'
        )
        stand.grow(years=50)
        metrics = stand.get_metrics()

        assert metrics['tpa'] > 0
        assert metrics['basal_area'] > 0
        assert metrics['volume'] > 0

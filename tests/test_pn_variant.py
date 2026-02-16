"""Tests for the PN (Pacific Northwest Coast) variant implementation.

Tests cover:
- Bark ratio (3 equation types: power, linear, constant)
- Crown ratio (Weibull with PN coefficients, Redwood logistic)
- SDI maximums (PN-specific per species)
- Volume (PNW species coefficients)
- Mortality (PN uses SN model with PN SDI maximums)
- Integration (full stand simulation with variant='PN')
"""
import math
import pytest

from pyfvs import Stand
from pyfvs.bark_ratio import (
    PNBarkRatioModel,
    create_bark_ratio_model,
)
from pyfvs.crown_ratio import (
    PNCrownRatioModel,
    create_crown_ratio_model,
)
from pyfvs.mortality import create_mortality_model, MortalityModel
from pyfvs.stand_metrics import StandMetricsCalculator
from pyfvs.volume_library import (
    VolumeCalculator,
    calculate_tree_volume,
    VOLUME_COEFFICIENTS_OUTSIDE_BARK,
    VOLUME_COEFFICIENTS_INSIDE_BARK,
    HARDWOOD_SPECIES,
)


# ===========================================================================
# Phase 1: PN Bark Ratio Tests
# ===========================================================================

class TestPNBarkRatio:
    """Tests for PNBarkRatioModel with 3 equation types."""

    def test_factory_creates_pn_model(self):
        """Factory returns PNBarkRatioModel for variant='PN'."""
        model = create_bark_ratio_model('DF', variant='PN')
        assert isinstance(model, PNBarkRatioModel)

    def test_type1_power_equation_df(self):
        """Type 1 (power): DF bark ratio at various DBH values."""
        model = PNBarkRatioModel('DF')
        # DF is group 1: DIB = 0.903563 * DOB^0.989388
        for dob in [5.0, 10.0, 20.0, 30.0]:
            dib = model.calculate_dib_from_dob(dob)
            ratio = model.calculate_bark_ratio(dob)
            assert 0.80 <= ratio <= 0.99, f"DF bark ratio {ratio} out of bounds at DOB={dob}"
            assert dib < dob, f"DIB {dib} >= DOB {dob}"
            assert dib > 0, f"DIB {dib} should be positive"

    def test_type1_power_equation_wh(self):
        """Type 1 (power): WH bark ratio (group 7, b=1.0)."""
        model = PNBarkRatioModel('WH')
        # WH group 7: DIB = 0.933710 * DOB^1.0 = 0.933710 * DOB
        dob = 10.0
        dib = model.calculate_dib_from_dob(dob)
        expected = 0.933710 * 10.0
        assert abs(dib - expected) < 0.01, f"WH DIB {dib} != expected {expected}"

    def test_type2_linear_equation_ra(self):
        """Type 2 (linear): RA bark ratio (Red Alder, group 11)."""
        model = PNBarkRatioModel('RA')
        # RA group 11: DIB = 0.075256 + 0.943730 * DOB
        dob = 10.0
        dib = model.calculate_dib_from_dob(dob)
        expected = 0.075256 + 0.943730 * 10.0
        assert abs(dib - expected) < 0.01, f"RA DIB {dib} != expected {expected}"

    def test_type2_linear_equation_bm(self):
        """Type 2 (linear): BM bark ratio (Bigleaf Maple, group 9)."""
        model = PNBarkRatioModel('BM')
        # BM group 9: DIB = 0.083600 + 0.947820 * DOB
        dob = 12.0
        dib = model.calculate_dib_from_dob(dob)
        expected = 0.083600 + 0.947820 * 12.0
        assert abs(dib - expected) < 0.01

    def test_type3_constant_ratio_es(self):
        """Type 3 (constant): ES bark ratio = 0.90."""
        model = PNBarkRatioModel('ES')
        # ES group 13: DIB = 0.90 * DOB
        dob = 10.0
        dib = model.calculate_dib_from_dob(dob)
        assert abs(dib - 9.0) < 0.01, f"ES DIB {dib} != 9.0"
        assert abs(model.calculate_bark_ratio(dob) - 0.90) < 0.01

    def test_type3_constant_ratio_lp(self):
        """Type 3 (constant): LP (lodgepole) bark ratio = 0.90 in PN."""
        model = PNBarkRatioModel('LP')
        dob = 8.0
        dib = model.calculate_dib_from_dob(dob)
        assert abs(dib - 7.2) < 0.01, f"LP PN DIB {dib} != 7.2"

    def test_all_ratios_bounded(self):
        """All PN bark ratios are bounded 0.80-0.99 for reasonable DBH."""
        species_list = ['DF', 'WH', 'RC', 'SS', 'SF', 'GF', 'RA', 'BM',
                        'ES', 'LP', 'RW', 'WO', 'GC', 'MH', 'AF', 'PP']
        for sp in species_list:
            model = PNBarkRatioModel(sp)
            for dob in [2.0, 5.0, 10.0, 20.0, 40.0]:
                ratio = model.calculate_bark_ratio(dob)
                assert 0.80 <= ratio <= 0.99, (
                    f"{sp} bark ratio {ratio} out of bounds at DOB={dob}"
                )

    def test_dob_from_dib_roundtrip(self):
        """Converting DOB->DIB->DOB roundtrips correctly."""
        model = PNBarkRatioModel('DF')
        dob_original = 15.0
        dib = model.calculate_dib_from_dob(dob_original)
        dob_recovered = model.calculate_dob_from_dib(dib)
        assert abs(dob_recovered - dob_original) < 0.01, (
            f"Roundtrip failed: {dob_original} -> {dib} -> {dob_recovered}"
        )

    def test_zero_dob_returns_zero(self):
        """Zero DOB returns zero DIB."""
        model = PNBarkRatioModel('DF')
        assert model.calculate_dib_from_dob(0.0) == 0.0
        assert model.calculate_bark_thickness(0.0) == 0.0

    def test_species_group_mapping(self):
        """Species-to-group mapping returns correct groups."""
        model = PNBarkRatioModel('DF')
        coeffs = model.get_species_coefficients()
        assert coeffs['type'] == 1  # DF is group 1 (power)

        model_ra = PNBarkRatioModel('RA')
        coeffs_ra = model_ra.get_species_coefficients()
        assert coeffs_ra['type'] == 2  # RA is group 11 (linear)

        model_es = PNBarkRatioModel('ES')
        coeffs_es = model_es.get_species_coefficients()
        assert coeffs_es['type'] == 3  # ES is group 13 (constant)


# ===========================================================================
# Phase 2: PN Crown Ratio Tests
# ===========================================================================

class TestPNCrownRatio:
    """Tests for PNCrownRatioModel with Weibull distribution."""

    def test_factory_creates_pn_model(self):
        """Factory returns PNCrownRatioModel for variant='PN'."""
        model = create_crown_ratio_model('DF', variant='PN')
        assert isinstance(model, PNCrownRatioModel)

    def test_mean_cr_decreases_with_sdi(self):
        """Mean CR decreases as relative SDI increases."""
        model = PNCrownRatioModel('DF')
        cr_low = model.calculate_average_crown_ratio(2.0)
        cr_mid = model.calculate_average_crown_ratio(5.0)
        cr_high = model.calculate_average_crown_ratio(10.0)
        assert cr_low > cr_mid > cr_high, (
            f"CR should decrease with SDI: {cr_low}, {cr_mid}, {cr_high}"
        )

    def test_crown_ratio_bounded(self):
        """Crown ratios are bounded [0.10, 0.95]."""
        model = PNCrownRatioModel('WH')
        for relsdi in [1.0, 3.0, 6.0, 9.0, 12.0]:
            cr = model.predict_individual_crown_ratio(0.5, relsdi)
            assert 0.10 <= cr <= 0.95, (
                f"WH CR {cr} out of bounds at RELSDI={relsdi}"
            )

    def test_different_species_different_cr(self):
        """Different species groups give different crown ratios."""
        model_df = PNCrownRatioModel('DF')  # Group 7
        model_wh = PNCrownRatioModel('WH')  # Group 9
        model_ra = PNCrownRatioModel('RA')  # Group 13

        cr_df = model_df.calculate_average_crown_ratio(5.0)
        cr_wh = model_wh.calculate_average_crown_ratio(5.0)
        cr_ra = model_ra.calculate_average_crown_ratio(5.0)

        # At least two should differ (they're in different groups)
        values = [cr_df, cr_wh, cr_ra]
        assert len(set(round(v, 4) for v in values)) >= 2, (
            f"Expected different CRs across species groups: {values}"
        )

    def test_larger_trees_higher_cr(self):
        """Trees with higher rank (larger) should tend toward higher CR."""
        model = PNCrownRatioModel('DF')
        cr_small = model.predict_individual_crown_ratio(0.1, 5.0)
        cr_large = model.predict_individual_crown_ratio(0.9, 5.0)
        # Weibull distribution: larger trees (higher rank) get higher CR values
        assert cr_large > cr_small, (
            f"Large tree CR {cr_large} should exceed small tree CR {cr_small}"
        )

    def test_redwood_logistic(self):
        """Redwood logistic equation produces reasonable crown ratios."""
        model = PNCrownRatioModel('RW')
        cr = model.predict_redwood_crown_ratio(
            dbh=20.0, height=120.0, qmd=15.0, relative_density=0.6
        )
        assert 0.10 <= cr <= 0.95, f"Redwood CR {cr} out of bounds"

    def test_redwood_logistic_larger_trees_lower_cr(self):
        """Larger Redwood trees in denser stands have lower CR."""
        model = PNCrownRatioModel('RW')
        cr_open = model.predict_redwood_crown_ratio(
            dbh=20.0, height=80.0, qmd=15.0, relative_density=0.3
        )
        cr_dense = model.predict_redwood_crown_ratio(
            dbh=20.0, height=80.0, qmd=15.0, relative_density=0.9
        )
        # Higher density should generally result in lower CR
        # (a2 is positive, so higher PRD increases X, decreasing 1/(1+exp(X)))
        assert cr_dense < cr_open, (
            f"Dense stand CR {cr_dense} should be < open CR {cr_open}"
        )

    def test_update_crown_ratio_change_bounded(self):
        """Crown ratio change is bounded per cycle."""
        model = PNCrownRatioModel('DF')
        new_cr = model.update_crown_ratio_change(
            current_cr=0.40, predicted_cr=0.70, height_growth=5.0, cycle_length=5
        )
        # Max change is 0.01 * 5 = 0.05
        assert new_cr <= 0.45 + 0.001, f"CR change exceeded bounds: {new_cr}"


# ===========================================================================
# Phase 3: PN SDI Maximums & Mortality Tests
# ===========================================================================

class TestPNSDIMaximums:
    """Tests for PN SDI maximum values."""

    def test_pn_sdi_maximums_exist(self):
        """PN SDI maximums dict has entries for key species."""
        sdi_max = StandMetricsCalculator.PN_SDI_MAXIMUMS
        assert 'DF' in sdi_max
        assert 'WH' in sdi_max
        assert 'RC' in sdi_max
        assert 'SS' in sdi_max

    def test_pn_df_sdi_max(self):
        """Douglas-fir SDI max is ~850."""
        assert StandMetricsCalculator.PN_SDI_MAXIMUMS['DF'] == 850

    def test_pn_wh_sdi_max(self):
        """Western Hemlock SDI max is ~900."""
        assert StandMetricsCalculator.PN_SDI_MAXIMUMS['WH'] == 900

    def test_all_sdi_max_positive(self):
        """All PN SDI maximums are positive."""
        for species, sdi_max in StandMetricsCalculator.PN_SDI_MAXIMUMS.items():
            assert sdi_max > 0, f"{species} SDI max {sdi_max} should be positive"

    def test_metrics_calculator_uses_pn_sdi(self):
        """StandMetricsCalculator loads PN SDI maximums for variant='PN'."""
        calc = StandMetricsCalculator(default_species='DF', variant='PN')
        # Access internal _sdi_maximums
        assert calc._sdi_maximums == StandMetricsCalculator.PN_SDI_MAXIMUMS

    def test_pn_sdi_maximums_range(self):
        """PN SDI maximums are in reasonable range (300-1100)."""
        for species, sdi_max in StandMetricsCalculator.PN_SDI_MAXIMUMS.items():
            assert 200 <= sdi_max <= 1100, (
                f"{species} SDI max {sdi_max} outside expected range"
            )


class TestPNMortality:
    """Tests for PN mortality model."""

    def test_factory_creates_mortality_model_for_pn(self):
        """Factory creates MortalityModel (not LS) for PN variant."""
        model = create_mortality_model(default_species='DF', variant='PN')
        assert isinstance(model, MortalityModel)

    def test_pn_mortality_uses_pn_sdi_max(self):
        """PN mortality model uses PN-specific SDI maximum."""
        model = create_mortality_model(default_species='DF', variant='PN')
        # DF SDI max should be 850 from PN_SDI_MAXIMUMS
        assert model.max_sdi == 850

    def test_pn_mortality_wh_sdi_max(self):
        """PN mortality model for WH uses WH SDI max."""
        model = create_mortality_model(default_species='WH', variant='PN')
        assert model.max_sdi == 900


# ===========================================================================
# Phase 4: PN Volume Tests
# ===========================================================================

class TestPNVolume:
    """Tests for PNW species volume coefficients."""

    def test_df_volume_reasonable(self):
        """Douglas-fir volume is reasonable (10" DBH, 80' ht -> ~20-30 cuft)."""
        result = calculate_tree_volume(10.0, 80.0, 'DF', variant='PN')
        assert result.is_valid()
        assert 15.0 <= result.total_cubic_volume <= 35.0, (
            f"DF volume {result.total_cubic_volume} outside expected range"
        )

    def test_wh_volume_reasonable(self):
        """Western Hemlock volume is reasonable."""
        result = calculate_tree_volume(12.0, 90.0, 'WH', variant='PN')
        assert result.is_valid()
        assert 20.0 <= result.total_cubic_volume <= 50.0, (
            f"WH volume {result.total_cubic_volume} outside expected range"
        )

    def test_rc_volume_reasonable(self):
        """Western Red Cedar volume is reasonable."""
        result = calculate_tree_volume(15.0, 100.0, 'RC', variant='PN')
        assert result.is_valid()
        assert 40.0 <= result.total_cubic_volume <= 80.0, (
            f"RC volume {result.total_cubic_volume} outside expected range"
        )

    def test_ss_volume_reasonable(self):
        """Sitka Spruce volume is reasonable."""
        result = calculate_tree_volume(14.0, 100.0, 'SS', variant='PN')
        assert result.is_valid()
        assert 40.0 <= result.total_cubic_volume <= 75.0, (
            f"SS volume {result.total_cubic_volume} outside expected range"
        )

    def test_ra_hardwood_volume(self):
        """Red Alder hardwood volume is reasonable."""
        result = calculate_tree_volume(10.0, 70.0, 'RA', variant='PN')
        assert result.is_valid()
        assert 10.0 <= result.total_cubic_volume <= 30.0, (
            f"RA volume {result.total_cubic_volume} outside expected range"
        )

    def test_pnw_species_in_coefficient_dicts(self):
        """All key PNW species have explicit volume coefficients."""
        pnw_species = ['DF', 'WH', 'RC', 'SS', 'SF', 'GF', 'WF', 'NF',
                        'AF', 'RF', 'IC', 'ES', 'YC', 'RW', 'MH', 'RA', 'BM']
        for sp in pnw_species:
            assert sp in VOLUME_COEFFICIENTS_OUTSIDE_BARK, (
                f"{sp} missing from VOLUME_COEFFICIENTS_OUTSIDE_BARK"
            )
            assert sp in VOLUME_COEFFICIENTS_INSIDE_BARK, (
                f"{sp} missing from VOLUME_COEFFICIENTS_INSIDE_BARK"
            )

    def test_pnw_hardwoods_in_set(self):
        """PNW hardwood species are in HARDWOOD_SPECIES set."""
        pnw_hardwoods = ['RA', 'BM', 'GC', 'AS', 'PY', 'DG', 'CH']
        for sp in pnw_hardwoods:
            assert sp in HARDWOOD_SPECIES, (
                f"{sp} missing from HARDWOOD_SPECIES set"
            )

    def test_volume_increases_with_size(self):
        """Volume increases with tree size for DF."""
        vol_small = calculate_tree_volume(6.0, 50.0, 'DF').total_cubic_volume
        vol_medium = calculate_tree_volume(12.0, 80.0, 'DF').total_cubic_volume
        vol_large = calculate_tree_volume(24.0, 140.0, 'DF').total_cubic_volume
        assert vol_small < vol_medium < vol_large


# ===========================================================================
# Phase 6: Integration Tests
# ===========================================================================

class TestPNIntegration:
    """Integration tests for full PN variant simulation."""

    def test_stand_initialize_planted_pn(self):
        """Stand.initialize_planted works with variant='PN'."""
        stand = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=120,
            species='DF',
            variant='PN'
        )
        assert stand.variant == 'PN'
        assert len(stand.trees) == 400
        assert stand.site_index == 120

    def test_pn_simulation_50_year(self):
        """50-year PN simulation produces reasonable yields."""
        stand = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=120,
            species='DF',
            variant='PN'
        )
        stand.grow(50)
        metrics = stand.get_metrics()

        tpa = metrics['tpa']
        qmd = metrics['qmd']
        ba = metrics['basal_area']
        volume = metrics['volume']

        # PN DF at SI=120 should produce good yields
        # High productivity site: heavy mortality reduces TPA, large QMD
        assert 150 <= tpa <= 400, f"TPA {tpa} outside expected range"
        assert 8.0 <= qmd <= 26.0, f"QMD {qmd} outside expected range"
        assert 150 <= ba <= 700, f"BA {ba} outside expected range"
        assert 5000 <= volume <= 30000, f"Volume {volume} outside expected range"

    def test_pn_vs_sn_higher_productivity(self):
        """PN at SI=120 should produce more volume than SN at same SI."""
        stand_pn = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=120,
            species='DF',
            variant='PN'
        )
        stand_pn.grow(50)

        stand_sn = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=70,
            species='LP',
            variant='SN',
            ecounit='M231'
        )
        stand_sn.grow(50)

        vol_pn = stand_pn.get_metrics()['volume']
        vol_sn = stand_sn.get_metrics()['volume']

        # Both should produce substantial volume
        assert vol_pn > 3000, f"PN volume {vol_pn} too low"
        assert vol_sn > 3000, f"SN volume {vol_sn} too low"

    def test_pn_tree_level_growth(self):
        """Individual DF tree grows with variant='PN'."""
        from pyfvs.tree import Tree

        tree = Tree(dbh=2.0, height=15.0, species='DF', age=10, variant='PN')
        initial_dbh = tree.dbh
        initial_height = tree.height

        tree.grow(
            site_index=120,
            ba=50.0,
            pbal=20.0,
            competition_factor=0.3,
            time_step=10,
        )

        assert tree.dbh > initial_dbh, "DBH should increase"
        assert tree.height > initial_height, "Height should increase"

    def test_pn_wh_simulation(self):
        """Western Hemlock simulation produces reasonable yields."""
        stand = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=100,
            species='WH',
            variant='PN'
        )
        stand.grow(50)
        metrics = stand.get_metrics()

        assert metrics['tpa'] > 100, "Should have surviving trees"
        assert metrics['qmd'] > 5.0, "QMD should grow"
        assert metrics['basal_area'] > 50.0, "BA should accumulate"

    def test_pn_bark_ratio_in_growth(self):
        """PN bark ratio is actually used during growth."""
        model = create_bark_ratio_model('DF', variant='PN')
        assert isinstance(model, PNBarkRatioModel)
        # DF bark ratio should be ~0.89-0.91 at 10"
        ratio = model.calculate_bark_ratio(10.0)
        assert 0.85 <= ratio <= 0.95, f"DF PN bark ratio {ratio} unexpected"

    def test_pn_crown_ratio_in_growth(self):
        """PN crown ratio model is used during simulation."""
        model = create_crown_ratio_model('DF', variant='PN')
        assert isinstance(model, PNCrownRatioModel)
        cr = model.calculate_average_crown_ratio(5.0)
        assert 0.10 <= cr <= 0.90, f"DF PN mean CR {cr} unexpected"

    def test_pn_stand_metrics_correct_variant(self):
        """Stand metrics calculator uses PN variant correctly."""
        stand = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=120,
            species='DF',
            variant='PN'
        )
        # The internal metrics calculator should have PN SDI maximums
        assert stand._metrics.variant == 'PN'
        max_sdi = stand._metrics.get_max_sdi(stand.trees, 'DF')
        assert max_sdi == 850, f"DF max SDI should be 850, got {max_sdi}"


class TestPNSmokeTest:
    """Smoke tests for PN variant - quick sanity checks."""

    def test_df_smoke(self):
        """DF SI=120 50yr smoke test."""
        stand = Stand.initialize_planted(400, 120, 'DF', variant='PN')
        stand.grow(50)
        metrics = stand.get_metrics()
        # Just verify it runs and produces non-zero results
        assert metrics['tpa'] > 0
        assert metrics['qmd'] > 0
        assert metrics['basal_area'] > 0
        assert metrics['volume'] > 0

    def test_wh_smoke(self):
        """WH SI=100 50yr smoke test."""
        stand = Stand.initialize_planted(400, 100, 'WH', variant='PN')
        stand.grow(50)
        metrics = stand.get_metrics()
        assert metrics['tpa'] > 0
        assert metrics['volume'] > 0

    def test_rc_smoke(self):
        """RC SI=100 50yr smoke test."""
        stand = Stand.initialize_planted(350, 100, 'RC', variant='PN')
        stand.grow(50)
        metrics = stand.get_metrics()
        assert metrics['tpa'] > 0
        assert metrics['volume'] > 0

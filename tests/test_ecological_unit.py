"""Tests for the ecological unit classification system.

Tests table selection, M231 vs 232 growth effect magnitude,
unknown ecounit handling, and integration with stand growth.
"""
import pytest

from pyfvs.ecological_unit import (
    EcologicalUnitClassifier,
    get_ecounit_effect,
    select_ecounit_table,
    MOUNTAIN_PROVINCE_ECOUNITS,
    LOWLAND_ECOUNITS,
)
from pyfvs import Stand


class TestTableSelection:
    """Table selection — mountain vs lowland ecounits."""

    def test_mountain_ecounit_selects_table_5(self):
        """Mountain province ecounits should select table 4.7.1.5."""
        for ecounit in ['M221', 'M222', 'M231', '221', '222', '231T']:
            table = select_ecounit_table(ecounit)
            assert table == 'table_4_7_1_5', f"{ecounit} should be table 5"

    def test_lowland_ecounit_selects_table_6(self):
        """Lowland ecounits should select table 4.7.1.6."""
        for ecounit in ['231L', '232', '234', '255', '411']:
            table = select_ecounit_table(ecounit)
            assert table == 'table_4_7_1_6', f"{ecounit} should be table 6"

    def test_unknown_ecounit_defaults_to_table_5(self):
        """Unknown ecounit should default to mountain table (broader coverage)."""
        table = select_ecounit_table('UNKNOWN')
        assert table == 'table_4_7_1_5'

    def test_case_insensitive(self):
        """Table selection should be case-insensitive."""
        table_upper = select_ecounit_table('M231')
        table_lower = select_ecounit_table('m231')
        assert table_upper == table_lower


class TestEcounitEffectMagnitude:
    """M231 vs 232 growth effect magnitude."""

    def test_m231_positive_effect_lp(self):
        """M231 should have a significant positive effect on LP growth."""
        effect = get_ecounit_effect('LP', 'M231')
        assert effect > 0.5, f"M231 LP effect={effect}, expected > 0.5"

    def test_232_near_zero_effect(self):
        """232 (base lowland) should have near-zero effect."""
        effect = get_ecounit_effect('LP', '232')
        # 232 is typically the base ecounit
        assert abs(effect) < 0.5

    def test_m231_larger_than_232(self):
        """M231 growth effect should be larger than 232."""
        m231_effect = get_ecounit_effect('LP', 'M231')
        e232_effect = get_ecounit_effect('LP', '232')
        assert m231_effect > e232_effect

    def test_231t_is_base_ecounit(self):
        """231T should be the base ecounit (effect near 0)."""
        effect = get_ecounit_effect('LP', '231T')
        assert abs(effect) < 0.2


class TestUnknownEcounit:
    """Unknown ecounit → zero effect."""

    def test_unknown_ecounit_zero_effect(self):
        """Unknown ecounit should return zero growth effect."""
        effect = get_ecounit_effect('LP', 'ZZZZZ')
        assert effect == 0.0

    def test_unknown_species_zero_effect(self):
        """Unknown species should return zero growth effect."""
        effect = get_ecounit_effect('ZZ', 'M231')
        assert effect == 0.0


class TestEcologicalUnitClassifier:
    """Classifier class tests."""

    def test_classifier_creation(self):
        """Classifier should be creatable."""
        classifier = EcologicalUnitClassifier()
        assert classifier is not None

    def test_get_coefficient(self):
        """Should return a float coefficient."""
        classifier = EcologicalUnitClassifier()
        coeff = classifier.get_coefficient('LP', 'M231')
        assert isinstance(coeff, (int, float))

    def test_available_species(self):
        """Should report available species."""
        classifier = EcologicalUnitClassifier()
        species_5 = classifier.get_available_species('table_4_7_1_5')
        assert len(species_5) > 0

    def test_all_coefficients_for_species(self):
        """Should return coefficients for all ecounits for a species."""
        classifier = EcologicalUnitClassifier()
        coeffs = classifier.get_all_coefficients_for_species('LP')
        assert isinstance(coeffs, dict)
        assert len(coeffs) > 0


class TestEcounitIntegration:
    """Integration: M231 stand grows more than 232."""

    def test_m231_stand_grows_faster(self):
        """Stand at M231 should grow faster (more BA) than at 232."""
        stand_m231 = Stand.initialize_planted(
            300, 70, 'LP', variant='SN', ecounit='M231', stochastic=False
        )
        stand_232 = Stand.initialize_planted(
            300, 70, 'LP', variant='SN', ecounit='232', stochastic=False
        )
        stand_m231.grow(25)
        stand_232.grow(25)

        metrics_m231 = stand_m231.get_metrics()
        metrics_232 = stand_232.get_metrics()

        assert metrics_m231['basal_area'] > metrics_232['basal_area'], (
            f"M231 BA={metrics_m231['basal_area']:.1f} should be > "
            f"232 BA={metrics_232['basal_area']:.1f}"
        )

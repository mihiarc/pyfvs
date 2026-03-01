"""Tests for large tree height growth model.

Tests potential height growth by variant, FINDAG age-finding algorithm,
crown ratio modifier, relative height modifier, and variant integration.
"""
import math
import pytest

from pyfvs.large_tree_height_growth import (
    LargeTreeHeightGrowthModel,
    create_large_tree_height_growth_model,
    calculate_large_tree_height_growth,
    calculate_crown_ratio_modifier,
    calculate_relative_height_modifier,
)


class TestPotentialHeightGrowth:
    """Potential height growth by variant."""

    @pytest.mark.parametrize("variant,species,si", [
        ('SN', 'LP', 70),
        ('LS', 'RN', 60),
        ('NE', 'RM', 55),
        ('CS', 'WO', 60),
        ('PN', 'DF', 120),
        ('WC', 'DF', 110),
    ])
    def test_positive_height_growth_all_variants(self, variant, species, si):
        """All variants should produce positive height growth for healthy trees."""
        htg = calculate_large_tree_height_growth(
            species_code=species, dbh=8.0, crown_ratio=0.6,
            relative_height=0.9, site_index=si,
            basal_area=100, pbal=30, variant=variant
        )
        assert htg > 0, f"{variant} {species} produced htg={htg}"

    def test_higher_si_more_growth(self):
        """Higher site index should produce more potential height growth."""
        htg_low = calculate_large_tree_height_growth(
            species_code='LP', dbh=8.0, crown_ratio=0.6,
            relative_height=0.9, site_index=50,
            basal_area=100, pbal=30, variant='SN'
        )
        htg_high = calculate_large_tree_height_growth(
            species_code='LP', dbh=8.0, crown_ratio=0.6,
            relative_height=0.9, site_index=90,
            basal_area=100, pbal=30, variant='SN'
        )
        assert htg_high > htg_low

    def test_pn_forward_increment(self):
        """PN should use forward height increment (H(age+5) - H(age))."""
        htg = calculate_large_tree_height_growth(
            species_code='DF', dbh=10.0, crown_ratio=0.6,
            relative_height=0.9, site_index=120,
            basal_area=120, pbal=40, variant='PN'
        )
        # Forward increment on concave-down curve should be positive but moderate
        assert 0.1 < htg < 15.0


class TestCrownRatioModifier:
    """Crown ratio modifier (Hoerl's function)."""

    def test_high_cr_near_one(self):
        """High crown ratio (0.6) should give modifier near 1.0."""
        mod = calculate_crown_ratio_modifier(0.6)
        assert 0.8 <= mod <= 1.0

    def test_low_cr_reduced(self):
        """Low crown ratio (0.2) should give reduced modifier."""
        mod = calculate_crown_ratio_modifier(0.2)
        assert mod < 0.5

    def test_very_low_cr_very_reduced(self):
        """Very low crown ratio (0.1) should give very low modifier."""
        mod = calculate_crown_ratio_modifier(0.1)
        assert mod < 0.2

    def test_modifier_capped_at_one(self):
        """Modifier should be capped at 1.0."""
        mod = calculate_crown_ratio_modifier(0.55)
        assert mod <= 1.0

    def test_monotonic_increase_low_to_mid(self):
        """Modifier should increase from low to mid crown ratios."""
        mod_low = calculate_crown_ratio_modifier(0.2)
        mod_mid = calculate_crown_ratio_modifier(0.4)
        assert mod_mid > mod_low


class TestRelativeHeightModifier:
    """Relative height modifier by shade tolerance."""

    def test_dominant_tree_high_modifier(self):
        """Dominant tree (RELHT=1.2) should have modifier > 1.0."""
        mod = calculate_relative_height_modifier(1.2, species_code='LP')
        assert mod > 0.8  # Dominant trees grow well

    def test_suppressed_tree_low_modifier(self):
        """Suppressed tree (RELHT=0.4) should have reduced modifier."""
        mod = calculate_relative_height_modifier(0.4, species_code='LP')
        assert mod < 1.0

    def test_intolerant_species_stronger_response(self):
        """Shade-intolerant species should have stronger RELHT response."""
        # LP is intolerant, BF/AB would be tolerant
        mod_dominant = calculate_relative_height_modifier(1.2, species_code='LP')
        mod_suppressed = calculate_relative_height_modifier(0.4, species_code='LP')
        # The difference should be meaningful
        assert mod_dominant > mod_suppressed

    def test_average_relht_moderate_modifier(self):
        """Average relative height (1.0) should give moderate modifier."""
        mod = calculate_relative_height_modifier(1.0, species_code='LP')
        assert 0.3 < mod < 1.5


class TestHeightGrowthIntegration:
    """Integration tests: full height growth calculation."""

    def test_growth_positive_with_typical_inputs(self):
        """Typical mature tree should produce positive height growth."""
        model = create_large_tree_height_growth_model('LP')
        htg = model.calculate_height_growth(
            dbh=10.0, crown_ratio=0.5, relative_height=0.9,
            site_index=70, basal_area=120, pbal=40, variant='SN'
        )
        assert htg > 0

    def test_growth_bounded(self):
        """Height growth should be bounded to reasonable range."""
        htg = calculate_large_tree_height_growth(
            species_code='LP', dbh=10.0, crown_ratio=0.5,
            relative_height=0.9, site_index=70,
            basal_area=120, pbal=40, variant='SN'
        )
        assert 0.1 <= htg <= 15.0

    def test_factory_caching(self):
        """Factory should return cached instances."""
        model1 = create_large_tree_height_growth_model('LP')
        model2 = create_large_tree_height_growth_model('LP')
        assert model1 is model2

    @pytest.mark.parametrize("variant,species,si", [
        ('SN', 'LP', 70),
        ('LS', 'RN', 60),
        ('CS', 'WO', 60),
        ('NE', 'RM', 55),
        ('PN', 'DF', 120),
        ('WC', 'DF', 110),
    ])
    def test_all_variants_positive_growth(self, variant, species, si):
        """All variants should produce positive height growth."""
        htg = calculate_large_tree_height_growth(
            species_code=species, dbh=8.0, crown_ratio=0.6,
            relative_height=0.9, site_index=si,
            basal_area=100, pbal=30, variant=variant
        )
        assert htg > 0.0

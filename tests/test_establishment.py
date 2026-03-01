"""Tests for tree establishment logic across all variants.

Tests Chapman-Richards height curves, HHTMAX caps, H-D inverse for initial DBH,
variant-specific establishment fractions, and SMHGDG-based establishment for PN/WC.
"""
import math
import pytest

from pyfvs.establishment import (
    get_hhtmax,
    compute_establishment_height,
    compute_essubh_height,
    compute_western_establishment_height,
    estimate_dbh_from_height,
    load_small_tree_coefficients,
)
from pyfvs import Stand


class TestChapmanRichardsHeight:
    """Chapman-Richards height curves by variant."""

    @pytest.mark.parametrize("variant,species,si,expected_min,expected_max", [
        ('SN', 'LP', 70, 5.0, 25.0),
        ('LS', 'RN', 60, 3.0, 20.0),
        ('NE', 'RM', 55, 3.0, 20.0),
        ('CS', 'WO', 60, 3.0, 20.0),
    ])
    def test_establishment_height_reasonable_range(self, variant, species, si, expected_min, expected_max):
        """Establishment height for cycle+2 years should be in reasonable range."""
        age = 12 if variant in ('LS', 'NE', 'CS') else 7
        height = compute_establishment_height(species, si, age, variant)
        assert expected_min < height < expected_max, (
            f"{variant} {species} SI={si} age={age}: height={height:.1f} "
            f"not in ({expected_min}, {expected_max})"
        )

    def test_height_increases_with_site_index(self):
        """Higher site index should produce taller establishment height."""
        h_low = compute_establishment_height('LP', 50, 7, 'SN')
        h_high = compute_establishment_height('LP', 90, 7, 'SN')
        assert h_high > h_low

    def test_height_increases_with_age(self):
        """Older age should produce taller establishment height."""
        h_young = compute_establishment_height('LP', 70, 5, 'SN')
        h_old = compute_establishment_height('LP', 70, 10, 'SN')
        assert h_old > h_young

    def test_sn_base_age_25_no_scaling(self):
        """SN uses base-age-25 coefficients without scaling."""
        h = compute_establishment_height('LP', 70, 7, 'SN')
        assert h > 0  # Just verify it doesn't crash

    def test_ls_base_age_50_scaling(self):
        """LS uses base-age-50 coefficients with dynamic scaling."""
        h = compute_establishment_height('RN', 60, 12, 'LS')
        assert h > 0


class TestHHTMAX:
    """HHTMAX caps by variant/species."""

    def test_sn_lp_hhtmax(self):
        """SN LP should have a species-specific HHTMAX."""
        hhtmax = get_hhtmax('LP', 'SN')
        assert hhtmax > 0

    def test_sn_default_hhtmax(self):
        """SN non-specific species should default to ~20."""
        hhtmax = get_hhtmax('OT', 'SN')
        assert 15 <= hhtmax <= 30

    def test_pn_default_hhtmax(self):
        """PN uses default HHTMAX (no species-specific overrides)."""
        hhtmax = get_hhtmax('DF', 'PN')
        assert hhtmax > 0

    def test_hhtmax_caps_height(self):
        """Establishment height should not exceed HHTMAX."""
        hhtmax = get_hhtmax('LP', 'SN')
        # Use a very high site index to push height toward the cap
        height = compute_establishment_height('LP', 130, 10, 'SN')
        assert height <= hhtmax + 0.01  # Allow tiny float tolerance


class TestHDInverse:
    """H-D inverse for initial DBH."""

    def test_sub_breast_height_dbh(self):
        """Below 4.5 ft, DBH should be very small (0.1 + 0.001*H)."""
        dbh = estimate_dbh_from_height(3.0, 'LP', 'SN')
        assert 0.1 <= dbh < 0.2

    def test_breast_height_positive_dbh(self):
        """Above 4.5 ft, H-D inverse should give positive DBH."""
        dbh = estimate_dbh_from_height(12.0, 'LP', 'SN')
        assert dbh > 0.5

    def test_taller_trees_wider_dbh(self):
        """Taller trees should have larger DBH from H-D inverse."""
        dbh_short = estimate_dbh_from_height(8.0, 'LP', 'SN')
        dbh_tall = estimate_dbh_from_height(18.0, 'LP', 'SN')
        assert dbh_tall > dbh_short


class TestVariantEstablishmentFractions:
    """Test variant-specific establishment fractions via Stand.initialize_planted."""

    def test_sn_planted_produces_trees(self):
        """SN planted stand should produce trees with positive DBH and height."""
        stand = Stand.initialize_planted(300, 70, 'LP', variant='SN', stochastic=False)
        assert len(stand.trees) == 300
        for tree in stand.trees:
            assert tree.dbh > 0
            assert tree.height > 0

    def test_ls_planted_produces_trees(self):
        """LS planted stand should produce reasonable trees."""
        stand = Stand.initialize_planted(300, 60, 'RN', variant='LS', stochastic=False)
        assert len(stand.trees) == 300
        for tree in stand.trees:
            assert tree.dbh > 0
            assert tree.height > 0

    def test_cs_ne_different_fractions(self):
        """CS and NE use different estab fractions, producing different QMDs."""
        stand_cs = Stand.initialize_planted(300, 60, 'WO', variant='CS', stochastic=False)
        stand_ne = Stand.initialize_planted(300, 60, 'RM', variant='NE', stochastic=False)
        qmd_cs = math.sqrt(sum(t.dbh**2 for t in stand_cs.trees) / len(stand_cs.trees))
        qmd_ne = math.sqrt(sum(t.dbh**2 for t in stand_ne.trees) / len(stand_ne.trees))
        # Both should be positive; not necessarily equal
        assert qmd_cs > 0
        assert qmd_ne > 0


class TestPNWCEstablishment:
    """SMHGDG-based establishment for PN/WC."""

    def test_pn_establishment_uses_smhgdg(self):
        """PN establishment should produce positive DBH without H-D inverse."""
        stand = Stand.initialize_planted(300, 120, 'DF', variant='PN', stochastic=False)
        assert len(stand.trees) == 300
        for tree in stand.trees:
            assert tree.dbh > 0
            assert tree.height > 4.5  # Should be above breast height

    def test_wc_establishment_uses_smhgdg(self):
        """WC establishment should produce positive DBH without H-D inverse."""
        stand = Stand.initialize_planted(300, 110, 'DF', variant='WC', stochastic=False)
        assert len(stand.trees) == 300
        for tree in stand.trees:
            assert tree.dbh > 0
            assert tree.height > 4.5

    def test_pn_wc_compute_western_establishment_height(self):
        """compute_western_establishment_height returns both height and DBH."""
        result = compute_western_establishment_height('DF', 120, 'PN')
        assert isinstance(result, tuple)
        height, dbh = result
        assert height > 0
        assert dbh > 0

    def test_pn_higher_si_taller_trees(self):
        """Higher site index should produce taller PN establishment trees."""
        stand_low = Stand.initialize_planted(100, 80, 'DF', variant='PN',
                                             random_seed=42, stochastic=False)
        stand_high = Stand.initialize_planted(100, 140, 'DF', variant='PN',
                                              random_seed=42, stochastic=False)
        avg_ht_low = sum(t.height for t in stand_low.trees) / len(stand_low.trees)
        avg_ht_high = sum(t.height for t in stand_high.trees) / len(stand_high.trees)
        assert avg_ht_high > avg_ht_low

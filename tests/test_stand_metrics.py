"""
Tests for StandMetricsCalculator.

These tests verify that the extracted metrics calculations produce
identical results to the original Stand class methods.
"""
import pytest
import math
from pyfvs.stand_metrics import (
    StandMetricsCalculator,
    get_metrics_calculator,
    calculate_stand_ccf,
    calculate_stand_sdi,
    calculate_stand_basal_area
)
from pyfvs.tree import Tree


class TestStandMetricsCalculator:
    """Tests for StandMetricsCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Create a metrics calculator instance."""
        return StandMetricsCalculator(default_species='LP')

    @pytest.fixture
    def sample_trees(self):
        """Create a sample list of trees for testing."""
        trees = []
        for i in range(10):
            dbh = 4.0 + i * 0.5  # DBH from 4.0 to 8.5 inches
            height = 30.0 + i * 3.0  # Heights from 30 to 57 feet
            tree = Tree(dbh=dbh, height=height, species='LP', age=15)
            trees.append(tree)
        return trees

    @pytest.fixture
    def mixed_species_trees(self):
        """Create trees with mixed species."""
        trees = []
        species_list = ['LP', 'LP', 'SP', 'SP', 'SA']
        for i, species in enumerate(species_list):
            dbh = 5.0 + i * 1.0
            height = 35.0 + i * 5.0
            tree = Tree(dbh=dbh, height=height, species=species, age=20)
            trees.append(tree)
        return trees

    def test_init(self, calculator):
        """Test calculator initialization."""
        assert calculator.default_species == 'LP'
        assert StandMetricsCalculator._sdi_loaded is True
        assert StandMetricsCalculator._sdi_maximums is not None

    def test_calculate_qmd(self, calculator, sample_trees):
        """Test QMD calculation."""
        qmd = calculator.calculate_qmd(sample_trees)

        # Manual calculation
        sum_dbh_squared = sum(t.dbh ** 2 for t in sample_trees)
        expected_qmd = math.sqrt(sum_dbh_squared / len(sample_trees))

        assert abs(qmd - expected_qmd) < 0.001

    def test_calculate_qmd_empty(self, calculator):
        """Test QMD with empty tree list."""
        qmd = calculator.calculate_qmd([])
        assert qmd == 0.0

    def test_calculate_basal_area(self, calculator, sample_trees):
        """Test basal area calculation."""
        ba = calculator.calculate_basal_area(sample_trees)

        # Manual calculation
        expected_ba = sum(math.pi * (t.dbh / 24.0) ** 2 for t in sample_trees)

        assert abs(ba - expected_ba) < 0.001

    def test_calculate_basal_area_empty(self, calculator):
        """Test basal area with empty tree list."""
        ba = calculator.calculate_basal_area([])
        assert ba == 0.0

    def test_calculate_sdi(self, calculator, sample_trees):
        """Test SDI calculation using Reineke's equation."""
        sdi = calculator.calculate_sdi(sample_trees)

        # Manual calculation
        tpa = len(sample_trees)
        sum_dbh_squared = sum(t.dbh ** 2 for t in sample_trees)
        qmd = math.sqrt(sum_dbh_squared / len(sample_trees))
        expected_sdi = tpa * ((qmd / 10.0) ** 1.605)

        assert abs(sdi - expected_sdi) < 0.01

    def test_calculate_sdi_empty(self, calculator):
        """Test SDI with empty tree list."""
        sdi = calculator.calculate_sdi([])
        assert sdi == 0.0

    def test_calculate_top_height(self, calculator, sample_trees):
        """Test top height calculation."""
        top_height = calculator.calculate_top_height(sample_trees)

        # With 10 trees, should average all heights
        expected = sum(t.height for t in sample_trees) / len(sample_trees)
        assert abs(top_height - expected) < 0.001

    def test_calculate_top_height_40_largest(self, calculator):
        """Test that top height uses 40 largest trees."""
        # Create 50 trees with varying heights
        trees = []
        for i in range(50):
            dbh = 4.0 + i * 0.1
            height = 30.0 + i * 0.5  # Heights increase with DBH
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=20))

        top_height = calculator.calculate_top_height(trees, n_trees=40)

        # Should be average of 40 largest (by DBH), which are the last 40 trees
        expected = sum(t.height for t in trees[10:]) / 40
        assert abs(top_height - expected) < 0.001

    def test_calculate_top_height_empty(self, calculator):
        """Test top height with empty tree list."""
        top_height = calculator.calculate_top_height([])
        assert top_height == 0.0

    def test_calculate_ccf(self, calculator, sample_trees):
        """Test CCF calculation."""
        ccf = calculator.calculate_ccf(sample_trees)

        # CCF should be positive for trees with DBH > 0.1
        assert ccf > 0.0

        # Larger trees contribute more to CCF
        small_tree = Tree(dbh=2.0, height=20.0, species='LP', age=10)
        large_tree = Tree(dbh=10.0, height=60.0, species='LP', age=30)

        small_ccf = calculator.calculate_ccf([small_tree])
        large_ccf = calculator.calculate_ccf([large_tree])

        assert large_ccf > small_ccf

    def test_calculate_ccf_small_trees(self, calculator):
        """Test CCF for very small trees."""
        small_trees = [Tree(dbh=0.05, height=4.5, species='LP', age=1) for _ in range(10)]
        ccf = calculator.calculate_ccf(small_trees)

        # Should use small tree CCF constant (0.001 per tree)
        expected = 0.001 * 10
        assert abs(ccf - expected) < 0.0001

    def test_calculate_ccf_empty(self, calculator):
        """Test CCF with empty tree list."""
        ccf = calculator.calculate_ccf([])
        assert ccf == 0.0

    def test_calculate_relsdi(self, calculator, sample_trees):
        """Test RELSDI calculation."""
        relsdi = calculator.calculate_relsdi(sample_trees, species='LP')

        # RELSDI should be bounded 1.0-12.0
        assert 1.0 <= relsdi <= 12.0

    def test_calculate_relsdi_bounds(self, calculator):
        """Test RELSDI is properly bounded."""
        # Very sparse stand should have RELSDI near 1.0
        sparse_trees = [Tree(dbh=2.0, height=20.0, species='LP', age=10)]
        relsdi_sparse = calculator.calculate_relsdi(sparse_trees, species='LP')
        assert relsdi_sparse >= 1.0

        # Very dense stand should not exceed 12.0
        dense_trees = [Tree(dbh=12.0, height=80.0, species='LP', age=40) for _ in range(1000)]
        relsdi_dense = calculator.calculate_relsdi(dense_trees, species='LP')
        assert relsdi_dense <= 12.0

    def test_calculate_relsdi_empty(self, calculator):
        """Test RELSDI with empty tree list."""
        relsdi = calculator.calculate_relsdi([])
        assert relsdi == 1.0

    def test_get_max_sdi_single_species(self, calculator, sample_trees):
        """Test max SDI for single species stand."""
        max_sdi = calculator.get_max_sdi(sample_trees, default_species='LP')

        # All LP trees should give LP's max SDI
        lp_max = StandMetricsCalculator._sdi_maximums.get('LP', 480)
        assert abs(max_sdi - lp_max) < 0.01

    def test_get_max_sdi_mixed_species(self, calculator, mixed_species_trees):
        """Test max SDI for mixed species stand."""
        max_sdi = calculator.get_max_sdi(mixed_species_trees, default_species='LP')

        # Should be weighted average based on basal area
        assert max_sdi > 0

    def test_get_max_sdi_empty(self, calculator):
        """Test max SDI with empty tree list."""
        max_sdi = calculator.get_max_sdi([], default_species='LP')
        lp_max = StandMetricsCalculator._sdi_maximums.get('LP', 480)
        assert abs(max_sdi - lp_max) < 0.01

    def test_calculate_pbal(self, calculator, sample_trees):
        """Test PBAL calculation."""
        target_tree = sample_trees[0]  # Smallest tree
        pbal = calculator.calculate_pbal(sample_trees, target_tree)

        # PBAL should be sum of BA for trees larger than target
        expected_pbal = sum(
            math.pi * (t.dbh / 24.0) ** 2
            for t in sample_trees
            if t.dbh > target_tree.dbh
        )
        assert abs(pbal - expected_pbal) < 0.001

    def test_calculate_pbal_largest_tree(self, calculator, sample_trees):
        """Test PBAL for the largest tree (should be 0)."""
        largest_tree = max(sample_trees, key=lambda t: t.dbh)
        pbal = calculator.calculate_pbal(sample_trees, largest_tree)
        assert pbal == 0.0

    def test_calculate_all_metrics(self, calculator, sample_trees):
        """Test calculate_all_metrics returns all expected keys."""
        metrics = calculator.calculate_all_metrics(sample_trees)

        expected_keys = {'tpa', 'ba', 'qmd', 'top_height', 'ccf', 'sdi', 'max_sdi', 'relsdi'}
        assert set(metrics.keys()) == expected_keys

        # All values should be positive for non-empty stand
        assert metrics['tpa'] == len(sample_trees)
        assert metrics['ba'] > 0
        assert metrics['qmd'] > 0
        assert metrics['top_height'] > 0
        assert metrics['ccf'] > 0
        assert metrics['sdi'] > 0
        assert metrics['max_sdi'] > 0
        assert 1.0 <= metrics['relsdi'] <= 12.0

    def test_calculate_all_metrics_empty(self, calculator):
        """Test calculate_all_metrics with empty tree list."""
        metrics = calculator.calculate_all_metrics([])

        assert metrics['tpa'] == 0
        assert metrics['ba'] == 0.0
        assert metrics['qmd'] == 0.0
        assert metrics['top_height'] == 0.0
        assert metrics['ccf'] == 0.0
        assert metrics['sdi'] == 0.0
        assert metrics['max_sdi'] > 0  # Uses default species
        assert metrics['relsdi'] == 1.0


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture
    def sample_trees(self):
        """Create sample trees."""
        return [Tree(dbh=6.0, height=40.0, species='LP', age=15) for _ in range(5)]

    def test_get_metrics_calculator(self):
        """Test get_metrics_calculator returns singleton."""
        calc1 = get_metrics_calculator()
        calc2 = get_metrics_calculator()
        assert calc1 is calc2

    def test_calculate_stand_ccf(self, sample_trees):
        """Test convenience function for CCF."""
        ccf = calculate_stand_ccf(sample_trees)
        assert ccf > 0

    def test_calculate_stand_sdi(self, sample_trees):
        """Test convenience function for SDI."""
        sdi = calculate_stand_sdi(sample_trees)
        assert sdi > 0

    def test_calculate_stand_basal_area(self, sample_trees):
        """Test convenience function for basal area."""
        ba = calculate_stand_basal_area(sample_trees)
        expected = sum(math.pi * (t.dbh / 24.0) ** 2 for t in sample_trees)
        assert abs(ba - expected) < 0.001


class TestMetricsEquivalence:
    """Tests to verify metrics match original Stand class calculations."""

    @pytest.fixture
    def trees_and_stand(self):
        """Create trees and a Stand for comparison testing."""
        from pyfvs.stand import Stand

        trees = []
        for i in range(20):
            dbh = 3.0 + i * 0.5
            height = 25.0 + i * 2.5
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=15))

        stand = Stand(trees=trees, site_index=70, species='LP')
        calculator = StandMetricsCalculator(default_species='LP')

        return trees, stand, calculator

    def test_qmd_equivalence(self, trees_and_stand):
        """Test that QMD matches Stand.calculate_qmd()."""
        trees, stand, calculator = trees_and_stand

        stand_qmd = stand.calculate_qmd()
        calc_qmd = calculator.calculate_qmd(trees)

        assert abs(stand_qmd - calc_qmd) < 0.0001

    def test_basal_area_equivalence(self, trees_and_stand):
        """Test that BA matches Stand.calculate_basal_area()."""
        trees, stand, calculator = trees_and_stand

        stand_ba = stand.calculate_basal_area()
        calc_ba = calculator.calculate_basal_area(trees)

        assert abs(stand_ba - calc_ba) < 0.0001

    def test_sdi_equivalence(self, trees_and_stand):
        """Test that SDI matches Stand.calculate_stand_sdi()."""
        trees, stand, calculator = trees_and_stand

        stand_sdi = stand.calculate_stand_sdi()
        calc_sdi = calculator.calculate_sdi(trees)

        assert abs(stand_sdi - calc_sdi) < 0.01

    def test_relsdi_equivalence(self, trees_and_stand):
        """Test that RELSDI matches Stand.calculate_relsdi()."""
        trees, stand, calculator = trees_and_stand

        stand_relsdi = stand.calculate_relsdi()
        calc_relsdi = calculator.calculate_relsdi(trees, species='LP')

        assert abs(stand_relsdi - calc_relsdi) < 0.01

    def test_top_height_equivalence(self, trees_and_stand):
        """Test that top height matches Stand.calculate_top_height()."""
        trees, stand, calculator = trees_and_stand

        stand_top_ht = stand.calculate_top_height()
        calc_top_ht = calculator.calculate_top_height(trees)

        assert abs(stand_top_ht - calc_top_ht) < 0.01

    def test_ccf_equivalence(self, trees_and_stand):
        """Test that CCF matches Stand.calculate_ccf_official()."""
        trees, stand, calculator = trees_and_stand

        stand_ccf = stand.calculate_ccf_official()
        calc_ccf = calculator.calculate_ccf(trees)

        assert abs(stand_ccf - calc_ccf) < 0.01

    def test_max_sdi_equivalence(self, trees_and_stand):
        """Test that max SDI matches Stand.get_max_sdi()."""
        trees, stand, calculator = trees_and_stand

        stand_max_sdi = stand.get_max_sdi()
        calc_max_sdi = calculator.get_max_sdi(trees, default_species='LP')

        assert abs(stand_max_sdi - calc_max_sdi) < 0.01

    def test_pbal_equivalence(self, trees_and_stand):
        """Test that PBAL matches Stand.calculate_pbal()."""
        trees, stand, calculator = trees_and_stand

        target_tree = trees[5]

        stand_pbal = stand.calculate_pbal(target_tree)
        calc_pbal = calculator.calculate_pbal(trees, target_tree)

        assert abs(stand_pbal - calc_pbal) < 0.0001

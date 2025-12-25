"""
Tests for CompetitionCalculator.

These tests verify that the extracted competition calculations produce
results consistent with the original Stand class implementation.
"""
import pytest
import math
from pyfvs.competition import (
    CompetitionCalculator,
    TreeCompetition,
    get_competition_calculator,
    calculate_stand_competition
)
from pyfvs.stand_metrics import StandMetricsCalculator
from pyfvs.tree import Tree


class TestCompetitionCalculator:
    """Tests for CompetitionCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Create a competition calculator instance."""
        return CompetitionCalculator(default_species='LP')

    @pytest.fixture
    def metrics_calculator(self):
        """Create a metrics calculator for injection."""
        return StandMetricsCalculator(default_species='LP')

    @pytest.fixture
    def sample_trees(self):
        """Create a sample stand of trees for testing."""
        trees = []
        for i in range(50):
            dbh = 4.0 + i * 0.2  # DBH from 4.0 to 13.8 inches
            height = 30.0 + i * 0.8  # Heights from 30 to 69.2 feet
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=15))
        return trees

    @pytest.fixture
    def uniform_stand(self):
        """Create a uniform stand with identical trees."""
        return [Tree(dbh=8.0, height=50.0, species='LP', age=20) for _ in range(25)]

    def test_init_default(self, calculator):
        """Test calculator initialization with defaults."""
        assert calculator.default_species == 'LP'
        assert calculator._metrics is not None

    def test_init_with_metrics_calculator(self, metrics_calculator):
        """Test initialization with injected metrics calculator."""
        calc = CompetitionCalculator(metrics_calculator, 'SP')

        assert calc.default_species == 'SP'
        assert calc._metrics is metrics_calculator

    def test_tree_competition_dataclass(self):
        """Test TreeCompetition dataclass."""
        comp = TreeCompetition(
            competition_factor=0.5,
            pbal=25.0,
            rank=0.75,
            relsdi=3.5,
            ccf=120.0,
            relht=0.95
        )
        assert comp.competition_factor == 0.5
        assert comp.pbal == 25.0
        assert comp.rank == 0.75
        assert comp.relsdi == 3.5
        assert comp.ccf == 120.0
        assert comp.relht == 0.95


class TestCalculateTreeCompetition:
    """Tests for tree competition calculation."""

    @pytest.fixture
    def calculator(self):
        return CompetitionCalculator()

    @pytest.fixture
    def sample_trees(self):
        trees = []
        for i in range(50):
            dbh = 4.0 + i * 0.2
            height = 30.0 + i * 0.8
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=15))
        return trees

    def test_empty_list(self, calculator):
        """Test with empty tree list."""
        result = calculator.calculate_tree_competition([], 70)
        assert result == []

    def test_single_tree(self, calculator):
        """Test with single tree."""
        tree = Tree(dbh=8.0, height=50.0, species='LP', age=20)
        result = calculator.calculate_tree_competition([tree], 70)

        assert len(result) == 1
        assert result[0].competition_factor == 0.0
        assert result[0].pbal == 0.0
        assert result[0].relsdi == 1.0

    def test_returns_one_per_tree(self, calculator, sample_trees):
        """Test that result has one entry per tree."""
        result = calculator.calculate_tree_competition(sample_trees, 70)
        assert len(result) == len(sample_trees)

    def test_all_results_are_tree_competition(self, calculator, sample_trees):
        """Test that all results are TreeCompetition objects."""
        result = calculator.calculate_tree_competition(sample_trees, 70)
        for comp in result:
            assert isinstance(comp, TreeCompetition)

    def test_competition_factor_bounded(self, calculator, sample_trees):
        """Test that competition factor is bounded 0-1."""
        result = calculator.calculate_tree_competition(sample_trees, 70)
        for comp in result:
            assert 0.0 <= comp.competition_factor <= 1.0

    def test_rank_bounded(self, calculator, sample_trees):
        """Test that rank is bounded 0-1."""
        result = calculator.calculate_tree_competition(sample_trees, 70)
        for comp in result:
            assert 0.0 <= comp.rank <= 1.0

    def test_relsdi_bounded(self, calculator, sample_trees):
        """Test that relsdi is bounded 1-12."""
        result = calculator.calculate_tree_competition(sample_trees, 70)
        for comp in result:
            assert 1.0 <= comp.relsdi <= 12.0

    def test_pbal_non_negative(self, calculator, sample_trees):
        """Test that PBAL is non-negative."""
        result = calculator.calculate_tree_competition(sample_trees, 70)
        for comp in result:
            assert comp.pbal >= 0.0

    def test_largest_tree_zero_pbal(self, calculator, sample_trees):
        """Test that the largest tree has zero PBAL."""
        result = calculator.calculate_tree_competition(sample_trees, 70)

        # Find index of largest tree
        max_dbh = max(t.dbh for t in sample_trees)
        max_idx = next(i for i, t in enumerate(sample_trees) if t.dbh == max_dbh)

        assert result[max_idx].pbal == 0.0

    def test_smaller_trees_have_higher_pbal(self, calculator, sample_trees):
        """Test that smaller trees have higher PBAL."""
        result = calculator.calculate_tree_competition(sample_trees, 70)

        # Get PBAL for smallest and largest trees
        min_dbh = min(t.dbh for t in sample_trees)
        max_dbh = max(t.dbh for t in sample_trees)

        min_idx = next(i for i, t in enumerate(sample_trees) if t.dbh == min_dbh)
        max_idx = next(i for i, t in enumerate(sample_trees) if t.dbh == max_dbh)

        assert result[min_idx].pbal > result[max_idx].pbal

    def test_ccf_shared_across_trees(self, calculator, sample_trees):
        """Test that CCF is the same for all trees."""
        result = calculator.calculate_tree_competition(sample_trees, 70)
        ccf_values = [comp.ccf for comp in result]

        # All CCF values should be equal
        assert all(ccf == ccf_values[0] for ccf in ccf_values)

    def test_relsdi_shared_across_trees(self, calculator, sample_trees):
        """Test that RELSDI is the same for all trees."""
        result = calculator.calculate_tree_competition(sample_trees, 70)
        relsdi_values = [comp.relsdi for comp in result]

        # All RELSDI values should be equal
        assert all(relsdi == relsdi_values[0] for relsdi in relsdi_values)


class TestCalculateTreeCompetitionDicts:
    """Tests for dictionary-based competition calculation."""

    @pytest.fixture
    def calculator(self):
        return CompetitionCalculator()

    @pytest.fixture
    def sample_trees(self):
        return [Tree(dbh=6.0 + i * 0.5, height=40.0 + i * 2.0, species='LP', age=15)
                for i in range(20)]

    def test_returns_dicts(self, calculator, sample_trees):
        """Test that result is list of dictionaries."""
        result = calculator.calculate_tree_competition_dicts(sample_trees, 70)

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)

    def test_dict_keys(self, calculator, sample_trees):
        """Test that dictionaries have expected keys."""
        result = calculator.calculate_tree_competition_dicts(sample_trees, 70)

        expected_keys = {'competition_factor', 'pbal', 'rank', 'relsdi', 'ccf', 'relht'}
        for item in result:
            assert set(item.keys()) == expected_keys


class TestRelativeHeight:
    """Tests for relative height calculations."""

    @pytest.fixture
    def calculator(self):
        return CompetitionCalculator()

    @pytest.fixture
    def sample_trees(self):
        return [Tree(dbh=8.0, height=30.0 + i * 2.0, species='LP', age=20)
                for i in range(20)]

    def test_relative_height_top_height(self, calculator, sample_trees):
        """Test relative height using top height method."""
        target_tree = sample_trees[10]  # Middle tree
        relht = calculator.calculate_relative_height(
            target_tree, sample_trees, method='top_height'
        )

        assert 0.0 < relht <= 1.5

    def test_relative_height_max_height(self, calculator, sample_trees):
        """Test relative height using max height method."""
        target_tree = sample_trees[0]  # Shortest tree
        relht = calculator.calculate_relative_height(
            target_tree, sample_trees, method='max_height'
        )

        assert 0.0 < relht < 1.0  # Should be less than 1 since not tallest

    def test_tallest_tree_relht_near_one(self, calculator, sample_trees):
        """Test that tallest tree has relht near 1."""
        tallest = max(sample_trees, key=lambda t: t.height)
        relht = calculator.calculate_relative_height(
            tallest, sample_trees, method='max_height'
        )

        assert abs(relht - 1.0) < 0.01

    def test_empty_list(self, calculator):
        """Test with empty tree list."""
        tree = Tree(dbh=8.0, height=50.0, species='LP', age=20)
        relht = calculator.calculate_relative_height(tree, [], method='top_height')
        assert relht == 1.0


class TestBasalAreaPercentile:
    """Tests for basal area percentile calculations."""

    @pytest.fixture
    def calculator(self):
        return CompetitionCalculator()

    @pytest.fixture
    def sample_trees(self):
        return [Tree(dbh=4.0 + i * 0.5, height=40.0, species='LP', age=15)
                for i in range(20)]

    def test_percentile_range(self, calculator, sample_trees):
        """Test that percentiles are in range 0-100."""
        for tree in sample_trees:
            pct = calculator.calculate_basal_area_percentile(tree, sample_trees)
            assert 0.0 <= pct <= 100.0

    def test_largest_tree_highest_percentile(self, calculator, sample_trees):
        """Test that largest tree has highest percentile."""
        largest = max(sample_trees, key=lambda t: t.dbh)
        pct = calculator.calculate_basal_area_percentile(largest, sample_trees)

        # Largest should be close to 100%
        assert pct > 95.0

    def test_smallest_tree_lowest_percentile(self, calculator, sample_trees):
        """Test that smallest tree has lowest percentile."""
        smallest = min(sample_trees, key=lambda t: t.dbh)
        pct = calculator.calculate_basal_area_percentile(smallest, sample_trees)

        # Smallest should be well below 50%
        assert pct < 20.0

    def test_empty_list(self, calculator):
        """Test with empty tree list."""
        tree = Tree(dbh=8.0, height=50.0, species='LP', age=20)
        pct = calculator.calculate_basal_area_percentile(tree, [])
        assert pct == 50.0


class TestForestTypeAndEcounitEffects:
    """Tests for forest type and ecological unit effects."""

    @pytest.fixture
    def calculator(self):
        return CompetitionCalculator()

    def test_forest_type_effect_loblolly(self, calculator):
        """Test forest type effect for loblolly pine."""
        # This may return 0 if forest_type module not fully implemented
        effect = calculator.get_forest_type_effect('LP', 'FTYLPN')
        assert isinstance(effect, float)

    def test_ecounit_effect_loblolly(self, calculator):
        """Test ecological unit effect for loblolly pine."""
        # This may return 0 if ecological_unit module not fully implemented
        effect = calculator.get_ecounit_effect('LP', '232')
        assert isinstance(effect, float)

    def test_ecounit_effect_none(self, calculator):
        """Test ecological unit effect with None."""
        effect = calculator.get_ecounit_effect('LP', None)
        assert effect == 0.0


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_competition_calculator_singleton(self):
        """Test that get_competition_calculator returns singleton."""
        calc1 = get_competition_calculator()
        calc2 = get_competition_calculator()
        assert calc1 is calc2

    def test_calculate_stand_competition(self):
        """Test convenience function for stand competition."""
        trees = [Tree(dbh=6.0 + i * 0.5, height=40.0, species='LP', age=15)
                 for i in range(10)]
        result = calculate_stand_competition(trees, 70.0)

        assert len(result) == 10
        assert all(isinstance(c, TreeCompetition) for c in result)


class TestCompetitionEquivalence:
    """Tests to verify competition matches original Stand class calculations."""

    @pytest.fixture
    def trees_and_stand(self):
        """Create trees and a Stand for comparison testing."""
        from pyfvs.stand import Stand

        trees = []
        for i in range(50):
            dbh = 4.0 + i * 0.2
            height = 30.0 + i * 0.6
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=15))

        stand = Stand(trees=list(trees), site_index=70, species='LP')
        calculator = CompetitionCalculator(default_species='LP')

        return trees, stand, calculator

    def test_competition_factor_range_similar(self, trees_and_stand):
        """Test that competition factor ranges are similar."""
        trees, stand, calculator = trees_and_stand

        # Get Stand's competition metrics
        stand_metrics = stand._calculate_competition_metrics()

        # Get calculator's competition metrics
        calc_metrics = calculator.calculate_tree_competition_dicts(trees, 70)

        # Compare ranges
        stand_cf = [m['competition_factor'] for m in stand_metrics]
        calc_cf = [m['competition_factor'] for m in calc_metrics]

        # Ranges should be similar
        assert abs(min(stand_cf) - min(calc_cf)) < 0.1
        assert abs(max(stand_cf) - max(calc_cf)) < 0.1

    def test_pbal_equivalence(self, trees_and_stand):
        """Test that PBAL calculations match."""
        trees, stand, calculator = trees_and_stand

        stand_metrics = stand._calculate_competition_metrics()
        calc_metrics = calculator.calculate_tree_competition_dicts(trees, 70)

        # Compare PBAL for each tree
        for i, (sm, cm) in enumerate(zip(stand_metrics, calc_metrics)):
            assert abs(sm['pbal'] - cm['pbal']) < 0.01, f"PBAL mismatch at tree {i}"

    def test_ccf_equivalence(self, trees_and_stand):
        """Test that CCF calculations match."""
        trees, stand, calculator = trees_and_stand

        stand_metrics = stand._calculate_competition_metrics()
        calc_metrics = calculator.calculate_tree_competition_dicts(trees, 70)

        # CCF should be same for all trees and match
        stand_ccf = stand_metrics[0]['ccf']
        calc_ccf = calc_metrics[0]['ccf']

        assert abs(stand_ccf - calc_ccf) < 0.1

    def test_relsdi_equivalence(self, trees_and_stand):
        """Test that RELSDI calculations match."""
        trees, stand, calculator = trees_and_stand

        stand_metrics = stand._calculate_competition_metrics()
        calc_metrics = calculator.calculate_tree_competition_dicts(trees, 70)

        # RELSDI should be same for all trees and match
        stand_relsdi = stand_metrics[0]['relsdi']
        calc_relsdi = calc_metrics[0]['relsdi']

        assert abs(stand_relsdi - calc_relsdi) < 0.1

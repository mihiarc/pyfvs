"""
Tests for HarvestManager.

These tests verify that the extracted harvest operations produce
results consistent with the original Stand class implementation.
"""
import pytest
import math
from pyfvs.harvest import (
    HarvestManager,
    HarvestRecord,
    HarvestResult,
    get_harvest_manager,
    thin_stand_from_below
)
from pyfvs.tree import Tree


class TestHarvestManager:
    """Tests for HarvestManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh harvest manager instance."""
        return HarvestManager()

    @pytest.fixture
    def sample_trees(self):
        """Create a sample stand of trees for testing."""
        trees = []
        for i in range(100):
            dbh = 4.0 + (i % 10) * 0.8  # DBH from 4.0 to 11.2 inches
            height = 30.0 + (i % 10) * 4.0  # Heights from 30 to 66 feet
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=15))
        return trees

    @pytest.fixture
    def diverse_stand(self):
        """Create a stand with diverse DBH distribution."""
        trees = []
        # Small trees (4-6")
        for i in range(30):
            trees.append(Tree(dbh=4.0 + i * 0.07, height=30.0, species='LP', age=10))
        # Medium trees (6-10")
        for i in range(40):
            trees.append(Tree(dbh=6.0 + i * 0.1, height=45.0, species='LP', age=20))
        # Large trees (10-14")
        for i in range(30):
            trees.append(Tree(dbh=10.0 + i * 0.13, height=60.0, species='LP', age=30))
        return trees

    def test_init(self, manager):
        """Test manager initialization."""
        assert manager.harvest_history == []

    def test_harvest_record_dataclass(self):
        """Test HarvestRecord dataclass."""
        record = HarvestRecord(
            year=20,
            harvest_type='thin_from_below',
            trees_removed=50,
            basal_area_removed=25.0,
            volume_removed=1000.0,
            merchantable_volume_removed=800.0,
            board_feet_removed=4000.0,
            mean_dbh_removed=6.0,
            residual_tpa=450,
            residual_ba=100.0,
            target_ba=100.0
        )
        assert record.year == 20
        assert record.harvest_type == 'thin_from_below'
        assert record.trees_removed == 50
        assert record.target_ba == 100.0

    def test_harvest_result_dataclass(self, manager, sample_trees):
        """Test HarvestResult dataclass."""
        result = manager.thin_from_below(sample_trees, 20, target_tpa=50)

        assert isinstance(result, HarvestResult)
        assert isinstance(result.remaining_trees, list)
        assert isinstance(result.removed_trees, list)
        assert isinstance(result.record, HarvestRecord)


class TestThinFromBelow:
    """Tests for thin_from_below operation."""

    @pytest.fixture
    def manager(self):
        return HarvestManager()

    @pytest.fixture
    def sample_trees(self):
        trees = []
        for i in range(100):
            dbh = 4.0 + i * 0.1  # DBH from 4.0 to 13.9 inches
            height = 30.0 + i * 0.4
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=15))
        return trees

    def test_thin_from_below_by_tpa(self, manager, sample_trees):
        """Test thinning to target TPA."""
        result = manager.thin_from_below(sample_trees, 20, target_tpa=50)

        assert len(result.remaining_trees) == 50
        assert len(result.removed_trees) == 50
        assert result.record.harvest_type == 'thin_from_below'
        assert result.record.trees_removed == 50

    def test_thin_from_below_removes_smallest(self, manager, sample_trees):
        """Test that smallest trees are removed first."""
        result = manager.thin_from_below(sample_trees, 20, target_tpa=50)

        # The 50 largest trees should remain
        remaining_dbhs = [t.dbh for t in result.remaining_trees]
        removed_dbhs = [t.dbh for t in result.removed_trees]

        # All remaining should be larger than all removed
        assert min(remaining_dbhs) >= max(removed_dbhs)

    def test_thin_from_below_by_ba(self, manager, sample_trees):
        """Test thinning to target basal area."""
        initial_ba = sum(math.pi * (t.dbh / 24) ** 2 for t in sample_trees)
        target_ba = initial_ba * 0.5  # Target 50% of current BA

        result = manager.thin_from_below(sample_trees, 20, target_ba=target_ba)

        residual_ba = sum(math.pi * (t.dbh / 24) ** 2 for t in result.remaining_trees)
        assert residual_ba <= target_ba + 1.0  # Allow small overage from discrete trees

    def test_thin_from_below_empty_list(self, manager):
        """Test thinning empty tree list."""
        result = manager.thin_from_below([], 20, target_tpa=50)

        assert len(result.remaining_trees) == 0
        assert len(result.removed_trees) == 0
        assert result.record.trees_removed == 0

    def test_thin_from_below_requires_target(self, manager, sample_trees):
        """Test that at least one target is required."""
        with pytest.raises(ValueError, match="Must specify"):
            manager.thin_from_below(sample_trees, 20)

    def test_thin_from_below_history_recorded(self, manager, sample_trees):
        """Test that harvest is recorded in history."""
        manager.thin_from_below(sample_trees, 20, target_tpa=50)

        assert len(manager.harvest_history) == 1
        assert manager.harvest_history[0].harvest_type == 'thin_from_below'


class TestThinFromAbove:
    """Tests for thin_from_above operation."""

    @pytest.fixture
    def manager(self):
        return HarvestManager()

    @pytest.fixture
    def sample_trees(self):
        trees = []
        for i in range(100):
            dbh = 4.0 + i * 0.1
            height = 30.0 + i * 0.4
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=15))
        return trees

    def test_thin_from_above_by_tpa(self, manager, sample_trees):
        """Test thinning from above to target TPA."""
        result = manager.thin_from_above(sample_trees, 20, target_tpa=50)

        assert len(result.remaining_trees) == 50
        assert len(result.removed_trees) == 50
        assert result.record.harvest_type == 'thin_from_above'

    def test_thin_from_above_removes_largest(self, manager, sample_trees):
        """Test that largest trees are removed first."""
        result = manager.thin_from_above(sample_trees, 20, target_tpa=50)

        remaining_dbhs = [t.dbh for t in result.remaining_trees]
        removed_dbhs = [t.dbh for t in result.removed_trees]

        # All remaining should be smaller than all removed
        assert max(remaining_dbhs) <= min(removed_dbhs)

    def test_thin_from_above_empty_list(self, manager):
        """Test thinning empty tree list from above."""
        result = manager.thin_from_above([], 20, target_tpa=50)

        assert len(result.remaining_trees) == 0
        assert result.record.trees_removed == 0

    def test_thin_from_above_requires_target(self, manager, sample_trees):
        """Test that at least one target is required."""
        with pytest.raises(ValueError, match="Must specify"):
            manager.thin_from_above(sample_trees, 20)


class TestThinByDbhRange:
    """Tests for thin_by_dbh_range operation."""

    @pytest.fixture
    def manager(self):
        return HarvestManager()

    @pytest.fixture
    def sample_trees(self):
        trees = []
        for i in range(100):
            dbh = 4.0 + i * 0.1  # 4.0 to 13.9 inches
            height = 30.0 + i * 0.4
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=15))
        return trees

    def test_thin_by_dbh_range_all(self, manager, sample_trees):
        """Test removing all trees in a DBH range."""
        # Trees from 6-8" should be removed
        result = manager.thin_by_dbh_range(sample_trees, 20, 6.0, 8.0, 1.0)

        # Check remaining trees are outside range
        for tree in result.remaining_trees:
            assert tree.dbh < 6.0 or tree.dbh > 8.0

    def test_thin_by_dbh_range_partial(self, manager, sample_trees):
        """Test removing a proportion of trees in DBH range."""
        in_range_count = sum(1 for t in sample_trees if 6.0 <= t.dbh <= 8.0)

        result = manager.thin_by_dbh_range(sample_trees, 20, 6.0, 8.0, 0.5)

        # About half of in-range trees should be removed
        expected_removed = int(in_range_count * 0.5)
        assert result.record.trees_removed == expected_removed

    def test_thin_by_dbh_range_invalid_range(self, manager, sample_trees):
        """Test that min_dbh must be less than max_dbh."""
        with pytest.raises(ValueError, match="must be less than"):
            manager.thin_by_dbh_range(sample_trees, 20, 8.0, 6.0)

    def test_thin_by_dbh_range_invalid_proportion(self, manager, sample_trees):
        """Test that proportion must be 0-1."""
        with pytest.raises(ValueError, match="proportion"):
            manager.thin_by_dbh_range(sample_trees, 20, 6.0, 8.0, 1.5)

    def test_thin_by_dbh_range_empty_list(self, manager):
        """Test thinning empty tree list by DBH range."""
        result = manager.thin_by_dbh_range([], 20, 6.0, 8.0)
        assert result.record.trees_removed == 0


class TestClearcut:
    """Tests for clearcut operation."""

    @pytest.fixture
    def manager(self):
        return HarvestManager()

    @pytest.fixture
    def sample_trees(self):
        return [Tree(dbh=8.0, height=50.0, species='LP', age=20) for _ in range(50)]

    def test_clearcut_removes_all(self, manager, sample_trees):
        """Test that clearcut removes all trees."""
        result = manager.clearcut(sample_trees, 25)

        assert len(result.remaining_trees) == 0
        assert len(result.removed_trees) == 50
        assert result.record.harvest_type == 'clearcut'
        assert result.record.trees_removed == 50

    def test_clearcut_records_volume(self, manager, sample_trees):
        """Test that clearcut records removed volumes."""
        result = manager.clearcut(sample_trees, 25)

        assert result.record.volume_removed > 0
        assert result.record.basal_area_removed > 0

    def test_clearcut_empty_stand(self, manager):
        """Test clearcut on empty stand."""
        result = manager.clearcut([], 25)

        assert result.record.trees_removed == 0
        assert result.record.volume_removed == 0.0


class TestSelectionHarvest:
    """Tests for selection_harvest operation."""

    @pytest.fixture
    def manager(self):
        return HarvestManager()

    @pytest.fixture
    def sample_trees(self):
        trees = []
        for i in range(100):
            dbh = 6.0 + i * 0.1  # 6.0 to 15.9 inches
            height = 40.0 + i * 0.4
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=25))
        return trees

    def test_selection_harvest_reaches_target(self, manager, sample_trees):
        """Test that selection harvest reaches target BA."""
        initial_ba = sum(math.pi * (t.dbh / 24) ** 2 for t in sample_trees)
        target_ba = initial_ba * 0.6  # Target 60% of BA

        result = manager.selection_harvest(sample_trees, 30, target_ba)

        residual_ba = sum(math.pi * (t.dbh / 24) ** 2 for t in result.remaining_trees)
        assert residual_ba <= target_ba + 1.0

    def test_selection_harvest_min_dbh(self, manager, sample_trees):
        """Test that min_dbh is respected."""
        initial_ba = sum(math.pi * (t.dbh / 24) ** 2 for t in sample_trees)
        target_ba = initial_ba * 0.5  # Target 50% of BA
        min_dbh = 10.0

        result = manager.selection_harvest(sample_trees, 30, target_ba, min_dbh=min_dbh)

        # All removed trees should be >= min_dbh
        for tree in result.removed_trees:
            assert tree.dbh >= min_dbh

    def test_selection_harvest_already_below_target(self, manager, sample_trees):
        """Test selection when already below target."""
        initial_ba = sum(math.pi * (t.dbh / 24) ** 2 for t in sample_trees)

        # Target higher than current BA
        result = manager.selection_harvest(sample_trees, 30, initial_ba * 2)

        assert len(result.removed_trees) == 0
        assert len(result.remaining_trees) == len(sample_trees)

    def test_selection_harvest_empty_list(self, manager):
        """Test selection harvest on empty list."""
        result = manager.selection_harvest([], 30, 50.0)
        assert result.record.trees_removed == 0


class TestHarvestHistory:
    """Tests for harvest history tracking."""

    @pytest.fixture
    def manager(self):
        return HarvestManager()

    @pytest.fixture
    def sample_trees(self):
        return [Tree(dbh=8.0, height=50.0, species='LP', age=20) for _ in range(100)]

    def test_multiple_harvests_tracked(self, manager, sample_trees):
        """Test that multiple harvests are tracked."""
        # First harvest
        result1 = manager.thin_from_below(sample_trees, 15, target_tpa=80)

        # Second harvest
        result2 = manager.thin_from_below(result1.remaining_trees, 20, target_tpa=60)

        assert len(manager.harvest_history) == 2
        assert manager.harvest_history[0].year == 15
        assert manager.harvest_history[1].year == 20

    def test_get_harvest_summary(self, manager, sample_trees):
        """Test harvest summary calculation."""
        result = manager.thin_from_below(sample_trees, 20, target_tpa=50)

        summary = manager.get_harvest_summary()

        assert summary['total_harvests'] == 1
        assert summary['total_trees_removed'] == 50
        assert summary['total_volume_removed'] > 0
        assert len(summary['harvest_history']) == 1

    def test_get_harvest_summary_empty(self, manager):
        """Test harvest summary with no harvests."""
        summary = manager.get_harvest_summary()

        assert summary['total_harvests'] == 0
        assert summary['total_trees_removed'] == 0
        assert summary['harvest_history'] == []

    def test_get_last_harvest(self, manager, sample_trees):
        """Test getting last harvest record."""
        manager.thin_from_below(sample_trees[:50], 15, target_tpa=25)
        manager.thin_from_above(sample_trees[50:], 20, target_tpa=25)

        last = manager.get_last_harvest()

        assert last is not None
        assert last.year == 20
        assert last.harvest_type == 'thin_from_above'

    def test_get_last_harvest_empty(self, manager):
        """Test getting last harvest when none exist."""
        assert manager.get_last_harvest() is None

    def test_clear_history(self, manager, sample_trees):
        """Test clearing harvest history."""
        manager.thin_from_below(sample_trees, 20, target_tpa=50)
        assert len(manager.harvest_history) == 1

        manager.clear_history()
        assert len(manager.harvest_history) == 0


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_harvest_manager_singleton(self):
        """Test that get_harvest_manager returns singleton."""
        manager1 = get_harvest_manager()
        manager2 = get_harvest_manager()
        assert manager1 is manager2

    def test_thin_stand_from_below(self):
        """Test convenience function for thinning."""
        trees = [Tree(dbh=6.0, height=40.0, species='LP', age=15) for _ in range(20)]
        result = thin_stand_from_below(trees, 15, target_tpa=10)

        assert isinstance(result, HarvestResult)
        assert len(result.remaining_trees) == 10


class TestHarvestEquivalence:
    """Tests to verify harvest matches original Stand class operations."""

    @pytest.fixture
    def trees_and_stand(self):
        """Create trees and a Stand for comparison testing."""
        from pyfvs.stand import Stand

        trees = []
        for i in range(100):
            dbh = 4.0 + (i % 10) * 0.8
            height = 30.0 + (i % 10) * 3.0
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=15))

        stand = Stand(trees=list(trees), site_index=70, species='LP')
        manager = HarvestManager()

        return trees, stand, manager

    def test_thin_from_below_equivalence(self, trees_and_stand):
        """Test that thin_from_below matches Stand behavior."""
        trees, stand, manager = trees_and_stand

        # Get initial BA
        initial_ba = sum(math.pi * (t.dbh / 24) ** 2 for t in trees)
        target_tpa = 50

        # Manager result
        result = manager.thin_from_below(list(trees), 15, target_tpa=target_tpa)

        # Stand result
        stand.thin_from_below(target_tpa=target_tpa)

        # Compare results
        assert len(result.remaining_trees) == len(stand.trees)
        assert result.record.trees_removed == (100 - len(stand.trees))

    def test_clearcut_equivalence(self, trees_and_stand):
        """Test that clearcut matches Stand behavior."""
        trees, stand, manager = trees_and_stand

        result = manager.clearcut(list(trees), 25)
        stand.clearcut()

        assert len(result.remaining_trees) == 0
        assert len(stand.trees) == 0
        assert result.record.trees_removed == 100

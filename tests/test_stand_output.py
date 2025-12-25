"""
Tests for StandOutputGenerator.

These tests verify that the extracted output generation produces
results consistent with the original Stand class implementation.
"""
import pytest
import tempfile
import os
from pathlib import Path
from pyfvs.stand_output import (
    StandOutputGenerator,
    YieldRecord,
    get_output_generator,
    generate_tree_list
)
from pyfvs.stand_metrics import StandMetricsCalculator
from pyfvs.tree import Tree


class TestYieldRecord:
    """Tests for YieldRecord dataclass."""

    def test_yield_record_creation(self):
        """Test creating a yield record."""
        record = YieldRecord(
            StandID="TEST001",
            Year=2025,
            Age=20,
            TPA=350,
            BA=120.0,
            SDI=250.0,
            CCF=150.0,
            TopHt=55.0,
            QMD=8.5,
            TCuFt=2500.0,
            MCuFt=2000.0,
            BdFt=12000.0
        )

        assert record.StandID == "TEST001"
        assert record.Year == 2025
        assert record.Age == 20
        assert record.TPA == 350
        assert record.BA == 120.0

    def test_yield_record_defaults(self):
        """Test yield record default values."""
        record = YieldRecord(
            StandID="TEST001",
            Year=2025,
            Age=20,
            TPA=350,
            BA=120.0,
            SDI=250.0,
            CCF=150.0,
            TopHt=55.0,
            QMD=8.5,
            TCuFt=2500.0,
            MCuFt=2000.0,
            BdFt=12000.0
        )

        # Check defaults
        assert record.RTpa == 0
        assert record.RTCuFt == 0.0
        assert record.PrdLen == 5
        assert record.Acc == 0.0
        assert record.Mort == 0.0
        assert record.MAI == 0.0
        assert record.ForTyp == 0  # Integer default for forest type code
        assert record.SizeCls == 0  # Integer default for size class
        assert record.StkCls == 0  # Integer default for stocking class

    def test_yield_record_to_dict(self):
        """Test converting yield record to dictionary."""
        record = YieldRecord(
            StandID="TEST001",
            Year=2025,
            Age=20,
            TPA=350,
            BA=120.0,
            SDI=250.0,
            CCF=150.0,
            TopHt=55.0,
            QMD=8.5,
            TCuFt=2500.0,
            MCuFt=2000.0,
            BdFt=12000.0
        )

        result = record.to_dict()

        assert isinstance(result, dict)
        assert result['StandID'] == "TEST001"
        assert result['TPA'] == 350
        assert 'RTpa' in result


class TestStandOutputGenerator:
    """Tests for StandOutputGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create an output generator instance."""
        return StandOutputGenerator(default_species='LP')

    @pytest.fixture
    def metrics_calculator(self):
        """Create a metrics calculator for injection."""
        return StandMetricsCalculator(default_species='LP')

    @pytest.fixture
    def sample_trees(self):
        """Create a sample stand of trees for testing."""
        trees = []
        for i in range(30):
            dbh = 4.0 + i * 0.3
            height = 30.0 + i * 1.5
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=15))
        return trees

    def test_init_default(self, generator):
        """Test generator initialization with defaults."""
        assert generator.default_species == 'LP'
        assert generator._metrics is not None
        assert generator._competition is not None

    def test_init_with_metrics(self, metrics_calculator):
        """Test initialization with injected metrics calculator."""
        gen = StandOutputGenerator(metrics_calculator, default_species='SP')

        assert gen.default_species == 'SP'
        assert gen._metrics is metrics_calculator


class TestGenerateTreeList:
    """Tests for tree list generation."""

    @pytest.fixture
    def generator(self):
        return StandOutputGenerator()

    @pytest.fixture
    def sample_trees(self):
        return [Tree(dbh=6.0 + i * 0.5, height=40.0 + i * 2.0, species='LP', age=15)
                for i in range(20)]

    def test_empty_tree_list(self, generator):
        """Test with empty tree list."""
        result = generator.generate_tree_list([], 20, 70)
        assert result == []

    def test_returns_list(self, generator, sample_trees):
        """Test that result is a list."""
        result = generator.generate_tree_list(sample_trees, 20, 70)
        assert isinstance(result, list)

    def test_one_record_per_tree(self, generator, sample_trees):
        """Test that result has one record per tree."""
        result = generator.generate_tree_list(sample_trees, 20, 70)
        assert len(result) == len(sample_trees)

    def test_records_are_dicts(self, generator, sample_trees):
        """Test that records are dictionaries."""
        result = generator.generate_tree_list(sample_trees, 20, 70)
        for record in result:
            assert isinstance(record, dict)

    def test_stand_id_included(self, generator, sample_trees):
        """Test that stand ID is included in records."""
        result = generator.generate_tree_list(sample_trees, 20, 70, stand_id="MY_STAND")
        for record in result:
            assert record['StandID'] == "MY_STAND"

    def test_tree_ids_sequential(self, generator, sample_trees):
        """Test that tree IDs are sequential starting from 1."""
        result = generator.generate_tree_list(sample_trees, 20, 70)
        tree_ids = [r['TreeId'] for r in result]
        assert tree_ids == list(range(1, len(sample_trees) + 1))


class TestGenerateStockTable:
    """Tests for stock table generation."""

    @pytest.fixture
    def generator(self):
        return StandOutputGenerator()

    @pytest.fixture
    def sample_trees(self):
        return [Tree(dbh=4.0 + i * 0.5, height=40.0, species='LP', age=15)
                for i in range(20)]

    def test_empty_stock_table(self, generator):
        """Test with empty tree list."""
        result = generator.generate_stock_table([])
        assert result == []

    def test_returns_list(self, generator, sample_trees):
        """Test that result is a list."""
        result = generator.generate_stock_table(sample_trees)
        assert isinstance(result, list)

    def test_stock_table_has_dbh_classes(self, generator, sample_trees):
        """Test that stock table has DBH class information."""
        result = generator.generate_stock_table(sample_trees)
        for row in result:
            assert 'DBHClass' in row
            assert 'DBHMin' in row
            assert 'DBHMax' in row

    def test_stock_table_has_metrics(self, generator, sample_trees):
        """Test that stock table has metrics."""
        result = generator.generate_stock_table(sample_trees)
        for row in result:
            assert 'TPA' in row
            assert 'BA' in row
            assert 'TcuFt' in row

    def test_custom_dbh_width(self, generator, sample_trees):
        """Test with custom DBH class width."""
        result_2inch = generator.generate_stock_table(sample_trees, dbh_class_width=2.0)
        result_4inch = generator.generate_stock_table(sample_trees, dbh_class_width=4.0)

        # With wider classes, should have fewer rows
        assert len(result_4inch) <= len(result_2inch)


class TestCreateYieldRecord:
    """Tests for yield record creation."""

    @pytest.fixture
    def generator(self):
        return StandOutputGenerator()

    @pytest.fixture
    def sample_trees(self):
        return [Tree(dbh=8.0, height=50.0, species='LP', age=20) for _ in range(100)]

    def test_basic_yield_record(self, generator, sample_trees):
        """Test creating a basic yield record."""
        record = generator.create_yield_record(
            sample_trees, stand_age=20, site_index=70
        )

        assert isinstance(record, YieldRecord)
        assert record.Age == 20
        assert record.TPA == 100

    def test_yield_record_with_removals(self, generator, sample_trees):
        """Test yield record with harvest removals."""
        record = generator.create_yield_record(
            sample_trees, stand_age=20, site_index=70,
            removed_tpa=25, removed_tcuft=500.0
        )

        assert record.RTpa == 25
        assert record.RTCuFt == 500.0

    def test_yield_record_accretion(self, generator, sample_trees):
        """Test yield record with accretion calculation."""
        record = generator.create_yield_record(
            sample_trees, stand_age=20, site_index=70,
            prev_volume=1000.0, period_length=5
        )

        # With positive growth, accretion should be positive
        assert record.Acc >= 0

    def test_yield_record_mai(self, generator, sample_trees):
        """Test yield record MAI calculation."""
        record = generator.create_yield_record(
            sample_trees, stand_age=20, site_index=70
        )

        # MAI should be volume / age
        expected_mai = record.TCuFt / 20
        assert abs(record.MAI - expected_mai) < 0.01


class TestExportFunctions:
    """Tests for export functionality."""

    @pytest.fixture
    def generator(self):
        return StandOutputGenerator()

    @pytest.fixture
    def sample_trees(self):
        return [Tree(dbh=8.0, height=50.0, species='LP', age=20) for _ in range(10)]

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_export_tree_list_csv(self, generator, sample_trees, temp_dir):
        """Test exporting tree list to CSV."""
        tree_list = generator.generate_tree_list(sample_trees, 20, 70)
        filepath = os.path.join(temp_dir, 'treelist')

        result_path = generator.export_tree_list(tree_list, filepath, format='csv')

        assert Path(result_path).exists()
        assert result_path.endswith('.csv')

    def test_export_tree_list_json(self, generator, sample_trees, temp_dir):
        """Test exporting tree list to JSON."""
        tree_list = generator.generate_tree_list(sample_trees, 20, 70)
        filepath = os.path.join(temp_dir, 'treelist')

        result_path = generator.export_tree_list(tree_list, filepath, format='json')

        assert Path(result_path).exists()
        assert result_path.endswith('.json')

    def test_export_yield_table_csv(self, generator, sample_trees, temp_dir):
        """Test exporting yield table to CSV."""
        records = [
            generator.create_yield_record(sample_trees, stand_age=i*5, site_index=70)
            for i in range(1, 5)
        ]
        filepath = os.path.join(temp_dir, 'yield')

        result_path = generator.export_yield_table(records, filepath, format='csv')

        assert Path(result_path).exists()
        assert result_path.endswith('.csv')

    def test_export_stock_table_csv(self, generator, sample_trees, temp_dir):
        """Test exporting stock table to CSV."""
        stock_table = generator.generate_stock_table(sample_trees)
        filepath = os.path.join(temp_dir, 'stock')

        result_path = generator.export_stock_table(stock_table, filepath, format='csv')

        assert Path(result_path).exists()
        assert result_path.endswith('.csv')

    def test_export_adds_extension(self, generator, sample_trees, temp_dir):
        """Test that export adds correct extension."""
        tree_list = generator.generate_tree_list(sample_trees, 20, 70)
        filepath = os.path.join(temp_dir, 'no_extension')

        result_path = generator.export_tree_list(tree_list, filepath, format='json')

        assert result_path.endswith('.json')

    def test_export_invalid_format(self, generator, sample_trees, temp_dir):
        """Test that invalid format raises error."""
        tree_list = generator.generate_tree_list(sample_trees, 20, 70)
        filepath = os.path.join(temp_dir, 'test')

        with pytest.raises(ValueError, match="Unsupported format"):
            generator.export_tree_list(tree_list, filepath, format='invalid')


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_output_generator_singleton(self):
        """Test that get_output_generator returns singleton."""
        gen1 = get_output_generator()
        gen2 = get_output_generator()
        assert gen1 is gen2

    def test_generate_tree_list_convenience(self):
        """Test convenience function for tree list generation."""
        trees = [Tree(dbh=8.0, height=50.0, species='LP', age=20) for _ in range(5)]
        result = generate_tree_list(trees, 20, 70.0, "TEST")

        assert len(result) == 5
        assert all(r['StandID'] == "TEST" for r in result)


class TestOutputEquivalence:
    """Tests to verify output matches original Stand class methods."""

    @pytest.fixture
    def trees_and_stand(self):
        """Create trees and a Stand for comparison testing."""
        from pyfvs.stand import Stand

        trees = []
        for i in range(30):
            dbh = 4.0 + i * 0.3
            height = 30.0 + i * 1.5
            trees.append(Tree(dbh=dbh, height=height, species='LP', age=15))

        stand = Stand(trees=list(trees), site_index=70, species='LP')
        generator = StandOutputGenerator(default_species='LP')

        return trees, stand, generator

    def test_tree_list_count_matches(self, trees_and_stand):
        """Test that tree list count matches Stand method."""
        trees, stand, generator = trees_and_stand

        stand_list = stand.get_tree_list()
        gen_list = generator.generate_tree_list(trees, stand.age, 70)

        assert len(stand_list) == len(gen_list)

    def test_tree_list_structure_matches(self, trees_and_stand):
        """Test that tree list structure matches Stand method."""
        trees, stand, generator = trees_and_stand

        stand_list = stand.get_tree_list()
        gen_list = generator.generate_tree_list(trees, stand.age, 70)

        # Check that first record has same keys
        if stand_list and gen_list:
            # Key sets should be similar (generator adds StandID)
            stand_keys = set(stand_list[0].keys())
            gen_keys = set(gen_list[0].keys())

            # Common keys should match
            common = stand_keys & gen_keys
            assert len(common) > 10  # Should have many common keys

"""
Tests for all documentation examples.

This module runs every code example from the PyFVS documentation to ensure
they work correctly and captures expected output for inclusion in the docs.

Run with: uv run pytest tests/test_documentation_examples.py -v
Generate output report: uv run pytest tests/test_documentation_examples.py -v --tb=short 2>&1 | tee test_output/docs_examples_report.txt
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from io import StringIO
import sys
import tempfile
import shutil

from pyfvs import Stand, Tree
from pyfvs.simulation_engine import SimulationEngine
from tests.utils import setup_test_output


class TestBasicSimulationExamples:
    """Tests for basic simulation examples from getting-started.md and examples.md"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test output directory."""
        self.output_dir = setup_test_output() / 'documentation_examples'
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}

    def test_simple_stand_growth(self):
        """
        Test: Simple Stand Growth (examples.md lines 9-28)

        Creates a planted loblolly pine stand and grows it for 30 years.
        """
        # Example code from documentation
        from pyfvs import Stand

        stand = Stand.initialize_planted(
            trees_per_acre=500,
            site_index=70,
            species='LP'
        )

        stand.grow(years=30)

        metrics = stand.get_metrics()

        # Capture output
        output = []
        output.append(f"Age: {stand.age} years")
        output.append(f"Trees/acre: {metrics['tpa']:.0f}")
        output.append(f"Volume: {metrics['volume']:.0f} ft³/acre")
        output.append(f"Mean DBH: {metrics['qmd']:.1f} inches")

        # Assertions
        assert stand.age == 30
        assert metrics['tpa'] > 0
        assert metrics['tpa'] < 500  # Some mortality expected
        assert metrics['volume'] > 0
        assert metrics['qmd'] > 0

        # Save results for documentation
        self._save_example_output('simple_stand_growth', '\n'.join(output))

        print("\n--- Simple Stand Growth Output ---")
        for line in output:
            print(line)

    def test_basic_stand_with_basal_area(self):
        """
        Test: Basic Stand Simulation (getting-started.md lines 33-52)

        Includes basal area in output metrics.
        """
        from pyfvs import Stand

        stand = Stand.initialize_planted(
            trees_per_acre=500,
            site_index=70,
            species='LP'
        )

        stand.grow(years=30)

        metrics = stand.get_metrics()

        output = []
        output.append(f"Age: {stand.age} years")
        output.append(f"Trees per acre: {metrics['tpa']:.0f}")
        output.append(f"Basal area: {metrics['basal_area']:.1f} ft²/acre")
        output.append(f"Volume: {metrics['volume']:.0f} ft³/acre")

        assert stand.age == 30
        assert metrics['basal_area'] > 0

        self._save_example_output('basic_stand_with_basal_area', '\n'.join(output))

        print("\n--- Basic Stand with Basal Area Output ---")
        for line in output:
            print(line)

    def test_ecounit_simulation(self):
        """
        Test: Using Ecological Units (getting-started.md lines 69-82)

        Demonstrates M231 ecounit for high-productivity simulation.
        """
        from pyfvs import Stand

        stand = Stand.initialize_planted(
            trees_per_acre=500,
            site_index=70,
            species='LP',
            ecounit='M231'
        )

        stand.grow(years=25)

        output = f"Volume: {stand.get_metrics()['volume']:.0f} ft³/acre"

        assert stand.get_metrics()['volume'] > 0

        self._save_example_output('ecounit_simulation', output)

        print(f"\n--- Ecounit Simulation Output ---")
        print(output)

    def _save_example_output(self, example_name: str, output: str):
        """Save example output to file for documentation reference."""
        output_file = self.output_dir / f'{example_name}_output.txt'
        with open(output_file, 'w') as f:
            f.write(output)


class TestHarvestOperationExamples:
    """Tests for harvest operation examples from getting-started.md and harvesting.md"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test output directory."""
        self.output_dir = setup_test_output() / 'documentation_examples'
        self.output_dir.mkdir(exist_ok=True)

    def test_thinning_from_below(self):
        """
        Test: Thinning from Below (getting-started.md lines 101-112)

        Thins a stand from 800 TPA to 200 TPA by removing smallest trees.
        """
        from pyfvs import Stand

        stand = Stand.initialize_planted(trees_per_acre=800, site_index=70, species='LP')
        stand.grow(years=15)

        pre_thin_tpa = stand.get_metrics()['tpa']

        stand.thin_from_below(target_tpa=200)

        stand.grow(years=15)

        output = f"Final TPA: {stand.get_metrics()['tpa']:.0f}"

        assert stand.get_metrics()['tpa'] <= 200  # Should be at or below target
        assert stand.get_metrics()['tpa'] > 0

        self._save_example_output('thinning_from_below', output)

        print(f"\n--- Thinning from Below Output ---")
        print(f"Pre-thin TPA: {pre_thin_tpa:.0f}")
        print(output)

    def test_single_thin_scenario(self):
        """
        Test: Single Thin Scenario (examples.md lines 34-55)

        Single commercial thin at age 15 with M231 ecounit.
        """
        from pyfvs import Stand

        stand = Stand.initialize_planted(
            trees_per_acre=700,
            site_index=70,
            species='LP',
            ecounit='M231'
        )

        stand.grow(years=15)
        pre_thin_output = f"Pre-thin: {stand.get_metrics()['tpa']:.0f} TPA"

        stand.thin_from_below(target_tpa=300)
        post_thin_output = f"Post-thin: {stand.get_metrics()['tpa']:.0f} TPA"

        stand.grow(years=15)
        final_output = f"Final volume: {stand.get_metrics()['volume']:.0f} ft³/acre"

        output = '\n'.join([pre_thin_output, post_thin_output, final_output])

        assert stand.get_metrics()['tpa'] <= 300
        assert stand.get_metrics()['volume'] > 0

        self._save_example_output('single_thin_scenario', output)

        print(f"\n--- Single Thin Scenario Output ---")
        print(output)

    def test_multiple_thins(self):
        """
        Test: Multiple Thins (examples.md lines 59-82)

        Two-thin schedule: first thin at age 12, second at age 20, harvest at 35.
        """
        from pyfvs import Stand

        stand = Stand.initialize_planted(
            trees_per_acre=800,
            site_index=75,
            species='LP',
            ecounit='M231'
        )

        stand.grow(years=12)
        stand.thin_from_below(target_tpa=400)

        stand.grow(years=8)
        stand.thin_from_below(target_tpa=200)

        stand.grow(years=15)

        metrics = stand.get_metrics()
        output = f"Final: {metrics['volume']:.0f} ft³/acre, {metrics['qmd']:.1f}\" DBH"

        assert metrics['tpa'] <= 200
        assert metrics['volume'] > 0
        assert metrics['qmd'] > 0

        self._save_example_output('multiple_thins', output)

        print(f"\n--- Multiple Thins Output ---")
        print(output)

    def test_commercial_thin_schedule(self):
        """
        Test: Commercial Thin Example (harvesting.md lines 74-101)

        Full commercial thinning schedule with two thins.
        """
        from pyfvs import Stand

        stand = Stand.initialize_planted(
            trees_per_acre=700,
            site_index=70,
            species='LP',
            ecounit='M231'
        )

        stand.grow(years=12)
        pre_thin_output = f"Pre-thin: {stand.get_metrics()['tpa']:.0f} TPA, {stand.get_metrics()['qmd']:.1f}\" QMD"

        stand.thin_from_below(target_tpa=350)
        post_thin_output = f"Post-thin: {stand.get_metrics()['tpa']:.0f} TPA"

        stand.grow(years=8)
        stand.thin_from_below(target_tpa=180)

        stand.grow(years=10)

        final_output = f"Final: {stand.get_metrics()['volume']:.0f} ft³/acre, {stand.get_metrics()['qmd']:.1f}\" QMD"

        output = '\n'.join([pre_thin_output, post_thin_output, final_output])

        self._save_example_output('commercial_thin_schedule', output)

        print(f"\n--- Commercial Thin Schedule Output ---")
        print(output)

    def test_sawtimber_rotation(self):
        """
        Test: Sawtimber Rotation (harvesting.md lines 105-120)

        Long rotation for large sawtimber at age 40.
        """
        stand = Stand.initialize_planted(trees_per_acre=600, site_index=75, species='LP')

        stand.grow(years=15)
        stand.thin_from_below(target_tpa=250)

        stand.grow(years=10)
        stand.thin_from_below(target_tpa=120)

        stand.grow(years=15)

        metrics = stand.get_metrics()

        output = []
        output.append(f"Final DBH: {metrics['qmd']:.1f} inches")
        output.append(f"Final volume: {metrics['volume']:.0f} ft³/acre")

        assert metrics['qmd'] > 10  # Should have large trees
        assert metrics['volume'] > 0

        self._save_example_output('sawtimber_rotation', '\n'.join(output))

        print(f"\n--- Sawtimber Rotation Output ---")
        for line in output:
            print(line)

    def _save_example_output(self, example_name: str, output: str):
        """Save example output to file for documentation reference."""
        output_file = self.output_dir / f'{example_name}_output.txt'
        with open(output_file, 'w') as f:
            f.write(output)


class TestYieldTableExamples:
    """Tests for yield table generation examples."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test output directory."""
        self.output_dir = setup_test_output() / 'documentation_examples'
        self.output_dir.mkdir(exist_ok=True)

    def test_yield_table_from_grow(self):
        """
        Test: Get Yield Table (getting-started.md lines 139-143)

        Generate yield table using get_yield_table_dataframe().
        Note: Actual column names are capitalized (Age, TPA, QMD, TCuFt)
        """
        from pyfvs import Stand

        stand = Stand.initialize_planted(trees_per_acre=500, site_index=70, species='LP')
        yield_table = stand.get_yield_table_dataframe(years=50, period_length=5)

        # Use actual column names (capitalized)
        output = yield_table[['Age', 'TPA', 'QMD', 'TCuFt']].to_string()

        assert isinstance(yield_table, pd.DataFrame)
        assert len(yield_table) >= 10  # Multiple time periods
        assert 'Age' in yield_table.columns
        assert 'TCuFt' in yield_table.columns

        self._save_example_output('yield_table_from_grow', output)

        print(f"\n--- Yield Table Output ---")
        # Rename columns for user-friendly display
        display_df = yield_table[['Age', 'TPA', 'QMD', 'TCuFt']].copy()
        display_df.columns = ['age', 'tpa', 'qmd', 'volume']
        print(display_df.to_string(index=False))

    def test_yield_table_multi_scenario(self):
        """
        Test: Single Species Yield Table (examples.md lines 88-115)

        Generate yield table across site indices and densities.
        """
        from pyfvs import Stand
        import pandas as pd

        results = []

        for si in [60, 70, 80]:
            for tpa in [400, 600]:
                stand = Stand.initialize_planted(
                    trees_per_acre=tpa,
                    site_index=si,
                    species='LP',
                    ecounit='M231'
                )
                stand.grow(years=30)

                m = stand.get_metrics()
                results.append({
                    'site_index': si,
                    'initial_tpa': tpa,
                    'final_volume': m['volume'],
                    'final_tpa': m['tpa'],
                    'final_qmd': m['qmd']
                })

        df = pd.DataFrame(results)
        output = df.to_string(index=False)

        assert len(df) == 6  # 3 site indices × 2 densities
        assert all(df['final_volume'] > 0)

        self._save_example_output('yield_table_multi_scenario', output)

        print(f"\n--- Multi-Scenario Yield Table Output ---")
        print(output)

    def _save_example_output(self, example_name: str, output: str):
        """Save example output to file for documentation reference."""
        output_file = self.output_dir / f'{example_name}_output.txt'
        with open(output_file, 'w') as f:
            f.write(output)


class TestSimulationEngineExamples:
    """Tests for SimulationEngine examples."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test output directory."""
        self.output_dir = setup_test_output() / 'documentation_examples'
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self, method):
        """Clean up temp directory."""
        if hasattr(self, 'temp_dir') and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_simulation_engine_basic(self):
        """
        Test: SimulationEngine Quick Start (simulation-engine.md lines 18-33)

        Basic SimulationEngine usage for single stand simulation.
        """
        from pyfvs.simulation_engine import SimulationEngine
        from pathlib import Path

        engine = SimulationEngine(output_dir=Path(self.temp_dir))

        results = engine.simulate_stand(
            species='LP',
            trees_per_acre=500,
            site_index=70,
            years=50,
            save_outputs=False,
            plot_results=False
        )

        output = results.tail().to_string()

        assert isinstance(results, pd.DataFrame)
        assert len(results) > 0
        assert results.iloc[-1]['age'] == 50

        self._save_example_output('simulation_engine_basic', output)

        print(f"\n--- SimulationEngine Basic Output ---")
        print(results.tail().to_string(index=False))

    @pytest.mark.slow
    def test_simulation_engine_yield_table(self):
        """
        Test: SimulationEngine Yield Table (examples.md lines 119-133)

        Generate yield table for multiple species using SimulationEngine.
        """
        from pyfvs.simulation_engine import SimulationEngine
        from pathlib import Path

        engine = SimulationEngine(output_dir=Path(self.temp_dir))

        yield_table = engine.simulate_yield_table(
            species=['LP', 'SP'],
            site_indices=[60, 70, 80],
            planting_densities=[400, 600],
            years=40,
            save_outputs=False
        )

        grouped = yield_table.groupby(['species', 'site_index', 'initial_tpa']).last()
        output = grouped[['age', 'tpa', 'volume']].to_string()

        assert len(yield_table['species'].unique()) == 2
        assert len(yield_table['site_index'].unique()) == 3

        self._save_example_output('simulation_engine_yield_table', output)

        print(f"\n--- SimulationEngine Yield Table Output ---")
        print(output)

    def _save_example_output(self, example_name: str, output: str):
        """Save example output to file for documentation reference."""
        output_file = self.output_dir / f'{example_name}_output.txt'
        with open(output_file, 'w') as f:
            f.write(output)


class TestSpeciesComparisonExample:
    """Tests for species comparison example."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test output directory."""
        self.output_dir = setup_test_output() / 'documentation_examples'
        self.output_dir.mkdir(exist_ok=True)

    def test_species_comparison(self):
        """
        Test: Species Comparison (examples.md lines 136-155)

        Compare all four southern pine species under identical conditions.
        """
        from pyfvs import Stand

        species_list = ['LP', 'SP', 'SA', 'LL']

        output_lines = []
        output_lines.append("Volume at age 30 (SI=70, 500 TPA):")
        output_lines.append("-" * 40)

        volumes = {}
        for sp in species_list:
            stand = Stand.initialize_planted(
                trees_per_acre=500,
                site_index=70,
                species=sp,
                ecounit='M231'
            )
            stand.grow(years=30)
            m = stand.get_metrics()
            volumes[sp] = m['volume']
            output_lines.append(f"{sp}: {m['volume']:,.0f} ft³/acre")

        output = '\n'.join(output_lines)

        # All species should produce positive volume
        for sp, vol in volumes.items():
            assert vol > 0, f"{sp} should have positive volume"

        self._save_example_output('species_comparison', output)

        print(f"\n--- Species Comparison Output ---")
        print(output)

    def _save_example_output(self, example_name: str, output: str):
        """Save example output to file for documentation reference."""
        output_file = self.output_dir / f'{example_name}_output.txt'
        with open(output_file, 'w') as f:
            f.write(output)


class TestDataExportExamples:
    """Tests for data export examples."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test output directory and temp directory for exports."""
        self.output_dir = setup_test_output() / 'documentation_examples'
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self, method):
        """Clean up temp directory."""
        if hasattr(self, 'temp_dir') and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_csv_export(self):
        """
        Test: Export to CSV (examples.md lines 161-173)

        Export yield table and tree list to CSV files.
        """
        from pyfvs import Stand

        stand = Stand.initialize_planted(trees_per_acre=500, site_index=70, species='LP')
        stand.grow(years=50)
        yield_table = stand.get_yield_table_dataframe(years=50, period_length=5)

        # Export yield table
        csv_path = Path(self.temp_dir) / 'yield_table.csv'
        yield_table.to_csv(csv_path, index=False)

        # Export tree list
        tree_list = stand.get_tree_list_dataframe()
        tree_csv_path = Path(self.temp_dir) / 'tree_list.csv'
        tree_list.to_csv(tree_csv_path, index=False)

        # Verify files exist
        assert csv_path.exists()
        assert tree_csv_path.exists()

        # Read back and verify
        loaded_yield = pd.read_csv(csv_path)
        loaded_trees = pd.read_csv(tree_csv_path)

        assert len(loaded_yield) == len(yield_table)
        assert len(loaded_trees) > 0

        output = []
        output.append(f"Yield table exported: {len(loaded_yield)} rows")
        output.append(f"Tree list exported: {len(loaded_trees)} trees")
        output.append(f"\nYield table columns: {', '.join(loaded_yield.columns)}")
        output.append(f"Tree list columns: {', '.join(loaded_trees.columns)}")

        self._save_example_output('csv_export', '\n'.join(output))

        print(f"\n--- CSV Export Output ---")
        for line in output:
            print(line)

    def test_excel_export(self):
        """
        Test: Export to Excel (examples.md lines 177-183)

        Export yield table and tree list to Excel workbook.
        """
        from pyfvs import Stand
        import pandas as pd

        stand = Stand.initialize_planted(trees_per_acre=500, site_index=70, species='LP')
        stand.grow(years=50)
        yield_table = stand.get_yield_table_dataframe(years=50, period_length=5)
        tree_list = stand.get_tree_list_dataframe()

        excel_path = Path(self.temp_dir) / 'simulation_results.xlsx'

        with pd.ExcelWriter(excel_path) as writer:
            yield_table.to_excel(writer, sheet_name='Yield Table', index=False)
            tree_list.to_excel(writer, sheet_name='Tree List', index=False)

        # Verify file exists
        assert excel_path.exists()

        # Read back and verify sheets
        loaded_yield = pd.read_excel(excel_path, sheet_name='Yield Table')
        loaded_trees = pd.read_excel(excel_path, sheet_name='Tree List')

        assert len(loaded_yield) == len(yield_table)
        assert len(loaded_trees) == len(tree_list)

        output = []
        output.append(f"Excel export successful: {excel_path.name}")
        output.append(f"  - Yield Table: {len(loaded_yield)} rows")
        output.append(f"  - Tree List: {len(loaded_trees)} rows")

        self._save_example_output('excel_export', '\n'.join(output))

        print(f"\n--- Excel Export Output ---")
        for line in output:
            print(line)

    def _save_example_output(self, example_name: str, output: str):
        """Save example output to file for documentation reference."""
        output_file = self.output_dir / f'{example_name}_output.txt'
        with open(output_file, 'w') as f:
            f.write(output)


class TestTreeExamples:
    """Tests for individual tree examples from api/tree.md"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test output directory."""
        self.output_dir = setup_test_output() / 'documentation_examples'
        self.output_dir.mkdir(exist_ok=True)

    def test_tree_quick_start(self):
        """
        Test: Tree Quick Start (api/tree.md lines 30-52)

        Create a tree, get volume, and grow one cycle.
        Note: The actual Tree API uses positional args (dbh, height, species, age, crown_ratio)
        """
        from pyfvs import Tree

        # Create tree with the actual API signature
        tree = Tree(
            dbh=6.0,
            height=45.0,
            species='LP',
            age=10
        )

        volume = tree.get_volume()
        initial_volume = f"Volume: {volume:.2f} ft³"

        # Grow with actual API signature
        tree.grow(
            site_index=70,
            competition_factor=0.3,
            pbal=50.0,
            time_step=5
        )

        output = []
        output.append(initial_volume)
        output.append(f"New DBH: {tree.dbh:.2f} inches")
        output.append(f"New height: {tree.height:.1f} feet")

        assert tree.dbh > 6.0  # Should have grown
        assert tree.height > 45.0

        self._save_example_output('tree_quick_start', '\n'.join(output))

        print(f"\n--- Tree Quick Start Output ---")
        for line in output:
            print(line)

    def _save_example_output(self, example_name: str, output: str):
        """Save example output to file for documentation reference."""
        output_file = self.output_dir / f'{example_name}_output.txt'
        with open(output_file, 'w') as f:
            f.write(output)


class TestAPIStandExamples:
    """Tests for Stand API examples from api/stand.md"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test output directory."""
        self.output_dir = setup_test_output() / 'documentation_examples'
        self.output_dir.mkdir(exist_ok=True)

    def test_stand_quick_start(self):
        """
        Test: Stand Quick Start (api/stand.md lines 18-36)

        Create stand with M231 ecounit and grow for 25 years.
        """
        from pyfvs import Stand

        stand = Stand.initialize_planted(
            trees_per_acre=500,
            site_index=70,
            species='LP',
            ecounit='M231'
        )

        stand.grow(years=25)

        metrics = stand.get_metrics()

        output = []
        output.append(f"Volume: {metrics['volume']:.0f} ft³/acre")
        output.append(f"Basal area: {metrics['basal_area']:.1f} ft²/acre")

        assert metrics['volume'] > 0
        assert metrics['basal_area'] > 0

        self._save_example_output('stand_quick_start', '\n'.join(output))

        print(f"\n--- Stand Quick Start Output ---")
        for line in output:
            print(line)

    def _save_example_output(self, example_name: str, output: str):
        """Save example output to file for documentation reference."""
        output_file = self.output_dir / f'{example_name}_output.txt'
        with open(output_file, 'w') as f:
            f.write(output)


def generate_documentation_outputs():
    """
    Run all examples and generate a comprehensive output report.

    This function can be called directly to generate documentation outputs
    without running the full pytest suite.
    """
    import io
    from contextlib import redirect_stdout

    output_dir = Path(__file__).parent.parent / 'test_output' / 'documentation_examples'
    output_dir.mkdir(parents=True, exist_ok=True)

    report_lines = []
    report_lines.append("# PyFVS Documentation Examples - Expected Output\n")
    report_lines.append("This file contains the expected output for all code examples in the PyFVS documentation.\n")
    report_lines.append("Generated automatically by running `uv run pytest tests/test_documentation_examples.py -v`\n\n")

    # Run each example and capture output
    examples = [
        ("Simple Stand Growth", test_simple_stand_growth_standalone),
        ("Basic Stand with Basal Area", test_basic_stand_with_basal_area_standalone),
        ("Ecounit Simulation", test_ecounit_simulation_standalone),
        ("Thinning from Below", test_thinning_from_below_standalone),
        ("Single Thin Scenario", test_single_thin_scenario_standalone),
        ("Multiple Thins", test_multiple_thins_standalone),
        ("Commercial Thin Schedule", test_commercial_thin_schedule_standalone),
        ("Sawtimber Rotation", test_sawtimber_rotation_standalone),
        ("Yield Table from grow()", test_yield_table_from_grow_standalone),
        ("Multi-Scenario Yield Table", test_yield_table_multi_scenario_standalone),
        ("Species Comparison", test_species_comparison_standalone),
        ("Tree Quick Start", test_tree_quick_start_standalone),
        ("Stand Quick Start", test_stand_quick_start_standalone),
    ]

    for name, func in examples:
        report_lines.append(f"## {name}\n")
        report_lines.append("```\n")

        f = io.StringIO()
        with redirect_stdout(f):
            try:
                func()
            except Exception as e:
                print(f"Error: {e}")

        output = f.getvalue()
        report_lines.append(output)
        report_lines.append("```\n\n")

    # Write report
    report_path = output_dir / 'expected_outputs.md'
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))

    print(f"Report generated: {report_path}")
    return report_path


# Standalone functions for generating documentation outputs
def test_simple_stand_growth_standalone():
    from pyfvs import Stand
    stand = Stand.initialize_planted(trees_per_acre=500, site_index=70, species='LP')
    stand.grow(years=30)
    metrics = stand.get_metrics()
    print(f"Age: {stand.age} years")
    print(f"Trees/acre: {metrics['tpa']:.0f}")
    print(f"Volume: {metrics['volume']:.0f} ft³/acre")
    print(f"Mean DBH: {metrics['qmd']:.1f} inches")

def test_basic_stand_with_basal_area_standalone():
    from pyfvs import Stand
    stand = Stand.initialize_planted(trees_per_acre=500, site_index=70, species='LP')
    stand.grow(years=30)
    metrics = stand.get_metrics()
    print(f"Age: {stand.age} years")
    print(f"Trees per acre: {metrics['tpa']:.0f}")
    print(f"Basal area: {metrics['basal_area']:.1f} ft²/acre")
    print(f"Volume: {metrics['volume']:.0f} ft³/acre")

def test_ecounit_simulation_standalone():
    from pyfvs import Stand
    stand = Stand.initialize_planted(trees_per_acre=500, site_index=70, species='LP', ecounit='M231')
    stand.grow(years=25)
    print(f"Volume: {stand.get_metrics()['volume']:.0f} ft³/acre")

def test_thinning_from_below_standalone():
    from pyfvs import Stand
    stand = Stand.initialize_planted(trees_per_acre=800, site_index=70, species='LP')
    stand.grow(years=15)
    stand.thin_from_below(target_tpa=200)
    stand.grow(years=15)
    print(f"Final TPA: {stand.get_metrics()['tpa']:.0f}")

def test_single_thin_scenario_standalone():
    from pyfvs import Stand
    stand = Stand.initialize_planted(trees_per_acre=700, site_index=70, species='LP', ecounit='M231')
    stand.grow(years=15)
    print(f"Pre-thin: {stand.get_metrics()['tpa']:.0f} TPA")
    stand.thin_from_below(target_tpa=300)
    print(f"Post-thin: {stand.get_metrics()['tpa']:.0f} TPA")
    stand.grow(years=15)
    print(f"Final volume: {stand.get_metrics()['volume']:.0f} ft³/acre")

def test_multiple_thins_standalone():
    from pyfvs import Stand
    stand = Stand.initialize_planted(trees_per_acre=800, site_index=75, species='LP', ecounit='M231')
    stand.grow(years=12)
    stand.thin_from_below(target_tpa=400)
    stand.grow(years=8)
    stand.thin_from_below(target_tpa=200)
    stand.grow(years=15)
    metrics = stand.get_metrics()
    print(f"Final: {metrics['volume']:.0f} ft³/acre, {metrics['qmd']:.1f}\" DBH")

def test_commercial_thin_schedule_standalone():
    from pyfvs import Stand
    stand = Stand.initialize_planted(trees_per_acre=700, site_index=70, species='LP', ecounit='M231')
    stand.grow(years=12)
    print(f"Pre-thin: {stand.get_metrics()['tpa']:.0f} TPA, {stand.get_metrics()['qmd']:.1f}\" QMD")
    stand.thin_from_below(target_tpa=350)
    print(f"Post-thin: {stand.get_metrics()['tpa']:.0f} TPA")
    stand.grow(years=8)
    stand.thin_from_below(target_tpa=180)
    stand.grow(years=10)
    print(f"Final: {stand.get_metrics()['volume']:.0f} ft³/acre, {stand.get_metrics()['qmd']:.1f}\" QMD")

def test_sawtimber_rotation_standalone():
    from pyfvs import Stand
    stand = Stand.initialize_planted(trees_per_acre=600, site_index=75, species='LP')
    stand.grow(years=15)
    stand.thin_from_below(target_tpa=250)
    stand.grow(years=10)
    stand.thin_from_below(target_tpa=120)
    stand.grow(years=15)
    metrics = stand.get_metrics()
    print(f"Final DBH: {metrics['qmd']:.1f} inches")
    print(f"Final volume: {metrics['volume']:.0f} ft³/acre")

def test_yield_table_from_grow_standalone():
    from pyfvs import Stand
    stand = Stand.initialize_planted(trees_per_acre=500, site_index=70, species='LP')
    yield_table = stand.get_yield_table_dataframe(years=50, period_length=5)
    # Rename columns for user-friendly display
    display_df = yield_table[['Age', 'TPA', 'QMD', 'TCuFt']].copy()
    display_df.columns = ['age', 'tpa', 'qmd', 'volume']
    print(display_df.to_string(index=False))

def test_yield_table_multi_scenario_standalone():
    from pyfvs import Stand
    import pandas as pd
    results = []
    for si in [60, 70, 80]:
        for tpa in [400, 600]:
            stand = Stand.initialize_planted(trees_per_acre=tpa, site_index=si, species='LP', ecounit='M231')
            stand.grow(years=30)
            m = stand.get_metrics()
            results.append({'site_index': si, 'initial_tpa': tpa, 'final_volume': m['volume'],
                          'final_tpa': m['tpa'], 'final_qmd': m['qmd']})
    df = pd.DataFrame(results)
    print(df.to_string(index=False))

def test_species_comparison_standalone():
    from pyfvs import Stand
    species_list = ['LP', 'SP', 'SA', 'LL']
    print("Volume at age 30 (SI=70, 500 TPA):")
    print("-" * 40)
    for sp in species_list:
        stand = Stand.initialize_planted(trees_per_acre=500, site_index=70, species=sp, ecounit='M231')
        stand.grow(years=30)
        m = stand.get_metrics()
        print(f"{sp}: {m['volume']:,.0f} ft³/acre")

def test_tree_quick_start_standalone():
    from pyfvs import Tree
    tree = Tree(dbh=6.0, height=45.0, species='LP', age=10)
    volume = tree.get_volume()
    print(f"Volume: {volume:.2f} ft³")
    tree.grow(site_index=70, competition_factor=0.3, pbal=50.0, time_step=5)
    print(f"New DBH: {tree.dbh:.2f} inches")
    print(f"New height: {tree.height:.1f} feet")

def test_stand_quick_start_standalone():
    from pyfvs import Stand
    stand = Stand.initialize_planted(trees_per_acre=500, site_index=70, species='LP', ecounit='M231')
    stand.grow(years=25)
    metrics = stand.get_metrics()
    print(f"Volume: {metrics['volume']:.0f} ft³/acre")
    print(f"Basal area: {metrics['basal_area']:.1f} ft²/acre")


if __name__ == '__main__':
    generate_documentation_outputs()

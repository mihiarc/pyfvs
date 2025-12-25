#!/usr/bin/env python
"""
FVS-Python Validation Suite

Main entry point for running validation tests against official FVS outputs
or verifying internal consistency of model predictions.
"""
import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from validation.scripts.compare_results import (
    ValidationMetrics,
    calculate_validation_metrics,
    check_acceptance_criteria,
    verify_bakuzis_relationships,
    generate_comparison_summary,
)
from validation.scripts.visualize import (
    plot_stand_comparison,
    plot_residuals,
    plot_bakuzis_matrix,
    plot_validation_summary,
    HAS_MATPLOTLIB,
)

console = Console()


@dataclass
class ValidationResult:
    """Container for validation test results."""
    test_name: str
    component: str
    passed: bool
    message: str
    metrics: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None


class ValidationSuite:
    """Run complete validation against FVS reference or internal verification."""

    def __init__(
        self,
        reference_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        verbose: bool = False
    ):
        """
        Initialize validation suite.

        Args:
            reference_dir: Directory containing FVS reference outputs
            output_dir: Directory for validation results
            verbose: Enable verbose output
        """
        self.validation_dir = Path(__file__).parent
        self.reference_dir = reference_dir or self.validation_dir / "reference_data"
        self.output_dir = output_dir or self.validation_dir / "results"
        self.verbose = verbose

        self.results: List[ValidationResult] = []
        self.start_time = None

    def run_all(self) -> Dict[str, Any]:
        """
        Execute full validation suite.

        Returns:
            Summary dictionary with all results
        """
        self.start_time = datetime.now(timezone.utc)
        self.results = []

        console.print(Panel.fit(
            "[bold blue]FVS-Python Validation Suite[/bold blue]\n"
            f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            border_style="blue"
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Level 1: Component models
            task = progress.add_task("Validating component models...", total=None)
            self.validate_component_models()
            progress.update(task, completed=True)

            # Level 2: Single tree growth
            task = progress.add_task("Validating single tree growth...", total=None)
            self.validate_single_tree_growth()
            progress.update(task, completed=True)

            # Level 3: Stand simulations
            task = progress.add_task("Validating stand simulations...", total=None)
            self.validate_stand_simulations()
            progress.update(task, completed=True)

            # Level 4: Bakuzis verification
            task = progress.add_task("Verifying Bakuzis relationships...", total=None)
            self.verify_bakuzis()
            progress.update(task, completed=True)

        # Generate summary and report
        summary = self.generate_summary()
        self.save_results(summary)
        self.print_summary(summary)

        return summary

    def validate_component_models(self) -> None:
        """Level 1: Validate individual equation implementations."""
        from pyfvs.height_diameter import create_height_diameter_model
        from pyfvs.bark_ratio import create_bark_ratio_model
        from pyfvs.crown_ratio import create_crown_ratio_model
        from pyfvs.crown_width import create_crown_width_model

        species_list = ["LP", "SP", "SA", "LL"]

        # Height-Diameter validation
        for species in species_list:
            model = create_height_diameter_model(species)
            test_dbhs = [3.0, 5.0, 8.0, 10.0, 15.0]

            all_valid = True
            for dbh in test_dbhs:
                height = model.predict_height(dbh)
                # Basic sanity checks
                if height <= 4.5 or height > 150:
                    all_valid = False
                    break
                # Height should increase with DBH
                if dbh > 3.0:
                    prev_height = model.predict_height(dbh - 2)
                    if height <= prev_height:
                        all_valid = False
                        break

            self.results.append(ValidationResult(
                test_name=f"height_diameter_{species}",
                component="height_diameter",
                passed=all_valid,
                message=f"Height-diameter model for {species}: {'PASS' if all_valid else 'FAIL'}",
                details={"species": species, "test_dbhs": test_dbhs},
            ))

        # Bark Ratio validation
        for species in species_list:
            model = create_bark_ratio_model(species)
            test_dobs = [5.0, 10.0, 15.0, 20.0]

            all_valid = True
            for dob in test_dobs:
                ratio = model.calculate_bark_ratio(dob)
                # Bark ratio should be between 0.80 and 0.99 per FVS spec
                if not (0.80 <= ratio <= 0.99):
                    all_valid = False
                    break

            self.results.append(ValidationResult(
                test_name=f"bark_ratio_{species}",
                component="bark_ratio",
                passed=all_valid,
                message=f"Bark ratio model for {species}: {'PASS' if all_valid else 'FAIL'}",
                details={"species": species, "test_dobs": test_dobs},
            ))

        # Crown Ratio validation
        for species in species_list:
            model = create_crown_ratio_model(species)
            test_relsdis = [2.0, 5.0, 8.0, 10.0]

            all_valid = True
            prev_acr = None
            for relsdi in test_relsdis:
                acr = model.calculate_average_crown_ratio(relsdi)
                # Crown ratio should be between 0.05 and 0.95
                if not (0.05 <= acr <= 0.95):
                    all_valid = False
                    break
                # Crown ratio should decrease with increasing RELSDI
                if prev_acr is not None and acr > prev_acr:
                    # This can vary by species equation, so just warn
                    if self.verbose:
                        console.print(f"  [yellow]Warning: CR increased with RELSDI for {species}[/yellow]")
                prev_acr = acr

            self.results.append(ValidationResult(
                test_name=f"crown_ratio_{species}",
                component="crown_ratio",
                passed=all_valid,
                message=f"Crown ratio model for {species}: {'PASS' if all_valid else 'FAIL'}",
                details={"species": species, "test_relsdis": test_relsdis},
            ))

        # Crown Width validation
        for species in species_list:
            model = create_crown_width_model(species)
            test_dbhs = [3.0, 5.0, 8.0, 10.0, 15.0]

            all_valid = True
            prev_fcw = None
            for dbh in test_dbhs:
                fcw = model.calculate_forest_grown_crown_width(dbh)
                ocw = model.calculate_open_grown_crown_width(dbh)

                # Basic bounds checking
                if fcw < 0 or fcw > 60 or ocw < 0 or ocw > 60:
                    all_valid = False
                    break

                # Crown width should generally increase with DBH
                if prev_fcw is not None and fcw < prev_fcw * 0.9:  # Allow 10% variation
                    all_valid = False
                    break
                prev_fcw = fcw

            self.results.append(ValidationResult(
                test_name=f"crown_width_{species}",
                component="crown_width",
                passed=all_valid,
                message=f"Crown width model for {species}: {'PASS' if all_valid else 'FAIL'}",
                details={"species": species, "test_dbhs": test_dbhs},
            ))

    def validate_single_tree_growth(self) -> None:
        """Level 2: Validate tree-level growth predictions."""
        from pyfvs.tree import Tree

        species_list = ["LP", "SP", "SA", "LL"]

        for species in species_list:
            # Test small tree growth (DBH < 1")
            tree = Tree(dbh=0.5, height=5.0, species=species, age=5)
            initial_height = tree.height
            tree.grow(site_index=70, competition_factor=0.3, time_step=5)

            small_tree_valid = (
                tree.height > initial_height and
                tree.dbh >= 0.5 and
                tree.age == 10
            )

            self.results.append(ValidationResult(
                test_name=f"small_tree_growth_{species}",
                component="single_tree_growth",
                passed=small_tree_valid,
                message=f"Small tree growth for {species}: {'PASS' if small_tree_valid else 'FAIL'}",
                details={
                    "species": species,
                    "initial_height": initial_height,
                    "final_height": tree.height,
                    "height_growth": tree.height - initial_height,
                },
            ))

            # Test large tree growth (DBH >= 5")
            tree = Tree(dbh=8.0, height=50.0, species=species, age=25)
            initial_dbh = tree.dbh
            initial_height = tree.height
            tree.grow(site_index=70, competition_factor=0.5, ba=100, pbal=50, time_step=5)

            large_tree_valid = (
                tree.dbh > initial_dbh and
                tree.height > initial_height and
                tree.age == 30
            )

            self.results.append(ValidationResult(
                test_name=f"large_tree_growth_{species}",
                component="single_tree_growth",
                passed=large_tree_valid,
                message=f"Large tree growth for {species}: {'PASS' if large_tree_valid else 'FAIL'}",
                details={
                    "species": species,
                    "initial_dbh": initial_dbh,
                    "final_dbh": tree.dbh,
                    "dbh_growth": tree.dbh - initial_dbh,
                },
            ))

            # Test transition zone (1-3" DBH)
            tree = Tree(dbh=2.0, height=20.0, species=species, age=10)
            initial_dbh = tree.dbh
            tree.grow(site_index=70, competition_factor=0.4, ba=80, pbal=40, time_step=5)

            transition_valid = (
                tree.dbh > initial_dbh and
                tree.height > 20.0
            )

            self.results.append(ValidationResult(
                test_name=f"transition_growth_{species}",
                component="single_tree_growth",
                passed=transition_valid,
                message=f"Transition zone growth for {species}: {'PASS' if transition_valid else 'FAIL'}",
                details={
                    "species": species,
                    "initial_dbh": initial_dbh,
                    "final_dbh": tree.dbh,
                },
            ))

    def validate_stand_simulations(self) -> None:
        """Level 3: Validate full stand simulations."""
        from pyfvs.stand import Stand

        # Test scenarios
        scenarios = [
            {"species": "LP", "site_index": 70, "tpa": 500},
            {"species": "SP", "site_index": 65, "tpa": 450},
            {"species": "SA", "site_index": 70, "tpa": 550},
            {"species": "LL", "site_index": 60, "tpa": 400},
        ]

        for scenario in scenarios:
            species = scenario["species"]
            si = scenario["site_index"]
            tpa = scenario["tpa"]

            stand = Stand.initialize_planted(
                trees_per_acre=tpa,
                site_index=si,
                species=species
            )

            initial_tpa = len(stand.trees)
            initial_ba = stand.calculate_basal_area()

            # Grow for 25 years (5 cycles)
            stand.grow(years=25)

            final_metrics = stand.get_metrics()

            # Verify expected stand behavior
            valid_conditions = [
                final_metrics['tpa'] < initial_tpa,  # Mortality should occur
                final_metrics['basal_area'] > initial_ba,  # BA should increase
                final_metrics['qmd'] > 0.5,  # Trees should grow
                final_metrics['top_height'] > 20,  # Significant height growth
            ]

            all_valid = all(valid_conditions)

            self.results.append(ValidationResult(
                test_name=f"stand_simulation_{species}_SI{si}_T{tpa}",
                component="stand_simulation",
                passed=all_valid,
                message=f"Stand simulation for {species}: {'PASS' if all_valid else 'FAIL'}",
                metrics=final_metrics,
                details={
                    "scenario": scenario,
                    "initial_tpa": initial_tpa,
                    "final_tpa": final_metrics['tpa'],
                    "conditions_met": valid_conditions,
                },
            ))

    def verify_bakuzis(self) -> None:
        """Level 4: Verify Bakuzis Matrix relationships."""
        from pyfvs.stand import Stand

        stand = Stand.initialize_planted(
            trees_per_acre=500,
            site_index=70,
            species="LP"
        )

        # Collect yield data over simulation
        yield_data = {"TPA": [], "BA": [], "QMD": [], "TopHt": [], "TCuFt": []}
        ages = []

        # Initial state
        metrics = stand.get_metrics()
        ages.append(0)
        for key in yield_data:
            if key == "TCuFt":
                yield_data[key].append(metrics.get("volume", 0))
            else:
                yield_data[key].append(metrics.get(key.lower(), metrics.get(key, 0)))

        # Grow and collect data
        for year in range(5, 55, 5):
            stand.grow(years=5)
            metrics = stand.get_metrics()
            ages.append(year)

            yield_data["TPA"].append(metrics["tpa"])
            yield_data["BA"].append(metrics["basal_area"])
            yield_data["QMD"].append(metrics["qmd"])
            yield_data["TopHt"].append(metrics["top_height"])
            yield_data["TCuFt"].append(metrics["volume"])

        # Verify relationships
        bakuzis_results = verify_bakuzis_relationships(yield_data, ages)

        all_valid = all(bakuzis_results.values())

        self.results.append(ValidationResult(
            test_name="bakuzis_matrix_verification",
            component="bakuzis_matrix",
            passed=all_valid,
            message=f"Bakuzis Matrix verification: {'PASS' if all_valid else 'FAIL'}",
            details=bakuzis_results,
        ))

        # Generate Bakuzis plot if matplotlib available
        if HAS_MATPLOTLIB:
            try:
                figures_dir = self.output_dir / "figures"
                figures_dir.mkdir(parents=True, exist_ok=True)
                plot_bakuzis_matrix(
                    yield_data, ages, "LP_SI70_T500",
                    output_path=figures_dir / "bakuzis_verification.png"
                )
            except Exception as e:
                if self.verbose:
                    console.print(f"[yellow]Warning: Could not generate Bakuzis plot: {e}[/yellow]")

    def generate_summary(self) -> Dict[str, Any]:
        """Generate validation summary."""
        end_time = datetime.now(timezone.utc)

        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        # Group by component
        by_component = {}
        for result in self.results:
            if result.component not in by_component:
                by_component[result.component] = {"passed": 0, "failed": 0}
            if result.passed:
                by_component[result.component]["passed"] += 1
            else:
                by_component[result.component]["failed"] += 1

        return {
            "validation_date": end_time.isoformat(),
            "duration_seconds": (end_time - self.start_time).total_seconds(),
            "total_tests": len(self.results),
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / len(self.results) * 100) if self.results else 0,
            "by_component": by_component,
            "results": [asdict(r) for r in self.results],
        }

    def save_results(self, summary: Dict[str, Any]) -> None:
        """Save validation results to files."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON summary
        with open(self.output_dir / "validation_results.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)

        # Save CSV of results
        try:
            import pandas as pd
            results_df = pd.DataFrame([
                {
                    "test_name": r.test_name,
                    "component": r.component,
                    "passed": r.passed,
                    "message": r.message,
                }
                for r in self.results
            ])
            results_df.to_csv(self.output_dir / "validation_results.csv", index=False)
        except ImportError:
            pass  # Skip CSV if pandas not available

        if self.verbose:
            console.print(f"[green]Results saved to {self.output_dir}[/green]")

    def print_summary(self, summary: Dict[str, Any]) -> None:
        """Print validation summary to console."""
        # Create summary table
        table = Table(title="Validation Summary", show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Passed", style="green", justify="right")
        table.add_column("Failed", style="red", justify="right")
        table.add_column("Pass Rate", justify="right")

        for component, counts in summary["by_component"].items():
            total = counts["passed"] + counts["failed"]
            rate = f"{counts['passed']/total*100:.0f}%" if total > 0 else "N/A"
            table.add_row(
                component,
                str(counts["passed"]),
                str(counts["failed"]),
                rate
            )

        # Add totals row
        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold green]{summary['passed']}[/bold green]",
            f"[bold red]{summary['failed']}[/bold red]",
            f"[bold]{summary['pass_rate']:.1f}%[/bold]"
        )

        console.print(table)

        # Print failed tests if any
        if summary["failed"] > 0:
            console.print("\n[bold red]Failed Tests:[/bold red]")
            for result in self.results:
                if not result.passed:
                    console.print(f"  [red]✗[/red] {result.test_name}: {result.message}")

        # Overall status
        if summary["pass_rate"] >= 100:
            console.print("\n[bold green]✓ All validation tests passed![/bold green]")
        elif summary["pass_rate"] >= 90:
            console.print(f"\n[bold yellow]⚠ {summary['pass_rate']:.1f}% of tests passed[/bold yellow]")
        else:
            console.print(f"\n[bold red]✗ Only {summary['pass_rate']:.1f}% of tests passed[/bold red]")


def main():
    """Main entry point for validation suite."""
    parser = argparse.ArgumentParser(
        description="FVS-Python Validation Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_validation.py                    # Run all validation tests
  python run_validation.py --level component  # Run only component tests
  python run_validation.py -v                 # Verbose output
        """
    )

    parser.add_argument(
        "--level",
        choices=["all", "component", "tree", "stand", "bakuzis"],
        default="all",
        help="Validation level to run (default: all)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for results"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    suite = ValidationSuite(
        output_dir=args.output,
        verbose=args.verbose
    )

    if args.level == "all":
        summary = suite.run_all()
    else:
        # Run specific levels
        suite.start_time = datetime.now(timezone.utc)
        suite.results = []

        if args.level == "component":
            suite.validate_component_models()
        elif args.level == "tree":
            suite.validate_single_tree_growth()
        elif args.level == "stand":
            suite.validate_stand_simulations()
        elif args.level == "bakuzis":
            suite.verify_bakuzis()

        summary = suite.generate_summary()
        suite.save_results(summary)
        suite.print_summary(summary)

    # Exit with non-zero status if tests failed
    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()

"""Validate FVS-Python predictions against published USFS reference data.

This script runs FVS-Python simulations and compares the results to published
yield tables from USDA Forest Service sources.
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fvs_python.stand import Stand
from fvs_python.config_loader import ConfigLoader

console = Console()

REFERENCE_DATA_DIR = Path(__file__).parent.parent / "reference_data"


@dataclass
class ComparisonResult:
    """Results from comparing a single metric."""

    metric: str
    reference_value: float
    predicted_value: float
    absolute_error: float
    percent_error: float
    within_tolerance: bool
    tolerance_pct: float


@dataclass
class YieldTableComparison:
    """Results from comparing an entire yield table."""

    species: str
    site_index: int
    initial_tpa: int
    results_by_age: dict = field(default_factory=dict)
    overall_pass: bool = True
    summary_stats: dict = field(default_factory=dict)


def load_reference_data() -> dict:
    """Load the combined reference data."""
    ref_path = REFERENCE_DATA_DIR / "combined_reference_data.json"
    if not ref_path.exists():
        raise FileNotFoundError(
            f"Reference data not found at {ref_path}. "
            "Run download_reference_data.py first."
        )
    with open(ref_path) as f:
        return json.load(f)


def load_acceptance_criteria() -> dict:
    """Load acceptance criteria."""
    criteria_path = REFERENCE_DATA_DIR / "acceptance_criteria.yaml"
    with open(criteria_path) as f:
        return yaml.safe_load(f)


def run_simulation(
    species: str,
    site_index: float,
    initial_tpa: int,
    max_age: int = 50,
    time_step: int = 5,
) -> dict:
    """Run an FVS-Python simulation and return yield table data.

    Args:
        species: Species code (LP, SP, SA, LL)
        site_index: Site index value
        initial_tpa: Initial trees per acre
        max_age: Maximum simulation age
        time_step: Years per growth cycle

    Returns:
        Dictionary with yield table data by age
    """
    # Initialize stand using class method
    stand = Stand.initialize_planted(
        trees_per_acre=initial_tpa,
        site_index=site_index,
        species=species,
    )

    results = {}

    # Simulate growth
    for year in range(0, max_age + 1, time_step):
        if year > 0:
            stand.grow(time_step)

        # Collect stand metrics using get_metrics()
        metrics = stand.get_metrics()
        results[year] = {
            "age": year,
            "tpa": metrics.get("tpa", len(stand.trees)),
            "ba_sqft_ac": metrics.get("basal_area", 0),
            "qmd_in": metrics.get("qmd", 0),
            "height_ft": metrics.get("mean_height", 0),
            "top_height_ft": metrics.get("top_height", metrics.get("mean_height", 0)),
            "vol_cuft_ac": metrics.get("volume", 0),
        }

    return results


def compare_metrics(
    reference: dict,
    predicted: dict,
    criteria: dict,
) -> list[ComparisonResult]:
    """Compare predicted metrics against reference values.

    Args:
        reference: Reference yield table row
        predicted: Predicted yield table row
        criteria: Acceptance criteria

    Returns:
        List of comparison results
    """
    results = []

    metric_mapping = {
        "tpa": ("tpa", "tpa"),
        "ba_sqft_ac": ("ba_sqft_ac", "basal_area"),
        "qmd_in": ("qmd_in", "qmd"),
        "height_ft": ("height_ft", "top_height"),
        "vol_cuft_ac": ("vol_cuft_ac", "volume"),
    }

    stand_criteria = criteria.get("stand_level", {})

    for metric_key, (ref_key, criteria_key) in metric_mapping.items():
        ref_val = reference.get(ref_key)
        pred_val = predicted.get(metric_key)

        if ref_val is None or pred_val is None:
            continue

        if ref_val == 0:
            abs_error = abs(pred_val - ref_val)
            pct_error = 100.0 if pred_val != 0 else 0.0
        else:
            abs_error = abs(pred_val - ref_val)
            pct_error = abs(pred_val - ref_val) / ref_val * 100

        tolerance = stand_criteria.get(criteria_key, {}).get("max_percent_error", 10)
        within_tol = pct_error <= tolerance

        results.append(
            ComparisonResult(
                metric=metric_key,
                reference_value=ref_val,
                predicted_value=pred_val,
                absolute_error=abs_error,
                percent_error=pct_error,
                within_tolerance=within_tol,
                tolerance_pct=tolerance,
            )
        )

    return results


def validate_yield_table(
    species_code: str,
    yield_table_id: str,
    reference_data: dict,
    criteria: dict,
) -> YieldTableComparison:
    """Validate FVS-Python against a reference yield table.

    Args:
        species_code: Species code (LP, SP, SA, LL)
        yield_table_id: ID of the yield table to validate against
        reference_data: Reference data dictionary
        criteria: Acceptance criteria

    Returns:
        YieldTableComparison with detailed results
    """
    # Map species code to reference data key
    species_map = {
        "LP": "loblolly_pine",
        "SP": "shortleaf_pine",
        "SA": "slash_pine",
        "LL": "longleaf_pine",
    }

    species_key = species_map.get(species_code)
    if not species_key:
        raise ValueError(f"Unknown species code: {species_code}")

    species_data = reference_data["species"].get(species_key)
    if not species_data:
        raise ValueError(f"No reference data for {species_key}")

    yield_table = species_data["yield_tables"].get(yield_table_id)
    if not yield_table:
        raise ValueError(f"No yield table {yield_table_id} for {species_key}")

    site_index = yield_table["site_index"]
    initial_tpa = yield_table["initial_tpa"]
    ref_data_rows = yield_table["data"]

    # Get max age from reference data
    max_age = max(row["age"] for row in ref_data_rows)

    # Run simulation
    predicted = run_simulation(
        species=species_code,
        site_index=site_index,
        initial_tpa=initial_tpa,
        max_age=max_age,
        time_step=5,
    )

    # Compare at each age
    comparison = YieldTableComparison(
        species=species_code,
        site_index=site_index,
        initial_tpa=initial_tpa,
    )

    all_errors = {"tpa": [], "ba_sqft_ac": [], "qmd_in": [], "height_ft": [], "vol_cuft_ac": []}
    all_pass = True

    for ref_row in ref_data_rows:
        age = ref_row["age"]
        if age not in predicted:
            continue

        pred_row = predicted[age]
        metrics = compare_metrics(ref_row, pred_row, criteria)
        comparison.results_by_age[age] = metrics

        for m in metrics:
            if m.metric in all_errors:
                all_errors[m.metric].append(m.percent_error)
            if not m.within_tolerance:
                all_pass = False

    # Calculate summary statistics
    for metric, errors in all_errors.items():
        if errors:
            comparison.summary_stats[metric] = {
                "mean_error_pct": sum(errors) / len(errors),
                "max_error_pct": max(errors),
                "min_error_pct": min(errors),
            }

    comparison.overall_pass = all_pass
    return comparison


def display_comparison_table(comparison: YieldTableComparison):
    """Display a comparison table in the console."""
    title = f"{comparison.species} SI={comparison.site_index} TPA={comparison.initial_tpa}"
    status = "[green]PASS[/green]" if comparison.overall_pass else "[red]FAIL[/red]"

    table = Table(
        title=f"{title} - {status}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("Age", justify="right", style="dim")
    table.add_column("Metric", style="cyan")
    table.add_column("Reference", justify="right")
    table.add_column("Predicted", justify="right")
    table.add_column("Error %", justify="right")
    table.add_column("Status", justify="center")

    for age in sorted(comparison.results_by_age.keys()):
        metrics = comparison.results_by_age[age]
        for i, m in enumerate(metrics):
            age_str = str(age) if i == 0 else ""
            status_str = "[green]OK[/green]" if m.within_tolerance else f"[red]>{m.tolerance_pct}%[/red]"

            table.add_row(
                age_str,
                m.metric,
                f"{m.reference_value:.1f}",
                f"{m.predicted_value:.1f}",
                f"{m.percent_error:.1f}%",
                status_str,
            )

    console.print(table)

    # Summary stats
    if comparison.summary_stats:
        summary_table = Table(title="Summary Statistics", box=box.SIMPLE)
        summary_table.add_column("Metric")
        summary_table.add_column("Mean Error %", justify="right")
        summary_table.add_column("Max Error %", justify="right")

        for metric, stats in comparison.summary_stats.items():
            summary_table.add_row(
                metric,
                f"{stats['mean_error_pct']:.1f}%",
                f"{stats['max_error_pct']:.1f}%",
            )

        console.print(summary_table)


def run_all_validations(species_filter: Optional[str] = None, verbose: bool = True):
    """Run validation against all reference yield tables.

    Args:
        species_filter: Optional species code to filter (LP, SP, SA, LL)
        verbose: Whether to display detailed output

    Returns:
        Dictionary with validation results
    """
    reference_data = load_reference_data()
    criteria = load_acceptance_criteria()

    species_map = {
        "LP": "loblolly_pine",
        "SP": "shortleaf_pine",
        "SA": "slash_pine",
        "LL": "longleaf_pine",
    }

    results = {}
    total_pass = 0
    total_fail = 0

    for species_code, species_key in species_map.items():
        if species_filter and species_code != species_filter:
            continue

        species_data = reference_data["species"].get(species_key)
        if not species_data:
            continue

        yield_tables = species_data.get("yield_tables", {})

        for table_id in yield_tables:
            if verbose:
                console.print(f"\n[bold]Validating {species_code} - {table_id}[/bold]")

            try:
                comparison = validate_yield_table(
                    species_code=species_code,
                    yield_table_id=table_id,
                    reference_data=reference_data,
                    criteria=criteria,
                )

                results[f"{species_code}_{table_id}"] = comparison

                if verbose:
                    display_comparison_table(comparison)

                if comparison.overall_pass:
                    total_pass += 1
                else:
                    total_fail += 1

            except Exception as e:
                console.print(f"[red]Error validating {species_code} {table_id}: {e}[/red]")
                total_fail += 1

    # Final summary
    console.print("\n")
    console.print(
        Panel(
            f"[bold]Validation Summary[/bold]\n\n"
            f"Total yield tables: {total_pass + total_fail}\n"
            f"[green]Passed: {total_pass}[/green]\n"
            f"[red]Failed: {total_fail}[/red]",
            title="Results",
            border_style="blue",
        )
    )

    return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate FVS-Python against reference data")
    parser.add_argument(
        "--species",
        choices=["LP", "SP", "SA", "LL"],
        help="Filter to specific species",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed output",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Save results to JSON file",
    )

    args = parser.parse_args()

    console.print("[bold blue]FVS-Python Validation Against Reference Data[/bold blue]\n")

    results = run_all_validations(
        species_filter=args.species,
        verbose=not args.quiet,
    )

    if args.output:
        # Convert results to serializable format
        output_data = {}
        for key, comparison in results.items():
            output_data[key] = {
                "species": comparison.species,
                "site_index": comparison.site_index,
                "initial_tpa": comparison.initial_tpa,
                "overall_pass": comparison.overall_pass,
                "summary_stats": comparison.summary_stats,
            }

        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        console.print(f"\n[green]Results saved to {args.output}[/green]")


if __name__ == "__main__":
    main()

"""
Side-by-side comparison of pyfvs vs native FVS growth simulations.

Runs identical stand initialization through both the Python (pyfvs.Stand)
and native Fortran (pyfvs.native.NativeStand) implementations, then
computes validation metrics for each output variable.

Usage:
    python -m validation.native.compare_native

    Or from Python:
        from validation.native.compare_native import compare_stand_growth
        results = compare_stand_growth(500, 70, 'LP', 'SN', 50)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from rich.console import Console
from rich.table import Table

# Add project root to path for validation imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pyfvs import Stand
from pyfvs.native import NativeStand, fvs_library_available
from validation.scripts.compare_results import (
    ValidationMetrics,
    calculate_validation_metrics,
    check_acceptance_criteria,
)

console = Console()


def compare_stand_growth(
    trees_per_acre: float,
    site_index: float,
    species: str,
    variant: str = "SN",
    years: int = 50,
    ecounit: str = "",
) -> Dict:
    """Run the same scenario through both pyfvs and native FVS, compare results.

    Args:
        trees_per_acre: Planting density.
        site_index: Site index value.
        species: Two-letter species code.
        variant: FVS variant code.
        years: Number of years to simulate.
        ecounit: Ecological unit code (pyfvs only).

    Returns:
        Dictionary containing:
            - 'pyfvs': pyfvs Stand metrics per cycle
            - 'native': NativeStand metrics per cycle
            - 'metrics': ValidationMetrics per output variable
            - 'acceptance': Pass/fail per output variable
    """
    if not fvs_library_available(variant):
        raise RuntimeError(
            f"FVS {variant} library not available. "
            f"Set FVS_LIB_PATH or install to ~/.fvs/lib/."
        )

    # --- Run pyfvs simulation ---
    pyfvs_kwargs = {
        "trees_per_acre": trees_per_acre,
        "site_index": site_index,
        "species": species,
        "variant": variant,
    }
    if ecounit:
        pyfvs_kwargs["ecounit"] = ecounit

    stand = Stand.initialize_planted(**pyfvs_kwargs)
    pyfvs_cycles = []

    cycle_length = 5 if variant in ("SN", "OP") else 10
    num_cycles = years // cycle_length

    # PyFVS now initializes trees at HTCALC establishment dimensions
    # (age=cycle_length), matching native FVS cycle 1 (LSKIPH, no growth).
    # Record initial state as cycle 1, then grow for remaining cycles.
    metrics = stand.get_metrics()
    pyfvs_cycles.append({
        "cycle": 1,
        "age": cycle_length,
        "tpa": metrics["tpa"],
        "basal_area": metrics["basal_area"],
        "qmd": metrics["qmd"],
        "top_height": metrics.get("top_height", 0.0),
        "volume": metrics.get("volume", 0.0),
    })

    for cycle in range(1, num_cycles):
        stand.grow(years=cycle_length)
        metrics = stand.get_metrics()
        pyfvs_cycles.append({
            "cycle": cycle + 1,
            "age": (cycle + 1) * cycle_length,
            "tpa": metrics["tpa"],
            "basal_area": metrics["basal_area"],
            "qmd": metrics["qmd"],
            "top_height": metrics.get("top_height", 0.0),
            "volume": metrics.get("volume", 0.0),
        })

    # --- Run native FVS simulation at each checkpoint ---
    # Run separate native simulations for each cycle endpoint to get
    # accurate tree-level metrics (the IOSUM summary has limited precision).
    from pyfvs.native.library_loader import clear_library_cache

    native_cycles = []
    for cycle_num in range(1, num_cycles + 1):
        cycle_years = cycle_num * cycle_length
        clear_library_cache()
        with NativeStand(variant=variant) as ns:
            ns.initialize_planted(trees_per_acre, site_index, species)
            ns.grow(cycle_years)
            metrics = ns.get_metrics()
            native_cycles.append({
                "cycle": cycle_num,
                "age": cycle_years,
                "tpa": metrics["tpa"],
                "basal_area": metrics["basal_area"],
                "qmd": metrics["qmd"],
                "top_height": metrics["top_height"],
                "volume": metrics["volume"],
            })

    # --- Compute validation metrics ---
    # Align by cycle count (use minimum common cycles)
    n_compare = min(len(pyfvs_cycles), len(native_cycles))

    validation_results = {}
    acceptance_results = {}

    output_vars = ["tpa", "basal_area", "qmd", "top_height", "volume"]
    metric_type_map = {
        "tpa": "tpa",
        "basal_area": "basal_area",
        "qmd": "diameter",
        "top_height": "height",
        "volume": "volume",
    }

    for var in output_vars:
        if n_compare > 0:
            observed = np.array([native_cycles[i][var] for i in range(n_compare)])
            predicted = np.array([pyfvs_cycles[i][var] for i in range(n_compare)])

            # Skip if all zeros (metric not available in native output)
            if np.all(observed == 0) and np.all(predicted == 0):
                continue

            try:
                vm = calculate_validation_metrics(observed, predicted)
                validation_results[var] = vm
                passed, msg = check_acceptance_criteria(vm, metric_type_map[var])
                acceptance_results[var] = {"passed": passed, "message": msg}
            except (ValueError, ZeroDivisionError):
                pass

    return {
        "scenario": {
            "species": species,
            "variant": variant,
            "trees_per_acre": trees_per_acre,
            "site_index": site_index,
            "years": years,
        },
        "pyfvs": pyfvs_cycles,
        "native": native_cycles,
        "metrics": validation_results,
        "acceptance": acceptance_results,
        "n_cycles_compared": n_compare,
    }


def generate_validation_report(
    results: Dict,
    output_dir: Optional[str] = None,
) -> None:
    """Print a rich-formatted validation report and optionally save to disk.

    Args:
        results: Output from compare_stand_growth().
        output_dir: Optional directory to save JSON results.
    """
    scenario = results["scenario"]

    console.print()
    console.rule(
        f"[bold]PyFVS vs Native FVS Comparison: "
        f"{scenario['species']} ({scenario['variant']})"
    )
    console.print(
        f"  TPA: {scenario['trees_per_acre']:.0f}  "
        f"SI: {scenario['site_index']:.0f}  "
        f"Years: {scenario['years']}  "
        f"Cycles compared: {results['n_cycles_compared']}"
    )
    console.print()

    # --- Yield table comparison ---
    table = Table(title="Yield Table Comparison")
    table.add_column("Cycle", justify="center")
    table.add_column("Age", justify="center")
    table.add_column("TPA (py)", justify="right")
    table.add_column("TPA (nat)", justify="right")
    table.add_column("BA (py)", justify="right")
    table.add_column("BA (nat)", justify="right")
    table.add_column("QMD (py)", justify="right")
    table.add_column("QMD (nat)", justify="right")

    n_compare = results["n_cycles_compared"]
    for i in range(n_compare):
        py = results["pyfvs"][i]
        nat = results["native"][i]
        table.add_row(
            str(py["cycle"]),
            str(py["age"]),
            f"{py['tpa']:.0f}",
            f"{nat['tpa']:.0f}",
            f"{py['basal_area']:.1f}",
            f"{nat['basal_area']:.1f}",
            f"{py['qmd']:.2f}",
            f"{nat['qmd']:.2f}",
        )

    console.print(table)
    console.print()

    # --- Validation metrics ---
    metrics_table = Table(title="Validation Metrics")
    metrics_table.add_column("Variable", style="bold")
    metrics_table.add_column("Bias", justify="right")
    metrics_table.add_column("MAE", justify="right")
    metrics_table.add_column("RMSE", justify="right")
    metrics_table.add_column("MAPE %", justify="right")
    metrics_table.add_column("R²", justify="right")
    metrics_table.add_column("Status", justify="center")

    for var, vm in results["metrics"].items():
        accept = results["acceptance"].get(var, {})
        status = "[green]PASS[/green]" if accept.get("passed") else "[red]FAIL[/red]"
        metrics_table.add_row(
            var,
            f"{vm.bias:.3f}",
            f"{vm.mae:.3f}",
            f"{vm.rmse:.3f}",
            f"{vm.mape:.1f}",
            f"{vm.r_squared:.4f}",
            status,
        )

    console.print(metrics_table)

    # --- Save JSON if output_dir specified ---
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        json_path = out_path / f"native_comparison_{scenario['variant']}_{scenario['species']}.json"

        serializable = {
            "scenario": scenario,
            "n_cycles_compared": results["n_cycles_compared"],
            "pyfvs": results["pyfvs"],
            "native": results["native"],
            "metrics": {k: v.to_dict() for k, v in results["metrics"].items()},
            "acceptance": results["acceptance"],
        }

        with open(json_path, "w") as f:
            json.dump(serializable, f, indent=2)

        console.print(f"\nResults saved to {json_path}")


def run_standard_comparisons(output_dir: Optional[str] = None) -> List[Dict]:
    """Run a standard set of comparison scenarios across available variants.

    Returns:
        List of comparison results dictionaries.
    """
    scenarios = [
        {"trees_per_acre": 500, "site_index": 70, "species": "LP", "variant": "SN", "years": 50},
        {"trees_per_acre": 500, "site_index": 65, "species": "RN", "variant": "LS", "years": 50},
        {"trees_per_acre": 400, "site_index": 120, "species": "DF", "variant": "PN", "years": 50},
        {"trees_per_acre": 400, "site_index": 120, "species": "DF", "variant": "WC", "years": 50},
        {"trees_per_acre": 500, "site_index": 60, "species": "RM", "variant": "NE", "years": 50},
        {"trees_per_acre": 500, "site_index": 65, "species": "WO", "variant": "CS", "years": 50},
        {"trees_per_acre": 400, "site_index": 120, "species": "DF", "variant": "OP", "years": 50},
    ]

    all_results = []

    for scenario in scenarios:
        variant = scenario["variant"]
        if not fvs_library_available(variant):
            console.print(
                f"[yellow]Skipping {variant} — library not available[/yellow]"
            )
            continue

        try:
            results = compare_stand_growth(**scenario)
            generate_validation_report(results, output_dir)
            all_results.append(results)
        except Exception as exc:
            console.print(f"[red]Error in {variant}: {exc}[/red]")

    return all_results


if __name__ == "__main__":
    output_dir = "validation/results/native"
    results = run_standard_comparisons(output_dir)

    if not results:
        console.print(
            "\n[yellow]No FVS libraries found. "
            "Set FVS_LIB_PATH or see native/BUILD.md for build instructions.[/yellow]"
        )
    else:
        console.print(f"\n[green]Completed {len(results)} comparisons.[/green]")

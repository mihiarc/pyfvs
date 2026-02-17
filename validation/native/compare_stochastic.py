"""
Stochastic validation: compare PyFVS stochastic mode (averaged over N seeds)
against native FVS.

For each standard scenario, runs stochastic PyFVS N times (default 20),
averages metrics across seeds, and compares to native FVS output. Also
compares against the deterministic PyFVS baseline.

Usage:
    uv run python -m validation.native.compare_stochastic
"""

import random
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from rich.console import Console
from rich.table import Table

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pyfvs import Stand
from pyfvs.native import NativeStand, fvs_library_available
from pyfvs.native.library_loader import clear_library_cache
from validation.scripts.compare_results import (
    calculate_validation_metrics,
    check_acceptance_criteria,
)

console = Console()

# Standard scenarios (same as compare_native.py)
SCENARIOS = [
    {"trees_per_acre": 500, "site_index": 70, "species": "LP", "variant": "SN", "years": 50},
    {"trees_per_acre": 500, "site_index": 65, "species": "RN", "variant": "LS", "years": 50},
    {"trees_per_acre": 400, "site_index": 120, "species": "DF", "variant": "PN", "years": 50},
    {"trees_per_acre": 400, "site_index": 120, "species": "DF", "variant": "WC", "years": 50},
    {"trees_per_acre": 500, "site_index": 60, "species": "RM", "variant": "NE", "years": 50},
    {"trees_per_acre": 500, "site_index": 65, "species": "WO", "variant": "CS", "years": 50},
]

OUTPUT_VARS = ["basal_area", "qmd", "tpa", "top_height", "volume"]
METRIC_TYPE_MAP = {
    "tpa": "tpa",
    "basal_area": "basal_area",
    "qmd": "diameter",
    "top_height": "height",
    "volume": "volume",
}
VAR_SHORT = {
    "basal_area": "BA",
    "qmd": "QMD",
    "tpa": "TPA",
    "top_height": "TopHt",
    "volume": "Vol",
}


def run_pyfvs_simulation(
    trees_per_acre: float,
    site_index: float,
    species: str,
    variant: str,
    years: int,
    stochastic: bool = False,
    random_seed: Optional[int] = None,
    global_seed: Optional[int] = None,
) -> List[Dict]:
    """Run a single PyFVS simulation and return per-cycle metrics.

    Args:
        trees_per_acre: Planting density.
        site_index: Site index.
        species: Species code.
        variant: FVS variant.
        years: Simulation length.
        stochastic: Enable stochastic diameter growth.
        random_seed: Seed for stochastic RNG.
        global_seed: Seed for global random (mortality).
    """
    if global_seed is not None:
        random.seed(global_seed)

    kwargs = {
        "trees_per_acre": trees_per_acre,
        "site_index": site_index,
        "species": species,
        "variant": variant,
    }
    if stochastic:
        kwargs["stochastic"] = True
        kwargs["random_seed"] = random_seed

    stand = Stand.initialize_planted(**kwargs)
    cycle_length = 5 if variant in ("SN", "OP") else 10
    num_cycles = years // cycle_length

    cycles = []
    metrics = stand.get_metrics()
    cycles.append({
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
        cycles.append({
            "cycle": cycle + 1,
            "age": (cycle + 1) * cycle_length,
            "tpa": metrics["tpa"],
            "basal_area": metrics["basal_area"],
            "qmd": metrics["qmd"],
            "top_height": metrics.get("top_height", 0.0),
            "volume": metrics.get("volume", 0.0),
        })

    return cycles


def run_native_simulation(
    trees_per_acre: float,
    site_index: float,
    species: str,
    variant: str,
    years: int,
) -> List[Dict]:
    """Run native FVS and return per-cycle metrics."""
    cycle_length = 5 if variant in ("SN", "OP") else 10
    num_cycles = years // cycle_length

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

    return native_cycles


def average_cycles(all_runs: List[List[Dict]]) -> List[Dict]:
    """Average per-cycle metrics across multiple runs."""
    num_cycles = len(all_runs[0])
    averaged = []
    for i in range(num_cycles):
        avg = {
            "cycle": all_runs[0][i]["cycle"],
            "age": all_runs[0][i]["age"],
        }
        for var in OUTPUT_VARS:
            values = [run[i][var] for run in all_runs]
            avg[var] = np.mean(values)
        averaged.append(avg)
    return averaged


def compute_mapes(predicted_cycles: List[Dict], native_cycles: List[Dict]) -> Dict[str, float]:
    """Compute MAPE for each output variable."""
    n = min(len(predicted_cycles), len(native_cycles))
    mapes = {}
    for var in OUTPUT_VARS:
        observed = np.array([native_cycles[i][var] for i in range(n)])
        predicted = np.array([predicted_cycles[i][var] for i in range(n)])
        if np.all(observed == 0) and np.all(predicted == 0):
            continue
        try:
            vm = calculate_validation_metrics(observed, predicted)
            mapes[var] = vm.mape
        except (ValueError, ZeroDivisionError):
            pass
    return mapes


def compute_passes(predicted_cycles: List[Dict], native_cycles: List[Dict]) -> int:
    """Count how many output variables pass acceptance criteria."""
    n = min(len(predicted_cycles), len(native_cycles))
    passes = 0
    for var in OUTPUT_VARS:
        observed = np.array([native_cycles[i][var] for i in range(n)])
        predicted = np.array([predicted_cycles[i][var] for i in range(n)])
        if np.all(observed == 0) and np.all(predicted == 0):
            continue
        try:
            vm = calculate_validation_metrics(observed, predicted)
            passed, _ = check_acceptance_criteria(vm, METRIC_TYPE_MAP[var])
            if passed:
                passes += 1
        except (ValueError, ZeroDivisionError):
            pass
    return passes


def run_stochastic_validation(n_seeds: int = 20) -> None:
    """Run stochastic validation for all standard scenarios."""
    console.rule("[bold]Stochastic vs Deterministic vs Native FVS Validation")
    console.print(f"Seeds: {n_seeds}, averaging stochastic runs per scenario\n")

    # Summary table
    summary_table = Table(title="MAPE Comparison: Deterministic vs Stochastic (averaged)")
    summary_table.add_column("Variant", style="bold")
    summary_table.add_column("Mode", style="dim")
    for var in OUTPUT_VARS:
        summary_table.add_column(VAR_SHORT[var], justify="right")
    summary_table.add_column("Passes", justify="center")

    for scenario in SCENARIOS:
        variant = scenario["variant"]
        species = scenario["species"]

        if not fvs_library_available(variant):
            console.print(f"[yellow]Skipping {variant} — library not available[/yellow]")
            continue

        console.print(f"[bold]{variant} {species}[/bold] — TPA={scenario['trees_per_acre']}, SI={scenario['site_index']}")

        # --- Native FVS ---
        console.print("  Running native FVS...", style="dim")
        native_cycles = run_native_simulation(**scenario)

        # --- Deterministic PyFVS ---
        console.print("  Running deterministic PyFVS...", style="dim")
        random.seed(12345)
        det_cycles = run_pyfvs_simulation(**scenario, stochastic=False, global_seed=12345)
        det_mapes = compute_mapes(det_cycles, native_cycles)
        det_passes = compute_passes(det_cycles, native_cycles)

        # --- Stochastic PyFVS (N seeds) ---
        console.print(f"  Running stochastic PyFVS ({n_seeds} seeds)...", style="dim")
        stochastic_runs = []
        for seed in range(1, n_seeds + 1):
            cycles = run_pyfvs_simulation(
                **scenario,
                stochastic=True,
                random_seed=seed,
                global_seed=seed * 1000,
            )
            stochastic_runs.append(cycles)

        avg_cycles = average_cycles(stochastic_runs)
        sto_mapes = compute_mapes(avg_cycles, native_cycles)
        sto_passes = compute_passes(avg_cycles, native_cycles)

        # Add deterministic row
        det_row = [f"{variant} {species}", "Determ."]
        for var in OUTPUT_VARS:
            mape = det_mapes.get(var)
            det_row.append(f"{mape:.1f}%" if mape is not None else "N/A")
        det_row.append(f"{det_passes}/5")
        summary_table.add_row(*det_row)

        # Add stochastic row
        sto_row = [f"{variant} {species}", f"Stoch.({n_seeds})"]
        for var in OUTPUT_VARS:
            mape_s = sto_mapes.get(var)
            mape_d = det_mapes.get(var)
            if mape_s is not None:
                # Color: green if improved, red if worsened
                if mape_d is not None and mape_s < mape_d - 0.3:
                    sto_row.append(f"[green]{mape_s:.1f}%[/green]")
                elif mape_d is not None and mape_s > mape_d + 0.3:
                    sto_row.append(f"[red]{mape_s:.1f}%[/red]")
                else:
                    sto_row.append(f"{mape_s:.1f}%")
            else:
                sto_row.append("N/A")
        sto_row.append(f"{sto_passes}/5")
        summary_table.add_row(*sto_row)

        # Separator between scenarios
        summary_table.add_section()

        # Per-seed detail for this scenario
        detail_table = Table(title=f"  {variant} {species} — Per-seed BA MAPE")
        detail_table.add_column("Seed", justify="center")
        detail_table.add_column("BA MAPE", justify="right")
        detail_table.add_column("QMD MAPE", justify="right")
        detail_table.add_column("Vol MAPE", justify="right")
        for seed_idx, run in enumerate(stochastic_runs):
            seed_mapes = compute_mapes(run, native_cycles)
            detail_table.add_row(
                str(seed_idx + 1),
                f"{seed_mapes.get('basal_area', 0):.1f}%",
                f"{seed_mapes.get('qmd', 0):.1f}%",
                f"{seed_mapes.get('volume', 0):.1f}%",
            )
        # Add average row
        detail_table.add_section()
        detail_table.add_row(
            "AVG",
            f"[bold]{sto_mapes.get('basal_area', 0):.1f}%[/bold]",
            f"[bold]{sto_mapes.get('qmd', 0):.1f}%[/bold]",
            f"[bold]{sto_mapes.get('volume', 0):.1f}%[/bold]",
        )
        console.print(detail_table)
        console.print()

    console.print(summary_table)


if __name__ == "__main__":
    run_stochastic_validation(n_seeds=20)

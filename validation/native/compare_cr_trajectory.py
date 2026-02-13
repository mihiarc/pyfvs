"""
Compare crown ratio trajectories between PyFVS and native FVS.

This script runs both simulators side-by-side for selected species and
tracks how crown ratio evolves over time. Diverging CR trajectories could
explain the growing-with-age DDS error pattern documented in DDS_INVESTIGATION.md.

Usage:
    uv run python -m validation.native.compare_cr_trajectory
"""
import sys
import numpy as np
from rich.console import Console
from rich.table import Table

console = Console()

# Test species configuration (SN variant, 500 TPA, SI=70)
SPECIES_CONFIG = [
    {"species": "LP", "tpa": 500, "si": 70, "label": "Loblolly Pine"},
    {"species": "WO", "tpa": 500, "si": 70, "label": "White Oak"},
    {"species": "RO", "tpa": 500, "si": 70, "label": "Northern Red Oak"},
    {"species": "YP", "tpa": 500, "si": 70, "label": "Yellow Poplar"},
    {"species": "SU", "tpa": 500, "si": 70, "label": "Sweetgum"},
]

AGES_TO_CHECK = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]


def get_native_cr_trajectory(species: str, tpa: int, si: int) -> dict:
    """Run native FVS and collect mean CR at each age."""
    from pyfvs.native import NativeStand

    results = {}
    for age in AGES_TO_CHECK:
        try:
            with NativeStand(variant='SN') as ns:
                ns.initialize_planted(tpa, si, species)
                ns.grow(age)
                tree_list = ns.get_tree_list()

                if not tree_list:
                    results[age] = {"mean_cr": 0.0, "min_cr": 0.0, "max_cr": 0.0, "n_trees": 0}
                    continue

                crs = [t["crown_ratio"] for t in tree_list]
                tpas = [t["tpa"] for t in tree_list]
                total_tpa = sum(tpas)

                # Native FVS returns CR on 0-100 scale; normalize to 0-1
                if total_tpa > 0:
                    weighted_cr = sum(cr * tp for cr, tp in zip(crs, tpas)) / total_tpa
                else:
                    weighted_cr = np.mean(crs)

                # Normalize to proportion (0-1) if on percentage scale
                if weighted_cr > 1.0:
                    weighted_cr /= 100.0
                    crs = [c / 100.0 for c in crs]

                results[age] = {
                    "mean_cr": weighted_cr,
                    "min_cr": min(crs),
                    "max_cr": max(crs),
                    "n_trees": len(tree_list),
                    "tpa": total_tpa,
                }
        except Exception as e:
            console.print(f"[red]Native error at age {age}: {e}[/red]")
            results[age] = {"mean_cr": 0.0, "min_cr": 0.0, "max_cr": 0.0, "n_trees": 0}

    return results


def get_pyfvs_cr_trajectory(species: str, tpa: int, si: int) -> dict:
    """Run PyFVS and collect mean CR at each age."""
    from pyfvs import Stand

    results = {}
    # Run a single simulation, collecting CR at each checkpoint
    stand = Stand.initialize_planted(tpa, si, species, variant='SN', ecounit='M231')

    current_age = 0
    for age in AGES_TO_CHECK:
        years_to_grow = age - current_age
        if years_to_grow > 0:
            stand.grow(years_to_grow)
            current_age = age

        trees = stand.trees
        if not trees:
            results[age] = {"mean_cr": 0.0, "min_cr": 0.0, "max_cr": 0.0, "n_trees": 0}
            continue

        crs = [t.crown_ratio for t in trees]
        # Each tree = 1 TPA in PyFVS
        n_trees = len(trees)

        results[age] = {
            "mean_cr": np.mean(crs),
            "min_cr": min(crs),
            "max_cr": max(crs),
            "n_trees": n_trees,
            "tpa": float(n_trees),
        }

    return results


def compare_species(config: dict):
    """Compare CR trajectories for a single species."""
    sp = config["species"]
    label = config["label"]

    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print(f"[bold]{label} ({sp}) — {config['tpa']} TPA, SI={config['si']}[/bold]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]")

    # Get trajectories
    native_cr = get_native_cr_trajectory(sp, config["tpa"], config["si"])
    pyfvs_cr = get_pyfvs_cr_trajectory(sp, config["tpa"], config["si"])

    # Build comparison table
    table = Table(title=f"{label} Crown Ratio Trajectory")
    table.add_column("Age", justify="right", style="bold")
    table.add_column("Native CR", justify="right")
    table.add_column("PyFVS CR", justify="right")
    table.add_column("Diff", justify="right")
    table.add_column("% Diff", justify="right")
    table.add_column("Native TPA", justify="right")
    table.add_column("PyFVS TPA", justify="right")

    for age in AGES_TO_CHECK:
        n = native_cr.get(age, {})
        p = pyfvs_cr.get(age, {})

        n_cr = n.get("mean_cr", 0.0)
        p_cr = p.get("mean_cr", 0.0)
        diff = p_cr - n_cr
        pct_diff = (diff / n_cr * 100) if n_cr > 0 else 0.0

        n_tpa = n.get("tpa", 0)
        p_tpa = p.get("tpa", 0)

        # Color coding for difference
        if abs(pct_diff) < 5:
            style = "green"
        elif abs(pct_diff) < 15:
            style = "yellow"
        else:
            style = "red"

        table.add_row(
            str(age),
            f"{n_cr:.3f}" if n_cr > 0 else "N/A",
            f"{p_cr:.3f}",
            f"[{style}]{diff:+.3f}[/{style}]",
            f"[{style}]{pct_diff:+.1f}%[/{style}]",
            f"{n_tpa:.0f}" if n_tpa else "N/A",
            f"{p_tpa:.0f}",
        )

    console.print(table)

    return native_cr, pyfvs_cr


def main():
    """Run CR trajectory comparison for all test species."""
    console.print("[bold]Crown Ratio Trajectory Comparison: PyFVS vs Native FVS[/bold]")
    console.print("SN variant, M231 ecounit, flat terrain\n")

    # Check native library availability
    try:
        from pyfvs.native import fvs_library_available
        if not fvs_library_available('SN'):
            console.print("[red]Native FVS SN library not available. Exiting.[/red]")
            sys.exit(1)
    except ImportError:
        console.print("[red]pyfvs.native not available. Exiting.[/red]")
        sys.exit(1)

    all_results = {}
    for config in SPECIES_CONFIG:
        native, pyfvs = compare_species(config)
        all_results[config["species"]] = {"native": native, "pyfvs": pyfvs}

    # Summary: which species have the biggest CR divergence at age 40?
    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print("[bold]Summary: CR Divergence at Key Ages[/bold]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]")

    summary_table = Table(title="CR Difference (PyFVS - Native) at Key Ages")
    summary_table.add_column("Species", justify="left", style="bold")
    for age in [10, 20, 30, 40, 50]:
        summary_table.add_column(f"Age {age}", justify="right")
    summary_table.add_column("Trend", justify="left")

    for sp_config in SPECIES_CONFIG:
        sp = sp_config["species"]
        data = all_results[sp]
        row = [sp_config["label"]]

        diffs = []
        for age in [10, 20, 30, 40, 50]:
            n_cr = data["native"].get(age, {}).get("mean_cr", 0)
            p_cr = data["pyfvs"].get(age, {}).get("mean_cr", 0)
            if n_cr > 0:
                pct = (p_cr - n_cr) / n_cr * 100
                diffs.append(pct)
                style = "green" if abs(pct) < 5 else ("yellow" if abs(pct) < 15 else "red")
                row.append(f"[{style}]{pct:+.1f}%[/{style}]")
            else:
                row.append("N/A")

        # Trend analysis
        if len(diffs) >= 3:
            if all(d > diffs[0] for d in diffs[1:]):
                trend = "[red]Growing divergence[/red]"
            elif all(d < diffs[0] for d in diffs[1:]):
                trend = "[green]Converging[/green]"
            elif abs(diffs[-1]) > abs(diffs[0]) + 5:
                trend = "[yellow]Widening[/yellow]"
            else:
                trend = "Stable"
        else:
            trend = "Insufficient data"

        row.append(trend)
        summary_table.add_row(*row)

    console.print(summary_table)


if __name__ == "__main__":
    main()

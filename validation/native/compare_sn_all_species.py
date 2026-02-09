"""
Comprehensive SN variant validation across all major species.

Runs PyFVS vs Native FVS comparisons for representative SN species
covering pines, oaks, and hardwoods at appropriate site indices.

Usage:
    uv run python -m validation.native.compare_sn_all_species
"""

import json
import sys
import traceback
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pyfvs.native import fvs_library_available
from validation.native.compare_native import compare_stand_growth

console = Console()

# SN species scenarios: species, common name, TPA, SI, group
# Site indices chosen to be typical for each species in the Southeast
SN_SPECIES_SCENARIOS = [
    # === PINES (softwoods) ===
    ("LP", "Loblolly Pine", 500, 70, "Pine"),
    ("SP", "Shortleaf Pine", 500, 60, "Pine"),
    ("SA", "Slash Pine", 500, 70, "Pine"),
    ("LL", "Longleaf Pine", 500, 70, "Pine"),
    ("VP", "Virginia Pine", 500, 60, "Pine"),
    ("SR", "Spruce Pine", 400, 70, "Pine"),
    ("PP", "Pond Pine", 400, 60, "Pine"),
    ("WP", "White Pine", 400, 70, "Pine"),
    ("PD", "Pitch Pine", 400, 50, "Pine"),

    # === UPLAND OAKS ===
    ("WO", "White Oak", 400, 70, "Oak"),
    ("RO", "Northern Red Oak", 400, 70, "Oak"),
    ("SO", "Scarlet Oak", 400, 60, "Oak"),
    ("SK", "Southern Red Oak", 400, 65, "Oak"),
    ("BK", "Black Oak", 400, 65, "Oak"),
    ("PO", "Post Oak", 400, 55, "Oak"),
    ("CO", "Chestnut Oak", 400, 65, "Oak"),

    # === BOTTOMLAND OAKS ===
    ("WK", "Water Oak", 400, 70, "Bottomland Oak"),
    ("LK", "Laurel Oak", 400, 65, "Bottomland Oak"),
    ("CB", "Cherrybark Oak", 400, 75, "Bottomland Oak"),
    ("OV", "Overcup Oak", 400, 60, "Bottomland Oak"),
    ("SN", "Swamp Chestnut Oak", 400, 70, "Bottomland Oak"),
    ("TO", "Turkey Oak", 400, 55, "Bottomland Oak"),

    # === MAJOR HARDWOODS ===
    ("YP", "Yellow-Poplar", 400, 80, "Hardwood"),
    ("SU", "Sweetgum", 400, 70, "Hardwood"),
    ("BC", "Black Cherry", 400, 60, "Hardwood"),
    ("RM", "Red Maple", 400, 60, "Hardwood"),
    ("SM", "Sugar Maple", 400, 60, "Hardwood"),
    ("SY", "American Sycamore", 400, 70, "Hardwood"),
    ("WA", "White Ash", 400, 65, "Hardwood"),
    ("GA", "Green Ash", 400, 65, "Hardwood"),
    ("WN", "Black Walnut", 300, 60, "Hardwood"),
    ("HI", "Hickory", 400, 60, "Hardwood"),
    ("AB", "American Beech", 400, 60, "Hardwood"),
    ("BD", "Basswood", 400, 65, "Hardwood"),

    # === MINOR SOFTWOODS/OTHER ===
    ("BY", "Baldcypress", 300, 70, "Other Softwood"),
    ("HM", "Hemlock", 400, 60, "Other Softwood"),
    ("JU", "Eastern Redcedar", 400, 45, "Other Softwood"),
    ("FR", "Fraser Fir", 400, 55, "Other Softwood"),

    # === MINOR HARDWOODS ===
    ("BG", "Blackgum", 400, 55, "Minor Hardwood"),
    ("SB", "Sweet Birch", 400, 55, "Minor Hardwood"),
    ("AE", "American Elm", 400, 60, "Minor Hardwood"),
    ("LB", "Black Locust", 400, 55, "Minor Hardwood"),
    ("DW", "Dogwood", 400, 45, "Minor Hardwood"),
    ("SS", "Sassafras", 400, 50, "Minor Hardwood"),
    ("MV", "Sweetbay", 400, 55, "Minor Hardwood"),
    ("BT", "Bigtooth Aspen", 400, 55, "Minor Hardwood"),
]


def run_sn_all_species(years: int = 50) -> dict:
    """Run comparisons for all SN species scenarios.

    Returns dict with results keyed by species code.
    """
    if not fvs_library_available("SN"):
        console.print("[red]SN native library not available[/red]")
        return {}

    results = {}
    errors = {}

    for species, name, tpa, si, group in SN_SPECIES_SCENARIOS:
        console.print(
            f"  Running {species} ({name}) - {tpa} TPA, SI {si}...",
            end=" ",
        )
        try:
            result = compare_stand_growth(
                trees_per_acre=tpa,
                site_index=si,
                species=species,
                variant="SN",
                years=years,
            )
            results[species] = {
                "name": name,
                "group": group,
                "tpa": tpa,
                "si": si,
                "result": result,
            }
            # Show quick status
            ba_mape = result["metrics"].get("basal_area")
            if ba_mape:
                console.print(f"BA MAPE: {ba_mape.mape:.1f}%")
            else:
                console.print("[yellow]no BA metrics[/yellow]")
        except Exception as exc:
            console.print(f"[red]ERROR: {exc}[/red]")
            errors[species] = {"name": name, "group": group, "error": str(exc)}

    return {"results": results, "errors": errors}


def print_summary_table(data: dict) -> None:
    """Print a rich summary table of all species results."""
    results = data["results"]
    errors = data["errors"]

    # Group results
    groups = {}
    for species, info in results.items():
        group = info["group"]
        if group not in groups:
            groups[group] = []
        groups[group].append((species, info))

    table = Table(
        title="SN Variant: PyFVS vs Native FVS - All Species (50yr)",
        show_lines=True,
    )
    table.add_column("Species", style="bold", width=6)
    table.add_column("Common Name", width=22)
    table.add_column("TPA/SI", justify="center", width=8)
    table.add_column("TPA MAPE%", justify="right", width=10)
    table.add_column("BA MAPE%", justify="right", width=10)
    table.add_column("QMD MAPE%", justify="right", width=10)
    table.add_column("Ht MAPE%", justify="right", width=10)
    table.add_column("Vol MAPE%", justify="right", width=10)
    table.add_column("Grade", justify="center", width=7)

    for group_name in [
        "Pine", "Oak", "Bottomland Oak", "Hardwood",
        "Other Softwood", "Minor Hardwood",
    ]:
        if group_name not in groups:
            continue
        table.add_row(
            f"[bold cyan]--- {group_name} ---[/bold cyan]",
            "", "", "", "", "", "", "", "",
        )

        for species, info in sorted(groups[group_name], key=lambda x: x[0]):
            metrics = info["result"]["metrics"]
            tpa_m = metrics.get("tpa")
            ba_m = metrics.get("basal_area")
            qmd_m = metrics.get("qmd")
            ht_m = metrics.get("top_height")
            vol_m = metrics.get("volume")

            def fmt(m, threshold_good=15, threshold_fair=30):
                if m is None:
                    return "[dim]n/a[/dim]"
                v = m.mape
                if v < threshold_good:
                    return f"[green]{v:.1f}[/green]"
                elif v < threshold_fair:
                    return f"[yellow]{v:.1f}[/yellow]"
                else:
                    return f"[red]{v:.1f}[/red]"

            # Overall grade based on BA MAPE
            if ba_m:
                ba_val = ba_m.mape
                if ba_val < 15:
                    grade = "[green]A[/green]"
                elif ba_val < 25:
                    grade = "[green]B[/green]"
                elif ba_val < 40:
                    grade = "[yellow]C[/yellow]"
                elif ba_val < 60:
                    grade = "[yellow]D[/yellow]"
                else:
                    grade = "[red]F[/red]"
            else:
                grade = "[dim]?[/dim]"

            table.add_row(
                species,
                info["name"],
                f"{info['tpa']}/{info['si']}",
                fmt(tpa_m, 5, 10),
                fmt(ba_m, 15, 30),
                fmt(qmd_m, 15, 30),
                fmt(ht_m, 15, 30),
                fmt(vol_m, 20, 40),
                grade,
            )

    # Add errors
    if errors:
        table.add_row(
            "[bold red]--- ERRORS ---[/bold red]",
            "", "", "", "", "", "", "", "",
        )
        for species, info in errors.items():
            table.add_row(
                species,
                info["name"],
                "",
                f"[red]{info['error'][:30]}[/red]",
                "", "", "", "", "[red]ERR[/red]",
            )

    console.print()
    console.print(table)

    # Summary stats
    ba_mapes = []
    for species, info in results.items():
        ba_m = info["result"]["metrics"].get("basal_area")
        if ba_m:
            ba_mapes.append((species, ba_m.mape))

    if ba_mapes:
        ba_mapes.sort(key=lambda x: x[1])
        n_total = len(ba_mapes)
        n_good = sum(1 for _, m in ba_mapes if m < 15)
        n_fair = sum(1 for _, m in ba_mapes if 15 <= m < 30)
        n_poor = sum(1 for _, m in ba_mapes if m >= 30)
        median_mape = ba_mapes[n_total // 2][1]

        console.print()
        console.print(Panel(
            f"[bold]Summary (BA MAPE)[/bold]\n"
            f"  Species tested: {n_total} (+{len(errors)} errors)\n"
            f"  Good (<15%): [green]{n_good}[/green]  "
            f"Fair (15-30%): [yellow]{n_fair}[/yellow]  "
            f"Poor (>30%): [red]{n_poor}[/red]\n"
            f"  Median BA MAPE: {median_mape:.1f}%\n"
            f"  Best: {ba_mapes[0][0]} ({ba_mapes[0][1]:.1f}%)  "
            f"Worst: {ba_mapes[-1][0]} ({ba_mapes[-1][1]:.1f}%)",
            title="Validation Summary",
        ))


def save_results(data: dict, output_dir: str) -> None:
    """Save results to JSON."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    serializable = {}
    for species, info in data["results"].items():
        result = info["result"]
        serializable[species] = {
            "name": info["name"],
            "group": info["group"],
            "scenario": result["scenario"],
            "n_cycles_compared": result["n_cycles_compared"],
            "pyfvs": result["pyfvs"],
            "native": result["native"],
            "metrics": {
                k: v.to_dict() for k, v in result["metrics"].items()
            },
            "acceptance": result["acceptance"],
        }

    json_path = out_path / "sn_all_species_comparison.json"
    with open(json_path, "w") as f:
        json.dump(serializable, f, indent=2)
    console.print(f"\nResults saved to {json_path}")

    # Also save a CSV summary
    csv_path = out_path / "sn_all_species_summary.csv"
    with open(csv_path, "w") as f:
        f.write("species,name,group,tpa,si,tpa_mape,ba_mape,qmd_mape,ht_mape,vol_mape\n")
        for species, info in sorted(serializable.items()):
            metrics = info["metrics"]
            f.write(
                f"{species},{info['name']},{info['group']},"
                f"{info['scenario']['trees_per_acre']},{info['scenario']['site_index']},"
                f"{metrics.get('tpa', {}).get('mape', 'NA')},"
                f"{metrics.get('basal_area', {}).get('mape', 'NA')},"
                f"{metrics.get('qmd', {}).get('mape', 'NA')},"
                f"{metrics.get('top_height', {}).get('mape', 'NA')},"
                f"{metrics.get('volume', {}).get('mape', 'NA')}\n"
            )
    console.print(f"CSV summary saved to {csv_path}")


if __name__ == "__main__":
    console.rule("[bold]SN Variant: Comprehensive Species Validation[/bold]")
    console.print(f"Testing {len(SN_SPECIES_SCENARIOS)} species against native FVS\n")

    data = run_sn_all_species(years=50)

    if data:
        print_summary_table(data)
        save_results(data, "validation/results/native")

"""Diagnose NE/CS BA overgrowth at ages 10-20.

Traces per-cycle growth to find where PyFVS diverges from native FVS.
Focuses on the small-tree phase (DBH < 3") where height drives DBH.
"""

import math
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table

from pyfvs import Stand
from pyfvs.native import NativeStand, fvs_library_available
from pyfvs.native.library_loader import clear_library_cache

console = Console()


def diagnose_variant(species, variant, site_index, tpa, years=50):
    """Trace per-cycle growth for a variant, comparing PyFVS vs native."""
    cycle_length = 5 if variant in ('SN', 'OP') else 10
    num_cycles = years // cycle_length

    console.rule(f"[bold]{species} ({variant}) SI={site_index} TPA={tpa}")

    # --- PyFVS ---
    stand = Stand.initialize_planted(tpa, site_index, species, variant=variant)

    table = Table(title=f"Per-Cycle Diagnostic: {species} ({variant})")
    table.add_column("Age", justify="center")
    table.add_column("TPA", justify="right")
    table.add_column("BA(py)", justify="right")
    table.add_column("BA(nat)", justify="right")
    table.add_column("QMD(py)", justify="right")
    table.add_column("QMD(nat)", justify="right")
    table.add_column("TopHt(py)", justify="right")
    table.add_column("TopHt(nat)", justify="right")
    table.add_column("MeanHt(py)", justify="right")
    table.add_column("MeanHt(nat)", justify="right")
    table.add_column("<1\"", justify="right")
    table.add_column("1-3\"", justify="right")
    table.add_column(">3\"", justify="right")

    # Collect PyFVS cycles
    py_cycles = []
    m = stand.get_metrics()
    trees_lt1 = sum(1 for t in stand.trees if t.dbh < 1.0)
    trees_1to3 = sum(1 for t in stand.trees if 1.0 <= t.dbh < 3.0)
    trees_gt3 = sum(1 for t in stand.trees if t.dbh >= 3.0)
    py_cycles.append({
        'age': cycle_length, 'tpa': m['tpa'], 'ba': m['basal_area'],
        'qmd': m['qmd'], 'top_ht': m['top_height'], 'mean_ht': m['mean_height'],
        'lt1': trees_lt1, '1to3': trees_1to3, 'gt3': trees_gt3,
    })

    for cycle in range(1, num_cycles):
        stand.grow(years=cycle_length)
        m = stand.get_metrics()
        trees_lt1 = sum(1 for t in stand.trees if t.dbh < 1.0)
        trees_1to3 = sum(1 for t in stand.trees if 1.0 <= t.dbh < 3.0)
        trees_gt3 = sum(1 for t in stand.trees if t.dbh >= 3.0)
        py_cycles.append({
            'age': (cycle + 1) * cycle_length, 'tpa': m['tpa'],
            'ba': m['basal_area'], 'qmd': m['qmd'],
            'top_ht': m['top_height'], 'mean_ht': m['mean_height'],
            'lt1': trees_lt1, '1to3': trees_1to3, 'gt3': trees_gt3,
        })

    # Collect native cycles
    nat_cycles = []
    if fvs_library_available(variant):
        for cycle_num in range(1, num_cycles + 1):
            cycle_years = cycle_num * cycle_length
            clear_library_cache()
            with NativeStand(variant=variant) as ns:
                ns.initialize_planted(tpa, site_index, species)
                ns.grow(cycle_years)
                nm = ns.get_metrics()
                nat_cycles.append({
                    'age': cycle_years, 'tpa': nm['tpa'],
                    'ba': nm['basal_area'], 'qmd': nm['qmd'],
                    'top_ht': nm['top_height'], 'mean_ht': nm.get('mean_height', 0),
                })
    else:
        console.print(f"[yellow]Native {variant} library not available[/yellow]")

    # Build table
    for i, py in enumerate(py_cycles):
        nat = nat_cycles[i] if i < len(nat_cycles) else None
        table.add_row(
            str(py['age']),
            str(py['tpa']),
            f"{py['ba']:.1f}",
            f"{nat['ba']:.1f}" if nat else "-",
            f"{py['qmd']:.2f}",
            f"{nat['qmd']:.2f}" if nat else "-",
            f"{py['top_ht']:.1f}",
            f"{nat['top_ht']:.1f}" if nat else "-",
            f"{py['mean_ht']:.1f}",
            f"{nat['mean_ht']:.1f}" if nat else "-",
            str(py['lt1']),
            str(py['1to3']),
            str(py['gt3']),
        )

    console.print(table)

    # Per-cycle BA increment comparison
    console.print()
    inc_table = Table(title="Per-Cycle BA Increment")
    inc_table.add_column("Period", justify="center")
    inc_table.add_column("dBA(py)", justify="right")
    inc_table.add_column("dBA(nat)", justify="right")
    inc_table.add_column("Ratio", justify="right")
    inc_table.add_column("dQMD(py)", justify="right")
    inc_table.add_column("dQMD(nat)", justify="right")
    inc_table.add_column("dHt(py)", justify="right")
    inc_table.add_column("dHt(nat)", justify="right")

    for i in range(1, len(py_cycles)):
        py_dba = py_cycles[i]['ba'] - py_cycles[i-1]['ba']
        py_dqmd = py_cycles[i]['qmd'] - py_cycles[i-1]['qmd']
        py_dht = py_cycles[i]['top_ht'] - py_cycles[i-1]['top_ht']
        if i < len(nat_cycles):
            nat_dba = nat_cycles[i]['ba'] - nat_cycles[i-1]['ba']
            nat_dqmd = nat_cycles[i]['qmd'] - nat_cycles[i-1]['qmd']
            nat_dht = nat_cycles[i]['top_ht'] - nat_cycles[i-1]['top_ht']
            ratio = py_dba / nat_dba if nat_dba > 0 else float('inf')
        else:
            nat_dba = nat_dqmd = nat_dht = 0
            ratio = 0

        period = f"{py_cycles[i-1]['age']}-{py_cycles[i]['age']}"
        inc_table.add_row(
            period,
            f"{py_dba:.1f}",
            f"{nat_dba:.1f}" if nat_dba else "-",
            f"{ratio:.2f}x" if ratio < 100 else "inf",
            f"{py_dqmd:.2f}",
            f"{nat_dqmd:.2f}" if nat_dqmd else "-",
            f"{py_dht:.1f}",
            f"{nat_dht:.1f}" if nat_dht else "-",
        )

    console.print(inc_table)

    # Height-DBH diagnostic at cycle 2
    if len(py_cycles) >= 2:
        console.print()
        console.print(f"[bold]Tree sample at age {py_cycles[1]['age']}:[/bold]")
        sample = sorted(stand.trees, key=lambda t: t.dbh)
        indices = [0, len(sample)//4, len(sample)//2, 3*len(sample)//4, len(sample)-1]
        for idx in indices:
            t = sample[idx]
            console.print(
                f"  Tree {idx}: DBH={t.dbh:.3f}\" Ht={t.height:.1f}ft "
                f"Age={t.age} CR={t.crown_ratio:.3f}"
            )

    console.print()


if __name__ == "__main__":
    diagnose_variant('RM', 'NE', 60, 500, 50)
    diagnose_variant('WO', 'CS', 65, 500, 50)

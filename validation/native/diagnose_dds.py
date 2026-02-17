"""
Tree-level DDS diagnostic: compare PyFVS vs native FVS diameter growth
at identical fixed conditions (no feedback loop).

For each test tree, we:
1. Run native FVS to grow a stand to a target age
2. Snapshot tree-level attributes (DBH, CR, height, BA, PBAL, etc.)
3. Grow native FVS one more cycle and compute actual DDS from DBH change
4. Feed the SAME pre-growth conditions into PyFVS's DDS model
5. Compare — this isolates the DDS equation from mortality/competition feedback

Usage:
    uv run python -m validation.native.diagnose_dds
    uv run python -m validation.native.diagnose_dds --variant SN --species LP
    uv run python -m validation.native.diagnose_dds --variant SN --species WO RO YP SU
"""

import argparse
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pyfvs.sn_diameter_growth import create_sn_diameter_growth_model
from pyfvs.ls_diameter_growth import create_ls_diameter_growth_model
from pyfvs.cs_diameter_growth import create_cs_diameter_growth_model
from pyfvs.pn_diameter_growth import create_pn_diameter_growth_model
from pyfvs.wc_diameter_growth import create_wc_diameter_growth_model
from pyfvs.op_diameter_growth import create_op_diameter_growth_model
from pyfvs.bark_ratio import create_bark_ratio_model

console = Console()

# Variant configuration
VARIANT_CONFIG = {
    'SN': {'cycle': 5, 'default_si': 70, 'default_tpa': 500, 'ecounit': 'M231'},
    'LS': {'cycle': 10, 'default_si': 65, 'default_tpa': 500, 'ecounit': ''},
    'CS': {'cycle': 10, 'default_si': 70, 'default_tpa': 500, 'ecounit': ''},
    'PN': {'cycle': 10, 'default_si': 120, 'default_tpa': 400, 'ecounit': ''},
    'WC': {'cycle': 10, 'default_si': 120, 'default_tpa': 400, 'ecounit': ''},
    'OP': {'cycle': 5, 'default_si': 120, 'default_tpa': 400, 'ecounit': ''},
}

# Default test species per variant
DEFAULT_SPECIES = {
    'SN': ['LP', 'WO', 'RO', 'YP', 'SU'],
    'LS': ['RN'],
    'CS': ['WO'],
    'PN': ['DF'],
    'WC': ['DF'],
    'OP': ['DF'],
}


def compute_pyfvs_dds(
    variant: str,
    species: str,
    dbh: float,
    crown_ratio: float,
    site_index: float,
    ba: float,
    pbal: float,
    relht: float = 1.0,
    time_step: float = 5.0,
) -> float:
    """Compute PyFVS DDS for a single tree at given conditions.

    Returns the raw DDS value (sq inches inside bark).
    """
    if variant == 'SN':
        model = create_sn_diameter_growth_model(species)
        return model.calculate_dds(
            dbh=dbh, crown_ratio=crown_ratio, site_index=site_index,
            ba=ba, pbal=pbal, relht=relht, time_step=time_step,
        )
    elif variant == 'LS':
        model = create_ls_diameter_growth_model(species)
        return model.calculate_dds(
            dbh=dbh, crown_ratio=crown_ratio, site_index=site_index,
            ba=ba, bal=pbal, time_step=time_step,
        )
    elif variant == 'CS':
        model = create_cs_diameter_growth_model(species)
        return model.calculate_dds(
            dbh=dbh, crown_ratio=crown_ratio, site_index=site_index,
            ba=ba, bal=pbal, time_step=time_step,
        )
    elif variant == 'PN':
        model = create_pn_diameter_growth_model(species)
        return model.calculate_dds(
            dbh=dbh, crown_ratio=crown_ratio, site_index=site_index,
            ba=ba, bal=pbal, time_step=time_step,
        )
    elif variant == 'WC':
        model = create_wc_diameter_growth_model(species)
        return model.calculate_dds(
            dbh=dbh, crown_ratio=crown_ratio, site_index=site_index,
            ba=ba, bal=pbal, time_step=time_step,
        )
    elif variant == 'OP':
        model = create_op_diameter_growth_model(species)
        bark_model = create_bark_ratio_model(species, variant='OP')
        bark_ratio = bark_model.calculate_bark_ratio(dbh)
        # OP predicts DG directly, convert to DDS for comparison
        dg = model.calculate_diameter_growth(
            dbh=dbh, crown_ratio=crown_ratio, site_index=site_index,
            ba=ba, bal=pbal, time_step=time_step,
        )
        # DDS = (dib_new^2 - dib_old^2) where dib = dbh * bark_ratio
        dib_old = dbh * bark_ratio
        dib_new = (dbh + dg) * bark_ratio
        return dib_new ** 2 - dib_old ** 2
    else:
        raise ValueError(f"Unsupported variant: {variant}")


def compute_pyfvs_dg(
    variant: str,
    species: str,
    dbh: float,
    crown_ratio: float,
    site_index: float,
    ba: float,
    pbal: float,
    relht: float = 1.0,
    time_step: float = 5.0,
) -> float:
    """Compute PyFVS diameter growth (inches OB) for a single tree."""
    bark_model = create_bark_ratio_model(species, variant=variant)
    bark_ratio = bark_model.calculate_bark_ratio(dbh)

    if variant == 'OP':
        model = create_op_diameter_growth_model(species)
        return model.calculate_diameter_growth(
            dbh=dbh, crown_ratio=crown_ratio, site_index=site_index,
            ba=ba, bal=pbal, time_step=time_step,
        )

    dds = compute_pyfvs_dds(
        variant, species, dbh, crown_ratio, site_index,
        ba, pbal, relht, time_step,
    )

    dib_old = dbh * bark_ratio
    dib_new_sq = dib_old ** 2 + dds
    if dib_new_sq <= dib_old ** 2:
        return 0.0
    dib_new = math.sqrt(dib_new_sq)
    return dib_new / bark_ratio - dbh


def diagnose_with_native(
    variant: str,
    species_list: List[str],
    target_ages: List[int] = None,
) -> List[Dict]:
    """Run native FVS and compare tree-level DDS at each target age.

    NativeStand.grow() reruns the full simulation from scratch, so we use
    two separate simulations for each comparison point:
    1. Simulation A: grow to age N — snapshot tree attributes (DBH, CR, BA, etc.)
    2. Simulation B: grow to age N+cycle — snapshot tree attributes
    3. Compute native DDS from the mean DBH difference
    4. Compute PyFVS DDS at the pre-growth conditions from Simulation A
    5. Compare — this isolates the DDS equation from mortality/competition feedback

    Returns list of result dicts.
    """
    try:
        from pyfvs.native import NativeStand, fvs_library_available
    except ImportError:
        console.print("[red]pyfvs.native not available[/red]")
        return []

    if not fvs_library_available(variant):
        console.print(f"[red]FVS {variant} library not available[/red]")
        return []

    cfg = VARIANT_CONFIG[variant]
    cycle = cfg['cycle']

    if target_ages is None:
        # Default: measure DDS at ages that give ~3", 5", 8", 12" DBH
        target_ages = [cycle * 2, cycle * 3, cycle * 4, cycle * 6, cycle * 8]

    results = []

    for species in species_list:
        console.print(f"\n[bold]{variant} {species}[/bold] — SI={cfg['default_si']}, "
                      f"TPA={cfg['default_tpa']}, cycle={cycle}yr")

        for target_age in target_ages:
            num_pre_cycles = target_age // cycle
            if num_pre_cycles < 1:
                continue

            try:
                # Simulation A: grow to target_age, snapshot pre-growth conditions
                with NativeStand(variant=variant) as ns_pre:
                    ns_pre.initialize_planted(
                        trees_per_acre=cfg['default_tpa'],
                        site_index=cfg['default_si'],
                        species=species,
                    )
                    ns_pre.grow(target_age)

                    dims = ns_pre._bindings.get_dim_sizes()
                    ntrees = dims.get('ntrees', 0)
                    if ntrees == 0:
                        continue

                    dbh_pre = ns_pre._bindings.get_tree_attr('dbh', ntrees)
                    ht_pre = ns_pre._bindings.get_tree_attr('ht', ntrees)
                    cr_pre = ns_pre._bindings.get_tree_attr('cratio', ntrees)
                    tpa_pre = ns_pre._bindings.get_tree_attr('tpa', ntrees)

                    metrics_pre = ns_pre.get_metrics()
                    ba_pre = metrics_pre.get('basal_area', 0.0)
                    top_ht = metrics_pre.get('top_height', 0.0)
                    tpa_stand = metrics_pre.get('tpa', 0.0)

                    # Mean tree conditions (weighted by TPA)
                    total_tpa = sum(tpa_pre)
                    if total_tpa <= 0:
                        continue

                    mean_dbh = sum(d * t for d, t in zip(dbh_pre, tpa_pre)) / total_tpa
                    mean_ht = sum(h * t for h, t in zip(ht_pre, tpa_pre)) / total_tpa
                    mean_cr = sum(c * t for c, t in zip(cr_pre, tpa_pre)) / total_tpa

                    # Compute PBAL for the median tree (roughly half BA)
                    mean_pbal = ba_pre * 0.5

                    # Compute RELHT
                    relht = mean_ht / top_ht if top_ht > 0 else 1.0

                # Simulation B: grow to target_age + cycle, snapshot post-growth
                with NativeStand(variant=variant) as ns_post:
                    ns_post.initialize_planted(
                        trees_per_acre=cfg['default_tpa'],
                        site_index=cfg['default_si'],
                        species=species,
                    )
                    ns_post.grow(target_age + cycle)

                    dims_post = ns_post._bindings.get_dim_sizes()
                    ntrees_post = dims_post.get('ntrees', 0)
                    if ntrees_post == 0:
                        continue

                    dbh_post = ns_post._bindings.get_tree_attr('dbh', ntrees_post)
                    tpa_post = ns_post._bindings.get_tree_attr('tpa', ntrees_post)

                    metrics_post = ns_post.get_metrics()

                # Compute native mean diameter growth
                total_tpa_post = sum(tpa_post)
                if total_tpa_post <= 0:
                    continue

                mean_dbh_post = sum(d * t for d, t in zip(dbh_post, tpa_post)) / total_tpa_post
                native_dg = mean_dbh_post - mean_dbh

                # Compute native DDS (approximate, using mean bark ratio)
                bark_model = create_bark_ratio_model(species, variant=variant)
                bark_ratio = bark_model.calculate_bark_ratio(mean_dbh)
                dib_pre_val = mean_dbh * bark_ratio
                dib_post_val = mean_dbh_post * bark_ratio
                native_dds = dib_post_val ** 2 - dib_pre_val ** 2

                # Compute PyFVS DDS at same pre-growth conditions
                pyfvs_dds = compute_pyfvs_dds(
                    variant=variant,
                    species=species,
                    dbh=mean_dbh,
                    crown_ratio=mean_cr,
                    site_index=cfg['default_si'],
                    ba=ba_pre,
                    pbal=mean_pbal,
                    relht=relht,
                    time_step=cycle,
                )
                pyfvs_dg = compute_pyfvs_dg(
                    variant=variant,
                    species=species,
                    dbh=mean_dbh,
                    crown_ratio=mean_cr,
                    site_index=cfg['default_si'],
                    ba=ba_pre,
                    pbal=mean_pbal,
                    relht=relht,
                    time_step=cycle,
                )

                # Compute error
                dds_error_pct = ((pyfvs_dds - native_dds) / native_dds * 100
                                 if native_dds > 0.01 else float('nan'))
                dg_error_pct = ((pyfvs_dg - native_dg) / native_dg * 100
                                if native_dg > 0.01 else float('nan'))

                result = {
                    'variant': variant,
                    'species': species,
                    'age': target_age,
                    'dbh': mean_dbh,
                    'cr': mean_cr,
                    'ba': ba_pre,
                    'pbal': mean_pbal,
                    'relht': relht,
                    'native_dds': native_dds,
                    'pyfvs_dds': pyfvs_dds,
                    'dds_error_pct': dds_error_pct,
                    'native_dg': native_dg,
                    'pyfvs_dg': pyfvs_dg,
                    'dg_error_pct': dg_error_pct,
                }
                results.append(result)

            except Exception as exc:
                console.print(f"  [yellow]Age {target_age}: {exc}[/yellow]")

    return results


def diagnose_without_native(
    variant: str,
    species_list: List[str],
) -> None:
    """Run PyFVS DDS diagnostic at fixed synthetic conditions (no native FVS).

    Useful for checking DDS model output when native library is not available.
    """
    cfg = VARIANT_CONFIG[variant]
    cycle = cfg['cycle']

    # Standard test conditions at various DBH values
    test_dbhs = [1.0, 3.0, 5.0, 8.0, 10.0, 15.0]
    cr = 0.40
    ba = 150.0
    pbal = 75.0
    relht = 1.0

    table = Table(title=f"{variant} PyFVS DDS at Fixed Conditions "
                        f"(CR={cr}, BA={ba}, PBAL={pbal}, SI={cfg['default_si']})")
    table.add_column("Species", style="bold")
    for d in test_dbhs:
        table.add_column(f"DBH={d}\"", justify="right")

    for species in species_list:
        row = [species]
        for dbh in test_dbhs:
            dds = compute_pyfvs_dds(
                variant=variant,
                species=species,
                dbh=dbh,
                crown_ratio=cr,
                site_index=cfg['default_si'],
                ba=ba,
                pbal=pbal,
                relht=relht,
                time_step=cycle,
            )
            dg = compute_pyfvs_dg(
                variant=variant,
                species=species,
                dbh=dbh,
                crown_ratio=cr,
                site_index=cfg['default_si'],
                ba=ba,
                pbal=pbal,
                relht=relht,
                time_step=cycle,
            )
            row.append(f"{dds:.2f} ({dg:.3f}\")")
        table.add_row(*row)

    console.print(table)


def print_results(results: List[Dict]) -> None:
    """Print comparison results in a formatted table."""
    if not results:
        console.print("[yellow]No results to display[/yellow]")
        return

    # Group by species
    species_seen = []
    for r in results:
        if r['species'] not in species_seen:
            species_seen.append(r['species'])

    for species in species_seen:
        species_results = [r for r in results if r['species'] == species]
        variant = species_results[0]['variant']

        table = Table(title=f"{variant} {species} — Tree-Level DDS Comparison "
                            f"(PyFVS vs Native FVS)")
        table.add_column("Age", justify="right")
        table.add_column("DBH", justify="right")
        table.add_column("CR", justify="right")
        table.add_column("BA", justify="right")
        table.add_column("RELHT", justify="right")
        table.add_column("Native DDS", justify="right")
        table.add_column("PyFVS DDS", justify="right")
        table.add_column("DDS Err%", justify="right")
        table.add_column("Native DG", justify="right")
        table.add_column("PyFVS DG", justify="right")
        table.add_column("DG Err%", justify="right")

        for r in species_results:
            dds_style = ""
            if not math.isnan(r['dds_error_pct']):
                if abs(r['dds_error_pct']) > 50:
                    dds_style = "red"
                elif abs(r['dds_error_pct']) > 25:
                    dds_style = "yellow"
                else:
                    dds_style = "green"

            dds_err_str = (f"{r['dds_error_pct']:+.1f}%"
                           if not math.isnan(r['dds_error_pct']) else "N/A")
            dg_err_str = (f"{r['dg_error_pct']:+.1f}%"
                          if not math.isnan(r['dg_error_pct']) else "N/A")

            table.add_row(
                str(r['age']),
                f"{r['dbh']:.1f}\"",
                f"{r['cr']:.2f}",
                f"{r['ba']:.0f}",
                f"{r['relht']:.2f}",
                f"{r['native_dds']:.2f}",
                f"{r['pyfvs_dds']:.2f}",
                f"[{dds_style}]{dds_err_str}[/{dds_style}]" if dds_style else dds_err_str,
                f"{r['native_dg']:.3f}\"",
                f"{r['pyfvs_dg']:.3f}\"",
                dg_err_str,
            )

        console.print(table)
        console.print()


def main():
    parser = argparse.ArgumentParser(
        description="Tree-level DDS diagnostic: PyFVS vs native FVS"
    )
    parser.add_argument(
        "--variant", "-v", default="SN",
        choices=list(VARIANT_CONFIG.keys()),
        help="FVS variant (default: SN)",
    )
    parser.add_argument(
        "--species", "-s", nargs="+", default=None,
        help="Species codes to test (default: variant-specific defaults)",
    )
    parser.add_argument(
        "--no-native", action="store_true",
        help="Skip native FVS comparison, just show PyFVS DDS values",
    )
    args = parser.parse_args()

    variant = args.variant.upper()
    species_list = args.species or DEFAULT_SPECIES.get(variant, ['LP'])
    species_list = [s.upper() for s in species_list]

    console.print(f"[bold]DDS Diagnostic: {variant} variant[/bold]")
    console.print(f"Species: {', '.join(species_list)}")
    console.print()

    # Always show PyFVS DDS at fixed conditions
    diagnose_without_native(variant, species_list)
    console.print()

    # Try native comparison if available
    if not args.no_native:
        results = diagnose_with_native(variant, species_list)
        print_results(results)
    else:
        console.print("[dim]Skipping native FVS comparison (--no-native)[/dim]")


if __name__ == "__main__":
    main()

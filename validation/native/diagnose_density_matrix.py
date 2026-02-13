"""
Density-matrix DDS diagnostic: separate intrinsic DDS model error from
mortality/competition feedback error.

Runs native FVS and PyFVS at multiple planting densities (100, 300, 500 TPA)
for each species. If DDS errors are similar across densities, the error is
intrinsic to the DDS equation. If errors grow with density, mortality and
competition feedback loops are amplifying the discrepancy.

Usage:
    uv run python -m validation.native.diagnose_density_matrix
    uv run python -m validation.native.diagnose_density_matrix --species LP RO
"""

import argparse
import math
import sys
from pathlib import Path
from typing import Dict, List

from rich.console import Console
from rich.table import Table

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from validation.native.diagnose_dds import (
    compute_pyfvs_dds,
    compute_pyfvs_dg,
    VARIANT_CONFIG,
)
from pyfvs.bark_ratio import create_bark_ratio_model

console = Console()

# Test densities: low (minimal mortality), moderate, high (mortality-dominated)
DENSITY_LEVELS = [100, 300, 500]

# Ages to check at each density
TARGET_AGES = [10, 15, 20, 25, 30, 35, 40]

# Default species to test
DEFAULT_SPECIES = ['LP', 'WO', 'RO', 'YP', 'SU']


def run_native_at_density(
    variant: str,
    species: str,
    tpa: int,
    site_index: float,
    cycle: int,
    target_ages: List[int],
) -> List[Dict]:
    """Run native FVS at a specific density and collect DDS comparisons."""
    from pyfvs.native import NativeStand

    results = []

    for target_age in target_ages:
        num_pre_cycles = target_age // cycle
        if num_pre_cycles < 1:
            continue

        try:
            # Simulation A: grow to target_age, snapshot pre-growth conditions
            with NativeStand(variant=variant) as ns_pre:
                ns_pre.initialize_planted(
                    trees_per_acre=tpa,
                    site_index=site_index,
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
                tpa_stand_pre = metrics_pre.get('tpa', 0.0)

                # Mean tree conditions (weighted by TPA)
                total_tpa = sum(tpa_pre)
                if total_tpa <= 0:
                    continue

                mean_dbh = sum(d * t for d, t in zip(dbh_pre, tpa_pre)) / total_tpa
                mean_ht = sum(h * t for h, t in zip(ht_pre, tpa_pre)) / total_tpa
                mean_cr = sum(c * t for c, t in zip(cr_pre, tpa_pre)) / total_tpa

                # Normalize CR to 0-1 if on 0-100 scale
                if mean_cr > 1.0:
                    mean_cr /= 100.0

                mean_pbal = ba_pre * 0.5
                relht = mean_ht / top_ht if top_ht > 0 else 1.0

            # Simulation B: grow to target_age + cycle
            with NativeStand(variant=variant) as ns_post:
                ns_post.initialize_planted(
                    trees_per_acre=tpa,
                    site_index=site_index,
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
                tpa_stand_post = metrics_post.get('tpa', 0.0)

            # Native mean DG
            total_tpa_post = sum(tpa_post)
            if total_tpa_post <= 0:
                continue
            mean_dbh_post = sum(d * t for d, t in zip(dbh_post, tpa_post)) / total_tpa_post
            native_dg = mean_dbh_post - mean_dbh

            # Native DDS (approximate)
            bark_model = create_bark_ratio_model(species, variant=variant)
            bark_ratio = bark_model.calculate_bark_ratio(mean_dbh)
            dib_pre = mean_dbh * bark_ratio
            dib_post = mean_dbh_post * bark_ratio
            native_dds = dib_post ** 2 - dib_pre ** 2

            # PyFVS DDS at same conditions
            pyfvs_dg = compute_pyfvs_dg(
                variant=variant,
                species=species,
                dbh=mean_dbh,
                crown_ratio=mean_cr,
                site_index=site_index,
                ba=ba_pre,
                pbal=mean_pbal,
                relht=relht,
                time_step=cycle,
            )

            # Errors
            dg_error_pct = ((pyfvs_dg - native_dg) / native_dg * 100
                            if native_dg > 0.01 else float('nan'))

            results.append({
                'age': target_age,
                'tpa_init': tpa,
                'tpa_actual': tpa_stand_pre,
                'tpa_post': tpa_stand_post,
                'mortality_pct': (1 - tpa_stand_pre / tpa) * 100,
                'dbh': mean_dbh,
                'cr': mean_cr,
                'ba': ba_pre,
                'relht': relht,
                'native_dg': native_dg,
                'pyfvs_dg': pyfvs_dg,
                'dg_error_pct': dg_error_pct,
            })

        except Exception as exc:
            console.print(f"  [yellow]TPA={tpa} Age {target_age}: {exc}[/yellow]")

    return results


def run_species_density_matrix(variant: str, species: str, site_index: float, cycle: int):
    """Run full density matrix for one species."""
    console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
    console.print(f"[bold]{species} — SI={site_index}, Variant={variant}, Cycle={cycle}yr[/bold]")
    console.print(f"[bold cyan]{'='*80}[/bold cyan]")

    all_results = {}
    for tpa_level in DENSITY_LEVELS:
        console.print(f"  Running {tpa_level} TPA...", end=" ")
        results = run_native_at_density(
            variant, species, tpa_level, site_index, cycle, TARGET_AGES
        )
        all_results[tpa_level] = results
        console.print(f"[green]{len(results)} age points[/green]")

    # Print per-density tables
    for tpa_level in DENSITY_LEVELS:
        results = all_results[tpa_level]
        if not results:
            continue

        table = Table(title=f"{species} at {tpa_level} TPA")
        table.add_column("Age", justify="right", style="bold")
        table.add_column("TPA Now", justify="right")
        table.add_column("Mort%", justify="right")
        table.add_column("DBH", justify="right")
        table.add_column("CR", justify="right")
        table.add_column("BA", justify="right")
        table.add_column("Native DG", justify="right")
        table.add_column("PyFVS DG", justify="right")
        table.add_column("DG Err%", justify="right")

        for r in results:
            err = r['dg_error_pct']
            if math.isnan(err):
                style = ""
                err_str = "N/A"
            elif abs(err) < 10:
                style = "green"
                err_str = f"{err:+.1f}%"
            elif abs(err) < 25:
                style = "yellow"
                err_str = f"{err:+.1f}%"
            else:
                style = "red"
                err_str = f"{err:+.1f}%"

            table.add_row(
                str(r['age']),
                f"{r['tpa_actual']:.0f}",
                f"{r['mortality_pct']:.0f}%",
                f"{r['dbh']:.1f}\"",
                f"{r['cr']:.2f}",
                f"{r['ba']:.0f}",
                f"{r['native_dg']:.3f}\"",
                f"{r['pyfvs_dg']:.3f}\"",
                f"[{style}]{err_str}[/{style}]" if style else err_str,
            )
        console.print(table)

    # Cross-density comparison table (the key diagnostic)
    console.print()
    cross_table = Table(title=f"{species} — DG Error% Across Densities (Intrinsic vs Feedback)")
    cross_table.add_column("Age", justify="right", style="bold")
    for tpa_level in DENSITY_LEVELS:
        cross_table.add_column(f"{tpa_level} TPA", justify="right")
    cross_table.add_column("Spread", justify="right")
    cross_table.add_column("Interpretation", justify="left")

    for age in TARGET_AGES:
        row = [str(age)]
        errors = []
        for tpa_level in DENSITY_LEVELS:
            matching = [r for r in all_results[tpa_level] if r['age'] == age]
            if matching:
                err = matching[0]['dg_error_pct']
                if not math.isnan(err):
                    errors.append(err)
                    style = "green" if abs(err) < 10 else ("yellow" if abs(err) < 25 else "red")
                    row.append(f"[{style}]{err:+.1f}%[/{style}]")
                else:
                    row.append("N/A")
            else:
                row.append("--")

        if len(errors) >= 2:
            spread = max(errors) - min(errors)
            if spread < 10:
                row.append(f"[green]{spread:.1f}pp[/green]")
                row.append("[green]Intrinsic (DDS eq)[/green]")
            elif spread < 20:
                row.append(f"[yellow]{spread:.1f}pp[/yellow]")
                row.append("[yellow]Mixed[/yellow]")
            else:
                row.append(f"[red]{spread:.1f}pp[/red]")
                row.append("[red]Feedback-driven[/red]")
        else:
            row.append("--")
            row.append("--")

        cross_table.add_row(*row)

    console.print(cross_table)
    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Density-matrix DDS diagnostic: intrinsic vs feedback error"
    )
    parser.add_argument(
        "--variant", "-v", default="SN",
        help="FVS variant (default: SN)",
    )
    parser.add_argument(
        "--species", "-s", nargs="+", default=None,
        help="Species codes (default: LP WO RO YP SU)",
    )
    args = parser.parse_args()

    variant = args.variant.upper()
    species_list = [s.upper() for s in (args.species or DEFAULT_SPECIES)]
    cfg = VARIANT_CONFIG[variant]

    console.print("[bold]Density-Matrix DDS Diagnostic[/bold]")
    console.print(f"Variant: {variant}, SI={cfg['default_si']}, "
                  f"Densities: {DENSITY_LEVELS} TPA")
    console.print(f"Species: {', '.join(species_list)}")
    console.print()

    # Check native library
    try:
        from pyfvs.native import fvs_library_available
        if not fvs_library_available(variant):
            console.print(f"[red]FVS {variant} library not available[/red]")
            sys.exit(1)
    except ImportError:
        console.print("[red]pyfvs.native not available[/red]")
        sys.exit(1)

    all_species_results = {}
    for species in species_list:
        all_species_results[species] = run_species_density_matrix(
            variant, species, cfg['default_si'], cfg['cycle']
        )

    # Final summary across all species
    console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
    console.print("[bold]Final Summary: Mean |DG Error%| by Density[/bold]")
    console.print(f"[bold cyan]{'='*80}[/bold cyan]")

    summary = Table(title="Mean Absolute DG Error% by Species and Density")
    summary.add_column("Species", style="bold")
    for tpa_level in DENSITY_LEVELS:
        summary.add_column(f"{tpa_level} TPA", justify="right")
    summary.add_column("Verdict", justify="left")

    for species in species_list:
        row = [species]
        mean_errors = []
        for tpa_level in DENSITY_LEVELS:
            results = all_species_results[species].get(tpa_level, [])
            errs = [abs(r['dg_error_pct']) for r in results
                    if not math.isnan(r['dg_error_pct'])]
            if errs:
                mean_err = sum(errs) / len(errs)
                mean_errors.append(mean_err)
                style = "green" if mean_err < 10 else ("yellow" if mean_err < 25 else "red")
                row.append(f"[{style}]{mean_err:.1f}%[/{style}]")
            else:
                row.append("--")

        # Verdict: does error grow with density?
        if len(mean_errors) >= 2:
            if mean_errors[-1] > mean_errors[0] + 10:
                row.append("[red]Feedback amplifies error[/red]")
            elif mean_errors[-1] < mean_errors[0] - 10:
                row.append("[yellow]Feedback reduces error[/yellow]")
            else:
                row.append("[green]Intrinsic to DDS equation[/green]")
        else:
            row.append("--")

        summary.add_row(*row)

    console.print(summary)


if __name__ == "__main__":
    main()

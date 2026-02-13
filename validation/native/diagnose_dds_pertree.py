"""
Per-tree DDS diagnostic: eliminate mean-tree approximation artifacts.

Instead of comparing at the mean-tree level (where PBAL≈BA×0.5 and
mean-of-nonlinear ≠ nonlinear-of-mean), this diagnostic:

1. Gets the FULL native FVS tree list at age N (with DG from last cycle)
2. Back-computes pre-growth DBH for each tree (DBH - DG)
3. Computes EXACT per-tree PBAL and RELHT from the tree list
4. Feeds each tree's exact conditions into PyFVS DDS
5. Compares TPA-weighted aggregate predicted DG to native DG

This isolates whether the DDS EQUATION itself is wrong, independent of
diagnostic methodology artifacts.

Usage:
    uv run python -m validation.native.diagnose_dds_pertree
    uv run python -m validation.native.diagnose_dds_pertree --species LP RO
"""

import argparse
import math
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
from rich.console import Console
from rich.table import Table

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pyfvs.sn_diameter_growth import create_sn_diameter_growth_model
from pyfvs.bark_ratio import create_bark_ratio_model

console = Console()

# SN variant config
CYCLE = 5
DEFAULT_SI = 70
ECOUNIT = 'M231'

# Ages to analyze (must be >= 2*CYCLE so DG attribute reflects a real cycle)
TARGET_AGES = [15, 20, 25, 30, 35, 40, 45, 50]

# Species + their SIGMAR values + S231T ecounit effects for reference
# S231T values from sn/dgf.f DATA S231T/ array, indexed by species number
# Native FVS with state=0 defaults to ecounit '231DD' (habtyp.f:135)
# which sets KS231T=1 (dgf.f:1077-1078), adding S231T(ISPC) to DGCON
SPECIES_CONFIG = {
    'LP': {'label': 'Loblolly Pine', 'sigmar': 0.4687, 's231t': -0.183317},  # idx 13
    'WO': {'label': 'White Oak',     'sigmar': 0.4407, 's231t':  0.000000},  # idx 63
    'RO': {'label': 'N. Red Oak',    'sigmar': 0.4048, 's231t':  0.132129},  # idx 75
    'YP': {'label': 'Yellow Poplar', 'sigmar': 0.5181, 's231t':  0.000000},  # idx 45
    'SU': {'label': 'Sweetgum',      'sigmar': 0.5779, 's231t': -0.034773},  # idx 44
}


def compute_pbal_per_tree(dbh_arr: np.ndarray, tpa_arr: np.ndarray) -> np.ndarray:
    """Compute exact PBAL for each tree from the tree list.

    PBAL_i = sum of basal area of all trees with DBH > DBH_i.
    In Fortran: PBAL = BA * (1 - PCT/100) where PCT is percentile rank.
    """
    n = len(dbh_arr)
    ba_per_tree = (math.pi / 4.0) * (dbh_arr ** 2) / 144.0 * tpa_arr
    pbal = np.zeros(n)

    # Sort indices by DBH descending
    sorted_idx = np.argsort(-dbh_arr)
    cumulative_ba = 0.0

    for rank, idx in enumerate(sorted_idx):
        pbal[idx] = cumulative_ba
        cumulative_ba += ba_per_tree[idx]

    return pbal


def compute_avh(dbh_arr: np.ndarray, ht_arr: np.ndarray, tpa_arr: np.ndarray,
                target_tpa: float = 40.0) -> float:
    """Compute AVH: TPA-weighted mean height of the top 40 TPA by DBH.

    Matches Fortran AVHT40 subroutine.
    """
    sorted_idx = np.argsort(-dbh_arr)
    cumul_tpa = 0.0
    ht_sum = 0.0
    tpa_sum = 0.0

    for idx in sorted_idx:
        remaining = target_tpa - cumul_tpa
        if remaining <= 0:
            break
        use_tpa = min(tpa_arr[idx], remaining)
        ht_sum += ht_arr[idx] * use_tpa
        tpa_sum += use_tpa
        cumul_tpa += tpa_arr[idx]

    if tpa_sum <= 0:
        return np.mean(ht_arr)  # fallback

    return ht_sum / tpa_sum


def run_pertree_comparison(species: str, tpa_init: int, age: int) -> Dict:
    """Run per-tree DDS comparison at a specific age.

    Returns dict with aggregate and per-tree comparison data.
    """
    from pyfvs.native import NativeStand

    with NativeStand(variant='SN') as ns:
        ns.initialize_planted(tpa_init, DEFAULT_SI, species)
        ns.grow(age)

        dims = ns._bindings.get_dim_sizes()
        ntrees = dims.get('ntrees', 0)
        if ntrees == 0:
            return None

        # Get per-tree attributes
        dbh = ns._bindings.get_tree_attr('dbh', ntrees)
        ht = ns._bindings.get_tree_attr('ht', ntrees)
        cr = ns._bindings.get_tree_attr('cratio', ntrees)
        tpa = ns._bindings.get_tree_attr('tpa', ntrees)
        native_dg = ns._bindings.get_tree_attr('dg', ntrees)

    # CR is on 0-100 scale from native FVS
    cr_proportion = cr / 100.0

    # CRITICAL: native DG is INSIDE-BARK (set in dgdriv.f as sqrt(D²+DDS*FRM)-D
    # where D=DBH*BRATIO). DBH is updated via: DBH += DG/BRATIO (update.f:115).
    # So pre-growth outside-bark DBH = current DBH - DG_ib/bark_ratio.
    bark_model = create_bark_ratio_model(species, variant='SN')
    bark_ratios = np.array([bark_model.calculate_bark_ratio(float(d)) for d in dbh])
    pre_dbh = dbh - native_dg / bark_ratios
    pre_dbh = np.maximum(pre_dbh, 0.1)  # safety floor

    # Compute stand BA from pre-growth DBH
    pre_ba = np.sum((math.pi / 4.0) * (pre_dbh ** 2) / 144.0 * tpa)

    # Compute per-tree PBAL from pre-growth DBH
    pre_pbal = compute_pbal_per_tree(pre_dbh, tpa)

    # Compute AVH and per-tree RELHT from current heights
    # (heights don't change as dramatically as DBH in one cycle)
    avh = compute_avh(pre_dbh, ht, tpa, target_tpa=40.0)
    relht = np.minimum(1.5, np.where(avh > 0, ht / avh, 1.0))

    # Get the DDS model (bark_model already created above for pre_dbh)
    dds_model = create_sn_diameter_growth_model(species)

    # Compute PyFVS DDS and DG for each tree
    # CRITICAL: native DG is INSIDE-BARK, so we compute inside-bark DG
    # for an apples-to-apples comparison.
    pyfvs_dg_ib = np.zeros(ntrees)
    pyfvs_dds = np.zeros(ntrees)

    # NativeStand keyword file has no ECOUNIT keyword — native FVS uses
    # default location (state=0) which defaults to ecounit '231DD' (habtyp.f:135).
    # '231DD' sets KS231T=1 (dgf.f:1077), adding S231T(ISPC) to DGCON.
    # To compare apples-to-apples, use the S231T value for this species.
    ecounit_effect = SPECIES_CONFIG[species]['s231t']

    for i in range(ntrees):
        dds_val = dds_model.calculate_dds(
            dbh=float(pre_dbh[i]),
            crown_ratio=float(cr_proportion[i]),
            site_index=DEFAULT_SI,
            ba=float(pre_ba),
            pbal=float(pre_pbal[i]),
            relht=float(relht[i]),
            ecounit_effect=ecounit_effect,
            time_step=CYCLE,
        )
        pyfvs_dds[i] = dds_val

        # Convert DDS to INSIDE-BARK DG (matching native FVS)
        # DG_ib = sqrt(D_ib² + DDS) - D_ib
        br = bark_ratios[i]
        dib_old = float(pre_dbh[i]) * br
        dib_new_sq = dib_old ** 2 + dds_val
        if dib_new_sq > dib_old ** 2:
            pyfvs_dg_ib[i] = math.sqrt(dib_new_sq) - dib_old
        else:
            pyfvs_dg_ib[i] = 0.0

    # Aggregate comparison (TPA-weighted)
    # Both native_dg and pyfvs_dg_ib are now INSIDE-BARK
    total_tpa = np.sum(tpa)
    native_mean_dg = np.average(native_dg, weights=tpa)
    pyfvs_mean_dg = np.average(pyfvs_dg_ib, weights=tpa)

    dg_error_pct = ((pyfvs_mean_dg - native_mean_dg) / native_mean_dg * 100
                    if native_mean_dg > 0.01 else float('nan'))

    # Per-tree error statistics
    # Native DG includes stochastic error, so per-tree comparison is noisy.
    # But the ratio distribution tells us about systematic bias.
    valid = native_dg > 0.01
    if np.any(valid):
        ratios = pyfvs_dg_ib[valid] / native_dg[valid]
        median_ratio = np.median(ratios)
        mean_ratio = np.average(ratios, weights=tpa[valid])
    else:
        median_ratio = float('nan')
        mean_ratio = float('nan')

    # Break down ln(DDS) terms at the TPA-weighted mean conditions
    mean_pre_dbh = np.average(pre_dbh, weights=tpa)
    mean_cr = np.average(cr_proportion, weights=tpa)
    mean_pbal = np.average(pre_pbal, weights=tpa)
    mean_relht = np.average(relht, weights=tpa)

    params = dds_model.coefficients
    term_breakdown = {
        'INTERC': params.get('INTERC', params.get('b1', 0)),
        'LDBH*ln(D)': params.get('LDBH', params.get('b2', 0)) * math.log(max(0.1, mean_pre_dbh)),
        'DBH2*D²': params.get('DBH2', params.get('b3', 0)) * mean_pre_dbh ** 2,
        'LCRWN*ln(CR%)': params.get('LCRWN', params.get('b4', 0)) * math.log(max(25, mean_cr * 100)),
        'HREL*RELHT': params.get('HREL', params.get('b5', 0)) * mean_relht,
        'ISIO*SI': params.get('ISIO', params.get('b6', 0)) * DEFAULT_SI,
        'PLTB*BA': params.get('PLTB', params.get('b7', 0)) * pre_ba,
        'PNTBL*PBAL': params.get('PNTBL', params.get('b8', 0)) * mean_pbal,
        'ecounit': ecounit_effect,
    }

    return {
        'age': age,
        'ntrees': ntrees,
        'tpa': total_tpa,
        'pre_ba': pre_ba,
        'mean_pre_dbh': mean_pre_dbh,
        'mean_cr': mean_cr,
        'mean_pbal': mean_pbal,
        'mean_pbal_pct_ba': (mean_pbal / pre_ba * 100) if pre_ba > 0 else 0,
        'mean_relht': mean_relht,
        'avh': avh,
        'native_mean_dg': native_mean_dg,
        'pyfvs_mean_dg': pyfvs_mean_dg,
        'dg_error_pct': dg_error_pct,
        'median_ratio': median_ratio,
        'mean_ratio': mean_ratio,
        'term_breakdown': term_breakdown,
    }


def run_species(species: str, tpa_init: int = 500):
    """Run full per-tree comparison for one species."""
    cfg = SPECIES_CONFIG[species]
    console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
    console.print(f"[bold]{cfg['label']} ({species}) — {tpa_init} TPA, SI={DEFAULT_SI}, "
                  f"σ={cfg['sigmar']}, S231T={cfg['s231t']:+.4f}, "
                  f"Baskerville bias={math.exp(0.5*cfg['sigmar']**2)-1:.1%}[/bold]")
    console.print(f"[bold cyan]{'='*80}[/bold cyan]")

    results = []
    for age in TARGET_AGES:
        try:
            r = run_pertree_comparison(species, tpa_init, age)
            if r:
                results.append(r)
        except Exception as e:
            console.print(f"  [yellow]Age {age}: {e}[/yellow]")

    if not results:
        console.print("[red]No results[/red]")
        return results

    # Main comparison table
    table = Table(title=f"{species} Per-Tree DDS Comparison")
    table.add_column("Age", justify="right", style="bold")
    table.add_column("Trees", justify="right")
    table.add_column("TPA", justify="right")
    table.add_column("Pre DBH", justify="right")
    table.add_column("Pre BA", justify="right")
    table.add_column("PBAL", justify="right")
    table.add_column("PBAL%BA", justify="right")
    table.add_column("RELHT", justify="right")
    table.add_column("Nat DG", justify="right")
    table.add_column("PyF DG", justify="right")
    table.add_column("Err%", justify="right")
    table.add_column("Med Ratio", justify="right")

    for r in results:
        err = r['dg_error_pct']
        if math.isnan(err):
            style = ""
        elif abs(err) < 10:
            style = "green"
        elif abs(err) < 25:
            style = "yellow"
        else:
            style = "red"

        err_str = f"{err:+.1f}%" if not math.isnan(err) else "N/A"

        table.add_row(
            str(r['age']),
            str(r['ntrees']),
            f"{r['tpa']:.0f}",
            f"{r['mean_pre_dbh']:.1f}\"",
            f"{r['pre_ba']:.0f}",
            f"{r['mean_pbal']:.0f}",
            f"{r['mean_pbal_pct_ba']:.0f}%",
            f"{r['mean_relht']:.3f}",
            f"{r['native_mean_dg']:.3f}\"",
            f"{r['pyfvs_mean_dg']:.3f}\"",
            f"[{style}]{err_str}[/{style}]" if style else err_str,
            f"{r['median_ratio']:.3f}" if not math.isnan(r['median_ratio']) else "N/A",
        )

    console.print(table)

    # Term breakdown for first and last ages
    for r in [results[0], results[-1]]:
        terms = r['term_breakdown']
        ln_dds = sum(terms.values())
        console.print(f"\n  [dim]ln(DDS) breakdown at age {r['age']} "
                      f"(DBH={r['mean_pre_dbh']:.1f}\", BA={r['pre_ba']:.0f}, "
                      f"PBAL={r['mean_pbal']:.0f}, RELHT={r['mean_relht']:.3f}):[/dim]")
        for term_name, term_val in terms.items():
            bar = "+" * int(abs(term_val) * 10) if term_val >= 0 else "-" * int(abs(term_val) * 10)
            console.print(f"    {term_name:>16}: {term_val:+.4f}  {bar}")
        console.print(f"    {'Σ ln(DDS)':>16}: {ln_dds:+.4f} → DDS={math.exp(ln_dds):.3f}")

    return results


def compare_old_vs_new(species: str, results: List[Dict]):
    """Compare per-tree results to the old mean-tree diagnostic."""
    console.print(f"\n[bold]  {species}: Per-Tree vs Old Mean-Tree Diagnostic[/bold]")

    # The old diagnostic used PBAL=BA*0.5. Show how actual PBAL differs.
    table = Table(title=f"{species} — Actual PBAL vs BA×0.5 Approximation")
    table.add_column("Age", justify="right")
    table.add_column("BA", justify="right")
    table.add_column("Actual PBAL", justify="right")
    table.add_column("BA×0.5", justify="right")
    table.add_column("PBAL Error", justify="right")
    table.add_column("Impact on ln(DDS)", justify="right")

    model = create_sn_diameter_growth_model(species)
    pntbl = model.coefficients.get('PNTBL', model.coefficients.get('b8', -0.0026))

    for r in results:
        ba = r['pre_ba']
        actual_pbal = r['mean_pbal']
        approx_pbal = ba * 0.5
        pbal_error = approx_pbal - actual_pbal
        lndds_impact = pntbl * pbal_error

        style = "green" if abs(lndds_impact) < 0.02 else ("yellow" if abs(lndds_impact) < 0.05 else "red")
        table.add_row(
            str(r['age']),
            f"{ba:.0f}",
            f"{actual_pbal:.1f}",
            f"{approx_pbal:.1f}",
            f"{pbal_error:+.1f}",
            f"[{style}]{lndds_impact:+.4f}[/{style}]",
        )

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Per-tree DDS diagnostic (eliminates mean-tree artifacts)"
    )
    parser.add_argument(
        "--species", "-s", nargs="+", default=None,
        help="Species codes (default: LP WO RO YP SU)",
    )
    parser.add_argument(
        "--tpa", type=int, default=500,
        help="Initial TPA (default: 500)",
    )
    args = parser.parse_args()

    species_list = [s.upper() for s in (args.species or list(SPECIES_CONFIG.keys()))]

    console.print("[bold]Per-Tree DDS Diagnostic: PyFVS vs Native FVS[/bold]")
    console.print(f"SN variant, SI={DEFAULT_SI}, {args.tpa} TPA")
    console.print("Native default ecounit: 231DD (S231T effect applied per species)")
    console.print("Uses EXACT per-tree PBAL and RELHT (not approximations)")
    console.print()

    # Check native library
    try:
        from pyfvs.native import fvs_library_available
        if not fvs_library_available('SN'):
            console.print("[red]FVS SN library not available[/red]")
            sys.exit(1)
    except ImportError:
        console.print("[red]pyfvs.native not available[/red]")
        sys.exit(1)

    all_results = {}
    for species in species_list:
        results = run_species(species, args.tpa)
        all_results[species] = results
        if results:
            compare_old_vs_new(species, results)

    # Final summary
    console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
    console.print("[bold]Summary: Per-Tree DG Error% at Key Ages[/bold]")
    console.print(f"[bold cyan]{'='*80}[/bold cyan]")

    summary = Table(title="Per-Tree DG Error% (with exact PBAL and RELHT)")
    summary.add_column("Species", style="bold")
    summary.add_column("σ", justify="right")
    summary.add_column("Bask.", justify="right")
    for age in [15, 20, 30, 40, 50]:
        summary.add_column(f"Age {age}", justify="right")
    summary.add_column("Mean |Err|", justify="right")

    for species in species_list:
        cfg = SPECIES_CONFIG[species]
        bask = math.exp(0.5 * cfg['sigmar'] ** 2) - 1
        row = [cfg['label'], f"{cfg['sigmar']:.3f}", f"+{bask:.0%}"]

        errors = []
        for age in [15, 20, 30, 40, 50]:
            matching = [r for r in all_results.get(species, []) if r['age'] == age]
            if matching:
                err = matching[0]['dg_error_pct']
                errors.append(abs(err))
                style = "green" if abs(err) < 10 else ("yellow" if abs(err) < 25 else "red")
                row.append(f"[{style}]{err:+.1f}%[/{style}]")
            else:
                row.append("--")

        mean_err = sum(errors) / len(errors) if errors else 0
        style = "green" if mean_err < 10 else ("yellow" if mean_err < 25 else "red")
        row.append(f"[{style}]{mean_err:.1f}%[/{style}]")
        summary.add_row(*row)

    console.print(summary)


if __name__ == "__main__":
    main()

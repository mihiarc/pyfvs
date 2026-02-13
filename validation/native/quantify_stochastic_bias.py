"""
Quantify the stochastic transform bias in native FVS diameter growth.

Native FVS computes DG = sqrt(D² + DDS * FRM) - D where FRM = exp(Z),
Z ~ truncated N(0, σ²) at ±DGSD*σ. This is a nonlinear (concave) transform,
so by Jensen's inequality:

    E[DG_stochastic] < sqrt(D² + DDS * E[FRM]) - D

Meanwhile PyFVS computes the deterministic:

    DG_det = sqrt(D² + DDS) - D

The question: how much does the stochastic transform bias E[DG] relative to DG_det?
If this bias accounts for the ~27% LP "overprediction" seen in the per-tree
diagnostic, then our DDS equation is actually correct.

Usage:
    uv run python -m validation.native.quantify_stochastic_bias
"""

import math
import sys
from pathlib import Path

import numpy as np
from rich.console import Console
from rich.table import Table

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

console = Console()

# SN variant SIGMAR values (from blkdat.f)
SPECIES_SIGMAR = {
    'LP': 0.4687,
    'WO': 0.4407,
    'RO': 0.4048,
    'YP': 0.5181,
    'SU': 0.5779,
}

DGSD = 2.0  # Error truncation at ±2 standard deviations (grinit.f:171)
N_SAMPLES = 100_000  # Monte Carlo sample size


def compute_stochastic_bias(d_ib: float, dds: float, sigma: float,
                            dgsd: float = 2.0, n_samples: int = 100_000,
                            rng: np.random.Generator = None) -> dict:
    """Compute the stochastic transform bias for DG.

    Args:
        d_ib: Inside-bark diameter (inches)
        dds: Deterministic DDS (change in D² inside bark)
        sigma: Standard error (SIGMAR or SSIGMA)
        dgsd: Truncation bound in std devs
        n_samples: Monte Carlo samples
        rng: Random number generator

    Returns:
        dict with dg_det, e_dg_stoch, bias_pct, e_frm, etc.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    dsq = d_ib ** 2

    # Deterministic DG (what PyFVS computes)
    dg_det = math.sqrt(dsq + dds) - d_ib

    # Generate truncated normal Z ~ N(0, sigma²), |Z| <= dgsd*sigma
    z_samples = rng.normal(0, sigma, size=n_samples * 2)
    z_samples = z_samples[np.abs(z_samples) <= dgsd * sigma][:n_samples]

    # FRM = exp(Z)
    frm_samples = np.exp(z_samples)
    e_frm = np.mean(frm_samples)

    # Stochastic DG = sqrt(D² + DDS * FRM) - D
    dg_stoch = np.sqrt(dsq + dds * frm_samples) - d_ib
    dg_stoch = np.maximum(dg_stoch, 0.0)  # floor at 0 (matching Fortran behavior)

    e_dg_stoch = np.mean(dg_stoch)

    # Bias: how much higher is deterministic vs stochastic mean?
    bias_pct = ((dg_det - e_dg_stoch) / e_dg_stoch * 100
                if e_dg_stoch > 0.001 else float('nan'))

    # Upper bound (if we just use E[FRM] instead of Jensen's)
    dg_upper = math.sqrt(dsq + dds * e_frm) - d_ib

    return {
        'd_ib': d_ib,
        'dds': dds,
        'sigma': sigma,
        'dg_det': dg_det,
        'e_dg_stoch': e_dg_stoch,
        'dg_upper': dg_upper,
        'bias_det_vs_stoch_pct': bias_pct,
        'e_frm': e_frm,
        'baskerville_bias_pct': (e_frm - 1.0) * 100,
        'jensen_effect_pct': ((dg_upper - e_dg_stoch) / e_dg_stoch * 100
                              if e_dg_stoch > 0.001 else float('nan')),
    }


def run_species_analysis(species: str, conditions: list[dict]):
    """Analyze stochastic bias for a species across conditions."""
    sigma = SPECIES_SIGMAR[species]

    console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
    console.print(f"[bold]{species} — σ={sigma:.4f}, "
                  f"Baskerville=+{math.exp(0.5*sigma**2)-1:.1%}, DGSD={DGSD}[/bold]")
    console.print(f"[bold cyan]{'='*80}[/bold cyan]")

    table = Table(title=f"{species} Stochastic Transform Bias (N={N_SAMPLES:,})")
    table.add_column("Age", justify="right", style="bold")
    table.add_column("D_ib", justify="right")
    table.add_column("DDS", justify="right")
    table.add_column("DG_det", justify="right")
    table.add_column("E[DG_stoch]", justify="right")
    table.add_column("Det vs Stoch", justify="right")
    table.add_column("E[FRM]", justify="right")
    table.add_column("Baskerville", justify="right")
    table.add_column("Jensen", justify="right")

    rng = np.random.default_rng(42)

    for cond in conditions:
        r = compute_stochastic_bias(
            d_ib=cond['d_ib'],
            dds=cond['dds'],
            sigma=sigma,
            dgsd=DGSD,
            n_samples=N_SAMPLES,
            rng=rng,
        )

        bias_style = ("green" if abs(r['bias_det_vs_stoch_pct']) < 10 else
                       ("yellow" if abs(r['bias_det_vs_stoch_pct']) < 25 else "red"))

        table.add_row(
            str(cond.get('age', '?')),
            f"{r['d_ib']:.2f}\"",
            f"{r['dds']:.3f}",
            f"{r['dg_det']:.4f}\"",
            f"{r['e_dg_stoch']:.4f}\"",
            f"[{bias_style}]+{r['bias_det_vs_stoch_pct']:.1f}%[/{bias_style}]",
            f"{r['e_frm']:.4f}",
            f"+{r['baskerville_bias_pct']:.1f}%",
            f"+{r['jensen_effect_pct']:.1f}%",
        )

    console.print(table)


def main():
    """Compute stochastic bias at realistic LP conditions across ages."""

    console.print("[bold]Stochastic Transform Bias Analysis[/bold]")
    console.print("Comparing deterministic DG (PyFVS) to E[stochastic DG] (native FVS)")
    console.print(f"Monte Carlo: N={N_SAMPLES:,}, DGSD={DGSD}")
    console.print()

    # First: parameter sweep to show how bias varies with D and DDS
    console.print("[bold]Parameter Sweep: Bias vs D_ib and DDS[/bold]")
    sweep_table = Table(title="Stochastic Bias % (Det vs Stoch) — σ=0.4687 (LP)")
    sweep_table.add_column("D_ib", justify="right", style="bold")
    for dds_val in [0.5, 1.0, 2.0, 3.0, 5.0, 8.0]:
        sweep_table.add_column(f"DDS={dds_val}", justify="right")

    rng = np.random.default_rng(42)
    for d_ib in [2.0, 4.0, 6.0, 8.0, 10.0]:
        row = [f"{d_ib:.1f}\""]
        for dds_val in [0.5, 1.0, 2.0, 3.0, 5.0, 8.0]:
            r = compute_stochastic_bias(d_ib, dds_val, 0.4687, DGSD, N_SAMPLES, rng)
            bias = r['bias_det_vs_stoch_pct']
            style = "green" if abs(bias) < 10 else ("yellow" if abs(bias) < 25 else "red")
            row.append(f"[{style}]{bias:+.1f}%[/{style}]")
        sweep_table.add_row(*row)

    console.print(sweep_table)

    # Now: realistic LP conditions from per-tree diagnostic
    # (approximate D_ib and DDS at each age from a 500 TPA SI=70 plantation)
    console.print("\n[bold]Realistic LP Conditions (500 TPA, SI=70)[/bold]")
    console.print("[dim]D_ib and DDS estimated from per-tree diagnostic output[/dim]")

    # These are approximate — we need actual values from the per-tree diagnostic
    # Running the per-tree diagnostic to get exact values
    try:
        from pyfvs.native import NativeStand, fvs_library_available
        if not fvs_library_available('SN'):
            console.print("[yellow]Native FVS not available, using estimated conditions[/yellow]")
            raise ImportError("not available")

        from pyfvs.sn_diameter_growth import create_sn_diameter_growth_model
        from pyfvs.bark_ratio import create_bark_ratio_model

        dds_model = create_sn_diameter_growth_model('LP')
        bark_model = create_bark_ratio_model('LP', variant='SN')

        conditions = []
        for age in [15, 20, 25, 30, 35, 40, 45, 50]:
            with NativeStand(variant='SN') as ns:
                ns.initialize_planted(500, 70, 'LP')
                ns.grow(age)

                dims = ns._bindings.get_dim_sizes()
                ntrees = dims.get('ntrees', 0)
                if ntrees == 0:
                    continue

                dbh_arr = np.array(ns._bindings.get_tree_attr('dbh', ntrees))
                ht_arr = np.array(ns._bindings.get_tree_attr('ht', ntrees))
                cr_arr = np.array(ns._bindings.get_tree_attr('cratio', ntrees)) / 100.0
                tpa_arr = np.array(ns._bindings.get_tree_attr('tpa', ntrees))
                dg_arr = np.array(ns._bindings.get_tree_attr('dg', ntrees))

                # TPA-weighted mean conditions
                total_tpa = np.sum(tpa_arr)
                mean_dbh = np.average(dbh_arr, weights=tpa_arr)
                mean_ht = np.average(ht_arr, weights=tpa_arr)
                mean_cr = np.average(cr_arr, weights=tpa_arr)

                # Pre-growth DBH
                pre_dbh = dbh_arr - dg_arr
                pre_dbh = np.maximum(pre_dbh, 0.1)
                mean_pre_dbh = np.average(pre_dbh, weights=tpa_arr)

                # Bark ratio and inside-bark diameter
                br = bark_model.calculate_bark_ratio(mean_pre_dbh)
                d_ib = mean_pre_dbh * br

                # Compute approximate DDS at mean conditions
                pre_ba = np.sum(np.pi / 4.0 * pre_dbh**2 / 144.0 * tpa_arr)

                # Compute PBAL and RELHT
                ba_per_tree = np.pi / 4.0 * pre_dbh**2 / 144.0 * tpa_arr
                sorted_idx = np.argsort(-pre_dbh)
                pbal = np.zeros(ntrees)
                cumba = 0.0
                for idx in sorted_idx:
                    pbal[idx] = cumba
                    cumba += ba_per_tree[idx]
                mean_pbal = np.average(pbal, weights=tpa_arr)

                # AVH (top 40 TPA by DBH)
                cumtpa = 0.0
                htsum = 0.0
                tpasum = 0.0
                for idx in sorted_idx:
                    remaining = 40.0 - cumtpa
                    if remaining <= 0:
                        break
                    use_tpa = min(tpa_arr[idx], remaining)
                    htsum += ht_arr[idx] * use_tpa
                    tpasum += use_tpa
                    cumtpa += tpa_arr[idx]
                avh = htsum / tpasum if tpasum > 0 else np.mean(ht_arr)
                mean_relht = min(1.5, mean_ht / avh if avh > 0 else 1.0)

                # Compute DDS using PyFVS model
                dds_val = dds_model.calculate_dds(
                    dbh=float(mean_pre_dbh),
                    crown_ratio=float(mean_cr),
                    site_index=70.0,
                    ba=float(pre_ba),
                    pbal=float(mean_pbal),
                    relht=float(mean_relht),
                    ecounit_effect=0.0,
                    time_step=5,
                )

                conditions.append({
                    'age': age,
                    'd_ib': d_ib,
                    'dds': dds_val,
                    'dbh': mean_pre_dbh,
                    'ba': pre_ba,
                })

        if conditions:
            run_species_analysis('LP', conditions)

            # Also show the comparison between stochastic bias and actual per-tree error
            console.print("\n[bold]Comparing Stochastic Bias to Actual Per-Tree Error[/bold]")
            console.print("[dim]If stochastic bias ≈ per-tree error, our DDS equation is correct[/dim]")

            comp_table = Table(title="LP: Stochastic Bias vs Per-Tree Diagnostic Error")
            comp_table.add_column("Age", justify="right", style="bold")
            comp_table.add_column("D_ib", justify="right")
            comp_table.add_column("DDS", justify="right")
            comp_table.add_column("Stochastic Bias", justify="right")
            comp_table.add_column("Verdict", justify="left")

            rng = np.random.default_rng(42)
            for cond in conditions:
                r = compute_stochastic_bias(
                    d_ib=cond['d_ib'],
                    dds=cond['dds'],
                    sigma=0.4687,
                    dgsd=DGSD,
                    n_samples=N_SAMPLES,
                    rng=rng,
                )
                bias = r['bias_det_vs_stoch_pct']
                style = "green" if abs(bias) < 10 else ("yellow" if abs(bias) < 25 else "red")

                comp_table.add_row(
                    str(cond['age']),
                    f"{cond['d_ib']:.2f}\"",
                    f"{cond['dds']:.3f}",
                    f"[{style}]+{bias:.1f}%[/{style}]",
                    "Explains gap" if 15 < bias < 40 else (
                        "Partial" if 5 < bias <= 15 else "Does not explain"),
                )

            console.print(comp_table)

    except (ImportError, Exception) as e:
        console.print(f"[yellow]Could not get native conditions: {e}[/yellow]")
        console.print("Using estimated conditions instead")

        # Estimated LP conditions at various ages
        conditions = [
            {'age': 15, 'd_ib': 2.5, 'dds': 1.5},
            {'age': 20, 'd_ib': 3.5, 'dds': 2.0},
            {'age': 25, 'd_ib': 4.5, 'dds': 2.2},
            {'age': 30, 'd_ib': 5.5, 'dds': 2.0},
            {'age': 35, 'd_ib': 6.5, 'dds': 1.8},
            {'age': 40, 'd_ib': 7.5, 'dds': 1.5},
            {'age': 45, 'd_ib': 8.0, 'dds': 1.2},
            {'age': 50, 'd_ib': 8.5, 'dds': 1.0},
        ]
        run_species_analysis('LP', conditions)

    # Run for all species with estimated conditions
    console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
    console.print("[bold]All Species: Stochastic Bias at Typical Conditions[/bold]")
    console.print(f"[bold cyan]{'='*80}[/bold cyan]")

    summary = Table(title="Stochastic Bias Summary (D_ib=6\", DDS=2.0)")
    summary.add_column("Species", style="bold")
    summary.add_column("σ", justify="right")
    summary.add_column("Baskerville", justify="right")
    summary.add_column("Jensen Effect", justify="right")
    summary.add_column("Net Bias (Det vs Stoch)", justify="right")

    rng = np.random.default_rng(42)
    for species, sigma in SPECIES_SIGMAR.items():
        r = compute_stochastic_bias(6.0, 2.0, sigma, DGSD, N_SAMPLES, rng)
        bask = r['baskerville_bias_pct']
        jensen = r['jensen_effect_pct']
        net = r['bias_det_vs_stoch_pct']
        style = "green" if abs(net) < 10 else ("yellow" if abs(net) < 25 else "red")

        summary.add_row(
            species,
            f"{sigma:.4f}",
            f"+{bask:.1f}%",
            f"+{jensen:.1f}%",
            f"[{style}]{net:+.1f}%[/{style}]",
        )

    console.print(summary)

    console.print("\n[bold]Interpretation:[/bold]")
    console.print("  Baskerville: E[exp(Z)] > 1 → native DDS is LARGER on average")
    console.print("  Jensen: E[sqrt(f(X))] < sqrt(f(E[X])) → native DG is SMALLER")
    console.print("  Net bias = Baskerville - Jensen effect on DG")
    console.print("  If Net > 0: deterministic PyFVS overpredicts (DG_det > E[DG_stoch])")
    console.print("  If Net ≈ per-tree diagnostic error: DDS equation is correct!")


if __name__ == "__main__":
    main()

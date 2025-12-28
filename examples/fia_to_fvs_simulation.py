#!/usr/bin/env python3
"""
Example: FIA to FVS Growth Simulation Workflow

This example demonstrates the complete workflow for simulating forest growth
using FIA (Forest Inventory and Analysis) data with PyFVS (Python Forest
Vegetation Simulator).

The workflow covers:
1. Loading FIA data using PyFIA (with notes on database requirements)
2. Extracting tree and condition data for a specific plot
3. Creating a PyFVS Stand using Stand.from_fia_data()
4. Simulating growth for 25 years
5. Getting and displaying stand metrics
6. Generating a yield table

This script includes two sections:
- Section A: Working with a real FIA database (requires pyfia and database)
- Section B: Working with mock data (runnable without database)

Part of the FIA Python Ecosystem:
- PyFIA: Survey/plot data analysis (source)
- PyFVS: Growth/yield simulation (this package)
- GridFIA: Spatial raster analysis
- AskFIA: AI conversational interface

Usage:
    # With mock data (no database needed):
    uv run python examples/fia_to_fvs_simulation.py

    # With real FIA database:
    uv run python examples/fia_to_fvs_simulation.py /path/to/fia.duckdb 37

Requirements:
    - pyfvs (this package)
    - polars
    - rich (for terminal output)
    - pyfia (optional, for Section A with real database)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import polars as pl
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import PyFVS components
from pyfvs import Stand

console = Console()


# =============================================================================
# Section A: Working with Real FIA Database
# =============================================================================

def load_fia_plot_data(
    db_path: str,
    state_fips: int,
    plot_index: int = 0
) -> tuple[pl.DataFrame, pl.DataFrame, int]:
    """
    Load tree and condition data for a specific plot from FIA database.

    This function demonstrates the PyFIA data access pattern for extracting
    plot-level data suitable for FVS simulation.

    Parameters
    ----------
    db_path : str
        Path to FIA DuckDB database (e.g., "~/.pyfia/data/nc/nc.duckdb")
    state_fips : int
        State FIPS code (e.g., 37 for NC, 13 for GA, 45 for SC)
    plot_index : int
        Index of plot to select from available plots (0 = first plot)

    Returns
    -------
    tuple[pl.DataFrame, pl.DataFrame, int]
        - tree_df: Tree-level data for the selected plot
        - cond_df: Condition-level data for the selected plot
        - plot_cn: Control number of the selected plot

    Notes
    -----
    Requires PyFIA package and a valid FIA DuckDB database.
    Download databases using: `pyfia download <state_abbrev>`

    Example
    -------
    >>> tree_df, cond_df, plot_cn = load_fia_plot_data(
    ...     "~/.pyfia/data/nc/nc.duckdb",
    ...     state_fips=37,
    ...     plot_index=0
    ... )
    """
    # Import PyFIA (only if using real database)
    try:
        from pyfia import FIA
    except ImportError:
        raise ImportError(
            "PyFIA is required for loading FIA databases. "
            "Install with: pip install pyfia"
        )

    # Expand user path
    db_path = str(Path(db_path).expanduser())

    console.print(f"[cyan]Loading FIA database: {db_path}[/cyan]")

    # Initialize FIA database connection
    db = FIA(db_path)

    # Clip to state and most recent inventory
    db.clip_by_state(state_fips)
    db.clip_most_recent(eval_type="VOL")

    # Load required tables
    # PLOT table is needed first for EVALID filtering in subsequent queries
    db.load_table("PLOT")

    # Get plot locations to select a specific plot
    plots = db.get_plots(columns=["CN", "LAT", "LON", "INVYR", "COUNTYCD"])
    console.print(f"[green]Found {len(plots)} plots in database[/green]")

    # Select a plot by index
    if plot_index >= len(plots):
        console.print(f"[yellow]Warning: plot_index {plot_index} exceeds available plots, using 0[/yellow]")
        plot_index = 0

    selected_plot_cn = plots["CN"][plot_index]
    console.print(f"[cyan]Selected plot CN: {selected_plot_cn}[/cyan]")

    # Get tree data for the selected plot
    # Required columns for Stand.from_fia_data():
    #   - SPCD: FIA species code (integer)
    #   - DIA: Diameter at breast height (inches)
    #   - HT: Total height (feet)
    #   - TPA_UNADJ: Unadjusted trees per acre
    # Optional columns:
    #   - CR: Crown ratio (percentage, 0-100)
    #   - CONDID: Condition ID (for multi-condition plots)
    #   - STATUSCD: Tree status (1=live, 2=dead)
    #   - BHAGE/TOTAGE: Tree age
    trees = db.get_trees(columns=[
        "CN", "PLT_CN", "SUBP", "TREE", "CONDID",
        "SPCD", "DIA", "HT", "CR",
        "TPA_UNADJ", "STATUSCD",
        "DRYBIO_AG", "VOLCFNET"
    ])

    # Filter to selected plot
    tree_df = trees.filter(pl.col("PLT_CN") == selected_plot_cn)
    console.print(f"[green]Found {len(tree_df)} trees in selected plot[/green]")

    # Get condition data for site index and forest type
    # Key columns:
    #   - SICOND: Site index for the condition (feet at base age)
    #   - FORTYPCD: FIA forest type code
    #   - STDAGE: Stand age
    #   - ECOSUBCD: Ecological subsection code
    conds = db.get_conditions(columns=[
        "CN", "PLT_CN", "CONDID",
        "SICOND", "SIBASE", "SISP",
        "FORTYPCD", "STDAGE", "STDSZCD",
        "SITECLCD", "OWNGRPCD", "ECOSUBCD",
        "CONDPROP_UNADJ", "COND_STATUS_CD"
    ])

    # Filter to selected plot
    cond_df = conds.filter(pl.col("PLT_CN") == selected_plot_cn)
    console.print(f"[green]Found {len(cond_df)} conditions in selected plot[/green]")

    return tree_df, cond_df, selected_plot_cn


def run_fia_simulation(db_path: str, state_fips: int) -> None:
    """
    Run complete FIA to FVS simulation workflow with real database.

    This function demonstrates the full workflow from FIA data to
    growth simulation and yield table generation.

    Parameters
    ----------
    db_path : str
        Path to FIA DuckDB database
    state_fips : int
        State FIPS code
    """
    console.print(Panel.fit(
        "[bold blue]FIA to FVS Simulation Workflow[/bold blue]\n"
        "[dim]Using real FIA database[/dim]",
        border_style="blue"
    ))

    # Step 1: Load FIA data
    console.print("\n[bold]Step 1: Load FIA Data[/bold]")
    tree_df, cond_df, plot_cn = load_fia_plot_data(db_path, state_fips)

    # Display sample of tree data
    console.print("\n[cyan]Sample of tree data:[/cyan]")
    console.print(tree_df.head(5))

    # Display condition data
    console.print("\n[cyan]Condition data:[/cyan]")
    console.print(cond_df)

    # Step 2: Create PyFVS Stand
    console.print("\n[bold]Step 2: Create PyFVS Stand[/bold]")
    console.print("[dim]Converting FIA data to PyFVS Stand object...[/dim]")

    # Create stand from FIA data
    # The from_fia_data() method handles:
    #   - Species code conversion (FIA SPCD to FVS 2-letter codes)
    #   - Crown ratio conversion (percentage to proportion)
    #   - Site index derivation (from SICOND or default)
    #   - Forest type determination (from FORTYPCD or species composition)
    #   - Multi-condition plot handling (selects dominant condition by basal area)
    stand = Stand.from_fia_data(
        tree_df=tree_df,
        cond_df=cond_df,
        # Optional parameters:
        # site_index=70,        # Override site index if known
        # condid=1,             # Select specific condition
        # ecounit="M231",       # Set ecological unit for growth modifiers
        # forest_type="FTYLPN", # Override forest type
        weight_by_tpa=True,     # Replicate trees based on TPA_UNADJ
        min_dia=1.0,            # Minimum diameter threshold
        max_trees=1000,         # Maximum trees (subsample if exceeded)
        condition_strategy="dominant"  # Strategy for multi-condition plots
    )

    console.print(f"[green]Created stand with {len(stand.trees)} trees[/green]")
    console.print(f"[cyan]Site Index: {stand.site_index}[/cyan]")
    console.print(f"[cyan]Forest Type: {stand.forest_type}[/cyan]")
    console.print(f"[cyan]Dominant Species: {stand.species}[/cyan]")

    # Step 3: Display initial metrics
    console.print("\n[bold]Step 3: Initial Stand Metrics[/bold]")
    display_stand_metrics(stand, "Initial Stand (Year 0)")

    # Step 4: Simulate growth
    console.print("\n[bold]Step 4: Simulate Growth for 25 Years[/bold]")
    stand.grow(years=25)
    console.print("[green]Growth simulation complete![/green]")

    # Step 5: Display final metrics
    console.print("\n[bold]Step 5: Final Stand Metrics[/bold]")
    display_stand_metrics(stand, "Final Stand (Year 25)")

    # Step 6: Generate yield table
    console.print("\n[bold]Step 6: Generate Yield Table[/bold]")
    display_yield_table(stand, years=50, period_length=5)


# =============================================================================
# Section B: Working with Mock Data (No Database Required)
# =============================================================================

def create_mock_fia_data() -> tuple[pl.DataFrame, pl.DataFrame]:
    """
    Create mock FIA tree and condition data for demonstration.

    This function generates realistic FIA-style data that can be used
    to demonstrate the PyFVS workflow without requiring an actual
    FIA database.

    Returns
    -------
    tuple[pl.DataFrame, pl.DataFrame]
        - tree_df: Mock tree data with FIA columns
        - cond_df: Mock condition data with FIA columns

    Notes
    -----
    The mock data represents a mixed pine-hardwood stand typical of
    the southern United States with:
    - Loblolly pine (SPCD=131) as dominant species
    - Some shortleaf pine (SPCD=110)
    - A few hardwood species (sweetgum, red maple)
    - Realistic diameter and height distributions
    """
    console.print("[cyan]Creating mock FIA data...[/cyan]")

    # Mock plot identifiers
    mock_plot_cn = 12345678901234

    # Create realistic tree data
    # FIA SPCD codes:
    #   131 = Loblolly pine (LP)
    #   110 = Shortleaf pine (SP)
    #   611 = Sweetgum (SU)
    #   316 = Red maple (RM)
    tree_records = [
        # Loblolly pines (dominant)
        {"SPCD": 131, "DIA": 12.5, "HT": 75, "CR": 45, "TPA_UNADJ": 25.0, "STATUSCD": 1, "CONDID": 1},
        {"SPCD": 131, "DIA": 10.2, "HT": 68, "CR": 50, "TPA_UNADJ": 30.0, "STATUSCD": 1, "CONDID": 1},
        {"SPCD": 131, "DIA": 14.1, "HT": 82, "CR": 40, "TPA_UNADJ": 20.0, "STATUSCD": 1, "CONDID": 1},
        {"SPCD": 131, "DIA": 8.5, "HT": 55, "CR": 55, "TPA_UNADJ": 35.0, "STATUSCD": 1, "CONDID": 1},
        {"SPCD": 131, "DIA": 11.0, "HT": 70, "CR": 48, "TPA_UNADJ": 28.0, "STATUSCD": 1, "CONDID": 1},
        {"SPCD": 131, "DIA": 9.8, "HT": 62, "CR": 52, "TPA_UNADJ": 22.0, "STATUSCD": 1, "CONDID": 1},
        {"SPCD": 131, "DIA": 13.5, "HT": 78, "CR": 42, "TPA_UNADJ": 18.0, "STATUSCD": 1, "CONDID": 1},
        {"SPCD": 131, "DIA": 7.2, "HT": 48, "CR": 60, "TPA_UNADJ": 40.0, "STATUSCD": 1, "CONDID": 1},
        # Shortleaf pines
        {"SPCD": 110, "DIA": 9.5, "HT": 58, "CR": 50, "TPA_UNADJ": 15.0, "STATUSCD": 1, "CONDID": 1},
        {"SPCD": 110, "DIA": 11.2, "HT": 65, "CR": 45, "TPA_UNADJ": 12.0, "STATUSCD": 1, "CONDID": 1},
        {"SPCD": 110, "DIA": 8.0, "HT": 52, "CR": 55, "TPA_UNADJ": 18.0, "STATUSCD": 1, "CONDID": 1},
        # Sweetgum
        {"SPCD": 611, "DIA": 8.5, "HT": 50, "CR": 35, "TPA_UNADJ": 10.0, "STATUSCD": 1, "CONDID": 1},
        {"SPCD": 611, "DIA": 6.2, "HT": 42, "CR": 40, "TPA_UNADJ": 8.0, "STATUSCD": 1, "CONDID": 1},
        # Red maple
        {"SPCD": 316, "DIA": 5.5, "HT": 35, "CR": 45, "TPA_UNADJ": 12.0, "STATUSCD": 1, "CONDID": 1},
        {"SPCD": 316, "DIA": 7.0, "HT": 45, "CR": 42, "TPA_UNADJ": 8.0, "STATUSCD": 1, "CONDID": 1},
    ]

    # Add plot identifiers to each record
    for record in tree_records:
        record["PLT_CN"] = mock_plot_cn
        record["SUBP"] = 1
        record["TREE"] = tree_records.index(record) + 1

    tree_df = pl.DataFrame(tree_records)

    # Create condition data
    # SICOND: Site index (feet at base age 25)
    # FORTYPCD: Forest type code (161 = Loblolly pine)
    # STDAGE: Stand age (years)
    cond_records = [
        {
            "PLT_CN": mock_plot_cn,
            "CONDID": 1,
            "SICOND": 70.0,      # Site index 70 feet
            "SIBASE": 25,        # Base age 25 years
            "SISP": 131,         # Site species is loblolly pine
            "FORTYPCD": 161,     # Loblolly pine forest type
            "STDAGE": 25,        # Stand age 25 years
            "STDSZCD": 3,        # Size class (3 = sawtimber)
            "ECOSUBCD": "232Gc", # Ecological subsection
            "CONDPROP_UNADJ": 1.0,
            "COND_STATUS_CD": 1  # Forested condition
        }
    ]

    cond_df = pl.DataFrame(cond_records)

    console.print(f"[green]Created mock data: {len(tree_df)} trees, {len(cond_df)} conditions[/green]")

    return tree_df, cond_df


def run_mock_simulation() -> None:
    """
    Run FIA to FVS simulation workflow with mock data.

    This function demonstrates the complete workflow using mock data,
    allowing users to run the example without an FIA database.
    """
    console.print(Panel.fit(
        "[bold green]FIA to FVS Simulation Workflow[/bold green]\n"
        "[dim]Using mock data (no database required)[/dim]",
        border_style="green"
    ))

    # Step 1: Create mock FIA data
    console.print("\n[bold]Step 1: Create Mock FIA Data[/bold]")
    tree_df, cond_df = create_mock_fia_data()

    # Display the mock data
    console.print("\n[cyan]Mock tree data:[/cyan]")
    display_tree_table(tree_df)

    console.print("\n[cyan]Mock condition data:[/cyan]")
    console.print(cond_df)

    # Step 2: Create PyFVS Stand from FIA data
    console.print("\n[bold]Step 2: Create PyFVS Stand from FIA Data[/bold]")
    console.print("[dim]Using Stand.from_fia_data() to convert FIA data...[/dim]")

    # Create stand from FIA data
    # This demonstrates the key integration between PyFIA and PyFVS
    stand = Stand.from_fia_data(
        tree_df=tree_df,
        cond_df=cond_df,
        # Use ecounit for appropriate growth rates
        # M231 = Southern Appalachian Mountains (high productivity)
        # 232 = Atlantic Coastal Flatwoods (base, moderate productivity)
        ecounit="M231",
        weight_by_tpa=True,
        min_dia=1.0,
        max_trees=500
    )

    console.print(f"\n[green]Stand created successfully![/green]")
    console.print(f"  [cyan]Trees in stand: {len(stand.trees)}[/cyan]")
    console.print(f"  [cyan]Site Index: {stand.site_index} feet (base age 25)[/cyan]")
    console.print(f"  [cyan]Forest Type: {stand.forest_type}[/cyan]")
    console.print(f"  [cyan]Dominant Species: {stand.species}[/cyan]")
    console.print(f"  [cyan]Ecological Unit: {stand.ecounit}[/cyan]")
    console.print(f"  [cyan]Initial Stand Age: {stand.age} years[/cyan]")

    # Step 3: Display initial stand metrics
    console.print("\n[bold]Step 3: Initial Stand Metrics[/bold]")
    display_stand_metrics(stand, "Initial Stand Conditions")

    # Step 4: Simulate 25 years of growth
    console.print("\n[bold]Step 4: Simulate Growth for 25 Years[/bold]")
    console.print("[dim]Running FVS growth model (5-year cycles internally)...[/dim]")

    stand.grow(years=25)

    console.print(f"[green]Growth simulation complete![/green]")
    console.print(f"  [cyan]Final stand age: {stand.age} years[/cyan]")

    # Step 5: Display final stand metrics
    console.print("\n[bold]Step 5: Final Stand Metrics (After 25 Years)[/bold]")
    display_stand_metrics(stand, "Final Stand Conditions")

    # Step 6: Generate and display yield table
    console.print("\n[bold]Step 6: Generate Yield Table[/bold]")
    display_yield_table(stand, years=50, period_length=5)

    # Step 7: Additional analysis examples
    console.print("\n[bold]Step 7: Additional Analysis Options[/bold]")
    demonstrate_additional_features(stand)


# =============================================================================
# Display Utilities
# =============================================================================

def display_tree_table(tree_df: pl.DataFrame) -> None:
    """Display tree data in a formatted table."""
    table = Table(title="FIA Tree Data Sample", show_header=True)

    table.add_column("SPCD", style="cyan", justify="right")
    table.add_column("DIA (in)", style="green", justify="right")
    table.add_column("HT (ft)", style="green", justify="right")
    table.add_column("CR (%)", style="yellow", justify="right")
    table.add_column("TPA", style="magenta", justify="right")

    # Show first 10 rows
    for row in tree_df.head(10).iter_rows(named=True):
        table.add_row(
            str(row.get("SPCD", "")),
            f"{row.get('DIA', 0):.1f}",
            f"{row.get('HT', 0):.0f}",
            f"{row.get('CR', 0):.0f}",
            f"{row.get('TPA_UNADJ', 0):.1f}"
        )

    if len(tree_df) > 10:
        table.add_row("...", "...", "...", "...", "...")

    console.print(table)


def display_stand_metrics(stand: Stand, title: str) -> None:
    """Display stand metrics in a formatted table."""
    metrics = stand.get_metrics()

    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_column("Units", style="dim")

    # Core structural metrics
    table.add_row("Trees per Acre", f"{metrics['tpa']:.0f}", "TPA")
    table.add_row("Basal Area", f"{metrics['basal_area']:.1f}", "sq ft/acre")
    table.add_row("Quadratic Mean Diameter", f"{metrics['qmd']:.1f}", "inches")
    table.add_row("Mean DBH", f"{metrics['mean_dbh']:.1f}", "inches")
    table.add_row("Top Height", f"{metrics['top_height']:.1f}", "feet")
    table.add_row("Mean Height", f"{metrics['mean_height']:.1f}", "feet")

    # Density metrics
    table.add_row("Stand Density Index", f"{metrics['sdi']:.0f}", "SDI")
    table.add_row("Max SDI", f"{metrics['max_sdi']:.0f}", "SDI")
    table.add_row("Relative SDI", f"{metrics['relsdi']:.2f}", "proportion")
    table.add_row("Crown Competition Factor", f"{metrics['ccf']:.0f}", "CCF")

    # Volume metrics
    table.add_row("Total Cubic Volume", f"{metrics['volume']:.0f}", "cu ft/acre")
    table.add_row("Merchantable Volume", f"{metrics['merchantable_volume']:.0f}", "cu ft/acre")
    table.add_row("Board Feet", f"{metrics['board_feet']:.0f}", "BF/acre")

    table.add_row("Stand Age", f"{metrics['age']}", "years")

    console.print(table)


def display_yield_table(stand: Stand, years: int = 50, period_length: int = 5) -> None:
    """Generate and display a yield table."""
    console.print("[dim]Generating yield table...[/dim]")

    # Generate yield records
    yield_records = stand.generate_yield_table(
        years=years,
        period_length=period_length,
        stand_id="EXAMPLE_STAND",
        start_year=2025
    )

    # Create display table
    table = Table(
        title=f"Yield Table ({years} Years, {period_length}-Year Periods)",
        show_header=True,
        header_style="bold"
    )

    table.add_column("Year", style="cyan", justify="right")
    table.add_column("Age", style="cyan", justify="right")
    table.add_column("TPA", style="green", justify="right")
    table.add_column("BA", style="green", justify="right")
    table.add_column("QMD", style="green", justify="right")
    table.add_column("TopHt", style="green", justify="right")
    table.add_column("TCuFt", style="yellow", justify="right")
    table.add_column("MCuFt", style="yellow", justify="right")
    table.add_column("BdFt", style="yellow", justify="right")
    table.add_column("MAI", style="magenta", justify="right")

    for record in yield_records:
        table.add_row(
            str(record.Year),
            str(record.Age),
            f"{record.TPA:.0f}",
            f"{record.BA:.1f}",
            f"{record.QMD:.1f}",
            f"{record.TopHt:.1f}",
            f"{record.TCuFt:.0f}",
            f"{record.MCuFt:.0f}",
            f"{record.BdFt:.0f}",
            f"{record.MAI:.1f}"
        )

    console.print(table)

    # Summary statistics
    if yield_records:
        final = yield_records[-1]
        console.print(f"\n[bold]Projection Summary:[/bold]")
        console.print(f"  Final TPA: {final.TPA:.0f} trees/acre")
        console.print(f"  Final Basal Area: {final.BA:.1f} sq ft/acre")
        console.print(f"  Final Volume: {final.TCuFt:.0f} cu ft/acre")
        console.print(f"  Mean Annual Increment: {final.MAI:.1f} cu ft/acre/year")


def demonstrate_additional_features(stand: Stand) -> None:
    """Demonstrate additional PyFVS features."""

    console.print("[cyan]Additional PyFVS capabilities:[/cyan]\n")

    # 1. Export options
    console.print("1. [bold]Export Options[/bold]")
    console.print("   - stand.export_tree_list('trees.csv') - Export tree list")
    console.print("   - stand.export_yield_table('yield.csv') - Export yield table")
    console.print("   - stand.get_tree_list_dataframe() - Get as pandas DataFrame")
    console.print("   - stand.get_stand_stock_dataframe() - Get stock table")

    # 2. Harvest operations
    console.print("\n2. [bold]Harvest Operations[/bold]")
    console.print("   - stand.thin_from_below(target_ba=80) - Thin from below")
    console.print("   - stand.thin_from_above(target_tpa=150) - Thin from above")
    console.print("   - stand.selection_harvest(target_ba=60) - Selection harvest")
    console.print("   - stand.clearcut() - Remove all trees")

    # 3. Stand metrics
    console.print("\n3. [bold]Detailed Metrics[/bold]")
    console.print(f"   - CCF (Crown Competition Factor): {stand.calculate_ccf_official():.1f}")
    console.print(f"   - SDI (Stand Density Index): {stand.calculate_stand_sdi():.1f}")
    console.print(f"   - RelSDI (Relative Density): {stand.calculate_relsdi():.2f}")
    console.print(f"   - QMD (Quadratic Mean Diameter): {stand.calculate_qmd():.1f} inches")

    # 4. Species info
    console.print("\n4. [bold]Species Mapping[/bold]")
    from pyfvs.fia_integration import FIASpeciesMapper
    mapper = FIASpeciesMapper()
    console.print("   Common FIA species codes:")
    for spcd, fvs in [(131, "LP"), (110, "SP"), (121, "LL"), (111, "SA")]:
        common = mapper.get_common_name(spcd) or "Unknown"
        console.print(f"   - SPCD {spcd} -> FVS '{fvs}' ({common})")


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> None:
    """
    Main entry point for the FIA to FVS simulation example.

    Usage:
        # Run with mock data (no arguments):
        python fia_to_fvs_simulation.py

        # Run with real FIA database:
        python fia_to_fvs_simulation.py /path/to/database.duckdb 37
    """
    console.print(Panel.fit(
        "[bold]PyFIA to PyFVS Integration Example[/bold]\n"
        "[dim]Demonstrating the FIA Python Ecosystem workflow[/dim]",
        border_style="bold blue"
    ))

    if len(sys.argv) >= 3:
        # Use provided database path and state FIPS
        db_path = sys.argv[1]
        state_fips = int(sys.argv[2])

        console.print(f"\n[cyan]Using FIA database: {db_path}[/cyan]")
        console.print(f"[cyan]State FIPS: {state_fips}[/cyan]\n")

        try:
            run_fia_simulation(db_path, state_fips)
        except ImportError as e:
            console.print(f"\n[red]Error: {e}[/red]")
            console.print("[yellow]Falling back to mock data demonstration...[/yellow]\n")
            run_mock_simulation()
        except FileNotFoundError:
            console.print(f"\n[red]Error: Database not found at {db_path}[/red]")
            console.print("[yellow]Falling back to mock data demonstration...[/yellow]\n")
            run_mock_simulation()

    else:
        # Run with mock data
        console.print("\n[yellow]No database specified. Running with mock data.[/yellow]")
        console.print("[dim]To use a real FIA database, run:[/dim]")
        console.print("[dim]  python fia_to_fvs_simulation.py /path/to/database.duckdb <state_fips>[/dim]\n")

        run_mock_simulation()

    console.print("\n" + "=" * 70)
    console.print("[bold green]Example complete![/bold green]")
    console.print(
        "\n[dim]For more information, see:\n"
        "  - PyFVS documentation: https://github.com/your-org/pyfvs\n"
        "  - PyFIA documentation: https://github.com/your-org/pyfia\n"
        "  - FVS Southern Variant documentation: USFS FVS manual[/dim]"
    )


if __name__ == "__main__":
    main()

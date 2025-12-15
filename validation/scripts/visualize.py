"""
Visualization functions for FVS validation.

Creates comparison plots for validation reports.
"""
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

try:
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def check_matplotlib():
    """Verify matplotlib is available."""
    if not HAS_MATPLOTLIB:
        raise ImportError(
            "matplotlib is required for visualization. "
            "Install with: pip install matplotlib"
        )


def plot_stand_comparison(
    fvs_data: Dict[str, List[float]],
    fvspy_data: Dict[str, List[float]],
    ages: List[int],
    scenario_name: str,
    output_path: Optional[Path] = None
) -> "plt.Figure":
    """
    Create 2x2 panel comparing key stand metrics over time.

    Args:
        fvs_data: FVS reference data with columns TPA, BA, QMD, TopHt
        fvspy_data: FVS-Python predictions with same columns
        ages: Stand ages for x-axis
        scenario_name: Scenario identifier for title
        output_path: Optional path to save figure

    Returns:
        matplotlib Figure object
    """
    check_matplotlib()

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    metrics = [
        ("TPA", "Trees per Acre"),
        ("BA", "Basal Area (sq ft/acre)"),
        ("QMD", "Quadratic Mean Diameter (in)"),
        ("TopHt", "Dominant Height (ft)"),
    ]

    for ax, (col, label) in zip(axes.flat, metrics):
        if col in fvs_data and col in fvspy_data:
            ax.plot(ages, fvs_data[col], 'b-', label="FVS-SN", linewidth=2)
            ax.plot(ages, fvspy_data[col], 'r--', label="FVS-Python", linewidth=2)
            ax.set_xlabel("Stand Age (years)")
            ax.set_ylabel(label)
            ax.legend()
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, f"Data not available for {col}",
                   ha='center', va='center', transform=ax.transAxes)

    fig.suptitle(f"Stand Development Comparison: {scenario_name}", fontsize=14)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')

    return fig


def plot_residuals(
    fvs_data: Dict[str, List[float]],
    fvspy_data: Dict[str, List[float]],
    ages: List[int],
    output_path: Optional[Path] = None
) -> "plt.Figure":
    """
    Plot residuals (FVS-Python - FVS) vs age and predicted values.

    Args:
        fvs_data: FVS reference data
        fvspy_data: FVS-Python predictions
        ages: Stand ages
        output_path: Optional path to save figure

    Returns:
        matplotlib Figure object
    """
    check_matplotlib()

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    metrics = ["TPA", "BA", "QMD", "TopHt"]

    for ax, metric in zip(axes.flat, metrics):
        if metric in fvs_data and metric in fvspy_data:
            fvs = np.array(fvs_data[metric])
            fvspy = np.array(fvspy_data[metric])
            residuals = fvspy - fvs

            ax.scatter(ages, residuals, alpha=0.7, edgecolors='k', linewidth=0.5)
            ax.axhline(y=0, color='r', linestyle='--', linewidth=1)
            ax.set_xlabel("Stand Age (years)")
            ax.set_ylabel(f"{metric} Residual")
            ax.set_title(f"{metric} Residuals (FVS-Python - FVS)")
            ax.grid(True, alpha=0.3)

            # Add mean and std annotation
            mean_res = np.mean(residuals)
            std_res = np.std(residuals)
            ax.annotate(
                f"Mean: {mean_res:.2f}\nStd: {std_res:.2f}",
                xy=(0.02, 0.98), xycoords='axes fraction',
                fontsize=9, ha='left', va='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
            )

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')

    return fig


def plot_bakuzis_matrix(
    yield_data: Dict[str, List[float]],
    ages: List[int],
    scenario_name: str,
    output_path: Optional[Path] = None
) -> "plt.Figure":
    """
    Visualize Bakuzis Matrix relationships in stand data.

    Shows relationships between:
    - TPA vs Age
    - QMD vs Age
    - BA vs Age
    - Height vs Age
    - TPA vs QMD
    - BA vs TPA

    Args:
        yield_data: Yield table data
        ages: Stand ages
        scenario_name: Scenario identifier
        output_path: Optional path to save figure

    Returns:
        matplotlib Figure object
    """
    check_matplotlib()

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    ages_arr = np.array(ages)

    # 1. TPA vs Age
    ax = axes[0, 0]
    if "TPA" in yield_data:
        ax.plot(ages_arr, yield_data["TPA"], 'b-', linewidth=2, marker='o')
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Trees per Acre")
    ax.set_title("TPA vs Age (should decrease)")
    ax.grid(True, alpha=0.3)

    # 2. QMD vs Age
    ax = axes[0, 1]
    if "QMD" in yield_data:
        ax.plot(ages_arr, yield_data["QMD"], 'g-', linewidth=2, marker='o')
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("QMD (inches)")
    ax.set_title("QMD vs Age (should increase)")
    ax.grid(True, alpha=0.3)

    # 3. BA vs Age
    ax = axes[0, 2]
    if "BA" in yield_data:
        ax.plot(ages_arr, yield_data["BA"], 'r-', linewidth=2, marker='o')
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Basal Area (sq ft/acre)")
    ax.set_title("BA vs Age (increase then plateau)")
    ax.grid(True, alpha=0.3)

    # 4. Height vs Age
    ax = axes[1, 0]
    if "TopHt" in yield_data:
        ax.plot(ages_arr, yield_data["TopHt"], 'm-', linewidth=2, marker='o')
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Dominant Height (ft)")
    ax.set_title("Height vs Age (S-curve)")
    ax.grid(True, alpha=0.3)

    # 5. TPA vs QMD
    ax = axes[1, 1]
    if "TPA" in yield_data and "QMD" in yield_data:
        ax.scatter(yield_data["QMD"], yield_data["TPA"], c=ages_arr, cmap='viridis',
                  s=50, edgecolors='k', linewidth=0.5)
        ax.set_xlabel("QMD (inches)")
        ax.set_ylabel("Trees per Acre")
        ax.set_title("TPA vs QMD (negative correlation)")
    ax.grid(True, alpha=0.3)

    # 6. Volume vs Age
    ax = axes[1, 2]
    if "TCuFt" in yield_data:
        ax.plot(ages_arr, yield_data["TCuFt"], 'c-', linewidth=2, marker='o')
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Total Cubic Volume (cu ft/acre)")
    ax.set_title("Volume vs Age")
    ax.grid(True, alpha=0.3)

    fig.suptitle(f"Bakuzis Matrix Verification: {scenario_name}", fontsize=14)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')

    return fig


def plot_component_validation(
    test_results: List[Dict[str, Any]],
    component_name: str,
    output_path: Optional[Path] = None
) -> "plt.Figure":
    """
    Plot component model validation results.

    Args:
        test_results: List of test result dictionaries with 'expected', 'actual', 'species'
        component_name: Name of component (e.g., "Height-Diameter")
        output_path: Optional path to save figure

    Returns:
        matplotlib Figure object
    """
    check_matplotlib()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Extract data
    expected = np.array([r['expected'] for r in test_results if 'expected' in r])
    actual = np.array([r['actual'] for r in test_results if 'actual' in r])
    species = [r.get('species', 'Unknown') for r in test_results]

    if len(expected) == 0 or len(actual) == 0:
        axes[0].text(0.5, 0.5, "No data available", ha='center', va='center')
        axes[1].text(0.5, 0.5, "No data available", ha='center', va='center')
        return fig

    # 1:1 plot
    ax = axes[0]
    species_colors = {'LP': 'blue', 'SP': 'green', 'SA': 'red', 'LL': 'orange'}
    for sp in set(species):
        mask = np.array([s == sp for s in species])
        color = species_colors.get(sp, 'gray')
        ax.scatter(expected[mask], actual[mask], c=color, label=sp, alpha=0.7,
                  edgecolors='k', linewidth=0.5)

    # Add 1:1 line
    min_val = min(expected.min(), actual.min())
    max_val = max(expected.max(), actual.max())
    ax.plot([min_val, max_val], [min_val, max_val], 'k--', linewidth=1, label='1:1')

    ax.set_xlabel("Reference Value")
    ax.set_ylabel("FVS-Python Value")
    ax.set_title(f"{component_name}: Predicted vs Reference")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Residual histogram
    ax = axes[1]
    residuals = actual - expected
    ax.hist(residuals, bins=20, edgecolor='black', alpha=0.7)
    ax.axvline(x=0, color='r', linestyle='--', linewidth=2)
    ax.axvline(x=np.mean(residuals), color='b', linestyle='-', linewidth=2,
              label=f'Mean: {np.mean(residuals):.3f}')
    ax.set_xlabel("Residual (Predicted - Reference)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"{component_name}: Residual Distribution")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')

    return fig


def plot_validation_summary(
    summary: Dict[str, Any],
    output_path: Optional[Path] = None
) -> "plt.Figure":
    """
    Create summary visualization of overall validation results.

    Args:
        summary: Validation summary dictionary from compare_results.generate_comparison_summary
        output_path: Optional path to save figure

    Returns:
        matplotlib Figure object
    """
    check_matplotlib()

    fig = plt.figure(figsize=(14, 8))
    gs = gridspec.GridSpec(2, 2, figure=fig)

    # 1. Pass/Fail pie chart
    ax1 = fig.add_subplot(gs[0, 0])
    passed = summary.get("passed_scenarios", 0)
    failed = summary.get("failed_scenarios", 0)
    colors = ['#2ecc71', '#e74c3c']
    ax1.pie([passed, failed], labels=['Passed', 'Failed'], colors=colors,
            autopct='%1.1f%%', startangle=90)
    ax1.set_title(f"Scenario Pass Rate ({passed}/{passed+failed})")

    # 2. MAPE by metric bar chart
    ax2 = fig.add_subplot(gs[0, 1])
    metric_summaries = summary.get("metric_summaries", {})
    if metric_summaries:
        metrics = list(metric_summaries.keys())
        mapes = [metric_summaries[m]["mean_mape"] for m in metrics]

        colors = ['green' if m < 5 else 'orange' if m < 10 else 'red' for m in mapes]
        bars = ax2.bar(metrics, mapes, color=colors, edgecolor='black')
        ax2.axhline(y=5, color='r', linestyle='--', linewidth=1, label='5% threshold')
        ax2.set_xlabel("Metric")
        ax2.set_ylabel("Mean MAPE (%)")
        ax2.set_title("Mean Absolute Percentage Error by Metric")
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')

    # 3. Bias by metric
    ax3 = fig.add_subplot(gs[1, 0])
    if metric_summaries:
        biases = [metric_summaries[m]["mean_bias"] for m in metrics]
        colors = ['green' if abs(b) < 1 else 'orange' if abs(b) < 5 else 'red' for b in biases]
        ax3.bar(metrics, biases, color=colors, edgecolor='black')
        ax3.axhline(y=0, color='k', linestyle='-', linewidth=1)
        ax3.set_xlabel("Metric")
        ax3.set_ylabel("Mean Bias")
        ax3.set_title("Mean Bias by Metric")
        ax3.grid(True, alpha=0.3, axis='y')

    # 4. Scenario details table
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')

    scenario_details = summary.get("scenario_details", [])
    if scenario_details:
        table_data = []
        for detail in scenario_details[:8]:  # Limit to 8 rows
            status = "PASS" if detail["passed"] else "FAIL"
            mapes = [f"{detail['metrics'].get(m, {}).get('mape', 0):.1f}"
                    for m in ["TPA", "BA", "QMD"]]
            table_data.append([detail["scenario_id"], status] + mapes)

        table = ax4.table(
            cellText=table_data,
            colLabels=["Scenario", "Status", "TPA%", "BA%", "QMD%"],
            loc='center',
            cellLoc='center'
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.5)
        ax4.set_title("Scenario Results", pad=20)

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')

    return fig


def create_validation_report_figures(
    results_dir: Path,
    output_dir: Path
) -> List[Path]:
    """
    Create all figures for validation report.

    Args:
        results_dir: Directory containing validation results
        output_dir: Directory to save figures

    Returns:
        List of paths to generated figures
    """
    check_matplotlib()

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_figures = []

    # This would be expanded to process actual results files
    # For now, return empty list

    return generated_figures


if __name__ == "__main__":
    # Example usage
    check_matplotlib()

    # Generate sample data for testing
    ages = list(range(0, 55, 5))

    # Sample FVS data (would come from actual FVS runs)
    fvs_data = {
        "TPA": [500, 480, 450, 400, 350, 300, 260, 230, 200, 180, 160],
        "BA": [0, 15, 40, 70, 95, 115, 130, 140, 148, 152, 155],
        "QMD": [0.5, 2.0, 3.5, 5.0, 6.5, 8.0, 9.5, 11.0, 12.5, 14.0, 15.5],
        "TopHt": [1, 15, 30, 42, 52, 60, 67, 73, 78, 82, 85],
    }

    # Sample FVS-Python data (with slight differences)
    fvspy_data = {
        "TPA": [500, 478, 445, 398, 348, 298, 258, 228, 198, 178, 158],
        "BA": [0, 14, 39, 68, 93, 113, 128, 138, 146, 150, 153],
        "QMD": [0.5, 2.0, 3.5, 5.0, 6.5, 8.0, 9.5, 11.0, 12.5, 14.0, 15.5],
        "TopHt": [1, 14, 29, 41, 51, 59, 66, 72, 77, 81, 84],
    }

    # Create comparison plot
    fig1 = plot_stand_comparison(fvs_data, fvspy_data, ages, "LP_SI70_T500")

    # Create residual plot
    fig2 = plot_residuals(fvs_data, fvspy_data, ages)

    # Create Bakuzis matrix plot
    fig3 = plot_bakuzis_matrix(fvspy_data, ages, "LP_SI70_T500")

    plt.show()

"""
Visualization functions for growth trajectories and stand metrics.
Provides comprehensive plotting capabilities for FVS-Python results.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd
import seaborn as sns
from typing import List, Dict, Optional, Union, Tuple
from pathlib import Path

# Set default style
try:
    plt.style.use('seaborn-v0_8')
except OSError:
    try:
        plt.style.use('seaborn')
    except OSError:
        plt.style.use('default')
        
sns.set_palette("husl")

def plot_stand_trajectories(metrics_over_time, save_path=None):
    """Plot key stand metrics over time.
    
    Args:
        metrics_over_time: List of dictionaries containing stand metrics at each age
        save_path: Optional path to save the plot
    """
    # Extract time series
    ages = [m['age'] for m in metrics_over_time]
    tpa = [m['tpa'] for m in metrics_over_time]
    volume = [m['volume'] for m in metrics_over_time]
    mean_height = [m['mean_height'] for m in metrics_over_time]
    mean_dbh = [m['mean_dbh'] for m in metrics_over_time]
    basal_area = [m['basal_area'] for m in metrics_over_time]
    
    # Create subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Stand Development Trajectories', fontsize=14)
    
    # Trees per acre
    ax1.plot(ages, tpa, 'b-', label='Trees per Acre')
    ax1.set_xlabel('Stand Age (years)')
    ax1.set_ylabel('Trees per Acre')
    ax1.grid(True)
    
    # Volume
    ax2.plot(ages, volume, 'g-', label='Volume')
    ax2.set_xlabel('Stand Age (years)')
    ax2.set_ylabel('Volume (cubic feet/acre)')
    ax2.grid(True)
    
    # Mean tree size
    ax3.plot(ages, mean_height, 'r-', label='Height')
    ax3.plot(ages, mean_dbh, 'b--', label='DBH')
    ax3.set_xlabel('Stand Age (years)')
    ax3.set_ylabel('Tree Size (feet/inches)')
    ax3.legend()
    ax3.grid(True)
    
    # Basal area
    ax4.plot(ages, basal_area, 'k-', label='Basal Area')
    ax4.set_xlabel('Stand Age (years)')
    ax4.set_ylabel('Basal Area (sq ft/acre)')
    ax4.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()


def plot_yield_table_comparison(yield_table: pd.DataFrame, 
                               metric: str = 'volume',
                               save_path: Optional[Path] = None) -> None:
    """Plot yield table comparison across site indices and densities.
    
    Args:
        yield_table: DataFrame with yield table results
        metric: Metric to plot ('volume', 'mean_dbh', 'mean_height', 'basal_area')
        save_path: Optional path to save the plot
    """
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle(f'Yield Table Comparison - {metric.title()}', fontsize=16)
    
    # Plot by site index
    site_indices = sorted(yield_table['site_index'].unique())
    colors = plt.cm.viridis(np.linspace(0, 1, len(site_indices)))
    
    for i, si in enumerate(site_indices):
        si_data = yield_table[yield_table['site_index'] == si]
        axes[0].plot(si_data['age'], si_data[metric], 
                    color=colors[i], linewidth=2, label=f'SI {si}')
    
    axes[0].set_xlabel('Age (years)')
    axes[0].set_ylabel(metric.replace('_', ' ').title())
    axes[0].set_title('By Site Index')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Plot by density
    densities = sorted(yield_table['initial_tpa'].unique())
    colors = plt.cm.plasma(np.linspace(0, 1, len(densities)))
    
    for i, density in enumerate(densities):
        density_data = yield_table[yield_table['initial_tpa'] == density]
        axes[1].plot(density_data['age'], density_data[metric],
                    color=colors[i], linewidth=2, label=f'{density} TPA')
    
    axes[1].set_xlabel('Age (years)')
    axes[1].set_ylabel(metric.replace('_', ' ').title())
    axes[1].set_title('By Initial Density')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()


def plot_scenario_comparison(comparison_df: pd.DataFrame,
                           metrics: List[str] = ['volume', 'mean_dbh', 'basal_area'],
                           save_path: Optional[Path] = None) -> None:
    """Plot comparison of multiple management scenarios.
    
    Args:
        comparison_df: DataFrame with scenario comparison results
        metrics: List of metrics to plot
        save_path: Optional path to save the plot
    """
    n_metrics = len(metrics)
    fig, axes = plt.subplots(1, n_metrics, figsize=(5 * n_metrics, 6))
    if n_metrics == 1:
        axes = [axes]
    
    fig.suptitle('Management Scenario Comparison', fontsize=16)
    
    scenarios = comparison_df['scenario'].unique()
    colors = sns.color_palette('Set1', len(scenarios))
    
    for i, metric in enumerate(metrics):
        for j, scenario in enumerate(scenarios):
            scenario_data = comparison_df[comparison_df['scenario'] == scenario]
            axes[i].plot(scenario_data['age'], scenario_data[metric],
                        color=colors[j], linewidth=2.5, label=scenario)
        
        axes[i].set_xlabel('Age (years)')
        axes[i].set_ylabel(metric.replace('_', ' ').title())
        axes[i].set_title(f'{metric.replace("_", " ").title()} Comparison')
        axes[i].legend()
        axes[i].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()


def save_all_plots(metrics_over_time: List[Dict],
                   stand_obj=None,
                   output_dir: Path = Path('./plots'),
                   prefix: str = 'fvs') -> None:
    """Save all available plots to files.
    
    Args:
        metrics_over_time: List of dictionaries containing stand metrics
        stand_obj: Optional Stand object for additional plots
        output_dir: Directory to save plots
        prefix: Prefix for plot filenames
    """
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Main trajectory plot
    plot_stand_trajectories(metrics_over_time, 
                           save_path=output_dir / f'{prefix}_trajectories.png')
    
    # Mortality patterns
    plot_mortality_patterns(metrics_over_time,
                          save_path=output_dir / f'{prefix}_mortality.png')
    
    # Stand-specific plots if available
    if stand_obj:
        plot_size_distributions(stand_obj,
                              save_path=output_dir / f'{prefix}_size_distributions.png')
        
        plot_competition_effects(stand_obj,
                                save_path=output_dir / f'{prefix}_competition.png')
    
    print(f"All plots saved to {output_dir}")

def plot_size_distributions(stand, save_path=None):
    """Plot current DBH and height distributions.
    
    Args:
        stand: Stand object
        save_path: Optional path to save the plot
    """
    if not stand.trees:
        return
    
    # Get tree data
    dbhs = [tree.dbh for tree in stand.trees]
    heights = [tree.height for tree in stand.trees]
    
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f'Stand Size Distributions at Age {stand.age}', fontsize=14)
    
    # DBH distribution
    ax1.hist(dbhs, bins=20, edgecolor='black')
    ax1.set_xlabel('DBH (inches)')
    ax1.set_ylabel('Number of Trees')
    ax1.set_title('DBH Distribution')
    ax1.grid(True)
    
    # Height distribution
    ax2.hist(heights, bins=20, edgecolor='black')
    ax2.set_xlabel('Height (feet)')
    ax2.set_ylabel('Number of Trees')
    ax2.set_title('Height Distribution')
    ax2.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()


def plot_yield_table_comparison(yield_table: pd.DataFrame, 
                               metric: str = 'volume',
                               save_path: Optional[Path] = None) -> None:
    """Plot yield table comparison across site indices and densities.
    
    Args:
        yield_table: DataFrame with yield table results
        metric: Metric to plot ('volume', 'mean_dbh', 'mean_height', 'basal_area')
        save_path: Optional path to save the plot
    """
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle(f'Yield Table Comparison - {metric.title()}', fontsize=16)
    
    # Plot by site index
    site_indices = sorted(yield_table['site_index'].unique())
    colors = plt.cm.viridis(np.linspace(0, 1, len(site_indices)))
    
    for i, si in enumerate(site_indices):
        si_data = yield_table[yield_table['site_index'] == si]
        axes[0].plot(si_data['age'], si_data[metric], 
                    color=colors[i], linewidth=2, label=f'SI {si}')
    
    axes[0].set_xlabel('Age (years)')
    axes[0].set_ylabel(metric.replace('_', ' ').title())
    axes[0].set_title('By Site Index')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Plot by density
    densities = sorted(yield_table['initial_tpa'].unique())
    colors = plt.cm.plasma(np.linspace(0, 1, len(densities)))
    
    for i, density in enumerate(densities):
        density_data = yield_table[yield_table['initial_tpa'] == density]
        axes[1].plot(density_data['age'], density_data[metric],
                    color=colors[i], linewidth=2, label=f'{density} TPA')
    
    axes[1].set_xlabel('Age (years)')
    axes[1].set_ylabel(metric.replace('_', ' ').title())
    axes[1].set_title('By Initial Density')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()


def plot_scenario_comparison(comparison_df: pd.DataFrame,
                           metrics: List[str] = ['volume', 'mean_dbh', 'basal_area'],
                           save_path: Optional[Path] = None) -> None:
    """Plot comparison of multiple management scenarios.
    
    Args:
        comparison_df: DataFrame with scenario comparison results
        metrics: List of metrics to plot
        save_path: Optional path to save the plot
    """
    n_metrics = len(metrics)
    fig, axes = plt.subplots(1, n_metrics, figsize=(5 * n_metrics, 6))
    if n_metrics == 1:
        axes = [axes]
    
    fig.suptitle('Management Scenario Comparison', fontsize=16)
    
    scenarios = comparison_df['scenario'].unique()
    colors = sns.color_palette('Set1', len(scenarios))
    
    for i, metric in enumerate(metrics):
        for j, scenario in enumerate(scenarios):
            scenario_data = comparison_df[comparison_df['scenario'] == scenario]
            axes[i].plot(scenario_data['age'], scenario_data[metric],
                        color=colors[j], linewidth=2.5, label=scenario)
        
        axes[i].set_xlabel('Age (years)')
        axes[i].set_ylabel(metric.replace('_', ' ').title())
        axes[i].set_title(f'{metric.replace("_", " ").title()} Comparison')
        axes[i].legend()
        axes[i].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()


def save_all_plots(metrics_over_time: List[Dict],
                   stand_obj=None,
                   output_dir: Path = Path('./plots'),
                   prefix: str = 'fvs') -> None:
    """Save all available plots to files.
    
    Args:
        metrics_over_time: List of dictionaries containing stand metrics
        stand_obj: Optional Stand object for additional plots
        output_dir: Directory to save plots
        prefix: Prefix for plot filenames
    """
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Main trajectory plot
    plot_stand_trajectories(metrics_over_time, 
                           save_path=output_dir / f'{prefix}_trajectories.png')
    
    # Mortality patterns
    plot_mortality_patterns(metrics_over_time,
                          save_path=output_dir / f'{prefix}_mortality.png')
    
    # Stand-specific plots if available
    if stand_obj:
        plot_size_distributions(stand_obj,
                              save_path=output_dir / f'{prefix}_size_distributions.png')
        
        plot_competition_effects(stand_obj,
                                save_path=output_dir / f'{prefix}_competition.png')
    
    print(f"All plots saved to {output_dir}")

def plot_mortality_patterns(metrics_over_time, save_path=None):
    """Plot mortality patterns over time.
    
    Args:
        metrics_over_time: List of dictionaries containing stand metrics at each age
        save_path: Optional path to save the plot
    """
    # Extract time series
    ages = [m['age'] for m in metrics_over_time]
    tpa = [m['tpa'] for m in metrics_over_time]
    
    # Calculate mortality rate
    mortality_rates = []
    for i in range(1, len(tpa)):
        rate = (tpa[i-1] - tpa[i]) / tpa[i-1] if tpa[i-1] > 0 else 0
        mortality_rates.append(rate)
    
    # Create plot
    plt.figure(figsize=(10, 6))
    plt.plot(ages[1:], mortality_rates, 'r-', label='Annual Mortality Rate')
    plt.xlabel('Stand Age (years)')
    plt.ylabel('Annual Mortality Rate')
    plt.title('Stand Mortality Patterns')
    plt.grid(True)
    plt.legend()
    
    if save_path:
        plt.savefig(save_path)
    else:
        plt.show()
    
    plt.close()

def plot_competition_effects(stand, save_path=None):
    """Plot relationship between tree size and competition.
    
    Args:
        stand: Stand object
        save_path: Optional path to save the plot
    """
    if not stand.trees:
        return
    
    # Get competition factors
    competition_metrics = stand._calculate_competition_metrics()
    competition_factors = [m['competition_factor'] for m in competition_metrics]
    
    # Get tree data
    dbhs = [tree.dbh for tree in stand.trees]
    heights = [tree.height for tree in stand.trees]
    
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f'Competition Effects at Age {stand.age}', fontsize=14)
    
    # DBH vs Competition
    ax1.scatter(dbhs, competition_factors, alpha=0.5)
    ax1.set_xlabel('DBH (inches)')
    ax1.set_ylabel('Competition Factor')
    ax1.set_title('DBH vs Competition')
    ax1.grid(True)
    
    # Height vs Competition
    ax2.scatter(heights, competition_factors, alpha=0.5)
    ax2.set_xlabel('Height (feet)')
    ax2.set_ylabel('Competition Factor')
    ax2.set_title('Height vs Competition')
    ax2.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()


def plot_yield_table_comparison(yield_table: pd.DataFrame, 
                               metric: str = 'volume',
                               save_path: Optional[Path] = None) -> None:
    """Plot yield table comparison across site indices and densities.
    
    Args:
        yield_table: DataFrame with yield table results
        metric: Metric to plot ('volume', 'mean_dbh', 'mean_height', 'basal_area')
        save_path: Optional path to save the plot
    """
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle(f'Yield Table Comparison - {metric.title()}', fontsize=16)
    
    # Plot by site index
    site_indices = sorted(yield_table['site_index'].unique())
    colors = plt.cm.viridis(np.linspace(0, 1, len(site_indices)))
    
    for i, si in enumerate(site_indices):
        si_data = yield_table[yield_table['site_index'] == si]
        axes[0].plot(si_data['age'], si_data[metric], 
                    color=colors[i], linewidth=2, label=f'SI {si}')
    
    axes[0].set_xlabel('Age (years)')
    axes[0].set_ylabel(metric.replace('_', ' ').title())
    axes[0].set_title('By Site Index')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Plot by density
    densities = sorted(yield_table['initial_tpa'].unique())
    colors = plt.cm.plasma(np.linspace(0, 1, len(densities)))
    
    for i, density in enumerate(densities):
        density_data = yield_table[yield_table['initial_tpa'] == density]
        axes[1].plot(density_data['age'], density_data[metric],
                    color=colors[i], linewidth=2, label=f'{density} TPA')
    
    axes[1].set_xlabel('Age (years)')
    axes[1].set_ylabel(metric.replace('_', ' ').title())
    axes[1].set_title('By Initial Density')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()


def plot_scenario_comparison(comparison_df: pd.DataFrame,
                           metrics: List[str] = ['volume', 'mean_dbh', 'basal_area'],
                           save_path: Optional[Path] = None) -> None:
    """Plot comparison of multiple management scenarios.
    
    Args:
        comparison_df: DataFrame with scenario comparison results
        metrics: List of metrics to plot
        save_path: Optional path to save the plot
    """
    n_metrics = len(metrics)
    fig, axes = plt.subplots(1, n_metrics, figsize=(5 * n_metrics, 6))
    if n_metrics == 1:
        axes = [axes]
    
    fig.suptitle('Management Scenario Comparison', fontsize=16)
    
    scenarios = comparison_df['scenario'].unique()
    colors = sns.color_palette('Set1', len(scenarios))
    
    for i, metric in enumerate(metrics):
        for j, scenario in enumerate(scenarios):
            scenario_data = comparison_df[comparison_df['scenario'] == scenario]
            axes[i].plot(scenario_data['age'], scenario_data[metric],
                        color=colors[j], linewidth=2.5, label=scenario)
        
        axes[i].set_xlabel('Age (years)')
        axes[i].set_ylabel(metric.replace('_', ' ').title())
        axes[i].set_title(f'{metric.replace("_", " ").title()} Comparison')
        axes[i].legend()
        axes[i].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()


def save_all_plots(metrics_over_time: List[Dict],
                   stand_obj=None,
                   output_dir: Path = Path('./plots'),
                   prefix: str = 'fvs') -> None:
    """Save all available plots to files.
    
    Args:
        metrics_over_time: List of dictionaries containing stand metrics
        stand_obj: Optional Stand object for additional plots
        output_dir: Directory to save plots
        prefix: Prefix for plot filenames
    """
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Main trajectory plot
    plot_stand_trajectories(metrics_over_time, 
                           save_path=output_dir / f'{prefix}_trajectories.png')
    
    # Mortality patterns
    plot_mortality_patterns(metrics_over_time,
                          save_path=output_dir / f'{prefix}_mortality.png')
    
    # Stand-specific plots if available
    if stand_obj:
        plot_size_distributions(stand_obj,
                              save_path=output_dir / f'{prefix}_size_distributions.png')
        
        plot_competition_effects(stand_obj,
                                save_path=output_dir / f'{prefix}_competition.png')
    
    print(f"All plots saved to {output_dir}") 
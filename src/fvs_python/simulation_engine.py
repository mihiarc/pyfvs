"""
Unified simulation engine for FVS-Python.
Consolidates all simulation functionality with a clean, parameterized interface.
"""
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
import csv

from .stand import Stand
from .tree import Tree
from .validation import ParameterValidator
from .logging_config import (
    get_logger, setup_logging, log_simulation_start, 
    log_simulation_progress, SimulationLogContext
)
from .growth_plots import (
    plot_stand_trajectories,
    plot_size_distributions,
    plot_mortality_patterns,
    plot_competition_effects,
    save_all_plots
)
from .data_export import DataExporter


class SimulationEngine:
    """Unified engine for running forest growth simulations."""
    
    def __init__(self, output_dir: Optional[Union[str, Path]] = None):
        """Initialize the simulation engine.
        
        Args:
            output_dir: Directory for saving outputs. If None, uses default.
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent / 'test_output'
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Setup logging with structured format
        log_file = self.output_dir / f'simulation_{datetime.now():%Y%m%d_%H%M%S}.log'
        setup_logging(log_level='INFO', log_file=log_file, structured=True)
        self.logger = get_logger(__name__)
        
        # Initialize data exporter
        self.exporter = DataExporter(self.output_dir)
    
    
    def simulate_stand(self, 
                      species: str = 'LP',
                      trees_per_acre: int = 500,
                      site_index: float = 70,
                      years: int = 50,
                      time_step: int = 5,
                      save_outputs: bool = True,
                      plot_results: bool = True) -> pd.DataFrame:
        """Run a single stand simulation.
        
        Args:
            species: Species code (e.g., 'LP', 'SP', 'SA', 'LL')
            trees_per_acre: Initial planting density
            site_index: Site index (base age 25) in feet
            years: Total simulation length in years
            time_step: Years between growth periods
            save_outputs: Whether to save results to files
            plot_results: Whether to generate plots
            
        Returns:
            DataFrame with simulation results
        """
        # Log simulation start with context
        log_simulation_start(self.logger, species, years, trees_per_acre, site_index)
        
        # Initialize stand
        stand = Stand.initialize_planted(
            trees_per_acre=trees_per_acre,
            site_index=site_index,
            species=species
        )
        
        # Run simulation and collect metrics
        metrics = self._run_growth_simulation(stand, years, time_step)
        
        # Convert to DataFrame
        df = pd.DataFrame(metrics)
        
        # Save outputs if requested
        if save_outputs:
            export_formats = ['csv', 'json']  # Default formats
            exported_files = self._save_results(df, species, trees_per_acre, site_index, export_formats)
            
            # Create summary report
            summary_data = {
                'parameters': {
                    'species': species,
                    'trees_per_acre': trees_per_acre,
                    'site_index': site_index,
                    'years': years,
                    'time_step': time_step
                },
                'final_metrics': df.iloc[-1].to_dict(),
                'growth_summary': {
                    'total_dbh_growth': df.iloc[-1]['mean_dbh'] - df.iloc[0]['mean_dbh'],
                    'total_height_growth': df.iloc[-1]['mean_height'] - df.iloc[0]['mean_height'],
                    'total_volume_growth': df.iloc[-1]['volume'] - df.iloc[0]['volume'],
                    'survival_rate': df.iloc[-1]['tpa'] / df.iloc[0]['tpa']
                },
                'output_files': exported_files
            }
            
            self.exporter.create_summary_report(summary_data, 
                                               f"summary_{species}_TPA{trees_per_acre}_SI{int(site_index)}")
        
        # Generate plots if requested
        if plot_results:
            self._generate_plots(metrics, species, trees_per_acre, site_index)
        
        self.logger.info("Simulation completed successfully")
        return df
    
    def simulate_yield_table(self,
                           species: Union[str, List[str]] = 'LP',
                           site_indices: List[float] = [60, 70, 80],
                           planting_densities: List[int] = [300, 500, 700],
                           years: int = 50,
                           time_step: int = 5,
                           save_outputs: bool = True) -> pd.DataFrame:
        """Generate yield tables for multiple scenarios.
        
        Args:
            species: Species code(s) to simulate
            site_indices: List of site indices to test
            planting_densities: List of initial TPAs to test
            years: Simulation length
            time_step: Growth period length
            save_outputs: Whether to save results
            
        Returns:
            DataFrame with yield table results
        """
        if isinstance(species, str):
            species = [species]
        
        all_results = []
        total_sims = len(species) * len(site_indices) * len(planting_densities)
        sim_count = 0
        
        for sp in species:
            for si in site_indices:
                for tpa in planting_densities:
                    sim_count += 1
                    
                    with SimulationLogContext(self.logger, species=sp, 
                                            site_index=si, trees_per_acre=tpa):
                        self.logger.info(f"Running yield table simulation {sim_count}/{total_sims}")
                    
                    # Run simulation without individual plots
                    df = self.simulate_stand(
                        species=sp,
                        trees_per_acre=tpa,
                        site_index=si,
                        years=years,
                        time_step=time_step,
                        save_outputs=False,
                        plot_results=False
                    )
                    
                    # Add scenario identifiers
                    df['species'] = sp
                    df['site_index'] = si
                    df['initial_tpa'] = tpa
                    
                    all_results.append(df)
        
        # Combine all results
        yield_table = pd.concat(all_results, ignore_index=True)
        
        # Save if requested
        if save_outputs:
            self.exporter.export_yield_table(yield_table, format='excel', filename='yield_table')
            self.exporter.export_yield_table(yield_table, format='csv', filename='yield_table')
        
        return yield_table
    
    def _run_growth_simulation(self, stand: Stand, years: int, time_step: int) -> List[Dict[str, Any]]:
        """Run the growth simulation for a stand.
        
        Args:
            stand: Stand to simulate
            years: Total years to simulate
            time_step: Years per growth period
            
        Returns:
            List of metrics dictionaries
        """
        metrics = []
        
        # Collect initial metrics
        current_metrics = stand.get_metrics()
        metrics.append(current_metrics)
        
        # Simulate growth
        for year in range(time_step, years + 1, time_step):
            # Grow stand
            stand.grow(years=time_step)
            
            # Collect metrics
            current_metrics = stand.get_metrics()
            metrics.append(current_metrics)
            
            # Log progress
            if year % 10 == 0:
                self.logger.info(f"  Age {year}: TPA={current_metrics['tpa']:.0f}, "
                               f"BA={current_metrics['basal_area']:.1f}, "
                               f"Volume={current_metrics['volume']:.0f}")
        
        return metrics
    
    def _save_results(self, df: pd.DataFrame, species: str, tpa: int, site_index: float, 
                     export_formats: List[str] = ['csv']):
        """Save simulation results to file(s).
        
        Args:
            df: Results DataFrame
            species: Species code
            tpa: Initial trees per acre
            site_index: Site index
            export_formats: List of formats to export ('csv', 'json', 'excel')
        """
        base_filename = f"sim_{species}_TPA{tpa}_SI{int(site_index)}"

        exported_files = {}
        for format_type in export_formats:
            try:
                if format_type == 'csv':
                    # Don't include metadata for CSV to allow easy reading back
                    filepath = self.exporter.export_to_csv(df, base_filename, include_metadata=False)
                elif format_type == 'json':
                    filepath = self.exporter.export_to_json(df, base_filename)
                elif format_type == 'excel':
                    filepath = self.exporter.export_to_excel(df, base_filename)
                else:
                    self.logger.warning(f"Unsupported export format: {format_type}")
                    continue

                exported_files[format_type] = filepath

            except Exception as e:
                self.logger.error(f"Failed to export {format_type}: {e}")
        
        return exported_files
    
    def _generate_plots(self, metrics: List[Dict[str, Any]], 
                       species: str, tpa: int, site_index: float):
        """Generate visualization plots.
        
        Args:
            metrics: List of metrics dictionaries
            species: Species code
            tpa: Initial trees per acre
            site_index: Site index
        """
        plot_prefix = f"{species}_TPA{tpa}_SI{int(site_index)}"
        
        # Stand trajectories
        plot_stand_trajectories(
            metrics,
            save_path=self.output_dir / f"{plot_prefix}_trajectories.png"
        )
        
        # Size distributions at key ages
        for age_metrics in metrics:
            age = age_metrics['age']
            if age in [0, 10, 25, 50]:
                # Note: This would need access to the stand object
                # For now, we'll skip size distribution plots
                pass
        
        # Mortality patterns
        if len(metrics) > 1:
            plot_mortality_patterns(
                metrics,
                save_path=self.output_dir / f"{plot_prefix}_mortality.png"
            )
    
    def compare_scenarios(self, scenarios: List[Dict[str, Any]], 
                         years: int = 50,
                         time_step: int = 5) -> pd.DataFrame:
        """Compare multiple simulation scenarios.
        
        Args:
            scenarios: List of scenario dictionaries with keys:
                      'name', 'species', 'trees_per_acre', 'site_index'
            years: Simulation length
            time_step: Growth period length
            
        Returns:
            DataFrame with comparison results
        """
        comparison_results = []
        
        for scenario in scenarios:
            self.logger.info(f"Running scenario: {scenario['name']}")
            
            df = self.simulate_stand(
                species=scenario.get('species', 'LP'),
                trees_per_acre=scenario.get('trees_per_acre', 500),
                site_index=scenario.get('site_index', 70),
                years=years,
                time_step=time_step,
                save_outputs=False,
                plot_results=False
            )
            
            # Add scenario name
            df['scenario'] = scenario['name']
            comparison_results.append(df)
        
        # Combine results
        comparison_df = pd.concat(comparison_results, ignore_index=True)

        # Save comparison results with fixed filenames
        self.exporter.export_scenario_comparison(comparison_df, format='excel', filename='scenario_comparison')
        self.exporter.export_scenario_comparison(comparison_df, format='csv', filename='scenario_comparison')

        return comparison_df


# Convenience functions for backward compatibility
def run_simulation(species: str = 'LP', 
                  trees_per_acre: int = 500,
                  site_index: float = 70,
                  years: int = 50,
                  time_step: int = 5,
                  output_dir: Optional[str] = None) -> pd.DataFrame:
    """Run a stand simulation using the unified engine.
    
    Args:
        species: Species code
        trees_per_acre: Initial planting density
        site_index: Site index
        years: Simulation length
        time_step: Growth period length
        output_dir: Output directory
        
    Returns:
        DataFrame with results
    """
    engine = SimulationEngine(output_dir)
    return engine.simulate_stand(
        species=species,
        trees_per_acre=trees_per_acre,
        site_index=site_index,
        years=years,
        time_step=time_step
    )


def generate_yield_table(species: Union[str, List[str]] = 'LP',
                       site_indices: List[float] = [60, 70, 80],
                       planting_densities: List[int] = [300, 500, 700],
                       years: int = 50,
                       output_dir: Optional[str] = None) -> pd.DataFrame:
    """Generate yield tables using the unified engine.
    
    Args:
        species: Species code(s)
        site_indices: Site indices to test
        planting_densities: Initial TPAs to test
        years: Simulation length
        output_dir: Output directory
        
    Returns:
        DataFrame with yield table
    """
    engine = SimulationEngine(output_dir)
    return engine.simulate_yield_table(
        species=species,
        site_indices=site_indices,
        planting_densities=planting_densities,
        years=years
    )
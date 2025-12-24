"""
Data export utilities for FVS-Python.
Provides various formats for exporting simulation results.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import numpy as np
from datetime import datetime

from .logging_config import get_logger


class DataExporter:
    """Handles export of simulation data to various formats."""
    
    def __init__(self, output_dir: Path):
        """Initialize the data exporter.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.logger = get_logger(__name__)
    
    def export_to_csv(self, 
                     data: Union[pd.DataFrame, List[Dict]], 
                     filename: str,
                     include_metadata: bool = True) -> Path:
        """Export data to CSV format.
        
        Args:
            data: Data to export (DataFrame or list of dicts)
            filename: Output filename
            include_metadata: Whether to include metadata header
            
        Returns:
            Path to exported file
        """
        filepath = self.output_dir / f"{filename}.csv"
        
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()
        
        with open(filepath, 'w', newline='') as f:
            if include_metadata:
                # Write metadata header
                f.write(f"# FVS-Python Export\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write(f"# Records: {len(df)}\n")
                f.write(f"# Columns: {', '.join(df.columns)}\n")
                f.write("#\n")
            
            # Write data
            df.to_csv(f, index=False)
        
        self.logger.info(f"Exported {len(df)} records to {filepath}")
        return filepath
    
    def export_to_json(self, 
                      data: Union[pd.DataFrame, List[Dict], Dict], 
                      filename: str,
                      include_metadata: bool = True,
                      format_style: str = 'records') -> Path:
        """Export data to JSON format.
        
        Args:
            data: Data to export
            filename: Output filename
            include_metadata: Whether to include metadata
            format_style: JSON format ('records', 'values', 'index', 'split')
            
        Returns:
            Path to exported file
        """
        filepath = self.output_dir / f"{filename}.json"
        
        # Prepare data
        if isinstance(data, pd.DataFrame):
            if format_style == 'records':
                export_data = data.to_dict('records')
            elif format_style == 'values':
                export_data = data.values.tolist()
            elif format_style == 'index':
                export_data = data.to_dict('index')
            elif format_style == 'split':
                export_data = data.to_dict('split')
            else:
                export_data = data.to_dict('records')
        elif isinstance(data, list):
            export_data = data
        else:
            export_data = data
        
        # Create output structure
        output = {}
        if include_metadata:
            output['metadata'] = {
                'generator': 'FVS-Python',
                'generated_at': datetime.now().isoformat(),
                'format': format_style,
                'record_count': len(export_data) if isinstance(export_data, list) else 1
            }
        
        output['data'] = export_data
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2, default=self._json_serializer)
        
        self.logger.info(f"Exported data to {filepath}")
        return filepath

    def export_to_excel(self,
                       data: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
                       filename: str) -> Path:
        """Export data to Excel format.

        Args:
            data: Data to export (single DataFrame or dict of DataFrames for multiple sheets)
            filename: Output filename

        Returns:
            Path to exported file
        """
        filepath = self.output_dir / f"{filename}.xlsx"

        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                if isinstance(data, pd.DataFrame):
                    data.to_excel(writer, sheet_name='Data', index=False)
                else:
                    for sheet_name, df in data.items():
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

            self.logger.info(f"Exported data to Excel file {filepath}")
            return filepath

        except ImportError:
            self.logger.warning("openpyxl not available, falling back to CSV export")
            if isinstance(data, pd.DataFrame):
                return self.export_to_csv(data, filename)
            else:
                first_sheet = next(iter(data.values()))
                return self.export_to_csv(first_sheet, filename)
    
    def export_yield_table(self,
                          yield_table: pd.DataFrame,
                          format: str = 'csv',
                          filename: Optional[str] = None) -> Path:
        """Export yield table with proper formatting.

        Args:
            yield_table: Yield table DataFrame
            format: Export format ('csv', 'json', 'excel')
            filename: Custom filename (optional)

        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"yield_table_{timestamp}"

        # Round numeric columns for better presentation
        display_table = yield_table.copy()
        numeric_columns = ['mean_dbh', 'mean_height', 'basal_area', 'volume']
        for col in numeric_columns:
            if col in display_table.columns:
                display_table[col] = display_table[col].round(2)

        # Sort by logical order
        if all(col in display_table.columns for col in ['species', 'site_index', 'initial_tpa', 'age']):
            display_table = display_table.sort_values(['species', 'site_index', 'initial_tpa', 'age'])

        if format.lower() == 'csv':
            # No metadata for CSV to allow easy reading back
            return self.export_to_csv(display_table, filename, include_metadata=False)
        elif format.lower() == 'json':
            return self.export_to_json(display_table, filename)
        elif format.lower() == 'excel':
            return self.export_to_excel(display_table, filename)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def export_scenario_comparison(self,
                                 comparison_df: pd.DataFrame,
                                 format: str = 'csv',
                                 filename: Optional[str] = None) -> Path:
        """Export scenario comparison results.

        Args:
            comparison_df: Scenario comparison DataFrame
            format: Export format
            filename: Custom filename (optional)

        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scenario_comparison_{timestamp}"

        # Create summary statistics
        if format.lower() == 'excel':
            # Create multiple sheets for Excel
            sheets = {
                'Raw_Data': comparison_df,
                'Summary': self._create_scenario_summary(comparison_df)
            }
            return self.export_to_excel(sheets, filename)
        elif format.lower() == 'csv':
            # No metadata for CSV to allow easy reading back
            return self.export_to_csv(comparison_df, filename, include_metadata=False)
        else:
            return getattr(self, f'export_to_{format.lower()}')(comparison_df, filename)

    def export_stand_metrics(self,
                           metrics_over_time: List[Dict],
                           format: str = 'csv',
                           filename: Optional[str] = None) -> Path:
        """Export stand metrics over time.

        Args:
            metrics_over_time: List of metric dictionaries
            format: Export format ('csv', 'json', 'excel')
            filename: Custom filename (optional)

        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stand_metrics_{timestamp}"

        df = pd.DataFrame(metrics_over_time)

        # Round numeric columns
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].round(2)

        if format.lower() == 'csv':
            # No metadata for CSV to allow easy reading back
            return self.export_to_csv(df, filename, include_metadata=False)
        elif format.lower() == 'json':
            return self.export_to_json(df, filename)
        elif format.lower() == 'excel':
            return self.export_to_excel(df, filename)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def create_summary_report(self,
                            simulation_results: Dict[str, Any],
                            filename: Optional[str] = None) -> Path:
        """Create a comprehensive summary report.

        Args:
            simulation_results: Dictionary containing all simulation results
            filename: Custom filename (optional)

        Returns:
            Path to summary report file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"simulation_summary_{timestamp}"

        filepath = self.output_dir / f"{filename}.txt"

        with open(filepath, 'w') as f:
            f.write("FVS-Python Simulation Summary Report\n")
            f.write("=" * 50 + "\n\n")

            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Software: FVS-Python v1.0.0\n\n")

            # Simulation parameters
            if 'parameters' in simulation_results:
                params = simulation_results['parameters']
                f.write("Simulation Parameters:\n")
                f.write("-" * 25 + "\n")
                for key, value in params.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")

            # Final metrics
            if 'final_metrics' in simulation_results:
                metrics = simulation_results['final_metrics']
                f.write("Final Stand Metrics:\n")
                f.write("-" * 25 + "\n")
                f.write(f"Age: {metrics.get('age', 'N/A')} years\n")
                f.write(f"Trees per Acre: {metrics.get('tpa', 'N/A'):.0f}\n")
                f.write(f"Mean DBH: {metrics.get('mean_dbh', 'N/A'):.1f} inches\n")
                f.write(f"Mean Height: {metrics.get('mean_height', 'N/A'):.1f} feet\n")
                f.write(f"Basal Area: {metrics.get('basal_area', 'N/A'):.1f} sq ft/acre\n")
                f.write(f"Volume: {metrics.get('volume', 'N/A'):.0f} cubic feet/acre\n")
                f.write("\n")

            # Growth summary
            if 'growth_summary' in simulation_results:
                f.write("Growth Summary:\n")
                f.write("-" * 25 + "\n")
                summary = simulation_results['growth_summary']
                f.write(f"Total DBH Growth: {summary.get('total_dbh_growth', 'N/A'):.1f} inches\n")
                f.write(f"Total Height Growth: {summary.get('total_height_growth', 'N/A'):.1f} feet\n")
                f.write(f"Total Volume Growth: {summary.get('total_volume_growth', 'N/A'):.0f} cu ft/acre\n")
                f.write(f"Survival Rate: {summary.get('survival_rate', 'N/A'):.1%}\n")
                f.write("\n")

            # File references
            f.write("Associated Files:\n")
            f.write("-" * 25 + "\n")
            if 'output_files' in simulation_results:
                for file_type, filepath_ref in simulation_results['output_files'].items():
                    f.write(f"{file_type}: {filepath_ref}\n")

        self.logger.info(f"Created summary report: {filepath}")
        return filepath

    def _json_serializer(self, obj):
        """JSON serializer for numpy types."""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return str(obj)

    def _create_scenario_summary(self, comparison_df: pd.DataFrame) -> pd.DataFrame:
        """Create summary statistics for scenario comparison."""
        if 'scenario' not in comparison_df.columns:
            return pd.DataFrame()

        # Get final metrics for each scenario
        final_metrics = []
        for scenario in comparison_df['scenario'].unique():
            scenario_data = comparison_df[comparison_df['scenario'] == scenario]
            final_row = scenario_data[scenario_data['age'] == scenario_data['age'].max()].iloc[0]

            summary = {
                'scenario': scenario,
                'final_age': final_row['age'],
                'final_tpa': final_row.get('tpa', 0),
                'final_volume': final_row.get('volume', 0),
                'final_mean_dbh': final_row.get('mean_dbh', 0),
                'final_mean_height': final_row.get('mean_height', 0)
            }
            final_metrics.append(summary)

        return pd.DataFrame(final_metrics)
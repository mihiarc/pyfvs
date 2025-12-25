"""
Test suite for crown ratio relationship functions.
Includes unit tests and visualization of crown ratio behavior.
"""
import pytest
import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pyfvs.crown_ratio import (
    CrownRatioModel,
    create_crown_ratio_model,
    calculate_average_crown_ratio,
    predict_tree_crown_ratio,
    compare_crown_ratio_models
)


class TestCrownRatioModel:
    """Test the CrownRatioModel class."""
    
    def test_model_initialization(self):
        """Test that models initialize correctly with species parameters."""
        model = CrownRatioModel("LP")
        assert model.species_code == "LP"
        assert hasattr(model, 'coefficients')
        assert hasattr(model, 'equations')
    
    def test_average_crown_ratio_calculation(self):
        """Test average crown ratio calculation for different RELSDI values."""
        model = CrownRatioModel("LP")
        
        # Test with different RELSDI values
        relsdi_values = [1.0, 3.0, 5.0, 8.0, 12.0]
        
        for relsdi in relsdi_values:
            acr = model.calculate_average_crown_ratio(relsdi)
            assert 0.05 <= acr <= 0.95, f"ACR {acr} out of bounds for RELSDI {relsdi}"
    
    def test_weibull_parameters(self):
        """Test Weibull parameter calculation."""
        model = CrownRatioModel("LP")
        
        acr = 0.6  # 60% average crown ratio
        A, B, C = model.calculate_weibull_parameters(acr)
        
        assert A > 0, "Weibull parameter A should be positive"
        assert B >= 3.0, "Weibull parameter B should be >= 3.0"
        assert C >= 2.0, "Weibull parameter C should be >= 2.0"
    
    def test_scale_factor(self):
        """Test scale factor calculation."""
        model = CrownRatioModel("LP")
        
        # Test different CCF values
        ccf_values = [50, 100, 150, 200, 300]
        
        for ccf in ccf_values:
            scale = model.calculate_scale_factor(ccf)
            assert 0.3 <= scale <= 1.0, f"Scale factor {scale} out of bounds for CCF {ccf}"
    
    def test_individual_crown_ratio_prediction(self):
        """Test individual tree crown ratio prediction."""
        model = CrownRatioModel("LP")
        
        # Test with different tree ranks and densities
        ranks = [0.1, 0.3, 0.5, 0.7, 0.9]
        relsdi_values = [2.0, 5.0, 8.0]
        
        for rank in ranks:
            for relsdi in relsdi_values:
                cr = model.predict_individual_crown_ratio(rank, relsdi)
                assert 0.05 <= cr <= 0.95, f"Crown ratio {cr} out of bounds"
    
    def test_dead_tree_crown_ratio(self):
        """Test crown ratio prediction for dead trees."""
        model = CrownRatioModel("LP")
        
        dbh_values = [5, 10, 15, 20, 25, 30]
        
        for dbh in dbh_values:
            cr = model.predict_dead_tree_crown_ratio(dbh, random_seed=42)
            assert 0.05 <= cr <= 0.95, f"Dead tree crown ratio {cr} out of bounds"
    
    def test_regeneration_crown_ratio(self):
        """Test crown ratio prediction for regeneration."""
        model = CrownRatioModel("LP")
        
        pccf_values = [50, 100, 150, 200]
        
        for pccf in pccf_values:
            cr = model.predict_regeneration_crown_ratio(pccf, random_seed=42)
            assert 0.2 <= cr <= 0.9, f"Regeneration crown ratio {cr} out of bounds"
    
    def test_crown_ratio_change_bounds(self):
        """Test crown ratio change with bounds checking."""
        model = CrownRatioModel("LP")
        
        current_cr = 0.6
        predicted_cr = 0.8
        height_growth = 5.0
        
        new_cr = model.update_crown_ratio_change(current_cr, predicted_cr, height_growth)
        assert 0.05 <= new_cr <= 0.95, "New crown ratio out of bounds"
        
        # Test that change is bounded (with small tolerance for floating point precision)
        change = new_cr - current_cr
        assert abs(change) <= 0.051, "Crown ratio change exceeds 5% limit for 5-year cycle"


class TestStandaloneFunctions:
    """Test standalone crown ratio functions."""
    
    def test_calculate_average_crown_ratio(self):
        """Test standalone average crown ratio function."""
        acr = calculate_average_crown_ratio("LP", 5.0)
        assert 0.05 <= acr <= 0.95
    
    def test_predict_tree_crown_ratio(self):
        """Test standalone tree crown ratio prediction."""
        cr = predict_tree_crown_ratio("LP", 0.5, 5.0)
        assert 0.05 <= cr <= 0.95
    
    def test_compare_crown_ratio_models(self):
        """Test model comparison function."""
        species_codes = ["LP", "SP", "WO"]
        relsdi_range = [1.0, 3.0, 5.0, 8.0, 12.0]
        
        results = compare_crown_ratio_models(species_codes, relsdi_range)
        
        assert 'relsdi' in results
        assert 'species_results' in results
        assert len(results['species_results']) == len(species_codes)
        
        for species in species_codes:
            assert species in results['species_results']
            species_data = results['species_results'][species]
            assert 'average_crown_ratio' in species_data
            assert 'individual_crown_ratio' in species_data
            assert 'equation_type' in species_data


class TestVisualization:
    """Test crown ratio visualization functions."""
    
    def test_crown_ratio_vs_density_plots(self):
        """Generate plots showing crown ratio vs stand density."""
        # Create output directory
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        
        # Test different species
        species_list = ["LP", "SP", "WO", "RM"]
        relsdi_range = np.linspace(1.0, 12.0, 50)
        
        plt.figure(figsize=(12, 8))
        
        for i, species in enumerate(species_list):
            model = create_crown_ratio_model(species)
            
            # Calculate average crown ratios
            acr_values = [model.calculate_average_crown_ratio(relsdi) for relsdi in relsdi_range]
            
            # Calculate individual crown ratios for different tree ranks
            ranks = [0.1, 0.5, 0.9]  # Small, medium, large trees
            
            plt.subplot(2, 2, i+1)
            plt.plot(relsdi_range, acr_values, 'k-', linewidth=2, label='Average CR')
            
            for rank in ranks:
                individual_cr = [model.predict_individual_crown_ratio(rank, relsdi) 
                               for relsdi in relsdi_range]
                plt.plot(relsdi_range, individual_cr, '--', 
                        label=f'Rank {rank:.1f}')
            
            plt.xlabel('Relative Stand Density Index')
            plt.ylabel('Crown Ratio')
            plt.title(f'{species} Crown Ratio vs Density')
            plt.legend()
            plt.grid(True)
            plt.ylim(0, 1)
        
        plt.tight_layout()
        plt.savefig(output_dir / "crown_ratio_vs_density.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def test_weibull_distribution_plots(self):
        """Generate plots showing Weibull distribution shapes."""
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        
        species_list = ["LP", "SP", "WO", "RM"]
        relsdi_values = [2.0, 5.0, 8.0, 11.0]
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes = axes.flatten()
        
        for i, species in enumerate(species_list):
            model = create_crown_ratio_model(species)
            
            ax = axes[i]
            
            for relsdi in relsdi_values:
                # Calculate crown ratios for different tree ranks
                ranks = np.linspace(0.05, 0.95, 100)
                crown_ratios = [model.predict_individual_crown_ratio(rank, relsdi) 
                              for rank in ranks]
                
                ax.plot(ranks, crown_ratios, label=f'RELSDI {relsdi:.1f}')
            
            ax.set_xlabel('Tree Rank (0=smallest, 1=largest)')
            ax.set_ylabel('Crown Ratio')
            ax.set_title(f'{species} Crown Ratio Distribution')
            ax.legend()
            ax.grid(True)
            ax.set_ylim(0, 1)
        
        plt.tight_layout()
        plt.savefig(output_dir / "crown_ratio_distributions.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def test_species_comparison_plot(self):
        """Generate comparison plot across species."""
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        
        species_list = ["LP", "SP", "WO", "RM", "CA", "AB"]
        relsdi_range = np.linspace(1.0, 12.0, 50)
        
        plt.figure(figsize=(14, 8))
        
        # Average crown ratio comparison
        plt.subplot(1, 2, 1)
        for species in species_list:
            model = create_crown_ratio_model(species)
            acr_values = [model.calculate_average_crown_ratio(relsdi) for relsdi in relsdi_range]
            plt.plot(relsdi_range, acr_values, label=species, linewidth=2)
        
        plt.xlabel('Relative Stand Density Index')
        plt.ylabel('Average Crown Ratio')
        plt.title('Average Crown Ratio by Species')
        plt.legend()
        plt.grid(True)
        plt.ylim(0, 1)
        
        # Individual tree crown ratio (median tree)
        plt.subplot(1, 2, 2)
        for species in species_list:
            model = create_crown_ratio_model(species)
            individual_cr = [model.predict_individual_crown_ratio(0.5, relsdi) 
                           for relsdi in relsdi_range]
            plt.plot(relsdi_range, individual_cr, label=species, linewidth=2)
        
        plt.xlabel('Relative Stand Density Index')
        plt.ylabel('Individual Crown Ratio (Median Tree)')
        plt.title('Individual Crown Ratio by Species')
        plt.legend()
        plt.grid(True)
        plt.ylim(0, 1)
        
        plt.tight_layout()
        plt.savefig(output_dir / "species_crown_ratio_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def test_generate_summary_report(self):
        """Generate a summary report of crown ratio models."""
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        
        species_list = ["LP", "SP", "WO", "RM", "CA", "AB", "AS", "WA"]
        
        with open(output_dir / "crown_ratio_summary.txt", "w") as f:
            f.write("Crown Ratio Model Summary Report\n")
            f.write("=" * 50 + "\n\n")
            
            for species in species_list:
                try:
                    model = create_crown_ratio_model(species)
                    
                    f.write(f"Species: {species}\n")
                    f.write("-" * 20 + "\n")
                    f.write(f"Equation Type: {model.coefficients['acr_equation']}\n")
                    f.write(f"Parameters:\n")
                    for param, value in model.coefficients.items():
                        if param != 'acr_equation':
                            f.write(f"  {param}: {value}\n")
                    
                    # Test predictions at different densities
                    f.write("\nPredictions at different densities:\n")
                    for relsdi in [2.0, 5.0, 8.0]:
                        acr = model.calculate_average_crown_ratio(relsdi)
                        individual_cr = model.predict_individual_crown_ratio(0.5, relsdi)
                        f.write(f"  RELSDI {relsdi}: ACR={acr:.3f}, Individual CR={individual_cr:.3f}\n")
                    
                    f.write("\n")
                    
                except Exception as e:
                    f.write(f"Species: {species} - Error: {str(e)}\n\n")


def test_run_all_crown_ratio_tests():
    """Run all crown ratio tests and generate visualizations."""
    print("Running crown ratio model tests...")
    
    # Create test instances
    model_tests = TestCrownRatioModel()
    function_tests = TestStandaloneFunctions()
    viz_tests = TestVisualization()
    
    # Run model tests
    print("Testing model initialization...")
    model_tests.test_model_initialization()
    
    print("Testing average crown ratio calculation...")
    model_tests.test_average_crown_ratio_calculation()
    
    print("Testing Weibull parameters...")
    model_tests.test_weibull_parameters()
    
    print("Testing scale factor...")
    model_tests.test_scale_factor()
    
    print("Testing individual crown ratio prediction...")
    model_tests.test_individual_crown_ratio_prediction()
    
    print("Testing dead tree crown ratio...")
    model_tests.test_dead_tree_crown_ratio()
    
    print("Testing regeneration crown ratio...")
    model_tests.test_regeneration_crown_ratio()
    
    print("Testing crown ratio change bounds...")
    model_tests.test_crown_ratio_change_bounds()
    
    # Run function tests
    print("Testing standalone functions...")
    function_tests.test_calculate_average_crown_ratio()
    function_tests.test_predict_tree_crown_ratio()
    function_tests.test_compare_crown_ratio_models()
    
    # Generate visualizations
    print("Generating crown ratio vs density plots...")
    viz_tests.test_crown_ratio_vs_density_plots()
    
    print("Generating Weibull distribution plots...")
    viz_tests.test_weibull_distribution_plots()
    
    print("Generating species comparison plots...")
    viz_tests.test_species_comparison_plot()
    
    print("Generating summary report...")
    viz_tests.test_generate_summary_report()
    
    print("All crown ratio tests completed successfully!")


if __name__ == "__main__":
    test_run_all_crown_ratio_tests() 
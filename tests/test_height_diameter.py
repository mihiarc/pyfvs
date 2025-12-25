"""
Test suite for height-diameter relationship functions.
Includes unit tests and visualization of model behavior.
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

from pyfvs.height_diameter import (
    HeightDiameterModel,
    create_height_diameter_model,
    curtis_arney_height,
    wykoff_height,
    compare_models
)


class TestHeightDiameterModel:
    """Test the HeightDiameterModel class."""
    
    def test_model_initialization(self):
        """Test that models initialize correctly with species parameters."""
        model = create_height_diameter_model("LP")
        assert model.species_code == "LP"
        assert "curtis_arney" in model.hd_params
        assert "wykoff" in model.hd_params
    
    def test_curtis_arney_basic(self):
        """Test Curtis-Arney model basic functionality."""
        model = create_height_diameter_model("LP")
        
        # Test small DBH (should return 4.5)
        height = model.curtis_arney_height(0.05)
        assert height == 4.5
        
        # Test normal DBH
        height = model.curtis_arney_height(10.0)
        assert height > 4.5
        assert height < 200  # Reasonable upper bound
    
    def test_wykoff_basic(self):
        """Test Wykoff model basic functionality."""
        model = create_height_diameter_model("LP")
        
        # Test zero DBH
        height = model.wykoff_height(0.0)
        assert height == 4.5
        
        # Test normal DBH
        height = model.wykoff_height(10.0)
        assert height > 4.5
        assert height < 200  # Reasonable upper bound
    
    def test_predict_height(self):
        """Test the general predict_height method."""
        model = create_height_diameter_model("LP")
        
        dbh = 8.0
        ca_height = model.predict_height(dbh, "curtis_arney")
        wy_height = model.predict_height(dbh, "wykoff")
        default_height = model.predict_height(dbh)
        
        assert ca_height > 4.5
        assert wy_height > 4.5
        assert default_height == ca_height  # Default should be curtis_arney
    
    def test_solve_dbh_from_height(self):
        """Test the numerical solver for DBH from height."""
        model = create_height_diameter_model("LP")
        
        # Test round-trip: DBH -> Height -> DBH
        original_dbh = 12.0
        height = model.predict_height(original_dbh)
        solved_dbh = model.solve_dbh_from_height(height)
        
        # Should be close to original (within tolerance)
        assert abs(solved_dbh - original_dbh) < 0.1
    
    def test_model_parameters(self):
        """Test parameter retrieval."""
        model = create_height_diameter_model("LP")
        
        ca_params = model.get_model_parameters("curtis_arney")
        assert "p2" in ca_params
        assert "p3" in ca_params
        assert "p4" in ca_params
        assert "dbw" in ca_params
        
        wy_params = model.get_model_parameters("wykoff")
        assert "b1" in wy_params
        assert "b2" in wy_params


class TestStandaloneFunctions:
    """Test standalone height-diameter functions."""
    
    def test_curtis_arney_standalone(self):
        """Test standalone Curtis-Arney function."""
        # Test with known parameters
        height = curtis_arney_height(10.0, p2=100.0, p3=0.1, p4=-0.5, dbw=0.1)
        assert height > 4.5
        
        # Test small tree
        height = curtis_arney_height(0.05, p2=100.0, p3=0.1, p4=-0.5, dbw=0.1)
        assert height == 4.5
    
    def test_wykoff_standalone(self):
        """Test standalone Wykoff function."""
        # Test with known parameters
        height = wykoff_height(10.0, b1=4.0, b2=-5.0)
        assert height > 4.5
        
        # Test zero DBH
        height = wykoff_height(0.0, b1=4.0, b2=-5.0)
        assert height == 4.5


class TestModelComparison:
    """Test model comparison functionality."""
    
    def test_compare_models(self):
        """Test the compare_models function."""
        dbh_range = [1, 5, 10, 15, 20]
        results = compare_models(dbh_range, "LP")
        
        assert "dbh" in results
        assert "curtis_arney" in results
        assert "wykoff" in results
        assert len(results["dbh"]) == len(dbh_range)
        assert len(results["curtis_arney"]) == len(dbh_range)
        assert len(results["wykoff"]) == len(dbh_range)


class TestVisualization:
    """Test visualization and create figures."""
    
    def test_create_species_comparison_figure(self):
        """Create a figure comparing height-diameter curves for multiple species."""
        # Select a few representative species
        species_list = ["LP", "SP", "SA", "WO", "RM"]  # Mix of softwood and hardwood
        dbh_range = np.linspace(0.1, 30, 100)
        
        plt.figure(figsize=(12, 8))
        
        for species in species_list:
            try:
                model = create_height_diameter_model(species)
                heights_ca = [model.curtis_arney_height(dbh) for dbh in dbh_range]
                heights_wy = [model.wykoff_height(dbh) for dbh in dbh_range]
                
                plt.plot(dbh_range, heights_ca, '-', label=f'{species} (Curtis-Arney)', linewidth=2)
                plt.plot(dbh_range, heights_wy, '--', label=f'{species} (Wykoff)', linewidth=1, alpha=0.7)
            except Exception as e:
                print(f"Warning: Could not plot {species}: {e}")
                continue
        
        plt.xlabel('Diameter at Breast Height (inches)')
        plt.ylabel('Height (feet)')
        plt.title('Height-Diameter Relationships by Species')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save figure
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        plt.savefig(output_dir / "height_diameter_species_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        assert (output_dir / "height_diameter_species_comparison.png").exists()
    
    def test_create_model_comparison_figure(self):
        """Create a figure comparing Curtis-Arney vs Wykoff models."""
        species_list = ["LP", "SP", "WO"]  # Representative species
        dbh_range = np.linspace(0.1, 25, 100)
        
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        for i, species in enumerate(species_list):
            try:
                model = create_height_diameter_model(species)
                heights_ca = [model.curtis_arney_height(dbh) for dbh in dbh_range]
                heights_wy = [model.wykoff_height(dbh) for dbh in dbh_range]
                
                axes[i].plot(dbh_range, heights_ca, 'b-', label='Curtis-Arney', linewidth=2)
                axes[i].plot(dbh_range, heights_wy, 'r--', label='Wykoff', linewidth=2)
                axes[i].set_xlabel('DBH (inches)')
                axes[i].set_ylabel('Height (feet)')
                axes[i].set_title(f'{species}')
                axes[i].legend()
                axes[i].grid(True, alpha=0.3)
                
                # Add difference plot as inset
                diff = np.array(heights_ca) - np.array(heights_wy)
                ax_inset = axes[i].inset_axes([0.6, 0.1, 0.35, 0.3])
                ax_inset.plot(dbh_range, diff, 'g-', linewidth=1)
                ax_inset.set_xlabel('DBH', fontsize=8)
                ax_inset.set_ylabel('Diff (ft)', fontsize=8)
                ax_inset.tick_params(labelsize=6)
                ax_inset.grid(True, alpha=0.3)
                
            except Exception as e:
                print(f"Warning: Could not plot {species}: {e}")
                continue
        
        plt.tight_layout()
        
        # Save figure
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        plt.savefig(output_dir / "height_diameter_model_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        assert (output_dir / "height_diameter_model_comparison.png").exists()
    
    def test_create_parameter_sensitivity_figure(self):
        """Create a figure showing parameter sensitivity for Curtis-Arney model."""
        dbh_range = np.linspace(0.1, 20, 100)
        
        # Base parameters (approximate for LP)
        base_p2 = 100.0
        base_p3 = 0.1
        base_p4 = -0.5
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # P2 sensitivity
        for p2_mult in [0.5, 1.0, 1.5, 2.0]:
            heights = [curtis_arney_height(dbh, p2=base_p2*p2_mult, p3=base_p3, p4=base_p4) 
                      for dbh in dbh_range]
            axes[0,0].plot(dbh_range, heights, label=f'P2 × {p2_mult}')
        axes[0,0].set_title('P2 Parameter Sensitivity')
        axes[0,0].set_xlabel('DBH (inches)')
        axes[0,0].set_ylabel('Height (feet)')
        axes[0,0].legend()
        axes[0,0].grid(True, alpha=0.3)
        
        # P3 sensitivity
        for p3_mult in [0.5, 1.0, 1.5, 2.0]:
            heights = [curtis_arney_height(dbh, p2=base_p2, p3=base_p3*p3_mult, p4=base_p4) 
                      for dbh in dbh_range]
            axes[0,1].plot(dbh_range, heights, label=f'P3 × {p3_mult}')
        axes[0,1].set_title('P3 Parameter Sensitivity')
        axes[0,1].set_xlabel('DBH (inches)')
        axes[0,1].set_ylabel('Height (feet)')
        axes[0,1].legend()
        axes[0,1].grid(True, alpha=0.3)
        
        # P4 sensitivity
        for p4_mult in [0.5, 1.0, 1.5, 2.0]:
            heights = [curtis_arney_height(dbh, p2=base_p2, p3=base_p3, p4=base_p4*p4_mult) 
                      for dbh in dbh_range]
            axes[1,0].plot(dbh_range, heights, label=f'P4 × {p4_mult}')
        axes[1,0].set_title('P4 Parameter Sensitivity')
        axes[1,0].set_xlabel('DBH (inches)')
        axes[1,0].set_ylabel('Height (feet)')
        axes[1,0].legend()
        axes[1,0].grid(True, alpha=0.3)
        
        # Combined comparison
        model = create_height_diameter_model("LP")
        heights_lp = [model.curtis_arney_height(dbh) for dbh in dbh_range]
        heights_base = [curtis_arney_height(dbh, p2=base_p2, p3=base_p3, p4=base_p4) 
                       for dbh in dbh_range]
        
        axes[1,1].plot(dbh_range, heights_lp, 'b-', label='LP Actual', linewidth=2)
        axes[1,1].plot(dbh_range, heights_base, 'r--', label='Base Parameters', linewidth=2)
        axes[1,1].set_title('Actual vs Base Parameters')
        axes[1,1].set_xlabel('DBH (inches)')
        axes[1,1].set_ylabel('Height (feet)')
        axes[1,1].legend()
        axes[1,1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save figure
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        plt.savefig(output_dir / "height_diameter_parameter_sensitivity.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        assert (output_dir / "height_diameter_parameter_sensitivity.png").exists()
    
    def test_create_residuals_figure(self):
        """Create a figure showing model residuals and fit quality."""
        # Generate synthetic "observed" data with some noise
        np.random.seed(42)  # For reproducible results
        
        species = "LP"
        model = create_height_diameter_model(species)
        
        # Create synthetic observed data
        dbh_obs = np.random.uniform(1, 25, 100)
        height_true_ca = np.array([model.curtis_arney_height(dbh) for dbh in dbh_obs])
        height_true_wy = np.array([model.wykoff_height(dbh) for dbh in dbh_obs])
        
        # Add noise to create "observed" heights
        noise = np.random.normal(0, 3, len(dbh_obs))  # 3-foot standard deviation
        height_obs = height_true_ca + noise
        
        # Calculate predictions
        height_pred_ca = np.array([model.curtis_arney_height(dbh) for dbh in dbh_obs])
        height_pred_wy = np.array([model.wykoff_height(dbh) for dbh in dbh_obs])
        
        # Calculate residuals
        residuals_ca = height_obs - height_pred_ca
        residuals_wy = height_obs - height_pred_wy
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Observed vs Predicted - Curtis-Arney
        axes[0,0].scatter(height_pred_ca, height_obs, alpha=0.6, s=20)
        min_h, max_h = min(height_obs.min(), height_pred_ca.min()), max(height_obs.max(), height_pred_ca.max())
        axes[0,0].plot([min_h, max_h], [min_h, max_h], 'r--', linewidth=2)
        axes[0,0].set_xlabel('Predicted Height (feet)')
        axes[0,0].set_ylabel('Observed Height (feet)')
        axes[0,0].set_title('Curtis-Arney: Observed vs Predicted')
        axes[0,0].grid(True, alpha=0.3)
        
        # Observed vs Predicted - Wykoff
        axes[0,1].scatter(height_pred_wy, height_obs, alpha=0.6, s=20, color='orange')
        axes[0,1].plot([min_h, max_h], [min_h, max_h], 'r--', linewidth=2)
        axes[0,1].set_xlabel('Predicted Height (feet)')
        axes[0,1].set_ylabel('Observed Height (feet)')
        axes[0,1].set_title('Wykoff: Observed vs Predicted')
        axes[0,1].grid(True, alpha=0.3)
        
        # Residuals vs DBH - Curtis-Arney
        axes[1,0].scatter(dbh_obs, residuals_ca, alpha=0.6, s=20)
        axes[1,0].axhline(y=0, color='r', linestyle='--', linewidth=2)
        axes[1,0].set_xlabel('DBH (inches)')
        axes[1,0].set_ylabel('Residuals (feet)')
        axes[1,0].set_title('Curtis-Arney: Residuals vs DBH')
        axes[1,0].grid(True, alpha=0.3)
        
        # Residuals vs DBH - Wykoff
        axes[1,1].scatter(dbh_obs, residuals_wy, alpha=0.6, s=20, color='orange')
        axes[1,1].axhline(y=0, color='r', linestyle='--', linewidth=2)
        axes[1,1].set_xlabel('DBH (inches)')
        axes[1,1].set_ylabel('Residuals (feet)')
        axes[1,1].set_title('Wykoff: Residuals vs DBH')
        axes[1,1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save figure
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        plt.savefig(output_dir / "height_diameter_residuals.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        assert (output_dir / "height_diameter_residuals.png").exists()


def test_create_summary_report():
    """Create a summary report of all available species and their parameters."""
    # Load the coefficients JSON
    coeffs_path = Path("docs/sn_height_diameter_coefficients.json")
    if coeffs_path.exists():
        with open(coeffs_path, 'r') as f:
            coeffs = json.load(f)
        
        # Create summary table
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        
        with open(output_dir / "height_diameter_summary.txt", 'w') as f:
            f.write("Height-Diameter Model Parameters Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total species: {len(coeffs)}\n\n")
            
            f.write("Curtis-Arney Parameters (P2, P3, P4, Dbw):\n")
            f.write("-" * 40 + "\n")
            f.write(f"{'Species':<8} {'P2':<12} {'P3':<12} {'P4':<12} {'Dbw':<8}\n")
            f.write("-" * 40 + "\n")
            
            for species, params in sorted(coeffs.items()):
                f.write(f"{species:<8} {params['P2']:<12.2f} {params['P3']:<12.6f} "
                       f"{params['P4']:<12.6f} {params['Dbw']:<8.1f}\n")
            
            f.write("\n\nWykoff Parameters (B1, B2):\n")
            f.write("-" * 25 + "\n")
            f.write(f"{'Species':<8} {'B1':<12} {'B2':<12}\n")
            f.write("-" * 25 + "\n")
            
            for species, params in sorted(coeffs.items()):
                f.write(f"{species:<8} {params['Wykoff_B1']:<12.4f} {params['Wykoff_B2']:<12.4f}\n")
        
        assert (output_dir / "height_diameter_summary.txt").exists()


if __name__ == "__main__":
    # Run tests with visualization
    pytest.main([__file__, "-v"]) 
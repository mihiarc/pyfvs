"""
Crown ratio relationship functions for FVS-Python.
Implements Weibull-based crown model and other crown ratio equations from the SN variant.
"""
import math
import random
from typing import Dict, Any, Optional, Tuple
from .config_loader import load_coefficient_file


def _get_crown_ratio_data() -> Dict[str, Any]:
    """Get crown ratio data using ConfigLoader (with caching)."""
    try:
        return load_coefficient_file('sn_crown_ratio_coefficients.json')
    except FileNotFoundError:
        return {}


class CrownRatioModel:
    """Crown ratio model implementing FVS Southern variant equations."""

    def __init__(self, species_code: str = "LP"):
        """Initialize with species-specific parameters.

        Args:
            species_code: Species code (e.g., "LP", "SP", "WO", etc.)
        """
        self.species_code = species_code
        self._load_parameters()

    def _load_parameters(self):
        """Load crown ratio parameters from configuration."""
        try:
            crown_data = _get_crown_ratio_data()

            if crown_data and self.species_code in crown_data.get('species_coefficients', {}):
                self.coefficients = crown_data['species_coefficients'][self.species_code]
                self.equations = crown_data.get('equations', {})
            elif crown_data and 'LP' in crown_data.get('species_coefficients', {}):
                # Fallback to default LP parameters if species not found
                self.coefficients = crown_data['species_coefficients']['LP']
                self.equations = crown_data.get('equations', {})
            else:
                # Fallback parameters if file not found or loading fails
                self._load_fallback_parameters()
        except Exception:
            # Fallback parameters if file not found or loading fails
            self._load_fallback_parameters()
    
    def _load_fallback_parameters(self):
        """Load fallback parameters if crown ratio file not available."""
        # Default LP parameters
        self.coefficients = {
            "acr_equation": "4.3.1.3",
            "d0": 3.8284,
            "d1": -0.2234,
            "d2": 0.0172,
            "a": 4.9701,
            "b0": -14.6680,
            "b1": 1.3196,
            "c": 2.8517
        }
        
        self.equations = {
            "live_trees_weibull": {
                "average_crown_ratio_equations": {
                    "4_3_1_3": "ACR = exp[d0 + (d1 * ln(RELSDI)) + (d2 * RELSDI)]",
                    "4_3_1_4": "ACR = exp[d0 + (d1 * ln(RELSDI))]",
                    "4_3_1_5": "ACR = d0 + (d2 * RELSDI)",
                    "4_3_1_6": "ACR = d0 + (d1 * log10(RELSDI))",
                    "4_3_1_7": "ACR = RELSDI / ((d0 * RELSDI) + d1)"
                }
            }
        }
    
    def calculate_average_crown_ratio(self, relsdi: float) -> float:
        """Calculate average crown ratio for the stand using species-specific equation.
        
        Args:
            relsdi: Relative stand density index ((Stand SDI / Maximum SDI) * 10)
                   Bounded between 1.0 and 12.0
            
        Returns:
            Average crown ratio as a proportion (0-1)
        """
        # Bound RELSDI
        relsdi = max(1.0, min(12.0, relsdi))
        
        equation_type = self.coefficients['acr_equation']
        d0 = self.coefficients['d0']
        d1 = self.coefficients.get('d1')
        d2 = self.coefficients.get('d2')
        
        if equation_type == "4.3.1.3":
            # ACR = exp[d0 + (d1 * ln(RELSDI)) + (d2 * RELSDI)]
            if d1 is not None and d2 is not None:
                acr = math.exp(d0 + (d1 * math.log(relsdi)) + (d2 * relsdi))
            else:
                acr = math.exp(d0)
        elif equation_type == "4.3.1.4":
            # ACR = exp[d0 + (d1 * ln(RELSDI))]
            if d1 is not None:
                acr = math.exp(d0 + (d1 * math.log(relsdi)))
            else:
                acr = math.exp(d0)
        elif equation_type == "4.3.1.5":
            # ACR = d0 + (d2 * RELSDI)
            if d2 is not None:
                acr = d0 + (d2 * relsdi)
            else:
                acr = d0
        elif equation_type == "4.3.1.6":
            # ACR = d0 + (d1 * log10(RELSDI))
            if d1 is not None:
                acr = d0 + (d1 * math.log10(relsdi))
            else:
                acr = d0
        elif equation_type == "4.3.1.7":
            # ACR = RELSDI / ((d0 * RELSDI) + d1)
            if d1 is not None:
                acr = relsdi / ((d0 * relsdi) + d1)
            else:
                acr = relsdi / (d0 * relsdi + 1.0)
        else:
            # Default fallback
            acr = math.exp(d0 + (d1 or 0) * math.log(relsdi) + (d2 or 0) * relsdi)
        
        # Convert from percentage to proportion and bound
        if acr > 1.0:  # Assume it's in percentage
            acr = acr / 100.0
        
        return max(0.05, min(0.95, acr))
    
    def calculate_weibull_parameters(self, average_crown_ratio: float) -> Tuple[float, float, float]:
        """Calculate Weibull distribution parameters from average crown ratio.

        Args:
            average_crown_ratio: Average crown ratio as proportion (0-1)

        Returns:
            Tuple of (A, B, C) Weibull parameters
        """
        a = self.coefficients['a']
        b0 = self.coefficients['b0']
        b1 = self.coefficients['b1']
        c = self.coefficients['c']

        # Convert ACR from proportion (0-1) to percentage (0-100) for Weibull calculation
        # The b0/b1 coefficients were calibrated expecting ACR in percentage form
        acr_pct = average_crown_ratio * 100.0

        # Calculate Weibull parameters
        A = a
        B = max(3.0, b0 + b1 * acr_pct)  # Bounded to be greater than 3.0
        C = max(2.0, c)  # Bounded to be greater than 2.0

        return A, B, C
    
    def calculate_scale_factor(self, ccf: float) -> float:
        """Calculate density-dependent scaling factor.
        
        Args:
            ccf: Crown competition factor
            
        Returns:
            Scale factor (bounded 0.3 < SCALE < 1.0)
        """
        scale = 1.0 - 0.00167 * (ccf - 100)
        return max(0.3, min(1.0, scale))
    
    def predict_individual_crown_ratio(self, tree_rank: float, relsdi: float, 
                                     ccf: float = 100.0) -> float:
        """Predict individual tree crown ratio using Weibull distribution.
        
        Args:
            tree_rank: Tree's rank in diameter distribution (0-1, where 0=smallest, 1=largest)
            relsdi: Relative stand density index
            ccf: Crown competition factor (default: 100)
            
        Returns:
            Crown ratio as proportion (0-1)
        """
        # Calculate average crown ratio
        acr = self.calculate_average_crown_ratio(relsdi)
        
        # Calculate Weibull parameters
        A, B, C = self.calculate_weibull_parameters(acr)
        
        # Calculate scale factor
        scale = self.calculate_scale_factor(ccf)
        
        # Bound tree rank to avoid numerical issues
        x = max(0.05, min(0.95, tree_rank))
        
        try:
            # Calculate crown ratio using Weibull distribution
            # Y = A + B(-ln(1-X))^(1/C)
            crown_ratio = A + B * ((-math.log(1 - x)) ** (1/C))
            
            # Apply scale factor
            crown_ratio *= scale
            
            # Convert from percentage to proportion if needed
            if crown_ratio > 1.0:
                crown_ratio = crown_ratio / 100.0
            
            # Bound between 5% and 95% as specified in FVS
            return max(0.05, min(0.95, crown_ratio))
            
        except (ValueError, OverflowError):
            # Fallback to simple calculation if Weibull fails
            return max(0.05, min(0.95, acr * scale))
    
    def predict_dead_tree_crown_ratio(self, dbh: float, random_seed: Optional[int] = None) -> float:
        """Predict crown ratio for dead trees using equations 4.3.1.1 and 4.3.1.2.
        
        Args:
            dbh: Diameter at breast height (inches)
            random_seed: Optional random seed for reproducibility
            
        Returns:
            Crown ratio as proportion (0-1)
        """
        if random_seed is not None:
            random.seed(random_seed)
        
        # Equation 4.3.1.1
        if dbh < 24.0:
            X = 0.70 - 0.40/24.0 * dbh
        else:
            X = 0.30
        
        # Add random component (standard deviation not specified, using 0.2)
        random_component = random.gauss(0, 0.2)
        
        # Equation 4.3.1.2: CR = 1 / (1 + exp(X + N(0,SD)))
        crown_ratio = 1.0 / (1.0 + math.exp(X + random_component))
        
        # Bound to specified range
        return max(0.05, min(0.95, crown_ratio))
    
    def predict_regeneration_crown_ratio(self, pccf: float, random_seed: Optional[int] = None) -> float:
        """Predict crown ratio for newly established trees during regeneration.
        
        Args:
            pccf: Crown competition factor on the inventory point where tree is established
            random_seed: Optional random seed for reproducibility
            
        Returns:
            Crown ratio as proportion (0-1)
        """
        if random_seed is not None:
            random.seed(random_seed)
        
        # Small random component
        ran = random.gauss(0, 0.05)
        
        # Equation 4.3.3.1: CR = 0.89722 - 0.0000461 * PCCF + RAN
        crown_ratio = 0.89722 - 0.0000461 * pccf + ran
        
        # Bound to specified range
        return max(0.2, min(0.9, crown_ratio))
    
    def update_crown_ratio_change(self, current_cr: float, predicted_cr: float, 
                                height_growth: float, cycle_length: int = 5) -> float:
        """Calculate crown ratio change with bounds checking.
        
        Args:
            current_cr: Current crown ratio (proportion)
            predicted_cr: Predicted crown ratio at end of cycle (proportion)
            height_growth: Height growth during cycle (feet)
            cycle_length: Length of projection cycle (years)
            
        Returns:
            New crown ratio (proportion)
        """
        # Calculate potential change
        change = predicted_cr - current_cr
        
        # Check that change doesn't exceed what's possible with height growth
        # Assume all height growth produces new crown
        max_possible_change = height_growth / 100.0  # Rough approximation
        
        # Bound change to 1% per year for cycle length
        max_annual_change = 0.01
        max_cycle_change = max_annual_change * cycle_length
        
        # Apply bounds
        bounded_change = max(-max_cycle_change, 
                           min(max_cycle_change, 
                               min(change, max_possible_change)))
        
        new_cr = current_cr + bounded_change
        
        # Final bounds
        return max(0.05, min(0.95, new_cr))


def create_crown_ratio_model(species_code: str = "LP") -> CrownRatioModel:
    """Factory function to create a crown ratio model for a species.
    
    Args:
        species_code: Species code (e.g., "LP", "SP", "WO", etc.)
        
    Returns:
        CrownRatioModel instance
    """
    return CrownRatioModel(species_code)


def calculate_average_crown_ratio(species_code: str, relsdi: float) -> float:
    """Standalone function to calculate average crown ratio.
    
    Args:
        species_code: Species code
        relsdi: Relative stand density index
        
    Returns:
        Average crown ratio as proportion
    """
    model = create_crown_ratio_model(species_code)
    return model.calculate_average_crown_ratio(relsdi)


def predict_tree_crown_ratio(species_code: str, tree_rank: float, relsdi: float, 
                           ccf: float = 100.0) -> float:
    """Standalone function to predict individual tree crown ratio.
    
    Args:
        species_code: Species code
        tree_rank: Tree's rank in diameter distribution (0-1)
        relsdi: Relative stand density index
        ccf: Crown competition factor
        
    Returns:
        Crown ratio as proportion
    """
    model = create_crown_ratio_model(species_code)
    return model.predict_individual_crown_ratio(tree_rank, relsdi, ccf)


def compare_crown_ratio_models(species_codes: list, relsdi_range: list) -> Dict[str, Any]:
    """Compare crown ratio predictions across species and density levels.
    
    Args:
        species_codes: List of species codes to compare
        relsdi_range: List of RELSDI values to evaluate
        
    Returns:
        Dictionary with comparison results
    """
    results = {
        'relsdi': relsdi_range,
        'species_results': {}
    }
    
    for species in species_codes:
        model = create_crown_ratio_model(species)
        
        acr_values = []
        individual_cr_values = []
        
        for relsdi in relsdi_range:
            acr = model.calculate_average_crown_ratio(relsdi)
            acr_values.append(acr)
            
            # Calculate individual tree CR for median tree (rank = 0.5)
            individual_cr = model.predict_individual_crown_ratio(0.5, relsdi)
            individual_cr_values.append(individual_cr)
        
        results['species_results'][species] = {
            'average_crown_ratio': acr_values,
            'individual_crown_ratio': individual_cr_values,
            'equation_type': model.coefficients['acr_equation']
        }
    
    return results 
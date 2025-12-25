"""
Bark ratio relationship functions for FVS-Python.
Implements bark ratio equations from Clark (1991) for converting between
diameter outside bark (DOB) and diameter inside bark (DIB).
"""
from typing import Dict, Any
from .config_loader import get_config_loader, load_coefficient_file


def _get_bark_ratio_data() -> Dict[str, Any]:
    """Get bark ratio data using ConfigLoader (with caching)."""
    try:
        return load_coefficient_file('sn_bark_ratio_coefficients.json')
    except FileNotFoundError:
        return {}


class BarkRatioModel:
    """Bark ratio model implementing FVS Southern variant equations."""
    
    def __init__(self, species_code: str = "LP"):
        """Initialize with species-specific parameters.
        
        Args:
            species_code: Species code (e.g., "LP", "SP", "SA", etc.)
        """
        self.species_code = species_code
        self._load_parameters()
    
    def _load_parameters(self):
        """Load bark ratio parameters from cached configuration."""
        # Use module-level cached data instead of loading from disk each time
        bark_data = _get_bark_ratio_data()

        if bark_data:
            species_coeffs = bark_data.get('species_coefficients', {})
            if self.species_code in species_coeffs:
                self.coefficients = species_coeffs[self.species_code]
            else:
                # Fallback to default LP parameters if species not found
                self.coefficients = species_coeffs.get('LP', {"b1": -0.48140, "b2": 0.91413})

            self.equation_info = bark_data.get('equation', {})
            self.bounds = self.equation_info.get('bounds', "0.80 < BRATIO < 0.99")
        else:
            # Fallback parameters if file not found
            self._load_fallback_parameters()
    
    def _load_fallback_parameters(self):
        """Load fallback parameters if bark ratio file not available."""
        # Default LP parameters from the JSON file
        self.coefficients = {
            "b1": -0.48140,
            "b2": 0.91413
        }
        
        self.equation_info = {
            "formula": "DIB = b1 + b2 * (DOB)",
            "bark_ratio": "BRATIO = DIB / DOB",
            "bounds": "0.80 < BRATIO < 0.99"
        }
        
        self.bounds = "0.80 < BRATIO < 0.99"
    
    def calculate_dib_from_dob(self, dob: float) -> float:
        """Calculate diameter inside bark from diameter outside bark.
        
        Uses the equation: DIB = b1 + b2 * DOB
        
        Args:
            dob: Diameter outside bark (inches)
            
        Returns:
            Diameter inside bark (inches)
        """
        if dob <= 0:
            return 0.0
        
        b1 = self.coefficients['b1']
        b2 = self.coefficients['b2']
        
        dib = b1 + b2 * dob
        
        # Ensure DIB is not negative and not greater than DOB
        dib = max(0.0, min(dib, dob))
        
        return dib
    
    def calculate_dob_from_dib(self, dib: float) -> float:
        """Calculate diameter outside bark from diameter inside bark.
        
        Solves the equation: DIB = b1 + b2 * DOB for DOB
        Therefore: DOB = (DIB - b1) / b2
        
        Args:
            dib: Diameter inside bark (inches)
            
        Returns:
            Diameter outside bark (inches)
        """
        if dib <= 0:
            return 0.0
        
        b1 = self.coefficients['b1']
        b2 = self.coefficients['b2']
        
        if b2 == 0:
            return dib  # Avoid division by zero
        
        dob = (dib - b1) / b2
        
        # Ensure DOB is not less than DIB
        dob = max(dib, dob)
        
        return dob
    
    def calculate_bark_ratio(self, dob: float) -> float:
        """Calculate bark ratio (DIB/DOB) for a given diameter outside bark.
        
        Args:
            dob: Diameter outside bark (inches)
            
        Returns:
            Bark ratio as proportion (0-1)
        """
        if dob <= 0:
            return 1.0
        
        dib = self.calculate_dib_from_dob(dob)
        bark_ratio = dib / dob
        
        # Apply bounds from FVS documentation: 0.80 < BRATIO < 0.99
        bark_ratio = max(0.80, min(0.99, bark_ratio))
        
        return bark_ratio
    
    def calculate_bark_thickness(self, dob: float) -> float:
        """Calculate bark thickness from diameter outside bark.
        
        Args:
            dob: Diameter outside bark (inches)
            
        Returns:
            Bark thickness (inches)
        """
        if dob <= 0:
            return 0.0
        
        dib = self.calculate_dib_from_dob(dob)
        bark_thickness = (dob - dib) / 2.0  # Radius difference
        
        return max(0.0, bark_thickness)
    
    def get_species_coefficients(self) -> Dict[str, float]:
        """Get the bark ratio coefficients for this species.
        
        Returns:
            Dictionary with b1 and b2 coefficients
        """
        return self.coefficients.copy()
    
    def validate_bark_ratio(self, bark_ratio: float) -> bool:
        """Validate that a bark ratio is within acceptable bounds.
        
        Args:
            bark_ratio: Bark ratio to validate (proportion)
            
        Returns:
            True if bark ratio is within bounds, False otherwise
        """
        return 0.80 <= bark_ratio <= 0.99
    
    def apply_bark_ratio_to_dbh(self, dbh_ob: float) -> float:
        """Apply bark ratio to convert DBH outside bark to inside bark.
        
        This is the most common use case in forest growth models.
        
        Args:
            dbh_ob: DBH outside bark (inches)
            
        Returns:
            DBH inside bark (inches)
        """
        return self.calculate_dib_from_dob(dbh_ob)
    
    def convert_dbh_ib_to_ob(self, dbh_ib: float) -> float:
        """Convert DBH inside bark to outside bark.
        
        Args:
            dbh_ib: DBH inside bark (inches)
            
        Returns:
            DBH outside bark (inches)
        """
        return self.calculate_dob_from_dib(dbh_ib)


def create_bark_ratio_model(species_code: str = "LP") -> BarkRatioModel:
    """Factory function to create a bark ratio model for a species.
    
    Args:
        species_code: Species code (e.g., "LP", "SP", "SA", etc.)
        
    Returns:
        BarkRatioModel instance
    """
    return BarkRatioModel(species_code)


def calculate_dib_from_dob(species_code: str, dob: float) -> float:
    """Standalone function to calculate DIB from DOB.
    
    Args:
        species_code: Species code
        dob: Diameter outside bark (inches)
        
    Returns:
        Diameter inside bark (inches)
    """
    model = create_bark_ratio_model(species_code)
    return model.calculate_dib_from_dob(dob)


def calculate_bark_ratio(species_code: str, dob: float) -> float:
    """Standalone function to calculate bark ratio.
    
    Args:
        species_code: Species code
        dob: Diameter outside bark (inches)
        
    Returns:
        Bark ratio as proportion
    """
    model = create_bark_ratio_model(species_code)
    return model.calculate_bark_ratio(dob)


def get_all_species_coefficients() -> Dict[str, Dict[str, float]]:
    """Get bark ratio coefficients for all species.

    Returns:
        Dictionary mapping species codes to their coefficients
    """
    bark_data = _get_bark_ratio_data()
    return bark_data.get('species_coefficients', {})


def compare_bark_ratios(species_codes: list, dob_range: list) -> Dict[str, Any]:
    """Compare bark ratios across species and diameter ranges.
    
    Args:
        species_codes: List of species codes to compare
        dob_range: List of DOB values to evaluate (inches)
        
    Returns:
        Dictionary with comparison results
    """
    results = {
        'dob': dob_range,
        'species_results': {}
    }
    
    for species in species_codes:
        model = create_bark_ratio_model(species)
        
        dib_values = []
        bark_ratios = []
        bark_thickness = []
        
        for dob in dob_range:
            dib = model.calculate_dib_from_dob(dob)
            ratio = model.calculate_bark_ratio(dob)
            thickness = model.calculate_bark_thickness(dob)
            
            dib_values.append(dib)
            bark_ratios.append(ratio)
            bark_thickness.append(thickness)
        
        results['species_results'][species] = {
            'dib': dib_values,
            'bark_ratio': bark_ratios,
            'bark_thickness': bark_thickness,
            'coefficients': model.get_species_coefficients()
        }
    
    return results


def validate_bark_ratio_implementation():
    """Validate the bark ratio implementation with test cases.
    
    Returns:
        Dictionary with validation results
    """
    test_cases = [
        {"species": "LP", "dob": 10.0, "expected_ratio_range": (0.85, 0.95)},
        {"species": "SA", "dob": 15.0, "expected_ratio_range": (0.80, 0.90)},
        {"species": "SP", "dob": 8.0, "expected_ratio_range": (0.85, 0.95)},
    ]
    
    results = {"passed": 0, "failed": 0, "details": []}
    
    for test in test_cases:
        model = create_bark_ratio_model(test["species"])
        calculated_ratio = model.calculate_bark_ratio(test["dob"])
        
        min_expected, max_expected = test["expected_ratio_range"]
        passed = min_expected <= calculated_ratio <= max_expected
        
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        results["details"].append({
            "species": test["species"],
            "dob": test["dob"],
            "calculated_ratio": calculated_ratio,
            "expected_range": test["expected_ratio_range"],
            "passed": passed
        })
    
    return results 
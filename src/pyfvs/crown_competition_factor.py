"""
Crown Competition Factor (CCF) calculation functions for FVS-Python.
Implements CCF equations from the FVS Southern variant for individual tree and stand-level calculations.
"""
from typing import Dict, Any, Optional, List
from .config_loader import load_coefficient_file


def _get_ccf_data() -> Dict[str, Any]:
    """Get CCF data using ConfigLoader (with caching)."""
    try:
        return load_coefficient_file('sn_crown_competition_factor.json')
    except FileNotFoundError:
        return {}


class CrownCompetitionFactorModel:
    """Crown Competition Factor model implementing FVS Southern variant equations."""
    
    def __init__(self):
        """Initialize the CCF model with parameters from configuration."""
        self._load_parameters()
    
    def _load_parameters(self):
        """Load CCF parameters from cached configuration."""
        # Use module-level cached data instead of loading from disk each time
        ccf_data = _get_ccf_data()

        if ccf_data:
            self.metadata = ccf_data.get('metadata', {})
            self.calculation_methods = ccf_data.get('calculation_methods', {})
            self.dependencies = ccf_data.get('dependencies', {})
            self.applications = ccf_data.get('applications', {})

            # Extract key parameters
            try:
                self.coefficient = ccf_data['calculation_methods']['individual_tree_ccf']['coefficient']['value']
            except (KeyError, TypeError):
                self.coefficient = 0.001803
            self.small_tree_ccf = 0.001  # Fixed value for DBH ≤ 0.1 inches
            self.dbh_threshold = 0.1     # DBH threshold for small trees
        else:
            # Fallback parameters if file not found
            self._load_fallback_parameters()
    
    def _load_fallback_parameters(self):
        """Load fallback parameters if CCF file not available."""
        self.coefficient = 0.001803
        self.small_tree_ccf = 0.001
        self.dbh_threshold = 0.1
        
        self.metadata = {
            "title": "Crown Competition Factor (CCF) for FVS Southern Variant",
            "description": "Crown competition factor calculation methods",
            "equations": {
                "4.5.1": "CCFt = 0.001803 * OCWt^2 (for DBH > 0.1), CCFt = 0.001 (for DBH ≤ 0.1)"
            }
        }
    
    def calculate_individual_ccf(self, dbh: float, open_crown_width: Optional[float] = None, 
                               species_code: str = "LP") -> float:
        """Calculate Crown Competition Factor for an individual tree.
        
        Uses equation 4.5.1: CCFt = 0.001803 * OCWt^2 (for DBH > 0.1)
                             CCFt = 0.001 (for DBH ≤ 0.1)
        
        Args:
            dbh: Diameter at breast height (inches)
            open_crown_width: Open-grown crown width (feet). If None, calculated from DBH.
            species_code: Species code for crown width calculation if OCW not provided
            
        Returns:
            Individual tree CCF value (percentage of acre covered)
        """
        if dbh <= 0:
            return 0.0
        
        # Check DBH threshold
        if dbh <= self.dbh_threshold:
            return self.small_tree_ccf
        
        # Calculate or use provided open crown width
        if open_crown_width is None:
            from .crown_width import calculate_open_crown_width
            open_crown_width = calculate_open_crown_width(species_code, dbh)
        
        # Apply equation 4.5.1
        ccf_individual = self.coefficient * (open_crown_width ** 2)
        
        return ccf_individual
    
    def calculate_stand_ccf(self, trees_data: List[Dict[str, Any]], 
                          species_code: str = "LP") -> float:
        """Calculate stand-level Crown Competition Factor.
        
        Stand CCF is the summation of individual tree CCFt values.
        
        Args:
            trees_data: List of dictionaries containing tree data with 'dbh' and optionally 'ocw'
            species_code: Default species code if not specified per tree
            
        Returns:
            Stand CCF value (sum of individual tree CCF values)
        """
        if not trees_data:
            return 0.0
        
        stand_ccf = 0.0
        
        for tree_data in trees_data:
            dbh = tree_data.get('dbh', 0.0)
            ocw = tree_data.get('ocw')  # Open crown width
            tree_species = tree_data.get('species', species_code)
            expansion_factor = tree_data.get('expansion_factor', 1.0)
            
            # Calculate individual tree CCF
            tree_ccf = self.calculate_individual_ccf(dbh, ocw, tree_species)
            
            # Apply expansion factor for plot-based data
            stand_ccf += tree_ccf * expansion_factor
        
        return stand_ccf
    
    def calculate_ccf_from_stand_object(self, stand) -> float:
        """Calculate stand CCF from a Stand object.
        
        Args:
            stand: Stand object with trees attribute
            
        Returns:
            Stand CCF value
        """
        if not hasattr(stand, 'trees') or not stand.trees:
            return 0.0
        
        trees_data = []
        for tree in stand.trees:
            tree_data = {
                'dbh': getattr(tree, 'dbh', 0.0),
                'species': getattr(tree, 'species', 'LP'),
                'expansion_factor': getattr(tree, 'expansion_factor', 1.0)
            }
            
            # Include open crown width if available
            if hasattr(tree, 'open_crown_width'):
                tree_data['ocw'] = tree.open_crown_width
            
            trees_data.append(tree_data)
        
        return self.calculate_stand_ccf(trees_data)
    
    def interpret_ccf_value(self, ccf: float) -> Dict[str, Any]:
        """Interpret CCF value according to FVS guidelines.
        
        Args:
            ccf: Crown Competition Factor value
            
        Returns:
            Dictionary with interpretation and management recommendations
        """
        interpretation = {
            'ccf_value': ccf,
            'theoretical_meaning': '',
            'density_assessment': '',
            'management_recommendation': '',
            'stocking_level': ''
        }
        
        if ccf < 100:
            interpretation.update({
                'theoretical_meaning': 'Tree crowns do not touch; gaps exist between crowns',
                'density_assessment': 'May indicate understocking',
                'management_recommendation': 'Consider regeneration or planting',
                'stocking_level': 'Low density'
            })
        elif ccf == 100:
            interpretation.update({
                'theoretical_meaning': 'Tree crowns just touch in an unthinned, evenly spaced stand',
                'density_assessment': 'Theoretical optimal spacing',
                'management_recommendation': 'Monitor for competition development',
                'stocking_level': 'Optimal theoretical density'
            })
        elif 100 < ccf <= 200:
            interpretation.update({
                'theoretical_meaning': 'Crown overlap and competition present',
                'density_assessment': 'Typical range for managed stands',
                'management_recommendation': 'Normal management practices apply',
                'stocking_level': 'Optimal density range'
            })
        else:  # ccf > 200
            interpretation.update({
                'theoretical_meaning': 'Significant crown overlap and intense competition',
                'density_assessment': 'May indicate overstocking',
                'management_recommendation': 'Consider thinning to reduce competition',
                'stocking_level': 'High density'
            })
        
        return interpretation
    
    def calculate_ccf_change_after_thinning(self, pre_thin_trees: List[Dict[str, Any]], 
                                          removed_trees: List[Dict[str, Any]], 
                                          species_code: str = "LP") -> Dict[str, float]:
        """Calculate CCF change after thinning operation.
        
        Args:
            pre_thin_trees: Tree data before thinning
            removed_trees: Tree data for removed trees
            species_code: Default species code
            
        Returns:
            Dictionary with pre-thin, removed, and post-thin CCF values
        """
        pre_thin_ccf = self.calculate_stand_ccf(pre_thin_trees, species_code)
        removed_ccf = self.calculate_stand_ccf(removed_trees, species_code)
        post_thin_ccf = pre_thin_ccf - removed_ccf
        
        return {
            'pre_thin_ccf': pre_thin_ccf,
            'removed_ccf': removed_ccf,
            'post_thin_ccf': post_thin_ccf,
            'ccf_reduction': removed_ccf,
            'ccf_reduction_percent': (removed_ccf / pre_thin_ccf * 100) if pre_thin_ccf > 0 else 0
        }
    
    def estimate_trees_per_acre_at_ccf(self, target_ccf: float, mean_dbh: float, 
                                     species_code: str = "LP") -> float:
        """Estimate trees per acre needed to achieve target CCF.
        
        Args:
            target_ccf: Target CCF value
            mean_dbh: Mean DBH of trees (inches)
            species_code: Species code for crown width calculation
            
        Returns:
            Estimated trees per acre
        """
        if mean_dbh <= self.dbh_threshold:
            individual_ccf = self.small_tree_ccf
        else:
            from .crown_width import calculate_open_crown_width
            ocw = calculate_open_crown_width(species_code, mean_dbh)
            individual_ccf = self.coefficient * (ocw ** 2)
        
        if individual_ccf <= 0:
            return 0.0
        
        return target_ccf / individual_ccf
    
    def get_ccf_parameters(self) -> Dict[str, Any]:
        """Get CCF calculation parameters.
        
        Returns:
            Dictionary with CCF parameters and metadata
        """
        return {
            'coefficient': self.coefficient,
            'small_tree_ccf': self.small_tree_ccf,
            'dbh_threshold': self.dbh_threshold,
            'equation': self.metadata.get('equations', {}).get('4.5.1', ''),
            'units': 'Percentage of acre covered by crown',
            'bounds': 'CCF ≥ 0, typically 0-400 for managed stands'
        }


def create_ccf_model() -> CrownCompetitionFactorModel:
    """Factory function to create a CCF model.
    
    Returns:
        CrownCompetitionFactorModel instance
    """
    return CrownCompetitionFactorModel()


def calculate_individual_ccf(dbh: float, open_crown_width: Optional[float] = None, 
                           species_code: str = "LP") -> float:
    """Standalone function to calculate individual tree CCF.
    
    Args:
        dbh: Diameter at breast height (inches)
        open_crown_width: Open-grown crown width (feet)
        species_code: Species code
        
    Returns:
        Individual tree CCF value
    """
    model = create_ccf_model()
    return model.calculate_individual_ccf(dbh, open_crown_width, species_code)


def calculate_stand_ccf(trees_data: List[Dict[str, Any]], species_code: str = "LP") -> float:
    """Standalone function to calculate stand CCF.
    
    Args:
        trees_data: List of tree data dictionaries
        species_code: Default species code
        
    Returns:
        Stand CCF value
    """
    model = create_ccf_model()
    return model.calculate_stand_ccf(trees_data, species_code)


def calculate_ccf_from_stand(stand) -> float:
    """Standalone function to calculate CCF from Stand object.
    
    Args:
        stand: Stand object
        
    Returns:
        Stand CCF value
    """
    model = create_ccf_model()
    return model.calculate_ccf_from_stand_object(stand)


def interpret_ccf(ccf: float) -> Dict[str, Any]:
    """Standalone function to interpret CCF value.
    
    Args:
        ccf: Crown Competition Factor value
        
    Returns:
        Dictionary with interpretation
    """
    model = create_ccf_model()
    return model.interpret_ccf_value(ccf)


def validate_ccf_implementation() -> Dict[str, Any]:
    """Validate the CCF implementation with test cases.
    
    Returns:
        Dictionary with validation results
    """
    model = create_ccf_model()
    
    test_cases = [
        {
            "description": "Small tree (DBH ≤ 0.1)",
            "dbh": 0.1,
            "expected_ccf": 0.001,
            "tolerance": 0.0001
        },
        {
            "description": "Medium tree (DBH = 10 inches)",
            "dbh": 10.0,
            "ocw": 15.0,  # Provided OCW
            "expected_ccf": 0.001803 * 15.0**2,  # 0.406
            "tolerance": 0.01
        },
        {
            "description": "Large tree (DBH = 20 inches)",
            "dbh": 20.0,
            "ocw": 25.0,  # Provided OCW
            "expected_ccf": 0.001803 * 25.0**2,  # 1.127
            "tolerance": 0.01
        }
    ]
    
    results = {"passed": 0, "failed": 0, "details": []}
    
    for test in test_cases:
        calculated_ccf = model.calculate_individual_ccf(
            test["dbh"], 
            test.get("ocw"), 
            "LP"
        )
        
        expected = test["expected_ccf"]
        tolerance = test["tolerance"]
        passed = abs(calculated_ccf - expected) <= tolerance
        
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        results["details"].append({
            "description": test["description"],
            "dbh": test["dbh"],
            "ocw": test.get("ocw"),
            "calculated_ccf": calculated_ccf,
            "expected_ccf": expected,
            "tolerance": tolerance,
            "passed": passed,
            "error": abs(calculated_ccf - expected)
        })
    
    # Test stand-level calculation
    stand_trees = [
        {"dbh": 10.0, "ocw": 15.0},
        {"dbh": 12.0, "ocw": 18.0},
        {"dbh": 8.0, "ocw": 12.0}
    ]
    
    expected_stand_ccf = (
        0.001803 * 15.0**2 +  # 0.406
        0.001803 * 18.0**2 +  # 0.583
        0.001803 * 12.0**2    # 0.259
    )  # Total: 1.248
    
    calculated_stand_ccf = model.calculate_stand_ccf(stand_trees, "LP")
    stand_passed = abs(calculated_stand_ccf - expected_stand_ccf) <= 0.01
    
    if stand_passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    results["details"].append({
        "description": "Stand-level CCF calculation",
        "trees": len(stand_trees),
        "calculated_stand_ccf": calculated_stand_ccf,
        "expected_stand_ccf": expected_stand_ccf,
        "passed": stand_passed,
        "error": abs(calculated_stand_ccf - expected_stand_ccf)
    })
    
    return results


def demonstrate_ccf_usage():
    """Demonstrate CCF module usage with examples."""
    print("Crown Competition Factor (CCF) Module Demonstration")
    print("=" * 55)
    
    model = create_ccf_model()
    
    # Example 1: Individual tree CCF
    print("\n1. Individual Tree CCF Calculation:")
    dbh = 10.0
    ccf_individual = model.calculate_individual_ccf(dbh, species_code="LP")
    print(f"   Tree with DBH = {dbh} inches")
    print(f"   Individual CCF = {ccf_individual:.3f}")
    
    # Example 2: Stand CCF
    print("\n2. Stand CCF Calculation:")
    trees = [
        {"dbh": 8.0}, {"dbh": 10.0}, {"dbh": 12.0}, 
        {"dbh": 14.0}, {"dbh": 16.0}
    ]
    stand_ccf = model.calculate_stand_ccf(trees, "LP")
    print(f"   Stand with {len(trees)} trees")
    print(f"   Stand CCF = {stand_ccf:.1f}")
    
    # Example 3: CCF interpretation
    print("\n3. CCF Interpretation:")
    interpretation = model.interpret_ccf_value(stand_ccf)
    print(f"   CCF Value: {interpretation['ccf_value']:.1f}")
    print(f"   Stocking Level: {interpretation['stocking_level']}")
    print(f"   Management Recommendation: {interpretation['management_recommendation']}")
    
    # Example 4: Validation
    print("\n4. Implementation Validation:")
    validation = validate_ccf_implementation()
    print(f"   Tests Passed: {validation['passed']}")
    print(f"   Tests Failed: {validation['failed']}")
    
    print("\nCCF Module demonstration completed successfully!")


if __name__ == "__main__":
    demonstrate_ccf_usage() 
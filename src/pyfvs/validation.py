"""
Parameter validation for FVS-Python growth models.
Ensures all inputs are within valid ranges based on FVS documentation.
"""
from typing import Dict, Any, Optional, Tuple


class ParameterValidator:
    """Validates parameters for FVS growth models."""
    
    # Parameter bounds based on FVS documentation
    BOUNDS = {
        'site_index': (20.0, 150.0),  # General range for site index
        'dbh': (0.1, 60.0),  # Diameter bounds in inches
        'height': (1.0, 200.0),  # Height bounds in feet
        'age': (0, 200),  # Age bounds in years
        'crown_ratio': (0.05, 0.95),  # Crown ratio as proportion
        'competition_factor': (0.0, 1.0),  # Competition factor normalized
        'basal_area': (0.0, 500.0),  # Basal area sq ft/acre
        'trees_per_acre': (1, 2000),  # Trees per acre
        'slope': (0.0, 1.0),  # Slope as proportion
        'aspect': (0.0, 6.284),  # Aspect in radians (0 to 2π)
        'rank': (0.0, 1.0),  # Tree rank in stand
        'relsdi': (0.0, 12.0),  # Relative SDI
        'pbal': (0.0, 500.0),  # Basal area in larger trees
        'time_step': (1, 10),  # Growth time step in years
    }
    
    # Species-specific site index bounds
    SPECIES_SI_BOUNDS = {
        'LP': (40.0, 125.0),  # Loblolly pine
        'SP': (40.0, 100.0),  # Shortleaf pine
        'SA': (40.0, 120.0),  # Slash pine
        'LL': (40.0, 100.0),  # Longleaf pine
        'WP': (30.0, 100.0),  # White pine
        'VP': (30.0, 90.0),   # Virginia pine
        'PP': (30.0, 80.0),   # Pitch pine
        'PD': (30.0, 80.0),   # Pond pine
        'TM': (30.0, 80.0),   # Table mountain pine
        'WO': (40.0, 100.0),  # White oak
        'RM': (40.0, 90.0),   # Red maple
        'YP': (50.0, 120.0),  # Yellow poplar
        'SU': (50.0, 110.0),  # Sweetgum
    }
    
    @classmethod
    def validate_parameter(cls, name: str, value: float, 
                         species_code: Optional[str] = None) -> float:
        """Validate and bound a single parameter.
        
        Args:
            name: Parameter name
            value: Parameter value
            species_code: Species code for species-specific bounds
            
        Returns:
            Bounded parameter value
            
        Raises:
            ValueError: If parameter name is unknown
        """
        # Special handling for site index with species-specific bounds
        if name == 'site_index' and species_code and species_code in cls.SPECIES_SI_BOUNDS:
            min_val, max_val = cls.SPECIES_SI_BOUNDS[species_code]
        elif name in cls.BOUNDS:
            min_val, max_val = cls.BOUNDS[name]
        else:
            # Unknown parameter, return as-is
            return value
        
        # Apply bounds
        bounded_value = max(min_val, min(max_val, value))
        
        # Warn if value was bounded (disabled for now to reduce noise)
        # if bounded_value != value:
        #     print(f"Warning: {name} value {value} was bounded to {bounded_value}")
        
        return bounded_value
    
    @classmethod
    def validate_tree_parameters(cls, dbh: float, height: float, age: int,
                               crown_ratio: float, species_code: str) -> Dict[str, Any]:
        """Validate all tree parameters.
        
        Args:
            dbh: Diameter at breast height (inches)
            height: Total height (feet)
            age: Tree age (years)
            crown_ratio: Crown ratio (proportion)
            species_code: Species code
            
        Returns:
            Dictionary of validated parameters
        """
        return {
            'dbh': cls.validate_parameter('dbh', dbh),
            'height': cls.validate_parameter('height', height),
            'age': int(cls.validate_parameter('age', age)),
            'crown_ratio': cls.validate_parameter('crown_ratio', crown_ratio),
            'species_code': species_code
        }
    
    @classmethod
    def validate_growth_parameters(cls, site_index: float, competition_factor: float,
                                 ba: float, pbal: float, rank: float, relsdi: float,
                                 slope: float, aspect: float, time_step: int,
                                 species_code: Optional[str] = None) -> Dict[str, Any]:
        """Validate all growth model parameters.
        
        Args:
            site_index: Site index (base age 25) in feet
            competition_factor: Competition factor (0-1)
            ba: Stand basal area (sq ft/acre)
            pbal: Basal area in larger trees (sq ft/acre)
            rank: Tree rank in diameter distribution (0-1)
            relsdi: Relative stand density index (0-12)
            slope: Ground slope (proportion)
            aspect: Aspect in radians
            time_step: Growth period in years
            species_code: Species code for site index validation
            
        Returns:
            Dictionary of validated parameters
        """
        return {
            'site_index': cls.validate_parameter('site_index', site_index, species_code),
            'competition_factor': cls.validate_parameter('competition_factor', competition_factor),
            'ba': cls.validate_parameter('basal_area', ba),
            'pbal': cls.validate_parameter('pbal', pbal),
            'rank': cls.validate_parameter('rank', rank),
            'relsdi': cls.validate_parameter('relsdi', relsdi),
            'slope': cls.validate_parameter('slope', slope),
            'aspect': cls.validate_parameter('aspect', aspect),
            'time_step': int(cls.validate_parameter('time_step', time_step))
        }
    
    @classmethod
    def validate_stand_parameters(cls, trees_per_acre: int, site_index: float,
                                species_code: Optional[str] = None) -> Dict[str, Any]:
        """Validate stand initialization parameters.
        
        Args:
            trees_per_acre: Number of trees per acre
            site_index: Site index (base age 25) in feet
            species_code: Species code
            
        Returns:
            Dictionary of validated parameters
        """
        return {
            'trees_per_acre': int(cls.validate_parameter('trees_per_acre', trees_per_acre)),
            'site_index': cls.validate_parameter('site_index', site_index, species_code)
        }
    
    @classmethod
    def check_height_dbh_relationship(cls, dbh: float, height: float) -> bool:
        """Check if height-DBH relationship is reasonable.
        
        Args:
            dbh: Diameter at breast height (inches)
            height: Total height (feet)
            
        Returns:
            True if relationship is reasonable
        """
        if dbh <= 0 or height <= 4.5:
            return False
        
        # Check height/DBH ratio is reasonable (typically 5-15 for mature trees)
        ratio = height / dbh
        return 2.0 <= ratio <= 20.0


def validate_and_bound(value: float, min_val: float, max_val: float, 
                      param_name: str = "parameter") -> float:
    """Simple validation function for direct use.
    
    Args:
        value: Value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        param_name: Name of parameter for warning message
        
    Returns:
        Bounded value
    """
    bounded = max(min_val, min(max_val, value))
    if bounded != value:
        print(f"Warning: {param_name} {value} bounded to {bounded}")
    return bounded
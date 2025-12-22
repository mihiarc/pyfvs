"""
Large tree height growth functions for FVS-Python.
Implements the large tree height growth model from the FVS Southern variant
following the approach of Wensel and others (1987).
"""
import json
import math
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from .config_loader import get_config_loader


class LargeTreeHeightGrowthModel:
    """Large tree height growth model implementing FVS Southern variant equations."""
    
    def __init__(self, species_code: str = "LP"):
        """Initialize with species-specific parameters.
        
        Args:
            species_code: Species code (e.g., "LP", "SP", "SA", etc.)
        """
        self.species_code = species_code
        self._load_parameters()
    
    def _load_parameters(self):
        """Load large tree height growth parameters from configuration."""
        from .config_loader import get_config_loader
        
        try:
            loader = get_config_loader()
            
            # Load height growth methodology from the main JSON file
            height_growth_file = loader.cfg_dir / "sn_large_tree_height_growth.json"
            self.methodology = loader._load_config_file(height_growth_file)
        except Exception:
            self._load_fallback_methodology()
        
        try:
            # Load diameter growth coefficients (used for potential height growth calculation)
            coefficients_file = loader.cfg_dir / "sn_large_tree_height_growth_coefficients.json"
            coeff_data = loader._load_config_file(coefficients_file)
            
            if self.species_code in coeff_data['coefficients']:
                self.diameter_coefficients = coeff_data['coefficients'][self.species_code]
            else:
                # Fallback to LP parameters if species not found
                self.diameter_coefficients = coeff_data['coefficients']['LP']
                
            self.equation_info = coeff_data['equation']
            self.variable_definitions = coeff_data['variable_definitions']
        except Exception:
            self._load_fallback_coefficients()
        
        # Load shade tolerance parameters
        self._load_shade_tolerance_parameters()
        
        # Load site index ranges and validation
        self._load_site_index_ranges()
    
    def _load_fallback_methodology(self):
        """Load fallback methodology if main file not available."""
        self.methodology = {
            "section": "4.7.2",
            "title": "Large Tree Height Growth",
            "equations": {
                "4.7.2.1": {
                    "formula": "HTG = POTHTG * (0.25 * HGMDCR + 0.75 * HGMDRH)",
                    "description": "Main height growth equation"
                },
                "4.7.2.2": {
                    "formula": "HGMDCR = 100 * CR^3.0 * exp(-5.0*CR)",
                    "description": "Crown ratio modifier using Hoerl's Special Function"
                }
            }
        }
    
    def _load_fallback_coefficients(self):
        """Load fallback coefficients if file not available."""
        # Default LP parameters
        self.diameter_coefficients = {
            "b1": 0.222214,
            "b2": 1.16304,
            "b3": -0.000863,
            "b4": 0.028483,
            "b5": 0.006935,
            "b6": 0.005018,
            "b7": -0.004184,
            "b8": -0.759347,
            "b9": 0.18536,
            "b10": 0.0,
            "b11": -0.072842
        }
        
        self.equation_info = "ln(DDS) = b1 + (b2 * ln(DBH)) + (b3 * DBH^2) + (b4 * ln(CR)) + (b5 * RELHT) + (b6 * SI) + (b7 * BA) + (b8 * PBAL) + (b9 * SLOPE) + (b10 * cos(ASP) * SLOPE) + (b11 * sin(ASP) * SLOPE)"
    
    def _load_shade_tolerance_parameters(self):
        """Load shade tolerance parameters from the methodology file."""
        if hasattr(self, 'methodology') and 'tables' in self.methodology:
            # Load shade tolerance coefficients from table 4.7.2.1
            tolerance_table = self.methodology['tables']['4.7.2.1']['data']
            self.shade_tolerance_coeffs = {}
            for row in tolerance_table:
                self.shade_tolerance_coeffs[row['shade_tolerance']] = {
                    'RHR': row['RHR'],
                    'RHYXS': row['RHYXS'],
                    'RHM': row['RHM'],
                    'RHB': row['RHB'],
                    'RHXS': row['RHXS'],
                    'RHK': row['RHK']
                }
            
            # Load species shade tolerance mapping from table 4.7.2.2
            species_table = self.methodology['tables']['4.7.2.2']['data']
            self.species_shade_tolerance = {}
            for row in species_table:
                self.species_shade_tolerance[row['species_code']] = row['shade_tolerance']
        else:
            self._load_fallback_shade_tolerance()
    
    def _load_fallback_shade_tolerance(self):
        """Load fallback shade tolerance parameters."""
        # Default shade tolerance coefficients
        self.shade_tolerance_coeffs = {
            'Intolerant': {
                'RHR': 13, 'RHYXS': 0.05, 'RHM': 1.1, 
                'RHB': -1.60, 'RHXS': 0, 'RHK': 1
            },
            'Tolerant': {
                'RHR': 16, 'RHYXS': 0.15, 'RHM': 1.1,
                'RHB': -1.20, 'RHXS': 0, 'RHK': 1
            }
        }
        
        # Default species mapping
        self.species_shade_tolerance = {
            'LP': 'Intolerant',
            'SP': 'Intolerant', 
            'SA': 'Intolerant',
            'LL': 'Intolerant'
        }
    
    def _load_site_index_ranges(self):
        """Load site index ranges and validation from configuration."""
        from .config_loader import get_config_loader
        
        try:
            loader = get_config_loader()
            site_index_file = loader.cfg_dir / "sn_relative_site_index.json"
            site_data = loader._load_config_file(site_index_file)
            
            # Get species-specific site index range
            species_ranges = site_data.get('species_site_index_ranges', {})
            if self.species_code in species_ranges:
                self.site_index_range = species_ranges[self.species_code]
            else:
                # Default range for LP
                self.site_index_range = {"si_min": 40, "si_max": 125}
        except Exception:
            self.site_index_range = {"si_min": 40, "si_max": 125}
    
    def _validate_site_index(self, site_index: float) -> float:
        """Validate and bound site index within species-specific ranges.
        
        Args:
            site_index: Input site index
            
        Returns:
            Validated site index within bounds
        """
        if not hasattr(self, 'site_index_range'):
            self._load_site_index_ranges()
        
        si_min = self.site_index_range.get('si_min', 40)
        si_max = self.site_index_range.get('si_max', 125)
        
        return max(si_min, min(si_max, site_index))
    
    def calculate_potential_height_growth(self, dbh: float, crown_ratio: float, 
                                        relative_height: float, site_index: float,
                                        basal_area: float, pbal: float, 
                                        slope: float = 0.0, aspect: float = 0.0,
                                        tree_age: Optional[float] = None,
                                        tree_height: Optional[float] = None) -> float:
        """Calculate potential height growth using the small-tree height increment model.
        
        This implements the methodology described in section 4.6.1 using the Chapman-Richards
        functional form as referenced in the large tree height growth methodology.
        
        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio as proportion (0-1)
            relative_height: Tree height relative to top 40 trees
            site_index: Site index (base age 25) in feet
            basal_area: Stand basal area (sq ft/acre)
            pbal: Plot basal area larger (sq ft/acre)
            slope: Ground slope (proportion)
            aspect: Aspect in radians
            tree_age: Tree age (years) - if not provided, estimated from height
            tree_height: Current tree height (feet) - if not provided, estimated from DBH
            
        Returns:
            Potential height growth (feet)
        """
        # Validate and bound site index
        site_index = self._validate_site_index(site_index)
        
        # Load small tree height growth coefficients
        small_tree_coeffs = self._get_small_tree_coefficients()
        
        # Estimate tree height if not provided
        if tree_height is None:
            tree_height = self._estimate_height_from_dbh(dbh)
        
        # Estimate tree age if not provided
        if tree_age is None:
            tree_age = self._estimate_age_from_height(tree_height, site_index, small_tree_coeffs)
        
        # Bound tree age to reasonable range
        # Allow ages as young as 5 for trees in the transition zone (DBH 1-3")
        # Very young trees won't use the large tree model anyway
        tree_age = max(5.0, min(150.0, tree_age))
        
        # Calculate potential height using Chapman-Richards equation
        # POTHT = c1 * SI^c2 * (1 - exp(-c3 * AGET))^(c4 * SI^c5)
        c1, c2, c3, c4, c5 = (small_tree_coeffs['c1'], small_tree_coeffs['c2'],
                              small_tree_coeffs['c3'], small_tree_coeffs['c4'],
                              small_tree_coeffs['c5'])

        # Site index base age for southern pines
        base_age = 25

        def _raw_chapman_richards(age: float) -> float:
            """Calculate unscaled Chapman-Richards height."""
            if age <= 0:
                return 1.0
            return c1 * (site_index ** c2) * (1.0 - math.exp(c3 * age)) ** (c4 * (site_index ** c5))

        try:
            # Calculate scaling factor to ensure Height(base_age=25) = SI
            # This is critical for consistency with the small tree model
            raw_height_at_base = _raw_chapman_richards(base_age)
            if raw_height_at_base > 0:
                scale_factor = site_index / raw_height_at_base
            else:
                scale_factor = 1.0

            # Note: tree_age is the age AFTER the growth period (consistent with
            # how grow() increments age before calling growth functions).
            # So we calculate growth TO current age FROM previous age (5 years ago).
            # This matches the small tree model's approach.
            previous_age = max(0, tree_age - 5)

            # Height at previous age (start of growth period)
            previous_potht = _raw_chapman_richards(previous_age) * scale_factor

            # Height at current age (end of growth period, scaled)
            current_potht = _raw_chapman_richards(tree_age) * scale_factor

            # Potential height growth = current - previous (growth TO this age)
            potential_height_growth = current_potht - previous_potht
            
            # Apply constraints based on tree size and site quality
            # Large trees should have slower height growth
            if dbh > 15.0:
                # Reduce growth for very large trees
                size_factor = max(0.3, 1.0 - (dbh - 15.0) * 0.02)
                potential_height_growth *= size_factor
            
            # Apply site index constraint - higher sites shouldn't have excessive growth
            if site_index > 80.0:
                # Moderate growth on very high sites
                site_factor = max(0.7, 1.0 - (site_index - 80.0) * 0.005)
                potential_height_growth *= site_factor
            
            # Bound potential height growth to reasonable range
            # Young trees on good sites can grow 10-15 ft per 5-year period
            # Mature trees typically grow 2-5 ft per 5-year period
            # Maximum based on SI (higher SI = higher max growth)
            max_growth = max(5.0, site_index * 0.20)  # e.g., SI=55 -> max 11 ft/5yr
            potential_height_growth = max(0.1, min(max_growth, potential_height_growth))
            
        except (ValueError, OverflowError, ZeroDivisionError):
            # Fallback calculation if Chapman-Richards fails
            potential_height_growth = self._fallback_potential_height_growth(dbh, site_index, tree_age)
        
        return max(0.0, potential_height_growth)
    
    def _fallback_potential_height_growth(self, dbh: float, site_index: float, tree_age: float) -> float:
        """Fallback calculation for potential height growth when Chapman-Richards fails.
        
        Args:
            dbh: Diameter at breast height (inches)
            site_index: Site index (feet)
            tree_age: Tree age (years)
            
        Returns:
            Fallback potential height growth (feet)
        """
        # Simple empirical relationship based on site index and tree size
        base_growth = (site_index / 70.0) * 1.5  # Base growth relative to SI=70
        
        # Age factor - older trees grow slower
        age_factor = max(0.2, 1.0 - (tree_age - 20.0) * 0.01)
        
        # Size factor - larger trees grow slower in height
        size_factor = max(0.3, 1.0 - (dbh - 8.0) * 0.03)
        
        fallback_growth = base_growth * age_factor * size_factor
        
        # Bound to reasonable range
        return max(0.1, min(3.0, fallback_growth))
    
    def _get_small_tree_coefficients(self) -> Dict[str, float]:
        """Get small tree height growth coefficients for the species.
        
        Returns:
            Dictionary with Chapman-Richards coefficients
        """
        from .config_loader import get_config_loader
        
        try:
            # Try to load from small tree height growth configuration
            loader = get_config_loader()
            small_tree_file = loader.cfg_dir / "sn_small_tree_height_growth.json"
            small_tree_data = loader._load_config_file(small_tree_file)
            
            if 'nc128_height_growth_coefficients' in small_tree_data:
                coeffs = small_tree_data['nc128_height_growth_coefficients']
                if self.species_code in coeffs:
                    return coeffs[self.species_code]
                else:
                    # Fallback to LP if species not found
                    return coeffs.get('LP', self._get_fallback_small_tree_coefficients())
        except Exception:
            pass
        
        # Fallback coefficients if file not available
        return self._get_fallback_small_tree_coefficients()
    
    def _get_fallback_small_tree_coefficients(self) -> Dict[str, float]:
        """Get fallback small tree coefficients.
        
        Returns:
            Dictionary with default LP coefficients
        """
        return {
            'c1': 1.421,
            'c2': 0.9947,
            'c3': -0.0269,
            'c4': 1.1344,
            'c5': -0.0109
        }
    
    def _estimate_height_from_dbh(self, dbh: float) -> float:
        """Estimate tree height from DBH using Curtis-Arney relationship.
        
        Args:
            dbh: Diameter at breast height (inches)
            
        Returns:
            Estimated height (feet)
        """
        # Curtis-Arney height-diameter relationship for large trees
        # height = 4.5 + p2 * exp(-p3 * DBH^p4)
        p2 = 243.860648
        p3 = 4.28460566
        p4 = -0.47130185
        
        height = 4.5 + p2 * math.exp(-p3 * (dbh ** p4))
        return max(4.5, height)
    
    def _estimate_age_from_height(self, height: float, site_index: float, 
                                 coeffs: Dict[str, float]) -> float:
        """Estimate tree age from height using inverse Chapman-Richards.
        
        Args:
            height: Tree height (feet)
            site_index: Site index (base age 25) in feet
            coeffs: Chapman-Richards coefficients
            
        Returns:
            Estimated age (years)
        """
        c1, c2, c3, c4, c5 = coeffs['c1'], coeffs['c2'], coeffs['c3'], coeffs['c4'], coeffs['c5']
        
        try:
            # Inverse Chapman-Richards: AGET = 1/c3 * ln(1 - (HT / (c1 * SI^c2))^(1 / (c4 * SI^c5)))
            ratio = height / (c1 * (site_index ** c2))
            if ratio >= 1.0:
                return 50.0  # Default age for mature trees
            
            inner_term = ratio ** (1.0 / (c4 * (site_index ** c5)))
            if inner_term >= 1.0:
                return 50.0
            
            age = (1.0 / c3) * math.log(1.0 - inner_term)
            return max(5.0, min(200.0, age))  # Bound age between 5 and 200 years
            
        except (ValueError, ZeroDivisionError, OverflowError):
            # Fallback age estimation
            return max(10.0, height * 0.5)  # Rough estimate: 0.5 years per foot of height
    
    def calculate_crown_ratio_modifier(self, crown_ratio: float) -> float:
        """Calculate crown ratio modifier using Hoerl's Special Function.

        Equation 4.7.2.2: HGMDCR = CRA * CR^CRB * exp(CRC * CR)

        From official FVS Fortran source (htgf.f):
            CRA = 100.0, CRB = 3.0, CRC = -5.0
            IF (HGMDCR .GT. 1.0) HGMDCR = 1.0

        Args:
            crown_ratio: Crown ratio as proportion (0-1)

        Returns:
            Crown ratio modifier (bounded to 1.0 max)
        """
        # Validate crown ratio bounds (from config: 0.05 < CR < 0.95)
        crown_ratio = max(0.05, min(0.95, crown_ratio))

        if crown_ratio <= 0:
            return 0.0

        # Apply Hoerl's Special Function per official FVS Fortran source
        # HGMDCR = CRA * CR^CRB * exp(CRC * CR)
        # where CRA=100, CRB=3, CRC=-5
        cra = 100.0
        crb = 3.0
        crc = -5.0

        hgmdcr = cra * (crown_ratio ** crb) * math.exp(crc * crown_ratio)

        # Bound to maximum of 1.0 as per FVS Fortran: IF (HGMDCR .GT. 1.0) HGMDCR = 1.0
        hgmdcr = min(hgmdcr, 1.0)

        return hgmdcr
    
    def calculate_relative_height_modifier(self, relative_height: float, 
                                         species_code: Optional[str] = None) -> float:
        """Calculate relative height modifier using Generalized Chapman-Richards function.
        
        Equations 4.7.2.3 - 4.7.2.7
        
        Args:
            relative_height: Tree height relative to top 40 trees in stand
            species_code: Species code for shade tolerance lookup
            
        Returns:
            Relative height modifier (0.0 to 1.0)
        """
        if species_code is None:
            species_code = self.species_code
        
        # Get shade tolerance for species
        shade_tolerance = self.species_shade_tolerance.get(species_code, 'Intolerant')
        coeffs = self.shade_tolerance_coeffs.get(shade_tolerance, 
                                                self.shade_tolerance_coeffs['Intolerant'])
        
        # Extract coefficients
        rhr = coeffs['RHR']
        rhyxs = coeffs['RHYXS']
        rhm = coeffs['RHM']
        rhb = coeffs['RHB']
        rhxs = coeffs['RHXS']
        rhk = coeffs['RHK']
        
        # Calculate intermediate factors (equations 4.7.2.3 - 4.7.2.6)
        try:
            # Equation 4.7.2.3: FCTRKX = ((RHK / RHYXS)^(RHM – 1)) – 1
            fctrkx = ((rhk / rhyxs) ** (rhm - 1)) - 1
            
            # Equation 4.7.2.4: FCTRRB = (-1.0 * RHR) / (1 – RHB)
            fctrrb = (-1.0 * rhr) / (1 - rhb)
            
            # Equation 4.7.2.5: FCTRXB = RELHT^ (1 – RHB) – RHXS^ (1 – RHB)
            fctrxb = (relative_height ** (1 - rhb)) - (rhxs ** (1 - rhb))
            
            # Equation 4.7.2.6: FCTRM = 1 / (1 – RHM)
            fctrm = 1 / (1 - rhm)
            
            # Equation 4.7.2.7: HGMDRH = RHK * (1 + FCTRKX * exp(FCTRRB*FCTRXB))^FCTRM
            hgmdrh = rhk * ((1 + fctrkx * math.exp(fctrrb * fctrxb)) ** fctrm)
            
            # Bound between 0.0 and 1.0
            hgmdrh = max(0.0, min(1.0, hgmdrh))
            
        except (ZeroDivisionError, OverflowError, ValueError):
            # Handle edge cases with fallback value
            hgmdrh = 0.5
        
        return hgmdrh
    
    def calculate_height_growth(self, dbh: float, crown_ratio: float, 
                              relative_height: float, site_index: float,
                              basal_area: float, pbal: float, 
                              slope: float = 0.0, aspect: float = 0.0,
                              species_code: Optional[str] = None,
                              tree_age: Optional[float] = None,
                              tree_height: Optional[float] = None) -> float:
        """Calculate periodic height growth for large trees.
        
        Main equation 4.7.2.1: HTG = POTHTG * (0.25 * HGMDCR + 0.75 * HGMDRH)
        
        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio as proportion (0-1)
            relative_height: Tree height relative to top 40 trees
            site_index: Site index (base age 25) in feet
            basal_area: Stand basal area (sq ft/acre)
            pbal: Plot basal area larger (sq ft/acre)
            slope: Ground slope (proportion)
            aspect: Aspect in radians
            species_code: Species code for shade tolerance
            tree_age: Tree age (years) - if not provided, estimated from height
            tree_height: Current tree height (feet) - if not provided, estimated from DBH
            
        Returns:
            Periodic height growth (feet)
        """
        if species_code is None:
            species_code = self.species_code
        
        # Calculate potential height growth
        pothtg = self.calculate_potential_height_growth(
            dbh, crown_ratio, relative_height, site_index,
            basal_area, pbal, slope, aspect, tree_age, tree_height
        )
        
        # Calculate crown ratio modifier
        hgmdcr = self.calculate_crown_ratio_modifier(crown_ratio)
        
        # Calculate relative height modifier
        hgmdrh = self.calculate_relative_height_modifier(relative_height, species_code)
        
        # Apply main equation 4.7.2.1
        htg = pothtg * (0.25 * hgmdcr + 0.75 * hgmdrh)
        
        return max(0.0, htg)
    
    def get_species_shade_tolerance(self, species_code: Optional[str] = None) -> str:
        """Get shade tolerance classification for a species.
        
        Args:
            species_code: Species code
            
        Returns:
            Shade tolerance classification
        """
        if species_code is None:
            species_code = self.species_code
        
        return self.species_shade_tolerance.get(species_code, 'Intolerant')
    
    def get_shade_tolerance_coefficients(self, shade_tolerance: str) -> Dict[str, float]:
        """Get shade tolerance coefficients for a tolerance class.
        
        Args:
            shade_tolerance: Shade tolerance classification
            
        Returns:
            Dictionary with shade tolerance coefficients
        """
        return self.shade_tolerance_coeffs.get(shade_tolerance, 
                                             self.shade_tolerance_coeffs['Intolerant']).copy()
    
    def get_model_parameters(self) -> Dict[str, Any]:
        """Get model parameters and metadata.
        
        Returns:
            Dictionary with model parameters
        """
        return {
            'species_code': self.species_code,
            'methodology': self.methodology.get('methodology', {}),
            'equations': self.methodology.get('equations', {}),
            'diameter_coefficients': self.diameter_coefficients.copy(),
            'shade_tolerance': self.get_species_shade_tolerance(),
            'shade_tolerance_coeffs': self.get_shade_tolerance_coefficients(
                self.get_species_shade_tolerance()
            )
        }


def create_large_tree_height_growth_model(species_code: str = "LP") -> LargeTreeHeightGrowthModel:
    """Factory function to create a large tree height growth model.
    
    Args:
        species_code: Species code (e.g., "LP", "SP", "SA", etc.)
        
    Returns:
        LargeTreeHeightGrowthModel instance
    """
    return LargeTreeHeightGrowthModel(species_code)


def calculate_large_tree_height_growth(species_code: str, dbh: float, crown_ratio: float,
                                     relative_height: float, site_index: float,
                                     basal_area: float, pbal: float,
                                     slope: float = 0.0, aspect: float = 0.0,
                                     tree_age: Optional[float] = None,
                                     tree_height: Optional[float] = None) -> float:
    """Standalone function to calculate large tree height growth.
    
    Args:
        species_code: Species code
        dbh: Diameter at breast height (inches)
        crown_ratio: Crown ratio as proportion (0-1)
        relative_height: Tree height relative to top 40 trees
        site_index: Site index (base age 25) in feet
        basal_area: Stand basal area (sq ft/acre)
        pbal: Plot basal area larger (sq ft/acre)
        slope: Ground slope (proportion)
        aspect: Aspect in radians
        tree_age: Tree age (years) - if not provided, estimated from height
        tree_height: Current tree height (feet) - if not provided, estimated from DBH
        
    Returns:
        Periodic height growth (feet)
    """
    model = create_large_tree_height_growth_model(species_code)
    return model.calculate_height_growth(
        dbh, crown_ratio, relative_height, site_index,
        basal_area, pbal, slope, aspect, species_code, tree_age, tree_height
    )


def calculate_crown_ratio_modifier(crown_ratio: float) -> float:
    """Standalone function to calculate crown ratio modifier.
    
    Args:
        crown_ratio: Crown ratio as proportion (0-1)
        
    Returns:
        Crown ratio modifier
    """
    model = create_large_tree_height_growth_model()
    return model.calculate_crown_ratio_modifier(crown_ratio)


def calculate_relative_height_modifier(relative_height: float, species_code: str = "LP") -> float:
    """Standalone function to calculate relative height modifier.
    
    Args:
        relative_height: Tree height relative to top 40 trees
        species_code: Species code
        
    Returns:
        Relative height modifier
    """
    model = create_large_tree_height_growth_model(species_code)
    return model.calculate_relative_height_modifier(relative_height, species_code)


def validate_large_tree_height_growth_implementation() -> Dict[str, Any]:
    """Validate the large tree height growth implementation with test cases.
    
    Returns:
        Dictionary with validation results
    """
    test_cases = [
        {
            "description": "Typical large tree - LP on average site",
            "species": "LP",
            "dbh": 10.0,
            "crown_ratio": 0.6,
            "relative_height": 0.8,
            "site_index": 70.0,  # Average site for LP (range 40-125)
            "basal_area": 120.0,
            "pbal": 60.0,
            "expected_range": (0.5, 3.0)  # Expected height growth range
        },
        {
            "description": "Small crown ratio - LP with poor crown",
            "species": "LP", 
            "dbh": 12.0,
            "crown_ratio": 0.3,  # Poor crown ratio
            "relative_height": 0.7,
            "site_index": 70.0,
            "basal_area": 120.0,
            "pbal": 60.0,
            "expected_range": (0.2, 2.0)
        },
        {
            "description": "High site index - LP on excellent site",
            "species": "LP",
            "dbh": 10.0,
            "crown_ratio": 0.6,
            "relative_height": 0.8,
            "site_index": 90.0,  # High but within LP range (40-125)
            "basal_area": 120.0,
            "pbal": 60.0,
            "expected_range": (0.8, 4.0)
        },
        {
            "description": "Large tree - LP mature tree",
            "species": "LP",
            "dbh": 18.0,  # Large tree
            "crown_ratio": 0.5,
            "relative_height": 0.9,  # Dominant tree
            "site_index": 80.0,
            "basal_area": 150.0,
            "pbal": 40.0,
            "expected_range": (0.3, 2.5)  # Slower growth for large trees
        }
    ]
    
    results = {"passed": 0, "failed": 0, "details": []}
    
    for test in test_cases:
        model = create_large_tree_height_growth_model(test["species"])
        
        calculated_growth = model.calculate_height_growth(
            test["dbh"], test["crown_ratio"], test["relative_height"],
            test["site_index"], test["basal_area"], test["pbal"]
        )
        
        min_expected, max_expected = test["expected_range"]
        passed = min_expected <= calculated_growth <= max_expected
        
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        results["details"].append({
            "description": test["description"],
            "species": test["species"],
            "parameters": {
                "dbh": test["dbh"],
                "crown_ratio": test["crown_ratio"],
                "relative_height": test["relative_height"],
                "site_index": test["site_index"]
            },
            "calculated_growth": calculated_growth,
            "expected_range": test["expected_range"],
            "passed": passed
        })
    
    # Test crown ratio modifier function
    # With correct FVS equation: HGMDCR = 100 * CR^3 * exp(-5*CR), capped at 1.0
    # CR=0.4: 100 * 0.064 * 0.135 = 0.867
    # CR=0.5: 100 * 0.125 * 0.082 = 1.025 → capped to 1.0
    # CR=0.6: 100 * 0.216 * 0.050 = 1.079 → capped to 1.0
    # CR=0.7: 100 * 0.343 * 0.030 = 1.031 → capped to 1.0
    cr_test_cases = [
        {"crown_ratio": 0.4, "expected_range": (0.80, 0.95)},   # Below peak, not capped
        {"crown_ratio": 0.5, "expected_range": (0.95, 1.01)},   # Near/at cap
        {"crown_ratio": 0.6, "expected_range": (0.95, 1.01)},   # At cap (peak is ~0.55)
        {"crown_ratio": 0.7, "expected_range": (0.95, 1.01)}    # At cap
    ]
    
    for test in cr_test_cases:
        calculated_modifier = calculate_crown_ratio_modifier(test["crown_ratio"])
        min_expected, max_expected = test["expected_range"]
        passed = min_expected <= calculated_modifier <= max_expected
        
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        results["details"].append({
            "description": f"Crown ratio modifier for CR={test['crown_ratio']}",
            "crown_ratio": test["crown_ratio"],
            "calculated_modifier": calculated_modifier,
            "expected_range": test["expected_range"],
            "passed": passed
        })
    
    return results


def demonstrate_large_tree_height_growth():
    """Demonstrate large tree height growth module usage."""
    print("Large Tree Height Growth Module Demonstration")
    print("=" * 50)
    
    model = create_large_tree_height_growth_model("LP")
    
    # Example 1: Basic height growth calculation
    print("\n1. Basic Height Growth Calculation:")
    dbh = 10.0
    crown_ratio = 0.6
    relative_height = 0.8
    site_index = 70.0
    basal_area = 120.0
    pbal = 60.0
    
    height_growth = model.calculate_height_growth(
        dbh, crown_ratio, relative_height, site_index, basal_area, pbal
    )
    
    print(f"   Tree: DBH={dbh}\", CR={crown_ratio}, RelHt={relative_height}")
    print(f"   Stand: SI={site_index}, BA={basal_area}, PBAL={pbal}")
    print(f"   Height Growth = {height_growth:.2f} feet")
    
    # Example 2: Crown ratio modifier
    print("\n2. Crown Ratio Modifier:")
    for cr in [0.4, 0.5, 0.6, 0.7, 0.8]:
        modifier = model.calculate_crown_ratio_modifier(cr)
        print(f"   CR = {cr:.1f} → Modifier = {modifier:.3f}")
    
    # Example 3: Relative height modifier by species
    print("\n3. Relative Height Modifier by Species:")
    species_list = ["LP", "SP", "SA"]
    for species in species_list:
        model_sp = create_large_tree_height_growth_model(species)
        modifier = model_sp.calculate_relative_height_modifier(0.7, species)
        tolerance = model_sp.get_species_shade_tolerance(species)
        print(f"   {species} ({tolerance}): RelHt=0.7 → Modifier = {modifier:.3f}")
    
    # Example 4: Validation
    print("\n4. Implementation Validation:")
    validation = validate_large_tree_height_growth_implementation()
    print(f"   Tests Passed: {validation['passed']}")
    print(f"   Tests Failed: {validation['failed']}")
    
    print("\nLarge Tree Height Growth module demonstration completed!")


if __name__ == "__main__":
    demonstrate_large_tree_height_growth() 
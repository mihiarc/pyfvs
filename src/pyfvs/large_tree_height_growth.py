"""
Large tree height growth functions for FVS-Python.
Implements the large tree height growth model from the FVS Southern variant
following the approach of Wensel and others (1987).
"""
import math
from typing import Dict, Any, Optional

from .model_base import ParameterizedModel
from .config_loader import load_coefficient_file
from .exceptions import FVSError

__all__ = [
    'LargeTreeHeightGrowthModel',
    'create_large_tree_height_growth_model',
    'calculate_large_tree_height_growth',
    'calculate_crown_ratio_modifier',
    'calculate_relative_height_modifier',
    'validate_large_tree_height_growth_implementation',
]


class LargeTreeHeightGrowthModel(ParameterizedModel):
    """Large tree height growth model implementing FVS Southern variant equations.

    Uses the ParameterizedModel base class pattern for loading species-specific
    coefficients from sn_large_tree_height_growth_coefficients.json with fallback support.
    """

    # Class attributes for ParameterizedModel base class
    COEFFICIENT_FILE = 'sn_large_tree_height_growth_coefficients.json'
    COEFFICIENT_KEY = 'coefficients'
    FALLBACK_PARAMETERS = {
        'LP': {
            'b1': 0.222214,
            'b2': 1.16304,
            'b3': -0.000863,
            'b4': 0.028483,
            'b5': 0.006935,
            'b6': 0.005018,
            'b7': -0.004184,
            'b8': -0.759347,
            'b9': 0.18536,
            'b10': 0.0,
            'b11': -0.072842
        },
        'SP': {
            'b1': -0.008942,
            'b2': 1.23817,
            'b3': -0.00117,
            'b4': 0.053076,
            'b5': 0.040334,
            'b6': 0.004723,
            'b7': -0.003271,
            'b8': -0.704687,
            'b9': 0.127667,
            'b10': 0.0,
            'b11': 0.028391
        },
        'SA': {
            'b1': -1.641698,
            'b2': 1.461093,
            'b3': -0.00253,
            'b4': 0.265872,
            'b5': 0.069104,
            'b6': 0.006851,
            'b7': -0.004873,
            'b8': -0.018479,
            'b9': -0.193157,
            'b10': 0.0,
            'b11': -0.251016
        },
        'LL': {
            'b1': -1.331052,
            'b2': 1.098112,
            'b3': -0.001834,
            'b4': 0.184512,
            'b5': 0.388018,
            'b6': 0.008774,
            'b7': -0.002898,
            'b8': 0.225213,
            'b9': 0.086883,
            'b10': 0.0,
            'b11': 0.107445
        },
    }
    DEFAULT_SPECIES = "LP"

    def __init__(self, species_code: str = "LP"):
        """Initialize with species-specific parameters.

        Args:
            species_code: Species code (e.g., "LP", "SP", "SA", etc.)
        """
        super().__init__(species_code)
    
    def _load_parameters(self):
        """Load large tree height growth parameters from configuration.

        Extends base class to also load methodology, equation info,
        variable definitions, shade tolerance, and site index ranges.
        """
        # Call parent to load species coefficients into self.coefficients
        super()._load_parameters()

        # Also store as diameter_coefficients for backward compatibility
        self.diameter_coefficients = self.coefficients.copy()

        # Load additional data from raw_data (equation info, variable definitions)
        if self.raw_data:
            self.equation_info = self.raw_data.get('equation', '')
            self.variable_definitions = self.raw_data.get('variable_definitions', {})
        else:
            self._load_fallback_equation_info()

        # Load methodology from separate file
        self._load_methodology()

        # Load shade tolerance parameters
        self._load_shade_tolerance_parameters()

        # Load site index ranges and validation
        self._load_site_index_ranges()

    def _load_methodology(self):
        """Load methodology from sn_large_tree_height_growth.json."""
        try:
            self.methodology = load_coefficient_file('sn_large_tree_height_growth.json')
        except FileNotFoundError:
            self._load_fallback_methodology()

    def _load_fallback_parameters(self):
        """Load fallback parameters if coefficient file not available."""
        # Call parent for coefficient fallback
        super()._load_fallback_parameters()
        # Also store as diameter_coefficients for backward compatibility
        self.diameter_coefficients = self.coefficients.copy()
        # Load fallback equation info
        self._load_fallback_equation_info()

    def _load_fallback_equation_info(self):
        """Load fallback equation info when file not available."""
        self.equation_info = "ln(DDS) = b1 + (b2 * ln(DBH)) + (b3 * DBH^2) + (b4 * ln(CR)) + (b5 * RELHT) + (b6 * SI) + (b7 * BA) + (b8 * PBAL) + (b9 * SLOPE) + (b10 * cos(ASP) * SLOPE) + (b11 * sin(ASP) * SLOPE)"
        self.variable_definitions = {}
    
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
        """Load fallback shade tolerance parameters.

        Includes all 5 shade tolerance classes from WC htgf.f lines 76-131
        and species mappings for SN, PN, and WC variants.
        """
        # All 5 shade tolerance classes from Fortran htgf.f
        self.shade_tolerance_coeffs = {
            'Very Tolerant': {
                'RHR': 20, 'RHYXS': 0.20, 'RHM': 1.1,
                'RHB': -1.10, 'RHXS': 0, 'RHK': 1
            },
            'Tolerant': {
                'RHR': 16, 'RHYXS': 0.15, 'RHM': 1.1,
                'RHB': -1.20, 'RHXS': 0, 'RHK': 1
            },
            'Intermediate': {
                'RHR': 15, 'RHYXS': 0.10, 'RHM': 1.1,
                'RHB': -1.45, 'RHXS': 0, 'RHK': 1
            },
            'Intolerant': {
                'RHR': 13, 'RHYXS': 0.05, 'RHM': 1.1,
                'RHB': -1.60, 'RHXS': 0, 'RHK': 1
            },
            'Very Intolerant': {
                'RHR': 12, 'RHYXS': 0.01, 'RHM': 1.1,
                'RHB': -1.60, 'RHXS': 0, 'RHK': 1
            }
        }

        # Species shade tolerance mapping — covers SN, PN/WC species
        # PN/WC mappings from WC htgf.f lines 101-131 (TOLPTS array)
        # SN species use simplified Intolerant/Tolerant from SN htgf.f
        self.species_shade_tolerance = {
            # SN species
            'LP': 'Intolerant',
            'SP': 'Intolerant',
            'SA': 'Intolerant',
            'LL': 'Intolerant',
            'LB': 'Intolerant',
            'SB': 'Intolerant',
            'VP': 'Intolerant',
            'SR': 'Intolerant',
            'LO': 'Intolerant',
            'TB': 'Intolerant',
            'RO': 'Intermediate',
            'YP': 'Intermediate',
            'SU': 'Intermediate',
            # PN/WC conifers
            'SF': 'Very Tolerant',      # Pacific silver fir
            'WF': 'Tolerant',           # White fir
            'GF': 'Tolerant',           # Grand fir
            'AF': 'Tolerant',           # Subalpine fir
            'RF': 'Tolerant',           # Red fir
            'SS': 'Intermediate',       # Sitka spruce
            'NF': 'Tolerant',           # Noble fir
            'YC': 'Very Tolerant',      # Alaska yellow-cedar
            'IC': 'Tolerant',           # Incense-cedar
            'ES': 'Intermediate',       # Engelmann spruce
            'JP': 'Intolerant',         # Jeffrey pine
            'WP': 'Intermediate',       # Western white pine
            'PP': 'Intolerant',         # Ponderosa pine
            'DF': 'Intermediate',       # Douglas-fir
            'RW': 'Tolerant',           # Redwood
            'RC': 'Very Tolerant',      # Western redcedar
            'WH': 'Very Tolerant',      # Western hemlock
            'MH': 'Very Tolerant',      # Mountain hemlock
            # PN/WC hardwoods
            'BM': 'Tolerant',           # Bigleaf maple
            'RA': 'Intolerant',         # Red alder
            'WA': 'Intolerant',         # White alder
            'PB': 'Intolerant',         # Paper birch
            'GC': 'Intermediate',       # Giant chinkapin
            'AS': 'Very Intolerant',    # Quaking aspen
            'CW': 'Very Intolerant',    # Black cottonwood
            'WO': 'Intermediate',       # Oregon white oak
            'WJ': 'Very Intolerant',    # Western juniper
            'WB': 'Intolerant',         # Whitebark pine
            'KP': 'Very Intolerant',    # Knobcone pine
            'PY': 'Very Tolerant',      # Pacific yew
            'DG': 'Tolerant',           # Pacific dogwood
            'HT': 'Very Intolerant',    # Hawthorn
            'CH': 'Intermediate',       # Cherry
            'WI': 'Very Intolerant',    # Willow
            'OT': 'Intermediate',       # Other
        }
    
    def _load_site_index_ranges(self):
        """Load site index ranges and validation from configuration."""
        try:
            site_data = load_coefficient_file('sn_relative_site_index.json')

            # Get species-specific site index range
            species_ranges = site_data.get('species_site_index_ranges', {})
            if self.species_code in species_ranges:
                self.site_index_range = species_ranges[self.species_code]
            else:
                # Default range for LP
                self.site_index_range = {"si_min": 40, "si_max": 125}
        except FileNotFoundError:
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
                                        tree_height: Optional[float] = None,
                                        variant: str = 'SN') -> float:
        """Calculate potential height growth using the small-tree height increment model.

        This implements the methodology described in section 4.6.1 using the Chapman-Richards
        functional form as referenced in the large tree height growth methodology.

        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio as proportion (0-1)
            relative_height: Tree height relative to top 40 trees
            site_index: Site index in feet (base age varies by variant)
            basal_area: Stand basal area (sq ft/acre)
            pbal: Plot basal area larger (sq ft/acre)
            slope: Ground slope (proportion)
            aspect: Aspect in radians
            tree_age: Tree age (years) - if not provided, estimated from height
            tree_height: Current tree height (feet) - if not provided, estimated from DBH
            variant: FVS variant code (e.g., 'SN', 'LS', 'CS', 'NE')

        Returns:
            Potential height growth (feet)
        """
        # Validate and bound site index
        site_index = self._validate_site_index(site_index)

        # PN/WC: use species-specific height-age curves from htcalc.f
        if variant in ('PN', 'WC'):
            return self._calculate_potential_height_growth_pnwc(
                dbh, site_index, tree_height, tree_age, variant
            )

        # Load small tree height growth coefficients (variant-specific)
        small_tree_coeffs = self._get_small_tree_coefficients(variant=variant)

        # Estimate tree height if not provided
        if tree_height is None:
            tree_height = self._estimate_height_from_dbh(dbh)

        # Estimate tree age if not provided
        if tree_age is None:
            tree_age = self._estimate_age_from_height(tree_height, site_index, small_tree_coeffs)

        # Bound tree age to reasonable range
        tree_age = max(5.0, min(150.0, tree_age))

        # Calculate potential height using Chapman-Richards equation
        # Matches Fortran htgf.f: CALL HTCALC(MODE9=9,...) which computes
        # a 5-year height increment from the NC-128 site curve.
        c1, c2, c3, c4, c5 = (small_tree_coeffs['c1'], small_tree_coeffs['c2'],
                              small_tree_coeffs['c3'], small_tree_coeffs['c4'],
                              small_tree_coeffs['c5'])
        bh = small_tree_coeffs.get('bh', 0.0)

        def _raw_chapman_richards(age: float) -> float:
            """Calculate unscaled Chapman-Richards height."""
            if age <= 0:
                return bh + 0.1
            return bh + c1 * (site_index ** c2) * (1.0 - math.exp(c3 * age)) ** (c4 * (site_index ** c5))

        try:
            # Scale factor anchors H(base_age) = SI.
            # SN: Fortran HTCALC uses raw LTBHEC coefficients with NO scaling
            # (base age 25, coefficients match SI directly).
            # LS/CS/NE: base age 50, coefficients from LTBHEC need scaling
            # to ensure the site curve passes through SI at base age.
            # This must match tree.py _grow_small_tree().
            if variant in ('LS', 'CS', 'NE', 'CA', 'OP'):
                base_age = 50
                raw_at_base = _raw_chapman_richards(base_age)
                scale_factor = site_index / raw_at_base if raw_at_base > 0 else 1.0
            else:
                scale_factor = 1.0

            # FINDAG: effective age from current height (Fortran htgf.f approach).
            # When a tree is behind the site curve (shorter than H(calendar_age)),
            # calendar age gives SMALLER POTHTG because the site curve flattens
            # with age. Using effective age places the tree on the steeper part
            # of the curve where it actually is, yielding larger increments.
            # SN uses scale_factor=1.0 with base-age-25 coefficients; the FINDAG
            # inversion doesn't work correctly with that parameterization.
            if tree_height is not None and variant in ('LS', 'CS', 'NE', 'CA', 'OP'):
                exponent = c4 * (site_index ** c5)
                raw_ht = tree_height / scale_factor if scale_factor > 0 else tree_height
                ratio = (raw_ht - bh) / (c1 * (site_index ** c2)) if c1 * (site_index ** c2) > 0 else 1.0
                if 0 < ratio < 1.0 and exponent > 0 and c3 != 0:
                    inner = ratio ** (1.0 / exponent)
                    if 0 < inner < 1.0:
                        tree_age = max(0.1, math.log(1.0 - inner) / c3)

            # Compute 5-year height increment.
            # tree_age is effective age (FINDAG) for LS/CS/NE variants,
            # or calendar age for SN.
            # Uses backward increment H(age) - H(age-5) to match the
            # historical calibration. tree.py scales by time_step/5.0
            # for 10yr cycle variants.
            previous_age = max(0, tree_age - 5)

            previous_potht = _raw_chapman_richards(previous_age) * scale_factor
            current_potht = _raw_chapman_richards(tree_age) * scale_factor

            potential_height_growth = current_potht - previous_potht

        except (ValueError, OverflowError, ZeroDivisionError):
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
    
    def _calculate_potential_height_growth_pnwc(
        self,
        dbh: float,
        site_index: float,
        tree_height: Optional[float],
        tree_age: Optional[float],
        variant: str
    ) -> float:
        """Calculate POTHTG for PN/WC using species-specific htcalc.f curves.

        Uses the exact height-age equations (King, Wiley, Farr, etc.) instead
        of Chapman-Richards. Computes a 5-year height increment via the
        effective-age method.

        Args:
            dbh: Diameter at breast height (inches)
            site_index: Site index in feet
            tree_height: Current tree height (feet)
            tree_age: Tree age (years, after growth increment)
            variant: 'PN' or 'WC'

        Returns:
            Potential height growth (feet) for a 5-year period
        """
        from .pn_height_age import height_at_age, age_from_height

        if tree_height is None:
            tree_height = self._estimate_height_from_dbh(dbh)

        # Find effective age from current height on species curve
        effective_age = age_from_height(self.species_code, tree_height, site_index, variant)

        # Forward 5-year height increment (matching Fortran htgf.f)
        # Uses H(age+5) - H(age), not H(age) - H(age-5), because the
        # height-age curve is concave-down and backward overestimates.
        future_age = effective_age + 5
        current_potht = height_at_age(self.species_code, effective_age, site_index, variant)
        future_potht = height_at_age(self.species_code, future_age, site_index, variant)

        return max(0.0, future_potht - current_potht)

    def _get_small_tree_coefficients(self, variant: str = 'SN') -> Dict[str, float]:
        """Get small tree height growth coefficients for the species.

        Loads from variant-specific NC-128 coefficient file first, then falls
        back to SN file, then to hardcoded LP defaults.

        Args:
            variant: FVS variant code (e.g., 'SN', 'LS', 'CS', 'NE')

        Returns:
            Dictionary with Chapman-Richards coefficients
        """
        variant_lower = variant.lower()
        filenames = [
            f'{variant_lower}_small_tree_height_growth.json',
            'sn_small_tree_height_growth.json',
        ]
        for filename in filenames:
            try:
                small_tree_data = load_coefficient_file(filename, variant=variant)
                if 'nc128_height_growth_coefficients' in small_tree_data:
                    coeffs = small_tree_data['nc128_height_growth_coefficients']
                    if self.species_code in coeffs:
                        return coeffs[self.species_code]
                    elif 'LP' in coeffs:
                        return coeffs['LP']
            except FVSError:
                continue

        # Fallback coefficients if no file available
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
            'c5': -0.0109,
            'bh': 0.0
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

            # Fortran does NOT bound individual HGMDRH — only the combined
            # HTGMOD = 0.25*HGMDCR + 0.75*HGMDRH is bounded to [0.1, 2.0].
            # Dominant trees can have HGMDRH > 1.0.
            hgmdrh = max(0.0, hgmdrh)
            
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
                              tree_height: Optional[float] = None,
                              variant: str = 'SN') -> float:
        """Calculate periodic height growth for large trees.

        Main equation 4.7.2.1: HTG = POTHTG * (0.25 * HGMDCR + 0.75 * HGMDRH)

        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio as proportion (0-1)
            relative_height: Tree height relative to top 40 trees
            site_index: Site index in feet (base age varies by variant)
            basal_area: Stand basal area (sq ft/acre)
            pbal: Plot basal area larger (sq ft/acre)
            slope: Ground slope (proportion)
            aspect: Aspect in radians
            species_code: Species code for shade tolerance
            tree_age: Tree age (years) - if not provided, estimated from height
            tree_height: Current tree height (feet) - if not provided, estimated from DBH
            variant: FVS variant code (e.g., 'SN', 'LS', 'CS', 'NE')

        Returns:
            Periodic height growth (feet)
        """
        if species_code is None:
            species_code = self.species_code

        # Calculate potential height growth
        pothtg = self.calculate_potential_height_growth(
            dbh, crown_ratio, relative_height, site_index,
            basal_area, pbal, slope, aspect, tree_age, tree_height,
            variant=variant
        )
        
        # Apply height growth modifier.
        # LS/CS/NE Fortran htgf.f uses eastern GMOD formula:
        #   GMOD = (1.0 - ((1.0-BALMOD)*(1.0-RELHTA))) * 0.8
        # which caps at 0.80 for dominant trees (RELHTA >= 1.0).
        # Native FVS compensates with OLDRN stochastic autocorrelation
        # that boosts dominant trees by ~25%, giving effective ~1.0.
        # Since PyFVS is deterministic, we use the SN formula which
        # gives ~0.98 for dominant trees — a better approximation of
        # the combined (1+OLDRN)*GMOD effect.
        hgmdcr = self.calculate_crown_ratio_modifier(crown_ratio)
        hgmdrh = self.calculate_relative_height_modifier(
            relative_height, species_code
        )
        htgmod = 0.25 * hgmdcr + 0.75 * hgmdrh
        htgmod = max(0.1, min(2.0, htgmod))

        htg = pothtg * htgmod

        return max(0.1, htg)
    
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
                                     tree_height: Optional[float] = None,
                                     variant: str = 'SN') -> float:
    """Standalone function to calculate large tree height growth.

    Args:
        species_code: Species code
        dbh: Diameter at breast height (inches)
        crown_ratio: Crown ratio as proportion (0-1)
        relative_height: Tree height relative to top 40 trees
        site_index: Site index in feet (base age varies by variant)
        basal_area: Stand basal area (sq ft/acre)
        pbal: Plot basal area larger (sq ft/acre)
        slope: Ground slope (proportion)
        aspect: Aspect in radians
        tree_age: Tree age (years) - if not provided, estimated from height
        tree_height: Current tree height (feet) - if not provided, estimated from DBH
        variant: FVS variant code (e.g., 'SN', 'LS', 'CS', 'NE')

    Returns:
        Periodic height growth (feet)
    """
    model = create_large_tree_height_growth_model(species_code)
    return model.calculate_height_growth(
        dbh, crown_ratio, relative_height, site_index,
        basal_area, pbal, slope, aspect, species_code, tree_age, tree_height,
        variant=variant
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
"""
Bark ratio relationship functions for FVS-Python.

Supports multiple FVS variants:
- SN (Southern): Clark (1991) equation DIB = b1 + b2 * DOB
- LS (Lake States): Constant bark ratio per species from Raile (1982)
- NE (Northeast): Constant bark ratio per species (TWIGS family, same as LS)
- PN (Pacific Northwest Coast): 3 equation types from bratio.f (power, linear, constant)
"""
from typing import Dict, Any, Optional

from .model_base import ParameterizedModel
from .config_loader import load_coefficient_file, get_default_variant

__all__ = [
    'BarkRatioModel',
    'LSBarkRatioModel',
    'NEBarkRatioModel',
    'CSBarkRatioModel',
    'PNBarkRatioModel',
    'WSBarkRatioModel',
    'CABarkRatioModel',
    'create_bark_ratio_model',
    'calculate_dib_from_dob',
    'calculate_bark_ratio',
    'get_all_species_coefficients',
    'compare_bark_ratios',
    'validate_bark_ratio_implementation',
]


# Variant-to-coefficient-file mapping
VARIANT_BARK_RATIO_FILES = {
    'SN': 'sn_bark_ratio_coefficients.json',
    'LS': 'ls/ls_bark_ratio_coefficients.json',
    'PN': 'pn/pn_bark_ratio_coefficients.json',
}


class BarkRatioModel(ParameterizedModel):
    """Bark ratio model implementing FVS Southern variant equations.

    Uses the base class pattern for loading species-specific coefficients
    from sn_bark_ratio_coefficients.json with fallback support.
    """

    # Class attributes for ParameterizedModel base class
    COEFFICIENT_FILE = 'sn_bark_ratio_coefficients.json'
    COEFFICIENT_KEY = 'species_coefficients'
    FALLBACK_PARAMETERS = {
        'LP': {'b1': -0.48140, 'b2': 0.91413},
        'SP': {'b1': -0.31239, 'b2': 0.91413},
        'SA': {'b1': -0.39305, 'b2': 0.91413},
        'LL': {'b1': -0.48140, 'b2': 0.91413},
    }
    DEFAULT_SPECIES = "LP"

    def __init__(self, species_code: str = "LP"):
        """Initialize with species-specific parameters.

        Args:
            species_code: Species code (e.g., "LP", "SP", "SA", etc.)
        """
        super().__init__(species_code)

    def _load_parameters(self):
        """Load bark ratio parameters from cached configuration.

        Extends base class to also load equation_info and bounds.
        """
        # Call parent to load coefficients
        super()._load_parameters()

        # Load additional bark ratio specific data
        if self.raw_data:
            self.equation_info = self.raw_data.get('equation', {})
            self.bounds = self.equation_info.get('bounds', "0.80 < BRATIO < 0.99")
        else:
            self._load_fallback_equation_info()

    def _load_fallback_parameters(self):
        """Load fallback parameters if bark ratio file not available."""
        # Call parent for coefficient fallback
        super()._load_fallback_parameters()
        # Also load fallback equation info
        self._load_fallback_equation_info()

    def _load_fallback_equation_info(self):
        """Load fallback equation info when file not available."""
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


class LSBarkRatioModel:
    """Bark ratio model for the Lake States (LS) variant.

    LS uses constant bark ratios per species from Raile (1982),
    unlike SN which uses the Clark (1991) equation DIB = b1 + b2 * DOB.

    Subclasses (e.g., NEBarkRatioModel) override class attributes to
    load variant-specific coefficient files and hardwood sets.
    """

    # Coefficient file path (relative to cfg/), overridden by subclasses
    _COEFFICIENT_FILE = 'ls/ls_bark_ratio_coefficients.json'

    # Fallback bark ratios for common LS species
    FALLBACK_RATIOS = {
        'JP': 0.899, 'SC': 0.899, 'RN': 0.916, 'RP': 0.916,
        'WP': 0.907, 'WS': 0.924, 'NS': 0.924, 'BF': 0.926,
        'BS': 0.924, 'TA': 0.915, 'WC': 0.916, 'EH': 0.916,
        'SM': 0.918, 'RM': 0.918, 'QA': 0.911, 'PB': 0.920,
        'RO': 0.914, 'WO': 0.914, 'YB': 0.920, 'AB': 0.920,
    }

    DEFAULT_SOFTWOOD = 0.916
    DEFAULT_HARDWOOD = 0.914

    # Hardwood species codes (overridden by subclasses)
    _HARDWOOD_SET = {
        'BA', 'GA', 'EC', 'SV', 'RM', 'BC', 'AE', 'RL', 'RE', 'YB',
        'BW', 'SM', 'BM', 'AB', 'WA', 'WO', 'SW', 'BR', 'CK', 'RO',
        'BO', 'BH', 'PH', 'SH', 'BT', 'QA', 'BP', 'PB', 'BN', 'WN',
        'HH', 'BK', 'OH', 'BE', 'ST', 'MM', 'AH', 'AC', 'HK', 'DW',
        'HT', 'AP', 'BG', 'SY', 'PR', 'CC', 'PL', 'WI', 'BL', 'DM',
        'SS', 'MA',
    }

    def __init__(self, species_code: str = "RN"):
        """Initialize with species-specific constant bark ratio.

        Args:
            species_code: Species code (e.g., "RN", "JP", "SM", etc.)
        """
        self.species_code = species_code
        self._bark_ratio = None
        self._all_ratios = None
        self._load_bark_ratio()

    def _load_bark_ratio(self):
        """Load constant bark ratio from coefficient file."""
        try:
            data = load_coefficient_file(self._COEFFICIENT_FILE)
            ratios = data.get('species_bark_ratios', {})
            self._all_ratios = ratios
            if self.species_code in ratios:
                self._bark_ratio = ratios[self.species_code]
            else:
                # Use softwood/hardwood default
                if self.species_code in self._HARDWOOD_SET:
                    self._bark_ratio = data.get('defaults', {}).get('hardwood', self.DEFAULT_HARDWOOD)
                else:
                    self._bark_ratio = data.get('defaults', {}).get('softwood', self.DEFAULT_SOFTWOOD)
        except FileNotFoundError:
            self._bark_ratio = self.FALLBACK_RATIOS.get(self.species_code, self.DEFAULT_SOFTWOOD)

    def calculate_bark_ratio(self, dob: float) -> float:
        """Return constant bark ratio (independent of diameter for LS).

        Args:
            dob: Diameter outside bark (inches) - not used but kept for interface compatibility

        Returns:
            Bark ratio as proportion (0-1)
        """
        return self._bark_ratio

    def calculate_dib_from_dob(self, dob: float) -> float:
        """Calculate diameter inside bark from diameter outside bark.

        Args:
            dob: Diameter outside bark (inches)

        Returns:
            Diameter inside bark (inches)
        """
        if dob <= 0:
            return 0.0
        return dob * self._bark_ratio

    def calculate_dob_from_dib(self, dib: float) -> float:
        """Calculate diameter outside bark from diameter inside bark.

        Args:
            dib: Diameter inside bark (inches)

        Returns:
            Diameter outside bark (inches)
        """
        if dib <= 0:
            return 0.0
        if self._bark_ratio == 0:
            return dib
        return dib / self._bark_ratio

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
        return max(0.0, (dob - dib) / 2.0)

    def apply_bark_ratio_to_dbh(self, dbh_ob: float) -> float:
        """Apply bark ratio to convert DBH outside bark to inside bark.

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

    def get_species_coefficients(self) -> Dict[str, float]:
        """Get the bark ratio for this species.

        Returns:
            Dictionary with bark_ratio constant
        """
        return {'bark_ratio': self._bark_ratio}

    def validate_bark_ratio(self, bark_ratio: float) -> bool:
        """Validate that a bark ratio is within acceptable bounds.

        Args:
            bark_ratio: Bark ratio to validate (proportion)

        Returns:
            True if bark ratio is within bounds
        """
        return 0.80 <= bark_ratio <= 0.99


class NEBarkRatioModel(LSBarkRatioModel):
    """Bark ratio model for the Northeast (NE) variant.

    NE uses constant bark ratios per species, same TWIGS model family as LS.
    Inherits all calculation methods from LSBarkRatioModel; only overrides
    coefficient file path, fallback ratios, and hardwood species set.
    """

    _COEFFICIENT_FILE = 'ne/ne_bark_ratio_coefficients.json'

    FALLBACK_RATIOS = {
        'RM': 0.918, 'SM': 0.918, 'WP': 0.907, 'RO': 0.914,
        'WO': 0.914, 'BF': 0.926, 'RS': 0.924, 'EH': 0.916,
        'YB': 0.920, 'AB': 0.920, 'WA': 0.918, 'BC': 0.920,
        'YP': 0.918, 'WN': 0.914, 'RN': 0.916, 'QA': 0.911,
    }

    _HARDWOOD_SET = {
        'RM', 'SM', 'BM', 'SV', 'BE', 'ST', 'YB', 'SB', 'RB', 'PB',
        'GB', 'WR', 'HI', 'PH', 'SL', 'SH', 'MH', 'AB', 'AS', 'WA',
        'BA', 'GA', 'PA', 'YP', 'SU', 'CT', 'QA', 'BP', 'EC', 'BT',
        'PY', 'BC', 'WO', 'BR', 'CK', 'PO', 'SW', 'SN', 'CO', 'OK',
        'SO', 'QI', 'WK', 'PN', 'RO', 'SK', 'BO', 'CB', 'WL', 'BU',
        'YY', 'HK', 'PS', 'HY', 'BN', 'WN', 'OO', 'MG', 'MV', 'AP',
        'WT', 'BG', 'SD', 'PW', 'SY', 'BK', 'BL', 'SS', 'BW', 'WB',
        'EL', 'AE', 'RL', 'OH', 'AI', 'SE', 'AH', 'DW', 'HT', 'HH',
        'PL', 'PR',
    }

    def __init__(self, species_code: str = "RM"):
        """Initialize with NE species-specific constant bark ratio.

        Args:
            species_code: Species code (e.g., "RM", "SM", "WP", etc.)
        """
        super().__init__(species_code)


class CSBarkRatioModel(LSBarkRatioModel):
    """Bark ratio model for the Central States (CS) variant.

    CS uses constant bark ratios per species, same TWIGS model family as LS/NE.
    Inherits all calculation methods from LSBarkRatioModel; only overrides
    coefficient file path, fallback ratios, and hardwood species set.
    """

    _COEFFICIENT_FILE = 'cs/cs_bark_ratio_coefficients.json'

    FALLBACK_RATIOS = {
        'WO': 0.914, 'RO': 0.914, 'SM': 0.918, 'WN': 0.914,
        'YP': 0.918, 'WA': 0.918, 'BC': 0.920, 'SP': 0.910,
        'WP': 0.907, 'RM': 0.918, 'BO': 0.914, 'SH': 0.914,
    }

    _HARDWOOD_SET = {
        'WN', 'BN', 'TL', 'TS', 'WT', 'BG', 'HS', 'SH', 'SL', 'MH',
        'PH', 'HI', 'WH', 'BH', 'PE', 'BI', 'AB', 'BA', 'PA', 'UA',
        'EC', 'RM', 'BE', 'SV', 'BC', 'AE', 'SG', 'HK', 'WE', 'EL',
        'SI', 'RL', 'RE', 'YP', 'BW', 'SM', 'AS', 'WA', 'GA',
        'WO', 'RO', 'SK', 'BO', 'SO', 'BJ', 'CK', 'SW', 'BR', 'SN',
        'PO', 'DO', 'CO', 'PN', 'CB', 'QI', 'OV', 'WK', 'NK', 'WL',
        'QS', 'UH', 'SS', 'OB', 'CA', 'PS', 'HL', 'BP', 'BT', 'QA',
        'BK', 'OL', 'SY', 'RB', 'SU', 'WI', 'BL', 'NC', 'AH', 'RD',
        'DW', 'HT', 'KC', 'OO', 'CT', 'MV', 'MB', 'HH', 'SD',
    }

    def __init__(self, species_code: str = "WO"):
        """Initialize with CS species-specific constant bark ratio.

        Args:
            species_code: Species code (e.g., "WO", "RO", "SM", etc.)
        """
        super().__init__(species_code)


class PNBarkRatioModel:
    """Bark ratio model for the Pacific Northwest Coast (PN) variant.

    PN uses 3 equation types from bratio.f with 16 species groups:
    - Type 1: DIB = a * DOB^b (power equation, most conifers)
    - Type 2: DIB = a + b * DOB (linear, BM/GC/RA)
    - Type 3: DIB = a * DOB (constant ratio, ES/LP)

    Species are mapped to groups via the JBARK array (39 species -> 16 groups).
    """

    # Fallback species-to-group mapping from bratio.f JBARK array
    _SPECIES_TO_GROUP = {
        'SF': 1, 'WF': 2, 'GF': 2, 'AF': 4, 'RF': 4,
        'SS': 5, 'NF': 4, 'YC': 15, 'IC': 4, 'ES': 13,
        'LP': 13, 'JP': 3, 'SP': 5, 'WP': 5, 'PP': 3,
        'DF': 1, 'RW': 14, 'RC': 6, 'WH': 7, 'MH': 16,
        'BM': 9, 'RA': 11, 'WA': 14, 'PB': 14, 'GC': 10,
        'AS': 14, 'CW': 14, 'WO': 8, 'WJ': 14, 'LL': 3,
        'WB': 3, 'KP': 3, 'PY': 14, 'DG': 14, 'HT': 14,
        'CH': 14, 'WI': 14, 'OT': 12,
    }

    # Fallback group coefficients from bratio.f
    _FALLBACK_GROUPS = {
        1:  {'type': 1, 'a': 0.903563, 'b': 0.989388},
        2:  {'type': 1, 'a': 0.904973, 'b': 1.0},
        3:  {'type': 1, 'a': 0.809427, 'b': 1.016866},
        4:  {'type': 1, 'a': 0.837291, 'b': 1.0},
        5:  {'type': 1, 'a': 0.958330, 'b': 1.0},
        6:  {'type': 1, 'a': 0.949670, 'b': 1.0},
        7:  {'type': 1, 'a': 0.933710, 'b': 1.0},
        8:  {'type': 1, 'a': 0.855800, 'b': 1.021300},
        9:  {'type': 2, 'a': 0.083600, 'b': 0.947820},
        10: {'type': 2, 'a': 0.155650, 'b': 0.901820},
        11: {'type': 2, 'a': 0.075256, 'b': 0.943730},
        12: {'type': 1, 'a': 0.933290, 'b': 1.0},
        13: {'type': 3, 'a': 0.900000, 'b': None},
        14: {'type': 1, 'a': 0.701200, 'b': 1.048620},
        15: {'type': 1, 'a': 0.949670, 'b': 1.0},
        16: {'type': 1, 'a': 0.933710, 'b': 1.0},
    }

    DEFAULT_GROUP = 12  # OT (other species) group

    def __init__(self, species_code: str = "DF"):
        """Initialize with species-specific bark ratio parameters.

        Args:
            species_code: Species code (e.g., "DF", "WH", "RC", etc.)
        """
        self.species_code = species_code
        self._eq_type = None
        self._a = None
        self._b = None
        self._species_to_group = None
        self._groups = None
        self._load_parameters()

    def _load_parameters(self):
        """Load bark ratio parameters from PN coefficient file."""
        try:
            data = load_coefficient_file('pn/pn_bark_ratio_coefficients.json')
            self._species_to_group = data.get('species_to_group', self._SPECIES_TO_GROUP)
            groups_raw = data.get('species_groups', {})
            # Convert string keys to int keys
            self._groups = {int(k): v for k, v in groups_raw.items()}
        except FileNotFoundError:
            self._species_to_group = self._SPECIES_TO_GROUP
            self._groups = self._FALLBACK_GROUPS

        # Look up this species' group
        group_num = self._species_to_group.get(self.species_code, self.DEFAULT_GROUP)
        group = self._groups.get(group_num, self._FALLBACK_GROUPS[self.DEFAULT_GROUP])

        self._eq_type = group['type']
        self._a = group['a']
        self._b = group.get('b')

    def calculate_dib_from_dob(self, dob: float) -> float:
        """Calculate diameter inside bark from diameter outside bark.

        Uses one of 3 equation types based on species group:
        - Type 1: DIB = a * DOB^b (power)
        - Type 2: DIB = a + b * DOB (linear)
        - Type 3: DIB = a * DOB (constant ratio)

        Args:
            dob: Diameter outside bark (inches)

        Returns:
            Diameter inside bark (inches)
        """
        if dob <= 0:
            return 0.0

        if self._eq_type == 1:
            dib = self._a * (dob ** self._b)
        elif self._eq_type == 2:
            dib = self._a + self._b * dob
        elif self._eq_type == 3:
            dib = self._a * dob
        else:
            dib = 0.9 * dob  # safe fallback

        # Ensure DIB is not negative and not greater than DOB
        return max(0.0, min(dib, dob))

    def calculate_dob_from_dib(self, dib: float) -> float:
        """Calculate diameter outside bark from diameter inside bark.

        Inverts the bark ratio equation for each type.

        Args:
            dib: Diameter inside bark (inches)

        Returns:
            Diameter outside bark (inches)
        """
        if dib <= 0:
            return 0.0

        if self._eq_type == 1:
            # DIB = a * DOB^b  =>  DOB = (DIB / a)^(1/b)
            if self._a > 0 and self._b != 0:
                dob = (dib / self._a) ** (1.0 / self._b)
            else:
                dob = dib
        elif self._eq_type == 2:
            # DIB = a + b * DOB  =>  DOB = (DIB - a) / b
            if self._b != 0:
                dob = (dib - self._a) / self._b
            else:
                dob = dib
        elif self._eq_type == 3:
            # DIB = a * DOB  =>  DOB = DIB / a
            if self._a > 0:
                dob = dib / self._a
            else:
                dob = dib
        else:
            dob = dib / 0.9

        return max(dib, dob)

    def calculate_bark_ratio(self, dob: float) -> float:
        """Calculate bark ratio (DIB/DOB) for a given diameter outside bark.

        Args:
            dob: Diameter outside bark (inches)

        Returns:
            Bark ratio as proportion (bounded 0.80-0.99)
        """
        if dob <= 0:
            return 1.0

        dib = self.calculate_dib_from_dob(dob)
        bark_ratio = dib / dob

        # Apply FVS bounds: 0.80 < BRATIO < 0.99
        return max(0.80, min(0.99, bark_ratio))

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
        return max(0.0, (dob - dib) / 2.0)

    def apply_bark_ratio_to_dbh(self, dbh_ob: float) -> float:
        """Apply bark ratio to convert DBH outside bark to inside bark.

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

    def get_species_coefficients(self) -> Dict[str, Any]:
        """Get the bark ratio coefficients for this species.

        Returns:
            Dictionary with equation type, a, and b coefficients
        """
        return {'type': self._eq_type, 'a': self._a, 'b': self._b}

    def validate_bark_ratio(self, bark_ratio: float) -> bool:
        """Validate that a bark ratio is within acceptable bounds.

        Args:
            bark_ratio: Bark ratio to validate (proportion)

        Returns:
            True if bark ratio is within bounds
        """
        return 0.80 <= bark_ratio <= 0.99


class WSBarkRatioModel:
    """Bark ratio model for the Western Sierra Nevada (WS) variant.

    WS uses constant bark ratios per species from bratio.f:
        BRATIO = BARK1 + BARK2 / D
    Most species have BARK2=0 (constant ratio). GB has diameter-dependent ratio.
    Bounded [0.80, 0.99] per FVS specification.
    """

    _COEFFICIENT_FILE = 'ws/ws_bark_ratio_coefficients.json'

    FALLBACK_RATIOS = {
        'SP': 0.8863, 'DF': 0.8839, 'WF': 0.8911, 'GS': 0.8863,
        'IC': 0.8374, 'JP': 0.8967, 'RF': 0.8911, 'PP': 0.8967,
        'LP': 0.9000, 'WB': 0.9000, 'WP': 0.8863, 'PM': 0.9329,
        'SF': 0.8911, 'MH': 0.8863, 'RW': 0.8863, 'BD': 0.8839,
        'MC': 0.9000, 'OS': 0.8967,
    }

    DEFAULT_SOFTWOOD = 0.9000
    DEFAULT_HARDWOOD = 0.8374

    _HARDWOOD_SET = {
        'LO', 'CY', 'BL', 'BO', 'VO', 'IO', 'TO', 'GC', 'AS', 'CL',
        'MA', 'DG', 'BM', 'OH',
    }

    def __init__(self, species_code: str = "SP"):
        self.species_code = species_code
        self._bark1 = None
        self._bark2 = None
        self._load_parameters()

    def _load_parameters(self):
        """Load bark ratio parameters from WS coefficient file."""
        try:
            data = load_coefficient_file(self._COEFFICIENT_FILE)
            ratios = data.get('species_bark_ratios', {})
            if self.species_code in ratios:
                entry = ratios[self.species_code]
                self._bark1 = entry['bark1']
                self._bark2 = entry['bark2']
            else:
                self._use_fallback()
        except FileNotFoundError:
            self._use_fallback()

    def _use_fallback(self):
        if self.species_code in self.FALLBACK_RATIOS:
            self._bark1 = self.FALLBACK_RATIOS[self.species_code]
        elif self.species_code in self._HARDWOOD_SET:
            self._bark1 = self.DEFAULT_HARDWOOD
        else:
            self._bark1 = self.DEFAULT_SOFTWOOD
        self._bark2 = 0.0

    def calculate_bark_ratio(self, dob: float) -> float:
        """Calculate bark ratio bounded [0.80, 0.99]."""
        if dob <= 0:
            return 1.0
        ratio = self._bark1 + self._bark2 / dob if dob > 0.1 else self._bark1
        return max(0.80, min(0.99, ratio))

    def calculate_dib_from_dob(self, dob: float) -> float:
        if dob <= 0:
            return 0.0
        return max(0.0, min(dob, dob * self.calculate_bark_ratio(dob)))

    def calculate_dob_from_dib(self, dib: float) -> float:
        if dib <= 0:
            return 0.0
        ratio = self._bark1
        if ratio <= 0:
            return dib
        return max(dib, dib / ratio)

    def calculate_bark_thickness(self, dob: float) -> float:
        if dob <= 0:
            return 0.0
        return max(0.0, (dob - self.calculate_dib_from_dob(dob)) / 2.0)

    def apply_bark_ratio_to_dbh(self, dbh_ob: float) -> float:
        return self.calculate_dib_from_dob(dbh_ob)

    def convert_dbh_ib_to_ob(self, dbh_ib: float) -> float:
        return self.calculate_dob_from_dib(dbh_ib)

    def get_species_coefficients(self) -> Dict[str, Any]:
        return {'bark1': self._bark1, 'bark2': self._bark2}

    def validate_bark_ratio(self, bark_ratio: float) -> bool:
        return 0.80 <= bark_ratio <= 0.99


class CABarkRatioModel:
    """Bark ratio model for the Inland California (CA) variant.

    CA uses 3 equation types from bratio.f with 28 species groups:
    - Type 1: DIB = a * DOB^b (power equation)
    - Type 2: DIB = a + b * DOB (linear)
    - Type 3: DIB = a * DOB (constant ratio)

    Species are mapped to groups via the JBARK array (49 species -> 28 groups).
    """

    _COEFFICIENT_FILE = 'ca/ca_bark_ratio_coefficients.json'

    # Fallback species-to-group mapping from bratio.f JBARK array
    _SPECIES_TO_GROUP = {
        'PC': 12, 'IC': 5, 'RC': 12, 'WF': 2, 'RF': 2, 'SH': 2, 'DF': 1,
        'WH': 13, 'MH': 13, 'WB': 10, 'KP': 27, 'LP': 10, 'CP': 3, 'LM': 10,
        'JP': 4, 'SP': 25, 'WP': 25, 'PP': 3, 'MP': 3, 'GP': 26,
        'WJ': 12, 'BR': 9, 'GS': 12, 'PY': 10, 'OS': 3, 'LO': 19,
        'CY': 18, 'BL': 17, 'EO': 20, 'WO': 8, 'BO': 16, 'VO': 24,
        'IO': 21, 'BM': 6, 'BU': 16, 'RA': 14, 'MA': 23, 'GC': 7,
        'DG': 16, 'FL': 16, 'WN': 16, 'TO': 28, 'SY': 16, 'AS': 14,
        'CW': 16, 'WI': 16, 'CN': 16, 'CL': 22, 'OH': 16,
    }

    _FALLBACK_GROUPS = {
        1:  {'type': 1, 'a': 0.903563, 'b': 0.989388},
        2:  {'type': 2, 'a': -0.1593, 'b': 0.8911},
        3:  {'type': 2, 'a': -0.4448, 'b': 0.8967},
        4:  {'type': 2, 'a': -0.4448, 'b': 0.8967},
        5:  {'type': 2, 'a': -0.0549, 'b': 0.8374},
        6:  {'type': 2, 'a': 0.08360, 'b': 0.94782},
        7:  {'type': 2, 'a': 0.15565, 'b': 0.90182},
        8:  {'type': 2, 'a': -0.30722, 'b': 0.95956},
        9:  {'type': 3, 'a': 0.9, 'b': None},
        10: {'type': 3, 'a': 0.9, 'b': None},
        11: {'type': 1, 'a': 0.958330, 'b': 1.0},
        12: {'type': 1, 'a': 0.949670, 'b': 1.0},
        13: {'type': 1, 'a': 0.933710, 'b': 1.0},
        14: {'type': 2, 'a': 0.075256, 'b': 0.94373},
        15: {'type': 1, 'a': 0.933290, 'b': 1.0},
        16: {'type': 2, 'a': -0.26824, 'b': 0.95767},
        17: {'type': 2, 'a': -0.17324, 'b': 0.94403},
        18: {'type': 2, 'a': -0.19128, 'b': 0.96147},
        19: {'type': 2, 'a': -0.75739, 'b': 0.93475},
        20: {'type': 2, 'a': -0.78572, 'b': 0.92472},
        21: {'type': 2, 'a': 0.04817, 'b': 0.92953},
        22: {'type': 2, 'a': -0.12791, 'b': 0.96579},
        23: {'type': 2, 'a': -0.013484, 'b': 0.98155},
        24: {'type': 2, 'a': -0.38289, 'b': 0.93545},
        25: {'type': 2, 'a': -0.1429, 'b': 0.8863},
        26: {'type': 3, 'a': 0.9329, 'b': None},
        27: {'type': 3, 'a': 0.9329, 'b': None},
        28: {'type': 2, 'a': -0.26824, 'b': 0.95354},
    }

    DEFAULT_GROUP = 15  # OT (other species) group

    def __init__(self, species_code: str = "PP"):
        self.species_code = species_code
        self._eq_type = None
        self._a = None
        self._b = None
        self._load_parameters()

    def _load_parameters(self):
        """Load bark ratio parameters from CA coefficient file."""
        species_to_group = self._SPECIES_TO_GROUP
        groups = self._FALLBACK_GROUPS

        try:
            data = load_coefficient_file(self._COEFFICIENT_FILE)
            species_to_group = data.get('species_to_group', species_to_group)
            groups_raw = data.get('species_groups', {})
            if groups_raw:
                groups = {int(k): v for k, v in groups_raw.items()}
        except FileNotFoundError:
            pass

        group_num = species_to_group.get(self.species_code, self.DEFAULT_GROUP)
        group = groups.get(group_num, self._FALLBACK_GROUPS[self.DEFAULT_GROUP])

        self._eq_type = group['type']
        self._a = group['a']
        self._b = group.get('b')

    def calculate_dib_from_dob(self, dob: float) -> float:
        if dob <= 0:
            return 0.0
        if self._eq_type == 1:
            dib = self._a * (dob ** self._b)
        elif self._eq_type == 2:
            dib = self._a + self._b * dob
        elif self._eq_type == 3:
            dib = self._a * dob
        else:
            dib = 0.9 * dob
        return max(0.0, min(dib, dob))

    def calculate_dob_from_dib(self, dib: float) -> float:
        if dib <= 0:
            return 0.0
        if self._eq_type == 1:
            if self._a > 0 and self._b != 0:
                dob = (dib / self._a) ** (1.0 / self._b)
            else:
                dob = dib
        elif self._eq_type == 2:
            if self._b != 0:
                dob = (dib - self._a) / self._b
            else:
                dob = dib
        elif self._eq_type == 3:
            if self._a > 0:
                dob = dib / self._a
            else:
                dob = dib
        else:
            dob = dib / 0.9
        return max(dib, dob)

    def calculate_bark_ratio(self, dob: float) -> float:
        if dob <= 0:
            return 1.0
        dib = self.calculate_dib_from_dob(dob)
        return max(0.80, min(0.99, dib / dob))

    def calculate_bark_thickness(self, dob: float) -> float:
        if dob <= 0:
            return 0.0
        return max(0.0, (dob - self.calculate_dib_from_dob(dob)) / 2.0)

    def apply_bark_ratio_to_dbh(self, dbh_ob: float) -> float:
        return self.calculate_dib_from_dob(dbh_ob)

    def convert_dbh_ib_to_ob(self, dbh_ib: float) -> float:
        return self.calculate_dob_from_dib(dbh_ib)

    def get_species_coefficients(self) -> Dict[str, Any]:
        return {'type': self._eq_type, 'a': self._a, 'b': self._b}

    def validate_bark_ratio(self, bark_ratio: float) -> bool:
        return 0.80 <= bark_ratio <= 0.99


_bark_ratio_cache: dict[tuple[str, str], object] = {}


def create_bark_ratio_model(species_code: str = "LP", variant: Optional[str] = None):
    """Factory function to create a cached bark ratio model for a species and variant.

    Args:
        species_code: Species code (e.g., "LP", "SP", "RN", etc.)
        variant: FVS variant code (e.g., 'SN', 'LS'). If None, uses default.

    Returns:
        BarkRatioModel or LSBarkRatioModel instance (cached per species+variant)
    """
    if variant is None:
        variant = get_default_variant()

    cache_key = (species_code.upper(), variant.upper())
    if cache_key not in _bark_ratio_cache:
        from .variant_registry import get_variant_config
        config = get_variant_config(variant)
        _bark_ratio_cache[cache_key] = config.bark_ratio_class(species_code)
    return _bark_ratio_cache[cache_key]


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
    try:
        bark_data = load_coefficient_file('sn_bark_ratio_coefficients.json')
        return bark_data.get('species_coefficients', {})
    except FileNotFoundError:
        return BarkRatioModel.FALLBACK_PARAMETERS.copy()


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
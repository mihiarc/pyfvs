"""
Northeast (NE) variant diameter growth model.

Implements the NE-TWIGS diameter growth equation for the FVS Northeast variant.
The NE variant uses a basal area increment model:

NE-TWIGS equation:
    Potential BA Growth = B1 * SI * (1 - exp(-B2 * DBH))
    Adjusted Growth = POTBAG * 0.7 * BAGMOD

where:
    - B1, B2 are species-specific coefficients
    - SI = site index
    - DBH = diameter at breast height
    - BAGMOD = competition modifier from basal area in larger trees (BAL)

The growth is then converted from basal area to diameter increment.
This model iterates 10 times annually per the dgf.f source code.

Key differences from other variants:
    - Uses a potential basal area growth approach
    - Simple 2-coefficient species equations (B1, B2)
    - 0.7 modifier applied to potential growth
    - Competition through BAL-based modifier
    - 10-year base cycle

Source: FVS Northeast Variant dgf.f, USDA Forest Service
"""
import math
from typing import Dict, Any, Optional

from .model_base import ParameterizedModel
from .config_loader import load_coefficient_file


class NEDiameterGrowthModel(ParameterizedModel):
    """Northeast variant diameter growth model.

    Calculates diameter increment using the NE-TWIGS approach.

    The NE variant uses potential basal area growth:
        POTBAG = B1 * SI * (1 - exp(-B2 * DBH))
        Adjusted = POTBAG * 0.7 * BAGMOD

    Then converts to diameter increment.

    Attributes:
        species_code: Species code (e.g., 'RM', 'SM', 'WP')
        coefficients: Species-specific coefficients (B1, B2)
    """

    COEFFICIENT_FILE = 'ne/ne_diameter_growth_coefficients.json'
    COEFFICIENT_KEY = 'coefficients'
    DEFAULT_SPECIES = 'RM'  # Red Maple is the default site species for NE

    # B3 coefficients from ne/balmod.f DATA statement, indexed by species idx.
    # Used in BAGMOD: GMOD = max(0.5, exp(-B3 * BAL))
    _B3_BY_IDX = {
        1: 0.012785, 2: 0.018831, 3: 0.013427,
        4: 0.011942, 5: 0.011942, 6: 0.011942, 7: 0.011942,
        8: 0.017300, 9: 0.015496, 10: 0.017300, 11: 0.016835,
        12: 0.012329, 13: 0.012329, 14: 0.012329, 15: 0.012329,
        16: 0.009149, 17: 0.009149,
        18: 0.016835, 19: 0.016835, 20: 0.016835, 21: 0.016835,
        22: 0.016835, 23: 0.016835, 24: 0.016835, 25: 0.016835,
        26: 0.016191,
        27: 0.016240, 28: 0.016240, 29: 0.016240,
        30: 0.019046, 31: 0.019046, 32: 0.019046,
        33: 0.023978, 34: 0.023978,
        35: 0.015963, 36: 0.015963, 37: 0.015963, 38: 0.015963, 39: 0.015963,
        40: 0.013029,
        41: 0.015004, 42: 0.015004, 43: 0.015004, 44: 0.015004, 45: 0.015004,
        46: 0.019904, 47: 0.019904, 48: 0.019904,
        49: 0.016877, 50: 0.016877, 51: 0.016877, 52: 0.016877, 53: 0.016877,
        54: 0.016537,
        55: 0.014235, 56: 0.014235, 57: 0.014235, 58: 0.014235, 59: 0.014235,
        60: 0.018560, 61: 0.018560, 62: 0.018560, 63: 0.018560,
        64: 0.013762, 65: 0.013762, 66: 0.013762,
        67: 0.018024, 68: 0.018024,
        69: 0.020843, 70: 0.020843,
        71: 0.020653, 72: 0.020653, 73: 0.020653, 74: 0.020653, 75: 0.020653,
        76: 0.020653, 77: 0.020653, 78: 0.020653, 79: 0.020653, 80: 0.020653,
        81: 0.020653, 82: 0.020653, 83: 0.020653, 84: 0.020653, 85: 0.020653,
        86: 0.020653, 87: 0.020653, 88: 0.020653, 89: 0.020653, 90: 0.020653,
        91: 0.020653, 92: 0.020653, 93: 0.020653, 94: 0.020653, 95: 0.020653,
        96: 0.020653, 97: 0.020653,
        98: 0.011620, 99: 0.011620, 100: 0.011620, 101: 0.011620,
        102: 0.011620, 103: 0.011620, 104: 0.011620, 105: 0.011620,
        106: 0.011620, 107: 0.011620, 108: 0.011620,
    }

    # Fallback parameters for key NE species (from dgf.f)
    FALLBACK_PARAMETERS = {
        'RM': {  # Red Maple
            'B1': 0.0007906,
            'B2': 0.0651982,
        },
        'SM': {  # Sugar Maple
            'B1': 0.0007439,
            'B2': 0.0706905,
        },
        'WP': {  # Eastern White Pine
            'B1': 0.0011303,
            'B2': 0.0934796,
        },
        'RO': {  # Northern Red Oak
            'B1': 0.0008920,
            'B2': 0.0979702,
        },
        'YB': {  # Yellow Birch
            'B1': 0.0006668,
            'B2': 0.0768212,
        },
        'AB': {  # American Beech
            'B1': 0.0006911,
            'B2': 0.0730441,
        },
        'EH': {  # Eastern Hemlock
            'B1': 0.0008737,
            'B2': 0.0940538,
        },
        'BF': {  # Balsam Fir
            'B1': 0.0008829,
            'B2': 0.0602785,
        },
        'RS': {  # Red Spruce
            'B1': 0.0008236,
            'B2': 0.0549439,
        },
        'WA': {  # White Ash
            'B1': 0.0008992,
            'B2': 0.0925395,
        },
    }

    def __init__(self, species_code: str = None, variant: str = 'NE'):
        """Initialize the NE diameter growth model.

        Args:
            species_code: Species code (e.g., 'RM', 'SM', 'WP').
                         Defaults to DEFAULT_SPECIES (RM).
            variant: FVS variant (should be 'NE' for this model)
        """
        self.variant = variant
        super().__init__(species_code)

    def _get_coefficient_data(self) -> Dict[str, Any]:
        """Load coefficient data from JSON file using ConfigLoader with caching.

        Returns:
            Dictionary containing the full coefficient file data.
        """
        try:
            return load_coefficient_file(self.COEFFICIENT_FILE, variant='NE')
        except FileNotFoundError:
            return {}

    def _calculate_bagmod(self, bal: float) -> float:
        """Calculate basal area growth modifier based on competition.

        Implements the BALMOD subroutine from ne/balmod.f:
            GMOD = max(0.5, exp(-B3 * BAL))

        where B3 is a species-specific coefficient.

        Args:
            bal: Basal area in larger trees (sq ft/acre)

        Returns:
            BAGMOD: Growth modifier (0.5-1.0)
        """
        if bal <= 0:
            return 1.0

        # Get B3 for this species from the idx-keyed lookup
        b3 = self._get_b3()

        gmod = math.exp(-b3 * bal)
        return max(0.5, gmod)

    def _get_b3(self) -> float:
        """Get B3 coefficient for this species from balmod.f DATA array."""
        # Look up by species idx from coefficient data
        idx = self.coefficients.get('idx', 0)
        if idx > 0 and idx in self._B3_BY_IDX:
            return self._B3_BY_IDX[idx]
        # Default: use RM value (species 26) as fallback
        return 0.016191

    def calculate_dds(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        bal: float,
        time_step: float = 10.0
    ) -> float:
        """Calculate diameter squared increment (DDS).

        The NE variant uses an iterative basal area growth approach:
            POTBAG = B1 * SI * (1 - exp(-B2 * DBH))
            Growth = POTBAG * 0.7 * BAGMOD

        Per the FVS dgf.f source, this iterates once per year in the cycle,
        with diameter updating each iteration. This accumulates growth over
        the time step.

        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio as proportion (0-1)
            site_index: Site index (base age 50 for NE) in feet
            ba: Stand basal area (sq ft/acre)
            bal: Basal area in larger trees (sq ft/acre)
            time_step: Growth period in years (default 10 for NE)

        Returns:
            DDS: Change in diameter squared (sq inches outside bark)
        """
        p = self.coefficients

        # Get coefficients
        b1 = p.get('B1', 0.0008)
        b2 = p.get('B2', 0.08)

        # Ensure valid inputs
        current_dbh = max(0.1, dbh)
        si_safe = max(20.0, site_index)

        # Number of annual iterations
        num_years = int(time_step)

        # Iterate once per year, updating diameter each year
        # This matches the FVS dgf.f DO 1000 ILOOP=1,10 loop
        for _ in range(num_years):
            # Calculate potential basal area growth for this year
            # POTBAG = B1 * SI * (1 - exp(-B2 * DBH))
            potbag = b1 * si_safe * (1.0 - math.exp(-b2 * current_dbh))

            # Apply 0.7 modifier (as in dgf.f line 132)
            potbag = potbag * 0.7

            # Get BAL modifier: GMOD = max(0.5, exp(-B3*BAL))
            # Fortran calls BALMOD each iteration (BAL from diameter class)
            # PyFVS uses stand-level BAL (close approximation)
            bagmod = self._calculate_bagmod(bal)

            # Fortran dgf.f line 145: DELD = POTBAG * BAGMOD (no CR term)
            deld = potbag * bagmod

            # Fortran dgf.f line 148-150:
            # QTRBA = DELD + (D*D*.0054542)
            # QDBH = (QTRBA/.0054542)**.5
            qtrba = deld + (current_dbh * current_dbh * 0.0054542)
            current_dbh = math.sqrt(qtrba / 0.0054542)

        # DDS is the change in diameter squared over the whole period
        dds = max(0.0, current_dbh ** 2 - dbh ** 2)

        # Apply reasonable bounds
        # Max DDS ~ 50 sq in corresponds to ~3.5" growth per decade for 10" tree
        dds = min(50.0, dds)

        return dds

    def calculate_diameter_growth(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        bal: float,
        bark_ratio: float = 0.9,
        time_step: float = 10.0
    ) -> float:
        """Calculate diameter growth in inches.

        Converts DDS to actual diameter increment, applying bark ratio
        to work with inside-bark measurements like FVS.

        Args:
            dbh: Current DBH (outside bark) in inches
            crown_ratio: Crown ratio as proportion (0-1)
            site_index: Site index (base age 50) in feet
            ba: Stand basal area (sq ft/acre)
            bal: Basal area in larger trees (sq ft/acre)
            bark_ratio: DIB/DOB ratio (default 0.9)
            time_step: Growth period in years (default 10)

        Returns:
            Diameter increment in inches (outside bark)
        """
        # Calculate DDS
        dds = self.calculate_dds(
            dbh=dbh,
            crown_ratio=crown_ratio,
            site_index=site_index,
            ba=ba,
            bal=bal,
            time_step=time_step
        )

        # NE iterates in OB space (Fortran dgf.f lines 127-151),
        # so DDS is already an OB quantity. Apply directly to OB diameter.
        dbh_new = math.sqrt(dbh * dbh + dds)

        # Return the OB increment
        return max(0.0, dbh_new - dbh)


# Module-level cache for model instances
_model_cache: Dict[str, NEDiameterGrowthModel] = {}


def create_ne_diameter_growth_model(species_code: str = 'RM') -> NEDiameterGrowthModel:
    """Factory function to create a cached NE diameter growth model.

    Args:
        species_code: Species code (e.g., 'RM', 'SM', 'WP')

    Returns:
        Cached NEDiameterGrowthModel instance
    """
    species_upper = species_code.upper()
    if species_upper not in _model_cache:
        _model_cache[species_upper] = NEDiameterGrowthModel(species_upper)
    return _model_cache[species_upper]


def calculate_ne_diameter_growth(
    dbh: float,
    crown_ratio: float,
    site_index: float,
    ba: float,
    bal: float,
    species_code: str = 'RM',
    bark_ratio: float = 0.9,
    time_step: float = 10.0
) -> float:
    """Convenience function to calculate NE diameter growth.

    Args:
        dbh: Current DBH (outside bark) in inches
        crown_ratio: Crown ratio as proportion (0-1)
        site_index: Site index (base age 50) in feet
        ba: Stand basal area (sq ft/acre)
        bal: Basal area in larger trees (sq ft/acre)
        species_code: Species code (default 'RM' - Red Maple)
        bark_ratio: DIB/DOB ratio (default 0.9)
        time_step: Growth period in years (default 10)

    Returns:
        Diameter increment in inches (outside bark)
    """
    model = create_ne_diameter_growth_model(species_code)
    return model.calculate_diameter_growth(
        dbh=dbh,
        crown_ratio=crown_ratio,
        site_index=site_index,
        ba=ba,
        bal=bal,
        bark_ratio=bark_ratio,
        time_step=time_step
    )

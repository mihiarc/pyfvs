"""
Central States (CS) variant diameter growth model.

Thin subclass of the Lake States (LS) model — identical ln(DDS) equation,
different coefficients.

CS equation (same form as LS):
    ln(DDS) = INTERC + VDBHC/D + DBHC*D + DBH2C*D² + RDBHC*RELDBH
              + RDBHSQC*RELDBH² + CRWNC*CR + CRSQC*CR² + SBAC*BA + BALC*BAL + SITEC*SI

Key differences from LS:
    - 96 species covering IL, IN, IA, MO (Midwest hardwood forests)
    - Different species coefficient file

Source: FVS Central States Variant dgf.f, USDA Forest Service
"""
import random
from typing import Dict, Any

from .ls_diameter_growth import LSDiameterGrowthModel
from .config_loader import load_coefficient_file


class CSDiameterGrowthModel(LSDiameterGrowthModel):
    """Central States variant diameter growth model.

    Inherits the ln(DDS) equation from LSDiameterGrowthModel, overriding
    only the coefficient file and default species.
    """

    COEFFICIENT_FILE = 'cs/cs_diameter_growth_coefficients.json'
    COEFFICIENT_KEY = 'coefficients'
    DEFAULT_SPECIES = 'WO'  # White Oak is the default site species for CS

    # Fortran cs/dgf.f:461-476 per-species QMDGE5 caps. These override the
    # LS-inherited _QMDGE5_CAPS (which apply LS values to CS species that
    # share codes) — many LS caps don't apply to CS and vice versa. For
    # example LS caps SH=13, but CS Fortran caps SH=25.
    _QMDGE5_CAPS = {
        # cs/dgf.f:462 CASE(50) BO: 12
        'BO': 12.0,
        # cs/dgf.f:464 CASE(3, 10:13) SP, TL, TS, WT, BG: 13
        'SP': 13.0, 'TL': 13.0, 'TS': 13.0, 'WT': 13.0, 'BG': 13.0,
        # cs/dgf.f:466 CASE(14:17, 28, 53:56) HS, SH, SL, MH, EC, CK, SW, BR, SN: 25
        'HS': 25.0, 'SH': 25.0, 'SL': 25.0, 'MH': 25.0,
        'EC': 25.0, 'CK': 25.0, 'SW': 25.0, 'BR': 25.0, 'SN': 25.0,
        # cs/dgf.f:468 CASE(24) AB: 40
        'AB': 40.0,
        # cs/dgf.f:470 CASE(51) SO: 11
        'SO': 11.0,
        # cs/dgf.f:472 CASE(44:46, 59) AS, WA, GA, CO: 20
        'AS': 20.0, 'WA': 20.0, 'GA': 20.0, 'CO': 20.0,
        # cs/dgf.f:474 CASE(48:49) RO, SK: 30
        'RO': 30.0, 'SK': 30.0,
        # cs/dgf.f:476 CASE(91) OO: 17
        'OO': 17.0,
    }

    # Fortran cs/dgf.f:482-493 per-species CR caps (percentage, 0-100).
    _CR_PCT_CAPS = {
        # cs/dgf.f:483 CASE(7) WP: 50
        'WP': 50.0,
        # cs/dgf.f:485 CASE(8:10) WN, BN, TL: 75
        'WN': 75.0, 'BN': 75.0, 'TL': 75.0,
        # cs/dgf.f:487 CASE(28, 41) EC, YP: 60
        'EC': 60.0, 'YP': 60.0,
        # cs/dgf.f:489 CASE(44:46) AS, WA, GA: 80
        'AS': 80.0, 'WA': 80.0, 'GA': 80.0,
        # cs/dgf.f:491 CASE(32, 78:84) BC, SY, BY, RB, SU, WI, BL: 85
        # (Fortran position 78 is a blank — OL in pyfvs; rows 79-84 are
        # SY, BY, RB, SU, WI, BL)
        'BC': 85.0, 'SY': 85.0, 'BY': 85.0, 'RB': 85.0,
        'SU': 85.0, 'WI': 85.0, 'BL': 85.0,
    }

    # Fallback parameters for key CS species (from dgf.f)
    FALLBACK_PARAMETERS = {
        'WO': {  # White Oak
            'INTERC': 0.26619,
            'VDBHC': 0.0,
            'DBHC': 0.0,
            'DBH2C': 0.01581,
            'RDBHC': 2.05379,
            'RDBHSQC': -0.10706,
            'SBAC': 0.0,
            'BALC': -0.00404,
            'CRWNC': 0.02135,
            'CRSQC': 0.0,
            'SITEC': 0.0,
        },
        'RO': {  # Northern Red Oak
            'INTERC': 0.86285,
            'VDBHC': 0.0,
            'DBHC': 0.0,
            'DBH2C': 0.00697,
            'RDBHC': 2.20892,
            'RDBHSQC': -0.17316,
            'SBAC': -0.00178,
            'BALC': -0.00399,
            'CRWNC': 0.02196,
            'CRSQC': 0.0,
            'SITEC': 0.0,
        },
        'SM': {  # Sugar Maple
            'INTERC': 0.78100,
            'VDBHC': 0.0,
            'DBHC': 0.0,
            'DBH2C': 0.01029,
            'RDBHC': 1.69350,
            'RDBHSQC': -0.10450,
            'SBAC': -0.00101,
            'BALC': -0.00324,
            'CRWNC': 0.02033,
            'CRSQC': 0.0,
            'SITEC': 0.0,
        },
        'WN': {  # Black Walnut
            'INTERC': 0.35979,
            'VDBHC': 0.0,
            'DBHC': 0.0,
            'DBH2C': 0.01134,
            'RDBHC': 2.00810,
            'RDBHSQC': -0.07997,
            'SBAC': 0.0,
            'BALC': -0.00340,
            'CRWNC': 0.01929,
            'CRSQC': 0.0,
            'SITEC': 0.0,
        },
        'YP': {  # Yellow-Poplar (Tuliptree)
            'INTERC': 1.08040,
            'VDBHC': -4.87000,
            'DBHC': 0.0,
            'DBH2C': 0.01085,
            'RDBHC': 1.34170,
            'RDBHSQC': -0.02746,
            'SBAC': 0.0,
            'BALC': -0.00340,
            'CRWNC': 0.02139,
            'CRSQC': 0.0,
            'SITEC': 0.0,
        },
        'SP': {  # Shortleaf Pine
            'INTERC': 0.64882,
            'VDBHC': 0.0,
            'DBHC': 0.0,
            'DBH2C': 0.01234,
            'RDBHC': 2.87386,
            'RDBHSQC': -0.20916,
            'SBAC': -0.00162,
            'BALC': -0.00318,
            'CRWNC': 0.02252,
            'CRSQC': 0.0,
            'SITEC': 0.0,
        },
    }

    def __init__(self, species_code: str = None, variant: str = 'CS'):
        """Initialize the CS diameter growth model.

        Args:
            species_code: Species code (e.g., 'WO', 'RO', 'SM').
                         Defaults to DEFAULT_SPECIES (WO).
            variant: FVS variant (should be 'CS' for this model)
        """
        super().__init__(species_code, variant=variant)

    def _get_coefficient_data(self) -> Dict[str, Any]:
        """Load CS-specific coefficient data."""
        try:
            return load_coefficient_file(self.COEFFICIENT_FILE, variant='CS')
        except FileNotFoundError:
            return {}


# Module-level cache for model instances
_model_cache: Dict[str, CSDiameterGrowthModel] = {}


def create_cs_diameter_growth_model(species_code: str = 'WO') -> CSDiameterGrowthModel:
    """Factory function to create a cached CS diameter growth model.

    Args:
        species_code: Species code (e.g., 'WO', 'RO', 'SM')

    Returns:
        Cached CSDiameterGrowthModel instance
    """
    species_upper = species_code.upper()
    if species_upper not in _model_cache:
        _model_cache[species_upper] = CSDiameterGrowthModel(species_upper)
    return _model_cache[species_upper]


def calculate_cs_diameter_growth(
    dbh: float,
    crown_ratio: float,
    site_index: float,
    ba: float,
    bal: float,
    species_code: str = 'WO',
    bark_ratio: float = 0.9,
    qmd_ge5: float = None,
    time_step: float = 10.0,
    rng: random.Random = None
) -> float:
    """Convenience function to calculate CS diameter growth.

    Args:
        dbh: Current DBH (outside bark) in inches
        crown_ratio: Crown ratio as proportion (0-1)
        site_index: Site index (base age 50) in feet
        ba: Stand basal area (sq ft/acre)
        bal: Basal area in larger trees (sq ft/acre)
        species_code: Species code (default 'WO' - White Oak)
        bark_ratio: DIB/DOB ratio (default 0.9)
        qmd_ge5: QMD of trees >= 5" DBH
        time_step: Growth period in years (default 10)

    Returns:
        Diameter increment in inches (outside bark)
    """
    model = create_cs_diameter_growth_model(species_code)
    return model.calculate_diameter_growth(
        dbh=dbh,
        crown_ratio=crown_ratio,
        site_index=site_index,
        ba=ba,
        bal=bal,
        bark_ratio=bark_ratio,
        qmd_ge5=qmd_ge5,
        time_step=time_step,
        rng=rng
    )

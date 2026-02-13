"""
ORGANON Pacific Northwest (OP) variant diameter growth model.

Implements the ORGANON diameter growth equation for the FVS OP variant.
Unlike other FVS variants which predict DDS (diameter squared increment),
ORGANON predicts diameter growth directly using a logarithmic model.

ORGANON equation form:
    ln(DG) = B0 + B1*ln(DBH+K1) + B2*DBH^K2 + B3*ln((CR+0.2)/1.2)
             + B4*ln(SI-4.5) + B5*(BAL^K3/ln(DBH+K4)) + B6*sqrt(BA)

where:
    - DG = 5-year diameter growth (inches)
    - DBH = diameter at breast height (inches)
    - CR = crown ratio (0-1)
    - SI = site index (King's 1966 for Douglas-fir)
    - BAL = basal area in larger trees (sq ft/acre)
    - BA = total stand basal area (sq ft/acre)
    - K1, K2, K3, K4 = shape parameters (typically K1=1, K2=2, K3=2, K4=5)
    - B0-B6 = species-specific coefficients

ORGANON versions:
    - SWO (Southwest Oregon): 18 species, version=1
    - NWO (Northwest Oregon): 11 species, version=2
    - SMC (Stand Management Cooperative): 11 species, version=3
    - RAP (Red Alder Plantation): 7 species, version=4

Source:
    - Hann, D.W. et al. (2006). Reanalysis of SMC-ORGANON equations for
      diameter-growth rate, height-growth rate, and mortality rate.
    - Zumrawi, A.A. and D.W. Hann (1993). Diameter growth equations for
      Douglas-fir and grand fir in the western Willamette Valley of Oregon.
    - FVS ORGANON variant (diagro.f)
"""
import math
from typing import Dict, Any, Optional

from .model_base import ParameterizedModel


class OPDiameterGrowthModel(ParameterizedModel):
    """ORGANON Pacific Northwest variant diameter growth model.

    Calculates diameter growth using the ORGANON logarithmic model.
    This model predicts diameter growth directly (not DDS like other variants).

    Attributes:
        species_code: Species code (e.g., 'DF', 'WH', 'RC')
        version: ORGANON version (1=SWO, 2=NWO, 3=SMC, 4=RAP)
        coefficients: Species-specific coefficients for the growth equation
    """

    COEFFICIENT_FILE = 'op/op_diameter_growth_coefficients.json'
    COEFFICIENT_KEY = 'coefficients'
    DEFAULT_SPECIES = 'DF'  # Douglas-fir is the default species

    # ORGANON species groups (ISPGRP in ORGANON)
    # Maps FVS species codes to ORGANON species group indices
    SPECIES_TO_INDEX = {
        # Major conifers
        'DF': '1',   # Douglas-fir
        'GF': '2',   # Grand fir
        'WF': '2',   # White fir (same as GF)
        'PP': '3',   # Ponderosa pine
        'SP': '4',   # Sugar pine
        'IC': '5',   # Incense cedar
        'WH': '6',   # Western hemlock
        'RC': '7',   # Western red cedar
        'PY': '8',   # Pacific yew
        'MH': '9',   # Mountain hemlock
        'GC': '10',  # Giant chinkapin
        # Hardwoods
        'TA': '11',  # Tanoak
        'CL': '12',  # California laurel
        'BL': '13',  # Black cottonwood
        'WO': '14',  # Oregon white oak
        'BO': '15',  # Bigleaf maple
        'RA': '16',  # Red alder
        'PD': '17',  # Pacific dogwood
        'WI': '18',  # Willow
        # Other (mapped to similar species)
        'LP': '3',   # Lodgepole pine -> PP
        'NF': '2',   # Noble fir -> GF
        'RF': '2',   # Red fir -> GF
        'SF': '6',   # Silver fir -> WH
        'SS': '6',   # Sitka spruce -> WH
        'YC': '7',   # Alaska yellow cedar -> RC
        'OT': '18',  # Other -> WI
    }

    # Default shape parameters (K values)
    DEFAULT_K = {'K1': 1.0, 'K2': 2.0, 'K3': 2.0, 'K4': 5.0}

    # Fallback parameters from ORGANON research papers
    # Coefficients for NWO (Northwest Oregon) version
    FALLBACK_PARAMETERS = {
        'DF': {  # Douglas-fir (Zumrawi & Hann 1993, Hann et al. 2006)
            'B0': -4.69624,
            'B1': 0.339513,
            'B2': -0.00042826,
            'B3': 1.19952,
            'B4': 1.15612,
            'B5': -0.0000446327,
            'B6': -0.0237003,
            'K1': 1.0,
            'K2': 2.0,
            'K3': 2.0,
            'K4': 5.0,
            'ADJ': 1.0,
        },
        'WH': {  # Western hemlock
            'B0': -4.87447,
            'B1': 0.467436,
            'B2': -0.00053996,
            'B3': 1.25394,
            'B4': 1.12657,
            'B5': -0.0000399813,
            'B6': -0.0259158,
            'K1': 1.0,
            'K2': 2.0,
            'K3': 2.0,
            'K4': 5.0,
            'ADJ': 0.95,
        },
        'RC': {  # Western red cedar
            'B0': -4.58019,
            'B1': 0.285885,
            'B2': -0.00038193,
            'B3': 1.05378,
            'B4': 1.09628,
            'B5': -0.0000312098,
            'B6': -0.0198741,
            'K1': 1.0,
            'K2': 2.0,
            'K3': 2.0,
            'K4': 5.0,
            'ADJ': 0.90,
        },
        'GF': {  # Grand fir
            'B0': -4.52387,
            'B1': 0.358413,
            'B2': -0.00046789,
            'B3': 1.12684,
            'B4': 1.08732,
            'B5': -0.0000389241,
            'B6': -0.0221587,
            'K1': 1.0,
            'K2': 2.0,
            'K3': 2.0,
            'K4': 5.0,
            'ADJ': 0.95,
        },
        'RA': {  # Red alder
            'B0': -3.78215,
            'B1': 0.411684,
            'B2': -0.00089247,
            'B3': 0.87234,
            'B4': 0.95127,
            'B5': -0.0000521634,
            'B6': -0.0312147,
            'K1': 1.0,
            'K2': 2.0,
            'K3': 2.0,
            'K4': 5.0,
            'ADJ': 1.0,
        },
        'PP': {  # Ponderosa pine
            'B0': -4.42189,
            'B1': 0.312547,
            'B2': -0.00038941,
            'B3': 1.08964,
            'B4': 1.04218,
            'B5': -0.0000367524,
            'B6': -0.0189356,
            'K1': 1.0,
            'K2': 2.0,
            'K3': 2.0,
            'K4': 5.0,
            'ADJ': 0.92,
        },
        'WO': {  # Oregon white oak
            'B0': -4.15687,
            'B1': 0.287412,
            'B2': -0.00041523,
            'B3': 0.92147,
            'B4': 0.89654,
            'B5': -0.0000421896,
            'B6': -0.0274158,
            'K1': 1.0,
            'K2': 2.0,
            'K3': 2.0,
            'K4': 5.0,
            'ADJ': 0.85,
        },
        'BM': {  # Bigleaf maple
            'B0': -3.98521,
            'B1': 0.298741,
            'B2': -0.00052147,
            'B3': 0.89457,
            'B4': 0.87214,
            'B5': -0.0000478521,
            'B6': -0.0298745,
            'K1': 1.0,
            'K2': 2.0,
            'K3': 2.0,
            'K4': 5.0,
            'ADJ': 0.88,
        },
    }

    def __init__(self, species_code: str = "DF", version: int = 2):
        """Initialize the OP diameter growth model.

        Args:
            species_code: FVS species code (e.g., 'DF', 'WH', 'RC')
            version: ORGANON version (1=SWO, 2=NWO, 3=SMC, 4=RAP). Default: 2 (NWO)
        """
        self.version = version
        super().__init__(species_code)

    def _load_parameters(self) -> None:
        """Load species-specific parameters using species-to-index mapping.

        ORGANON uses species group indices, so we map species codes to
        coefficient indices before loading.
        """
        self.raw_data = self._get_coefficient_data()

        if self.raw_data:
            coeffs = self.raw_data.get(self.COEFFICIENT_KEY, {})

            # Get coefficient index for this species
            coef_idx = self.SPECIES_TO_INDEX.get(self.species_code.upper(), '1')

            # Try to get version-specific coefficients
            version_key = f"v{self.version}"
            if version_key in coeffs and coef_idx in coeffs[version_key]:
                self.coefficients = coeffs[version_key][coef_idx]
            elif coef_idx in coeffs:
                self.coefficients = coeffs[coef_idx]
            else:
                self._load_fallback_parameters()
        else:
            self._load_fallback_parameters()

    def calculate_diameter_growth(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        bal: float,
        time_step: float = 5.0
    ) -> float:
        """Calculate diameter growth using ORGANON model.

        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio (0-1)
            site_index: Site index (feet, King's 1966 base age 50)
            ba: Stand basal area (sq ft/acre)
            bal: Basal area in larger trees (sq ft/acre)
            time_step: Growth period in years (default 5)

        Returns:
            Diameter growth (inches) for the time period
        """
        # Get coefficients
        params = self.coefficients

        # Apply safety bounds
        dbh_safe = max(0.1, dbh)
        cr = max(0.05, min(0.95, crown_ratio))
        si = max(10.0, site_index)
        ba_bounded = max(1.0, min(500.0, ba))
        bal_bounded = max(0.0, min(400.0, bal))

        # Get coefficient values with defaults
        b0 = params.get('B0', -4.5)
        b1 = params.get('B1', 0.35)
        b2 = params.get('B2', -0.0004)
        b3 = params.get('B3', 1.1)
        b4 = params.get('B4', 1.1)
        b5 = params.get('B5', -0.00004)
        b6 = params.get('B6', -0.02)

        # Shape parameters
        k1 = params.get('K1', 1.0)
        k2 = params.get('K2', 2.0)
        k3 = params.get('K3', 2.0)
        k4 = params.get('K4', 5.0)

        # Species adjustment factor
        adj = params.get('ADJ', 1.0)

        # Calculate ln(DG) terms
        # LNDG = B0 + B1*ln(DBH+K1) + B2*DBH^K2 + B3*ln((CR+0.2)/1.2)
        #        + B4*ln(SI-4.5) + B5*(BAL^K3/ln(DBH+K4)) + B6*sqrt(BA)

        # Term 1: Intercept
        term0 = b0

        # Term 2: Diameter effect
        term1 = b1 * math.log(dbh_safe + k1)

        # Term 3: Diameter squared effect (typically negative)
        term2 = b2 * (dbh_safe ** k2)

        # Term 4: Crown ratio effect
        cr_transformed = (cr + 0.2) / 1.2
        term3 = b3 * math.log(cr_transformed)

        # Term 5: Site index effect
        si_adjusted = max(5.0, si - 4.5)
        term4 = b4 * math.log(si_adjusted)

        # Term 6: Competition effect (BAL interaction)
        if bal_bounded > 0:
            bal_term = (bal_bounded ** k3) / math.log(dbh_safe + k4)
            term5 = b5 * bal_term
        else:
            term5 = 0.0

        # Term 7: Stand density effect
        term6 = b6 * math.sqrt(ba_bounded)

        # Sum all terms
        ln_dg = term0 + term1 + term2 + term3 + term4 + term5 + term6

        # Convert from ln(DG) to DG (5-year growth)
        dg_5yr = math.exp(ln_dg)

        # Apply crown ratio adjustment for very low CR
        # CRADJ = 1.0 if CR > 0.17, else 1.0 - exp(-(25*CR)^2)
        if cr <= 0.17:
            cradj = 1.0 - math.exp(-((25.0 * cr) ** 2))
        else:
            cradj = 1.0

        # Apply adjustments
        dg_5yr = dg_5yr * cradj * adj

        # Scale by time step (base is 5 years)
        dg = dg_5yr * (time_step / 5.0)

        # Ensure non-negative growth
        return max(0.0, dg)


# Module-level cache for model instances
_model_cache: Dict[str, OPDiameterGrowthModel] = {}


def get_op_diameter_growth_model(
    species_code: str = "DF",
    version: int = 2
) -> OPDiameterGrowthModel:
    """Factory function to create a cached OP diameter growth model.

    Args:
        species_code: FVS species code (default 'DF' for Douglas-fir)
        version: ORGANON version (1=SWO, 2=NWO, 3=SMC, 4=RAP). Default: 2

    Returns:
        Cached OPDiameterGrowthModel instance
    """
    cache_key = f"{species_code.upper()}_{version}"
    if cache_key not in _model_cache:
        _model_cache[cache_key] = OPDiameterGrowthModel(species_code, version)
    return _model_cache[cache_key]


# Alias for consistency with other modules
create_op_diameter_growth_model = get_op_diameter_growth_model

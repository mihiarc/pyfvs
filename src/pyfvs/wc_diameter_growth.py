"""
West Cascades (WC) variant diameter growth model.

Thin subclass of the Pacific Northwest Coast (PN) model — identical ln(DDS)
equation with topographic effects, different coefficients and IFOR index.

WC equation (same form as PN):
    ln(DDS) = CONSPP + DGLD*ln(D) + CR*(DGCR + CR*DGCRSQ) + DGDS*D²
              + DGDBAL*BAL/ln(D+1) + DGPCCF*PCCF + DGHAH*RELHT
              + DGLBA*ln(BA) + DGBAL*BAL + DGBA*BA + DGSITE*ln(SI)
              + DGEL*ELEV + DGEL2*ELEV² + DGSLOP*SLOPE + DGSLSQ*SLOPE²
              + DGSASP*SLOPE*sin(ASPECT) + DGCASP*SLOPE*cos(ASPECT)

Key differences from PN:
    - 19 coefficient sets for 37 species
    - Default IFOR=6 (index 5) for forest location intercept
    - Default elevation = 20 (hundreds of feet) vs PN's 10
    - Different species-to-group mapping

Source: FVS West Cascades Variant dgf.f, USDA Forest Service
"""
from typing import Dict, Any

from .pn_diameter_growth import PNDiameterGrowthModel
from .config_loader import load_coefficient_file


class WCDiameterGrowthModel(PNDiameterGrowthModel):
    """West Cascades variant diameter growth model.

    Inherits the ln(DDS) equation from PNDiameterGrowthModel, overriding
    only coefficient file, IFOR index, elevation default, species mapping,
    and fallback parameters.
    """

    COEFFICIENT_FILE = 'wc/wc_diameter_growth_coefficients.json'
    COEFFICIENT_KEY = 'coefficient_sets'
    DEFAULT_SPECIES = 'DF'
    DEFAULT_ELEVATION = 20.0  # WC default: 2000 ft
    DEFAULT_IFOR_INDEX = 5  # IFOR=6 → array index 5

    # Fallback parameters for key WC species (from dgf.f)
    FALLBACK_PARAMETERS = {
        'DF': {  # Douglas-fir (group 7)
            'DGLD': 0.534138,
            'DGCR': 1.636854,
            'DGCRSQ': -0.045578,
            'DGSITE': 1.020863,
            'DGDBAL': -0.009363,
            'DGLBA': 0.0,
            'DGBA': -0.000215,
            'DGBAL': 0.0,
            'DGPCCF': 0.0,
            'DGHAH': 0.0,
            'DGFOR': [-2.750874, -2.787499, -2.672664, -2.533437, -2.693964, -2.718852],
            'DGDS': -0.0001039,
            'DGEL': -0.037591,
            'DGEL2': 0.000549,
            'DGSASP': -0.038992,
            'DGCASP': -0.080943,
            'DGSLOP': 0.077787,
            'DGSLSQ': -0.215778,
        },
        'WH': {  # Western Hemlock (group 9)
            'DGLD': 0.722462,
            'DGCR': 2.160348,
            'DGCRSQ': -0.834196,
            'DGSITE': 0.380416,
            'DGDBAL': -0.004065,
            'DGLBA': 0.0,
            'DGBA': 0.0,
            'DGBAL': 0.0,
            'DGPCCF': 0.0,
            'DGHAH': -0.000358,
            'DGFOR': [-0.298310, -0.147675, -0.006413, 0.0, 0.0, 0.0],
            'DGDS': -0.0001546,
            'DGEL': -0.040067,
            'DGEL2': 0.000395,
            'DGSASP': 0.0,
            'DGCASP': 0.0,
            'DGSLOP': 0.421486,
            'DGSLSQ': -0.693610,
        },
        'RC': {  # Western Red Cedar (group 8)
            'DGLD': 0.843013,
            'DGCR': 2.878032,
            'DGCRSQ': -1.631418,
            'DGSITE': 0.139734,
            'DGDBAL': -0.003923,
            'DGLBA': 0.0,
            'DGBA': 0.0,
            'DGBAL': 0.0,
            'DGPCCF': -0.000552,
            'DGHAH': 0.0,
            'DGFOR': [0.412763, 0.645645, 0.0, 0.0, 0.0, 0.0],
            'DGDS': -0.0000644,
            'DGEL': -0.050081,
            'DGEL2': 0.000660,
            'DGSASP': 0.0,
            'DGCASP': 0.0,
            'DGSLOP': 0.0,
            'DGSLSQ': 0.0,
        },
    }

    # Species mapping to coefficient groups (from MAPSPC in dgf.f)
    SPECIES_MAP = {
        'SF': '1', 'WF': '2', 'GF': '2', 'AF': '3', 'RF': '17',
        'NF': '4', 'YC': '15', 'IC': '11', 'ES': '11', 'LP': '16',
        'JP': '6', 'SP': '5', 'WP': '5', 'PP': '6', 'DF': '7',
        'RW': '19', 'RC': '8', 'WH': '9', 'MH': '10', 'BM': '12',
        'RA': '13', 'WA': '14', 'PB': '14', 'GC': '14', 'AS': '14',
        'CW': '14', 'WO': '18', 'WJ': '14', 'LL': '11', 'WB': '11',
        'KP': '11', 'PY': '11', 'DG': '14', 'HT': '14', 'CH': '14',
        'WI': '14', 'OT': '14'
    }

    def _get_coefficient_data(self) -> Dict[str, Any]:
        """Load WC-specific coefficient data."""
        try:
            return load_coefficient_file(self.COEFFICIENT_FILE, variant='WC')
        except FileNotFoundError:
            return {}


# Module-level cache for model instances
_model_cache: Dict[str, WCDiameterGrowthModel] = {}


def create_wc_diameter_growth_model(species_code: str = "DF") -> WCDiameterGrowthModel:
    """Factory function to create a cached WC diameter growth model.

    Args:
        species_code: FVS species code (e.g., 'DF', 'WH', 'RC')

    Returns:
        Cached WCDiameterGrowthModel instance
    """
    species_upper = species_code.upper()
    if species_upper not in _model_cache:
        _model_cache[species_upper] = WCDiameterGrowthModel(species_upper)
    return _model_cache[species_upper]

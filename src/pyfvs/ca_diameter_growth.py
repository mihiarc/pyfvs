"""
Inland California (CA) variant diameter growth model.

Implements the DDS (diameter squared increment) equation for the FVS Inland California variant.
The CA variant uses ln(DDS) transformation with 13 different equation sets:

CA equation (standard form):
    ln(DDS) = CONSPP + DGLD*ln(D) + CR*(DGCR + CR*DGCRSQ) + DGDSQ*D²
            + DGDBAL*BAL/ln(D+1) + DGPCCF*PCCF + DGHAH*RELHT
            + DGLBA*ln(BA) + DGBAL*BAL + DGSITE*ln(SI)
            + topographic corrections (elevation, slope, aspect)

where:
    - CONSPP = forest location intercept (DGFOR array, 5 classes)
    - D = DBH (inches)
    - CR = crown ratio (0-1 scale)
    - BA = stand basal area (sq ft/acre)
    - BAL = basal area in larger trees (sq ft/acre)
    - PCCF = point crown competition factor
    - RELHT = relative height (tree height / average stand height)
    - SI = site index (base age 50)

Special equations:
    - Equation 12 (Giant Sequoia, Redwood): ln(DDS) = -3.502444 + 0.415435*ln(SI)
    - Equation 13 (Tanoak): 5-year model scaled to 10-year

Key characteristics:
    - Covers inland California and southern Cascades
    - 50 species mapped to 13 equation sets
    - Uses ln(DDS) transformation
    - Includes elevation, slope, aspect effects
    - 10-year base cycle

Source: FVS Inland California Variant dgf.f, USDA Forest Service
"""
import math
from typing import Dict, Any

from .model_base import ParameterizedModel
from .config_loader import load_coefficient_file

__all__ = [
    'CADiameterGrowthModel',
    'create_ca_diameter_growth_model',
    'calculate_ca_diameter_growth',
]


class CADiameterGrowthModel(ParameterizedModel):
    """Inland California variant diameter growth model.

    Calculates diameter squared increment (DDS) using the CA variant equation.
    Uses ln(DDS) transformation with species-specific equation assignments.

    Attributes:
        species_code: Species code (e.g., 'DF', 'PP', 'WF')
        coefficients: Species-specific coefficients for the ln(DDS) equation
        equation_num: Which of the 13 equations applies to this species
    """

    COEFFICIENT_FILE = 'ca/ca_diameter_growth_coefficients.json'
    COEFFICIENT_KEY = 'species'
    DEFAULT_SPECIES = 'PP'  # Ponderosa Pine is common in CA

    # Fallback parameters for key CA species
    # SIGMAR values from blkdat.f for stochastic diameter growth (49 species)
    _SIGMA = {
        'PC': 0.4936, 'IC': 0.4936, 'RC': 0.4936, 'WF': 0.4391, 'RF': 0.4112,
        'SH': 0.4112, 'DF': 0.4791, 'WH': 0.4687, 'MH': 0.4687, 'WB': 0.4169,
        'KP': 0.4392, 'LP': 0.4169, 'CP': 0.4392, 'LM': 0.4392, 'JP': 0.4458,
        'SP': 0.4687, 'WP': 0.4745, 'PP': 0.4458, 'MP': 0.4458, 'GP': 0.4392,
        'WJ': 0.4392, 'BR': 0.4391, 'GS': 0.4408, 'PY': 0.4392, 'OS': 0.4458,
        'LO': 0.5998, 'CY': 0.5998, 'BL': 0.5998, 'EO': 0.5998, 'WO': 0.5998,
        'BO': 0.5998, 'VO': 0.5998, 'IO': 0.5998, 'BM': 0.5998, 'BU': 0.5998,
        'RA': 0.5998, 'MA': 0.6608, 'GC': 0.6608, 'DG': 0.6608, 'FL': 0.5998,
        'WN': 0.5998, 'TO': 0.5166, 'SY': 0.5998, 'AS': 0.5998, 'CW': 0.5998,
        'WI': 0.5998, 'CN': 0.4392, 'CL': 0.5998, 'OH': 0.5998,
    }

    FALLBACK_PARAMETERS = {
        'PP': {  # Ponderosa Pine - equation 9
            'equation': 9,
            'DGLD': 0.738750,
            'DGCR': 3.454857,
            'DGCRSQ': -1.773805,
            'DGDSQ': -0.0004708,
            'DGSITE': 1.011504,
            'DGDBAL': -0.013091,
            'DGLBA': -0.131185,
            'DGBAL': 0.0,
            'DGPCCF': -0.000593,
            'DGHAH': 0.0,
            'DGFOR': [-2.568986, -2.465393, -2.465393, -2.390050, -2.390050],
        },
        'DF': {  # Douglas-fir - equation 4
            'equation': 4,
            'DGLD': 0.716226,
            'DGCR': 3.272451,
            'DGCRSQ': -1.642904,
            'DGDSQ': -0.0002723,
            'DGSITE': 0.759305,
            'DGDBAL': -0.008787,
            'DGLBA': -0.028564,
            'DGBAL': 0.0,
            'DGPCCF': -0.000224,
            'DGHAH': 0.0,
            'DGFOR': [-2.368706, -2.228135, -2.228135, -2.175635, -2.175635],
        },
        'WF': {  # White Fir - equation 2
            'equation': 2,
            'DGLD': 1.182104,
            'DGCR': 2.856578,
            'DGCRSQ': -1.093354,
            'DGDSQ': -0.0006362,
            'DGSITE': 0.365679,
            'DGDBAL': -0.005992,
            'DGLBA': -0.058039,
            'DGBAL': 0.0,
            'DGPCCF': -0.001014,
            'DGHAH': 0.0,
            'DGFOR': [-2.108357, 0.0, 0.0, 0.0, 0.0],
        },
    }

    def __init__(self, species_code: str = None, variant: str = 'CA'):
        """Initialize the CA diameter growth model.

        Args:
            species_code: Species code (e.g., 'DF', 'PP', 'WF').
                         Defaults to DEFAULT_SPECIES (PP).
            variant: FVS variant (should be 'CA' for this model)
        """
        self.variant = variant
        self._equation_map = None
        self._equations = None
        super().__init__(species_code)

    def _get_coefficient_data(self) -> Dict[str, Any]:
        """Load coefficient data from JSON file using ConfigLoader with caching.

        Returns:
            Dictionary containing the full coefficient file data.
        """
        try:
            data = load_coefficient_file(self.COEFFICIENT_FILE, variant='CA')
            # Cache the equation map and equations for later use
            self._equation_map = data.get('species_equation_map', {})
            self._equations = data.get('equations', {})
            return data
        except FileNotFoundError:
            return {}

    def _get_species_coefficients(self) -> Dict[str, Any]:
        """Get coefficients for the species based on its equation assignment.

        Returns:
            Dictionary of coefficients for this species' equation.
        """
        # Load full coefficient data if not already loaded
        if self._equation_map is None or self._equations is None:
            self._get_coefficient_data()

        # Get the equation number for this species
        species_upper = self.species_code.upper() if self.species_code else self.DEFAULT_SPECIES
        equation_num = self._equation_map.get(species_upper, 9)  # Default to equation 9

        # Get the coefficients for this equation
        equation_key = str(equation_num)
        if equation_key in self._equations:
            return self._equations[equation_key]

        # Fallback to default
        return self.FALLBACK_PARAMETERS.get(species_upper, self.FALLBACK_PARAMETERS['PP'])

    def calculate_dds(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        bal: float,
        pccf: float = None,
        relht: float = 1.0,
        elevation: float = 0.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        forest_class: int = 1,
        time_step: float = 10.0,
        rng=None
    ) -> float:
        """Calculate diameter squared increment (DDS).

        The CA variant uses a 10-year base period with ln(DDS) transformation.

        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio as proportion (0-1)
            site_index: Site index (base age 50 for CA) in feet
            ba: Stand basal area (sq ft/acre)
            bal: Basal area in larger trees (sq ft/acre)
            pccf: Point crown competition factor (default: estimated from BA)
            relht: Relative height (tree height / stand avg height, default 1.0)
            elevation: Elevation in feet (default 0)
            slope: Slope as proportion (0-1, default 0)
            aspect: Aspect in radians (default 0)
            forest_class: Forest location class 1-5 (default 1)
            time_step: Growth period in years (default 10 for CA)

        Returns:
            DDS: Change in diameter squared (sq inches inside bark)
        """
        # Get species-specific coefficients
        p = self._get_species_coefficients()

        # Get equation number for special handling
        species_upper = self.species_code.upper() if self.species_code else self.DEFAULT_SPECIES
        equation_num = self._equation_map.get(species_upper, 9) if self._equation_map else 9

        # Special handling for Giant Sequoia and Redwood (equation 12)
        if equation_num == 12:
            return self._calculate_dds_redwood(dbh, site_index, time_step)

        # Get coefficients
        dgld = p.get('DGLD', 0.7)
        dgcr = p.get('DGCR', 2.0)
        dgcrsq = p.get('DGCRSQ', -1.0)
        dgdsq = p.get('DGDSQ', -0.0003)
        dgsite = p.get('DGSITE', 0.5)
        dgdbal = p.get('DGDBAL', -0.005)
        dglba = p.get('DGLBA', -0.05)
        dgbal = p.get('DGBAL', 0.0)
        dgpccf = p.get('DGPCCF', -0.0005)
        dghah = p.get('DGHAH', 0.0)
        dgfor = p.get('DGFOR', [-2.5, -2.5, -2.5, -2.5, -2.5])

        # Topographic coefficients
        dgcasp = p.get('DGCASP', 0.0)
        dgsasp = p.get('DGSASP', 0.0)
        dgslop = p.get('DGSLOP', 0.0)
        dgel = p.get('DGEL', 0.0)
        dgelsq = p.get('DGELSQ', 0.0)

        # Ensure valid inputs
        dbh_safe = max(0.1, dbh)
        cr_safe = max(0.01, min(1.0, crown_ratio))
        si_safe = max(20.0, site_index)
        ba_safe = max(1.0, ba)
        bal_safe = max(0.0, bal)
        relht_safe = max(0.5, min(2.0, relht))

        # Estimate PCCF if not provided (rough approximation)
        if pccf is None:
            pccf = ba_safe * 1.5  # Simple approximation

        # Get forest intercept (0-indexed array, class 1 = index 0)
        forest_idx = max(0, min(4, forest_class - 1))
        conspp = dgfor[forest_idx] if isinstance(dgfor, list) else dgfor

        # Calculate ln(DDS) using CA equation
        ln_dds = conspp

        # Diameter terms
        ln_dds += dgld * math.log(dbh_safe)
        ln_dds += dgdsq * dbh_safe * dbh_safe

        # Crown ratio terms
        ln_dds += cr_safe * (dgcr + cr_safe * dgcrsq)

        # Site index term
        if dgsite != 0 and si_safe > 0:
            ln_dds += dgsite * math.log(si_safe)

        # Competition terms
        if dgdbal != 0 and dbh_safe > 0:
            ln_dds += dgdbal * bal_safe / math.log(dbh_safe + 1)

        if dglba != 0 and ba_safe > 0:
            ln_dds += dglba * math.log(ba_safe)

        if dgbal != 0:
            ln_dds += dgbal * bal_safe

        if dgpccf != 0:
            ln_dds += dgpccf * pccf

        # Relative height term
        if dghah != 0:
            ln_dds += dghah * relht_safe

        # Topographic terms
        elev_100 = elevation / 100.0  # Elevation in 100s of feet
        slope_pct = slope * 100.0  # Slope as percentage

        if dgel != 0:
            ln_dds += dgel * elev_100

        if dgelsq != 0:
            ln_dds += dgelsq * elev_100 * elev_100

        if dgslop != 0:
            ln_dds += dgslop * slope_pct

        if dgcasp != 0:
            ln_dds += dgcasp * slope_pct * math.cos(aspect)

        if dgsasp != 0:
            ln_dds += dgsasp * slope_pct * math.sin(aspect)

        # Stochastic or Baskerville correction
        sigma = self._SIGMA.get(
            self.species_code.upper() if self.species_code else 'PP', 0.45
        )
        if rng is not None:
            z = rng.gauss(0, sigma)
            z = max(-2 * sigma, min(2 * sigma, z))
            if ln_dds + z > 4.0:
                z *= max(0.0, 1.0 - (ln_dds + z - 4.0) / 2.0)
            ln_dds += z
        else:
            ln_dds += 0.88 * sigma * sigma / 2.0

        # Apply bounds on ln(DDS)
        ln_dds = max(-5.0, min(5.0, ln_dds))

        # Convert from ln(DDS) to DDS
        dds = math.exp(ln_dds)

        # Special scaling for Tanoak (equation 13) - 5-year model
        if equation_num == 13:
            dds = dds * 2.0  # Scale 5-year to 10-year

        # Scale for time step (CA is calibrated for 10-year periods)
        dds_scaled = dds * (time_step / 10.0)

        return dds_scaled

    def _calculate_dds_redwood(
        self,
        dbh: float,
        site_index: float,
        time_step: float = 10.0
    ) -> float:
        """Calculate DDS for Giant Sequoia and Redwood using special equation.

        Uses simplified form: ln(DDS) = -3.502444 + 0.415435*ln(SI)

        Args:
            dbh: Diameter at breast height (inches)
            site_index: Site index (base age 50) in feet
            time_step: Growth period in years

        Returns:
            DDS: Change in diameter squared
        """
        si_safe = max(20.0, site_index)

        # Special equation for RW/GS
        ln_dds = -3.502444 + 0.415435 * math.log(si_safe)

        # Apply bounds
        ln_dds = max(-5.0, min(5.0, ln_dds))

        dds = math.exp(ln_dds)
        dds_scaled = dds * (time_step / 10.0)

        return dds_scaled

    def calculate_diameter_growth(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        bal: float,
        bark_ratio: float = 0.9,
        pccf: float = None,
        relht: float = 1.0,
        elevation: float = 0.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        forest_class: int = 1,
        time_step: float = 10.0,
        rng=None
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
            pccf: Point crown competition factor
            relht: Relative height
            elevation: Elevation in feet
            slope: Slope as proportion (0-1)
            aspect: Aspect in radians
            forest_class: Forest location class 1-5
            time_step: Growth period in years (default 10)

        Returns:
            Diameter increment in inches (outside bark)
        """
        from .model_base import dds_to_diameter_growth

        dds = self.calculate_dds(
            dbh=dbh,
            crown_ratio=crown_ratio,
            site_index=site_index,
            ba=ba,
            bal=bal,
            pccf=pccf,
            relht=relht,
            elevation=elevation,
            slope=slope,
            aspect=aspect,
            forest_class=forest_class,
            time_step=time_step,
            rng=rng
        )

        return dds_to_diameter_growth(dds, dbh, bark_ratio)


# Module-level cache for model instances
_model_cache: Dict[str, CADiameterGrowthModel] = {}


def create_ca_diameter_growth_model(species_code: str = 'PP') -> CADiameterGrowthModel:
    """Factory function to create a cached CA diameter growth model.

    Args:
        species_code: Species code (e.g., 'DF', 'PP', 'WF')

    Returns:
        Cached CADiameterGrowthModel instance
    """
    species_upper = species_code.upper()
    if species_upper not in _model_cache:
        _model_cache[species_upper] = CADiameterGrowthModel(species_upper)
    return _model_cache[species_upper]


def calculate_ca_diameter_growth(
    dbh: float,
    crown_ratio: float,
    site_index: float,
    ba: float,
    bal: float,
    species_code: str = 'PP',
    bark_ratio: float = 0.9,
    pccf: float = None,
    relht: float = 1.0,
    elevation: float = 0.0,
    slope: float = 0.0,
    aspect: float = 0.0,
    forest_class: int = 1,
    time_step: float = 10.0
) -> float:
    """Convenience function to calculate CA diameter growth.

    Args:
        dbh: Current DBH (outside bark) in inches
        crown_ratio: Crown ratio as proportion (0-1)
        site_index: Site index (base age 50) in feet
        ba: Stand basal area (sq ft/acre)
        bal: Basal area in larger trees (sq ft/acre)
        species_code: Species code (default 'PP' - Ponderosa Pine)
        bark_ratio: DIB/DOB ratio (default 0.9)
        pccf: Point crown competition factor
        relht: Relative height
        elevation: Elevation in feet
        slope: Slope as proportion
        aspect: Aspect in radians
        forest_class: Forest location class 1-5
        time_step: Growth period in years (default 10)

    Returns:
        Diameter increment in inches (outside bark)
    """
    model = create_ca_diameter_growth_model(species_code)
    return model.calculate_diameter_growth(
        dbh=dbh,
        crown_ratio=crown_ratio,
        site_index=site_index,
        ba=ba,
        bal=bal,
        bark_ratio=bark_ratio,
        pccf=pccf,
        relht=relht,
        elevation=elevation,
        slope=slope,
        aspect=aspect,
        forest_class=forest_class,
        time_step=time_step
    )

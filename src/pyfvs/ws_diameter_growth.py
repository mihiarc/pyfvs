"""
Western Sierra Nevada (WS) variant diameter growth model.

This module implements the WS variant diameter growth equations based on
the FVS WS variant from the USDA Forest Service FMSC.

Equation form:
    ln(DDS) = DGFOR + DGLD*ln(D) + DGCR*CR + DGCRSQ*CR^2 + DGDS*D^2
            + DGSITE*ln(SI) + DGDBAL*BAL/ln(D+1) + DGBA*ln(BA)
            + DGPCCF*PCCF + DGHAH*RELHT
            + DGEL*ELEV + DGELSQ*ELEV^2 + DGSLOP*SLOPE + DGSLSQ*SLOPE^2
            + DGCASP*SLOPE*cos(ASP) + DGSASP*SLOPE*sin(ASP)

Where:
    DDS = change in squared diameter (inside bark)
    D = diameter at breast height (inches)
    CR = crown ratio (0-1)
    SI = site index (feet, base age 50)
    BA = basal area per acre (sq ft)
    BAL = basal area in larger trees (sq ft/acre)
    PCCF = point crown competition factor
    RELHT = relative height (tree height / top height)
    ELEV = elevation (100s of feet)
    SLOPE = slope (proportion 0-1)
    ASP = aspect (radians from north)

Special equations for Giant Sequoia and Redwood:
    ln(DDS) = -3.502444 + 0.415435*ln(SI)

References:
    USDA Forest Service, Forest Management Service Center, Fort Collins, CO
    FVS WS variant documentation
"""
import math
from typing import Dict, Any, Optional

from .model_base import ParameterizedModel

__all__ = [
    'WSDiameterGrowthModel',
    'create_ws_diameter_growth_model',
    'calculate_ws_dds',
]

# Module-level cache for model instances
_model_cache: Dict[str, 'WSDiameterGrowthModel'] = {}


class WSDiameterGrowthModel(ParameterizedModel):
    """WS variant diameter growth model using ln(DDS) equation form.

    The WS variant uses 14 equation sets for 43 species. Species are mapped
    to equation sets via the species_to_equation mapping in the coefficient file.
    """

    COEFFICIENT_FILE = 'ws/ws_diameter_growth_coefficients.json'
    COEFFICIENT_KEY = 'coefficients'
    DEFAULT_SPECIES = 'SP'  # Sugar Pine is the default for WS

    # Species to equation index mapping
    SPECIES_TO_INDEX = {
        'SP': '1', 'WP': '1', 'MH': '1',
        'DF': '2', 'BD': '2',
        'WF': '3', 'SF': '3',
        'GS': '4', 'RW': '4',
        'IC': '5',
        'JP': '6',
        'RF': '7', 'GB': '7',
        'PP': '8', 'MP': '8',
        'LP': '9', 'WB': '9',
        'PM': '10', 'KP': '10', 'FP': '10', 'CP': '10', 'LM': '10',
        'GP': '10', 'WE': '10', 'WJ': '10', 'UJ': '10', 'CJ': '10',
        'LO': '11', 'CY': '11', 'BL': '11', 'BO': '11', 'VO': '11', 'IO': '11', 'OH': '11',
        'TO': '12', 'GC': '12', 'AS': '12', 'CL': '12', 'MA': '12', 'DG': '12', 'BM': '12',
        'MC': '13',
        'OS': '14',
    }

    FALLBACK_PARAMETERS = {
        '1': {  # Sugar Pine (default)
            'DGLD': 1.0857, 'DGCR': 0.3910, 'DGCRSQ': 0.0,
            'DGDS': -0.000288, 'DGSITE': 0.5827, 'DGDBAL': -0.00579,
            'DGBA': -0.1313, 'DGPCCF': -0.00058, 'DGHAH': 0.0,
            'DGEL': 0.01919, 'DGELSQ': -0.00025, 'DGSLOP': 0.7603,
            'DGSLSQ': -2.2339, 'DGCASP': 0.01664, 'DGSASP': -0.00350,
            'DGFOR': [-0.70344, -0.90272, 0.0]
        }
    }

    # SIGMAR values from blkdat.f for stochastic diameter growth (43 species)
    _SIGMA = {
        'SP': 0.347, 'DF': 0.407, 'WF': 0.347, 'GS': 0.4408, 'IC': 0.433,
        'JP': 0.289, 'RF': 0.4182, 'PP': 0.371, 'LP': 0.4169, 'WB': 0.4169,
        'WP': 0.347, 'PM': 0.4392, 'SF': 0.347, 'KP': 0.4392, 'FP': 0.4392,
        'CP': 0.4392, 'LM': 0.4392, 'MP': 0.371, 'GP': 0.4392, 'WE': 0.4392,
        'GB': 0.2, 'BD': 0.407, 'RW': 0.4408, 'MH': 0.347, 'WJ': 0.4392,
        'UJ': 0.4392, 'CJ': 0.4392, 'LO': 0.4721, 'CY': 0.4721, 'BL': 0.4721,
        'BO': 0.4721, 'VO': 0.4721, 'IO': 0.4721, 'TO': 0.4744, 'GC': 0.4744,
        'AS': 0.4744, 'CL': 0.4744, 'MA': 0.4744, 'DG': 0.4744, 'BM': 0.4721,
        'MC': 0.5357, 'OS': 0.313, 'OH': 0.4721,
    }

    def __init__(self, species_code: str = 'SP'):
        """Initialize WS diameter growth model for a species.

        Args:
            species_code: FVS species code (e.g., 'SP', 'DF', 'PP')
        """
        self.equation_index = self.SPECIES_TO_INDEX.get(
            species_code.upper(),
            self.SPECIES_TO_INDEX[self.DEFAULT_SPECIES]
        )
        super().__init__(species_code)

    def _load_parameters(self) -> None:
        """Load diameter growth coefficients for this species."""
        self.raw_data = self._get_coefficient_data()

        if self.raw_data and self.equation_index in self.raw_data:
            self.coefficients = self.raw_data[self.equation_index]
        elif self.equation_index in self.FALLBACK_PARAMETERS:
            self.coefficients = self.FALLBACK_PARAMETERS[self.equation_index].copy()
        elif '1' in self.FALLBACK_PARAMETERS:  # Sugar Pine fallback
            self.coefficients = self.FALLBACK_PARAMETERS['1'].copy()
        else:
            self.coefficients = {}

    def calculate_dds(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        bal: float,
        pccf: float = 100.0,
        relht: float = 1.0,
        elevation: float = 0.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        location_class: int = 0,
        time_step: float = 10.0,
        rng=None
    ) -> float:
        """Calculate change in squared diameter (DDS).

        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio as proportion (0-1)
            site_index: Site index (feet, base age 50)
            ba: Stand basal area (sq ft/acre)
            bal: Basal area in larger trees (sq ft/acre)
            pccf: Point crown competition factor (default 100)
            relht: Relative height (tree height / top height, default 1.0)
            elevation: Elevation in hundreds of feet (default 0)
            slope: Slope as proportion 0-1 (default 0)
            aspect: Aspect in radians from north (default 0)
            location_class: Location/forest class 0-2 (default 0)
            time_step: Growth period in years (default 10)

        Returns:
            Change in squared diameter (DDS) for the time period
        """
        # Check for Giant Sequoia/Redwood special equation
        if self.equation_index == '4':
            return self._calculate_dds_gs_rw(site_index, time_step)

        # Check for Red Fir/Bristlecone special case (use GS equation)
        if self.equation_index == '7':
            return self._calculate_dds_gs_rw(site_index, time_step)

        # Ensure valid inputs
        dbh = max(0.1, dbh)
        crown_ratio = max(0.01, min(0.99, crown_ratio))
        site_index = max(10.0, site_index)
        ba = max(0.001, ba)
        bal = max(0.0, bal)

        # Get coefficients
        c = self.coefficients

        # Get location-specific intercept
        dgfor_array = c.get('DGFOR', [-1.0, 0.0, 0.0])
        loc_idx = min(location_class, len(dgfor_array) - 1)
        dgfor = dgfor_array[loc_idx] if dgfor_array[loc_idx] != 0.0 else dgfor_array[0]

        # Calculate ln(DDS)
        ln_dds = dgfor

        # Diameter term
        if c.get('DGLD', 0.0) != 0.0:
            ln_dds += c.get('DGLD', 0.0) * math.log(dbh)

        # Crown ratio terms
        ln_dds += c.get('DGCR', 0.0) * crown_ratio
        ln_dds += c.get('DGCRSQ', 0.0) * crown_ratio * crown_ratio

        # Diameter squared term
        ln_dds += c.get('DGDS', 0.0) * dbh * dbh

        # Site index term
        if c.get('DGSITE', 0.0) != 0.0 and site_index > 0:
            ln_dds += c.get('DGSITE', 0.0) * math.log(site_index)

        # Competition terms
        if c.get('DGDBAL', 0.0) != 0.0:
            ln_dds += c.get('DGDBAL', 0.0) * bal / math.log(dbh + 1.0)

        if c.get('DGBA', 0.0) != 0.0 and ba > 0:
            ln_dds += c.get('DGBA', 0.0) * math.log(ba)

        ln_dds += c.get('DGPCCF', 0.0) * pccf
        ln_dds += c.get('DGHAH', 0.0) * relht

        # Topographic terms
        ln_dds += c.get('DGEL', 0.0) * elevation
        ln_dds += c.get('DGELSQ', 0.0) * elevation * elevation
        ln_dds += c.get('DGSLOP', 0.0) * slope
        ln_dds += c.get('DGSLSQ', 0.0) * slope * slope
        ln_dds += c.get('DGCASP', 0.0) * slope * math.cos(aspect)
        ln_dds += c.get('DGSASP', 0.0) * slope * math.sin(aspect)

        # Stochastic draw or deterministic Baskerville bump.
        # TODO(parity): Fortran dgscor.f returns FRM=1.0 in deterministic
        # mode — the +0.88*sigma^2/2 bump below is a pyfvs-only compensator
        # and is not Fortran-faithful.  Remove as part of WS parity work.
        sigma = self._SIGMA.get(self.species_code.upper(), 0.4)
        if rng is not None:
            z = rng.gauss(0, sigma)
            z = max(-2 * sigma, min(2 * sigma, z))
            if ln_dds + z > 4.0:
                z *= max(0.0, 1.0 - (ln_dds + z - 4.0) / 2.0)
            ln_dds += z
        else:
            ln_dds += 0.88 * sigma * sigma / 2.0

        # Convert from ln(DDS) to DDS
        dds = math.exp(ln_dds)

        # Scale for time step (base equation is 10-year for WS)
        dds = dds * (time_step / 10.0)

        return max(0.0, dds)

    def _calculate_dds_gs_rw(
        self,
        site_index: float,
        time_step: float
    ) -> float:
        """Special equation for Giant Sequoia and Redwood.

        ln(DDS) = -3.502444 + 0.415435*ln(SI)

        This is the same equation used in CA variant for GS/RW species.
        """
        site_index = max(10.0, site_index)

        ln_dds = -3.502444 + 0.415435 * math.log(site_index)
        dds = math.exp(ln_dds)

        # Scale for time step (base equation is 10-year)
        dds = dds * (time_step / 10.0)

        return max(0.0, dds)

    def calculate_diameter_growth(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        bal: float,
        bark_ratio: float = 0.9,
        pccf: float = 100.0,
        relht: float = 1.0,
        elevation: float = 0.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        location_class: int = 0,
        time_step: float = 10.0,
        rng=None
    ) -> float:
        """Calculate diameter growth from DDS with bark ratio conversion.

        DDS is an inside-bark quantity.  Fortran dgdriv.f applies it to
        DIB then converts back to OB via BRATIO.  See model_base.dds_to_diameter_growth.

        Args:
            (same as calculate_dds, plus bark_ratio)
            bark_ratio: DIB/DOB ratio (default 0.9)

        Returns:
            Outside-bark diameter growth in inches for the time period.
        """
        from .model_base import dds_to_diameter_growth

        dds = self.calculate_dds(
            dbh, crown_ratio, site_index, ba, bal,
            pccf, relht, elevation, slope, aspect,
            location_class, time_step, rng=rng
        )

        return dds_to_diameter_growth(dds, dbh, bark_ratio)


def create_ws_diameter_growth_model(species_code: str = 'SP') -> WSDiameterGrowthModel:
    """Factory function to create a cached WS diameter growth model.

    Args:
        species_code: FVS species code

    Returns:
        Cached WSDiameterGrowthModel instance
    """
    key = species_code.upper()
    if key not in _model_cache:
        _model_cache[key] = WSDiameterGrowthModel(species_code)
    return _model_cache[key]


def calculate_ws_dds(
    species_code: str,
    dbh: float,
    crown_ratio: float,
    site_index: float,
    ba: float,
    bal: float,
    **kwargs
) -> float:
    """Convenience function to calculate WS variant DDS.

    Args:
        species_code: FVS species code
        dbh: Diameter at breast height (inches)
        crown_ratio: Crown ratio (0-1)
        site_index: Site index (feet)
        ba: Stand basal area (sq ft/acre)
        bal: Basal area in larger trees
        **kwargs: Additional arguments (pccf, relht, elevation, slope, aspect, etc.)

    Returns:
        DDS value
    """
    model = create_ws_diameter_growth_model(species_code)
    return model.calculate_dds(dbh, crown_ratio, site_index, ba, bal, **kwargs)

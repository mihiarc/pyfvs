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
        time_step: float = 10.0
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
        ba = max(1.0, ba)
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
        pccf: float = 100.0,
        relht: float = 1.0,
        elevation: float = 0.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        location_class: int = 0,
        time_step: float = 10.0
    ) -> float:
        """Calculate diameter growth from DDS.

        Converts DDS to diameter increment using:
            DG = sqrt(DBH^2 + DDS) - DBH

        Args:
            (same as calculate_dds)

        Returns:
            Diameter growth in inches for the time period
        """
        dds = self.calculate_dds(
            dbh, crown_ratio, site_index, ba, bal,
            pccf, relht, elevation, slope, aspect,
            location_class, time_step
        )

        # Convert DDS to diameter increment
        # DDS is change in D^2, so new D = sqrt(old_D^2 + DDS)
        dbh_squared = dbh * dbh
        new_dbh_squared = dbh_squared + dds

        if new_dbh_squared <= 0:
            return 0.0

        new_dbh = math.sqrt(new_dbh_squared)
        diameter_growth = new_dbh - dbh

        return max(0.0, diameter_growth)


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

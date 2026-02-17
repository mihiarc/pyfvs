"""
ORGANON Southwest Oregon (OC) variant diameter growth model.

This module implements the OC variant diameter growth equations based on
Hann and Hanus (2002) and the FVS-ORGANON integration.

Unlike the OP variant which uses direct diameter growth (ln(DG)),
the OC variant uses the ln(DDS) equation form similar to CA variant.

Equation form:
    ln(DDS) = DGFOR + DGLD*ln(D) + DGCR*CR + DGCRSQ*CR^2 + DGDS*D^2
            + DGSITE*ln(SI) + DGDBAL*BAL/ln(D+1) + DGLBA*ln(BA)
            + DGBAL*BAL + DGPCCF*PCCF + DGHAH*RELHT
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

References:
    Hann, D.W. and M.L. Hanus. 2002. Enhanced diameter-growth-rate equations
    for undamaged and damaged trees in southwest Oregon. Research Contribution 39.
    Forest Research Laboratory, Oregon State University.
"""
import math
from typing import Dict, Any, Optional

from .model_base import ParameterizedModel

__all__ = [
    'OCDiameterGrowthModel',
    'create_oc_diameter_growth_model',
    'calculate_oc_dds',
]

# Module-level cache for model instances
_model_cache: Dict[str, 'OCDiameterGrowthModel'] = {}


class OCDiameterGrowthModel(ParameterizedModel):
    """OC variant diameter growth model using ln(DDS) equation form.

    The OC variant uses 13 equation sets for 50 species. Species are mapped
    to equation sets via the species_to_equation mapping in the coefficient file.
    """

    COEFFICIENT_FILE = 'oc/oc_diameter_growth_coefficients.json'
    COEFFICIENT_KEY = 'coefficients'
    DEFAULT_SPECIES = 'DF'  # Douglas-fir is the most common species in SW Oregon

    # Species to equation index mapping
    SPECIES_TO_INDEX = {
        'PC': '1', 'IC': '1', 'RC': '1',
        'GF': '2', 'BR': '2',
        'RF': '3', 'SH': '3',
        'DF': '4',
        'KP': '5', 'CP': '5', 'LM': '5', 'GP': '5', 'WJ': '5', 'PY': '5', 'CN': '5',
        'WB': '6', 'LP': '6',
        'WH': '7', 'MH': '7', 'SP': '7',
        'WP': '8',
        'JP': '9', 'PP': '9', 'MP': '9', 'OS': '9',
        'LO': '10', 'CY': '10', 'BL': '10', 'EO': '10', 'WO': '10', 'BO': '10',
        'VO': '10', 'IO': '10', 'BM': '10', 'BU': '10', 'RA': '10', 'FL': '10',
        'WN': '10', 'SY': '10', 'AS': '10', 'CW': '10', 'WI': '10', 'CL': '10', 'OH': '10',
        'MA': '11', 'GC': '11', 'DG': '11',
        'GS': '12', 'RW': '12',
        'TO': '13',
    }

    FALLBACK_PARAMETERS = {
        '4': {  # Douglas-fir (default)
            'DGLD': 0.716226, 'DGCR': 3.272451, 'DGCRSQ': -1.642904,
            'DGDS': -0.0002723, 'DGSITE': 0.759305, 'DGDBAL': -0.008787,
            'DGLBA': -0.028564, 'DGBAL': 0.0, 'DGPCCF': -0.000224,
            'DGHAH': 0.0, 'DGEL': -0.0141, 'DGELSQ': 0.00024083,
            'DGSLOP': -0.339369, 'DGSLSQ': 0.0, 'DGCASP': -0.151727,
            'DGSASP': 0.018681,
            'DGFOR': [-1.877695, -2.099646, -2.211587, -1.955301, -2.078432]
        }
    }

    def __init__(self, species_code: str = 'DF'):
        """Initialize OC diameter growth model for a species.

        Args:
            species_code: FVS species code (e.g., 'DF', 'PP', 'WH')
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
        elif '4' in self.FALLBACK_PARAMETERS:  # Douglas-fir fallback
            self.coefficients = self.FALLBACK_PARAMETERS['4'].copy()
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
        time_step: float = 5.0
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
            location_class: Location/forest class 0-4 (default 0)
            time_step: Growth period in years (default 5)

        Returns:
            Change in squared diameter (DDS) for the time period
        """
        # Check for Giant Sequoia/Redwood special equation
        if self.equation_index == '12':
            return self._calculate_dds_gs_rw(dbh, crown_ratio, bal, slope, aspect, time_step)

        # Ensure valid inputs
        dbh = max(0.1, dbh)
        crown_ratio = max(0.01, min(0.99, crown_ratio))
        site_index = max(10.0, site_index)
        ba = max(1.0, ba)
        bal = max(0.0, bal)

        # Get coefficients
        c = self.coefficients

        # Get location-specific intercept
        dgfor_array = c.get('DGFOR', [-2.0, 0.0, 0.0, 0.0, 0.0])
        loc_idx = min(location_class, len(dgfor_array) - 1)
        dgfor = dgfor_array[loc_idx] if dgfor_array[loc_idx] != 0.0 else dgfor_array[0]

        # Calculate ln(DDS)
        ln_dds = dgfor

        # Diameter term
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

        if c.get('DGLBA', 0.0) != 0.0 and ba > 0:
            ln_dds += c.get('DGLBA', 0.0) * math.log(ba)

        ln_dds += c.get('DGBAL', 0.0) * bal
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

        # Scale for time step (base equation is 5-year)
        dds = dds * (time_step / 5.0)

        return max(0.0, dds)

    def _calculate_dds_gs_rw(
        self,
        dbh: float,
        crown_ratio: float,
        pbal: float,
        slope: float,
        aspect: float,
        time_step: float
    ) -> float:
        """Special equation for Giant Sequoia and Redwood.

        ln(DDS) = -3.502444 + 0.185911*ln(D) - 0.000073*D^2 - 0.001796*PBAL
                - 0.42078*PRD + 0.589318*ln(CR*100) - 0.000926*SLOPE*100
                - 0.002203*SLOPE*100*cos(ASP)

        Note: PRD (percentile rank of diameter) is approximated as 0.5
        """
        dbh = max(0.1, dbh)
        crown_ratio = max(0.01, min(0.99, crown_ratio))
        prd = 0.5  # Approximation for percentile rank of diameter

        ln_dds = -3.502444
        ln_dds += 0.185911 * math.log(dbh)
        ln_dds += -0.000073 * dbh * dbh
        ln_dds += -0.001796 * pbal
        ln_dds += -0.42078 * prd
        ln_dds += 0.589318 * math.log(crown_ratio * 100)
        ln_dds += -0.000926 * slope * 100
        ln_dds += -0.002203 * slope * 100 * math.cos(aspect)

        dds = math.exp(ln_dds)

        # Scale for time step
        dds = dds * (time_step / 5.0)

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
        time_step: float = 5.0
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


def create_oc_diameter_growth_model(species_code: str = 'DF') -> OCDiameterGrowthModel:
    """Factory function to create a cached OC diameter growth model.

    Args:
        species_code: FVS species code

    Returns:
        Cached OCDiameterGrowthModel instance
    """
    key = species_code.upper()
    if key not in _model_cache:
        _model_cache[key] = OCDiameterGrowthModel(species_code)
    return _model_cache[key]


def calculate_oc_dds(
    species_code: str,
    dbh: float,
    crown_ratio: float,
    site_index: float,
    ba: float,
    bal: float,
    **kwargs
) -> float:
    """Convenience function to calculate OC variant DDS.

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
    model = create_oc_diameter_growth_model(species_code)
    return model.calculate_dds(dbh, crown_ratio, site_index, ba, bal, **kwargs)

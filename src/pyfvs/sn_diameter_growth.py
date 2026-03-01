"""
Southern (SN) variant diameter growth model.

Implements the DDS (diameter squared increment) equation for the FVS Southern variant.
The SN variant uses a ln(DDS) transformation with ecological and management effects:

SN equation:
    ln(DDS) = CONSPP + INTERC + LDBH*ln(D) + DBH2*D^2 + LCRWN*ln(CR)
              + HREL*RELHT + PLTB*BA + PNTBL*PBAL
              + [forest_type_effect] + [ecounit_effect] + [plant_effect]

where:
    CONSPP = ISIO*SI + TANS*SLOPE + FCOS*SLOPE*cos(ASPECT) + FSIN*SLOPE*sin(ASPECT)

    - D = diameter at breast height (inches)
    - CR = crown ratio as percentage (25-100)
    - BA = stand basal area (sq ft/acre), minimum 25
    - PBAL = basal area in larger trees (sq ft/acre)
    - RELHT = relative height (tree height / top height, capped at 1.5)
    - SI = site index (feet, base age 25)
    - SLOPE = slope as tangent (rise/run)
    - ASPECT = aspect (radians, 0 = N)

Key features:
    - 90 species supported
    - Ecological unit modifiers (provinces 221-255, M231, sections)
    - Forest type modifiers (FTYLPN, FTYSLP, etc.)
    - Planting effect for managed stands
    - Base growth cycle is 5 years

Source: FVS Southern Variant dgf.f, USDA Forest Service
"""
import math
import random
from typing import Dict, Any, Optional

from .model_base import ParameterizedModel
from .config_loader import load_coefficient_file


class SNDiameterGrowthModel(ParameterizedModel):
    """Southern variant diameter growth model.

    Calculates diameter squared increment (DDS) using the SN variant equation.
    This model uses ln(DDS) with ecological unit and forest type modifiers.

    Attributes:
        species_code: Species code (e.g., 'LP', 'SP', 'SA', 'LL')
        coefficients: Species-specific coefficients for the DDS equation
    """

    COEFFICIENT_FILE = 'sn_diameter_growth_coefficients.json'
    COEFFICIENT_KEY = 'core_coefficients'
    DEFAULT_SPECIES = 'LP'  # Loblolly pine is the default site species for SN
    FALLBACK_PARAMETERS = {}

    def __init__(self, species_code: str = "LP"):
        """Initialize the SN diameter growth model.

        Args:
            species_code: FVS species code (e.g., 'LP', 'SP', 'SA', 'LL')
        """
        super().__init__(species_code)
        # Load SIGMAR (std dev of ln(DDS) residuals) for Baskerville correction
        self._sigma = self._load_sigma()

    def calculate_dds(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        pbal: float,
        relht: float = 1.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        ecounit_effect: float = 0.0,
        fortype_effect: float = 0.0,
        plant_effect: float = 0.0,
        time_step: float = 5.0,
        rng: random.Random = None
    ) -> float:
        """Calculate diameter squared increment (DDS).

        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio as proportion (0-1)
            site_index: Site index (feet, base age 25)
            ba: Stand basal area (sq ft/acre), will be bounded to min 25
            pbal: Basal area in larger trees (sq ft/acre)
            relht: Relative height (tree height / top height, capped at 1.5)
            slope: Slope as tangent (rise/run)
            aspect: Aspect in radians (0=N, pi/2=E)
            ecounit_effect: Ecological unit modifier (from ecounit lookup)
            fortype_effect: Forest type modifier (from forest type lookup)
            plant_effect: Planting effect modifier
            time_step: Growth period in years (default 5)

        Returns:
            Diameter squared increment (DDS) in sq inches
        """
        params = self.coefficients

        # Apply FVS bounds
        dbh_safe = max(0.1, dbh)
        # Fortran dgf.f line 270: IF(BA .LE. 0.) BA= 25.
        # BA=25 is a "no data" default, NOT a floor for competition.
        ba_bounded = ba if ba > 0.0 else 25.0
        pbal_bounded = max(0.0, pbal)
        relht_bounded = min(1.5, max(0.1, relht))

        # Crown ratio must be integer percentage (25-100) for ln(CR) calculation
        cr_pct = max(25.0, min(100.0, crown_ratio * 100.0))

        # Get coefficient values with defaults
        interc = params.get('INTERC', params.get('b1', -2.04))
        ldbh = params.get('LDBH', params.get('b2', 0.48))
        dbh2 = params.get('DBH2', params.get('b3', -0.001))
        lcrwn = params.get('LCRWN', params.get('b4', 0.47))
        hrel = params.get('HREL', params.get('b5', 0.28))
        isio = params.get('ISIO', params.get('b6', 0.014))
        pltb = params.get('PLTB', params.get('b7', -0.0017))
        pntbl = params.get('PNTBL', params.get('b8', -0.0026))
        tans = params.get('TANS', params.get('b9', 0.0))
        fcos = params.get('FCOS', params.get('b10', 0.0))
        fsin = params.get('FSIN', params.get('b11', 0.0))

        # Calculate CONSPP (site and topographic terms)
        # CONSPP = ISIO*SI + TANS*SLOPE + FCOS*SLOPE*cos(ASPECT) + FSIN*SLOPE*sin(ASPECT)
        conspp = (
            isio * site_index +
            tans * slope +
            fcos * slope * math.cos(aspect) +
            fsin * slope * math.sin(aspect)
        )

        # Calculate ln(DDS)
        # ln(DDS) = CONSPP + INTERC + LDBH*ln(D) + DBH2*D^2
        #           + LCRWN*ln(CR) + HREL*RELHT + PLTB*BA + PNTBL*PBAL
        #           + [forest_type] + [eco_unit] + [plant_effect]
        ln_dds = (
            conspp +
            interc +
            ldbh * math.log(dbh_safe) +
            dbh2 * dbh_safe * dbh_safe +
            lcrwn * math.log(cr_pct) +
            hrel * relht_bounded +
            pltb * ba_bounded +
            pntbl * pbal_bounded +
            fortype_effect +
            ecounit_effect +
            plant_effect
        )

        # Apply FVS bounds for ln(DDS) — lower from Fortran, upper defensive
        ln_dds = max(-9.21, min(11.0, ln_dds))

        # Apply stochastic multiplier: Baskerville correction (deterministic)
        # or random draw (stochastic) matching Fortran dgscor.f.
        correction = self._stochastic_multiplier(ln_dds, rng)

        # Convert to DDS and scale by time step (model calibrated for 5-year growth)
        dds = math.exp(ln_dds) * correction * (time_step / 5.0)

        return max(0.0, dds)

    def calculate_diameter_growth(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        pbal: float,
        bark_ratio: float = 0.9,
        relht: float = 1.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        ecounit_effect: float = 0.0,
        fortype_effect: float = 0.0,
        plant_effect: float = 0.0,
        time_step: float = 5.0,
        rng: random.Random = None
    ) -> float:
        """Calculate diameter growth (DG) from DDS with bark ratio conversion.

        FVS applies DDS to inside-bark diameter, then converts back.
        From dgdriv.f: D=DBH(I)*BRATIO(...); DG=(SQRT(DSQ+DDS)-D)

        Args:
            dbh: Diameter at breast height (inches, outside bark)
            crown_ratio: Crown ratio as proportion (0-1)
            site_index: Site index (feet)
            ba: Stand basal area (sq ft/acre)
            pbal: Basal area in larger trees (sq ft/acre)
            bark_ratio: DIB/DOB ratio (default 0.9)
            relht: Relative height (tree height / top height)
            slope: Slope as tangent (rise/run)
            aspect: Aspect in radians
            ecounit_effect: Ecological unit modifier
            fortype_effect: Forest type modifier
            plant_effect: Planting effect modifier
            time_step: Growth period in years

        Returns:
            Diameter growth (inches) for the time period
        """
        dds = self.calculate_dds(
            dbh, crown_ratio, site_index, ba, pbal,
            relht, slope, aspect,
            ecounit_effect, fortype_effect, plant_effect,
            time_step, rng=rng
        )

        # Convert DBH to inside-bark diameter
        dib_old = dbh * bark_ratio
        dib_old_sq = dib_old * dib_old

        # Apply DDS to inside-bark diameter
        dib_new_sq = dib_old_sq + dds
        if dib_new_sq <= dib_old_sq:
            return 0.0

        dib_new = math.sqrt(dib_new_sq)

        # Convert back to outside-bark (DBH) and calculate growth
        dbh_new = dib_new / bark_ratio
        return dbh_new - dbh


# Module-level cache for model instances
_model_cache: Dict[str, SNDiameterGrowthModel] = {}


def create_sn_diameter_growth_model(species_code: str = "LP") -> SNDiameterGrowthModel:
    """Factory function to create a cached SN diameter growth model.

    Args:
        species_code: FVS species code (e.g., 'LP', 'SP', 'SA', 'LL')

    Returns:
        SNDiameterGrowthModel instance (cached)
    """
    species_upper = species_code.upper()
    if species_upper not in _model_cache:
        _model_cache[species_upper] = SNDiameterGrowthModel(species_upper)
    return _model_cache[species_upper]

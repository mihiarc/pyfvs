"""
Pacific Northwest Coast (PN) variant diameter growth model.

Implements the DDS (diameter squared increment) equation for the FVS Pacific Northwest Coast variant.
The PN variant uses ln(DDS) transformation similar to SN but with a more complex equation structure:

PN equation:
    ln(DDS) = CONSPP + DGLD*ln(D) + CR*(DGCR + CR*DGCRSQ) + DGDSQ*D²
              + DGDBAL*BAL/ln(D+1) + DGPCCF*PCCF + DGHAH*RELHT
              + DGLBA*ln(BA) + DGBAL*BAL + DGBA*BA + DGSITE*ln(SI)
              + DGEL*ELEV + DGEL2*ELEV² + DGSLOP*SLOPE + DGSLSQ*SLOPE²
              + DGSASP*SLOPE*sin(ASPECT) + DGCASP*SLOPE*cos(ASPECT)

where:
    - D = diameter at breast height (inches)
    - CR = crown ratio (0-1)
    - BA = stand basal area (sq ft/acre)
    - BAL = basal area in larger trees (sq ft/acre)
    - PCCF = point crown competition factor
    - RELHT = relative height (tree height / average height, capped at 1.5)
    - SI = site index (feet)
    - ELEV = elevation (hundreds of feet)
    - SLOPE = slope (proportion, 0-1)
    - ASPECT = aspect (radians, 0 = N, π/2 = E)

Key differences from SN variant:
    - Uses different coefficient names and structure
    - Includes elevation, slope, and aspect effects directly in equation
    - Uses PCCF (point crown competition factor) instead of CCF
    - Has location/forest-specific intercepts (DGFOR)
    - Base cycle is 10 years (vs 5 years for SN)

Source: FVS Pacific Northwest Coast Variant dgf.f, USDA Forest Service
"""
import math
from typing import Dict, Any, Optional

from .model_base import ParameterizedModel
from .config_loader import load_coefficient_file


class PNDiameterGrowthModel(ParameterizedModel):
    """Pacific Northwest Coast variant diameter growth model.

    Calculates diameter squared increment (DDS) using the PN variant equation.
    This model uses ln(DDS) like SN but with additional topographic effects.

    Attributes:
        species_code: Species code (e.g., 'DF', 'WH', 'RC')
        coefficients: Species-specific coefficients for the DDS equation
    """

    COEFFICIENT_FILE = 'pn/pn_diameter_growth_coefficients.json'
    COEFFICIENT_KEY = 'coefficients'
    DEFAULT_SPECIES = 'DF'  # Douglas-fir is the default site species for PN

    # Fallback parameters for key PN species (from dgf.f)
    FALLBACK_PARAMETERS = {
        'DF': {  # Douglas-fir
            'DGLD': 0.802905,
            'DGCR': 1.936912,
            'DGCRSQ': 0.0,
            'DGSITE': 0.495162,
            'DGDBAL': -0.001827,
            'DGLBA': -0.129474,
            'DGBAL': -0.001639,
            'DGBA': 0.0,
            'DGPCCF': 0.0,
            'DGHAH': 0.0,
            'DGFOR': -0.739354,
            'DGDS': -0.0000896,
            'DGEL': -0.009845,
            'DGEL2': 0.0,
            'DGSASP': 0.003263,
            'DGCASP': 0.014165,
            'DGSLOP': -0.340401,
            'DGSLSQ': 0.0,
        },
        'WH': {  # Western Hemlock
            'DGLD': 0.641956,
            'DGCR': 1.471926,
            'DGCRSQ': 0.0,
            'DGSITE': 0.634098,
            'DGDBAL': -0.012589,
            'DGLBA': -0.085525,
            'DGBAL': 0.002385,
            'DGBA': 0.0,
            'DGPCCF': 0.0,
            'DGHAH': 0.0,
            'DGFOR': -0.594460,
            'DGDS': -0.0001736,
            'DGEL': -0.018444,
            'DGEL2': 0.0,
            'DGSASP': 0.061254,
            'DGCASP': -0.056608,
            'DGSLOP': 0.736143,
            'DGSLSQ': -1.082191,
        },
        'RC': {  # Western Red Cedar
            'DGLD': 0.744005,
            'DGCR': 0.771395,
            'DGCRSQ': 0.0,
            'DGSITE': 0.708166,
            'DGDBAL': -0.016240,
            'DGLBA': -0.130036,
            'DGBAL': 0.003883,
            'DGBA': 0.0,
            'DGPCCF': 0.0,
            'DGHAH': 0.0,
            'DGFOR': -0.688250,
            'DGDS': -0.0000572,
            'DGEL': -0.009564,
            'DGEL2': 0.0,
            'DGSASP': -0.106020,
            'DGCASP': -0.106936,
            'DGSLOP': -0.303490,
            'DGSLSQ': 0.0,
        },
        'SS': {  # Sitka Spruce
            'DGLD': 0.949631,
            'DGCR': 1.826879,
            'DGCRSQ': 0.0,
            'DGSITE': 0.375175,
            'DGDBAL': -0.005350,
            'DGLBA': 0.0,
            'DGBAL': 0.0,
            'DGBA': 0.000040,
            'DGPCCF': 0.0,
            'DGHAH': 0.0,
            'DGFOR': -9.211184,
            'DGDS': -0.0003552,
            'DGEL': 0.323546,
            'DGEL2': -0.003130,
            'DGSASP': 0.202507,
            'DGCASP': -0.935870,
            'DGSLOP': 0.0,
            'DGSLSQ': 0.0,
        },
    }

    def __init__(self, species_code: str = "DF"):
        """Initialize the PN diameter growth model.

        Args:
            species_code: FVS species code (e.g., 'DF', 'WH', 'RC')
        """
        super().__init__(species_code)

    # Species mapping from MAPSPC array in dgf.f
    # Maps 39 species to 20 coefficient sets
    SPECIES_TO_INDEX = {
        'SF': '1', 'WF': '2', 'GF': '2', 'AF': '3', 'RF': '4',
        'SS': '17', 'NF': '4', 'YC': '15', 'IC': '11', 'ES': '18',
        'LP': '16', 'JP': '6', 'SP': '5', 'WP': '5', 'PP': '6',
        'DF': '7', 'RW': '20', 'RC': '8', 'WH': '9', 'MH': '10',
        'BM': '12', 'RA': '13', 'WA': '14', 'PB': '14', 'GC': '14',
        'AS': '14', 'CW': '14', 'WO': '19', 'CH': '14', 'WI': '14',
        'WJ': '14', 'WB': '14', 'KP': '14', 'PY': '14', 'DG': '14',
        'HT': '14', 'LL': '14', 'OS': '14', 'OT': '14'
    }

    def _load_parameters(self) -> None:
        """Load species-specific parameters using species-to-index mapping.

        PN variant uses numeric indices in the coefficient file, so we need
        to map species codes to coefficient indices before loading.
        """
        self.raw_data = self._get_coefficient_data()

        if self.raw_data:
            coeffs = self.raw_data.get(self.COEFFICIENT_KEY, {})

            # Get coefficient index for this species (e.g., 'DF' -> '7')
            coef_idx = self.SPECIES_TO_INDEX.get(self.species_code.upper(), '7')

            if coef_idx in coeffs:
                self.coefficients = coeffs[coef_idx]
            else:
                self._load_fallback_parameters()
        else:
            self._load_fallback_parameters()

    def calculate_dds(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        bal: float,
        pccf: float = 100.0,
        relht: float = 1.0,
        elevation: float = 10.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        time_step: float = 10.0
    ) -> float:
        """Calculate diameter squared increment (DDS).

        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio (0-1)
            site_index: Site index (feet)
            ba: Stand basal area (sq ft/acre)
            bal: Basal area in larger trees (sq ft/acre)
            pccf: Point crown competition factor (default 100)
            relht: Relative height (tree height / avg height, capped at 1.5)
            elevation: Elevation in hundreds of feet (default 10 = 1000 ft)
            slope: Slope as proportion (0-1, default 0)
            aspect: Aspect in radians (0=N, π/2=E, default 0)
            time_step: Growth period in years (default 10)

        Returns:
            Diameter squared increment (DDS) in sq inches
        """
        # Get coefficients
        params = self.coefficients

        # Apply bounds
        dbh_safe = max(0.1, dbh)
        cr = max(0.01, min(0.99, crown_ratio))
        si = max(10.0, site_index)
        ba_bounded = max(0.0, min(500.0, ba))
        bal_bounded = max(0.0, min(400.0, bal))
        relht_bounded = max(0.1, min(1.5, relht))
        slope_bounded = max(0.0, min(1.0, slope))

        # Get coefficient values with defaults
        dgld = params.get('DGLD', 0.8)
        dgcr = params.get('DGCR', 1.5)
        dgcrsq = params.get('DGCRSQ', 0.0)
        dgsite = params.get('DGSITE', 0.5)
        dgdbal = params.get('DGDBAL', -0.005)
        dglba = params.get('DGLBA', 0.0)
        dgbal = params.get('DGBAL', 0.0)
        dgba = params.get('DGBA', 0.0)
        dgpccf = params.get('DGPCCF', 0.0)
        dghah = params.get('DGHAH', 0.0)
        dgfor = params.get('DGFOR', -0.7)
        if isinstance(dgfor, list):
            dgfor = dgfor[0]  # Use first location class
        dgds = params.get('DGDS', -0.0001)
        if isinstance(dgds, list):
            dgds = dgds[0]
        dgel = params.get('DGEL', 0.0)
        dgel2 = params.get('DGEL2', 0.0)
        dgsasp = params.get('DGSASP', 0.0)
        dgcasp = params.get('DGCASP', 0.0)
        dgslop = params.get('DGSLOP', 0.0)
        dgslsq = params.get('DGSLSQ', 0.0)

        # Calculate ln(DDS) components
        # Base intercept (location-specific)
        conspp = dgfor

        # Diameter term
        d_term = dgld * math.log(dbh_safe)

        # Crown ratio term (linear + quadratic)
        cr_term = cr * (dgcr + cr * dgcrsq)

        # Diameter squared term
        dsq_term = dgds * dbh_safe * dbh_safe

        # BAL interaction term
        bal_d_term = dgdbal * bal_bounded / math.log(dbh_safe + 1.0)

        # Competition terms
        pccf_term = dgpccf * pccf
        relht_term = dghah * relht_bounded

        # Basal area terms
        lba_term = dglba * math.log(max(1.0, ba_bounded)) if dglba != 0 else 0.0
        bal_term = dgbal * bal_bounded
        ba_term = dgba * ba_bounded

        # Site index term
        si_term = dgsite * math.log(si)

        # Topographic terms
        elev_term = dgel * elevation + dgel2 * elevation * elevation
        slope_term = dgslop * slope_bounded + dgslsq * slope_bounded * slope_bounded
        aspect_term = (dgsasp * slope_bounded * math.sin(aspect) +
                      dgcasp * slope_bounded * math.cos(aspect))

        # Sum all terms
        ln_dds = (conspp + d_term + cr_term + dsq_term + bal_d_term +
                  pccf_term + relht_term + lba_term + bal_term + ba_term +
                  si_term + elev_term + slope_term + aspect_term)

        # Convert from ln(DDS) to DDS
        dds = math.exp(ln_dds)

        # Scale by time step (base cycle is 10 years)
        dds = dds * (time_step / 10.0)

        # Ensure non-negative
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
        elevation: float = 10.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        time_step: float = 10.0,
        bark_ratio: float = 0.90
    ) -> float:
        """Calculate diameter growth from DDS.

        The PN variant applies DDS to inside-bark diameter, then converts back.

        Args:
            dbh: Current diameter at breast height (inches)
            crown_ratio: Crown ratio (0-1)
            site_index: Site index (feet)
            ba: Stand basal area (sq ft/acre)
            bal: Basal area in larger trees (sq ft/acre)
            pccf: Point crown competition factor
            relht: Relative height (tree height / avg height)
            elevation: Elevation in hundreds of feet
            slope: Slope as proportion (0-1)
            aspect: Aspect in radians
            time_step: Growth period in years
            bark_ratio: Species-specific bark ratio (DIB/DOB), default 0.90

        Returns:
            Diameter growth (inches) for the time period
        """
        # Calculate DDS
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
            time_step=time_step
        )

        # Convert DBH to inside-bark diameter
        dib = dbh * bark_ratio

        # Calculate inside-bark diameter squared
        dsq = dib * dib

        # Add DDS to get new inside-bark diameter squared
        new_dsq = dsq + dds

        # Calculate new inside-bark diameter
        new_dib = math.sqrt(max(dsq, new_dsq))

        # Convert back to outside-bark diameter
        new_dbh = new_dib / bark_ratio

        # Calculate diameter growth
        dg = new_dbh - dbh

        # Ensure non-negative growth for living trees
        return max(0.0, dg)


# Module-level cache for model instances
_model_cache: Dict[str, PNDiameterGrowthModel] = {}


def create_pn_diameter_growth_model(species_code: str = "DF") -> PNDiameterGrowthModel:
    """Factory function to create a cached PN diameter growth model.

    Args:
        species_code: FVS species code (default 'DF' for Douglas-fir)

    Returns:
        Cached PNDiameterGrowthModel instance
    """
    species_upper = species_code.upper()
    if species_upper not in _model_cache:
        _model_cache[species_upper] = PNDiameterGrowthModel(species_upper)
    return _model_cache[species_upper]

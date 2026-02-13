"""
West Cascades (WC) variant diameter growth model.

Implements the DDS (diameter squared increment) equation for the FVS West Cascades variant.
The WC variant uses the same ln(DDS) transformation as PN with topographic effects:

WC equation:
    ln(DDS) = CONSPP + DGLD*ln(D) + CR*(DGCR + CR*DGCRSQ) + DGDS*D²
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

Key features:
    - 19 coefficient sets for 37 species
    - Forest location-specific intercepts (DGFOR)
    - Special equations for Red Alder (RA) and Redwood (RW)
    - Base cycle is 10 years

Source: FVS West Cascades Variant dgf.f, USDA Forest Service
"""
import math
from typing import Dict, Any

from .model_base import ParameterizedModel
from .config_loader import load_coefficient_file


class WCDiameterGrowthModel(ParameterizedModel):
    """West Cascades variant diameter growth model.

    Calculates diameter squared increment (DDS) using the WC variant equation.
    This model uses ln(DDS) like PN with topographic effects.

    Attributes:
        species_code: Species code (e.g., 'DF', 'WH', 'RC')
        coefficients: Species-specific coefficients for the DDS equation
    """

    COEFFICIENT_FILE = 'wc/wc_diameter_growth_coefficients.json'
    COEFFICIENT_KEY = 'coefficient_sets'
    DEFAULT_SPECIES = 'DF'  # Douglas-fir is the default site species for WC

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
    SPECIES_TO_GROUP = {
        'SF': '1', 'WF': '2', 'GF': '2', 'AF': '3', 'RF': '17',
        'NF': '4', 'YC': '15', 'IC': '11', 'ES': '11', 'LP': '16',
        'JP': '6', 'SP': '5', 'WP': '5', 'PP': '6', 'DF': '7',
        'RW': '19', 'RC': '8', 'WH': '9', 'MH': '10', 'BM': '12',
        'RA': '13', 'WA': '14', 'PB': '14', 'GC': '14', 'AS': '14',
        'CW': '14', 'WO': '18', 'WJ': '14', 'LL': '11', 'WB': '11',
        'KP': '11', 'PY': '11', 'DG': '14', 'HT': '14', 'CH': '14',
        'WI': '14', 'OT': '14'
    }

    def __init__(self, species_code: str = "DF"):
        """Initialize the WC diameter growth model.

        Args:
            species_code: FVS species code (e.g., 'DF', 'WH', 'RC')
        """
        super().__init__(species_code)

    def _load_parameters(self) -> None:
        """Load species-specific parameters using species-to-group mapping.

        WC variant uses numeric group indices in the coefficient file, so we need
        to map species codes to coefficient groups before loading.
        """
        self.raw_data = self._get_coefficient_data()

        if self.raw_data:
            coeffs = self.raw_data.get(self.COEFFICIENT_KEY, {})

            # Get coefficient group for this species (e.g., 'DF' -> '7')
            coef_group = self.SPECIES_TO_GROUP.get(self.species_code.upper(), '7')

            if coef_group in coeffs:
                self.coefficients = coeffs[coef_group]
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
        elevation: float = 20.0,
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
            elevation: Elevation in hundreds of feet (default 20 = 2000 ft)
            slope: Slope as proportion (0-1, default 0)
            aspect: Aspect in radians (0=N, π/2=E, default 0)
            time_step: Growth period in years (default 10)

        Returns:
            Diameter squared increment (DDS) in sq inches
        """
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
            dgfor = dgfor[0]  # Use first location class (Willamette default)
        dgds = params.get('DGDS', -0.0001)
        dgel = params.get('DGEL', 0.0)
        dgel2 = params.get('DGEL2', 0.0)
        dgsasp = params.get('DGSASP', 0.0)
        dgcasp = params.get('DGCASP', 0.0)
        dgslop = params.get('DGSLOP', 0.0)
        dgslsq = params.get('DGSLSQ', 0.0)

        # Calculate ln(DDS) components
        conspp = dgfor
        d_term = dgld * math.log(dbh_safe)
        cr_term = cr * (dgcr + cr * dgcrsq)
        dsq_term = dgds * dbh_safe * dbh_safe
        bal_d_term = dgdbal * bal_bounded / math.log(dbh_safe + 1.0)
        pccf_term = dgpccf * pccf
        relht_term = dghah * relht_bounded
        lba_term = dglba * math.log(max(1.0, ba_bounded)) if dglba != 0 else 0.0
        bal_term = dgbal * bal_bounded
        ba_term = dgba * ba_bounded
        si_term = dgsite * math.log(si)
        elev_term = dgel * elevation + dgel2 * elevation * elevation
        slope_term = dgslop * slope_bounded + dgslsq * slope_bounded * slope_bounded
        aspect_term = (dgsasp * slope_bounded * math.sin(aspect) +
                      dgcasp * slope_bounded * math.cos(aspect))

        # Sum all terms
        ln_dds = (conspp + d_term + cr_term + dsq_term + bal_d_term +
                  pccf_term + relht_term + lba_term + bal_term + ba_term +
                  si_term + elev_term + slope_term + aspect_term)

        # Exponentiate
        dds = math.exp(ln_dds)

        # Scale by time step (base is 10 years)
        dds *= (time_step / 10.0)

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
        elevation: float = 20.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        time_step: float = 10.0,
        bark_ratio: float = 0.90
    ) -> float:
        """Calculate diameter growth (DG) from DDS with bark ratio conversion.

        FVS applies DDS to inside-bark diameter, then converts back.
        From dgdriv.f: D=DBH(I)*BRATIO(...); DG=(SQRT(DSQ+DDS)-D)

        Args:
            Same as calculate_dds(), plus:
            bark_ratio: Species-specific bark ratio (DIB/DOB), default 0.90

        Returns:
            Diameter growth (inches) for the time period
        """
        dds = self.calculate_dds(
            dbh, crown_ratio, site_index, ba, bal,
            pccf, relht, elevation, slope, aspect, time_step
        )

        # Convert DBH to inside-bark diameter
        dib = dbh * bark_ratio
        dsq = dib * dib

        # Apply DDS to inside-bark diameter squared
        new_dsq = dsq + dds
        if new_dsq <= dsq:
            return 0.0

        # Convert back to outside-bark and calculate growth
        new_dib = math.sqrt(new_dsq)
        new_dbh = new_dib / bark_ratio
        return new_dbh - dbh


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

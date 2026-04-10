"""
FVS Southwest Oregon (OC) variant diameter growth model.

Port of the Fortran FVS OC variant (ForestVegetationSimulator/oc/dgf.f).
The OC variant is structurally a 5-year-cycle sister of the CA (Inland
California / Southern Cascades) variant, sharing 13 equation groups across
50 species. Mark Castle refit the GS/RW (giant sequoia / coast redwood)
equations in 2019.

Equation form (per equation group, not per species):
    ln(DDS_10) = DGFOR + DGLD*ln(D) + DGCR*CR + DGCRSQ*CR^2 + DGDS*D^2
               + DGSITE*ln(SI) + DGDBAL*BAL/ln(D+1) + DGLBA*ln(BA)
               + DGBAL*BAL + DGPCCF*PCCF + DGHAH*RELHT
               + DGEL*ELEV + DGELSQ*ELEV^2 + DGSLOP*SLOPE + DGSLSQ*SLOPE^2
               + DGCASP*SLOPE*cos(ASP) + DGSASP*SLOPE*sin(ASP)

The underlying coefficients are 10-year. OC runs on 5-year cycles
(Fortran blkdat.f: DATA YR / 5.0 /), so the Fortran code converts in
real space at the end of dgf.f:402-403:
    TDDS = EXP(DDS)        ! 10-year DDS in real space
    DDS  = ALOG(TDDS/2.0)  ! 5-year DDS in log space (= ln(DDS_10) - ln(2))
This module applies the same conversion. Tanoak (TO, species 42) is the
exception: its underlying equation is fit for 5-year, so Fortran multiplies
by 2 first before the universal /2 (oc/dgf.f:387-393), netting to no change.

Where:
    DDS = change in squared diameter (inside bark) over the 5-year cycle
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

Note: prior versions of this module described OC as the ORGANON Southwest
Oregon model (Hann & Hanus 2002). That is a different model — the FVS OC
variant is its own 5-year FVS cycle variant derived from CA. This module
is the FVS port, not ORGANON SWO.
"""
import math
from typing import Dict, Any, Optional

from .model_base import ParameterizedModel

__all__ = [
    'OCDiameterGrowthModel',
    'create_oc_diameter_growth_model',
    'calculate_oc_dds',
]

# SIGMAR stochastic sigma values from SO blkdat.f for 33 species
_SIGMA = {
    'WP': 0.26248, 'SP': 0.26795, 'DF': 0.27398, 'WF': 0.26064, 'MH': 0.28256,
    'IC': 0.26601, 'LP': 0.34451, 'ES': 0.51620, 'SH': 0.41120, 'PP': 0.29512,
    'WJ': 0.34663, 'GF': 0.26064, 'AF': 0.25900, 'SF': 0.34663, 'NF': 0.42750,
    'WB': 0.34663, 'WL': 0.34663, 'RC': 0.34663, 'WH': 0.41040, 'PY': 0.48420,
    'WA': 0.53570, 'RA': 0.74870, 'BM': 0.51070, 'AS': 0.34663, 'CW': 0.53570,
    'CH': 0.53570, 'WO': 0.59980, 'WI': 0.53570, 'GC': 0.53570, 'MC': 0.53570,
    'MB': 0.53570, 'OS': 0.27398, 'OH': 0.53570,
}

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

    # MAPLOC(10,13) from oc/dgf.f:182-195.  Maps (IFOR, equation) →
    # 1-based location class used to index DGFOR.  Stored here as a dict
    # keyed by 1-based equation number; each value is a list of 10 entries
    # for IFOR 1-10.  Most species map to 1 regardless of forest.
    _MAPLOC = {
        '1':  [1,1,1,1,2,1,1,1,1,1],
        '2':  [1,1,1,1,1,1,1,1,1,1],
        '3':  [1,1,1,2,1,1,1,1,1,1],
        '4':  [1,2,2,1,3,4,5,4,4,5],
        '5':  [1,1,1,1,1,1,1,1,1,1],
        '6':  [1,1,1,2,1,1,1,1,1,1],
        '7':  [1,1,1,1,1,1,1,1,1,1],
        '8':  [1,1,1,1,1,1,1,1,1,1],
        '9':  [1,1,1,1,1,1,1,1,1,1],
        '10': [1,1,1,1,1,1,1,1,1,1],
        '11': [1,1,1,1,1,1,1,1,1,1],
        '12': [1,1,1,1,1,1,1,1,1,1],
        '13': [1,1,1,1,1,1,1,1,1,1],
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
        ifor: int = 9,
        time_step: float = 5.0,
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
            ifor: Forest number 1-10 (default 9 per oc/grinit.f:192).
                Mapped to a location class via MAPLOC (oc/dgf.f:182-195).
            time_step: Growth period in years (default 5)

        Returns:
            Change in squared diameter (DDS) for the time period
        """
        # Check for Giant Sequoia/Redwood special equation
        if self.equation_index == '12':
            return self._calculate_dds_gs_rw(dbh, crown_ratio, bal, slope, aspect, time_step, rng=rng)

        # Ensure valid inputs
        dbh = max(0.1, dbh)
        crown_ratio = max(0.01, min(0.99, crown_ratio))
        site_index = max(10.0, site_index)
        ba = max(1.0, ba)
        bal = max(0.0, bal)

        # Get coefficients
        c = self.coefficients

        # Map (IFOR, equation) → 1-based location class via MAPLOC,
        # then index into DGFOR (0-based).  oc/dgf.f:434:
        #   ISPFOR = MAPLOC(IFOR, JSPC)
        maploc_row = self._MAPLOC.get(self.equation_index, [1]*10)
        ifor_idx = max(0, min(len(maploc_row) - 1, ifor - 1))  # 1-based → 0-based
        ispfor = maploc_row[ifor_idx]  # 1-based location class

        dgfor_array = c.get('DGFOR', [-2.0, 0.0, 0.0, 0.0, 0.0])
        loc_idx = min(ispfor - 1, len(dgfor_array) - 1)  # 1-based → 0-based
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

        # 10-year -> 5-year cycle conversion (Fortran oc/dgf.f:399-403).
        # The OC equations are calibrated for 10-year diameter growth, but the
        # OC variant runs on 5-year cycles (blkdat.f: DATA YR / 5.0 /). The
        # Fortran converts in real space: TDDS=EXP(DDS); DDS=ALOG(TDDS/2.0),
        # which is equivalent to subtracting ln(2) in log space.
        # Tanoak (species TO) is the exception: its underlying equation was
        # fit for 5-year growth, so Fortran multiplies it by 2 before the
        # universal divide-by-2 (oc/dgf.f:387-393), netting to no change.
        species_upper = self.species_code.upper() if self.species_code else 'DF'
        if species_upper != 'TO':
            ln_dds -= math.log(2.0)

        # Stochastic error (dgscor.f).  When DGSD < 1.0 (deterministic
        # mode), Fortran sets FRM = EXP(0.0) = 1.0 — no Baskerville
        # correction.  Only stochastic mode draws from the error
        # distribution; the log-normal mean correction emerges naturally
        # from averaging many draws.
        if rng is not None:
            sigma = _SIGMA.get(species_upper, 0.35)
            z = rng.gauss(0, sigma)
            z = max(-2 * sigma, min(2 * sigma, z))
            if ln_dds + z > 4.0:
                z *= max(0.0, 1.0 - (ln_dds + z - 4.0) / 2.0)
            ln_dds += z

        # Floor at ln(DDS) = -9.21 to match Fortran oc/dgf.f:404
        if ln_dds < -9.21:
            ln_dds = -9.21

        # Convert from ln(DDS) to DDS (now correctly on a 5-year base)
        dds = math.exp(ln_dds)

        # Scale for non-default time steps. OC runs natively on 5-year cycles,
        # so callers passing time_step=5 get the unscaled value.
        if time_step != 5.0:
            dds = dds * (time_step / 5.0)

        return max(0.0, dds)

    def _calculate_dds_gs_rw(
        self,
        dbh: float,
        crown_ratio: float,
        pbal: float,
        slope: float,
        aspect: float,
        time_step: float,
        rng=None
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

        # 10-year -> 5-year conversion (Fortran oc/dgf.f:402-403). GS/RW
        # fall through the universal conversion in Fortran the same as
        # other species.
        ln_dds -= math.log(2.0)

        # Stochastic error for GS/RW (same dgscor.f logic as main path)
        if rng is not None:
            sigma = _SIGMA.get(self.species_code.upper() if self.species_code else 'DF', 0.35)
            z = rng.gauss(0, sigma)
            z = max(-2 * sigma, min(2 * sigma, z))
            if ln_dds + z > 4.0:
                z *= max(0.0, 1.0 - (ln_dds + z - 4.0) / 2.0)
            ln_dds += z

        # Floor at ln(DDS) = -9.21 to match Fortran oc/dgf.f:404
        if ln_dds < -9.21:
            ln_dds = -9.21

        dds = math.exp(ln_dds)

        # Scale for non-default time steps (5-year is the OC native cycle)
        if time_step != 5.0:
            dds = dds * (time_step / 5.0)

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
        ifor: int = 9,
        time_step: float = 5.0,
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
            ifor, time_step, rng=rng
        )

        return dds_to_diameter_growth(dds, dbh, bark_ratio)


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

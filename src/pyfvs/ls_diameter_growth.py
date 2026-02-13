"""
Lake States (LS) variant diameter growth model.

Implements the DDS (diameter squared increment) equation for the FVS Lake States variant.
The LS variant uses a different functional form than the Southern (SN) variant:

LS equation:
    ln(DDS) = CONSPP + INTERC + VDBHC/D + DBHC*D + DBH2C*D² + RDBHC*RELDBH
              + RDBHSQC*RELDBH² + CRWNC*CR + CRSQC*CR² + SBAC*BA + BALC*BAL + SITEC*SI

    DDS = exp(ln(DDS))

where:
    - CONSPP is typically 0 (no site-specific terms in LS variant dgf.f)
    - RELDBH = D/QMDGE5 (tree diameter relative to QMD of trees >= 5")
    - CR = crown ratio as percentage (0-100)
    - BA = stand basal area (sq ft/acre)
    - BAL = basal area in larger trees (sq ft/acre)
    - SI = site index

Key differences from SN variant:
    - Uses linear/quadratic DBH terms instead of ln(DBH)
    - Uses RELDBH instead of RELHT
    - Uses linear/quadratic CR instead of ln(CR)
    - No forest type or ecological unit modifiers

Source: FVS Lake States Variant dgf.f, USDA Forest Service
"""
import math
from typing import Dict, Any, Optional

from .model_base import ParameterizedModel
from .config_loader import load_coefficient_file


class LSDiameterGrowthModel(ParameterizedModel):
    """Lake States variant diameter growth model.

    Calculates diameter squared increment (DDS) using the LS variant equation.
    Like other FVS variants, this uses ln(DDS) transformation:
        ln(DDS) = f(DBH, CR, SI, BA, BAL, RELDBH)
        DDS = exp(ln(DDS))

    Attributes:
        species_code: Species code (e.g., 'JP', 'RN', 'WP')
        coefficients: Species-specific coefficients for the ln(DDS) equation
    """

    COEFFICIENT_FILE = 'ls/ls_diameter_growth_coefficients.json'
    COEFFICIENT_KEY = 'coefficients'
    DEFAULT_SPECIES = 'RN'  # Red Pine is the default site species for LS

    # Fallback parameters for key LS species (from dgf.f)
    FALLBACK_PARAMETERS = {
        'JP': {  # Jack Pine
            'INTERC': 1.395,
            'VDBHC': -3.9398,
            'DBHC': 0.0,
            'DBH2C': 0.01213,
            'RDBHC': 1.3727,
            'RDBHSQC': -0.17735,
            'SBAC': 0.0,
            'BALC': -0.00428,
            'CRWNC': 0.02997,
            'CRSQC': -0.00015,
            'SITEC': 0.00385,
        },
        'RN': {  # Red Pine
            'INTERC': 0.21748,
            'VDBHC': 0.0,
            'DBHC': 0.30253,
            'DBH2C': -0.00885,
            'RDBHC': 0.0,
            'RDBHSQC': 0.0,
            'SBAC': -0.00114,
            'BALC': -0.00306,
            'CRWNC': 0.01947,
            'CRSQC': 0.0,
            'SITEC': 0.00581,
        },
        'WP': {  # Eastern White Pine
            'INTERC': 0.78424,
            'VDBHC': 0.0,
            'DBHC': 0.0,
            'DBH2C': 0.0,
            'RDBHC': 0.0,
            'RDBHSQC': 0.0,
            'SBAC': -0.00141,
            'BALC': -0.00251,
            'CRWNC': 0.02066,
            'CRSQC': 0.0,
            'SITEC': 0.00686,
        },
    }

    def __init__(self, species_code: str = None, variant: str = 'LS'):
        """Initialize the LS diameter growth model.

        Args:
            species_code: Species code (e.g., 'JP', 'RN', 'WP').
                         Defaults to DEFAULT_SPECIES (RN).
            variant: FVS variant (should be 'LS' for this model)
        """
        self.variant = variant
        super().__init__(species_code)

    def _get_coefficient_data(self) -> Dict[str, Any]:
        """Load coefficient data from JSON file using ConfigLoader with caching.

        Returns:
            Dictionary containing the full coefficient file data.
        """
        try:
            return load_coefficient_file(self.COEFFICIENT_FILE, variant='LS')
        except FileNotFoundError:
            return {}

    def calculate_dds(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        bal: float,
        qmd_ge5: float = None,
        time_step: float = 10.0
    ) -> float:
        """Calculate diameter squared increment (DDS).

        The LS variant uses a 10-year base period (vs 5-year for SN).
        Like other FVS variants, this calculates ln(DDS), then exponentiates.

        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio as proportion (0-1), converted to % internally
            site_index: Site index (base age 50 for LS) in feet
            ba: Stand basal area (sq ft/acre)
            bal: Basal area in larger trees (sq ft/acre)
            qmd_ge5: QMD of trees >= 5" DBH (for RELDBH calculation).
                    If None, RELDBH terms are not applied.
            time_step: Growth period in years (default 10 for LS)

        Returns:
            DDS: Change in diameter squared (sq inches inside bark)
        """
        p = self.coefficients

        # Get coefficients with defaults
        interc = p.get('INTERC', 0.0)
        vdbhc = p.get('VDBHC', 0.0)
        dbhc = p.get('DBHC', 0.0)
        dbh2c = p.get('DBH2C', 0.0)
        rdbhc = p.get('RDBHC', 0.0)
        rdbhsqc = p.get('RDBHSQC', 0.0)
        sbac = p.get('SBAC', 0.0)
        balc = p.get('BALC', 0.0)
        crwnc = p.get('CRWNC', 0.0)
        crsqc = p.get('CRSQC', 0.0)
        sitec = p.get('SITEC', 0.0)

        # Convert crown ratio to percentage (LS uses 0-100)
        cr_pct = min(99.0, max(1.0, crown_ratio * 100.0))

        # Calculate RELDBH (relative diameter)
        # RELDBH = D / QMDGE5 (tree diameter relative to QMD of trees >= 5")
        if qmd_ge5 is not None and qmd_ge5 > 0:
            reldbh = dbh / qmd_ge5
        else:
            # If no QMD provided, assume average tree (reldbh = 1.0)
            reldbh = 1.0

        # Apply FVS bounds
        ba_bounded = max(0.0, ba)  # LS doesn't have a minimum BA like SN
        bal_bounded = max(0.0, bal)

        # Prevent division by zero for small trees
        dbh_safe = max(0.1, dbh)

        # Calculate ln(DDS) using LS equation
        # ln(DDS) = INTERC + VDBHC/D + DBHC*D + DBH2C*D² + RDBHC*RELDBH
        #           + RDBHSQC*RELDBH² + CRWNC*CR + CRSQC*CR² + SBAC*BA + BALC*BAL + SITEC*SI
        ln_dds = (
            interc +
            vdbhc / dbh_safe +
            dbhc * dbh +
            dbh2c * dbh * dbh +
            rdbhc * reldbh +
            rdbhsqc * reldbh * reldbh +
            crwnc * cr_pct +
            crsqc * cr_pct * cr_pct +
            sbac * ba_bounded +
            balc * bal_bounded +
            sitec * site_index
        )

        # Apply bounds on ln(DDS) to prevent extreme values
        # ln(DDS) = -5 corresponds to DDS = 0.007 sq in (minimal growth)
        # ln(DDS) = 5 corresponds to DDS = 148 sq in (~2.2" growth per decade for 10" tree)
        # This is necessary because some species (e.g., Jack Pine) have positive DBH² coefficients
        # that can cause runaway growth without bounds
        ln_dds = max(-5.0, min(5.0, ln_dds))

        # Convert from ln(DDS) to DDS
        dds = math.exp(ln_dds)

        # Scale for time step (LS is calibrated for 10-year periods)
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
        qmd_ge5: float = None,
        time_step: float = 10.0
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
            qmd_ge5: QMD of trees >= 5" DBH
            time_step: Growth period in years (default 10)

        Returns:
            Diameter increment in inches (outside bark)
        """
        # Calculate DDS
        dds = self.calculate_dds(
            dbh=dbh,
            crown_ratio=crown_ratio,
            site_index=site_index,
            ba=ba,
            bal=bal,
            qmd_ge5=qmd_ge5,
            time_step=time_step
        )

        # Convert to inside-bark diameter
        dib_old = dbh * bark_ratio
        dib_old_sq = dib_old * dib_old

        # Apply DDS to inside-bark diameter
        dib_new = math.sqrt(dib_old_sq + dds)

        # Convert back to outside-bark diameter
        dbh_new = dib_new / bark_ratio

        # Return the increment
        return dbh_new - dbh


# Module-level cache for model instances
_model_cache: Dict[str, LSDiameterGrowthModel] = {}


def create_ls_diameter_growth_model(species_code: str = 'RN') -> LSDiameterGrowthModel:
    """Factory function to create a cached LS diameter growth model.

    Args:
        species_code: Species code (e.g., 'JP', 'RN', 'WP')

    Returns:
        Cached LSDiameterGrowthModel instance
    """
    species_upper = species_code.upper()
    if species_upper not in _model_cache:
        _model_cache[species_upper] = LSDiameterGrowthModel(species_upper)
    return _model_cache[species_upper]


# Backwards compatibility alias
get_ls_diameter_growth_model = create_ls_diameter_growth_model


def calculate_ls_diameter_growth(
    dbh: float,
    crown_ratio: float,
    site_index: float,
    ba: float,
    bal: float,
    species_code: str = 'RN',
    bark_ratio: float = 0.9,
    qmd_ge5: float = None,
    time_step: float = 10.0
) -> float:
    """Convenience function to calculate LS diameter growth.

    Args:
        dbh: Current DBH (outside bark) in inches
        crown_ratio: Crown ratio as proportion (0-1)
        site_index: Site index (base age 50) in feet
        ba: Stand basal area (sq ft/acre)
        bal: Basal area in larger trees (sq ft/acre)
        species_code: Species code (default 'RN' - Red Pine)
        bark_ratio: DIB/DOB ratio (default 0.9)
        qmd_ge5: QMD of trees >= 5" DBH
        time_step: Growth period in years (default 10)

    Returns:
        Diameter increment in inches (outside bark)
    """
    model = get_ls_diameter_growth_model(species_code)
    return model.calculate_diameter_growth(
        dbh=dbh,
        crown_ratio=crown_ratio,
        site_index=site_index,
        ba=ba,
        bal=bal,
        bark_ratio=bark_ratio,
        qmd_ge5=qmd_ge5,
        time_step=time_step
    )

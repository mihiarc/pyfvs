"""
Central States (CS) variant diameter growth model.

Implements the DDS (diameter squared increment) equation for the FVS Central States variant.
The CS variant uses the same functional form as the Lake States (LS) variant:

CS equation:
    ln(DDS) = CONSPP + INTERC + VDBHC/D + DBHC*D + DBH2C*D² + RDBHC*RELDBH
              + RDBHSQC*RELDBH² + CRWNC*CR + CRSQC*CR² + SBAC*BA + BALC*BAL + SITEC*SI

    DDS = exp(ln(DDS))

where:
    - CONSPP is typically 0 (no site-specific terms)
    - RELDBH = D/QMDGE5 (tree diameter relative to QMD of trees >= 5")
    - CR = crown ratio as percentage (0-100)
    - BA = stand basal area (sq ft/acre)
    - BAL = basal area in larger trees (sq ft/acre)
    - SI = site index

Key characteristics:
    - Covers IL, IN, IA, MO (Midwest hardwood forests)
    - 96 species including oaks, hickories, maples, ashes
    - Uses linear/quadratic DBH terms
    - Uses RELDBH for competition
    - 10-year base cycle

Source: FVS Central States Variant dgf.f, USDA Forest Service
"""
import math
from typing import Dict, Any

from .model_base import ParameterizedModel
from .config_loader import load_coefficient_file


class CSDiameterGrowthModel(ParameterizedModel):
    """Central States variant diameter growth model.

    Calculates diameter squared increment (DDS) using the CS variant equation.
    Like LS, this uses ln(DDS) transformation:
        ln(DDS) = f(DBH, CR, SI, BA, BAL, RELDBH)
        DDS = exp(ln(DDS))

    Attributes:
        species_code: Species code (e.g., 'WO', 'RO', 'SM')
        coefficients: Species-specific coefficients for the ln(DDS) equation
    """

    COEFFICIENT_FILE = 'cs/cs_diameter_growth_coefficients.json'
    COEFFICIENT_KEY = 'coefficients'
    DEFAULT_SPECIES = 'WO'  # White Oak is the default site species for CS

    # Fallback parameters for key CS species (from dgf.f)
    FALLBACK_PARAMETERS = {
        'WO': {  # White Oak
            'INTERC': 0.26619,
            'VDBHC': 0.0,
            'DBHC': 0.0,
            'DBH2C': 0.01581,
            'RDBHC': 2.05379,
            'RDBHSQC': -0.10706,
            'SBAC': 0.0,
            'BALC': -0.00404,
            'CRWNC': 0.02135,
            'CRSQC': 0.0,
            'SITEC': 0.0,
        },
        'RO': {  # Northern Red Oak
            'INTERC': 0.86285,
            'VDBHC': 0.0,
            'DBHC': 0.0,
            'DBH2C': 0.00697,
            'RDBHC': 2.20892,
            'RDBHSQC': -0.17316,
            'SBAC': -0.00178,
            'BALC': -0.00399,
            'CRWNC': 0.02196,
            'CRSQC': 0.0,
            'SITEC': 0.0,
        },
        'SM': {  # Sugar Maple
            'INTERC': 0.78100,
            'VDBHC': 0.0,
            'DBHC': 0.0,
            'DBH2C': 0.01029,
            'RDBHC': 1.69350,
            'RDBHSQC': -0.10450,
            'SBAC': -0.00101,
            'BALC': -0.00324,
            'CRWNC': 0.02033,
            'CRSQC': 0.0,
            'SITEC': 0.0,
        },
        'WN': {  # Black Walnut
            'INTERC': 0.35979,
            'VDBHC': 0.0,
            'DBHC': 0.0,
            'DBH2C': 0.01134,
            'RDBHC': 2.00810,
            'RDBHSQC': -0.07997,
            'SBAC': 0.0,
            'BALC': -0.00340,
            'CRWNC': 0.01929,
            'CRSQC': 0.0,
            'SITEC': 0.0,
        },
        'YP': {  # Yellow-Poplar (Tuliptree)
            'INTERC': 1.08040,
            'VDBHC': -4.87000,
            'DBHC': 0.0,
            'DBH2C': 0.01085,
            'RDBHC': 1.34170,
            'RDBHSQC': -0.02746,
            'SBAC': 0.0,
            'BALC': -0.00340,
            'CRWNC': 0.02139,
            'CRSQC': 0.0,
            'SITEC': 0.0,
        },
        'SP': {  # Shortleaf Pine
            'INTERC': 0.64882,
            'VDBHC': 0.0,
            'DBHC': 0.0,
            'DBH2C': 0.01234,
            'RDBHC': 2.87386,
            'RDBHSQC': -0.20916,
            'SBAC': -0.00162,
            'BALC': -0.00318,
            'CRWNC': 0.02252,
            'CRSQC': 0.0,
            'SITEC': 0.0,
        },
    }

    def __init__(self, species_code: str = None, variant: str = 'CS'):
        """Initialize the CS diameter growth model.

        Args:
            species_code: Species code (e.g., 'WO', 'RO', 'SM').
                         Defaults to DEFAULT_SPECIES (WO).
            variant: FVS variant (should be 'CS' for this model)
        """
        self.variant = variant
        super().__init__(species_code)

    def _get_coefficient_data(self) -> Dict[str, Any]:
        """Load coefficient data from JSON file using ConfigLoader with caching.

        Returns:
            Dictionary containing the full coefficient file data.
        """
        try:
            return load_coefficient_file(self.COEFFICIENT_FILE, variant='CS')
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

        The CS variant uses a 10-year base period.
        Like LS and other Eastern variants, this calculates ln(DDS), then exponentiates.

        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio as proportion (0-1), converted to % internally
            site_index: Site index (base age 50 for CS) in feet
            ba: Stand basal area (sq ft/acre)
            bal: Basal area in larger trees (sq ft/acre)
            qmd_ge5: QMD of trees >= 5" DBH (for RELDBH calculation).
                    If None, RELDBH terms are not applied.
            time_step: Growth period in years (default 10 for CS)

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

        # Convert crown ratio to percentage (CS uses 0-100)
        cr_pct = min(99.0, max(1.0, crown_ratio * 100.0))

        # Calculate RELDBH (relative diameter)
        # RELDBH = D / QMDGE5 (tree diameter relative to QMD of trees >= 5")
        if qmd_ge5 is not None and qmd_ge5 > 0:
            reldbh = dbh / qmd_ge5
        else:
            # If no QMD provided, assume average tree (reldbh = 1.0)
            reldbh = 1.0

        # Apply FVS bounds
        ba_bounded = max(0.0, ba)
        bal_bounded = max(0.0, bal)

        # Prevent division by zero for small trees
        dbh_safe = max(0.1, dbh)

        # Calculate ln(DDS) using CS equation
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
        ln_dds = max(-5.0, min(5.0, ln_dds))

        # Convert from ln(DDS) to DDS
        dds = math.exp(ln_dds)

        # Scale for time step (CS is calibrated for 10-year periods)
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
        return max(0.0, dbh_new - dbh)


# Module-level cache for model instances
_model_cache: Dict[str, CSDiameterGrowthModel] = {}


def create_cs_diameter_growth_model(species_code: str = 'WO') -> CSDiameterGrowthModel:
    """Factory function to create a cached CS diameter growth model.

    Args:
        species_code: Species code (e.g., 'WO', 'RO', 'SM')

    Returns:
        Cached CSDiameterGrowthModel instance
    """
    species_upper = species_code.upper()
    if species_upper not in _model_cache:
        _model_cache[species_upper] = CSDiameterGrowthModel(species_upper)
    return _model_cache[species_upper]


# Backwards compatibility alias
get_cs_diameter_growth_model = create_cs_diameter_growth_model


def calculate_cs_diameter_growth(
    dbh: float,
    crown_ratio: float,
    site_index: float,
    ba: float,
    bal: float,
    species_code: str = 'WO',
    bark_ratio: float = 0.9,
    qmd_ge5: float = None,
    time_step: float = 10.0
) -> float:
    """Convenience function to calculate CS diameter growth.

    Args:
        dbh: Current DBH (outside bark) in inches
        crown_ratio: Crown ratio as proportion (0-1)
        site_index: Site index (base age 50) in feet
        ba: Stand basal area (sq ft/acre)
        bal: Basal area in larger trees (sq ft/acre)
        species_code: Species code (default 'WO' - White Oak)
        bark_ratio: DIB/DOB ratio (default 0.9)
        qmd_ge5: QMD of trees >= 5" DBH
        time_step: Growth period in years (default 10)

    Returns:
        Diameter increment in inches (outside bark)
    """
    model = get_cs_diameter_growth_model(species_code)
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

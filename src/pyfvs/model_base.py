"""
Base class for parameterized FVS growth models.

Provides common functionality for loading species-specific coefficients
from JSON configuration files with caching and fallback support.

This module eliminates code duplication across model classes like:
- BarkRatioModel
- CrownWidthModel
- CrownRatioModel
- CrownCompetitionFactorModel

Usage:
    class BarkRatioModel(ParameterizedModel):
        COEFFICIENT_FILE = 'sn_bark_ratio_coefficients.json'
        COEFFICIENT_KEY = 'species_coefficients'
        FALLBACK_PARAMETERS = {
            'LP': {'b1': -0.48140, 'b2': 0.91413}
        }

        def __init__(self, species_code: str = "LP"):
            super().__init__(species_code)
"""
import logging
import math
import random
from abc import ABC
from typing import Dict, Any, Optional

from .config_loader import load_coefficient_file
from .species import SpeciesCode

logger = logging.getLogger("pyfvs.model_base")


def dds_to_diameter_growth(dds: float, dbh: float, bark_ratio: float) -> float:
    """Convert inside-bark DDS to outside-bark diameter growth.

    Implements the Fortran dgdriv.f DDS-to-DG conversion used by most
    FVS variants (SN, PN, WC, CA, EC, OC, WS):

        D     = DBH(I) * BRATIO(...)         ! OB → IB
        DDS   = EXP(WK2(I) + XDGROW) * WK4  ! (already computed by caller)
        DG(I) = SQRT(D*D + DDS*FRM) - D      ! DG in IB space

    Then update.f converts back:

        DBH(I) = DBH(I) + DG(I) / BRATIO(...)  ! IB → OB

    Variants with different conventions (LS/CS: OB DDS then OB→IB DG;
    NE: pure OB; OP: direct DG) should NOT use this function.

    Args:
        dds: Change in inside-bark diameter squared (sq inches).
        dbh: Current outside-bark DBH (inches).
        bark_ratio: DIB/DOB ratio (0 < bark_ratio <= 1).

    Returns:
        Outside-bark diameter growth in inches, non-negative.
    """
    if bark_ratio <= 0:
        bark_ratio = 1.0
    dib = dbh * bark_ratio
    dib_sq = dib * dib
    new_dib_sq = dib_sq + dds
    if new_dib_sq <= dib_sq:
        return 0.0
    new_dbh = math.sqrt(new_dib_sq) / bark_ratio
    return new_dbh - dbh


class ParameterizedModel(ABC):
    """Base class for FVS growth models with species-specific coefficients.

    Subclasses must define:
        COEFFICIENT_FILE: str - Name of the JSON file containing coefficients
        COEFFICIENT_KEY: str - Key in the JSON file containing species coefficients
        FALLBACK_PARAMETERS: dict - Fallback coefficients by species code

    Optional class attributes:
        DEFAULT_SPECIES: str - Default species code (default: "LP")

    Attributes:
        species_code: The species code for this model instance
        coefficients: The loaded coefficients for the species
        raw_data: The complete raw data loaded from the coefficient file
    """

    # Subclasses must override these
    COEFFICIENT_FILE: str = None
    COEFFICIENT_KEY: str = 'species_coefficients'
    FALLBACK_PARAMETERS: Dict[str, Dict[str, Any]] = {}
    DEFAULT_SPECIES: str = SpeciesCode.LOBLOLLY_PINE.value

    # Formerly controlled Baskerville correction in deterministic mode.
    # Removed: Fortran dgscor.f returns FRM=1.0 when DGSD<1 (deterministic),
    # so no correction should be applied.  Kept as no-op for subclass compat.
    _use_baskerville: bool = True

    def __init__(self, species_code: str = None):
        """Initialize the model with species-specific parameters.

        Args:
            species_code: Species code (e.g., "LP", "SP", "SA", etc.).
                         Defaults to DEFAULT_SPECIES if not provided.
        """
        if species_code is None:
            species_code = self.DEFAULT_SPECIES
        self.species_code = species_code
        self.coefficients: Dict[str, Any] = {}
        self.raw_data: Dict[str, Any] = {}
        self._sigma: float = 0.0
        self._load_parameters()

    def _get_coefficient_data(self) -> Dict[str, Any]:
        """Load coefficient data from JSON file using ConfigLoader with caching.

        Returns:
            Dictionary containing the full coefficient file data,
            or empty dict if file not found.
        """
        if self.COEFFICIENT_FILE is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define COEFFICIENT_FILE class attribute"
            )

        try:
            return load_coefficient_file(self.COEFFICIENT_FILE)
        except FileNotFoundError:
            logger.warning(
                "%s: coefficient file '%s' not found, using fallback parameters",
                self.__class__.__name__, self.COEFFICIENT_FILE,
            )
            return {}

    def _load_parameters(self) -> None:
        """Load species-specific parameters from configuration.

        This method:
        1. Loads the coefficient file data (cached)
        2. Extracts species-specific coefficients
        3. Falls back to LP coefficients if species not found
        4. Falls back to FALLBACK_PARAMETERS if file loading fails

        Subclasses can override this method for custom loading logic,
        but should call super()._load_parameters() first.
        """
        self.raw_data = self._get_coefficient_data()

        if self.raw_data:
            # Get species coefficients from the configured key
            species_coeffs = self.raw_data.get(self.COEFFICIENT_KEY, {})

            if not species_coeffs:
                logger.warning(
                    "%s: key '%s' not found in '%s', using fallback parameters",
                    self.__class__.__name__, self.COEFFICIENT_KEY, self.COEFFICIENT_FILE,
                )

            if self.species_code in species_coeffs:
                self.coefficients = species_coeffs[self.species_code]
            elif self.DEFAULT_SPECIES in species_coeffs:
                # Fallback to default species if current species not found
                logger.warning(
                    "%s: species '%s' not found in '%s', falling back to DEFAULT_SPECIES '%s'",
                    self.__class__.__name__, self.species_code,
                    self.COEFFICIENT_FILE, self.DEFAULT_SPECIES,
                )
                self.coefficients = species_coeffs[self.DEFAULT_SPECIES]
            else:
                # Fallback to hardcoded parameters
                self._load_fallback_parameters()
        else:
            # Fallback if file not found or empty
            self._load_fallback_parameters()

    def _load_fallback_parameters(self) -> None:
        """Load fallback parameters when coefficient file is not available.

        Uses FALLBACK_PARAMETERS class attribute to get coefficients.
        Subclasses can override this to add additional fallback data
        (e.g., equation_info, bounds).
        """
        if self.species_code in self.FALLBACK_PARAMETERS:
            logger.warning(
                "%s: using FALLBACK_PARAMETERS for species '%s'",
                self.__class__.__name__, self.species_code,
            )
            self.coefficients = self.FALLBACK_PARAMETERS[self.species_code].copy()
        elif self.DEFAULT_SPECIES in self.FALLBACK_PARAMETERS:
            logger.warning(
                "%s: using FALLBACK_PARAMETERS for DEFAULT_SPECIES '%s' (species '%s' not found)",
                self.__class__.__name__, self.DEFAULT_SPECIES, self.species_code,
            )
            self.coefficients = self.FALLBACK_PARAMETERS[self.DEFAULT_SPECIES].copy()
        else:
            logger.error(
                "%s: no coefficients loaded for species '%s' — "
                "file '%s' missing/empty and no FALLBACK_PARAMETERS defined",
                self.__class__.__name__, self.species_code, self.COEFFICIENT_FILE,
            )
            self.coefficients = {}

    def get_species_coefficients(self) -> Dict[str, Any]:
        """Get the coefficients for this species.

        Returns:
            Dictionary containing species-specific coefficients.
        """
        return self.coefficients.copy()

    def get_raw_data(self) -> Dict[str, Any]:
        """Get the full raw data loaded from the coefficient file.

        Returns:
            Dictionary containing all data from the coefficient file.
        """
        return self.raw_data.copy()

    def get_coefficient(self, key: str, default: Any = None) -> Any:
        """Get a specific coefficient value.

        Args:
            key: Coefficient key to retrieve
            default: Default value if key not found

        Returns:
            Coefficient value or default
        """
        return self.coefficients.get(key, default)

    def _load_sigma(self) -> float:
        """Load SIGMAR for this species from variance_parameters.

        SIGMAR is the standard deviation of ln(DDS) residuals, used for
        the Baskerville (1972) bias correction or stochastic draws.

        Returns:
            SIGMAR value, or 0.0 if not found.
        """
        variance_params = self.raw_data.get('variance_parameters', {})
        return variance_params.get(self.species_code, 0.0)

    def _stochastic_multiplier(self, ln_dds: float, rng: random.Random = None) -> float:
        """DDS multiplier: 1.0 (deterministic) or random draw (stochastic).

        Matches Fortran dgscor.f behavior:
        - When DGSD < 1.0 (deterministic): FRM = EXP(0.0) = 1.0.
          No Baskerville correction — the coefficients were calibrated
          expecting this, and the bias is built in.
        - When DGSD >= 1.0 (stochastic): draw Z ~ N(0, sigma²) bounded
          +/- DGSD*sigma with size-based suppression, return EXP(Z).
        """
        if self._sigma <= 0.0:
            return 1.0

        if rng is None:
            # Deterministic: Fortran dgscor.f returns FRM = EXP(0) = 1.0
            return 1.0

        # Stochastic: draw bounded normal (dgscor.f)
        if ln_dds > 5.0:
            return 1.0
        suppress = (5.0 - ln_dds) / 1.0 if ln_dds > 4.0 else 1.0

        dgsd = 2.0
        z = rng.gauss(0.0, self._sigma)
        z = max(-dgsd * self._sigma, min(dgsd * self._sigma, z))
        z *= suppress
        return math.exp(z)

    def __repr__(self) -> str:
        """Return string representation of the model."""
        return f"{self.__class__.__name__}(species_code='{self.species_code}')"

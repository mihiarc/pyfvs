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
import functools
import logging
import math
import random
from abc import ABC
from typing import Dict, Any, Optional, Tuple

from .config_loader import load_coefficient_file
from .species import SpeciesCode

logger = logging.getLogger("pyfvs.model_base")


class StochasticDGState:
    """Per-tree carry state for AR(1) DG noise (Fortran OLDRN(IT))."""
    __slots__ = ('oldrn',)

    def __init__(self, oldrn: float = 0.0):
        self.oldrn = oldrn


@functools.lru_cache(maxsize=8)
def _bjrho_table(bjphi: float, bjthet: float) -> Tuple[float, ...]:
    """ARMA(1,1) serial correlation function (40 terms). Mirror autcor.f:44-48."""
    rho1 = (1.0 - bjphi * bjthet) * (bjphi - bjthet) / (1.0 + bjthet * (bjthet - 2.0 * bjphi))
    table = [rho1]
    for _ in range(1, 40):
        table.append(table[-1] * bjphi)
    return tuple(table)


@functools.lru_cache(maxsize=64)
def _autcor(new: int, nold: int, bjphi: float, bjthet: float) -> Tuple[float, float]:
    """Variance multiplier (VMLT) and covariance (COVMLT). Mirror autcor.f:60-93."""
    bjrho = _bjrho_table(bjphi, bjthet)

    var = float(new)
    for i in range(1, new):
        var += 2.0 * bjrho[i - 1] * (new - i)
    vmlt = var

    L = min(new + nold - 1, 40)
    nbig = max(new, nold)
    nsml = min(new, nold)
    t, dt = 0.0, 1.0
    covar = 0.0
    for i in range(1, L + 1):
        t += dt
        covar += bjrho[i - 1] * t
        if i == nsml:
            dt = 0.0
        if i == nbig:
            dt = -1.0

    return vmlt, covar


@functools.lru_cache(maxsize=256)
def _ar1_weights(sigma: float, time_step: int, prev_time_step: int,
                 bjphi: float, bjthet: float) -> Tuple[float, float, float]:
    """Per-species AR(1) weights for current cycle. Mirror dgdriv.f:121-160.

    Returns (rho, rhocp, ssigma):
        rho    -- weight on previous cycle's saved FRM
        rhocp  -- weight on fresh draw, sqrt(1-rho^2)
        ssigma -- bounded normal std for fresh draw (cycle-scaled SIGMA)
    """
    if sigma <= 0.0:
        return 0.0, 1.0, 0.0

    new = max(1, int(time_step))
    nold = max(1, int(prev_time_step))

    vmlt, covmlt = _autcor(new, nold, bjphi, bjthet)
    pvmlt, _ = _autcor(nold, nold, bjphi, bjthet)

    if vmlt <= 0.0 or pvmlt <= 0.0:
        return 0.0, 1.0, sigma

    corr = covmlt / math.sqrt(vmlt * pvmlt)

    sigma2 = sigma * sigma
    vtemp = math.exp(sigma2)
    vmltyr = pvmlt
    vardg = (vtemp - 1.0) * vtemp / vmltyr

    varyp1 = vardg * pvmlt
    varyp2 = vardg * vmlt
    evarp1 = (math.sqrt(1.0 + 4.0 * varyp1) + 1.0) / 2.0
    evarp2 = (math.sqrt(1.0 + 4.0 * varyp2) + 1.0) / 2.0

    sig1 = math.sqrt(math.log(evarp1)) if evarp1 > 1.0 else 0.0
    ssigma = math.sqrt(math.log(evarp2)) if evarp2 > 1.0 else 0.0

    if sig1 <= 0.0 or ssigma <= 0.0:
        return 0.0, max(0.0, ssigma), ssigma

    inner = corr * math.sqrt(max(0.0, evarp1 - 1.0) * max(0.0, evarp2 - 1.0))
    rho = math.log(max(1e-9, 1.0 + inner)) / (sig1 * ssigma)
    rho = max(-0.99, min(0.99, rho))
    rhocp = math.sqrt(1.0 - rho * rho)

    return rho, rhocp, ssigma


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
        """Load SIGMAR (std dev of ln(DDS) residuals) from variance_parameters.

        Used as the scale parameter for the stochastic random draw.  Not
        used in deterministic mode — pyfvs mirrors Fortran dgscor.f, which
        returns FRM=1.0 when DGSD<1.0.

        Returns:
            SIGMAR value, or 0.0 if not found.
        """
        variance_params = self.raw_data.get('variance_parameters', {})
        return variance_params.get(self.species_code, 0.0)

    def _stochastic_multiplier(
        self,
        ln_dds: float,
        rng: random.Random = None,
        state: Optional[StochasticDGState] = None,
        time_step: float = 5.0,
        prev_time_step: Optional[float] = None,
        bjphi: float = 0.74,
        bjthet: float = 0.42,
    ) -> float:
        """DDS multiplier matching Fortran dgscor.f, including AR(1) carry.

        Implements the full chain: AUTCOR (variance/covariance multipliers from
        ARMA(1,1) parameters) -> per-species RHO/RHOCP/SSIGMA -> DGSCOR
        (truncated normal blended with previous cycle's saved FRM via OLDRN).

        - Deterministic (rng=None, Fortran DGSD<1.0): returns 1.0; resets
          state.oldrn=0 so a later switch into stochastic doesn't blend stale
          carry.
        - Stochastic (rng set, Fortran DGSD>=1.0): draw eps~N(0, ssigma^2);
          FRM = eps*RHOCP + RHO*OLDRN_in (rejected/redrawn if |FRM|>DGSD*SSIGMA);
          tail attenuation for ln_dds in (4,5] (multiply by ln_dds-4) or zero
          for ln_dds>5; save FRM as new OLDRN; return exp(FRM).
        """
        if self._sigma <= 0.0:
            return 1.0

        if rng is None:
            if state is not None:
                state.oldrn = 0.0
            return 1.0

        rho, rhocp, ssigma = _ar1_weights(
            self._sigma,
            int(time_step) if time_step > 0 else 5,
            int(prev_time_step) if prev_time_step is not None and prev_time_step > 0
            else (int(time_step) if time_step > 0 else 5),
            bjphi,
            bjthet,
        )

        if ssigma <= 0.0:
            if state is not None:
                state.oldrn = 0.0
            return 1.0

        dgsd = 2.0
        bound = dgsd * ssigma
        oldrn_in = state.oldrn if state is not None else 0.0

        # dgscor.f BACHLO loop with rejection on |FRM|>DGSD*SSIG.
        frm = 0.0
        for _ in range(100):
            eps = rng.gauss(0.0, ssigma)
            frm = eps * rhocp + rho * oldrn_in
            if abs(frm) <= bound:
                break
        else:
            frm = max(-bound, min(bound, frm))

        # dgscor.f:42-47 tail attenuation on ln(DDS).
        if ln_dds > 5.0:
            frm = 0.0
        elif ln_dds > 4.0:
            frm = (ln_dds - 4.0) * frm

        if state is not None:
            state.oldrn = frm

        return math.exp(frm)

    def __repr__(self) -> str:
        """Return string representation of the model."""
        return f"{self.__class__.__name__}(species_code='{self.species_code}')"

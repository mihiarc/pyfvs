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
from abc import ABC
from typing import Dict, Any, Optional

from .config_loader import load_coefficient_file
from .species import SpeciesCode


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

            if self.species_code in species_coeffs:
                self.coefficients = species_coeffs[self.species_code]
            elif self.DEFAULT_SPECIES in species_coeffs:
                # Fallback to default species if current species not found
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
            self.coefficients = self.FALLBACK_PARAMETERS[self.species_code].copy()
        elif self.DEFAULT_SPECIES in self.FALLBACK_PARAMETERS:
            self.coefficients = self.FALLBACK_PARAMETERS[self.DEFAULT_SPECIES].copy()
        else:
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

    def __repr__(self) -> str:
        """Return string representation of the model."""
        return f"{self.__class__.__name__}(species_code='{self.species_code}')"

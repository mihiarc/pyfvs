"""
Ecological unit classification system for FVS-Python.

Implements the FVS Southern variant ecological unit (ECOUNIT) classification system
for modifying growth predictions based on ecological subsection codes.

The system uses two coefficient tables:
- Table 4.7.1.5: For mountain/province-level ecounits (M221, M222, M231, 221, 222, 231T)
- Table 4.7.1.6: For lowland ecounits (231L, 232, 234, 255, 411)
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, Set
from .config_loader import get_config_loader
from .exceptions import ConfigurationError


# Define the ecological unit groups for each table
MOUNTAIN_PROVINCE_ECOUNITS: Set[str] = {"M221", "M222", "M231", "221", "222", "231T"}
LOWLAND_ECOUNITS: Set[str] = {"231L", "232", "234", "255", "411"}


def select_ecounit_table(ecounit_group: str) -> str:
    """Determine which coefficient table to use based on ecological unit group.

    Table 4.7.1.5 is used for mountain/province-level ecounits:
        M221, M222, M231, 221, 222, 231T

    Table 4.7.1.6 is used for lowland ecounits:
        231L, 232, 234, 255, 411

    Args:
        ecounit_group: Ecological unit group code (e.g., "M221", "232", "231L")

    Returns:
        Table identifier string: "table_4_7_1_5" or "table_4_7_1_6"
    """
    normalized_group = ecounit_group.upper().strip()

    if normalized_group in MOUNTAIN_PROVINCE_ECOUNITS:
        return "table_4_7_1_5"
    elif normalized_group in LOWLAND_ECOUNITS:
        return "table_4_7_1_6"
    else:
        # Unknown ecounit - default to table 4.7.1.5 as it has broader coverage
        return "table_4_7_1_5"


class EcologicalUnitClassifier:
    """Classifier for mapping ecological subsection codes to ECOUNIT groups.

    This class implements the FVS Southern variant ecological unit classification
    system, handling both Table 4.7.1.5 (mountain/province-level regions) and
    Table 4.7.1.6 (lowland regions).
    """

    # Class-level cache for coefficient tables
    _coefficients_table_5: Optional[Dict[str, Any]] = None
    _coefficients_table_6: Optional[Dict[str, Any]] = None
    _tables_loaded: bool = False

    def __init__(self):
        """Initialize the ecological unit classifier."""
        if not EcologicalUnitClassifier._tables_loaded:
            self._load_coefficient_tables()

    def _load_coefficient_tables(self) -> None:
        """Load coefficient tables from JSON files in the cfg directory."""
        try:
            loader = get_config_loader()
            cfg_dir = loader.cfg_dir

            # Load Table 4.7.1.5 (mountain/province ecounits)
            table_5_path = cfg_dir / "ecounit_coefficients_table_4_7_1_5.json"
            if table_5_path.exists():
                with open(table_5_path, 'r', encoding='utf-8') as f:
                    EcologicalUnitClassifier._coefficients_table_5 = json.load(f)
            else:
                EcologicalUnitClassifier._coefficients_table_5 = self._get_empty_table()

            # Load Table 4.7.1.6 (lowland ecounits)
            table_6_path = cfg_dir / "ecounit_coefficients_table_4_7_1_6.json"
            if table_6_path.exists():
                with open(table_6_path, 'r', encoding='utf-8') as f:
                    EcologicalUnitClassifier._coefficients_table_6 = json.load(f)
            else:
                EcologicalUnitClassifier._coefficients_table_6 = self._get_empty_table()

            EcologicalUnitClassifier._tables_loaded = True

        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Failed to parse ecological unit coefficient files: {str(e)}"
            ) from e
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            # Set empty tables to avoid repeated failures
            EcologicalUnitClassifier._coefficients_table_5 = self._get_empty_table()
            EcologicalUnitClassifier._coefficients_table_6 = self._get_empty_table()
            EcologicalUnitClassifier._tables_loaded = True

    @staticmethod
    def _get_empty_table() -> Dict[str, Any]:
        """Return an empty coefficient table structure."""
        return {
            "table_description": "Empty fallback table",
            "ecological_unit_groups": {},
            "species_coefficients": {}
        }

    def get_coefficient(self, species_code: str, ecounit_group: str) -> float:
        """Get the ecological unit coefficient for a species and ecounit group.

        Args:
            species_code: FVS species code (e.g., "LP", "SP", "WO")
            ecounit_group: Ecological unit group code (e.g., "M221", "232")

        Returns:
            The coefficient value to add to the growth equation.
            Returns 0.0 if the species or ecounit is not found.
        """
        normalized_species = species_code.upper().strip()
        normalized_ecounit = ecounit_group.upper().strip()

        # Select the appropriate table
        table_name = select_ecounit_table(normalized_ecounit)

        if table_name == "table_4_7_1_5":
            coefficients = self._coefficients_table_5
        else:
            coefficients = self._coefficients_table_6

        if coefficients is None:
            return 0.0

        # Look up species coefficients
        species_data = coefficients.get("species_coefficients", {}).get(normalized_species)
        if species_data is None:
            return 0.0

        # Look up ecounit coefficient
        ecounit_coefficients = species_data.get("coefficients", {})
        return ecounit_coefficients.get(normalized_ecounit, 0.0)

    def get_base_ecounit(self, species_code: str, table: str = "table_4_7_1_5") -> Optional[str]:
        """Get the base ecological unit for a species."""
        normalized_species = species_code.upper().strip()

        if table == "table_4_7_1_5":
            coefficients = self._coefficients_table_5
        else:
            coefficients = self._coefficients_table_6

        if coefficients is None:
            return None

        species_data = coefficients.get("species_coefficients", {}).get(normalized_species)
        if species_data is None:
            return None

        return species_data.get("base_ecounit")

    def get_available_species(self, table: str = "table_4_7_1_5") -> list:
        """Get list of species codes available in a coefficient table."""
        if table == "table_4_7_1_5":
            coefficients = self._coefficients_table_5
        else:
            coefficients = self._coefficients_table_6

        if coefficients is None:
            return []

        return list(coefficients.get("species_coefficients", {}).keys())

    def get_all_coefficients_for_species(self, species_code: str) -> Dict[str, float]:
        """Get all ecological unit coefficients for a species across both tables."""
        normalized_species = species_code.upper().strip()
        all_coefficients = {}

        # Get coefficients from Table 4.7.1.5
        if self._coefficients_table_5:
            species_data = self._coefficients_table_5.get(
                "species_coefficients", {}
            ).get(normalized_species, {})
            all_coefficients.update(species_data.get("coefficients", {}))

        # Get coefficients from Table 4.7.1.6
        if self._coefficients_table_6:
            species_data = self._coefficients_table_6.get(
                "species_coefficients", {}
            ).get(normalized_species, {})
            all_coefficients.update(species_data.get("coefficients", {}))

        return all_coefficients

    def is_lowland_ecounit(self, ecounit_group: str) -> bool:
        """Check if an ecological unit group is classified as lowland."""
        normalized_ecounit = ecounit_group.upper().strip()
        return normalized_ecounit in LOWLAND_ECOUNITS

    def is_mountain_province_ecounit(self, ecounit_group: str) -> bool:
        """Check if an ecological unit group is classified as mountain/province."""
        normalized_ecounit = ecounit_group.upper().strip()
        return normalized_ecounit in MOUNTAIN_PROVINCE_ECOUNITS

    @classmethod
    def reset_cache(cls) -> None:
        """Reset the cached coefficient tables."""
        cls._coefficients_table_5 = None
        cls._coefficients_table_6 = None
        cls._tables_loaded = False


def get_ecounit_effect(species_code: str, ecounit_group: str) -> float:
    """Get the ecological unit coefficient for a given species and ecounit group.

    Loads the appropriate coefficient table based on whether the ecounit is
    in a lowland or upland/mountain region, then returns the coefficient
    that should be added to the base growth equation.

    Args:
        species_code: FVS species code (e.g., "LP", "SP", "WO")
        ecounit_group: Ecological unit group code (e.g., "M221", "232")

    Returns:
        The ecological unit coefficient (effect) for the species/ecounit combination.
        Returns 0.0 if the species or ecounit is not found in the table.
    """
    classifier = EcologicalUnitClassifier()
    return classifier.get_coefficient(species_code, ecounit_group)


def create_classifier() -> EcologicalUnitClassifier:
    """Factory function to create an ecological unit classifier."""
    return EcologicalUnitClassifier()


def get_ecounit_summary(species_code: str) -> Dict[str, Any]:
    """Get a summary of ecological unit effects for a species."""
    classifier = EcologicalUnitClassifier()
    normalized_species = species_code.upper().strip()

    # Get effects from both tables
    mountain_effects = {}
    lowland_effects = {}

    for ecounit in MOUNTAIN_PROVINCE_ECOUNITS:
        coeff = classifier.get_coefficient(normalized_species, ecounit)
        if coeff != 0.0 or ecounit == classifier.get_base_ecounit(
            normalized_species, "table_4_7_1_5"
        ):
            mountain_effects[ecounit] = coeff

    for ecounit in LOWLAND_ECOUNITS:
        coeff = classifier.get_coefficient(normalized_species, ecounit)
        if coeff != 0.0 or ecounit == classifier.get_base_ecounit(
            normalized_species, "table_4_7_1_6"
        ):
            lowland_effects[ecounit] = coeff

    return {
        "species": normalized_species,
        "mountain_province_effects": mountain_effects,
        "lowland_effects": lowland_effects,
        "base_ecounit_table_5": classifier.get_base_ecounit(
            normalized_species, "table_4_7_1_5"
        ),
        "base_ecounit_table_6": classifier.get_base_ecounit(
            normalized_species, "table_4_7_1_6"
        )
    }

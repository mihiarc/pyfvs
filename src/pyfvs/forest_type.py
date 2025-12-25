"""
Forest Type Classification System for FVS-Python.

This module implements the FVS forest type classification system, which maps
FIA forest type codes to FVS forest type groups. These groups are used in
diameter increment and other growth models.

Forest Type Groups (SN variant):
    - FTLOHD: Lowland Hardwoods
    - FTNOHD: Northern Hardwoods
    - FTOKPN: Oak-Pine
    - FTSFHP: Spruce-Fir-Hemlock-Pine
    - FTUPHD: Upland Hardwoods
    - FTUPOK: Upland Oak
    - FTYLPN: Yellow Pine

Reference: FVS Southern variant documentation, Tables 4.7.1.3 and 4.7.1.4
"""
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from .config_loader import load_coefficient_file


class ForestTypeGroup(str, Enum):
    """Enumeration of FVS forest type groups."""
    FTLOHD = "FTLOHD"  # Lowland Hardwoods
    FTNOHD = "FTNOHD"  # Northern Hardwoods
    FTOKPN = "FTOKPN"  # Oak-Pine
    FTSFHP = "FTSFHP"  # Spruce-Fir-Hemlock-Pine
    FTUPHD = "FTUPHD"  # Upland Hardwoods
    FTUPOK = "FTUPOK"  # Upland Oak
    FTYLPN = "FTYLPN"  # Yellow Pine


@dataclass
class ForestTypeResult:
    """Result of forest type classification.

    Attributes:
        fia_type_code: The FIA forest type code (if determined)
        forest_type_group: The FVS forest type group
        group_name: Human-readable name of the forest type group
        confidence: Confidence in the classification (0-1)
        dominant_species: The dominant species code in the stand
        species_composition: Dictionary of species codes to proportions
    """
    fia_type_code: Optional[int]
    forest_type_group: str
    group_name: str
    confidence: float
    dominant_species: Optional[str]
    species_composition: Dict[str, float]


# FIA forest type to FVS forest type group mapping
# Based on Table 4.7.1.4 from FVS Southern variant documentation
FIA_TO_FVS_MAPPING: Dict[str, Dict[str, Any]] = {
    "FTLOHD": {
        "name": "Lowland Hardwoods",
        "fia_forest_types": [168, 508, 601, 602, 605, 606, 607, 608, 702, 703, 704, 705, 706, 708]
    },
    "FTNOHD": {
        "name": "Northern Hardwoods",
        "fia_forest_types": [701, 801, 805]
    },
    "FTOKPN": {
        "name": "Oak - Pine",
        "fia_forest_types": [165, 403, 404, 405, 406, 407, 409]
    },
    "FTSFHP": {
        "name": "Spruce - Fir - Hemlock - Pine",
        "fia_forest_types": [104, 105, 121, 124]
    },
    "FTUPHD": {
        "name": "Upland Hardwoods",
        "fia_forest_types": [103, 167, 181, 401, 402, 506, 511, 512, 513, 519, 520, 802, 807, 809]
    },
    "FTUPOK": {
        "name": "Upland Oak",
        "fia_forest_types": [501, 502, 503, 504, 505, 510, 514, 515]
    },
    "FTYLPN": {
        "name": "Yellow Pine",
        "fia_forest_types": [141, 142, 161, 162, 163, 164, 166]
    }
}

# Species code to forest type group mapping for when FIA type is unknown
SPECIES_TO_FOREST_TYPE: Dict[str, str] = {
    # Yellow Pine species (FTYLPN)
    "LP": "FTYLPN", "SP": "FTYLPN", "SA": "FTYLPN", "LL": "FTYLPN",
    "VP": "FTYLPN", "TM": "FTYLPN", "PP": "FTYLPN", "PD": "FTYLPN", "PS": "FTYLPN",
    # Oak species (FTUPOK)
    "WO": "FTUPOK", "SO": "FTUPOK", "RO": "FTUPOK", "BO": "FTUPOK",
    "PO": "FTUPOK", "CO": "FTUPOK", "SK": "FTUPOK", "TO": "FTUPOK",
    "BJ": "FTUPOK", "CK": "FTUPOK", "WK": "FTUPOK",
    # Lowland Hardwoods (FTLOHD)
    "BY": "FTLOHD", "PC": "FTLOHD", "SR": "FTLOHD", "LO": "FTLOHD",
    "OV": "FTLOHD", "WI": "FTLOHD", "CB": "FTLOHD", "SN": "FTLOHD",
    "LK": "FTLOHD", "WT": "FTLOHD", "BB": "FTLOHD", "SB": "FTLOHD",
    "RM": "FTLOHD", "SV": "FTLOHD", "EL": "FTLOHD", "RL": "FTLOHD",
    "SY": "FTLOHD", "CW": "FTLOHD", "BA": "FTLOHD", "GA": "FTLOHD", "HL": "FTLOHD",
    # Upland Hardwoods (FTUPHD)
    "YP": "FTUPHD", "HI": "FTUPHD", "SM": "FTUPHD", "BN": "FTUPHD",
    "WN": "FTUPHD", "SS": "FTUPHD", "DW": "FTUPHD", "RD": "FTUPHD",
    "SD": "FTUPHD", "BG": "FTUPHD", "BC": "FTUPHD", "WA": "FTUPHD",
    "AB": "FTUPHD", "BK": "FTUPHD",
    # Northern Hardwoods (FTNOHD)
    "BU": "FTNOHD", "BD": "FTNOHD",
    # Spruce-Fir-Hemlock-Pine (FTSFHP)
    "HM": "FTSFHP", "FR": "FTSFHP", "PI": "FTSFHP", "WP": "FTSFHP", "PU": "FTSFHP",
}


class ForestTypeClassifier:
    """Classifier for determining FVS forest type groups from stand composition."""

    def __init__(self):
        """Initialize the forest type classifier."""
        # Build reverse mapping from FIA code to forest type group
        self._fia_to_group: Dict[int, str] = {}
        self._group_names: Dict[str, str] = {}

        for group_code, group_data in FIA_TO_FVS_MAPPING.items():
            self._group_names[group_code] = group_data["name"]
            for fia_code in group_data["fia_forest_types"]:
                self._fia_to_group[fia_code] = group_code

        self._fortype_coefficients: Optional[Dict[str, Any]] = None

    def _load_fortype_coefficients(self) -> Dict[str, Any]:
        """Load forest type coefficients using ConfigLoader (with caching)."""
        if self._fortype_coefficients is not None:
            return self._fortype_coefficients

        try:
            self._fortype_coefficients = load_coefficient_file('fortype_coefficients_table_4_7_1_3.json')
        except FileNotFoundError:
            self._fortype_coefficients = {"species_coefficients": {}}

        return self._fortype_coefficients

    def fia_to_fvs_group(self, fia_type_code: int) -> Optional[str]:
        """Map an FIA forest type code to an FVS forest type group."""
        return self._fia_to_group.get(fia_type_code)

    def get_group_name(self, forest_type_group: str) -> str:
        """Get the human-readable name for a forest type group."""
        return self._group_names.get(forest_type_group, "Unknown")

    def classify_from_species(self, species_code: str) -> str:
        """Classify forest type from a single species code."""
        species_upper = species_code.upper()
        if species_upper in SPECIES_TO_FOREST_TYPE:
            return SPECIES_TO_FOREST_TYPE[species_upper]
        return "FTUPHD"  # Default

    def classify_from_trees(self, trees: List[Any], basal_area_weighted: bool = True) -> ForestTypeResult:
        """Classify forest type from a list of trees."""
        if not trees:
            return ForestTypeResult(
                fia_type_code=None, forest_type_group="FTYLPN",
                group_name="Yellow Pine", confidence=0.0,
                dominant_species=None, species_composition={}
            )

        species_weights: Dict[str, float] = Counter()
        for tree in trees:
            species = getattr(tree, 'species', None)
            if species is None:
                continue
            species = species.upper()
            if basal_area_weighted:
                dbh = getattr(tree, 'dbh', 1.0)
                weight = dbh * dbh
            else:
                weight = 1.0
            species_weights[species] += weight

        if not species_weights:
            return ForestTypeResult(
                fia_type_code=None, forest_type_group="FTYLPN",
                group_name="Yellow Pine", confidence=0.0,
                dominant_species=None, species_composition={}
            )

        total_weight = sum(species_weights.values())
        species_composition = {sp: wt / total_weight for sp, wt in species_weights.items()}
        dominant_species = max(species_weights.keys(), key=lambda s: species_weights[s])

        group_weights: Dict[str, float] = Counter()
        for species, proportion in species_composition.items():
            group = self.classify_from_species(species)
            group_weights[group] += proportion

        dominant_group = max(group_weights.keys(), key=lambda g: group_weights[g])
        confidence = group_weights[dominant_group]

        return ForestTypeResult(
            fia_type_code=None, forest_type_group=dominant_group,
            group_name=self.get_group_name(dominant_group),
            confidence=confidence, dominant_species=dominant_species,
            species_composition=species_composition
        )

    def get_forest_type_coefficient(self, species_code: str, forest_type_group: str) -> float:
        """Get the forest type coefficient for a species and forest type group."""
        coefficients = self._load_fortype_coefficients()
        species_data = coefficients.get("species_coefficients", {})
        species_upper = species_code.upper()

        if species_upper not in species_data:
            return 0.0

        fortype_codes = species_data[species_upper].get("fortype_codes", {})
        return fortype_codes.get(forest_type_group, 0.0)

    def get_base_forest_type(self, species_code: str) -> str:
        """Get the base (default) forest type for a species."""
        coefficients = self._load_fortype_coefficients()
        species_data = coefficients.get("species_coefficients", {})
        species_upper = species_code.upper()

        if species_upper not in species_data:
            return "FTUPHD"

        return species_data[species_upper].get("base_fortype", "FTUPHD")


def get_forest_type_effect(species_code: str, forest_type_group: str) -> float:
    """Get the forest type effect coefficient for growth calculations."""
    classifier = ForestTypeClassifier()
    return classifier.get_forest_type_coefficient(species_code, forest_type_group)


def classify_forest_type_from_species(species_code: str) -> str:
    """Classify forest type from a species code."""
    classifier = ForestTypeClassifier()
    return classifier.classify_from_species(species_code)


def map_fia_to_fvs(fia_type_code: int) -> Optional[str]:
    """Map an FIA forest type code to an FVS forest type group."""
    classifier = ForestTypeClassifier()
    return classifier.fia_to_fvs_group(fia_type_code)


def get_forest_type_group_info() -> Dict[str, Dict[str, Any]]:
    """Get information about all forest type groups."""
    return FIA_TO_FVS_MAPPING.copy()

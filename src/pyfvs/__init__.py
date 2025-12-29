"""
PyFVS: Forest Vegetation Simulator for Python

A Python implementation of forest growth models based on the
Forest Vegetation Simulator (FVS) Southern variant.

Part of the FIA Python Ecosystem:
- PyFIA: Survey/plot data analysis (https://github.com/mihiarc/pyfia)
- GridFIA: Spatial raster analysis (https://github.com/mihiarc/gridfia)
- PyFVS: Growth/yield simulation (this package)
- AskFIA: AI conversational interface (https://github.com/mihiarc/askfia)
"""

from .stand import Stand
from .tree import Tree
from .config_loader import get_config_loader, load_stand_config, load_tree_config
from .height_diameter import create_height_diameter_model, curtis_arney_height, wykoff_height
from .crown_ratio import create_crown_ratio_model, calculate_average_crown_ratio, predict_tree_crown_ratio
from .bark_ratio import create_bark_ratio_model, calculate_dib_from_dob, calculate_bark_ratio
from .crown_width import create_crown_width_model, calculate_forest_crown_width, calculate_open_crown_width, calculate_ccf_contribution, calculate_hopkins_index
from .crown_competition_factor import create_ccf_model, calculate_individual_ccf, calculate_stand_ccf, calculate_ccf_from_stand, interpret_ccf
from .volume_library import (
    VolumeCalculator, VolumeLibrary, VolumeResult, calculate_tree_volume,
    get_volume_library, get_volume_library_info, validate_volume_library
)
from .forest_type import (
    ForestTypeClassifier, ForestTypeGroup, ForestTypeResult,
    get_forest_type_effect, classify_forest_type_from_species,
    map_fia_to_fvs, get_forest_type_group_info
)
from .ecological_unit import (
    EcologicalUnitClassifier, get_ecounit_effect, select_ecounit_table,
    create_classifier as create_ecounit_classifier, get_ecounit_summary,
    MOUNTAIN_PROVINCE_ECOUNITS, LOWLAND_ECOUNITS
)
from .fia_integration import (
    FIASpeciesMapper, FIATreeRecord, FIAPlotData,
    validate_fia_input, transform_fia_trees, select_condition,
    derive_site_index, derive_forest_type, derive_ecounit,
    derive_stand_age, create_trees_from_fia
)
from .main import main

__version__ = "0.2.3"
__author__ = "PyFVS Development Team"

__all__ = [
    "Stand",
    "Tree",
    "get_config_loader",
    "load_stand_config",
    "load_tree_config",
    "create_height_diameter_model",
    "curtis_arney_height",
    "wykoff_height",
    "create_crown_ratio_model",
    "calculate_average_crown_ratio",
    "predict_tree_crown_ratio",
    "create_bark_ratio_model",
    "calculate_dib_from_dob",
    "calculate_bark_ratio",
    "create_crown_width_model",
    "calculate_forest_crown_width",
    "calculate_open_crown_width",
    "calculate_ccf_contribution",
    "calculate_hopkins_index",
    "create_ccf_model",
    "calculate_individual_ccf",
    "calculate_stand_ccf",
    "calculate_ccf_from_stand",
    "interpret_ccf",
    "VolumeCalculator",
    "VolumeLibrary",  # Alias for VolumeCalculator (backwards compatibility)
    "VolumeResult",
    "calculate_tree_volume",
    "get_volume_library",
    "get_volume_library_info",
    "validate_volume_library",
    # Forest Type Classification
    "ForestTypeClassifier",
    "ForestTypeGroup",
    "ForestTypeResult",
    "get_forest_type_effect",
    "classify_forest_type_from_species",
    "map_fia_to_fvs",
    "get_forest_type_group_info",
    # Ecological Unit Classification
    "EcologicalUnitClassifier",
    "get_ecounit_effect",
    "select_ecounit_table",
    "create_ecounit_classifier",
    "get_ecounit_summary",
    "MOUNTAIN_PROVINCE_ECOUNITS",
    "LOWLAND_ECOUNITS",
    # FIA Integration
    "FIASpeciesMapper",
    "FIATreeRecord",
    "FIAPlotData",
    "validate_fia_input",
    "transform_fia_trees",
    "select_condition",
    "derive_site_index",
    "derive_forest_type",
    "derive_ecounit",
    "derive_stand_age",
    "create_trees_from_fia",
    "main"
]

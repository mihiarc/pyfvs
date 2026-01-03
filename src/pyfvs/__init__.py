"""
PyFVS: Forest Vegetation Simulator for Python

A Python implementation of forest growth models based on the
Forest Vegetation Simulator (FVS) Southern variant.

Part of the FIA Python Ecosystem:
- PyFIA: Survey/plot data analysis (https://github.com/mihiarc/pyfia)
- GridFIA: Spatial raster analysis (https://github.com/mihiarc/gridfia)
- PyFVS: Growth/yield simulation (this package)
- AskFIA: AI conversational interface (https://github.com/mihiarc/askfia)

Quick Start:
    >>> from pyfvs import Stand
    >>> stand = Stand.initialize_planted(trees_per_acre=500, site_index=70, species='LP')
    >>> stand.grow(years=25)
    >>> print(stand.get_metrics())
"""

# =============================================================================
# Package Metadata
# =============================================================================
__version__ = "0.2.3"
__author__ = "PyFVS Development Team"

# =============================================================================
# Core Classes - Primary API
# =============================================================================
from .stand import Stand
from .tree import Tree
from .growth_parameters import GrowthParameters

# =============================================================================
# Species and Classification
# =============================================================================
from .species import SpeciesCode, get_species_code, validate_species_code

# =============================================================================
# Ecological Unit Classification
# =============================================================================
from .ecological_unit import (
    EcologicalUnitClassifier,
    get_ecounit_effect,
    select_ecounit_table,
    create_classifier as create_ecounit_classifier,
    get_ecounit_summary,
    MOUNTAIN_PROVINCE_ECOUNITS,
    LOWLAND_ECOUNITS,
)

# =============================================================================
# Forest Type Classification
# =============================================================================
from .forest_type import (
    ForestTypeClassifier,
    ForestTypeGroup,
    ForestTypeResult,
    get_forest_type_effect,
    classify_forest_type_from_species,
    map_fia_to_fvs,
    get_forest_type_group_info,
)

# =============================================================================
# Configuration Loading
# =============================================================================
from .config_loader import get_config_loader, load_stand_config, load_tree_config

# =============================================================================
# Simulation Engine
# =============================================================================
from .simulation_engine import SimulationEngine

# =============================================================================
# Growth Models - Height-Diameter
# =============================================================================
from .height_diameter import (
    create_height_diameter_model,
    curtis_arney_height,
    wykoff_height,
)

# =============================================================================
# Growth Models - Crown Ratio
# =============================================================================
from .crown_ratio import (
    create_crown_ratio_model,
    calculate_average_crown_ratio,
    predict_tree_crown_ratio,
)

# =============================================================================
# Growth Models - Bark Ratio
# =============================================================================
from .bark_ratio import (
    create_bark_ratio_model,
    calculate_dib_from_dob,
    calculate_bark_ratio,
)

# =============================================================================
# Growth Models - Crown Width
# =============================================================================
from .crown_width import (
    create_crown_width_model,
    calculate_forest_crown_width,
    calculate_open_crown_width,
    calculate_ccf_contribution,
    calculate_hopkins_index,
)

# =============================================================================
# Competition Metrics - CCF
# =============================================================================
from .crown_competition_factor import (
    create_ccf_model,
    calculate_individual_ccf,
    calculate_stand_ccf,
    calculate_ccf_from_stand,
    interpret_ccf,
)

# =============================================================================
# Volume Calculations
# =============================================================================
from .volume_library import (
    VolumeCalculator,
    VolumeLibrary,  # Alias for VolumeCalculator (backwards compatibility)
    VolumeResult,
    calculate_tree_volume,
    get_volume_library,
    get_volume_library_info,
    validate_volume_library,
)

# =============================================================================
# FIA Integration
# =============================================================================
from .fia_integration import (
    FIASpeciesMapper,
    FIATreeRecord,
    FIAPlotData,
    validate_fia_input,
    transform_fia_trees,
    select_condition,
    derive_site_index,
    derive_forest_type,
    derive_ecounit,
    derive_stand_age,
    create_trees_from_fia,
)

# =============================================================================
# Data Export
# =============================================================================
from .data_export import DataExporter

# =============================================================================
# Utilities
# =============================================================================
from .utils import normalize_code, normalize_species_code, normalize_ecounit

# =============================================================================
# Exceptions
# =============================================================================
from .exceptions import (
    FVSError,
    ConfigurationError,
    SpeciesNotFoundError,
    ParameterError,
    InvalidParameterError,
    SimulationError,
    GrowthModelError,
    StandError,
    EmptyStandError,
    DataError,
    InvalidDataError,
)

# =============================================================================
# Base Classes (for extension)
# =============================================================================
from .model_base import ParameterizedModel

# =============================================================================
# Entry Point
# =============================================================================
from .main import main

# =============================================================================
# Public API Definition
# =============================================================================
__all__ = [
    # Package Metadata
    "__version__",
    "__author__",
    # Core Classes
    "Stand",
    "Tree",
    "GrowthParameters",
    # Species and Classification
    "SpeciesCode",
    "get_species_code",
    "validate_species_code",
    # Ecological Unit Classification
    "EcologicalUnitClassifier",
    "get_ecounit_effect",
    "select_ecounit_table",
    "create_ecounit_classifier",
    "get_ecounit_summary",
    "MOUNTAIN_PROVINCE_ECOUNITS",
    "LOWLAND_ECOUNITS",
    # Forest Type Classification
    "ForestTypeClassifier",
    "ForestTypeGroup",
    "ForestTypeResult",
    "get_forest_type_effect",
    "classify_forest_type_from_species",
    "map_fia_to_fvs",
    "get_forest_type_group_info",
    # Configuration
    "get_config_loader",
    "load_stand_config",
    "load_tree_config",
    # Simulation Engine
    "SimulationEngine",
    # Height-Diameter Models
    "create_height_diameter_model",
    "curtis_arney_height",
    "wykoff_height",
    # Crown Ratio Models
    "create_crown_ratio_model",
    "calculate_average_crown_ratio",
    "predict_tree_crown_ratio",
    # Bark Ratio Models
    "create_bark_ratio_model",
    "calculate_dib_from_dob",
    "calculate_bark_ratio",
    # Crown Width Models
    "create_crown_width_model",
    "calculate_forest_crown_width",
    "calculate_open_crown_width",
    "calculate_ccf_contribution",
    "calculate_hopkins_index",
    # Competition Metrics
    "create_ccf_model",
    "calculate_individual_ccf",
    "calculate_stand_ccf",
    "calculate_ccf_from_stand",
    "interpret_ccf",
    # Volume Calculations
    "VolumeCalculator",
    "VolumeLibrary",
    "VolumeResult",
    "calculate_tree_volume",
    "get_volume_library",
    "get_volume_library_info",
    "validate_volume_library",
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
    # Data Export
    "DataExporter",
    # Utilities
    "normalize_code",
    "normalize_species_code",
    "normalize_ecounit",
    # Exceptions
    "FVSError",
    "ConfigurationError",
    "SpeciesNotFoundError",
    "ParameterError",
    "InvalidParameterError",
    "SimulationError",
    "GrowthModelError",
    "StandError",
    "EmptyStandError",
    "DataError",
    "InvalidDataError",
    # Base Classes
    "ParameterizedModel",
    # Entry Point
    "main",
]

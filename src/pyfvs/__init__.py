"""
PyFVS: Forest Vegetation Simulator for Python

A Python implementation of the USDA Forest Vegetation Simulator (FVS)
supporting 10 regional variants with taper-based volume calculations
and 500+ species configurations across the United States.

Variants: SN, LS, PN, WC, NE, CS, OP, CA, OC, WS

Quick Start:
    >>> from pyfvs import Stand
    >>> stand = Stand.initialize_planted(trees_per_acre=500, site_index=70, species='LP')
    >>> stand.grow(years=25)
    >>> print(stand.get_metrics())

Multi-variant:
    >>> stand = Stand.initialize_planted(400, 120, 'DF', variant='PN')
    >>> stand.grow(years=50)
"""

# =============================================================================
# Package Metadata
# =============================================================================
__version__ = "0.3.1"
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
from .config_loader import (
    get_config_loader,
    load_tree_config,
    set_default_variant,
    get_default_variant,
    SUPPORTED_VARIANTS,
)

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
    FVSNativeError,
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
# Native FVS Bindings (optional - requires FVS shared library)
# =============================================================================
from . import native

# =============================================================================
# Base Classes (for extension)
# =============================================================================
from .model_base import ParameterizedModel

# =============================================================================
# Variant-Specific Growth Models
# =============================================================================
from .sn_diameter_growth import (
    SNDiameterGrowthModel,
    create_sn_diameter_growth_model,
)

from .ls_diameter_growth import (
    LSDiameterGrowthModel,
    create_ls_diameter_growth_model,
    calculate_ls_diameter_growth,
)

from .pn_diameter_growth import (
    PNDiameterGrowthModel,
    create_pn_diameter_growth_model,
)

from .wc_diameter_growth import (
    WCDiameterGrowthModel,
    create_wc_diameter_growth_model,
)

from .ne_diameter_growth import (
    NEDiameterGrowthModel,
    create_ne_diameter_growth_model,
    calculate_ne_diameter_growth,
)

from .cs_diameter_growth import (
    CSDiameterGrowthModel,
    create_cs_diameter_growth_model,
    calculate_cs_diameter_growth,
)

from .ca_diameter_growth import (
    CADiameterGrowthModel,
    create_ca_diameter_growth_model,
    calculate_ca_diameter_growth,
)

from .op_diameter_growth import (
    OPDiameterGrowthModel,
    create_op_diameter_growth_model,
)

from .oc_diameter_growth import (
    OCDiameterGrowthModel,
    create_oc_diameter_growth_model,
    calculate_oc_dds,
)

from .ws_diameter_growth import (
    WSDiameterGrowthModel,
    create_ws_diameter_growth_model,
    calculate_ws_dds,
)

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
    "load_tree_config",
    "set_default_variant",
    "get_default_variant",
    "SUPPORTED_VARIANTS",
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
    "FVSNativeError",
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
    # Native FVS Bindings
    "native",
    # Base Classes
    "ParameterizedModel",
    # Variant-Specific Growth Models
    "SNDiameterGrowthModel",
    "create_sn_diameter_growth_model",
    "LSDiameterGrowthModel",
    "create_ls_diameter_growth_model",
    "calculate_ls_diameter_growth",
    "PNDiameterGrowthModel",
    "create_pn_diameter_growth_model",
    "WCDiameterGrowthModel",
    "create_wc_diameter_growth_model",
    # NE (Northeast) Variant
    "NEDiameterGrowthModel",
    "create_ne_diameter_growth_model",
    "calculate_ne_diameter_growth",
    # CS (Central States) Variant
    "CSDiameterGrowthModel",
    "create_cs_diameter_growth_model",
    "calculate_cs_diameter_growth",
    # CA (Inland California) Variant
    "CADiameterGrowthModel",
    "create_ca_diameter_growth_model",
    "calculate_ca_diameter_growth",
    # OP (ORGANON Pacific Northwest) Variant
    "OPDiameterGrowthModel",
    "create_op_diameter_growth_model",
    # OC (ORGANON Southwest Oregon) Variant
    "OCDiameterGrowthModel",
    "create_oc_diameter_growth_model",
    "calculate_oc_dds",
    # WS (Western Sierra Nevada) Variant
    "WSDiameterGrowthModel",
    "create_ws_diameter_growth_model",
    "calculate_ws_dds",
    # Entry Point
    "main",
]

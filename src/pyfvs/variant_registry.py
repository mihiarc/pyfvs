"""
Centralized variant registry for FVS-Python.

Replaces scattered if/elif variant dispatch with a single registry mapping
variant codes to their model classes, factory functions, and constants.
Adding a new variant requires only registering it here.

Growth algorithm branching (4 paths in tree.py) is intentionally NOT
centralized — those are genuinely different code paths, not data-driven.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Type, Any

from .bark_ratio import (
    BarkRatioModel, LSBarkRatioModel, NEBarkRatioModel,
    CSBarkRatioModel, PNBarkRatioModel, WSBarkRatioModel,
)
from .crown_ratio import (
    CrownRatioModel, LSCrownRatioModel, NECrownRatioModel,
    CSCrownRatioModel, PNCrownRatioModel, WSCrownRatioModel,
)
from .mortality import (
    MortalityModel, LSMortalityModel, NEMortalityModel, CSMortalityModel,
)
from .taper import ClarkTaperModel, FlewellingTaperModel


@dataclass(frozen=True)
class VariantConfig:
    """Configuration for an FVS variant.

    Holds all variant-specific model classes, constants, and factory info
    in one place so that dispatch code can do a single lookup instead of
    scattered if/elif chains.
    """
    code: str
    name: str
    cycle_length: int
    default_species: str

    # Growth algorithm category (used by tree.py to pick the right _grow method).
    # One of: 'sn', 'op', 'topographic', 'standard'
    growth_category: str

    # Model classes for factory dispatch
    bark_ratio_class: Type
    crown_ratio_class: Type
    mortality_class: Type
    taper_class: Optional[Type]

    # Diameter growth: module name and factory function name (lazy import)
    dg_module: str
    dg_factory: str

    # Mortality uses MortalityModel (SN base) for PN/WC/OP but needs SDI
    # from StandMetricsCalculator. This flag tells the factory to look up
    # variant-specific SDI maximums from StandMetricsCalculator.
    mortality_needs_sdi_lookup: bool = False

    # Default elevation for topographic variants (in variant-specific units)
    default_elevation: float = 0.0

    # Transition zone overrides (None = use species config or defaults)
    transition_xmin: Optional[float] = None
    transition_xmax: Optional[float] = None
    transition_blend: str = 'smoothstep'

    # HHTMAX dict and default for establishment height caps
    hhtmax: Dict[str, float] = field(default_factory=dict)
    hhtmax_default: float = 20.0

    # SDI maximums by species
    sdi_maximums: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# Import HHTMAX data from establishment module (to avoid duplication)
# =============================================================================
from .establishment import (
    _SN_HHTMAX, _SN_HHTMAX_DEFAULT,
    _NE_HHTMAX, _NE_HHTMAX_DEFAULT,
    _CS_HHTMAX, _CS_HHTMAX_DEFAULT,
    _LS_HHTMAX, _LS_HHTMAX_DEFAULT,
    _WS_HHTMAX, _WS_HHTMAX_DEFAULT,
)

# =============================================================================
# Import SDI maximums from stand_metrics (to avoid duplication)
# =============================================================================
from .stand_metrics import StandMetricsCalculator

_SN_SDI_MAXIMUMS: Dict[str, int] = {}  # Loaded lazily from config


def _load_sn_sdi_maximums() -> Dict[str, int]:
    """Load SN SDI maximums from config (cached)."""
    global _SN_SDI_MAXIMUMS
    if not _SN_SDI_MAXIMUMS:
        _SN_SDI_MAXIMUMS = StandMetricsCalculator._load_sn_sdi_maximums()
    return _SN_SDI_MAXIMUMS


# =============================================================================
# Registry
# =============================================================================

REGISTRY: Dict[str, VariantConfig] = {
    'SN': VariantConfig(
        code='SN',
        name='Southern',
        cycle_length=5,
        default_species='LP',
        growth_category='sn',
        bark_ratio_class=BarkRatioModel,
        crown_ratio_class=CrownRatioModel,
        mortality_class=MortalityModel,
        taper_class=ClarkTaperModel,
        dg_module='sn_diameter_growth',
        dg_factory='create_sn_diameter_growth_model',
        transition_xmin=1.0,
        transition_xmax=3.0,
        hhtmax=_SN_HHTMAX,
        hhtmax_default=_SN_HHTMAX_DEFAULT,
    ),
    'LS': VariantConfig(
        code='LS',
        name='Lake States',
        cycle_length=10,
        default_species='RN',
        growth_category='standard',
        bark_ratio_class=LSBarkRatioModel,
        crown_ratio_class=LSCrownRatioModel,
        mortality_class=LSMortalityModel,
        taper_class=ClarkTaperModel,
        dg_module='ls_diameter_growth',
        dg_factory='create_ls_diameter_growth_model',
        hhtmax=_LS_HHTMAX,
        hhtmax_default=_LS_HHTMAX_DEFAULT,
        sdi_maximums=StandMetricsCalculator.LS_SDI_MAXIMUMS,
    ),
    'PN': VariantConfig(
        code='PN',
        name='Pacific Northwest Coast',
        cycle_length=10,
        default_species='DF',
        growth_category='topographic',
        bark_ratio_class=PNBarkRatioModel,
        crown_ratio_class=PNCrownRatioModel,
        mortality_class=MortalityModel,
        mortality_needs_sdi_lookup=True,
        taper_class=FlewellingTaperModel,
        dg_module='pn_diameter_growth',
        dg_factory='create_pn_diameter_growth_model',
        default_elevation=7.0,
        hhtmax_default=20.0,
        sdi_maximums=StandMetricsCalculator.PN_SDI_MAXIMUMS,
    ),
    'WC': VariantConfig(
        code='WC',
        name='West Cascades',
        cycle_length=10,
        default_species='DF',
        growth_category='topographic',
        bark_ratio_class=PNBarkRatioModel,
        crown_ratio_class=PNCrownRatioModel,
        mortality_class=MortalityModel,
        mortality_needs_sdi_lookup=True,
        taper_class=FlewellingTaperModel,
        dg_module='wc_diameter_growth',
        dg_factory='create_wc_diameter_growth_model',
        default_elevation=35.0,
        hhtmax_default=20.0,
        sdi_maximums=StandMetricsCalculator.WC_SDI_MAXIMUMS,
    ),
    'NE': VariantConfig(
        code='NE',
        name='Northeast',
        cycle_length=10,
        default_species='RM',
        growth_category='standard',
        bark_ratio_class=NEBarkRatioModel,
        crown_ratio_class=NECrownRatioModel,
        mortality_class=NEMortalityModel,
        taper_class=ClarkTaperModel,
        dg_module='ne_diameter_growth',
        dg_factory='create_ne_diameter_growth_model',
        hhtmax=_NE_HHTMAX,
        hhtmax_default=_NE_HHTMAX_DEFAULT,
        sdi_maximums=StandMetricsCalculator.NE_SDI_MAXIMUMS,
    ),
    'CS': VariantConfig(
        code='CS',
        name='Central States',
        cycle_length=10,
        default_species='WO',
        growth_category='standard',
        bark_ratio_class=CSBarkRatioModel,
        crown_ratio_class=CSCrownRatioModel,
        mortality_class=CSMortalityModel,
        taper_class=ClarkTaperModel,
        dg_module='cs_diameter_growth',
        dg_factory='create_cs_diameter_growth_model',
        hhtmax=_CS_HHTMAX,
        hhtmax_default=_CS_HHTMAX_DEFAULT,
        sdi_maximums=StandMetricsCalculator.CS_SDI_MAXIMUMS,
    ),
    'OP': VariantConfig(
        code='OP',
        name='ORGANON Pacific Northwest',
        cycle_length=5,
        default_species='DF',
        growth_category='op',
        bark_ratio_class=PNBarkRatioModel,
        crown_ratio_class=PNCrownRatioModel,
        mortality_class=MortalityModel,
        mortality_needs_sdi_lookup=True,
        taper_class=FlewellingTaperModel,
        dg_module='op_diameter_growth',
        dg_factory='create_op_diameter_growth_model',
        hhtmax_default=20.0,
        sdi_maximums=StandMetricsCalculator.OP_SDI_MAXIMUMS,
    ),
    'CA': VariantConfig(
        code='CA',
        name='Inland California',
        cycle_length=10,
        default_species='DF',
        growth_category='topographic',
        bark_ratio_class=BarkRatioModel,
        crown_ratio_class=CrownRatioModel,
        mortality_class=MortalityModel,
        taper_class=None,
        dg_module='ca_diameter_growth',
        dg_factory='create_ca_diameter_growth_model',
        default_elevation=3000.0,
    ),
    'OC': VariantConfig(
        code='OC',
        name='Southwest Oregon',
        cycle_length=10,
        default_species='DF',
        growth_category='topographic',
        bark_ratio_class=BarkRatioModel,
        crown_ratio_class=CrownRatioModel,
        mortality_class=MortalityModel,
        taper_class=None,
        dg_module='oc_diameter_growth',
        dg_factory='create_oc_diameter_growth_model',
    ),
    'WS': VariantConfig(
        code='WS',
        name='Sierra Nevada',
        cycle_length=10,
        default_species='PP',
        growth_category='topographic',
        bark_ratio_class=WSBarkRatioModel,
        crown_ratio_class=WSCrownRatioModel,
        mortality_class=MortalityModel,
        mortality_needs_sdi_lookup=True,
        taper_class=FlewellingTaperModel,
        dg_module='ws_diameter_growth',
        dg_factory='create_ws_diameter_growth_model',
        default_elevation=45.0,
        hhtmax=_WS_HHTMAX,
        hhtmax_default=_WS_HHTMAX_DEFAULT,
        sdi_maximums=StandMetricsCalculator.WS_SDI_MAXIMUMS,
    ),
}


# =============================================================================
# Lookup functions
# =============================================================================

def get_variant_config(variant: str) -> VariantConfig:
    """Get configuration for a variant.

    Args:
        variant: FVS variant code (e.g., 'SN', 'LS')

    Returns:
        VariantConfig for the given variant.

    Raises:
        ValueError: If variant is not registered.
    """
    config = REGISTRY.get(variant)
    if config is None:
        raise ValueError(
            f"Unknown variant '{variant}'. "
            f"Registered variants: {sorted(REGISTRY.keys())}"
        )
    return config


def get_growth_category(variant: str) -> str:
    """Get the growth algorithm category for a variant.

    Returns one of: 'sn', 'op', 'topographic', 'standard'.
    """
    return get_variant_config(variant).growth_category


def create_diameter_growth_model(species: str, variant: str):
    """Create a diameter growth model using lazy import from the registry.

    This is the unified DG factory that replaces per-variant inline imports
    in tree.py. It uses string-based module/factory names from the registry
    to avoid circular imports and centralizes the dispatch.

    Args:
        species: FVS species code (e.g., 'LP', 'DF')
        variant: FVS variant code (e.g., 'SN', 'LS')

    Returns:
        A diameter growth model instance for the species/variant.
    """
    import importlib

    config = get_variant_config(variant)
    module = importlib.import_module(f'.{config.dg_module}', package='pyfvs')
    factory = getattr(module, config.dg_factory)
    return factory(species)

"""
Stand class managing a collection of trees and stand-level dynamics.

This module provides the Stand class which coordinates tree growth, mortality,
harvest operations, and output generation through composition with specialized
component classes.

Supports multiple FVS variants:
- SN (Southern): Southeastern US pine/hardwood
- LS (Lake States): Great Lakes region (MI, WI, MN)

Implements stand-level calculations including:
- Crown Competition Factor (CCF) using official equation 4.5.1
- Stand Density Index (SDI) using Reineke's equation
- Relative SDI (RELSDI) for competition modeling
- Forest type classification for growth modifiers
- Ecological unit classification for regional growth effects
- Harvest tracking (thinning, clearcut) with volume accounting
"""
import math
import random
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

from .tree import Tree
from .config_loader import load_stand_config, get_default_variant, SUPPORTED_VARIANTS
from .validation import ParameterValidator
from .logging_config import get_logger
from .utils import normalize_code

# Import component classes
from .stand_metrics import StandMetricsCalculator
from .mortality import MortalityModel, create_mortality_model
from .harvest import HarvestManager, HarvestRecord
from .competition import CompetitionCalculator
from .stand_output import StandOutputGenerator, YieldRecord

__all__ = ['Stand']

# Variant cycle lengths (from variant source code)
# SN and OP use 5-year cycles; all others use 10-year cycles
_VARIANT_CYCLE_LENGTHS = {
    'SN': 5, 'OP': 5, 'LS': 10, 'PN': 10, 'WC': 10,
    'NE': 10, 'CS': 10, 'CA': 10, 'OC': 10, 'WS': 10,
}

# =============================================================================
# Carmean Reference Age (CARAGE) for ESSUBH establishment
# =============================================================================
# Fortran ESSUBH (estab.f) computes establishment height by interpolating the
# NC-128 Chapman-Richards curve at a reference age (CARAGE), then linearly
# scaling to 5 years. Default CARAGE = 20 for most species.
_ESSUBH_DEFAULT_CARAGE = 20


def _load_small_tree_coefficients(species: str, variant: str) -> dict:
    """Load variant-specific NC-128 small tree height growth coefficients.

    Replicates Tree._load_variant_small_tree_coefficients() at module level
    so it can be called before Tree objects exist.

    Args:
        species: Species code (e.g., 'LP', 'DF')
        variant: FVS variant code (e.g., 'SN', 'LS')

    Returns:
        Coefficient dict with keys c1-c5 and bh, or empty dict if not found.
    """
    from .config_loader import load_coefficient_file
    variant_lower = variant.lower()
    filenames = [
        f'{variant_lower}_small_tree_height_growth.json',
        'sn_small_tree_height_growth.json',
    ]
    for filename in filenames:
        try:
            data = load_coefficient_file(filename, variant=variant)
            coeffs = data.get('nc128_height_growth_coefficients', {})
            if species in coeffs:
                return coeffs[species]
        except (FileNotFoundError, Exception):
            continue
    return {}


def _compute_establishment_height(species: str, site_index: float,
                                   age: float, variant: str) -> float:
    """Compute tree height from Chapman-Richards at a given age.

    Matches Fortran ESSUBH -> HTCALC(MODE1=1): place tree on the site curve
    at the establishment age, then apply HHTMAX cap from estab.f.

    Args:
        species: Species code (e.g., 'LP', 'DF')
        site_index: Site index in feet
        age: Establishment age in years
        variant: FVS variant code

    Returns:
        Height in feet at the given age on the site curve.
    """
    p = _load_small_tree_coefficients(species, variant)
    if not p:
        # Fallback: use default SN LP coefficients
        p = {'c1': 1.1421, 'c2': 1.0042, 'c3': -0.0374,
             'c4': 0.7632, 'c5': 0.0358, 'bh': 0.0}

    bh = p.get('bh', 0.0)
    raw_height = bh + p['c1'] * (site_index ** p['c2']) * \
        (1.0 - math.exp(p['c3'] * age)) ** (p['c4'] * (site_index ** p['c5']))

    # Scale factor: anchor Height(base_age) = SI for non-SN variants
    if variant == 'SN':
        height = max(0.5, raw_height)
    else:
        base_age = 50 if variant in ('LS', 'PN', 'WC', 'NE', 'CS', 'CA', 'OP') else 25
        raw_at_base = bh + p['c1'] * (site_index ** p['c2']) * \
            (1.0 - math.exp(p['c3'] * base_age)) ** (p['c4'] * (site_index ** p['c5']))
        scale = site_index / raw_at_base if raw_at_base > 0 else 1.0
        height = max(0.5, raw_height * scale)

    # Apply HHTMAX cap (estab.f line 1040: IF(HHT.GT.HHTMAX(IPNSPE)) HHT=HHTMAX(IPNSPE))
    hhtmax = _get_hhtmax(species, variant)
    if hhtmax > 0 and height > hhtmax:
        height = hhtmax

    return height


# SN HHTMAX values from blkdat.f — maximum establishment height per species.
# Species 1-11 have variant-specific values; species 12-90 all use 20.0.
_SN_HHTMAX = {
    'LB': 23.0, 'SA': 27.0, 'SP': 21.0, 'LL': 21.0, 'SB': 22.0,
    'VP': 20.0, 'SR': 24.0, 'LO': 18.0, 'TB': 18.0, 'PP': 17.0,
    'RC': 22.0,
}
_SN_HHTMAX_DEFAULT = 20.0


def _get_hhtmax(species: str, variant: str) -> float:
    """Get the maximum establishment height for a species.

    From Fortran blkdat.f HHTMAX array. Applied in estab.f after HTCALC
    to prevent unrealistically tall establishment heights.

    Args:
        species: Species code
        variant: FVS variant code

    Returns:
        Maximum establishment height in feet, or 0 if no cap applies.
    """
    if variant == 'SN':
        return _SN_HHTMAX.get(species, _SN_HHTMAX_DEFAULT)
    # Other variants: use 20.0 as default cap (conservative)
    return 20.0


def _compute_essubh_height(species: str, site_index: float,
                            variant: str, cycle_length: int) -> float:
    """Compute establishment height for 10-year eastern variants (LS/CS/NE).

    Replicates Fortran ESSUBH + regent establishment sequence:
    1. Compute Chapman-Richards height at CARAGE (default 20 years)
       with HHTMAX cap (estab.f clips HTCALC output to HHTMAX)
    2. Linear interpolation to get 5 years of establishment growth
    3. Add half-cycle regent growth (5yr increment scaled by 0.5)

    The HHTMAX cap applied to h_at_carage normalizes the intermediate
    height for species whose CR curves overshoot at CARAGE. For most
    eastern species, CR(20) > HHTMAX=20, so essubh = (20/20)*5 = 5 ft.

    Args:
        species: Species code (e.g., 'RN', 'WO', 'RM')
        site_index: Site index in feet (base age 50)
        variant: FVS variant code ('LS', 'CS', or 'NE')
        cycle_length: Variant cycle length in years (10)

    Returns:
        Establishment height in feet.
    """
    carmean_age = _ESSUBH_DEFAULT_CARAGE  # 20 years

    # Step 1: Height at CARAGE from Chapman-Richards (includes HHTMAX cap,
    # matching estab.f which clips HTCALC output before linear interp)
    h_at_carage = _compute_establishment_height(
        species, site_index, carmean_age, variant
    )

    # Step 2: ESSUBH linear interpolation to 5 years
    # Fortran: HHT = (HTHT / CARAGE) * 5.0
    essubh_height = (h_at_carage / carmean_age) * 5.0

    # Step 3: Regent growth for remaining half-cycle
    # Load CR coefficients for regent growth computation
    p = _load_small_tree_coefficients(species, variant)
    if not p:
        p = {'c1': 1.1421, 'c2': 1.0042, 'c3': -0.0374,
             'c4': 0.7632, 'c5': 0.0358, 'bh': 0.0}

    bh = p.get('bh', 0.0)

    # Scale factor: anchor Height(base_age=50) = SI
    base_age = 50
    raw_at_base = bh + p['c1'] * (site_index ** p['c2']) * \
        (1.0 - math.exp(p['c3'] * base_age)) ** (p['c4'] * (site_index ** p['c5']))
    scale = site_index / raw_at_base if raw_at_base > 0 else 1.0

    def _scaled_cr(age):
        if age <= 0:
            return (bh + 0.1) * scale
        raw = bh + p['c1'] * (site_index ** p['c2']) * \
            (1.0 - math.exp(p['c3'] * age)) ** (p['c4'] * (site_index ** p['c5']))
        return raw * scale

    # Inverse CR: find effective age from essubh_height
    max_height = bh + p['c1'] * (site_index ** p['c2'])
    exponent = p['c4'] * (site_index ** p['c5'])
    raw_essubh = essubh_height / scale if scale > 0 else essubh_height

    if raw_essubh >= max_height - 0.1:
        effective_age = 200.0
    elif raw_essubh <= bh + 0.1:
        effective_age = 0.1
    else:
        ratio = (raw_essubh - bh) / (p['c1'] * (site_index ** p['c2']))
        if ratio <= 0 or ratio >= 1.0 or exponent <= 0:
            effective_age = 0.1
        else:
            inner = ratio ** (1.0 / exponent)
            if inner >= 1.0:
                effective_age = 0.1
            else:
                effective_age = max(0.1, math.log(1.0 - inner) / p['c3'])

    # Regent: 5yr growth increment scaled by 0.5 (half-cycle)
    # Matches Fortran regent.f SCALE = FNT/REGYR for establishment
    regent_5yr = _scaled_cr(effective_age + 5.0) - _scaled_cr(effective_age)
    regent_growth = regent_5yr * 0.5

    total_height = essubh_height + regent_growth

    # Apply HHTMAX cap to final height
    hhtmax = _get_hhtmax(species, variant)
    if hhtmax > 0 and total_height > hhtmax:
        total_height = hhtmax

    return max(0.5, total_height)


def _compute_western_establishment_height(species: str, site_index: float,
                                           variant: str) -> float:
    """Compute establishment height for 10-year western variants (PN/WC).

    Uses species-specific height-age curves from htcalc.f (King, Wiley, Farr,
    etc.) to compute height at age = cycle_length (10 years).

    Args:
        species: Species code (e.g., 'DF', 'WH', 'RC')
        site_index: Site index in feet (base age varies by species)
        variant: FVS variant code ('PN' or 'WC')

    Returns:
        Establishment height in feet.
    """
    from .pn_height_age import height_at_age

    cycle_length = _VARIANT_CYCLE_LENGTHS.get(variant, 10)
    total_height = height_at_age(species, cycle_length, site_index, variant)

    # Apply HHTMAX cap
    hhtmax = _get_hhtmax(species, variant)
    if hhtmax > 0 and total_height > hhtmax:
        total_height = hhtmax

    return max(0.5, total_height)


def _estimate_dbh_from_height(height: float, species: str, variant: str) -> float:
    """Estimate DBH from height using Curtis-Arney H-D inverse.

    For sub-breast-height trees, uses the Fortran rule: DBH = 0.1 + 0.001*HT.
    For taller trees, uses the analytical inverse of the Curtis-Arney model.

    Args:
        height: Tree height in feet
        species: Species code
        variant: FVS variant code

    Returns:
        Estimated DBH in inches.
    """
    if height <= 4.5:
        return 0.1 + 0.001 * height

    from .height_diameter import create_height_diameter_model
    hd_model = create_height_diameter_model(species, variant=variant)
    dbh = hd_model.solve_dbh_from_height(target_height=height)
    return max(0.1, dbh)


class Stand:
    """Manages a collection of trees with stand-level dynamics.

    Uses composition to delegate to specialized components:
    - StandMetricsCalculator for all metrics calculations
    - MortalityModel for mortality application
    - HarvestManager for harvest operations
    - CompetitionCalculator for competition metrics
    - StandOutputGenerator for output generation

    Supports multiple FVS variants (SN, LS, etc.) through the variant parameter.

    Attributes:
        trees: List of Tree objects in the stand
        site_index: Site index in feet (base age varies by variant)
        age: Stand age in years
        species: Default species code
        variant: FVS variant code (e.g., 'SN', 'LS')
    """

    def __init__(
        self,
        trees: Optional[List[Tree]] = None,
        site_index: float = 70,
        species: str = 'LP',
        forest_type: Optional[str] = None,
        ecounit: Optional[str] = None,
        variant: Optional[str] = None
    ):
        """Initialize a stand with a list of trees.

        Args:
            trees: List of Tree objects. If None, creates an empty stand.
            site_index: Site index in feet (base age varies by variant)
            species: Default species code for stand parameters
            forest_type: FVS forest type group (e.g., "FTYLPN", "FTLOHD")
            ecounit: Ecological unit code (e.g., "M221", "232")
            variant: FVS variant code (e.g., 'SN', 'LS'). If None, uses default.
        """
        self.trees = trees if trees is not None else []

        # Set variant (default based on global setting)
        self.variant = (variant or get_default_variant()).upper()
        if self.variant not in SUPPORTED_VARIANTS:
            raise ValueError(
                f"Unsupported variant '{self.variant}'. "
                f"Supported variants: {list(SUPPORTED_VARIANTS.keys())}"
            )

        # Validate parameters
        validated_params = ParameterValidator.validate_stand_parameters(
            trees_per_acre=len(self.trees) if self.trees else 1,
            site_index=site_index,
            species_code=species
        )
        self.site_index = validated_params['site_index']

        self.age = 0
        self.species = species
        self._forest_type = forest_type
        self.ecounit = ecounit
        # Native FVS with state=0 defaults to ecounit '231DD' which maps to
        # S231T=1 (habtyp.f:135), applying S231T coefficients. Match this
        # behavior: when no ecounit is specified for SN, default to '231T'.
        if self.ecounit is None and self.variant == 'SN':
            self.ecounit = '231T'

        # Set up logging
        self.logger = get_logger(__name__)

        # Load configuration with variant
        self.params = load_stand_config(species, variant=self.variant)
        self._load_growth_params()

        # Initialize component classes (variant-aware)
        self._metrics = StandMetricsCalculator(default_species=species, variant=self.variant)
        self._mortality = create_mortality_model(default_species=species, variant=self.variant)
        self._harvest = HarvestManager()
        self._competition = CompetitionCalculator(self._metrics, species)
        self._output = StandOutputGenerator(self._metrics, self._competition, species)

    def _load_growth_params(self):
        """Load growth model parameters from configuration."""
        try:
            from .config_loader import get_config_loader
            loader = get_config_loader()
            growth_params_file = loader.cfg_dir / 'growth_model_parameters.yaml'
            self.growth_params = loader._load_config_file(growth_params_file)
        except Exception:
            self.growth_params = {
                'mortality': {
                    'early_mortality': {'age_threshold': 5, 'base_rate': 0.25},
                    'background_mortality': {
                        'base_rate': 0.05,
                        'competition_threshold': 0.55,
                        'competition_multiplier': 0.1
                    }
                },
                'initial_tree': {'dbh': {'mean': 0.5, 'std_dev': 0.1, 'minimum': 0.1}}
            }

    # =========================================================================
    # Forest Type and Ecological Unit
    # =========================================================================

    @property
    def forest_type(self) -> str:
        """Get the forest type, auto-determining if not set."""
        if self._forest_type is None:
            self._forest_type = self._auto_determine_forest_type()
        return self._forest_type

    @forest_type.setter
    def forest_type(self, value: str) -> None:
        """Set the forest type manually."""
        self._forest_type = value

    def _auto_determine_forest_type(self) -> str:
        """Auto-determine forest type from stand species composition."""
        if not self.trees:
            return "FTYLPN"

        try:
            from .forest_type import ForestTypeClassifier
            classifier = ForestTypeClassifier()
            result = classifier.classify_from_trees(self.trees, basal_area_weighted=True)
            return result.forest_type_group
        except ImportError:
            return "FTYLPN"

    def set_forest_type(self, forest_type: str) -> None:
        """Manually set the forest type."""
        valid_types = {"FTYLPN", "FTLOHD", "FTUPHD", "FTUPOK", "FTOKPN", "FTNOHD", "FTSFHP"}
        normalized = normalize_code(forest_type)
        if normalized not in valid_types:
            self.logger.warning(f"Unknown forest type: {forest_type}. Using as-is.")
        self._forest_type = normalized

    def set_ecounit(self, ecounit: str) -> None:
        """Manually set the ecological unit."""
        self.ecounit = normalize_code(ecounit)

    # =========================================================================
    # Stand Metrics - Delegated to StandMetricsCalculator
    # =========================================================================

    def calculate_ccf_official(self) -> float:
        """Calculate Crown Competition Factor using official FVS equation 4.5.1."""
        return self._metrics.calculate_ccf(self.trees)

    def calculate_qmd(self) -> float:
        """Calculate Quadratic Mean Diameter."""
        return self._metrics.calculate_qmd(self.trees)

    def _calculate_qmd_ge5(self) -> float:
        """Calculate QMD of trees >= 5" DBH (for LS variant RELDBH).

        The LS variant uses relative diameter (RELDBH = D / QMDGE5) in its
        diameter growth equation. QMDGE5 is the quadratic mean diameter of
        all trees with DBH >= 5 inches.

        Returns:
            QMD of trees >= 5" DBH, or overall QMD if no trees >= 5"
        """
        import math
        trees_ge5 = [t for t in self.trees if t.dbh >= 5.0]

        if not trees_ge5:
            # Fall back to overall QMD if no trees >= 5"
            return self.calculate_qmd()

        # QMD = sqrt(sum(D^2) / n)
        sum_dbh_sq = sum(t.dbh ** 2 for t in trees_ge5)
        return math.sqrt(sum_dbh_sq / len(trees_ge5))

    def calculate_top_height(self, n_trees: int = 40) -> float:
        """Calculate top height (average of n largest trees by DBH)."""
        return self._metrics.calculate_top_height(self.trees, n_trees)

    def calculate_basal_area(self) -> float:
        """Calculate stand basal area in sq ft/acre."""
        return self._metrics.calculate_basal_area(self.trees)

    def calculate_stand_sdi(self) -> float:
        """Calculate Stand Density Index using Reineke's equation."""
        return self._metrics.calculate_sdi(self.trees)

    def get_max_sdi(self) -> float:
        """Get maximum SDI for stand based on species composition."""
        return self._metrics.get_max_sdi(self.trees, self.species)

    def calculate_relsdi(self) -> float:
        """Calculate Relative Stand Density Index (1.0-12.0)."""
        return self._metrics.calculate_relsdi(self.trees, self.species)

    def calculate_pbal(self, target_tree: Tree) -> float:
        """Calculate Point Basal Area in Larger trees for a specific tree."""
        return self._metrics.calculate_pbal(self.trees, target_tree)

    # =========================================================================
    # Competition - Delegated to CompetitionCalculator
    # =========================================================================

    def get_forest_type_effect(self, species_code: str) -> float:
        """Get forest type growth effect for a species."""
        return self._competition.get_forest_type_effect(species_code, self.forest_type)

    def get_ecounit_effect(self, species_code: str) -> float:
        """Get ecological unit growth effect for a species."""
        if self.ecounit is None:
            return 0.0
        return self._competition.get_ecounit_effect(species_code, self.ecounit)

    def _calculate_competition_metrics(self) -> List[Dict[str, float]]:
        """Calculate competition metrics for each tree."""
        return self._competition.calculate_tree_competition_dicts(
            self.trees, self.site_index, self.forest_type, self.ecounit
        )

    # =========================================================================
    # Stand Initialization
    # =========================================================================

    @classmethod
    def initialize_planted(
        cls,
        trees_per_acre: int,
        site_index: float = 70,
        species: str = 'LP',
        ecounit: Optional[str] = None,
        forest_type: Optional[str] = None,
        variant: Optional[str] = None
    ):
        """Create a new planted stand.

        Args:
            trees_per_acre: Number of trees per acre to plant
            site_index: Site index in feet (base age varies by variant)
            species: Species code for the plantation
            ecounit: Ecological unit code (e.g., "M231", "232") for regional growth effects
            forest_type: FVS forest type group (e.g., "FTYLPN")
            variant: FVS variant code (e.g., 'SN', 'LS'). If None, uses default.

        Returns:
            Stand: New stand instance

        Examples:
            Southern variant (default):
                >>> stand = Stand.initialize_planted(500, 70, 'LP')

            Lake States variant:
                >>> stand = Stand.initialize_planted(500, 60, 'RN', variant='LS')
        """
        if trees_per_acre <= 0:
            raise ValueError(f"trees_per_acre must be positive, got {trees_per_acre}")

        validated_params = ParameterValidator.validate_stand_parameters(
            trees_per_acre=trees_per_acre,
            site_index=site_index,
            species_code=species
        )
        trees_per_acre = validated_params['trees_per_acre']
        site_index = validated_params['site_index']

        # Create temporary stand to access config and resolve variant
        temp_stand = cls([], site_index, species, variant=variant)
        actual_variant = temp_stand.variant

        cycle_length = _VARIANT_CYCLE_LENGTHS.get(actual_variant, 5)

        # Variant-dispatched establishment height computation.
        # Fortran ESSUBH + regent behavior differs by cycle length:
        # - SN/OP (5yr cycle): establishment_age = cycle_length + 2 = 7, direct CR
        # - CS/NE (10yr cycle): ESSUBH linear interp at 5yr + 5yr regent growth
        # - LS (10yr cycle): direct CR at establishment_age (NC-128 curves
        #   underestimate LS growth at young ages; Fortran HTCALC uses
        #   species-specific height-age functions not available here)
        # - PN/WC (10yr cycle): 1.0 ft seedling + 10yr CR growth
        # - CA/OC/WS: fallback to SN approach (use SN models)
        if actual_variant in ('SN', 'OP', 'CA', 'OC', 'WS', 'LS'):
            # SN/OP/LS: direct CR at establishment_age
            establishment_age = cycle_length + 2
            base_height = _compute_establishment_height(
                species, site_index, establishment_age, actual_variant
            )
        elif actual_variant in ('CS', 'NE'):
            # Eastern 10yr variants: ESSUBH linear interp + regent
            base_height = _compute_essubh_height(
                species, site_index, actual_variant, cycle_length
            )
        elif actual_variant in ('PN', 'WC'):
            # Western 10yr variants: 1.0 ft seedling + 10yr CR growth
            base_height = _compute_western_establishment_height(
                species, site_index, actual_variant
            )
            # Compute ESSUBH-equivalent intermediate height for non-equilibrium
            # DBH estimation. In Fortran, height and diameter decouple during
            # establishment: ESSUBH grows height via site curve, regent adds
            # more height growth, but diameter only grows through actual DDS
            # equations (not equilibrium H-D). Using H-D inverse at the full
            # establishment height overestimates DBH (e.g., WC DF: 3.13" vs
            # native 1.50"). The midpoint between ESSUBH height and final
            # height approximates the average growth state.
            from .pn_height_age import height_at_age as _pn_height_at_age
            pnwc_essubh_height = _pn_height_at_age(
                species, 5, site_index, actual_variant
            )
        else:
            # Unknown variant: fallback to direct CR
            establishment_age = cycle_length + 2
            base_height = _compute_establishment_height(
                species, site_index, establishment_age, actual_variant
            )

        # Get HHTMAX cap for post-variation application
        hhtmax = _get_hhtmax(species, actual_variant)

        # Create trees with lognormal height variation around the base.
        # Fortran FVS applies stochastic error (DGSCOR) to each tree's
        # diameter growth prediction, creating DBH differentiation that
        # drives PBAL (basal area in larger trees) competition effects.
        # Without variation, all trees in a monoculture have PBAL=0,
        # removing a critical growth dampening term.
        # Use deterministic seed for reproducibility.
        rng = random.Random(42)
        trees = []
        for _ in range(trees_per_acre):
            # Lognormal height variation: sigma=0.1, bounded [0.7x, 1.3x]
            # Substitutes for Fortran DGSCOR (diameter growth stochastic error)
            # which creates DBH differentiation driving PBAL competition effects.
            height_multiplier = max(0.7, min(1.3, math.exp(rng.gauss(0, 0.1))))
            tree_height = base_height * height_multiplier

            # Apply HHTMAX cap AFTER variation (fixes bug where lognormal
            # multiplier could push trees above HHTMAX)
            if hhtmax > 0 and tree_height > hhtmax:
                tree_height = hhtmax

            # DBH from H-D relationship (natural variation through height)
            if actual_variant in ('PN', 'WC'):
                # Height and diameter decouple during establishment (Fortran
                # LSKIPH). Use H-D inverse at midpoint height to approximate
                # non-equilibrium DBH. For WC DF: midpoint ~12.5ft → DBH ~1.5"
                # (matches native FVS QMD=1.50").
                midpoint_height = (pnwc_essubh_height + tree_height) / 2
                tree_dbh = _estimate_dbh_from_height(
                    midpoint_height, species, actual_variant
                )
            else:
                tree_dbh = _estimate_dbh_from_height(
                    tree_height, species, actual_variant
                )

            trees.append(Tree(
                dbh=tree_dbh,
                height=tree_height,
                species=species,
                age=cycle_length,
                variant=actual_variant
            ))

        stand = cls(trees, site_index, species, forest_type=forest_type,
                    ecounit=ecounit, variant=variant)
        stand.age = cycle_length
        return stand

    @classmethod
    def from_fia_data(
        cls,
        tree_df: 'pl.DataFrame',
        cond_df: Optional['pl.DataFrame'] = None,
        site_index: Optional[float] = None,
        condid: Optional[int] = None,
        ecounit: Optional[str] = None,
        forest_type: Optional[str] = None,
        weight_by_tpa: bool = True,
        min_dia: float = 1.0,
        max_trees: int = 1000,
        random_seed: Optional[int] = None,
        condition_strategy: str = "dominant"
    ) -> 'Stand':
        """
        Create a Stand from FIA plot data.

        This factory method converts FIA tree-level data (from pyFIA) into a
        PyFVS Stand for growth projection. It handles species code conversion,
        unit transformations, and multi-condition plot handling.

        Part of the FIA Python Ecosystem integration:
        - PyFIA: Survey/plot data analysis (source)
        - PyFVS: Growth/yield simulation (this package)

        Args:
            tree_df: Polars DataFrame with FIA TREE table columns.
                Required: SPCD, DIA, HT, TPA_UNADJ
                Optional: CR, CONDID, STATUSCD, BHAGE, TOTAGE
            cond_df: Optional COND table DataFrame for site index and forest type.
                Used columns: CONDID, SICOND, FORTYPCD, ECOSUBCD, STDAGE
            site_index: Override site index. If None, derives from SICOND in cond_df
                or uses default of 70.
            condid: Specific condition to use (for multi-condition plots).
                If None, uses condition_strategy to select.
            ecounit: Ecological unit code (e.g., "M231", "232").
                Can be derived from ECOSUBCD if available.
            forest_type: FVS forest type group (e.g., "FTYLPN").
                If None, auto-determined from FORTYPCD or species composition.
            weight_by_tpa: If True, replicate trees based on TPA_UNADJ.
                If False, use one Tree per FIA tree record.
            min_dia: Minimum DBH threshold (inches). Trees smaller are excluded.
            max_trees: Maximum trees to include (random subsample if exceeded).
            random_seed: Seed for reproducible subsampling.
            condition_strategy: Strategy for selecting condition when condid is None:
                - "dominant": Use condition with most basal area (default)
                - "first": Use condition 1
                - "forested": Use first forested condition

        Returns:
            Stand: PyFVS Stand object ready for growth simulation.

        Raises:
            ValueError: If required columns missing or no valid trees found.
            TypeError: If input is not a Polars DataFrame.

        Example:
            >>> from pyfia import FIA
            >>> from pyfvs import Stand
            >>>
            >>> # Load FIA data using pyFIA
            >>> with FIA("nc.duckdb") as db:
            ...     db.clip_by_state(37)  # North Carolina
            ...     db.clip_most_recent(eval_type="VOL")
            ...
            ...     # Get tree and condition data for a specific plot
            ...     trees = db.get_trees()
            ...     conds = db.get_conditions()
            ...
            ...     plot_cn = trees["PLT_CN"][0]  # First plot
            ...     plot_trees = trees.filter(pl.col("PLT_CN") == plot_cn)
            ...     plot_conds = conds.filter(pl.col("PLT_CN") == plot_cn)
            >>>
            >>> # Create stand for simulation
            >>> stand = Stand.from_fia_data(
            ...     tree_df=plot_trees,
            ...     cond_df=plot_conds,
            ...     ecounit="M231"  # Appalachian Mountains
            ... )
            >>>
            >>> # Project growth for 25 years
            >>> stand.grow(years=25)
            >>> print(stand.get_metrics())

        Notes:
            - FIA species codes (SPCD) are converted to FVS 2-letter codes
            - Crown ratio is converted from percentage to proportion
            - Unknown species are logged and excluded
            - Age defaults to 0 if not available (affects small-tree model only)
            - Live trees only (STATUSCD=1) are included by default
            - Multi-condition plots: use condid parameter or condition with
              most basal area is used by default

        See Also:
            - :func:`initialize_planted`: Create a planted stand
            - :mod:`pyfvs.fia_integration`: Detailed FIA integration utilities
        """
        from .fia_integration import (
            FIASpeciesMapper,
            validate_fia_input,
            transform_fia_trees,
            select_condition,
            derive_site_index,
            derive_forest_type,
            derive_ecounit,
            derive_stand_age,
            determine_dominant_species,
            create_trees_from_fia,
        )

        # Validate input DataFrame
        validate_fia_input(tree_df)

        # Handle lazy frames
        import polars as pl
        if isinstance(tree_df, pl.LazyFrame):
            tree_df = tree_df.collect()
        if cond_df is not None and isinstance(cond_df, pl.LazyFrame):
            cond_df = cond_df.collect()

        # Select condition for multi-condition plots
        if condid is not None:
            if "CONDID" in tree_df.columns:
                tree_df = tree_df.filter(pl.col("CONDID") == condid)
            selected_condid = condid
        else:
            tree_df, selected_condid = select_condition(
                tree_df, cond_df, strategy=condition_strategy
            )

        # Filter condition data to selected condition
        if cond_df is not None and "CONDID" in cond_df.columns:
            cond_df = cond_df.filter(pl.col("CONDID") == selected_condid)

        # Transform FIA tree records (filters live trees and applies min_dia)
        fia_records = transform_fia_trees(
            tree_df,
            min_dia=min_dia,
            status_filter=1  # Live trees only
        )

        if not fia_records:
            raise ValueError(
                f"No valid trees found after filtering. "
                f"Check that tree_df contains live trees (STATUSCD=1) "
                f"with DIA >= {min_dia}"
            )

        # Initialize species mapper
        mapper = FIASpeciesMapper()

        # Derive or use provided parameters
        final_site_index = site_index
        if final_site_index is None:
            final_site_index = derive_site_index(cond_df, tree_df, selected_condid)

        final_forest_type = forest_type
        if final_forest_type is None:
            final_forest_type = derive_forest_type(cond_df, tree_df, mapper, selected_condid)

        final_ecounit = ecounit
        if final_ecounit is None:
            final_ecounit = derive_ecounit(cond_df, selected_condid)

        # Get stand age if available
        stand_age = derive_stand_age(cond_df, tree_df, selected_condid)

        # Create PyFVS Tree objects
        trees = create_trees_from_fia(
            fia_records,
            mapper,
            weight_by_tpa=weight_by_tpa,
            max_trees=max_trees,
            random_seed=random_seed
        )

        if not trees:
            raise ValueError(
                "No trees could be converted. All species may be unsupported."
            )

        # Determine dominant species for stand parameters
        dominant_species = determine_dominant_species(trees)

        # Create stand
        stand = cls(
            trees=trees,
            site_index=final_site_index,
            species=dominant_species,
            forest_type=final_forest_type,
            ecounit=final_ecounit
        )

        # Set stand age if available
        if stand_age is not None:
            stand.age = stand_age

        # Log creation summary
        stand.logger.info(
            f"Created stand from FIA data: {len(trees)} trees, "
            f"SI={final_site_index}, species={dominant_species}, "
            f"forest_type={final_forest_type}, ecounit={final_ecounit}"
        )

        return stand

    # =========================================================================
    # Growth
    # =========================================================================

    def grow(self, years: int = 5):
        """Grow stand for specified number of years.

        The FVS growth model was calibrated for 5-year cycles. To ensure
        consistent results regardless of the user-specified time step, cycles
        longer than 5 years are internally subdivided into 5-year sub-cycles.
        This recalculates competition metrics at appropriate intervals,
        preventing longer cycles from accumulating excessive growth due to
        stale (low) competition values.

        Args:
            years: Number of years to grow (default 5 years to match FVS)
        """
        if years <= 0:
            return

        # Standard FVS cycle length for which the model was calibrated
        BASE_CYCLE = 5

        # For cycles > 5 years, internally subdivide to maintain consistent
        # dynamics. This ensures competition is recalculated appropriately.
        if years > BASE_CYCLE:
            remaining = years
            while remaining > 0:
                sub_cycle = min(BASE_CYCLE, remaining)
                self._grow_single_cycle(sub_cycle)
                remaining -= sub_cycle
        else:
            self._grow_single_cycle(years)

    def _grow_single_cycle(self, years: int):
        """Execute a single growth cycle (internal helper).

        This method performs the actual growth calculation for a single cycle.
        It should only be called with cycle lengths <= 5 years to ensure
        the growth model operates within its calibrated parameters.

        Args:
            years: Number of years to grow (should be <= 5 for best accuracy)
        """
        # Store initial tree count for logging
        initial_count = len(self.trees)

        # Save pre-growth QMD and TPA for mortality model (Fortran DQ0)
        # Only count staged trees (DBH >= 1.0") per Fortran morts.f DBHSTAGE
        staged_d2 = [t.dbh ** 2 for t in self.trees if t.dbh >= 1.0]
        pre_growth_tpa = len(staged_d2)
        if pre_growth_tpa > 0:
            pre_growth_qmd = math.sqrt(sum(staged_d2) / pre_growth_tpa)
        else:
            pre_growth_qmd = 0.0

        # Update stand age
        self.age += years

        if not self.trees:
            return

        # Calculate stand-level metrics needed for individual tree growth
        ba = self.calculate_basal_area()
        relsdi = self.calculate_relsdi()

        # Calculate QMD of trees >= 5" DBH (needed for LS variant RELDBH)
        qmd_ge5 = self._calculate_qmd_ge5()

        # Calculate top height (avg height of 40 largest trees per acre)
        # Used for RELHT in SN, PN, WC, CA, OC, WS variants
        top_height = self._metrics.calculate_top_height(self.trees)

        # Set top_height on each tree so RELHT can be computed in tree.grow()
        for tree in self.trees:
            tree._top_height = top_height

        # Get competition metrics for each tree
        competition_metrics = self._calculate_competition_metrics()

        # Grow each tree
        for i, tree in enumerate(self.trees):
            metrics = competition_metrics[i] if i < len(competition_metrics) else {
                'competition_factor': 0.0,
                'pbal': 0.0,
                'rank': 0.5,
                'relsdi': relsdi,
                'relht': 1.0
            }

            tree.grow(
                site_index=self.site_index,
                competition_factor=metrics.get('competition_factor', 0.0),
                ba=ba,
                pbal=metrics.get('pbal', 0.0),
                slope=0.0,
                aspect=0.0,
                rank=metrics.get('rank', 0.5),
                relsdi=metrics.get('relsdi', relsdi),
                time_step=years,
                ecounit=self.ecounit,
                forest_type=self._forest_type,  # Pass raw value; None → UPHD default in tree
                qmd_ge5=qmd_ge5  # For LS variant RELDBH calculation
            )

        # Apply mortality (pass pre-growth QMD for Fortran-style TPA targeting)
        mortality_count = self._apply_mortality(
            cycle_length=years,
            pre_growth_qmd=pre_growth_qmd,
            pre_growth_tpa=pre_growth_tpa
        )

        # Log growth summary
        self.logger.debug(
            f"Grew {years} years: TPA {initial_count}->{len(self.trees)}, "
            f"mortality={mortality_count}"
        )

    def _apply_mortality(
        self,
        cycle_length: int = 5,
        pre_growth_qmd: float = 0.0,
        pre_growth_tpa: int = 0
    ) -> int:
        """Apply mortality using the MortalityModel.

        Args:
            cycle_length: Length of projection cycle in years
            pre_growth_qmd: QMD before growth (DQ0 in Fortran)
            pre_growth_tpa: TPA before growth

        Returns:
            Number of trees that died
        """
        if len(self.trees) <= 1:
            return 0

        max_sdi = self.get_max_sdi()
        result = self._mortality.apply_mortality(
            self.trees,
            cycle_length=cycle_length,
            max_sdi=max_sdi,
            pre_growth_qmd=pre_growth_qmd,
            pre_growth_tpa=pre_growth_tpa
        )

        self.trees = result.survivors
        return result.mortality_count

    # =========================================================================
    # Metrics Summary
    # =========================================================================

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive stand metrics.

        Returns:
            Dictionary with all stand metrics including volumes
        """
        all_metrics = self._metrics.calculate_all_metrics(self.trees, self.species)

        # Add volumes and additional metrics
        if self.trees:
            volume = sum(t.get_volume('total_cubic') for t in self.trees)
            merch_volume = sum(t.get_volume('merchantable_cubic') for t in self.trees)
            board_feet = sum(t.get_volume('board_foot') for t in self.trees)
            mean_height = sum(t.height for t in self.trees) / len(self.trees)
            mean_dbh = sum(t.dbh for t in self.trees) / len(self.trees)
        else:
            volume = 0.0
            merch_volume = 0.0
            board_feet = 0.0
            mean_height = 0.0
            mean_dbh = 0.0

        return {
            'tpa': all_metrics['tpa'],
            'basal_area': all_metrics['ba'],
            'qmd': all_metrics['qmd'],
            'mean_dbh': mean_dbh,
            'top_height': all_metrics['top_height'],
            'mean_height': mean_height,
            'ccf': all_metrics['ccf'],
            'sdi': all_metrics['sdi'],
            'max_sdi': all_metrics['max_sdi'],
            'relsdi': all_metrics['relsdi'],
            'age': self.age,
            'volume': volume,
            'merchantable_volume': merch_volume,
            'board_feet': board_feet
        }

    # =========================================================================
    # Harvest Operations - Delegated to HarvestManager
    # =========================================================================

    @property
    def harvest_history(self) -> List[HarvestRecord]:
        """Get the harvest history from the harvest manager."""
        return self._harvest.harvest_history

    def thin_from_below(
        self,
        target_ba: Optional[float] = None,
        target_tpa: Optional[int] = None
    ) -> HarvestRecord:
        """Thin stand from below (remove smallest trees first)."""
        result = self._harvest.thin_from_below(
            self.trees, self.age, target_ba=target_ba, target_tpa=target_tpa
        )
        self.trees = result.remaining_trees
        return result.record

    def thin_from_above(
        self,
        target_ba: Optional[float] = None,
        target_tpa: Optional[int] = None
    ) -> HarvestRecord:
        """Thin stand from above (remove largest trees first)."""
        result = self._harvest.thin_from_above(
            self.trees, self.age, target_ba=target_ba, target_tpa=target_tpa
        )
        self.trees = result.remaining_trees
        return result.record

    def thin_by_dbh_range(
        self,
        min_dbh: float,
        max_dbh: float,
        proportion: float = 1.0
    ) -> HarvestRecord:
        """Thin trees within a DBH range."""
        result = self._harvest.thin_by_dbh_range(
            self.trees, self.age, min_dbh, max_dbh, proportion
        )
        self.trees = result.remaining_trees
        return result.record

    def clearcut(self) -> HarvestRecord:
        """Remove all trees from the stand."""
        result = self._harvest.clearcut(self.trees, self.age)
        self.trees = result.remaining_trees
        return result.record

    def selection_harvest(
        self,
        target_ba: float,
        min_dbh: float = 0.0
    ) -> HarvestRecord:
        """Perform a selection harvest targeting specific basal area."""
        result = self._harvest.selection_harvest(
            self.trees, self.age, target_ba, min_dbh
        )
        self.trees = result.remaining_trees
        return result.record

    def get_harvest_summary(self) -> Dict[str, Any]:
        """Get cumulative harvest summary."""
        return self._harvest.get_harvest_summary()

    def get_last_harvest(self) -> Optional[HarvestRecord]:
        """Get the most recent harvest record."""
        return self._harvest.get_last_harvest()

    # =========================================================================
    # Output Generation - Delegated to StandOutputGenerator
    # =========================================================================

    def get_tree_list(
        self,
        stand_id: str = "STAND001",
        include_growth: bool = True
    ) -> List[Dict[str, Any]]:
        """Generate FVS-compatible tree list output."""
        return self._output.generate_tree_list(
            self.trees, self.age, self.site_index, stand_id, include_growth
        )

    def get_tree_list_dataframe(
        self,
        stand_id: str = "STAND001",
        include_growth: bool = True
    ):
        """Get tree list as a pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas required for DataFrame output")

        tree_list = self.get_tree_list(stand_id, include_growth)
        if not tree_list:
            columns = ['StandID', 'Year', 'TreeId', 'Species', 'TPA', 'DBH',
                      'DG', 'Ht', 'HtG', 'PctCr', 'CrWidth', 'Age',
                      'BAPctile', 'PtBAL', 'TcuFt', 'McuFt', 'BdFt']
            return pd.DataFrame(columns=columns)

        return pd.DataFrame(tree_list)

    def export_tree_list(
        self,
        filepath: str,
        format: str = 'csv',
        stand_id: str = "STAND001",
        include_growth: bool = True
    ) -> str:
        """Export tree list to file."""
        tree_list = self.get_tree_list(stand_id, include_growth)
        return self._output.export_tree_list(tree_list, filepath, format, stand_id)

    def get_stand_stock_table(
        self,
        dbh_class_width: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Generate stand and stock table by diameter class."""
        return self._output.generate_stock_table(self.trees, dbh_class_width)

    def get_stand_stock_dataframe(self, dbh_class_width: float = 2.0):
        """Get stock table as pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas required for DataFrame output")

        stock_table = self.get_stand_stock_table(dbh_class_width)
        return pd.DataFrame(stock_table)

    def _get_size_class(self) -> int:
        """Determine stand size class based on QMD.

        Returns:
            Size class: 0 = Nonstocked (no trees), 1 = Seedling/sapling (QMD < 5"),
            2 = Poletimber (5-9"), 3 = Small sawtimber (9-15"),
            4 = Medium sawtimber (15-21"), 5 = Large sawtimber (21"+)
        """
        if not self.trees:
            return 0  # Nonstocked - no trees

        qmd = self.calculate_qmd()
        if qmd < 5.0:
            return 1  # Seedling/sapling (includes small trees with QMD < 1")
        elif qmd < 9.0:
            return 2  # Poletimber
        elif qmd < 15.0:
            return 3  # Small sawtimber
        elif qmd < 21.0:
            return 4  # Medium sawtimber
        else:
            return 5  # Large sawtimber

    def _get_stocking_class(self) -> int:
        """Determine stand stocking class based on SDI."""
        sdi = self.calculate_stand_sdi()
        max_sdi = self.get_max_sdi()

        if max_sdi <= 0:
            return 0

        rel_density = sdi / max_sdi

        if rel_density < 0.10:
            return 0  # Nonstocked
        elif rel_density < 0.35:
            return 1  # Poorly stocked
        elif rel_density < 0.60:
            return 2  # Moderately stocked
        elif rel_density < 0.85:
            return 3  # Fully stocked
        else:
            return 4  # Overstocked

    def _get_forest_type_code(self) -> int:
        """Get numeric forest type code from string type."""
        type_codes = {
            'FTYLPN': 1, 'FTLOHD': 2, 'FTUPHD': 3, 'FTUPOK': 4,
            'FTOKPN': 5, 'FTNOHD': 6, 'FTSFHP': 7
        }
        return type_codes.get(self.forest_type, 0)

    def get_yield_record(
        self,
        stand_id: str = "STAND001",
        year: int = 0,
        prev_volume: float = 0.0,
        mortality_volume: float = 0.0,
        period_length: int = 5,
        harvest_record: Optional[HarvestRecord] = None
    ) -> YieldRecord:
        """Get current stand state as FVS_Summary compatible yield record."""
        metrics = self.get_metrics()

        # Calculate accretion and mortality rate
        if prev_volume > 0 and period_length > 0:
            gross_growth = metrics['volume'] - prev_volume + mortality_volume
            accretion = max(0, gross_growth) / period_length
            mort_rate = mortality_volume / period_length
        else:
            accretion = 0.0
            mort_rate = 0.0

        mai = metrics['volume'] / self.age if self.age > 0 else 0.0

        # Extract harvest info
        r_tpa = 0
        r_tcuft = 0.0
        r_mcuft = 0.0
        r_bdft = 0.0

        if harvest_record is not None:
            r_tpa = harvest_record.trees_removed
            r_tcuft = harvest_record.volume_removed
            r_mcuft = harvest_record.merchantable_volume_removed
            r_bdft = harvest_record.board_feet_removed

        return YieldRecord(
            StandID=stand_id,
            Year=year if year > 0 else self.age,
            Age=self.age,
            TPA=metrics['tpa'],
            BA=metrics['basal_area'],
            SDI=metrics['sdi'],
            CCF=metrics['ccf'],
            TopHt=metrics['top_height'],
            QMD=metrics['qmd'],
            TCuFt=metrics['volume'],
            MCuFt=metrics['merchantable_volume'],
            BdFt=metrics['board_feet'],
            RTpa=r_tpa,
            RTCuFt=r_tcuft,
            RMCuFt=r_mcuft,
            RBdFt=r_bdft,
            AThinBA=metrics['basal_area'],
            AThinSDI=metrics['sdi'],
            AThinCCF=metrics['ccf'],
            AThinTopHt=metrics['top_height'],
            AThinQMD=metrics['qmd'],
            PrdLen=period_length,
            Acc=accretion,
            Mort=mort_rate,
            MAI=mai,
            ForTyp=self._get_forest_type_code(),
            SizeCls=self._get_size_class(),
            StkCls=self._get_stocking_class()
        )

    def generate_yield_table(
        self,
        years: int = 50,
        period_length: int = 5,
        stand_id: str = "STAND001",
        start_year: int = 2025
    ) -> List[YieldRecord]:
        """Generate FVS_Summary compatible yield table."""
        import copy

        # Create working copy to preserve original stand state
        working_stand = copy.deepcopy(self)
        yield_records = []

        # Collect initial metrics
        prev_volume = working_stand.get_metrics()['volume']

        # Record initial state
        initial_record = working_stand.get_yield_record(
            stand_id=stand_id,
            year=start_year,
            prev_volume=0.0,
            mortality_volume=0.0,
            period_length=0
        )
        yield_records.append(initial_record)

        # Track harvest history length
        prev_harvest_count = len(working_stand.harvest_history)

        # Simulate growth
        current_year = start_year
        for period in range(period_length, years + 1, period_length):
            # Store pre-growth metrics
            pre_tpa = len(working_stand.trees)
            pre_volume = working_stand.get_metrics()['volume']

            # Grow stand
            working_stand.grow(years=period_length)
            current_year += period_length

            # Calculate mortality
            post_tpa = len(working_stand.trees)
            trees_died = pre_tpa - post_tpa

            if trees_died > 0 and pre_tpa > 0:
                avg_tree_vol = pre_volume / pre_tpa
                mortality_volume = trees_died * avg_tree_vol * 0.8
            else:
                mortality_volume = 0.0

            # Check for new harvests
            harvest_record = None
            if len(working_stand.harvest_history) > prev_harvest_count:
                harvest_record = working_stand.harvest_history[-1]
                prev_harvest_count = len(working_stand.harvest_history)

            # Create yield record
            record = working_stand.get_yield_record(
                stand_id=stand_id,
                year=current_year,
                prev_volume=prev_volume,
                mortality_volume=mortality_volume,
                period_length=period_length,
                harvest_record=harvest_record
            )
            yield_records.append(record)

            prev_volume = working_stand.get_metrics()['volume']

        return yield_records

    def get_yield_table_dataframe(
        self,
        years: int = 50,
        period_length: int = 5,
        stand_id: str = "STAND001",
        start_year: int = 2025
    ):
        """Generate yield table as pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas required for DataFrame output")

        yield_records = self.generate_yield_table(
            years=years,
            period_length=period_length,
            stand_id=stand_id,
            start_year=start_year
        )

        return pd.DataFrame([r.to_dict() for r in yield_records])

    def export_yield_table(
        self,
        filepath: str,
        format: str = 'csv',
        years: int = 50,
        period_length: int = 5,
        stand_id: str = "STAND001",
        start_year: int = 2025
    ) -> str:
        """Export yield table to file."""
        yield_records = self.generate_yield_table(
            years=years,
            period_length=period_length,
            stand_id=stand_id,
            start_year=start_year
        )

        return self._output.export_yield_table(yield_records, filepath, format, stand_id)

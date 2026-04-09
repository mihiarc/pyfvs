"""
Tree class representing an individual tree.
Implements both small-tree and large-tree growth models.
"""
import math
from typing import Dict, Any, Optional, Union

from .validation import ParameterValidator
from .logging_config import get_logger, log_model_transition
from .growth_parameters import GrowthParameters
from .exceptions import FVSError

__all__ = ['Tree']


class Tree:
    def __init__(self, dbh, height, species="LP", age=0, crown_ratio=0.85, variant=None):
        """Initialize a tree with basic measurements.

        Args:
            dbh: Diameter at breast height (inches)
            height: Total height (feet)
            species: Species code (e.g., "LP" for loblolly pine, "RN" for red pine)
            age: Tree age in years
            crown_ratio: Initial crown ratio (proportion of tree height with live crown)
            variant: FVS variant code (e.g., 'SN', 'LS'). If None, uses current default.
        """
        # Validate parameters
        validated = ParameterValidator.validate_tree_parameters(
            dbh, height, age, crown_ratio, species
        )

        self.dbh = validated['dbh']
        self.height = validated['height']
        self.species = species
        self.age = validated['age']
        self.crown_ratio = validated['crown_ratio']

        # Initialize optional ecounit, forest_type, managed flag (set during grow())
        self._ecounit = None
        self._forest_type = None
        self._managed = False  # Only apply plant effect when MANAGD equivalent is set

        # Set up logging
        self.logger = get_logger(__name__)

        # Check height-DBH relationship (disabled warning for small seedlings)
        if self.height > 4.5 and not ParameterValidator.check_height_dbh_relationship(self.dbh, self.height):
            self.logger.warning(
                f"Unusual height-DBH relationship: DBH={self.dbh}, Height={self.height}"
            )

        # Load configuration with variant
        self._load_config(variant)
    
    def _load_config(self, variant: str = None):
        """Load configuration using the new config loader.

        Args:
            variant: FVS variant code (e.g., 'SN', 'LS'). If None, uses current default.
        """
        from .config_loader import get_config_loader

        loader = get_config_loader(variant)

        # Load species-specific parameters
        self.species_params = loader.load_species_config(self.species)

        # Store the variant for use in growth equations
        self._variant = self.species_params.get('_variant', loader.variant)

        # Load functional forms and site index parameters
        self.functional_forms = loader.functional_forms
        self.site_index_params = loader.site_index_params

        # Load growth model parameters
        try:
            growth_params_file = loader.cfg_dir / 'growth_model_parameters.yaml'
            self.growth_params = loader._load_config_file(growth_params_file)
        except (FVSError, KeyError) as exc:
            self.logger.warning(
                "Failed to load growth_model_parameters.yaml: %s; using defaults", exc,
            )
            self.growth_params = {
                'growth_transitions': {'small_to_large_tree': {'xmin': 3.0, 'xmax': 3.0}},
                'small_tree_growth': {'default': {
                    'c1': 1.1421, 'c2': 1.0042, 'c3': -0.0374, 'c4': 0.7632, 'c5': 0.0358
                }}
            }
    
    def grow(
        self,
        params_or_site_index: Union[GrowthParameters, float] = None,
        competition_factor: float = None,
        rank: float = 0.5,
        relsdi: float = 5.0,
        ba: float = 100,
        pbal: float = 50,
        slope: float = 0.05,
        aspect: float = 0,
        time_step: int = 5,
        ecounit: str = None,
        forest_type: str = None,
        qmd_ge5: float = None,
        *,
        site_index: float = None,
        rng=None,
        top_height: float = None,
        avg_height: float = None
    ) -> None:
        """Grow the tree for the specified number of years.

        This method accepts either a GrowthParameters dataclass or individual
        parameters for backwards compatibility.

        Args:
            params_or_site_index: Either a GrowthParameters object containing all
                growth parameters, or the site_index value (for backwards compatibility).
            competition_factor: Competition factor (0-1). Required if using individual
                parameters.
            rank: Tree's rank in diameter distribution (0-1). Default: 0.5.
            relsdi: Relative stand density index (0-12). Default: 5.0.
            ba: Stand basal area (sq ft/acre). Default: 100.
            pbal: Plot basal area in larger trees (sq ft/acre). Default: 50.
            slope: Ground slope (proportion). Default: 0.05.
            aspect: Aspect in radians. Default: 0.
            time_step: Number of years to grow the tree. Default: 5.
            ecounit: Ecological unit code (e.g., "232", "M231") - passed from Stand.
            forest_type: Forest type group (e.g., "FTYLPN") - passed from Stand.
            qmd_ge5: QMD of trees >= 5" DBH (for LS variant RELDBH calculation).
            site_index: Alternative keyword argument for site_index (for clarity when
                not using GrowthParameters).

        Examples:
            Using GrowthParameters (recommended):
                >>> params = GrowthParameters(site_index=70, ba=100, ecounit='M231')
                >>> tree.grow(params)

            Using individual parameters (backwards compatible):
                >>> tree.grow(site_index=70, competition_factor=0.3, ba=100)

            Legacy positional style (still supported):
                >>> tree.grow(70, 0.3, ba=100)
        """
        # Handle the two calling conventions:
        # 1. GrowthParameters object as first argument
        # 2. Individual parameters (site_index as first positional or keyword arg)
        if isinstance(params_or_site_index, GrowthParameters):
            # Extract all parameters from the dataclass
            params = params_or_site_index
            site_index = params.site_index
            competition_factor = params.competition_factor
            rank = params.rank
            relsdi = params.relsdi
            ba = params.ba
            pbal = params.pbal
            slope = params.slope
            aspect = params.aspect
            time_step = params.time_step
            ecounit = params.ecounit
            forest_type = params.forest_type
            rng = params.rng if rng is None else rng
            top_height = params.top_height if top_height is None else top_height
            avg_height = params.avg_height if avg_height is None else avg_height
        else:
            # Individual parameters - handle both positional and keyword site_index
            if params_or_site_index is not None:
                site_index = params_or_site_index
            elif site_index is None:
                raise ValueError(
                    "site_index is required. Provide either a GrowthParameters object "
                    "or site_index as the first positional argument or keyword argument."
                )
            # competition_factor defaults to 0.0 if not provided
            if competition_factor is None:
                competition_factor = 0.0

        # Store ecounit and forest_type for use in growth methods
        self._ecounit = ecounit
        self._forest_type = forest_type
        # Validate growth parameters
        validated = ParameterValidator.validate_growth_parameters(
            site_index, competition_factor, ba, pbal, rank, relsdi,
            slope, aspect, time_step, self.species
        )
        
        # Use validated parameters
        site_index = validated['site_index']
        competition_factor = validated['competition_factor']
        ba = validated['ba']
        pbal = validated['pbal']
        rank = validated['rank']
        relsdi = validated['relsdi']
        slope = validated['slope']
        aspect = validated['aspect']
        time_step = validated['time_step']
        
        # Store initial values before any changes
        initial_age = self.age
        initial_dbh = self.dbh
        initial_height = self.height
        
        # Get transition parameters from config
        variant = self._variant

        # PN/WC: species-specific transition zones from regent.f XMIN/XMAX
        if variant in ('PN', 'WC'):
            from .pn_small_tree_growth import get_smhgdg_coefficients
            smhgdg = get_smhgdg_coefficients(self.species)
            if smhgdg:
                xmin = smhgdg['xmin']
                xmax = smhgdg['xmax']
            else:
                xmin = 2.0
                xmax = 4.0
        else:
            from .variant_registry import get_variant_config
            vc = get_variant_config(variant)
            if vc.transition_xmin is not None:
                xmin = vc.transition_xmin
                xmax = vc.transition_xmax
            else:
                transition_params = self.growth_params['growth_transitions']['small_to_large_tree']
                xmin = transition_params['xmin']
                xmax = transition_params['xmax']

        # Default avg_height to 0.0 for PN/WC SMHGDG if not provided
        if avg_height is None:
            avg_height = 0.0

        # Calculate weight for blending growth models based on initial DBH
        if initial_dbh < xmin:
            weight = 0.0
        elif initial_dbh >= xmax:
            weight = 1.0
        elif xmin >= xmax:
            weight = 1.0
        elif variant in ('PN', 'WC'):
            # PN/WC: linear blend matching Fortran regent.f
            # XWT = (D - XMN) / (XMX - XMN)
            weight = (initial_dbh - xmin) / (xmax - xmin)
        else:
            # Other variants: smoothstep function 3t^2 - 2t^3
            t = (initial_dbh - xmin) / (xmax - xmin)
            weight = t * t * (3.0 - 2.0 * t)
            
        # Log model transition if crossing threshold
        if initial_dbh < xmin and self.dbh >= xmin:
            log_model_transition(self.logger, f"{self.species}_{id(self)}", 
                                "small_tree", "blended", self.dbh)
        elif initial_dbh < xmax and self.dbh >= xmax:
            log_model_transition(self.logger, f"{self.species}_{id(self)}", 
                                "blended", "large_tree", self.dbh)
        
        # Temporarily increment age for growth calculations
        self.age = initial_age + time_step

        if weight == 0.0:
            # Pure small-tree model (DBH < xmin)
            self._grow_small_tree(site_index, competition_factor, time_step, ba=ba, pbal=pbal, avg_height=avg_height)
        elif weight == 1.0:
            # Pure large-tree model (DBH > xmax)
            self._grow_large_tree(site_index, competition_factor, ba, pbal, slope, aspect, time_step, qmd_ge5, rng=rng, top_height=top_height)
        else:
            # Transition zone: blend both models
            self._grow_small_tree(site_index, competition_factor, time_step, ba=ba, pbal=pbal, avg_height=avg_height)
            small_dbh = self.dbh
            small_height = self.height

            # Reset to initial state for large tree model
            self.dbh = initial_dbh
            self.height = initial_height

            self._grow_large_tree(site_index, competition_factor, ba, pbal, slope, aspect, time_step, qmd_ge5, rng=rng, top_height=top_height)
            large_dbh = self.dbh
            large_height = self.height

            # Blend results
            self.dbh = (1 - weight) * small_dbh + weight * large_dbh
            self.height = (1 - weight) * small_height + weight * large_height

        # Ensure age is properly set after growth
        self.age = initial_age + time_step
        
        # Update crown ratio using Weibull model (pass time_step for proper scaling)
        self._update_crown_ratio_weibull(rank, relsdi, competition_factor, time_step)
    
    def _grow_small_tree(self, site_index, competition_factor, time_step=5, ba=0.0, pbal=0.0, avg_height=0.0):
        """Implement small tree height growth model.

        For PN/WC variants, uses species-specific height-age curves from
        htcalc.f (King, Wiley, Farr, etc.). For all other variants, uses
        the Chapman-Richards NC-128 functional form.

        Args:
            site_index: Site index in feet (base age varies by variant)
            competition_factor: Competition factor (0-1)
            time_step: Number of years to grow (any positive integer)
            ba: Stand basal area (sq ft/acre), for PN/WC SMHGDG
            pbal: Basal area in larger trees (sq ft/acre), for PN/WC SMHGDG
            avg_height: Average stand height (feet), for PN/WC SMHGDG
        """
        variant = self._variant

        # PN/WC: use species-specific height-age curves from htcalc.f
        if variant in ('PN', 'WC'):
            self._grow_small_tree_pnwc(site_index, competition_factor, time_step, ba=ba, pbal=pbal, avg_height=avg_height)
            return

        # OC: 5-group SMHTGF model from oc/smhtgf.f
        if variant == 'OC':
            self._grow_small_tree_oc(site_index, time_step, bal=pbal, avg_height=avg_height)
            return

        # Get species-specific parameters - prefer variant-specific JSON file
        # which has Fortran LTBHEC-matched coefficients, then fall back to
        # species config YAML (which may have older publication coefficients).
        p = self._load_variant_small_tree_coefficients(variant)
        if not p:
            p = self.species_params.get('small_tree_height_growth', {})
        if not p:
            # Fallback to growth_params if species config doesn't have it
            small_tree_params = self.growth_params.get('small_tree_growth', {})
            if self.species in small_tree_params:
                p = small_tree_params[self.species]
            else:
                p = small_tree_params.get('default', {
                    'c1': 1.1421,
                    'c2': 1.0042,
                    'c3': -0.0374,
                    'c4': 0.7632,
                    'c5': 0.0358,
                    'bh': 0.0
                })
        
        # Chapman-Richards predicts cumulative height at age t
        # Height(t) = c1 * SI^c2 * (1 - exp(c3 * t))^(c4 * SI^c5)
        #
        # The NC-128 coefficients may have been calibrated with a different site index
        # base age. To ensure Height(base_age=25) = SI, we compute a scaling factor.

        # Current age (before growth) - age was already incremented in grow()
        current_age = self.age - time_step

        # Note: Stand.initialize_planted() places trees on the Chapman-Richards
        # site curve at establishment_age = cycle_length + 1 (matching Fortran
        # ESSUBH -> HTCALC). Trees start at age=cycle_length with ~20 ft height
        # for SN LP SI=70. The effective-age logic below correctly continues
        # growth from that anchor point on the site curve.

        # Site index base age varies by variant
        # SN (Southern): base age 25
        # LS/PN/WC/NE/CS/CA/OP: base age 50
        if variant in ('LS', 'PN', 'WC', 'NE', 'CS', 'CA', 'OP'):
            base_age = 50
        else:
            base_age = 25

        # Breast height offset (BH) from NC-128 curves — some curves add 4.5 ft
        bh = p.get('bh', 0.0)

        def _raw_chapman_richards(age):
            """Calculate unscaled Chapman-Richards height."""
            if age <= 0:
                return bh + 0.1
            return (
                bh + p['c1'] * (site_index ** p['c2']) *
                (1.0 - math.exp(p['c3'] * age)) **
                (p['c4'] * (site_index ** p['c5']))
            )

        # Scale factor anchors Height(base_age) = SI for variants whose
        # NC-128 coefficients use a different base age than the variant's SI.
        # SN: Fortran htcalc.f uses raw LTBHEC coefficients with NO scale
        # factor — the SI parameter directly drives the curve magnitude.
        # LS/NE/CS: Coefficients from LTBHEC(6,127) need SI anchoring.
        if variant == 'SN':
            scale_factor = 1.0
        else:
            raw_height_at_base = _raw_chapman_richards(base_age)
            if raw_height_at_base > 0:
                scale_factor = site_index / raw_height_at_base
            else:
                scale_factor = 1.0

        def _scaled_height(age):
            """Calculate scaled Chapman-Richards height at given age."""
            return _raw_chapman_richards(age) * scale_factor

        # FINDAG: Derive effective age from current height via inverse Chapman-Richards
        # Matches Fortran regent.f:206-208: CALL HTCALC(MODE0=0, ISPC, AGET, H, ...)
        # This anchors growth rate to the tree's actual size, not calendar age.
        max_height = bh + p['c1'] * (site_index ** p['c2'])
        exponent = p['c4'] * (site_index ** p['c5'])

        def _effective_age_from_height(height):
            """Inverse Chapman-Richards: solve for age given height."""
            # Correct for scale factor to get raw height
            raw_height = height / scale_factor if scale_factor > 0 else height
            if raw_height >= max_height - 0.1:
                return 200.0  # At asymptote, return large age
            if raw_height <= bh + 0.1:
                return 0.1  # Minimum effective age for very small trees
            ratio = (raw_height - bh) / (p['c1'] * (site_index ** p['c2']))
            if ratio <= 0 or ratio >= 1.0:
                return 0.1
            if exponent <= 0:
                return 0.1
            inner = ratio ** (1.0 / exponent)
            if inner >= 1.0:
                return 0.1
            age = math.log(1.0 - inner) / p['c3']
            return max(0.1, age)

        # Use effective age (from current height) instead of calendar age
        effective_age = _effective_age_from_height(self.height)
        future_effective_age = effective_age + time_step

        # Height growth = CR(effective_age + time_step) - CR(effective_age)
        current_height_on_curve = _scaled_height(effective_age)
        future_height_on_curve = _scaled_height(future_effective_age)
        height_growth = future_height_on_curve - current_height_on_curve

        # NOTE: No ecounit modifier is applied to height growth. Site Index
        # already incorporates regional productivity through the Chapman-Richards
        # curve. However, the ecounit effect IS applied to DIAMETER growth below.

        # Apply competition modifier (Fortran regent.f:233 applies CON*SCALE*HGADJ*XRHGRO)
        # CON includes calibration; we use competition_factor as a proxy
        max_reduction = self.growth_params.get('competition_effects', {}).get(
            'small_tree_competition', {}).get('max_reduction', 0.2)
        competition_modifier = 1.0 - (max_reduction * competition_factor)

        # Scale height growth to match cycle length (Fortran: SCALE = FNT/REGYR)
        # The Chapman-Richards 5-year increment is computed via htcalc, then
        # scaled by FNT/5 in regent.f line 233. Our effective-age method
        # directly computes the increment for the full time_step, so no
        # additional scaling is needed.
        actual_growth = height_growth * competition_modifier

        # Update height with bounds checking
        # Trees can exist below breast height (4.5 ft) during establishment
        # Minimum 0.5 ft prevents degenerate zero-height trees
        self.height = max(0.5, self.height + actual_growth)

        # Calculate new DBH from height using height-diameter relationship.
        # Ecounit effects are NOT applied to small-tree growth, matching
        # Fortran DGBND which uses pure height + H-D inverse. Ecounit
        # effects only apply in the large-tree DDS model (DGF).
        self._update_dbh_from_height()

    def _load_variant_small_tree_coefficients(self, variant: str) -> dict:
        """Load variant-specific NC-128 small tree height growth coefficients.

        Looks for {variant}_small_tree_height_growth.json in the variant's
        config directory (via load_coefficient_file). Falls back to the SN
        file if variant-specific file not found.

        Args:
            variant: FVS variant code (e.g., 'LS', 'CS', 'NE', 'SN')

        Returns:
            Coefficient dict with keys c1-c5 and bh, or empty dict if not found.
        """
        from .config_loader import load_coefficient_file
        variant_lower = variant.lower()
        # Try variant-specific file first
        filenames = [
            f'{variant_lower}_small_tree_height_growth.json',
            'sn_small_tree_height_growth.json',
        ]
        for filename in filenames:
            try:
                data = load_coefficient_file(filename, variant=variant)
                coeffs = data.get('nc128_height_growth_coefficients', {})
                if self.species in coeffs:
                    return coeffs[self.species]
            except FVSError:
                continue
        return {}

    def _grow_small_tree_pnwc(self, site_index, competition_factor, time_step=5, ba=0.0, pbal=0.0, avg_height=0.0):
        """Small-tree growth for PN/WC using SMHGDG logistic model.

        Implements the Gould & Harrington (2011) model from Fortran smhgdg.f
        which predicts both height and diameter growth simultaneously with
        competition effects. This replaces the earlier htcalc.f height-age
        approach which gave incorrect diameter estimates via H-D inverse.

        SMHGDG returns 5-year growth increments. For time_step > 5, we call
        the model multiple times with updated state between calls (matching
        Fortran regent.f behavior which calls SMHGDG once per 5-year sub-step).

        The first-cycle LESTB scaling (SCALE=0.5) is already built into the
        establishment function (compute_western_establishment_height) so that
        initialization matches native FVS cycle 1 output. No special scaling
        is needed during grow().

        Args:
            site_index: Site index in feet (base age varies by species)
            competition_factor: Competition factor (0-1)
            time_step: Number of years to grow
            ba: Stand basal area (sq ft/acre)
            pbal: Basal area in larger trees (sq ft/acre)
            avg_height: Average stand height (feet)
        """
        from .pn_small_tree_growth import calculate_small_tree_growth

        variant = self._variant

        # Call SMHGDG in 5-year sub-steps (Fortran base period is 5 years)
        n_steps = max(1, time_step // 5)
        for _ in range(n_steps):
            hg5, dg5 = calculate_small_tree_growth(
                species=self.species,
                height=self.height,
                dbh=self.dbh,
                site_index=site_index,
                variant=variant,
                ptba=ba,
                ptbal=pbal,
                crown_ratio=self.crown_ratio,
                avg_height=avg_height
            )
            self.height = max(0.5, self.height + hg5)
            self.dbh = max(0.0, self.dbh + dg5)

    def _grow_small_tree_oc(
        self,
        site_index: float,
        time_step: float = 5.0,
        bal: float = 0.0,
        avg_height: float = 0.0,
    ) -> None:
        """Small-tree height growth for OC using SMHTGF (oc/smhtgf.f).

        Five species groups (pines, firs+DF, black oak, tanoak, redwood) each
        with their own functional form. Computes a 5-year height increment,
        applies it, then re-derives DBH from the new height via the height-
        diameter inverse (matching Fortran small-tree behavior where DBH is
        recomputed from height for trees below the small/large transition).

        Args:
            site_index: Site index (feet, base age 50, R6).
            time_step: Cycle length in years.
            bal: Basal area in larger trees (sq ft/acre).
            avg_height: Average stand height (feet) for relative-height calc.
        """
        from .oc_height_growth import calculate_oc_small_tree_height_growth

        relht = (self.height / avg_height) if avg_height > 0 else 1.0

        htgr = calculate_oc_small_tree_height_growth(
            species_code=self.species,
            height=self.height,
            crown_ratio=self.crown_ratio,
            site_index=site_index,
            bal=bal,
            relative_height=relht,
            time_step=time_step,
        )

        self.height = max(0.5, self.height + htgr)
        self._update_dbh_from_height()

    def _grow_large_tree(self, site_index, competition_factor, ba, pbal, slope, aspect, time_step=5, qmd_ge5=None, rng=None, top_height=None):
        """Implement large tree diameter growth model using variant-specific equations.

        Dispatches to the appropriate growth method based on the tree's variant:
        - SN (Southern): Uses ln(DDS) formulation with ecounit/forest type effects
        - OP (ORGANON PNW): Predicts diameter growth directly (not DDS)
        - Topographic variants (PN, WC, CA, OC, WS): ln(DDS) with elevation/slope/aspect
        - Standard variants (LS, NE, CS): DDS without topographic effects

        Args:
            site_index: Site index in feet (base age varies by variant)
            competition_factor: Competition factor (0-1)
            ba: Stand basal area (sq ft/acre)
            pbal: Plot basal area in larger trees (sq ft/acre)
            slope: Ground slope as tangent (rise/run)
            aspect: Aspect in radians
            time_step: Number of years to grow (default: 5)
            qmd_ge5: QMD of trees >= 5" DBH (for LS/CS RELDBH calculation)
            rng: Random number generator for stochastic mode (None = deterministic)
            top_height: Stand top height in feet (for RELHT calculation)
        """
        variant = self._variant

        # SN variant (default) - special handling for ecounit/forest type effects
        if variant == 'SN':
            self._grow_large_tree_sn(site_index, competition_factor, ba, pbal, slope, aspect, time_step, rng=rng, top_height=top_height)

        # OP variant - predicts diameter growth directly (not DDS)
        elif variant == 'OP':
            self._grow_large_tree_op(site_index, ba, pbal, time_step)

        # Topographic variants - use elevation/slope/aspect effects
        elif variant in ('PN', 'WC', 'CA', 'OC', 'WS'):
            self._grow_large_tree_topographic(variant, site_index, ba, pbal, slope, aspect, time_step, rng=rng, top_height=top_height)

        # Standard variants - DDS without topographic effects
        elif variant in ('LS', 'NE', 'CS'):
            self._grow_large_tree_standard(variant, site_index, ba, pbal, time_step, qmd_ge5, rng=rng, top_height=top_height)

        else:
            # Unknown variant - fall back to SN
            self._grow_large_tree_sn(site_index, competition_factor, ba, pbal, slope, aspect, time_step, rng=rng, top_height=top_height)

    def _grow_large_tree_standard(
        self,
        variant: str,
        site_index: float,
        ba: float,
        pbal: float,
        time_step: float = 10.0,
        qmd_ge5: float = None,
        rng=None,
        top_height: float = None
    ) -> None:
        """Generic large tree growth for non-topographic variants (LS, NE, CS).

        These variants use DDS-based equations without topographic effects.
        All use bark ratio conversion and 10-year base cycle.

        Args:
            variant: FVS variant code ('LS', 'NE', 'CS')
            site_index: Site index (base age 50) in feet
            ba: Stand basal area (sq ft/acre)
            pbal: Basal area in larger trees (sq ft/acre)
            time_step: Number of years to grow (default: 10)
            qmd_ge5: QMD of trees >= 5" DBH (for RELDBH calculation in LS/CS)
        """
        from .bark_ratio import create_bark_ratio_model

        # Get bark ratio for diameter conversion (variant-aware)
        bark_model = create_bark_ratio_model(self.species, variant=variant)
        bark_ratio = bark_model.calculate_bark_ratio(self.dbh)

        # Get diameter growth model from registry (unified factory)
        from .variant_registry import create_diameter_growth_model
        dg_model = create_diameter_growth_model(self.species, variant)

        # Each variant's DG model has a slightly different call signature
        if variant == 'NE':
            diameter_increment = dg_model.calculate_diameter_growth(
                dbh=self.dbh,
                crown_ratio=self.crown_ratio,
                site_index=site_index,
                ba=ba,
                bal=pbal,
                bark_ratio=bark_ratio,
                time_step=time_step
            )
        else:  # LS, CS
            diameter_increment = dg_model.calculate_diameter_growth(
                dbh=self.dbh,
                crown_ratio=self.crown_ratio,
                site_index=site_index,
                ba=ba,
                bal=pbal,
                bark_ratio=bark_ratio,
                qmd_ge5=qmd_ge5,
                time_step=time_step,
                rng=rng
            )

        # Apply increment to DBH (ensure non-negative)
        self.dbh = max(self.dbh, self.dbh + diameter_increment)

        # Update height using potential height growth model (Section 4.7.2)
        # All LS/CS/NE variants use the full POTHTG model with crown ratio
        # and relative height modifiers, not the simple H-D snapshot blend.
        # This ensures site-index-driven height growth dynamics.
        # Calculate RELHT (relative height)
        if top_height is not None and top_height > 0:
            relht = min(1.5, self.height / top_height)
        else:
            relht = 1.0

        self._update_height_large_tree(
            site_index=site_index,
            ba=ba,
            pbal=pbal,
            relht=relht,
            time_step=time_step,
            variant=variant
        )

    def _update_height_large_tree_variant(self, variant: str, site_index: float) -> None:
        """Update height for variant large trees using height-diameter relationship.

        Uses the Curtis-Arney height-diameter model to update height based on
        the new diameter after growth. Works for LS, PN, and WC variants.

        Args:
            variant: FVS variant code ('LS', 'PN', 'WC')
            site_index: Site index in feet - stored for potential future use
        """
        from .height_diameter import create_height_diameter_model

        # Get height-diameter model for this species and variant
        hd_model = create_height_diameter_model(self.species, variant=variant)

        # Calculate expected height for current DBH using Curtis-Arney model
        expected_height = hd_model.predict_height(self.dbh)

        # Apply smooth transition to new height (avoid abrupt changes)
        # Weight current height 30%, predicted height 70%
        self.height = 0.3 * self.height + 0.7 * expected_height

    def _grow_large_tree_topographic(
        self,
        variant: str,
        site_index: float,
        ba: float,
        pbal: float,
        slope: float = 0.0,
        aspect: float = 0.0,
        time_step: float = 10.0,
        elevation: float = None,
        rng=None,
        top_height: float = None
    ) -> None:
        """Generic large tree growth for topographic variants (PN, WC, CA, OC, WS).

        All these variants use ln(DDS) equations with topographic effects:
        - Elevation, slope, aspect terms
        - RELHT (relative height) competition
        - PCCF (point crown competition factor)

        Args:
            variant: FVS variant code ('PN', 'WC', 'CA', 'OC', 'WS')
            site_index: Site index (base age 50) in feet
            ba: Stand basal area (sq ft/acre)
            pbal: Basal area in larger trees (sq ft/acre)
            slope: Ground slope as proportion (0-1, default 0)
            aspect: Aspect in radians (0=N, π/2=E, default 0)
            time_step: Number of years to grow (default varies by variant)
            elevation: Elevation - units vary by variant (see below)
        """
        from .bark_ratio import create_bark_ratio_model
        from .variant_registry import create_diameter_growth_model, get_variant_config

        # Get diameter growth model from registry (unified factory)
        dg_model = create_diameter_growth_model(self.species, variant)

        # Use provided elevation or default from registry
        variant_config = get_variant_config(variant)
        elev = elevation if elevation is not None else variant_config.default_elevation

        # Get bark ratio for diameter conversion (variant-aware)
        bark_model = create_bark_ratio_model(self.species, variant=variant)
        bark_ratio = bark_model.calculate_bark_ratio(self.dbh)

        # Calculate RELHT (relative height) - tree height / top stand height
        if top_height is not None and top_height > 0:
            relht = min(1.5, self.height / top_height)
        else:
            relht = 1.0

        # Estimate PCCF from BA (rough approximation)
        pccf = ba * 1.5 if variant == 'CA' else 100.0

        # Calculate diameter growth using variant-specific parameters
        if variant == 'CA':
            # CA model has special interface with forest_class + stochastic support
            diameter_increment = dg_model.calculate_diameter_growth(
                dbh=self.dbh,
                crown_ratio=self.crown_ratio,
                site_index=site_index,
                ba=ba,
                bal=pbal,
                bark_ratio=bark_ratio,
                pccf=pccf,
                relht=relht,
                elevation=elev,
                slope=slope,
                aspect=aspect,
                forest_class=1,
                time_step=time_step,
                rng=rng
            )
        elif variant == 'OC':
            # OC has location_class parameter + stochastic support
            diameter_increment = dg_model.calculate_diameter_growth(
                dbh=self.dbh,
                crown_ratio=self.crown_ratio,
                site_index=site_index,
                ba=ba,
                bal=pbal,
                pccf=pccf,
                relht=relht,
                elevation=elev,
                slope=slope,
                aspect=aspect,
                location_class=0,
                time_step=time_step,
                rng=rng
            )
        elif variant == 'WS':
            # WS has location_class parameter + stochastic support
            diameter_increment = dg_model.calculate_diameter_growth(
                dbh=self.dbh,
                crown_ratio=self.crown_ratio,
                site_index=site_index,
                ba=ba,
                bal=pbal,
                pccf=pccf,
                relht=relht,
                elevation=elev,
                slope=slope,
                aspect=aspect,
                location_class=0,
                time_step=time_step,
                rng=rng
            )
        else:  # PN, WC
            diameter_increment = dg_model.calculate_diameter_growth(
                dbh=self.dbh,
                crown_ratio=self.crown_ratio,
                site_index=site_index,
                ba=ba,
                bal=pbal,
                pccf=pccf,
                relht=relht,
                elevation=elev,
                slope=slope,
                aspect=aspect,
                time_step=time_step,
                bark_ratio=bark_ratio,
                rng=rng
            )

        # Apply increment to DBH
        self.dbh = self.dbh + max(0.0, diameter_increment)

        # Update height using POTHTG model (matching Fortran htgf.f)
        if top_height is not None and top_height > 0:
            relht = min(1.5, self.height / top_height)
        else:
            relht = 1.0

        if variant == 'OC':
            # OC uses site-curve based HTGF (oc/htgf.f) — distinct from the
            # SN regression used by _update_height_large_tree.
            self._update_height_large_tree_oc(
                site_index=site_index,
                relht=relht,
                diameter_increment=max(0.0, diameter_increment),
                bark_ratio=bark_ratio,
                time_step=time_step,
            )
        else:
            self._update_height_large_tree(
                site_index=site_index,
                ba=ba,
                pbal=pbal,
                relht=relht,
                time_step=time_step,
                variant=variant
            )

    def _grow_large_tree_op(self, site_index, ba, pbal, time_step=5):
        """Implement large tree diameter growth model for OP (ORGANON Pacific Northwest) variant.

        Uses the ORGANON diameter growth equation which predicts diameter growth
        directly (not DDS like other variants):

        ln(DG) = B0 + B1*ln(DBH+K1) + B2*DBH^K2 + B3*ln((CR+0.2)/1.2)
                 + B4*ln(SI-4.5) + B5*(BAL^K3/ln(DBH+K4)) + B6*sqrt(BA)

        Key differences from other variants:
        - Predicts diameter growth directly (not DDS)
        - Base cycle is 5 years (like SN)
        - Based on ORGANON model from Oregon State University

        Args:
            site_index: Site index (King 1966, base age 50) in feet
            ba: Stand basal area (sq ft/acre)
            pbal: Basal area in larger trees (sq ft/acre)
            time_step: Number of years to grow (default: 5)
        """
        from .variant_registry import create_diameter_growth_model as _create_dg_model

        # Get the OP diameter growth model from registry
        dg_model = _create_dg_model(self.species, 'OP')

        # Calculate diameter growth using ORGANON model
        # Note: ORGANON predicts diameter growth directly, not DDS
        diameter_increment = dg_model.calculate_diameter_growth(
            dbh=self.dbh,
            crown_ratio=self.crown_ratio,
            site_index=site_index,
            ba=ba,
            bal=pbal,
            time_step=time_step
        )

        # Apply increment to DBH
        self.dbh = self.dbh + diameter_increment

        # Update height using height-diameter relationship for OP
        self._update_height_large_tree_variant('OP', site_index)

    def _grow_large_tree_sn(self, site_index, competition_factor, ba, pbal, slope, aspect, time_step=5, rng=None, top_height=None):
        """Implement large tree diameter growth model for SN (Southern) variant.

        Uses the SN variant ln(DDS) equation:
        ln(DDS) = CONSPP + INTERC + LDBH*ln(D) + DBH2*D^2 + LCRWN*ln(CR)
                  + HREL*RELHT + PLTB*BA + PNTBL*PBAL
                  + [forest_type_effect] + [ecounit_effect] + [plant_effect]

        Args:
            site_index: Site index (base age 25) in feet
            competition_factor: Competition factor (0-1)
            ba: Stand basal area (sq ft/acre)
            pbal: Basal area in larger trees (sq ft/acre)
            slope: Ground slope as tangent (rise/run)
            aspect: Aspect in radians
            time_step: Number of years to grow (default: 5)
        """
        from .variant_registry import create_diameter_growth_model
        from .bark_ratio import create_bark_ratio_model

        # Get the SN diameter growth model from registry
        dg_model = create_diameter_growth_model(self.species, 'SN')

        # Get bark ratio for diameter conversion
        bark_model = create_bark_ratio_model(self.species)
        bark_ratio = bark_model.calculate_bark_ratio(self.dbh)

        # Calculate RELHT (relative height)
        if top_height is not None and top_height > 0:
            relht = min(1.5, self.height / top_height)
        else:
            relht = 1.0

        # Get forest type effect
        # When no forest type is set (IFORTP=0 in Fortran), ALL forest type
        # flags stay 0, so no forest type effect is applied. Only when a
        # specific forest type is set do we look up the matching coefficient.
        if self._forest_type is not None:
            from .forest_type import get_forest_type_effect
            fortype_effect = get_forest_type_effect(self.species, self._forest_type)
        else:
            fortype_effect = 0.0

        # Get ecological unit effect
        # When ecounit is not set (tree created outside Stand context),
        # default to '231T' matching native FVS behavior (state=0 → S231T=1).
        from .ecological_unit import get_ecounit_effect
        effective_ecounit = self._ecounit if self._ecounit is not None else '231T'
        ecounit_effect = get_ecounit_effect(self.species, effective_ecounit)

        # Get plant effect — only applied when managed flag is set
        # (matches Fortran FVS which requires MANAGD keyword for KPLANT=1)
        plant_effect = 0.0
        if self._managed:
            plant_config = self.species_params.get('plant', {})
            plant_effect = plant_config.get('value', 0.0)
            planting_effects = self.growth_params.get('large_tree_modifiers', {}).get('planting_effect', {})
            if self.species in planting_effects:
                plant_effect = planting_effects[self.species]

        # Calculate diameter growth using SN model
        diameter_increment = dg_model.calculate_diameter_growth(
            dbh=self.dbh,
            crown_ratio=self.crown_ratio,
            site_index=site_index,
            ba=ba,
            pbal=pbal,
            bark_ratio=bark_ratio,
            relht=relht,
            slope=slope,
            aspect=aspect,
            ecounit_effect=ecounit_effect,
            fortype_effect=fortype_effect,
            plant_effect=plant_effect,
            time_step=time_step,
            rng=rng
        )

        # Apply increment to DBH
        self.dbh = self.dbh + diameter_increment

        # Update height using FVS large-tree height growth model (Section 4.7.2)
        self._update_height_large_tree(
            site_index=site_index,
            ba=ba,
            pbal=pbal,
            slope=slope,
            aspect=aspect,
            relht=relht,
            time_step=time_step,
            competition_factor=competition_factor,
            variant='SN'
        )
    
    def _update_crown_ratio_weibull(self, rank, relsdi, competition_factor, time_step=5):
        """Update crown ratio using Weibull-based model with FVS-style change calculation.

        FVS calculates crown ratio CHANGE, not absolute CR:
        1. Predict "old" CR from start-of-cycle conditions
        2. Predict "new" CR from end-of-cycle conditions
        3. Change = new_prediction - old_prediction
        4. Apply change to actual CR

        This prevents rapid crown ratio collapse that occurs when
        replacing CR with predicted values directly.

        Args:
            rank: Tree's rank in diameter distribution (0-1)
            relsdi: Relative stand density index (0-12)
            competition_factor: Competition factor (0-1)
            time_step: Growth cycle length in years (default 5)
        """
        from .crown_ratio import create_crown_ratio_model

        # Create crown ratio model for this species and variant
        variant = self._variant
        cr_model = create_crown_ratio_model(self.species, variant=variant)

        # Calculate CCF from competition factor (rough approximation)
        ccf = 100.0 + 100.0 * competition_factor

        try:
            # Predict crown ratio for current conditions (end of growth cycle)
            predicted_cr = cr_model.predict_individual_crown_ratio(rank, relsdi, ccf)

            # FVS-style change calculation (crown.f lines 310-314):
            # PDIFPY = CHG / REAL(ICR(I)) / FINT
            # IF(PDIFPY.GT.0.01) CHG = REAL(ICR(I)) * 0.01 * FINT
            # IF(PDIFPY.LT.-0.01) CHG = REAL(ICR(I)) * (-0.01) * FINT
            # Change is bounded as a PROPORTION of current CR (1% per year),
            # not a flat absolute amount.
            max_change_per_cycle = self.crown_ratio * 0.01 * time_step

            # Calculate change from current CR toward predicted CR
            change = predicted_cr - self.crown_ratio

            # Bound the change (proportional to current CR)
            bounded_change = max(-max_change_per_cycle,
                               min(max_change_per_cycle, change))

            # Apply change to current crown ratio
            new_cr = self.crown_ratio + bounded_change

            # Ensure reasonable bounds
            self.crown_ratio = max(0.15, min(0.95, new_cr))
        except (ValueError, KeyError, AttributeError) as exc:
            self.logger.debug(
                "Crown ratio model failed for %s (DBH=%.1f): %s; using gradual reduction",
                self.species, self.dbh, exc,
            )
            reduction = 0.02 * (time_step / 5.0)
            self.crown_ratio = max(0.15, min(0.95,
                self.crown_ratio * (1.0 - reduction)))
    
    def _update_dbh_from_height(self):
        """Update DBH based on height using height-diameter model.

        Sub-breast-height behavior matches Fortran regent.f:285-287:
        When HT <= 4.5: DG=0; DBH = D + 0.001*HK (DBH stays near initial value).
        Above breast height: use H-D relationship to derive DBH from height.
        """
        original_dbh = self.dbh

        if self.height <= 4.5:
            # Sub-breast-height: freeze DBH with tiny increment
            # Fortran: DG=0; DBH = D + 0.001*HK
            self.dbh = original_dbh + 0.001 * self.height
        else:
            # Above breast height: use H-D relationship
            from .height_diameter import create_height_diameter_model
            variant = self._variant
            hd_model = create_height_diameter_model(self.species, variant=variant)

            dbh = hd_model.solve_dbh_from_height(
                target_height=self.height,
                initial_dbh=self.dbh
            )
            # Ensure minimum DBH for species (Fortran DIAM(ISPC))
            min_dbh = hd_model.hd_params['curtis_arney'].get('dbw', 0.1)
            self.dbh = max(original_dbh, dbh, min_dbh)
    
    def _update_height_from_dbh(self):
        """Update height based on DBH using height-diameter model."""
        from .height_diameter import create_height_diameter_model

        # Create height-diameter model for this species
        hd_model = create_height_diameter_model(self.species)

        # Use the default model specified in configuration
        self.height = hd_model.predict_height(self.dbh)

    def _update_height_large_tree(
        self,
        site_index: float,
        ba: float = 25.0,
        pbal: float = 0.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        relht: float = 1.0,
        time_step: int = 5,
        competition_factor: float = 0.0,
        variant: str = 'SN'
    ):
        """Update height using FVS large-tree height growth model (Section 4.7.2).

        Delegates to the large_tree_height_growth module which implements the
        FVS potential height growth equations:
        HTG = POTHTG * (0.25 * HGMDCR + 0.75 * HGMDRH)

        Where:
        - POTHTG = potential height growth from site index curve
        - HGMDCR = crown ratio modifier (Hoerl's Special Function)
        - HGMDRH = relative height modifier (shade tolerance dependent)

        Args:
            site_index: Site index in feet (base age varies by variant)
            ba: Stand basal area (sq ft/acre)
            pbal: Plot basal area in larger trees (sq ft/acre)
            slope: Ground slope as tangent (rise/run)
            aspect: Aspect in radians
            relht: Relative height (tree height / top height)
            time_step: Number of years to grow (default: 5)
            competition_factor: Competition factor (0-1), higher = more competition
            variant: FVS variant code (e.g., 'SN', 'LS', 'CS', 'NE')
        """
        from .large_tree_height_growth import calculate_large_tree_height_growth

        # Calculate height growth using the module (variant-aware)
        htg = calculate_large_tree_height_growth(
            species_code=self.species,
            dbh=self.dbh,
            crown_ratio=self.crown_ratio,
            relative_height=relht,
            site_index=site_index,
            basal_area=ba,
            pbal=pbal,
            slope=slope,
            aspect=aspect,
            tree_age=self.age,
            tree_height=self.height,
            variant=variant
        )

        # Scale for time step (module returns 5-year growth)
        htg = htg * (time_step / 5.0)

        # Note: No additional competition modifier is applied here.
        # Fortran htgf.f uses HTGMOD = 0.25*HGMDCR + 0.75*HGMDRH as the
        # sole competition/position modifier. This is already computed in
        # calculate_large_tree_height_growth().

        # Update height with bounds checking
        self.height = max(4.5, self.height + htg)

    def _update_height_large_tree_oc(
        self,
        site_index: float,
        relht: float,
        diameter_increment: float,
        bark_ratio: float,
        time_step: float = 5.0,
    ) -> None:
        """OC variant large-tree height update (oc/htgf.f).

        Uses the OC site-curve / FINDAG approach instead of the SN-style
        ln(DDS) regression. RW (50) and GS (23) take a special direct
        equation that depends on inside-bark diameter growth.

        Args:
            site_index: Site index (feet, base age 50, R6).
            relht: Relative height (tree height / top height), bounded 0-1
                inside HTGF.
            diameter_increment: Outside-bark DBH growth this cycle (inches).
                Converted to inside-bark via bark_ratio for the RW/GS path.
            bark_ratio: Inside-bark / outside-bark ratio (DIB/DOB).
            time_step: Cycle length in years.
        """
        from .oc_height_growth import calculate_oc_large_tree_height_growth

        # Convert OB increment to IB to match Fortran HTGF semantics where
        # DG(I) is stored as inside-bark.
        dg_inside_bark = diameter_increment * bark_ratio if bark_ratio > 0 else diameter_increment

        htg = calculate_oc_large_tree_height_growth(
            species_code=self.species,
            dbh=self.dbh,
            height=self.height,
            crown_ratio=self.crown_ratio,
            relative_height=relht,
            site_index=site_index,
            diameter_growth_inside_bark=dg_inside_bark,
            bark_ratio=bark_ratio,
            time_step=time_step,
            jfor=6,  # SW Oregon is R6
        )

        self.height = max(4.5, self.height + htg)

    def get_volume(self, volume_type: str = 'total_cubic') -> float:
        """Calculate tree volume using USFS Volume Estimator Library.
        
        Args:
            volume_type: Type of volume to return. Options:
                - 'total_cubic': Total cubic volume (default)
                - 'merchantable_cubic': Merchantable cubic volume
                - 'board_foot': Board foot volume
                - 'green_weight': Green weight in pounds
                - 'dry_weight': Dry weight in pounds
                - 'biomass_main_stem': Main stem biomass
                
        Returns:
            Volume in specified units
        """
        from .volume_library import calculate_tree_volume

        # Calculate volume using taper model if available, fallback otherwise
        result = calculate_tree_volume(
            dbh=self.dbh,
            height=self.height,
            species_code=self.species,
            variant=self._variant
        )

        # Return requested volume type
        volume_mapping = {
            'total_cubic': result.total_cubic_volume,
            'gross_cubic': result.gross_cubic_volume,
            'net_cubic': result.net_cubic_volume,
            'merchantable_cubic': result.merchantable_cubic_volume,
            'board_foot': result.board_foot_volume,
            'cord': result.cord_volume,
            'green_weight': result.green_weight,
            'dry_weight': result.dry_weight,
            'sawlog_cubic': result.sawlog_cubic_volume,
            'sawlog_board_foot': result.sawlog_board_foot,
            'biomass_main_stem': result.biomass_main_stem,
            'biomass_live_branches': result.biomass_live_branches,
            'biomass_foliage': result.biomass_foliage
        }
        
        return volume_mapping.get(volume_type, result.total_cubic_volume)
    
    def get_volume_detailed(self) -> dict:
        """Get detailed volume breakdown for the tree.
        
        Returns:
            Dictionary with all volume types and biomass estimates
        """
        from .volume_library import calculate_tree_volume

        result = calculate_tree_volume(
            dbh=self.dbh,
            height=self.height,
            species_code=self.species,
            variant=self._variant
        )

        return result.to_dict()

    def to_tree_record(self, tree_id: int = 0, year: int = 0,
                      ba_percentile: float = 0.0, pbal: float = 0.0,
                      prev_dbh: Optional[float] = None,
                      prev_height: Optional[float] = None) -> Dict[str, Any]:
        """Convert tree to FVS-compatible tree record format.

        Creates a dictionary matching the FVS_TreeList database table schema
        for compatibility with FVS output processing tools.

        Args:
            tree_id: Unique tree identifier within stand
            year: Stand age/simulation year
            ba_percentile: Basal area percentile (rank) 0-100
            pbal: Point basal area in larger trees (sq ft/acre)
            prev_dbh: Previous period DBH (for growth calculation)
            prev_height: Previous period height (for growth calculation)

        Returns:
            Dictionary with FVS_TreeList compatible columns:
            - TreeId: Tree identifier
            - Species: Species code
            - Year: Simulation year
            - TPA: Trees per acre (expansion factor)
            - DBH: Diameter at breast height (inches)
            - DG: Diameter growth since last period (inches)
            - Ht: Total height (feet)
            - HtG: Height growth since last period (feet)
            - PctCr: Crown ratio as percent (0-100)
            - CrWidth: Crown width (feet)
            - Age: Tree age (years)
            - BAPctile: Basal area percentile
            - PtBAL: Point basal area larger
            - TcuFt: Total cubic foot volume
            - McuFt: Merchantable cubic foot volume
            - BdFt: Board foot volume (Scribner)
        """
        from .crown_width import calculate_open_crown_width

        # Calculate growth since last period
        dg = self.dbh - prev_dbh if prev_dbh is not None else 0.0
        htg = self.height - prev_height if prev_height is not None else 0.0

        # Calculate crown width
        try:
            cr_width = calculate_open_crown_width(self.species, self.dbh)
        except (ValueError, KeyError, AttributeError) as exc:
            self.logger.debug(
                "Crown width failed for %s (DBH=%.1f): %s; using fallback",
                self.species, self.dbh, exc,
            )
            cr_width = self.dbh * 1.5

        # Get volumes
        total_cubic = self.get_volume('total_cubic')
        merch_cubic = self.get_volume('merchantable_cubic')
        board_feet = self.get_volume('board_foot')

        return {
            'TreeId': tree_id,
            'Species': self.species,
            'Year': year,
            'TPA': 1.0,  # Each tree object represents 1 tree/acre
            'DBH': round(self.dbh, 2),
            'DG': round(dg, 3),
            'Ht': round(self.height, 1),
            'HtG': round(htg, 2),
            'PctCr': round(self.crown_ratio * 100, 1),
            'CrWidth': round(cr_width, 1),
            'Age': self.age,
            'BAPctile': round(ba_percentile, 1),
            'PtBAL': round(pbal, 2),
            'TcuFt': round(total_cubic, 2),
            'McuFt': round(merch_cubic, 2),
            'BdFt': round(board_feet, 1)
        } 
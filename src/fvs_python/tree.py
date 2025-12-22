"""
Tree class representing an individual tree.
Implements both small-tree and large-tree growth models.
"""
import math
import yaml
import numpy as np
from scipy.stats import weibull_min
from pathlib import Path
from typing import Dict, Any, Optional
from .validation import ParameterValidator
from .logging_config import get_logger, log_model_transition

class Tree:
    def __init__(self, dbh, height, species="LP", age=0, crown_ratio=0.85):
        """Initialize a tree with basic measurements.
        
        Args:
            dbh: Diameter at breast height (inches)
            height: Total height (feet)
            species: Species code (e.g., "LP" for loblolly pine)
            age: Tree age in years
            crown_ratio: Initial crown ratio (proportion of tree height with live crown)
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

        # Initialize optional ecounit and forest_type (set during grow())
        self._ecounit = None
        self._forest_type = None

        # Set up logging
        self.logger = get_logger(__name__)
        
        # Check height-DBH relationship (disabled warning for small seedlings)
        if self.height > 4.5 and not ParameterValidator.check_height_dbh_relationship(self.dbh, self.height):
            self.logger.warning(
                f"Unusual height-DBH relationship: DBH={self.dbh}, Height={self.height}"
            )
        
        # Load configuration
        self._load_config()
    
    def _load_config(self):
        """Load configuration using the new config loader."""
        from .config_loader import get_config_loader
        
        loader = get_config_loader()
        
        # Load species-specific parameters
        self.species_params = loader.load_species_config(self.species)
        
        # Load functional forms and site index parameters
        self.functional_forms = loader.functional_forms
        self.site_index_params = loader.site_index_params
        
        # Load growth model parameters
        try:
            growth_params_file = loader.cfg_dir / 'growth_model_parameters.yaml'
            self.growth_params = loader._load_config_file(growth_params_file)
        except Exception:
            # Fallback to defaults if file not found
            self.growth_params = {
                'growth_transitions': {'small_to_large_tree': {'xmin': 1.0, 'xmax': 3.0}},
                'small_tree_growth': {'default': {
                    'c1': 1.1421, 'c2': 1.0042, 'c3': -0.0374, 'c4': 0.7632, 'c5': 0.0358
                }}
            }
    
    def grow(self, site_index: float, competition_factor: float, rank: float = 0.5, relsdi: float = 5.0, ba: float = 100, pbal: float = 50, slope: float = 0.05, aspect: float = 0, time_step: int = 5, ecounit: str = None, forest_type: str = None) -> None:
        """Grow the tree for the specified number of years.

        Args:
            site_index: Site index (base age 25) in feet
            competition_factor: Competition factor (0-1)
            rank: Tree's rank in diameter distribution (0-1)
            relsdi: Relative stand density index (0-12)
            ba: Stand basal area (sq ft/acre)
            pbal: Plot basal area in larger trees (sq ft/acre)
            slope: Ground slope (proportion)
            aspect: Aspect in radians
            time_step: Number of years to grow the tree (default: 5)
            ecounit: Ecological unit code (e.g., "232", "M231") - passed from Stand
            forest_type: Forest type group (e.g., "FTYLPN") - passed from Stand
        """
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
        transition_params = self.growth_params['growth_transitions']['small_to_large_tree']
        xmin = transition_params['xmin']  # minimum DBH for transition (inches)
        xmax = transition_params['xmax']  # maximum DBH for transition (inches)
        
        # Calculate weight for blending growth models based on initial DBH
        # Use smoothstep function for smoother transition (reduces discontinuities)
        if initial_dbh < xmin:
            weight = 0.0
            model_used = "small_tree"
        elif initial_dbh > xmax:
            weight = 1.0
            model_used = "large_tree"
        else:
            # Smoothstep function: 3t² - 2t³ where t = (dbh - xmin) / (xmax - xmin)
            t = (initial_dbh - xmin) / (xmax - xmin)
            weight = t * t * (3.0 - 2.0 * t)
            model_used = "blended"
            
        # Log model transition if crossing threshold
        if initial_dbh < xmin and self.dbh >= xmin:
            log_model_transition(self.logger, f"{self.species}_{id(self)}", 
                                "small_tree", "blended", self.dbh)
        elif initial_dbh < xmax and self.dbh >= xmax:
            log_model_transition(self.logger, f"{self.species}_{id(self)}", 
                                "blended", "large_tree", self.dbh)
        
        # Temporarily increment age for growth calculations
        self.age = initial_age + time_step
        
        # Calculate small tree growth
        self._grow_small_tree(site_index, competition_factor, time_step)
        small_dbh = self.dbh
        small_height = self.height
        
        # Reset to initial state for large tree model
        self.dbh = initial_dbh
        self.height = initial_height
        
        # Calculate large tree growth
        self._grow_large_tree(site_index, competition_factor, ba, pbal, slope, aspect, time_step)
        large_dbh = self.dbh
        large_height = self.height
        
        # Blend results based on initial DBH
        self.dbh = (1 - weight) * small_dbh + weight * large_dbh
        self.height = (1 - weight) * small_height + weight * large_height
        
        # Ensure age is properly set after growth
        self.age = initial_age + time_step
        
        # Update crown ratio using Weibull model (pass time_step for proper scaling)
        self._update_crown_ratio_weibull(rank, relsdi, competition_factor, time_step)
    
    def _grow_small_tree(self, site_index, competition_factor, time_step=5):
        """Implement small tree height growth model using Chapman-Richards function.

        The Chapman-Richards model (NC-128 form) predicts cumulative height at
        a given age, not periodic growth. Height growth is calculated as the
        difference between heights at future age and current age:

            Height(t) = c1 * SI^c2 * (1 - exp(c3 * t))^(c4 * SI^c5)
            HeightGrowth = Height(age + time_step) - Height(age)

        **Time Step Handling:** Unlike the large tree diameter growth model which
        requires explicit scaling (DDS * time_step/5), the Chapman-Richards
        equation naturally handles any time step because it calculates cumulative
        height at discrete ages. The growth increment is simply the difference
        between the height curves at two points in time.

        **Ecological Unit Effect:** Unlike the large-tree DDS model which applies
        ecounit as an additive term in ln(DDS), the small-tree model does NOT
        apply an ecounit modifier. This is because:
        1. Site Index already incorporates regional productivity - SI=55 means
           height at base age 25 = 55 feet, regardless of region
        2. The Chapman-Richards curve is calibrated to match SI at base age
        3. The FVS large-tree height growth (POTHTG) also does NOT apply ecounit
        4. Ecounit affects DIAMETER growth (DDS), not height growth

        Args:
            site_index: Site index (base age 25) in feet
            competition_factor: Competition factor (0-1)
            time_step: Number of years to grow (any positive integer)
        """
        # Get parameters from config
        small_tree_params = self.growth_params.get('small_tree_growth', {})
        if self.species in small_tree_params:
            p = small_tree_params[self.species]
        else:
            p = small_tree_params.get('default', {
                'c1': 1.1421,
                'c2': 1.0042,
                'c3': -0.0374,
                'c4': 0.7632,
                'c5': 0.0358
            })
        
        # Chapman-Richards predicts cumulative height at age t
        # Height(t) = c1 * SI^c2 * (1 - exp(c3 * t))^(c4 * SI^c5)
        #
        # The NC-128 coefficients may have been calibrated with a different site index
        # base age. To ensure Height(base_age=25) = SI, we compute a scaling factor.

        # Current age (before growth) - age was already incremented in grow()
        current_age = self.age - time_step
        future_age = self.age  # This is current_age + time_step

        # Site index base age for southern pines
        base_age = 25

        def _raw_chapman_richards(age):
            """Calculate unscaled Chapman-Richards height."""
            if age <= 0:
                return 1.0
            return (
                p['c1'] * (site_index ** p['c2']) *
                (1.0 - math.exp(p['c3'] * age)) **
                (p['c4'] * (site_index ** p['c5']))
            )

        # Calculate scaling factor to ensure Height(base_age) = SI
        # This corrects for NC-128 coefficients that may use different base ages
        raw_height_at_base = _raw_chapman_richards(base_age)
        if raw_height_at_base > 0:
            scale_factor = site_index / raw_height_at_base
        else:
            scale_factor = 1.0

        # Calculate scaled heights
        if current_age <= 0:
            current_height = 1.0  # Initial height at planting
        else:
            current_height = _raw_chapman_richards(current_age) * scale_factor

        future_height = _raw_chapman_richards(future_age) * scale_factor
        
        # Height growth is the difference
        height_growth = future_height - current_height

        # NOTE: No ecounit modifier is applied to height growth. Site Index
        # already incorporates regional productivity through the Chapman-Richards
        # curve. However, the ecounit effect IS applied to DIAMETER growth below.

        # Apply a modifier for competition (subtle effect for small trees)
        # Small trees are less affected by competition than large trees
        max_reduction = self.growth_params.get('competition_effects', {}).get(
            'small_tree_competition', {}).get('max_reduction', 0.2)
        competition_modifier = 1.0 - (max_reduction * competition_factor)
        actual_growth = height_growth * competition_modifier

        # Update height with bounds checking
        self.height = max(4.5, self.height + actual_growth)

        # Get ecological unit effect for DIAMETER growth (not height)
        # This matches how FVS applies ecounit to the DDS equation for large trees
        ecounit_multiplier = 1.0
        if self._ecounit is not None:
            from .ecological_unit import get_ecounit_effect
            ecounit_effect = get_ecounit_effect(self.species, self._ecounit)
            # Convert additive ln(DDS) effect to multiplicative diameter increment effect
            # For M231 with LP: ecounit_effect = 0.790, exp(0.790) ≈ 2.2x growth
            ecounit_multiplier = math.exp(ecounit_effect)

        # Save original DBH before height-diameter update
        original_dbh = self.dbh

        # Calculate new DBH from height using height-diameter relationship
        self._update_dbh_from_height()

        # Apply ecounit effect to the DBH INCREMENT (not to height)
        # This ensures regional productivity affects diameter growth
        if ecounit_multiplier != 1.0 and self.dbh > original_dbh:
            dbh_increment = self.dbh - original_dbh
            adjusted_increment = dbh_increment * ecounit_multiplier
            self.dbh = original_dbh + adjusted_increment
    
    def _grow_large_tree(self, site_index, competition_factor, ba, pbal, slope, aspect, time_step=5):
        """Implement large tree diameter growth model using official FVS-SN equations.

        Based on USDA Forest Service FVS Southern Variant (SN) from dgf.f:
        ln(DDS) = CONSPP + INTERC + LDBH*ln(D) + DBH2*D^2 + LCRWN*ln(CR)
                  + HREL*RELHT + PLTB*BA + PNTBL*PBAL
                  + [forest_type_terms] + [eco_unit_terms] + [plant_effect]

        Where CONSPP = ISIO*SI + TANS*SLOPE + FCOS*SLOPE*cos(ASPECT) + FSIN*SLOPE*sin(ASPECT)

        Args:
            site_index: Site index (base age 50) in feet
            competition_factor: Competition factor (0-1)
            ba: Stand basal area (sq ft/acre), minimum 25.0
            pbal: Plot basal area in larger trees (sq ft/acre)
            slope: Ground slope as tangent (rise/run)
            aspect: Aspect in radians
            time_step: Number of years to grow (default: 5)
        """
        # Get diameter growth coefficients from species config
        dg_config = self.species_params.get('diameter_growth', {})
        p = dg_config.get('coefficients', {})

        # Apply FVS bounds
        # BA minimum is 25.0 in FVS
        ba_bounded = max(25.0, ba)

        # Crown ratio for FVS must be integer percentage (0-100), minimum 25
        # Our crown_ratio is stored as proportion (0-1), convert to percentage
        cr_pct = max(25.0, self.crown_ratio * 100.0)

        # Relative height (RELHT) = HT/AVH, capped at 1.5 in FVS
        # AVH is the average height of the 40 largest trees (top height)
        # For individual tree growth without stand context, assume codominant (relht = 1.0)
        # This is appropriate for:
        # - Plantation trees that are uniformly managed
        # - Dominant/codominant trees in natural stands
        # When called from Stand.grow(), the Stand should pass actual top height
        # via the _top_height attribute if competition-based height reduction is needed
        if hasattr(self, '_top_height') and self._top_height is not None and self._top_height > 0:
            # Use actual stand top height (passed from Stand)
            relht = min(1.5, self.height / self._top_height)
        else:
            # Default: assume codominant tree (no height suppression)
            # This is appropriate for plantations and dominant trees
            relht = 1.0

        # Get forest type effect - use passed forest_type or fall back to species config
        fortype_config = self.species_params.get('fortype', {})
        if self._forest_type is not None:
            # Use passed forest type from Stand
            from .forest_type import get_forest_type_effect
            fortype_effect = get_forest_type_effect(self.species, self._forest_type)
        else:
            # Fall back to species config base forest type
            fortype_effect = fortype_config.get('coefficients', {}).get(
                fortype_config.get('base_fortype', 'FTYLPN'), 0.0
            )

        # Get ecological unit effect - use passed ecounit or fall back to species config
        if self._ecounit is not None:
            # Use passed ecounit from Stand
            from .ecological_unit import get_ecounit_effect
            ecounit_effect = get_ecounit_effect(self.species, self._ecounit)
        else:
            # Fall back to species config base ecounit (typically 0.0)
            ecounit_config = self.species_params.get('ecounit', {}).get('table_4_7_1_5', {})
            ecounit_effect = ecounit_config.get('coefficients', {}).get(
                ecounit_config.get('base_ecounit', '232'), 0.0
            )

        # Get plant effect from species config
        plant_config = self.species_params.get('plant', {})
        plant_effect = plant_config.get('value', 0.0)

        # Also check growth_params for managed plantation setting
        planting_effects = self.growth_params.get('large_tree_modifiers', {}).get('planting_effect', {})
        if self.species in planting_effects:
            plant_effect = planting_effects[self.species]

        # Build the diameter growth equation following official FVS structure
        # Coefficient mapping from config (b1-b11) to FVS variables:
        # b1 = INTERC (intercept)
        # b2 = LDBH (ln(DBH) coefficient)
        # b3 = DBH2 (DBH^2 coefficient)
        # b4 = LCRWN (ln(CR) coefficient)
        # b5 = HREL (relative height coefficient)
        # b6 = ISIO (site index coefficient)
        # b7 = PLTB (basal area coefficient) - NOTE: config may have wrong value
        # b8 = PNTBL (point basal area larger coefficient)
        # b9 = TANS (slope tangent coefficient)
        # b10 = FCOS (slope*cos(aspect) coefficient)
        # b11 = FSIN (slope*sin(aspect) coefficient)

        # Check for new-style coefficient names first, fall back to b1-b11
        interc = p.get('INTERC', p.get('b1', 0.0))
        ldbh = p.get('LDBH', p.get('b2', 0.0))
        dbh2 = p.get('DBH2', p.get('b3', 0.0))
        lcrwn = p.get('LCRWN', p.get('b4', 0.0))
        hrel = p.get('HREL', p.get('b5', 0.0))
        isio = p.get('ISIO', p.get('b6', 0.0))
        pltb = p.get('PLTB', p.get('b7', 0.0))
        pntbl = p.get('PNTBL', p.get('b8', 0.0))
        tans = p.get('TANS', p.get('b9', 0.0))
        fcos = p.get('FCOS', p.get('b10', 0.0))
        fsin = p.get('FSIN', p.get('b11', 0.0))

        # Calculate CONSPP (site and topographic terms)
        # CONSPP = ISIO*SI + TANS*SLOPE + FCOS*SLOPE*cos(ASPECT) + FSIN*SLOPE*sin(ASPECT)
        conspp = (
            isio * site_index +
            tans * slope +
            fcos * slope * math.cos(aspect) +
            fsin * slope * math.sin(aspect)
        )

        # Calculate ln(DDS) - change in squared diameter (inside bark)
        # Main equation: ln(DDS) = CONSPP + INTERC + LDBH*ln(D) + DBH2*D^2
        #                         + LCRWN*ln(CR) + HREL*RELHT + PLTB*BA + PNTBL*PBAL
        #                         + [forest_type] + [eco_unit] + [plant_effect]
        ln_dds = (
            conspp +
            interc +
            ldbh * math.log(self.dbh) +
            dbh2 * self.dbh**2 +
            lcrwn * math.log(cr_pct) +
            hrel * relht +
            pltb * ba_bounded +
            pntbl * pbal +
            fortype_effect +
            ecounit_effect +
            plant_effect
        )

        # Apply FVS minimum bound for ln(DDS)
        ln_dds = max(-9.21, ln_dds)

        # Convert ln(DDS) to diameter growth
        # DDS is change in squared diameter (inside bark) over growth period
        # Scale growth based on time_step (model is calibrated for 5-year growth)
        dds = math.exp(ln_dds) * (time_step / 5.0)

        # FVS applies DDS to inside-bark diameter, then converts back to outside-bark
        # From dgdriv.f: D=DBH(I)*BRATIO(...); DG=(SQRT(DSQ+DDS)-D)
        # We must convert DBH to inside-bark, apply DDS, then convert back
        from .bark_ratio import create_bark_ratio_model
        bark_model = create_bark_ratio_model(self.species)

        # Get bark ratio (DIB/DOB) for current tree
        bark_ratio = bark_model.calculate_bark_ratio(self.dbh)

        # Convert to inside-bark diameter
        dib_old = self.dbh * bark_ratio
        dib_old_sq = dib_old * dib_old

        # Apply DDS to inside-bark diameter
        dib_new = math.sqrt(dib_old_sq + dds)

        # Convert back to outside-bark (DBH)
        self.dbh = dib_new / bark_ratio

        # Update height using FVS large-tree height growth model (Section 4.7.2)
        # HTG = POTHTG * (0.25 * HGMDCR + 0.75 * HGMDRH)
        self._update_height_large_tree(
            site_index=site_index,
            ba=ba_bounded,
            pbal=pbal,
            slope=slope,
            aspect=aspect,
            relht=relht,
            time_step=time_step,
            competition_factor=competition_factor
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

        # Create crown ratio model for this species
        cr_model = create_crown_ratio_model(self.species)

        # Calculate CCF from competition factor (rough approximation)
        ccf = 100.0 + 100.0 * competition_factor

        try:
            # Predict crown ratio for current conditions (end of growth cycle)
            predicted_cr = cr_model.predict_individual_crown_ratio(rank, relsdi, ccf)

            # FVS-style change calculation:
            # The change is bounded to prevent dramatic swings
            # Maximum change is typically 5% per 5-year cycle (1% per year)
            # Scale by time_step to handle different cycle lengths
            max_change_per_cycle = 0.05 * (time_step / 5.0)

            # Calculate change from current CR toward predicted CR
            change = predicted_cr - self.crown_ratio

            # Bound the change
            bounded_change = max(-max_change_per_cycle,
                               min(max_change_per_cycle, change))

            # Apply change to current crown ratio
            new_cr = self.crown_ratio + bounded_change

            # Apply age-related reduction (small gradual decrease with age)
            # Scale by time_step to maintain consistent rate regardless of cycle length
            cr_params = self.growth_params.get('crown_ratio', {})
            age_reduction_rate = cr_params.get('age_reduction', {}).get('rate', 0.001)
            age_reduction = age_reduction_rate * (time_step / 5.0)  # Scale per cycle
            new_cr = new_cr * (1.0 - age_reduction)

            # Ensure reasonable bounds
            self.crown_ratio = max(0.15, min(0.95, new_cr))
        except Exception:
            # Fallback to simpler update if crown ratio calculation fails
            # Use gradual reduction rather than replacement
            # Scale by time_step (2% per 5-year cycle = 0.4% per year)
            reduction = 0.02 * (time_step / 5.0)
            self.crown_ratio = max(0.15, min(0.95,
                self.crown_ratio * (1.0 - reduction)))
    
    def _update_dbh_from_height(self):
        """Update DBH based on height using height-diameter model."""
        from .height_diameter import create_height_diameter_model
        
        # Create height-diameter model for this species
        hd_model = create_height_diameter_model(self.species)
        
        # Store original DBH to ensure we don't decrease it
        original_dbh = self.dbh
        
        if self.height <= 4.5:
            dbw = hd_model.hd_params['curtis_arney']['dbw']
            self.dbh = max(original_dbh, dbw)  # Set to minimum DBH, but never decrease
        else:
            # Solve for DBH given target height
            dbh = hd_model.solve_dbh_from_height(
                target_height=self.height,
                initial_dbh=self.dbh
            )
            
            # Ensure DBH never decreases
            self.dbh = max(original_dbh, dbh)
    
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
        competition_factor: float = 0.0
    ):
        """Update height using FVS large-tree height growth model (Section 4.7.2).

        Delegates to the large_tree_height_growth module which implements the
        FVS Southern variant equations:
        HTG = POTHTG * (0.25 * HGMDCR + 0.75 * HGMDRH)

        Where:
        - POTHTG = potential height growth from site index curve
        - HGMDCR = crown ratio modifier (Hoerl's Special Function)
        - HGMDRH = relative height modifier (shade tolerance dependent)

        Args:
            site_index: Site index (base age 25) in feet
            ba: Stand basal area (sq ft/acre)
            pbal: Plot basal area in larger trees (sq ft/acre)
            slope: Ground slope as tangent (rise/run)
            aspect: Aspect in radians
            relht: Relative height (tree height / top height)
            time_step: Number of years to grow (default: 5)
            competition_factor: Competition factor (0-1), higher = more competition
        """
        from .large_tree_height_growth import calculate_large_tree_height_growth

        # Calculate height growth using the module
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
            tree_height=self.height
        )

        # Scale for time step (module returns 5-year growth)
        htg = htg * (time_step / 5.0)

        # Apply competition modifier (consistent with previous implementation)
        competition_effects = self.growth_params.get('competition_effects') or {}
        large_tree_comp = competition_effects.get('large_tree_competition') or {}
        max_reduction = large_tree_comp.get('max_reduction', 0.15)
        competition_modifier = 1.0 - (max_reduction * competition_factor)
        htg = htg * competition_modifier

        # Update height with bounds checking
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
        
        # Calculate volume using NVEL if available, fallback otherwise
        result = calculate_tree_volume(
            dbh=self.dbh,
            height=self.height,
            species_code=self.species
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
            species_code=self.species
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
            - BdFt: Board foot volume (Doyle)
        """
        from .crown_width import calculate_open_crown_width

        # Calculate growth since last period
        dg = self.dbh - prev_dbh if prev_dbh is not None else 0.0
        htg = self.height - prev_height if prev_height is not None else 0.0

        # Calculate crown width
        try:
            cr_width = calculate_open_crown_width(self.species, self.dbh)
        except Exception:
            cr_width = self.dbh * 1.5  # Fallback estimate

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
"""
Stand class managing a collection of trees and stand-level dynamics.
Handles competition, mortality, and stand metrics.

Implements FVS Southern variant stand-level calculations including:
- Crown Competition Factor (CCF) using official equation 4.5.1
- Stand Density Index (SDI) using Reineke's equation
- Relative SDI (RELSDI) for competition modeling
- Forest type classification for growth modifiers
- Ecological unit classification for regional growth effects
"""
import math
import random
import yaml
import json
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Any
from .tree import Tree
from .config_loader import load_stand_config
from .validation import ParameterValidator
from .logging_config import get_logger, log_growth_summary


class Stand:
    """Stand class implementing FVS Southern variant stand dynamics.

    This class manages tree collections and calculates stand-level metrics
    following the official FVS-SN methodology including:
    - CCF (Crown Competition Factor) from crown widths
    - SDI (Stand Density Index) using Reineke's equation
    - RELSDI (Relative SDI) for growth models
    - Forest type and ecological unit effects
    """

    # Class-level cache for SDI maximums
    _sdi_maximums: Optional[Dict[str, int]] = None
    _sdi_loaded: bool = False

    def __init__(self, trees: Optional[List[Tree]] = None, site_index: float = 70,
                 species: str = 'LP', forest_type: Optional[str] = None,
                 ecounit: Optional[str] = None):
        """Initialize a stand with a list of trees.

        Args:
            trees: List of Tree objects. If None, creates an empty stand.
            site_index: Site index (base age 25) in feet
            species: Default species code for stand parameters
            forest_type: FVS forest type group (e.g., "FTYLPN", "FTLOHD")
                        If None, auto-determined from species composition
            ecounit: Ecological unit code (e.g., "M221", "232")
                    Used for regional growth adjustments

        Note:
            Empty stands can be initialized but should have trees added before
            running simulations.
        """
        self.trees = trees if trees is not None else []

        # Validate site index
        validated_params = ParameterValidator.validate_stand_parameters(
            trees_per_acre=len(self.trees) if self.trees else 1,
            site_index=site_index,
            species_code=species
        )
        self.site_index = validated_params['site_index']

        self.age = 0
        self.species = species

        # Forest type and ecological unit for growth modifiers
        self._forest_type = forest_type
        self.ecounit = ecounit

        # Set up logging
        self.logger = get_logger(__name__)

        # Load configuration using new config system
        self.params = load_stand_config(species)

        # Load SDI maximums if not cached
        if not Stand._sdi_loaded:
            self._load_sdi_maximums()

        # Load growth model parameters
        try:
            from .config_loader import get_config_loader
            loader = get_config_loader()
            growth_params_file = loader.cfg_dir / 'growth_model_parameters.yaml'
            self.growth_params = loader._load_config_file(growth_params_file)
        except Exception:
            # Fallback defaults
            self.growth_params = {
                'mortality': {
                    'early_mortality': {'age_threshold': 5, 'base_rate': 0.25},
                    'background_mortality': {'base_rate': 0.05, 'competition_threshold': 0.55, 'competition_multiplier': 0.1}
                },
                'initial_tree': {'dbh': {'mean': 0.5, 'std_dev': 0.1, 'minimum': 0.1}}
            }

    @classmethod
    def _load_sdi_maximums(cls) -> None:
        """Load SDI maximum values from configuration."""
        try:
            sdi_file = Path(__file__).parent.parent.parent / "cfg" / "sn_stand_density_index.json"
            if sdi_file.exists():
                with open(sdi_file, 'r') as f:
                    sdi_data = json.load(f)
                cls._sdi_maximums = {
                    species: data['sdi_maximum']
                    for species, data in sdi_data.get('sdi_maximums', {}).items()
                }
            else:
                cls._sdi_maximums = {'LP': 480, 'SP': 490, 'SA': 385, 'LL': 332}
            cls._sdi_loaded = True
        except Exception:
            cls._sdi_maximums = {'LP': 480, 'SP': 490, 'SA': 385, 'LL': 332}
            cls._sdi_loaded = True

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
        """Auto-determine forest type from stand species composition.

        Uses basal area-weighted species composition to classify stand.

        Returns:
            FVS forest type group code (e.g., "FTYLPN", "FTLOHD")
        """
        if not self.trees:
            return "FTYLPN"  # Default to Yellow Pine

        try:
            from .forest_type import ForestTypeClassifier
            classifier = ForestTypeClassifier()
            result = classifier.classify_from_trees(self.trees, basal_area_weighted=True)
            return result.forest_type_group
        except ImportError:
            # Fallback if forest_type module not available
            return "FTYLPN"

    def calculate_ccf_official(self) -> float:
        """Calculate Crown Competition Factor using official FVS equation 4.5.1.

        Uses open-grown crown widths for each tree:
        - CCFt = 0.001803 * OCW² (for DBH > 0.1 inches)
        - CCFt = 0.001 (for DBH ≤ 0.1 inches)
        - Stand CCF = Σ CCFt

        Returns:
            Stand-level Crown Competition Factor
        """
        if not self.trees:
            return 0.0

        try:
            from .crown_width import CrownWidthModel
        except ImportError:
            # Fallback to approximation
            return self._calculate_ccf()

        CCF_COEFFICIENT = 0.001803
        SMALL_TREE_CCF = 0.001
        DBH_THRESHOLD = 0.1

        total_ccf = 0.0

        for tree in self.trees:
            dbh = getattr(tree, 'dbh', 0.0)
            species = getattr(tree, 'species', self.species)

            if dbh <= DBH_THRESHOLD:
                total_ccf += SMALL_TREE_CCF
            else:
                # Calculate open-grown crown width
                try:
                    model = CrownWidthModel(species)
                    ocw = model.calculate_open_grown_crown_width(dbh)
                    tree_ccf = CCF_COEFFICIENT * (ocw ** 2)
                    total_ccf += tree_ccf
                except Exception:
                    # Fallback: estimate OCW linearly
                    ocw_estimate = 3.0 + 0.15 * dbh
                    total_ccf += CCF_COEFFICIENT * (ocw_estimate ** 2)

        return total_ccf

    def calculate_qmd(self) -> float:
        """Calculate Quadratic Mean Diameter (QMD).

        QMD = sqrt(sum(DBH²) / n)

        Returns:
            Quadratic mean diameter in inches
        """
        if not self.trees:
            return 0.0

        sum_dbh_squared = sum(tree.dbh ** 2 for tree in self.trees)
        n = len(self.trees)

        return math.sqrt(sum_dbh_squared / n)

    def calculate_basal_area(self) -> float:
        """Calculate stand basal area.

        BA = Σ (π * (DBH/24)²)  [sq ft per acre]

        Returns:
            Total basal area in square feet per acre
        """
        if not self.trees:
            return 0.0

        return sum(math.pi * (tree.dbh / 24.0) ** 2 for tree in self.trees)

    def calculate_stand_sdi(self) -> float:
        """Calculate Stand Density Index using Reineke's equation.

        SDI = TPA * (QMD / 10)^1.605

        Returns:
            Stand Density Index
        """
        if not self.trees:
            return 0.0

        tpa = len(self.trees)
        qmd = self.calculate_qmd()

        if qmd <= 0:
            return 0.0

        return tpa * ((qmd / 10.0) ** 1.605)

    def get_max_sdi(self) -> float:
        """Get maximum SDI for the stand based on species composition.

        Uses basal area-weighted average of species-specific SDI maximums.

        Returns:
            Maximum SDI for the stand
        """
        if not self.trees:
            return self._sdi_maximums.get(self.species, 480)

        # Calculate basal area by species
        species_ba: Dict[str, float] = {}
        total_ba = 0.0

        for tree in self.trees:
            species = getattr(tree, 'species', self.species)
            ba = math.pi * (tree.dbh / 24.0) ** 2
            species_ba[species] = species_ba.get(species, 0.0) + ba
            total_ba += ba

        if total_ba == 0:
            return self._sdi_maximums.get(self.species, 480)

        # Weighted average of SDI maximums
        weighted_sdi = 0.0
        for species, ba in species_ba.items():
            species_sdi = self._sdi_maximums.get(species, 400)
            weighted_sdi += (ba / total_ba) * species_sdi

        return weighted_sdi

    def calculate_relsdi(self) -> float:
        """Calculate Relative Stand Density Index (RELSDI).

        RELSDI = (Stand_SDI / Max_SDI) * 10
        Bounded between 1.0 and 12.0 per FVS specification.

        Returns:
            Relative SDI value (1.0-12.0)
        """
        stand_sdi = self.calculate_stand_sdi()
        max_sdi = self.get_max_sdi()

        if max_sdi <= 0:
            return 1.0

        relsdi = (stand_sdi / max_sdi) * 10.0

        # Apply FVS bounds
        return max(1.0, min(12.0, relsdi))

    def calculate_pbal(self, target_tree: Tree) -> float:
        """Calculate Point Basal Area in Larger trees (PBAL).

        PBAL is the basal area of trees with DBH larger than the target tree.

        Args:
            target_tree: Tree to calculate PBAL for

        Returns:
            PBAL in square feet per acre
        """
        target_dbh = target_tree.dbh
        pbal = sum(
            math.pi * (tree.dbh / 24.0) ** 2
            for tree in self.trees
            if tree.dbh > target_dbh
        )
        return pbal

    def get_forest_type_effect(self, species_code: str) -> float:
        """Get forest type growth effect for a species.

        Args:
            species_code: Species code (e.g., "LP", "SP")

        Returns:
            Forest type coefficient to add to growth equation
        """
        try:
            from .forest_type import get_forest_type_effect
            return get_forest_type_effect(species_code, self.forest_type)
        except ImportError:
            return 0.0

    def get_ecounit_effect(self, species_code: str) -> float:
        """Get ecological unit growth effect for a species.

        Args:
            species_code: Species code (e.g., "LP", "SP")

        Returns:
            Ecological unit coefficient to add to growth equation
        """
        if self.ecounit is None:
            return 0.0

        try:
            from .ecological_unit import get_ecounit_effect
            return get_ecounit_effect(species_code, self.ecounit)
        except ImportError:
            return 0.0

    def set_forest_type(self, forest_type: str) -> None:
        """Manually set the forest type.

        Args:
            forest_type: FVS forest type code (e.g., "FTYLPN", "FTLOHD")
        """
        valid_types = {"FTYLPN", "FTLOHD", "FTUPHD", "FTUPOK", "FTOKPN", "FTNOHD", "FTSFHP"}
        if forest_type.upper() not in valid_types:
            self.logger.warning(f"Unknown forest type: {forest_type}. Using as-is.")
        self._forest_type = forest_type.upper()

    def set_ecounit(self, ecounit: str) -> None:
        """Manually set the ecological unit.

        Args:
            ecounit: Ecological unit code (e.g., "M221", "232", "231L")
        """
        self.ecounit = ecounit.upper()

    @classmethod
    def initialize_planted(cls, trees_per_acre: int, site_index: float = 70, species: str = 'LP'):
        """Create a new planted stand.
        
        Args:
            trees_per_acre: Number of trees per acre to plant
            site_index: Site index (base age 25) in feet
            species: Species code for the plantation
            
        Returns:
            Stand: New stand instance
        """
        # Validate parameters
        validated_params = ParameterValidator.validate_stand_parameters(
            trees_per_acre=trees_per_acre,
            site_index=site_index,
            species_code=species
        )
        
        trees_per_acre = validated_params['trees_per_acre']
        site_index = validated_params['site_index']
        
        # Create stand instance to access config
        temp_stand = cls([], site_index, species)
        initial_params = temp_stand.growth_params.get('initial_tree', {})
        
        dbh_params = initial_params.get('dbh', {})
        dbh_mean = dbh_params.get('mean', 0.5)
        dbh_sd = dbh_params.get('std_dev', 0.1)
        dbh_min = dbh_params.get('minimum', 0.1)
        
        initial_height = initial_params.get('height', {}).get('planted', 1.0)
        
        # Create trees with random variation
        trees = [
            Tree(
                dbh=max(dbh_min, dbh_mean + random.gauss(0, dbh_sd)),
                height=initial_height,
                species=species,
                age=0
            )
            for _ in range(trees_per_acre)
        ]
        
        return cls(trees, site_index, species)
    
    def grow(self, years=5):
        """Grow stand for specified number of years.
        
        Args:
            years: Number of years to grow (default 5 years to match FVS)
        """
        # Ensure years is a multiple of 5
        if years % 5 != 0:
            years = 5 * math.ceil(years / 5)
            
        for period in range(0, years, 5):  # Step in 5-year increments
            # Store initial metrics
            initial_count = len(self.trees)
            initial_metrics = self.get_metrics() if self.trees else None
            
            # Calculate competition metrics
            competition_metrics = self._calculate_competition_metrics()
            
            # Grow each tree
            for tree, metrics in zip(self.trees, competition_metrics):
                tree.grow(
                    site_index=self.site_index,
                    competition_factor=metrics['competition_factor']
                )
            
            # Apply mortality
            mortality_count = self._apply_mortality()
            
            self.age += 5
            
            # Log growth summary
            if initial_metrics and self.trees:
                final_metrics = self.get_metrics()
                dbh_growth = final_metrics['mean_dbh'] - initial_metrics['mean_dbh']
                height_growth = final_metrics['mean_height'] - initial_metrics['mean_height']
                log_growth_summary(self.logger, period // 5 + 1, 
                                 dbh_growth, height_growth, mortality_count)
    
    def _calculate_crown_width(self, tree):
        """Calculate maximum crown width for a tree.
        
        Uses equation from FVS Southern Variant for loblolly pine:
        MCW = a1 + (a2 * DBH) + (a3 * DBH^2)
        """
        p = self.params['crown']
        if tree.dbh >= 5.0:
            return p['a1'] + (p['a2'] * tree.dbh) + (p['a3'] * tree.dbh**2)
        else:
            # Linear interpolation for small trees
            mcw_at_5 = p['a1'] + (p['a2'] * 5.0) + (p['a3'] * 5.0**2)
            return mcw_at_5 * (tree.dbh / 5.0)
    
    def _calculate_ccf(self):
        """Calculate Crown Competition Factor.
        
        CCF is the sum of maximum crown areas divided by stand area,
        expressed as a percentage.
        """
        total_crown_area = 0
        for tree in self.trees:
            crown_width = self._calculate_crown_width(tree)
            crown_area = math.pi * (crown_width / 2)**2
            total_crown_area += crown_area
        
        # Convert to percentage (1 acre = 43560 sq ft)
        return (total_crown_area / 43560) * 100
    
    def _calculate_competition_metrics(self):
        """Calculate competition metrics for each tree using official FVS methods.

        Uses the official CCF calculation (equation 4.5.1) and RELSDI
        (bounded 1.0-12.0) for FVS-accurate competition modeling.

        Returns:
            list: Dictionaries containing competition metrics for each tree
        """
        if len(self.trees) <= 1:
            return [{'competition_factor': 0.0, 'pbal': 0.0, 'relsdi': 1.0}] * len(self.trees)

        # Sort trees by DBH for PBAL calculation
        sorted_trees = sorted(self.trees, key=lambda t: t.dbh)
        tree_to_rank = {tree: rank for rank, tree in enumerate(sorted_trees)}

        # Calculate stand-level metrics using official methods
        stand_ba = self.calculate_basal_area()
        ccf = self.calculate_ccf_official()  # Use official CCF calculation
        relsdi = self.calculate_relsdi()     # Use official RELSDI calculation
        max_sdi = self.get_max_sdi()

        # Calculate mean DBH for relative size calculations
        mean_dbh = sum(t.dbh for t in self.trees) / len(self.trees) if self.trees else 1.0

        # Calculate metrics for each tree
        metrics = []
        for tree in self.trees:
            # Calculate PBAL (basal area in larger trees)
            pbal = self.calculate_pbal(tree)

            # Calculate relative position in diameter distribution
            rank = tree_to_rank[tree] / len(self.trees)

            # Calculate relative height for competition
            # RELHT = tree height / average height of 40 tallest trees
            # Here we approximate with site index as per current implementation
            relht = min(1.5, tree.height / self.site_index) if self.site_index > 0 else 1.0

            # Calculate competition factor combining density and size effects
            # Using FVS-style combination of CCF, PBAL, and relative size
            density_factor = min(0.8, stand_ba / 150.0)  # BA effect
            ccf_factor = min(0.8, ccf / 200.0)          # CCF effect (100 = crowns touching)
            size_factor = min(1.0, tree.dbh / mean_dbh) if mean_dbh > 0 else 0.5

            # Combine factors with weights
            # Larger weight on CCF as it's more accurate now
            competition_factor = min(0.95, 0.35 * density_factor + 0.45 * ccf_factor + 0.2 * (1.0 - size_factor))

            metrics.append({
                'competition_factor': competition_factor,
                'pbal': pbal,
                'rank': rank,
                'relsdi': relsdi,
                'ccf': ccf,
                'relht': relht
            })

        return metrics
    
    def _apply_mortality(self):
        """Apply mortality based on stand density and tree characteristics.
        
        Returns:
            int: Number of trees that died
        """
        if len(self.trees) <= 1:
            return 0
        
        initial_count = len(self.trees)
        
        # Calculate competition metrics
        basal_area = sum(math.pi * (tree.dbh / 24)**2 for tree in self.trees)
        max_sdi = self.params['mortality']['max_sdi']
        relative_density = basal_area / max_sdi
        
        # Get mortality parameters from config
        mortality_params = self.growth_params.get('mortality', {})
        early_params = mortality_params.get('early_mortality', {})
        background_params = mortality_params.get('background_mortality', {})
        
        # Base mortality rate with competition effect
        age_threshold = early_params.get('age_threshold', 5)
        if self.age <= age_threshold:
            mortality_rate = early_params.get('base_rate', 0.25)
        else:
            # Background mortality rate
            base_rate = background_params.get('base_rate', 0.05)
            comp_threshold = background_params.get('competition_threshold', 0.55)
            comp_multiplier = background_params.get('competition_multiplier', 0.1)
            
            competition_mortality = max(0.0, comp_multiplier * (relative_density - comp_threshold))
            mortality_rate = base_rate + competition_mortality
        
        # Calculate mean DBH
        mean_dbh = sum(tree.dbh for tree in self.trees) / len(self.trees)
        
        # Apply mortality
        survivors = []
        for tree in self.trees:
            # Smaller trees have higher mortality
            size_multiplier = mortality_params.get('size_effect', {}).get('multiplier', 0.2)
            size_effect = 1.0 + max(0.0, size_multiplier * (1.0 - tree.dbh / mean_dbh))
            
            # Check survival (adjusted for 5-year period)
            if random.random() > mortality_rate * size_effect:
                survivors.append(tree)
        
        self.trees = survivors
        mortality_count = initial_count - len(survivors)
        return mortality_count
    
    def get_metrics(self) -> Dict[str, Any]:
        """Calculate stand-level metrics using official FVS methods.

        Returns:
            Dictionary containing:
            - age: Stand age in years
            - tpa: Trees per acre
            - mean_dbh: Mean diameter at breast height (inches)
            - qmd: Quadratic mean diameter (inches)
            - mean_height: Mean tree height (feet)
            - basal_area: Stand basal area (sq ft/acre)
            - volume: Total volume (cubic feet)
            - ccf: Crown Competition Factor (official calculation)
            - sdi: Stand Density Index (Reineke's equation)
            - max_sdi: Maximum SDI for stand species composition
            - relsdi: Relative SDI (1.0-12.0 scale)
            - forest_type: FVS forest type group
            - ecounit: Ecological unit code (if set)
        """
        if not self.trees:
            return {
                'age': self.age,
                'tpa': 0,
                'mean_dbh': 0.0,
                'qmd': 0.0,
                'mean_height': 0.0,
                'basal_area': 0.0,
                'volume': 0.0,
                'ccf': 0.0,
                'sdi': 0.0,
                'max_sdi': self.get_max_sdi(),
                'relsdi': 1.0,
                'forest_type': self.forest_type,
                'ecounit': self.ecounit
            }

        n_trees = len(self.trees)
        metrics = {
            'age': self.age,
            'tpa': n_trees,
            'mean_dbh': sum(tree.dbh for tree in self.trees) / n_trees,
            'qmd': self.calculate_qmd(),
            'mean_height': sum(tree.height for tree in self.trees) / n_trees,
            'basal_area': self.calculate_basal_area(),
            'volume': sum(tree.get_volume() for tree in self.trees),
            'ccf': self.calculate_ccf_official(),
            'sdi': self.calculate_stand_sdi(),
            'max_sdi': self.get_max_sdi(),
            'relsdi': self.calculate_relsdi(),
            'forest_type': self.forest_type,
            'ecounit': self.ecounit
        }

        return metrics 
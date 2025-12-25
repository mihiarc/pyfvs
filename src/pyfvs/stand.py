"""
Stand class managing a collection of trees and stand-level dynamics.

This module provides the Stand class which coordinates tree growth, mortality,
harvest operations, and output generation through composition with specialized
component classes.

Implements FVS Southern variant stand-level calculations including:
- Crown Competition Factor (CCF) using official equation 4.5.1
- Stand Density Index (SDI) using Reineke's equation
- Relative SDI (RELSDI) for competition modeling
- Forest type classification for growth modifiers
- Ecological unit classification for regional growth effects
- Harvest tracking (thinning, clearcut) with volume accounting
"""
import math
import random
from pathlib import Path
from typing import List, Optional, Dict, Any

from .tree import Tree
from .config_loader import load_stand_config
from .validation import ParameterValidator
from .logging_config import get_logger

# Import component classes
from .stand_metrics import StandMetricsCalculator
from .mortality import MortalityModel
from .harvest import HarvestManager, HarvestRecord
from .competition import CompetitionCalculator
from .stand_output import StandOutputGenerator, YieldRecord


class Stand:
    """Manages a collection of trees with stand-level dynamics.

    Uses composition to delegate to specialized components:
    - StandMetricsCalculator for all metrics calculations
    - MortalityModel for mortality application
    - HarvestManager for harvest operations
    - CompetitionCalculator for competition metrics
    - StandOutputGenerator for output generation

    Attributes:
        trees: List of Tree objects in the stand
        site_index: Site index (base age 25) in feet
        age: Stand age in years
        species: Default species code
    """

    def __init__(
        self,
        trees: Optional[List[Tree]] = None,
        site_index: float = 70,
        species: str = 'LP',
        forest_type: Optional[str] = None,
        ecounit: Optional[str] = None
    ):
        """Initialize a stand with a list of trees.

        Args:
            trees: List of Tree objects. If None, creates an empty stand.
            site_index: Site index (base age 25) in feet
            species: Default species code for stand parameters
            forest_type: FVS forest type group (e.g., "FTYLPN", "FTLOHD")
            ecounit: Ecological unit code (e.g., "M221", "232")
        """
        self.trees = trees if trees is not None else []

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

        # Set up logging
        self.logger = get_logger(__name__)

        # Load configuration
        self.params = load_stand_config(species)
        self._load_growth_params()

        # Initialize component classes
        self._metrics = StandMetricsCalculator(default_species=species)
        self._mortality = MortalityModel(default_species=species)
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
        if forest_type.upper() not in valid_types:
            self.logger.warning(f"Unknown forest type: {forest_type}. Using as-is.")
        self._forest_type = forest_type.upper()

    def set_ecounit(self, ecounit: str) -> None:
        """Manually set the ecological unit."""
        self.ecounit = ecounit.upper()

    # =========================================================================
    # Stand Metrics - Delegated to StandMetricsCalculator
    # =========================================================================

    def calculate_ccf_official(self) -> float:
        """Calculate Crown Competition Factor using official FVS equation 4.5.1."""
        return self._metrics.calculate_ccf(self.trees)

    def calculate_qmd(self) -> float:
        """Calculate Quadratic Mean Diameter."""
        return self._metrics.calculate_qmd(self.trees)

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
        forest_type: Optional[str] = None
    ):
        """Create a new planted stand.

        Args:
            trees_per_acre: Number of trees per acre to plant
            site_index: Site index (base age 25) in feet
            species: Species code for the plantation
            ecounit: Ecological unit code (e.g., "M231", "232") for regional growth effects
            forest_type: FVS forest type group (e.g., "FTYLPN")

        Returns:
            Stand: New stand instance
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

        # Create temporary stand to access config
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

        return cls(trees, site_index, species, forest_type=forest_type, ecounit=ecounit)

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
        # Store initial metrics
        initial_count = len(self.trees)
        initial_metrics = self.get_metrics() if self.trees else None

        # Update stand age
        self.age += years

        if not self.trees:
            return

        # Calculate stand-level metrics needed for individual tree growth
        ba = self.calculate_basal_area()
        relsdi = self.calculate_relsdi()

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
                forest_type=self.forest_type
            )

        # Apply mortality
        mortality_count = self._apply_mortality(cycle_length=years)

        # Log growth summary
        final_metrics = self.get_metrics()
        self.logger.debug(
            f"Grew {years} years: TPA {initial_count}->{len(self.trees)}, "
            f"mortality={mortality_count}"
        )

    def _apply_mortality(self, cycle_length: int = 5) -> int:
        """Apply mortality using the MortalityModel.

        Args:
            cycle_length: Length of projection cycle in years

        Returns:
            Number of trees that died
        """
        if len(self.trees) <= 1:
            return 0

        max_sdi = self.get_max_sdi()
        result = self._mortality.apply_mortality(
            self.trees,
            cycle_length=cycle_length,
            max_sdi=max_sdi
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
        initial_tpa = len(working_stand.trees)

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

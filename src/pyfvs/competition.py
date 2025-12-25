"""
Competition calculator for FVS-Python.

This module implements competition metric calculations extracted from the Stand class
for improved testability and maintainability.

Competition metrics include:
- Competition factor combining density and size effects
- Point Basal Area in Larger trees (PBAL)
- Relative height (RELHT)
- Forest type and ecological unit effects
"""
import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .tree import Tree
    from .stand_metrics import StandMetricsCalculator


@dataclass
class TreeCompetition:
    """Competition metrics for an individual tree.

    Attributes:
        competition_factor: Combined competition factor (0-1)
        pbal: Point basal area in larger trees (sq ft/acre)
        rank: Relative position in diameter distribution (0-1)
        relsdi: Stand-level relative SDI
        ccf: Stand-level crown competition factor
        relht: Relative height (tree height / dominant height)
    """
    competition_factor: float
    pbal: float
    rank: float
    relsdi: float
    ccf: float
    relht: float


class CompetitionCalculator:
    """Calculator for tree competition metrics.

    Provides competition calculations for individual trees within a stand,
    using stand-level metrics and tree-level position information.

    Attributes:
        metrics_calculator: StandMetricsCalculator for stand-level metrics
        default_species: Default species code
    """

    def __init__(
        self,
        metrics_calculator: Optional['StandMetricsCalculator'] = None,
        default_species: str = 'LP'
    ):
        """Initialize the competition calculator.

        Args:
            metrics_calculator: StandMetricsCalculator for stand metrics
            default_species: Default species code
        """
        self.default_species = default_species

        if metrics_calculator is None:
            from .stand_metrics import StandMetricsCalculator
            self._metrics = StandMetricsCalculator(default_species)
        else:
            self._metrics = metrics_calculator

    def calculate_tree_competition(
        self,
        trees: List['Tree'],
        site_index: float,
        forest_type: Optional[str] = None,
        ecounit: Optional[str] = None
    ) -> List[TreeCompetition]:
        """Calculate competition metrics for each tree in a stand.

        Uses the official CCF calculation (equation 4.5.1) and RELSDI
        (bounded 1.0-12.0) for FVS-accurate competition modeling.

        Args:
            trees: List of Tree objects in the stand
            site_index: Stand site index (used for relative height calculation)
            forest_type: Optional forest type code
            ecounit: Optional ecological unit code

        Returns:
            List of TreeCompetition objects, one per tree
        """
        if not trees:
            return []

        if len(trees) == 1:
            return [TreeCompetition(
                competition_factor=0.0,
                pbal=0.0,
                rank=0.5,
                relsdi=1.0,
                ccf=0.0,
                relht=1.0
            )]

        # Sort trees by DBH for rank calculation
        sorted_trees = sorted(trees, key=lambda t: t.dbh)
        tree_to_rank = {id(tree): rank for rank, tree in enumerate(sorted_trees)}

        # Calculate stand-level metrics
        stand_ba = self._metrics.calculate_basal_area(trees)
        ccf = self._metrics.calculate_ccf(trees)
        relsdi = self._metrics.calculate_relsdi(trees, species=self.default_species)

        # Calculate mean DBH for relative size calculations
        mean_dbh = sum(t.dbh for t in trees) / len(trees)

        # Calculate metrics for each tree
        competition_list = []
        for tree in trees:
            # Calculate PBAL (basal area in larger trees)
            pbal = self._metrics.calculate_pbal(trees, tree)

            # Calculate relative position in diameter distribution
            rank = tree_to_rank[id(tree)] / len(trees)

            # Calculate relative height for competition
            # RELHT = tree height / site_index (approximation)
            relht = min(1.5, tree.height / site_index) if site_index > 0 else 1.0

            # Calculate competition factor combining density and size effects
            density_factor = min(0.8, stand_ba / 150.0)
            ccf_factor = min(0.8, ccf / 200.0)
            size_factor = min(1.0, tree.dbh / mean_dbh) if mean_dbh > 0 else 0.5

            # Combine factors with weights
            competition_factor = min(
                0.95,
                0.35 * density_factor + 0.45 * ccf_factor + 0.2 * (1.0 - size_factor)
            )

            competition_list.append(TreeCompetition(
                competition_factor=competition_factor,
                pbal=pbal,
                rank=rank,
                relsdi=relsdi,
                ccf=ccf,
                relht=relht
            ))

        return competition_list

    def calculate_tree_competition_dicts(
        self,
        trees: List['Tree'],
        site_index: float,
        forest_type: Optional[str] = None,
        ecounit: Optional[str] = None
    ) -> List[Dict[str, float]]:
        """Calculate competition metrics as dictionaries.

        Provides backwards compatibility with the original Stand class
        _calculate_competition_metrics method.

        Args:
            trees: List of Tree objects in the stand
            site_index: Stand site index
            forest_type: Optional forest type code
            ecounit: Optional ecological unit code

        Returns:
            List of dictionaries containing competition metrics
        """
        competitions = self.calculate_tree_competition(
            trees, site_index, forest_type, ecounit
        )

        return [
            {
                'competition_factor': c.competition_factor,
                'pbal': c.pbal,
                'rank': c.rank,
                'relsdi': c.relsdi,
                'ccf': c.ccf,
                'relht': c.relht
            }
            for c in competitions
        ]

    def get_forest_type_effect(self, species_code: str, forest_type: str) -> float:
        """Get forest type growth effect for a species.

        Args:
            species_code: Species code (e.g., "LP", "SP")
            forest_type: FVS forest type code (e.g., "FTYLPN", "FTLOHD")

        Returns:
            Forest type coefficient to add to growth equation
        """
        try:
            from .forest_type import get_forest_type_effect
            return get_forest_type_effect(species_code, forest_type)
        except ImportError:
            return 0.0

    def get_ecounit_effect(self, species_code: str, ecounit: str) -> float:
        """Get ecological unit growth effect for a species.

        Args:
            species_code: Species code (e.g., "LP", "SP")
            ecounit: Ecological unit code (e.g., "M221", "232", "231L")

        Returns:
            Ecological unit coefficient to add to growth equation
        """
        if ecounit is None:
            return 0.0

        try:
            from .ecological_unit import get_ecounit_effect
            return get_ecounit_effect(species_code, ecounit)
        except ImportError:
            return 0.0

    def calculate_relative_height(
        self,
        tree: 'Tree',
        trees: List['Tree'],
        method: str = 'top_height'
    ) -> float:
        """Calculate relative height for a tree.

        Args:
            tree: Target tree
            trees: All trees in the stand
            method: Method for calculating reference height
                   'top_height': Use top height (40 largest trees)
                   'site_index': Use site index
                   'max_height': Use maximum tree height

        Returns:
            Relative height ratio (typically 0.5 - 1.5)
        """
        if not trees or tree.height <= 0:
            return 1.0

        if method == 'top_height':
            reference_height = self._metrics.calculate_top_height(trees)
        elif method == 'max_height':
            reference_height = max(t.height for t in trees)
        else:
            # Default to site_index method - handled by caller
            return 1.0

        if reference_height <= 0:
            return 1.0

        return min(1.5, tree.height / reference_height)

    def calculate_basal_area_percentile(self, tree: 'Tree', trees: List['Tree']) -> float:
        """Calculate a tree's percentile in the basal area distribution.

        This is used in mortality calculations to determine which trees
        are more likely to die (smaller trees have higher mortality).

        Args:
            tree: Target tree
            trees: All trees in the stand

        Returns:
            Basal area percentile (0-100)
        """
        if not trees:
            return 50.0

        # Calculate total basal area and cumulative BA
        total_ba = sum(math.pi * (t.dbh / 24) ** 2 for t in trees)
        if total_ba <= 0:
            return 50.0

        # Sort trees by DBH
        sorted_trees = sorted(trees, key=lambda t: t.dbh)

        cumulative_ba = 0.0
        for t in sorted_trees:
            tree_ba = math.pi * (t.dbh / 24) ** 2
            cumulative_ba += tree_ba
            if id(t) == id(tree):
                return (cumulative_ba / total_ba) * 100.0

        return 50.0


# Module-level convenience functions
_default_calculator: Optional[CompetitionCalculator] = None


def get_competition_calculator(
    metrics_calculator: Optional['StandMetricsCalculator'] = None,
    species: str = 'LP'
) -> CompetitionCalculator:
    """Get or create a competition calculator instance.

    Args:
        metrics_calculator: Optional StandMetricsCalculator
        species: Default species code

    Returns:
        CompetitionCalculator instance
    """
    global _default_calculator
    if _default_calculator is None:
        _default_calculator = CompetitionCalculator(metrics_calculator, species)
    return _default_calculator


def calculate_stand_competition(
    trees: List['Tree'],
    site_index: float = 70.0
) -> List[TreeCompetition]:
    """Calculate competition for all trees in a stand.

    Convenience function using the default calculator.

    Args:
        trees: List of Tree objects
        site_index: Stand site index

    Returns:
        List of TreeCompetition objects
    """
    return get_competition_calculator().calculate_tree_competition(trees, site_index)

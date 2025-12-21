"""
Stand metrics calculator for FVS-Python.

This module provides stand-level metric calculations extracted from the Stand class
to improve testability and maintainability. All calculations follow FVS Southern
variant specifications.

Metrics include:
- Crown Competition Factor (CCF) using equation 4.5.1
- Quadratic Mean Diameter (QMD)
- Basal Area (BA)
- Stand Density Index (SDI) using Reineke's equation
- Relative SDI (RELSDI)
- Top Height
- Point Basal Area in Larger trees (PBAL)
"""
import math
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .tree import Tree


class StandMetricsCalculator:
    """Calculator for stand-level metrics.

    Provides all stand metric calculations in a standalone class that can be
    tested independently and reused across different components.

    Attributes:
        default_species: Default species code for SDI calculations
        _sdi_maximums: Cached SDI maximum values by species
    """

    # Class-level cache for SDI maximums (shared across instances)
    _sdi_maximums: Optional[Dict[str, int]] = None
    _sdi_loaded: bool = False

    def __init__(self, default_species: str = 'LP'):
        """Initialize the metrics calculator.

        Args:
            default_species: Default species code for SDI lookups
        """
        self.default_species = default_species

        # Load SDI maximums if not already loaded
        if not StandMetricsCalculator._sdi_loaded:
            self._load_sdi_maximums()

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

    def calculate_all_metrics(self, trees: List['Tree'], species: str = None) -> Dict[str, float]:
        """Calculate all stand metrics in a single pass for efficiency.

        Args:
            trees: List of Tree objects in the stand
            species: Species code for SDI calculations (uses default if None)

        Returns:
            Dictionary containing all calculated metrics:
            - tpa: Trees per acre
            - ba: Basal area (sq ft/acre)
            - qmd: Quadratic mean diameter (inches)
            - top_height: Average height of 40 largest trees (feet)
            - ccf: Crown Competition Factor
            - sdi: Stand Density Index
            - max_sdi: Maximum SDI for species composition
            - relsdi: Relative SDI (1.0-12.0)
        """
        species = species or self.default_species

        if not trees:
            return {
                'tpa': 0,
                'ba': 0.0,
                'qmd': 0.0,
                'top_height': 0.0,
                'ccf': 0.0,
                'sdi': 0.0,
                'max_sdi': self._sdi_maximums.get(species, 480),
                'relsdi': 1.0
            }

        # Calculate basic metrics in single pass
        n_trees = len(trees)
        sum_dbh_squared = 0.0
        total_ba = 0.0
        species_ba: Dict[str, float] = {}

        for tree in trees:
            dbh = tree.dbh
            tree_species = getattr(tree, 'species', species)

            sum_dbh_squared += dbh ** 2
            ba = math.pi * (dbh / 24.0) ** 2
            total_ba += ba
            species_ba[tree_species] = species_ba.get(tree_species, 0.0) + ba

        # Derived metrics
        qmd = math.sqrt(sum_dbh_squared / n_trees) if n_trees > 0 else 0.0
        sdi = n_trees * ((qmd / 10.0) ** 1.605) if qmd > 0 else 0.0

        # Max SDI (basal area weighted)
        max_sdi = self._calculate_weighted_max_sdi(species_ba, total_ba, species)

        # Relative SDI
        relsdi = (sdi / max_sdi) * 10.0 if max_sdi > 0 else 1.0
        relsdi = max(1.0, min(12.0, relsdi))

        return {
            'tpa': n_trees,
            'ba': total_ba,
            'qmd': qmd,
            'top_height': self.calculate_top_height(trees),
            'ccf': self.calculate_ccf(trees),
            'sdi': sdi,
            'max_sdi': max_sdi,
            'relsdi': relsdi
        }

    def _calculate_weighted_max_sdi(
        self,
        species_ba: Dict[str, float],
        total_ba: float,
        default_species: str
    ) -> float:
        """Calculate basal area-weighted maximum SDI.

        Args:
            species_ba: Dictionary of basal area by species
            total_ba: Total stand basal area
            default_species: Default species if no trees

        Returns:
            Weighted maximum SDI
        """
        if total_ba == 0:
            return self._sdi_maximums.get(default_species, 480)

        weighted_sdi = 0.0
        for species, ba in species_ba.items():
            species_sdi = self._sdi_maximums.get(species, 400)
            weighted_sdi += (ba / total_ba) * species_sdi

        return weighted_sdi

    def calculate_ccf(self, trees: List['Tree']) -> float:
        """Calculate Crown Competition Factor using official FVS equation 4.5.1.

        Uses open-grown crown widths for each tree:
        - CCFt = 0.001803 * OCW² (for DBH > 0.1 inches)
        - CCFt = 0.001 (for DBH ≤ 0.1 inches)
        - Stand CCF = Σ CCFt

        Args:
            trees: List of Tree objects

        Returns:
            Stand-level Crown Competition Factor
        """
        if not trees:
            return 0.0

        try:
            from .crown_width import CrownWidthModel
            use_crown_model = True
        except ImportError:
            use_crown_model = False

        CCF_COEFFICIENT = 0.001803
        SMALL_TREE_CCF = 0.001
        DBH_THRESHOLD = 0.1

        total_ccf = 0.0

        for tree in trees:
            dbh = getattr(tree, 'dbh', 0.0)
            species = getattr(tree, 'species', self.default_species)

            if dbh <= DBH_THRESHOLD:
                total_ccf += SMALL_TREE_CCF
            elif use_crown_model:
                try:
                    model = CrownWidthModel(species)
                    ocw = model.calculate_open_grown_crown_width(dbh)
                    tree_ccf = CCF_COEFFICIENT * (ocw ** 2)
                    total_ccf += tree_ccf
                except Exception:
                    # Fallback: estimate OCW linearly
                    ocw_estimate = 3.0 + 0.15 * dbh
                    total_ccf += CCF_COEFFICIENT * (ocw_estimate ** 2)
            else:
                # Fallback: estimate OCW linearly
                ocw_estimate = 3.0 + 0.15 * dbh
                total_ccf += CCF_COEFFICIENT * (ocw_estimate ** 2)

        return total_ccf

    def calculate_qmd(self, trees: List['Tree']) -> float:
        """Calculate Quadratic Mean Diameter (QMD).

        QMD = sqrt(sum(DBH²) / n)

        Args:
            trees: List of Tree objects

        Returns:
            Quadratic mean diameter in inches
        """
        if not trees:
            return 0.0

        sum_dbh_squared = sum(tree.dbh ** 2 for tree in trees)
        n = len(trees)

        return math.sqrt(sum_dbh_squared / n)

    def calculate_top_height(self, trees: List['Tree'], n_trees: int = 40) -> float:
        """Calculate top height (average height of largest trees by DBH).

        Top height is defined in FVS as the average height of the 40 largest
        (by DBH) trees per acre. This is used in site index calculations and
        as a measure of dominant stand height.

        Args:
            trees: List of Tree objects
            n_trees: Number of largest trees to include (default 40 per FVS standard)

        Returns:
            Top height in feet (average height of n largest trees by DBH)
        """
        if not trees:
            return 0.0

        # Sort trees by DBH descending and take the largest n
        sorted_trees = sorted(trees, key=lambda t: t.dbh, reverse=True)
        top_trees = sorted_trees[:min(n_trees, len(sorted_trees))]

        if not top_trees:
            return 0.0

        return sum(tree.height for tree in top_trees) / len(top_trees)

    def calculate_basal_area(self, trees: List['Tree']) -> float:
        """Calculate stand basal area.

        BA = Σ (π * (DBH/24)²) [sq ft per acre]

        Args:
            trees: List of Tree objects

        Returns:
            Total basal area in square feet per acre
        """
        if not trees:
            return 0.0

        return sum(math.pi * (tree.dbh / 24.0) ** 2 for tree in trees)

    def calculate_sdi(self, trees: List['Tree']) -> float:
        """Calculate Stand Density Index using Reineke's equation.

        SDI = TPA * (QMD / 10)^1.605

        Args:
            trees: List of Tree objects

        Returns:
            Stand Density Index
        """
        if not trees:
            return 0.0

        tpa = len(trees)
        qmd = self.calculate_qmd(trees)

        if qmd <= 0:
            return 0.0

        return tpa * ((qmd / 10.0) ** 1.605)

    def calculate_relsdi(self, trees: List['Tree'], species: str = None) -> float:
        """Calculate Relative Stand Density Index (RELSDI).

        RELSDI = (Stand_SDI / Max_SDI) * 10
        Bounded between 1.0 and 12.0 per FVS specification.

        Args:
            trees: List of Tree objects
            species: Species code for SDI max lookup

        Returns:
            Relative SDI value (1.0-12.0)
        """
        species = species or self.default_species

        stand_sdi = self.calculate_sdi(trees)
        max_sdi = self.get_max_sdi(trees, species)

        if max_sdi <= 0:
            return 1.0

        relsdi = (stand_sdi / max_sdi) * 10.0

        # Apply FVS bounds
        return max(1.0, min(12.0, relsdi))

    def get_max_sdi(self, trees: List['Tree'], default_species: str = None) -> float:
        """Get maximum SDI for the stand based on species composition.

        Uses basal area-weighted average of species-specific SDI maximums.

        Args:
            trees: List of Tree objects
            default_species: Species to use if no trees

        Returns:
            Maximum SDI for the stand
        """
        default_species = default_species or self.default_species

        if not trees:
            return self._sdi_maximums.get(default_species, 480)

        # Calculate basal area by species
        species_ba: Dict[str, float] = {}
        total_ba = 0.0

        for tree in trees:
            species = getattr(tree, 'species', default_species)
            ba = math.pi * (tree.dbh / 24.0) ** 2
            species_ba[species] = species_ba.get(species, 0.0) + ba
            total_ba += ba

        return self._calculate_weighted_max_sdi(species_ba, total_ba, default_species)

    def calculate_pbal(self, trees: List['Tree'], target_tree: 'Tree') -> float:
        """Calculate Point Basal Area in Larger trees (PBAL).

        PBAL is the basal area of trees with DBH larger than the target tree.

        Args:
            trees: List of all Tree objects in the stand
            target_tree: Tree to calculate PBAL for

        Returns:
            PBAL in square feet per acre
        """
        target_dbh = target_tree.dbh
        pbal = sum(
            math.pi * (tree.dbh / 24.0) ** 2
            for tree in trees
            if tree.dbh > target_dbh
        )
        return pbal


# Module-level convenience functions for backwards compatibility
_default_calculator: Optional[StandMetricsCalculator] = None


def get_metrics_calculator(species: str = 'LP') -> StandMetricsCalculator:
    """Get or create a metrics calculator instance.

    Args:
        species: Default species code

    Returns:
        StandMetricsCalculator instance
    """
    global _default_calculator
    if _default_calculator is None:
        _default_calculator = StandMetricsCalculator(species)
    return _default_calculator


def calculate_stand_ccf(trees: List['Tree']) -> float:
    """Calculate CCF for a list of trees.

    Convenience function that uses the default calculator.

    Args:
        trees: List of Tree objects

    Returns:
        Crown Competition Factor
    """
    return get_metrics_calculator().calculate_ccf(trees)


def calculate_stand_sdi(trees: List['Tree']) -> float:
    """Calculate SDI for a list of trees.

    Convenience function that uses the default calculator.

    Args:
        trees: List of Tree objects

    Returns:
        Stand Density Index
    """
    return get_metrics_calculator().calculate_sdi(trees)


def calculate_stand_basal_area(trees: List['Tree']) -> float:
    """Calculate basal area for a list of trees.

    Convenience function that uses the default calculator.

    Args:
        trees: List of Tree objects

    Returns:
        Basal area in sq ft/acre
    """
    return get_metrics_calculator().calculate_basal_area(trees)

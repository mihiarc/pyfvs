"""
Harvest management for FVS-Python.

This module implements harvest operations extracted from the Stand class
for improved testability and maintainability.

Harvest operations include:
- Thin from below (remove smallest trees first)
- Thin from above (remove largest trees first)
- Thin by DBH range (remove trees within DBH range)
- Clearcut (remove all trees)
- Selection harvest (targeted basal area reduction)
"""
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .tree import Tree


@dataclass
class HarvestRecord:
    """Record of a single harvest event following FVS output format.

    Attributes:
        year: Stand age at time of harvest
        harvest_type: Type of harvest ('thin_from_below', 'thin_from_above',
                     'thin_by_dbh', 'clearcut', 'selection')
        trees_removed: Number of trees removed per acre
        basal_area_removed: Basal area removed (sq ft/acre)
        volume_removed: Total cubic volume removed (cu ft/acre)
        merchantable_volume_removed: Merchantable cubic volume removed (cu ft/acre)
        board_feet_removed: Board foot volume removed (bf/acre, Doyle scale)
        mean_dbh_removed: Mean DBH of removed trees (inches)
        residual_tpa: Trees per acre after harvest
        residual_ba: Basal area after harvest (sq ft/acre)
        target_ba: Target basal area (if applicable)
        target_tpa: Target TPA (if applicable)
        min_dbh: Minimum DBH cut (for thin_by_dbh)
        max_dbh: Maximum DBH cut (for thin_by_dbh)
        proportion: Proportion removed (for thin_by_dbh)
    """
    year: int
    harvest_type: str
    trees_removed: int
    basal_area_removed: float
    volume_removed: float
    merchantable_volume_removed: float
    board_feet_removed: float
    mean_dbh_removed: float
    residual_tpa: int
    residual_ba: float
    target_ba: Optional[float] = None
    target_tpa: Optional[int] = None
    min_dbh: Optional[float] = None
    max_dbh: Optional[float] = None
    proportion: Optional[float] = None


@dataclass
class HarvestResult:
    """Result of a harvest operation.

    Attributes:
        remaining_trees: List of trees after harvest
        removed_trees: List of trees that were removed
        record: HarvestRecord with details
    """
    remaining_trees: List['Tree']
    removed_trees: List['Tree']
    record: HarvestRecord


class HarvestManager:
    """Manager for forest harvest operations.

    Provides methods for various harvest types and tracks harvest history.
    This class is stateless regarding trees - it operates on provided tree
    lists and returns results. The caller is responsible for updating
    their tree collection.

    Attributes:
        harvest_history: List of all harvest records
    """

    def __init__(self):
        """Initialize the harvest manager."""
        self.harvest_history: List[HarvestRecord] = []

    def _calculate_basal_area(self, trees: List['Tree']) -> float:
        """Calculate total basal area for a list of trees.

        Args:
            trees: List of trees

        Returns:
            Basal area in square feet per acre
        """
        if not trees:
            return 0.0
        return sum(math.pi * (tree.dbh / 24.0) ** 2 for tree in trees)

    def _create_harvest_record(
        self,
        removed_trees: List['Tree'],
        remaining_trees: List['Tree'],
        harvest_type: str,
        stand_age: int,
        target_ba: Optional[float] = None,
        target_tpa: Optional[int] = None,
        min_dbh: Optional[float] = None,
        max_dbh: Optional[float] = None,
        proportion: Optional[float] = None
    ) -> HarvestRecord:
        """Create a harvest record.

        Args:
            removed_trees: List of trees that were removed
            remaining_trees: List of trees that remain
            harvest_type: Type of harvest operation
            stand_age: Current stand age
            target_ba: Target basal area (if applicable)
            target_tpa: Target TPA (if applicable)
            min_dbh: Minimum DBH for thin_by_dbh
            max_dbh: Maximum DBH for thin_by_dbh
            proportion: Proportion removed for thin_by_dbh

        Returns:
            HarvestRecord with all harvest details
        """
        residual_ba = self._calculate_basal_area(remaining_trees)

        if not removed_trees:
            return HarvestRecord(
                year=stand_age,
                harvest_type=harvest_type,
                trees_removed=0,
                basal_area_removed=0.0,
                volume_removed=0.0,
                merchantable_volume_removed=0.0,
                board_feet_removed=0.0,
                mean_dbh_removed=0.0,
                residual_tpa=len(remaining_trees),
                residual_ba=residual_ba,
                target_ba=target_ba,
                target_tpa=target_tpa,
                min_dbh=min_dbh,
                max_dbh=max_dbh,
                proportion=proportion
            )

        # Calculate removed volumes
        volume_removed = sum(t.get_volume('total_cubic') for t in removed_trees)
        merch_volume_removed = sum(t.get_volume('merchantable_cubic') for t in removed_trees)
        bf_removed = sum(t.get_volume('board_foot') for t in removed_trees)

        # Calculate removed basal area
        ba_removed = self._calculate_basal_area(removed_trees)

        # Mean DBH of removed trees
        mean_dbh_removed = sum(t.dbh for t in removed_trees) / len(removed_trees)

        return HarvestRecord(
            year=stand_age,
            harvest_type=harvest_type,
            trees_removed=len(removed_trees),
            basal_area_removed=ba_removed,
            volume_removed=volume_removed,
            merchantable_volume_removed=merch_volume_removed,
            board_feet_removed=bf_removed,
            mean_dbh_removed=mean_dbh_removed,
            residual_tpa=len(remaining_trees),
            residual_ba=residual_ba,
            target_ba=target_ba,
            target_tpa=target_tpa,
            min_dbh=min_dbh,
            max_dbh=max_dbh,
            proportion=proportion
        )

    def thin_from_below(
        self,
        trees: List['Tree'],
        stand_age: int,
        target_ba: Optional[float] = None,
        target_tpa: Optional[int] = None
    ) -> HarvestResult:
        """Thin stand from below (remove smallest trees first).

        Removes trees starting with the smallest DBH until the target
        basal area or TPA is reached. This is similar to FVS THINBA
        with thinning from below.

        Args:
            trees: List of trees in the stand
            stand_age: Current stand age
            target_ba: Target residual basal area (sq ft/acre)
            target_tpa: Target residual trees per acre

        Returns:
            HarvestResult with remaining trees and harvest details

        Raises:
            ValueError: If neither target_ba nor target_tpa is specified

        Example:
            >>> result = manager.thin_from_below(trees, 20, target_ba=80)
        """
        if target_ba is None and target_tpa is None:
            raise ValueError("Must specify either target_ba or target_tpa")

        if not trees:
            record = self._create_harvest_record(
                [], [], 'thin_from_below', stand_age,
                target_ba=target_ba, target_tpa=target_tpa
            )
            self.harvest_history.append(record)
            return HarvestResult(remaining_trees=[], removed_trees=[], record=record)

        # Sort trees by DBH ascending (smallest first)
        sorted_trees = sorted(trees, key=lambda t: t.dbh)

        removed_trees = []
        remaining_trees = []

        current_ba = self._calculate_basal_area(trees)
        current_tpa = len(trees)

        for tree in sorted_trees:
            # Check if we've reached target
            reached_target = False

            if target_ba is not None and current_ba <= target_ba:
                reached_target = True
            if target_tpa is not None and current_tpa <= target_tpa:
                reached_target = True

            if reached_target:
                remaining_trees.append(tree)
            else:
                # Remove this tree
                removed_trees.append(tree)
                tree_ba = math.pi * (tree.dbh / 24) ** 2
                current_ba -= tree_ba
                current_tpa -= 1

        record = self._create_harvest_record(
            removed_trees, remaining_trees, 'thin_from_below', stand_age,
            target_ba=target_ba, target_tpa=target_tpa
        )
        self.harvest_history.append(record)
        return HarvestResult(
            remaining_trees=remaining_trees,
            removed_trees=removed_trees,
            record=record
        )

    def thin_from_above(
        self,
        trees: List['Tree'],
        stand_age: int,
        target_ba: Optional[float] = None,
        target_tpa: Optional[int] = None
    ) -> HarvestResult:
        """Thin stand from above (remove largest trees first).

        Removes trees starting with the largest DBH until the target
        basal area or TPA is reached. This simulates high-grading or
        selective harvest of the best trees.

        Args:
            trees: List of trees in the stand
            stand_age: Current stand age
            target_ba: Target residual basal area (sq ft/acre)
            target_tpa: Target residual trees per acre

        Returns:
            HarvestResult with remaining trees and harvest details

        Raises:
            ValueError: If neither target_ba nor target_tpa is specified
        """
        if target_ba is None and target_tpa is None:
            raise ValueError("Must specify either target_ba or target_tpa")

        if not trees:
            record = self._create_harvest_record(
                [], [], 'thin_from_above', stand_age,
                target_ba=target_ba, target_tpa=target_tpa
            )
            self.harvest_history.append(record)
            return HarvestResult(remaining_trees=[], removed_trees=[], record=record)

        # Sort trees by DBH descending (largest first)
        sorted_trees = sorted(trees, key=lambda t: t.dbh, reverse=True)

        removed_trees = []
        remaining_trees = []

        current_ba = self._calculate_basal_area(trees)
        current_tpa = len(trees)

        for tree in sorted_trees:
            # Check if we've reached target
            reached_target = False

            if target_ba is not None and current_ba <= target_ba:
                reached_target = True
            if target_tpa is not None and current_tpa <= target_tpa:
                reached_target = True

            if reached_target:
                remaining_trees.append(tree)
            else:
                # Remove this tree
                removed_trees.append(tree)
                tree_ba = math.pi * (tree.dbh / 24) ** 2
                current_ba -= tree_ba
                current_tpa -= 1

        record = self._create_harvest_record(
            removed_trees, remaining_trees, 'thin_from_above', stand_age,
            target_ba=target_ba, target_tpa=target_tpa
        )
        self.harvest_history.append(record)
        return HarvestResult(
            remaining_trees=remaining_trees,
            removed_trees=removed_trees,
            record=record
        )

    def thin_by_dbh_range(
        self,
        trees: List['Tree'],
        stand_age: int,
        min_dbh: float,
        max_dbh: float,
        proportion: float = 1.0
    ) -> HarvestResult:
        """Thin trees within a DBH range.

        Similar to FVS THINDBH keyword. Removes a proportion of trees
        within the specified DBH range.

        Args:
            trees: List of trees in the stand
            stand_age: Current stand age
            min_dbh: Minimum DBH to include (inches)
            max_dbh: Maximum DBH to include (inches)
            proportion: Proportion of trees in range to remove (0.0-1.0)

        Returns:
            HarvestResult with remaining trees and harvest details

        Raises:
            ValueError: If min_dbh >= max_dbh or proportion out of range

        Example:
            >>> result = manager.thin_by_dbh_range(trees, 20, 4, 8, 0.5)
        """
        if min_dbh >= max_dbh:
            raise ValueError(f"min_dbh ({min_dbh}) must be less than max_dbh ({max_dbh})")
        if not 0.0 <= proportion <= 1.0:
            raise ValueError(f"proportion must be between 0 and 1, got {proportion}")

        if not trees:
            record = self._create_harvest_record(
                [], [], 'thin_by_dbh', stand_age,
                min_dbh=min_dbh, max_dbh=max_dbh, proportion=proportion
            )
            self.harvest_history.append(record)
            return HarvestResult(remaining_trees=[], removed_trees=[], record=record)

        # Separate trees into those in range and those outside
        in_range = [t for t in trees if min_dbh <= t.dbh <= max_dbh]
        outside_range = [t for t in trees if not (min_dbh <= t.dbh <= max_dbh)]

        # Determine how many to remove from in_range
        n_to_remove = int(len(in_range) * proportion)

        # Randomly select trees to remove (or could sort by DBH)
        if n_to_remove > 0:
            # Sort by DBH and remove smallest first within range
            in_range_sorted = sorted(in_range, key=lambda t: t.dbh)
            removed_trees = in_range_sorted[:n_to_remove]
            kept_in_range = in_range_sorted[n_to_remove:]
        else:
            removed_trees = []
            kept_in_range = in_range

        remaining_trees = outside_range + kept_in_range

        record = self._create_harvest_record(
            removed_trees, remaining_trees, 'thin_by_dbh', stand_age,
            min_dbh=min_dbh, max_dbh=max_dbh, proportion=proportion
        )
        self.harvest_history.append(record)
        return HarvestResult(
            remaining_trees=remaining_trees,
            removed_trees=removed_trees,
            record=record
        )

    def clearcut(
        self,
        trees: List['Tree'],
        stand_age: int
    ) -> HarvestResult:
        """Remove all trees from the stand (clearcut harvest).

        Args:
            trees: List of trees in the stand
            stand_age: Current stand age

        Returns:
            HarvestResult with harvest details for all removed trees
        """
        removed_trees = list(trees)
        remaining_trees = []

        record = self._create_harvest_record(
            removed_trees, remaining_trees, 'clearcut', stand_age
        )
        self.harvest_history.append(record)
        return HarvestResult(
            remaining_trees=remaining_trees,
            removed_trees=removed_trees,
            record=record
        )

    def selection_harvest(
        self,
        trees: List['Tree'],
        stand_age: int,
        target_ba: float,
        min_dbh: float = 0.0
    ) -> HarvestResult:
        """Perform a selection harvest targeting specific basal area.

        Removes trees across the diameter distribution to achieve
        target residual basal area, prioritizing removal of trees
        above minimum DBH. This is a simplified selection system.

        Args:
            trees: List of trees in the stand
            stand_age: Current stand age
            target_ba: Target residual basal area (sq ft/acre)
            min_dbh: Minimum DBH to consider for removal (inches)

        Returns:
            HarvestResult with harvest details
        """
        if not trees:
            record = self._create_harvest_record(
                [], [], 'selection', stand_age, target_ba=target_ba
            )
            self.harvest_history.append(record)
            return HarvestResult(remaining_trees=[], removed_trees=[], record=record)

        current_ba = self._calculate_basal_area(trees)
        if current_ba <= target_ba:
            record = self._create_harvest_record(
                [], list(trees), 'selection', stand_age, target_ba=target_ba
            )
            self.harvest_history.append(record)
            return HarvestResult(
                remaining_trees=list(trees),
                removed_trees=[],
                record=record
            )

        # Sort by DBH descending, but only consider trees >= min_dbh
        eligible = [(i, t) for i, t in enumerate(trees) if t.dbh >= min_dbh]
        eligible_sorted = sorted(eligible, key=lambda x: x[1].dbh, reverse=True)

        removed_indices = set()
        removed_trees = []

        for idx, tree in eligible_sorted:
            if current_ba <= target_ba:
                break

            tree_ba = math.pi * (tree.dbh / 24) ** 2
            removed_indices.add(idx)
            removed_trees.append(tree)
            current_ba -= tree_ba

        # Keep trees not in removed set
        remaining_trees = [t for i, t in enumerate(trees) if i not in removed_indices]

        record = self._create_harvest_record(
            removed_trees, remaining_trees, 'selection', stand_age,
            target_ba=target_ba
        )
        self.harvest_history.append(record)
        return HarvestResult(
            remaining_trees=remaining_trees,
            removed_trees=removed_trees,
            record=record
        )

    def get_harvest_summary(self) -> Dict[str, Any]:
        """Get cumulative harvest summary across all harvest events.

        Returns:
            Dictionary containing:
            - total_harvests: Number of harvest events
            - total_trees_removed: Cumulative trees removed
            - total_volume_removed: Cumulative cubic volume removed
            - total_merchantable_removed: Cumulative merchantable cubic removed
            - total_board_feet_removed: Cumulative board feet removed
            - total_ba_removed: Cumulative basal area removed
            - harvest_history: List of individual harvest records as dicts
        """
        if not self.harvest_history:
            return {
                'total_harvests': 0,
                'total_trees_removed': 0,
                'total_volume_removed': 0.0,
                'total_merchantable_removed': 0.0,
                'total_board_feet_removed': 0.0,
                'total_ba_removed': 0.0,
                'harvest_history': []
            }

        return {
            'total_harvests': len(self.harvest_history),
            'total_trees_removed': sum(h.trees_removed for h in self.harvest_history),
            'total_volume_removed': sum(h.volume_removed for h in self.harvest_history),
            'total_merchantable_removed': sum(
                h.merchantable_volume_removed for h in self.harvest_history
            ),
            'total_board_feet_removed': sum(h.board_feet_removed for h in self.harvest_history),
            'total_ba_removed': sum(h.basal_area_removed for h in self.harvest_history),
            'harvest_history': [
                {
                    'year': h.year,
                    'harvest_type': h.harvest_type,
                    'trees_removed': h.trees_removed,
                    'basal_area_removed': h.basal_area_removed,
                    'volume_removed': h.volume_removed,
                    'merchantable_volume_removed': h.merchantable_volume_removed,
                    'board_feet_removed': h.board_feet_removed,
                    'mean_dbh_removed': h.mean_dbh_removed,
                    'residual_tpa': h.residual_tpa,
                    'residual_ba': h.residual_ba
                }
                for h in self.harvest_history
            ]
        }

    def get_last_harvest(self) -> Optional[HarvestRecord]:
        """Get the most recent harvest record.

        Returns:
            Most recent HarvestRecord or None if no harvests
        """
        if self.harvest_history:
            return self.harvest_history[-1]
        return None

    def clear_history(self) -> None:
        """Clear all harvest history."""
        self.harvest_history = []


# Module-level convenience functions
_default_manager: Optional[HarvestManager] = None


def get_harvest_manager() -> HarvestManager:
    """Get or create a harvest manager instance.

    Returns:
        HarvestManager instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = HarvestManager()
    return _default_manager


def thin_stand_from_below(
    trees: List['Tree'],
    stand_age: int,
    target_ba: Optional[float] = None,
    target_tpa: Optional[int] = None
) -> HarvestResult:
    """Thin a stand from below using the default manager.

    Args:
        trees: List of trees
        stand_age: Current stand age
        target_ba: Target residual basal area
        target_tpa: Target residual TPA

    Returns:
        HarvestResult
    """
    return get_harvest_manager().thin_from_below(
        trees, stand_age, target_ba=target_ba, target_tpa=target_tpa
    )

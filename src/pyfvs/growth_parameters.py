"""
GrowthParameters dataclass for encapsulating tree growth model inputs.

This module provides a dataclass that bundles all the parameters needed for
the Tree.grow() method, reducing the number of individual parameters from 11
to a single object. This improves code readability and makes it easier to
pass growth context between Stand and Tree objects.
"""
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .stand import Stand

__all__ = ['GrowthParameters']


@dataclass
class GrowthParameters:
    """Parameters for tree growth simulation.

    This dataclass encapsulates all environmental and competition parameters
    needed by the Tree.grow() method. It provides sensible defaults matching
    the original method signature and includes a factory method to create
    parameters directly from a Stand object.

    Attributes:
        site_index: Site index (base age 25) in feet. Represents the expected
            height of dominant trees at age 25. Higher values indicate more
            productive sites. Default: 70 feet (typical for loblolly pine).

        competition_factor: Competition factor ranging from 0 (no competition)
            to 1 (maximum competition). Derived from crown competition factor
            or stand density metrics. Default: 0.0.

        rank: Tree's rank in the diameter distribution, ranging from 0 (smallest)
            to 1 (largest). Used in crown ratio calculations. Default: 0.5
            (median tree).

        relsdi: Relative Stand Density Index on a 1-12 scale. Values above 6
            indicate high competition. Used in crown ratio updates.
            Default: 5.0 (moderate density).

        ba: Stand basal area in square feet per acre. Total cross-sectional
            area of all trees at breast height. Used in the large-tree diameter
            growth equation. Default: 100 sq ft/acre.

        pbal: Point Basal Area in Larger trees (sq ft/acre). The basal area
            of trees larger than the subject tree. Represents asymmetric
            competition (one-sided). Default: 50 sq ft/acre.

        slope: Ground slope as a proportion (rise/run). Used in topographic
            adjustments to growth. Default: 0.05 (5% slope).

        aspect: Aspect in radians (0 = North, pi/2 = East, pi = South,
            3*pi/2 = West). Used with slope for topographic effects.
            Default: 0.0 (north-facing).

        time_step: Number of years to simulate growth. The FVS model was
            calibrated for 5-year cycles. Default: 5 years.

        ecounit: Ecological unit code (e.g., "232", "M231", "255"). Affects
            diameter growth through regional productivity adjustments.
            M231 (Mountain) provides ~2.2x boost vs base 232 (Georgia).
            Default: None (uses species config base).

        forest_type: FVS forest type group (e.g., "FTYLPN", "FTLOHD").
            Affects diameter growth through stand composition effects.
            Default: None (uses species config base).

    Example:
        >>> from pyfvs.growth_parameters import GrowthParameters
        >>> from pyfvs import Tree
        >>>
        >>> # Create with defaults
        >>> params = GrowthParameters(site_index=70)
        >>> tree = Tree(dbh=5.0, height=30.0, species='LP', age=10)
        >>> tree.grow(params)
        >>>
        >>> # Create with all parameters
        >>> params = GrowthParameters(
        ...     site_index=65,
        ...     competition_factor=0.3,
        ...     ba=120,
        ...     pbal=40,
        ...     ecounit='M231'
        ... )
        >>> tree.grow(params)
        >>>
        >>> # Create from a Stand object
        >>> from pyfvs import Stand
        >>> stand = Stand.initialize_planted(500, site_index=70, species='LP')
        >>> params = GrowthParameters.from_stand(stand)
    """

    site_index: float = 70.0
    competition_factor: float = 0.0
    rank: float = 0.5
    relsdi: float = 5.0
    ba: float = 100.0
    pbal: float = 50.0
    slope: float = 0.05
    aspect: float = 0.0
    time_step: int = 5
    ecounit: Optional[str] = None
    forest_type: Optional[str] = None

    @classmethod
    def from_stand(
        cls,
        stand: 'Stand',
        target_tree_index: Optional[int] = None,
        time_step: int = 5
    ) -> 'GrowthParameters':
        """Create GrowthParameters from a Stand object.

        This factory method extracts all relevant metrics from a Stand to
        create growth parameters suitable for tree-level simulation. If a
        target tree index is provided, tree-specific competition metrics
        (rank, pbal) are calculated for that tree.

        Args:
            stand: The Stand object to extract parameters from.
            target_tree_index: Optional index of the target tree in stand.trees.
                If provided, calculates tree-specific competition metrics.
                If None, uses stand-average values.
            time_step: Number of years for growth simulation. Default: 5.

        Returns:
            GrowthParameters: A new instance populated with stand metrics.

        Example:
            >>> stand = Stand.initialize_planted(500, site_index=70, species='LP')
            >>> stand.grow(years=10)
            >>>
            >>> # Get parameters for the stand (average values)
            >>> params = GrowthParameters.from_stand(stand)
            >>>
            >>> # Get parameters for a specific tree
            >>> params = GrowthParameters.from_stand(stand, target_tree_index=0)
        """
        # Calculate stand-level metrics
        ba = stand.calculate_basal_area()
        relsdi = stand.calculate_relsdi()
        ccf = stand.calculate_ccf_official()

        # Competition factor from CCF (normalized to 0-1 range)
        # CCF of 100 is "full site occupancy", higher values mean more competition
        competition_factor = min(1.0, max(0.0, (ccf - 100) / 200))

        # Default tree-specific values
        rank = 0.5
        pbal = ba / 2.0  # Default to half of BA

        # Calculate tree-specific metrics if target tree provided
        if target_tree_index is not None and stand.trees:
            if 0 <= target_tree_index < len(stand.trees):
                target_tree = stand.trees[target_tree_index]

                # Calculate PBAL for target tree
                pbal = stand.calculate_pbal(target_tree)

                # Calculate rank (proportion of trees smaller than target)
                target_dbh = target_tree.dbh
                smaller_count = sum(1 for t in stand.trees if t.dbh < target_dbh)
                rank = smaller_count / len(stand.trees)

        return cls(
            site_index=stand.site_index,
            competition_factor=competition_factor,
            rank=rank,
            relsdi=relsdi,
            ba=ba,
            pbal=pbal,
            slope=0.0,  # Stand doesn't track topography currently
            aspect=0.0,
            time_step=time_step,
            ecounit=stand.ecounit,
            forest_type=stand.forest_type
        )

"""
Tree utility functions for FVS-Python.

Provides common calculations used across multiple modules to avoid duplication
and ensure consistency.
"""
import math
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .tree import Tree


# Basal area constant: pi / 576 (converts DBH in inches to BA in square feet)
# Formula: BA = pi * (DBH/24)^2 = pi * DBH^2 / 576
BASAL_AREA_FACTOR = math.pi / 576.0  # Approximately 0.005454


def calculate_tree_basal_area(dbh: float) -> float:
    """Calculate basal area for a single tree.

    Basal area is the cross-sectional area of a tree at breast height (4.5 feet).
    Formula: BA = pi * (DBH/24)^2 = pi * DBH^2 / 576

    Args:
        dbh: Diameter at breast height in inches

    Returns:
        Basal area in square feet
    """
    return BASAL_AREA_FACTOR * dbh * dbh


def calculate_stand_basal_area(trees: List['Tree']) -> float:
    """Calculate total basal area for a collection of trees.

    Args:
        trees: List of Tree objects with dbh attribute

    Returns:
        Total basal area in square feet per acre
    """
    return sum(calculate_tree_basal_area(t.dbh) for t in trees)

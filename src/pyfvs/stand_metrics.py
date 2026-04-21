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
import logging
import math
from typing import List, Dict, Optional, TYPE_CHECKING

from .config_loader import load_coefficient_file

logger = logging.getLogger(__name__)
from .tree_utils import calculate_tree_basal_area, calculate_stand_basal_area

if TYPE_CHECKING:
    from .tree import Tree

__all__ = [
    'StandMetricsCalculator',
    'get_metrics_calculator',
    'calculate_stand_ccf',
    'calculate_stand_sdi',
]


class StandMetricsCalculator:
    """Calculator for stand-level metrics.

    Provides all stand metric calculations in a standalone class that can be
    tested independently and reused across different components.

    Attributes:
        default_species: Default species code for SDI calculations
        variant: FVS variant code ('SN', 'LS', etc.)
        _sdi_maximums: Cached SDI maximum values by species
    """

    # Class-level cache for SDI maximums, keyed by variant
    _sdi_cache: Dict[str, Dict[str, int]] = {}

    # LS SDI maximums from FVS LS variant documentation
    LS_SDI_MAXIMUMS = {
        'JP': 400, 'SC': 400, 'RN': 500, 'RP': 500, 'WP': 450,
        'WS': 500, 'NS': 500, 'BF': 400, 'BS': 400, 'TA': 350,
        'WC': 400, 'EH': 500, 'OS': 400, 'RC': 400,
        'BA': 350, 'GA': 400, 'EC': 300, 'SV': 400, 'RM': 400,
        'BC': 400, 'AE': 350, 'RL': 400, 'RE': 350, 'YB': 400,
        'BW': 300, 'SM': 450, 'BM': 450, 'AB': 450, 'WA': 350,
        'WO': 400, 'SW': 400, 'BR': 400, 'CK': 400,
        'RO': 400, 'BO': 400, 'NP': 500, 'BH': 400, 'PH': 400,
        'SH': 400, 'BT': 350, 'QA': 350, 'BP': 300, 'PB': 350,
        'BN': 350, 'WN': 400, 'HH': 400, 'BK': 350, 'OH': 350,
    }

    # PN SDI maximums derived from ecocls.f typical eco-class values
    PN_SDI_MAXIMUMS = {
        'SF': 1000, 'WF': 700, 'GF': 700, 'AF': 550, 'RF': 700,
        'SS': 800, 'NF': 700, 'YC': 600, 'IC': 500, 'ES': 550,
        'LP': 450, 'JP': 450, 'SP': 550, 'WP': 550, 'PP': 450,
        'DF': 850, 'RW': 950, 'RC': 850, 'WH': 900, 'MH': 600,
        'BM': 500, 'RA': 700, 'WA': 500, 'PB': 400, 'GC': 500,
        'AS': 400, 'CW': 500, 'WO': 500, 'WJ': 300, 'LL': 400,
        'WL': 280, 'VN': 400, 'SH': 500,  # EC additions (WL: ec/ecocls.f GBA-derived)
        'WB': 400, 'KP': 400, 'PY': 350, 'DG': 400, 'HT': 350,
        'CH': 400, 'WI': 350, 'OT': 500, 'PL': 400, 'OS': 500,
        'OH': 400,
    }

    # NE SDI maximums for Northeast variant - from NE-TWIGS documentation
    # and FVS NE variant ecocls.f
    NE_SDI_MAXIMUMS = {
        # Conifers
        'BF': 400, 'TA': 350, 'WS': 500, 'RS': 450, 'NS': 450,
        'BS': 400, 'PI': 400, 'RN': 500, 'WP': 450, 'LP': 450,
        'VP': 350, 'OP': 400, 'JP': 400, 'SP': 400, 'TM': 350,
        'PP': 350, 'PD': 350, 'SC': 400, 'WC': 400, 'AW': 350,
        'RC': 350, 'JU': 350, 'EH': 500, 'HM': 450, 'OS': 400,
        # Hardwoods - Maples
        'RM': 400, 'SM': 450, 'BM': 450, 'SV': 400, 'BE': 350, 'ST': 350,
        # Hardwoods - Birches
        'YB': 400, 'SB': 400, 'RB': 350, 'PB': 350, 'GB': 300, 'WR': 300,
        # Hardwoods - Hickories
        'HI': 400, 'PH': 400, 'SL': 400, 'SH': 400, 'MH': 400,
        # Hardwoods - Beech
        'AB': 450,
        # Hardwoods - Ashes
        'AS': 350, 'WA': 350, 'BA': 350, 'GA': 400, 'PA': 350,
        # Hardwoods - Poplars/Tulip
        'YP': 450, 'SU': 400, 'CT': 400, 'QA': 350, 'BP': 300,
        'EC': 300, 'BT': 350, 'PY': 300,
        # Hardwoods - Cherry
        'BC': 400,
        # Hardwoods - White Oaks
        'WO': 400, 'BR': 400, 'CK': 400, 'PO': 350, 'SW': 400,
        'SN': 400, 'CO': 400,
        # Hardwoods - Red Oaks
        'OK': 400, 'SO': 400, 'QI': 350, 'WK': 350, 'PN': 400,
        'RO': 400, 'SK': 400, 'BO': 400, 'CB': 400, 'WL': 400,
        # Hardwoods - Other
        'BU': 350, 'YY': 350, 'HK': 350, 'PS': 300, 'HY': 300,
        'BN': 350, 'WN': 400, 'OO': 300, 'MG': 400, 'MV': 400,
        'AP': 300, 'WT': 350, 'BG': 350, 'SD': 300, 'PW': 300,
        'SY': 400, 'BK': 350, 'BL': 300, 'SS': 300, 'BW': 400,
        'WB': 400, 'EL': 350, 'AE': 350, 'RL': 350, 'OH': 350,
        'AI': 300, 'SE': 300, 'AH': 350, 'DW': 300, 'HT': 300,
        'HH': 350, 'PL': 300, 'PR': 300,
    }

    # CS SDI maximums for Central States variant - from FVS CS variant
    # documentation and TWIGS calibration data for Midwest oak-hickory forests
    CS_SDI_MAXIMUMS = {
        # Conifers
        'RC': 400, 'JU': 350, 'SP': 450, 'VP': 400, 'LP': 450,
        'OS': 400, 'WP': 450, 'BY': 400,
        # Walnuts/Butternut
        'WN': 400, 'BN': 350,
        # Tupelo/Sweetgum
        'TL': 400, 'TS': 400, 'SU': 400,
        # Hickories
        'HS': 380, 'SH': 380, 'SL': 380, 'MH': 380, 'PH': 380,
        'HI': 380, 'WH': 380, 'BH': 380, 'PE': 380, 'BI': 380,
        # Beech/Birch
        'AB': 450, 'BW': 350, 'BK': 350, 'RB': 350,
        # Ashes
        'BA': 350, 'PA': 350, 'UA': 350, 'WA': 400, 'GA': 400, 'AS': 400,
        # Maples
        'RM': 400, 'SM': 450, 'BE': 400, 'SV': 400,
        # Cherry/Magnolia
        'BC': 400, 'CT': 400, 'MV': 400,
        # Elms
        'AE': 400, 'SG': 400, 'WE': 350, 'EL': 350, 'SI': 350, 'RL': 350, 'RE': 350,
        # Yellow-Poplar/Basswood
        'YP': 450, 'BW': 350,
        # White Oaks
        'WO': 420, 'BR': 420, 'CK': 420, 'SW': 420, 'PO': 380,
        'DO': 380, 'CO': 420, 'OV': 380, 'WK': 380,
        # Red Oaks
        'RO': 420, 'SK': 400, 'BO': 420, 'SO': 400, 'BJ': 350,
        'SN': 400, 'PN': 400, 'CB': 420, 'QI': 380, 'NK': 400,
        'WL': 400, 'QS': 400,
        # Poplars/Aspen
        'EC': 300, 'BP': 300, 'BT': 350, 'QA': 350,
        # Misc hardwoods
        'WT': 350, 'BG': 350, 'HK': 350, 'UH': 350, 'SS': 350,
        'OB': 350, 'CA': 350, 'PS': 350, 'HL': 400, 'SY': 400,
        'OL': 350, 'WI': 300, 'BL': 300,
        'OO': 350, 'MB': 350, 'HH': 350, 'SD': 300,
        # Understory/small trees
        'NC': 300, 'AH': 350, 'RD': 300, 'DW': 300, 'HT': 300,
        'KC': 350,
    }

    # OP SDI maximums for ORGANON Pacific Northwest variant
    # Values based on PN/WC typical ranges for intensively managed plantations
    OP_SDI_MAXIMUMS = {
        'DF': 850, 'GF': 700, 'WF': 650, 'PP': 450, 'SP': 500,
        'IC': 500, 'WH': 900, 'RC': 850, 'PY': 300, 'MH': 550,
        'GC': 450, 'TA': 600, 'CL': 400, 'BL': 400,
        'WO': 450, 'BO': 500, 'RA': 650, 'PD': 300, 'WI': 300,
    }

    # WS SDI maximums for Western Sierra Nevada variant from sitset.f SDICON array
    WS_SDI_MAXIMUMS = {
        'SP': 647, 'DF': 547, 'WF': 759, 'GS': 588, 'IC': 706,
        'JP': 571, 'RF': 800, 'PP': 571, 'LP': 622, 'WB': 675,
        'WP': 297, 'PM': 358, 'SF': 889, 'KP': 430, 'FP': 430,
        'CP': 430, 'LM': 493, 'MP': 571, 'GP': 259, 'WE': 430,
        'GB': 470, 'BD': 547, 'RW': 1120, 'MH': 817, 'WJ': 290,
        'UJ': 498, 'CJ': 430, 'LO': 382, 'CY': 382, 'BL': 382,
        'BO': 382, 'VO': 382, 'IO': 382, 'TO': 759, 'GC': 759,
        'AS': 759, 'CL': 759, 'MA': 759, 'DG': 759, 'BM': 382,
        'MC': 353, 'OS': 624, 'OH': 382,
    }

    # CA SDI maximums for Inland California variant from sitset.f R5SDI array
    CA_SDI_MAXIMUMS = {
        'PC': 570, 'IC': 570, 'RC': 570, 'WF': 760, 'RF': 800, 'SH': 800,
        'DF': 600, 'WH': 580, 'MH': 580, 'WB': 460, 'KP': 430, 'LP': 580,
        'CP': 430, 'LM': 460, 'JP': 430, 'SP': 430, 'WP': 460, 'PP': 430,
        'MP': 430, 'GP': 430, 'WJ': 330, 'BR': 580, 'GS': 570, 'PY': 570,
        'OS': 430, 'LO': 550, 'CY': 550, 'BL': 550, 'EO': 550, 'WO': 550,
        'BO': 550, 'VO': 550, 'IO': 550, 'BM': 550, 'BU': 550, 'RA': 550,
        'MA': 550, 'GC': 550, 'DG': 550, 'FL': 550, 'WN': 550, 'TO': 550,
        'SY': 550, 'AS': 550, 'CW': 550, 'WI': 550, 'CN': 550, 'CL': 550,
        'OH': 550,
    }

    # OC SDI maximums for Southwest Oregon variant from sitset.f C5 array
    # For R6 forests, SDI is scaled by C6 ratio; C5 is non-R6 default
    OC_SDI_MAXIMUMS = {
        'WP': 272, 'SP': 561, 'DF': 570, 'WF': 800, 'MH': 687,
        'IC': 576, 'LP': 679, 'ES': 620, 'SH': 1000, 'PP': 365,
        'WJ': 272, 'GF': 800, 'AF': 602, 'SF': 790, 'NF': 1000,
        'WB': 621, 'WL': 423, 'RC': 762, 'WH': 682, 'PY': 576,
        'WA': 441, 'RA': 441, 'BM': 629, 'AS': 562, 'CW': 452,
        'CH': 441, 'WO': 440, 'WI': 447, 'GC': 785, 'MC': 501,
        'MB': 501, 'OS': 365, 'OH': 441,
    }

    # WC SDI maximums for West Cascades variant (interior Cascades, generally
    # lower than coastal PN due to drier conditions)
    WC_SDI_MAXIMUMS = {
        'SF': 900, 'WF': 650, 'GF': 650, 'AF': 500, 'RF': 650,
        'NF': 650, 'YC': 550, 'IC': 450, 'RC': 800, 'ES': 500,
        'LP': 400, 'JP': 400, 'SP': 500, 'WP': 500, 'PP': 400,
        'DF': 800, 'RW': 900, 'WH': 850, 'MH': 550,
        'BM': 450, 'RA': 650, 'WA': 450, 'PB': 350, 'GC': 450,
        'AS': 350, 'CW': 450, 'WO': 450, 'WJ': 250, 'LL': 350,
        'WB': 350, 'KP': 350, 'PY': 300, 'DG': 350, 'HT': 300,
        'CH': 350, 'WI': 300, 'OT': 450,
    }

    def __init__(self, default_species: str = 'LP', variant: Optional[str] = None):
        """Initialize the metrics calculator.

        Args:
            default_species: Default species code for SDI lookups
            variant: FVS variant code ('SN', 'LS', etc.). If None, uses default.
        """
        self.default_species = default_species
        self.variant = variant or 'SN'

        # Load SDI maximums for this variant
        self._sdi_maximums = self._get_sdi_maximums()

    def _get_sdi_maximums(self) -> Dict[str, int]:
        """Get SDI maximum values for the current variant."""
        if self.variant in self._sdi_cache:
            return self._sdi_cache[self.variant]

        from .variant_registry import get_variant_config
        config = get_variant_config(self.variant)

        if config.sdi_maximums:
            self._sdi_cache[self.variant] = config.sdi_maximums
            return config.sdi_maximums

        # SN and other variants without pre-defined SDI maximums: load from config
        sdi_maximums = self._load_sn_sdi_maximums()
        self._sdi_cache[self.variant] = sdi_maximums
        return sdi_maximums

    @staticmethod
    def _load_sn_sdi_maximums() -> Dict[str, int]:
        """Load SN SDI maximum values from configuration."""
        try:
            sdi_data = load_coefficient_file('sn_stand_density_index.json')
            return {
                species: data['sdi_maximum']
                for species, data in sdi_data.get('sdi_maximums', {}).items()
            }
        except (FileNotFoundError, KeyError):
            return {'LP': 480, 'SP': 490, 'SA': 385, 'LL': 332}

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
            ba = calculate_tree_basal_area(dbh)
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
                except (ValueError, KeyError, AttributeError) as exc:
                    logger.debug(
                        "CrownWidthModel failed for %s (DBH=%.1f): %s; using linear OCW estimate",
                        species, dbh, exc,
                    )
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

        return calculate_stand_basal_area(trees)

    # Variants that use Zeide-form SDI per Fortran grinit.f LZEIDE flag.
    # Reineke uses stand QMD; Zeide uses per-tree D^1.605 sum.
    # SN/LS/CS/NE/WS/CA: LZEIDE=TRUE; PN/WC/OC/OP: LZEIDE=FALSE.
    _ZEIDE_VARIANTS = frozenset({'SN', 'LS', 'CS', 'NE', 'WS', 'CA'})

    def calculate_sdi(self, trees: List['Tree']) -> float:
        """Calculate Stand Density Index per Fortran morts.f LZEIDE branch.

        Zeide variants (SN/LS/CS/NE/WS/CA): SDI = sum(P * (D/10)^1.605)
            equivalently TPA * (DR0/10)^1.605 with DR0 = (mean D^1.605)^(1/1.605).
        Reineke variants (PN/WC/OC/OP): SDI = TPA * (QMD/10)^1.605.

        For uniform-DBH stands the two are equal; for variable stands Zeide
        DR0 < QMD, so Zeide SDI < Reineke SDI.

        Args:
            trees: List of Tree objects

        Returns:
            Stand Density Index
        """
        if not trees:
            return 0.0

        if self.variant in self._ZEIDE_VARIANTS:
            # Zeide: per-tree D^1.605 contribution (PROB=1 for our trees).
            return sum((tree.dbh / 10.0) ** 1.605 for tree in trees if tree.dbh > 0)

        # Reineke: stand QMD form.
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
            ba = calculate_tree_basal_area(tree.dbh)
            species_ba[species] = species_ba.get(species, 0.0) + ba
            total_ba += ba

        return self._calculate_weighted_max_sdi(species_ba, total_ba, default_species)

    def calculate_pbal(self, trees: List['Tree'], target_tree: 'Tree') -> float:
        """Calculate Point Basal Area in Larger trees (PBAL) for one tree.

        Mirrors Fortran PCTILE semantics by computing PBAL for the entire
        stand (with proper tie-spreading) and returning the target tree's
        value. Naive "BA of trees with strictly larger DBH" gives PBAL=0
        for all tied trees, which contradicts Fortran where ties spread
        across the percentile range so mean PBAL across ties = BA/2.

        Args:
            trees: List of all Tree objects in the stand
            target_tree: Tree to calculate PBAL for

        Returns:
            PBAL in square feet per acre
        """
        sorted_trees = sorted(trees, key=lambda t: t.dbh)
        pbal_map = self.calculate_pbal_all(sorted_trees)
        return pbal_map.get(id(target_tree), 0.0)

    def calculate_pbal_all(self, sorted_trees: List['Tree']) -> Dict[int, float]:
        """Calculate PBAL for all trees, matching Fortran PCTILE semantics.

        Fortran pctile.f sorts trees DESCENDING by BA via a stable INDEX
        array, then assigns PCT(I) = cumulative BA from smallest up to
        and including tree I (in desc-sort position) / total_BA * 100.
        PBAL(I) = PBA * (1 - PCT/100) = BA of trees STRICTLY ABOVE tree I
        in the desc-sort order.

        Critical: ties are NOT grouped.  Fortran's stable sort gives tied
        trees unique positions, so the desc-first tied tree gets PBAL=0
        and the desc-last tied tree gets PBAL≈BA.  Mean PBAL across tied
        trees is BA/2 — this variance matters for density-dependent DG.

        Args:
            sorted_trees: List of Tree objects sorted ascending by DBH

        Returns:
            Dict mapping id(tree) to PBAL in square feet per acre
        """
        if not sorted_trees:
            return {}

        # pyfvs passes ascending-sort; Fortran PCTILE uses descending.
        # Python's reversed() preserves stable ordering within the
        # original ascending sort, which mirrors Fortran's stable INDEX.
        descending = list(reversed(sorted_trees))
        pbal_map: Dict[int, float] = {}
        cum_above = 0.0
        for tree in descending:
            pbal_map[id(tree)] = cum_above
            cum_above += calculate_tree_basal_area(tree.dbh)
        return pbal_map


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

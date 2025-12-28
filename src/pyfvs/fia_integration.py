"""
FIA-FVS Integration Module.

Provides utilities for converting FIA plot data to PyFVS Stand objects
for forest growth simulation.

Part of the FIA Python Ecosystem:
- PyFIA: Survey/plot data analysis
- PyFVS: Growth/yield simulation (this package)
- GridFIA: Spatial raster analysis
- AskFIA: AI conversational interface

This module bridges PyFIA output (Polars DataFrames with FIA tree/plot data)
to PyFVS input (Stand objects with Tree collections).

Example Usage:
    >>> from pyfia import FIA
    >>> from pyfvs import Stand
    >>>
    >>> # Load FIA data
    >>> with FIA("database.duckdb") as db:
    ...     db.clip_by_state(37)  # North Carolina
    ...     trees = db.tables['TREE']
    ...     cond = db.tables['COND']
    ...
    >>> # Create PyFVS stand from FIA data
    >>> stand = Stand.from_fia_data(
    ...     tree_df=trees.filter(pl.col("PLT_CN") == plot_cn),
    ...     cond_df=cond.filter(pl.col("PLT_CN") == plot_cn),
    ...     site_index=70,
    ...     ecounit="M231"
    ... )
    >>> stand.grow(years=25)
"""

from __future__ import annotations

import json
import logging
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

logger = logging.getLogger(__name__)

# Required columns for FIA tree data conversion
REQUIRED_TREE_COLUMNS = {"SPCD", "DIA", "HT", "TPA_UNADJ"}
OPTIONAL_TREE_COLUMNS = {"CR", "CONDID", "STATUSCD", "BHAGE", "TOTAGE", "SITREE", "PLT_CN"}

# Required columns for FIA condition data
OPTIONAL_COND_COLUMNS = {"SICOND", "FORTYPCD", "ECOSUBCD", "STDAGE", "CONDID", "COND_STATUS_CD"}


class FIASpeciesMapper:
    """
    Maps FIA species codes (SPCD) to FVS 2-letter codes and vice versa.

    FIA uses integer species codes (e.g., 131 for loblolly pine), while
    FVS uses 2-letter codes (e.g., "LP" for loblolly pine). This class
    provides bidirectional mapping using the official species table.

    Attributes:
        _spcd_to_fvs: Dictionary mapping FIA SPCD (int) to FVS code (str)
        _fvs_to_spcd: Dictionary mapping FVS code (str) to FIA SPCD (int)
        _spcd_to_common: Dictionary mapping FIA SPCD to common name

    Example:
        >>> mapper = FIASpeciesMapper()
        >>> mapper.spcd_to_fvs(131)
        'LP'
        >>> mapper.fvs_to_spcd('LP')
        131
        >>> mapper.get_common_name(131)
        'loblolly pine'
    """

    _instance: Optional['FIASpeciesMapper'] = None

    def __new__(cls) -> 'FIASpeciesMapper':
        """Singleton pattern for efficient reuse."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize mapper by loading species code table."""
        if getattr(self, '_initialized', False):
            return

        self._spcd_to_fvs: Dict[int, str] = {}
        self._fvs_to_spcd: Dict[str, int] = {}
        self._spcd_to_common: Dict[int, str] = {}
        self._spcd_to_scientific: Dict[int, str] = {}
        self._load_mapping()
        self._initialized = True

    def _load_mapping(self) -> None:
        """Load species mapping from configuration file."""
        cfg_dir = Path(__file__).parent / 'cfg'
        species_file = cfg_dir / 'sn_species_codes_table.json'

        try:
            with open(species_file, 'r') as f:
                data = json.load(f)

            for species in data.get('species', []):
                # FIA code is stored as string, convert to int
                fia_code_str = species.get('fia_code', '')
                try:
                    fia_code = int(fia_code_str)
                except (ValueError, TypeError):
                    continue

                fvs_code = species.get('fvs_code', '').upper()
                common_name = species.get('common_name', '')
                scientific_name = species.get('scientific_name', '')

                if fvs_code:
                    self._spcd_to_fvs[fia_code] = fvs_code
                    self._fvs_to_spcd[fvs_code] = fia_code
                    self._spcd_to_common[fia_code] = common_name
                    self._spcd_to_scientific[fia_code] = scientific_name

            logger.debug(f"Loaded {len(self._spcd_to_fvs)} species mappings")

        except FileNotFoundError:
            logger.warning(f"Species mapping file not found: {species_file}")
            self._load_fallback_mapping()
        except json.JSONDecodeError as e:
            logger.warning(f"Error parsing species mapping file: {e}")
            self._load_fallback_mapping()

    def _load_fallback_mapping(self) -> None:
        """Load essential species mappings as fallback."""
        # Primary southern pine species
        fallback = {
            131: ('LP', 'loblolly pine', 'Pinus taeda'),
            110: ('SP', 'shortleaf pine', 'Pinus echinata'),
            121: ('LL', 'longleaf pine', 'Pinus palustris'),
            111: ('SA', 'slash pine', 'Pinus elliottii'),
            129: ('WP', 'eastern white pine', 'Pinus strobus'),
            132: ('VP', 'Virginia pine', 'Pinus virginiana'),
            802: ('WO', 'white oak', 'Quercus alba'),
            833: ('RO', 'northern red oak', 'Quercus rubra'),
            316: ('RM', 'red maple', 'Acer rubrum'),
            621: ('YP', 'tuliptree', 'Liriodendron tulipifera'),
            611: ('SU', 'sweetgum', 'Liquidambar styraciflua'),
        }

        for spcd, (fvs, common, scientific) in fallback.items():
            self._spcd_to_fvs[spcd] = fvs
            self._fvs_to_spcd[fvs] = spcd
            self._spcd_to_common[spcd] = common
            self._spcd_to_scientific[spcd] = scientific

    def spcd_to_fvs(self, spcd: int) -> Optional[str]:
        """
        Convert FIA species code to FVS 2-letter code.

        Args:
            spcd: FIA species code (integer)

        Returns:
            FVS 2-letter code or None if not found

        Example:
            >>> mapper.spcd_to_fvs(131)
            'LP'
        """
        return self._spcd_to_fvs.get(spcd)

    def fvs_to_spcd(self, fvs_code: str) -> Optional[int]:
        """
        Convert FVS 2-letter code to FIA species code.

        Args:
            fvs_code: FVS species code (2-letter string)

        Returns:
            FIA species code (integer) or None if not found

        Example:
            >>> mapper.fvs_to_spcd('LP')
            131
        """
        return self._fvs_to_spcd.get(fvs_code.upper())

    def get_common_name(self, spcd: int) -> Optional[str]:
        """Get common name for a species code."""
        return self._spcd_to_common.get(spcd)

    def get_scientific_name(self, spcd: int) -> Optional[str]:
        """Get scientific name for a species code."""
        return self._spcd_to_scientific.get(spcd)

    def is_supported(self, spcd: int) -> bool:
        """Check if a species code is supported for FVS simulation."""
        return spcd in self._spcd_to_fvs

    def batch_convert(self, spcd_list: List[int]) -> List[Optional[str]]:
        """
        Convert a list of FIA species codes to FVS codes.

        Args:
            spcd_list: List of FIA species codes

        Returns:
            List of FVS codes (None for unsupported species)
        """
        return [self.spcd_to_fvs(spcd) for spcd in spcd_list]

    @property
    def supported_species(self) -> List[int]:
        """Get list of all supported FIA species codes."""
        return list(self._spcd_to_fvs.keys())

    def get_species_info(self, spcd: int) -> Optional[Dict[str, Any]]:
        """Get full species information for a species code."""
        fvs_code = self.spcd_to_fvs(spcd)
        if fvs_code is None:
            return None

        return {
            'spcd': spcd,
            'fvs_code': fvs_code,
            'common_name': self._spcd_to_common.get(spcd, ''),
            'scientific_name': self._spcd_to_scientific.get(spcd, ''),
        }


@dataclass
class FIATreeRecord:
    """
    Intermediate representation of an FIA tree record.

    This dataclass holds FIA tree data in a format ready for conversion
    to PyFVS Tree objects. It handles unit conversions and validation.

    Attributes:
        spcd: FIA species code (integer)
        dia: Diameter at breast height (inches)
        ht: Total height (feet)
        cr: Crown ratio as percentage (0-100)
        tpa_unadj: Unadjusted trees per acre
        age: Tree age in years (optional)
        condid: Condition ID for multi-condition plots
        statuscd: Tree status code (1=live, 2=dead, 3=removed)
    """
    spcd: int
    dia: float
    ht: float
    cr: float = 50.0  # Default crown ratio (50%)
    tpa_unadj: float = 1.0
    age: Optional[int] = None
    condid: int = 1
    statuscd: int = 1  # Default to live tree

    def __post_init__(self):
        """Validate and clean data after initialization."""
        # Ensure non-negative values
        self.dia = max(0.0, float(self.dia))
        self.ht = max(0.0, float(self.ht))
        self.cr = max(0.0, min(100.0, float(self.cr)))
        self.tpa_unadj = max(0.0, float(self.tpa_unadj))

        if self.age is not None:
            self.age = max(0, int(self.age))

    @property
    def crown_ratio_proportion(self) -> float:
        """Crown ratio as proportion (0-1) for PyFVS."""
        return self.cr / 100.0

    @property
    def is_live(self) -> bool:
        """Check if tree is a live tree."""
        return self.statuscd == 1

    def to_pyfvs_tree(self, mapper: FIASpeciesMapper):
        """
        Convert to PyFVS Tree object.

        Args:
            mapper: FIASpeciesMapper instance for species code conversion

        Returns:
            PyFVS Tree object or None if species not supported
        """
        from .tree import Tree

        fvs_code = mapper.spcd_to_fvs(self.spcd)
        if fvs_code is None:
            logger.warning(f"Unsupported species code: {self.spcd}")
            return None

        return Tree(
            dbh=self.dia,
            height=self.ht,
            species=fvs_code,
            age=self.age or 0,
            crown_ratio=self.crown_ratio_proportion
        )


@dataclass
class FIAPlotData:
    """
    Container for FIA plot data ready for FVS conversion.

    Holds processed tree records and plot-level attributes needed
    for creating a PyFVS Stand.

    Attributes:
        trees: List of FIATreeRecord objects
        site_index: Site index (base age 25)
        forest_type: FVS forest type group
        ecounit: Ecological unit code
        plot_cn: FIA plot control number
        condid: Selected condition ID
        stand_age: Stand age from COND table
    """
    trees: List[FIATreeRecord] = field(default_factory=list)
    site_index: Optional[float] = None
    forest_type: Optional[str] = None
    ecounit: Optional[str] = None
    plot_cn: Optional[str] = None
    condid: int = 1
    stand_age: Optional[int] = None

    @property
    def tree_count(self) -> int:
        """Number of trees in the plot."""
        return len(self.trees)

    @property
    def live_tree_count(self) -> int:
        """Number of live trees in the plot."""
        return sum(1 for t in self.trees if t.is_live)

    def get_species_summary(self, mapper: FIASpeciesMapper) -> Dict[str, int]:
        """Get summary of species composition."""
        summary: Dict[str, int] = Counter()
        for tree in self.trees:
            fvs_code = mapper.spcd_to_fvs(tree.spcd)
            if fvs_code:
                summary[fvs_code] += 1
        return dict(summary)


def validate_fia_input(tree_df: 'pl.DataFrame') -> None:
    """
    Validate that a DataFrame has required FIA columns.

    Args:
        tree_df: Polars DataFrame with FIA TREE table columns

    Raises:
        TypeError: If input is not a Polars DataFrame
        ValueError: If required columns are missing
    """
    import polars as pl

    if not isinstance(tree_df, (pl.DataFrame, pl.LazyFrame)):
        raise TypeError(f"Expected Polars DataFrame or LazyFrame, got {type(tree_df).__name__}")

    # Collect if lazy
    if isinstance(tree_df, pl.LazyFrame):
        columns = tree_df.collect_schema().names()
    else:
        columns = tree_df.columns

    missing = REQUIRED_TREE_COLUMNS - set(columns)
    if missing:
        raise ValueError(f"Missing required FIA columns: {missing}. "
                        f"Required columns are: {REQUIRED_TREE_COLUMNS}")


def transform_fia_trees(
    tree_df: 'pl.DataFrame',
    min_dia: float = 1.0,
    status_filter: Optional[int] = 1
) -> List[FIATreeRecord]:
    """
    Transform FIA TREE DataFrame to list of FIATreeRecord.

    Args:
        tree_df: Polars DataFrame with FIA TREE columns
        min_dia: Minimum diameter threshold (inches)
        status_filter: STATUSCD filter (1=live, 2=dead, None=all)

    Returns:
        List of FIATreeRecord objects
    """
    import polars as pl

    # Collect if lazy
    if isinstance(tree_df, pl.LazyFrame):
        tree_df = tree_df.collect()

    records = []

    for row in tree_df.iter_rows(named=True):
        # Extract required fields
        spcd = row.get('SPCD')
        dia = row.get('DIA')
        ht = row.get('HT')
        tpa = row.get('TPA_UNADJ', 1.0)

        # Skip if missing required data
        if spcd is None or dia is None or ht is None:
            continue

        # Skip if below diameter threshold
        if float(dia) < min_dia:
            continue

        # Apply status filter
        statuscd = row.get('STATUSCD', 1)
        if status_filter is not None and statuscd != status_filter:
            continue

        # Extract optional fields
        cr = row.get('CR', 50.0) or 50.0  # Default crown ratio
        condid = row.get('CONDID', 1) or 1

        # Try to get age (BHAGE preferred, fall back to TOTAGE)
        age = row.get('BHAGE') or row.get('TOTAGE')

        record = FIATreeRecord(
            spcd=int(spcd),
            dia=float(dia),
            ht=float(ht),
            cr=float(cr),
            tpa_unadj=float(tpa) if tpa else 1.0,
            age=int(age) if age else None,
            condid=int(condid),
            statuscd=int(statuscd) if statuscd else 1
        )
        records.append(record)

    return records


def select_condition(
    tree_df: 'pl.DataFrame',
    cond_df: Optional['pl.DataFrame'] = None,
    strategy: str = "dominant"
) -> Tuple['pl.DataFrame', int]:
    """
    Select a single condition from a multi-condition plot.

    FIA plots can have multiple conditions representing different forest
    types or stand conditions. This function selects one condition for
    simulation.

    Args:
        tree_df: FIA TREE DataFrame with CONDID column
        cond_df: Optional FIA COND DataFrame for area weighting
        strategy: Selection strategy:
            - "dominant": Condition with most basal area (default)
            - "first": Condition 1
            - "forested": First forested condition (COND_STATUS_CD=1)

    Returns:
        Tuple of (filtered tree_df, selected condid)
    """
    import polars as pl

    # Collect if lazy
    if isinstance(tree_df, pl.LazyFrame):
        tree_df = tree_df.collect()

    if "CONDID" not in tree_df.columns:
        return tree_df, 1

    unique_conditions = tree_df.select("CONDID").unique()
    if len(unique_conditions) <= 1:
        condid = unique_conditions["CONDID"][0] if len(unique_conditions) > 0 else 1
        return tree_df, int(condid) if condid else 1

    if strategy == "dominant":
        # Select condition with highest basal area
        if "DIA" in tree_df.columns and "TPA_UNADJ" in tree_df.columns:
            ba_by_cond = (
                tree_df
                .with_columns(
                    (pl.col("DIA") ** 2 * 0.005454 * pl.col("TPA_UNADJ")).alias("BA")
                )
                .group_by("CONDID")
                .agg(pl.col("BA").sum())
                .sort("BA", descending=True)
            )
            selected_condid = int(ba_by_cond["CONDID"][0])
        else:
            selected_condid = 1

    elif strategy == "first":
        selected_condid = 1

    elif strategy == "forested":
        if cond_df is not None:
            if isinstance(cond_df, pl.LazyFrame):
                cond_df = cond_df.collect()
            if "COND_STATUS_CD" in cond_df.columns:
                forested = cond_df.filter(pl.col("COND_STATUS_CD") == 1)
                if len(forested) > 0:
                    selected_condid = int(forested["CONDID"][0])
                else:
                    selected_condid = 1
            else:
                selected_condid = 1
        else:
            selected_condid = 1
    else:
        selected_condid = 1

    filtered_df = tree_df.filter(pl.col("CONDID") == selected_condid)
    return filtered_df, selected_condid


def derive_site_index(
    cond_df: Optional['pl.DataFrame'],
    tree_df: Optional['pl.DataFrame'] = None,
    condid: int = 1,
    default: float = 70.0
) -> float:
    """
    Derive site index from FIA condition or tree data.

    Attempts to get site index from:
    1. SICOND column in COND table
    2. SITREE column in TREE table (average of site trees)
    3. Default value

    Args:
        cond_df: FIA COND DataFrame
        tree_df: FIA TREE DataFrame (optional fallback)
        condid: Condition ID to use
        default: Default site index if not found

    Returns:
        Site index (base age 25) in feet
    """
    import polars as pl

    # Try SICOND from condition table
    if cond_df is not None:
        if isinstance(cond_df, pl.LazyFrame):
            cond_df = cond_df.collect()

        if "SICOND" in cond_df.columns:
            filtered = cond_df.filter(pl.col("CONDID") == condid) if "CONDID" in cond_df.columns else cond_df
            if len(filtered) > 0:
                sicond = filtered["SICOND"][0]
                if sicond is not None and sicond > 0:
                    return float(sicond)

    # Try SITREE from tree table
    if tree_df is not None:
        if isinstance(tree_df, pl.LazyFrame):
            tree_df = tree_df.collect()

        if "SITREE" in tree_df.columns:
            site_trees = tree_df.filter(pl.col("SITREE").is_not_null())
            if len(site_trees) > 0:
                avg_si = site_trees["SITREE"].mean()
                if avg_si is not None and avg_si > 0:
                    return float(avg_si)

    return default


def derive_forest_type(
    cond_df: Optional['pl.DataFrame'],
    tree_df: Optional['pl.DataFrame'],
    mapper: FIASpeciesMapper,
    condid: int = 1
) -> str:
    """
    Derive FVS forest type group from FIA data.

    Attempts to determine forest type from:
    1. FORTYPCD from COND table (mapped to FVS group)
    2. Species composition of trees

    Args:
        cond_df: FIA COND DataFrame
        tree_df: FIA TREE DataFrame
        mapper: Species code mapper
        condid: Condition ID to use

    Returns:
        FVS forest type group code (e.g., "FTYLPN")
    """
    import polars as pl
    from .forest_type import map_fia_to_fvs, ForestTypeClassifier

    # Try FORTYPCD from COND table
    if cond_df is not None:
        if isinstance(cond_df, pl.LazyFrame):
            cond_df = cond_df.collect()

        if "FORTYPCD" in cond_df.columns:
            filtered = cond_df.filter(pl.col("CONDID") == condid) if "CONDID" in cond_df.columns else cond_df
            if len(filtered) > 0:
                fortypcd = filtered["FORTYPCD"][0]
                if fortypcd is not None:
                    fvs_group = map_fia_to_fvs(int(fortypcd))
                    if fvs_group:
                        return fvs_group

    # Fall back to species composition
    if tree_df is not None:
        if isinstance(tree_df, pl.LazyFrame):
            tree_df = tree_df.collect()

        from .tree import Tree
        classifier = ForestTypeClassifier()

        # Create temporary trees for classification
        temp_trees = []
        for row in tree_df.iter_rows(named=True):
            spcd = row.get('SPCD')
            dia = row.get('DIA', 5.0)
            ht = row.get('HT', 30.0)

            if spcd is not None:
                fvs_code = mapper.spcd_to_fvs(int(spcd))
                if fvs_code:
                    temp_trees.append(Tree(
                        dbh=float(dia) if dia else 5.0,
                        height=float(ht) if ht else 30.0,
                        species=fvs_code
                    ))

        if temp_trees:
            result = classifier.classify_from_trees(temp_trees, basal_area_weighted=True)
            return result.forest_type_group

    # Default to yellow pine
    return "FTYLPN"


def derive_ecounit(
    cond_df: Optional['pl.DataFrame'],
    condid: int = 1,
    default: Optional[str] = None
) -> Optional[str]:
    """
    Derive ecological unit from FIA condition data.

    Attempts to determine ecounit from ECOSUBCD column in COND table.

    Args:
        cond_df: FIA COND DataFrame
        condid: Condition ID to use
        default: Default ecounit if not found

    Returns:
        Ecological unit code or default
    """
    import polars as pl

    if cond_df is None:
        return default

    if isinstance(cond_df, pl.LazyFrame):
        cond_df = cond_df.collect()

    if "ECOSUBCD" in cond_df.columns:
        filtered = cond_df.filter(pl.col("CONDID") == condid) if "CONDID" in cond_df.columns else cond_df
        if len(filtered) > 0:
            ecosubcd = filtered["ECOSUBCD"][0]
            if ecosubcd is not None:
                # Map ECOSUBCD to FVS ecounit
                # This is a simplified mapping - full implementation would
                # use the ecological subregion to province mapping
                eco_str = str(ecosubcd)

                # Check for mountain provinces
                if eco_str.startswith('M'):
                    return eco_str[:4]  # e.g., "M231"

                # Check for numbered provinces
                if len(eco_str) >= 3:
                    return eco_str[:3]  # e.g., "232", "231"

    return default


def derive_stand_age(
    cond_df: Optional['pl.DataFrame'],
    tree_df: Optional['pl.DataFrame'] = None,
    condid: int = 1
) -> Optional[int]:
    """
    Derive stand age from FIA data.

    Args:
        cond_df: FIA COND DataFrame
        tree_df: FIA TREE DataFrame (optional fallback)
        condid: Condition ID to use

    Returns:
        Stand age in years or None
    """
    import polars as pl

    # Try STDAGE from condition table
    if cond_df is not None:
        if isinstance(cond_df, pl.LazyFrame):
            cond_df = cond_df.collect()

        if "STDAGE" in cond_df.columns:
            filtered = cond_df.filter(pl.col("CONDID") == condid) if "CONDID" in cond_df.columns else cond_df
            if len(filtered) > 0:
                stdage = filtered["STDAGE"][0]
                if stdage is not None and stdage > 0:
                    return int(stdage)

    # Try average tree age from tree table
    if tree_df is not None:
        if isinstance(tree_df, pl.LazyFrame):
            tree_df = tree_df.collect()

        age_col = None
        if "BHAGE" in tree_df.columns:
            age_col = "BHAGE"
        elif "TOTAGE" in tree_df.columns:
            age_col = "TOTAGE"

        if age_col:
            ages = tree_df.filter(pl.col(age_col).is_not_null())
            if len(ages) > 0:
                avg_age = ages[age_col].mean()
                if avg_age is not None and avg_age > 0:
                    return int(avg_age)

    return None


def determine_dominant_species(trees: List['Tree']) -> str:
    """
    Determine the dominant species by basal area.

    Args:
        trees: List of PyFVS Tree objects

    Returns:
        FVS species code of dominant species
    """
    if not trees:
        return "LP"  # Default to loblolly pine

    species_ba: Dict[str, float] = Counter()
    for tree in trees:
        ba = tree.dbh ** 2 * 0.005454  # Basal area factor
        species_ba[tree.species] += ba

    if not species_ba:
        return "LP"

    return max(species_ba.keys(), key=lambda s: species_ba[s])


def classify_stand_purity(trees: List['Tree']) -> str:
    """
    Classify whether a stand is pure or mixed species.

    Args:
        trees: List of PyFVS Tree objects

    Returns:
        "pure" if dominant species >= 80% of basal area, "mixed" otherwise
    """
    if not trees:
        return "mixed"

    species_ba: Dict[str, float] = Counter()
    total_ba = 0.0

    for tree in trees:
        ba = tree.dbh ** 2 * 0.005454
        species_ba[tree.species] += ba
        total_ba += ba

    if total_ba == 0:
        return "mixed"

    max_proportion = max(species_ba.values()) / total_ba
    return "pure" if max_proportion >= 0.8 else "mixed"


def create_trees_from_fia(
    fia_records: List[FIATreeRecord],
    mapper: FIASpeciesMapper,
    weight_by_tpa: bool = True,
    max_trees: int = 1000,
    random_seed: Optional[int] = None
) -> List:
    """
    Create PyFVS Tree objects from FIA tree records.

    Args:
        fia_records: List of FIATreeRecord objects
        mapper: Species code mapper
        weight_by_tpa: If True, replicate trees based on TPA_UNADJ
        max_trees: Maximum number of trees (subsample if exceeded)
        random_seed: Random seed for reproducible subsampling

    Returns:
        List of PyFVS Tree objects
    """
    import copy

    trees = []
    unsupported_species: Dict[int, int] = Counter()

    for record in fia_records:
        pyfvs_tree = record.to_pyfvs_tree(mapper)
        if pyfvs_tree is None:
            unsupported_species[record.spcd] += 1
            continue

        if weight_by_tpa and record.tpa_unadj > 1:
            # TPA_UNADJ represents trees per acre
            # Round to integer, but ensure at least 1
            n_copies = max(1, round(record.tpa_unadj))
            trees.extend([copy.copy(pyfvs_tree) for _ in range(n_copies)])
        else:
            trees.append(pyfvs_tree)

    # Log unsupported species
    if unsupported_species:
        for spcd, count in unsupported_species.items():
            logger.warning(f"Skipped {count} trees of unsupported species SPCD={spcd}")

    # Subsample if too many trees
    if len(trees) > max_trees:
        rng = random.Random(random_seed)
        trees = rng.sample(trees, max_trees)
        logger.info(f"Subsampled from {len(trees)} to {max_trees} trees")

    return trees


# Export public API
__all__ = [
    'FIASpeciesMapper',
    'FIATreeRecord',
    'FIAPlotData',
    'validate_fia_input',
    'transform_fia_trees',
    'select_condition',
    'derive_site_index',
    'derive_forest_type',
    'derive_ecounit',
    'derive_stand_age',
    'determine_dominant_species',
    'classify_stand_purity',
    'create_trees_from_fia',
    'REQUIRED_TREE_COLUMNS',
    'OPTIONAL_TREE_COLUMNS',
]

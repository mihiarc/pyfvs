"""
Stand output generator for FVS-Python.

This module provides output generation utilities extracted from the Stand class
for improved testability and maintainability.

Output formats include:
- FVS-compatible tree lists
- Yield records (FVS_Summary format)
- Stand stock tables
- Export to CSV, JSON, Excel

Note: Export functionality delegates to DataExporter for file I/O.
"""
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .tree import Tree
    from .stand_metrics import StandMetricsCalculator
    from .competition import CompetitionCalculator
    from .data_export import DataExporter


@dataclass
class YieldRecord:
    """Record for FVS_Summary compatible yield table output.

    Implements the FVS_Summary database table schema for compatibility
    with FVS post-processing tools and yield table analysis.

    Attributes:
        StandID: Stand identification
        Year: Calendar year of projection
        Age: Stand age in years
        TPA: Trees per acre
        BA: Basal area per acre (sq ft)
        SDI: Stand density index
        CCF: Crown competition factor
        TopHt: Average dominant height (feet)
        QMD: Quadratic mean diameter (inches)
        TCuFt: Total cubic foot volume (pulp + sawtimber)
        MCuFt: Merchantable (sawtimber) cubic foot volume
        BdFt: Board foot volume (Doyle scale)
        RTpa: Removed trees per acre
        RTCuFt: Removed total cubic volume
        RMCuFt: Removed merchantable cubic volume
        RBdFt: Removed board foot volume
        AThinBA: After-thin basal area
        AThinSDI: After-thin stand density index
        AThinCCF: After-thin crown competition factor
        AThinTopHt: After-thin dominant height
        AThinQMD: After-thin QMD
        PrdLen: Period length (years)
        Acc: Accretion (cubic feet/acre/year)
        Mort: Mortality (cubic feet/acre/year)
        MAI: Mean annual increment
        ForTyp: Forest type code
        SizeCls: Size class code
        StkCls: Stocking class code
    """
    StandID: str
    Year: int
    Age: int
    TPA: int
    BA: float
    SDI: float
    CCF: float
    TopHt: float
    QMD: float
    TCuFt: float
    MCuFt: float
    BdFt: float
    RTpa: int = 0
    RTCuFt: float = 0.0
    RMCuFt: float = 0.0
    RBdFt: float = 0.0
    AThinBA: float = 0.0
    AThinSDI: float = 0.0
    AThinCCF: float = 0.0
    AThinTopHt: float = 0.0
    AThinQMD: float = 0.0
    PrdLen: int = 5
    Acc: float = 0.0
    Mort: float = 0.0
    MAI: float = 0.0
    ForTyp: int = 0
    SizeCls: int = 0
    StkCls: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return asdict(self)


class StandOutputGenerator:
    """Generator for stand output reports and exports.

    Provides methods for generating FVS-compatible output formats
    including tree lists, yield records, and stock tables.

    Attributes:
        metrics_calculator: StandMetricsCalculator for stand metrics
        competition_calculator: CompetitionCalculator for tree competition
        default_species: Default species code
    """

    def __init__(
        self,
        metrics_calculator: Optional['StandMetricsCalculator'] = None,
        competition_calculator: Optional['CompetitionCalculator'] = None,
        default_species: str = 'LP',
        output_dir: Optional[Path] = None
    ):
        """Initialize the output generator.

        Args:
            metrics_calculator: StandMetricsCalculator instance
            competition_calculator: CompetitionCalculator instance
            default_species: Default species code
            output_dir: Directory for exports (default: current directory)
        """
        self.default_species = default_species
        self._output_dir = output_dir or Path('.')
        self._exporter: Optional['DataExporter'] = None

        if metrics_calculator is None:
            from .stand_metrics import StandMetricsCalculator
            self._metrics = StandMetricsCalculator(default_species)
        else:
            self._metrics = metrics_calculator

        if competition_calculator is None:
            from .competition import CompetitionCalculator
            self._competition = CompetitionCalculator(self._metrics, default_species)
        else:
            self._competition = competition_calculator

    @property
    def exporter(self) -> 'DataExporter':
        """Lazy-load DataExporter for file I/O."""
        if self._exporter is None:
            from .data_export import DataExporter
            self._exporter = DataExporter(self._output_dir)
        return self._exporter

    def generate_tree_list(
        self,
        trees: List['Tree'],
        stand_age: int,
        site_index: float,
        stand_id: str = "STAND001",
        include_growth: bool = True
    ) -> List[Dict[str, Any]]:
        """Generate FVS-compatible tree list output.

        Creates a list of tree records matching the FVS_TreeList database
        table schema for compatibility with FVS post-processing tools.

        Args:
            trees: List of Tree objects
            stand_age: Current stand age
            site_index: Stand site index
            stand_id: Stand identifier
            include_growth: Include growth calculations (DG, HtG)

        Returns:
            List of dictionaries with FVS_TreeList compatible columns
        """
        if not trees:
            return []

        # Calculate competition metrics for BA percentile and PBAL
        competition_metrics = self._competition.calculate_tree_competition_dicts(
            trees, site_index
        )

        # Pre-compute BA percentile using rank (position in sorted DBH order)
        # This gives larger trees higher percentiles (0-100 scale)
        sorted_by_dbh = sorted(range(len(trees)), key=lambda i: trees[i].dbh)
        tree_to_rank = {sorted_by_dbh[i]: i for i in range(len(sorted_by_dbh))}

        tree_records = []
        for i, (tree, metrics) in enumerate(zip(trees, competition_metrics)):
            # Calculate BA percentile as rank in diameter distribution (0-100)
            # Larger trees have higher percentiles
            rank = tree_to_rank[i] / len(trees) if trees else 0.5
            ba_percentile = rank * 100.0
            pbal = metrics.get('pbal', 0)

            # Generate tree record
            record = tree.to_tree_record(
                tree_id=i + 1,
                year=stand_age,
                ba_percentile=ba_percentile,
                pbal=pbal,
                prev_dbh=None if not include_growth else None,
                prev_height=None if not include_growth else None
            )

            # Add stand-level identifiers
            record['StandID'] = stand_id
            # Use stand age for Age field (FVS convention for tree list output)
            record['Age'] = stand_age

            tree_records.append(record)

        return tree_records

    def generate_stock_table(
        self,
        trees: List['Tree'],
        dbh_class_width: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Generate stand and stock table by diameter class.

        Creates a summary table similar to FVS StdStk output showing
        trees per acre, basal area, and volumes by diameter class.

        Args:
            trees: List of Tree objects
            dbh_class_width: Width of diameter classes (default 2 inches)

        Returns:
            List of dictionaries with stock table columns
        """
        if not trees:
            return []

        # Determine diameter range
        min_dbh = min(t.dbh for t in trees)
        max_dbh = max(t.dbh for t in trees)

        # Create diameter classes
        class_min = math.floor(min_dbh / dbh_class_width) * dbh_class_width
        class_max = math.ceil(max_dbh / dbh_class_width) * dbh_class_width

        stock_table = []
        current_class = class_min

        while current_class < class_max:
            class_upper = current_class + dbh_class_width

            # Filter trees in this class
            class_trees = [t for t in trees
                          if current_class <= t.dbh < class_upper]

            if class_trees:
                # Calculate class metrics
                tpa = len(class_trees)
                ba = sum(math.pi * (t.dbh / 24) ** 2 for t in class_trees)
                tcuft = sum(t.get_volume('total_cubic') for t in class_trees)
                mcuft = sum(t.get_volume('merchantable_cubic') for t in class_trees)
                bdft = sum(t.get_volume('board_foot') for t in class_trees)

                stock_table.append({
                    'DBHClass': current_class + dbh_class_width / 2,
                    'DBHMin': current_class,
                    'DBHMax': class_upper,
                    'TPA': tpa,
                    'BA': ba,
                    'TcuFt': tcuft,
                    'McuFt': mcuft,
                    'BdFt': bdft
                })

            current_class = class_upper

        return stock_table

    def create_yield_record(
        self,
        trees: List['Tree'],
        stand_age: int,
        site_index: float,
        stand_id: str = "STAND001",
        year: int = 0,
        prev_volume: float = 0.0,
        mortality_volume: float = 0.0,
        period_length: int = 5,
        removed_tpa: int = 0,
        removed_tcuft: float = 0.0,
        removed_mcuft: float = 0.0,
        removed_bdft: float = 0.0,
        forest_type: str = "",
        size_class: str = "",
        stocking_class: str = ""
    ) -> YieldRecord:
        """Create a yield record from current stand state.

        Args:
            trees: List of Tree objects
            stand_age: Current stand age
            site_index: Stand site index
            stand_id: Stand identifier
            year: Calendar year (if 0, uses stand age)
            prev_volume: Previous period total cubic volume
            mortality_volume: Volume lost to mortality
            period_length: Length of growth period
            removed_tpa: Trees removed this period
            removed_tcuft: Total cubic volume removed
            removed_mcuft: Merchantable cubic volume removed
            removed_bdft: Board feet removed
            forest_type: Forest type code
            size_class: Size class code
            stocking_class: Stocking class code

        Returns:
            YieldRecord with FVS_Summary compatible fields
        """
        # Calculate metrics
        all_metrics = self._metrics.calculate_all_metrics(trees, self.default_species)

        # Calculate volumes
        volume = sum(t.get_volume('total_cubic') for t in trees) if trees else 0.0
        merch_volume = sum(t.get_volume('merchantable_cubic') for t in trees) if trees else 0.0
        board_feet = sum(t.get_volume('board_foot') for t in trees) if trees else 0.0

        # Calculate accretion and mortality rate
        if prev_volume > 0 and period_length > 0:
            gross_growth = volume - prev_volume + mortality_volume
            accretion = max(0, gross_growth) / period_length
            mort_rate = mortality_volume / period_length
        else:
            accretion = 0.0
            mort_rate = 0.0

        # Calculate MAI
        mai = volume / stand_age if stand_age > 0 else 0.0

        return YieldRecord(
            StandID=stand_id,
            Year=year if year > 0 else stand_age,
            Age=stand_age,
            TPA=all_metrics['tpa'],
            BA=all_metrics['ba'],
            SDI=all_metrics['sdi'],
            CCF=all_metrics['ccf'],
            TopHt=all_metrics['top_height'],
            QMD=all_metrics['qmd'],
            TCuFt=volume,
            MCuFt=merch_volume,
            BdFt=board_feet,
            RTpa=removed_tpa,
            RTCuFt=removed_tcuft,
            RMCuFt=removed_mcuft,
            RBdFt=removed_bdft,
            AThinBA=all_metrics['ba'],
            AThinSDI=all_metrics['sdi'],
            AThinCCF=all_metrics['ccf'],
            AThinTopHt=all_metrics['top_height'],
            AThinQMD=all_metrics['qmd'],
            PrdLen=period_length,
            Acc=accretion,
            Mort=mort_rate,
            MAI=mai,
            ForTyp=forest_type,
            SizeCls=size_class,
            StkCls=stocking_class
        )

    def export_tree_list(
        self,
        tree_list: List[Dict[str, Any]],
        filepath: str,
        format: str = 'csv',
        stand_id: str = "STAND001"
    ) -> str:
        """Export tree list to file.

        Delegates to DataExporter for CSV/Excel I/O.
        JSON uses FVS-specific format for compatibility with FVS tools.

        Args:
            tree_list: List of tree record dictionaries
            filepath: Output file path (extension added if not present)
            format: Export format ('csv', 'json', 'excel')
            stand_id: Stand identifier for metadata

        Returns:
            Path to exported file
        """
        import json
        import pandas as pd

        filename = Path(filepath).stem

        if format == 'csv':
            df = pd.DataFrame(tree_list)
            return str(self.exporter.export_to_csv(df, filename, include_metadata=False))
        elif format == 'json':
            # Use FVS-specific JSON format for compatibility
            path = self._output_dir / f"{filename}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump({
                    'metadata': {
                        'format': 'FVS_TreeList',
                        'stand_id': stand_id,
                        'record_count': len(tree_list)
                    },
                    'trees': tree_list
                }, f, indent=2)
            return str(path)
        elif format == 'excel':
            df = pd.DataFrame(tree_list)
            return str(self.exporter.export_to_excel(df, filename))
        else:
            raise ValueError(f"Unsupported format: {format}")

    def export_yield_table(
        self,
        yield_records: List[YieldRecord],
        filepath: str,
        format: str = 'csv',
        stand_id: str = "STAND001"
    ) -> str:
        """Export yield table to file.

        Delegates to DataExporter for CSV/Excel I/O.
        JSON uses FVS-specific format for compatibility with FVS tools.

        Args:
            yield_records: List of YieldRecord objects
            filepath: Output file path
            format: Export format ('csv', 'json', 'excel')
            stand_id: Stand identifier for metadata

        Returns:
            Path to exported file
        """
        import json
        import pandas as pd

        yield_dicts = [r.to_dict() for r in yield_records]
        filename = Path(filepath).stem

        if format == 'csv':
            df = pd.DataFrame(yield_dicts)
            return str(self.exporter.export_to_csv(df, filename, include_metadata=False))
        elif format == 'json':
            # Use FVS-specific JSON format for compatibility
            path = self._output_dir / f"{filename}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump({
                    'metadata': {
                        'format': 'FVS_Summary',
                        'stand_id': stand_id,
                        'record_count': len(yield_dicts)
                    },
                    'yield_table': yield_dicts
                }, f, indent=2)
            return str(path)
        elif format == 'excel':
            df = pd.DataFrame(yield_dicts)
            return str(self.exporter.export_to_excel(df, filename))
        else:
            raise ValueError(f"Unsupported format: {format}")

    def export_stock_table(
        self,
        stock_table: List[Dict[str, Any]],
        filepath: str,
        format: str = 'csv'
    ) -> str:
        """Export stock table to file.

        Delegates to DataExporter for CSV/Excel I/O.
        JSON uses FVS-specific format for consistency.

        Args:
            stock_table: List of stock table dictionaries
            filepath: Output file path
            format: Export format ('csv', 'json', 'excel')

        Returns:
            Path to exported file
        """
        import json
        import pandas as pd

        filename = Path(filepath).stem

        if format == 'csv':
            df = pd.DataFrame(stock_table)
            return str(self.exporter.export_to_csv(df, filename, include_metadata=False))
        elif format == 'json':
            # Use FVS-specific JSON format for consistency
            path = self._output_dir / f"{filename}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump({
                    'metadata': {
                        'format': 'FVS_Python',
                        'record_count': len(stock_table)
                    },
                    'stock_table': stock_table
                }, f, indent=2)
            return str(path)
        elif format == 'excel':
            df = pd.DataFrame(stock_table)
            return str(self.exporter.export_to_excel(df, filename))
        else:
            raise ValueError(f"Unsupported format: {format}")


# Module-level convenience functions
_default_generator: Optional[StandOutputGenerator] = None


def get_output_generator(
    metrics_calculator: Optional['StandMetricsCalculator'] = None,
    species: str = 'LP'
) -> StandOutputGenerator:
    """Get or create an output generator instance.

    Args:
        metrics_calculator: Optional StandMetricsCalculator
        species: Default species code

    Returns:
        StandOutputGenerator instance
    """
    global _default_generator
    if _default_generator is None:
        _default_generator = StandOutputGenerator(metrics_calculator, None, species)
    return _default_generator


def generate_tree_list(
    trees: List['Tree'],
    stand_age: int,
    site_index: float = 70.0,
    stand_id: str = "STAND001"
) -> List[Dict[str, Any]]:
    """Generate tree list using the default generator.

    Args:
        trees: List of Tree objects
        stand_age: Current stand age
        site_index: Stand site index
        stand_id: Stand identifier

    Returns:
        List of tree record dictionaries
    """
    return get_output_generator().generate_tree_list(
        trees, stand_age, site_index, stand_id
    )

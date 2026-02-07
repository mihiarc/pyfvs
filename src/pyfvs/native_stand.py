"""
NativeStand - Bridge between pyfvs Stand API and official FVS Fortran library.

This module provides a NativeStand class that has the same API as the Python
Stand class but uses the official USDA FVS Fortran library for growth projections.

Benefits:
- Authoritative growth projections matching official FVS output
- Access to all FVS functionality (extensions, reports, etc.)
- Validation of Python reimplementation against official code

Usage:
    from pyfvs.native_stand import NativeStand
    
    # Create and grow a stand using official FVS
    stand = NativeStand.initialize_planted(500, site_index=70, species='LP')
    stand.grow(years=25)
    metrics = stand.get_metrics()
    
    # Access tree-level data
    for tree in stand.trees:
        print(f"DBH: {tree.dbh:.1f}, Height: {tree.height:.1f}")

Author: Claude (Anthropic) for OpenClaw
Date: 2026-02-07
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import logging
import json

from .fvs_native import FVSLibrary, FVSError, find_fvs_libraries
from .tree import Tree

logger = logging.getLogger(__name__)


# Species code mapping: pyfvs 2-letter code -> FVS sequence number
# Based on sn_species_codes_table.json
SN_SPECIES_MAP = {
    'FR': 1,   # fir
    'JU': 2,   # juniper
    'PI': 3,   # spruce
    'PU': 4,   # sand pine
    'SP': 5,   # shortleaf pine
    'SA': 6,   # slash pine
    'SR': 7,   # spruce pine
    'LL': 8,   # longleaf pine
    'TM': 9,   # Table Mountain pine
    'PP': 10,  # pitch pine
    'PD': 11,  # pond pine
    'WP': 12,  # eastern white pine
    'LP': 13,  # loblolly pine
    'VP': 14,  # Virginia pine
    'BY': 15,  # bald cypress
    'PC': 16,  # pond cypress
    'HM': 17,  # hemlock
    'FM': 18,  # southern sugar maple
    'BE': 19,  # boxelder
    'RM': 20,  # red maple
    # Add more as needed...
    'WO': 52,  # white oak
    'RO': 68,  # red oak (northern)
    'WA': 78,  # white ash
    'YP': 57,  # yellow-poplar
}

# Reverse mapping
SN_SEQUENCE_TO_CODE = {v: k for k, v in SN_SPECIES_MAP.items()}


@dataclass
class NativeTree:
    """Tree data from native FVS output.
    
    Mimics the pyfvs Tree class interface for compatibility.
    """
    dbh: float
    height: float
    species: str
    age: int = 0
    crown_ratio: float = 0.5
    tpa: float = 1.0  # Trees per acre this tree represents
    
    # Growth since last period
    dg: float = 0.0  # Diameter growth
    htg: float = 0.0  # Height growth
    
    def get_volume(self, volume_type: str = 'total_cubic') -> float:
        """Calculate tree volume.
        
        For now, uses simple regression. Future: get from FVS directly.
        """
        # Simple cubic volume estimate (Schumacher-Hall form)
        # V = b0 * DBH^b1 * H^b2
        if self.dbh < 1.0 or self.height < 4.5:
            return 0.0
        
        if volume_type == 'total_cubic':
            # Rough pine volume equation
            return 0.002 * (self.dbh ** 2) * self.height
        elif volume_type == 'merchantable_cubic':
            if self.dbh < 5.0:
                return 0.0
            return 0.0015 * (self.dbh ** 2) * self.height
        elif volume_type == 'board_foot':
            if self.dbh < 9.0:
                return 0.0
            return 0.05 * (self.dbh ** 2) * self.height
        else:
            return 0.0


class NativeStand:
    """Stand class using official FVS Fortran library for growth projections.
    
    Provides the same API as pyfvs.Stand but delegates growth calculations
    to the official FVS shared library.
    
    Attributes:
        trees: List of NativeTree objects in the stand
        site_index: Site index in feet (base age 25 for SN)
        age: Current stand age in years
        species: Default species code
        variant: FVS variant code (e.g., 'sn')
    """
    
    def __init__(
        self,
        trees: Optional[List[NativeTree]] = None,
        site_index: float = 70.0,
        species: str = 'LP',
        variant: str = 'sn',
        inv_year: int = 2024,
    ):
        """Initialize a native stand.
        
        Args:
            trees: List of NativeTree objects. If None, creates empty stand.
            site_index: Site index in feet (base age 25 for SN)
            species: Default species code
            variant: FVS variant code (lowercase)
            inv_year: Inventory year for FVS simulation
        """
        self.trees = trees if trees is not None else []
        self.site_index = site_index
        self.species = species.upper()
        self.variant = variant.lower()
        self.inv_year = inv_year
        self.age = 0
        
        # FVS library handle (lazy loaded)
        self._fvs: Optional[FVSLibrary] = None
        
        # Cached summary data from last run
        self._last_summaries: List[Dict] = []
        
        # Track keyword file for debugging
        self._last_keyword_file: Optional[str] = None
        
    @classmethod
    def initialize_planted(
        cls,
        trees_per_acre: int,
        site_index: float = 70.0,
        species: str = 'LP',
        variant: str = 'sn',
        inv_year: int = 2024,
        initial_dbh: float = 0.5,
        initial_height: float = 1.0,
    ) -> 'NativeStand':
        """Create a new planted stand.
        
        Args:
            trees_per_acre: Number of trees per acre to plant
            site_index: Site index in feet (base age 25 for SN)
            species: Species code for the plantation
            variant: FVS variant code (lowercase)
            inv_year: Inventory year
            initial_dbh: Initial DBH (inches) for seedlings
            initial_height: Initial height (feet) for seedlings
            
        Returns:
            NativeStand: New stand instance
        """
        if trees_per_acre <= 0:
            raise ValueError(f"trees_per_acre must be positive, got {trees_per_acre}")
        
        # Create tree records
        # In FVS, each tree record can represent multiple trees via TPA
        # For efficiency, we use one tree record with TPA = trees_per_acre
        trees = [
            NativeTree(
                dbh=initial_dbh,
                height=initial_height,
                species=species.upper(),
                tpa=float(trees_per_acre),
                crown_ratio=0.85,
            )
        ]
        
        return cls(
            trees=trees,
            site_index=site_index,
            species=species.upper(),
            variant=variant,
            inv_year=inv_year,
        )
    
    def _get_fvs(self) -> FVSLibrary:
        """Get or create the FVS library handle."""
        if self._fvs is None:
            self._fvs = FVSLibrary(self.variant)
        return self._fvs
    
    def _get_species_sequence(self, species_code: str) -> int:
        """Convert pyfvs species code to FVS sequence number."""
        code = species_code.upper()
        if code in SN_SPECIES_MAP:
            return SN_SPECIES_MAP[code]
        # Default to loblolly pine if unknown
        logger.warning(f"Unknown species code '{code}', defaulting to LP (13)")
        return 13
    
    def _generate_keyword_file(self, num_cycles: int = 5) -> str:
        """Generate FVS keyword file content for the current stand.
        
        Uses the PLANT keyword for initial tree establishment, which is more
        reliable than TREELIST for planted stands with uniform initial conditions.
        
        Args:
            num_cycles: Number of 5-year growth cycles to simulate
            
        Returns:
            Keyword file content as string
            
        FVS Keyword Reference:
        - STDIDENT: Stand identification
        - SITECODE: Site index by species (species_seq, site_index)
        - INVYEAR: Inventory year
        - NUMCYCLE: Number of projection cycles
        - ESTAB/PLANT: Establishment model for planted trees
        """
        lines = []
        
        # Stand identification
        lines.append("STDIDENT")
        lines.append("PYFVS001  PyFVS Native Stand")
        
        # Site index - use SITECODE for species-specific SI
        species_seq = self._get_species_sequence(self.species)
        lines.append(f"SITECODE          {species_seq}        {self.site_index:.0f}.")
        
        # Stand info for proper initialization
        lines.append("STDINFO                  m9999")
        
        # Maximum SDI for the species
        lines.append("SDIMAX                    450.")
        
        # Indicate no existing trees (will use PLANT keyword)
        lines.append("NOTREES")
        
        # Inventory year
        lines.append(f"INVYEAR         {self.inv_year}")
        
        # Number of cycles
        lines.append(f"NUMCYCLE           {num_cycles}")
        
        # Use ESTAB/PLANT keywords to establish trees
        if self.trees:
            lines.append("ESTAB")
            
            for tree in self.trees:
                species_seq = self._get_species_sequence(tree.species)
                # PLANT keyword format:
                # PLANT  year  species_seq  trees_per_acre  [height] [shade_code]
                # If height not specified, FVS uses default seedling height
                tpa = int(tree.tpa) if tree.tpa >= 1 else 1
                
                if tree.height > 1.5:  # Specify height if not default seedling
                    lines.append(f"PLANT           {self.inv_year}        {species_seq}       {tpa}       {tree.height:.1f}")
                else:
                    lines.append(f"PLANT           {self.inv_year}        {species_seq}       {tpa}")
            
            lines.append("END")
        
        # Process the simulation
        lines.append("PROCESS")
        
        # Stop
        lines.append("STOP")
        
        return "\n".join(lines)
    
    def grow(self, years: int = 5) -> None:
        """Grow the stand for specified number of years.
        
        Uses the official FVS library to project growth.
        
        Args:
            years: Number of years to grow (will be rounded to 5-year cycles)
        """
        if years <= 0:
            return
        
        # Calculate number of 5-year cycles
        num_cycles = max(1, (years + 2) // 5)  # Round to nearest
        actual_years = num_cycles * 5
        
        # Generate keyword file
        keyword_content = self._generate_keyword_file(num_cycles)
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.key',
            delete=False
        ) as f:
            f.write(keyword_content)
            keyword_path = f.name
        
        self._last_keyword_file = keyword_path
        
        try:
            # Create fresh FVS instance for each run
            fvs = FVSLibrary(self.variant)
            
            # Run FVS
            rtn = fvs.run(f'--keywordfile={keyword_path}')
            
            if rtn not in (0, 1):  # 0 = success, 1 = normal end
                raise FVSError(f"FVS run failed with code {rtn}")
            
            # Get results
            self._last_summaries = fvs.get_all_summaries()
            
            # Update stand state from final cycle
            self._update_from_fvs(fvs, num_cycles)
            
            # Update age
            self.age += actual_years
            
        finally:
            # Clean up temp file
            try:
                os.unlink(keyword_path)
            except OSError:
                pass
    
    def _update_from_fvs(self, fvs: FVSLibrary, cycle: int) -> None:
        """Update stand state from FVS tree data after simulation.
        
        Args:
            fvs: FVS library handle after running simulation
            cycle: Cycle number to get data from
        """
        # Get tree data from FVS
        tree_data = fvs.get_tree_data()
        
        if not tree_data or 'dbh' not in tree_data:
            logger.warning("No tree data returned from FVS")
            return
        
        # Update or create trees
        ntrees = len(tree_data.get('dbh', []))
        new_trees = []
        
        for i in range(ntrees):
            # Get species code from sequence
            species_seq = int(tree_data.get('species', [13])[i])
            species_code = SN_SEQUENCE_TO_CODE.get(species_seq, 'LP')
            
            tree = NativeTree(
                dbh=float(tree_data['dbh'][i]),
                height=float(tree_data['ht'][i]) if 'ht' in tree_data else 0.0,
                species=species_code,
                tpa=float(tree_data['tpa'][i]) if 'tpa' in tree_data else 1.0,
                crown_ratio=float(tree_data['cratio'][i]) / 100.0 if 'cratio' in tree_data else 0.5,
                dg=float(tree_data['dg'][i]) if 'dg' in tree_data else 0.0,
                htg=float(tree_data['htg'][i]) if 'htg' in tree_data else 0.0,
            )
            new_trees.append(tree)
        
        self.trees = new_trees
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive stand metrics.
        
        Returns:
            Dictionary with all stand metrics
        """
        if not self.trees:
            return {
                'tpa': 0,
                'basal_area': 0.0,
                'qmd': 0.0,
                'mean_dbh': 0.0,
                'top_height': 0.0,
                'mean_height': 0.0,
                'ccf': 0.0,
                'sdi': 0.0,
                'age': self.age,
                'volume': 0.0,
                'merchantable_volume': 0.0,
                'board_feet': 0.0,
            }
        
        # Calculate from tree list
        import math
        
        total_tpa = sum(t.tpa for t in self.trees)
        total_ba = sum(t.tpa * 0.005454 * t.dbh ** 2 for t in self.trees)
        sum_dbh_sq_tpa = sum(t.tpa * t.dbh ** 2 for t in self.trees)
        qmd = math.sqrt(sum_dbh_sq_tpa / total_tpa) if total_tpa > 0 else 0.0
        
        mean_dbh = sum(t.tpa * t.dbh for t in self.trees) / total_tpa if total_tpa > 0 else 0.0
        mean_height = sum(t.tpa * t.height for t in self.trees) / total_tpa if total_tpa > 0 else 0.0
        
        # Top height (weighted average of tallest trees)
        sorted_trees = sorted(self.trees, key=lambda t: t.dbh, reverse=True)
        top_n = min(40, len(sorted_trees))
        top_height = sum(t.height for t in sorted_trees[:top_n]) / top_n if top_n > 0 else 0.0
        
        # SDI (Reineke's equation)
        sdi = total_ba * (10.0 / qmd) ** 1.605 if qmd > 0 else 0.0
        
        # CCF (rough estimate)
        ccf = total_ba * 3.0  # Approximate
        
        # Volumes
        volume = sum(t.tpa * t.get_volume('total_cubic') for t in self.trees)
        merch_volume = sum(t.tpa * t.get_volume('merchantable_cubic') for t in self.trees)
        board_feet = sum(t.tpa * t.get_volume('board_foot') for t in self.trees)
        
        # Get from FVS summary if available
        if self._last_summaries:
            last_summary = self._last_summaries[-1]
            return {
                'tpa': last_summary.get('tpa', int(total_tpa)),
                'basal_area': last_summary.get('ba', total_ba),
                'qmd': qmd,
                'mean_dbh': mean_dbh,
                'top_height': last_summary.get('topht', top_height),
                'mean_height': mean_height,
                'ccf': last_summary.get('ccf', ccf),
                'sdi': sdi,
                'age': self.age,
                'volume': last_summary.get('tcuft', volume),
                'merchantable_volume': last_summary.get('mcuft', merch_volume),
                'board_feet': last_summary.get('bdft', board_feet),
            }
        
        return {
            'tpa': int(total_tpa),
            'basal_area': total_ba,
            'qmd': qmd,
            'mean_dbh': mean_dbh,
            'top_height': top_height,
            'mean_height': mean_height,
            'ccf': ccf,
            'sdi': sdi,
            'age': self.age,
            'volume': volume,
            'merchantable_volume': merch_volume,
            'board_feet': board_feet,
        }
    
    def get_summary(self, cycle: int = -1) -> Dict[str, Any]:
        """Get FVS summary for a specific cycle.
        
        Args:
            cycle: Cycle number (0-indexed). -1 for last cycle.
            
        Returns:
            Summary dictionary from FVS
        """
        if not self._last_summaries:
            return {}
        
        if cycle == -1:
            return self._last_summaries[-1]
        
        if 0 <= cycle < len(self._last_summaries):
            return self._last_summaries[cycle]
        
        return {}
    
    def get_all_summaries(self) -> List[Dict[str, Any]]:
        """Get all FVS summaries from last run.
        
        Returns:
            List of summary dictionaries, one per cycle
        """
        return self._last_summaries.copy()
    
    def print_summary(self) -> str:
        """Print formatted summary table.
        
        Returns:
            Formatted summary string
        """
        if not self._last_summaries:
            return "No summary data available. Run grow() first."
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"FVS {self.variant.upper()} Native Stand Summary")
        lines.append(f"Species: {self.species}, Site Index: {self.site_index}")
        lines.append("=" * 80)
        lines.append(
            f"{'Year':>6} {'Age':>4} {'TPA':>6} {'BA':>5} {'TopHt':>5} "
            f"{'TCuFt':>7} {'MCuFt':>7} {'BdFt':>7}"
        )
        lines.append("-" * 80)
        
        for s in self._last_summaries:
            lines.append(
                f"{s.get('year', 0):>6} {s.get('age', 0):>4} "
                f"{s.get('tpa', 0):>6} {s.get('ba', 0):>5} "
                f"{s.get('topht', 0):>5} {s.get('tcuft', 0):>7} "
                f"{s.get('mcuft', 0):>7} {s.get('bdft', 0):>7}"
            )
        
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        total_tpa = sum(t.tpa for t in self.trees)
        return (
            f"NativeStand(variant='{self.variant}', species='{self.species}', "
            f"tpa={total_tpa:.0f}, age={self.age}, si={self.site_index})"
        )


# ================================================================
# Convenience Functions
# ================================================================

def create_native_stand(
    trees_per_acre: int = 500,
    site_index: float = 70.0,
    species: str = 'LP',
    variant: str = 'sn',
) -> NativeStand:
    """Convenience function to create a planted native stand.
    
    Args:
        trees_per_acre: Initial planting density
        site_index: Site index in feet
        species: Species code
        variant: FVS variant code
        
    Returns:
        NativeStand instance
    """
    return NativeStand.initialize_planted(
        trees_per_acre=trees_per_acre,
        site_index=site_index,
        species=species,
        variant=variant,
    )


def compare_native_vs_python(
    trees_per_acre: int = 500,
    site_index: float = 70.0,
    species: str = 'LP',
    years: int = 25,
) -> Dict[str, Dict]:
    """Compare native FVS results to Python implementation.
    
    Args:
        trees_per_acre: Initial planting density
        site_index: Site index
        species: Species code
        years: Years to project
        
    Returns:
        Dictionary with 'native' and 'python' metrics
    """
    from .stand import Stand
    
    # Run native FVS
    native = NativeStand.initialize_planted(trees_per_acre, site_index, species)
    native.grow(years)
    native_metrics = native.get_metrics()
    
    # Run Python implementation
    python = Stand.initialize_planted(trees_per_acre, site_index, species)
    python.grow(years)
    python_metrics = python.get_metrics()
    
    return {
        'native': native_metrics,
        'python': python_metrics,
        'differences': {
            key: native_metrics.get(key, 0) - python_metrics.get(key, 0)
            for key in native_metrics
            if isinstance(native_metrics.get(key), (int, float))
        }
    }


# ================================================================
# Module Testing
# ================================================================

if __name__ == '__main__':
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    print("NativeStand - FVS Bridge Module")
    print("=" * 40)
    
    # Check for available FVS libraries
    available = find_fvs_libraries()
    if not available:
        print("ERROR: No FVS libraries found!")
        print("Build them with: cd ~/src/fvs-official/bin && make")
        sys.exit(1)
    
    print(f"Available FVS variants: {list(available.keys())}")
    
    # Test with SN variant if available
    if 'sn' in available:
        print("\nTesting NativeStand with SN variant...")
        
        stand = NativeStand.initialize_planted(
            trees_per_acre=500,
            site_index=70,
            species='LP',
            variant='sn'
        )
        
        print(f"Created: {stand}")
        print(f"Initial metrics: {stand.get_metrics()}")
        
        # Grow for 25 years
        print("\nGrowing for 25 years...")
        stand.grow(years=25)
        
        print(f"After growth: {stand}")
        print(f"Final metrics: {stand.get_metrics()}")
        print("\nSummary table:")
        print(stand.print_summary())
    else:
        print("SN variant not available for testing")

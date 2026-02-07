"""
fvs_native.py - Python bindings for the official USDA FVS Fortran library

This module provides ctypes-based bindings to the official USDA Forest
Vegetation Simulator (FVS) shared library, enabling pyfvs to call
authoritative FVS code instead of maintaining parallel Python implementations.

Usage:
    from pyfvs.fvs_native import FVSLibrary
    
    # Initialize with SN variant
    fvs = FVSLibrary('sn')
    
    # Run simulation from keyword file
    fvs.run('--keywordfile=mystand.key')
    
    # Or run programmatically
    fvs.init()
    fvs.add_trees(dbh=[10.0, 15.0], species=[1, 1], tpa=[100.0, 50.0])
    fvs.run_cycle()
    results = fvs.get_tree_data()

Author: Claude (Anthropic) for OpenClaw
Date: 2026-02-07
"""

import ctypes
from ctypes import c_int, c_double, c_char, c_char_p, POINTER, byref
import os
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple, Union
import numpy as np

logger = logging.getLogger(__name__)

# Default library search paths
DEFAULT_LIB_PATHS = [
    Path.home() / "src" / "fvs-official" / "bin",
    Path("/usr/local/lib"),
    Path("/usr/lib"),
]


class FVSError(Exception):
    """Exception raised when FVS returns an error code."""
    pass


class FVSLibrary:
    """
    Python wrapper for the USDA FVS Fortran shared library.
    
    This class provides high-level Python access to FVS functions including:
    - Initialization and simulation control
    - Tree and stand data access
    - Growth projection functions
    - Species and stand attribute management
    
    Attributes:
        variant: FVS variant code (e.g., 'sn', 'pn', 'ie')
        lib: The loaded ctypes CDLL library handle
    """
    
    # Variant-specific information
    VARIANTS = {
        'ak': 'Alaska',
        'bc': 'British Columbia', 
        'bm': 'Blue Mountains',
        'ca': 'California',
        'ci': 'Central Idaho',
        'cr': 'Central Rockies',
        'cs': 'Central States',
        'ec': 'East Cascades',
        'em': 'Eastern Montana',
        'ie': 'Inland Empire',
        'kt': 'Kootenai',
        'ls': 'Lake States',
        'nc': 'Northern California',
        'ne': 'Northeast',
        'oc': 'Oregon Coast',
        'on': 'Ontario',
        'op': 'Olympic Peninsula',
        'pn': 'Pacific Northwest',
        'sn': 'Southern',
        'so': 'South Oregon/Northeast California',
        'tt': 'Tetons',
        'ut': 'Utah',
        'wc': 'West Cascades',
        'ws': 'Western Sierra',
    }
    
    def __init__(self, variant: str = 'sn', lib_path: Optional[Path] = None):
        """
        Initialize the FVS library wrapper.
        
        Args:
            variant: FVS variant code (e.g., 'sn' for Southern)
            lib_path: Optional path to library directory. If None, searches
                     default paths.
        
        Raises:
            FileNotFoundError: If the FVS shared library cannot be found
            OSError: If the library fails to load
        """
        self.variant = variant.lower()
        if self.variant not in self.VARIANTS:
            logger.warning(f"Unknown variant '{variant}'. Known variants: {list(self.VARIANTS.keys())}")
        
        self.lib_path = self._find_library(lib_path)
        self.lib = self._load_library()
        self._setup_functions()
        
        # State tracking
        self._initialized = False
        self._current_cycle = 0
        
    def _find_library(self, lib_path: Optional[Path] = None) -> Path:
        """Find the FVS shared library file."""
        lib_name = f"FVS{self.variant}.so"
        
        search_paths = [lib_path] if lib_path else DEFAULT_LIB_PATHS
        
        for path in search_paths:
            if path is None:
                continue
            full_path = Path(path) / lib_name
            if full_path.exists():
                logger.info(f"Found FVS library: {full_path}")
                return full_path
                
        # Also check LD_LIBRARY_PATH
        ld_path = os.environ.get('LD_LIBRARY_PATH', '')
        for path in ld_path.split(':'):
            if path:
                full_path = Path(path) / lib_name
                if full_path.exists():
                    return full_path
        
        raise FileNotFoundError(
            f"Could not find FVS library '{lib_name}'. "
            f"Searched: {[str(p) for p in search_paths if p]}"
        )
    
    def _load_library(self) -> ctypes.CDLL:
        """Load the FVS shared library."""
        try:
            lib = ctypes.CDLL(str(self.lib_path))
            logger.info(f"Loaded FVS library: {self.lib_path}")
            return lib
        except OSError as e:
            raise OSError(f"Failed to load FVS library: {e}")
    
    def _setup_functions(self):
        """Configure ctypes function signatures for FVS API functions."""
        
        # ============================================================
        # Initialization and Control Functions
        # ============================================================
        
        # fvsSetCmdLineC(theCmdLine, lenCL, IRTNCD)
        # Note: C-callable versions use lowercase with C suffix
        try:
            self._fvsSetCmdLineC = self.lib.fvsSetCmdLineC
            self._fvsSetCmdLineC.argtypes = [c_char_p, POINTER(c_int), POINTER(c_int)]
            self._fvsSetCmdLineC.restype = None
        except AttributeError:
            # Fall back to Fortran naming
            self._fvsSetCmdLineC = self.lib.fvssetcmdline_
            self._fvsSetCmdLineC.argtypes = [c_char_p, POINTER(c_int), POINTER(c_int)]
            self._fvsSetCmdLineC.restype = None
        
        # fvsGetRtnCode(rtnCode)
        self._fvsGetRtnCode = self.lib.fvsgetrtncode_
        self._fvsGetRtnCode.argtypes = [POINTER(c_int)]
        self._fvsGetRtnCode.restype = None
        
        # fvsRestart(restrtcd)
        self._fvsRestart = self.lib.fvsrestart_
        self._fvsRestart.argtypes = [POINTER(c_int)]
        self._fvsRestart.restype = None
        
        # Main FVS entry point: fvs_(IRTNCD)
        self._fvs = self.lib.fvs_
        self._fvs.argtypes = [POINTER(c_int)]
        self._fvs.restype = None
        
        # ============================================================
        # Dimension Information
        # ============================================================
        
        # fvsDimSizes(ntrees, ncycles, nplots, maxtrees, maxspecies, maxplots, maxcycles)
        self._fvsDimSizes = self.lib.fvsdimsizes_
        self._fvsDimSizes.argtypes = [
            POINTER(c_int), POINTER(c_int), POINTER(c_int),
            POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_int)
        ]
        self._fvsDimSizes.restype = None
        
        # ============================================================
        # Tree Attribute Access (C-callable versions)
        # ============================================================
        
        # fvsTreeAttrC(name, nch, action, ntrees, attr, rtnCode)
        try:
            self._fvsTreeAttrC = self.lib.fvsTreeAttrC
        except AttributeError:
            self._fvsTreeAttrC = self.lib.fvstreeattr_
        self._fvsTreeAttrC.argtypes = [
            c_char_p, POINTER(c_int), c_char_p, 
            POINTER(c_int), POINTER(c_double), POINTER(c_int)
        ]
        self._fvsTreeAttrC.restype = None
        
        # ============================================================
        # Species Attribute Access
        # ============================================================
        
        try:
            self._fvsSpeciesAttrC = self.lib.fvsSpeciesAttrC
        except AttributeError:
            self._fvsSpeciesAttrC = self.lib.fvsspeciesattr_
        self._fvsSpeciesAttrC.argtypes = [
            c_char_p, POINTER(c_int), c_char_p,
            POINTER(c_double), POINTER(c_int)
        ]
        self._fvsSpeciesAttrC.restype = None
        
        # ============================================================
        # Summary Data
        # ============================================================
        
        # fvsSummary(summary, icycle, ncycles, maxrow, maxcol, rtnCode)
        self._fvsSummary = self.lib.fvssummary_
        self._fvsSummary.argtypes = [
            POINTER(c_int), POINTER(c_int), POINTER(c_int),
            POINTER(c_int), POINTER(c_int), POINTER(c_int)
        ]
        self._fvsSummary.restype = None
        
        # ============================================================
        # Tree Manipulation
        # ============================================================
        
        # fvsAddTrees - complex signature, set up carefully
        self._fvsAddTrees = self.lib.fvsaddtrees_
        
        # fvsCutTrees(pToCut, ntrees, rtnCode)
        self._fvsCutTrees = self.lib.fvscuttrees_
        self._fvsCutTrees.argtypes = [
            POINTER(c_double), POINTER(c_int), POINTER(c_int)
        ]
        self._fvsCutTrees.restype = None
        
        # ============================================================
        # Low-level Growth Functions (variant-specific, work on COMMON blocks)
        # ============================================================
        
        # bratio_(ispc, d, ht) -> REAL
        try:
            self._bratio = self.lib.bratio_
            self._bratio.argtypes = [POINTER(c_int), POINTER(c_double), POINTER(c_double)]
            self._bratio.restype = c_double  # Actually REAL but we use double for safety
        except AttributeError:
            self._bratio = None
            logger.warning("bratio_ not found in library")
        
        logger.debug("FVS function signatures configured")
    
    # ================================================================
    # High-Level API Methods
    # ================================================================
    
    def set_cmdline(self, cmdline: str) -> int:
        """
        Set the FVS command line parameters.
        
        Args:
            cmdline: Command line string (e.g., '--keywordfile=stand.key')
        
        Returns:
            Return code (0 = success)
        """
        cmd_bytes = cmdline.encode('utf-8')
        len_cl = c_int(len(cmd_bytes))
        rtn_code = c_int(-1)
        
        self._fvsSetCmdLineC(cmd_bytes, byref(len_cl), byref(rtn_code))
        
        if rtn_code.value != 0:
            logger.warning(f"fvsSetCmdLine returned code: {rtn_code.value}")
        
        return rtn_code.value
    
    def get_rtn_code(self) -> int:
        """Get the current FVS return code."""
        rtn_code = c_int(-1)
        self._fvsGetRtnCode(byref(rtn_code))
        return rtn_code.value
    
    def restart(self) -> int:
        """
        Restart FVS for another simulation.
        
        Note: FVS restart behavior is complex. For independent simulations,
        it may be better to create a new FVSLibrary instance.
        
        Returns:
            Restart code (0 = success, -1 = error)
        """
        restart_code = c_int(0)
        self._fvsRestart(byref(restart_code))
        return restart_code.value
    
    def run(self, cmdline: Optional[str] = None) -> int:
        """
        Run a full FVS simulation.
        
        Args:
            cmdline: Optional command line string. If provided, sets it first.
        
        Returns:
            Return code (0 = success, 1 = normal end, 2 = error)
        """
        if cmdline:
            rtn = self.set_cmdline(cmdline)
            if rtn != 0:
                raise FVSError(f"Failed to set command line: {rtn}")
        
        rtn_code = c_int(0)
        self._fvs(byref(rtn_code))
        
        self._initialized = True
        return rtn_code.value
    
    def get_dimensions(self) -> Dict[str, int]:
        """
        Get current FVS dimension information.
        
        Returns:
            Dictionary with keys:
            - ntrees: Current number of trees
            - ncycles: Number of cycles
            - nplots: Number of plots
            - maxtrees: Maximum trees allowed
            - maxspecies: Maximum species
            - maxplots: Maximum plots
            - maxcycles: Maximum cycles
        """
        ntrees = c_int(0)
        ncycles = c_int(0)
        nplots = c_int(0)
        maxtrees = c_int(0)
        maxspecies = c_int(0)
        maxplots = c_int(0)
        maxcycles = c_int(0)
        
        self._fvsDimSizes(
            byref(ntrees), byref(ncycles), byref(nplots),
            byref(maxtrees), byref(maxspecies), byref(maxplots), byref(maxcycles)
        )
        
        return {
            'ntrees': ntrees.value,
            'ncycles': ncycles.value,
            'nplots': nplots.value,
            'maxtrees': maxtrees.value,
            'maxspecies': maxspecies.value,
            'maxplots': maxplots.value,
            'maxcycles': maxcycles.value,
        }
    
    def get_tree_attr(self, name: str, ntrees: Optional[int] = None) -> np.ndarray:
        """
        Get a tree attribute array.
        
        Args:
            name: Attribute name. Valid names include:
                  'tpa', 'dbh', 'ht', 'dg', 'htg', 'cratio', 'species',
                  'age', 'mort', 'tcuft', 'mcuft', 'scuft', 'bdft', etc.
            ntrees: Number of trees. If None, queries from FVS.
        
        Returns:
            NumPy array of attribute values
        """
        if ntrees is None:
            dims = self.get_dimensions()
            ntrees = dims['ntrees']
        
        if ntrees == 0:
            return np.array([])
        
        name_bytes = name.encode('utf-8')
        nch = c_int(len(name_bytes))
        action = b'get'
        ntrees_c = c_int(ntrees)
        attr = (c_double * ntrees)()
        rtn_code = c_int(0)
        
        self._fvsTreeAttrC(
            name_bytes, byref(nch), action,
            byref(ntrees_c), attr, byref(rtn_code)
        )
        
        if rtn_code.value != 0:
            raise FVSError(f"Failed to get tree attribute '{name}': code {rtn_code.value}")
        
        return np.array(attr[:ntrees])
    
    def set_tree_attr(self, name: str, values: np.ndarray) -> None:
        """
        Set a tree attribute array.
        
        Args:
            name: Attribute name
            values: NumPy array of values to set
        """
        ntrees = len(values)
        name_bytes = name.encode('utf-8')
        nch = c_int(len(name_bytes))
        action = b'set'
        ntrees_c = c_int(ntrees)
        attr = (c_double * ntrees)(*values)
        rtn_code = c_int(0)
        
        self._fvsTreeAttrC(
            name_bytes, byref(nch), action,
            byref(ntrees_c), attr, byref(rtn_code)
        )
        
        if rtn_code.value != 0:
            raise FVSError(f"Failed to set tree attribute '{name}': code {rtn_code.value}")
    
    def get_tree_data(self) -> Dict[str, np.ndarray]:
        """
        Get all commonly used tree data as a dictionary of arrays.
        
        Returns:
            Dictionary with tree attribute arrays
        """
        dims = self.get_dimensions()
        ntrees = dims['ntrees']
        
        if ntrees == 0:
            return {}
        
        attrs = ['tpa', 'dbh', 'ht', 'dg', 'htg', 'cratio', 'species', 'age']
        result = {}
        
        for attr in attrs:
            try:
                result[attr] = self.get_tree_attr(attr, ntrees)
            except FVSError:
                logger.warning(f"Could not get attribute '{attr}'")
        
        return result
    
    def get_species_attr(self, name: str, maxspecies: Optional[int] = None) -> np.ndarray:
        """
        Get a species-level attribute array.
        
        Args:
            name: Attribute name (e.g., 'spsiteindx', 'spsdi')
            maxspecies: Number of species. If None, queries from FVS.
        
        Returns:
            NumPy array of attribute values (one per species)
        """
        if maxspecies is None:
            dims = self.get_dimensions()
            maxspecies = dims['maxspecies']
        
        name_bytes = name.encode('utf-8')
        nch = c_int(len(name_bytes))
        action = b'get'
        attr = (c_double * maxspecies)()
        rtn_code = c_int(0)
        
        self._fvsSpeciesAttrC(
            name_bytes, byref(nch), action,
            attr, byref(rtn_code)
        )
        
        if rtn_code.value != 0:
            raise FVSError(f"Failed to get species attribute '{name}': code {rtn_code.value}")
        
        return np.array(attr[:maxspecies])
    
    def get_summary(self, cycle: int) -> Dict[str, int]:
        """
        Get summary statistics for a specific cycle.
        
        Args:
            cycle: Cycle number (1-indexed)
        
        Returns:
            Dictionary with summary statistics (from IOSUM array)
            
        Column definitions (from sumout.f):
            1: year - Simulation year
            2: age - Stand age
            3: tpa - Trees per acre (start of period)
            4: tcuft - Total cubic feet (start of period)
            5: mcuft - Merchantable cubic feet (start of period)
            6: bdft - Board feet sawlog (start of period)
            7: rem_tpa - Removed trees per acre
            8: rem_tcuft - Removed total cubic feet
            9: rem_mcuft - Removed merchantable cubic feet
            10: rem_bdft - Removed board feet sawlog
            11: ba - Basal area per acre (after treatment)
            12: ccf - Crown competition factor (after treatment)
            13: topht - Average dominant height (after treatment)
            14: period_len - Period length in years
            15: accretion - Annual accretion (cuft/acre)
            16: mortality - Annual mortality (cuft/acre)
            17: samwt - Sample weight
            18: fortyp - Forest cover type code
            19: sizecls - Size class
            20: stkcls - Stocking class
            21: scuft - Cubic saw volume (start of period)
            22: rem_scuft - Removed cubic saw volume
        """
        maxcol = 22
        summary = (c_int * maxcol)()
        icycle = c_int(cycle)
        ncycles = c_int(0)
        maxrow = c_int(0)
        maxcol_c = c_int(0)
        rtn_code = c_int(0)
        
        self._fvsSummary(
            summary, byref(icycle), byref(ncycles),
            byref(maxrow), byref(maxcol_c), byref(rtn_code)
        )
        
        if rtn_code.value != 0:
            raise FVSError(f"Failed to get summary for cycle {cycle}: code {rtn_code.value}")
        
        # Summary column names (from sumout.f IOSUM documentation)
        col_names = [
            'year', 'age', 'tpa', 'tcuft', 'mcuft', 'bdft',
            'rem_tpa', 'rem_tcuft', 'rem_mcuft', 'rem_bdft',
            'ba', 'ccf', 'topht', 'period_len', 'accretion', 'mortality',
            'samwt', 'fortyp', 'sizecls', 'stkcls', 'scuft', 'rem_scuft'
        ]
        
        return {name: summary[i] for i, name in enumerate(col_names) if i < maxcol}
    
    def get_all_summaries(self) -> List[Dict[str, int]]:
        """
        Get summary statistics for all cycles.
        
        Returns:
            List of dictionaries, one per cycle
        """
        dims = self.get_dimensions()
        ncycles = dims['ncycles']
        
        results = []
        for cycle in range(1, ncycles + 2):  # +2 because ncycles is index, need end state too
            try:
                results.append(self.get_summary(cycle))
            except FVSError:
                break
        
        return results
    
    def print_summary_table(self) -> str:
        """
        Print a formatted summary table similar to FVS output.
        
        Returns:
            Formatted summary string
        """
        summaries = self.get_all_summaries()
        if not summaries:
            return "No summary data available"
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"FVS {self.variant.upper()} Simulation Summary")
        lines.append("=" * 80)
        lines.append(f"{'Year':>6} {'Age':>4} {'TPA':>6} {'BA':>5} {'TopHt':>5} {'TCuFt':>7} {'MCuFt':>7} {'BdFt':>7} {'Accr':>5} {'Mort':>5}")
        lines.append("-" * 80)
        
        for s in summaries:
            lines.append(
                f"{s['year']:>6} {s['age']:>4} {s['tpa']:>6} {s['ba']:>5} "
                f"{s['topht']:>5} {s['tcuft']:>7} {s['mcuft']:>7} {s['bdft']:>7} "
                f"{s['accretion']:>5} {s['mortality']:>5}"
            )
        
        return "\n".join(lines)
    
    def cut_trees(self, proportion_to_cut: np.ndarray) -> int:
        """
        Mark trees for cutting.
        
        Args:
            proportion_to_cut: Array of proportions (0-1) for each tree
        
        Returns:
            Return code (0 = success)
        """
        ntrees = len(proportion_to_cut)
        pcut = (c_double * ntrees)(*proportion_to_cut)
        ntrees_c = c_int(ntrees)
        rtn_code = c_int(0)
        
        self._fvsCutTrees(pcut, byref(ntrees_c), byref(rtn_code))
        
        return rtn_code.value
    
    # ================================================================
    # Variant Information
    # ================================================================
    
    @classmethod
    def list_variants(cls) -> Dict[str, str]:
        """Return dictionary of available FVS variants and descriptions."""
        return cls.VARIANTS.copy()
    
    @property
    def variant_name(self) -> str:
        """Get the full name of the current variant."""
        return self.VARIANTS.get(self.variant, f"Unknown ({self.variant})")
    
    # ================================================================
    # Context Manager Support
    # ================================================================
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Could add cleanup here if needed
        pass
    
    def __repr__(self):
        return f"FVSLibrary(variant='{self.variant}', lib='{self.lib_path}')"


# ================================================================
# Convenience Functions
# ================================================================

def run_fvs(keywordfile: str, variant: str = 'sn', lib_path: Optional[Path] = None) -> int:
    """
    Run an FVS simulation from a keyword file.
    
    Args:
        keywordfile: Path to keyword file
        variant: FVS variant code
        lib_path: Optional path to library directory
    
    Returns:
        Return code (0 = success)
    """
    with FVSLibrary(variant, lib_path) as fvs:
        return fvs.run(f'--keywordfile={keywordfile}')


def find_fvs_libraries(search_paths: Optional[List[Path]] = None) -> Dict[str, Path]:
    """
    Find all available FVS shared libraries.
    
    Args:
        search_paths: Directories to search. If None, uses defaults.
    
    Returns:
        Dictionary mapping variant codes to library paths
    """
    paths = search_paths or DEFAULT_LIB_PATHS
    found = {}
    
    for variant in FVSLibrary.VARIANTS:
        lib_name = f"FVS{variant}.so"
        for path in paths:
            full_path = Path(path) / lib_name
            if full_path.exists():
                found[variant] = full_path
                break
    
    return found


# ================================================================
# Testing / Demo
# ================================================================

if __name__ == '__main__':
    import sys
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    print("FVS Native Library Python Bindings")
    print("=" * 40)
    
    # Find available libraries
    print("\nSearching for FVS libraries...")
    available = find_fvs_libraries()
    
    if not available:
        print("No FVS libraries found!")
        print("Build them with: cd ~/src/fvs-official/bin && make FVSsn.so")
        sys.exit(1)
    
    print(f"Found {len(available)} variant(s):")
    for variant, path in available.items():
        name = FVSLibrary.VARIANTS.get(variant, 'Unknown')
        print(f"  {variant}: {name} -> {path}")
    
    # Try to load the first available variant
    variant = list(available.keys())[0]
    print(f"\nLoading {variant} variant...")
    
    try:
        fvs = FVSLibrary(variant)
        print(f"Loaded: {fvs}")
        
        # Get dimensions (will be zeros before initialization)
        dims = fvs.get_dimensions()
        print(f"\nDimension info:")
        for key, val in dims.items():
            print(f"  {key}: {val}")
        
        print("\nFVS library loaded successfully!")
        print("To run a simulation: fvs.run('--keywordfile=yourfile.key')")
        
    except Exception as e:
        print(f"Error loading library: {e}")
        sys.exit(1)

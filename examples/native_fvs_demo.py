#!/usr/bin/env python3
"""
Native FVS Demo - Demonstrates using the official USDA FVS Fortran library
from Python through the pyfvs wrapper.

This example shows:
1. Loading the FVS shared library
2. Getting dimension information
3. Running a simulation (if a keyword file is available)
4. Accessing tree and stand data

Prerequisites:
- Build FVS shared library: cd ~/src/fvs-official/bin && make FVSsn.so
- Install pyfvs: cd ~/src/pyfvs && pip install -e .
"""

import sys
import logging
from pathlib import Path

# Add pyfvs to path if not installed
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from pyfvs.fvs_native import FVSLibrary, find_fvs_libraries, FVSError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_library_discovery():
    """Demo: Find available FVS libraries."""
    print("\n" + "=" * 60)
    print("Demo 1: Library Discovery")
    print("=" * 60)
    
    available = find_fvs_libraries()
    
    if not available:
        print("No FVS libraries found!")
        print("\nTo build the SN variant:")
        print("  cd ~/src/fvs-official/bin")
        print("  make FVSsn.so")
        return None
    
    print(f"\nFound {len(available)} FVS variant(s):")
    print("-" * 40)
    
    for variant, path in available.items():
        name = FVSLibrary.VARIANTS.get(variant, 'Unknown')
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  {variant:4s} ({name:25s}): {size_mb:.1f} MB")
    
    return list(available.keys())[0]


def demo_library_loading(variant: str):
    """Demo: Load an FVS library and get basic info."""
    print("\n" + "=" * 60)
    print(f"Demo 2: Loading {variant.upper()} Variant")
    print("=" * 60)
    
    fvs = FVSLibrary(variant)
    print(f"\nLoaded: {fvs}")
    print(f"Variant: {fvs.variant_name}")
    print(f"Library: {fvs.lib_path}")
    
    # Get dimension info (shows max values before simulation)
    dims = fvs.get_dimensions()
    print("\nDimension information:")
    print("-" * 40)
    for key, val in dims.items():
        print(f"  {key:15s}: {val:6d}")
    
    return fvs


def demo_run_simple_simulation(fvs: FVSLibrary):
    """Demo: Create and run a minimal simulation."""
    print("\n" + "=" * 60)
    print("Demo 3: Running a Simulation")
    print("=" * 60)
    
    # Create a minimal keyword file for testing
    keyword_content = """
STDIDENT
DEMO01   Demo Stand for pyfvs Native Wrapper
STDINFO          300     250      50     .01   -999
SITEINDEX         25           90                
INVYEAR         2024
NUMCYCLE           3
TREELIST          15
1    PP    15.3       75    100       0        1       0
2    PP    12.8       60    100       0        1       0
3    PP    10.2       50    100       0        1       0
END
PROCESS
STOP
"""
    
    # Write keyword file to temp location
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as f:
        f.write(keyword_content)
        keyfile = f.name
    
    print(f"\nCreated test keyword file: {keyfile}")
    
    try:
        # Run FVS
        print("\nRunning FVS simulation...")
        rtn = fvs.run(f'--keywordfile={keyfile}')
        print(f"Return code: {rtn}")
        
        # Get updated dimensions
        dims = fvs.get_dimensions()
        print(f"\nAfter simulation:")
        print(f"  Trees: {dims['ntrees']}")
        print(f"  Cycles: {dims['ncycles']}")
        
        # Get tree data if we have trees
        if dims['ntrees'] > 0:
            print("\nTree data:")
            data = fvs.get_tree_data()
            for attr, values in data.items():
                if len(values) > 0:
                    print(f"  {attr}: {values[:3]}...")
        
        # Get summary for cycle 1 if available
        if dims['ncycles'] > 0:
            print("\nCycle 1 summary:")
            try:
                summary = fvs.get_summary(1)
                for key, val in list(summary.items())[:8]:
                    print(f"  {key}: {val}")
            except FVSError as e:
                print(f"  Could not get summary: {e}")
                
    except FVSError as e:
        print(f"FVS Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        import os
        os.unlink(keyfile)


def demo_api_overview():
    """Print an overview of available API functions."""
    print("\n" + "=" * 60)
    print("Demo 4: API Overview")
    print("=" * 60)
    
    print("""
FVSLibrary provides these main methods:

Initialization:
  - FVSLibrary(variant)    : Load FVS library for a variant
  - fvs.run(cmdline)       : Run simulation with command line
  - fvs.set_cmdline(s)     : Set command line parameters
  
Data Access:
  - fvs.get_dimensions()   : Get tree/cycle/species counts
  - fvs.get_tree_attr(n)   : Get tree attribute array
  - fvs.set_tree_attr(n,v) : Set tree attribute array  
  - fvs.get_tree_data()    : Get all common tree attributes
  - fvs.get_species_attr() : Get species-level attributes
  - fvs.get_summary(cycle) : Get cycle summary statistics
  
Tree Manipulation:
  - fvs.cut_trees(p)       : Mark trees for cutting

Available Tree Attributes:
  - tpa      : Trees per acre
  - dbh      : Diameter at breast height
  - ht       : Total height
  - dg       : Diameter growth
  - htg      : Height growth
  - cratio   : Crown ratio (%)
  - species  : Species code
  - age      : Tree age
  - mort     : Mortality prediction
  - tcuft    : Total cubic foot volume
  - mcuft    : Merchantable cubic foot
  - bdft     : Board foot volume
  - defect   : Defect percent

Available Species Attributes:
  - spsiteindx  : Site index by species
  - spsdi       : SDI by species
  - spccf       : CCF by species
  - baimult     : BA growth multiplier
  - htgmult     : Height growth multiplier
  - mortmult    : Mortality multiplier
""")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("  PYFVS Native FVS Library Demo")
    print("  Official USDA Fortran FVS via Python")
    print("=" * 60)
    
    # Demo 1: Find libraries
    variant = demo_library_discovery()
    if not variant:
        return 1
    
    # Demo 2: Load library
    try:
        fvs = demo_library_loading(variant)
    except Exception as e:
        print(f"Failed to load library: {e}")
        return 1
    
    # Demo 3: Run simulation
    demo_run_simple_simulation(fvs)
    
    # Demo 4: API overview
    demo_api_overview()
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60 + "\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

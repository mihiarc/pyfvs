#!/usr/bin/env python3
"""
FVS Native Library Demo
=======================

Demonstrates end-to-end Python integration with the official USDA FVS
Fortran library. This script:

1. Loads the FVS shared library (Southern variant)
2. Runs a simulation from a keyword file
3. Retrieves stand-level summary data
4. Retrieves individual tree data
5. Displays results in formatted tables

Requirements:
- FVSsn.so compiled in ~/src/fvs-official/bin/
- Test keyword file available

Usage:
    python fvs_native_demo.py [keyword_file]
    
If no keyword file specified, uses the standard test file.

Author: Claude (Anthropic) for OpenClaw
Date: 2026-02-07
"""

import sys
import os
from pathlib import Path

# Add pyfvs to path
sys.path.insert(0, str(Path.home() / "src" / "pyfvs" / "src"))

# Import directly to avoid yaml dependency in main package
import ctypes
from ctypes import c_int, c_double, c_char, c_char_p, POINTER, byref
import numpy as np

# Load the fvs_native module
_fvs_native_path = Path.home() / "src" / "pyfvs" / "src" / "pyfvs" / "fvs_native.py"
exec(open(_fvs_native_path).read().split("if __name__")[0])


def print_tree_distribution(tree_data: dict, bins: int = 10):
    """Print a simple DBH distribution."""
    dbh = tree_data.get('dbh', np.array([]))
    tpa = tree_data.get('tpa', np.array([]))
    
    if len(dbh) == 0:
        print("  No tree data available")
        return
    
    # Create DBH classes
    dbh_min, dbh_max = dbh.min(), dbh.max()
    bin_edges = np.linspace(dbh_min, dbh_max + 0.1, bins + 1)
    
    print(f"\n{'DBH Class':>12} {'Trees/Acre':>12} {'Count':>8}")
    print("-" * 36)
    
    for i in range(bins):
        lo, hi = bin_edges[i], bin_edges[i+1]
        mask = (dbh >= lo) & (dbh < hi)
        count = mask.sum()
        tpa_sum = tpa[mask].sum()
        if count > 0:
            print(f"  {lo:5.1f}-{hi:5.1f}   {tpa_sum:10.1f}   {count:6d}")


def print_species_summary(tree_data: dict):
    """Print summary by species."""
    species = tree_data.get('species', np.array([]))
    tpa = tree_data.get('tpa', np.array([]))
    dbh = tree_data.get('dbh', np.array([]))
    
    if len(species) == 0:
        print("  No tree data available")
        return
    
    # SN variant species codes (subset)
    species_names = {
        1: 'FR', 22: 'LL', 23: 'TM', 24: 'PP', 26: 'SP', 
        40: 'WO', 41: 'SO', 43: 'SK', 47: 'RO', 48: 'BO',
        50: 'YP', 51: 'SY', 52: 'HI', 53: 'BE', 89: 'OH'
    }
    
    unique_sp = np.unique(species.astype(int))
    
    print(f"\n{'Species':>8} {'Name':>6} {'TPA':>10} {'Avg DBH':>10} {'Count':>8}")
    print("-" * 50)
    
    for sp in unique_sp:
        mask = species.astype(int) == sp
        count = mask.sum()
        tpa_sum = tpa[mask].sum()
        avg_dbh = dbh[mask].mean()
        name = species_names.get(sp, '??')
        print(f"  {sp:6d}   {name:>4}   {tpa_sum:8.1f}   {avg_dbh:8.1f}   {count:6d}")


def main():
    print("=" * 70)
    print("FVS Native Library Python Integration Demo")
    print("=" * 70)
    
    # Determine keyword file
    if len(sys.argv) > 1:
        keyfile = sys.argv[1]
    else:
        keyfile = str(Path.home() / "src" / "fvs-official" / "tests" / "FVSsn" / "snt01.key")
    
    if not os.path.exists(keyfile):
        print(f"ERROR: Keyword file not found: {keyfile}")
        sys.exit(1)
    
    print(f"\nKeyword file: {keyfile}")
    
    # Load FVS library
    print("\n[1] Loading FVS Southern Variant library...")
    try:
        fvs = FVSLibrary('sn')
        print(f"    Loaded: {fvs.lib_path}")
    except Exception as e:
        print(f"    ERROR: {e}")
        sys.exit(1)
    
    # Check initial state
    dims = fvs.get_dimensions()
    print(f"    Max trees: {dims['maxtrees']}, Max species: {dims['maxspecies']}")
    
    # Run simulation
    print("\n[2] Running FVS simulation...")
    print("-" * 70)
    
    rtn = fvs.run(f'--keywordfile={keyfile}')
    
    print("-" * 70)
    print(f"    Return code: {rtn}")
    
    # Get post-simulation dimensions
    dims = fvs.get_dimensions()
    print(f"    Trees: {dims['ntrees']}, Cycles: {dims['ncycles']}, Plots: {dims['nplots']}")
    
    # Display summary table
    print("\n[3] Stand Summary Table")
    print(fvs.print_summary_table())
    
    # Get tree-level data
    print("\n[4] Tree-Level Data")
    tree_data = fvs.get_tree_data()
    
    print(f"\n    Total tree records: {dims['ntrees']}")
    print(f"    Total TPA: {tree_data['tpa'].sum():.1f}")
    
    # Attribute statistics
    print(f"\n{'Attribute':>12} {'Min':>10} {'Max':>10} {'Mean':>10} {'Std':>10}")
    print("-" * 56)
    for attr in ['dbh', 'ht', 'tpa', 'cratio', 'age']:
        if attr in tree_data:
            arr = tree_data[attr]
            print(f"  {attr:>10} {arr.min():>10.1f} {arr.max():>10.1f} {arr.mean():>10.1f} {arr.std():>10.1f}")
    
    # DBH distribution
    print("\n[5] DBH Distribution")
    print_tree_distribution(tree_data, bins=8)
    
    # Species summary
    print("\n[6] Species Summary")
    print_species_summary(tree_data)
    
    # Additional cycle details
    print("\n[7] Growth Analysis")
    summaries = fvs.get_all_summaries()
    if len(summaries) >= 2:
        first = summaries[0]
        last = summaries[-1]
        years = last['year'] - first['year']
        
        vol_growth = last['tcuft'] - first['tcuft']
        ba_growth = last['ba'] - first['ba']
        tpa_change = last['tpa'] - first['tpa']
        
        print(f"\n    Simulation period: {first['year']} - {last['year']} ({years} years)")
        print(f"    Volume growth: {first['tcuft']} → {last['tcuft']} cuft ({vol_growth:+d})")
        print(f"    BA change: {first['ba']} → {last['ba']} sqft ({ba_growth:+d})")
        print(f"    TPA change: {first['tpa']} → {last['tpa']} ({tpa_change:+d})")
        print(f"    Mean annual increment: {vol_growth / years:.1f} cuft/year")
    
    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()

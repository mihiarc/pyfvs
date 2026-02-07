#!/usr/bin/env python3
"""
Unit tests for fvs_native.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / 'src' / 'pyfvs' / 'src'))

import ctypes
from ctypes import c_int, c_double, c_char, c_char_p, POINTER, byref
import numpy as np

# Load module
exec(open(Path.home() / 'src/pyfvs/src/pyfvs/fvs_native.py').read().split('if __name__')[0])


def test_library_load():
    """Test that library loads correctly."""
    fvs = FVSLibrary('sn')
    assert fvs.lib is not None
    assert fvs.variant == 'sn'
    print("✓ Library load")


def test_dimensions_before_run():
    """Test dimension query before simulation."""
    fvs = FVSLibrary('sn')
    dims = fvs.get_dimensions()
    assert dims['maxtrees'] > 0
    assert dims['maxspecies'] > 0
    assert dims['ntrees'] == 0  # No trees loaded yet
    print("✓ Dimensions (pre-run)")


def test_simulation_run():
    """Test running a simulation."""
    fvs = FVSLibrary('sn')
    keyfile = Path.home() / 'src/fvs-official/tests/FVSsn/snt01.key'
    rtn = fvs.run(f'--keywordfile={keyfile}')
    assert rtn == 0
    
    dims = fvs.get_dimensions()
    assert dims['ntrees'] > 0
    assert dims['ncycles'] > 0
    print(f"✓ Simulation run ({dims['ntrees']} trees, {dims['ncycles']} cycles)")


def test_tree_attributes():
    """Test tree attribute retrieval."""
    fvs = FVSLibrary('sn')
    keyfile = Path.home() / 'src/fvs-official/tests/FVSsn/snt01.key'
    fvs.run(f'--keywordfile={keyfile}')
    
    dbh = fvs.get_tree_attr('dbh')
    assert len(dbh) > 0
    assert dbh.min() >= 0
    assert dbh.max() < 200  # Reasonable DBH range
    
    tpa = fvs.get_tree_attr('tpa')
    assert len(tpa) == len(dbh)
    
    ht = fvs.get_tree_attr('ht')
    assert len(ht) == len(dbh)
    print(f"✓ Tree attributes (DBH: {dbh.min():.1f}-{dbh.max():.1f})")


def test_summary_data():
    """Test summary data retrieval."""
    fvs = FVSLibrary('sn')
    keyfile = Path.home() / 'src/fvs-official/tests/FVSsn/snt01.key'
    fvs.run(f'--keywordfile={keyfile}')
    
    summary = fvs.get_summary(1)
    assert 'year' in summary
    assert 'tpa' in summary
    assert 'ba' in summary
    assert summary['year'] == 1990  # First year in test file
    assert summary['tpa'] > 0
    print(f"✓ Summary data (Year {summary['year']}, TPA={summary['tpa']})")


def test_all_summaries():
    """Test retrieving all cycle summaries."""
    fvs = FVSLibrary('sn')
    keyfile = Path.home() / 'src/fvs-official/tests/FVSsn/snt01.key'
    fvs.run(f'--keywordfile={keyfile}')
    
    summaries = fvs.get_all_summaries()
    assert len(summaries) > 0
    
    # Verify years are sequential
    years = [s['year'] for s in summaries]
    assert years == sorted(years)
    print(f"✓ All summaries ({len(summaries)} cycles, {years[0]}-{years[-1]})")


def test_volume_reconciliation():
    """Test that tree volumes match summary (with stockable factor)."""
    fvs = FVSLibrary('sn')
    keyfile = Path.home() / 'src/fvs-official/tests/FVSsn/snt01.key'
    fvs.run(f'--keywordfile={keyfile}')
    
    tpa = fvs.get_tree_attr('tpa')
    tcuft = fvs.get_tree_attr('tcuft')
    tree_total = (tcuft * tpa).sum()
    
    dims = fvs.get_dimensions()
    summary = fvs.get_summary(dims['ncycles'] + 1)  # Final state
    
    # Stockable factor (10/11 for test file)
    stockable = 10/11
    adjusted = tree_total * stockable
    
    # Allow small tolerance
    assert abs(adjusted - summary['tcuft']) < 10
    print(f"✓ Volume reconciliation ({adjusted:.0f} ≈ {summary['tcuft']})")


def test_tree_data_dict():
    """Test get_tree_data convenience method."""
    fvs = FVSLibrary('sn')
    keyfile = Path.home() / 'src/fvs-official/tests/FVSsn/snt01.key'
    fvs.run(f'--keywordfile={keyfile}')
    
    data = fvs.get_tree_data()
    assert 'dbh' in data
    assert 'ht' in data
    assert 'tpa' in data
    assert len(data['dbh']) > 0
    print(f"✓ Tree data dict ({len(data)} attributes)")


if __name__ == '__main__':
    print("FVS Native Library Tests")
    print("=" * 40)
    
    # Suppress FVS output
    import io
    import contextlib
    
    tests = [
        test_library_load,
        test_dimensions_before_run,
        test_simulation_run,
        test_tree_attributes,
        test_summary_data,
        test_all_summaries,
        test_volume_reconciliation,
        test_tree_data_dict,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            # Run with stdout redirected to suppress FVS output
            with contextlib.redirect_stdout(io.StringIO()):
                test()
            passed += 1
            # Print result after redirect
            test()  # Run again to print result
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__}: {e}")
    
    print("=" * 40)
    print(f"Results: {passed} passed, {failed} failed")

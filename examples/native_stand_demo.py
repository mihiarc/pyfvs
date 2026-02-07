#!/usr/bin/env python3
"""
NativeStand Demo - Using Official FVS with pyfvs

This script demonstrates how to use the NativeStand class to run
growth projections using the official USDA FVS Fortran library.

Usage:
    python native_stand_demo.py
    
Requirements:
    - pyfvs package installed
    - FVS shared libraries built (FVSsn.so at ~/src/fvs-official/bin/)
"""

import sys
from pathlib import Path

# Add pyfvs to path if not installed
pyfvs_path = Path(__file__).parent.parent / 'src'
if pyfvs_path.exists():
    sys.path.insert(0, str(pyfvs_path))


def demo_basic_usage():
    """Demonstrate basic NativeStand usage."""
    print("\n" + "=" * 60)
    print("DEMO 1: Basic NativeStand Usage")
    print("=" * 60)
    
    from pyfvs.native_stand import NativeStand
    
    # Create a loblolly pine plantation
    stand = NativeStand.initialize_planted(
        trees_per_acre=500,
        site_index=70,  # Base age 25 for SN variant
        species='LP',   # Loblolly pine
        variant='sn'    # Southern variant
    )
    
    print(f"Created stand: {stand}")
    print(f"Initial TPA: {sum(t.tpa for t in stand.trees):.0f}")
    
    # Grow for 25 years
    print("\nGrowing for 25 years...")
    stand.grow(years=25)
    
    # Get metrics
    metrics = stand.get_metrics()
    
    print("\n--- Stand Metrics at Age 25 ---")
    print(f"  Trees per acre: {metrics['tpa']}")
    print(f"  Basal area: {metrics['basal_area']:.1f} sq ft/acre")
    print(f"  QMD: {metrics['qmd']:.1f} inches")
    print(f"  Mean DBH: {metrics['mean_dbh']:.1f} inches")
    print(f"  Top height: {metrics['top_height']:.1f} feet")
    print(f"  Mean height: {metrics['mean_height']:.1f} feet")
    print(f"  Volume (total cubic): {metrics['volume']:.0f} cu ft/acre")
    print(f"  Volume (merchantable): {metrics['merchantable_volume']:.0f} cu ft/acre")
    print(f"  Board feet: {metrics['board_feet']:.0f} bf/acre")


def demo_summary_table():
    """Demonstrate FVS summary table access."""
    print("\n" + "=" * 60)
    print("DEMO 2: FVS Summary Table")
    print("=" * 60)
    
    from pyfvs.native_stand import NativeStand
    
    stand = NativeStand.initialize_planted(
        trees_per_acre=500,
        site_index=70,
        species='LP',
        variant='sn'
    )
    
    # Grow for 40 years (8 cycles)
    stand.grow(years=40)
    
    # Print FVS-style summary table
    print(stand.print_summary())


def demo_site_index_comparison():
    """Compare growth at different site indices."""
    print("\n" + "=" * 60)
    print("DEMO 3: Site Index Comparison")
    print("=" * 60)
    
    from pyfvs.native_stand import NativeStand
    
    site_indices = [55, 70, 85]
    years = 25
    
    print(f"\nComparing {years}-year growth at different site indices:")
    print("-" * 50)
    print(f"{'Site Index':>12} {'Height (ft)':>12} {'DBH (in)':>12} {'Volume':>12}")
    print("-" * 50)
    
    for si in site_indices:
        stand = NativeStand.initialize_planted(
            trees_per_acre=500,
            site_index=si,
            species='LP',
            variant='sn'
        )
        stand.grow(years=years)
        m = stand.get_metrics()
        
        print(f"{si:>12} {m['mean_height']:>12.1f} {m['mean_dbh']:>12.1f} {m['volume']:>12.0f}")


def demo_species_comparison():
    """Compare growth of different pine species."""
    print("\n" + "=" * 60)
    print("DEMO 4: Species Comparison")
    print("=" * 60)
    
    from pyfvs.native_stand import NativeStand
    
    species_list = [
        ('LP', 'Loblolly pine'),
        ('SP', 'Shortleaf pine'),
        ('SA', 'Slash pine'),
        ('LL', 'Longleaf pine'),
    ]
    
    print(f"\nComparing 25-year growth at SI=70:")
    print("-" * 60)
    print(f"{'Species':>15} {'Height (ft)':>12} {'DBH (in)':>12} {'Volume':>12}")
    print("-" * 60)
    
    for code, name in species_list:
        try:
            stand = NativeStand.initialize_planted(
                trees_per_acre=500,
                site_index=70,
                species=code,
                variant='sn'
            )
            stand.grow(years=25)
            m = stand.get_metrics()
            
            print(f"{name:>15} {m['mean_height']:>12.1f} {m['mean_dbh']:>12.1f} {m['volume']:>12.0f}")
        except Exception as e:
            print(f"{name:>15} {'(error)':>12} {str(e)[:20]:>24}")


def demo_density_effect():
    """Demonstrate effect of planting density."""
    print("\n" + "=" * 60)
    print("DEMO 5: Planting Density Effect")
    print("=" * 60)
    
    from pyfvs.native_stand import NativeStand
    
    densities = [300, 500, 700, 900]
    
    print(f"\nComparing 25-year growth at different initial densities:")
    print("-" * 70)
    print(f"{'Initial TPA':>12} {'Final TPA':>12} {'DBH (in)':>12} {'BA':>12} {'Volume':>12}")
    print("-" * 70)
    
    for tpa in densities:
        stand = NativeStand.initialize_planted(
            trees_per_acre=tpa,
            site_index=70,
            species='LP',
            variant='sn'
        )
        stand.grow(years=25)
        m = stand.get_metrics()
        
        print(f"{tpa:>12} {m['tpa']:>12} {m['mean_dbh']:>12.1f} {m['basal_area']:>12.1f} {m['volume']:>12.0f}")


def demo_native_vs_python():
    """Compare native FVS vs Python implementation."""
    print("\n" + "=" * 60)
    print("DEMO 6: Native FVS vs Python Implementation")
    print("=" * 60)
    
    from pyfvs.native_stand import NativeStand
    
    try:
        from pyfvs.stand import Stand
    except ImportError:
        print("Python Stand class not available for comparison")
        return
    
    # Create matching stands
    tpa = 500
    si = 70
    years = 25
    
    # Native FVS
    native = NativeStand.initialize_planted(
        trees_per_acre=tpa,
        site_index=si,
        species='LP',
        variant='sn'
    )
    native.grow(years=years)
    native_m = native.get_metrics()
    
    # Python implementation
    python = Stand.initialize_planted(
        trees_per_acre=tpa,
        site_index=si,
        species='LP'
    )
    python.grow(years=years)
    python_m = python.get_metrics()
    
    print(f"\nComparison after {years} years (TPA={tpa}, SI={si}):")
    print("-" * 60)
    print(f"{'Metric':>20} {'Native FVS':>15} {'Python':>15} {'Diff %':>10}")
    print("-" * 60)
    
    for key in ['tpa', 'mean_dbh', 'mean_height', 'basal_area', 'volume']:
        nv = native_m.get(key, 0)
        pv = python_m.get(key, 0)
        diff_pct = ((nv - pv) / pv * 100) if pv else 0
        
        if isinstance(nv, int):
            print(f"{key:>20} {nv:>15} {pv:>15} {diff_pct:>9.1f}%")
        else:
            print(f"{key:>20} {nv:>15.1f} {pv:>15.1f} {diff_pct:>9.1f}%")


def main():
    """Run all demos."""
    from pyfvs.fvs_native import find_fvs_libraries
    
    print("=" * 60)
    print("NativeStand Demo - Official FVS Integration")
    print("=" * 60)
    
    # Check for available FVS libraries
    available = find_fvs_libraries()
    if not available:
        print("\nERROR: No FVS libraries found!")
        print("Build them with:")
        print("  cd ~/src/fvs-official/bin && make FVSsn.so")
        return 1
    
    print(f"\nAvailable FVS variants: {list(available.keys())}")
    
    if 'sn' not in available:
        print("ERROR: SN variant required for demos but not found!")
        return 1
    
    # Run demos
    try:
        demo_basic_usage()
        demo_summary_table()
        demo_site_index_comparison()
        demo_species_comparison()
        demo_density_effect()
        demo_native_vs_python()
        
        print("\n" + "=" * 60)
        print("All demos completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

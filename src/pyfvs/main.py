#!/usr/bin/env python3
"""
Main entry point for FVS-Python simulations.
Uses the unified simulation engine for all operations.
"""
import logging
from pathlib import Path
from datetime import datetime

from .simulation_engine import SimulationEngine, run_simulation, generate_yield_table


def main():
    """Main execution function."""
    # Create output directory
    output_dir = Path(__file__).parent.parent.parent / 'test_output'
    output_dir.mkdir(exist_ok=True)
    
    # Initialize simulation engine
    engine = SimulationEngine(output_dir)
    
    print("Starting FVS-Python simulation...")
    print("-" * 50)
    
    # Example 1: Single stand simulation
    print("\n1. Running single stand simulation (Loblolly Pine)...")
    results = engine.simulate_stand(
        species='LP',
        trees_per_acre=500,
        site_index=70,
        years=50,
        time_step=5
    )
    
    print(f"   Simulation complete. Final metrics:")
    final = results.iloc[-1]
    print(f"   - Age: {final['age']} years")
    print(f"   - Trees/acre: {final['tpa']:.0f}")
    print(f"   - Mean DBH: {final['mean_dbh']:.1f} inches")
    print(f"   - Mean Height: {final['mean_height']:.1f} feet")
    print(f"   - Volume: {final['volume']:.0f} ft³/acre")
    
    # Example 2: Generate yield table
    print("\n2. Generating yield table for multiple scenarios...")
    yield_table = engine.simulate_yield_table(
        species=['LP', 'SP'],  # Loblolly and Shortleaf pine
        site_indices=[60, 70, 80],
        planting_densities=[300, 500, 700],
        years=40
    )
    
    print(f"   Generated yield table with {len(yield_table)} records")
    print(f"   Species included: {yield_table['species'].unique()}")
    print(f"   Site indices: {yield_table['site_index'].unique()}")
    print(f"   Initial densities: {yield_table['initial_tpa'].unique()}")
    
    # Example 3: Scenario comparison
    print("\n3. Comparing management scenarios...")
    scenarios = [
        {
            'name': 'Low Density LP',
            'species': 'LP',
            'trees_per_acre': 300,
            'site_index': 70
        },
        {
            'name': 'High Density LP',
            'species': 'LP',
            'trees_per_acre': 700,
            'site_index': 70
        },
        {
            'name': 'Low Site LP',
            'species': 'LP',
            'trees_per_acre': 500,
            'site_index': 60
        },
        {
            'name': 'High Site LP',
            'species': 'LP',
            'trees_per_acre': 500,
            'site_index': 80
        }
    ]
    
    comparison = engine.compare_scenarios(scenarios, years=30)
    
    print("\n   Scenario comparison at age 30:")
    age_30 = comparison[comparison['age'] == 30]
    for _, row in age_30.iterrows():
        print(f"   {row['scenario']:20s} - Volume: {row['volume']:6.0f} ft³/acre")
    
    print("\n" + "="*50)
    print("All simulations completed successfully!")
    print(f"Results saved to: {output_dir}")
    

if __name__ == '__main__':
    main()
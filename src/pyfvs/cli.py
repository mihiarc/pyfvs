#!/usr/bin/env python3
"""
Command-line interface for FVS-Python.
Provides easy access to simulation and configuration management.
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

from .simulation_engine import SimulationEngine
from .logging_config import setup_logging, get_logger
from .config_loader import convert_yaml_to_toml, get_config_loader


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="fvs-python",
        description="FVS-Python: Southern Yellow Pine Growth Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a basic simulation
  fvs-python simulate --species LP --tpa 500 --site-index 70 --years 30

  # Generate yield table
  fvs-python yield-table --species LP SP --site-indices 60 70 80 --densities 300 500 700

  # Compare scenarios
  fvs-python compare scenarios.json

  # List available species
  fvs-python list-species

  # Validate configuration files
  fvs-python validate-config
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add global options
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    parser.add_argument(
        '--structured-logs',
        action='store_true',
        help='Use structured JSON logging format'
    )
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='FVS-Python 1.0.0'
    )
    
    # Simulate command (replaces 'run')
    run_parser = subparsers.add_parser(
        "simulate", 
        help="Run a single stand simulation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    run_parser.add_argument(
        "--years", 
        type=int, 
        default=50,
        help="Total simulation length in years (default: 50)"
    )
    run_parser.add_argument(
        "--timestep", 
        type=int, 
        default=5,
        help="Years between measurements (default: 5)"
    )
    run_parser.add_argument(
        "--species", 
        type=str, 
        default="LP",
        choices=["LP", "SP", "SA", "LL"],
        help="Species code (default: LP for Loblolly Pine)"
    )
    run_parser.add_argument(
        "--site-index", 
        type=float, 
        default=70.0,
        help="Site index (base age 25) in feet (default: 70)"
    )
    run_parser.add_argument(
        "--trees-per-acre", "--tpa",
        type=int, 
        default=500,
        help="Initial trees per acre (default: 500)"
    )
    run_parser.add_argument(
        "--output-dir", 
        type=Path, 
        default=None,
        help="Output directory for results (default: ./output)"
    )
    run_parser.add_argument(
        "--no-plots",
        action='store_true',
        help="Skip generating plots"
    )
    run_parser.add_argument(
        "--no-save",
        action='store_true',
        help="Skip saving output files"
    )
    
    # Yield table command
    yield_parser = subparsers.add_parser(
        "yield-table",
        help="Generate yield tables for multiple scenarios",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    yield_parser.add_argument(
        "--species",
        nargs='+',
        default=['LP'],
        help="Species codes to include"
    )
    yield_parser.add_argument(
        "--site-indices",
        nargs='+',
        type=float,
        default=[60, 70, 80],
        help="Site indices to test"
    )
    yield_parser.add_argument(
        "--densities",
        nargs='+',
        type=int,
        default=[300, 500, 700],
        help="Planting densities to test (trees per acre)"
    )
    yield_parser.add_argument(
        "--years", "-y",
        type=int, 
        default=50,
        help="Simulation length in years"
    )
    yield_parser.add_argument(
        "--output-dir", 
        type=Path, 
        default=None,
        help="Output directory for results"
    )
    
    # List species command
    list_parser = subparsers.add_parser(
        "list-species",
        help="List available species and their parameters"
    )
    list_parser.add_argument(
        "--detailed",
        action='store_true',
        help="Show detailed species parameters"
    )
    
    # Convert configuration command
    convert_parser = subparsers.add_parser(
        "convert-config",
        help="Convert YAML configuration files to TOML format"
    )
    convert_parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Input directory with YAML configs (default: ./cfg)"
    )
    convert_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for TOML configs (default: ./cfg/toml)"
    )
    
    # Validate configuration command
    validate_parser = subparsers.add_parser(
        "validate-config",
        help="Validate configuration files"
    )
    validate_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory to validate (default: ./cfg)"
    )
    
    # Show configuration command
    show_parser = subparsers.add_parser(
        "show-config",
        help="Display configuration for a species"
    )
    show_parser.add_argument(
        "--species",
        type=str,
        default="LP",
        choices=["LP", "SP", "SA", "LL"],
        help="Species code to show config for (default: LP)"
    )
    show_parser.add_argument(
        "--format",
        type=str,
        default="yaml",
        choices=["yaml", "json"],
        help="Output format (default: yaml)"
    )
    
    return parser


def cmd_simulate(args) -> int:
    """Run a single stand simulation."""
    logger = get_logger(__name__)
    
    try:
        output_dir = args.output_dir or Path('./output')
        output_dir.mkdir(exist_ok=True, parents=True)
        
        engine = SimulationEngine(output_dir)
        
        results = engine.simulate_stand(
            species=args.species,
            trees_per_acre=args.trees_per_acre,
            site_index=args.site_index,
            years=args.years,
            time_step=args.timestep,
            save_outputs=not args.no_save,
            plot_results=not args.no_plots
        )
        
        logger.info("Simulation completed. Final metrics:")
        final_row = results.iloc[-1]
        logger.info(f"  Age: {final_row['age']} years")
        logger.info(f"  Trees per acre: {final_row['tpa']:.0f}")
        logger.info(f"  Mean DBH: {final_row['mean_dbh']:.1f} inches")
        logger.info(f"  Mean height: {final_row['mean_height']:.1f} feet")
        logger.info(f"  Volume: {final_row['volume']:.0f} cubic feet per acre")
        
        return 0
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        return 1


def cmd_yield_table(args) -> int:
    """Generate yield tables."""
    logger = get_logger(__name__)
    
    try:
        output_dir = args.output_dir or Path('./output')
        output_dir.mkdir(exist_ok=True, parents=True)
        
        engine = SimulationEngine(output_dir)
        
        yield_table = engine.simulate_yield_table(
            species=args.species,
            site_indices=args.site_indices,
            planting_densities=args.densities,
            years=args.years
        )
        
        logger.info(f"Yield table generated with {len(yield_table)} rows")
        logger.info(f"Species: {', '.join(args.species)}")
        logger.info(f"Site indices: {args.site_indices}")
        logger.info(f"Densities: {args.densities}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Yield table generation failed: {e}")
        return 1


def cmd_list_species(args) -> int:
    """List available species."""
    logger = get_logger(__name__)
    
    try:
        loader = get_config_loader()
        species_config = loader.species_config['species']
        
        print(f"Available species ({len(species_config)} total):")
        print("=" * 50)
        
        for code, info in species_config.items():
            name = info.get('name', 'Unknown')
            print(f"{code:4s} - {name}")
            
            if args.detailed:
                try:
                    config = loader.load_species_config(code)
                    print(f"      Growth model: {config.get('diameter_growth', {}).get('model', 'Unknown')}")
                    print(f"      Height-diameter: {list(config.get('height_diameter', {}).keys())}")
                    print()
                except Exception as e:
                    print(f"      Error loading config: {e}")
                    print()
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to list species: {e}")
        return 1


def cmd_convert_config(args) -> int:
    """Convert YAML configuration files to TOML."""
    try:
        print("Converting YAML configuration files to TOML...")
        
        input_dir = args.input_dir or Path.cwd() / "cfg"
        output_dir = args.output_dir or input_dir / "toml"
        
        print(f"Input directory: {input_dir}")
        print(f"Output directory: {output_dir}")
        
        convert_yaml_to_toml(input_dir, output_dir)
        
        print("Configuration conversion completed successfully!")
        return 0
        
    except Exception as e:
        print(f"Error converting configuration: {e}", file=sys.stderr)
        return 1


def cmd_validate_config(args) -> int:
    """Validate configuration files."""
    try:
        print("Validating configuration files...")
        
        config_dir = args.config_dir or Path.cwd() / "cfg"
        print(f"Configuration directory: {config_dir}")
        
        # Try to load the configuration
        loader = get_config_loader()
        
        # Test loading each species
        species_codes = ["LP", "SP", "SA", "LL"]
        for species in species_codes:
            try:
                config = loader.load_species_config(species)
                print(f"✓ {species}: Configuration loaded successfully")
            except Exception as e:
                print(f"✗ {species}: Error loading configuration - {e}")
        
        print("Configuration validation completed!")
        return 0
        
    except Exception as e:
        print(f"Error validating configuration: {e}", file=sys.stderr)
        return 1


def cmd_show_config(args) -> int:
    """Display configuration for a species."""
    try:
        loader = get_config_loader()
        config = loader.load_species_config(args.species)
        
        print(f"Configuration for species {args.species}:")
        print("-" * 40)
        
        if args.format == "yaml":
            import yaml
            print(yaml.dump(config, default_flow_style=False, sort_keys=False))
        elif args.format == "json":
            import json
            print(json.dumps(config, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"Error showing configuration: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Set up logging
    output_dir = getattr(args, 'output_dir', None) or Path('./output')
    output_dir.mkdir(exist_ok=True, parents=True)
    
    setup_logging(
        log_level=args.log_level,
        log_file=output_dir / 'fvs-python.log',
        structured=args.structured_logs
    )
    
    # Route to appropriate command handler
    if args.command == "simulate":
        return cmd_simulate(args)
    elif args.command == "yield-table":
        return cmd_yield_table(args)
    elif args.command == "list-species":
        return cmd_list_species(args)
    elif args.command == "convert-config":
        return cmd_convert_config(args)
    elif args.command == "validate-config":
        return cmd_validate_config(args)
    elif args.command == "show-config":
        return cmd_show_config(args)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 
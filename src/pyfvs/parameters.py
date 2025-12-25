"""
Loblolly Pine (Pinus taeda) growth parameters.
All parameters are sourced from the Southern variant of FVS.
"""
import yaml
from pathlib import Path

# Height-Diameter Relationship Parameters (Curtis-Arney equation)
# height = 4.5 + p2 * exp(-p3 * DBH**p4)  # for DBH >= 3.0 inches
HD_PARAMS = {
    'p2': 243.860648,
    'p3': 4.28460566,
    'p4': -0.47130185,
    'Dbw': 0.5  # diameter breakpoint for small trees
}

# Crown and Bark Parameters
CROWN_PARAMS = {
    # Crown width parameters (for CCF calculation)
    'a1': 0.7380,
    'a2': 0.2450,
    'a3': 0.000809,
    
    # Average crown ratio parameters
    'acr_b0': 4.2,      # Increased base level
    'acr_b1': -0.5,     # Stronger density response
    
    # Weibull crown ratio parameters
    'weibull_a': 15.0,   # Higher minimum (percent)
    'weibull_b0': 40.0,  # Higher base scale
    'weibull_b1': 0.6,   # Stronger ACR response
    'weibull_c': 3.0     # Sharper distribution
}

# Small Tree Growth Parameters (height growth)
# Uses Chapman-Richards equation
SMALL_TREE_PARAMS = {
    'c1': 1.1421,
    'c2': 1.0042,
    'c3': -0.0374,
    'c4': 0.7632,
    'c5': 0.0358
}

# Large Tree Growth Parameters (diameter growth)
# For predicting ln(DDS) - natural log of change in squared inside-bark diameter
LARGE_TREE_PARAMS = {
    'b1': 0.222214,      # Intercept
    'b2': 1.163040,      # log(dbh) coefficient
    'b3': -0.000863,     # dbh^2 coefficient
    'b4': 0.028483,      # log(cr) coefficient
    'b5': 0.006935,      # relative height coefficient
    'b6': 0.005018,      # site index coefficient
    'b7': 0.0,           # basal area coefficient
    'b8': 0.0,           # plot basal area coefficient
    'b9': 0.0,           # slope coefficient
    'b10': 0.0,          # cos(aspect)*slope coefficient
    'b11': 0.0,          # sin(aspect)*slope coefficient
    'forest_type_factor': 0.0,
    'ecounit_factor': 0.0,
    'planting_factor': 0.245669
}

# Model Transition Parameters
TRANSITION_PARAMS = {
    'Xmin': 1.0,  # minimum DBH for transition (inches)
    'Xmax': 3.0   # maximum DBH for transition (inches)
}

# Stand Initialization Parameters
STAND_INIT = {
    'initial_tpa': 500,          # trees per acre at planting
    'initial_dbh_mean': 0.5,     # initial mean DBH (inches)
    'initial_dbh_sd': 0.1,       # initial DBH standard deviation
    'initial_height': 1.0,       # initial height (feet)
    'site_index': 70            # site index (base age 25)
}

# Mortality Parameters
MORTALITY = {
    'background_rate': 0.005,    # annual background mortality rate
    'max_sdi': 450,             # maximum stand density index
    'competition_threshold': 0.55  # relative density threshold for competition mortality
}

# Volume Parameters
VOLUME = {
    'form_factor': 0.48,  # tree form factor for volume calculations
}

def create_config():
    """Create configuration dictionary with all parameters."""
    return {
        'species': 'loblolly_pine',
        'height_diameter': HD_PARAMS,
        'crown': CROWN_PARAMS,
        'small_tree_growth': SMALL_TREE_PARAMS,
        'large_tree_growth': LARGE_TREE_PARAMS,
        'transition': TRANSITION_PARAMS,
        'stand_init': STAND_INIT,
        'mortality': MORTALITY,
        'volume': VOLUME
    }

def write_config_file():
    """Write configuration to YAML file."""
    config = create_config()
    
    # Create config directory if it doesn't exist
    config_dir = Path(__file__).parent.parent / 'cfg'
    config_dir.mkdir(exist_ok=True)
    
    # Write config file
    config_path = config_dir / 'loblolly_params.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"Configuration written to {config_path}")

if __name__ == '__main__':
    write_config_file() 
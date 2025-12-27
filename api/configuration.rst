Configuration
=============

FVS-Python uses a flexible configuration system for species parameters and model coefficients.

Config Loader
-------------

.. automodule:: fvs_python.config_loader
   :members:
   :undoc-members:
   :show-inheritance:

The ConfigLoader provides unified access to YAML, TOML, and JSON configuration files
with caching for performance.


Configuration File Structure
----------------------------

Configuration files are organized in the ``cfg/`` directory:

.. code-block:: text

    cfg/
    ├── species/                          # Species-specific parameters
    │   ├── lp_loblolly_pine.yaml
    │   ├── sp_shortleaf_pine.yaml
    │   ├── ll_longleaf_pine.yaml
    │   ├── sa_slash_pine.yaml
    │   └── ... (90 species total)
    ├── functional_forms.yaml             # Growth equation specifications
    ├── sn_diameter_growth_coefficients.json
    ├── sn_height_diameter_coefficients.json
    ├── sn_crown_width_coefficients.json
    ├── sn_ccf_coefficients.json
    └── sn_bark_ratio_coefficients.json


Species Configuration
---------------------

Each species YAML file contains parameters for all growth models:

.. code-block:: yaml

    # cfg/species/lp_loblolly_pine.yaml
    code: LP
    name: Loblolly Pine
    scientific_name: Pinus taeda

    # Height-diameter relationship (Curtis-Arney)
    height_diameter:
      model: curtis_arney
      p2: 243.860648
      p3: 4.28460566
      p4: -0.47130185
      Dbw: 0.5

    # Bark ratio (Clark 1991)
    bark_ratio:
      b1: -0.48140
      b2: 0.91413

    # Crown width coefficients
    crown_width:
      a1: 0.7380
      a2: 0.2450
      a3: 0.000809

    # Small-tree height growth (Chapman-Richards)
    small_tree:
      c1: 1.1421
      c2: 1.0042
      c3: -0.0374
      c4: 0.7632
      c5: 0.0358

    # Large-tree diameter growth (ln(DDS))
    diameter_growth:
      model: ln_dds
      b1: 0.222214
      b2: 1.163040
      b3: -0.000863
      b4: 0.028483
      b5: 0.006935
      b6: 0.005018

    # Transition zone
    transition:
      Xmin: 1.0
      Xmax: 3.0

    # Ecological units
    ecounit:
      base_ecounit: '232'
      effects:
        '232': 0.0      # Georgia (base)
        '231L': 0.256   # Lowland
        '255': 0.275    # Prairie
        'M231': 0.790   # Mountain


Loading Configuration
---------------------

.. code-block:: python

    from fvs_python.config_loader import get_config_loader

    loader = get_config_loader()

    # Load species configuration
    lp_config = loader.load_species_config('LP')
    print(f"Species: {lp_config['name']}")

    # Load coefficient file
    hd_coeffs = loader.load_coefficient_file('sn_height_diameter_coefficients.json')


Functional Forms
----------------

The ``functional_forms.yaml`` file documents the mathematical equations:

.. code-block:: yaml

    height_diameter:
      curtis_arney:
        equation: "H = 4.5 + P2 * exp(-P3 * DBH^P4)"
        parameters:
          - P2: "Asymptote parameter"
          - P3: "Shape parameter"
          - P4: "Rate parameter"
        source: "Curtis (1967), Arney (1985)"

      wykoff:
        equation: "H = 4.5 + exp(B1 + B2 / (DBH + 1))"
        parameters:
          - B1: "Intercept"
          - B2: "Slope"
        source: "Wykoff (1990)"


Simulation Engine
-----------------

.. automodule:: fvs_python.simulation_engine
   :members:
   :undoc-members:
   :show-inheritance:

The SimulationEngine provides high-level simulation management:

.. code-block:: python

    from fvs_python import SimulationEngine
    from pathlib import Path

    engine = SimulationEngine(Path('./output'))

    # Single simulation
    results = engine.simulate_stand(
        species='LP',
        trees_per_acre=500,
        site_index=70,
        years=30
    )

    # Yield table generation
    yield_table = engine.simulate_yield_table(
        species=['LP', 'SP'],
        site_indices=[60, 70, 80],
        planting_densities=[300, 500, 700],
        years=50
    )


Validation
----------

.. automodule:: fvs_python.validation
   :members:
   :undoc-members:
   :show-inheritance:

Parameter validation using Pydantic models:

.. code-block:: python

    from fvs_python.validation import validate_tree_params

    # Validates and raises errors for out-of-bounds values
    params = validate_tree_params(
        species='LP',
        dbh=6.0,
        height=45.0,
        crown_ratio=0.45
    )

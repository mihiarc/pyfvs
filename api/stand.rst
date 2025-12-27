Stand Module
============

The Stand class manages collections of trees and stand-level operations.

.. module:: fvs_python.stand

Stand Class
-----------

.. autoclass:: Stand
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   .. rubric:: Class Methods

   .. autosummary::
      :nosignatures:

      ~Stand.initialize_planted

   .. rubric:: Instance Methods

   .. autosummary::
      :nosignatures:

      ~Stand.grow
      ~Stand.get_metrics
      ~Stand.thin_from_below
      ~Stand.thin_from_above
      ~Stand.add_tree

Stand Composition
-----------------

The Stand class uses composition with specialized components:

- **StandMetricsCalculator** - CCF, QMD, SDI, basal area calculations
- **MortalityModel** - Background and density-dependent mortality
- **HarvestManager** - Thinning operations
- **CompetitionCalculator** - Tree-level competition metrics
- **StandOutputGenerator** - Yield tables, exports

Example Usage
-------------

Creating and managing a planted stand:

.. code-block:: python

    from fvs_python import Stand

    # Initialize a planted stand
    stand = Stand.initialize_planted(
        trees_per_acre=500,
        site_index=70,
        species='LP',
        ecounit='M231'
    )

    # Grow for 25 years
    stand.grow(years=25)

    # Get stand metrics
    metrics = stand.get_metrics()
    print(f"Trees per acre: {metrics['tpa']:.0f}")
    print(f"Mean DBH: {metrics['mean_dbh']:.1f} inches")
    print(f"Volume: {metrics['volume']:.0f} cuft/acre")

Thinning Operations
-------------------

.. code-block:: python

    from fvs_python import Stand

    stand = Stand.initialize_planted(
        trees_per_acre=500,
        site_index=70,
        species='LP'
    )

    # Grow 10 years
    stand.grow(years=10)

    # Thin from below to 200 TPA
    stand.thin_from_below(target_tpa=200)

    # Continue growing
    stand.grow(years=15)


Stand Metrics
-------------

.. automodule:: fvs_python.stand_metrics
   :members:
   :undoc-members:


Competition Calculator
----------------------

.. automodule:: fvs_python.competition
   :members:
   :undoc-members:


Harvest Manager
---------------

.. automodule:: fvs_python.harvest
   :members:
   :undoc-members:

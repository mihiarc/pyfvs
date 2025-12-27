API Reference
=============

This section documents the public API of FVS-Python.

Core Classes
------------

The two main classes for running simulations:

.. autosummary::
   :toctree: generated
   :nosignatures:

   fvs_python.tree.Tree
   fvs_python.stand.Stand

Growth Models
-------------

Individual growth model implementations:

.. autosummary::
   :toctree: generated
   :nosignatures:

   fvs_python.height_diameter
   fvs_python.large_tree_height_growth
   fvs_python.crown_ratio
   fvs_python.crown_width
   fvs_python.bark_ratio
   fvs_python.crown_competition_factor
   fvs_python.mortality

Stand Components
----------------

Specialized stand management components:

.. autosummary::
   :toctree: generated
   :nosignatures:

   fvs_python.stand_metrics
   fvs_python.competition
   fvs_python.harvest

Configuration & Utilities
-------------------------

.. autosummary::
   :toctree: generated
   :nosignatures:

   fvs_python.config_loader
   fvs_python.simulation_engine
   fvs_python.validation


Module Index
------------

.. toctree::
   :maxdepth: 1

   tree
   stand
   growth_models
   configuration

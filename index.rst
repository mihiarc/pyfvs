FVS-Python Documentation
=========================

FVS-Python is a Python implementation of the Southern variant of the Forest Vegetation Simulator (FVS).
It simulates the growth and yield of southern yellow pine species: Loblolly, Shortleaf, Longleaf, and Slash pine.

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   getting_started

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/index
   api/tree
   api/stand
   api/growth_models
   api/configuration

.. toctree::
   :maxdepth: 2
   :caption: Technical Documentation

   FVS_PYTHON_VALIDATION_SPEC
   FVS_SN_COEFFICIENTS
   volume_library_integration

.. toctree::
   :maxdepth: 2
   :caption: Reference

   COEFFICIENT_COMPARISON


Quick Start
-----------

Install FVS-Python::

    pip install -e .

Run a simulation::

    fvs-python simulate --species LP --tpa 500 --site-index 70 --years 30

Or use the Python API:

.. code-block:: python

    from fvs_python import Stand

    stand = Stand.initialize_planted(
        trees_per_acre=500,
        site_index=70,
        species='LP'
    )
    stand.grow(years=25)
    metrics = stand.get_metrics()


Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

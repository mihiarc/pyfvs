Tree Module
===========

The Tree class represents an individual tree with its attributes and growth methods.

.. module:: fvs_python.tree

Tree Class
----------

.. autoclass:: Tree
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   .. rubric:: Attributes

   .. autosummary::
      :nosignatures:

      ~Tree.species
      ~Tree.dbh
      ~Tree.height
      ~Tree.age
      ~Tree.crown_ratio
      ~Tree.expansion_factor

   .. rubric:: Methods

   .. autosummary::
      :nosignatures:

      ~Tree.grow
      ~Tree.get_volume
      ~Tree.get_bark_ratio
      ~Tree.get_crown_width

Growth Model Selection
----------------------

The Tree class automatically selects between small-tree and large-tree growth models
based on DBH:

- **DBH < 1.0"**: Small-tree model only (height-driven)
- **1.0" <= DBH <= 3.0"**: Weighted blend of both models
- **DBH > 3.0"**: Large-tree model only (diameter-driven)

Example Usage
-------------

Creating and growing a tree:

.. code-block:: python

    from fvs_python import Tree

    # Create a Loblolly Pine tree
    tree = Tree(
        species='LP',
        dbh=6.0,
        height=45.0,
        age=15,
        crown_ratio=0.45
    )

    # Grow for 5 years
    tree.grow(
        site_index=70,
        basal_area=120.0,
        time_step=5
    )

    print(f"New DBH: {tree.dbh:.1f} inches")
    print(f"New height: {tree.height:.1f} feet")
    print(f"Volume: {tree.get_volume():.1f} cubic feet")

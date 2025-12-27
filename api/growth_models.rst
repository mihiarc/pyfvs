Growth Models
=============

FVS-Python implements several interconnected growth models from the FVS Southern variant.

Height-Diameter Relationship
----------------------------

.. automodule:: fvs_python.height_diameter
   :members:
   :undoc-members:
   :show-inheritance:

The primary model is the Curtis-Arney equation:

.. math::

   H = 4.5 + P_2 \cdot e^{-P_3 \cdot DBH^{P_4}}

Where:

- H = total height (feet)
- DBH = diameter at breast height (inches)
- P2, P3, P4 = species-specific coefficients


Large Tree Height Growth
------------------------

.. automodule:: fvs_python.large_tree_height_growth
   :members:
   :undoc-members:
   :show-inheritance:

The large-tree model predicts potential height growth from the Chapman-Richards growth curve.


Crown Ratio
-----------

.. automodule:: fvs_python.crown_ratio
   :members:
   :undoc-members:
   :show-inheritance:

Crown ratio (live crown length / total height) is modeled using a Weibull distribution
with competition effects.


Crown Width
-----------

.. automodule:: fvs_python.crown_width
   :members:
   :undoc-members:
   :show-inheritance:

Crown width equations support both forest-grown and open-grown conditions:

- **Forest grown**: Used for PCC (Point Centered Quarter) calculations
- **Open grown**: Used for CCF (Crown Competition Factor)


Bark Ratio
----------

.. automodule:: fvs_python.bark_ratio
   :members:
   :undoc-members:
   :show-inheritance:

Converts between diameter outside bark (DOB) and diameter inside bark (DIB) using
Clark (1991) equations:

.. math::

   DIB = b_1 + b_2 \cdot DOB


Crown Competition Factor
------------------------

.. automodule:: fvs_python.crown_competition_factor
   :members:
   :undoc-members:
   :show-inheritance:

CCF measures stand density as the percentage of an acre that would be covered by
the crowns of open-grown trees.


Mortality
---------

.. automodule:: fvs_python.mortality
   :members:
   :undoc-members:
   :show-inheritance:

Implements background mortality and density-dependent mortality using SDI (Stand Density Index).


Growth Model Interaction
------------------------

The growth models interact in a specific sequence during each growth cycle:

1. **Calculate competition** - Update CCF, basal area, competition indices
2. **Diameter growth** (large trees) - Predict ln(DDS) and convert to diameter increment
3. **Height growth** - Use height-diameter relationship or potential height growth
4. **Crown ratio update** - Adjust crown ratio based on competition
5. **Mortality** - Apply background and density-dependent mortality

Small-Tree vs Large-Tree Models
-------------------------------

The transition between models occurs in the 1-3 inch DBH range:

.. code-block:: python

    if dbh < Xmin:  # typically 1.0"
        weight = 0.0  # 100% small-tree model
    elif dbh >= Xmax:  # typically 3.0"
        weight = 1.0  # 100% large-tree model
    else:
        weight = (dbh - Xmin) / (Xmax - Xmin)

    growth = (1 - weight) * small_tree_growth + weight * large_tree_growth

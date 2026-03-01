"""
Volume calculation module for FVS-Python.

Implements two volume estimation approaches:

1. **Taper-based volume** (preferred when coefficients are available):
   Uses stem profile models to predict diameter at any height, then
   merchandises the tree into logs with Scribner, International 1/4",
   and Doyle board-foot rules.

   - Clark model for Eastern US (SN, NE, CS, LS variants)
   - Flewelling model for Western US (PN, WC, OP variants)

2. **Combined-variable fallback** (``V = a + b * D²H``):
   Used when taper coefficients are not available for a species/variant.

References:
    Clark et al. (1991) SE-282 - Stem Profile Equations for Southern Species
    Flewelling & Raynes (1993) - Variable-shape stem-profile predictions
    Amateis & Burkhart (1987) - Cubic-Foot Volume Equations for Loblolly Pine
"""
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

from .config_loader import get_default_variant


@dataclass
class VolumeResult:
    """Container for volume calculation results.

    All cubic volumes are inside bark. Board-foot volumes use the standard
    FVS log rules: Scribner (primary), International 1/4", and Doyle.
    """
    total_cubic_volume: float = 0.0
    gross_cubic_volume: float = 0.0
    net_cubic_volume: float = 0.0
    merchantable_cubic_volume: float = 0.0
    board_foot_volume: float = 0.0          # Primary BF (Scribner)
    cord_volume: float = 0.0
    green_weight: float = 0.0
    dry_weight: float = 0.0
    sawlog_cubic_volume: float = 0.0
    sawlog_board_foot: float = 0.0
    board_foot_international: float = 0.0   # International 1/4" rule
    board_foot_doyle: float = 0.0           # Doyle rule
    biomass_main_stem: float = 0.0
    biomass_live_branches: float = 0.0
    biomass_foliage: float = 0.0
    error_flag: int = 0

    def is_valid(self) -> bool:
        """Check if volume calculation was successful."""
        return self.error_flag == 0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for easy access."""
        return asdict(self)


# Combined-variable equation coefficients: V = a + b × D²H
# Where D = DBH (inches), H = total height (feet), V = volume (cubic feet)
# Coefficients from published research for site-prepared plantation pines
# Source: Amateis & Burkhart (1987), validated against SE-282 taper equations
# LS species from Gevorkiantz & Olsen (1955), Hahn (1984), and USFS LS-FVS documentation
VOLUME_COEFFICIENTS_OUTSIDE_BARK: Dict[str, Dict[str, float]] = {
    # Southern pines - from Amateis & Burkhart (1987) and similar studies
    'LP': {'a': 0.18658, 'b': 0.00250},   # Loblolly Pine (R² = 0.98)
    'SP': {'a': 0.18658, 'b': 0.00250},   # Shortleaf Pine (use loblolly, validated)
    'SA': {'a': 0.15000, 'b': 0.00260},   # Slash Pine (adjusted for faster growth)
    'LL': {'a': 0.20000, 'b': 0.00245},   # Longleaf Pine (more taper)
    'VP': {'a': 0.18658, 'b': 0.00240},   # Virginia Pine
    'PD': {'a': 0.18658, 'b': 0.00240},   # Pitch Pine
    'SR': {'a': 0.18658, 'b': 0.00250},   # Spruce Pine
    'PP': {'a': 0.18658, 'b': 0.00240},   # Pond Pine
    'SD': {'a': 0.18658, 'b': 0.00235},   # Sand Pine
    # Lake States species - from Gevorkiantz & Olsen (1955), Hahn (1984)
    'JP': {'a': 0.15000, 'b': 0.00230},   # Jack Pine (high taper, lower form)
    'SC': {'a': 0.15000, 'b': 0.00230},   # Scotch Pine (use Jack Pine)
    'RN': {'a': 0.12000, 'b': 0.00248},   # Red Pine (good form, straight stem)
    'RP': {'a': 0.12000, 'b': 0.00248},   # Red Pine (alternate code)
    'WP': {'a': 0.10000, 'b': 0.00255},   # Eastern White Pine (excellent form)
    'WS': {'a': 0.10000, 'b': 0.00240},   # White Spruce
    'NS': {'a': 0.10000, 'b': 0.00240},   # Norway Spruce (use White Spruce)
    'BF': {'a': 0.08000, 'b': 0.00235},   # Balsam Fir (high taper)
    'BS': {'a': 0.10000, 'b': 0.00230},   # Black Spruce (small, high taper)
    'TA': {'a': 0.12000, 'b': 0.00225},   # Tamarack
    'EH': {'a': 0.10000, 'b': 0.00245},   # Eastern Hemlock
    'QA': {'a': 0.08000, 'b': 0.00220},   # Quaking Aspen (short-lived, moderate form)
    'BT': {'a': 0.08000, 'b': 0.00220},   # Bigtooth Aspen (use Quaking Aspen)
    'PB': {'a': 0.10000, 'b': 0.00225},   # Paper Birch
    'YB': {'a': 0.10000, 'b': 0.00235},   # Yellow Birch
    'SM': {'a': 0.10000, 'b': 0.00240},   # Sugar Maple (excellent form)
    'RM': {'a': 0.08000, 'b': 0.00225},   # Red Maple
    'AB': {'a': 0.10000, 'b': 0.00235},   # American Beech
    'RO': {'a': 0.10000, 'b': 0.00235},   # Northern Red Oak
    'WO': {'a': 0.10000, 'b': 0.00230},   # White Oak
    'BO': {'a': 0.10000, 'b': 0.00230},   # Black Oak (use White Oak)
    'WA': {'a': 0.08000, 'b': 0.00225},   # White Ash
    'BA': {'a': 0.08000, 'b': 0.00220},   # Black Ash
    'WN': {'a': 0.10000, 'b': 0.00240},   # Black Walnut (high value, good form)
    'BC': {'a': 0.08000, 'b': 0.00230},   # Black Cherry
    # PNW conifers - from Brackett (1977), Curtis et al. (1981)
    'DF': {'a': 0.10, 'b': 0.00260},   # Douglas-fir (excellent form)
    'WH': {'a': 0.08, 'b': 0.00255},   # Western Hemlock
    'RC': {'a': 0.10, 'b': 0.00245},   # Western Redcedar (high taper)
    'SS': {'a': 0.10, 'b': 0.00265},   # Sitka Spruce (good form)
    'SF': {'a': 0.08, 'b': 0.00250},   # Silver Fir (Pacific Silver Fir)
    'GF': {'a': 0.08, 'b': 0.00250},   # Grand Fir
    'WF': {'a': 0.08, 'b': 0.00248},   # White Fir
    'NF': {'a': 0.08, 'b': 0.00252},   # Noble Fir
    'AF': {'a': 0.06, 'b': 0.00240},   # Subalpine Fir
    'RF': {'a': 0.08, 'b': 0.00250},   # California Red Fir
    'IC': {'a': 0.10, 'b': 0.00240},   # Incense Cedar
    'ES': {'a': 0.08, 'b': 0.00240},   # Engelmann Spruce
    'YC': {'a': 0.10, 'b': 0.00245},   # Alaska Yellow Cedar
    'RW': {'a': 0.15, 'b': 0.00270},   # Redwood (massive form)
    'MH': {'a': 0.06, 'b': 0.00245},   # Mountain Hemlock
    # PNW hardwoods - from Brackett (1977), Chambers & Foltz (1979)
    'RA': {'a': 0.06, 'b': 0.00230},   # Red Alder
    'BM': {'a': 0.06, 'b': 0.00220},   # Bigleaf Maple
    'GC': {'a': 0.06, 'b': 0.00215},   # Giant Chinquapin
    'AS': {'a': 0.06, 'b': 0.00210},   # Quaking Aspen (PNW)
    'PY': {'a': 0.06, 'b': 0.00210},   # Pacific Yew
    'DG': {'a': 0.06, 'b': 0.00215},   # Pacific Dogwood
    'CH': {'a': 0.06, 'b': 0.00220},   # Bitter Cherry
    'CW': {'a': 0.06, 'b': 0.00215},   # Black Cottonwood (PNW)
    'WJ': {'a': 0.10, 'b': 0.00200},   # Western Juniper (high taper, low form)
    'WB': {'a': 0.08, 'b': 0.00235},   # Whitebark Pine
    'KP': {'a': 0.08, 'b': 0.00230},   # Knobcone Pine
    'HT': {'a': 0.06, 'b': 0.00200},   # Hawthorn (small tree)
    'WI': {'a': 0.06, 'b': 0.00200},   # Willow (small tree)
    'OT': {'a': 0.08, 'b': 0.00220},   # Other species (PNW generic)
    # NE-unique species - from Miles & Smith (2009), Hahn (1984)
    'RS': {'a': 0.10000, 'b': 0.00240},   # Red Spruce
    'AW': {'a': 0.10000, 'b': 0.00240},   # Atlantic White Cedar
    'TM': {'a': 0.15000, 'b': 0.00235},   # Table Mountain Pine
    'SB': {'a': 0.10000, 'b': 0.00235},   # Sweet Birch (similar to Yellow Birch)
    'RB': {'a': 0.08000, 'b': 0.00220},   # River Birch
    'GB': {'a': 0.06000, 'b': 0.00200},   # Gray Birch (small tree)
    'CT': {'a': 0.10000, 'b': 0.00240},   # Cucumbertree (Magnolia family)
    'CO': {'a': 0.10000, 'b': 0.00230},   # Chestnut Oak (use White Oak)
    'SL': {'a': 0.10000, 'b': 0.00230},   # Shellbark Hickory
    'YP': {'a': 0.10000, 'b': 0.00250},   # Yellow-Poplar (excellent form)
    'SU': {'a': 0.08000, 'b': 0.00225},   # Sweetgum
    'SO': {'a': 0.10000, 'b': 0.00230},   # Scarlet Oak
    'CB': {'a': 0.10000, 'b': 0.00235},   # Cherrybark Oak
    'SK': {'a': 0.10000, 'b': 0.00230},   # Southern Red Oak
    'WL': {'a': 0.10000, 'b': 0.00230},   # Willow Oak
    'BU': {'a': 0.08000, 'b': 0.00225},   # Buckeye
    'YY': {'a': 0.08000, 'b': 0.00225},   # Yellow Buckeye
    'MG': {'a': 0.10000, 'b': 0.00240},   # Magnolia
    'MV': {'a': 0.10000, 'b': 0.00240},   # Sweetbay
    'SD': {'a': 0.06000, 'b': 0.00200},   # Sourwood (small tree)
    'PW': {'a': 0.08000, 'b': 0.00230},   # Paulownia
    'AI': {'a': 0.08000, 'b': 0.00220},   # Ailanthus
    'SE': {'a': 0.06000, 'b': 0.00200},   # Serviceberry (small tree)
    'EL': {'a': 0.08000, 'b': 0.00220},   # Other Elm
    # Note: 'WB' (White Basswood, NE idx 94) collides with 'WB' (Whitebark Pine,
    # PNW idx 31) defined above. White Basswood falls back to DEFAULT_HARDWOOD.
    # CS-unique species - from Clark et al. (1991), Miles & Smith (2009)
    'BY': {'a': 0.12000, 'b': 0.00250},   # Bald Cypress (excellent form)
    'TL': {'a': 0.10000, 'b': 0.00230},   # Tupelo (Black Tupelo)
    'TS': {'a': 0.10000, 'b': 0.00230},   # Swamp Tupelo
    'HS': {'a': 0.10000, 'b': 0.00225},   # Shagbark Hickory (generic hickory)
    'PE': {'a': 0.10000, 'b': 0.00225},   # Pecan
    'BI': {'a': 0.10000, 'b': 0.00225},   # Bitternut Hickory
    'UA': {'a': 0.08000, 'b': 0.00220},   # Blue Ash
    'SG': {'a': 0.08000, 'b': 0.00220},   # Sugarberry
    'WE': {'a': 0.08000, 'b': 0.00220},   # Winged Elm
    'SI': {'a': 0.08000, 'b': 0.00220},   # Siberian Elm
    'BJ': {'a': 0.10000, 'b': 0.00220},   # Blackjack Oak (small form)
    'DO': {'a': 0.10000, 'b': 0.00230},   # Bottomland Post Oak
    'NK': {'a': 0.10000, 'b': 0.00230},   # Nuttall Oak
    'QS': {'a': 0.10000, 'b': 0.00235},   # Shumard Oak
    'OV': {'a': 0.10000, 'b': 0.00225},   # Overcup Oak
    'UH': {'a': 0.08000, 'b': 0.00220},   # Unidentified Hardwood
    'OB': {'a': 0.08000, 'b': 0.00220},   # Ohio Buckeye
    'CA': {'a': 0.08000, 'b': 0.00215},   # Catalpa
    'HL': {'a': 0.08000, 'b': 0.00225},   # Honeylocust
    'OL': {'a': 0.08000, 'b': 0.00225},   # Other Locust
    'NC': {'a': 0.06000, 'b': 0.00200},   # Other Noncommercial Hdwd (small)
    'RD': {'a': 0.06000, 'b': 0.00200},   # Redbud (small tree)
    'KC': {'a': 0.08000, 'b': 0.00225},   # Kentucky Coffeetree
    'MB': {'a': 0.08000, 'b': 0.00215},   # Mulberry
    # OP-unique species - from Chambers & Foltz (1979), PNW hardwood estimates
    'CL': {'a': 0.06000, 'b': 0.00215},   # California Laurel (medium broadleaf)
    # Default for other softwoods
    'DEFAULT_SOFTWOOD': {'a': 0.15, 'b': 0.00245},
    'DEFAULT_LAKE_STATES_SOFTWOOD': {'a': 0.10, 'b': 0.00240},
    'DEFAULT_PNW_SOFTWOOD': {'a': 0.08, 'b': 0.00250},
    # Hardwoods typically have lower form factors
    'DEFAULT_HARDWOOD': {'a': 0.10, 'b': 0.00220},
    'DEFAULT_LAKE_STATES_HARDWOOD': {'a': 0.08, 'b': 0.00225},
    'DEFAULT_PNW_HARDWOOD': {'a': 0.06, 'b': 0.00220},
}

VOLUME_COEFFICIENTS_INSIDE_BARK: Dict[str, Dict[str, float]] = {
    'LP': {'a': -0.09653, 'b': 0.00210},  # Loblolly Pine (R² = 0.97)
    'SP': {'a': -0.09653, 'b': 0.00210},  # Shortleaf Pine
    'SA': {'a': -0.08000, 'b': 0.00215},  # Slash Pine
    'LL': {'a': -0.10000, 'b': 0.00205},  # Longleaf Pine
    'VP': {'a': -0.09653, 'b': 0.00200},  # Virginia Pine
    # Lake States species (inside bark)
    'JP': {'a': -0.10000, 'b': 0.00195},  # Jack Pine
    'RN': {'a': -0.08000, 'b': 0.00210},  # Red Pine
    'RP': {'a': -0.08000, 'b': 0.00210},  # Red Pine (alternate code)
    'WP': {'a': -0.07000, 'b': 0.00218},  # Eastern White Pine
    'WS': {'a': -0.07000, 'b': 0.00205},  # White Spruce
    'BF': {'a': -0.06000, 'b': 0.00200},  # Balsam Fir
    'BS': {'a': -0.07000, 'b': 0.00195},  # Black Spruce
    'QA': {'a': -0.06000, 'b': 0.00185},  # Quaking Aspen
    'SM': {'a': -0.07000, 'b': 0.00205},  # Sugar Maple
    'RM': {'a': -0.06000, 'b': 0.00190},  # Red Maple
    'RO': {'a': -0.07000, 'b': 0.00200},  # Northern Red Oak
    'WO': {'a': -0.07000, 'b': 0.00195},  # White Oak
    'PB': {'a': -0.07000, 'b': 0.00190},  # Paper Birch
    'YB': {'a': -0.07000, 'b': 0.00200},  # Yellow Birch
    # PNW conifers (inside bark)
    'DF': {'a': -0.08, 'b': 0.00220},  # Douglas-fir
    'WH': {'a': -0.07, 'b': 0.00215},  # Western Hemlock
    'RC': {'a': -0.08, 'b': 0.00210},  # Western Redcedar
    'SS': {'a': -0.08, 'b': 0.00225},  # Sitka Spruce
    'SF': {'a': -0.07, 'b': 0.00212},  # Silver Fir
    'GF': {'a': -0.07, 'b': 0.00212},  # Grand Fir
    'WF': {'a': -0.07, 'b': 0.00210},  # White Fir
    'NF': {'a': -0.07, 'b': 0.00215},  # Noble Fir
    'AF': {'a': -0.06, 'b': 0.00200},  # Subalpine Fir
    'RF': {'a': -0.07, 'b': 0.00212},  # California Red Fir
    'IC': {'a': -0.08, 'b': 0.00202},  # Incense Cedar
    'ES': {'a': -0.07, 'b': 0.00205},  # Engelmann Spruce
    'YC': {'a': -0.08, 'b': 0.00210},  # Alaska Yellow Cedar
    'RW': {'a': -0.10, 'b': 0.00235},  # Redwood
    'MH': {'a': -0.06, 'b': 0.00208},  # Mountain Hemlock
    # PNW hardwoods (inside bark)
    'RA': {'a': -0.05, 'b': 0.00195},  # Red Alder
    'BM': {'a': -0.05, 'b': 0.00185},  # Bigleaf Maple
    'GC': {'a': -0.05, 'b': 0.00180},  # Giant Chinquapin
    'AS': {'a': -0.05, 'b': 0.00175},  # Quaking Aspen (PNW)
    'CW': {'a': -0.05, 'b': 0.00180},  # Black Cottonwood (PNW)
    'WJ': {'a': -0.08, 'b': 0.00168},  # Western Juniper
    'WB': {'a': -0.07, 'b': 0.00200},  # Whitebark Pine
    'KP': {'a': -0.07, 'b': 0.00195},  # Knobcone Pine
    'HT': {'a': -0.05, 'b': 0.00168},  # Hawthorn
    'WI': {'a': -0.05, 'b': 0.00168},  # Willow
    'OT': {'a': -0.07, 'b': 0.00185},  # Other species (PNW generic)
    # NE-unique species (inside bark)
    'RS': {'a': -0.07000, 'b': 0.00205},  # Red Spruce
    'AW': {'a': -0.07000, 'b': 0.00205},  # Atlantic White Cedar
    'TM': {'a': -0.10000, 'b': 0.00200},  # Table Mountain Pine
    'SB': {'a': -0.07000, 'b': 0.00200},  # Sweet Birch
    'RB': {'a': -0.06000, 'b': 0.00185},  # River Birch
    'GB': {'a': -0.05000, 'b': 0.00168},  # Gray Birch
    'CT': {'a': -0.07000, 'b': 0.00205},  # Cucumbertree
    'CO': {'a': -0.07000, 'b': 0.00195},  # Chestnut Oak
    'SL': {'a': -0.07000, 'b': 0.00195},  # Shellbark Hickory
    'YP': {'a': -0.07000, 'b': 0.00215},  # Yellow-Poplar
    'SU': {'a': -0.06000, 'b': 0.00190},  # Sweetgum
    'SO': {'a': -0.07000, 'b': 0.00195},  # Scarlet Oak
    'CB': {'a': -0.07000, 'b': 0.00200},  # Cherrybark Oak
    'SK': {'a': -0.07000, 'b': 0.00195},  # Southern Red Oak
    'WL': {'a': -0.07000, 'b': 0.00195},  # Willow Oak
    'BU': {'a': -0.06000, 'b': 0.00190},  # Buckeye
    'YY': {'a': -0.06000, 'b': 0.00190},  # Yellow Buckeye
    'MG': {'a': -0.07000, 'b': 0.00205},  # Magnolia
    'MV': {'a': -0.07000, 'b': 0.00205},  # Sweetbay
    'SD': {'a': -0.05000, 'b': 0.00168},  # Sourwood
    'PW': {'a': -0.06000, 'b': 0.00195},  # Paulownia
    'AI': {'a': -0.06000, 'b': 0.00185},  # Ailanthus
    'SE': {'a': -0.05000, 'b': 0.00168},  # Serviceberry
    'EL': {'a': -0.06000, 'b': 0.00185},  # Other Elm
    # Note: 'WB' (White Basswood) omitted — collides with Whitebark Pine above.
    # CS-unique species (inside bark)
    'BY': {'a': -0.08000, 'b': 0.00215},  # Bald Cypress
    'TL': {'a': -0.07000, 'b': 0.00195},  # Tupelo (Black Tupelo)
    'TS': {'a': -0.07000, 'b': 0.00195},  # Swamp Tupelo
    'HS': {'a': -0.07000, 'b': 0.00190},  # Shagbark Hickory
    'PE': {'a': -0.07000, 'b': 0.00190},  # Pecan
    'BI': {'a': -0.07000, 'b': 0.00190},  # Bitternut Hickory
    'UA': {'a': -0.06000, 'b': 0.00185},  # Blue Ash
    'SG': {'a': -0.06000, 'b': 0.00185},  # Sugarberry
    'WE': {'a': -0.06000, 'b': 0.00185},  # Winged Elm
    'SI': {'a': -0.06000, 'b': 0.00185},  # Siberian Elm
    'BJ': {'a': -0.07000, 'b': 0.00185},  # Blackjack Oak
    'DO': {'a': -0.07000, 'b': 0.00195},  # Bottomland Post Oak
    'NK': {'a': -0.07000, 'b': 0.00195},  # Nuttall Oak
    'QS': {'a': -0.07000, 'b': 0.00200},  # Shumard Oak
    'OV': {'a': -0.07000, 'b': 0.00190},  # Overcup Oak
    'UH': {'a': -0.06000, 'b': 0.00185},  # Unidentified Hardwood
    'OB': {'a': -0.06000, 'b': 0.00185},  # Ohio Buckeye
    'CA': {'a': -0.06000, 'b': 0.00180},  # Catalpa
    'HL': {'a': -0.06000, 'b': 0.00190},  # Honeylocust
    'OL': {'a': -0.06000, 'b': 0.00190},  # Other Locust
    'NC': {'a': -0.05000, 'b': 0.00168},  # Other Noncommercial Hdwd
    'RD': {'a': -0.05000, 'b': 0.00168},  # Redbud
    'KC': {'a': -0.06000, 'b': 0.00190},  # Kentucky Coffeetree
    'MB': {'a': -0.06000, 'b': 0.00180},  # Mulberry
    # OP-unique species (inside bark)
    'CL': {'a': -0.05000, 'b': 0.00180},  # California Laurel
    'DEFAULT_SOFTWOOD': {'a': -0.08, 'b': 0.00205},
    'DEFAULT_LAKE_STATES_SOFTWOOD': {'a': -0.07, 'b': 0.00205},
    'DEFAULT_PNW_SOFTWOOD': {'a': -0.07, 'b': 0.00212},
    'DEFAULT_HARDWOOD': {'a': -0.05, 'b': 0.00185},
    'DEFAULT_LAKE_STATES_HARDWOOD': {'a': -0.06, 'b': 0.00190},
    'DEFAULT_PNW_HARDWOOD': {'a': -0.05, 'b': 0.00185},
}

# Hardwood species codes (SN + LS + PNW)
HARDWOOD_SPECIES = {
    # SN hardwoods
    'WO', 'SO', 'WK', 'LK', 'OV', 'CW', 'SK', 'HI', 'SU', 'YP',
    'RM', 'SM', 'SV', 'WA', 'GA', 'RA', 'BA', 'BC', 'SY', 'BG',
    'WE', 'AE', 'RL', 'BE', 'FM', 'OH',
    # LS additional hardwoods
    'EC', 'YB', 'BW', 'BM', 'AB', 'SW', 'BR', 'CK', 'RO', 'BO',
    'BH', 'PH', 'SH', 'BT', 'QA', 'BP', 'PB', 'BN', 'WN', 'HH',
    'BK', 'ST', 'MM', 'AH', 'AC', 'HK', 'DW', 'HT', 'AP', 'PR',
    'CC', 'PL', 'WI', 'BL', 'DM', 'SS', 'MA', 'RE', 'NP',
    # PNW additional hardwoods
    'GC', 'AS', 'PY', 'DG', 'CH',
    # NE additional hardwoods
    'SB', 'RB', 'GB', 'WR', 'SL', 'CT', 'PO', 'OK', 'QI', 'PN', 'CO',
    'SW', 'SN', 'CB', 'WL', 'BU', 'YY', 'PS', 'HY', 'OO', 'MG', 'MV',
    'WT', 'SD', 'PW', 'WB', 'EL', 'AI', 'SE', 'SK', 'SO', 'YP', 'SU',
    # CS additional hardwoods
    'TL', 'TS', 'HS', 'PE', 'BI', 'UA', 'SG', 'WE', 'SI', 'RL',
    'BJ', 'DO', 'NK', 'QS', 'OV', 'UH', 'OB', 'CA', 'HL', 'OL',
    'NC', 'RD', 'KC', 'MB',
    # OP additional hardwoods
    'CL',
}

# FVS merchantability specifications
STUMP_HEIGHT = 1.0  # feet
MIN_MERCH_DBH = 5.0  # inches
MIN_MERCH_TOP = 4.0  # inches DOB


class VolumeCalculator:
    """Calculate tree volumes using taper models or combined-variable equations.

    When taper coefficients are available for the species+variant, uses
    stem profile models (Clark or Flewelling) with per-log merchandising
    for accurate board-foot and cubic-foot volumes.

    Falls back to combined-variable equations (V = a + b × D²H) when
    taper coefficients are not available.

    References:
        Clark et al. (1991) SE-282 - Stem Profile Equations for Southern Species
        Flewelling & Raynes (1993) - Variable-shape stem-profile predictions
        Amateis & Burkhart (1987) - Cubic-Foot Volume Equations for Loblolly Pine
    """

    def __init__(self, species_code: str = "LP", variant: Optional[str] = None):
        """Initialize volume calculator.

        Args:
            species_code: FVS species code (default: LP for Loblolly Pine)
            variant: FVS variant code (e.g., 'SN', 'PN'). If None, uses
                     the current default variant.
        """
        from .taper import create_taper_model

        self.species_code = species_code
        self.variant = variant or get_default_variant()
        self.is_hardwood = species_code in HARDWOOD_SPECIES

        # Set sawlog specifications based on species type
        if self.is_hardwood:
            self.min_saw_dbh = 11.0  # inches
            self.min_saw_top = 9.6   # inches DIB
        else:
            self.min_saw_dbh = 9.0   # inches
            self.min_saw_top = 7.6   # inches DIB

        # Get combined-variable coefficients (fallback)
        default_key = 'DEFAULT_HARDWOOD' if self.is_hardwood else 'DEFAULT_SOFTWOOD'
        self.coef_ob = VOLUME_COEFFICIENTS_OUTSIDE_BARK.get(
            species_code,
            VOLUME_COEFFICIENTS_OUTSIDE_BARK[default_key]
        )
        self.coef_ib = VOLUME_COEFFICIENTS_INSIDE_BARK.get(
            species_code,
            VOLUME_COEFFICIENTS_INSIDE_BARK[default_key]
        )

        # Try to get a taper model for this species/variant
        self._taper_model = create_taper_model(species_code, self.variant)

    def calculate_volume(self, dbh: float, height: float) -> VolumeResult:
        """Calculate tree volume.

        Uses taper-based volume when a taper model is available for this
        species+variant, otherwise falls back to combined-variable equations.

        Args:
            dbh: Diameter at breast height (inches, outside bark)
            height: Total tree height (feet)

        Returns:
            VolumeResult object with calculated volumes
        """
        # Try taper-based volume first
        if self._taper_model is not None and dbh >= 1.0 and height > 4.5:
            try:
                return self._calculate_volume_taper(dbh, height)
            except (ValueError, ZeroDivisionError, KeyError, AttributeError) as exc:
                logger.debug(
                    "Taper volume failed for %s (DBH=%.1f, HT=%.1f): %s; "
                    "falling back to combined-variable",
                    self.species_code, dbh, height, exc,
                )

        return self._calculate_volume_combined_variable(dbh, height)

    def _calculate_volume_taper(self, dbh: float, height: float) -> VolumeResult:
        """Taper-based volume with per-log merchandising.

        Uses the taper model to predict stem profile.  Merchantable cubic
        volume is computed from stump to the 4" DOB top (standard FVS
        practice).  Board-foot volumes come from per-log merchandising
        with the variant-specific primary-product top DIB.
        """
        from .merchandising import merchandise_tree, get_merchandising_rules

        taper = self._taper_model
        taper.initialize_tree(dbh, height)

        # Total cubic volume (stump to tip, inside bark)
        total_cubic = taper.predict_volume(STUMP_HEIGHT, height)

        # Merchantable cubic: stump to 4" top DIB (MIN_MERCH_TOP)
        # This is separate from board-foot merchandising which uses a
        # higher top diameter (6-7") for sawtimber.
        merch_cubic = 0.0
        if dbh >= MIN_MERCH_DBH:
            merch_top_ht = taper.predict_height_to_dib(MIN_MERCH_TOP)
            if merch_top_ht > STUMP_HEIGHT:
                merch_cubic = taper.predict_volume(STUMP_HEIGHT, merch_top_ht)
                merch_cubic = min(merch_cubic, total_cubic)

        # Board-foot merchandising: use variant-specific rules
        # (6" or 7" primary product top)
        rules = get_merchandising_rules(self.variant)
        logs, _log_cubic, tip_vol = merchandise_tree(taper, rules)

        # Sum board feet across all logs
        bf_scribner = sum(log.bf_scribner for log in logs)
        bf_international = sum(log.bf_international for log in logs)
        bf_doyle = sum(log.bf_doyle for log in logs)

        # Cord volume from merchantable cubic
        cord_volume = merch_cubic / 79.0 if merch_cubic > 0 else 0.0

        # Net cubic (apply 5% defect allowance)
        net_cubic = total_cubic * 0.95

        return VolumeResult(
            total_cubic_volume=total_cubic,
            gross_cubic_volume=total_cubic,
            net_cubic_volume=net_cubic,
            merchantable_cubic_volume=merch_cubic,
            board_foot_volume=bf_scribner,
            cord_volume=cord_volume,
            board_foot_international=bf_international,
            board_foot_doyle=bf_doyle,
        )

    def _calculate_volume_combined_variable(self, dbh: float,
                                            height: float) -> VolumeResult:
        """Combined-variable fallback: V = a + b * D²H.

        Used when taper coefficients are not available.  Computes board-foot
        volumes using all three standard log rules (Scribner, International
        1/4", and Doyle) for consistency with the taper pathway.
        """
        from .bark_ratio import create_bark_ratio_model
        from .merchandising import (scribner_decimal_c,
                                    international_quarter_inch, doyle)

        try:
            # Calculate combined variable D²H
            d2h = dbh * dbh * height

            # Calculate total cubic volume using combined-variable equation
            # V = a + b × D²H
            total_cubic_ib = max(0.0, self.coef_ib['a'] + self.coef_ib['b'] * d2h)

            # Use inside bark as primary total volume to match taper pathway.
            # Taper models return IB volume; CV must be consistent so that
            # switching pathways (e.g., if taper coefficients are missing)
            # doesn't cause a ~10% volume discontinuity.
            total_cubic = total_cubic_ib

            # Get inside-bark diameter for merchantable calculations
            bark_model = create_bark_ratio_model(self.species_code)
            dbh_inside_bark = bark_model.apply_bark_ratio_to_dbh(dbh)

            # Initialize volume components
            merchantable_cubic = 0.0
            sawlog_cubic = 0.0
            cord_volume = 0.0
            bf_scribner = 0.0
            bf_international = 0.0
            bf_doyle = 0.0

            # Calculate merchantable cubic volume (trees >= 5" DBH)
            if dbh >= MIN_MERCH_DBH:
                merch_height = self._estimate_merchantable_height(
                    dbh, height, MIN_MERCH_TOP, STUMP_HEIGHT
                )

                # Merchantable volume ratio based on top diameter
                if height > 0:
                    merch_ratio = merch_height / height
                    # Adjust for volume concentration in lower stem
                    merch_ratio = min(0.90, merch_ratio * 1.1)
                else:
                    merch_ratio = 0.85

                merchantable_cubic = total_cubic_ib * merch_ratio

                # Convert to cords (1 cord = 128 cu ft gross, ~79 cu ft solid wood)
                cord_volume = merchantable_cubic / 79.0

            # Calculate board foot volume (sawlog trees only)
            if dbh >= self.min_saw_dbh:
                sawlog_height = self._estimate_merchantable_height(
                    dbh, height, self.min_saw_top, STUMP_HEIGHT
                )

                # Sawlog cubic volume
                if height > 0:
                    sawlog_ratio = sawlog_height / height
                    sawlog_ratio = min(0.85, sawlog_ratio * 1.05)
                else:
                    sawlog_ratio = 0.75
                sawlog_cubic = total_cubic_ib * sawlog_ratio

                # Board foot calculation using all three log rules
                stump_dib = dbh_inside_bark * 0.95

                if stump_dib > 4:
                    num_logs = int(sawlog_height / 16)
                    remaining_length = sawlog_height - (num_logs * 16)

                    for i in range(num_logs):
                        log_dib = stump_dib - (i * 2.0)
                        if log_dib >= 4:
                            bf_scribner += scribner_decimal_c(log_dib, 16.0)
                            bf_international += international_quarter_inch(log_dib, 16.0)
                            bf_doyle += doyle(log_dib, 16.0)

                    if remaining_length > 8 and (stump_dib - num_logs * 2.0) > 4:
                        log_dib = stump_dib - (num_logs * 2.0)
                        bf_scribner += scribner_decimal_c(log_dib, remaining_length)
                        bf_international += international_quarter_inch(log_dib, remaining_length)
                        bf_doyle += doyle(log_dib, remaining_length)

                    # Apply defect factor
                    bf_scribner *= 0.92
                    bf_international *= 0.92
                    bf_doyle *= 0.92

            return VolumeResult(
                total_cubic_volume=total_cubic,
                gross_cubic_volume=total_cubic,
                net_cubic_volume=total_cubic * 0.95,
                merchantable_cubic_volume=merchantable_cubic,
                board_foot_volume=bf_scribner,
                cord_volume=cord_volume,
                sawlog_cubic_volume=sawlog_cubic,
                sawlog_board_foot=bf_scribner,
                board_foot_international=bf_international,
                board_foot_doyle=bf_doyle,
            )

        except (ValueError, ZeroDivisionError, KeyError, AttributeError) as exc:
            logger.warning(
                "Combined-variable volume failed for %s (DBH=%.1f, HT=%.1f): %s; "
                "using LP default coefficients",
                self.species_code, dbh, height, exc,
            )
            d2h = dbh * dbh * height
            cubic_volume = max(0.0, 0.18658 + 0.00250 * d2h)
            return VolumeResult(total_cubic_volume=cubic_volume)

    def _estimate_merchantable_height(
        self,
        dbh: float,
        total_height: float,
        top_dob: float,
        stump_height: float
    ) -> float:
        """Estimate merchantable height using simplified taper model.

        Args:
            dbh: Diameter at breast height (inches)
            total_height: Total tree height (feet)
            top_dob: Minimum top diameter outside bark (inches)
            stump_height: Stump height (feet)

        Returns:
            Merchantable height in feet (from stump to merchantable top)
        """
        if dbh <= top_dob:
            return 0.0

        # Simplified linear taper model
        height_to_top = total_height * (1 - (top_dob / dbh))

        # Merchantable height is from stump to merch top
        merch_height = height_to_top - stump_height

        # Ensure positive and reasonable
        merch_height = max(0.0, merch_height)
        merch_height = min(merch_height, total_height - stump_height - 4.0)

        return merch_height

    def get_supported_species(self) -> List[str]:
        """Get list of supported species codes with explicit coefficients."""
        return list(VOLUME_COEFFICIENTS_OUTSIDE_BARK.keys())


# Backwards compatibility alias
VolumeLibrary = VolumeCalculator


# Module-level cache for VolumeCalculator instances, keyed by variant:species
_volume_calculators: Dict[str, VolumeCalculator] = {}


def get_volume_library(species_code: str = "LP",
                       variant: Optional[str] = None) -> VolumeCalculator:
    """Get a cached volume calculator instance for the given species+variant.

    Args:
        species_code: FVS species code (default: LP for Loblolly Pine)
        variant: FVS variant code. If None, uses the current default variant.

    Returns:
        VolumeCalculator instance (cached per species+variant)
    """
    variant = variant or get_default_variant()
    cache_key = f"{variant}:{species_code}"
    if cache_key not in _volume_calculators:
        _volume_calculators[cache_key] = VolumeCalculator(species_code, variant)
    return _volume_calculators[cache_key]


def calculate_tree_volume(
    dbh: float,
    height: float,
    species_code: str = "LP",
    variant: Optional[str] = None,
    **kwargs: Any
) -> VolumeResult:
    """Calculate tree volume.

    Convenience function for calculating tree volume using a cached
    VolumeCalculator instance for the given species and variant.

    Uses taper-based volume when available, otherwise falls back to
    combined-variable equations.

    Args:
        dbh: Diameter at breast height (inches, outside bark)
        height: Total tree height (feet)
        species_code: FVS species code (default: LP)
        variant: FVS variant code. If None, uses the default variant.
        **kwargs: Additional arguments (ignored, for backwards compatibility)

    Returns:
        VolumeResult object with calculated volumes
    """
    calculator = get_volume_library(species_code, variant)
    return calculator.calculate_volume(dbh, height)


def get_volume_library_info() -> Dict[str, Any]:
    """Get information about the volume library.

    Returns:
        Dictionary with library information
    """
    return {
        'name': 'PyFVS Volume Calculator',
        'description': 'Combined-variable volume equations from published research',
        'references': [
            'Amateis & Burkhart (1987) - Cubic-Foot Volume Equations for Loblolly Pine',
            'Tasissa et al. (1997) - Volume ratio equations for southern pines',
            'Gonzalez-Benecke et al. (2014) - Longleaf pine volume functions',
            'Clark et al. (1991) SE-282 - Stem Profile Equations for Southern Species',
        ],
        'supported_species': list(VOLUME_COEFFICIENTS_OUTSIDE_BARK.keys()),
        'equations': {
            'total_cubic': 'V = a + b × D²H (outside bark)',
            'merchantable': 'Trees ≥5" DBH, from 1-ft stump to 4" top DOB',
            'sawlog_softwood': 'Trees ≥9" DBH to 7.6" top DIB',
            'sawlog_hardwood': 'Trees ≥11" DBH to 9.6" top DIB',
        }
    }


def validate_volume_library() -> Dict[str, Any]:
    """Validate volume library is working correctly.

    Returns:
        Dictionary with validation results
    """
    test_cases = [
        {'dbh': 10.0, 'height': 60.0, 'species': 'LP'},
        {'dbh': 15.0, 'height': 80.0, 'species': 'LP'},
        {'dbh': 8.0, 'height': 50.0, 'species': 'SA'},
    ]

    results = []
    for case in test_cases:
        result = calculate_tree_volume(
            case['dbh'],
            case['height'],
            case['species']
        )
        results.append({
            'input': case,
            'total_cubic': result.total_cubic_volume,
            'merchantable_cubic': result.merchantable_cubic_volume,
            'board_foot': result.board_foot_volume,
            'valid': result.is_valid()
        })

    return {
        'status': 'ok',
        'test_results': results,
        'all_valid': all(r['valid'] for r in results)
    }

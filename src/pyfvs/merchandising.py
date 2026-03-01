"""
Log merchandising and board-foot scaling rules.

Implements tree merchandising (log bucking) and three board-foot log rules:

- **Scribner Decimal C**: Standard USFS rule, lookup table from NVEL scrib.f.
  Most common in western US and FVS. Board feet per 16-ft log by small-end DIB.

- **International 1/4-inch**: FIA standard rule, formula-based.
  Subdivides each log into 4-ft sections with 0.5-inch taper per section.
  Considered the most accurate rule.

- **Doyle**: Traditional eastern US rule.
  BF = (DIB - 4)^2 * L / 16. Overestimates defect in small logs.

Usage:
    from pyfvs.taper import create_taper_model
    from pyfvs.merchandising import merchandise_tree, get_merchandising_rules

    taper = create_taper_model('LP', 'SN')
    taper.initialize_tree(dbh=14.0, height=85.0)
    rules = get_merchandising_rules('SN')
    logs, merch_vol, tip_vol = merchandise_tree(taper, rules)
"""
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from .taper import TaperModel


# ============================================================================
# Data structures
# ============================================================================

class LogRule(Enum):
    """Board-foot log scaling rules."""
    SCRIBNER = 'scribner'
    INTERNATIONAL = 'international'
    DOYLE = 'doyle'


@dataclass
class MerchandisingRules:
    """Merchandising specifications for log bucking.

    Controls how a tree stem is divided into logs, matching the
    MERCHRULES type in NVEL mrules.f.
    """
    stump_height: float = 1.0            # Stump height (feet)
    min_top_dib_primary: float = 6.0     # Primary product min top DIB (inches)
    min_top_dib_secondary: float = 4.0   # Secondary product min top DIB (inches)
    max_log_length: float = 16.0         # Maximum log length (feet, nominal)
    min_log_length: float = 8.0          # Minimum log length (feet)
    trim_allowance: float = 0.5          # Trim per log (feet)
    min_dbh_sawtimber_sw: float = 9.0    # Min DBH for softwood sawtimber
    min_dbh_sawtimber_hw: float = 11.0   # Min DBH for hardwood sawtimber
    min_merch_length: float = 8.0        # Minimum merchantable bole length


@dataclass
class LogSegment:
    """A single log segment from a merchandised tree.

    Contains dimensions and volume in all three board-foot rules.
    """
    position: int              # Log number (1 = butt log)
    length: float              # Nominal log length (feet, without trim)
    large_end_dib: float       # DIB at large (bottom) end (inches)
    small_end_dib: float       # DIB at small (top) end (inches)
    height_bottom: float       # Height of large end above ground (feet)
    height_top: float          # Height of small end above ground (feet)
    cubic_volume: float = 0.0  # Smalian cubic-foot volume
    bf_scribner: float = 0.0   # Scribner Decimal C board feet
    bf_international: float = 0.0  # International 1/4" board feet
    bf_doyle: float = 0.0      # Doyle board feet


# ============================================================================
# Scribner Decimal C table
# ============================================================================

# Board feet per 16-foot log by small-end DIB (inches).
# From NVEL scrib.f. Values are in Decimal C (divide by 10 for standard).
# Index: DIB in 1-inch classes from 6" to 50".
# For non-16ft logs, scale proportionally by length/16.
SCRIBNER_16FT: List[float] = [
    # DIB:  6     7     8     9    10    11    12    13    14    15
            10,   20,   30,   40,   60,   80,  100,  120,  150,  180,
    # DIB: 16    17    18    19    20    21    22    23    24    25
           210,  250,  290,  330,  370,  420,  470,  520,  570,  630,
    # DIB: 26    27    28    29    30    31    32    33    34    35
           690,  750,  820,  890,  960, 1030, 1110, 1190, 1270, 1360,
    # DIB: 36    37    38    39    40    41    42    43    44    45
          1450, 1540, 1640, 1740, 1840, 1940, 2050, 2160, 2270, 2390,
    # DIB: 46    47    48    49    50
          2510, 2630, 2760, 2890, 3020,
]

# Minimum DIB for Scribner (6 inches)
_SCRIB_MIN_DIB = 6
_SCRIB_MAX_DIB = 50


def scribner_decimal_c(small_end_dib: float, log_length: float) -> float:
    """Compute Scribner Decimal C board feet for a single log.

    Uses the standard NVEL lookup table indexed by small-end DIB
    for 16-ft logs, scaled proportionally for other lengths.

    Args:
        small_end_dib: Small-end diameter inside bark (inches).
        log_length: Log length in feet (nominal, excluding trim).

    Returns:
        Board feet (Scribner Decimal C).
    """
    if small_end_dib < _SCRIB_MIN_DIB or log_length <= 0:
        return 0.0

    # Clamp DIB to table range
    dib_int = int(round(small_end_dib))
    dib_int = max(_SCRIB_MIN_DIB, min(_SCRIB_MAX_DIB, dib_int))

    # Table index (0-based, starting at DIB=6)
    idx = dib_int - _SCRIB_MIN_DIB
    if idx >= len(SCRIBNER_16FT):
        idx = len(SCRIBNER_16FT) - 1

    bf_16 = SCRIBNER_16FT[idx]

    # Scale for non-16ft logs
    bf = bf_16 * (log_length / 16.0)

    return bf


# ============================================================================
# International 1/4-inch rule
# ============================================================================

def international_quarter_inch(small_end_dib: float,
                               log_length: float) -> float:
    """Compute International 1/4-inch board feet for a single log.

    Subdivides the log into 4-ft sections, assuming 0.5-inch taper
    per 4-ft section (1/8 inch per foot). Each section volume is
    computed from the formula:

        SEGVOL = (0.22 * D^2 - 0.71 * D) * 0.905

    where D is the small-end diameter of that 4-ft section.

    From NVEL intl78.f.

    Args:
        small_end_dib: Small-end diameter inside bark (inches).
        log_length: Log length in feet.

    Returns:
        Board feet (International 1/4-inch rule).
    """
    if small_end_dib < 4.0 or log_length <= 0:
        return 0.0

    total_bf = 0.0
    taper_per_4ft = 0.5  # 0.5 inch taper per 4-ft section

    # Number of 4-ft sections
    n_sections = int(log_length / 4.0)
    remainder = log_length - (n_sections * 4.0)

    # Process each 4-ft section from top (small end) down
    current_dib = small_end_dib
    for _ in range(n_sections):
        seg_vol = (0.22 * current_dib ** 2 - 0.71 * current_dib) * 0.905
        total_bf += max(0.0, seg_vol)
        current_dib += taper_per_4ft  # Moving toward butt, diameter increases

    # Handle remainder
    if remainder > 0:
        seg_vol = (0.22 * current_dib ** 2 - 0.71 * current_dib) * 0.905
        total_bf += max(0.0, seg_vol * (remainder / 4.0))

    # Round to nearest 5 board feet (per NVEL convention)
    total_bf = round(total_bf / 5.0) * 5.0

    return total_bf


# ============================================================================
# Doyle rule
# ============================================================================

def doyle(small_end_dib: float, log_length: float) -> float:
    """Compute Doyle board feet for a single log.

    Formula: BF = (DIB - 4)^2 * L / 16

    The Doyle rule is the simplest and least accurate rule.
    It overestimates defect in small logs (< 14" DIB) and
    underestimates in large logs.

    Args:
        small_end_dib: Small-end diameter inside bark (inches).
        log_length: Log length in feet.

    Returns:
        Board feet (Doyle rule).
    """
    if small_end_dib <= 4.0 or log_length <= 0:
        return 0.0

    bf = (small_end_dib - 4.0) ** 2 * log_length / 16.0
    return bf


# ============================================================================
# Log-rule dispatcher
# ============================================================================

def compute_board_feet(small_end_dib: float, log_length: float,
                       rule: LogRule) -> float:
    """Compute board feet using the specified log rule.

    Args:
        small_end_dib: Small-end DIB (inches).
        log_length: Log length (feet).
        rule: Which log rule to apply.

    Returns:
        Board feet.
    """
    if rule == LogRule.SCRIBNER:
        return scribner_decimal_c(small_end_dib, log_length)
    elif rule == LogRule.INTERNATIONAL:
        return international_quarter_inch(small_end_dib, log_length)
    elif rule == LogRule.DOYLE:
        return doyle(small_end_dib, log_length)
    return 0.0


# ============================================================================
# Smalian cubic volume
# ============================================================================

# Smalian constant: pi / (4 * 144 * 2)
_SMALIAN_K = 0.00272708


def smalian_cubic(large_end_dib: float, small_end_dib: float,
                  length: float) -> float:
    """Compute cubic-foot volume using Smalian's formula.

    V = K * (D1^2 + D2^2) * L

    where K = pi / (4 * 144 * 2) = 0.00272708

    Args:
        large_end_dib: Large-end DIB (inches).
        small_end_dib: Small-end DIB (inches).
        length: Log length (feet).

    Returns:
        Cubic feet.
    """
    if length <= 0:
        return 0.0
    return _SMALIAN_K * (large_end_dib ** 2 + small_end_dib ** 2) * length


# ============================================================================
# Tree merchandising
# ============================================================================

def merchandise_tree(
    taper_model: TaperModel,
    rules: Optional[MerchandisingRules] = None,
) -> Tuple[List[LogSegment], float, float]:
    """Buck a tree into logs using taper-predicted diameters.

    Determines the merchantable bole length from the taper model,
    divides it into logs according to the merchandising rules,
    and computes cubic and board-foot volumes for each log using
    all three log rules.

    Args:
        taper_model: An initialized TaperModel (initialize_tree must
                     have been called).
        rules: Merchandising specifications. Uses defaults if None.

    Returns:
        Tuple of:
        - List of LogSegment objects (one per log, butt to top)
        - Total merchantable cubic volume (sum of log cubic volumes)
        - Tip cubic volume (from merch top to tree tip)
    """
    if rules is None:
        rules = MerchandisingRules()

    dbh = taper_model.dbh
    height = taper_model.height

    if dbh is None or height is None or height <= 4.5 or dbh < 1.0:
        return [], 0.0, 0.0

    # 1. Find merchantable top height
    merch_top_ht = taper_model.predict_height_to_dib(rules.min_top_dib_primary)
    if merch_top_ht <= rules.stump_height:
        return [], 0.0, 0.0

    # 2. Merchantable length
    merch_length = merch_top_ht - rules.stump_height

    if merch_length < rules.min_merch_length:
        return [], 0.0, 0.0

    # 3. Determine number and length of logs
    # NVEL approach: divide into nominal log lengths with trim,
    # combine top piece if too short.
    nominal_length = rules.max_log_length
    effective_log_length = nominal_length + rules.trim_allowance

    n_full_logs = int(merch_length / effective_log_length)
    remainder = merch_length - (n_full_logs * effective_log_length)

    # If remainder is too short, combine with last full log
    if remainder > 0 and remainder < rules.min_log_length:
        if n_full_logs > 0:
            # Redistribute: split the last log + remainder into 2
            combined = effective_log_length + remainder
            if combined >= 2 * rules.min_log_length:
                # Two shorter logs
                half = combined / 2.0
                log_lengths = ([effective_log_length] * (n_full_logs - 1)
                               + [half, half])
            else:
                # One longer log
                log_lengths = ([effective_log_length] * (n_full_logs - 1)
                               + [combined])
        else:
            # Single short log (still above min merch length)
            log_lengths = [remainder]
    elif remainder >= rules.min_log_length:
        log_lengths = [effective_log_length] * n_full_logs + [remainder]
    else:
        log_lengths = [effective_log_length] * n_full_logs

    if not log_lengths:
        return [], 0.0, 0.0

    # 4. Build log segments from stump upward
    logs: List[LogSegment] = []
    current_ht = rules.stump_height

    for i, log_len in enumerate(log_lengths):
        top_ht = current_ht + log_len
        top_ht = min(top_ht, merch_top_ht)
        actual_len = top_ht - current_ht

        if actual_len <= 0:
            break

        # Get DIB at both ends from taper model
        large_dib = taper_model.predict_dib(current_ht)
        small_dib = taper_model.predict_dib(top_ht)

        # Nominal length for board foot calculation (without trim)
        nominal = min(actual_len, nominal_length)

        # Compute volumes using all three rules
        cubic = smalian_cubic(large_dib, small_dib, actual_len)
        bf_scrib = scribner_decimal_c(small_dib, nominal)
        bf_intl = international_quarter_inch(small_dib, nominal)
        bf_doyle_val = doyle(small_dib, nominal)

        log = LogSegment(
            position=i + 1,
            length=nominal,
            large_end_dib=large_dib,
            small_end_dib=small_dib,
            height_bottom=current_ht,
            height_top=top_ht,
            cubic_volume=cubic,
            bf_scribner=bf_scrib,
            bf_international=bf_intl,
            bf_doyle=bf_doyle_val,
        )
        logs.append(log)
        current_ht = top_ht

    # 5. Sum merchantable cubic
    merch_cubic = sum(log.cubic_volume for log in logs)

    # 6. Tip volume (merch top to tree tip)
    tip_vol = taper_model.predict_volume(merch_top_ht, height)

    return logs, merch_cubic, tip_vol


# ============================================================================
# Regional merchandising rules
# ============================================================================

# Default merchandising rules by FVS variant.
# Values from NVEL mrules.f regional defaults.
REGIONAL_RULES: dict[str, MerchandisingRules] = {}

# Workaround: can't use Dict in module-level due to dataclass import order
def _init_regional_rules():
    global REGIONAL_RULES
    REGIONAL_RULES = {
        # Eastern US (Regions 8, 9): 7" top for sawtimber
        'SN': MerchandisingRules(
            min_top_dib_primary=7.0,
            min_top_dib_secondary=4.0,
            max_log_length=16.0,
            min_log_length=8.0,
            trim_allowance=0.3,
            min_dbh_sawtimber_sw=9.0,
            min_dbh_sawtimber_hw=11.0,
        ),
        'NE': MerchandisingRules(
            min_top_dib_primary=7.0,
            min_top_dib_secondary=4.0,
            max_log_length=16.0,
            min_log_length=8.0,
            trim_allowance=0.3,
        ),
        'CS': MerchandisingRules(
            min_top_dib_primary=7.0,
            min_top_dib_secondary=4.0,
            max_log_length=16.0,
            min_log_length=8.0,
            trim_allowance=0.3,
        ),
        'LS': MerchandisingRules(
            min_top_dib_primary=7.0,
            min_top_dib_secondary=4.0,
            max_log_length=16.0,
            min_log_length=8.0,
            trim_allowance=0.3,
        ),
        # Western US (Region 6): 6" top for sawtimber
        'PN': MerchandisingRules(
            min_top_dib_primary=6.0,
            min_top_dib_secondary=4.0,
            max_log_length=32.0,
            min_log_length=8.0,
            trim_allowance=0.5,
        ),
        'WC': MerchandisingRules(
            min_top_dib_primary=6.0,
            min_top_dib_secondary=4.0,
            max_log_length=32.0,
            min_log_length=8.0,
            trim_allowance=0.5,
        ),
        'OP': MerchandisingRules(
            min_top_dib_primary=6.0,
            min_top_dib_secondary=4.0,
            max_log_length=32.0,
            min_log_length=8.0,
            trim_allowance=0.5,
        ),
    }

_init_regional_rules()


def get_merchandising_rules(variant: Optional[str] = None) -> MerchandisingRules:
    """Get default merchandising rules for a variant.

    Args:
        variant: FVS variant code. If None, returns generic defaults.

    Returns:
        MerchandisingRules for the variant.
    """
    if variant and variant in REGIONAL_RULES:
        return REGIONAL_RULES[variant]
    return MerchandisingRules()

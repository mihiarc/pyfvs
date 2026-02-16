"""
Crown ratio relationship functions for FVS-Python.

Supports multiple FVS variants:
- SN (Southern): Weibull-based crown model
- LS (Lake States): TWIGS model from Belcher et al. (1982)
- NE (Northeast): TWIGS model (same as LS, different coefficients)
- PN (Pacific Northwest Coast): Weibull with linear mean CR from crown.f
"""
import math
import random
from typing import Dict, Any, Optional, Tuple

from .model_base import ParameterizedModel
from .config_loader import load_coefficient_file, get_default_variant

__all__ = [
    'CrownRatioModel',
    'LSCrownRatioModel',
    'NECrownRatioModel',
    'CSCrownRatioModel',
    'PNCrownRatioModel',
    'create_crown_ratio_model',
    'calculate_average_crown_ratio',
    'predict_tree_crown_ratio',
    'compare_crown_ratio_models',
]


class CrownRatioModel(ParameterizedModel):
    """Crown ratio model implementing FVS Southern variant equations.

    Uses the base class pattern for loading species-specific coefficients
    from sn_crown_ratio_coefficients.json with fallback support.
    """

    # Class attributes for ParameterizedModel base class
    COEFFICIENT_FILE = 'sn_crown_ratio_coefficients.json'
    COEFFICIENT_KEY = 'species_coefficients'
    FALLBACK_PARAMETERS = {
        'LP': {
            "acr_equation": "4.3.1.3",
            "d0": 3.8284,
            "d1": -0.2234,
            "d2": 0.0172,
            "a": 4.9701,
            "b0": -14.6680,
            "b1": 1.3196,
            "c": 2.8517
        },
        'SP': {
            "acr_equation": "4.3.1.3",
            "d0": 3.8284,
            "d1": -0.2234,
            "d2": 0.0172,
            "a": 4.9701,
            "b0": -14.6680,
            "b1": 1.3196,
            "c": 2.8517
        },
        'SA': {
            "acr_equation": "4.3.1.3",
            "d0": 3.8284,
            "d1": -0.2234,
            "d2": 0.0172,
            "a": 4.9701,
            "b0": -14.6680,
            "b1": 1.3196,
            "c": 2.8517
        },
        'LL': {
            "acr_equation": "4.3.1.3",
            "d0": 3.8284,
            "d1": -0.2234,
            "d2": 0.0172,
            "a": 4.9701,
            "b0": -14.6680,
            "b1": 1.3196,
            "c": 2.8517
        },
    }
    DEFAULT_SPECIES = "LP"

    def __init__(self, species_code: str = "LP"):
        """Initialize with species-specific parameters.

        Args:
            species_code: Species code (e.g., "LP", "SP", "WO", etc.)
        """
        super().__init__(species_code)

    def _load_parameters(self):
        """Load crown ratio parameters from cached configuration.

        Extends base class to also load equation info.
        """
        # Call parent to load coefficients
        super()._load_parameters()

        # Load additional crown ratio specific data (equations)
        if self.raw_data:
            self.equations = self.raw_data.get('equations', {})
        else:
            self._load_fallback_equation_info()

    def _load_fallback_parameters(self):
        """Load fallback parameters if crown ratio file not available."""
        # Call parent for coefficient fallback
        super()._load_fallback_parameters()
        # Also load fallback equation info
        self._load_fallback_equation_info()

    def _load_fallback_equation_info(self):
        """Load fallback equation info when file not available."""
        self.equations = {
            "live_trees_weibull": {
                "average_crown_ratio_equations": {
                    "4_3_1_3": "ACR = exp[d0 + (d1 * ln(RELSDI)) + (d2 * RELSDI)]",
                    "4_3_1_4": "ACR = exp[d0 + (d1 * ln(RELSDI))]",
                    "4_3_1_5": "ACR = d0 + (d2 * RELSDI)",
                    "4_3_1_6": "ACR = d0 + (d1 * log10(RELSDI))",
                    "4_3_1_7": "ACR = RELSDI / ((d0 * RELSDI) + d1)"
                }
            }
        }

    def calculate_average_crown_ratio(self, relsdi: float) -> float:
        """Calculate average crown ratio for the stand using species-specific equation.

        Args:
            relsdi: Relative stand density index ((Stand SDI / Maximum SDI) * 10)
                   Bounded between 1.0 and 12.0

        Returns:
            Average crown ratio as a proportion (0-1)
        """
        # Bound RELSDI
        relsdi = max(1.0, min(12.0, relsdi))

        equation_type = self.coefficients['acr_equation']
        d0 = self.coefficients['d0']
        d1 = self.coefficients.get('d1')
        d2 = self.coefficients.get('d2')

        if equation_type == "4.3.1.3":
            # ACR = exp[d0 + (d1 * ln(RELSDI)) + (d2 * RELSDI)]
            if d1 is not None and d2 is not None:
                acr = math.exp(d0 + (d1 * math.log(relsdi)) + (d2 * relsdi))
            else:
                acr = math.exp(d0)
        elif equation_type == "4.3.1.4":
            # ACR = exp[d0 + (d1 * ln(RELSDI))]
            if d1 is not None:
                acr = math.exp(d0 + (d1 * math.log(relsdi)))
            else:
                acr = math.exp(d0)
        elif equation_type == "4.3.1.5":
            # ACR = d0 + (d2 * RELSDI)
            if d2 is not None:
                acr = d0 + (d2 * relsdi)
            else:
                acr = d0
        elif equation_type == "4.3.1.6":
            # ACR = d0 + (d1 * log10(RELSDI))
            if d1 is not None:
                acr = d0 + (d1 * math.log10(relsdi))
            else:
                acr = d0
        elif equation_type == "4.3.1.7":
            # ACR = RELSDI / ((d0 * RELSDI) + d1)
            if d1 is not None:
                acr = relsdi / ((d0 * relsdi) + d1)
            else:
                acr = relsdi / (d0 * relsdi + 1.0)
        else:
            # Default fallback
            acr = math.exp(d0 + (d1 or 0) * math.log(relsdi) + (d2 or 0) * relsdi)

        # Convert from percentage to proportion and bound
        if acr > 1.0:  # Assume it's in percentage
            acr = acr / 100.0

        return max(0.05, min(0.95, acr))

    def calculate_weibull_parameters(self, average_crown_ratio: float) -> Tuple[float, float, float]:
        """Calculate Weibull distribution parameters from average crown ratio.

        Args:
            average_crown_ratio: Average crown ratio as proportion (0-1)

        Returns:
            Tuple of (A, B, C) Weibull parameters
        """
        a = self.coefficients['a']
        b0 = self.coefficients['b0']
        b1 = self.coefficients['b1']
        c = self.coefficients['c']

        # Convert ACR from proportion (0-1) to percentage (0-100) for Weibull calculation
        # The b0/b1 coefficients were calibrated expecting ACR in percentage form
        acr_pct = average_crown_ratio * 100.0

        # Calculate Weibull parameters
        A = a
        B = max(3.0, b0 + b1 * acr_pct)  # Bounded to be greater than 3.0
        C = max(2.0, c)  # Bounded to be greater than 2.0

        return A, B, C

    def calculate_scale_factor(self, ccf: float) -> float:
        """Calculate density-dependent scaling factor.

        Args:
            ccf: Crown competition factor

        Returns:
            Scale factor (bounded 0.3 < SCALE < 1.0)
        """
        scale = 1.0 - 0.00167 * (ccf - 100)
        return max(0.3, min(1.0, scale))

    def predict_individual_crown_ratio(self, tree_rank: float, relsdi: float,
                                     ccf: float = 100.0) -> float:
        """Predict individual tree crown ratio using Weibull distribution.

        Args:
            tree_rank: Tree's rank in diameter distribution (0-1, where 0=smallest, 1=largest)
            relsdi: Relative stand density index
            ccf: Crown competition factor (default: 100)

        Returns:
            Crown ratio as proportion (0-1)
        """
        # Calculate average crown ratio
        acr = self.calculate_average_crown_ratio(relsdi)

        # Calculate Weibull parameters
        A, B, C = self.calculate_weibull_parameters(acr)

        # Calculate scale factor
        scale = self.calculate_scale_factor(ccf)

        # Bound tree rank to avoid numerical issues
        x = max(0.05, min(0.95, tree_rank))

        try:
            # Calculate crown ratio using Weibull distribution
            # Y = A + B(-ln(1-X))^(1/C)
            crown_ratio = A + B * ((-math.log(1 - x)) ** (1/C))

            # Apply scale factor
            crown_ratio *= scale

            # Convert from percentage to proportion if needed
            if crown_ratio > 1.0:
                crown_ratio = crown_ratio / 100.0

            # Bound between 5% and 95% as specified in FVS
            return max(0.05, min(0.95, crown_ratio))

        except (ValueError, OverflowError):
            # Fallback to simple calculation if Weibull fails
            return max(0.05, min(0.95, acr * scale))

    def predict_dead_tree_crown_ratio(self, dbh: float, random_seed: Optional[int] = None) -> float:
        """Predict crown ratio for dead trees using equations 4.3.1.1 and 4.3.1.2.

        Args:
            dbh: Diameter at breast height (inches)
            random_seed: Optional random seed for reproducibility

        Returns:
            Crown ratio as proportion (0-1)
        """
        if random_seed is not None:
            random.seed(random_seed)

        # Equation 4.3.1.1
        if dbh < 24.0:
            X = 0.70 - 0.40/24.0 * dbh
        else:
            X = 0.30

        # Add random component (standard deviation not specified, using 0.2)
        random_component = random.gauss(0, 0.2)

        # Equation 4.3.1.2: CR = 1 / (1 + exp(X + N(0,SD)))
        crown_ratio = 1.0 / (1.0 + math.exp(X + random_component))

        # Bound to specified range
        return max(0.05, min(0.95, crown_ratio))

    def predict_regeneration_crown_ratio(self, pccf: float, random_seed: Optional[int] = None) -> float:
        """Predict crown ratio for newly established trees during regeneration.

        Args:
            pccf: Crown competition factor on the inventory point where tree is established
            random_seed: Optional random seed for reproducibility

        Returns:
            Crown ratio as proportion (0-1)
        """
        if random_seed is not None:
            random.seed(random_seed)

        # Small random component
        ran = random.gauss(0, 0.05)

        # Equation 4.3.3.1: CR = 0.89722 - 0.0000461 * PCCF + RAN
        crown_ratio = 0.89722 - 0.0000461 * pccf + ran

        # Bound to specified range
        return max(0.2, min(0.9, crown_ratio))

    def update_crown_ratio_change(self, current_cr: float, predicted_cr: float,
                                height_growth: float, cycle_length: int = 5) -> float:
        """Calculate crown ratio change with bounds checking.

        Args:
            current_cr: Current crown ratio (proportion)
            predicted_cr: Predicted crown ratio at end of cycle (proportion)
            height_growth: Height growth during cycle (feet)
            cycle_length: Length of projection cycle (years)

        Returns:
            New crown ratio (proportion)
        """
        # Calculate potential change
        change = predicted_cr - current_cr

        # Check that change doesn't exceed what's possible with height growth
        # Assume all height growth produces new crown
        max_possible_change = height_growth / 100.0  # Rough approximation

        # Bound change to 1% per year for cycle length
        max_annual_change = 0.01
        max_cycle_change = max_annual_change * cycle_length

        # Apply bounds
        bounded_change = max(-max_cycle_change,
                           min(max_cycle_change,
                               min(change, max_possible_change)))

        new_cr = current_cr + bounded_change

        # Final bounds
        return max(0.05, min(0.95, new_cr))


class LSCrownRatioModel:
    """Crown ratio model for the Lake States (LS) variant.

    Uses the TWIGS model from Belcher et al. (1982):
        ACR = 10 * (BCR1/(1 + BCR2*BA) + BCR3*(1 - exp(BCR4*D)))

    where:
        ACR = average crown ratio (0-100 scale)
        BA = stand basal area (sq ft/acre)
        D = tree DBH (inches)
        BCR1-BCR4 = species-specific coefficients

    Subclasses (e.g., NECrownRatioModel) override class attributes to
    load variant-specific coefficient files.
    """

    # Coefficient file path (relative to cfg/), overridden by subclasses
    _COEFFICIENT_FILE = 'ls/ls_crown_ratio_coefficients.json'

    # Fallback TWIGS coefficients for common species
    FALLBACK_COEFFICIENTS = {
        'JP':  {'BCR1': 1.447, 'BCR2': 0.00328, 'BCR3': 5.302, 'BCR4': -0.05726},
        'RN':  {'BCR1': 2.310, 'BCR2': 0.00619, 'BCR3': 4.310, 'BCR4': -0.03059},
        'SM':  {'BCR1': 3.111, 'BCR2': 0.01534, 'BCR3': 6.251, 'BCR4': -0.01552},
        'QA':  {'BCR1': 1.612, 'BCR2': 0.00380, 'BCR3': 4.910, 'BCR4': -0.05120},
        'BF':  {'BCR1': 4.185, 'BCR2': 0.01710, 'BCR3': 6.162, 'BCR4': -0.01875},
    }

    DEFAULT_COEFFICIENTS = {'BCR1': 2.300, 'BCR2': 0.00700, 'BCR3': 5.800, 'BCR4': -0.02800}

    def __init__(self, species_code: str = "RN"):
        """Initialize with species-specific TWIGS coefficients.

        Args:
            species_code: Species code (e.g., "RN", "JP", "SM", etc.)
        """
        self.species_code = species_code
        self.coefficients = {}
        self._load_coefficients()

    def _load_coefficients(self):
        """Load TWIGS coefficients from crown ratio config."""
        try:
            data = load_coefficient_file(self._COEFFICIENT_FILE)
            species_coeffs = data.get('species_coefficients', {})
            if self.species_code in species_coeffs:
                self.coefficients = species_coeffs[self.species_code]
            else:
                self.coefficients = data.get('defaults', {}).get(
                    'hardwood', self.DEFAULT_COEFFICIENTS
                )
        except FileNotFoundError:
            self.coefficients = self.FALLBACK_COEFFICIENTS.get(
                self.species_code, self.DEFAULT_COEFFICIENTS
            )

    def predict_crown_ratio(self, dbh: float, ba: float) -> float:
        """Predict crown ratio using TWIGS model.

        Equation: ACR = 10 * (BCR1/(1 + BCR2*BA) + BCR3*(1 - exp(BCR4*D)))

        Args:
            dbh: Diameter at breast height (inches)
            ba: Stand basal area (sq ft/acre)

        Returns:
            Crown ratio as proportion (0.05 to 0.95)
        """
        bcr1 = self.coefficients['BCR1']
        bcr2 = self.coefficients['BCR2']
        bcr3 = self.coefficients['BCR3']
        bcr4 = self.coefficients['BCR4']

        ba = max(0.0, ba)
        dbh = max(0.1, dbh)

        acr = 10.0 * (bcr1 / (1.0 + bcr2 * ba) + bcr3 * (1.0 - math.exp(bcr4 * dbh)))

        # ACR is in 0-100 scale, convert to proportion
        cr = acr / 100.0

        # Bound to [0.05, 0.95]
        return max(0.05, min(0.95, cr))

    def predict_individual_crown_ratio(self, tree_rank: float, relsdi: float,
                                       ccf: float = 100.0, dbh: float = 5.0,
                                       ba: float = 100.0) -> float:
        """Predict individual tree crown ratio (LS uses TWIGS, not Weibull).

        For interface compatibility with SN variant. LS uses the TWIGS
        equation directly with DBH and BA.

        Args:
            tree_rank: Tree's rank (0-1) - not used in LS TWIGS model
            relsdi: Relative stand density index - not used in LS TWIGS model
            ccf: Crown competition factor - not used in LS TWIGS model
            dbh: Diameter at breast height (inches)
            ba: Stand basal area (sq ft/acre)

        Returns:
            Crown ratio as proportion (0.05 to 0.95)
        """
        return self.predict_crown_ratio(dbh, ba)

    def calculate_average_crown_ratio(self, relsdi: float, ba: float = 100.0,
                                      mean_dbh: float = 8.0) -> float:
        """Calculate average crown ratio for the stand using TWIGS at mean DBH.

        Args:
            relsdi: Relative SDI - not directly used, but kept for interface compatibility
            ba: Stand basal area (sq ft/acre)
            mean_dbh: Mean stand DBH (inches)

        Returns:
            Average crown ratio as proportion (0.05 to 0.95)
        """
        return self.predict_crown_ratio(mean_dbh, ba)

    def update_crown_ratio_change(self, current_cr: float, predicted_cr: float,
                                  height_growth: float, cycle_length: int = 5) -> float:
        """Calculate crown ratio change with bounds checking.

        For LS, uses a simpler approach than SN: move current CR toward
        TWIGS-predicted CR with bounded annual change rate.

        Args:
            current_cr: Current crown ratio (proportion)
            predicted_cr: Predicted crown ratio from TWIGS (proportion)
            height_growth: Height growth during cycle (feet)
            cycle_length: Length of projection cycle (years)

        Returns:
            New crown ratio (proportion)
        """
        change = predicted_cr - current_cr

        # Bound change to 1% per year
        max_cycle_change = 0.01 * cycle_length
        bounded_change = max(-max_cycle_change, min(max_cycle_change, change))

        new_cr = current_cr + bounded_change
        return max(0.05, min(0.95, new_cr))


class NECrownRatioModel(LSCrownRatioModel):
    """Crown ratio model for the Northeast (NE) variant.

    NE uses the TWIGS model (same equation as LS), with NE-specific coefficients.
    Inherits all calculation methods from LSCrownRatioModel; only overrides
    coefficient file path and fallback coefficients.
    """

    _COEFFICIENT_FILE = 'ne/ne_crown_ratio_coefficients.json'

    FALLBACK_COEFFICIENTS = {
        'RM':  {'BCR1': 2.750, 'BCR2': 0.01050, 'BCR3': 6.250, 'BCR4': -0.01950},
        'SM':  {'BCR1': 3.111, 'BCR2': 0.01534, 'BCR3': 6.251, 'BCR4': -0.01552},
        'WP':  {'BCR1': 1.891, 'BCR2': 0.00430, 'BCR3': 5.560, 'BCR4': -0.04500},
        'RO':  {'BCR1': 2.380, 'BCR2': 0.00780, 'BCR3': 5.950, 'BCR4': -0.02450},
        'BF':  {'BCR1': 4.185, 'BCR2': 0.01710, 'BCR3': 6.162, 'BCR4': -0.01875},
        'WO':  {'BCR1': 2.450, 'BCR2': 0.00820, 'BCR3': 6.120, 'BCR4': -0.02150},
        'YB':  {'BCR1': 2.520, 'BCR2': 0.00920, 'BCR3': 5.890, 'BCR4': -0.02210},
    }

    DEFAULT_COEFFICIENTS = {'BCR1': 2.300, 'BCR2': 0.00700, 'BCR3': 5.800, 'BCR4': -0.02800}

    def __init__(self, species_code: str = "RM"):
        """Initialize with NE species-specific TWIGS coefficients.

        Args:
            species_code: Species code (e.g., "RM", "SM", "WP", etc.)
        """
        super().__init__(species_code)


class CSCrownRatioModel(LSCrownRatioModel):
    """Crown ratio model for the Central States (CS) variant.

    CS uses the TWIGS model (same equation as LS/NE), with CS-specific coefficients.
    Inherits all calculation methods from LSCrownRatioModel; only overrides
    coefficient file path and fallback coefficients.
    """

    _COEFFICIENT_FILE = 'cs/cs_crown_ratio_coefficients.json'

    FALLBACK_COEFFICIENTS = {
        'WO':  {'BCR1': 2.450, 'BCR2': 0.00820, 'BCR3': 6.120, 'BCR4': -0.02150},
        'RO':  {'BCR1': 2.380, 'BCR2': 0.00780, 'BCR3': 5.950, 'BCR4': -0.02450},
        'SM':  {'BCR1': 3.111, 'BCR2': 0.01534, 'BCR3': 6.251, 'BCR4': -0.01552},
        'WN':  {'BCR1': 2.200, 'BCR2': 0.00600, 'BCR3': 5.500, 'BCR4': -0.03200},
        'SP':  {'BCR1': 1.800, 'BCR2': 0.00400, 'BCR3': 5.300, 'BCR4': -0.04800},
    }

    DEFAULT_COEFFICIENTS = {'BCR1': 2.300, 'BCR2': 0.00700, 'BCR3': 5.800, 'BCR4': -0.02800}

    def __init__(self, species_code: str = "WO"):
        """Initialize with CS species-specific TWIGS coefficients.

        Args:
            species_code: Species code (e.g., "WO", "RO", "SM", etc.)
        """
        super().__init__(species_code)


class PNCrownRatioModel:
    """Crown ratio model for the Pacific Northwest Coast (PN) variant.

    Uses Weibull distribution with PN-specific coefficients from crown.f:
    - Mean CR: ACR = C0 + C1 * RELSDI * 100 (linear in relative SDI)
    - Weibull location: A = WEIBA[group]
    - Weibull scale: B = WEIBB0 + WEIBB1 * ACR
    - Weibull shape: C = WEIBC0 + WEIBC1 * ACR
    - Crown ratio: CR = A + B * (-ln(1-X))^(1/C), bounded [0.10, 0.95]

    17 species groups mapped from 39 PN species via IMAP array.
    Special Redwood (species 17) uses logistic equation.
    """

    # Species-to-group mapping from IMAP array in crown.f
    _SPECIES_TO_GROUP = {
        'SF': 1, 'WF': 2, 'GF': 2, 'AF': 3, 'RF': 3,
        'SS': 16, 'NF': 4, 'YC': 15, 'IC': 11, 'ES': 11,
        'LP': 16, 'JP': 6, 'SP': 5, 'WP': 5, 'PP': 6,
        'DF': 7, 'RW': 11, 'RC': 8, 'WH': 9, 'MH': 10,
        'BM': 12, 'RA': 13, 'WA': 14, 'PB': 14, 'GC': 14,
        'AS': 14, 'CW': 14, 'WO': 14, 'WJ': 14, 'LL': 11,
        'WB': 11, 'KP': 11, 'PY': 14, 'DG': 14, 'HT': 14,
        'CH': 14, 'WI': 14, 'OT': 14,
    }

    # Fallback mean CR coefficients (C0, C1) by group
    _FALLBACK_MEAN_CR = {
        1:  (5.073, -0.01143),
        2:  (5.212, -0.01162),
        3:  (4.860, -0.00617),
        4:  (5.569, -0.02129),
        5:  (4.280, -0.00248),
        6:  (5.073, -0.02099),
        7:  (5.191, -0.00827),
        8:  (5.330, -0.01408),
        9:  (4.522, -0.00628),
        10: (5.330, -0.01408),
        11: (5.138, -0.01128),
        12: (3.802, -0.00393),
        13: (6.193, -0.01792),
        14: (5.175, -0.01128),
        15: (5.330, -0.01408),
        16: (4.556, -0.00898),
        17: (0, 0),
    }

    # Fallback Weibull parameters (WEIBA, WEIBB0, WEIBB1, WEIBC0, WEIBC1) by group
    _FALLBACK_WEIBULL = {
        1:  (0, -0.17168, 1.16155, 2.82630, 0),
        2:  (0,  0.13094, 1.09341, 1.35514, 0.35047),
        3:  (1, -0.98111, 1.09227, 1.32605, 0.31839),
        4:  (0, -0.13581, 1.14771, 3.01749, 0),
        5:  (0,  0.01995, 1.10874, 2.62123, 0.18673),
        6:  (0, -0.03670, 1.13279, 2.87609, 0),
        7:  (0,  0.04023, 1.10040, 2.57407, 0),
        8:  (0,  0.13424, 1.08508, 1.49476, 0.37279),
        9:  (0,  0.14291, 1.10098, 2.64033, 0.12893),
        10: (0,  0.13424, 1.08508, 1.49476, 0.37279),
        11: (0, -0.14891, 1.14484, 2.67756, 0),
        12: (0,  0.13424, 1.08508, 1.49476, 0.37279),
        13: (0, -0.17168, 1.16155, 2.82630, 0),
        14: (0,  0.12139, 1.06988, 3.47174, -0.11500),
        15: (0,  0.13424, 1.08508, 1.49476, 0.37279),
        16: (0,  0.14291, 1.10098, 2.64033, 0.12893),
        17: (0, 0, 0, 0, 0),
    }

    # Redwood logistic equation coefficients
    _REDWOOD_LOGISTIC = {
        'a0': -1.021064,
        'a1': 0.309296,
        'a2': 0.869720,
        'a3': -0.116274,
    }

    DEFAULT_GROUP = 14  # Misc hardwoods

    def __init__(self, species_code: str = "DF"):
        """Initialize with species-specific crown ratio parameters.

        Args:
            species_code: Species code (e.g., "DF", "WH", "RC", etc.)
        """
        self.species_code = species_code
        self._group = None
        self._mean_cr_c0 = None
        self._mean_cr_c1 = None
        self._weiba = None
        self._weibb0 = None
        self._weibb1 = None
        self._weibc0 = None
        self._weibc1 = None
        self._load_parameters()

    def _load_parameters(self):
        """Load crown ratio parameters from PN coefficient file."""
        species_to_group = self._SPECIES_TO_GROUP
        mean_cr_groups = self._FALLBACK_MEAN_CR
        weibull_groups = self._FALLBACK_WEIBULL

        try:
            data = load_coefficient_file('pn/pn_crown_ratio_coefficients.json')
            species_to_group = data.get('species_to_group', species_to_group)

            # Load mean CR coefficients
            mcr_data = data.get('mean_cr_coefficients', {}).get('groups', {})
            if mcr_data:
                mean_cr_groups = {}
                for k, v in mcr_data.items():
                    mean_cr_groups[int(k)] = (v['C0'], v['C1'])

            # Load Weibull parameters
            weib_data = data.get('weibull_parameters', {}).get('groups', {})
            if weib_data:
                weibull_groups = {}
                for k, v in weib_data.items():
                    weibull_groups[int(k)] = (
                        v['WEIBA'], v['WEIBB0'], v['WEIBB1'],
                        v['WEIBC0'], v['WEIBC1']
                    )
        except FileNotFoundError:
            pass

        # Look up this species' group
        self._group = species_to_group.get(self.species_code, self.DEFAULT_GROUP)

        # Load mean CR coefficients for the group
        c0, c1 = mean_cr_groups.get(self._group, mean_cr_groups[self.DEFAULT_GROUP])
        self._mean_cr_c0 = c0
        self._mean_cr_c1 = c1

        # Load Weibull parameters for the group
        weib = weibull_groups.get(self._group, weibull_groups[self.DEFAULT_GROUP])
        self._weiba = weib[0]
        self._weibb0 = weib[1]
        self._weibb1 = weib[2]
        self._weibc0 = weib[3]
        self._weibc1 = weib[4]

    def calculate_average_crown_ratio(self, relsdi: float) -> float:
        """Calculate average crown ratio using PN linear equation.

        Fortran crown.f: RELSDI = SDI/SDIMAX (0-1.5 scale), capped at 1.5.
        ACRNEW = C0 + C1 * RELSDI * 100 (C1 operates on 0-150 scale).

        PyFVS passes relsdi on 1-12 scale (SDI/SDIMAX * 10), so we convert
        back to Fortran's 0-1.5 scale before applying C1.

        Args:
            relsdi: Relative stand density index (1.0-12.0 scale from StandMetrics)

        Returns:
            Average crown ratio as proportion (0.05-0.95)
        """
        # Convert from PyFVS 1-12 scale back to Fortran 0-1.5 scale
        relsdi_fortran = relsdi / 10.0
        relsdi_fortran = max(0.0, min(1.5, relsdi_fortran))

        # PN/WC crown.f: ACRNEW = C0 + C1 * RELSDI * 100 (Fortran scale)
        acr = self._mean_cr_c0 + self._mean_cr_c1 * relsdi_fortran * 100.0

        # ACR is on 0-10 scale in PN, convert to proportion
        acr_proportion = acr / 10.0

        return max(0.05, min(0.95, acr_proportion))

    def predict_individual_crown_ratio(self, tree_rank: float, relsdi: float,
                                       ccf: float = 100.0, dbh: float = 5.0,
                                       ba: float = 100.0, height: float = 50.0,
                                       qmd: float = 8.0) -> float:
        """Predict individual tree crown ratio using PN Weibull distribution.

        Args:
            tree_rank: Tree's rank in diameter distribution (0-1)
            relsdi: Relative stand density index (1.0-12.0)
            ccf: Crown competition factor (not used in PN)
            dbh: Diameter at breast height (inches)
            ba: Stand basal area (sq ft/acre)
            height: Tree height (feet)
            qmd: Stand QMD (inches)

        Returns:
            Crown ratio as proportion (0.10-0.95)
        """
        # Calculate average crown ratio
        acr = self.calculate_average_crown_ratio(relsdi)

        # ACR as a 0-10 value for Weibull parameter calculation
        acr_ten = acr * 10.0

        # Calculate Weibull parameters
        weib_a = self._weiba
        weib_b = self._weibb0 + self._weibb1 * acr_ten
        weib_c = self._weibc0 + self._weibc1 * acr_ten

        # Fortran crown.f: IF(B .LT. 3.0) B=3.0; IF(C .LT. 2.0) C=2.0
        weib_b = max(3.0, weib_b)
        weib_c = max(2.0, weib_c)

        # Bound tree rank to avoid numerical issues
        x = max(0.05, min(0.95, tree_rank))

        try:
            # Weibull: CR = A + B * (-ln(1-X))^(1/C)
            cr = weib_a + weib_b * ((-math.log(1 - x)) ** (1.0 / weib_c))

            # CR is on 0-10 scale, convert to proportion
            cr = cr / 10.0

        except (ValueError, OverflowError, ZeroDivisionError):
            cr = acr

        # Bound to [0.10, 0.95] per PN specification
        return max(0.10, min(0.95, cr))

    def predict_redwood_crown_ratio(self, dbh: float, height: float,
                                     qmd: float, relative_density: float) -> float:
        """Predict crown ratio for Redwood using logistic equation.

        Equation: X = a0 + a1*ln(HDR) + a2*PRD + a3*(D/QMDPLT)
                  CR = 1/(1+exp(X))

        Args:
            dbh: Diameter at breast height (inches)
            height: Tree total height (feet)
            qmd: Plot-level QMD (inches)
            relative_density: Predicted relative density (0-1)

        Returns:
            Crown ratio as proportion (0.10-0.95)
        """
        if dbh <= 0 or height <= 0:
            return 0.50

        hdr = height / dbh
        d_over_qmd = dbh / qmd if qmd > 0 else 1.0

        coeffs = self._REDWOOD_LOGISTIC
        x = (coeffs['a0']
             + coeffs['a1'] * math.log(max(1.0, hdr))
             + coeffs['a2'] * relative_density
             + coeffs['a3'] * d_over_qmd)

        cr = 1.0 / (1.0 + math.exp(x))

        return max(0.10, min(0.95, cr))

    def update_crown_ratio_change(self, current_cr: float, predicted_cr: float,
                                  height_growth: float, cycle_length: int = 5) -> float:
        """Calculate crown ratio change with bounds checking.

        Args:
            current_cr: Current crown ratio (proportion)
            predicted_cr: Predicted crown ratio (proportion)
            height_growth: Height growth during cycle (feet)
            cycle_length: Length of projection cycle (years)

        Returns:
            New crown ratio (proportion)
        """
        change = predicted_cr - current_cr

        # Bound change to 1% per year
        max_cycle_change = 0.01 * cycle_length
        bounded_change = max(-max_cycle_change, min(max_cycle_change, change))

        new_cr = current_cr + bounded_change
        return max(0.10, min(0.95, new_cr))


def create_crown_ratio_model(species_code: str = "LP", variant: Optional[str] = None):
    """Factory function to create a crown ratio model for a species and variant.

    Args:
        species_code: Species code (e.g., "LP", "SP", "RN", etc.)
        variant: FVS variant code (e.g., 'SN', 'LS'). If None, uses default.

    Returns:
        CrownRatioModel or LSCrownRatioModel instance
    """
    if variant is None:
        variant = get_default_variant()

    if variant == 'LS':
        return LSCrownRatioModel(species_code)
    elif variant == 'NE':
        return NECrownRatioModel(species_code)
    elif variant == 'CS':
        return CSCrownRatioModel(species_code)
    elif variant in ('PN', 'WC', 'OP'):
        return PNCrownRatioModel(species_code)
    else:
        return CrownRatioModel(species_code)


def calculate_average_crown_ratio(species_code: str, relsdi: float,
                                  variant: Optional[str] = None) -> float:
    """Standalone function to calculate average crown ratio.

    Args:
        species_code: Species code
        relsdi: Relative stand density index
        variant: FVS variant code

    Returns:
        Average crown ratio as proportion
    """
    model = create_crown_ratio_model(species_code, variant=variant)
    return model.calculate_average_crown_ratio(relsdi)


def predict_tree_crown_ratio(species_code: str, tree_rank: float, relsdi: float,
                           ccf: float = 100.0, variant: Optional[str] = None) -> float:
    """Standalone function to predict individual tree crown ratio.

    Args:
        species_code: Species code
        tree_rank: Tree's rank in diameter distribution (0-1)
        relsdi: Relative stand density index
        ccf: Crown competition factor
        variant: FVS variant code

    Returns:
        Crown ratio as proportion
    """
    model = create_crown_ratio_model(species_code, variant=variant)
    return model.predict_individual_crown_ratio(tree_rank, relsdi, ccf)


def compare_crown_ratio_models(species_codes: list, relsdi_range: list) -> Dict[str, Any]:
    """Compare crown ratio predictions across species and density levels.

    Args:
        species_codes: List of species codes to compare
        relsdi_range: List of RELSDI values to evaluate

    Returns:
        Dictionary with comparison results
    """
    results = {
        'relsdi': relsdi_range,
        'species_results': {}
    }

    for species in species_codes:
        model = create_crown_ratio_model(species)

        acr_values = []
        individual_cr_values = []

        for relsdi in relsdi_range:
            acr = model.calculate_average_crown_ratio(relsdi)
            acr_values.append(acr)

            # Calculate individual tree CR for median tree (rank = 0.5)
            individual_cr = model.predict_individual_crown_ratio(0.5, relsdi)
            individual_cr_values.append(individual_cr)

        results['species_results'][species] = {
            'average_crown_ratio': acr_values,
            'individual_crown_ratio': individual_cr_values,
            'equation_type': model.coefficients.get('acr_equation', 'TWIGS')
        }

    return results

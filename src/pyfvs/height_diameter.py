"""
Height-diameter relationship functions for FVS-Python.
Implements Curtis-Arney and Wykoff models for predicting tree height from diameter.
"""
import math
from typing import Dict, Any

from .model_base import ParameterizedModel

__all__ = [
    'HeightDiameterModel',
    'create_height_diameter_model',
    'curtis_arney_height',
    'wykoff_height',
    'compare_models',
]


class HeightDiameterModel(ParameterizedModel):
    """Height-diameter model implementing Curtis-Arney and Wykoff equations.

    Uses the base class pattern for loading species-specific coefficients
    from variant-specific coefficient files with fallback support.

    Supported variants:
        - SN: sn_height_diameter_coefficients.json
        - LS: ls/ls_height_diameter_coefficients.json

    The JSON file stores coefficients in a flat structure per species:
        {"LP": {"P2": ..., "P3": ..., "P4": ..., "Dbw": ..., "Wykoff_B1": ..., "Wykoff_B2": ...}, ...}

    This class restructures them into the nested format expected by calculation methods:
        {"curtis_arney": {"p2": ..., "p3": ..., "p4": ..., "dbw": ...}, "wykoff": {"b1": ..., "b2": ...}}
    """

    # Variant-specific coefficient file mapping
    VARIANT_COEFFICIENT_FILES = {
        'SN': 'sn_height_diameter_coefficients.json',
        'LS': 'ls/ls_height_diameter_coefficients.json',
        'PN': 'pn/pn_height_diameter_coefficients.json',
        'WC': 'wc/wc_height_diameter_coefficients.json',
        'NE': 'ne/ne_height_diameter_coefficients.json',
        'CS': 'cs/cs_height_diameter_coefficients.json',
        'CA': 'ca/ca_height_diameter_coefficients.json',
        'OP': 'op/op_height_diameter_coefficients.json',
        'OC': 'oc/oc_height_diameter_coefficients.json',
        'WS': 'ws/ws_height_diameter_coefficients.json',
    }

    # Class attributes for ParameterizedModel base class
    COEFFICIENT_FILE = 'sn_height_diameter_coefficients.json'  # Default for SN
    COEFFICIENT_KEY = None  # Special case: species are top-level keys, not nested
    FALLBACK_PARAMETERS = {
        'LP': {
            'P2': 243.860648, 'P3': 4.28460566, 'P4': -0.47130185, 'Dbw': 0.5,
            'Wykoff_B1': 4.6897, 'Wykoff_B2': -6.8801
        },
        'SP': {
            'P2': 444.0921666, 'P3': 4.11876312, 'P4': -0.30617043, 'Dbw': 0.5,
            'Wykoff_B1': 4.6271, 'Wykoff_B2': -6.4095
        },
        'SA': {
            'P2': 1087.101439, 'P3': 5.10450596, 'P4': -0.24284896, 'Dbw': 0.5,
            'Wykoff_B1': 4.6561, 'Wykoff_B2': -6.2258
        },
        'LL': {
            'P2': 98.56082813, 'P3': 3.89930709, 'P4': -0.86730393, 'Dbw': 0.5,
            'Wykoff_B1': 4.5991, 'Wykoff_B2': -5.9111
        },
        # LS variant fallbacks
        'JP': {  # Jack Pine
            'P2': 266.456, 'P3': 3.993, 'P4': -0.386, 'Dbw': 0.1,
            'Wykoff_B1': 4.5, 'Wykoff_B2': -6.5
        },
        'RN': {  # Red Pine
            'P2': 311.165, 'P3': 3.832, 'P4': -0.357, 'Dbw': 0.1,
            'Wykoff_B1': 4.6, 'Wykoff_B2': -6.6
        },
        # PN variant fallbacks
        'DF': {  # Douglas-fir
            'P2': 1091.85, 'P3': 5.29, 'P4': -0.26, 'Dbw': 0.1,
            'Wykoff_B1': 4.7, 'Wykoff_B2': -6.8
        },
        'WH': {  # Western Hemlock
            'P2': 609.42, 'P3': 5.59, 'P4': -0.38, 'Dbw': 0.1,
            'Wykoff_B1': 4.6, 'Wykoff_B2': -6.5
        },
        'RC': {  # Western Red Cedar
            'P2': 665.09, 'P3': 5.50, 'P4': -0.32, 'Dbw': 0.1,
            'Wykoff_B1': 4.5, 'Wykoff_B2': -6.3
        },
        'SS': {  # Sitka Spruce
            'P2': 3844.39, 'P3': 7.07, 'P4': -0.21, 'Dbw': 0.1,
            'Wykoff_B1': 4.8, 'Wykoff_B2': -6.9
        },
    }
    DEFAULT_SPECIES = "LP"

    def __init__(self, species_code: str = "LP", variant: str = None):
        """Initialize with species-specific parameters.

        Args:
            species_code: Species code (e.g., "LP", "SP", "SA", "JP", "RN", etc.)
            variant: FVS variant code (e.g., "SN", "LS"). If None, uses current default.
        """
        # Set variant before calling parent init (which calls _load_parameters)
        from .config_loader import get_default_variant
        self.variant = (variant or get_default_variant()).upper()

        # Set the coefficient file based on variant
        self.COEFFICIENT_FILE = self.VARIANT_COEFFICIENT_FILES.get(
            self.variant, self.VARIANT_COEFFICIENT_FILES['SN']
        )

        super().__init__(species_code)

    def _load_parameters(self) -> None:
        """Load height-diameter parameters from cached configuration.

        Overrides base class to handle the flat coefficient structure in the JSON
        file and restructure into nested format for calculation methods.
        """
        self.raw_data = self._get_coefficient_data()

        # The height-diameter JSON has species at the top level (no nested key)
        if self.raw_data:
            if self.species_code in self.raw_data:
                flat_coeffs = self.raw_data[self.species_code]
            elif self.DEFAULT_SPECIES in self.raw_data:
                flat_coeffs = self.raw_data[self.DEFAULT_SPECIES]
            else:
                self._load_fallback_parameters()
                return
        else:
            self._load_fallback_parameters()
            return

        # Store raw flat coefficients
        self.coefficients = flat_coeffs

        # Restructure into nested format expected by calculation methods
        self.hd_params = self._restructure_coefficients(flat_coeffs)

    def _load_fallback_parameters(self) -> None:
        """Load fallback parameters when coefficient file is not available."""
        if self.species_code in self.FALLBACK_PARAMETERS:
            flat_coeffs = self.FALLBACK_PARAMETERS[self.species_code].copy()
        elif self.DEFAULT_SPECIES in self.FALLBACK_PARAMETERS:
            flat_coeffs = self.FALLBACK_PARAMETERS[self.DEFAULT_SPECIES].copy()
        else:
            flat_coeffs = {}

        self.coefficients = flat_coeffs
        self.hd_params = self._restructure_coefficients(flat_coeffs)

    def _restructure_coefficients(self, flat_coeffs: Dict[str, Any]) -> Dict[str, Any]:
        """Restructure flat coefficients into nested format for calculation methods.

        Args:
            flat_coeffs: Flat dictionary with P2, P3, P4, Dbw, Wykoff_B1, Wykoff_B2

        Returns:
            Nested dictionary with 'curtis_arney' and 'wykoff' sub-dicts
        """
        return {
            'model': 'curtis_arney',  # Default model
            'curtis_arney': {
                'p2': flat_coeffs.get('P2', 243.860648),
                'p3': flat_coeffs.get('P3', 4.28460566),
                'p4': flat_coeffs.get('P4', -0.47130185),
                'dbw': flat_coeffs.get('Dbw', 0.5),
            },
            'wykoff': {
                'b1': flat_coeffs.get('Wykoff_B1', 4.6897),
                'b2': flat_coeffs.get('Wykoff_B2', -6.8801),
            }
        }

    def predict_height(self, dbh: float, model: str = None) -> float:
        """Predict height from diameter.

        Args:
            dbh: Diameter at breast height (inches)
            model: Model to use ('curtis_arney' or 'wykoff'). If None, uses default.

        Returns:
            Predicted height (feet)
        """
        if model is None:
            model = self.hd_params.get('model', 'curtis_arney')

        if model == 'curtis_arney':
            return self.curtis_arney_height(dbh)
        elif model == 'wykoff':
            return self.wykoff_height(dbh)
        else:
            raise ValueError(f"Unknown height-diameter model: {model}")

    def curtis_arney_height(self, dbh: float) -> float:
        """Calculate height using Curtis-Arney equation.

        The Curtis-Arney equation is:
        Height = 4.5 + P2 * exp(-P3 * DBH^P4)

        For small trees (DBH < 3.0), uses linear interpolation.

        Args:
            dbh: Diameter at breast height (inches)

        Returns:
            Predicted height (feet)
        """
        params = self.hd_params['curtis_arney']
        p2 = params['p2']
        p3 = params['p3']
        p4 = params['p4']
        dbw = params['dbw']  # Diameter breakpoint for small trees

        if dbh <= dbw:
            return 4.51
        elif dbh < 3.0:
            # Linear interpolation for small trees (Fortran htdbh.f)
            # H = ((H3 - 4.51) * (D - DB) / (3 - DB)) + 4.51
            h3 = 4.5 + p2 * math.exp(-p3 * 3.0**p4)
            return ((h3 - 4.51) * (dbh - dbw) / (3.0 - dbw)) + 4.51
        else:
            # Standard Curtis-Arney equation for larger trees
            return 4.5 + p2 * math.exp(-p3 * dbh**p4)

    def wykoff_height(self, dbh: float) -> float:
        """Calculate height using Wykoff equation.

        The Wykoff equation is:
        Height = 4.5 + exp(B1 + B2 / (DBH + 1))

        Args:
            dbh: Diameter at breast height (inches)

        Returns:
            Predicted height (feet)
        """
        params = self.hd_params['wykoff']
        b1 = params['b1']
        b2 = params['b2']

        if dbh <= 0:
            return 4.5

        return 4.5 + math.exp(b1 + b2 / (dbh + 1))

    def solve_dbh_from_height(self, target_height: float, model: str = None,
                             initial_dbh: float = 1.0, tolerance: float = 0.01,
                             max_iterations: int = 20) -> float:
        """Solve for DBH given a target height using analytical inversion.

        Uses the closed-form inverse of the Curtis-Arney H-D model,
        matching the Fortran FVS HTDBH subroutine (MODE=1):
        - For H >= HAT3: D = exp(log((log(H-4.5) - log(P2)) / (-P3)) / P4)
        - For H < HAT3: Linear interpolation from budwidth to 3.0"

        Args:
            target_height: Target height (feet)
            model: Model to use (ignored, always uses curtis_arney inverse).
            initial_dbh: Initial guess (unused, kept for API compatibility).
            tolerance: Convergence tolerance (unused, analytical solution).
            max_iterations: Max iterations (unused, analytical solution).

        Returns:
            Estimated DBH (inches)
        """
        params = self.hd_params['curtis_arney']
        p2 = params['p2']
        p3 = params['p3']
        p4 = params['p4']
        db = params['dbw']  # Budwidth (SNDBAL in Fortran)

        if target_height <= 4.5:
            return db

        # Height at 3" DBH (transition point between linear and exponential)
        hat3 = 4.5 + p2 * math.exp(-p3 * 3.0**p4)

        if target_height >= hat3:
            # Analytical inversion of Curtis-Arney for D >= 3"
            # H = 4.5 + P2 * exp(-P3 * D^P4)
            # => D = exp(log((log(H-4.5) - log(P2)) / (-P3)) / P4)
            h_above_bh = target_height - 4.5
            if h_above_bh >= p2:
                # Tree exceeds asymptotic height — return large DBH
                return 30.0
            ratio = (math.log(h_above_bh) - math.log(p2)) / (-p3)
            if ratio <= 0:
                return 30.0
            return math.exp(math.log(ratio) / p4)
        else:
            # Linear interpolation for D < 3" (Fortran: regent.f small-tree region)
            # D = ((H - 4.51) * (3 - DB)) / (HAT3 - 4.51) + DB
            denom = hat3 - 4.51
            if denom <= 0:
                return db
            return ((target_height - 4.51) * (3.0 - db)) / denom + db

    def get_model_parameters(self, model: str = None) -> Dict[str, Any]:
        """Get parameters for a specific model.

        Args:
            model: Model name ('curtis_arney' or 'wykoff'). If None, returns all.

        Returns:
            Dictionary of model parameters
        """
        if model is None:
            return self.hd_params
        elif model in self.hd_params:
            return self.hd_params[model]
        else:
            raise ValueError(f"Unknown model: {model}")


def create_height_diameter_model(species_code: str = "LP", variant: str = None) -> HeightDiameterModel:
    """Factory function to create a height-diameter model for a species.

    Args:
        species_code: Species code (e.g., "LP", "SP", "SA", "JP", "RN", etc.)
        variant: FVS variant code (e.g., "SN", "LS"). If None, uses current default.

    Returns:
        HeightDiameterModel instance
    """
    return HeightDiameterModel(species_code, variant=variant)


def curtis_arney_height(dbh: float, p2: float, p3: float, p4: float, dbw: float = 0.1) -> float:
    """Standalone Curtis-Arney height function.

    Args:
        dbh: Diameter at breast height (inches)
        p2: Curtis-Arney parameter P2
        p3: Curtis-Arney parameter P3
        p4: Curtis-Arney parameter P4
        dbw: Diameter breakpoint for small trees (inches)

    Returns:
        Predicted height (feet)
    """
    if dbh <= dbw:
        return 4.5
    elif dbh < 3.0:
        # Linear interpolation for small trees
        h3 = 4.5 + p2 * math.exp(-p3 * 3.0**p4)
        return 4.5 + (h3 - 4.5) * (dbh - dbw) / (3.0 - dbw)
    else:
        # Standard Curtis-Arney equation
        return 4.5 + p2 * math.exp(-p3 * dbh**p4)


def wykoff_height(dbh: float, b1: float, b2: float) -> float:
    """Standalone Wykoff height function.

    Args:
        dbh: Diameter at breast height (inches)
        b1: Wykoff parameter B1
        b2: Wykoff parameter B2

    Returns:
        Predicted height (feet)
    """
    if dbh <= 0:
        return 4.5

    return 4.5 + math.exp(b1 + b2 / (dbh + 1))


def compare_models(dbh_range: list, species_code: str = "LP") -> Dict[str, list]:
    """Compare Curtis-Arney and Wykoff models over a range of DBH values.

    Args:
        dbh_range: List of DBH values to evaluate (inches)
        species_code: Species code for parameter lookup

    Returns:
        Dictionary with DBH values and predicted heights for each model
    """
    model = create_height_diameter_model(species_code)

    results = {
        'dbh': dbh_range,
        'curtis_arney': [],
        'wykoff': []
    }

    for dbh in dbh_range:
        results['curtis_arney'].append(model.curtis_arney_height(dbh))
        results['wykoff'].append(model.wykoff_height(dbh))

    return results

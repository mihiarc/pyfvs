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
    'wykoff_inverse_dbh',
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

        Supports two JSON layouts:
        - Top-level species keys: {"LP": {...}, "SP": {...}} (SN, WC, OP)
        - Nested under "coefficients": {"coefficients": {"LP": {...}}} (NE, CS, LS, PN)
        """
        self.raw_data = self._get_coefficient_data()

        if self.raw_data:
            # Extract species dict: check for "coefficients" wrapper first,
            # then fall back to top-level species keys
            species_dict = self.raw_data.get('coefficients', self.raw_data)

            if self.species_code in species_dict:
                flat_coeffs = species_dict[self.species_code]
            elif self.DEFAULT_SPECIES in species_dict:
                flat_coeffs = species_dict[self.DEFAULT_SPECIES]
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

        Handles both uppercase keys (P2, P3, P4, Dbw) from NE/SN files and
        lowercase keys (p2, p3, p4, dbw) from CS/LS/PN files.

        Args:
            flat_coeffs: Flat dictionary with P2/p2, P3/p3, P4/p4, Dbw/dbw keys

        Returns:
            Nested dictionary with 'curtis_arney' and 'wykoff' sub-dicts
        """
        # Support both uppercase (NE/SN) and lowercase (CS/LS/PN) key conventions
        def _get(key_upper, key_lower, default):
            return flat_coeffs.get(key_upper, flat_coeffs.get(key_lower, default))

        # IWYKCA flag (LS htdbh.f:290): 0 = use Wykoff, 1 = use Curtis-Arney.
        # Only LS JSON populates this per-species per Fortran blkdat.f/htdbh.f.
        # Other variants omit it; default None preserves Curtis-Arney behavior.
        iwykca = flat_coeffs.get('IWYKCA', None)
        return {
            'model': 'curtis_arney',  # Default model
            'iwykca': iwykca,
            'curtis_arney': {
                'p2': _get('P2', 'p2', 243.860648),
                'p3': _get('P3', 'p3', 4.28460566),
                'p4': _get('P4', 'p4', -0.47130185),
                'dbw': _get('Dbw', 'dbw', 0.5),
                # Dbreak = linear/exponential breakpoint diameter. SN/LS/etc.
                # hardcode 3.0 in Fortran htdbh.f (SN) and derivatives; OC/CA
                # variants use a per-species SPLINE value (2, 3, 5, or 6) from
                # FVSoc htdbh.f. Default 3.0 preserves non-OC behavior.
                'dbreak': _get('Dbreak', 'dbreak', 3.0),
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

        For small trees (DBH < Dbreak), uses linear interpolation from
        (Dbw, 4.51) to (Dbreak, H(Dbreak)). For most variants Dbreak=3.0
        (matching SN htdbh.f); OC uses per-species SPLINE values.

        Args:
            dbh: Diameter at breast height (inches)

        Returns:
            Predicted height (feet)
        """
        params = self.hd_params['curtis_arney']
        p2 = params['p2']
        p3 = params['p3']
        p4 = params['p4']
        dbw = params['dbw']          # Lower bound for small-tree linear interp
        dbreak = params['dbreak']    # Upper bound of small-tree linear interp

        if dbh <= dbw:
            return 4.51
        elif dbh < dbreak:
            # Linear interpolation for small trees (Fortran htdbh.f)
            # H = ((H(Dbreak) - 4.51) * (D - DB) / (Dbreak - DB)) + 4.51
            h_at_break = 4.5 + p2 * math.exp(-p3 * dbreak**p4)
            return ((h_at_break - 4.51) * (dbh - dbw) / (dbreak - dbw)) + 4.51
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
        - For H >= H(Dbreak): D = exp(log((log(H-4.5) - log(P2)) / (-P3)) / P4)
        - For H <  H(Dbreak): Linear interpolation from Dbw to Dbreak

        Dbreak is 3.0" for SN/LS/NE/etc. (hardcoded in SN htdbh.f) and a
        per-species SPLINE value for OC (2, 3, 5, or 6 from OC htdbh.f).

        For LS species, Fortran htdbh.f dispatches on the IWYKCA flag:
        IWYKCA=0 uses the Wykoff inverse `D = B2/(ln(H-4.5)-B1) - 1` with
        blkdat.f HT1/HT2 coefficients. When this model carries IWYKCA=0
        in hd_params, we use the Wykoff inverse to match Fortran behavior.

        Args:
            target_height: Target height (feet)
            model: Model to use (ignored, always uses curtis_arney inverse).
            initial_dbh: Initial guess (unused, kept for API compatibility).
            tolerance: Convergence tolerance (unused, analytical solution).
            max_iterations: Max iterations (unused, analytical solution).

        Returns:
            Estimated DBH (inches)
        """
        # Fortran LS htdbh.f:319-340 dispatch: IWYKCA=0 => Wykoff, 1 => CA.
        if self.hd_params.get('iwykca') == 0:
            dbw = self.hd_params['curtis_arney']['dbw']
            d = self.wykoff_inverse_dbh(target_height, dbh_min=dbw)
            # Fortran line 343: IF(MODE.NE.0 .AND. D.LT.DB) D=DB
            return max(d, dbw)
        params = self.hd_params['curtis_arney']
        p2 = params['p2']
        p3 = params['p3']
        p4 = params['p4']
        db = params['dbw']           # Lower bound for linear interp (SNDBAL in SN)
        dbreak = params['dbreak']    # Upper bound of linear interp

        if target_height <= 4.5:
            return db

        # Height at the Dbreak diameter (transition between linear and exponential)
        h_at_break = 4.5 + p2 * math.exp(-p3 * dbreak**p4)

        if target_height >= h_at_break:
            # Analytical inversion of Curtis-Arney for D >= Dbreak
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
            # Linear interpolation for D < Dbreak (Fortran: htdbh.f)
            # D = ((H - 4.51) * (Dbreak - DB)) / (H(Dbreak) - 4.51) + DB
            denom = h_at_break - 4.51
            if denom <= 0:
                return db
            return ((target_height - 4.51) * (dbreak - db)) / denom + db

    def wykoff_inverse_dbh(self, height: float, dbh_min: float = 0.1) -> float:
        """Solve for DBH given a target height using the analytical Wykoff inverse.

        Uses this model's species-specific Wykoff B1/B2 coefficients
        (the Wykoff_B1/Wykoff_B2 fields from the coefficient JSON).
        See the standalone wykoff_inverse_dbh function for the formula
        and the OC Fortran reference.

        Args:
            height: Target height (feet).
            dbh_min: Floor DBH returned at or below 4.5 ft. Defaults to 0.1.

        Returns:
            Estimated DBH (inches).
        """
        params = self.hd_params['wykoff']
        return wykoff_inverse_dbh(
            height, b1=params['b1'], b2=params['b2'], dbh_min=dbh_min
        )

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


_height_diameter_model_cache: dict[tuple[str, str], HeightDiameterModel] = {}


def create_height_diameter_model(species_code: str = "LP", variant: str = None) -> HeightDiameterModel:
    """Factory function to create a height-diameter model for a species.

    Caches model instances by (species, variant) to avoid repeatedly loading
    coefficient files from disk. This is critical for performance in
    Stand.initialize_planted() which calls this once per tree.

    Args:
        species_code: Species code (e.g., "LP", "SP", "SA", "JP", "RN", etc.)
        variant: FVS variant code (e.g., "SN", "LS"). If None, uses current default.

    Returns:
        HeightDiameterModel instance (may be shared across calls)
    """
    from .config_loader import get_default_variant
    resolved_variant = (variant or get_default_variant()).upper()
    cache_key = (species_code.upper(), resolved_variant)

    if cache_key not in _height_diameter_model_cache:
        _height_diameter_model_cache[cache_key] = HeightDiameterModel(
            species_code, variant=variant
        )
    return _height_diameter_model_cache[cache_key]


def curtis_arney_height(dbh: float, p2: float, p3: float, p4: float,
                        dbw: float = 0.1, dbreak: float = 3.0) -> float:
    """Standalone Curtis-Arney height function.

    Args:
        dbh: Diameter at breast height (inches)
        p2: Curtis-Arney parameter P2
        p3: Curtis-Arney parameter P3
        p4: Curtis-Arney parameter P4
        dbw: Lower bound for the small-tree linear interpolation (inches)
        dbreak: Breakpoint between linear interp and the exponential form
                (inches). Default 3.0 matches SN htdbh.f; OC variants use
                per-species SPLINE values.

    Returns:
        Predicted height (feet)
    """
    if dbh <= dbw:
        return 4.5
    elif dbh < dbreak:
        # Linear interpolation for small trees
        h_at_break = 4.5 + p2 * math.exp(-p3 * dbreak**p4)
        return 4.5 + (h_at_break - 4.5) * (dbh - dbw) / (dbreak - dbw)
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


def wykoff_inverse_dbh(height: float, b1: float, b2: float,
                       dbh_min: float = 0.1) -> float:
    """Solve for DBH given a target height using the analytical Wykoff inverse.

    The Wykoff height equation is:
        H = 4.5 + exp(b1 + b2 / (D + 1))

    Inverting algebraically for DBH:
        D = b2 / (ln(H - 4.5) - b1) - 1

    This matches the OC variant's small-tree DBH derivation in
    ``oc/regent.f`` lines 296,300, where HT1/HT2 (the Wykoff B1/B2
    coefficients from ``oc/blkdat.f``) are used to convert a small tree's
    height back to a DBH for use in the small-tree growth path. NOTE:
    OC's HT1/HT2 are *different values* from the Curtis-Arney CURARN
    coefficients in ``oc/htdbh.f`` — the small-tree path uses Wykoff,
    while the standard initialization path uses Curtis-Arney.

    Args:
        height: Target height (feet). Must be > 4.5 for the inverse to
            apply; otherwise dbh_min is returned.
        b1: Wykoff B1 coefficient.
        b2: Wykoff B2 coefficient (typically negative).
        dbh_min: Floor DBH returned for heights at or below 4.5 ft and
            for trees beyond the model's asymptote. Defaults to 0.1
            (the floor used by OC's small-tree path).

    Returns:
        Estimated DBH (inches), no smaller than dbh_min.
    """
    if height <= 4.5:
        return dbh_min

    denom = math.log(height - 4.5) - b1
    if denom >= 0:
        # ln(H-4.5) >= b1 means the height is at or beyond the Wykoff
        # asymptote (H = 4.5 + exp(b1)), where the inverse is undefined
        # or yields a negative DBH. Match solve_dbh_from_height by
        # returning a large sentinel.
        return 30.0

    dbh = b2 / denom - 1.0
    return max(dbh, dbh_min)


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

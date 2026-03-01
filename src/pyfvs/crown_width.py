"""
Crown width relationship functions for FVS-Python.
Implements forest-grown and open-grown crown width equations from the FVS Southern variant.
"""
from typing import Dict, Any

from .model_base import ParameterizedModel

__all__ = [
    'CrownWidthModel',
    'create_crown_width_model',
    'calculate_forest_crown_width',
    'calculate_open_crown_width',
    'calculate_ccf_contribution',
    'calculate_hopkins_index',
    'compare_crown_width_models',
    'validate_crown_width_implementation',
]


class CrownWidthModel(ParameterizedModel):
    """Crown width model implementing FVS Southern variant equations.

    Uses the base class pattern for loading species-specific coefficients
    from sn_crown_width_coefficients.json with fallback support.

    Note: This model has a more complex structure than other models because
    it has separate coefficient sets for forest-grown and open-grown crown width.
    """

    # Class attributes for ParameterizedModel base class
    COEFFICIENT_FILE = 'sn_crown_width_coefficients.json'
    COEFFICIENT_KEY = 'forest_grown'  # Primary key, but we also load 'open_grown'
    FALLBACK_PARAMETERS = {
        'LP': {
            'forest_grown': {
                "equation_number": "13101",
                "a1": -0.8277,
                "a2": 1.3946,
                "a3": None,
                "a4": 0.0768,
                "a5": None,
                "bounds": "FCW < 55"
            },
            'open_grown': {
                "equation_number": "13105",
                "a1": 0.7380,
                "a2": 0.2450,
                "a3": 0.000809,
                "a4": None,
                "a5": None,
                "bounds": "OCW < 55"
            }
        }
    }
    DEFAULT_SPECIES = "LP"

    def __init__(self, species_code: str = "LP"):
        """Initialize with species-specific parameters.

        Args:
            species_code: Species code (e.g., "LP", "SP", "SA", etc.)
        """
        super().__init__(species_code)

    def _load_parameters(self):
        """Load crown width parameters from cached configuration.

        Overrides base class to handle the dual coefficient structure
        (forest_grown and open_grown) specific to crown width models.
        """
        self.raw_data = self._get_coefficient_data()

        if self.raw_data:
            self.metadata = self.raw_data.get('metadata', {})
            self.equations = self.metadata.get('equations', {})

            # Get species coefficients for both forest-grown and open-grown
            forest_grown_data = self.raw_data.get('forest_grown', {})
            open_grown_data = self.raw_data.get('open_grown', {})

            self.forest_grown = forest_grown_data.get(self.species_code, {})
            self.open_grown = open_grown_data.get(self.species_code, {})

            # If species not found, use LP as default
            if not self.forest_grown:
                self.forest_grown = forest_grown_data.get(self.DEFAULT_SPECIES, {})
            if not self.open_grown:
                self.open_grown = open_grown_data.get(self.DEFAULT_SPECIES, {})

            # If still no data, use fallback
            if not self.forest_grown:
                self._load_fallback_parameters()

            # Store combined coefficients for base class compatibility
            self.coefficients = {
                'forest_grown': self.forest_grown,
                'open_grown': self.open_grown
            }
        else:
            # Fallback if file not found or empty
            self._load_fallback_parameters()

    def _load_fallback_parameters(self):
        """Load fallback parameters if crown width file not available.

        Overrides base class to handle the dual coefficient structure.
        """
        if self.species_code in self.FALLBACK_PARAMETERS:
            fallback = self.FALLBACK_PARAMETERS[self.species_code]
        else:
            fallback = self.FALLBACK_PARAMETERS.get(self.DEFAULT_SPECIES, {})

        self.forest_grown = fallback.get('forest_grown', {}).copy()
        self.open_grown = fallback.get('open_grown', {}).copy()

        self.metadata = {
            "equations": {
                "4.4.1": {
                    "formula": "FCW = a1 + (a2 * DBH) + (a3 * DBH^2) + (a4 * CR) + (a5 * HI)"
                },
                "4.4.3": {
                    "formula": "OCW = a1 + (a2 * DBH^a3)"
                }
            }
        }
        self.equations = self.metadata.get('equations', {})

        # Store combined coefficients for base class compatibility
        self.coefficients = {
            'forest_grown': self.forest_grown,
            'open_grown': self.open_grown
        }

    def calculate_hopkins_index(self, elevation: float, latitude: float, longitude: float) -> float:
        """Calculate Hopkins Index for geographic adjustment.

        Args:
            elevation: Elevation in feet
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees (negative for western hemisphere)

        Returns:
            Hopkins Index value
        """
        hi = ((elevation - 887) / 100 * 1.0 +
              (latitude - 39.54) * 4.0 +
              (-82.52 - longitude) * 1.25)
        return hi

    def calculate_forest_grown_crown_width(self, dbh: float, crown_ratio: float = 50.0,
                                         hopkins_index: float = 0.0) -> float:
        """Calculate forest-grown crown width (FCW).

        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio (percent, 0-100)
            hopkins_index: Hopkins Index for geographic adjustment

        Returns:
            Forest-grown crown width (feet)
        """
        if dbh <= 0:
            return 0.0

        coeffs = self.forest_grown

        # Extract coefficients
        a1 = coeffs.get('a1', 0.0)
        a2 = coeffs.get('a2', 0.0)
        a3 = coeffs.get('a3')
        a4 = coeffs.get('a4')
        a5 = coeffs.get('a5')

        # Determine equation type and calculate FCW
        # Use Bechtold equation (4.4.1) if species has a4 or a5 coefficients (crown ratio or Hopkins index terms)
        # Use Bragg equation (4.4.2) if species only has a1, a2, a3 coefficients
        if (a4 is not None or a5 is not None):
            # Equation 4.4.1: FCW = a1 + (a2 * DBH) + (a3 * DBH^2) + (a4 * CR) + (a5 * HI)
            fcw = a1 + (a2 * dbh)

            if a3 is not None:
                fcw += a3 * dbh**2
            if a4 is not None:
                fcw += a4 * crown_ratio
            if a5 is not None:
                fcw += a5 * hopkins_index
        else:
            # Equation 4.4.2: FCW = a1 + (a2 * DBH^a3)
            if a3 is not None:
                fcw = a1 + (a2 * dbh**a3)
            else:
                fcw = a1 + (a2 * dbh)

        # Apply scaling for small trees (DBH < 5.0)
        if dbh < 5.0:
            fcw_at_5 = self.calculate_forest_grown_crown_width(5.0, crown_ratio, hopkins_index)
            fcw = fcw_at_5 * (dbh / 5.0)

        # Apply bounds if specified
        bounds = coeffs.get('bounds', '')
        if 'FCW <' in bounds:
            try:
                max_fcw = float(bounds.split('FCW <')[1].strip())
                fcw = min(fcw, max_fcw)
            except (ValueError, IndexError):
                pass
        elif 'DBH <' in bounds:
            try:
                max_dbh = float(bounds.split('DBH <')[1].strip())
                if dbh >= max_dbh:
                    # Use the equation at the maximum allowed DBH
                    bounded_dbh = max_dbh - 0.1
                    # Recalculate with bounded DBH to avoid infinite recursion
                    if (a4 is not None or a5 is not None):
                        fcw = a1 + (a2 * bounded_dbh)
                        if a3 is not None:
                            fcw += a3 * bounded_dbh**2
                        if a4 is not None:
                            fcw += a4 * crown_ratio
                        if a5 is not None:
                            fcw += a5 * hopkins_index
                    else:
                        if a3 is not None:
                            fcw = a1 + (a2 * bounded_dbh**a3)
                        else:
                            fcw = a1 + (a2 * bounded_dbh)
            except (ValueError, IndexError):
                pass

        return max(0.0, fcw)

    def calculate_open_grown_crown_width(self, dbh: float) -> float:
        """Calculate open-grown crown width (OCW).

        Args:
            dbh: Diameter at breast height (inches)

        Returns:
            Open-grown crown width (feet)
        """
        if dbh <= 0:
            return 0.0

        coeffs = self.open_grown
        equation_num = coeffs.get('equation_number', '13105')
        eq_type = equation_num[:3]  # Get equation type from first 3 digits

        # Extract coefficients
        a1 = coeffs.get('a1', 0.0)
        a2 = coeffs.get('a2', 0.0)
        a3 = coeffs.get('a3')

        # Determine equation type and calculate OCW
        # Check if it's equation 4.4.5 (Smith et al. 1992) - has specific equation numbers ending in 61
        if equation_num.endswith('61') and a3 is not None:
            # Equation 4.4.5: OCW = a1 + (a2 * DBH * 2.54) + (a3 * (DBH * 2.54)^2) * 3.28084
            dbh_cm = dbh * 2.54  # Convert to cm
            ocw = a1 + (a2 * dbh_cm)
            if a3 is not None:
                ocw += a3 * dbh_cm**2
            ocw *= 3.28084  # Convert to feet
        elif eq_type in ['012', '068', '094', '132', '110', '131', '221'] or equation_num.endswith('01'):
            # Equation 4.4.4: OCW = a1 + (a2 * DBH)
            ocw = a1 + (a2 * dbh)
        elif a3 is not None:
            # Equation 4.4.3: OCW = a1 + (a2 * DBH^a3)
            ocw = a1 + (a2 * dbh**a3)
        else:
            # Default linear equation: OCW = a1 + (a2 * DBH)
            ocw = a1 + (a2 * dbh)

        # Apply scaling for small trees (DBH < 3.0)
        if dbh < 3.0:
            ocw_at_3 = self.calculate_open_grown_crown_width(3.0)
            ocw = ocw_at_3 * (dbh / 3.0)

        # Apply bounds if specified
        bounds = coeffs.get('bounds', '')
        if 'OCW <' in bounds:
            try:
                max_ocw = float(bounds.split('OCW <')[1].strip())
                ocw = min(ocw, max_ocw)
            except (ValueError, IndexError):
                pass
        elif 'DBH <' in bounds:
            try:
                max_dbh = float(bounds.split('DBH <')[1].strip())
                if dbh >= max_dbh:
                    # Use the equation at the maximum allowed DBH
                    bounded_dbh = max_dbh - 0.1
                    # Recalculate with bounded DBH to avoid infinite recursion
                    if equation_num.endswith('61') and a3 is not None:
                        dbh_cm = bounded_dbh * 2.54
                        ocw = a1 + (a2 * dbh_cm)
                        if a3 is not None:
                            ocw += a3 * dbh_cm**2
                        ocw *= 3.28084
                    elif eq_type in ['012', '068', '094', '132', '110', '131', '221'] or equation_num.endswith('01'):
                        ocw = a1 + (a2 * bounded_dbh)
                    elif a3 is not None:
                        ocw = a1 + (a2 * bounded_dbh**a3)
                    else:
                        ocw = a1 + (a2 * bounded_dbh)
            except (ValueError, IndexError):
                pass

        return max(0.0, ocw)

    def calculate_ccf_contribution(self, dbh: float) -> float:
        """Calculate Crown Competition Factor contribution for a single tree.

        Args:
            dbh: Diameter at breast height (inches)

        Returns:
            CCF contribution for this tree
        """
        if dbh <= 0.1:
            return 0.001

        ocw = self.calculate_open_grown_crown_width(dbh)
        return 0.001803 * ocw**2

    def calculate_maximum_crown_width(self, dbh: float, crown_ratio: float = 50.0,
                                    hopkins_index: float = 0.0,
                                    crown_type: str = "forest") -> float:
        """Calculate maximum crown width based on crown type.

        Args:
            dbh: Diameter at breast height (inches)
            crown_ratio: Crown ratio (percent, 0-100)
            hopkins_index: Hopkins Index for geographic adjustment
            crown_type: Type of crown width ("forest" or "open")

        Returns:
            Maximum crown width (feet)
        """
        if crown_type.lower() in ["forest", "fcw"]:
            return self.calculate_forest_grown_crown_width(dbh, crown_ratio, hopkins_index)
        elif crown_type.lower() in ["open", "ocw"]:
            return self.calculate_open_grown_crown_width(dbh)
        else:
            raise ValueError(f"Unknown crown type: {crown_type}. Use 'forest' or 'open'.")

    def get_species_coefficients(self) -> Dict[str, Dict[str, Any]]:
        """Get the crown width coefficients for this species.

        Returns:
            Dictionary with forest-grown and open-grown coefficients
        """
        return {
            'forest_grown': self.forest_grown.copy(),
            'open_grown': self.open_grown.copy()
        }

    def get_equation_info(self, crown_type: str = "forest") -> Dict[str, Any]:
        """Get equation information for the specified crown type.

        Args:
            crown_type: Type of crown width ("forest" or "open")

        Returns:
            Dictionary with equation information
        """
        if crown_type.lower() in ["forest", "fcw"]:
            eq_num = self.forest_grown.get('equation_number', '13101')
        else:
            eq_num = self.open_grown.get('equation_number', '13105')

        # Map equation numbers to equation types
        eq_type_map = {
            '01201': '4.4.1', '06801': '4.4.1', '09401': '4.4.1', '13201': '4.4.1',
            '11001': '4.4.1', '11101': '4.4.2', '11001': '4.4.1', '12101': '4.4.1',
            '12601': '4.4.1', '12801': '4.4.2', '12901': '4.4.1', '13101': '4.4.1',
            '22101': '4.4.1', '26101': '4.4.2', '31801': '4.4.1', '31301': '4.4.1',
            '31601': '4.4.2', '31701': '4.4.1', '40701': '4.4.1', '37301': '4.4.1',
            '37201': '4.4.1', '39101': '4.4.1', '93101': '4.4.1', '46201': '4.4.1',
            '49101': '4.4.1', '52101': '4.4.1', '53101': '4.4.1', '54401': '4.4.1',
            '54101': '4.4.1', '54301': '4.4.1', '55201': '4.4.1', '65301': '4.4.1'
        }

        eq_type = eq_type_map.get(eq_num[:5], '4.4.1')

        return {
            'equation_number': eq_num,
            'equation_type': eq_type,
            'equation_info': self.equations.get(eq_type, {})
        }


_crown_width_cache: dict[str, CrownWidthModel] = {}


def create_crown_width_model(species_code: str = "LP") -> CrownWidthModel:
    """Factory function to create a cached crown width model for a species.

    Args:
        species_code: Species code (e.g., "LP", "SP", "SA", etc.)

    Returns:
        CrownWidthModel instance (cached by species)
    """
    key = species_code.upper()
    if key not in _crown_width_cache:
        _crown_width_cache[key] = CrownWidthModel(species_code)
    return _crown_width_cache[key]


def calculate_forest_crown_width(species_code: str, dbh: float, crown_ratio: float = 50.0,
                               hopkins_index: float = 0.0) -> float:
    """Standalone function to calculate forest-grown crown width.

    Args:
        species_code: Species code
        dbh: Diameter at breast height (inches)
        crown_ratio: Crown ratio (percent)
        hopkins_index: Hopkins Index for geographic adjustment

    Returns:
        Forest-grown crown width (feet)
    """
    model = create_crown_width_model(species_code)
    return model.calculate_forest_grown_crown_width(dbh, crown_ratio, hopkins_index)


def calculate_open_crown_width(species_code: str, dbh: float) -> float:
    """Standalone function to calculate open-grown crown width.

    Args:
        species_code: Species code
        dbh: Diameter at breast height (inches)

    Returns:
        Open-grown crown width (feet)
    """
    model = create_crown_width_model(species_code)
    return model.calculate_open_grown_crown_width(dbh)


def calculate_ccf_contribution(species_code: str, dbh: float) -> float:
    """Standalone function to calculate CCF contribution.

    Args:
        species_code: Species code
        dbh: Diameter at breast height (inches)

    Returns:
        CCF contribution for this tree
    """
    model = create_crown_width_model(species_code)
    return model.calculate_ccf_contribution(dbh)


def calculate_hopkins_index(elevation: float, latitude: float, longitude: float) -> float:
    """Standalone function to calculate Hopkins Index.

    Args:
        elevation: Elevation in feet
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees (negative for western hemisphere)

    Returns:
        Hopkins Index value
    """
    return ((elevation - 887) / 100 * 1.0 +
            (latitude - 39.54) * 4.0 +
            (-82.52 - longitude) * 1.25)


def compare_crown_width_models(species_codes: list, dbh_range: list) -> Dict[str, Any]:
    """Compare crown width predictions across species and diameter ranges.

    Args:
        species_codes: List of species codes to compare
        dbh_range: List of DBH values to evaluate (inches)

    Returns:
        Dictionary with comparison results
    """
    results = {
        'dbh': dbh_range,
        'species_results': {}
    }

    for species in species_codes:
        model = create_crown_width_model(species)

        forest_cw = []
        open_cw = []
        ccf_contrib = []

        for dbh in dbh_range:
            fcw = model.calculate_forest_grown_crown_width(dbh)
            ocw = model.calculate_open_grown_crown_width(dbh)
            ccf = model.calculate_ccf_contribution(dbh)

            forest_cw.append(fcw)
            open_cw.append(ocw)
            ccf_contrib.append(ccf)

        results['species_results'][species] = {
            'forest_crown_width': forest_cw,
            'open_crown_width': open_cw,
            'ccf_contribution': ccf_contrib,
            'coefficients': model.get_species_coefficients()
        }

    return results


def validate_crown_width_implementation():
    """Validate the crown width implementation with test cases.

    Returns:
        Dictionary with validation results
    """
    test_cases = [
        {"species": "LP", "dbh": 10.0, "expected_fcw_range": (8.0, 15.0), "expected_ocw_range": (5.0, 12.0)},
        {"species": "SA", "dbh": 15.0, "expected_fcw_range": (12.0, 20.0), "expected_ocw_range": (8.0, 16.0)},
        {"species": "SP", "dbh": 8.0, "expected_fcw_range": (6.0, 12.0), "expected_ocw_range": (4.0, 10.0)},
    ]

    results = {"passed": 0, "failed": 0, "details": []}

    for test in test_cases:
        model = create_crown_width_model(test["species"])

        fcw = model.calculate_forest_grown_crown_width(test["dbh"])
        ocw = model.calculate_open_grown_crown_width(test["dbh"])

        fcw_min, fcw_max = test["expected_fcw_range"]
        ocw_min, ocw_max = test["expected_ocw_range"]

        fcw_passed = fcw_min <= fcw <= fcw_max
        ocw_passed = ocw_min <= ocw <= ocw_max
        passed = fcw_passed and ocw_passed

        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1

        results["details"].append({
            "species": test["species"],
            "dbh": test["dbh"],
            "calculated_fcw": fcw,
            "calculated_ocw": ocw,
            "expected_fcw_range": test["expected_fcw_range"],
            "expected_ocw_range": test["expected_ocw_range"],
            "fcw_passed": fcw_passed,
            "ocw_passed": ocw_passed,
            "passed": passed
        })

    return results

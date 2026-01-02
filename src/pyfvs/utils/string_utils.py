"""
String normalization utilities for FVS-Python.

Provides consistent string normalization for species codes, ecological unit codes,
and other identifiers used throughout the codebase.
"""


def normalize_code(code: str) -> str:
    """Normalize a code string (species, ecounit, etc.) to uppercase, trimmed.

    Args:
        code: The code string to normalize.

    Returns:
        Uppercase, whitespace-trimmed version of the code.
        Returns empty string if code is None or falsy.
    """
    return code.upper().strip() if code else ""


def normalize_species_code(code: str) -> str:
    """Normalize a species code to uppercase, trimmed.

    Args:
        code: FVS species code (e.g., "lp", " LP ", "Lp").

    Returns:
        Normalized species code (e.g., "LP").
    """
    return normalize_code(code)


def normalize_ecounit(code: str) -> str:
    """Normalize an ecological unit code to uppercase, trimmed.

    Args:
        code: Ecological unit group code (e.g., "m231", " M231 ").

    Returns:
        Normalized ecounit code (e.g., "M231").
    """
    return normalize_code(code)

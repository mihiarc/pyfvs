"""Pydantic 2 validation schemas for FVS coefficient JSON files.

Provides structural validation for the ~55 JSON configuration files used by PyFVS.
Schemas validate that required keys exist with correct types while allowing extras
(extra="allow"). Validation is warn-only by default — no behavioral changes.

Usage:
    from pyfvs.config_schemas import validate_coefficient_file

    warnings = validate_coefficient_file("sn_bark_ratio_coefficients.json", data)
    # Returns list of ValidationWarning; logs via pyfvs.config_validation
"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, ValidationError

logger = logging.getLogger("pyfvs.config_validation")


# ---------------------------------------------------------------------------
# Validation result types
# ---------------------------------------------------------------------------

@dataclass
class ValidationWarning:
    """A single validation warning for a coefficient file."""
    filename: str
    message: str
    field: str = ""


# ---------------------------------------------------------------------------
# Schema models — one per structural family
# ---------------------------------------------------------------------------

# --- Bark Ratio (SN: linear b1/b2 per species) ---

class BarkRatioLinearCoeffs(BaseModel):
    model_config = ConfigDict(extra="allow")
    b1: float
    b2: float


class SNBarkRatioFile(BaseModel):
    """SN bark ratio: species_coefficients → {b1, b2}."""
    model_config = ConfigDict(extra="allow")
    species_coefficients: Dict[str, BarkRatioLinearCoeffs]


# --- Bark Ratio (LS/CS/NE: constant ratio per species) ---

class ConstantBarkRatioFile(BaseModel):
    """LS/CS/NE bark ratio: species_bark_ratios → float."""
    model_config = ConfigDict(extra="allow")
    species_bark_ratios: Dict[str, float]


# --- Bark Ratio (WS: species_bark_ratios with bark1/bark2) ---

class WSBarkRatioFile(BaseModel):
    """WS bark ratio: species_bark_ratios → {bark1, bark2}."""
    model_config = ConfigDict(extra="allow")
    species_bark_ratios: Dict[str, Any]


# --- Bark Ratio (PN: group-based with jbark_array) ---

class PNBarkRatioFile(BaseModel):
    """PN bark ratio: species_groups + jbark_array."""
    model_config = ConfigDict(extra="allow")
    species_groups: Dict[str, Any]
    species_to_group: Dict[str, Any]


# --- SN Diameter Growth (core_coefficients with INTERC/LDBH/...) ---

class SNDGSpeciesCoeffs(BaseModel):
    model_config = ConfigDict(extra="allow")
    INTERC: float
    LDBH: float
    DBH2: float


class SNDGFile(BaseModel):
    """SN diameter growth: core_coefficients keyed by species code."""
    model_config = ConfigDict(extra="allow")
    core_coefficients: Dict[str, SNDGSpeciesCoeffs]


# --- LS/CS Diameter Growth (coefficients with INTERC) ---

class LSDGSpeciesCoeffs(BaseModel):
    model_config = ConfigDict(extra="allow")
    INTERC: float


class StandardDGFile(BaseModel):
    """LS/CS diameter growth: coefficients with UPPERCASE keys."""
    model_config = ConfigDict(extra="allow")
    coefficients: Dict[str, LSDGSpeciesCoeffs]


# --- NE Diameter Growth (coefficients with B1/B2) ---

class NEDGSpeciesCoeffs(BaseModel):
    model_config = ConfigDict(extra="allow")
    B1: float
    B2: float


class NEDGFile(BaseModel):
    """NE diameter growth: coefficients with B1/B2."""
    model_config = ConfigDict(extra="allow")
    coefficients: Dict[str, NEDGSpeciesCoeffs]


# --- PN/OP/OC/WS Diameter Growth (numeric-keyed + species_mapping) ---

class NumericKeyedDGFile(BaseModel):
    """PN/OP/OC/WS diameter growth: coefficients with numeric or species keys.

    PN/OP use species_mapping; OC/WS use species_to_equation. Both have coefficients.
    """
    model_config = ConfigDict(extra="allow")
    coefficients: Dict[str, Dict[str, Any]]


# --- WC Diameter Growth (coefficient_sets instead of coefficients) ---

class WCDGFile(BaseModel):
    """WC diameter growth: species_mapping + coefficient_sets."""
    model_config = ConfigDict(extra="allow")
    species_mapping: Dict[str, Any]
    coefficient_sets: Dict[str, Dict[str, Any]]


# --- CA Diameter Growth (species key instead of coefficients) ---

class CADGFile(BaseModel):
    """CA diameter growth: species_equation_map + species."""
    model_config = ConfigDict(extra="allow")
    species: Dict[str, Any]


# --- EC Diameter Growth (species_coefficients with DGLD/DGCR/...) ---

class ECDGFile(BaseModel):
    """EC diameter growth: species_coefficients keyed by species code.

    Each species coefficients dict has DGLD, DGCR, DGCRSQ, DGSITE,
    DGDBAL, DGDUM, DGHCCF, DGPCCF, DGCCFA, DGCASP, DGSASP, DGSLOP,
    DGSLSQ, DGEL, DGEL2, SL0DUM, DGBA, DGFOR (list), DGDS (list),
    fortran_index, and equation_class. Schema is intentionally
    permissive to avoid coupling to every numeric key; exact structure
    is asserted via the ec_diameter_growth unit tests.
    """
    model_config = ConfigDict(extra="allow")
    species_coefficients: Dict[str, Dict[str, Any]]
    species_to_equation: Dict[str, Any]
    variance_parameters: Dict[str, float]


# --- Height-Diameter (metadata + coefficients with P2/P3/P4) ---

class HDSpeciesCoeffs(BaseModel):
    """Height-diameter species coefficients. P2/P3/P4 may be uppercase or lowercase."""
    model_config = ConfigDict(extra="allow")
    # Some files use P2/P3/P4, others use p2/p3/p4, some have only Wykoff.
    # We make all optional and validate that at least one set exists in
    # _validate_flat_height_diameter.


class HeightDiameterFile(BaseModel):
    """Height-diameter files with metadata/description + coefficients wrapper."""
    model_config = ConfigDict(extra="allow")
    coefficients: Dict[str, Any]


class FlatHeightDiameterFile(BaseModel):
    """Height-diameter file with species codes as top-level keys (no wrapper).

    Used by SN, OP, WC, OC, WS. Validated via custom logic since
    Pydantic models expect a fixed object structure.
    """
    pass  # Validated via _validate_flat_height_diameter


# --- Small Tree Height Growth (SN/LS/CS/NE: nc128 with c1-c5) ---

class SmallTreeHGSpeciesCoeffs(BaseModel):
    model_config = ConfigDict(extra="allow")
    c1: float
    c2: float
    c3: float
    c4: float
    c5: float


class SmallTreeHGFile(BaseModel):
    """SN/LS/CS/NE small tree HG: nc128_height_growth_coefficients."""
    model_config = ConfigDict(extra="allow")
    nc128_height_growth_coefficients: Dict[str, SmallTreeHGSpeciesCoeffs]


# --- PN SMHGDG (coefficients with alpha array + beta + dmax) ---

class SMHGDGSpeciesCoeffs(BaseModel):
    model_config = ConfigDict(extra="allow")
    beta: float
    dmax: float
    alpha: List[float]


class SMHGDGFile(BaseModel):
    """PN SMHGDG small-tree diameter/height growth."""
    model_config = ConfigDict(extra="allow")
    coefficients: Dict[str, SMHGDGSpeciesCoeffs]


# --- Clark Taper (species_coefficients with r/c/e/p/a/b) ---

class ClarkTaperSpeciesCoeffs(BaseModel):
    model_config = ConfigDict(extra="allow")
    r: float
    c: float
    e: float
    p: float
    a: float
    b: float


class ClarkTaperFile(BaseModel):
    """Clark taper files (R8/R9) with species_coefficients."""
    model_config = ConfigDict(extra="allow")
    species_coefficients: Dict[str, ClarkTaperSpeciesCoeffs]


# --- Flewelling Taper (species_parameters with jsp) ---

class FlewellingSpeciesParams(BaseModel):
    model_config = ConfigDict(extra="allow")
    jsp: int


class FlewellingFile(BaseModel):
    """Flewelling taper file with species_parameters."""
    model_config = ConfigDict(extra="allow")
    species_parameters: Dict[str, FlewellingSpeciesParams]


# --- Crown Ratio (SN: species_coefficients with d0) ---

class SNCrownRatioSpeciesCoeffs(BaseModel):
    model_config = ConfigDict(extra="allow")
    d0: float


class SNCrownRatioFile(BaseModel):
    """SN crown ratio: species_coefficients with d0/d1/d2/a/b/c."""
    model_config = ConfigDict(extra="allow")
    species_coefficients: Dict[str, SNCrownRatioSpeciesCoeffs]


# --- Crown Ratio (LS/CS/NE: species_coefficients with BCR1-4) ---

class LSCrownRatioSpeciesCoeffs(BaseModel):
    model_config = ConfigDict(extra="allow")
    BCR1: float
    BCR2: float
    BCR3: float
    BCR4: float


class StandardCrownRatioFile(BaseModel):
    """LS/CS/NE crown ratio: species_coefficients with BCR1-4."""
    model_config = ConfigDict(extra="allow")
    species_coefficients: Dict[str, LSCrownRatioSpeciesCoeffs]


# --- Crown Ratio (PN: mean_cr_coefficients + weibull_parameters) ---

class PNCrownRatioFile(BaseModel):
    """PN crown ratio: mean_cr_coefficients + weibull_parameters."""
    model_config = ConfigDict(extra="allow")
    mean_cr_coefficients: Dict[str, Any]
    weibull_parameters: Dict[str, Any]


# --- Crown Ratio (EC: species_coefficients with per-species Weibull + C0/C1) ---

class ECCrownRatioSpeciesCoeffs(BaseModel):
    model_config = ConfigDict(extra="allow")
    weib_a: float
    weib_b0: float
    weib_b1: float
    weib_c0: float
    weib_c1: float
    c0: float
    c1: float


class ECCrownRatioFile(BaseModel):
    """EC crown ratio: per-species Weibull parameters from ec/crown.f."""
    model_config = ConfigDict(extra="allow")
    species_coefficients: Dict[str, ECCrownRatioSpeciesCoeffs]


# --- Large Tree Height Growth (balmod_coefficients or coefficients) ---

class LargeTreeHGFile(BaseModel):
    """Large tree height growth coefficient files."""
    model_config = ConfigDict(extra="allow")
    # SN uses 'coefficients', LS uses 'balmod_coefficients' — both are dicts
    # We only require that the file is a valid dict (extra="allow" handles the rest)


# --- Mortality (SN: tables structure) ---

class MortalityTableEntry(BaseModel):
    model_config = ConfigDict(extra="allow")


class SNMortalityFile(BaseModel):
    """SN mortality model with tables structure."""
    model_config = ConfigDict(extra="allow")
    tables: Dict[str, MortalityTableEntry]


# --- Mortality (LS/CS/NE: coefficients structure) ---

class StandardMortalityFile(BaseModel):
    """LS/CS/NE mortality: coefficients keyed by species."""
    model_config = ConfigDict(extra="allow")
    coefficients: Dict[str, Dict[str, Any]]


class SNMortalityDefaultsFile(BaseModel):
    """SN variant VARADJ shade tolerance defaults."""
    model_config = ConfigDict(extra="allow")
    varadj: Dict[str, float]


class LSMortalityDefaultsFile(BaseModel):
    """LS variant mortality defaults: species groups, SDI maximums, shade tolerance."""
    model_config = ConfigDict(extra="allow")
    species_mortality_group: Dict[str, int]
    sdi_maximums: Dict[str, float]
    shade_tolerance: Dict[str, float]


class WSMortalityDefaultsFile(BaseModel):
    """WS variant mortality defaults: background mortality B0/B1 + VARADJ shade tolerance."""
    model_config = ConfigDict(extra="allow")
    varadj: Dict[str, float]


class CABarkRatioFile(BaseModel):
    """CA bark ratio: species_to_group + species_groups with type/a/b."""
    model_config = ConfigDict(extra="allow")
    species_to_group: Dict[str, Any]
    species_groups: Dict[str, Any]


class CAMortalityDefaultsFile(BaseModel):
    """CA variant mortality defaults: VARADJ shade tolerance + background mortality."""
    model_config = ConfigDict(extra="allow")
    varadj: Dict[str, float]


class OCBarkRatioFile(BaseModel):
    """OC bark ratio: species_bark_ratios with per-species type/brdat/a/b."""
    model_config = ConfigDict(extra="allow")
    species_bark_ratios: Dict[str, Any]


class OCMortalityDefaultsFile(BaseModel):
    """OC variant mortality defaults: 50-species mortality groups, SDI maximums, shade tolerance.

    Mirrors the LS layout (species_mortality_group + sdi_maximums + shade_tolerance) since
    OCMortalityModel is implemented as an LSMortalityModel subclass with 7 background groups
    instead of 4.
    """
    model_config = ConfigDict(extra="allow")
    species_mortality_group: Dict[str, int]
    sdi_maximums: Dict[str, float]
    shade_tolerance: Dict[str, float]


class ECMortalityDefaultsFile(BaseModel):
    """EC variant mortality defaults: per-species PMSC/PMD + HHTMAX."""
    model_config = ConfigDict(extra="allow")
    species_coefficients: Dict[str, Any]


# ---------------------------------------------------------------------------
# Schema registry — maps filename patterns to schema classes
# ---------------------------------------------------------------------------

# Each entry: (regex pattern, schema class)
# Order matters: first match wins.
SCHEMA_REGISTRY: List[tuple] = [
    # Bark ratio
    (r"sn_bark_ratio_coefficients\.json$", SNBarkRatioFile),
    (r"(ne|ls|cs).+bark_ratio_coefficients\.json$", ConstantBarkRatioFile),
    (r"ws.+bark_ratio_coefficients\.json$", WSBarkRatioFile),
    (r"ca.+bark_ratio_coefficients\.json$", CABarkRatioFile),
    (r"oc.+bark_ratio_coefficients\.json$", OCBarkRatioFile),
    (r"pn.+bark_ratio_coefficients\.json$", PNBarkRatioFile),
    (r"ec.+bark_ratio_coefficients\.json$", PNBarkRatioFile),

    # Diameter growth
    (r"sn_diameter_growth_coefficients\.json$", SNDGFile),
    (r"ne.+diameter_growth_coefficients\.json$", NEDGFile),
    (r"(ls|cs).+diameter_growth_coefficients\.json$", StandardDGFile),
    (r"wc.+diameter_growth_coefficients\.json$", WCDGFile),
    (r"ca.+diameter_growth_coefficients\.json$", CADGFile),
    (r"ec.+diameter_growth_coefficients\.json$", ECDGFile),
    (r"(pn|op|oc|ws).+diameter_growth_coefficients\.json$", NumericKeyedDGFile),

    # Height-diameter — flat (species as top-level keys) must come before wrapped
    (r"sn_height_diameter_coefficients\.json$", FlatHeightDiameterFile),
    (r"(op|wc|oc|ws).+height_diameter_coefficients\.json$", FlatHeightDiameterFile),
    (r"height_diameter_coefficients\.json$", HeightDiameterFile),

    # Small tree height growth
    (r"smhgdg_coefficients\.json$", SMHGDGFile),
    (r"small_tree_height_growth\.json$", SmallTreeHGFile),

    # Taper
    (r"clark_r[89]_coefficients\.json$", ClarkTaperFile),
    (r"flewelling_coefficients\.json$", FlewellingFile),

    # Crown ratio
    (r"sn_crown_ratio_coefficients\.json$", SNCrownRatioFile),
    (r"pn.+crown_ratio_coefficients\.json$", PNCrownRatioFile),
    (r"ws.+crown_ratio_coefficients\.json$", PNCrownRatioFile),
    (r"ca.+crown_ratio_coefficients\.json$", PNCrownRatioFile),
    (r"oc.+crown_ratio_coefficients\.json$", PNCrownRatioFile),
    (r"ec.+crown_ratio_coefficients\.json$", ECCrownRatioFile),
    (r"crown_ratio_coefficients\.json$", StandardCrownRatioFile),

    # Large tree height growth
    (r"large_tree_height_growth_coefficients\.json$", LargeTreeHGFile),

    # Mortality
    (r"sn_mortality_model\.json$", SNMortalityFile),
    (r"sn_mortality_defaults\.json$", SNMortalityDefaultsFile),
    (r"ls_mortality_defaults\.json$", LSMortalityDefaultsFile),
    (r"ws_mortality_defaults\.json$", WSMortalityDefaultsFile),
    (r"ca_mortality_defaults\.json$", CAMortalityDefaultsFile),
    (r"oc_mortality_defaults\.json$", OCMortalityDefaultsFile),
    (r"ec_mortality_defaults\.json$", ECMortalityDefaultsFile),
    (r"mortality_coefficients\.json$", StandardMortalityFile),
]


def _find_schema(filename: str) -> Optional[Type[BaseModel]]:
    """Look up the validation schema for a given filename.

    Args:
        filename: The coefficient file name (may include subdirectory path).

    Returns:
        The Pydantic model class, or None if no schema is registered.
    """
    normalized = filename.replace("\\", "/")
    for pattern, schema_class in SCHEMA_REGISTRY:
        if re.search(pattern, normalized):
            return schema_class
    return None


# ---------------------------------------------------------------------------
# Validation function
# ---------------------------------------------------------------------------

def validate_coefficient_file(
    filename: str,
    data: Any,
    strict: bool = False,
) -> List[ValidationWarning]:
    """Validate a coefficient file's structure against its registered schema.

    Args:
        filename: The coefficient file name (used for schema lookup and logging).
        data: The parsed JSON data (dict).
        strict: If True, raise ConfigurationError on validation failure.
                If False (default), log warnings and return them.

    Returns:
        List of ValidationWarning objects (empty if valid or no schema found).
    """
    from .exceptions import ConfigurationError

    warnings: List[ValidationWarning] = []

    schema_class = _find_schema(filename)
    if schema_class is None:
        return warnings

    # Special handling for FlatHeightDiameterFile (species as top-level keys)
    if schema_class is FlatHeightDiameterFile:
        return _validate_flat_height_diameter(filename, data, strict)

    try:
        schema_class.model_validate(data)
    except ValidationError as exc:
        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            message = f"{error['msg']} at {field_path}"
            warning = ValidationWarning(
                filename=filename,
                message=message,
                field=field_path,
            )
            warnings.append(warning)
            logger.warning("Config validation [%s]: %s", filename, message)

        if strict:
            raise ConfigurationError(
                f"Validation failed for {filename}: "
                f"{len(warnings)} error(s). First: {warnings[0].message}"
            ) from exc

    return warnings


def _validate_flat_height_diameter(
    filename: str,
    data: Any,
    strict: bool,
) -> List[ValidationWarning]:
    """Validate height-diameter files with species codes as top-level keys."""
    from .exceptions import ConfigurationError

    warnings: List[ValidationWarning] = []

    if not isinstance(data, dict):
        warning = ValidationWarning(
            filename=filename,
            message="Expected dict with species-code keys, got " + type(data).__name__,
            field="(root)",
        )
        warnings.append(warning)
        logger.warning("Config validation [%s]: %s", filename, warning.message)
        if strict:
            raise ConfigurationError(
                f"Validation failed for {filename}: {warning.message}"
            )
        return warnings

    species_count = 0
    for species_code, coeffs in data.items():
        # Skip metadata keys (e.g. _metadata, metadata)
        if species_code.startswith("_") or species_code == "metadata":
            continue
        if not isinstance(coeffs, dict):
            continue
        species_count += 1
        # Validate that at least one of P2/p2 or Wykoff_B1 exists
        has_curtis_arney = any(
            k in coeffs for k in ("P2", "p2", "P3", "p3")
        )
        has_wykoff = "Wykoff_B1" in coeffs
        if not has_curtis_arney and not has_wykoff:
            message = f"No P2/p2 or Wykoff_B1 found at {species_code}"
            warning = ValidationWarning(
                filename=filename, message=message, field=species_code
            )
            warnings.append(warning)
            logger.warning("Config validation [%s]: %s", filename, message)

    if species_count == 0:
        message = "No species entries found (expected species-code keys)"
        warning = ValidationWarning(
            filename=filename, message=message, field="(root)"
        )
        warnings.append(warning)
        logger.warning("Config validation [%s]: %s", filename, message)

    if strict and warnings:
        raise ConfigurationError(
            f"Validation failed for {filename}: "
            f"{len(warnings)} error(s). First: {warnings[0].message}"
        )
    return warnings


def validate_all_configs(cfg_dir: Optional[Path] = None) -> List[ValidationWarning]:
    """Validate all JSON coefficient files under the cfg directory.

    Args:
        cfg_dir: Path to the cfg directory. Defaults to the package cfg/.

    Returns:
        Aggregated list of all validation warnings.
    """
    import json

    if cfg_dir is None:
        cfg_dir = Path(__file__).parent / "cfg"

    all_warnings: List[ValidationWarning] = []

    for json_path in sorted(cfg_dir.rglob("*.json")):
        relative = str(json_path.relative_to(cfg_dir))
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            warning = ValidationWarning(
                filename=relative,
                message=f"Failed to parse: {exc}",
            )
            all_warnings.append(warning)
            logger.error("Config validation [%s]: %s", relative, warning.message)
            continue

        file_warnings = validate_coefficient_file(relative, data)
        all_warnings.extend(file_warnings)

    return all_warnings

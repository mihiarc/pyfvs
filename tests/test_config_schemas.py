"""Tests for JSON coefficient file validation schemas.

Validates that:
- All JSON files parse without errors
- All files with registered schemas validate cleanly
- Key coefficient file families have correct structure
- Fallback logging works correctly
- Invalid data produces appropriate warnings
"""
import json
import logging
from pathlib import Path

import pytest

from pyfvs.config_schemas import (
    SCHEMA_REGISTRY,
    ValidationWarning,
    _find_schema,
    validate_all_configs,
    validate_coefficient_file,
)

CFG_DIR = Path(__file__).parent.parent / "src" / "pyfvs" / "cfg"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_json_files():
    """Yield (relative_path, data) for every JSON file in cfg/."""
    for json_path in sorted(CFG_DIR.rglob("*.json")):
        relative = str(json_path.relative_to(CFG_DIR))
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        yield relative, data


# ---------------------------------------------------------------------------
# Phase 1: All JSON files parse
# ---------------------------------------------------------------------------

class TestAllJsonFilesParse:
    """Every JSON file in cfg/ must parse without errors."""

    @pytest.fixture(scope="class")
    def json_files(self):
        return list(CFG_DIR.rglob("*.json"))

    def test_all_json_files_exist(self, json_files):
        assert len(json_files) > 40, f"Expected 40+ JSON files, found {len(json_files)}"

    def test_all_json_files_parse(self, json_files):
        errors = []
        for json_path in json_files:
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError as exc:
                errors.append(f"{json_path.name}: {exc}")
        assert errors == [], f"JSON parse errors:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# Phase 2: All files with schemas validate cleanly
# ---------------------------------------------------------------------------

class TestAllJsonFilesValidate:
    """Every JSON file with a registered schema must validate without warnings."""

    def test_validate_all_configs_clean(self):
        warnings = validate_all_configs(CFG_DIR)
        if warnings:
            details = "\n".join(f"  {w.filename}: {w.message}" for w in warnings[:20])
            pytest.fail(
                f"{len(warnings)} validation warning(s):\n{details}"
            )

    def test_all_json_files_have_no_warnings(self):
        for relative, data in _all_json_files():
            warnings = validate_coefficient_file(relative, data)
            assert warnings == [], (
                f"{relative}: {len(warnings)} warning(s) — "
                f"{warnings[0].message if warnings else ''}"
            )


# ---------------------------------------------------------------------------
# Phase 3: Schema coverage
# ---------------------------------------------------------------------------

class TestSchemaCoverage:
    """Key coefficient file families have registered schemas."""

    def test_all_dg_files_have_schemas(self):
        missing = []
        for json_path in CFG_DIR.rglob("*diameter_growth_coefficients.json"):
            relative = str(json_path.relative_to(CFG_DIR))
            schema = _find_schema(relative)
            if schema is None:
                missing.append(relative)
        assert missing == [], f"DG files without schemas: {missing}"

    def test_all_bark_ratio_files_have_schemas(self):
        missing = []
        for json_path in CFG_DIR.rglob("*bark_ratio_coefficients.json"):
            relative = str(json_path.relative_to(CFG_DIR))
            schema = _find_schema(relative)
            if schema is None:
                missing.append(relative)
        assert missing == [], f"Bark ratio files without schemas: {missing}"

    def test_all_height_diameter_files_have_schemas(self):
        missing = []
        for json_path in CFG_DIR.rglob("*height_diameter_coefficients.json"):
            relative = str(json_path.relative_to(CFG_DIR))
            schema = _find_schema(relative)
            if schema is None:
                missing.append(relative)
        assert missing == [], f"H-D files without schemas: {missing}"

    def test_all_crown_ratio_files_have_schemas(self):
        missing = []
        for json_path in CFG_DIR.rglob("*crown_ratio_coefficients.json"):
            relative = str(json_path.relative_to(CFG_DIR))
            schema = _find_schema(relative)
            if schema is None:
                missing.append(relative)
        assert missing == [], f"Crown ratio files without schemas: {missing}"

    def test_all_mortality_files_have_schemas(self):
        missing = []
        for json_path in CFG_DIR.rglob("*mortality_*.json"):
            relative = str(json_path.relative_to(CFG_DIR))
            schema = _find_schema(relative)
            if schema is None:
                missing.append(relative)
        assert missing == [], f"Mortality files without schemas: {missing}"

    def test_all_taper_files_have_schemas(self):
        missing = []
        for json_path in (CFG_DIR / "taper").rglob("*.json"):
            relative = str(json_path.relative_to(CFG_DIR))
            schema = _find_schema(relative)
            if schema is None:
                missing.append(relative)
        assert missing == [], f"Taper files without schemas: {missing}"

    def test_all_small_tree_hg_files_have_schemas(self):
        missing = []
        for json_path in CFG_DIR.rglob("*small_tree_height_growth*.json"):
            relative = str(json_path.relative_to(CFG_DIR))
            schema = _find_schema(relative)
            if schema is None:
                missing.append(relative)
        for json_path in CFG_DIR.rglob("*smhgdg_coefficients.json"):
            relative = str(json_path.relative_to(CFG_DIR))
            schema = _find_schema(relative)
            if schema is None:
                missing.append(relative)
        assert missing == [], f"Small tree HG files without schemas: {missing}"

    def test_schema_registry_has_entries(self):
        assert len(SCHEMA_REGISTRY) >= 15, (
            f"Expected 15+ schema patterns, found {len(SCHEMA_REGISTRY)}"
        )


# ---------------------------------------------------------------------------
# Phase 4: Individual schema family tests (against real files)
# ---------------------------------------------------------------------------

class TestSNDiameterGrowthSchema:
    def test_validates_cleanly(self):
        with open(CFG_DIR / "sn_diameter_growth_coefficients.json") as f:
            data = json.load(f)
        warnings = validate_coefficient_file("sn_diameter_growth_coefficients.json", data)
        assert warnings == []

    def test_has_core_coefficients(self):
        with open(CFG_DIR / "sn_diameter_growth_coefficients.json") as f:
            data = json.load(f)
        assert "core_coefficients" in data
        assert "LP" in data["core_coefficients"]
        lp = data["core_coefficients"]["LP"]
        assert isinstance(lp["INTERC"], (int, float))


class TestLSDiameterGrowthSchema:
    def test_validates_cleanly(self):
        with open(CFG_DIR / "ls" / "ls_diameter_growth_coefficients.json") as f:
            data = json.load(f)
        warnings = validate_coefficient_file(
            "ls/ls_diameter_growth_coefficients.json", data
        )
        assert warnings == []


class TestNEDiameterGrowthSchema:
    def test_validates_cleanly(self):
        with open(CFG_DIR / "ne" / "ne_diameter_growth_coefficients.json") as f:
            data = json.load(f)
        warnings = validate_coefficient_file(
            "ne/ne_diameter_growth_coefficients.json", data
        )
        assert warnings == []

    def test_has_b1_b2(self):
        with open(CFG_DIR / "ne" / "ne_diameter_growth_coefficients.json") as f:
            data = json.load(f)
        first_species = next(iter(data["coefficients"]))
        assert "B1" in data["coefficients"][first_species]
        assert "B2" in data["coefficients"][first_species]


class TestPNDiameterGrowthSchema:
    def test_validates_cleanly(self):
        with open(CFG_DIR / "pn" / "pn_diameter_growth_coefficients.json") as f:
            data = json.load(f)
        warnings = validate_coefficient_file(
            "pn/pn_diameter_growth_coefficients.json", data
        )
        assert warnings == []


class TestSNBarkRatioSchema:
    def test_validates_cleanly(self):
        with open(CFG_DIR / "sn_bark_ratio_coefficients.json") as f:
            data = json.load(f)
        warnings = validate_coefficient_file("sn_bark_ratio_coefficients.json", data)
        assert warnings == []

    def test_species_have_b1_b2(self):
        with open(CFG_DIR / "sn_bark_ratio_coefficients.json") as f:
            data = json.load(f)
        for species_code, coeffs in data["species_coefficients"].items():
            assert "b1" in coeffs, f"Missing b1 for {species_code}"
            assert "b2" in coeffs, f"Missing b2 for {species_code}"


class TestNEBarkRatioSchema:
    def test_validates_cleanly(self):
        with open(CFG_DIR / "ne" / "ne_bark_ratio_coefficients.json") as f:
            data = json.load(f)
        warnings = validate_coefficient_file(
            "ne/ne_bark_ratio_coefficients.json", data
        )
        assert warnings == []

    def test_species_are_floats(self):
        with open(CFG_DIR / "ne" / "ne_bark_ratio_coefficients.json") as f:
            data = json.load(f)
        for species_code, ratio in data["species_bark_ratios"].items():
            assert isinstance(ratio, (int, float)), (
                f"{species_code}: expected float, got {type(ratio)}"
            )


class TestClarkTaperSchema:
    @pytest.mark.parametrize("region", ["r8", "r9"])
    def test_validates_cleanly(self, region):
        with open(CFG_DIR / "taper" / f"clark_{region}_coefficients.json") as f:
            data = json.load(f)
        warnings = validate_coefficient_file(
            f"taper/clark_{region}_coefficients.json", data
        )
        assert warnings == []

    def test_r8_has_taper_coefficients(self):
        with open(CFG_DIR / "taper" / "clark_r8_coefficients.json") as f:
            data = json.load(f)
        first_species = next(iter(data["species_coefficients"]))
        coeffs = data["species_coefficients"][first_species]
        for key in ("r", "c", "e", "p", "a", "b"):
            assert key in coeffs, f"Missing {key} for {first_species}"


class TestFlewellingTaperSchema:
    def test_validates_cleanly(self):
        with open(CFG_DIR / "taper" / "flewelling_coefficients.json") as f:
            data = json.load(f)
        warnings = validate_coefficient_file(
            "taper/flewelling_coefficients.json", data
        )
        assert warnings == []

    def test_species_have_jsp(self):
        with open(CFG_DIR / "taper" / "flewelling_coefficients.json") as f:
            data = json.load(f)
        for species_code, params in data["species_parameters"].items():
            assert "jsp" in params, f"Missing jsp for {species_code}"
            assert isinstance(params["jsp"], int)


class TestHeightDiameterSchemas:
    def test_sn_flat_validates(self):
        with open(CFG_DIR / "sn_height_diameter_coefficients.json") as f:
            data = json.load(f)
        warnings = validate_coefficient_file(
            "sn_height_diameter_coefficients.json", data
        )
        assert warnings == []

    def test_ls_wrapped_validates(self):
        with open(CFG_DIR / "ls" / "ls_height_diameter_coefficients.json") as f:
            data = json.load(f)
        warnings = validate_coefficient_file(
            "ls/ls_height_diameter_coefficients.json", data
        )
        assert warnings == []

    @pytest.mark.parametrize(
        "variant",
        ["cs", "ne", "pn", "op", "wc", "oc", "ws", "ca"],
    )
    def test_variant_hd_validates(self, variant):
        hd_path = CFG_DIR / variant / f"{variant}_height_diameter_coefficients.json"
        if not hd_path.exists():
            pytest.skip(f"No H-D file for {variant}")
        with open(hd_path) as f:
            data = json.load(f)
        relative = f"{variant}/{variant}_height_diameter_coefficients.json"
        warnings = validate_coefficient_file(relative, data)
        assert warnings == [], f"{relative}: {[w.message for w in warnings[:3]]}"


class TestSmallTreeHGSchemas:
    def test_sn_validates(self):
        with open(CFG_DIR / "sn_small_tree_height_growth.json") as f:
            data = json.load(f)
        warnings = validate_coefficient_file(
            "sn_small_tree_height_growth.json", data
        )
        assert warnings == []

    @pytest.mark.parametrize("variant", ["ls", "cs", "ne"])
    def test_variant_validates(self, variant):
        path = CFG_DIR / variant / f"{variant}_small_tree_height_growth.json"
        if not path.exists():
            pytest.skip(f"No small tree HG for {variant}")
        with open(path) as f:
            data = json.load(f)
        relative = f"{variant}/{variant}_small_tree_height_growth.json"
        warnings = validate_coefficient_file(relative, data)
        assert warnings == []

    def test_pn_smhgdg_validates(self):
        with open(CFG_DIR / "pn" / "pn_smhgdg_coefficients.json") as f:
            data = json.load(f)
        warnings = validate_coefficient_file(
            "pn/pn_smhgdg_coefficients.json", data
        )
        assert warnings == []


# ---------------------------------------------------------------------------
# Phase 5: Fallback logging and invalid data
# ---------------------------------------------------------------------------

class TestFallbackLogging:
    def test_missing_species_logs_warning(self, caplog):
        """Verify that requesting an unknown species logs a fallback warning."""
        from pyfvs.bark_ratio import BarkRatioModel

        with caplog.at_level(logging.WARNING, logger="pyfvs.model_base"):
            model = BarkRatioModel(species_code="ZZZZZ")

        fallback_messages = [
            r for r in caplog.records
            if "pyfvs.model_base" in r.name and "ZZZZZ" in r.message
        ]
        assert len(fallback_messages) > 0, (
            "Expected a fallback warning for unknown species 'ZZZZZ'"
        )

    def test_missing_file_logs_warning(self, caplog):
        """Verify that _get_coefficient_data logs when FileNotFoundError caught.

        Note: ConfigLoader raises FVSFileNotFoundError (not FileNotFoundError),
        so we must mock load_coefficient_file to raise a plain FileNotFoundError.
        """
        from unittest.mock import patch
        from pyfvs.model_base import ParameterizedModel

        class BrokenModel(ParameterizedModel):
            COEFFICIENT_FILE = "nonexistent_file_12345.json"
            COEFFICIENT_KEY = "species_coefficients"
            FALLBACK_PARAMETERS = {"LP": {"b1": 0.0, "b2": 1.0}}

        with caplog.at_level(logging.WARNING, logger="pyfvs.model_base"):
            with patch(
                "pyfvs.model_base.load_coefficient_file",
                side_effect=FileNotFoundError("not found"),
            ):
                model = BrokenModel(species_code="LP")

        file_warnings = [
            r for r in caplog.records
            if "not found" in r.message and "nonexistent" in r.message
        ]
        assert len(file_warnings) > 0, (
            "Expected a warning about missing coefficient file"
        )
        # Should still load fallback parameters
        assert model.coefficients.get("b1") == 0.0

    def test_empty_coefficients_logs_error(self, caplog):
        """Verify that empty coefficients logs an error."""
        from unittest.mock import patch
        from pyfvs.model_base import ParameterizedModel

        class EmptyModel(ParameterizedModel):
            COEFFICIENT_FILE = "nonexistent_file_67890.json"
            COEFFICIENT_KEY = "species_coefficients"
            FALLBACK_PARAMETERS = {}

        with caplog.at_level(logging.ERROR, logger="pyfvs.model_base"):
            with patch(
                "pyfvs.model_base.load_coefficient_file",
                side_effect=FileNotFoundError("not found"),
            ):
                model = EmptyModel(species_code="LP")

        error_messages = [
            r for r in caplog.records
            if r.levelno >= logging.ERROR and "no coefficients" in r.message.lower()
        ]
        assert len(error_messages) > 0, (
            "Expected an error when no coefficients loaded and no fallback"
        )
        assert model.coefficients == {}


class TestInvalidDataWarnings:
    def test_invalid_bark_ratio_produces_warnings(self):
        """Feed bad data to bark ratio schema, expect warnings."""
        bad_data = {
            "species_coefficients": {
                "LP": {"b1": "not_a_number", "b2": 0.91}
            }
        }
        warnings = validate_coefficient_file(
            "sn_bark_ratio_coefficients.json", bad_data
        )
        assert len(warnings) > 0
        assert any("LP" in w.field or "b1" in w.field for w in warnings)

    def test_missing_key_produces_warning(self):
        """Missing required top-level key produces a warning."""
        bad_data = {"wrong_key": {}}
        warnings = validate_coefficient_file(
            "sn_diameter_growth_coefficients.json", bad_data
        )
        assert len(warnings) > 0
        assert any("core_coefficients" in w.message for w in warnings)

    def test_strict_mode_raises(self):
        """strict=True should raise ConfigurationError."""
        from pyfvs.exceptions import ConfigurationError

        bad_data = {"wrong_key": {}}
        with pytest.raises(ConfigurationError, match="Validation failed"):
            validate_coefficient_file(
                "sn_diameter_growth_coefficients.json", bad_data, strict=True
            )

    def test_unknown_file_returns_no_warnings(self):
        """Files without a registered schema should return empty list."""
        warnings = validate_coefficient_file(
            "some_unknown_file.json", {"anything": True}
        )
        assert warnings == []

    def test_flat_hd_invalid_data(self):
        """Flat H-D schema should warn on missing P2 and Wykoff_B1."""
        bad_data = {
            "LP": {"only_garbage": 42},
            "SP": {"P2": 100.0, "P3": 3.0, "P4": -0.5},
        }
        warnings = validate_coefficient_file(
            "sn_height_diameter_coefficients.json", bad_data
        )
        # LP should produce a warning (no P2 or Wykoff_B1)
        assert len(warnings) == 1
        assert "LP" in warnings[0].message


# ---------------------------------------------------------------------------
# Schema registry tests
# ---------------------------------------------------------------------------

class TestSchemaRegistry:
    @pytest.mark.parametrize(
        "filename,expected_name",
        [
            ("sn_bark_ratio_coefficients.json", "SNBarkRatioFile"),
            ("ne/ne_bark_ratio_coefficients.json", "ConstantBarkRatioFile"),
            ("ls/ls_bark_ratio_coefficients.json", "ConstantBarkRatioFile"),
            ("pn/pn_bark_ratio_coefficients.json", "PNBarkRatioFile"),
            ("sn_diameter_growth_coefficients.json", "SNDGFile"),
            ("ls/ls_diameter_growth_coefficients.json", "StandardDGFile"),
            ("ne/ne_diameter_growth_coefficients.json", "NEDGFile"),
            ("pn/pn_diameter_growth_coefficients.json", "NumericKeyedDGFile"),
            ("wc/wc_diameter_growth_coefficients.json", "WCDGFile"),
            ("ca/ca_diameter_growth_coefficients.json", "CADGFile"),
            ("sn_height_diameter_coefficients.json", "FlatHeightDiameterFile"),
            ("op/op_height_diameter_coefficients.json", "FlatHeightDiameterFile"),
            ("ls/ls_height_diameter_coefficients.json", "HeightDiameterFile"),
            ("sn_small_tree_height_growth.json", "SmallTreeHGFile"),
            ("ls/ls_small_tree_height_growth.json", "SmallTreeHGFile"),
            ("pn/pn_smhgdg_coefficients.json", "SMHGDGFile"),
            ("taper/clark_r8_coefficients.json", "ClarkTaperFile"),
            ("taper/flewelling_coefficients.json", "FlewellingFile"),
            ("sn_crown_ratio_coefficients.json", "SNCrownRatioFile"),
            ("ls/ls_crown_ratio_coefficients.json", "StandardCrownRatioFile"),
            ("pn/pn_crown_ratio_coefficients.json", "PNCrownRatioFile"),
            ("sn_mortality_model.json", "SNMortalityFile"),
            ("ls/ls_mortality_coefficients.json", "StandardMortalityFile"),
        ],
    )
    def test_schema_lookup(self, filename, expected_name):
        schema = _find_schema(filename)
        assert schema is not None, f"No schema found for {filename}"
        assert schema.__name__ == expected_name, (
            f"Expected {expected_name}, got {schema.__name__} for {filename}"
        )

    def test_unregistered_file_returns_none(self):
        assert _find_schema("random_lookup_table.json") is None
        assert _find_schema("ecounit_coefficients_table_4_7_1_5.json") is None

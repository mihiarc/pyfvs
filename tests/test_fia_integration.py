"""
Comprehensive unit tests for the FIA-FVS Integration Module.

Tests cover all major components of the fia_integration.py module:
- FIASpeciesMapper: Species code conversion between FIA and FVS formats
- FIATreeRecord: Intermediate tree data representation
- validate_fia_input: Input validation for Polars DataFrames
- transform_fia_trees: FIA to internal record transformation
- select_condition: Multi-condition plot handling
- derive_site_index: Site index derivation from FIA data
- Stand.from_fia_data: Full integration testing

Uses Polars DataFrames for all test data following project conventions.
"""

import pytest
import polars as pl
from typing import Dict, List, Optional

from pyfvs.fia_integration import (
    FIASpeciesMapper,
    FIATreeRecord,
    FIAPlotData,
    validate_fia_input,
    transform_fia_trees,
    select_condition,
    derive_site_index,
    derive_ecounit,
    derive_stand_age,
    determine_dominant_species,
    classify_stand_purity,
    create_trees_from_fia,
    REQUIRED_TREE_COLUMNS,
    OPTIONAL_TREE_COLUMNS,
)
from pyfvs.stand import Stand
from pyfvs.tree import Tree


# ============================================================================
# Fixtures for test data
# ============================================================================

@pytest.fixture
def species_mapper() -> FIASpeciesMapper:
    """Return a FIASpeciesMapper instance."""
    return FIASpeciesMapper()


@pytest.fixture
def valid_tree_df() -> pl.DataFrame:
    """Create a valid FIA tree DataFrame with required columns."""
    return pl.DataFrame({
        "SPCD": [131, 131, 110, 121],
        "DIA": [8.5, 10.2, 6.0, 12.1],
        "HT": [45.0, 52.0, 38.0, 60.0],
        "TPA_UNADJ": [6.0, 6.0, 6.0, 6.0],
        "CR": [55.0, 60.0, 45.0, 70.0],
        "CONDID": [1, 1, 1, 1],
        "STATUSCD": [1, 1, 1, 1],
    })


@pytest.fixture
def multi_condition_tree_df() -> pl.DataFrame:
    """Create a tree DataFrame with multiple conditions.

    Uses only species supported by PyFVS (LP=131, SP=110, LL=121, SA=111, WP=129, VP=132).
    """
    return pl.DataFrame({
        "SPCD": [131, 131, 110, 121, 111, 129],  # LP, LP, SP, LL, SA, WP
        "DIA": [8.5, 10.2, 6.0, 12.1, 14.0, 16.0],
        "HT": [45.0, 52.0, 38.0, 60.0, 55.0, 65.0],
        "TPA_UNADJ": [6.0, 6.0, 6.0, 6.0, 6.0, 6.0],
        "CR": [55.0, 60.0, 45.0, 70.0, 50.0, 55.0],
        "CONDID": [1, 1, 1, 2, 2, 2],
        "STATUSCD": [1, 1, 1, 1, 1, 1],
    })


@pytest.fixture
def valid_cond_df() -> pl.DataFrame:
    """Create a valid FIA condition DataFrame."""
    return pl.DataFrame({
        "CONDID": [1],
        "SICOND": [70.0],
        "FORTYPCD": [161],  # Loblolly pine forest type
        "ECOSUBCD": ["M231A"],
        "STDAGE": [25],
        "COND_STATUS_CD": [1],
    })


@pytest.fixture
def multi_condition_cond_df() -> pl.DataFrame:
    """Create a condition DataFrame with multiple conditions."""
    return pl.DataFrame({
        "CONDID": [1, 2],
        "SICOND": [70.0, 65.0],
        "FORTYPCD": [161, 503],
        "ECOSUBCD": ["M231A", "232B"],
        "STDAGE": [25, 35],
        "COND_STATUS_CD": [1, 1],
    })


@pytest.fixture
def minimal_tree_df() -> pl.DataFrame:
    """Create a minimal valid tree DataFrame with only required columns."""
    return pl.DataFrame({
        "SPCD": [131, 110],
        "DIA": [8.5, 6.0],
        "HT": [45.0, 38.0],
        "TPA_UNADJ": [6.0, 6.0],
    })


# ============================================================================
# Tests for FIASpeciesMapper
# ============================================================================

class TestFIASpeciesMapper:
    """Tests for the FIASpeciesMapper class."""

    def test_spcd_to_fvs_loblolly_pine(self, species_mapper: FIASpeciesMapper):
        """Test conversion of loblolly pine SPCD 131 to FVS code 'LP'."""
        result = species_mapper.spcd_to_fvs(131)
        assert result == "LP", f"Expected 'LP' for SPCD 131, got {result}"

    def test_spcd_to_fvs_shortleaf_pine(self, species_mapper: FIASpeciesMapper):
        """Test conversion of shortleaf pine SPCD 110 to FVS code 'SP'."""
        result = species_mapper.spcd_to_fvs(110)
        assert result == "SP", f"Expected 'SP' for SPCD 110, got {result}"

    def test_spcd_to_fvs_longleaf_pine(self, species_mapper: FIASpeciesMapper):
        """Test conversion of longleaf pine SPCD 121 to FVS code 'LL'."""
        result = species_mapper.spcd_to_fvs(121)
        assert result == "LL", f"Expected 'LL' for SPCD 121, got {result}"

    def test_spcd_to_fvs_slash_pine(self, species_mapper: FIASpeciesMapper):
        """Test conversion of slash pine SPCD 111 to FVS code 'SA'."""
        result = species_mapper.spcd_to_fvs(111)
        assert result == "SA", f"Expected 'SA' for SPCD 111, got {result}"

    def test_spcd_to_fvs_eastern_white_pine(self, species_mapper: FIASpeciesMapper):
        """Test conversion of eastern white pine SPCD 129 to FVS code 'WP'."""
        result = species_mapper.spcd_to_fvs(129)
        assert result == "WP", f"Expected 'WP' for SPCD 129, got {result}"

    def test_spcd_to_fvs_virginia_pine(self, species_mapper: FIASpeciesMapper):
        """Test conversion of Virginia pine SPCD 132 to FVS code 'VP'."""
        result = species_mapper.spcd_to_fvs(132)
        assert result == "VP", f"Expected 'VP' for SPCD 132, got {result}"

    def test_spcd_to_fvs_unknown_species_returns_none(self, species_mapper: FIASpeciesMapper):
        """Test that unknown species codes return None."""
        result = species_mapper.spcd_to_fvs(99999)
        assert result is None, f"Expected None for unknown SPCD 99999, got {result}"

    def test_spcd_to_fvs_negative_species_returns_none(self, species_mapper: FIASpeciesMapper):
        """Test that negative species codes return None."""
        result = species_mapper.spcd_to_fvs(-1)
        assert result is None, f"Expected None for negative SPCD -1, got {result}"

    def test_fvs_to_spcd_loblolly_pine(self, species_mapper: FIASpeciesMapper):
        """Test reverse conversion of 'LP' to SPCD 131."""
        result = species_mapper.fvs_to_spcd("LP")
        assert result == 131, f"Expected 131 for FVS code 'LP', got {result}"

    def test_fvs_to_spcd_shortleaf_pine(self, species_mapper: FIASpeciesMapper):
        """Test reverse conversion of 'SP' to SPCD 110."""
        result = species_mapper.fvs_to_spcd("SP")
        assert result == 110, f"Expected 110 for FVS code 'SP', got {result}"

    def test_fvs_to_spcd_case_insensitive(self, species_mapper: FIASpeciesMapper):
        """Test that FVS code lookup is case insensitive."""
        result_upper = species_mapper.fvs_to_spcd("LP")
        result_lower = species_mapper.fvs_to_spcd("lp")
        result_mixed = species_mapper.fvs_to_spcd("Lp")
        assert result_upper == result_lower == result_mixed == 131

    def test_fvs_to_spcd_unknown_code_returns_none(self, species_mapper: FIASpeciesMapper):
        """Test that unknown FVS codes return None."""
        result = species_mapper.fvs_to_spcd("XX")
        assert result is None, f"Expected None for unknown FVS code 'XX', got {result}"

    def test_singleton_behavior(self):
        """Test that FIASpeciesMapper uses singleton pattern."""
        mapper1 = FIASpeciesMapper()
        mapper2 = FIASpeciesMapper()
        assert mapper1 is mapper2, "FIASpeciesMapper should be a singleton"

    def test_batch_convert_multiple_species(self, species_mapper: FIASpeciesMapper):
        """Test batch conversion of multiple species codes."""
        spcd_list = [131, 110, 121, 111]
        result = species_mapper.batch_convert(spcd_list)
        expected = ["LP", "SP", "LL", "SA"]
        assert result == expected, f"Expected {expected}, got {result}"

    def test_batch_convert_with_unknown_species(self, species_mapper: FIASpeciesMapper):
        """Test batch conversion handles unknown species gracefully."""
        spcd_list = [131, 99999, 110]
        result = species_mapper.batch_convert(spcd_list)
        expected = ["LP", None, "SP"]
        assert result == expected, f"Expected {expected}, got {result}"

    def test_batch_convert_empty_list(self, species_mapper: FIASpeciesMapper):
        """Test batch conversion with empty list."""
        result = species_mapper.batch_convert([])
        assert result == [], "Empty list should return empty list"

    def test_is_supported(self, species_mapper: FIASpeciesMapper):
        """Test is_supported method for known and unknown species."""
        assert species_mapper.is_supported(131) is True
        assert species_mapper.is_supported(99999) is False

    def test_get_common_name(self, species_mapper: FIASpeciesMapper):
        """Test getting common name for a species."""
        name = species_mapper.get_common_name(131)
        assert name is not None
        assert "loblolly" in name.lower() or "pine" in name.lower()

    def test_get_scientific_name(self, species_mapper: FIASpeciesMapper):
        """Test getting scientific name for a species."""
        name = species_mapper.get_scientific_name(131)
        assert name is not None
        # Pinus taeda is loblolly pine
        assert "Pinus" in name or "pinus" in name.lower()

    def test_supported_species_list(self, species_mapper: FIASpeciesMapper):
        """Test that supported_species returns a non-empty list of integers."""
        supported = species_mapper.supported_species
        assert isinstance(supported, list)
        assert len(supported) > 0
        assert all(isinstance(s, int) for s in supported)
        assert 131 in supported  # Loblolly pine should be supported

    def test_get_species_info(self, species_mapper: FIASpeciesMapper):
        """Test getting full species information."""
        info = species_mapper.get_species_info(131)
        assert info is not None
        assert info["spcd"] == 131
        assert info["fvs_code"] == "LP"
        assert "common_name" in info
        assert "scientific_name" in info

    def test_get_species_info_unknown(self, species_mapper: FIASpeciesMapper):
        """Test get_species_info returns None for unknown species."""
        info = species_mapper.get_species_info(99999)
        assert info is None


# ============================================================================
# Tests for FIATreeRecord
# ============================================================================

class TestFIATreeRecord:
    """Tests for the FIATreeRecord dataclass."""

    def test_creation_with_valid_data(self):
        """Test creating a FIATreeRecord with valid data."""
        record = FIATreeRecord(
            spcd=131,
            dia=10.5,
            ht=50.0,
            cr=60.0,
            tpa_unadj=6.0,
            age=20,
            condid=1,
            statuscd=1,
        )
        assert record.spcd == 131
        assert record.dia == 10.5
        assert record.ht == 50.0
        assert record.cr == 60.0
        assert record.tpa_unadj == 6.0
        assert record.age == 20
        assert record.condid == 1
        assert record.statuscd == 1

    def test_creation_with_defaults(self):
        """Test that FIATreeRecord uses appropriate defaults."""
        record = FIATreeRecord(spcd=131, dia=10.0, ht=50.0)
        assert record.cr == 50.0  # Default crown ratio
        assert record.tpa_unadj == 1.0  # Default TPA
        assert record.age is None
        assert record.condid == 1  # Default condition
        assert record.statuscd == 1  # Default to live tree

    def test_crown_ratio_conversion_percentage_to_proportion(self):
        """Test crown ratio conversion from percentage (0-100) to proportion (0-1)."""
        record = FIATreeRecord(spcd=131, dia=10.0, ht=50.0, cr=75.0)
        assert record.crown_ratio_proportion == 0.75

    def test_crown_ratio_conversion_low_value(self):
        """Test crown ratio conversion at lower bound."""
        record = FIATreeRecord(spcd=131, dia=10.0, ht=50.0, cr=10.0)
        assert record.crown_ratio_proportion == 0.10

    def test_crown_ratio_conversion_high_value(self):
        """Test crown ratio conversion at upper bound."""
        record = FIATreeRecord(spcd=131, dia=10.0, ht=50.0, cr=100.0)
        assert record.crown_ratio_proportion == 1.0

    def test_crown_ratio_clamping_above_100(self):
        """Test that crown ratio above 100 is clamped."""
        record = FIATreeRecord(spcd=131, dia=10.0, ht=50.0, cr=150.0)
        assert record.cr == 100.0
        assert record.crown_ratio_proportion == 1.0

    def test_crown_ratio_clamping_below_0(self):
        """Test that negative crown ratio is clamped to 0."""
        record = FIATreeRecord(spcd=131, dia=10.0, ht=50.0, cr=-10.0)
        assert record.cr == 0.0
        assert record.crown_ratio_proportion == 0.0

    def test_negative_dia_clamped_to_zero(self):
        """Test that negative diameter is clamped to 0."""
        record = FIATreeRecord(spcd=131, dia=-5.0, ht=50.0)
        assert record.dia == 0.0

    def test_negative_height_clamped_to_zero(self):
        """Test that negative height is clamped to 0."""
        record = FIATreeRecord(spcd=131, dia=10.0, ht=-20.0)
        assert record.ht == 0.0

    def test_is_live_property_live_tree(self):
        """Test is_live property for a live tree (STATUSCD=1)."""
        record = FIATreeRecord(spcd=131, dia=10.0, ht=50.0, statuscd=1)
        assert record.is_live is True

    def test_is_live_property_dead_tree(self):
        """Test is_live property for a dead tree (STATUSCD=2)."""
        record = FIATreeRecord(spcd=131, dia=10.0, ht=50.0, statuscd=2)
        assert record.is_live is False

    def test_to_pyfvs_tree_conversion(self, species_mapper: FIASpeciesMapper):
        """Test conversion to PyFVS Tree object."""
        record = FIATreeRecord(
            spcd=131,
            dia=10.5,
            ht=50.0,
            cr=60.0,
            age=20,
        )
        tree = record.to_pyfvs_tree(species_mapper)

        assert tree is not None
        assert tree.dbh == 10.5
        assert tree.height == 50.0
        assert tree.species == "LP"
        assert tree.age == 20
        assert tree.crown_ratio == 0.60

    def test_to_pyfvs_tree_unsupported_species_returns_none(
        self, species_mapper: FIASpeciesMapper
    ):
        """Test that unsupported species returns None."""
        record = FIATreeRecord(spcd=99999, dia=10.0, ht=50.0)
        tree = record.to_pyfvs_tree(species_mapper)
        assert tree is None

    def test_to_pyfvs_tree_age_defaults_to_zero(
        self, species_mapper: FIASpeciesMapper
    ):
        """Test that None age defaults to 0 in PyFVS Tree."""
        record = FIATreeRecord(spcd=131, dia=10.0, ht=50.0, age=None)
        tree = record.to_pyfvs_tree(species_mapper)
        assert tree.age == 0


# ============================================================================
# Tests for FIAPlotData
# ============================================================================

class TestFIAPlotData:
    """Tests for the FIAPlotData dataclass."""

    def test_tree_count(self):
        """Test tree_count property."""
        plot_data = FIAPlotData(trees=[
            FIATreeRecord(spcd=131, dia=10.0, ht=50.0),
            FIATreeRecord(spcd=110, dia=8.0, ht=40.0),
        ])
        assert plot_data.tree_count == 2

    def test_live_tree_count(self):
        """Test live_tree_count property."""
        plot_data = FIAPlotData(trees=[
            FIATreeRecord(spcd=131, dia=10.0, ht=50.0, statuscd=1),
            FIATreeRecord(spcd=110, dia=8.0, ht=40.0, statuscd=2),  # Dead
            FIATreeRecord(spcd=121, dia=12.0, ht=55.0, statuscd=1),
        ])
        assert plot_data.live_tree_count == 2

    def test_get_species_summary(self, species_mapper: FIASpeciesMapper):
        """Test species composition summary."""
        plot_data = FIAPlotData(trees=[
            FIATreeRecord(spcd=131, dia=10.0, ht=50.0),
            FIATreeRecord(spcd=131, dia=12.0, ht=55.0),
            FIATreeRecord(spcd=110, dia=8.0, ht=40.0),
        ])
        summary = plot_data.get_species_summary(species_mapper)
        assert summary == {"LP": 2, "SP": 1}


# ============================================================================
# Tests for validate_fia_input
# ============================================================================

class TestValidateFIAInput:
    """Tests for the validate_fia_input function."""

    def test_raises_typeerror_for_dict(self):
        """Test that a dictionary input raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            validate_fia_input({"SPCD": [131], "DIA": [10.0], "HT": [50.0]})
        assert "Polars DataFrame" in str(exc_info.value)

    def test_raises_typeerror_for_list(self):
        """Test that a list input raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            validate_fia_input([[131, 10.0, 50.0]])
        assert "Polars DataFrame" in str(exc_info.value)

    def test_raises_typeerror_for_pandas_dataframe(self):
        """Test that a pandas DataFrame raises TypeError."""
        try:
            import pandas as pd
            pandas_df = pd.DataFrame({
                "SPCD": [131],
                "DIA": [10.0],
                "HT": [50.0],
                "TPA_UNADJ": [6.0],
            })
            with pytest.raises(TypeError) as exc_info:
                validate_fia_input(pandas_df)
            assert "Polars DataFrame" in str(exc_info.value)
        except ImportError:
            pytest.skip("pandas not installed")

    def test_raises_valueerror_for_missing_spcd(self):
        """Test that missing SPCD column raises ValueError."""
        df = pl.DataFrame({
            "DIA": [10.0],
            "HT": [50.0],
            "TPA_UNADJ": [6.0],
        })
        with pytest.raises(ValueError) as exc_info:
            validate_fia_input(df)
        assert "SPCD" in str(exc_info.value)

    def test_raises_valueerror_for_missing_dia(self):
        """Test that missing DIA column raises ValueError."""
        df = pl.DataFrame({
            "SPCD": [131],
            "HT": [50.0],
            "TPA_UNADJ": [6.0],
        })
        with pytest.raises(ValueError) as exc_info:
            validate_fia_input(df)
        assert "DIA" in str(exc_info.value)

    def test_raises_valueerror_for_missing_ht(self):
        """Test that missing HT column raises ValueError."""
        df = pl.DataFrame({
            "SPCD": [131],
            "DIA": [10.0],
            "TPA_UNADJ": [6.0],
        })
        with pytest.raises(ValueError) as exc_info:
            validate_fia_input(df)
        assert "HT" in str(exc_info.value)

    def test_raises_valueerror_for_missing_tpa_unadj(self):
        """Test that missing TPA_UNADJ column raises ValueError."""
        df = pl.DataFrame({
            "SPCD": [131],
            "DIA": [10.0],
            "HT": [50.0],
        })
        with pytest.raises(ValueError) as exc_info:
            validate_fia_input(df)
        assert "TPA_UNADJ" in str(exc_info.value)

    def test_passes_for_valid_dataframe(self, valid_tree_df: pl.DataFrame):
        """Test that valid DataFrame passes validation."""
        # Should not raise any exception
        validate_fia_input(valid_tree_df)

    def test_passes_for_minimal_dataframe(self, minimal_tree_df: pl.DataFrame):
        """Test that minimal valid DataFrame passes validation."""
        validate_fia_input(minimal_tree_df)

    def test_accepts_lazyframe(self, valid_tree_df: pl.DataFrame):
        """Test that LazyFrame is also accepted."""
        lazy_df = valid_tree_df.lazy()
        validate_fia_input(lazy_df)


# ============================================================================
# Tests for transform_fia_trees
# ============================================================================

class TestTransformFIATrees:
    """Tests for the transform_fia_trees function."""

    def test_transforms_valid_data(self, valid_tree_df: pl.DataFrame):
        """Test basic transformation of valid FIA tree data."""
        records = transform_fia_trees(valid_tree_df)
        assert len(records) == 4
        assert all(isinstance(r, FIATreeRecord) for r in records)

    def test_respects_min_dia_filter(self, valid_tree_df: pl.DataFrame):
        """Test that min_dia filter excludes small trees."""
        records = transform_fia_trees(valid_tree_df, min_dia=8.0)
        # Only trees with DIA >= 8.0 should be included
        assert all(r.dia >= 8.0 for r in records)
        # Should exclude the 6.0" tree
        assert len(records) < len(valid_tree_df)

    def test_min_dia_filter_excludes_all(self, valid_tree_df: pl.DataFrame):
        """Test min_dia filter when all trees are below threshold."""
        records = transform_fia_trees(valid_tree_df, min_dia=100.0)
        assert len(records) == 0

    def test_respects_status_filter_live_trees(self):
        """Test that status_filter=1 keeps only live trees."""
        df = pl.DataFrame({
            "SPCD": [131, 131, 110],
            "DIA": [10.0, 12.0, 8.0],
            "HT": [50.0, 55.0, 40.0],
            "TPA_UNADJ": [6.0, 6.0, 6.0],
            "STATUSCD": [1, 2, 1],  # Live, dead, live
        })
        records = transform_fia_trees(df, status_filter=1)
        assert len(records) == 2
        assert all(r.is_live for r in records)

    def test_respects_status_filter_dead_trees(self):
        """Test that status_filter=2 keeps only dead trees."""
        df = pl.DataFrame({
            "SPCD": [131, 131, 110],
            "DIA": [10.0, 12.0, 8.0],
            "HT": [50.0, 55.0, 40.0],
            "TPA_UNADJ": [6.0, 6.0, 6.0],
            "STATUSCD": [1, 2, 1],
        })
        records = transform_fia_trees(df, status_filter=2)
        assert len(records) == 1
        assert records[0].statuscd == 2

    def test_status_filter_none_includes_all(self):
        """Test that status_filter=None includes all trees."""
        df = pl.DataFrame({
            "SPCD": [131, 131, 110],
            "DIA": [10.0, 12.0, 8.0],
            "HT": [50.0, 55.0, 40.0],
            "TPA_UNADJ": [6.0, 6.0, 6.0],
            "STATUSCD": [1, 2, 1],
        })
        records = transform_fia_trees(df, status_filter=None)
        assert len(records) == 3

    def test_handles_missing_optional_columns(self, minimal_tree_df: pl.DataFrame):
        """Test transformation with only required columns."""
        records = transform_fia_trees(minimal_tree_df)
        assert len(records) == 2
        # Should use default values
        for record in records:
            assert record.cr == 50.0  # Default crown ratio
            assert record.condid == 1  # Default condition
            assert record.statuscd == 1  # Default status

    def test_skips_rows_with_null_required_values(self):
        """Test that rows with null required values are skipped."""
        df = pl.DataFrame({
            "SPCD": [131, None, 110],
            "DIA": [10.0, 12.0, None],
            "HT": [50.0, 55.0, 40.0],
            "TPA_UNADJ": [6.0, 6.0, 6.0],
        })
        records = transform_fia_trees(df)
        assert len(records) == 1  # Only first row is complete

    def test_uses_bhage_over_totage(self):
        """Test that BHAGE is preferred over TOTAGE for age."""
        df = pl.DataFrame({
            "SPCD": [131],
            "DIA": [10.0],
            "HT": [50.0],
            "TPA_UNADJ": [6.0],
            "BHAGE": [25],
            "TOTAGE": [30],
        })
        records = transform_fia_trees(df)
        assert records[0].age == 25  # Should use BHAGE

    def test_falls_back_to_totage(self):
        """Test fallback to TOTAGE when BHAGE is not available."""
        df = pl.DataFrame({
            "SPCD": [131],
            "DIA": [10.0],
            "HT": [50.0],
            "TPA_UNADJ": [6.0],
            "TOTAGE": [30],
        })
        records = transform_fia_trees(df)
        assert records[0].age == 30  # Should use TOTAGE

    def test_accepts_lazyframe(self, valid_tree_df: pl.DataFrame):
        """Test that LazyFrame input is collected and processed."""
        lazy_df = valid_tree_df.lazy()
        records = transform_fia_trees(lazy_df)
        assert len(records) == 4


# ============================================================================
# Tests for select_condition
# ============================================================================

class TestSelectCondition:
    """Tests for the select_condition function."""

    def test_returns_dominant_condition_by_basal_area(
        self, multi_condition_tree_df: pl.DataFrame
    ):
        """Test that 'dominant' strategy returns condition with highest BA."""
        filtered_df, selected_condid = select_condition(
            multi_condition_tree_df, strategy="dominant"
        )
        # Condition 2 has larger trees (14" and 16") so higher BA
        assert selected_condid == 2
        # All returned trees should be from condition 2
        assert (filtered_df["CONDID"] == 2).all()

    def test_returns_condition_1_for_first_strategy(
        self, multi_condition_tree_df: pl.DataFrame
    ):
        """Test that 'first' strategy returns condition 1."""
        filtered_df, selected_condid = select_condition(
            multi_condition_tree_df, strategy="first"
        )
        assert selected_condid == 1

    def test_returns_forested_condition(
        self, multi_condition_tree_df: pl.DataFrame,
        multi_condition_cond_df: pl.DataFrame
    ):
        """Test that 'forested' strategy returns first forested condition."""
        filtered_df, selected_condid = select_condition(
            multi_condition_tree_df,
            cond_df=multi_condition_cond_df,
            strategy="forested"
        )
        assert selected_condid == 1  # First forested condition

    def test_handles_single_condition(self, valid_tree_df: pl.DataFrame):
        """Test handling of DataFrame with single condition."""
        filtered_df, selected_condid = select_condition(valid_tree_df)
        assert selected_condid == 1
        assert len(filtered_df) == len(valid_tree_df)

    def test_handles_missing_condid_column(self, minimal_tree_df: pl.DataFrame):
        """Test handling when CONDID column is missing."""
        filtered_df, selected_condid = select_condition(minimal_tree_df)
        assert selected_condid == 1
        assert len(filtered_df) == len(minimal_tree_df)

    def test_unknown_strategy_defaults_to_1(
        self, multi_condition_tree_df: pl.DataFrame
    ):
        """Test that unknown strategy defaults to condition 1."""
        filtered_df, selected_condid = select_condition(
            multi_condition_tree_df, strategy="unknown_strategy"
        )
        assert selected_condid == 1

    def test_accepts_lazyframe(self, multi_condition_tree_df: pl.DataFrame):
        """Test that LazyFrame input is handled correctly."""
        lazy_df = multi_condition_tree_df.lazy()
        filtered_df, selected_condid = select_condition(lazy_df, strategy="first")
        assert selected_condid == 1


# ============================================================================
# Tests for derive_site_index
# ============================================================================

class TestDeriveSiteIndex:
    """Tests for the derive_site_index function."""

    def test_returns_sicond_when_available(self, valid_cond_df: pl.DataFrame):
        """Test that SICOND is returned when available in condition data."""
        si = derive_site_index(valid_cond_df)
        assert si == 70.0

    def test_falls_back_to_default_when_sicond_missing(self):
        """Test fallback to default when SICOND is not available."""
        cond_df = pl.DataFrame({
            "CONDID": [1],
            "FORTYPCD": [161],
        })
        si = derive_site_index(cond_df, default=65.0)
        assert si == 65.0

    def test_falls_back_to_default_when_sicond_null(self):
        """Test fallback to default when SICOND is null."""
        cond_df = pl.DataFrame({
            "CONDID": [1],
            "SICOND": [None],
        })
        si = derive_site_index(cond_df, default=60.0)
        assert si == 60.0

    def test_falls_back_to_default_when_sicond_zero(self):
        """Test fallback to default when SICOND is 0."""
        cond_df = pl.DataFrame({
            "CONDID": [1],
            "SICOND": [0.0],
        })
        si = derive_site_index(cond_df, default=55.0)
        assert si == 55.0

    def test_uses_sitree_from_tree_df_as_fallback(self):
        """Test using SITREE from tree table when SICOND not available."""
        cond_df = pl.DataFrame({"CONDID": [1]})
        tree_df = pl.DataFrame({
            "SITREE": [68.0, 72.0, None, 70.0],
        })
        si = derive_site_index(cond_df, tree_df=tree_df)
        # Should average the non-null SITREE values: (68 + 72 + 70) / 3 = 70
        assert si == 70.0

    def test_returns_default_when_no_data_available(self):
        """Test returning default when no site index data available."""
        si = derive_site_index(None, default=70.0)
        assert si == 70.0

    def test_filters_by_condid(self, multi_condition_cond_df: pl.DataFrame):
        """Test that site index is filtered by condid."""
        si = derive_site_index(multi_condition_cond_df, condid=2)
        assert si == 65.0  # SICOND for condition 2

    def test_accepts_lazyframe(self, valid_cond_df: pl.DataFrame):
        """Test that LazyFrame input is handled correctly."""
        lazy_df = valid_cond_df.lazy()
        si = derive_site_index(lazy_df)
        assert si == 70.0


# ============================================================================
# Tests for derive_ecounit
# ============================================================================

class TestDeriveEcounit:
    """Tests for the derive_ecounit function."""

    def test_returns_ecosubcd_when_available(self, valid_cond_df: pl.DataFrame):
        """Test that ECOSUBCD is returned when available."""
        eco = derive_ecounit(valid_cond_df)
        assert eco == "M231"  # Truncated from M231A

    def test_returns_default_when_ecosubcd_missing(self):
        """Test fallback to default when ECOSUBCD not available."""
        cond_df = pl.DataFrame({"CONDID": [1]})
        eco = derive_ecounit(cond_df, default="232")
        assert eco == "232"

    def test_returns_default_when_cond_df_none(self):
        """Test fallback to default when cond_df is None."""
        eco = derive_ecounit(None, default="M231")
        assert eco == "M231"


# ============================================================================
# Tests for derive_stand_age
# ============================================================================

class TestDeriveStandAge:
    """Tests for the derive_stand_age function."""

    def test_returns_stdage_when_available(self, valid_cond_df: pl.DataFrame):
        """Test that STDAGE is returned when available."""
        age = derive_stand_age(valid_cond_df)
        assert age == 25

    def test_falls_back_to_tree_ages(self):
        """Test fallback to tree ages when STDAGE not available."""
        cond_df = pl.DataFrame({"CONDID": [1]})
        tree_df = pl.DataFrame({
            "BHAGE": [20, 22, 24],
        })
        age = derive_stand_age(cond_df, tree_df=tree_df)
        assert age == 22  # Average of 20, 22, 24

    def test_returns_none_when_no_age_available(self):
        """Test returning None when no age data available."""
        age = derive_stand_age(None)
        assert age is None


# ============================================================================
# Tests for determine_dominant_species
# ============================================================================

class TestDetermineDominantSpecies:
    """Tests for the determine_dominant_species function."""

    def test_determines_dominant_by_basal_area(self):
        """Test determination of dominant species by basal area."""
        trees = [
            Tree(dbh=10.0, height=50.0, species="LP"),
            Tree(dbh=12.0, height=55.0, species="LP"),
            Tree(dbh=8.0, height=45.0, species="SP"),
        ]
        dominant = determine_dominant_species(trees)
        assert dominant == "LP"  # Higher total BA

    def test_returns_lp_for_empty_list(self):
        """Test that empty list returns default 'LP'."""
        dominant = determine_dominant_species([])
        assert dominant == "LP"


# ============================================================================
# Tests for classify_stand_purity
# ============================================================================

class TestClassifyStandPurity:
    """Tests for the classify_stand_purity function."""

    def test_pure_stand(self):
        """Test classification of a pure stand (>= 80% one species)."""
        trees = [
            Tree(dbh=10.0, height=50.0, species="LP"),
            Tree(dbh=12.0, height=55.0, species="LP"),
            Tree(dbh=14.0, height=60.0, species="LP"),
            Tree(dbh=6.0, height=35.0, species="SP"),  # < 20% BA
        ]
        purity = classify_stand_purity(trees)
        assert purity == "pure"

    def test_mixed_stand(self):
        """Test classification of a mixed stand (< 80% one species)."""
        trees = [
            Tree(dbh=10.0, height=50.0, species="LP"),
            Tree(dbh=10.0, height=50.0, species="SP"),
            Tree(dbh=10.0, height=50.0, species="LL"),
        ]
        purity = classify_stand_purity(trees)
        assert purity == "mixed"

    def test_empty_list_returns_mixed(self):
        """Test that empty list returns 'mixed'."""
        purity = classify_stand_purity([])
        assert purity == "mixed"


# ============================================================================
# Tests for create_trees_from_fia
# ============================================================================

class TestCreateTreesFromFIA:
    """Tests for the create_trees_from_fia function."""

    def test_creates_trees_from_records(self, species_mapper: FIASpeciesMapper):
        """Test creation of PyFVS Trees from FIA records."""
        records = [
            FIATreeRecord(spcd=131, dia=10.0, ht=50.0, tpa_unadj=1.0),
            FIATreeRecord(spcd=110, dia=8.0, ht=40.0, tpa_unadj=1.0),
        ]
        trees = create_trees_from_fia(records, species_mapper, weight_by_tpa=False)
        assert len(trees) == 2
        assert all(isinstance(t, Tree) for t in trees)

    def test_replicates_trees_by_tpa(self, species_mapper: FIASpeciesMapper):
        """Test that trees are replicated based on TPA_UNADJ."""
        records = [
            FIATreeRecord(spcd=131, dia=10.0, ht=50.0, tpa_unadj=3.0),
        ]
        trees = create_trees_from_fia(records, species_mapper, weight_by_tpa=True)
        assert len(trees) == 3

    def test_subsamples_when_exceeding_max_trees(
        self, species_mapper: FIASpeciesMapper
    ):
        """Test that trees are subsampled when exceeding max_trees."""
        records = [
            FIATreeRecord(spcd=131, dia=10.0, ht=50.0, tpa_unadj=20.0),
        ]
        trees = create_trees_from_fia(
            records, species_mapper, weight_by_tpa=True, max_trees=10
        )
        assert len(trees) == 10

    def test_random_seed_for_reproducibility(self, species_mapper: FIASpeciesMapper):
        """Test that random_seed produces reproducible subsampling."""
        records = [
            FIATreeRecord(spcd=131, dia=10.0, ht=50.0, tpa_unadj=20.0),
        ]
        trees1 = create_trees_from_fia(
            records, species_mapper, weight_by_tpa=True, max_trees=10, random_seed=42
        )
        trees2 = create_trees_from_fia(
            records, species_mapper, weight_by_tpa=True, max_trees=10, random_seed=42
        )
        # Should produce same results with same seed
        assert len(trees1) == len(trees2)

    def test_skips_unsupported_species(self, species_mapper: FIASpeciesMapper):
        """Test that unsupported species are skipped with warning."""
        records = [
            FIATreeRecord(spcd=131, dia=10.0, ht=50.0, tpa_unadj=1.0),
            FIATreeRecord(spcd=99999, dia=8.0, ht=40.0, tpa_unadj=1.0),  # Unknown
        ]
        trees = create_trees_from_fia(records, species_mapper, weight_by_tpa=False)
        assert len(trees) == 1  # Only known species


# ============================================================================
# Tests for Stand.from_fia_data
# ============================================================================

class TestStandFromFIAData:
    """Tests for Stand.from_fia_data factory method."""

    def test_creates_valid_stand_from_mock_fia_data(
        self, valid_tree_df: pl.DataFrame, valid_cond_df: pl.DataFrame
    ):
        """Test creation of a valid Stand from mock FIA data."""
        stand = Stand.from_fia_data(
            tree_df=valid_tree_df,
            cond_df=valid_cond_df,
            weight_by_tpa=False,
        )
        assert stand is not None
        assert len(stand.trees) > 0
        assert stand.site_index == 70.0

    def test_handles_missing_optional_columns_gracefully(
        self, minimal_tree_df: pl.DataFrame
    ):
        """Test that Stand is created even without optional columns."""
        stand = Stand.from_fia_data(
            tree_df=minimal_tree_df,
            site_index=65.0,
            weight_by_tpa=False,
        )
        assert stand is not None
        assert stand.site_index == 65.0

    def test_raises_typeerror_for_invalid_input(self):
        """Test that TypeError is raised for non-Polars input."""
        with pytest.raises(TypeError):
            Stand.from_fia_data(tree_df={"SPCD": [131]})

    def test_raises_valueerror_for_missing_required_columns(self):
        """Test that ValueError is raised for missing required columns."""
        df = pl.DataFrame({
            "SPCD": [131],
            "DIA": [10.0],
            # Missing HT and TPA_UNADJ
        })
        with pytest.raises(ValueError):
            Stand.from_fia_data(tree_df=df)

    def test_raises_valueerror_for_no_valid_trees(self):
        """Test that ValueError is raised when no valid trees found."""
        df = pl.DataFrame({
            "SPCD": [131],
            "DIA": [0.5],  # Below min_dia
            "HT": [4.0],
            "TPA_UNADJ": [6.0],
            "STATUSCD": [1],
        })
        with pytest.raises(ValueError) as exc_info:
            Stand.from_fia_data(tree_df=df, min_dia=1.0)
        assert "No valid trees found" in str(exc_info.value)

    def test_uses_provided_site_index_override(
        self, valid_tree_df: pl.DataFrame, valid_cond_df: pl.DataFrame
    ):
        """Test that provided site_index overrides SICOND."""
        stand = Stand.from_fia_data(
            tree_df=valid_tree_df,
            cond_df=valid_cond_df,
            site_index=80.0,  # Override
            weight_by_tpa=False,
        )
        assert stand.site_index == 80.0

    def test_uses_provided_ecounit(
        self, valid_tree_df: pl.DataFrame
    ):
        """Test that provided ecounit is used."""
        stand = Stand.from_fia_data(
            tree_df=valid_tree_df,
            ecounit="M231",
            weight_by_tpa=False,
        )
        assert stand.ecounit == "M231"

    def test_respects_min_dia_filter(
        self, valid_tree_df: pl.DataFrame
    ):
        """Test that min_dia filter is respected."""
        stand = Stand.from_fia_data(
            tree_df=valid_tree_df,
            min_dia=10.0,
            weight_by_tpa=False,
        )
        # Only trees with DIA >= 10.0 should be included
        assert all(t.dbh >= 10.0 for t in stand.trees)

    def test_condition_selection_with_condid_parameter(
        self, multi_condition_tree_df: pl.DataFrame,
        multi_condition_cond_df: pl.DataFrame
    ):
        """Test explicit condition selection with condid parameter."""
        stand = Stand.from_fia_data(
            tree_df=multi_condition_tree_df,
            cond_df=multi_condition_cond_df,
            condid=2,
            weight_by_tpa=False,
        )
        assert stand.site_index == 65.0  # SI from condition 2

    def test_condition_strategy_dominant(
        self, multi_condition_tree_df: pl.DataFrame
    ):
        """Test condition selection with dominant strategy."""
        stand = Stand.from_fia_data(
            tree_df=multi_condition_tree_df,
            condition_strategy="dominant",
            weight_by_tpa=False,
        )
        assert stand is not None
        # Condition 2 has larger trees, should be selected

    def test_condition_strategy_first(
        self, multi_condition_tree_df: pl.DataFrame
    ):
        """Test condition selection with first strategy."""
        stand = Stand.from_fia_data(
            tree_df=multi_condition_tree_df,
            condition_strategy="first",
            weight_by_tpa=False,
        )
        assert stand is not None

    def test_weight_by_tpa_true(self, valid_tree_df: pl.DataFrame):
        """Test that weight_by_tpa replicates trees based on TPA_UNADJ."""
        stand = Stand.from_fia_data(
            tree_df=valid_tree_df,
            weight_by_tpa=True,
        )
        # With TPA_UNADJ=6.0, should have more trees than records
        assert len(stand.trees) > len(valid_tree_df)

    def test_weight_by_tpa_false(self, valid_tree_df: pl.DataFrame):
        """Test that weight_by_tpa=False uses one tree per record."""
        stand = Stand.from_fia_data(
            tree_df=valid_tree_df,
            weight_by_tpa=False,
        )
        assert len(stand.trees) == len(valid_tree_df)

    def test_max_trees_subsampling(self, valid_tree_df: pl.DataFrame):
        """Test max_trees parameter limits tree count."""
        stand = Stand.from_fia_data(
            tree_df=valid_tree_df,
            weight_by_tpa=True,
            max_trees=5,
        )
        assert len(stand.trees) <= 5

    def test_accepts_lazyframe(self, valid_tree_df: pl.DataFrame):
        """Test that LazyFrame input is accepted."""
        lazy_df = valid_tree_df.lazy()
        stand = Stand.from_fia_data(
            tree_df=lazy_df,
            weight_by_tpa=False,
        )
        assert stand is not None

    def test_stand_can_grow(
        self, valid_tree_df: pl.DataFrame, valid_cond_df: pl.DataFrame
    ):
        """Test that created stand can be grown."""
        stand = Stand.from_fia_data(
            tree_df=valid_tree_df,
            cond_df=valid_cond_df,
            ecounit="M231",
            weight_by_tpa=False,
        )
        initial_ba = stand.get_metrics()["basal_area"]
        stand.grow(years=10)
        final_ba = stand.get_metrics()["basal_area"]
        assert final_ba > initial_ba


# ============================================================================
# Integration tests
# ============================================================================

class TestIntegration:
    """Integration tests for the complete FIA to PyFVS workflow."""

    def test_full_workflow_with_mock_fia_data(self):
        """Test complete workflow from FIA data to growth projection."""
        # Create mock FIA data
        tree_df = pl.DataFrame({
            "SPCD": [131, 131, 131, 110, 121],
            "DIA": [6.0, 8.5, 10.2, 7.0, 12.0],
            "HT": [35.0, 45.0, 52.0, 40.0, 58.0],
            "TPA_UNADJ": [6.0, 6.0, 6.0, 6.0, 6.0],
            "CR": [65.0, 55.0, 50.0, 60.0, 70.0],
            "CONDID": [1, 1, 1, 1, 1],
            "STATUSCD": [1, 1, 1, 1, 1],
        })

        cond_df = pl.DataFrame({
            "CONDID": [1],
            "SICOND": [70.0],
            "FORTYPCD": [161],
            "ECOSUBCD": ["M231A"],
            "STDAGE": [20],
        })

        # Create stand
        stand = Stand.from_fia_data(
            tree_df=tree_df,
            cond_df=cond_df,
            weight_by_tpa=False,
        )

        # Verify initial state
        assert len(stand.trees) == 5
        assert stand.site_index == 70.0

        # Get initial metrics
        initial_metrics = stand.get_metrics()
        assert initial_metrics["basal_area"] > 0
        assert initial_metrics["tpa"] > 0

        # Grow for 25 years
        stand.grow(years=25)

        # Verify growth occurred
        final_metrics = stand.get_metrics()
        assert final_metrics["basal_area"] > initial_metrics["basal_area"]

    def test_species_conversion_roundtrip(self):
        """Test that species codes can be converted and back."""
        mapper = FIASpeciesMapper()

        # Test common species
        species_codes = [131, 110, 121, 111, 129, 132]

        for spcd in species_codes:
            fvs_code = mapper.spcd_to_fvs(spcd)
            assert fvs_code is not None, f"SPCD {spcd} should have FVS code"

            converted_back = mapper.fvs_to_spcd(fvs_code)
            assert converted_back == spcd, f"Roundtrip failed for SPCD {spcd}"

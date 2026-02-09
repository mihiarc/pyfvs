"""
Tests for the native FVS bindings subpackage.

Tests are split into two categories:
1. Always-run tests: species_map (pure data), library_loader search logic
2. Skip-when-absent tests: NativeStand, FVSBindings (require FVS shared library)
"""

import pytest

from pyfvs.native.species_map import (
    get_species_index,
    get_species_code,
    get_supported_variants,
    get_species_count,
    VARIANT_SPECIES_MAPS,
    SN_SPECIES_MAP,
    LS_SPECIES_MAP,
    PN_SPECIES_MAP,
    WC_SPECIES_MAP,
    NE_SPECIES_MAP,
    CS_SPECIES_MAP,
    OP_SPECIES_MAP,
    CA_SPECIES_MAP,
    OC_SPECIES_MAP,
    WS_SPECIES_MAP,
)
from pyfvs.native.library_loader import (
    fvs_library_available,
    get_library_info,
    clear_library_cache,
    _get_platform_extension,
    _get_search_paths,
)


# =============================================================================
# Skip marker for tests requiring the native FVS library
# =============================================================================
requires_fvs_sn = pytest.mark.skipif(
    not fvs_library_available("SN"),
    reason="FVS SN library not available (set FVS_LIB_PATH)",
)

requires_fvs_pn = pytest.mark.skipif(
    not fvs_library_available("PN"),
    reason="FVS PN library not available (set FVS_LIB_PATH)",
)

requires_fvs_ls = pytest.mark.skipif(
    not fvs_library_available("LS"),
    reason="FVS LS library not available (set FVS_LIB_PATH)",
)


# =============================================================================
# Species Map Tests (always run — no library needed)
# =============================================================================
class TestSpeciesMapData:
    """Test that species map data is complete and internally consistent."""

    def test_all_ten_variants_present(self):
        """All 10 FVS variants should have species maps."""
        expected = {"SN", "LS", "PN", "WC", "NE", "CS", "OP", "CA", "OC", "WS"}
        assert set(VARIANT_SPECIES_MAPS.keys()) == expected

    def test_get_supported_variants(self):
        """get_supported_variants returns sorted list of all 10 variants."""
        variants = get_supported_variants()
        assert len(variants) == 10
        assert variants == sorted(variants)

    @pytest.mark.parametrize("variant,expected_min", [
        ("SN", 80),
        ("LS", 60),
        ("PN", 35),
        ("WC", 35),
        ("NE", 100),
        ("CS", 90),
        ("OP", 15),
        ("CA", 45),
        ("OC", 45),
        ("WS", 40),
    ])
    def test_species_count_minimum(self, variant, expected_min):
        """Each variant should have at least the expected number of species."""
        count = get_species_count(variant)
        assert count >= expected_min, (
            f"{variant} has {count} species, expected >= {expected_min}"
        )

    def test_species_indices_are_positive(self):
        """All species indices should be positive integers."""
        for variant, species_map in VARIANT_SPECIES_MAPS.items():
            for code, index in species_map.items():
                assert isinstance(index, int), (
                    f"{variant}/{code}: index {index} is not int"
                )
                assert index > 0, (
                    f"{variant}/{code}: index {index} is not positive"
                )

    def test_species_codes_are_uppercase_two_letter(self):
        """All species codes should be 2-3 uppercase letters."""
        for variant, species_map in VARIANT_SPECIES_MAPS.items():
            for code in species_map.keys():
                assert code == code.upper(), (
                    f"{variant}/{code}: not uppercase"
                )
                assert 2 <= len(code) <= 3, (
                    f"{variant}/{code}: length {len(code)} not 2-3"
                )


class TestSpeciesMapLookup:
    """Test species code / index lookup functions."""

    def test_sn_loblolly_pine(self):
        """LP (Loblolly Pine) should map to index 13 in SN variant."""
        assert get_species_index("LP", "SN") == 13

    def test_sn_reverse_lookup(self):
        """Index 13 should map back to LP in SN variant."""
        assert get_species_code(13, "SN") == "LP"

    def test_ls_red_pine(self):
        """RN (Red Pine) should map to index 3 in LS variant."""
        assert get_species_index("RN", "LS") == 3

    def test_pn_douglas_fir(self):
        """DF (Douglas-fir) should map to index 16 in PN variant."""
        assert get_species_index("DF", "PN") == 16

    def test_ne_red_maple(self):
        """RM (Red Maple) should map to index 26 in NE variant."""
        assert get_species_index("RM", "NE") == 26

    def test_cs_white_oak(self):
        """WO (White Oak) should map to index 47 in CS variant."""
        assert get_species_index("WO", "CS") == 47

    def test_op_douglas_fir(self):
        """DF (Douglas-fir) should map to index 16 in OP variant."""
        assert get_species_index("DF", "OP") == 16

    def test_ca_douglas_fir(self):
        """DF (Douglas-fir) should map to index 7 in CA variant."""
        assert get_species_index("DF", "CA") == 7

    def test_oc_douglas_fir(self):
        """DF (Douglas-fir) should map to index 7 in OC variant."""
        assert get_species_index("DF", "OC") == 7

    def test_ws_douglas_fir(self):
        """DF (Douglas-fir) should map to index 2 in WS variant."""
        assert get_species_index("DF", "WS") == 2

    def test_case_insensitive_lookup(self):
        """Species code lookup should be case-insensitive."""
        assert get_species_index("lp", "SN") == get_species_index("LP", "SN")
        assert get_species_index("df", "pn") == get_species_index("DF", "PN")

    def test_invalid_species_raises(self):
        """Invalid species code should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            get_species_index("ZZ", "SN")

    def test_invalid_variant_raises(self):
        """Invalid variant code should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown variant"):
            get_species_index("LP", "XX")

    def test_invalid_index_raises(self):
        """Invalid species index should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            get_species_code(9999, "SN")

    def test_roundtrip_all_variants(self):
        """Every species should roundtrip: code -> index -> code."""
        for variant, species_map in VARIANT_SPECIES_MAPS.items():
            # Build reverse map to handle duplicate indices
            index_to_code = {}
            for code, index in species_map.items():
                if index not in index_to_code:
                    index_to_code[index] = code

            for code, index in species_map.items():
                recovered = get_species_code(index, variant)
                assert recovered in species_map, (
                    f"{variant}: index {index} -> {recovered} not in species map"
                )
                assert species_map[recovered] == index, (
                    f"{variant}: roundtrip failed for {code} -> {index} -> {recovered}"
                )


class TestSpeciesMapCrossVariant:
    """Test species that appear in multiple variants have correct mappings."""

    def test_douglas_fir_varies_by_variant(self):
        """DF should have different indices across variant families."""
        pn_idx = PN_SPECIES_MAP.get("DF")
        op_idx = OP_SPECIES_MAP.get("DF")
        ca_idx = CA_SPECIES_MAP.get("DF")
        ws_idx = WS_SPECIES_MAP.get("DF")

        # PN/OP both use PNW JSP (DF=16), CA has DF=7, WS has DF=2
        assert pn_idx == op_idx  # Both PNW variants share JSP
        assert pn_idx != ca_idx  # CA has different species order
        assert ca_idx != ws_idx  # WS has different species order

    def test_pn_wc_share_species_order(self):
        """PN and WC should share the same species ordering."""
        # Both are PNW variants from same Fortran source
        common_species = set(PN_SPECIES_MAP.keys()) & set(WC_SPECIES_MAP.keys())
        for code in common_species:
            assert PN_SPECIES_MAP[code] == WC_SPECIES_MAP[code], (
                f"PN/WC differ for {code}: "
                f"PN={PN_SPECIES_MAP[code]} vs WC={WC_SPECIES_MAP[code]}"
            )


# =============================================================================
# Library Loader Tests (always run — tests search logic, not library loading)
# =============================================================================
class TestLibraryLoader:
    """Test library loader search path and platform detection logic."""

    def test_platform_extension(self):
        """Platform extension should be .dylib, .so, or .dll."""
        ext = _get_platform_extension()
        assert ext in (".dylib", ".so", ".dll")

    def test_search_paths_include_home_fvs(self):
        """Search paths should include ~/.fvs/lib/."""
        paths = _get_search_paths()
        path_strs = [str(p) for p in paths]
        assert any(".fvs/lib" in p for p in path_strs)

    def test_library_info_structure(self):
        """get_library_info should return a well-formed dict."""
        info = get_library_info("SN")
        assert "variant" in info
        assert "available" in info
        assert "platform" in info
        assert "search_paths" in info
        assert info["variant"] == "SN"
        assert isinstance(info["available"], bool)
        assert isinstance(info["search_paths"], list)

    def test_fvs_library_available_returns_bool(self):
        """fvs_library_available should return a boolean."""
        result = fvs_library_available("SN")
        assert isinstance(result, bool)


# =============================================================================
# Native FVS Integration Tests (skip when library absent)
# =============================================================================
@requires_fvs_sn
class TestNativeStandSN:
    """Integration tests for NativeStand with the SN variant.

    Note: FVS uses Fortran COMMON blocks for global state. The library
    cache must be cleared between tests to avoid state contamination.
    """

    @pytest.fixture(autouse=True)
    def _clear_fvs_state(self):
        """Clear the library cache before each test for clean Fortran state."""
        clear_library_cache()

    def test_native_stand_init(self):
        """NativeStand should initialize without error."""
        from pyfvs.native import NativeStand

        with NativeStand(variant="SN") as ns:
            ns.initialize_planted(500, 70, "LP")
            assert ns._initialized

    def test_native_stand_grow(self):
        """NativeStand should run a simulation and produce metrics."""
        from pyfvs.native import NativeStand

        with NativeStand(variant="SN") as ns:
            ns.initialize_planted(500, 70, "LP")
            ns.grow(50)
            metrics = ns.get_metrics()

            # 50 years of LP growth at SI=70 should produce substantial metrics
            assert metrics["tpa"] > 100
            assert metrics["basal_area"] > 50
            assert metrics["qmd"] > 5
            assert metrics["top_height"] > 50

    def test_native_stand_yield_table(self):
        """NativeStand should produce a multi-cycle yield table."""
        from pyfvs.native import NativeStand

        with NativeStand(variant="SN") as ns:
            ns.initialize_planted(500, 70, "LP")
            ns.grow(50)
            yield_table = ns.get_yield_table()

            # 50 years / 10-year cycles = 5 cycles + initial = 6 rows
            assert len(yield_table) >= 3  # At least initial + 2 cycles
            for row in yield_table:
                assert "year" in row
                assert "begin_tpa" in row

    def test_native_stand_tree_list(self):
        """NativeStand should produce a tree list."""
        from pyfvs.native import NativeStand

        with NativeStand(variant="SN") as ns:
            ns.initialize_planted(500, 70, "LP")
            ns.grow(50)
            tree_list = ns.get_tree_list()

            assert len(tree_list) > 0
            for tree in tree_list:
                assert "dbh" in tree
                assert "height" in tree
                assert tree["dbh"] > 0


@requires_fvs_pn
class TestNativeStandPN:
    """Integration tests for NativeStand with the PN variant."""

    @pytest.fixture(autouse=True)
    def _clear_fvs_state(self):
        clear_library_cache()

    def test_pn_douglas_fir_growth(self):
        """PN variant should grow Douglas-fir with reasonable metrics."""
        from pyfvs.native import NativeStand

        with NativeStand(variant="PN") as ns:
            ns.initialize_planted(400, 120, "DF")
            ns.grow(50)
            metrics = ns.get_metrics()

            assert metrics["tpa"] > 0
            assert metrics["basal_area"] > 50
            assert metrics["qmd"] > 5


@requires_fvs_ls
class TestNativeStandLS:
    """Integration tests for NativeStand with the LS variant."""

    @pytest.fixture(autouse=True)
    def _clear_fvs_state(self):
        clear_library_cache()

    def test_ls_red_pine_growth(self):
        """LS variant should grow Red Pine with reasonable metrics."""
        from pyfvs.native import NativeStand

        with NativeStand(variant="LS") as ns:
            ns.initialize_planted(500, 65, "RN")
            ns.grow(50)
            metrics = ns.get_metrics()

            assert metrics["tpa"] > 0
            assert metrics["basal_area"] > 50


@requires_fvs_sn
class TestFVSBindings:
    """Low-level FVSBindings integration tests."""

    @pytest.fixture(autouse=True)
    def _clear_fvs_state(self):
        clear_library_cache()

    def test_bindings_init(self):
        """FVSBindings should initialize with the SN variant."""
        from pyfvs.native import FVSBindings

        bindings = FVSBindings("SN")
        assert bindings.variant == "SN"


# =============================================================================
# Package import tests (always run)
# =============================================================================
class TestNativePackageImport:
    """Test that the native package imports cleanly."""

    def test_import_native(self):
        """Importing pyfvs.native should never fail."""
        import pyfvs.native
        assert hasattr(pyfvs.native, "fvs_library_available")
        assert hasattr(pyfvs.native, "get_species_index")

    def test_import_species_map(self):
        """Importing species_map should never fail."""
        from pyfvs.native import species_map
        assert hasattr(species_map, "VARIANT_SPECIES_MAPS")

    def test_import_library_loader(self):
        """Importing library_loader should never fail."""
        from pyfvs.native import library_loader
        assert hasattr(library_loader, "fvs_library_available")

    def test_fvs_native_error_importable(self):
        """FVSNativeError should be importable from pyfvs."""
        from pyfvs import FVSNativeError
        assert issubclass(FVSNativeError, Exception)

    def test_native_module_on_pyfvs(self):
        """pyfvs should expose the native subpackage."""
        import pyfvs
        assert hasattr(pyfvs, "native")

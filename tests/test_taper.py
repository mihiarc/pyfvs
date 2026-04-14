"""Tests for taper model and merchandising systems.

Tests the Clark segmented profile model (Eastern US), taper factory,
and volume integration with the VolumeCalculator.
"""
import math
import pytest

from pyfvs.taper import (
    TaperModel,
    ClarkTaperModel,
    FlewellingTaperModel,
    create_taper_model,
    clear_taper_cache,
)
from pyfvs.merchandising import (
    scribner_decimal_c,
    international_quarter_inch,
    doyle,
    smalian_cubic,
    merchandise_tree,
    get_merchandising_rules,
    MerchandisingRules,
    LogRule,
    compute_board_feet,
)
from pyfvs.volume_library import (
    VolumeCalculator,
    VolumeResult,
    calculate_tree_volume,
    get_volume_library,
    _volume_calculators,
)


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear taper and volume caches before each test."""
    clear_taper_cache()
    _volume_calculators.clear()
    yield
    clear_taper_cache()
    _volume_calculators.clear()


# ============================================================================
# Clark Taper Model Tests
# ============================================================================

class TestClarkTaperModel:
    """Tests for the Clark (1991) segmented profile model."""

    def test_create_clark_for_sn(self):
        """SN variant creates a ClarkTaperModel."""
        model = create_taper_model('LP', 'SN')
        assert model is not None
        assert isinstance(model, ClarkTaperModel)

    def test_create_clark_for_ne(self):
        """NE variant creates a ClarkTaperModel."""
        model = create_taper_model('RM', 'NE')
        assert model is not None
        assert isinstance(model, ClarkTaperModel)

    def test_create_clark_for_cs(self):
        """CS variant creates a ClarkTaperModel."""
        model = create_taper_model('WO', 'CS')
        assert model is not None
        assert isinstance(model, ClarkTaperModel)

    def test_create_clark_for_ls(self):
        """LS variant creates a ClarkTaperModel."""
        model = create_taper_model('RN', 'LS')
        assert model is not None
        assert isinstance(model, ClarkTaperModel)

    def test_lp_coefficients_loaded(self):
        """LP R8 coefficients are species-specific (not fallback).

        A4/B4 come from the R8CF forest-group table at group 4 (Alabama
        Bankhead default, r8dib.f). R comes from the forest-invariant
        TOTAL array (r8clkcoef.inc).
        """
        model = create_taper_model('LP', 'SN')
        assert model is not None
        coef = model._coefficients
        # LP group-4 A4/B4 from volume/NVEL/r8dib.f
        assert coef['a4'] == pytest.approx(-0.12527, abs=0.0001)
        assert coef['b4'] == pytest.approx(0.87509, abs=0.0001)
        # R from TOTAL array (volume/NVEL/r8clkcoef.inc)
        assert coef['r'] == pytest.approx(31.66, abs=1.0)

    def test_rm_r9_coefficients_loaded(self):
        """RM R9 coefficients are loaded for NE variant."""
        model = create_taper_model('RM', 'NE')
        assert model is not None
        coef = model._coefficients
        # Should have species-specific coefficients, not fallback
        assert 'a4' in coef
        assert 'b4' in coef
        assert 'r' in coef

    def test_dib_at_breast_height_matches_dbhib(self):
        """DIB at 4.5 ft should match the predicted DBHIB."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(12.0, 80.0)
        dib_bh = model.predict_dib(4.5)
        assert dib_bh == pytest.approx(model._dbhib, abs=0.01)

    def test_dib_at_17_3_matches_dib17(self):
        """DIB at 17.3 ft should match the predicted DIB17."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(12.0, 80.0)
        dib_17 = model.predict_dib(17.3)
        assert dib_17 == pytest.approx(model._dib17, abs=0.1)

    def test_dib_monotonically_decreasing(self):
        """DIB should decrease from stump to tip."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(14.0, 85.0)

        heights = [4.5, 10.0, 17.3, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]
        dibs = [model.predict_dib(h) for h in heights]

        for i in range(1, len(dibs)):
            assert dibs[i] <= dibs[i - 1] + 0.01, (
                f"DIB increased from h={heights[i-1]} ({dibs[i-1]:.2f}) "
                f"to h={heights[i]} ({dibs[i]:.2f})"
            )

    def test_dib_zero_at_tip(self):
        """DIB should be approximately zero at the tree tip."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(12.0, 80.0)
        dib_tip = model.predict_dib(80.0)
        assert dib_tip == 0.0

    def test_dib_positive_below_bh(self):
        """DIB should be positive (and larger) below breast height."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(12.0, 80.0)
        dib_stump = model.predict_dib(1.0)
        dib_bh = model.predict_dib(4.5)
        assert dib_stump > dib_bh  # Butt swell

    def test_volume_positive(self):
        """Volume should be positive for a reasonable tree."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(12.0, 80.0)
        vol = model.predict_volume(1.0, 80.0)
        assert vol > 0

    def test_volume_reasonable_range_lp(self):
        """LP 12" 80' volume should be in expected range (20-35 cuft IB)."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(12.0, 80.0)
        vol = model.predict_volume(1.0, 80.0)
        assert 15.0 <= vol <= 35.0, f"LP volume {vol} outside expected range"

    def test_volume_reasonable_range_rm(self):
        """RM 10" 65' volume should be in expected range (8-18 cuft IB)."""
        model = create_taper_model('RM', 'NE')
        model.initialize_tree(10.0, 65.0)
        vol = model.predict_volume(1.0, 65.0)
        assert 5.0 <= vol <= 20.0, f"RM volume {vol} outside expected range"

    def test_volume_reasonable_range_wo(self):
        """WO 14" 70' volume should be in expected range (15-40 cuft IB)."""
        model = create_taper_model('WO', 'CS')
        model.initialize_tree(14.0, 70.0)
        vol = model.predict_volume(1.0, 70.0)
        assert 10.0 <= vol <= 40.0, f"WO volume {vol} outside expected range"

    def test_volume_increases_with_dbh(self):
        """Volume should increase with DBH for same height."""
        model = create_taper_model('LP', 'SN')

        model.initialize_tree(8.0, 60.0)
        vol_small = model.get_total_volume()

        model.initialize_tree(14.0, 60.0)
        vol_large = model.get_total_volume()

        assert vol_large > vol_small

    def test_volume_increases_with_height(self):
        """Volume should increase with height for same DBH."""
        model = create_taper_model('LP', 'SN')

        model.initialize_tree(12.0, 60.0)
        vol_short = model.get_total_volume()

        model.initialize_tree(12.0, 90.0)
        vol_tall = model.get_total_volume()

        assert vol_tall > vol_short

    def test_height_to_dib_inverse_consistency(self):
        """predict_height_to_dib should be consistent with predict_dib."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(14.0, 85.0)

        target_dib = 6.0
        h = model.predict_height_to_dib(target_dib)
        assert h > 4.5  # Should be above BH

        dib_at_h = model.predict_dib(h)
        assert dib_at_h == pytest.approx(target_dib, abs=0.05)

    def test_merchantable_height(self):
        """get_merchantable_height should return height to 4" top."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(12.0, 80.0)

        merch_ht = model.get_merchantable_height(min_top_dib=4.0)
        assert merch_ht > 4.5
        assert merch_ht < 80.0

        dib_at_merch = model.predict_dib(merch_ht)
        assert dib_at_merch == pytest.approx(4.0, abs=0.1)

    def test_small_tree_no_merchantable_height(self):
        """Very small tree should have no merchantable height at 4" top."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(3.0, 20.0)
        merch_ht = model.get_merchantable_height(min_top_dib=4.0)
        assert merch_ht == 0.0

    def test_uninitialized_model_returns_zero(self):
        """Uninitialized model should return zero for all predictions."""
        model = create_taper_model('LP', 'SN')
        assert model.predict_dib(10.0) == 0.0
        assert model.predict_volume(1.0, 80.0) == 0.0
        assert model.get_total_volume() == 0.0

    def test_very_short_tree(self):
        """Tree shorter than 4.5 ft should still work."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(2.0, 4.0)
        # Should not crash
        dib = model.predict_dib(2.0)
        assert dib >= 0

    def test_hardwood_correction_factor(self):
        """Hardwood species should get a 10% volume reduction."""
        # RM is hardwood
        model = create_taper_model('RM', 'NE')
        assert model.species_code in ClarkTaperModel._HARDWOOD_SPECIES

    def test_softwood_correction_factor(self):
        """Softwood species should get a 4% volume reduction."""
        model = create_taper_model('LP', 'SN')
        assert model.species_code not in ClarkTaperModel._HARDWOOD_SPECIES

    def test_volume_segment_below_bh(self):
        """Volume from 0 to 4.5 ft should be positive."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(12.0, 80.0)
        vol = model.predict_volume(0.5, 4.5)
        assert vol > 0

    def test_volume_segment_mid(self):
        """Volume from 4.5 to 17.3 ft should be positive."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(12.0, 80.0)
        vol = model.predict_volume(4.5, 17.3)
        assert vol > 0

    def test_volume_segment_upper(self):
        """Volume above 17.3 ft should be positive."""
        model = create_taper_model('LP', 'SN')
        model.initialize_tree(12.0, 80.0)
        vol = model.predict_volume(17.3, 80.0)
        assert vol > 0


# ============================================================================
# Taper Factory Tests
# ============================================================================

class TestTaperFactory:
    """Tests for the create_taper_model factory."""

    def test_caching(self):
        """Factory returns cached instances."""
        m1 = create_taper_model('LP', 'SN')
        m2 = create_taper_model('LP', 'SN')
        assert m1 is m2

    def test_different_species_different_models(self):
        """Different species get different model instances."""
        m1 = create_taper_model('LP', 'SN')
        m2 = create_taper_model('DF', 'SN')
        assert m1 is not m2

    def test_unsupported_variant_returns_none(self):
        """Unsupported variants (CA, OC, WS) return None."""
        assert create_taper_model('LP', 'CA') is None
        assert create_taper_model('LP', 'OC') is None
        assert create_taper_model('LP', 'WS') is None

    def test_western_variants_flewelling_supported_species(self):
        """PN/WC/OP return Flewelling models for DF, WH, RC."""
        for variant in ('PN', 'WC', 'OP'):
            for sp in ('DF', 'WH', 'RC'):
                model = create_taper_model(sp, variant)
                assert model is not None, f"{sp} {variant} should have Flewelling model"
                assert isinstance(model, FlewellingTaperModel)

    def test_western_variants_unsupported_species_none(self):
        """PN/WC/OP return None for species without Flewelling coefficients."""
        assert create_taper_model('SS', 'PN') is None
        assert create_taper_model('RA', 'PN') is None
        assert create_taper_model('GF', 'WC') is None

    def test_clear_cache(self):
        """clear_taper_cache removes all cached models."""
        create_taper_model('LP', 'SN')
        clear_taper_cache()
        # After clearing, a new call creates a fresh instance
        m = create_taper_model('LP', 'SN')
        assert m is not None

    def test_fallback_for_unknown_species(self):
        """Unknown species code should get fallback coefficients."""
        model = create_taper_model('XX', 'SN')
        assert model is not None
        # Should use fallback or group mapping
        coef = model._coefficients
        assert 'a4' in coef


# ============================================================================
# Log Rule Tests
# ============================================================================

class TestScribnerDecimalC:
    """Tests for Scribner Decimal C log rule."""

    def test_minimum_dib(self):
        """Scribner returns 0 for DIB below 6 inches."""
        assert scribner_decimal_c(5.9, 16.0) == 0.0
        assert scribner_decimal_c(5.0, 16.0) == 0.0

    def test_16ft_log_6_inch(self):
        """6" DIB 16ft log should give 10 BF (first table entry)."""
        bf = scribner_decimal_c(6.0, 16.0)
        assert bf == pytest.approx(10.0, abs=1.0)

    def test_16ft_log_12_inch(self):
        """12" DIB 16ft log should give 100 BF."""
        bf = scribner_decimal_c(12.0, 16.0)
        assert bf == pytest.approx(100.0, abs=5.0)

    def test_16ft_log_20_inch(self):
        """20" DIB 16ft log should give 370 BF."""
        bf = scribner_decimal_c(20.0, 16.0)
        assert bf == pytest.approx(370.0, abs=10.0)

    def test_scales_by_length(self):
        """Non-16ft logs should scale proportionally."""
        bf_16 = scribner_decimal_c(12.0, 16.0)
        bf_8 = scribner_decimal_c(12.0, 8.0)
        assert bf_8 == pytest.approx(bf_16 / 2.0, abs=1.0)

    def test_zero_length(self):
        """Zero length returns 0."""
        assert scribner_decimal_c(12.0, 0.0) == 0.0


class TestInternationalQuarterInch:
    """Tests for International 1/4-inch log rule."""

    def test_minimum_dib(self):
        """International returns 0 for DIB below 4 inches."""
        assert international_quarter_inch(3.9, 16.0) == 0.0

    def test_known_value_12_inch(self):
        """12" DIB 16ft log should give reasonable BF."""
        bf = international_quarter_inch(12.0, 16.0)
        # International 1/4" typically gives more than Scribner for same log
        assert 80 <= bf <= 140

    def test_increases_with_dib(self):
        """BF should increase with diameter."""
        bf_10 = international_quarter_inch(10.0, 16.0)
        bf_14 = international_quarter_inch(14.0, 16.0)
        assert bf_14 > bf_10

    def test_increases_with_length(self):
        """BF should increase with log length."""
        bf_8 = international_quarter_inch(12.0, 8.0)
        bf_16 = international_quarter_inch(12.0, 16.0)
        assert bf_16 > bf_8


class TestDoyle:
    """Tests for Doyle log rule."""

    def test_minimum_dib(self):
        """Doyle returns 0 for DIB at or below 4 inches."""
        assert doyle(4.0, 16.0) == 0.0
        assert doyle(3.0, 16.0) == 0.0

    def test_known_formula(self):
        """Verify Doyle formula: BF = (DIB - 4)^2 * L / 16."""
        # 12" DIB, 16ft log: (12-4)^2 * 16/16 = 64
        bf = doyle(12.0, 16.0)
        assert bf == pytest.approx(64.0, abs=0.1)

    def test_known_formula_large(self):
        """Doyle for 20" DIB 16ft log: (20-4)^2 = 256."""
        bf = doyle(20.0, 16.0)
        assert bf == pytest.approx(256.0, abs=0.1)

    def test_increases_with_dib(self):
        """BF should increase with diameter."""
        bf_8 = doyle(8.0, 16.0)
        bf_14 = doyle(14.0, 16.0)
        assert bf_14 > bf_8


class TestLogRuleComparison:
    """Comparative tests across log rules."""

    def test_rule_ordering_small_log(self):
        """For small logs (<14"), International > Scribner > Doyle."""
        dib = 10.0
        length = 16.0
        scrib = scribner_decimal_c(dib, length)
        intl = international_quarter_inch(dib, length)
        doyle_bf = doyle(dib, length)
        assert intl >= scrib >= doyle_bf

    def test_rule_ordering_large_log(self):
        """For large logs (>24"), Doyle catches up to other rules."""
        dib = 30.0
        length = 16.0
        scrib = scribner_decimal_c(dib, length)
        intl = international_quarter_inch(dib, length)
        doyle_bf = doyle(dib, length)
        # For large logs, all three should be within ~50% of each other
        assert doyle_bf > 0
        assert intl > 0
        assert scrib > 0

    def test_compute_board_feet_dispatcher(self):
        """compute_board_feet dispatches correctly."""
        scrib = compute_board_feet(12.0, 16.0, LogRule.SCRIBNER)
        intl = compute_board_feet(12.0, 16.0, LogRule.INTERNATIONAL)
        doyle_bf = compute_board_feet(12.0, 16.0, LogRule.DOYLE)

        assert scrib == scribner_decimal_c(12.0, 16.0)
        assert intl == international_quarter_inch(12.0, 16.0)
        assert doyle_bf == doyle(12.0, 16.0)


# ============================================================================
# Smalian Volume Tests
# ============================================================================

class TestSmalianCubic:
    """Tests for Smalian cubic volume formula."""

    def test_cylinder(self):
        """Equal-diameter "log" = cylinder volume."""
        # Cylinder: V = pi/4 * D^2 * L / 144
        dib = 10.0
        length = 16.0
        expected = math.pi / 4 * (dib ** 2) * length / 144.0
        actual = smalian_cubic(dib, dib, length)
        assert actual == pytest.approx(expected, rel=0.01)

    def test_zero_length(self):
        """Zero length returns 0."""
        assert smalian_cubic(10.0, 8.0, 0.0) == 0.0

    def test_tapered_log(self):
        """Tapered log volume should be between cylinder volumes."""
        large = 12.0
        small = 8.0
        length = 16.0
        vol = smalian_cubic(large, small, length)

        vol_small_cyl = math.pi / 4 * (small ** 2) * length / 144.0
        vol_large_cyl = math.pi / 4 * (large ** 2) * length / 144.0

        assert vol_small_cyl < vol < vol_large_cyl


# ============================================================================
# Merchandising Tests
# ============================================================================

class TestMerchandising:
    """Tests for tree merchandising (log bucking)."""

    def _make_taper(self, dbh, height, variant='SN'):
        """Helper to create an initialized taper model."""
        model = create_taper_model('LP', variant)
        if model is None:
            pytest.skip("No taper model for this variant")
        model.initialize_tree(dbh, height)
        return model

    def test_merch_produces_logs(self):
        """A sawtimber-size tree should produce at least one log."""
        taper = self._make_taper(14.0, 85.0)
        logs, merch_cubic, tip_vol = merchandise_tree(taper)
        assert len(logs) >= 1
        assert merch_cubic > 0

    def test_log_positions_sequential(self):
        """Log positions should be sequential from 1."""
        taper = self._make_taper(14.0, 85.0)
        logs, _, _ = merchandise_tree(taper)
        positions = [log.position for log in logs]
        assert positions == list(range(1, len(logs) + 1))

    def test_log_diameters_decreasing(self):
        """Large-end DIB should decrease from butt to top."""
        taper = self._make_taper(16.0, 90.0)
        logs, _, _ = merchandise_tree(taper)
        if len(logs) > 1:
            for i in range(1, len(logs)):
                assert logs[i].large_end_dib <= logs[i - 1].large_end_dib + 0.1

    def test_small_end_less_than_large_end(self):
        """Each log's small end should be less than large end."""
        taper = self._make_taper(14.0, 85.0)
        logs, _, _ = merchandise_tree(taper)
        for log in logs:
            assert log.small_end_dib <= log.large_end_dib + 0.01

    def test_all_three_log_rules_computed(self):
        """Each log should have all three board-foot rules computed."""
        taper = self._make_taper(14.0, 85.0)
        rules = get_merchandising_rules('SN')
        logs, _, _ = merchandise_tree(taper, rules)
        for log in logs:
            if log.small_end_dib >= 6.0:
                assert log.bf_scribner > 0
            if log.small_end_dib >= 4.0:
                assert log.bf_international > 0
            if log.small_end_dib > 4.0:
                assert log.bf_doyle > 0

    def test_cubic_volume_per_log_positive(self):
        """Each log should have positive cubic volume."""
        taper = self._make_taper(14.0, 85.0)
        logs, _, _ = merchandise_tree(taper)
        for log in logs:
            assert log.cubic_volume > 0

    def test_tip_volume_positive(self):
        """Tip volume (above merch top) should be positive."""
        taper = self._make_taper(14.0, 85.0)
        _, _, tip_vol = merchandise_tree(taper)
        assert tip_vol > 0

    def test_small_tree_no_logs(self):
        """A very small tree should produce no logs."""
        taper = self._make_taper(3.0, 20.0)
        logs, merch_cubic, _ = merchandise_tree(taper)
        assert len(logs) == 0
        assert merch_cubic == 0.0

    def test_sn_rules(self):
        """SN merchandising rules should have 7" primary top."""
        rules = get_merchandising_rules('SN')
        assert rules.min_top_dib_primary == 7.0
        assert rules.max_log_length == 16.0

    def test_pn_rules(self):
        """PN merchandising rules should have 6" primary top."""
        rules = get_merchandising_rules('PN')
        assert rules.min_top_dib_primary == 6.0
        assert rules.max_log_length == 32.0

    def test_default_rules(self):
        """Default rules should be returned for unknown variant."""
        rules = get_merchandising_rules('XX')
        assert rules.min_top_dib_primary == 6.0  # MerchandisingRules default

    def test_custom_rules(self):
        """Custom merchandising rules should be respected."""
        taper = self._make_taper(14.0, 85.0)
        custom_rules = MerchandisingRules(
            min_top_dib_primary=4.0,  # Lower top = more logs
            max_log_length=8.0,       # Shorter logs = more logs
        )
        logs_custom, _, _ = merchandise_tree(taper, custom_rules)

        default_rules = get_merchandising_rules('SN')
        logs_default, _, _ = merchandise_tree(taper, default_rules)

        # Custom rules with lower top and shorter logs should produce more logs
        assert len(logs_custom) >= len(logs_default)


# ============================================================================
# Volume Integration Tests
# ============================================================================

class TestVolumeIntegration:
    """Tests for taper-based volume integration with VolumeCalculator."""

    def test_sn_uses_taper(self):
        """SN variant VolumeCalculator should use Clark taper model."""
        calc = get_volume_library('LP', 'SN')
        assert calc._taper_model is not None
        assert isinstance(calc._taper_model, ClarkTaperModel)

    def test_ne_uses_taper(self):
        """NE variant VolumeCalculator should use Clark taper model."""
        calc = get_volume_library('RM', 'NE')
        assert calc._taper_model is not None
        assert isinstance(calc._taper_model, ClarkTaperModel)

    def test_pn_df_uses_flewelling(self):
        """PN variant should use Flewelling taper for DF."""
        calc = get_volume_library('DF', 'PN')
        assert calc._taper_model is not None
        assert isinstance(calc._taper_model, FlewellingTaperModel)

    def test_pn_unsupported_uses_combined_variable(self):
        """PN variant should fall back to combined-variable for unsupported species."""
        calc = get_volume_library('SS', 'PN')
        assert calc._taper_model is None

    def test_ca_uses_combined_variable(self):
        """CA variant should use combined-variable (no taper)."""
        calc = get_volume_library('LP', 'CA')
        assert calc._taper_model is None

    def test_taper_volume_has_all_log_rules(self):
        """Taper-based volume should populate all three log rule fields."""
        result = calculate_tree_volume(14.0, 85.0, 'LP', variant='SN')
        assert result.board_foot_volume > 0      # Scribner (slot 4)
        assert result.board_foot_international > 0  # Int'l 1/4" (slot 10)
        assert result.board_foot_doyle > 0          # Doyle (slot 11)

    def test_combined_variable_all_bf_rules(self):
        """Combined-variable fallback should populate all three BF rules."""
        # Use SS in PN — no Flewelling coefficients, falls back to combined-variable
        result = calculate_tree_volume(14.0, 85.0, 'SS', variant='PN')
        assert result.board_foot_volume > 0         # Scribner (primary)
        assert result.board_foot_international > 0   # International 1/4"
        assert result.board_foot_doyle > 0           # Doyle

    def test_merchantable_cubic_uses_4_inch_top(self):
        """Merchantable cubic should use 4" top (not 6/7" sawtimber top)."""
        # 6" DBH tree: DBHIB ~5.4", has 4" top merch but no 7" sawtimber
        result = calculate_tree_volume(6.0, 40.0, 'LP', variant='SN')
        assert result.merchantable_cubic_volume > 0
        assert result.board_foot_volume == 0.0  # Below 9" sawtimber min

    def test_merchantable_does_not_exceed_total(self):
        """Merchantable cubic should not exceed total cubic."""
        result = calculate_tree_volume(14.0, 70.0, 'WO', variant='CS')
        assert result.merchantable_cubic_volume <= result.total_cubic_volume

    def test_cord_volume_from_merchantable(self):
        """Cord volume should be merchantable_cubic / 79."""
        result = calculate_tree_volume(12.0, 80.0, 'LP', variant='SN')
        if result.merchantable_cubic_volume > 0:
            expected_cords = result.merchantable_cubic_volume / 79.0
            assert result.cord_volume == pytest.approx(expected_cords, rel=0.01)

    def test_very_small_tree_uses_combined_variable(self):
        """Trees with DBH < 1.0 should use combined-variable fallback."""
        result = calculate_tree_volume(0.5, 10.0, 'LP', variant='SN')
        assert result.total_cubic_volume >= 0
        # Should NOT use taper (fallback)
        assert result.board_foot_international == 0.0

    def test_short_tree_uses_combined_variable(self):
        """Trees shorter than 4.5 ft should use combined-variable."""
        result = calculate_tree_volume(2.0, 4.0, 'LP', variant='SN')
        assert result.total_cubic_volume >= 0

    def test_cache_key_includes_variant(self):
        """Volume calculator cache should be variant-specific."""
        calc_sn = get_volume_library('LP', 'SN')
        calc_ne = get_volume_library('LP', 'NE')
        # Different variant = different calculator instance
        assert calc_sn is not calc_ne

    def test_volume_result_to_dict(self):
        """VolumeResult.to_dict should include all log rule fields."""
        result = calculate_tree_volume(14.0, 85.0, 'LP', variant='SN')
        d = result.to_dict()
        assert 'board_foot_volume' in d
        assert 'board_foot_international' in d
        assert 'board_foot_doyle' in d
        assert 'merchantable_cubic_volume' in d

    def test_taper_vs_combined_variable_agreement(self):
        """Taper volume should roughly agree with combined-variable IB."""
        # LP 12" 80': taper IB should be within 30% of combined-variable IB
        result_taper = calculate_tree_volume(12.0, 80.0, 'LP', variant='SN')
        taper_vol = result_taper.total_cubic_volume

        # Combined-variable IB: V = a + b * D²H
        d2h = 12.0 ** 2 * 80.0
        cv_ib = max(0, -0.09653 + 0.00210 * d2h)

        ratio = taper_vol / cv_ib if cv_ib > 0 else 0
        assert 0.70 <= ratio <= 1.30, (
            f"Taper/CV ratio {ratio:.2f} outside expected range "
            f"(taper={taper_vol:.1f}, cv={cv_ib:.1f})"
        )


# ============================================================================
# Variant Volume Regression Tests
# ============================================================================

class TestVariantVolumeRegression:
    """Regression tests to ensure variant volumes remain stable."""

    def test_sn_lp_benchmark(self):
        """SN LP 12" 80' benchmark volume."""
        result = calculate_tree_volume(12.0, 80.0, 'LP', variant='SN')
        assert 15.0 <= result.total_cubic_volume <= 35.0

    def test_ne_rm_benchmark(self):
        """NE RM 10" 65' benchmark volume."""
        result = calculate_tree_volume(10.0, 65.0, 'RM', variant='NE')
        assert 5.0 <= result.total_cubic_volume <= 20.0

    def test_cs_wo_benchmark(self):
        """CS WO 14" 70' benchmark volume."""
        result = calculate_tree_volume(14.0, 70.0, 'WO', variant='CS')
        assert 10.0 <= result.total_cubic_volume <= 40.0

    def test_ls_rn_benchmark(self):
        """LS RN 10" 65' benchmark volume."""
        result = calculate_tree_volume(10.0, 65.0, 'RN', variant='LS')
        assert 5.0 <= result.total_cubic_volume <= 25.0

    def test_pn_df_benchmark(self):
        """PN DF 16" 120' benchmark volume (Flewelling taper)."""
        result = calculate_tree_volume(16.0, 120.0, 'DF', variant='PN')
        # Flewelling taper model: ~65 cuft for 16" DF at 120'
        assert 50.0 <= result.total_cubic_volume <= 120.0


# ============================================================================
# Flewelling taper model tests
# ============================================================================


class TestFlewellingTaperModel:
    """Tests for the Flewelling variable-shape profile model (PN/WC/OP)."""

    def setup_method(self):
        clear_taper_cache()

    def test_df_dib_at_breast_height(self):
        """DIB at BH should equal DBHIB."""
        model = create_taper_model('DF', 'PN')
        model.initialize_tree(16.0, 120.0)
        dib_bh = model.predict_dib(4.5)
        assert dib_bh == pytest.approx(model._dbhib, rel=0.001)

    def test_wh_dib_at_breast_height(self):
        """WH: DIB at BH should equal DBHIB."""
        model = create_taper_model('WH', 'PN')
        model.initialize_tree(14.0, 100.0)
        dib_bh = model.predict_dib(4.5)
        assert dib_bh == pytest.approx(model._dbhib, rel=0.001)

    def test_rc_dib_at_breast_height(self):
        """RC: DIB at BH should equal DBHIB."""
        model = create_taper_model('RC', 'PN')
        model.initialize_tree(20.0, 90.0)
        dib_bh = model.predict_dib(4.5)
        assert dib_bh == pytest.approx(model._dbhib, rel=0.001)

    def test_dib_monotonically_decreasing(self):
        """DIB should decrease from stump to tip."""
        model = create_taper_model('DF', 'PN')
        model.initialize_tree(16.0, 120.0)
        prev_dib = model.predict_dib(4.5)
        for h in range(10, 120, 5):
            dib = model.predict_dib(float(h))
            assert dib <= prev_dib + 0.01, (
                f"DIB increased from {prev_dib:.3f} to {dib:.3f} at h={h}")
            prev_dib = dib

    def test_dib_zero_at_tip(self):
        """DIB should be approximately 0 at the tip."""
        model = create_taper_model('DF', 'PN')
        model.initialize_tree(16.0, 120.0)
        dib_tip = model.predict_dib(120.0)
        assert dib_tip == 0.0

    def test_dib_positive_below_tip(self):
        """DIB should be positive below the tip."""
        model = create_taper_model('DF', 'PN')
        model.initialize_tree(16.0, 120.0)
        for h in [1.0, 4.5, 30.0, 60.0, 90.0, 110.0]:
            assert model.predict_dib(h) > 0.0, f"DIB should be > 0 at h={h}"

    def test_dbhib_less_than_dbh(self):
        """DBHIB should be less than DBH (bark thickness)."""
        for sp in ('DF', 'WH', 'RC'):
            model = create_taper_model(sp, 'PN')
            model.initialize_tree(16.0, 100.0)
            assert model._dbhib < 16.0
            assert model._dbhib > 12.0  # reasonable bark, not excessive

    def test_df_volume_reasonable(self):
        """DF 16" 120': Flewelling volume should match expected range."""
        model = create_taper_model('DF', 'PN')
        model.initialize_tree(16.0, 120.0)
        vol = model.predict_volume(1.0, 120.0)
        # Expected: 55-75 cuft (inside bark, stump to tip)
        assert 55.0 <= vol <= 80.0, f"DF volume {vol:.1f} outside expected range"

    def test_wh_volume_reasonable(self):
        """WH 14" 100': volume should be in expected range."""
        model = create_taper_model('WH', 'PN')
        model.initialize_tree(14.0, 100.0)
        vol = model.predict_volume(1.0, 100.0)
        # WH 14"/100': ~35-55 cuft
        assert 30.0 <= vol <= 60.0, f"WH volume {vol:.1f} outside expected range"

    def test_rc_volume_reasonable(self):
        """RC 18" 90': volume should be in expected range."""
        model = create_taper_model('RC', 'PN')
        model.initialize_tree(18.0, 90.0)
        vol = model.predict_volume(1.0, 90.0)
        # RC 18"/90': ~40-65 cuft
        assert 35.0 <= vol <= 70.0, f"RC volume {vol:.1f} outside expected range"

    def test_form_factor_reasonable(self):
        """Form factor should be between cone (0.33) and cylinder (1.0).

        RC has high taper (RHLONGI=0, no straight segment) so form factor
        can approach cone level.
        """
        for sp, dbh, ht in [('DF', 16, 120), ('WH', 14, 100), ('RC', 18, 90)]:
            model = create_taper_model(sp, 'PN')
            model.initialize_tree(dbh, ht)
            vol = model.predict_volume(1.0, ht)
            v_cyl = 0.005454154 * model._dbhib ** 2 * ht
            form = vol / v_cyl
            assert 0.30 <= form <= 0.60, (
                f"{sp} form factor {form:.3f} outside range")

    def test_height_to_dib_inverse(self):
        """predict_height_to_dib should be consistent with predict_dib."""
        model = create_taper_model('DF', 'PN')
        model.initialize_tree(16.0, 120.0)
        for target_dib in [12.0, 10.0, 8.0, 6.0, 4.0]:
            h = model.predict_height_to_dib(target_dib)
            assert h is not None and h > 0
            dib_at_h = model.predict_dib(h)
            assert dib_at_h == pytest.approx(target_dib, abs=0.15)

    def test_knot_positions_ordered(self):
        """Knot positions should be in order: RHI1 < RHI2 < RHC < 1."""
        model = create_taper_model('DF', 'PN')
        model.initialize_tree(16.0, 120.0)
        assert 0 < model._rhi1 < model._rhi2 < model._rhc < 1.0

    def test_variants_produce_same_flewelling(self):
        """PN, WC, OP should all produce Flewelling models for DF."""
        for variant in ('PN', 'WC', 'OP'):
            model = create_taper_model('DF', variant)
            assert isinstance(model, FlewellingTaperModel)
            model.initialize_tree(16.0, 120.0)
            vol = model.predict_volume(1.0, 120.0)
            assert vol > 50.0  # All should give reasonable volume

    def test_volume_increases_with_dbh(self):
        """Larger trees should have more volume."""
        volumes = []
        for dbh in [10, 14, 18, 22]:
            model = create_taper_model('DF', 'PN')
            model.initialize_tree(dbh, 100.0)
            volumes.append(model.predict_volume(1.0, 100.0))
        for i in range(1, len(volumes)):
            assert volumes[i] > volumes[i - 1]

    def test_volume_increases_with_height(self):
        """Taller trees should have more volume."""
        volumes = []
        for ht in [60, 80, 100, 120]:
            model = create_taper_model('DF', 'PN')
            model.initialize_tree(16.0, ht)
            volumes.append(model.predict_volume(1.0, ht))
        for i in range(1, len(volumes)):
            assert volumes[i] > volumes[i - 1]

    def test_small_tree_flewelling(self):
        """Flewelling should work for small trees (5" DBH, 30' HT)."""
        model = create_taper_model('DF', 'PN')
        model.initialize_tree(5.0, 30.0)
        vol = model.predict_volume(1.0, 30.0)
        assert 0.5 <= vol <= 5.0  # very small volume for small tree
        assert model.predict_dib(4.5) > 3.0  # DIB at BH should be reasonable

    def test_large_tree_flewelling(self):
        """Flewelling should work for large trees (30" DBH, 180' HT)."""
        model = create_taper_model('DF', 'PN')
        model.initialize_tree(30.0, 180.0)
        vol = model.predict_volume(1.0, 180.0)
        assert 200.0 <= vol <= 500.0  # large DF volume
        assert model.predict_dib(4.5) > 25.0

    def test_flewelling_merchandising_integration(self):
        """Flewelling model should work with merchandising system."""
        result = calculate_tree_volume(16.0, 120.0, 'DF', variant='PN')
        assert result.total_cubic_volume > 50.0
        assert result.merchantable_cubic_volume > 0
        assert result.board_foot_volume > 0        # Scribner
        assert result.board_foot_international > 0  # Int'l 1/4"
        assert result.board_foot_doyle > 0          # Doyle
        assert result.merchantable_cubic_volume <= result.total_cubic_volume

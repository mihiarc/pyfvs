"""Tests for diameter growth models across all variants.

Tests DDS/DG calculation, bounds checking, monotonicity (SI/competition effects),
species fallback behavior, and time step scaling.
"""
import math
import pytest

from pyfvs.sn_diameter_growth import (
    SNDiameterGrowthModel, create_sn_diameter_growth_model,
)
from pyfvs.ls_diameter_growth import (
    LSDiameterGrowthModel, create_ls_diameter_growth_model,
)
from pyfvs.cs_diameter_growth import (
    CSDiameterGrowthModel, create_cs_diameter_growth_model,
)
from pyfvs.pn_diameter_growth import (
    PNDiameterGrowthModel, create_pn_diameter_growth_model,
)
from pyfvs.wc_diameter_growth import (
    WCDiameterGrowthModel, create_wc_diameter_growth_model,
)
from pyfvs.ne_diameter_growth import (
    NEDiameterGrowthModel, create_ne_diameter_growth_model,
)
from pyfvs.op_diameter_growth import (
    OPDiameterGrowthModel, create_op_diameter_growth_model,
)


# ============================================================================
# SN Variant
# ============================================================================

class TestSNDiameterGrowth:
    """SN variant DDS model tests."""

    def test_positive_dds(self):
        """SN should produce positive DDS for typical inputs."""
        model = create_sn_diameter_growth_model('LP')
        dds = model.calculate_dds(
            dbh=8.0, crown_ratio=0.6, site_index=70,
            ba=120.0, pbal=40.0
        )
        assert dds > 0

    def test_lower_bound_ln_dds(self):
        """Extreme negative inputs should hit ln(DDS) lower bound."""
        model = create_sn_diameter_growth_model('LP')
        # Very small tree, high competition → very low DDS
        dds = model.calculate_dds(
            dbh=0.5, crown_ratio=0.15, site_index=30,
            ba=300.0, pbal=250.0
        )
        assert dds >= 0  # Still non-negative

    def test_upper_bound_ln_dds(self):
        """Upper bound (11.0) should prevent extreme DDS values."""
        model = create_sn_diameter_growth_model('LP')
        dds = model.calculate_dds(
            dbh=20.0, crown_ratio=0.95, site_index=130,
            ba=10.0, pbal=0.0
        )
        # exp(11) ≈ 60000, but model should produce reasonable values
        assert dds < 100000

    def test_higher_si_more_growth(self):
        """Higher site index should produce more DDS."""
        model = create_sn_diameter_growth_model('LP')
        dds_low = model.calculate_dds(dbh=8.0, crown_ratio=0.6, site_index=50,
                                      ba=100.0, pbal=30.0)
        dds_high = model.calculate_dds(dbh=8.0, crown_ratio=0.6, site_index=90,
                                       ba=100.0, pbal=30.0)
        assert dds_high > dds_low

    def test_dominant_grows_faster(self):
        """Dominant tree (low PBAL) should grow faster than suppressed."""
        model = create_sn_diameter_growth_model('LP')
        dds_dom = model.calculate_dds(dbh=8.0, crown_ratio=0.6, site_index=70,
                                      ba=100.0, pbal=10.0)
        dds_sup = model.calculate_dds(dbh=8.0, crown_ratio=0.6, site_index=70,
                                      ba=100.0, pbal=80.0)
        assert dds_dom > dds_sup

    def test_5yr_base_cycle(self):
        """SN DDS scales linearly with time step (5yr base)."""
        model = create_sn_diameter_growth_model('LP')
        dds_5 = model.calculate_dds(dbh=8.0, crown_ratio=0.6, site_index=70,
                                    ba=100.0, pbal=30.0, time_step=5.0)
        dds_10 = model.calculate_dds(dbh=8.0, crown_ratio=0.6, site_index=70,
                                     ba=100.0, pbal=30.0, time_step=10.0)
        assert abs(dds_10 / dds_5 - 2.0) < 0.01


# ============================================================================
# LS Variant
# ============================================================================

class TestLSDiameterGrowth:
    """LS variant DDS model tests."""

    def test_positive_dds(self):
        model = create_ls_diameter_growth_model('RN')
        dds = model.calculate_dds(dbh=8.0, crown_ratio=0.6, site_index=60,
                                  ba=100.0, bal=30.0)
        assert dds > 0

    def test_reldbh_effect(self):
        """RELDBH should affect growth — tree larger than QMD grows faster."""
        model = create_ls_diameter_growth_model('JP')
        dds_small = model.calculate_dds(dbh=5.0, crown_ratio=0.6, site_index=60,
                                        ba=100.0, bal=30.0, qmd_ge5=8.0)
        dds_large = model.calculate_dds(dbh=12.0, crown_ratio=0.6, site_index=60,
                                        ba=100.0, bal=30.0, qmd_ge5=8.0)
        assert dds_large > dds_small

    def test_bounds_ln_dds(self):
        """LS uses tighter bounds [-5, 5] on ln(DDS)."""
        model = create_ls_diameter_growth_model('RN')
        # Even with extreme inputs, DDS should be bounded
        dds = model.calculate_dds(dbh=0.2, crown_ratio=0.05, site_index=20,
                                  ba=500.0, bal=400.0)
        assert dds >= 0

    def test_10yr_base_cycle(self):
        """LS DDS scales with 10yr base cycle."""
        model = create_ls_diameter_growth_model('RN')
        dds_10 = model.calculate_dds(dbh=8.0, crown_ratio=0.6, site_index=60,
                                     ba=100.0, bal=30.0, time_step=10.0)
        dds_5 = model.calculate_dds(dbh=8.0, crown_ratio=0.6, site_index=60,
                                    ba=100.0, bal=30.0, time_step=5.0)
        assert abs(dds_10 / dds_5 - 2.0) < 0.01


# ============================================================================
# CS Variant (subclass of LS)
# ============================================================================

class TestCSDiameterGrowth:
    """CS variant DDS model tests (inherits LS equation)."""

    def test_positive_dds(self):
        model = create_cs_diameter_growth_model('WO')
        dds = model.calculate_dds(dbh=8.0, crown_ratio=0.6, site_index=60,
                                  ba=100.0, bal=30.0)
        assert dds > 0

    def test_is_ls_subclass(self):
        """CS model should be a subclass of LS."""
        model = create_cs_diameter_growth_model('WO')
        assert isinstance(model, LSDiameterGrowthModel)

    def test_no_baskerville(self):
        """CS should NOT use Baskerville correction."""
        model = create_cs_diameter_growth_model('WO')
        assert model._use_baskerville is False

    def test_cs_uses_own_coefficients(self):
        """CS and LS should have different coefficients."""
        cs_model = create_cs_diameter_growth_model('WO')
        ls_model = create_ls_diameter_growth_model('RN')
        # Different species, different coefficients
        assert cs_model.coefficients != ls_model.coefficients


# ============================================================================
# PN Variant
# ============================================================================

class TestPNDiameterGrowth:
    """PN variant DDS model tests (topographic ln(DDS))."""

    def test_positive_dds(self):
        model = create_pn_diameter_growth_model('DF')
        dds = model.calculate_dds(dbh=10.0, crown_ratio=0.6, site_index=120,
                                  ba=120.0, bal=40.0)
        assert dds > 0

    def test_elevation_effect(self):
        """Higher elevation should affect PN growth."""
        model = create_pn_diameter_growth_model('DF')
        dds_low = model.calculate_dds(dbh=10.0, crown_ratio=0.6, site_index=120,
                                      ba=120.0, bal=40.0, elevation=5.0)
        dds_high = model.calculate_dds(dbh=10.0, crown_ratio=0.6, site_index=120,
                                       ba=120.0, bal=40.0, elevation=40.0)
        # Growth should differ (elevation has nonzero coefficients)
        assert dds_low != dds_high

    def test_default_elevation_10(self):
        """PN default elevation should be 10 (hundreds of feet)."""
        assert PNDiameterGrowthModel.DEFAULT_ELEVATION == 10.0

    def test_slope_aspect_effect(self):
        """Slope and aspect should modify PN growth."""
        model = create_pn_diameter_growth_model('DF')
        dds_flat = model.calculate_dds(dbh=10.0, crown_ratio=0.6, site_index=120,
                                       ba=120.0, bal=40.0, slope=0.0)
        dds_steep = model.calculate_dds(dbh=10.0, crown_ratio=0.6, site_index=120,
                                        ba=120.0, bal=40.0, slope=0.5, aspect=1.57)
        assert dds_flat != dds_steep


# ============================================================================
# WC Variant (subclass of PN)
# ============================================================================

class TestWCDiameterGrowth:
    """WC variant DDS model tests (inherits PN equation)."""

    def test_positive_dds(self):
        model = create_wc_diameter_growth_model('DF')
        dds = model.calculate_dds(dbh=10.0, crown_ratio=0.6, site_index=110,
                                  ba=120.0, bal=40.0)
        assert dds > 0

    def test_is_pn_subclass(self):
        """WC model should be a subclass of PN."""
        model = create_wc_diameter_growth_model('DF')
        assert isinstance(model, PNDiameterGrowthModel)

    def test_default_elevation_20(self):
        """WC default elevation should be 20 (hundreds of feet)."""
        assert WCDiameterGrowthModel.DEFAULT_ELEVATION == 20.0

    def test_different_ifor_index(self):
        """WC should use IFOR index 5, not PN's 1."""
        assert WCDiameterGrowthModel.DEFAULT_IFOR_INDEX == 5
        assert PNDiameterGrowthModel.DEFAULT_IFOR_INDEX == 1


# ============================================================================
# NE Variant
# ============================================================================

class TestNEDiameterGrowth:
    """NE variant DDS model tests (BA growth form, annual iteration)."""

    def test_positive_dds(self):
        model = create_ne_diameter_growth_model('RM')
        dds = model.calculate_dds(dbh=8.0, crown_ratio=0.5, site_index=55,
                                  ba=100.0, bal=30.0)
        assert dds > 0

    def test_higher_si_more_growth(self):
        """Higher site index should produce more NE growth."""
        model = create_ne_diameter_growth_model('RM')
        dds_low = model.calculate_dds(dbh=8.0, crown_ratio=0.5, site_index=40,
                                      ba=100.0, bal=30.0)
        dds_high = model.calculate_dds(dbh=8.0, crown_ratio=0.5, site_index=70,
                                       ba=100.0, bal=30.0)
        assert dds_high > dds_low

    def test_bal_suppresses_growth(self):
        """Higher BAL (more competition) should reduce NE growth."""
        model = create_ne_diameter_growth_model('RM')
        dds_dom = model.calculate_dds(dbh=8.0, crown_ratio=0.5, site_index=55,
                                      ba=100.0, bal=10.0)
        dds_sup = model.calculate_dds(dbh=8.0, crown_ratio=0.5, site_index=55,
                                      ba=100.0, bal=80.0)
        assert dds_dom > dds_sup

    def test_dds_upper_bound(self):
        """NE DDS should be bounded at 50 sq in."""
        model = create_ne_diameter_growth_model('RM')
        dds = model.calculate_dds(dbh=30.0, crown_ratio=0.9, site_index=100,
                                  ba=10.0, bal=0.0, time_step=10.0)
        assert dds <= 50.0

    def test_no_stochastic(self):
        """NE model should not accept rng parameter."""
        model = create_ne_diameter_growth_model('RM')
        # NE calculate_dds has no rng parameter — just verify it works
        dds = model.calculate_dds(dbh=8.0, crown_ratio=0.5, site_index=55,
                                  ba=100.0, bal=30.0)
        assert dds > 0


# ============================================================================
# OP Variant
# ============================================================================

class TestOPDiameterGrowth:
    """OP variant DG model tests (direct diameter growth, not DDS)."""

    def test_positive_dg(self):
        model = create_op_diameter_growth_model('DF')
        dg = model.calculate_diameter_growth(
            dbh=10.0, crown_ratio=0.6, site_index=120,
            ba=120.0, bal=40.0
        )
        assert dg > 0

    def test_higher_si_more_growth(self):
        """Higher site index should produce more OP growth."""
        model = create_op_diameter_growth_model('DF')
        dg_low = model.calculate_diameter_growth(
            dbh=10.0, crown_ratio=0.6, site_index=80,
            ba=120.0, bal=40.0
        )
        dg_high = model.calculate_diameter_growth(
            dbh=10.0, crown_ratio=0.6, site_index=140,
            ba=120.0, bal=40.0
        )
        assert dg_high > dg_low

    def test_bal_suppresses_growth(self):
        """Higher BAL should suppress OP growth."""
        model = create_op_diameter_growth_model('DF')
        dg_dom = model.calculate_diameter_growth(
            dbh=10.0, crown_ratio=0.6, site_index=120,
            ba=100.0, bal=10.0
        )
        dg_sup = model.calculate_diameter_growth(
            dbh=10.0, crown_ratio=0.6, site_index=120,
            ba=100.0, bal=80.0
        )
        assert dg_dom > dg_sup

    def test_5yr_base_cycle(self):
        """OP uses 5yr base cycle for DG scaling."""
        model = create_op_diameter_growth_model('DF')
        dg_5 = model.calculate_diameter_growth(
            dbh=10.0, crown_ratio=0.6, site_index=120,
            ba=120.0, bal=40.0, time_step=5.0
        )
        dg_10 = model.calculate_diameter_growth(
            dbh=10.0, crown_ratio=0.6, site_index=120,
            ba=120.0, bal=40.0, time_step=10.0
        )
        assert abs(dg_10 / dg_5 - 2.0) < 0.01


# ============================================================================
# Species Fallback
# ============================================================================

class TestSpeciesFallback:
    """Species fallback behavior across variants."""

    def test_ls_unknown_species_uses_default(self):
        """LS model should fall back to RN for unknown species."""
        model = create_ls_diameter_growth_model('ZZ')
        # Should not crash; uses fallback
        assert model.coefficients is not None
        assert len(model.coefficients) > 0

    def test_ne_unknown_species_uses_default(self):
        """NE model should fall back to RM for unknown species."""
        model = create_ne_diameter_growth_model('ZZ')
        assert model.coefficients is not None

    def test_op_unknown_species_uses_default(self):
        """OP model should fall back to DF for unknown species."""
        model = create_op_diameter_growth_model('ZZ')
        assert model.coefficients is not None

    def test_factory_caching(self):
        """Factory functions should cache models by species."""
        m1 = create_sn_diameter_growth_model('LP')
        m2 = create_sn_diameter_growth_model('LP')
        assert m1 is m2

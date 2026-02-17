"""Tests for stochastic diameter growth mode.

Verifies that:
1. Deterministic mode (default) is unchanged by the stochastic additions
2. Stochastic mode with same seed produces identical results (reproducibility)
3. Different seeds produce different results
4. Random draws are bounded within +/-2*sigma
5. NE and OP variants are unaffected by stochastic flag
6. CS has no Baskerville in deterministic mode but draws noise in stochastic
"""
import math
import random

import pytest

from pyfvs import Stand
from pyfvs.tree import Tree
from pyfvs.sn_diameter_growth import create_sn_diameter_growth_model
from pyfvs.ls_diameter_growth import create_ls_diameter_growth_model
from pyfvs.pn_diameter_growth import create_pn_diameter_growth_model
from pyfvs.wc_diameter_growth import create_wc_diameter_growth_model
from pyfvs.cs_diameter_growth import create_cs_diameter_growth_model


def _run_stand_deterministic(tpa, si, species, variant, years, global_seed=0):
    """Run a deterministic stand, seeding global random for mortality reproducibility."""
    random.seed(global_seed)
    stand = Stand.initialize_planted(tpa, si, species, variant=variant)
    stand.grow(years)
    return stand.get_metrics()


def _run_stand_stochastic(tpa, si, species, variant, years, seed, global_seed=0):
    """Run a stochastic stand, seeding global random for mortality reproducibility."""
    random.seed(global_seed)
    stand = Stand.initialize_planted(
        tpa, si, species, variant=variant, stochastic=True, random_seed=seed
    )
    stand.grow(years)
    return stand.get_metrics()


# =========================================================================
# Reproducibility tests
# =========================================================================

class TestStochasticReproducibility:
    """Two runs with the same seed must produce identical results."""

    def test_sn_stand_same_seed_identical(self):
        """SN variant: same seed -> identical metrics after 50 years."""
        m1 = _run_stand_stochastic(500, 70, 'LP', 'SN', 50, seed=42, global_seed=100)
        m2 = _run_stand_stochastic(500, 70, 'LP', 'SN', 50, seed=42, global_seed=100)

        assert m1['basal_area'] == pytest.approx(m2['basal_area'], rel=1e-10)
        assert m1['qmd'] == pytest.approx(m2['qmd'], rel=1e-10)
        assert m1['tpa'] == m2['tpa']
        assert m1['volume'] == pytest.approx(m2['volume'], rel=1e-10)

    def test_ls_stand_same_seed_identical(self):
        """LS variant: same seed -> identical metrics."""
        m1 = _run_stand_stochastic(500, 60, 'RN', 'LS', 30, seed=99, global_seed=200)
        m2 = _run_stand_stochastic(500, 60, 'RN', 'LS', 30, seed=99, global_seed=200)

        assert m1['basal_area'] == pytest.approx(m2['basal_area'], rel=1e-10)
        assert m1['qmd'] == pytest.approx(m2['qmd'], rel=1e-10)

    def test_pn_stand_same_seed_identical(self):
        """PN variant: same seed -> identical metrics."""
        m1 = _run_stand_stochastic(300, 110, 'DF', 'PN', 20, seed=7, global_seed=300)
        m2 = _run_stand_stochastic(300, 110, 'DF', 'PN', 20, seed=7, global_seed=300)

        assert m1['basal_area'] == pytest.approx(m2['basal_area'], rel=1e-10)
        assert m1['qmd'] == pytest.approx(m2['qmd'], rel=1e-10)

    def test_sn_model_level_reproducible(self):
        """SN model: same rng seed -> identical DDS values."""
        model = create_sn_diameter_growth_model('LP')

        rng1 = random.Random(42)
        dds1 = [model.calculate_dds(
            dbh=8.0, crown_ratio=0.7, site_index=70,
            ba=100, pbal=50, rng=rng1
        ) for _ in range(20)]

        rng2 = random.Random(42)
        dds2 = [model.calculate_dds(
            dbh=8.0, crown_ratio=0.7, site_index=70,
            ba=100, pbal=50, rng=rng2
        ) for _ in range(20)]

        for d1, d2 in zip(dds1, dds2):
            assert d1 == d2


# =========================================================================
# Different seeds diverge
# =========================================================================

class TestStochasticDivergence:
    """Different seeds must produce different results."""

    def test_sn_different_seeds_diverge(self):
        """SN variant: different seeds -> different BA after growth."""
        m1 = _run_stand_stochastic(500, 70, 'LP', 'SN', 25, seed=1, global_seed=100)
        m2 = _run_stand_stochastic(500, 70, 'LP', 'SN', 25, seed=999, global_seed=100)

        # BA should differ (though not enormously)
        assert m1['basal_area'] != pytest.approx(m2['basal_area'], rel=1e-6)

    def test_cs_different_seeds_diverge(self):
        """CS variant: different seeds -> different results."""
        m1 = _run_stand_stochastic(400, 65, 'WO', 'CS', 20, seed=10, global_seed=100)
        m2 = _run_stand_stochastic(400, 65, 'WO', 'CS', 20, seed=20, global_seed=100)

        assert m1['basal_area'] != pytest.approx(m2['basal_area'], rel=1e-6)

    def test_sn_model_different_seeds_diverge(self):
        """SN model: different rng seeds -> different DDS values."""
        model = create_sn_diameter_growth_model('LP')

        rng1 = random.Random(1)
        dds1 = model.calculate_dds(
            dbh=8.0, crown_ratio=0.7, site_index=70,
            ba=100, pbal=50, rng=rng1
        )

        rng2 = random.Random(999)
        dds2 = model.calculate_dds(
            dbh=8.0, crown_ratio=0.7, site_index=70,
            ba=100, pbal=50, rng=rng2
        )

        assert dds1 != dds2


# =========================================================================
# Deterministic unchanged
# =========================================================================

class TestDeterministicUnchanged:
    """Stochastic=False (default) must produce identical results to pre-change behavior."""

    def test_sn_deterministic_default(self):
        """SN: stochastic=False is the default and works normally."""
        stand = Stand.initialize_planted(500, 70, 'LP', variant='SN')
        assert stand.stochastic is False
        assert stand._rng is None
        stand.grow(25)
        m = stand.get_metrics()
        # Sanity: BA should be reasonable for LP at age 30
        assert 50 < m['basal_area'] < 250

    def test_ls_deterministic_default(self):
        """LS: deterministic mode works normally."""
        stand = Stand.initialize_planted(500, 60, 'RN', variant='LS')
        assert stand._rng is None
        stand.grow(30)
        m = stand.get_metrics()
        assert m['basal_area'] > 0
        assert m['qmd'] > 0

    def test_sn_model_rng_none_uses_baskerville(self):
        """SN model: rng=None uses deterministic Baskerville correction."""
        model = create_sn_diameter_growth_model('LP')
        dds_det = model.calculate_dds(
            dbh=8.0, crown_ratio=0.7, site_index=70,
            ba=100, pbal=50, rng=None
        )
        # Should be > 0 and include Baskerville boost
        assert dds_det > 0

    def test_cs_deterministic_no_baskerville(self):
        """CS model: deterministic mode has no Baskerville (correction=1.0)."""
        model = create_cs_diameter_growth_model('WO')
        # _stochastic_multiplier with rng=None should return 1.0 for CS
        mult = model._stochastic_multiplier(2.0, rng=None)
        assert mult == 1.0


# =========================================================================
# Bounded draws
# =========================================================================

class TestBoundedDraws:
    """Stochastic draws must be bounded within +/-2*sigma."""

    def _collect_multipliers(self, model, ln_dds, n=1000, seed=42):
        """Draw n multipliers and return as list."""
        rng = random.Random(seed)
        return [model._stochastic_multiplier(ln_dds, rng) for _ in range(n)]

    def test_sn_draws_bounded(self):
        """SN: all multipliers within exp(+/-2*sigma)."""
        model = create_sn_diameter_growth_model('LP')
        sigma = model._sigma
        assert sigma > 0, "LP should have non-zero sigma"

        mults = self._collect_multipliers(model, ln_dds=2.0, n=2000)

        max_z = 2.0 * sigma
        upper = math.exp(max_z)
        lower = math.exp(-max_z)

        for m in mults:
            assert lower - 1e-10 <= m <= upper + 1e-10, (
                f"Multiplier {m} outside bounds [{lower}, {upper}]"
            )

    def test_ls_draws_bounded(self):
        """LS: all multipliers within exp(+/-2*sigma)."""
        model = create_ls_diameter_growth_model('RN')
        sigma = model._sigma
        assert sigma > 0

        mults = self._collect_multipliers(model, ln_dds=2.0, n=2000)

        max_z = 2.0 * sigma
        upper = math.exp(max_z)
        lower = math.exp(-max_z)

        for m in mults:
            assert lower - 1e-10 <= m <= upper + 1e-10

    def test_suppression_at_high_ln_dds(self):
        """Large ln(DDS) > 5.0 should always return 1.0 (no noise)."""
        model = create_sn_diameter_growth_model('LP')
        rng = random.Random(123)
        for _ in range(100):
            mult = model._stochastic_multiplier(6.0, rng)
            assert mult == 1.0

    def test_suppression_taper_zone(self):
        """ln(DDS) between 4.0 and 5.0 should have reduced noise."""
        model = create_sn_diameter_growth_model('LP')

        # At ln_dds=4.5, suppress = 0.5, so effective sigma is sigma*0.5
        mults_full = self._collect_multipliers(model, ln_dds=2.0, n=1000, seed=1)
        mults_tapered = self._collect_multipliers(model, ln_dds=4.5, n=1000, seed=1)

        # Variance of tapered should be less than full
        import statistics
        var_full = statistics.variance(mults_full)
        var_tapered = statistics.variance(mults_tapered)
        assert var_tapered < var_full


# =========================================================================
# NE and OP unaffected
# =========================================================================

class TestUnaffectedVariants:
    """NE (BA increment) and OP (direct DG) should not be affected by stochastic flag."""

    def test_ne_stochastic_same_as_deterministic(self):
        """NE variant: stochastic flag has no effect on diameter growth.

        Note: mortality uses global random, so we seed it identically for
        both runs to isolate the diameter growth comparison.
        """
        m_det = _run_stand_deterministic(400, 60, 'RM', 'NE', 20, global_seed=500)
        # For stochastic run, also seed global random to same value
        random.seed(500)
        stand_sto = Stand.initialize_planted(
            400, 60, 'RM', variant='NE', stochastic=True, random_seed=42
        )
        stand_sto.grow(20)
        m_sto = stand_sto.get_metrics()

        # NE doesn't use rng for diameter growth, so with same mortality
        # seed, results should be identical
        assert m_det['basal_area'] == pytest.approx(m_sto['basal_area'], rel=1e-10)
        assert m_det['qmd'] == pytest.approx(m_sto['qmd'], rel=1e-10)

    def test_op_stochastic_same_as_deterministic(self):
        """OP variant: stochastic flag has no effect on diameter growth."""
        random.seed(600)
        trees_det = [Tree(dbh=5.0, height=30.0, species='DF', age=15, variant='OP')
                     for _ in range(100)]
        stand_det = Stand(trees_det, site_index=110, species='DF', variant='OP')
        stand_det.age = 15
        stand_det.grow(10)
        m_det = stand_det.get_metrics()

        random.seed(600)
        trees_sto = [Tree(dbh=5.0, height=30.0, species='DF', age=15, variant='OP')
                     for _ in range(100)]
        stand_sto = Stand(trees_sto, site_index=110, species='DF', variant='OP',
                          stochastic=True, random_seed=42)
        stand_sto.age = 15
        stand_sto.grow(10)
        m_sto = stand_sto.get_metrics()

        assert m_det['basal_area'] == pytest.approx(m_sto['basal_area'], rel=1e-10)
        assert m_det['qmd'] == pytest.approx(m_sto['qmd'], rel=1e-10)


# =========================================================================
# CS special case
# =========================================================================

class TestCSSpecialCase:
    """CS: no Baskerville deterministic, but does draw noise stochastic."""

    def test_cs_stochastic_differs_from_deterministic(self):
        """CS stochastic should differ from CS deterministic at model level."""
        model = create_cs_diameter_growth_model('WO')
        rng = random.Random(42)

        det_dds = model.calculate_dds(
            dbh=8.0, crown_ratio=0.7, site_index=65,
            ba=100, bal=50, rng=None
        )

        sto_dds = model.calculate_dds(
            dbh=8.0, crown_ratio=0.7, site_index=65,
            ba=100, bal=50, rng=rng
        )

        # Stochastic should differ from deterministic
        assert det_dds != sto_dds

    def test_cs_model_sigma_loaded(self):
        """CS model should have non-zero sigma for WO."""
        model = create_cs_diameter_growth_model('WO')
        assert model._sigma > 0, "WO should have non-zero sigma"

    def test_cs_stochastic_draws_have_variation(self):
        """CS stochastic draws should have variation."""
        model = create_cs_diameter_growth_model('WO')
        rng = random.Random(42)

        dds_values = [model.calculate_dds(
            dbh=8.0, crown_ratio=0.7, site_index=65,
            ba=100, bal=50, rng=rng
        ) for _ in range(100)]

        assert max(dds_values) > min(dds_values) * 1.05


# =========================================================================
# Model-level stochastic tests
# =========================================================================

class TestModelLevelStochastic:
    """Direct model-level tests for stochastic behavior."""

    def test_sn_stochastic_mean_near_baskerville(self):
        """Mean of many stochastic draws should approximate Baskerville correction."""
        model = create_sn_diameter_growth_model('LP')
        rng = random.Random(12345)

        n_draws = 500
        stochastic_dds = []
        for _ in range(n_draws):
            dds = model.calculate_dds(
                dbh=8.0, crown_ratio=0.7, site_index=70,
                ba=100, pbal=50, rng=rng
            )
            stochastic_dds.append(dds)

        det_dds = model.calculate_dds(
            dbh=8.0, crown_ratio=0.7, site_index=70,
            ba=100, pbal=50, rng=None
        )

        mean_stochastic = sum(stochastic_dds) / len(stochastic_dds)

        # Mean of stochastic should be within ~15% of deterministic
        # (they approximate the same expected value, but from different
        # directions -- Baskerville is an analytic approximation)
        assert abs(mean_stochastic - det_dds) / det_dds < 0.15

    def test_wc_stochastic_produces_variation(self):
        """WC model stochastic draws should have non-trivial variation."""
        model = create_wc_diameter_growth_model('DF')
        rng = random.Random(42)

        dds_values = []
        for _ in range(100):
            dds = model.calculate_dds(
                dbh=8.0, crown_ratio=0.6, site_index=120,
                ba=150, bal=80, rng=rng
            )
            dds_values.append(dds)

        # Should have variation
        assert max(dds_values) > min(dds_values) * 1.1

    def test_pn_stochastic_produces_variation(self):
        """PN model stochastic draws should have non-trivial variation."""
        model = create_pn_diameter_growth_model('DF')
        rng = random.Random(42)

        dds_values = []
        for _ in range(100):
            dds = model.calculate_dds(
                dbh=8.0, crown_ratio=0.6, site_index=120,
                ba=150, bal=80, rng=rng
            )
            dds_values.append(dds)

        assert max(dds_values) > min(dds_values) * 1.1

    def test_ls_stochastic_produces_variation(self):
        """LS model stochastic draws should have non-trivial variation."""
        model = create_ls_diameter_growth_model('RN')
        rng = random.Random(42)

        dds_values = [model.calculate_dds(
            dbh=8.0, crown_ratio=0.7, site_index=60,
            ba=100, bal=50, rng=rng
        ) for _ in range(100)]

        assert max(dds_values) > min(dds_values) * 1.1

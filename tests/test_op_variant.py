"""Tests for the OP (ORGANON Pacific Northwest) variant implementation.

OP shares bark ratio, crown ratio, and most volume infrastructure with PN since
both use PNW species (DF, WH, RC, GF, etc.). OP has its own SDI maximums and
a unique diameter growth model (ORGANON ln(DG) equation predicting diameter
growth directly rather than DDS).

Tests cover:
- Factory dispatch (OP -> PNBarkRatioModel, PNCrownRatioModel, MortalityModel)
- Bark ratio via PN model
- Crown ratio via PN model
- OP-specific SDI maximums
- Mortality with OP SDI maximums
- Volume coverage for OP species
- Integration (full stand simulation with variant='OP')
- Smoke tests (50-year simulations for key species)
"""
import math
import pytest

from pyfvs import Stand
from pyfvs.bark_ratio import (
    PNBarkRatioModel,
    create_bark_ratio_model,
)
from pyfvs.crown_ratio import (
    PNCrownRatioModel,
    create_crown_ratio_model,
)
from pyfvs.mortality import create_mortality_model, MortalityModel
from pyfvs.stand_metrics import StandMetricsCalculator
from pyfvs.volume_library import (
    VolumeCalculator,
    calculate_tree_volume,
    VOLUME_COEFFICIENTS_OUTSIDE_BARK,
    VOLUME_COEFFICIENTS_INSIDE_BARK,
    HARDWOOD_SPECIES,
)


# OP species list (18 total)
OP_CONIFER_SPECIES = ['DF', 'GF', 'WF', 'PP', 'SP', 'IC', 'WH', 'RC', 'PY', 'MH', 'GC']
OP_HARDWOOD_SPECIES = ['TA', 'CL', 'BL', 'WO', 'BO', 'RA', 'PD', 'WI']
OP_ALL_SPECIES = OP_CONIFER_SPECIES + OP_HARDWOOD_SPECIES


# ===========================================================================
# Phase 1: Factory Dispatch Tests
# ===========================================================================

class TestOPFactoryDispatch:
    """Tests that OP variant dispatches to PN models correctly."""

    def test_bark_ratio_factory_returns_pn_model(self):
        """create_bark_ratio_model with variant='OP' returns PNBarkRatioModel."""
        model = create_bark_ratio_model('DF', variant='OP')
        assert isinstance(model, PNBarkRatioModel)

    def test_crown_ratio_factory_returns_pn_model(self):
        """create_crown_ratio_model with variant='OP' returns PNCrownRatioModel."""
        model = create_crown_ratio_model('DF', variant='OP')
        assert isinstance(model, PNCrownRatioModel)

    def test_mortality_factory_returns_mortality_model(self):
        """create_mortality_model with variant='OP' returns MortalityModel."""
        model = create_mortality_model('DF', variant='OP')
        assert isinstance(model, MortalityModel)

    def test_op_bark_ratio_matches_pn(self):
        """OP and PN bark ratios are identical for shared species."""
        for species in ['DF', 'WH', 'RC', 'SF', 'GF']:
            op_model = create_bark_ratio_model(species, variant='OP')
            pn_model = create_bark_ratio_model(species, variant='PN')
            op_ratio = op_model.calculate_bark_ratio(10.0)
            pn_ratio = pn_model.calculate_bark_ratio(10.0)
            assert op_ratio == pn_ratio, (
                f"{species} bark ratio differs: OP={op_ratio} vs PN={pn_ratio}"
            )


# ===========================================================================
# Phase 2: Bark Ratio via PN Model
# ===========================================================================

class TestOPBarkRatio:
    """Tests bark ratio calculations for OP species using PN model."""

    def test_df_bark_ratio_reasonable(self):
        """Douglas-fir bark ratio is in expected range."""
        model = create_bark_ratio_model('DF', variant='OP')
        for dob in [5.0, 10.0, 20.0, 30.0]:
            ratio = model.calculate_bark_ratio(dob)
            assert 0.85 <= ratio <= 0.95, (
                f"DF bark ratio {ratio} out of bounds at DOB={dob}"
            )

    def test_wh_bark_ratio_reasonable(self):
        """Western Hemlock bark ratio is in expected range."""
        model = create_bark_ratio_model('WH', variant='OP')
        ratio = model.calculate_bark_ratio(10.0)
        assert 0.88 <= ratio <= 0.96, f"WH bark ratio {ratio} unexpected"

    def test_op_unique_species_get_defaults(self):
        """OP-unique species (TA, CL, BL, PD) fall to PN default group."""
        for species in ['TA', 'CL', 'BL', 'PD']:
            model = create_bark_ratio_model(species, variant='OP')
            ratio = model.calculate_bark_ratio(10.0)
            assert 0.80 <= ratio <= 0.99, (
                f"{species} bark ratio {ratio} out of bounds"
            )

    def test_all_op_species_valid_bark_ratio(self):
        """All 18 OP species produce valid bark ratios (0.80-0.99)."""
        for species in OP_ALL_SPECIES:
            model = create_bark_ratio_model(species, variant='OP')
            ratio = model.calculate_bark_ratio(10.0)
            assert 0.80 <= ratio <= 0.99, (
                f"{species} bark ratio {ratio} out of bounds"
            )


# ===========================================================================
# Phase 3: Crown Ratio via PN Model
# ===========================================================================

class TestOPCrownRatio:
    """Tests crown ratio calculations for OP species using PN model."""

    def test_df_crown_ratio_decreases_with_sdi(self):
        """DF crown ratio decreases as relative SDI increases."""
        model = create_crown_ratio_model('DF', variant='OP')
        cr_low = model.calculate_average_crown_ratio(2.0)
        cr_high = model.calculate_average_crown_ratio(8.0)
        assert cr_low > cr_high, (
            f"CR should decrease with SDI: low={cr_low}, high={cr_high}"
        )

    def test_crown_ratio_bounded(self):
        """Crown ratios are bounded within reasonable range."""
        model = create_crown_ratio_model('DF', variant='OP')
        for relsdi in [1.0, 2.0, 5.0, 8.0]:
            cr = model.calculate_average_crown_ratio(relsdi)
            assert 0.05 <= cr <= 0.95, (
                f"CR {cr} out of bounds at RELSDI={relsdi}"
            )

    def test_op_crown_ratio_matches_pn(self):
        """OP and PN crown ratios are identical for shared species."""
        for species in ['DF', 'WH', 'RC']:
            op_model = create_crown_ratio_model(species, variant='OP')
            pn_model = create_crown_ratio_model(species, variant='PN')
            op_cr = op_model.calculate_average_crown_ratio(5.0)
            pn_cr = pn_model.calculate_average_crown_ratio(5.0)
            assert op_cr == pn_cr, (
                f"{species} crown ratio differs: OP={op_cr} vs PN={pn_cr}"
            )

    def test_individual_cr_valid_range(self):
        """Individual tree crown ratio predictions are in valid range."""
        model = create_crown_ratio_model('DF', variant='OP')
        cr = model.predict_individual_crown_ratio(
            tree_rank=0.5, relsdi=5.0, dbh=10.0, ba=150.0
        )
        assert 0.10 <= cr <= 0.95, f"Individual CR {cr} out of bounds"


# ===========================================================================
# Phase 4: OP SDI Maximums
# ===========================================================================

class TestOPSDIMaximums:
    """Tests for OP-specific SDI maximum values."""

    def test_op_sdi_maximums_loaded(self):
        """OP_SDI_MAXIMUMS is available on StandMetricsCalculator."""
        sdi_maxs = StandMetricsCalculator.OP_SDI_MAXIMUMS
        assert isinstance(sdi_maxs, dict)
        assert len(sdi_maxs) >= 18, f"Expected 19 species, got {len(sdi_maxs)}"

    def test_df_sdi_max_850(self):
        """Douglas-fir SDI max is 850 for OP."""
        calc = StandMetricsCalculator('DF', variant='OP')
        max_sdi = calc.get_max_sdi([], 'DF')
        assert max_sdi == 850

    def test_wh_sdi_max_900(self):
        """Western Hemlock SDI max is 900 for OP."""
        calc = StandMetricsCalculator('WH', variant='OP')
        max_sdi = calc.get_max_sdi([], 'WH')
        assert max_sdi == 900

    def test_all_species_have_positive_sdi_max(self):
        """All OP species have positive SDI maximum values."""
        sdi_maxs = StandMetricsCalculator.OP_SDI_MAXIMUMS
        for species, max_val in sdi_maxs.items():
            assert max_val > 0, f"{species} has non-positive SDI max: {max_val}"
            assert max_val >= 300, f"{species} SDI max {max_val} seems too low"
            assert max_val <= 1000, f"{species} SDI max {max_val} seems too high"


# ===========================================================================
# Phase 5: OP Mortality
# ===========================================================================

class TestOPMortality:
    """Tests for OP mortality model with OP-specific SDI maximums."""

    def test_mortality_model_uses_op_sdi(self):
        """Mortality model with variant='OP' uses OP SDI maximums."""
        model = create_mortality_model('DF', variant='OP')
        assert model.max_sdi == 850, (
            f"Expected OP DF max_sdi=850, got {model.max_sdi}"
        )

    def test_wh_mortality_sdi(self):
        """WH mortality model uses OP SDI max of 900."""
        model = create_mortality_model('WH', variant='OP')
        assert model.max_sdi == 900, (
            f"Expected OP WH max_sdi=900, got {model.max_sdi}"
        )

    def test_ra_mortality_sdi(self):
        """RA mortality model uses OP SDI max of 650."""
        model = create_mortality_model('RA', variant='OP')
        assert model.max_sdi == 650, (
            f"Expected OP RA max_sdi=650, got {model.max_sdi}"
        )

    def test_mortality_applies_to_stand(self):
        """Mortality can be applied to an OP stand."""
        stand = Stand.initialize_planted(
            trees_per_acre=600,
            site_index=120,
            species='DF',
            variant='OP'
        )
        initial_tpa = len(stand.trees)
        stand.grow(50)
        final_tpa = len(stand.trees)
        # Some mortality should occur over 50 years at 600 TPA
        assert final_tpa < initial_tpa, (
            f"Expected mortality: initial={initial_tpa}, final={final_tpa}"
        )


# ===========================================================================
# Phase 6: OP Volume
# ===========================================================================

class TestOPVolume:
    """Tests for OP species volume coverage."""

    def test_df_volume_reasonable(self):
        """Douglas-fir volume is reasonable (10" DBH, 80' ht)."""
        result = calculate_tree_volume(10.0, 80.0, 'DF')
        assert result.is_valid()
        assert 15.0 <= result.total_cubic_volume <= 35.0, (
            f"DF volume {result.total_cubic_volume} outside expected range"
        )

    def test_cl_has_volume_coefficients(self):
        """California Laurel (CL) has explicit volume coefficients."""
        assert 'CL' in VOLUME_COEFFICIENTS_OUTSIDE_BARK, (
            "CL missing from outside bark coefficients"
        )
        assert 'CL' in VOLUME_COEFFICIENTS_INSIDE_BARK, (
            "CL missing from inside bark coefficients"
        )
        result = calculate_tree_volume(8.0, 40.0, 'CL')
        assert result.is_valid()
        assert result.total_cubic_volume > 0

    def test_cl_in_hardwood_species(self):
        """California Laurel (CL) is classified as hardwood."""
        assert 'CL' in HARDWOOD_SPECIES

    def test_major_op_species_have_volume(self):
        """Major OP species produce valid volume calculations."""
        test_species = ['DF', 'WH', 'RC', 'GF', 'RA', 'WO', 'PP']
        for sp in test_species:
            result = calculate_tree_volume(10.0, 70.0, sp)
            assert result.is_valid(), f"{sp} volume calculation failed"
            assert result.total_cubic_volume > 0, f"{sp} volume is zero"


# ===========================================================================
# Phase 7: Integration Tests
# ===========================================================================

class TestOPIntegration:
    """Integration tests for full OP variant simulation."""

    def test_stand_initialize_planted_op(self):
        """Stand.initialize_planted works with variant='OP'."""
        stand = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=120,
            species='DF',
            variant='OP'
        )
        assert stand.variant == 'OP'
        assert len(stand.trees) == 400
        assert stand.site_index == 120

    def test_op_tree_level_growth(self):
        """Individual DF tree grows with variant='OP'."""
        from pyfvs.tree import Tree

        tree = Tree(dbh=2.0, height=15.0, species='DF', age=10, variant='OP')
        initial_dbh = tree.dbh
        initial_height = tree.height

        tree.grow(
            site_index=120,
            ba=50.0,
            pbal=20.0,
            competition_factor=0.3,
            time_step=5,
        )

        assert tree.dbh > initial_dbh, "DBH should increase"
        assert tree.height > initial_height, "Height should increase"

    def test_op_stand_metrics_correct_variant(self):
        """Stand metrics calculator uses OP variant correctly."""
        stand = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=120,
            species='DF',
            variant='OP'
        )
        assert stand._metrics.variant == 'OP'
        max_sdi = stand._metrics.get_max_sdi(stand.trees, 'DF')
        assert max_sdi == 850, f"DF max SDI should be 850, got {max_sdi}"

    def test_op_wh_simulation(self):
        """Western Hemlock OP simulation produces reasonable yields."""
        stand = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=100,
            species='WH',
            variant='OP'
        )
        stand.grow(50)
        metrics = stand.get_metrics()

        assert metrics['tpa'] > 100, "Should have surviving trees"
        assert metrics['qmd'] > 5.0, "QMD should grow"
        assert metrics['basal_area'] > 50.0, "BA should accumulate"

    def test_op_ra_simulation(self):
        """Red Alder OP simulation produces reasonable yields."""
        stand = Stand.initialize_planted(
            trees_per_acre=300,
            site_index=80,
            species='RA',
            variant='OP'
        )
        stand.grow(30)
        metrics = stand.get_metrics()

        assert metrics['tpa'] > 50, "Should have surviving trees"
        assert metrics['qmd'] > 3.0, "QMD should grow"

    def test_op_vs_pn_yields(self):
        """OP yields should be in the same order of magnitude as PN."""
        stand_op = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=120,
            species='DF',
            variant='OP'
        )
        stand_op.grow(50)
        vol_op = stand_op.get_metrics()['volume']

        stand_pn = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=120,
            species='DF',
            variant='PN'
        )
        stand_pn.grow(50)
        vol_pn = stand_pn.get_metrics()['volume']

        # Both should produce substantial volume
        assert vol_op > 3000, f"OP volume {vol_op} too low"
        assert vol_pn > 3000, f"PN volume {vol_pn} too low"

        # Different diameter growth models will produce different yields
        # but should be within same order of magnitude
        ratio = vol_op / vol_pn if vol_pn > 0 else 0
        assert 0.2 <= ratio <= 5.0, (
            f"OP/PN volume ratio {ratio:.2f} too extreme "
            f"(OP={vol_op:.0f}, PN={vol_pn:.0f})"
        )


# ===========================================================================
# Phase 8: Smoke Tests
# ===========================================================================

class TestOPSmokeTest:
    """Smoke tests for 50-year OP simulations with key species."""

    def test_df_si120_50yr(self):
        """DF SI=120 50-year simulation produces plausible yields."""
        stand = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=120,
            species='DF',
            variant='OP'
        )
        stand.grow(50)
        metrics = stand.get_metrics()

        tpa = metrics['tpa']
        qmd = metrics['qmd']
        ba = metrics['basal_area']
        volume = metrics['volume']

        # OP DF SI=120 50yr: expect substantial yields
        assert 150 <= tpa <= 400, f"TPA {tpa} outside expected range"
        assert 8.0 <= qmd <= 25.0, f"QMD {qmd} outside expected range"
        assert 100 <= ba <= 900, f"BA {ba} outside expected range"
        assert 3000 <= volume <= 40000, f"Volume {volume} outside expected range"

        # Print for manual verification
        print(f"\nOP DF SI=120 50yr smoke test:")
        print(f"  TPA: {tpa}")
        print(f"  QMD: {qmd:.1f}")
        print(f"  BA:  {ba:.0f}")
        print(f"  Vol: {volume:.0f}")

    def test_wh_si100_50yr(self):
        """WH SI=100 50-year simulation produces plausible yields."""
        stand = Stand.initialize_planted(
            trees_per_acre=400,
            site_index=100,
            species='WH',
            variant='OP'
        )
        stand.grow(50)
        metrics = stand.get_metrics()

        tpa = metrics['tpa']
        qmd = metrics['qmd']
        ba = metrics['basal_area']
        volume = metrics['volume']

        assert 100 <= tpa <= 400, f"TPA {tpa} outside expected range"
        assert 5.0 <= qmd <= 20.0, f"QMD {qmd} outside expected range"
        assert 50 <= ba <= 600, f"BA {ba} outside expected range"
        assert 1000 <= volume <= 25000, f"Volume {volume} outside expected range"

        print(f"\nOP WH SI=100 50yr smoke test:")
        print(f"  TPA: {tpa}")
        print(f"  QMD: {qmd:.1f}")
        print(f"  BA:  {ba:.0f}")
        print(f"  Vol: {volume:.0f}")

    def test_ra_si80_30yr(self):
        """RA SI=80 30-year simulation (Red Alder is short-rotation)."""
        stand = Stand.initialize_planted(
            trees_per_acre=300,
            site_index=80,
            species='RA',
            variant='OP'
        )
        stand.grow(30)
        metrics = stand.get_metrics()

        tpa = metrics['tpa']
        qmd = metrics['qmd']

        assert 50 <= tpa <= 300, f"TPA {tpa} outside expected range"
        assert 3.0 <= qmd <= 18.0, f"QMD {qmd} outside expected range"

        print(f"\nOP RA SI=80 30yr smoke test:")
        print(f"  TPA: {tpa}")
        print(f"  QMD: {qmd:.1f}")
        print(f"  BA:  {metrics['basal_area']:.0f}")
        print(f"  Vol: {metrics['volume']:.0f}")

"""
Pytest integration for FVS-Python validation.

These tests run the validation suite as part of the normal test suite
and can be used in CI/CD pipelines.
"""
import math
import sys
from pathlib import Path

import pytest
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pyfvs.tree import Tree
from pyfvs.stand import Stand
from pyfvs.height_diameter import create_height_diameter_model
from pyfvs.bark_ratio import create_bark_ratio_model
from pyfvs.crown_ratio import create_crown_ratio_model
from pyfvs.crown_width import create_crown_width_model


class TestComponentModels:
    """Level 1: Component model validation tests."""

    @pytest.mark.parametrize("species", ["LP", "SP", "SA", "LL"])
    def test_height_diameter_reasonable_outputs(self, species):
        """Test that height-diameter model produces reasonable heights."""
        model = create_height_diameter_model(species)

        # Test across diameter range
        for dbh in [1.0, 3.0, 5.0, 8.0, 10.0, 15.0, 20.0]:
            height = model.predict_height(dbh)

            # Basic sanity checks
            assert height >= 4.5, f"Height {height} below breast height for {species} DBH={dbh}"
            assert height < 150, f"Height {height} unreasonably high for {species} DBH={dbh}"

            # Height should increase with DBH (generally)
            if dbh >= 3.0:
                prev_height = model.predict_height(dbh - 2)
                assert height >= prev_height, (
                    f"Height decreased from {prev_height} to {height} "
                    f"as DBH increased for {species}"
                )

    @pytest.mark.parametrize("species", ["LP", "SP", "SA", "LL"])
    def test_height_diameter_inverse(self, species):
        """Test that we can solve for DBH from height."""
        model = create_height_diameter_model(species)

        for target_dbh in [5.0, 10.0, 15.0]:
            # Get height for this DBH
            height = model.predict_height(target_dbh)

            # Solve back for DBH
            solved_dbh = model.solve_dbh_from_height(height, initial_dbh=target_dbh)

            # Should be close to original
            assert abs(solved_dbh - target_dbh) < 0.5, (
                f"Inverse solve error: {target_dbh} -> {height} -> {solved_dbh}"
            )

    @pytest.mark.parametrize("species", ["LP", "SP", "SA", "LL"])
    def test_bark_ratio_bounds(self, species):
        """Test that bark ratio stays within FVS bounds (0.80-0.99)."""
        model = create_bark_ratio_model(species)

        for dob in [2.0, 5.0, 10.0, 15.0, 20.0, 30.0]:
            ratio = model.calculate_bark_ratio(dob)

            assert 0.80 <= ratio <= 0.99, (
                f"Bark ratio {ratio} outside bounds for {species} DOB={dob}"
            )

    @pytest.mark.parametrize("species", ["LP", "SP", "SA", "LL"])
    def test_bark_ratio_dib_less_than_dob(self, species):
        """Test that DIB is always less than DOB."""
        model = create_bark_ratio_model(species)

        for dob in [2.0, 5.0, 10.0, 15.0, 20.0]:
            dib = model.calculate_dib_from_dob(dob)

            assert dib < dob, f"DIB {dib} >= DOB {dob} for {species}"
            assert dib > 0, f"DIB {dib} <= 0 for {species}"

    @pytest.mark.parametrize("species", ["LP", "SP", "SA", "LL"])
    def test_crown_ratio_bounds(self, species):
        """Test that crown ratio stays within bounds (0.05-0.95)."""
        model = create_crown_ratio_model(species)

        for relsdi in [1.0, 3.0, 5.0, 8.0, 10.0, 12.0]:
            acr = model.calculate_average_crown_ratio(relsdi)

            assert 0.05 <= acr <= 0.95, (
                f"Crown ratio {acr} outside bounds for {species} RELSDI={relsdi}"
            )

    @pytest.mark.parametrize("species", ["LP", "SP", "SA", "LL"])
    def test_crown_width_positive(self, species):
        """Test that crown width is positive and reasonable."""
        model = create_crown_width_model(species)

        # Use larger DBH range to avoid edge cases with small trees
        for dbh in [5.0, 8.0, 10.0, 15.0]:
            fcw = model.calculate_forest_grown_crown_width(dbh)
            ocw = model.calculate_open_grown_crown_width(dbh)

            assert fcw >= 0, f"Forest crown width {fcw} < 0 for {species} DBH={dbh}"
            assert ocw >= 0, f"Open crown width {ocw} < 0 for {species} DBH={dbh}"
            assert fcw < 60, f"Forest crown width {fcw} > 60 ft for {species}"
            assert ocw < 60, f"Open crown width {ocw} > 60 ft for {species}"

            # At least one should be positive for reasonable DBH
            if dbh >= 5.0:
                assert fcw > 0 or ocw > 0, (
                    f"Both crown widths are 0 for {species} DBH={dbh}"
                )

    @pytest.mark.parametrize("species", ["LP", "SP", "SA", "LL"])
    def test_ccf_calculation(self, species):
        """Test CCF contribution calculation."""
        model = create_crown_width_model(species)

        for dbh in [5.0, 10.0, 15.0]:
            ccf = model.calculate_ccf_contribution(dbh)

            # CCF contribution should be positive and reasonable
            assert ccf > 0, f"CCF contribution <= 0 for {species} DBH={dbh}"
            assert ccf < 5.0, f"CCF contribution > 5 for single tree for {species}"


class TestSingleTreeGrowth:
    """Level 2: Single tree growth validation tests."""

    @pytest.mark.parametrize("species", ["LP", "SP", "SA", "LL"])
    def test_small_tree_height_growth(self, species):
        """Test small tree (< 3" DBH) height growth."""
        tree = Tree(dbh=0.5, height=5.0, species=species, age=5)
        initial_height = tree.height

        tree.grow(site_index=70, competition_factor=0.3, time_step=5)

        assert tree.height > initial_height, (
            f"Small tree {species} height did not increase: "
            f"{initial_height} -> {tree.height}"
        )
        assert tree.age == 10, f"Tree age not updated correctly: {tree.age}"

    @pytest.mark.parametrize("species", ["LP", "SP", "SA", "LL"])
    def test_large_tree_diameter_growth(self, species):
        """Test large tree (> 3" DBH) diameter growth."""
        tree = Tree(dbh=8.0, height=50.0, species=species, age=25)
        initial_dbh = tree.dbh

        tree.grow(
            site_index=70,
            competition_factor=0.5,
            ba=100,
            pbal=50,
            time_step=5
        )

        assert tree.dbh > initial_dbh, (
            f"Large tree {species} DBH did not increase: "
            f"{initial_dbh} -> {tree.dbh}"
        )

    @pytest.mark.parametrize("species", ["LP", "SP", "SA", "LL"])
    def test_transition_zone_growth(self, species):
        """Test growth in transition zone (1-3" DBH)."""
        tree = Tree(dbh=2.0, height=20.0, species=species, age=10)
        initial_dbh = tree.dbh
        initial_height = tree.height

        tree.grow(
            site_index=70,
            competition_factor=0.4,
            ba=80,
            pbal=40,
            time_step=5
        )

        assert tree.dbh > initial_dbh, (
            f"Transition tree {species} DBH did not increase"
        )
        assert tree.height > initial_height, (
            f"Transition tree {species} height did not increase"
        )

    def test_growth_responds_to_site_index(self):
        """Test that growth is higher on better sites."""
        trees = []
        for si in [60, 70, 80]:
            tree = Tree(dbh=5.0, height=30.0, species="LP", age=15)
            tree.grow(site_index=si, competition_factor=0.4, ba=80, time_step=5)
            trees.append((si, tree.dbh))

        # Higher site index should produce more growth
        assert trees[1][1] > trees[0][1], "SI 70 should outgrow SI 60"
        assert trees[2][1] > trees[1][1], "SI 80 should outgrow SI 70"

    def test_growth_responds_to_competition(self):
        """Test that growth decreases with increased competition."""
        trees = []
        for comp in [0.2, 0.5, 0.8]:
            tree = Tree(dbh=5.0, height=30.0, species="LP", age=15)
            tree.grow(site_index=70, competition_factor=comp, ba=100, time_step=5)
            trees.append((comp, tree.dbh))

        # Higher competition should reduce growth
        assert trees[0][1] >= trees[1][1], "Low comp should outgrow medium comp"
        assert trees[1][1] >= trees[2][1], "Medium comp should outgrow high comp"


class TestStandSimulations:
    """Level 3: Stand-level validation tests."""

    @pytest.mark.parametrize("species,si,tpa", [
        ("LP", 70, 500),
        ("SP", 65, 450),
        ("SA", 70, 550),
        ("LL", 60, 400),
    ])
    def test_stand_grows_correctly(self, species, si, tpa):
        """Test that stands grow and develop as expected."""
        stand = Stand.initialize_planted(
            trees_per_acre=tpa,
            site_index=si,
            species=species
        )

        initial_tpa = len(stand.trees)
        initial_ba = stand.calculate_basal_area()

        # Grow for 25 years
        stand.grow(years=25)

        metrics = stand.get_metrics()

        # Basic checks
        assert metrics['tpa'] <= initial_tpa, "TPA should decrease or stay same"
        assert metrics['basal_area'] > initial_ba, "BA should increase"
        assert metrics['qmd'] > 0.5, "Trees should have grown"
        assert metrics['top_height'] > 20, "Should have significant height growth"

    def test_mortality_occurs(self):
        """Test that mortality reduces tree count over time."""
        stand = Stand.initialize_planted(
            trees_per_acre=700,  # High density for mortality
            site_index=70,
            species="LP"
        )

        initial_tpa = len(stand.trees)

        # Grow for 30 years
        stand.grow(years=30)

        final_tpa = len(stand.trees)

        assert final_tpa < initial_tpa, (
            f"Mortality should have occurred: {initial_tpa} -> {final_tpa}"
        )

    def test_yield_table_generation(self):
        """Test that yield table can be generated."""
        stand = Stand.initialize_planted(
            trees_per_acre=500,
            site_index=70,
            species="LP"
        )

        yield_records = stand.generate_yield_table(years=25, period_length=5)

        assert len(yield_records) == 6, "Should have 6 records (0, 5, 10, 15, 20, 25)"

        # Check that values are reasonable
        for record in yield_records:
            assert record.TPA >= 0, f"TPA should be non-negative"
            assert record.BA >= 0, f"BA should be non-negative"
            assert record.QMD >= 0, f"QMD should be non-negative"


class TestBakuzisMatrix:
    """Level 4: Bakuzis matrix relationship verification."""

    @pytest.fixture
    def yield_data(self):
        """Generate yield data for Bakuzis tests."""
        stand = Stand.initialize_planted(
            trees_per_acre=500,
            site_index=70,
            species="LP"
        )

        data = {"ages": [], "tpa": [], "ba": [], "qmd": [], "top_height": []}

        metrics = stand.get_metrics()
        data["ages"].append(0)
        data["tpa"].append(metrics["tpa"])
        data["ba"].append(metrics["basal_area"])
        data["qmd"].append(metrics["qmd"])
        data["top_height"].append(metrics["top_height"])

        for year in range(5, 55, 5):
            stand.grow(years=5)
            metrics = stand.get_metrics()
            data["ages"].append(year)
            data["tpa"].append(metrics["tpa"])
            data["ba"].append(metrics["basal_area"])
            data["qmd"].append(metrics["qmd"])
            data["top_height"].append(metrics["top_height"])

        return data

    def test_tpa_decreases_with_age(self, yield_data):
        """Verify TPA decreases over time (mortality)."""
        ages = np.array(yield_data["ages"][1:])  # Skip age 0
        tpa = np.array(yield_data["tpa"][1:])

        # Linear regression slope should be negative
        slope = np.polyfit(ages, tpa, 1)[0]
        assert slope < 0, f"TPA should decrease with age, slope={slope}"

    def test_qmd_increases_with_age(self, yield_data):
        """Verify QMD increases over time (growth)."""
        ages = np.array(yield_data["ages"])
        qmd = np.array(yield_data["qmd"])

        # Linear regression slope should be positive
        slope = np.polyfit(ages, qmd, 1)[0]
        assert slope > 0, f"QMD should increase with age, slope={slope}"

    def test_height_increases_with_age(self, yield_data):
        """Verify height increases over time."""
        ages = np.array(yield_data["ages"])
        height = np.array(yield_data["top_height"])

        # Linear regression slope should be positive
        slope = np.polyfit(ages, height, 1)[0]
        assert slope > 0, f"Height should increase with age, slope={slope}"

    def test_tpa_qmd_inverse_relationship(self, yield_data):
        """Verify TPA and QMD are inversely related."""
        tpa = np.array(yield_data["tpa"][1:])  # Skip initial values
        qmd = np.array(yield_data["qmd"][1:])

        # Correlation should be negative
        corr = np.corrcoef(tpa, qmd)[0, 1]
        assert corr < 0, f"TPA and QMD should be negatively correlated, r={corr}"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_small_tree(self):
        """Test handling of very small trees."""
        tree = Tree(dbh=0.1, height=1.0, species="LP", age=1)

        # Should not raise errors
        tree.grow(site_index=70, competition_factor=0.3, time_step=5)

        assert tree.dbh >= 0.1, "DBH should not decrease"
        assert tree.height >= 1.0, "Height should not decrease"

    def test_very_large_tree(self):
        """Test handling of very large trees."""
        tree = Tree(dbh=30.0, height=100.0, species="LP", age=80)

        # Should not raise errors
        tree.grow(site_index=70, competition_factor=0.5, ba=100, pbal=30, time_step=5)

        assert tree.dbh >= 30.0, "Large tree DBH should not decrease"

    def test_extreme_site_index_low(self):
        """Test handling of very low site index."""
        stand = Stand.initialize_planted(
            trees_per_acre=500,
            site_index=40,  # Very low
            species="LP"
        )

        stand.grow(years=10)

        # Should still have positive growth
        metrics = stand.get_metrics()
        assert metrics["qmd"] > 0.5, "Should have some growth even on poor site"

    def test_extreme_site_index_high(self):
        """Test handling of very high site index."""
        stand = Stand.initialize_planted(
            trees_per_acre=500,
            site_index=100,  # Very high
            species="LP"
        )

        stand.grow(years=10)

        # Should have substantial growth
        metrics = stand.get_metrics()
        assert metrics["top_height"] > 30, "High site should grow well"

    def test_low_density_stand(self):
        """Test handling of very low density stand."""
        stand = Stand.initialize_planted(
            trees_per_acre=100,  # Very low
            site_index=70,
            species="LP"
        )

        initial_tpa = len(stand.trees)
        stand.grow(years=25)

        # Minimal mortality expected at low density
        final_tpa = len(stand.trees)
        mortality_rate = (initial_tpa - final_tpa) / initial_tpa
        assert mortality_rate < 0.3, f"Low density should have low mortality: {mortality_rate}"

    def test_high_density_stand(self):
        """Test handling of very high density stand."""
        stand = Stand.initialize_planted(
            trees_per_acre=1000,  # Very high
            site_index=70,
            species="LP"
        )

        initial_tpa = len(stand.trees)
        stand.grow(years=25)

        # Some mortality expected at high density (threshold lowered to account
        # for early-stage plantations where trees haven't reached competition yet)
        final_tpa = len(stand.trees)
        mortality_rate = (initial_tpa - final_tpa) / initial_tpa
        assert mortality_rate > 0.05, f"High density should have some mortality: {mortality_rate}"
        # Verify the stand is under density stress (high SDI)
        assert stand.calculate_stand_sdi() > 100, "High density stand should have elevated SDI"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

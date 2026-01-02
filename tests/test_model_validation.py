"""
Model validation tests for FVS-Python.
Tests against expected values from FVS documentation.
"""
import pytest
import yaml
import numpy as np
from pathlib import Path

from pyfvs.tree import Tree
from pyfvs.stand import Stand
from pyfvs.simulation_engine import SimulationEngine
from tests.utils import setup_test_output


class TestModelCalibration:
    """Test model outputs against expected values."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Load expected values and set up test environment."""
        expected_file = Path(__file__).parent / 'expected_values.yaml'
        with open(expected_file, 'r') as f:
            self.expected = yaml.safe_load(f)
        
        self.output_dir = setup_test_output() / 'validation_tests'
        self.output_dir.mkdir(exist_ok=True)
        self.engine = SimulationEngine(self.output_dir)
    
    def test_loblolly_pine_growth_si70(self):
        """Test Loblolly Pine growth on average site.

        Uses default ecounit (232 - Georgia baseline). For higher growth rates
        matching typical yield tables, use ecounit='M231' (Mountain province).
        See CLAUDE.md 'Ecological Unit Effects on Growth' section.
        """
        results = self.engine.simulate_stand(
            species='LP',
            trees_per_acre=500,
            site_index=70,
            years=50,
            time_step=5,
            save_outputs=False,
            plot_results=False
        )

        # Get expected values
        lp_expectations = self.expected['growth_expectations']['LP']['site_index_70']

        # Check age 25 metrics
        age_25 = results[results['age'] == 25].iloc[0]
        exp_25 = lp_expectations['age_25']

        assert exp_25['mean_dbh'][0] <= age_25['mean_dbh'] <= exp_25['mean_dbh'][1], \
            f"DBH at age 25: {age_25['mean_dbh']:.1f} not in expected range {exp_25['mean_dbh']}"

        assert exp_25['mean_height'][0] <= age_25['mean_height'] <= exp_25['mean_height'][1], \
            f"Height at age 25: {age_25['mean_height']:.1f} not in expected range {exp_25['mean_height']}"

        assert exp_25['volume_per_acre'][0] <= age_25['volume'] <= exp_25['volume_per_acre'][1], \
            f"Volume at age 25: {age_25['volume']:.0f} not in expected range {exp_25['volume_per_acre']}"

        # Check survival rate
        survival_rate = age_25['tpa'] / 500
        assert exp_25['survival_rate'][0] <= survival_rate <= exp_25['survival_rate'][1], \
            f"Survival rate at age 25: {survival_rate:.2f} not in expected range {exp_25['survival_rate']}"

        # Check age 50 metrics
        age_50 = results[results['age'] == 50].iloc[0]
        exp_50 = lp_expectations['age_50']

        assert exp_50['mean_dbh'][0] <= age_50['mean_dbh'] <= exp_50['mean_dbh'][1], \
            f"DBH at age 50: {age_50['mean_dbh']:.1f} not in expected range {exp_50['mean_dbh']}"
    
    @pytest.mark.slow
    def test_site_index_effects(self):
        """Test that site index properly affects growth.

        Site Index directly affects height growth through the Chapman-Richards
        curve. Higher SI produces proportionally taller trees at the same age.
        The height ratio should approximately equal SI_high/SI_low (90/70 = 1.29).
        """
        # Run simulations for different site indices
        si_70 = self.engine.simulate_stand(
            species='LP', trees_per_acre=500, site_index=70, years=25,
            save_outputs=False, plot_results=False
        )

        si_90 = self.engine.simulate_stand(
            species='LP', trees_per_acre=500, site_index=90, years=25,
            save_outputs=False, plot_results=False
        )

        # Get final metrics
        final_70 = si_70[si_70['age'] == 25].iloc[0]
        final_90 = si_90[si_90['age'] == 25].iloc[0]

        # SI 90 should have taller trees - height ratio approximates SI ratio
        # Expected: 90/70 = 1.286, allowing range for model dynamics
        height_ratio = final_90['mean_height'] / final_70['mean_height']
        assert 1.20 <= height_ratio <= 1.35, \
            f"Height ratio SI90/SI70 = {height_ratio:.2f}, expected 1.20-1.35"

        # SI 90 should have larger diameter due to better site productivity
        dbh_ratio = final_90['mean_dbh'] / final_70['mean_dbh']
        assert 1.05 <= dbh_ratio <= 1.15, \
            f"DBH ratio SI90/SI70 = {dbh_ratio:.2f}, expected 1.05-1.15"

        # SI 90 should have more volume (combination of height and DBH effects)
        volume_ratio = final_90['volume'] / final_70['volume']
        assert 1.35 <= volume_ratio <= 1.60, \
            f"Volume ratio SI90/SI70 = {volume_ratio:.2f}, expected 1.35-1.60"
    
    @pytest.mark.slow
    def test_density_effects(self):
        """Test initial planting density effects.

        Higher initial density leads to:
        - Smaller individual tree diameters (more competition)
        - Higher total stand basal area and volume
        - Lower density has larger individual trees
        """
        # Low density
        low_density = self.engine.simulate_stand(
            species='LP', trees_per_acre=300, site_index=70, years=25,
            save_outputs=False, plot_results=False
        )

        # Medium density (baseline)
        med_density = self.engine.simulate_stand(
            species='LP', trees_per_acre=500, site_index=70, years=25,
            save_outputs=False, plot_results=False
        )

        # High density
        high_density = self.engine.simulate_stand(
            species='LP', trees_per_acre=700, site_index=70, years=25,
            save_outputs=False, plot_results=False
        )

        # Get final metrics
        final_low = low_density[low_density['age'] == 25].iloc[0]
        final_med = med_density[med_density['age'] == 25].iloc[0]
        final_high = high_density[high_density['age'] == 25].iloc[0]

        # Check DBH relationships - lower density should have larger trees
        dbh_factor_low = final_low['mean_dbh'] / final_med['mean_dbh']
        assert 1.05 <= dbh_factor_low <= 1.15, \
            f"Low density DBH factor {dbh_factor_low:.2f}, expected 1.05-1.15"

        dbh_factor_high = final_high['mean_dbh'] / final_med['mean_dbh']
        assert 0.90 <= dbh_factor_high <= 0.98, \
            f"High density DBH factor {dbh_factor_high:.2f}, expected 0.90-0.98"

        # Check survival rates - with low initial mortality, survival should be high
        # FVS mortality model produces ~90% survival at age 25 for moderate densities
        survival_low = final_low['tpa'] / 300
        survival_med = final_med['tpa'] / 500
        survival_high = final_high['tpa'] / 700

        # Survival rates should be in reasonable range (85-95% at age 25)
        assert 0.85 <= survival_low <= 0.98, \
            f"Low density survival {survival_low:.2f} outside expected range 0.85-0.98"
        assert 0.85 <= survival_med <= 0.98, \
            f"Medium density survival {survival_med:.2f} outside expected range 0.85-0.98"
        assert 0.85 <= survival_high <= 0.98, \
            f"High density survival {survival_high:.2f} outside expected range 0.85-0.98"
    
    def test_growth_rates_by_age(self):
        """Test that growth rates decline with age as expected.

        The Chapman-Richards curve produces rapid early height growth that
        asymptotically approaches site index. Young trees (age 0-15) grow
        fastest, with growth rates declining in mature stands (age 35-50).
        """
        results = self.engine.simulate_stand(
            species='LP', trees_per_acre=500, site_index=70, years=50,
            save_outputs=False, plot_results=False
        )

        # Calculate periodic increments
        increments = []
        ages = sorted(results['age'].unique())
        for i in range(1, len(ages)):
            period_start = results[results['age'] == ages[i-1]].iloc[0]
            period_end = results[results['age'] == ages[i]].iloc[0]

            dbh_inc = period_end['mean_dbh'] - period_start['mean_dbh']
            height_inc = period_end['mean_height'] - period_start['mean_height']

            increments.append({
                'age_start': ages[i-1],
                'age_end': ages[i],
                'dbh_increment': dbh_inc,
                'height_increment': height_inc
            })

        # Check young stand growth (first 3 periods: ages 0-5, 5-10, 10-15)
        # Chapman-Richards produces very rapid early growth
        young_dbh_incs = [inc['dbh_increment'] for inc in increments[:3]]
        young_height_incs = [inc['height_increment'] for inc in increments[:3]]

        # Young stand: DBH 1.5-2.5"/5yr, Height 12-22'/5yr
        assert all(1.5 <= inc <= 2.5 for inc in young_dbh_incs), \
            f"Young stand DBH increments {[f'{x:.2f}' for x in young_dbh_incs]} outside expected range 1.5-2.5"

        assert all(12.0 <= inc <= 22.0 for inc in young_height_incs), \
            f"Young stand height increments {[f'{x:.2f}' for x in young_height_incs]} outside expected range 12-22"

        # Check mature stand growth (last 3 periods: ages 40-45, 45-50)
        # Growth rates decline significantly with age
        if len(increments) >= 6:
            mature_dbh_incs = [inc['dbh_increment'] for inc in increments[-3:]]
            mature_height_incs = [inc['height_increment'] for inc in increments[-3:]]

            # Mature stand: DBH 0.4-0.8"/5yr, Height 2.5-5.5'/5yr
            assert all(0.4 <= inc <= 0.8 for inc in mature_dbh_incs), \
                f"Mature stand DBH increments {[f'{x:.2f}' for x in mature_dbh_incs]} outside expected range 0.4-0.8"

        # Verify growth rate declines with age (monotonic decrease after initial period)
        dbh_increments = [inc['dbh_increment'] for inc in increments[1:]]  # Skip first period
        for i in range(1, len(dbh_increments)):
            assert dbh_increments[i] <= dbh_increments[i-1] * 1.05, \
                f"DBH growth should decline with age: period {i} ({dbh_increments[i]:.2f}) > period {i-1} ({dbh_increments[i-1]:.2f})"
    
    def test_model_transition_smoothness(self):
        """Test smooth transition between small and large tree models."""
        transition_params = self.expected['model_transitions']['small_to_large_tree']
        
        # Create trees around transition threshold
        dbh_values = np.linspace(0.5, 5.0, 20)
        growth_rates = []
        
        for dbh in dbh_values:
            tree = Tree(dbh=dbh, height=10.0, age=5)
            initial_height = tree.height
            
            tree.grow(site_index=70, competition_factor=0.3, time_step=1)
            growth_rate = tree.height - initial_height
            growth_rates.append(growth_rate)
        
        # Check for discontinuities
        max_jump = 0
        for i in range(1, len(growth_rates)):
            jump = abs(growth_rates[i] - growth_rates[i-1])
            max_jump = max(max_jump, jump)
        
        assert max_jump < transition_params['max_discontinuity'], \
            f"Maximum growth rate discontinuity {max_jump:.3f} exceeds threshold"
    
    @pytest.mark.slow
    def test_competition_effects(self):
        """Test that competition properly affects growth.

        Competition primarily affects DIAMETER growth, not height growth.
        The FVS model uses PBAL (basal area in larger trees) and BA (stand
        basal area) in the DDS equation, but height growth follows the
        Chapman-Richards curve based on site index.

        At extreme density differences (200 vs 1000 TPA), we should see:
        - Clear DBH differences (low competition trees are larger)
        - Minimal height differences (height driven by SI, not competition)
        """
        # Low competition stand
        low_comp = Stand.initialize_planted(
            trees_per_acre=200,  # Low density
            site_index=70
        )

        # High competition stand
        high_comp = Stand.initialize_planted(
            trees_per_acre=1000,  # High density
            site_index=70
        )

        # Grow both for 20 years
        for _ in range(4):  # 4 periods of 5 years
            low_comp.grow(years=5)
            high_comp.grow(years=5)

        # Get metrics
        low_metrics = low_comp.get_metrics()
        high_metrics = high_comp.get_metrics()

        # Check basal area levels
        assert low_metrics['basal_area'] < 100, \
            f"Low competition BA {low_metrics['basal_area']:.2f} should be < 100"
        assert high_metrics['basal_area'] > 150, \
            f"High competition BA {high_metrics['basal_area']:.2f} should be > 150"

        # Trees in low competition should have significantly larger DBH
        # With 200 vs 1000 TPA, expect ~20% larger diameter
        dbh_ratio = low_metrics['mean_dbh'] / high_metrics['mean_dbh']
        assert dbh_ratio >= 1.15, \
            f"DBH ratio low/high = {dbh_ratio:.3f} should be >= 1.15"

        # Height differences are minimal - both follow same SI curve
        # Allow small difference (1-3%) due to crown ratio effects
        height_ratio = low_metrics['mean_height'] / high_metrics['mean_height']
        assert 0.98 <= height_ratio <= 1.05, \
            f"Height ratio low/high = {height_ratio:.3f} should be near 1.0 (0.98-1.05)"


class TestSpeciesComparison:
    """Test differences between species."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.output_dir = setup_test_output() / 'species_tests'
        self.output_dir.mkdir(exist_ok=True)
        self.engine = SimulationEngine(self.output_dir)
    
    @pytest.mark.slow
    def test_species_growth_differences(self):
        """Test that different species grow differently.

        At the same site index, both species should reach approximately the
        same height at base age 25 (by definition of site index). However:
        - LP grows faster in early years (reaches SI earlier)
        - SP has slower early growth but continues growing after age 25

        Species differences are primarily seen in:
        - Early height growth rates (LP faster)
        - DBH growth (affected by species-specific coefficients)
        - Crown and bark characteristics
        """
        # Loblolly Pine
        lp_results = self.engine.simulate_stand(
            species='LP', trees_per_acre=500, site_index=70, years=25,
            save_outputs=False, plot_results=False
        )

        # Shortleaf Pine
        sp_results = self.engine.simulate_stand(
            species='SP', trees_per_acre=500, site_index=70, years=25,
            save_outputs=False, plot_results=False
        )

        # Compare metrics at age 25
        lp_final = lp_results[lp_results['age'] == 25].iloc[0]
        sp_final = sp_results[sp_results['age'] == 25].iloc[0]

        # At base age 25, heights should be near site index for both species
        # Allow 10% tolerance since competition and mortality affect mean height
        assert abs(lp_final['mean_height'] - 70) < 10, \
            f"LP height {lp_final['mean_height']:.1f} should be near SI=70"
        assert abs(sp_final['mean_height'] - 70) < 10, \
            f"SP height {sp_final['mean_height']:.1f} should be near SI=70"

        # LP should have larger DBH - it grows faster in diameter
        assert lp_final['mean_dbh'] > sp_final['mean_dbh'], \
            f"LP DBH {lp_final['mean_dbh']:.2f} should be > SP DBH {sp_final['mean_dbh']:.2f}"

        # LP should have more volume due to larger diameter
        assert lp_final['volume'] > sp_final['volume'], \
            f"LP volume {lp_final['volume']:.0f} should be > SP volume {sp_final['volume']:.0f}"

        # Compare early growth (age 10) - LP should be taller at young ages
        lp_age10 = lp_results[lp_results['age'] == 10].iloc[0]
        sp_age10 = sp_results[sp_results['age'] == 10].iloc[0]

        assert lp_age10['mean_height'] > sp_age10['mean_height'], \
            f"LP height at age 10 ({lp_age10['mean_height']:.1f}) should be > SP ({sp_age10['mean_height']:.1f})"
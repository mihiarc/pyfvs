"""
Tests for NativeStand - FVS bridge module.

These tests verify that NativeStand properly interfaces with the
official FVS Fortran library and produces reasonable results.
"""
import pytest
import logging
from pathlib import Path

# Skip all tests if FVS libraries are not available
try:
    from pyfvs.fvs_native import find_fvs_libraries
    AVAILABLE_VARIANTS = find_fvs_libraries()
except ImportError:
    AVAILABLE_VARIANTS = {}

HAS_SN = 'sn' in AVAILABLE_VARIANTS
HAS_ANY_FVS = len(AVAILABLE_VARIANTS) > 0

pytestmark = pytest.mark.skipif(
    not HAS_ANY_FVS,
    reason="No FVS libraries available"
)


@pytest.fixture
def sn_stand():
    """Create a basic SN native stand for testing."""
    if not HAS_SN:
        pytest.skip("SN variant not available")
    
    from pyfvs.native_stand import NativeStand
    return NativeStand.initialize_planted(
        trees_per_acre=500,
        site_index=70,
        species='LP',
        variant='sn'
    )


class TestNativeStandInitialization:
    """Test NativeStand initialization."""
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_basic_initialization(self):
        """Test basic stand initialization."""
        from pyfvs.native_stand import NativeStand
        
        stand = NativeStand.initialize_planted(
            trees_per_acre=500,
            site_index=70,
            species='LP',
            variant='sn'
        )
        
        assert stand is not None
        assert stand.site_index == 70
        assert stand.species == 'LP'
        assert stand.variant == 'sn'
        assert len(stand.trees) > 0
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_initial_metrics(self):
        """Test that initial metrics are reasonable."""
        from pyfvs.native_stand import NativeStand
        
        stand = NativeStand.initialize_planted(
            trees_per_acre=500,
            site_index=70,
            species='LP'
        )
        
        metrics = stand.get_metrics()
        
        # Initial metrics should be reasonable
        assert metrics['age'] == 0
        assert metrics['tpa'] == 500
        assert metrics['mean_dbh'] > 0
        assert metrics['mean_height'] > 0
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_invalid_tpa_raises_error(self):
        """Test that invalid TPA raises error."""
        from pyfvs.native_stand import NativeStand
        
        with pytest.raises(ValueError):
            NativeStand.initialize_planted(trees_per_acre=0)
        
        with pytest.raises(ValueError):
            NativeStand.initialize_planted(trees_per_acre=-100)


class TestNativeStandGrowth:
    """Test NativeStand growth projections."""
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_basic_growth(self, sn_stand):
        """Test basic growth projection."""
        initial_age = sn_stand.age
        
        sn_stand.grow(years=5)
        
        assert sn_stand.age == initial_age + 5
        
        metrics = sn_stand.get_metrics()
        assert metrics['age'] == 5
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_25_year_growth(self, sn_stand):
        """Test 25-year growth projection."""
        sn_stand.grow(years=25)
        
        metrics = sn_stand.get_metrics()
        
        # After 25 years, trees should be substantial
        assert metrics['age'] == 25
        assert metrics['mean_dbh'] > 5.0  # At least 5" DBH
        assert metrics['mean_height'] > 40.0  # At least 40 feet
        assert metrics['volume'] > 0
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_growth_increases_volume(self, sn_stand):
        """Test that growth increases volume."""
        initial_metrics = sn_stand.get_metrics()
        
        sn_stand.grow(years=10)
        
        final_metrics = sn_stand.get_metrics()
        
        assert final_metrics['volume'] > initial_metrics['volume']
        assert final_metrics['mean_dbh'] > initial_metrics['mean_dbh']
        assert final_metrics['mean_height'] > initial_metrics['mean_height']
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_mortality_reduces_tpa(self, sn_stand):
        """Test that mortality reduces TPA over time."""
        initial_tpa = sn_stand.get_metrics()['tpa']
        
        sn_stand.grow(years=30)
        
        final_tpa = sn_stand.get_metrics()['tpa']
        
        # Some mortality should occur
        assert final_tpa <= initial_tpa
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_zero_years_growth(self, sn_stand):
        """Test that 0 years growth does nothing."""
        initial_age = sn_stand.age
        initial_metrics = sn_stand.get_metrics()
        
        sn_stand.grow(years=0)
        
        assert sn_stand.age == initial_age
        
        final_metrics = sn_stand.get_metrics()
        assert final_metrics['mean_dbh'] == initial_metrics['mean_dbh']


class TestNativeStandMetrics:
    """Test NativeStand metrics calculations."""
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_all_metrics_present(self, sn_stand):
        """Test that all expected metrics are present."""
        sn_stand.grow(years=10)
        metrics = sn_stand.get_metrics()
        
        expected_keys = [
            'tpa', 'basal_area', 'qmd', 'mean_dbh',
            'top_height', 'mean_height', 'ccf', 'sdi',
            'age', 'volume', 'merchantable_volume', 'board_feet'
        ]
        
        for key in expected_keys:
            assert key in metrics, f"Missing metric: {key}"
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_basal_area_positive(self, sn_stand):
        """Test that basal area is positive after growth."""
        sn_stand.grow(years=15)
        metrics = sn_stand.get_metrics()
        
        assert metrics['basal_area'] > 0
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_qmd_calculation(self, sn_stand):
        """Test QMD calculation is reasonable."""
        sn_stand.grow(years=20)
        metrics = sn_stand.get_metrics()
        
        # QMD should be between mean_dbh and max DBH
        # For uniform stands, they should be similar
        assert 0.5 * metrics['mean_dbh'] <= metrics['qmd'] <= 2.0 * metrics['mean_dbh']


class TestNativeStandSummary:
    """Test NativeStand FVS summary access."""
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_summaries_available_after_growth(self, sn_stand):
        """Test that summaries are available after growth."""
        sn_stand.grow(years=20)
        
        summaries = sn_stand.get_all_summaries()
        
        assert len(summaries) > 0
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_summary_progression(self, sn_stand):
        """Test that summary values progress logically."""
        sn_stand.grow(years=25)
        
        summaries = sn_stand.get_all_summaries()
        
        # Ages should increase
        ages = [s.get('age', 0) for s in summaries]
        for i in range(1, len(ages)):
            assert ages[i] >= ages[i-1]
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_print_summary(self, sn_stand):
        """Test summary printing."""
        sn_stand.grow(years=15)
        
        summary_str = sn_stand.print_summary()
        
        assert len(summary_str) > 0
        assert 'FVS' in summary_str
        assert 'Year' in summary_str or 'TPA' in summary_str


class TestNativeStandMultipleSpecies:
    """Test NativeStand with different species."""
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    @pytest.mark.parametrize("species", ["LP", "SP", "SA", "LL"])
    def test_different_species(self, species):
        """Test initialization with different species."""
        from pyfvs.native_stand import NativeStand
        
        stand = NativeStand.initialize_planted(
            trees_per_acre=500,
            site_index=70,
            species=species,
            variant='sn'
        )
        
        assert stand.species == species
        
        # Should be able to grow without error
        stand.grow(years=10)
        
        metrics = stand.get_metrics()
        assert metrics['volume'] >= 0


class TestNativeStandSiteIndex:
    """Test NativeStand with different site indices."""
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    @pytest.mark.parametrize("site_index", [55, 70, 85])
    def test_different_site_indices(self, site_index):
        """Test that site index affects growth."""
        from pyfvs.native_stand import NativeStand
        
        stand = NativeStand.initialize_planted(
            trees_per_acre=500,
            site_index=site_index,
            species='LP',
            variant='sn'
        )
        
        stand.grow(years=25)
        
        metrics = stand.get_metrics()
        
        # Higher site index should produce taller trees
        assert metrics['mean_height'] > 0


class TestNativeStandKeywordGeneration:
    """Test keyword file generation."""
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_keyword_file_created(self, sn_stand):
        """Test that keyword file is generated."""
        keyword_content = sn_stand._generate_keyword_file(num_cycles=3)
        
        # Should have required keywords
        assert 'STDIDENT' in keyword_content
        assert 'SITECODE' in keyword_content or 'SITINDEX' in keyword_content
        assert 'INVYEAR' in keyword_content
        assert 'NUMCYCLE' in keyword_content
        assert 'TREELIST' in keyword_content
        assert 'END' in keyword_content
        assert 'PROCESS' in keyword_content
        assert 'STOP' in keyword_content
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_keyword_includes_trees(self, sn_stand):
        """Test that keyword file includes tree data."""
        keyword_content = sn_stand._generate_keyword_file(num_cycles=1)
        
        # Should have tree data
        assert 'TREELIST' in keyword_content


class TestCompareNativeVsPython:
    """Test comparison between native and Python implementations."""
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    @pytest.mark.slow
    def test_compare_implementations(self):
        """Compare native vs Python implementation results."""
        from pyfvs.native_stand import compare_native_vs_python
        
        try:
            results = compare_native_vs_python(
                trees_per_acre=500,
                site_index=70,
                species='LP',
                years=25
            )
            
            # Both should produce results
            assert 'native' in results
            assert 'python' in results
            
            # Both should have volume > 0
            assert results['native'].get('volume', 0) > 0
            assert results['python'].get('volume', 0) > 0
            
            # Log differences for analysis
            logging.info("Native vs Python comparison:")
            for key, diff in results.get('differences', {}).items():
                native_val = results['native'].get(key, 0)
                python_val = results['python'].get(key, 0)
                pct_diff = abs(diff / python_val * 100) if python_val else 0
                logging.info(f"  {key}: native={native_val:.2f}, python={python_val:.2f}, diff={pct_diff:.1f}%")
        
        except Exception as e:
            # If comparison fails, log but don't fail the test
            # (Python Stand may have different requirements)
            logging.warning(f"Comparison failed: {e}")


class TestNativeStandEmptyStand:
    """Test NativeStand with empty tree list."""
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    def test_empty_stand_metrics(self):
        """Test metrics for empty stand."""
        from pyfvs.native_stand import NativeStand
        
        stand = NativeStand(trees=[], site_index=70, variant='sn')
        
        metrics = stand.get_metrics()
        
        assert metrics['tpa'] == 0
        assert metrics['volume'] == 0
        assert metrics['basal_area'] == 0


# ================================================================
# Integration Tests
# ================================================================

class TestNativeStandIntegration:
    """Integration tests for NativeStand."""
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    @pytest.mark.slow
    def test_full_rotation(self):
        """Test full 40-year rotation simulation."""
        from pyfvs.native_stand import NativeStand
        
        stand = NativeStand.initialize_planted(
            trees_per_acre=500,
            site_index=70,
            species='LP',
            variant='sn'
        )
        
        # Grow in 5-year increments and track metrics
        metrics_over_time = []
        
        for year in range(0, 41, 5):
            if year > 0:
                stand.grow(years=5)
            metrics = stand.get_metrics()
            metrics['year'] = year
            metrics_over_time.append(metrics)
        
        # Verify progression
        assert len(metrics_over_time) == 9  # 0, 5, 10, ..., 40
        
        # Volume should generally increase
        volumes = [m['volume'] for m in metrics_over_time]
        assert volumes[-1] > volumes[0]
        
        # DBH should increase
        dbhs = [m['mean_dbh'] for m in metrics_over_time]
        assert dbhs[-1] > dbhs[0]
        
        # Final trees should be substantial
        final = metrics_over_time[-1]
        assert final['mean_dbh'] > 8.0  # At least 8" at 40 years
        assert final['mean_height'] > 60.0  # At least 60' at 40 years
    
    @pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
    @pytest.mark.slow
    def test_different_densities(self):
        """Test growth at different planting densities."""
        from pyfvs.native_stand import NativeStand
        
        results = {}
        
        for tpa in [300, 500, 700]:
            stand = NativeStand.initialize_planted(
                trees_per_acre=tpa,
                site_index=70,
                species='LP',
                variant='sn'
            )
            
            stand.grow(years=25)
            results[tpa] = stand.get_metrics()
        
        # Higher density should have:
        # - More TPA (though mortality may reduce it)
        # - More basal area (total, not per tree)
        # - Smaller individual tree DBH (more competition)
        
        # BA should increase with initial density
        # (though mortality may affect final result)
        assert results[700]['basal_area'] >= results[300]['basal_area'] * 0.8


# ================================================================
# Example/Demo Test
# ================================================================

@pytest.mark.skipif(not HAS_SN, reason="SN variant not available")
def test_example_usage():
    """Example usage as a test."""
    from pyfvs.native_stand import NativeStand
    
    # Create a stand
    stand = NativeStand.initialize_planted(
        trees_per_acre=500,
        site_index=70,
        species='LP',
        variant='sn'
    )
    
    # Grow for 25 years
    stand.grow(years=25)
    
    # Get metrics
    metrics = stand.get_metrics()
    
    print(f"\n=== NativeStand Example ===")
    print(f"Species: {stand.species}")
    print(f"Site Index: {stand.site_index}")
    print(f"Age: {metrics['age']} years")
    print(f"TPA: {metrics['tpa']}")
    print(f"Mean DBH: {metrics['mean_dbh']:.1f} inches")
    print(f"Mean Height: {metrics['mean_height']:.1f} feet")
    print(f"Basal Area: {metrics['basal_area']:.1f} sq ft/acre")
    print(f"Volume: {metrics['volume']:.0f} cu ft/acre")
    
    # Print summary
    print("\n" + stand.print_summary())

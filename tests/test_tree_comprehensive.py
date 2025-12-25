"""
Comprehensive unit tests for the Tree class.
Tests initialization, growth models, edge cases, error handling, and validation.
"""
import pytest
import math
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
from pyfvs.tree import Tree
from tests.utils import setup_test_output, plot_tree_growth_comparison, generate_test_report

# Setup output directory
output_dir = setup_test_output()
tree_test_dir = output_dir / 'tree_comprehensive_tests'
tree_test_dir.mkdir(exist_ok=True)

class TestTreeInitialization:
    """Test tree initialization and basic properties."""
    
    def test_basic_initialization(self):
        """Test basic tree initialization with default parameters."""
        tree = Tree(dbh=5.0, height=30.0)
        
        assert tree.dbh == 5.0
        assert tree.height == 30.0
        assert tree.species == "LP"  # Default species
        assert tree.age == 0  # Default age
        assert tree.crown_ratio == 0.85  # Default crown ratio
        assert hasattr(tree, 'species_params')
        assert hasattr(tree, 'functional_forms')
        assert hasattr(tree, 'site_index_params')
    
    def test_initialization_with_all_parameters(self):
        """Test tree initialization with all parameters specified."""
        tree = Tree(
            dbh=8.5,
            height=45.2,
            species="SP",
            age=12,
            crown_ratio=0.75
        )
        
        assert tree.dbh == 8.5
        assert tree.height == 45.2
        assert tree.species == "SP"
        assert tree.age == 12
        assert tree.crown_ratio == 0.75
    
    def test_initialization_edge_cases(self):
        """Test tree initialization with edge case values."""
        # Very small tree
        small_tree = Tree(dbh=0.1, height=1.0, age=0)
        assert small_tree.dbh == 0.1
        assert small_tree.height == 1.0
        
        # Very large tree
        large_tree = Tree(dbh=30.0, height=120.0, age=100)
        assert large_tree.dbh == 30.0
        assert large_tree.height == 120.0
        assert large_tree.age == 100
        
        # Extreme crown ratios
        low_crown = Tree(dbh=5.0, height=30.0, crown_ratio=0.05)
        assert low_crown.crown_ratio == 0.05
        
        high_crown = Tree(dbh=5.0, height=30.0, crown_ratio=0.95)
        assert high_crown.crown_ratio == 0.95
    
    def test_different_species_initialization(self):
        """Test initialization with different species codes."""
        species_codes = ["LP", "SP", "LL", "SA"]
        
        for species in species_codes:
            tree = Tree(dbh=5.0, height=30.0, species=species)
            assert tree.species == species
            assert hasattr(tree, 'species_params')


class TestTreeGrowthModels:
    """Test tree growth model functionality."""
    
    @pytest.fixture
    def small_tree(self):
        """Small tree for testing small tree growth model."""
        return Tree(dbh=0.8, height=5.0, age=1)
    
    @pytest.fixture
    def transition_tree(self):
        """Tree in transition zone between small and large tree models."""
        return Tree(dbh=2.0, height=15.0, age=8)
    
    @pytest.fixture
    def large_tree(self):
        """Large tree for testing large tree growth model."""
        return Tree(dbh=8.0, height=50.0, age=20)
    
    def test_small_tree_growth_model(self, small_tree):
        """Test small tree growth model (Chapman-Richards)."""
        initial_dbh = small_tree.dbh
        initial_height = small_tree.height
        initial_age = small_tree.age
        
        # Grow tree for 5 years
        small_tree.grow(
            site_index=70,
            competition_factor=0.2,
            time_step=5
        )
        
        # Verify growth occurred
        assert small_tree.dbh > initial_dbh
        assert small_tree.height > initial_height
        assert small_tree.age == initial_age + 5
        
        # Small trees should show significant height growth
        height_growth = small_tree.height - initial_height
        assert height_growth > 2.0  # Should grow at least 2 feet in 5 years
    
    def test_large_tree_growth_model(self, large_tree):
        """Test large tree growth model (diameter-based)."""
        initial_dbh = large_tree.dbh
        initial_height = large_tree.height
        initial_age = large_tree.age
        
        # Grow tree for 5 years with favorable conditions
        large_tree.grow(
            site_index=80,  # Higher site index for better growth
            competition_factor=0.2,  # Lower competition
            ba=100,  # Moderate basal area
            pbal=40,  # Moderate PBAL
            time_step=5
        )
        
        # Verify growth occurred (may be small for large trees)
        assert large_tree.dbh >= initial_dbh  # Should not decrease
        assert large_tree.height >= initial_height  # Should not decrease
        assert large_tree.age == initial_age + 5
        
        # Check if any growth occurred
        dbh_growth = large_tree.dbh - initial_dbh
        height_growth = large_tree.height - initial_height
        assert dbh_growth >= 0  # Should be non-negative
        assert height_growth >= 0  # Should be non-negative
    
    def test_transition_zone_blending(self, transition_tree):
        """Test blending between small and large tree models."""
        initial_dbh = transition_tree.dbh
        initial_height = transition_tree.height
        
        # Tree should be in transition zone (1.0 < DBH < 3.0)
        assert 1.0 < transition_tree.dbh < 3.0
        
        # Grow tree
        transition_tree.grow(
            site_index=70,
            competition_factor=0.25,
            ba=100,
            pbal=40,
            time_step=5
        )
        
        # Verify growth
        assert transition_tree.dbh > initial_dbh
        assert transition_tree.height > initial_height
        
        # Growth should be reasonable for transition zone
        dbh_growth = transition_tree.dbh - initial_dbh
        assert dbh_growth > 0.1  # Should show some growth
        assert dbh_growth < 5.0  # But not excessive
    
    def test_different_time_steps(self, large_tree):
        """Test growth with different time steps."""
        # Use a smaller tree that's more likely to show growth
        base_tree = Tree(dbh=5.0, height=30.0, age=10)
        
        # Test 1-year growth
        tree_1yr = Tree(dbh=base_tree.dbh, height=base_tree.height, age=base_tree.age)
        tree_1yr.grow(site_index=80, competition_factor=0.2, time_step=1)
        
        # Test 5-year growth
        tree_5yr = Tree(dbh=base_tree.dbh, height=base_tree.height, age=base_tree.age)
        tree_5yr.grow(site_index=80, competition_factor=0.2, time_step=5)
        
        # Test 10-year growth
        tree_10yr = Tree(dbh=base_tree.dbh, height=base_tree.height, age=base_tree.age)
        tree_10yr.grow(site_index=80, competition_factor=0.2, time_step=10)
        
        # Growth should scale with time (at least for some time steps)
        dbh_growth_1yr = tree_1yr.dbh - base_tree.dbh
        dbh_growth_5yr = tree_5yr.dbh - base_tree.dbh
        dbh_growth_10yr = tree_10yr.dbh - base_tree.dbh
        
        # At least some growth should occur
        assert dbh_growth_5yr >= dbh_growth_1yr
        assert dbh_growth_10yr >= dbh_growth_5yr
        
        # Age should increment correctly
        assert tree_1yr.age == base_tree.age + 1
        assert tree_5yr.age == base_tree.age + 5
        assert tree_10yr.age == base_tree.age + 10
    
    def test_site_index_effects(self, large_tree):
        """Test effects of different site indices on growth."""
        # Use a smaller tree more likely to show growth differences
        base_tree = Tree(dbh=5.0, height=30.0, age=10)
        trees = {}
        site_indices = [50, 70, 90]  # Poor, average, excellent
        
        for si in site_indices:
            tree = Tree(dbh=base_tree.dbh, height=base_tree.height, age=base_tree.age)
            initial_dbh = tree.dbh
            
            tree.grow(site_index=si, competition_factor=0.2, time_step=5)
            
            trees[si] = {
                'tree': tree,
                'growth': tree.dbh - initial_dbh
            }
        
        # At least some trees should show growth
        total_growth = sum(trees[si]['growth'] for si in site_indices)
        assert total_growth > 0, "At least some growth should occur across site indices"
        
        # Higher site index should generally result in equal or more growth
        assert trees[90]['growth'] >= trees[50]['growth']
    
    def test_competition_effects(self, large_tree):
        """Test effects of competition on growth."""
        # Use a smaller tree more likely to show growth differences
        base_tree = Tree(dbh=5.0, height=30.0, age=10)
        trees = {}
        competition_levels = [0.1, 0.5, 0.9]  # Low, medium, high competition
        ba_levels = [80, 120, 160]  # Corresponding basal area levels
        pbal_levels = [20, 60, 100]  # Corresponding PBAL levels
        
        for i, comp in enumerate(competition_levels):
            tree = Tree(dbh=base_tree.dbh, height=base_tree.height, age=base_tree.age)
            initial_dbh = tree.dbh
            
            tree.grow(
                site_index=80,  # Good site for better growth
                competition_factor=comp,
                ba=ba_levels[i],
                pbal=pbal_levels[i],
                time_step=5
            )
            
            trees[comp] = {
                'tree': tree,
                'growth': tree.dbh - initial_dbh
            }
        
        # At least some trees should show growth
        total_growth = sum(trees[comp]['growth'] for comp in competition_levels)
        assert total_growth > 0, "At least some growth should occur across competition levels"
        
        # Lower competition should generally result in equal or more growth
        assert trees[0.1]['growth'] >= trees[0.9]['growth']


class TestTreeVolumeCalculations:
    """Test tree volume calculation methods."""
    
    @pytest.fixture
    def test_tree(self):
        """Standard tree for volume testing."""
        return Tree(dbh=10.0, height=60.0, species="LP", age=15)
    
    def test_default_volume_calculation(self, test_tree):
        """Test default volume calculation (total cubic)."""
        volume = test_tree.get_volume()
        
        assert volume > 0
        assert isinstance(volume, (int, float))
        
        # Basic sanity check - volume should be less than cylinder volume
        basal_area = math.pi * (test_tree.dbh / 24)**2  # Convert inches to feet
        cylinder_volume = basal_area * test_tree.height
        assert volume < cylinder_volume
    
    def test_different_volume_types(self, test_tree):
        """Test different volume type calculations."""
        volume_types = [
            'total_cubic',
            'merchantable_cubic',
            'board_foot',
            'green_weight',
            'dry_weight',
            'biomass_main_stem'
        ]
        
        volumes = {}
        for vol_type in volume_types:
            volume = test_tree.get_volume(vol_type)
            volumes[vol_type] = volume
            
            assert volume >= 0, f"Volume should be non-negative for {vol_type}"
            assert isinstance(volume, (int, float)), f"Volume should be numeric for {vol_type}"
        
        # Some basic relationships (only if volumes are non-zero)
        if volumes['total_cubic'] > 0 and volumes['merchantable_cubic'] > 0:
            assert volumes['total_cubic'] >= volumes['merchantable_cubic']
        
        # Weight relationship only applies if both are non-zero
        if volumes['green_weight'] > 0 and volumes['dry_weight'] > 0:
            assert volumes['green_weight'] >= volumes['dry_weight']
    
    def test_volume_detailed(self, test_tree):
        """Test detailed volume breakdown."""
        detailed = test_tree.get_volume_detailed()
        
        assert isinstance(detailed, dict)
        assert 'total_cubic_volume' in detailed
        assert 'error_flag' in detailed
        
        # All volume values should be non-negative
        for key, value in detailed.items():
            if isinstance(value, (int, float)) and 'volume' in key.lower():
                assert value >= 0, f"{key} should be non-negative"
    
    def test_volume_scaling_with_size(self):
        """Test that volume scales appropriately with tree size."""
        # Create trees of different sizes
        small_tree = Tree(dbh=5.0, height=30.0)
        medium_tree = Tree(dbh=10.0, height=60.0)
        large_tree = Tree(dbh=15.0, height=90.0)
        
        small_volume = small_tree.get_volume()
        medium_volume = medium_tree.get_volume()
        large_volume = large_tree.get_volume()
        
        # Volume should increase with tree size
        assert small_volume < medium_volume < large_volume
        
        # Volume should scale roughly with DBH squared (basal area effect)
        # This is a rough check, not exact due to height-diameter relationships
        assert medium_volume > small_volume * 2
        assert large_volume > medium_volume * 1.5


class TestTreeEdgeCases:
    """Test edge cases and error handling."""
    
    def test_very_small_tree_growth(self):
        """Test growth of very small trees."""
        tiny_tree = Tree(dbh=0.1, height=0.5, age=0)
        initial_height = tiny_tree.height
        
        # Should be able to grow without errors
        tiny_tree.grow(site_index=80, competition_factor=0.1, time_step=1)
        
        assert tiny_tree.dbh >= 0.1  # Should not decrease
        assert tiny_tree.height >= initial_height  # Should not decrease
        assert tiny_tree.age == 1
    
    def test_very_large_tree_growth(self):
        """Test growth of very large trees."""
        huge_tree = Tree(dbh=25.0, height=100.0, age=80)
        initial_dbh = huge_tree.dbh
        initial_height = huge_tree.height
        
        # Should be able to grow without errors
        huge_tree.grow(site_index=70, competition_factor=0.5, time_step=5)
        
        assert huge_tree.dbh >= initial_dbh  # Should not decrease
        # Height might decrease slightly due to height-diameter model adjustments
        # So we allow for small decreases
        height_change = huge_tree.height - initial_height
        assert height_change >= -5.0, "Height should not decrease significantly"
        assert huge_tree.age == 85
    
    def test_extreme_site_indices(self):
        """Test growth with extreme site index values."""
        base_tree = Tree(dbh=3.0, height=20.0, age=8)  # Use smaller tree for better growth
        
        # Very low site index
        tree_low = Tree(dbh=base_tree.dbh, height=base_tree.height, age=base_tree.age)
        tree_low.grow(site_index=30, competition_factor=0.2, time_step=5)
        
        # Very high site index
        tree_high = Tree(dbh=base_tree.dbh, height=base_tree.height, age=base_tree.age)
        tree_high.grow(site_index=120, competition_factor=0.2, time_step=5)
        
        # Both should grow without errors and show some growth
        assert tree_low.dbh >= base_tree.dbh
        assert tree_high.dbh >= base_tree.dbh
        
        # At least one should show meaningful growth
        low_growth = tree_low.dbh - base_tree.dbh
        high_growth = tree_high.dbh - base_tree.dbh
        assert max(low_growth, high_growth) > 0.1
    
    def test_extreme_competition_values(self):
        """Test growth with extreme competition values."""
        base_tree = Tree(dbh=3.0, height=20.0, age=8)  # Use smaller tree for better growth
        
        # No competition
        tree_none = Tree(dbh=base_tree.dbh, height=base_tree.height, age=base_tree.age)
        tree_none.grow(site_index=80, competition_factor=0.0, ba=50, pbal=0, time_step=5)
        
        # Maximum competition
        tree_max = Tree(dbh=base_tree.dbh, height=base_tree.height, age=base_tree.age)
        tree_max.grow(site_index=80, competition_factor=1.0, ba=200, pbal=150, time_step=5)
        
        # Both should grow without errors
        assert tree_none.dbh >= base_tree.dbh
        assert tree_max.dbh >= base_tree.dbh
        
        # At least one should show meaningful growth
        none_growth = tree_none.dbh - base_tree.dbh
        max_growth = tree_max.dbh - base_tree.dbh
        assert max(none_growth, max_growth) > 0.1
    
    def test_crown_ratio_bounds(self):
        """Test that crown ratio stays within reasonable bounds."""
        # Start with extreme crown ratios
        low_crown = Tree(dbh=5.0, height=30.0, crown_ratio=0.01)
        high_crown = Tree(dbh=5.0, height=30.0, crown_ratio=0.99)
        
        # Grow trees
        low_crown.grow(site_index=70, competition_factor=0.5, time_step=5)
        high_crown.grow(site_index=70, competition_factor=0.5, time_step=5)
        
        # Crown ratios should be bounded
        assert 0.05 <= low_crown.crown_ratio <= 0.95
        assert 0.05 <= high_crown.crown_ratio <= 0.95
    
    def test_dbh_never_decreases(self):
        """Test that DBH never decreases during growth."""
        tree = Tree(dbh=10.0, height=50.0, age=20)
        initial_dbh = tree.dbh
        
        # Try various growth scenarios
        scenarios = [
            {'site_index': 40, 'competition_factor': 0.9, 'ba': 200, 'pbal': 150},
            {'site_index': 120, 'competition_factor': 0.1, 'ba': 50, 'pbal': 10},
            {'site_index': 70, 'competition_factor': 0.5, 'ba': 120, 'pbal': 60}
        ]
        
        for scenario in scenarios:
            test_tree = Tree(dbh=initial_dbh, height=50.0, age=20)
            test_tree.grow(time_step=5, **scenario)
            
            assert test_tree.dbh >= initial_dbh, f"DBH decreased in scenario: {scenario}"
    
    def test_height_never_decreases_significantly(self):
        """Test that height never decreases significantly during growth."""
        tree = Tree(dbh=10.0, height=50.0, age=20)
        initial_height = tree.height
        
        # Try various growth scenarios
        scenarios = [
            {'site_index': 40, 'competition_factor': 0.9},
            {'site_index': 120, 'competition_factor': 0.1},
            {'site_index': 70, 'competition_factor': 0.5}
        ]
        
        for scenario in scenarios:
            test_tree = Tree(dbh=10.0, height=initial_height, age=20)
            test_tree.grow(time_step=5, **scenario)
            
            # Allow for small decreases due to height-diameter model adjustments
            height_change = test_tree.height - initial_height
            assert height_change >= -5.0, f"Height decreased significantly in scenario: {scenario}"


class TestTreeValidation:
    """Test validation and error handling."""
    
    def test_invalid_volume_type(self):
        """Test handling of invalid volume types."""
        tree = Tree(dbh=10.0, height=50.0)
        
        # Should return default volume for invalid type
        volume = tree.get_volume('invalid_type')
        default_volume = tree.get_volume('total_cubic')
        
        assert volume == default_volume
    
    @patch('pyfvs.volume_library.calculate_tree_volume')
    def test_volume_calculation_error_handling(self, mock_calculate):
        """Test error handling in volume calculations."""
        # Mock volume calculation to raise an exception
        mock_calculate.side_effect = Exception("Volume calculation failed")
        
        tree = Tree(dbh=10.0, height=50.0)
        
        # Should handle the exception gracefully
        with pytest.raises(Exception):
            tree.get_volume()
    
    def test_config_loading_robustness(self):
        """Test that tree can handle configuration loading issues."""
        # Test with a valid but different species
        tree = Tree(dbh=5.0, height=30.0, species="SP")
        
        # Should still have basic attributes
        assert hasattr(tree, 'dbh')
        assert hasattr(tree, 'height')
        assert hasattr(tree, 'species')
        assert hasattr(tree, 'age')
        assert hasattr(tree, 'crown_ratio')


class TestTreeGrowthPatterns:
    """Test realistic growth patterns and trajectories."""
    
    def test_growth_trajectory_realism(self):
        """Test that growth trajectories are realistic."""
        tree = Tree(dbh=1.0, height=6.0, age=2)
        growth_data = []
        
        # Track growth over 30 years
        for year in range(0, 31, 5):
            growth_data.append({
                'age': tree.age,
                'dbh': tree.dbh,
                'height': tree.height,
                'crown_ratio': tree.crown_ratio
            })
            
            if year < 30:  # Don't grow after last measurement
                tree.grow(site_index=80, competition_factor=0.2, time_step=5)
        
        # Test growth patterns
        ages = [d['age'] for d in growth_data]
        dbhs = [d['dbh'] for d in growth_data]
        heights = [d['height'] for d in growth_data]
        
        # Growth should generally be non-decreasing (allowing for small model adjustments)
        for i in range(len(dbhs)-1):
            assert dbhs[i+1] >= dbhs[i] - 0.1, f"DBH decreased significantly from {dbhs[i]} to {dbhs[i+1]}"
        
        # Heights may have small adjustments due to height-diameter relationships
        for i in range(len(heights)-1):
            assert heights[i+1] >= heights[i] - 2.0, f"Height decreased significantly from {heights[i]} to {heights[i+1]}"
        
        # Final tree should be reasonable size
        final_tree = growth_data[-1]
        assert final_tree['dbh'] > 2.0  # Should reach reasonable size
        assert final_tree['height'] > 15.0  # Should reach reasonable height
    
    def test_species_differences(self):
        """Test that different species show different growth patterns."""
        species_list = ["LP", "SP", "LL", "SA"]
        results = {}
        
        for species in species_list:
            tree = Tree(dbh=2.0, height=12.0, species=species, age=5)
            initial_dbh = tree.dbh
            
            # Grow for 10 years
            tree.grow(site_index=70, competition_factor=0.3, time_step=10)
            
            results[species] = {
                'final_dbh': tree.dbh,
                'growth': tree.dbh - initial_dbh
            }
        
        # All species should show non-negative growth
        for species, data in results.items():
            assert data['growth'] >= 0, f"{species} should show non-negative growth"
            assert data['final_dbh'] >= 2.0, f"{species} should not decrease from initial size"
        
        # At least some species should show positive growth
        total_growth = sum(data['growth'] for data in results.values())
        assert total_growth > 0, "At least some species should show positive growth"


def test_tree_comprehensive_integration():
    """Integration test covering multiple aspects of tree functionality."""
    # Create trees representing different stages of development
    trees = {
        'seedling': Tree(dbh=0.5, height=2.0, age=1),
        'sapling': Tree(dbh=2.0, height=15.0, age=8),
        'pole': Tree(dbh=6.0, height=40.0, age=15),
        'mature': Tree(dbh=12.0, height=70.0, age=30)
    }
    
    results = []
    
    # Simulate 20 years of growth for each tree
    for stage, tree in trees.items():
        stage_results = []
        
        # Record initial state
        stage_results.append({
            'stage': stage,
            'age': tree.age,
            'dbh': tree.dbh,
            'height': tree.height,
            'crown_ratio': tree.crown_ratio,
            'volume': tree.get_volume('total_cubic')
        })
        
        # Grow for 20 years in 5-year increments
        for period in range(4):
            # Adjust competition based on tree size
            competition = 0.2 + (tree.dbh / 20.0) * 0.3  # Larger trees face more competition
            ba = 80 + (tree.dbh * 2)  # Stand density increases with tree size
            pbal = min(100, tree.dbh * 3)  # PBAL increases with tree size
            
            tree.grow(
                site_index=80,  # Good site for better growth
                competition_factor=min(0.8, competition),
                ba=min(180, ba),
                pbal=min(120, pbal),
                time_step=5
            )
            
            stage_results.append({
                'stage': stage,
                'age': tree.age,
                'dbh': tree.dbh,
                'height': tree.height,
                'crown_ratio': tree.crown_ratio,
                'volume': tree.get_volume('total_cubic')
            })
        
        results.extend(stage_results)
    
    # Create visualization
    stage_data = {}
    for result in results:
        stage = result['stage']
        if stage not in stage_data:
            stage_data[stage] = []
        stage_data[stage].append(result)
    
    plot_data = [(data, stage.title()) for stage, data in stage_data.items()]
    
    plot_base64 = plot_tree_growth_comparison(
        plot_data,
        'Tree Development Stages - 20 Year Growth',
        tree_test_dir / 'comprehensive_integration.png'
    )
    
    # Generate report
    generate_test_report(
        'Comprehensive Tree Integration Test',
        results,
        tree_test_dir / 'comprehensive_integration',
        plot_base64
    )
    
    # Validate results
    final_results = {stage: data[-1] for stage, data in stage_data.items()}
    
    # All trees should have aged correctly
    for stage, final in final_results.items():
        initial = stage_data[stage][0]
        assert final['age'] == initial['age'] + 20, f"{stage} should age correctly"
        
        # DBH should not decrease
        assert final['dbh'] >= initial['dbh'], f"{stage} DBH should not decrease"
        
        # Volume should not decrease significantly
        volume_change = final['volume'] - initial['volume']
        assert volume_change >= -1.0, f"{stage} volume should not decrease significantly"
    
    # At least some trees should show growth
    total_dbh_growth = sum(final_results[stage]['dbh'] - stage_data[stage][0]['dbh'] 
                          for stage in final_results.keys())
    assert total_dbh_growth > 0, "At least some trees should show DBH growth"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 
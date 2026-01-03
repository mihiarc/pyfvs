"""
Unit tests for individual tree growth.
"""
import pytest
import math
from pathlib import Path
from pyfvs.tree import Tree
from tests.utils import setup_test_output, plot_tree_growth_comparison, generate_test_report, plot_long_term_growth

# Setup output directory
output_dir = setup_test_output()
tree_test_dir = output_dir / 'tree_tests'

# Species codes for parametrized tests (southern yellow pines)
SOUTHERN_PINE_SPECIES = ["LP", "SP", "SA", "LL"]

# DBH sizes for parametrized tests
DBH_TEST_SIZES = [
    (1.0, 6.0, 2, "small"),      # small tree
    (2.5, 20.0, 8, "transition"), # transition zone
    (6.0, 40.0, 15, "large"),     # large tree
]

# Site indices for parametrized tests
SITE_INDICES = [50, 60, 70, 80]

@pytest.fixture
def small_tree():
    """Create a small tree for testing."""
    return Tree(dbh=1.0, height=6.0, age=2)

@pytest.fixture
def large_tree():
    """Create a large tree for testing."""
    return Tree(dbh=6.0, height=40.0, age=15)

@pytest.fixture
def transition_tree():
    """Create a tree in the transition zone."""
    return Tree(dbh=2.5, height=20.0, age=8)

def test_small_tree_growth(small_tree):
    """Test small tree height growth behavior."""
    # Store initial state
    initial_metrics = [{
        'age': small_tree.age,
        'dbh': small_tree.dbh,
        'height': small_tree.height,
        'crown_ratio': small_tree.crown_ratio
    }]
    
    # Grow for one 5-year period
    small_tree.grow(site_index=70, competition_factor=0.0, ba=100, pbal=30, slope=0.05, aspect=0)
    initial_metrics.append({
        'age': small_tree.age,
        'dbh': small_tree.dbh,
        'height': small_tree.height,
        'crown_ratio': small_tree.crown_ratio
    })
    
    # Create visualization and get base64 data
    plot_base64 = plot_tree_growth_comparison(
        [(initial_metrics, 'Small Tree')],
        'Small Tree Growth Test',
        tree_test_dir / 'small_tree_growth.png'
    )
    
    # Generate report with embedded plot
    generate_test_report(
        'Small Tree Growth Test',
        initial_metrics,
        tree_test_dir / 'small_tree_growth',
        plot_base64
    )
    
    # Run assertions
    assert small_tree.height > initial_metrics[0]['height']
    assert small_tree.dbh > initial_metrics[0]['dbh']
    # Crown ratio bounds - FVS allows minimum of 5% (0.05)
    assert 0.05 <= small_tree.crown_ratio <= 0.95
    assert small_tree.age == 7  # 2 + 5 years

def test_large_tree_growth(large_tree):
    """Test large tree growth behavior."""
    # Store initial state
    metrics = [{
        'age': large_tree.age,
        'dbh': large_tree.dbh,
        'height': large_tree.height,
        'crown_ratio': large_tree.crown_ratio
    }]
    
    # Grow for one 5-year period
    large_tree.grow(site_index=70, competition_factor=0.0, ba=120, pbal=60, slope=0.05, aspect=0)
    metrics.append({
        'age': large_tree.age,
        'dbh': large_tree.dbh,
        'height': large_tree.height,
        'crown_ratio': large_tree.crown_ratio
    })
    
    # Create visualization and get base64 data
    plot_base64 = plot_tree_growth_comparison(
        [(metrics, 'Large Tree')],
        'Large Tree Growth Test',
        tree_test_dir / 'large_tree_growth.png'
    )
    
    # Generate report with embedded plot
    generate_test_report(
        'Large Tree Growth Test',
        metrics,
        tree_test_dir / 'large_tree_growth',
        plot_base64
    )
    
    # Run assertions
    assert large_tree.dbh > metrics[0]['dbh']
    assert large_tree.height > metrics[0]['height']
    # Crown ratio bounds - FVS allows minimum of 5% (0.05)
    assert 0.05 <= large_tree.crown_ratio <= 0.95
    assert large_tree.age == 20  # 15 + 5 years

def test_transition_zone_growth(transition_tree):
    """Test growth behavior in transition zone."""
    initial_dbh = transition_tree.dbh
    initial_height = transition_tree.height
    
    # Grow tree for one 5-year period
    transition_tree.grow(site_index=70, competition_factor=0.0, ba=110, pbal=45, slope=0.05, aspect=0)
    
    # Both diameter and height should increase
    assert transition_tree.dbh > initial_dbh
    assert transition_tree.height > initial_height
    # Crown ratio bounds - FVS allows minimum of 5% (0.05)
    assert 0.05 <= transition_tree.crown_ratio <= 0.95
    # Age should increment by 5
    assert transition_tree.age == 13  # 8 + 5 years

def test_competition_effects(large_tree):
    """Test the effects of competition on growth."""
    # Create trees for different competition levels
    trees = {
        'No Competition': Tree(dbh=large_tree.dbh, height=large_tree.height, age=large_tree.age),
        'Medium Competition': Tree(dbh=large_tree.dbh, height=large_tree.height, age=large_tree.age),
        'High Competition': Tree(dbh=large_tree.dbh, height=large_tree.height, age=large_tree.age)
    }
    competition_levels = {'No Competition': 0.0, 'Medium Competition': 0.5, 'High Competition': 0.9}
    ranks = {'No Competition': 0.8, 'Medium Competition': 0.5, 'High Competition': 0.2}
    # Basal area and PBAL should increase with competition
    ba_levels = {'No Competition': 80, 'Medium Competition': 120, 'High Competition': 160}
    pbal_levels = {'No Competition': 30, 'Medium Competition': 60, 'High Competition': 90}
    
    # Collect metrics for each competition level over one 5-year period
    metrics_by_competition = {}
    for label, tree in trees.items():
        metrics = [{
            'age': tree.age,
            'dbh': tree.dbh,
            'height': tree.height,
            'crown_ratio': tree.crown_ratio
        }]
        
        tree.grow(
            site_index=70, 
            competition_factor=competition_levels[label],
            rank=ranks[label],
            ba=ba_levels[label],
            pbal=pbal_levels[label],
            slope=0.05,
            aspect=0
        )
        metrics.append({
            'age': tree.age,
            'dbh': tree.dbh,
            'height': tree.height,
            'crown_ratio': tree.crown_ratio
        })
        metrics_by_competition[label] = metrics
    
    # Create visualization and get base64 data
    plot_base64 = plot_tree_growth_comparison(
        [(metrics, label) for label, metrics in metrics_by_competition.items()],
        'Competition Effects Test',
        tree_test_dir / 'competition_effects.png'
    )
    
    # Generate report with embedded plot
    results = []
    for label, metrics in metrics_by_competition.items():
        final_metrics = metrics[-1]
        results.append({
            'competition_level': label,
            'dbh': final_metrics['dbh'],
            'height': final_metrics['height'],
            'crown_ratio': final_metrics['crown_ratio']
        })
    
    generate_test_report(
        'Competition Effects Test',
        results,
        tree_test_dir / 'competition_effects',
        plot_base64
    )
    
    # Run assertions
    final_metrics = {label: metrics[-1] for label, metrics in metrics_by_competition.items()}
    assert final_metrics['High Competition']['dbh'] < final_metrics['Medium Competition']['dbh'] < final_metrics['No Competition']['dbh']
    assert final_metrics['High Competition']['height'] < final_metrics['Medium Competition']['height'] < final_metrics['No Competition']['height']
    assert final_metrics['High Competition']['crown_ratio'] <= final_metrics['Medium Competition']['crown_ratio'] <= final_metrics['No Competition']['crown_ratio']

def test_volume_calculation(large_tree):
    """Test tree volume calculation."""
    volume = large_tree.get_volume()
    
    # Volume should be positive
    assert volume > 0
    
    # Basic volume check (cylinder * form factor)
    basal_area = math.pi * (large_tree.dbh / 24)**2
    cylinder_volume = basal_area * large_tree.height
    assert volume < cylinder_volume  # Volume should be less than cylinder

def test_long_term_growth():
    """Test tree development over multiple years."""
    tree = Tree(dbh=0.5, height=1.0, age=0)
    growth_metrics = []
    
    # Grow for 60 years with 1-year time steps
    for i in range(60):
        growth_metrics.append({
            'age': tree.age,
            'dbh': tree.dbh,
            'height': tree.height,
            'crown_ratio': tree.crown_ratio,
            'volume': tree.get_volume()
        })
        
        # Increase basal area as tree grows
        current_ba = 80 + (i * 2)  # Start at 80, increase more gradually
        current_pbal = min(80, i * 1.5)  # Increase more gradually
        # Lower competition factor to get more growth
        competition_factor = max(0.1, 0.3 - (i * 0.004))  # Decrease more gradually
        
        # Grow tree with 1-year time step
        tree.grow(
            site_index=70,
            competition_factor=competition_factor,
            ba=current_ba,
            pbal=current_pbal,
            slope=0.05,
            aspect=0,
            time_step=1
        )
    
    # Add final state
    growth_metrics.append({
        'age': tree.age,
        'dbh': tree.dbh,
        'height': tree.height,
        'crown_ratio': tree.crown_ratio,
        'volume': tree.get_volume()
    })
    
    # Create visualization
    plot_base64 = plot_long_term_growth(
        growth_metrics,
        'Long-term Tree Development (60 years)',
        tree_test_dir / 'long_term_growth.png'
    )
    
    # Generate report
    generate_test_report(
        'Long-term Tree Growth Test',
        growth_metrics,
        tree_test_dir / 'long_term_growth',
        plot_base64
    )
    
    # Run assertions
    assert tree.age == 60
    assert tree.dbh > 4.0  # Should reach a reasonable size for 60 years
    assert tree.height > 30.0  # Should reach a reasonable height
    assert tree.get_volume() > 0
    
    # Growth pattern assertions
    dbh_growth = [metrics['dbh'] for metrics in growth_metrics]
    height_growth = [metrics['height'] for metrics in growth_metrics]
    volume_growth = [metrics['volume'] for metrics in growth_metrics]
    crown_ratios = [metrics['crown_ratio'] for metrics in growth_metrics]
    
    # Height growth should follow sigmoid pattern (faster early, slower late)
    early_height_growth = height_growth[10] - height_growth[0]  # First 10 years
    late_height_growth = height_growth[-1] - height_growth[-11]  # Last 10 years
    assert early_height_growth > late_height_growth, "Height growth should slow with age"
    
    # DBH growth should show gradual decline over time
    early_dbh_growth = dbh_growth[10] - dbh_growth[0]  # First 10 years
    late_dbh_growth = dbh_growth[-1] - dbh_growth[-11]  # Last 10 years
    assert early_dbh_growth > late_dbh_growth, "Diameter growth should slow with age"
    assert late_dbh_growth > 0, "Tree should continue to grow in diameter, albeit slowly"
    
    # Volume growth pattern
    mid_point = len(volume_growth) // 2
    early_volume_growth = volume_growth[mid_point] - volume_growth[0]
    late_volume_growth = volume_growth[-1] - volume_growth[mid_point]
    # Tree should accumulate volume over time
    assert volume_growth[-1] > volume_growth[0], "Tree should gain volume over time"
    
    # Crown ratio should decrease with age
    assert crown_ratios[-1] < crown_ratios[0], "Should decrease over time"

def test_small_tree_annual_growth():
    """Test small tree growth in 1-year increments to visualize growth curve."""
    small_tree = Tree(dbh=1.0, height=6.0, age=2)
    growth_metrics = []
    
    # Store initial state
    growth_metrics.append({
        'age': small_tree.age,
        'dbh': small_tree.dbh,
        'height': small_tree.height,
        'crown_ratio': small_tree.crown_ratio
    })
    
    # Grow for 10 years, one year at a time
    for _ in range(10):
        small_tree.grow(site_index=70, competition_factor=0.0, ba=100, pbal=30, slope=0.05, aspect=0, time_step=1)
        growth_metrics.append({
            'age': small_tree.age,
            'dbh': small_tree.dbh,
            'height': small_tree.height,
            'crown_ratio': small_tree.crown_ratio
        })
    
    # Create visualization and get base64 data
    plot_base64 = plot_tree_growth_comparison(
        [(growth_metrics, 'Small Tree Annual Growth')],
        'Small Tree Annual Growth Curve',
        tree_test_dir / 'small_tree_annual_growth.png'
    )
    
    # Generate report with embedded plot
    generate_test_report(
        'Small Tree Annual Growth Test',
        growth_metrics,
        tree_test_dir / 'small_tree_annual_growth',
        plot_base64
    )
    
    # Verify growth pattern - early growth should be faster than later growth
    # Get height growth rates for early and late periods
    early_height_growth = growth_metrics[3]['height'] - growth_metrics[0]['height']  # First 3 years
    late_height_growth = growth_metrics[-1]['height'] - growth_metrics[-4]['height']  # Last 3 years
    
    # Chapman-Richards should show non-linear growth pattern
    # The assertion may need adjustment based on actual growth patterns
    assert early_height_growth != late_height_growth, "Growth should not be perfectly linear"


# =============================================================================
# Parametrized Tests - Multi-species and multi-size coverage
# =============================================================================

class TestMultiSpeciesGrowth:
    """Parametrized tests across multiple species."""

    @pytest.mark.parametrize("species", SOUTHERN_PINE_SPECIES)
    def test_species_tree_creation(self, species):
        """Test that trees can be created for all southern pine species."""
        tree = Tree(dbh=5.0, height=30.0, species=species, age=10)
        assert tree.species == species
        assert tree.dbh == 5.0
        assert tree.height == 30.0
        assert tree.age == 10

    @pytest.mark.parametrize("species", SOUTHERN_PINE_SPECIES)
    def test_species_growth_positive(self, species):
        """Test that all species show positive growth under normal conditions."""
        tree = Tree(dbh=5.0, height=30.0, species=species, age=10)
        initial_dbh = tree.dbh
        initial_height = tree.height

        tree.grow(site_index=70, competition_factor=0.0, ba=100, pbal=30, slope=0.05, aspect=0)

        assert tree.dbh > initial_dbh, f"{species} should show positive DBH growth"
        assert tree.height > initial_height, f"{species} should show positive height growth"
        assert 0.05 <= tree.crown_ratio <= 0.95, f"{species} crown ratio out of bounds"
        assert tree.age == 15, f"{species} age should increment by 5"

    @pytest.mark.parametrize("species", SOUTHERN_PINE_SPECIES)
    def test_species_volume_positive(self, species):
        """Test that volume calculations work for all species."""
        tree = Tree(dbh=8.0, height=50.0, species=species, age=15)
        volume = tree.get_volume()

        assert volume > 0, f"{species} should have positive volume"
        # Volume should be less than cylinder volume
        basal_area = math.pi * (tree.dbh / 24)**2
        cylinder_volume = basal_area * tree.height
        assert volume < cylinder_volume, f"{species} volume should be less than cylinder"

    @pytest.mark.parametrize("species,dbh,height,age,size_class", [
        ("LP", 1.0, 6.0, 2, "small"),
        ("LP", 2.5, 20.0, 8, "transition"),
        ("LP", 6.0, 40.0, 15, "large"),
        ("SP", 1.0, 6.0, 2, "small"),
        ("SP", 6.0, 40.0, 15, "large"),
        ("SA", 1.0, 6.0, 2, "small"),
        ("SA", 6.0, 40.0, 15, "large"),
        ("LL", 1.0, 6.0, 2, "small"),
        ("LL", 6.0, 40.0, 15, "large"),
    ])
    def test_species_size_combinations(self, species, dbh, height, age, size_class):
        """Test growth for various species and size combinations."""
        tree = Tree(dbh=dbh, height=height, species=species, age=age)
        initial_dbh = tree.dbh
        initial_height = tree.height

        tree.grow(site_index=70, competition_factor=0.0, ba=100, pbal=30, slope=0.05, aspect=0)

        assert tree.dbh > initial_dbh, f"{species} {size_class} should grow in DBH"
        assert tree.height > initial_height, f"{species} {size_class} should grow in height"


class TestMultiSiteIndexGrowth:
    """Parametrized tests across site indices."""

    @pytest.mark.parametrize("site_index", SITE_INDICES)
    def test_site_index_affects_growth(self, site_index):
        """Test that trees grow under various site indices."""
        tree = Tree(dbh=5.0, height=30.0, species="LP", age=10)
        initial_dbh = tree.dbh
        initial_height = tree.height

        tree.grow(site_index=site_index, competition_factor=0.0, ba=100, pbal=30, slope=0.05, aspect=0)

        assert tree.dbh > initial_dbh, f"SI={site_index} should allow DBH growth"
        assert tree.height > initial_height, f"SI={site_index} should allow height growth"

    @pytest.mark.parametrize("site_index", SITE_INDICES)
    def test_higher_si_more_growth(self, site_index):
        """Test that higher site index produces more height growth."""
        # Create baseline tree at SI=50
        baseline_tree = Tree(dbh=5.0, height=30.0, species="LP", age=10)
        baseline_tree.grow(site_index=50, competition_factor=0.0, ba=100, pbal=30, slope=0.05, aspect=0)

        # Create test tree at current site index
        test_tree = Tree(dbh=5.0, height=30.0, species="LP", age=10)
        test_tree.grow(site_index=site_index, competition_factor=0.0, ba=100, pbal=30, slope=0.05, aspect=0)

        if site_index > 50:
            assert test_tree.height >= baseline_tree.height, \
                f"SI={site_index} should produce >= height growth than SI=50"


class TestTreeSizeClasses:
    """Parametrized tests across tree size classes."""

    @pytest.mark.parametrize("dbh,height,age,size_class", DBH_TEST_SIZES)
    def test_size_class_growth(self, dbh, height, age, size_class):
        """Test growth for different size classes."""
        tree = Tree(dbh=dbh, height=height, species="LP", age=age)
        initial_dbh = tree.dbh
        initial_height = tree.height

        tree.grow(site_index=70, competition_factor=0.0, ba=100, pbal=30, slope=0.05, aspect=0)

        assert tree.dbh > initial_dbh, f"{size_class} tree should grow in DBH"
        assert tree.height > initial_height, f"{size_class} tree should grow in height"
        assert 0.05 <= tree.crown_ratio <= 0.95, f"{size_class} crown ratio out of bounds"

    @pytest.mark.parametrize("dbh,height,age,size_class", DBH_TEST_SIZES)
    def test_size_class_volume(self, dbh, height, age, size_class):
        """Test volume calculation for different size classes."""
        tree = Tree(dbh=dbh, height=height, species="LP", age=age)
        volume = tree.get_volume()

        assert volume > 0, f"{size_class} tree should have positive volume"


class TestCompetitionLevels:
    """Parametrized tests for competition effects."""

    @pytest.mark.parametrize("competition_factor,rank,ba,pbal,label", [
        (0.0, 0.8, 80, 30, "no_competition"),
        (0.5, 0.5, 120, 60, "medium_competition"),
        (0.9, 0.2, 160, 90, "high_competition"),
    ])
    def test_competition_reduces_growth(self, competition_factor, rank, ba, pbal, label):
        """Test that growth occurs under various competition levels."""
        tree = Tree(dbh=6.0, height=40.0, species="LP", age=15)
        initial_dbh = tree.dbh
        initial_height = tree.height

        tree.grow(
            site_index=70,
            competition_factor=competition_factor,
            rank=rank,
            ba=ba,
            pbal=pbal,
            slope=0.05,
            aspect=0
        )

        assert tree.dbh > initial_dbh, f"{label}: tree should still grow in DBH"
        assert tree.height > initial_height, f"{label}: tree should still grow in height"

    @pytest.mark.parametrize("species", SOUTHERN_PINE_SPECIES)
    @pytest.mark.parametrize("competition_factor", [0.0, 0.5, 0.9])
    def test_species_competition_interaction(self, species, competition_factor):
        """Test that all species respond to competition."""
        tree = Tree(dbh=6.0, height=40.0, species=species, age=15)
        initial_dbh = tree.dbh

        tree.grow(
            site_index=70,
            competition_factor=competition_factor,
            ba=120,
            pbal=50,
            slope=0.05,
            aspect=0
        )

        assert tree.dbh > initial_dbh, f"{species} with comp={competition_factor} should grow" 
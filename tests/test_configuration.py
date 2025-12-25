"""
Configuration tests for FVS-Python.
Tests configuration loading, validation, and format conversion.
"""
import pytest
import yaml
import tempfile
import shutil
from pathlib import Path

from pyfvs.config_loader import ConfigLoader, get_config_loader
from pyfvs.exceptions import (
    ConfigurationError, 
    SpeciesNotFoundError,
    FileNotFoundError as FVSFileNotFoundError,
    InvalidDataError
)


class TestConfigLoader:
    """Test the configuration loading system."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_load_main_config(self):
        """Test loading the main configuration files."""
        loader = get_config_loader()
        
        # Should have loaded species config
        assert hasattr(loader, 'species_config')
        assert 'species' in loader.species_config
        assert 'LP' in loader.species_config['species']
        
        # Should have loaded functional forms
        assert hasattr(loader, 'functional_forms')
        
        # Should have loaded site index params
        assert hasattr(loader, 'site_index_params')
    
    def test_load_species_config(self):
        """Test loading individual species configurations."""
        loader = get_config_loader()
        
        # Test valid species
        lp_config = loader.load_species_config('LP')
        assert 'diameter_growth' in lp_config
        assert 'height_diameter' in lp_config
        assert 'coefficients' in lp_config['diameter_growth']
        
        # Test invalid species
        with pytest.raises(SpeciesNotFoundError) as exc_info:
            loader.load_species_config('INVALID')
        assert 'INVALID' in str(exc_info.value)
    
    def test_yaml_loading(self, temp_config_dir):
        """Test YAML file loading."""
        # Use the global loader to test the method (avoid reinitializing)
        loader = get_config_loader()

        # Create test YAML file in temp directory
        test_yaml = temp_config_dir / 'test.yaml'
        test_data = {
            'test_key': 'test_value',
            'nested': {'key': 'value'},
            'list': [1, 2, 3]
        }
        with open(test_yaml, 'w') as f:
            yaml.dump(test_data, f)

        # Load and verify
        loaded = loader._load_config_file(test_yaml)
        assert loaded == test_data
    
    def test_toml_loading(self, temp_config_dir):
        """Test TOML file loading if available."""
        try:
            import tomli_w
        except ImportError:
            pytest.skip("tomli_w not available for TOML testing")

        # Use the global loader to test the method
        loader = get_config_loader()

        # Create test TOML file in temp directory
        test_toml = temp_config_dir / 'test.toml'
        test_data = {
            'section': {
                'key': 'value',
                'number': 42
            }
        }
        with open(test_toml, 'wb') as f:
            tomli_w.dump(test_data, f)

        # Load and verify
        loaded = loader._load_config_file(test_toml)
        assert loaded == test_data
    
    def test_missing_file_error(self, temp_config_dir):
        """Test error handling for missing files."""
        # Use the global loader to test the method
        loader = get_config_loader()

        with pytest.raises(FVSFileNotFoundError) as exc_info:
            loader._load_config_file(temp_config_dir / 'nonexistent.yaml')

        assert 'nonexistent.yaml' in str(exc_info.value)
        assert 'configuration file' in str(exc_info.value)
    
    def test_invalid_yaml_error(self, temp_config_dir):
        """Test error handling for invalid YAML."""
        # Use the global loader to test the method
        loader = get_config_loader()

        # Create invalid YAML file
        invalid_yaml = temp_config_dir / 'invalid.yaml'
        with open(invalid_yaml, 'w') as f:
            f.write("invalid: yaml: content: [unclosed")

        with pytest.raises(InvalidDataError) as exc_info:
            loader._load_config_file(invalid_yaml)

        assert 'YAML' in str(exc_info.value)
        assert 'parsing error' in str(exc_info.value)
    
    def test_unsupported_format_error(self, temp_config_dir):
        """Test error handling for unsupported file formats."""
        # Use the global loader to test the method
        loader = get_config_loader()

        # Create file with unsupported extension
        unsupported = temp_config_dir / 'config.txt'
        unsupported.touch()

        with pytest.raises(ConfigurationError) as exc_info:
            loader._load_config_file(unsupported)

        assert '.txt' in str(exc_info.value)
        assert 'Unsupported' in str(exc_info.value)
    
    def test_get_stand_params(self):
        """Test getting stand parameters in legacy format."""
        loader = get_config_loader()
        
        # Test default species
        params = loader.get_stand_params()
        assert 'species' in params
        assert 'crown' in params
        assert 'mortality' in params
        assert params['species'] == 'lp_pine'
        
        # Test specific species
        params = loader.get_stand_params('SP')
        assert params['species'] == 'sp_pine'
    
    def test_yaml_to_toml_conversion(self, temp_config_dir):
        """Test YAML to TOML conversion functionality."""
        # Create test YAML structure
        yaml_dir = temp_config_dir / 'yaml'
        yaml_dir.mkdir()

        # Create species config with all required fields
        species_config = {
            'functional_forms_file': 'functional_forms.yaml',
            'site_index_transformation_file': 'site_index_transformation.yaml',
            'species': {
                'TEST': {
                    'name': 'test_species',
                    'file': 'species/test.yaml'
                }
            }
        }
        with open(yaml_dir / 'species_config.yaml', 'w') as f:
            yaml.dump(species_config, f)

        # Create functional forms file
        functional_forms = {'forms': {'test': 'value'}}
        with open(yaml_dir / 'functional_forms.yaml', 'w') as f:
            yaml.dump(functional_forms, f)

        # Create site index transformation file
        site_index = {'transformations': {'test': 'value'}}
        with open(yaml_dir / 'site_index_transformation.yaml', 'w') as f:
            yaml.dump(site_index, f)

        # Create species file directory
        species_dir = yaml_dir / 'species'
        species_dir.mkdir()

        # Create species file
        species_data = {
            'diameter_growth': {
                'coefficients': {'b1': 0.1, 'b2': 0.2}
            }
        }
        with open(species_dir / 'test.yaml', 'w') as f:
            yaml.dump(species_data, f)

        # Test conversion
        loader = ConfigLoader(yaml_dir)
        toml_dir = temp_config_dir / 'toml'

        try:
            loader.create_toml_config_from_yaml(toml_dir)

            # Verify TOML files were created
            assert (toml_dir / 'species_config.toml').exists()
            assert (toml_dir / 'species' / 'test.toml').exists()
        except ImportError:
            pytest.skip("TOML writing not available")


class TestGrowthModelParameters:
    """Test the new growth model parameters configuration."""
    
    def test_growth_params_loading(self):
        """Test loading growth_model_parameters.yaml."""
        loader = get_config_loader()
        
        # Load the growth params file
        growth_params_file = loader.cfg_dir / 'growth_model_parameters.yaml'
        if growth_params_file.exists():
            growth_params = loader._load_config_file(growth_params_file)
            
            # Verify structure
            assert 'growth_transitions' in growth_params
            assert 'small_tree_growth' in growth_params
            assert 'large_tree_modifiers' in growth_params
            assert 'mortality' in growth_params
            
            # Verify transition parameters
            transitions = growth_params['growth_transitions']['small_to_large_tree']
            assert 'xmin' in transitions
            assert 'xmax' in transitions
            assert transitions['xmin'] < transitions['xmax']
            
            # Verify small tree parameters
            assert 'default' in growth_params['small_tree_growth']
            default_params = growth_params['small_tree_growth']['default']
            assert all(f'c{i}' in default_params for i in range(1, 6))
            
            # Verify mortality parameters
            mortality = growth_params['mortality']
            assert 'early_mortality' in mortality
            assert 'background_mortality' in mortality
            assert mortality['early_mortality']['base_rate'] > 0
    
    def test_species_specific_parameters(self):
        """Test that species-specific parameters override defaults."""
        from pyfvs.tree import Tree
        
        # Create tree and check it loads parameters
        tree = Tree(dbh=2.0, height=15.0, species='LP')
        
        # Check growth params were loaded
        assert hasattr(tree, 'growth_params')
        assert 'growth_transitions' in tree.growth_params
        
        # If LP-specific params exist, they should be used
        if 'LP' in tree.growth_params.get('small_tree_growth', {}):
            lp_params = tree.growth_params['small_tree_growth']['LP']
            assert 'c1' in lp_params
    
    def test_fallback_values(self):
        """Test that fallback values work when config is missing."""
        from pyfvs.tree import Tree
        
        # Temporarily rename config file to simulate missing file
        loader = get_config_loader()
        growth_params_file = loader.cfg_dir / 'growth_model_parameters.yaml'
        temp_name = loader.cfg_dir / 'growth_model_parameters.yaml.bak'
        
        if growth_params_file.exists():
            growth_params_file.rename(temp_name)
        
        try:
            # Create tree - should use fallback values
            tree = Tree(dbh=2.0, height=15.0, species='LP')
            
            # Check fallback values are present
            assert tree.growth_params['growth_transitions']['small_to_large_tree']['xmin'] == 1.0
            assert tree.growth_params['growth_transitions']['small_to_large_tree']['xmax'] == 3.0
            
        finally:
            # Restore file
            if temp_name.exists():
                temp_name.rename(growth_params_file)


class TestConfigurationIntegrity:
    """Test configuration file integrity and consistency."""
    
    def test_all_species_have_files(self):
        """Test that all species listed have corresponding config files."""
        loader = get_config_loader()
        
        missing_species = []
        for species_code, species_info in loader.species_config['species'].items():
            try:
                loader.load_species_config(species_code)
            except Exception:
                missing_species.append(species_code)
        
        assert len(missing_species) == 0, \
            f"Species with missing config files: {missing_species}"
    
    def test_species_parameter_consistency(self):
        """Test that all species configs have required parameters."""
        loader = get_config_loader()
        
        required_sections = ['diameter_growth', 'height_diameter']
        
        # Test a few key species
        for species in ['LP', 'SP', 'SA', 'LL']:
            if species in loader.species_config['species']:
                config = loader.load_species_config(species)
                
                for section in required_sections:
                    assert section in config, \
                        f"Species {species} missing required section: {section}"
                
                # Check diameter growth has coefficients
                assert 'coefficients' in config['diameter_growth'], \
                    f"Species {species} missing diameter growth coefficients"
                
                # Check height-diameter has model specification
                assert 'model' in config['height_diameter'] or \
                       'curtis_arney' in config['height_diameter'], \
                    f"Species {species} missing height-diameter model"
    
    def test_coefficient_ranges(self):
        """Test that coefficients are within reasonable ranges."""
        loader = get_config_loader()
        
        # Test LP as example
        lp_config = loader.load_species_config('LP')
        
        # Diameter growth coefficients
        dg_coeffs = lp_config['diameter_growth']['coefficients']
        
        # b1 (intercept) should be reasonable
        assert -5 < dg_coeffs['b1'] < 5, \
            f"Diameter growth intercept {dg_coeffs['b1']} out of range"
        
        # b2 (log DBH coefficient) should be positive
        assert dg_coeffs['b2'] > 0, \
            f"Log DBH coefficient should be positive, got {dg_coeffs['b2']}"
        
        # Height-diameter parameters
        hd_params = lp_config['height_diameter']
        if 'curtis_arney' in hd_params:
            ca_params = hd_params['curtis_arney']
            assert ca_params['p2'] > 0, "Curtis-Arney P2 should be positive"
            assert ca_params['p3'] > 0, "Curtis-Arney P3 should be positive"
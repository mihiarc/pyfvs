"""
Configuration loader for FVS-Python.
Provides unified access to YAML, TOML, and JSON configuration files.

Supports:
- YAML (.yaml, .yml) - species configurations, functional forms
- TOML (.toml) - structured configuration with types
- JSON (.json) - coefficient files (bark ratio, crown width, CCF, etc.)

Features:
- Coefficient file caching for performance
- Unified API for all configuration types
"""
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Union
import sys
from .exceptions import ConfigurationError
from .utils import normalize_species_code

# Handle TOML imports for different Python versions
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    import tomli_w
except ImportError:
    tomli_w = None


class ConfigLoader:
    """Loads and manages FVS configuration from the cfg/ directory.

    Provides unified access to:
    - Species configuration (YAML)
    - Functional forms (YAML)
    - Coefficient files (JSON) with caching

    Attributes:
        cfg_dir: Path to the configuration directory
        species_config: Loaded species configuration
        functional_forms: Loaded functional forms
        site_index_params: Loaded site index parameters
    """

    def __init__(self, cfg_dir: Path = None):
        """Initialize the configuration loader.

        Args:
            cfg_dir: Path to the configuration directory. Defaults to ../cfg relative to this file.
        """
        if cfg_dir is None:
            # cfg/ directory is now inside the package
            cfg_dir = Path(__file__).parent / 'cfg'
        self.cfg_dir = cfg_dir

        # Cache for coefficient files (loaded once, reused)
        self._coefficient_cache: Dict[str, Dict[str, Any]] = {}

        # Load main configuration files
        self._load_main_config()
    
    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from YAML or TOML file.
        
        Args:
            file_path: Path to the configuration file
            
        Returns:
            Dictionary containing configuration data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ConfigurationError: If file format is not supported or parsing fails
        """
        from .exceptions import FileNotFoundError as FVSFileNotFoundError, ConfigurationError, InvalidDataError
        
        if not file_path.exists():
            raise FVSFileNotFoundError(str(file_path), "configuration file")
        
        suffix = file_path.suffix.lower()
        
        try:
            if suffix in ['.yaml', '.yml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data is None:
                        raise InvalidDataError("YAML file", "file is empty or contains only comments")
                    return data
            elif suffix == '.toml':
                if tomllib is None:
                    raise ImportError(
                        "TOML support requires 'tomli' package for Python < 3.11. "
                        "Install with: pip install tomli"
                    )
                with open(file_path, 'rb') as f:
                    return tomllib.load(f)
            elif suffix == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data is None:
                        raise InvalidDataError("JSON file", "file is empty or contains null")
                    return data
            else:
                raise ConfigurationError(f"Unsupported configuration file format: {suffix}. "
                                       f"Supported formats: .yaml, .yml, .toml, .json")
        except yaml.YAMLError as e:
            raise InvalidDataError("YAML configuration", f"parsing error: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise InvalidDataError("JSON configuration", f"parsing error: {str(e)}") from e
        except Exception as e:
            if isinstance(e, (FVSFileNotFoundError, ConfigurationError, InvalidDataError)):
                raise
            raise ConfigurationError(f"Failed to load configuration from {file_path}: {str(e)}") from e
    
    def _save_config_file(self, data: Dict[str, Any], file_path: Path) -> None:
        """Save configuration to YAML or TOML file.
        
        Args:
            data: Configuration data to save
            file_path: Path where to save the file
            
        Raises:
            ValueError: If file format is not supported
        """
        suffix = file_path.suffix.lower()
        
        # Create parent directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if suffix in ['.yaml', '.yml']:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        elif suffix == '.toml':
            if tomli_w is None:
                raise ImportError(
                    "TOML writing requires 'tomli-w' package. "
                    "Install with: pip install tomli-w"
                )
            with open(file_path, 'wb') as f:
                tomli_w.dump(data, f)
        else:
            raise ValueError(f"Unsupported configuration file format: {suffix}")
    
    def _load_main_config(self):
        """Load the main configuration files."""
        # Try to load species configuration (prefer TOML, fallback to YAML)
        species_config_files = [
            self.cfg_dir / 'species_config.toml',
            self.cfg_dir / 'species_config.yaml'
        ]
        
        species_config_file = None
        for config_file in species_config_files:
            if config_file.exists():
                species_config_file = config_file
                break
        
        if species_config_file is None:
            raise FileNotFoundError(
                f"No species configuration file found. Looked for: {species_config_files}"
            )
        
        self.species_config = self._load_config_file(species_config_file)
        
        # Load functional forms
        functional_forms_file = self.cfg_dir / self.species_config['functional_forms_file']
        self.functional_forms = self._load_config_file(functional_forms_file)
        
        # Load site index transformations
        site_index_file = self.cfg_dir / self.species_config['site_index_transformation_file']
        self.site_index_params = self._load_config_file(site_index_file)
    
    def load_species_config(self, species_code: str) -> Dict[str, Any]:
        """Load configuration for a specific species.

        Args:
            species_code: Species code (e.g., 'LP', 'SP', 'SA', 'LL')

        Returns:
            Dictionary containing species-specific parameters

        Raises:
            SpeciesNotFoundError: If species code is not found
            ConfigurationError: If species file cannot be loaded
        """
        from .exceptions import SpeciesNotFoundError

        normalized_code = normalize_species_code(species_code)
        if normalized_code not in self.species_config['species']:
            raise SpeciesNotFoundError(species_code)

        try:
            species_info = self.species_config['species'][normalized_code]
            species_file = self.cfg_dir / species_info['file']
            
            return self._load_config_file(species_file)
        except Exception as e:
            if isinstance(e, SpeciesNotFoundError):
                raise
            raise ConfigurationError(
                f"Failed to load configuration for species '{species_code}': {str(e)}"
            ) from e
    
    def get_stand_params(self, species_code: str = 'LP') -> Dict[str, Any]:
        """Get parameters needed for Stand class in the legacy format.

        Args:
            species_code: Species code (default: 'LP' for loblolly pine)

        Returns:
            Dictionary with parameters in the format expected by Stand class
        """
        normalized_code = normalize_species_code(species_code)
        species_params = self.load_species_config(normalized_code)

        # Convert to legacy format expected by Stand class
        stand_params = {
            'species': normalized_code.lower() + '_pine',
            'crown': {
                # Extract crown width parameters for loblolly pine
                'a1': 0.7380,  # From README.md species data
                'a2': 0.2450,
                'a3': 0.000809
            },
            'mortality': {
                'max_sdi': species_params.get('density', {}).get('sdi_max', 480),
                'background_rate': 0.005,
                'competition_threshold': 0.55
            },
            'volume': {
                'form_factor': 0.48
            }
        }
        
        return stand_params
    
    def get_tree_params(self, species_code: str = 'LP') -> Dict[str, Any]:
        """Get parameters needed for Tree class.

        Args:
            species_code: Species code (default: 'LP' for loblolly pine)

        Returns:
            Dictionary with parameters for Tree class
        """
        return self.load_species_config(species_code)

    def load_coefficient_file(self, filename: str) -> Dict[str, Any]:
        """Load a JSON coefficient file with caching.

        Coefficient files are loaded once and cached for performance.
        This is the preferred method for loading JSON files like:
        - sn_bark_ratio_coefficients.json
        - sn_crown_width_coefficients.json
        - sn_ccf_coefficients.json
        - sn_diameter_growth_coefficients.json
        - etc.

        Args:
            filename: Name of the coefficient file (e.g., 'sn_bark_ratio_coefficients.json')

        Returns:
            Dictionary containing coefficient data

        Raises:
            FileNotFoundError: If the file doesn't exist
            ConfigurationError: If the file cannot be parsed
        """
        if filename not in self._coefficient_cache:
            file_path = self.cfg_dir / filename
            self._coefficient_cache[filename] = self._load_config_file(file_path)
        return self._coefficient_cache[filename]

    def clear_coefficient_cache(self) -> None:
        """Clear the coefficient file cache.

        Useful for testing or when configuration files may have changed.
        """
        self._coefficient_cache.clear()
    
    def save_config(self, config_data: Dict[str, Any], file_path: Union[str, Path]) -> None:
        """Save configuration data to file.
        
        Args:
            config_data: Configuration data to save
            file_path: Path where to save the configuration
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        self._save_config_file(config_data, file_path)
    
    def create_toml_config_from_yaml(self, output_dir: Path = None) -> None:
        """Convert existing YAML configuration to TOML format.
        
        Args:
            output_dir: Directory to save TOML files. Defaults to cfg_dir/toml/
        """
        if output_dir is None:
            output_dir = self.cfg_dir / 'toml'
        
        output_dir.mkdir(exist_ok=True)
        
        # Convert main configuration files
        config_files = [
            'species_config.yaml',
            'functional_forms.yaml', 
            'site_index_transformation.yaml'
        ]
        
        for config_file in config_files:
            yaml_path = self.cfg_dir / config_file
            if yaml_path.exists():
                toml_path = output_dir / config_file.replace('.yaml', '.toml')
                config_data = self._load_config_file(yaml_path)
                self._save_config_file(config_data, toml_path)
                print(f"Converted {yaml_path} -> {toml_path}")
        
        # Convert species files
        species_dir = output_dir / 'species'
        species_dir.mkdir(exist_ok=True)
        
        for species_code, species_info in self.species_config['species'].items():
            yaml_path = self.cfg_dir / species_info['file']
            if yaml_path.exists():
                toml_filename = yaml_path.name.replace('.yaml', '.toml')
                toml_path = species_dir / toml_filename
                config_data = self._load_config_file(yaml_path)
                self._save_config_file(config_data, toml_path)
                print(f"Converted {yaml_path} -> {toml_path}")


# Global configuration loader instance
_config_loader = None

def get_config_loader() -> ConfigLoader:
    """Get the global configuration loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader

def load_stand_config(species_code: str = 'LP') -> Dict[str, Any]:
    """Convenience function to load stand configuration."""
    return get_config_loader().get_stand_params(species_code)

def load_tree_config(species_code: str = 'LP') -> Dict[str, Any]:
    """Convenience function to load tree configuration."""
    return get_config_loader().get_tree_params(species_code)


def load_coefficient_file(filename: str) -> Dict[str, Any]:
    """Convenience function to load a JSON coefficient file with caching.

    Args:
        filename: Name of the coefficient file (e.g., 'sn_bark_ratio_coefficients.json')

    Returns:
        Dictionary containing coefficient data
    """
    return get_config_loader().load_coefficient_file(filename)

def convert_yaml_to_toml(cfg_dir: Path = None, output_dir: Path = None) -> None:
    """Convert YAML configuration files to TOML format.
    
    Args:
        cfg_dir: Source configuration directory
        output_dir: Output directory for TOML files
    """
    loader = ConfigLoader(cfg_dir)
    loader.create_toml_config_from_yaml(output_dir) 
"""
Configuration loader for FVS-Python.
Provides unified access to YAML, TOML, and JSON configuration files.

Supports:
- YAML (.yaml, .yml) - species configurations, functional forms
- TOML (.toml) - structured configuration with types
- JSON (.json) - coefficient files (bark ratio, crown width, CCF, etc.)

Features:
- Multi-variant support (SN, LS, CS, NE, etc.)
- Coefficient file caching for performance
- Unified API for all configuration types

Variants:
- SN: Southern (default) - southeastern US pine/hardwood
- LS: Lake States - Great Lakes region (MI, WI, MN)
- CS: Central States - Midwest oak-hickory
- NE: Northeast - New England/Mid-Atlantic
"""
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Union, Optional
import sys
from .exceptions import ConfigurationError
from .utils import normalize_species_code

# Supported FVS variants
SUPPORTED_VARIANTS = {
    'SN': {'name': 'Southern', 'config_dir': '', 'species_count': 90},
    'LS': {'name': 'Lake States', 'config_dir': 'ls', 'species_count': 67},
    'PN': {'name': 'Pacific Northwest Coast', 'config_dir': 'pn', 'species_count': 39},
    'WC': {'name': 'West Cascades', 'config_dir': 'wc', 'species_count': 37},
    'NE': {'name': 'Northeast', 'config_dir': 'ne', 'species_count': 108},
    'CS': {'name': 'Central States', 'config_dir': 'cs', 'species_count': 96},
    'CA': {'name': 'Inland California', 'config_dir': 'ca', 'species_count': 50},
    'OP': {'name': 'ORGANON Pacific Northwest', 'config_dir': 'op', 'species_count': 18},
    'OC': {'name': 'FVS Southwest Oregon', 'config_dir': 'oc', 'species_count': 50},
    'WS': {'name': 'Western Sierra Nevada', 'config_dir': 'ws', 'species_count': 43},
    'EC': {'name': 'East Cascades', 'config_dir': 'ec', 'species_count': 32},
}

DEFAULT_VARIANT = 'SN'

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

    Supports multiple FVS variants (SN, LS, CS, NE, etc.)

    Attributes:
        cfg_dir: Path to the base configuration directory
        variant: FVS variant code (SN, LS, etc.)
        variant_dir: Path to the variant-specific configuration directory
        species_config: Loaded species configuration
        functional_forms: Loaded functional forms
        site_index_params: Loaded site index parameters
    """

    def __init__(self, cfg_dir: Path = None, variant: str = None):
        """Initialize the configuration loader.

        Args:
            cfg_dir: Path to the configuration directory. Defaults to ../cfg relative to this file.
            variant: FVS variant code (SN, LS, CS, NE). Defaults to SN (Southern).
        """
        if cfg_dir is None:
            # cfg/ directory is now inside the package
            cfg_dir = Path(__file__).parent / 'cfg'
        self.cfg_dir = cfg_dir

        # Set variant (default to SN)
        self.variant = (variant or DEFAULT_VARIANT).upper()
        if self.variant not in SUPPORTED_VARIANTS:
            raise ConfigurationError(
                f"Unsupported variant '{self.variant}'. "
                f"Supported variants: {list(SUPPORTED_VARIANTS.keys())}"
            )

        # Set variant-specific directory
        variant_subdir = SUPPORTED_VARIANTS[self.variant]['config_dir']
        if variant_subdir:
            self.variant_dir = self.cfg_dir / variant_subdir
        else:
            self.variant_dir = self.cfg_dir  # SN uses base cfg dir

        # Cache for coefficient files (loaded once, reused)
        self._coefficient_cache: Dict[str, Dict[str, Any]] = {}

        # Cache for config files (YAML/JSON/TOML parsed once per file path)
        self._config_file_cache: Dict[str, Dict[str, Any]] = {}

        # Load main configuration files
        self._load_main_config()
    
    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from YAML or TOML file.

        Results are cached by file path to avoid repeatedly parsing the same
        files. This is critical for performance when creating many Tree objects
        with the same species, since each Tree.__init__ loads species config.

        Args:
            file_path: Path to the configuration file

        Returns:
            Dictionary containing configuration data

        Raises:
            FileNotFoundError: If file doesn't exist
            ConfigurationError: If file format is not supported or parsing fails
        """
        from .exceptions import FileNotFoundError as FVSFileNotFoundError, ConfigurationError, InvalidDataError

        cache_key = str(file_path)
        if cache_key in self._config_file_cache:
            return self._config_file_cache[cache_key]

        if not file_path.exists():
            raise FVSFileNotFoundError(str(file_path), "configuration file")
        
        suffix = file_path.suffix.lower()
        
        try:
            if suffix in ['.yaml', '.yml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data is None:
                        raise InvalidDataError("YAML file", "file is empty or contains only comments")
            elif suffix == '.toml':
                if tomllib is None:
                    raise ImportError(
                        "TOML support requires 'tomli' package for Python < 3.11. "
                        "Install with: pip install tomli"
                    )
                with open(file_path, 'rb') as f:
                    data = tomllib.load(f)
            elif suffix == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data is None:
                        raise InvalidDataError("JSON file", "file is empty or contains null")
                # Validate JSON coefficient files against registered schemas
                from .config_schemas import validate_coefficient_file
                try:
                    relative_name = str(file_path.relative_to(self.cfg_dir))
                except ValueError:
                    relative_name = file_path.name
                validate_coefficient_file(relative_name, data)
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

        self._config_file_cache[cache_key] = data
        return data
    
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
        """Load the main configuration files for the selected variant."""
        # Determine species config file name based on variant
        if self.variant == 'SN':
            config_names = ['species_config.toml', 'species_config.yaml']
        else:
            # Other variants use variant-prefixed config files
            variant_lower = self.variant.lower()
            config_names = [
                f'{variant_lower}_species_config.toml',
                f'{variant_lower}_species_config.yaml'
            ]

        # Try to load species configuration (prefer TOML, fallback to YAML)
        species_config_files = [self.variant_dir / name for name in config_names]

        species_config_file = None
        for config_file in species_config_files:
            if config_file.exists():
                species_config_file = config_file
                break

        if species_config_file is None:
            raise FileNotFoundError(
                f"No species configuration file found for variant {self.variant}. "
                f"Looked for: {species_config_files}"
            )

        self.species_config = self._load_config_file(species_config_file)

        # Load functional forms (SN variant has these, others may not)
        if 'functional_forms_file' in self.species_config:
            functional_forms_file = self.cfg_dir / self.species_config['functional_forms_file']
            self.functional_forms = self._load_config_file(functional_forms_file)
        else:
            # Use SN functional forms as fallback for other variants
            fallback_file = self.cfg_dir / 'functional_forms.yaml'
            if fallback_file.exists():
                self.functional_forms = self._load_config_file(fallback_file)
            else:
                self.functional_forms = {}

        # Load site index transformations (SN variant has these, others may not)
        if 'site_index_transformation_file' in self.species_config:
            site_index_file = self.cfg_dir / self.species_config['site_index_transformation_file']
            self.site_index_params = self._load_config_file(site_index_file)
        else:
            # Use SN site index params as fallback
            fallback_file = self.cfg_dir / 'site_index_transformation.yaml'
            if fallback_file.exists():
                self.site_index_params = self._load_config_file(fallback_file)
            else:
                self.site_index_params = {}
    
    def load_species_config(self, species_code: str) -> Dict[str, Any]:
        """Load configuration for a specific species.

        Args:
            species_code: Species code (e.g., 'LP', 'SP', 'JP', 'RP')

        Returns:
            Dictionary containing species-specific parameters

        Raises:
            SpeciesNotFoundError: If species code is not found
            ConfigurationError: If species file cannot be loaded
        """
        from .exceptions import SpeciesNotFoundError

        normalized_code = normalize_species_code(species_code)
        if normalized_code not in self.species_config['species']:
            available = list(self.species_config['species'].keys())[:10]
            raise SpeciesNotFoundError(
                f"{species_code} (variant: {self.variant}). Available species: {available}..."
            )

        try:
            species_info = self.species_config['species'][normalized_code]
            # Use variant_dir for species files
            species_file = self.variant_dir / species_info['file']

            config = self._load_config_file(species_file)
            # Add variant info to the config
            config['_variant'] = self.variant
            return config
        except Exception as e:
            if isinstance(e, SpeciesNotFoundError):
                raise
            raise ConfigurationError(
                f"Failed to load configuration for species '{species_code}' "
                f"in variant {self.variant}: {str(e)}"
            ) from e
    
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
        Looks in variant directory first, then falls back to base cfg directory.

        For variant-specific files:
        - LS variant: ls_diameter_growth_coefficients.json
        - SN variant: sn_diameter_growth_coefficients.json
        - etc.

        Args:
            filename: Name of the coefficient file (e.g., 'sn_bark_ratio_coefficients.json')

        Returns:
            Dictionary containing coefficient data

        Raises:
            FileNotFoundError: If the file doesn't exist
            ConfigurationError: If the file cannot be parsed
        """
        cache_key = f"{self.variant}:{filename}"
        if cache_key not in self._coefficient_cache:
            # Try variant directory first
            file_path = self.variant_dir / filename
            if not file_path.exists():
                # Fall back to base cfg directory
                file_path = self.cfg_dir / filename
            self._coefficient_cache[cache_key] = self._load_config_file(file_path)
        return self._coefficient_cache[cache_key]

    def get_variant_info(self) -> Dict[str, Any]:
        """Get information about the current variant.

        Returns:
            Dictionary with variant code, name, and species count
        """
        info = SUPPORTED_VARIANTS[self.variant].copy()
        info['code'] = self.variant
        info['variant_dir'] = str(self.variant_dir)
        return info

    def validate_all_configs(self):
        """Validate all JSON coefficient files in cfg/ against registered schemas.

        Returns:
            List of ValidationWarning objects from config_schemas.validate_all_configs.
        """
        from .config_schemas import validate_all_configs
        return validate_all_configs(self.cfg_dir)

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


# Global configuration loader instances (one per variant)
_config_loaders: Dict[str, ConfigLoader] = {}
_current_variant = DEFAULT_VARIANT


def get_config_loader(variant: str = None) -> ConfigLoader:
    """Get a configuration loader instance for the specified variant.

    Args:
        variant: FVS variant code (SN, LS, CS, NE). If None, uses current default.

    Returns:
        ConfigLoader instance for the specified variant
    """
    global _config_loaders, _current_variant
    variant = (variant or _current_variant).upper()

    if variant not in _config_loaders:
        _config_loaders[variant] = ConfigLoader(variant=variant)

    return _config_loaders[variant]


def set_default_variant(variant: str) -> None:
    """Set the default variant for all subsequent operations.

    Args:
        variant: FVS variant code (SN, LS, CS, NE)
    """
    global _current_variant
    variant = variant.upper()
    if variant not in SUPPORTED_VARIANTS:
        raise ConfigurationError(
            f"Unsupported variant '{variant}'. "
            f"Supported variants: {list(SUPPORTED_VARIANTS.keys())}"
        )
    _current_variant = variant


def get_default_variant() -> str:
    """Get the current default variant.

    Returns:
        Current default variant code
    """
    return _current_variant


def load_tree_config(species_code: str = 'LP', variant: str = None) -> Dict[str, Any]:
    """Convenience function to load tree configuration.

    Args:
        species_code: Species code (e.g., 'LP' for SN, 'JP' for LS)
        variant: FVS variant code. If None, uses current default.
    """
    return get_config_loader(variant).get_tree_params(species_code)


def load_coefficient_file(filename: str, variant: str = None) -> Dict[str, Any]:
    """Convenience function to load a JSON coefficient file with caching.

    Args:
        filename: Name of the coefficient file (e.g., 'sn_bark_ratio_coefficients.json')
        variant: FVS variant code. If None, uses current default.

    Returns:
        Dictionary containing coefficient data
    """
    return get_config_loader(variant).load_coefficient_file(filename)

def convert_yaml_to_toml(cfg_dir: Path = None, output_dir: Path = None) -> None:
    """Convert YAML configuration files to TOML format.
    
    Args:
        cfg_dir: Source configuration directory
        output_dir: Output directory for TOML files
    """
    loader = ConfigLoader(cfg_dir)
    loader.create_toml_config_from_yaml(output_dir) 
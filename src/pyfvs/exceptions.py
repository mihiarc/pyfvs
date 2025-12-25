"""
Custom exceptions for FVS-Python.
Provides domain-specific error handling with informative messages.
"""


class FVSError(Exception):
    """Base exception for all FVS-Python errors."""
    pass


class ConfigurationError(FVSError):
    """Raised when there are configuration-related issues."""
    pass


class SpeciesNotFoundError(ConfigurationError):
    """Raised when a species code is not found in configuration."""
    def __init__(self, species_code: str):
        self.species_code = species_code
        super().__init__(f"Species '{species_code}' not found in configuration. "
                        f"Valid species codes can be found in cfg/species_config.yaml")


class ParameterError(FVSError):
    """Raised when parameters are invalid or out of bounds."""
    pass


class InvalidParameterError(ParameterError):
    """Raised when a parameter value is invalid."""
    def __init__(self, param_name: str, value: any, reason: str = ""):
        self.param_name = param_name
        self.value = value
        self.reason = reason
        message = f"Invalid value for parameter '{param_name}': {value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)


class SimulationError(FVSError):
    """Raised when simulation encounters an error."""
    pass


class GrowthModelError(SimulationError):
    """Raised when growth model calculations fail."""
    def __init__(self, model_name: str, reason: str):
        self.model_name = model_name
        self.reason = reason
        super().__init__(f"Growth model '{model_name}' failed: {reason}")


class StandError(SimulationError):
    """Raised when stand-level operations fail."""
    pass


class EmptyStandError(StandError):
    """Raised when operations are attempted on an empty stand."""
    def __init__(self, operation: str):
        self.operation = operation
        super().__init__(f"Cannot perform '{operation}' on an empty stand. "
                        f"Add trees before running simulations.")


class DataError(FVSError):
    """Raised when there are data-related issues."""
    pass


class FileNotFoundError(DataError):
    """Raised when a required file is not found."""
    def __init__(self, file_path: str, file_type: str = "file"):
        self.file_path = file_path
        self.file_type = file_type
        super().__init__(f"Required {file_type} not found: {file_path}")


class InvalidDataError(DataError):
    """Raised when data is malformed or invalid."""
    def __init__(self, data_description: str, reason: str):
        self.data_description = data_description
        self.reason = reason
        super().__init__(f"Invalid {data_description}: {reason}")
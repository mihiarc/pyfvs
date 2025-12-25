"""
Logging configuration for FVS-Python.
Provides structured logging with different levels and formats.
"""
import logging
import logging.config
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'species'):
            log_data['species'] = record.species
        if hasattr(record, 'stand_id'):
            log_data['stand_id'] = record.stand_id
        if hasattr(record, 'simulation_year'):
            log_data['simulation_year'] = record.simulation_year
        if hasattr(record, 'tree_count'):
            log_data['tree_count'] = record.tree_count
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging(
    log_level: str = 'INFO',
    log_file: Optional[Path] = None,
    structured: bool = False
) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        structured: Whether to use structured (JSON) logging
    """
    # Base configuration
    config: Dict[str, Any] = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(funcName)s:%(lineno)d] - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'structured': {
                '()': StructuredFormatter
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'standard' if not structured else 'structured',
                'stream': 'ext://sys.stdout'
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['console']
        },
        'loggers': {
            'fvs_python': {
                'level': log_level,
                'handlers': ['console'],
                'propagate': False
            }
        }
    }
    
    # Add file handler if specified
    if log_file:
        config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'detailed' if not structured else 'structured',
            'filename': str(log_file),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        }
        config['root']['handlers'].append('file')
        config['loggers']['fvs_python']['handlers'].append('file')
    
    # Apply configuration
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class SimulationLogContext:
    """Context manager for simulation-specific logging context."""
    
    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize logging context.
        
        Args:
            logger: Logger instance
            **context: Context variables (species, stand_id, etc.)
        """
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        """Enter context and set up log record factory."""
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        self.old_factory = old_factory
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original factory."""
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


# Convenience functions for common log messages
def log_simulation_start(logger: logging.Logger, species: str, years: int, 
                        trees_per_acre: int, site_index: float) -> None:
    """Log simulation start."""
    logger.info(
        f"Starting simulation: species={species}, years={years}, "
        f"TPA={trees_per_acre}, SI={site_index}"
    )


def log_simulation_progress(logger: logging.Logger, current_year: int, 
                          total_years: int, trees_alive: int) -> None:
    """Log simulation progress."""
    progress = (current_year / total_years) * 100
    logger.debug(
        f"Simulation progress: {current_year}/{total_years} years "
        f"({progress:.1f}%), {trees_alive} trees alive"
    )


def log_growth_summary(logger: logging.Logger, period: int,
                      dbh_growth: float, height_growth: float,
                      mortality: int) -> None:
    """Log growth period summary."""
    logger.info(
        f"Period {period} growth: DBH +{dbh_growth:.2f}\", "
        f"Height +{height_growth:.1f}', Mortality: {mortality} trees"
    )


def log_model_transition(logger: logging.Logger, tree_id: str,
                        from_model: str, to_model: str, dbh: float) -> None:
    """Log model transition for a tree."""
    logger.debug(
        f"Tree {tree_id} transitioned from {from_model} to {to_model} "
        f"model at DBH={dbh:.1f}\""
    )


def log_configuration_loaded(logger: logging.Logger, config_type: str,
                           config_file: str) -> None:
    """Log configuration loading."""
    logger.info(f"Loaded {config_type} configuration from {config_file}")


def log_error_with_context(logger: logging.Logger, error: Exception,
                         context: Dict[str, Any]) -> None:
    """Log error with additional context."""
    logger.error(
        f"Error occurred: {type(error).__name__}: {str(error)}",
        exc_info=True,
        extra=context
    )
"""
Height-diameter relationship functions for FVS-Python.
Implements Curtis-Arney and Wykoff models for predicting tree height from diameter.
"""
import math
from typing import Dict, Any, Optional
from .config_loader import get_config_loader

# Module-level cache for height-diameter parameters by species
_HD_PARAMS_CACHE: Dict[str, Dict[str, Any]] = {}


def _get_hd_params(species_code: str) -> Dict[str, Any]:
    """Get height-diameter parameters from cache or load once."""
    if species_code not in _HD_PARAMS_CACHE:
        loader = get_config_loader()
        species_config = loader.load_species_config(species_code)
        _HD_PARAMS_CACHE[species_code] = species_config['height_diameter']
    return _HD_PARAMS_CACHE[species_code]


class HeightDiameterModel:
    """Base class for height-diameter relationship models."""
    
    def __init__(self, species_code: str = "LP"):
        """Initialize with species-specific parameters.
        
        Args:
            species_code: Species code (e.g., "LP", "SP", "SA", etc.)
        """
        self.species_code = species_code
        self._load_parameters()
    
    def _load_parameters(self):
        """Load height-diameter parameters from cached configuration."""
        self.hd_params = _get_hd_params(self.species_code)
    
    def predict_height(self, dbh: float, model: str = None) -> float:
        """Predict height from diameter.
        
        Args:
            dbh: Diameter at breast height (inches)
            model: Model to use ('curtis_arney' or 'wykoff'). If None, uses default.
            
        Returns:
            Predicted height (feet)
        """
        if model is None:
            model = self.hd_params.get('model', 'curtis_arney')
        
        if model == 'curtis_arney':
            return self.curtis_arney_height(dbh)
        elif model == 'wykoff':
            return self.wykoff_height(dbh)
        else:
            raise ValueError(f"Unknown height-diameter model: {model}")
    
    def curtis_arney_height(self, dbh: float) -> float:
        """Calculate height using Curtis-Arney equation.
        
        The Curtis-Arney equation is:
        Height = 4.5 + P2 * exp(-P3 * DBH^P4)
        
        For small trees (DBH < 3.0), uses linear interpolation.
        
        Args:
            dbh: Diameter at breast height (inches)
            
        Returns:
            Predicted height (feet)
        """
        params = self.hd_params['curtis_arney']
        p2 = params['p2']
        p3 = params['p3']
        p4 = params['p4']
        dbw = params['dbw']  # Diameter breakpoint for small trees
        
        if dbh <= dbw:
            return 4.5
        elif dbh < 3.0:
            # Linear interpolation for small trees
            h3 = 4.5 + p2 * math.exp(-p3 * 3.0**p4)
            return 4.5 + (h3 - 4.5) * (dbh - dbw) / (3.0 - dbw)
        else:
            # Standard Curtis-Arney equation for larger trees
            return 4.5 + p2 * math.exp(-p3 * dbh**p4)
    
    def wykoff_height(self, dbh: float) -> float:
        """Calculate height using Wykoff equation.
        
        The Wykoff equation is:
        Height = 4.5 + exp(B1 + B2 / (DBH + 1))
        
        Args:
            dbh: Diameter at breast height (inches)
            
        Returns:
            Predicted height (feet)
        """
        params = self.hd_params['wykoff']
        b1 = params['b1']
        b2 = params['b2']
        
        if dbh <= 0:
            return 4.5
        
        return 4.5 + math.exp(b1 + b2 / (dbh + 1))
    
    def solve_dbh_from_height(self, target_height: float, model: str = None, 
                             initial_dbh: float = 1.0, tolerance: float = 0.01, 
                             max_iterations: int = 20) -> float:
        """Solve for DBH given a target height using numerical methods.
        
        Args:
            target_height: Target height (feet)
            model: Model to use ('curtis_arney' or 'wykoff'). If None, uses default.
            initial_dbh: Initial guess for DBH (inches)
            tolerance: Convergence tolerance (feet)
            max_iterations: Maximum number of iterations
            
        Returns:
            Estimated DBH (inches)
        """
        if target_height <= 4.5:
            return self.hd_params['curtis_arney']['dbw']
        
        if model is None:
            model = self.hd_params.get('model', 'curtis_arney')
        
        dbh = initial_dbh
        
        for _ in range(max_iterations):
            predicted_height = self.predict_height(dbh, model)
            error = predicted_height - target_height
            
            if abs(error) < tolerance:
                break
            
            # Use Newton-Raphson method with numerical derivative
            h = 0.01  # Small step for numerical derivative
            predicted_height_plus = self.predict_height(dbh + h, model)
            derivative = (predicted_height_plus - predicted_height) / h
            
            if abs(derivative) < 1e-10:
                # Derivative too small, use simple adjustment
                dbh *= (target_height / predicted_height)**0.5
            else:
                # Newton-Raphson update
                dbh -= error / derivative
            
            # Ensure DBH stays positive
            dbh = max(0.1, dbh)
        
        return dbh
    
    def get_model_parameters(self, model: str = None) -> Dict[str, Any]:
        """Get parameters for a specific model.
        
        Args:
            model: Model name ('curtis_arney' or 'wykoff'). If None, returns all.
            
        Returns:
            Dictionary of model parameters
        """
        if model is None:
            return self.hd_params
        elif model in self.hd_params:
            return self.hd_params[model]
        else:
            raise ValueError(f"Unknown model: {model}")


def create_height_diameter_model(species_code: str = "LP") -> HeightDiameterModel:
    """Factory function to create a height-diameter model for a species.
    
    Args:
        species_code: Species code (e.g., "LP", "SP", "SA", etc.)
        
    Returns:
        HeightDiameterModel instance
    """
    return HeightDiameterModel(species_code)


def curtis_arney_height(dbh: float, p2: float, p3: float, p4: float, dbw: float = 0.1) -> float:
    """Standalone Curtis-Arney height function.
    
    Args:
        dbh: Diameter at breast height (inches)
        p2: Curtis-Arney parameter P2
        p3: Curtis-Arney parameter P3
        p4: Curtis-Arney parameter P4
        dbw: Diameter breakpoint for small trees (inches)
        
    Returns:
        Predicted height (feet)
    """
    if dbh <= dbw:
        return 4.5
    elif dbh < 3.0:
        # Linear interpolation for small trees
        h3 = 4.5 + p2 * math.exp(-p3 * 3.0**p4)
        return 4.5 + (h3 - 4.5) * (dbh - dbw) / (3.0 - dbw)
    else:
        # Standard Curtis-Arney equation
        return 4.5 + p2 * math.exp(-p3 * dbh**p4)


def wykoff_height(dbh: float, b1: float, b2: float) -> float:
    """Standalone Wykoff height function.
    
    Args:
        dbh: Diameter at breast height (inches)
        b1: Wykoff parameter B1
        b2: Wykoff parameter B2
        
    Returns:
        Predicted height (feet)
    """
    if dbh <= 0:
        return 4.5
    
    return 4.5 + math.exp(b1 + b2 / (dbh + 1))


def compare_models(dbh_range: list, species_code: str = "LP") -> Dict[str, list]:
    """Compare Curtis-Arney and Wykoff models over a range of DBH values.
    
    Args:
        dbh_range: List of DBH values to evaluate (inches)
        species_code: Species code for parameter lookup
        
    Returns:
        Dictionary with DBH values and predicted heights for each model
    """
    model = create_height_diameter_model(species_code)
    
    results = {
        'dbh': dbh_range,
        'curtis_arney': [],
        'wykoff': []
    }
    
    for dbh in dbh_range:
        results['curtis_arney'].append(model.curtis_arney_height(dbh))
        results['wykoff'].append(model.wykoff_height(dbh))
    
    return results 
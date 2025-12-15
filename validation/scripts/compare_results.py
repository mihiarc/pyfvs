"""
Statistical comparison functions for FVS validation.

Provides metrics and statistical tests for comparing FVS-Python predictions
against reference data (official FVS outputs or empirical observations).
"""
import math
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from scipy import stats


@dataclass
class ValidationMetrics:
    """Container for validation metrics comparing observed vs predicted values."""

    n: int
    bias: float
    mae: float
    rmse: float
    mape: float
    r_squared: float
    max_error: float
    min_error: float
    equivalence_test_passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "n": self.n,
            "bias": round(self.bias, 4),
            "mae": round(self.mae, 4),
            "rmse": round(self.rmse, 4),
            "mape": round(self.mape, 2),
            "r_squared": round(self.r_squared, 4),
            "max_error": round(self.max_error, 4),
            "min_error": round(self.min_error, 4),
            "equivalence_test_passed": self.equivalence_test_passed,
        }


def calculate_validation_metrics(
    observed: np.ndarray,
    predicted: np.ndarray,
    equivalence_threshold: Optional[float] = None
) -> ValidationMetrics:
    """
    Calculate standard validation metrics.

    Args:
        observed: Array of observed (reference) values
        predicted: Array of predicted values
        equivalence_threshold: Optional threshold for equivalence testing

    Returns:
        ValidationMetrics object with all computed metrics
    """
    observed = np.asarray(observed)
    predicted = np.asarray(predicted)

    if len(observed) != len(predicted):
        raise ValueError("observed and predicted must have same length")

    n = len(observed)
    if n == 0:
        raise ValueError("Arrays cannot be empty")

    # Calculate residuals
    residuals = predicted - observed

    # Basic metrics
    bias = np.mean(residuals)
    mae = np.mean(np.abs(residuals))
    rmse = np.sqrt(np.mean(residuals ** 2))

    # Mean Absolute Percentage Error (avoid division by zero)
    nonzero_mask = observed != 0
    if np.any(nonzero_mask):
        mape = np.mean(np.abs(residuals[nonzero_mask] / observed[nonzero_mask])) * 100
    else:
        mape = float('inf')

    # R-squared (coefficient of determination)
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((observed - np.mean(observed)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Error range
    max_error = np.max(residuals)
    min_error = np.min(residuals)

    # Equivalence test if threshold provided
    equivalence_passed = False
    if equivalence_threshold is not None:
        equivalence_passed = tost_equivalence_test(
            observed, predicted, equivalence_threshold
        )

    return ValidationMetrics(
        n=n,
        bias=bias,
        mae=mae,
        rmse=rmse,
        mape=mape,
        r_squared=r_squared,
        max_error=max_error,
        min_error=min_error,
        equivalence_test_passed=equivalence_passed,
    )


def tost_equivalence_test(
    observed: np.ndarray,
    predicted: np.ndarray,
    threshold: float,
    alpha: float = 0.05
) -> bool:
    """
    Two One-Sided Tests (TOST) procedure for equivalence.

    Tests whether the mean difference between observed and predicted is
    within the equivalence threshold.

    H0: |mean(observed) - mean(predicted)| >= threshold
    H1: |mean(observed) - mean(predicted)| < threshold

    Args:
        observed: Array of observed values
        predicted: Array of predicted values
        threshold: Equivalence threshold (same units as data)
        alpha: Significance level (default 0.05)

    Returns:
        True if equivalence is established at the given alpha level
    """
    observed = np.asarray(observed)
    predicted = np.asarray(predicted)

    diff = observed - predicted
    mean_diff = np.mean(diff)
    se_diff = np.std(diff, ddof=1) / np.sqrt(len(diff))

    if se_diff == 0:
        return abs(mean_diff) < threshold

    # Upper bound test: H0: mean_diff >= threshold
    t_upper = (mean_diff - threshold) / se_diff
    p_upper = stats.t.cdf(t_upper, len(diff) - 1)

    # Lower bound test: H0: mean_diff <= -threshold
    t_lower = (mean_diff + threshold) / se_diff
    p_lower = 1 - stats.t.cdf(t_lower, len(diff) - 1)

    # Both must be significant for equivalence
    return max(p_upper, p_lower) < alpha


def calculate_percent_error(
    observed: float,
    predicted: float
) -> float:
    """
    Calculate percent error between observed and predicted.

    Args:
        observed: Reference value
        predicted: Predicted value

    Returns:
        Percent error (positive = overprediction, negative = underprediction)
    """
    if observed == 0:
        return float('inf') if predicted != 0 else 0.0
    return ((predicted - observed) / observed) * 100


def check_acceptance_criteria(
    metrics: ValidationMetrics,
    metric_type: str
) -> Tuple[bool, str]:
    """
    Check if validation metrics meet acceptance criteria.

    Acceptance criteria from validation spec:
    - Diameter growth (5-yr): ±5% or ±0.1 inches
    - Height growth (5-yr): ±5% or ±0.5 feet
    - Basal area (stand): ±3%
    - Trees per acre: ±2%
    - Volume: ±10%

    Args:
        metrics: ValidationMetrics object
        metric_type: Type of metric ('diameter', 'height', 'basal_area', 'tpa', 'volume')

    Returns:
        Tuple of (passed: bool, message: str)
    """
    thresholds = {
        "diameter": {"mape": 5.0, "mae": 0.1, "units": "inches"},
        "height": {"mape": 5.0, "mae": 0.5, "units": "feet"},
        "basal_area": {"mape": 3.0, "units": "sq ft/acre"},
        "tpa": {"mape": 2.0, "units": "trees/acre"},
        "volume": {"mape": 10.0, "units": "cu ft/acre"},
    }

    if metric_type not in thresholds:
        return False, f"Unknown metric type: {metric_type}"

    threshold = thresholds[metric_type]

    # Check MAPE threshold
    if metrics.mape > threshold["mape"]:
        return False, (
            f"{metric_type} MAPE {metrics.mape:.1f}% exceeds threshold "
            f"of {threshold['mape']}%"
        )

    # Check absolute MAE threshold if specified
    if "mae" in threshold and metrics.mae > threshold["mae"]:
        return False, (
            f"{metric_type} MAE {metrics.mae:.3f} {threshold['units']} "
            f"exceeds threshold of {threshold['mae']} {threshold['units']}"
        )

    return True, f"{metric_type} validation PASSED (MAPE: {metrics.mape:.1f}%)"


def compare_yield_tables(
    fvs_data: Dict[str, List[float]],
    fvspy_data: Dict[str, List[float]],
    ages: List[int]
) -> Dict[str, ValidationMetrics]:
    """
    Compare yield table outputs between FVS and FVS-Python.

    Args:
        fvs_data: Dictionary with FVS outputs keyed by metric name
        fvspy_data: Dictionary with FVS-Python outputs keyed by metric name
        ages: List of stand ages for comparison points

    Returns:
        Dictionary of ValidationMetrics by metric name
    """
    results = {}

    metrics_to_compare = ["TPA", "BA", "QMD", "TopHt", "TCuFt", "MCuFt"]
    metric_types = {
        "TPA": "tpa",
        "BA": "basal_area",
        "QMD": "diameter",
        "TopHt": "height",
        "TCuFt": "volume",
        "MCuFt": "volume",
    }

    for metric in metrics_to_compare:
        if metric in fvs_data and metric in fvspy_data:
            observed = np.array(fvs_data[metric])
            predicted = np.array(fvspy_data[metric])

            # Determine equivalence threshold
            metric_type = metric_types.get(metric, "volume")
            if metric_type == "diameter":
                eq_threshold = 0.1
            elif metric_type == "height":
                eq_threshold = 0.5
            elif metric_type == "basal_area":
                eq_threshold = 3.0
            elif metric_type == "tpa":
                eq_threshold = 10.0
            else:
                eq_threshold = 50.0

            results[metric] = calculate_validation_metrics(
                observed, predicted, eq_threshold
            )

    return results


def generate_comparison_summary(
    scenario_results: Dict[str, Dict[str, ValidationMetrics]]
) -> Dict[str, Any]:
    """
    Generate summary statistics across all validation scenarios.

    Args:
        scenario_results: Dictionary mapping scenario_id to metric results

    Returns:
        Summary dictionary with overall pass/fail status and statistics
    """
    summary = {
        "total_scenarios": len(scenario_results),
        "passed_scenarios": 0,
        "failed_scenarios": 0,
        "metric_summaries": {},
        "scenario_details": [],
    }

    # Aggregate metrics across scenarios
    metric_values = {}

    for scenario_id, metrics in scenario_results.items():
        scenario_passed = True
        scenario_detail = {
            "scenario_id": scenario_id,
            "metrics": {},
            "passed": True,
        }

        for metric_name, metric_obj in metrics.items():
            if metric_name not in metric_values:
                metric_values[metric_name] = {
                    "mape": [],
                    "rmse": [],
                    "bias": [],
                }

            metric_values[metric_name]["mape"].append(metric_obj.mape)
            metric_values[metric_name]["rmse"].append(metric_obj.rmse)
            metric_values[metric_name]["bias"].append(metric_obj.bias)

            # Determine if this metric passed
            metric_type = {
                "TPA": "tpa", "BA": "basal_area", "QMD": "diameter",
                "TopHt": "height", "TCuFt": "volume", "MCuFt": "volume"
            }.get(metric_name, "volume")

            passed, _ = check_acceptance_criteria(metric_obj, metric_type)
            scenario_detail["metrics"][metric_name] = {
                "mape": metric_obj.mape,
                "passed": passed,
            }
            if not passed:
                scenario_passed = False

        scenario_detail["passed"] = scenario_passed
        summary["scenario_details"].append(scenario_detail)

        if scenario_passed:
            summary["passed_scenarios"] += 1
        else:
            summary["failed_scenarios"] += 1

    # Calculate aggregate statistics
    for metric_name, values in metric_values.items():
        summary["metric_summaries"][metric_name] = {
            "mean_mape": np.mean(values["mape"]),
            "max_mape": np.max(values["mape"]),
            "mean_rmse": np.mean(values["rmse"]),
            "mean_bias": np.mean(values["bias"]),
        }

    summary["overall_pass_rate"] = (
        summary["passed_scenarios"] / summary["total_scenarios"] * 100
        if summary["total_scenarios"] > 0 else 0
    )

    return summary


def verify_bakuzis_relationships(
    yield_data: Dict[str, List[float]],
    ages: List[int]
) -> Dict[str, bool]:
    """
    Verify that stand dynamics follow Bakuzis Matrix relationships.

    Expected relationships in even-aged stands:
    1. TPA vs Age: Negative (decreasing)
    2. QMD vs Age: Positive (increasing)
    3. BA vs Age: Positive then asymptotic
    4. Height vs Age: Positive (S-curve)
    5. TPA vs QMD: Negative

    Args:
        yield_data: Dictionary with yield table data
        ages: List of stand ages

    Returns:
        Dictionary of relationship verification results
    """
    results = {}
    ages = np.array(ages)

    # 1. TPA vs Age: should decrease
    if "TPA" in yield_data and len(yield_data["TPA"]) > 2:
        tpa = np.array(yield_data["TPA"])
        slope, _, r_value, _, _ = stats.linregress(ages, tpa)
        results["tpa_decreases_with_age"] = slope < 0

    # 2. QMD vs Age: should increase
    if "QMD" in yield_data and len(yield_data["QMD"]) > 2:
        qmd = np.array(yield_data["QMD"])
        slope, _, r_value, _, _ = stats.linregress(ages, qmd)
        results["qmd_increases_with_age"] = slope > 0

    # 3. BA vs Age: should generally increase (early growth)
    if "BA" in yield_data and len(yield_data["BA"]) > 2:
        ba = np.array(yield_data["BA"])
        # Check if BA increases in first half of simulation
        mid = len(ba) // 2
        results["ba_increases_early"] = ba[mid] > ba[0]

    # 4. Height vs Age: should increase
    if "TopHt" in yield_data and len(yield_data["TopHt"]) > 2:
        height = np.array(yield_data["TopHt"])
        slope, _, r_value, _, _ = stats.linregress(ages, height)
        results["height_increases_with_age"] = slope > 0

    # 5. TPA vs QMD: should be negatively correlated
    if "TPA" in yield_data and "QMD" in yield_data:
        tpa = np.array(yield_data["TPA"])
        qmd = np.array(yield_data["QMD"])
        corr, _ = stats.pearsonr(tpa, qmd)
        results["tpa_qmd_negative_correlation"] = corr < 0

    return results


if __name__ == "__main__":
    # Example usage and testing
    import random

    # Generate example data
    np.random.seed(42)
    observed = np.array([100, 150, 200, 250, 300])
    predicted = observed + np.random.normal(0, 5, len(observed))

    metrics = calculate_validation_metrics(observed, predicted, equivalence_threshold=10)
    print("Validation Metrics:")
    print(f"  Bias: {metrics.bias:.3f}")
    print(f"  RMSE: {metrics.rmse:.3f}")
    print(f"  MAPE: {metrics.mape:.2f}%")
    print(f"  R²: {metrics.r_squared:.4f}")
    print(f"  Equivalence passed: {metrics.equivalence_test_passed}")

    # Test acceptance criteria
    passed, message = check_acceptance_criteria(metrics, "basal_area")
    print(f"\nAcceptance: {message}")

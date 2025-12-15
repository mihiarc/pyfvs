"""Validation scripts for FVS-Python."""

from .compare_results import (
    ValidationMetrics,
    calculate_validation_metrics,
    check_acceptance_criteria,
    tost_equivalence_test,
    compare_yield_tables,
    generate_comparison_summary,
    verify_bakuzis_relationships,
)

from .generate_test_data import (
    TreeInitRecord,
    StandInitRecord,
    TestScenario,
    generate_planted_stand_trees,
    generate_test_scenario,
    generate_standard_test_scenarios,
    generate_component_test_cases,
    generate_single_tree_test_cases,
    save_test_data,
    load_test_scenario,
)

from .visualize import (
    plot_stand_comparison,
    plot_residuals,
    plot_bakuzis_matrix,
    plot_component_validation,
    plot_validation_summary,
    create_validation_report_figures,
)

__all__ = [
    # Compare results
    "ValidationMetrics",
    "calculate_validation_metrics",
    "check_acceptance_criteria",
    "tost_equivalence_test",
    "compare_yield_tables",
    "generate_comparison_summary",
    "verify_bakuzis_relationships",
    # Generate test data
    "TreeInitRecord",
    "StandInitRecord",
    "TestScenario",
    "generate_planted_stand_trees",
    "generate_test_scenario",
    "generate_standard_test_scenarios",
    "generate_component_test_cases",
    "generate_single_tree_test_cases",
    "save_test_data",
    "load_test_scenario",
    # Visualize
    "plot_stand_comparison",
    "plot_residuals",
    "plot_bakuzis_matrix",
    "plot_component_validation",
    "plot_validation_summary",
    "create_validation_report_figures",
]

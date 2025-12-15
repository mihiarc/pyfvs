"""
Test data generation for FVS-Python validation.

Generates consistent test data for both FVS-Python and official FVS comparison.
"""
import json
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@dataclass
class TreeInitRecord:
    """Individual tree record for FVS_TreeInit table."""
    Stand_ID: str
    Stand_Plot_ID: str
    Tree_ID: int
    Tree_Count: float = 1.0
    History: int = 0
    Species: str = "LP"
    DBH: float = 0.5
    DG: float = 0.0
    Ht: float = 1.0
    HtTopK: float = 0.0
    CrRatio: float = 0.9
    Damage1: int = 0
    Severity1: int = 0
    Damage2: int = 0
    Severity2: int = 0
    Damage3: int = 0
    Severity3: int = 0
    TreeValue: int = 0
    Prescription: int = 0


@dataclass
class StandInitRecord:
    """Stand initialization record for FVS_StandInit table."""
    Stand_ID: str
    Variant: str = "SN"
    Inv_Year: int = 2025
    Latitude: float = 33.5
    Longitude: float = -82.0
    Region: int = 8
    Forest: int = 0
    District: int = 0
    Site_Species: str = "LP"
    Site_Index: float = 70.0
    Aspect: float = 0.0
    Slope: float = 0.0
    Elevation: float = 500.0
    Basal_Area_Factor: float = 0.0
    Inv_Plot_Size: float = 0.0
    Brk_DBH: float = 0.0
    Num_Plots: int = 1
    Sam_Wt: float = 1.0
    DG_Trans: int = 0
    DG_Measure: int = 0
    HTG_Trans: int = 0
    HTG_Measure: int = 0
    Mort_Trans: int = 0
    Mort_Measure: int = 0
    Max_BA: float = 0.0
    Max_SDI: float = 0.0
    State: int = 0
    County: int = 0
    Fuel_Model: int = 0


@dataclass
class TestScenario:
    """Complete test scenario definition."""
    scenario_id: str
    species: str
    site_index: float
    trees_per_acre: int
    simulation_years: int = 50
    description: str = ""
    stand_init: Optional[StandInitRecord] = None
    tree_init: List[TreeInitRecord] = field(default_factory=list)


def generate_planted_stand_trees(
    stand_id: str,
    species: str,
    trees_per_acre: int,
    dbh_mean: float = 0.5,
    dbh_std: float = 0.1,
    initial_height: float = 1.0,
    initial_crown_ratio: float = 0.9,
    seed: int = 42
) -> List[TreeInitRecord]:
    """
    Generate tree records for a planted stand.

    Args:
        stand_id: Stand identifier
        species: Species code (LP, SP, SA, LL)
        trees_per_acre: Number of trees per acre
        dbh_mean: Mean initial DBH (inches)
        dbh_std: Standard deviation of DBH (inches)
        initial_height: Initial tree height (feet)
        initial_crown_ratio: Initial crown ratio (proportion)
        seed: Random seed for reproducibility

    Returns:
        List of TreeInitRecord objects
    """
    np.random.seed(seed)

    trees = []
    for i in range(trees_per_acre):
        dbh = max(0.1, np.random.normal(dbh_mean, dbh_std))
        trees.append(TreeInitRecord(
            Stand_ID=stand_id,
            Stand_Plot_ID=f"{stand_id}_1",
            Tree_ID=i + 1,
            Tree_Count=1.0,
            Species=species,
            DBH=round(dbh, 2),
            Ht=initial_height,
            CrRatio=initial_crown_ratio,
        ))

    return trees


def generate_test_scenario(
    scenario_id: str,
    species: str,
    site_index: float,
    trees_per_acre: int,
    simulation_years: int = 50,
    description: str = "",
    seed: int = 42
) -> TestScenario:
    """
    Generate a complete test scenario with stand and tree data.

    Args:
        scenario_id: Unique scenario identifier
        species: Species code (LP, SP, SA, LL)
        site_index: Site index (base age 25) in feet
        trees_per_acre: Number of trees per acre
        simulation_years: Total simulation period (years)
        description: Human-readable description
        seed: Random seed for reproducibility

    Returns:
        TestScenario object with all data
    """
    stand_init = StandInitRecord(
        Stand_ID=scenario_id,
        Site_Species=species,
        Site_Index=site_index,
    )

    tree_init = generate_planted_stand_trees(
        stand_id=scenario_id,
        species=species,
        trees_per_acre=trees_per_acre,
        seed=seed,
    )

    return TestScenario(
        scenario_id=scenario_id,
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        simulation_years=simulation_years,
        description=description or f"{species} plantation, SI={site_index}, TPA={trees_per_acre}",
        stand_init=stand_init,
        tree_init=tree_init,
    )


def generate_standard_test_scenarios() -> List[TestScenario]:
    """
    Generate the standard set of test scenarios from validation spec.

    Returns:
        List of TestScenario objects for all standard tests
    """
    scenarios = []

    # Loblolly Pine scenarios - varying site index
    for si in [60, 70, 80]:
        scenarios.append(generate_test_scenario(
            scenario_id=f"LP_SI{si}_T500",
            species="LP",
            site_index=float(si),
            trees_per_acre=500,
            description=f"Loblolly Pine, Site Index {si}, 500 TPA",
            seed=42 + si,
        ))

    # Loblolly Pine scenarios - varying density
    for tpa in [300, 500, 700]:
        scenarios.append(generate_test_scenario(
            scenario_id=f"LP_SI70_T{tpa}",
            species="LP",
            site_index=70.0,
            trees_per_acre=tpa,
            description=f"Loblolly Pine, Site Index 70, {tpa} TPA",
            seed=42 + tpa,
        ))

    # Other species
    species_configs = [
        ("SP", 65, 450, "Shortleaf Pine"),
        ("LL", 60, 400, "Longleaf Pine"),
        ("SA", 70, 550, "Slash Pine"),
    ]

    for code, si, tpa, name in species_configs:
        scenarios.append(generate_test_scenario(
            scenario_id=f"{code}_SI{si}_T{tpa}",
            species=code,
            site_index=float(si),
            trees_per_acre=tpa,
            description=f"{name}, Site Index {si}, {tpa} TPA",
            seed=42,
        ))

    return scenarios


def generate_component_test_cases() -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate test cases for component model validation.

    Returns:
        Dictionary of test cases by component type
    """
    species_list = ["LP", "SP", "SA", "LL"]

    # Height-diameter test cases
    height_diameter_cases = []
    for species in species_list:
        for dbh in [1.0, 3.0, 5.0, 8.0, 10.0, 12.0, 15.0, 20.0]:
            height_diameter_cases.append({
                "species": species,
                "dbh": dbh,
                "tolerance_feet": 1.0,
            })

    # Bark ratio test cases
    bark_ratio_cases = []
    for species in species_list:
        for dob in [2.0, 5.0, 8.0, 10.0, 15.0, 20.0]:
            bark_ratio_cases.append({
                "species": species,
                "dob": dob,
                "tolerance": 0.02,
            })

    # Crown ratio test cases
    crown_ratio_cases = []
    for species in species_list:
        for relsdi in [2.0, 4.0, 6.0, 8.0, 10.0]:
            crown_ratio_cases.append({
                "species": species,
                "relsdi": relsdi,
                "tolerance": 0.05,
            })

    # Crown width test cases
    crown_width_cases = []
    for species in species_list:
        for dbh in [3.0, 5.0, 8.0, 10.0, 15.0]:
            crown_width_cases.append({
                "species": species,
                "dbh": dbh,
                "crown_ratio_pct": 50.0,
                "tolerance_feet": 1.0,
            })

    # CCF test cases
    ccf_cases = []
    for species in species_list:
        for tpa in [200, 400, 600]:
            ccf_cases.append({
                "species": species,
                "trees_per_acre": tpa,
                "mean_dbh": 8.0,
                "tolerance": 5.0,
            })

    return {
        "height_diameter": height_diameter_cases,
        "bark_ratio": bark_ratio_cases,
        "crown_ratio": crown_ratio_cases,
        "crown_width": crown_width_cases,
        "ccf": ccf_cases,
    }


def generate_single_tree_test_cases() -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate test cases for single-tree growth validation.

    Returns:
        Dictionary of test cases by growth model type
    """
    species_list = ["LP", "SP", "SA", "LL"]

    # Small tree height growth test cases
    small_tree_cases = []
    for species in species_list:
        for age in [5, 10, 15]:
            for si in [60, 70, 80]:
                small_tree_cases.append({
                    "species": species,
                    "site_index": si,
                    "current_age": age,
                    "initial_dbh": 0.5,
                    "initial_height": 5.0 + age * 1.5,
                    "tolerance_feet": 1.0,
                })

    # Large tree diameter growth test cases
    large_tree_cases = []
    for species in species_list:
        for dbh in [5.0, 8.0, 10.0, 15.0]:
            for si in [60, 70, 80]:
                for ba in [80, 120, 160]:
                    large_tree_cases.append({
                        "species": species,
                        "dbh": dbh,
                        "crown_ratio": 0.5,
                        "site_index": si,
                        "basal_area": ba,
                        "pbal": ba * 0.5,
                        "tolerance_inches": 0.2,
                    })

    # Transition zone test cases (1-3" DBH)
    transition_cases = []
    for species in species_list:
        for dbh in [1.5, 2.0, 2.5]:
            transition_cases.append({
                "species": species,
                "dbh": dbh,
                "site_index": 70,
                "basal_area": 100,
                "tolerance_inches": 0.15,
            })

    return {
        "small_tree_growth": small_tree_cases,
        "large_tree_growth": large_tree_cases,
        "transition_zone": transition_cases,
    }


def save_test_data(output_dir: Path) -> None:
    """
    Save all test data to files.

    Args:
        output_dir: Directory to save test data
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate and save standard scenarios
    scenarios = generate_standard_test_scenarios()

    scenarios_data = []
    for scenario in scenarios:
        scenario_dict = {
            "scenario_id": scenario.scenario_id,
            "species": scenario.species,
            "site_index": scenario.site_index,
            "trees_per_acre": scenario.trees_per_acre,
            "simulation_years": scenario.simulation_years,
            "description": scenario.description,
        }
        scenarios_data.append(scenario_dict)

        # Create scenario directory and save tree data
        scenario_dir = output_dir / scenario.scenario_id
        scenario_dir.mkdir(exist_ok=True)

        tree_data = [asdict(t) for t in scenario.tree_init]
        with open(scenario_dir / "tree_init.json", "w") as f:
            json.dump(tree_data, f, indent=2)

        stand_data = asdict(scenario.stand_init)
        with open(scenario_dir / "stand_init.json", "w") as f:
            json.dump(stand_data, f, indent=2)

    # Save scenario manifest
    with open(output_dir / "scenarios.json", "w") as f:
        json.dump(scenarios_data, f, indent=2)

    # Save component test cases
    component_cases = generate_component_test_cases()
    with open(output_dir / "component_tests.json", "w") as f:
        json.dump(component_cases, f, indent=2)

    # Save single-tree test cases
    tree_cases = generate_single_tree_test_cases()
    with open(output_dir / "single_tree_tests.json", "w") as f:
        json.dump(tree_cases, f, indent=2)

    print(f"Test data saved to {output_dir}")
    print(f"  - {len(scenarios)} stand scenarios")
    print(f"  - {sum(len(v) for v in component_cases.values())} component test cases")
    print(f"  - {sum(len(v) for v in tree_cases.values())} single-tree test cases")


def load_test_scenario(scenario_dir: Path) -> TestScenario:
    """
    Load a test scenario from disk.

    Args:
        scenario_dir: Directory containing scenario data

    Returns:
        TestScenario object
    """
    with open(scenario_dir / "stand_init.json") as f:
        stand_data = json.load(f)

    with open(scenario_dir / "tree_init.json") as f:
        tree_data = json.load(f)

    stand_init = StandInitRecord(**stand_data)
    tree_init = [TreeInitRecord(**t) for t in tree_data]

    scenario_id = scenario_dir.name
    parts = scenario_id.split("_")
    species = parts[0]
    site_index = float(parts[1].replace("SI", ""))
    trees_per_acre = int(parts[2].replace("T", ""))

    return TestScenario(
        scenario_id=scenario_id,
        species=species,
        site_index=site_index,
        trees_per_acre=trees_per_acre,
        stand_init=stand_init,
        tree_init=tree_init,
    )


if __name__ == "__main__":
    # Generate test data when run directly
    validation_dir = Path(__file__).parent.parent
    test_data_dir = validation_dir / "reference_data"
    save_test_data(test_data_dir)

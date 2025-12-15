# FVS-Python Validation Specification

## Document Overview

**Purpose:** Define the validation strategy for FVS-Python against the official USDA Forest Service FVS Southern (SN) variant to establish credibility for public release.

**Scope:** Validation of growth predictions for four southern yellow pine species (Loblolly, Shortleaf, Longleaf, Slash) in planted stand conditions.

**Framework:** Based on USFS FVS Model Validation Protocols (2009, revised 2010).

---

## 1. Validation Philosophy

### 1.1 Key Distinction

FVS-Python is a **pure Python reimplementation** of the FVS-SN growth equations, not a wrapper around the Fortran code. This means:

- We are validating that our implementation of the published equations produces equivalent results
- Minor numerical differences are expected due to floating-point precision and solver implementations
- The goal is **functional equivalence**, not bit-for-bit identical outputs

### 1.2 Acceptance Criteria

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Diameter growth (5-yr) | ±5% or ±0.1 inches | Primary driver of FVS predictions |
| Height growth (5-yr) | ±5% or ±0.5 feet | Secondary, derived from diameter |
| Basal area (stand) | ±3% | Cumulative metric, tighter tolerance |
| Trees per acre | ±2% | Integer counts, should match closely |
| Volume | ±10% | Compounds diameter/height errors |

---

## 2. Reference System Setup

### 2.1 Official FVS Installation

**Source:** USDA Forest Service FVS Complete Package  
**URL:** https://www.fs.usda.gov/fvs/software/complete.php

```
Installation Steps:
1. Download FVS Software Complete Package (Windows)
2. Install to default location (C:\FVSbin)
3. Verify FVSsn.exe is present (Southern variant executable)
4. Note version/revision date from executable header
```

**Version Tracking:**
- Record FVS revision date (found in output file header)
- Store in `validation/fvs_version.txt`
- Re-validate when FVS updates

### 2.2 Alternative: Command-Line FVS

For automated testing, use the FVS executable directly:

```bash
# Windows
FVSsn.exe --keywordfile=test_case.key

# Linux (build from source)
# See: https://sourceforge.net/p/open-fvs/wiki/BuildProcess_UnixAlike/
./FVSsn --keywordfile=test_case.key
```

### 2.3 Required FVS Keywords

Create keyword files (.key) that match FVS-Python test scenarios:

```
STDIDENT
TEST_LP_SI70_TPA500
STANDS      DATABASE
FVS_StandInit

INVYEAR      2024
NUMCYCLE        10

SITECODE       811
STDINFO        811        1       70

TREEFMT
(I4,T1,I7,F6,I1,A3,F4.1,F3.1,2F3.0,F4.1,I1)

TREEDATA         DATABASE
FVS_TreeInit

PROCESS
STOP
```

---

## 3. Validation Test Suite

### 3.1 Level 1: Component Model Validation

Validate individual equations before full simulation.

#### 3.1.1 Height-Diameter Relationship

**Test:** Given DBH, predict height using Curtis-Arney equation.

```python
# Test cases for each species
test_cases_height_diameter = [
    # (species, dbh_inches, expected_height_feet, tolerance_feet)
    ("LP", 1.0, expected_from_fvs, 0.5),
    ("LP", 3.0, expected_from_fvs, 0.5),
    ("LP", 6.0, expected_from_fvs, 0.5),
    ("LP", 10.0, expected_from_fvs, 0.5),
    ("LP", 15.0, expected_from_fvs, 0.5),
    # ... repeat for SP, LL, SA
]
```

**FVS Reference:** Extract height-diameter predictions from FVS TreeList output.

#### 3.1.2 Bark Ratio

**Test:** Given DOB, predict DIB.

```python
test_cases_bark_ratio = [
    # (species, dob_inches, expected_dib_inches, tolerance)
    ("LP", 5.0, expected_from_fvs, 0.05),
    ("LP", 10.0, expected_from_fvs, 0.05),
    # ...
]
```

**Validation Method:** 
- FVS outputs DIB in certain reports
- Alternatively, back-calculate from volume equations

#### 3.1.3 Crown Ratio

**Test:** Predict initial crown ratio for regenerating trees.

```python
test_cases_crown_ratio = [
    # (ccf, expected_cr, tolerance)
    (50, expected_from_fvs, 0.05),
    (100, expected_from_fvs, 0.05),
    (200, expected_from_fvs, 0.05),
]
```

#### 3.1.4 Crown Width

**Test:** Predict crown width from DBH and crown ratio.

```python
test_cases_crown_width = [
    # (species, dbh, cr, hopkins_index, expected_cw_feet, tolerance)
    ("LP", 5.0, 0.5, 0.0, expected_from_fvs, 0.5),
    ("SA", 8.0, 0.6, 0.0, expected_from_fvs, 0.5),
    # ...
]
```

#### 3.1.5 Crown Competition Factor (CCF)

**Test:** Calculate stand CCF from tree list.

```python
test_cases_ccf = [
    # Provide identical tree lists to FVS and FVS-Python
    # Compare stand CCF output
    (tree_list_1, expected_ccf_from_fvs, 1.0),  # tolerance in CCF units
]
```

### 3.2 Level 2: Single-Tree Growth Validation

#### 3.2.1 Small Tree Height Growth

**Test:** Predict 5-year height growth for trees < 3" DBH.

```python
test_cases_small_tree = [
    # (species, site_index, current_age, current_height, expected_5yr_growth, tolerance)
    ("LP", 70, 5, 8.0, expected_from_fvs, 0.5),
    ("LP", 70, 10, 20.0, expected_from_fvs, 0.5),
    # ...
]
```

#### 3.2.2 Large Tree Diameter Growth (ln_dds)

**Test:** Predict 5-year diameter growth for trees >= 3" DBH.

```python
test_cases_large_tree = [
    # (species, dbh, cr, site_index, ba, bal, expected_dds, tolerance)
    ("LP", 5.0, 0.5, 70, 80, 40, expected_from_fvs, 0.1),
    ("LP", 10.0, 0.4, 70, 120, 60, expected_from_fvs, 0.1),
    # ...
]
```

**Critical Variables:**
- DBH (diameter at breast height)
- CR (crown ratio)
- SI (site index)
- BA (basal area per acre)
- BAL (basal area in larger trees)
- Relative height
- Slope, aspect (set to 0 for baseline tests)

#### 3.2.3 Transition Zone (1-3" DBH)

**Test:** Verify weighted blending between small and large tree models.

```python
test_cases_transition = [
    # (species, dbh, ..., expected_growth, tolerance)
    ("LP", 1.5, ..., expected_from_fvs, 0.2),  # Weight toward small tree
    ("LP", 2.0, ..., expected_from_fvs, 0.2),  # 50/50 blend
    ("LP", 2.5, ..., expected_from_fvs, 0.2),  # Weight toward large tree
]
```

### 3.3 Level 3: Stand-Level Validation

#### 3.3.1 Bare Ground Planting Verification

**Purpose:** Verify basic stand dynamics (from USFS Validation Protocols).

**Test Scenarios:**

| Scenario | Species | Site Index | Initial TPA | Simulation Years |
|----------|---------|------------|-------------|------------------|
| LP_SI60_T500 | LP | 60 | 500 | 50 |
| LP_SI70_T500 | LP | 70 | 500 | 50 |
| LP_SI80_T500 | LP | 80 | 500 | 50 |
| LP_SI70_T300 | LP | 70 | 300 | 50 |
| LP_SI70_T700 | LP | 70 | 700 | 50 |
| SP_SI65_T450 | SP | 65 | 450 | 50 |
| LL_SI60_T400 | LL | 60 | 400 | 50 |
| SA_SI70_T550 | SA | 70 | 550 | 50 |

**Required Behaviors (Verification):**
- [ ] TPA decreases over time (mortality)
- [ ] Mean DBH increases over time
- [ ] Mean height increases over time
- [ ] Basal area increases then stabilizes
- [ ] Dominant height tracks site index curves

**Quantitative Validation:**
Compare FVS-Python vs FVS-SN outputs at ages 10, 20, 30, 40, 50:

| Metric | Age 10 | Age 20 | Age 30 | Age 40 | Age 50 |
|--------|--------|--------|--------|--------|--------|
| TPA | ±2% | ±2% | ±3% | ±3% | ±5% |
| QMD | ±5% | ±5% | ±5% | ±5% | ±5% |
| Dominant Ht | ±5% | ±5% | ±5% | ±5% | ±5% |
| BA/acre | ±3% | ±3% | ±5% | ±5% | ±5% |

#### 3.3.2 Bakuzis Matrix Verification

The Bakuzis Matrix describes expected relationships in even-aged stands:

```
Verify these relationships hold in FVS-Python output:

1. TPA vs Age: Negative (decreasing)
2. QMD vs Age: Positive (increasing)  
3. BA vs Age: Positive then asymptotic
4. Height vs Age: Positive (S-curve)
5. TPA vs QMD: Negative
6. BA vs TPA: Complex (initial positive, then negative)
```

### 3.4 Level 4: Sensitivity Analysis

#### 3.4.1 Parameter Sensitivity

Identify which input variables most affect outputs.

**Method:** Latin Hypercube Sampling across parameter space.

```python
sensitivity_parameters = {
    "site_index": (50, 90),      # Range to test
    "initial_tpa": (200, 800),
    "dbh_variation": (0.0, 0.3),  # CV of initial DBH
}

# Response variable: 10-year basal area increment
```

**Expected Result:** Document sensitivity rankings for FVS-Python, compare to published FVS-SN sensitivity analyses.

#### 3.4.2 Edge Case Testing

```python
edge_cases = [
    # Extreme site indices
    {"site_index": 40, "expected": "low_growth"},
    {"site_index": 100, "expected": "high_growth"},
    
    # High/low density
    {"tpa": 100, "expected": "minimal_mortality"},
    {"tpa": 1000, "expected": "high_mortality"},
    
    # Species limits
    {"dbh": 0.1, "expected": "handles_small_trees"},
    {"dbh": 30.0, "expected": "handles_large_trees"},
]
```

---

## 4. Test Data Generation

### 4.1 FVS Input Database Schema

Create SQLite databases for FVS input:

```sql
-- FVS_StandInit table
CREATE TABLE FVS_StandInit (
    Stand_ID TEXT PRIMARY KEY,
    Variant TEXT DEFAULT 'SN',
    Inv_Year INTEGER,
    Latitude REAL,
    Longitude REAL,
    Region INTEGER,
    Forest INTEGER,
    District INTEGER,
    Site_Species TEXT,
    Site_Index REAL,
    Aspect REAL DEFAULT 0,
    Slope REAL DEFAULT 0,
    Elevation REAL DEFAULT 500
);

-- FVS_TreeInit table  
CREATE TABLE FVS_TreeInit (
    Stand_ID TEXT,
    Stand_Plot_ID TEXT,
    Tree_ID INTEGER,
    Tree_Count REAL,
    History INTEGER DEFAULT 0,
    Species TEXT,
    DBH REAL,
    DG REAL,
    Ht REAL,
    HtTopK REAL,
    CrRatio REAL,
    Damage1 INTEGER,
    Severity1 INTEGER,
    Damage2 INTEGER,
    Severity2 INTEGER,
    Damage3 INTEGER,
    Severity3 INTEGER,
    TreeValue INTEGER,
    Prescription INTEGER
);
```

### 4.2 Test Data Generator

```python
# validation/generate_test_data.py

def generate_planted_stand_input(
    stand_id: str,
    species: str,
    site_index: float,
    trees_per_acre: int,
    dbh_mean: float = 0.5,
    dbh_std: float = 0.1,
    seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate matching input data for both FVS and FVS-Python.
    
    Returns:
        stand_init: DataFrame for FVS_StandInit
        tree_init: DataFrame for FVS_TreeInit
    """
    np.random.seed(seed)
    
    # Generate tree list
    trees = []
    for i in range(trees_per_acre):
        dbh = max(0.1, np.random.normal(dbh_mean, dbh_std))
        trees.append({
            "Stand_ID": stand_id,
            "Stand_Plot_ID": f"{stand_id}_1",
            "Tree_ID": i + 1,
            "Tree_Count": 1.0,  # Expansion factor
            "Species": species,
            "DBH": round(dbh, 2),
            "Ht": 1.0,  # Initial height
            "CrRatio": 0.9,
        })
    
    tree_init = pd.DataFrame(trees)
    
    stand_init = pd.DataFrame([{
        "Stand_ID": stand_id,
        "Variant": "SN",
        "Inv_Year": 2024,
        "Site_Species": species,
        "Site_Index": site_index,
    }])
    
    return stand_init, tree_init
```

### 4.3 FVS Output Parsing

```python
# validation/parse_fvs_output.py

def parse_fvs_summary(output_file: str) -> pd.DataFrame:
    """
    Parse FVS summary table from .out or .sum file.
    
    Returns DataFrame with columns:
        Year, Age, TPA, BA, SDI, CCF, TopHt, QMD, 
        MCuFt, TCuFt, MBdFt, Accret, Mort, ...
    """
    # FVS summary table has fixed-width format
    # Parse starting from "SUMMARY STATISTICS" line
    pass

def parse_fvs_treelist(treelist_file: str) -> pd.DataFrame:
    """
    Parse FVS detailed tree list output.
    
    Returns DataFrame with individual tree attributes.
    """
    pass

def parse_fvs_compute_variables(output_file: str) -> Dict:
    """
    Parse COMPUTE variable output for detailed validation.
    """
    pass
```

---

## 5. Validation Infrastructure

### 5.1 Directory Structure

```
fvs-python/
├── validation/
│   ├── README.md                    # Validation overview
│   ├── fvs_version.txt              # Reference FVS version info
│   │
│   ├── reference_data/              # FVS-generated reference outputs
│   │   ├── LP_SI70_T500/
│   │   │   ├── input.db             # SQLite input database
│   │   │   ├── keywords.key         # FVS keyword file
│   │   │   ├── output.out           # FVS main output
│   │   │   ├── summary.csv          # Parsed summary table
│   │   │   └── treelist.csv         # Parsed tree lists
│   │   ├── SP_SI65_T450/
│   │   └── ...
│   │
│   ├── test_cases/                  # Test case definitions
│   │   ├── component_tests.yaml     # Height-diameter, bark ratio, etc.
│   │   ├── single_tree_tests.yaml   # Individual tree growth
│   │   └── stand_tests.yaml         # Full stand simulations
│   │
│   ├── scripts/
│   │   ├── generate_test_data.py    # Create test inputs
│   │   ├── run_fvs_reference.py     # Execute FVS for reference
│   │   ├── parse_fvs_output.py      # Parse FVS outputs
│   │   └── compare_results.py       # Statistical comparison
│   │
│   ├── results/                     # Validation run outputs
│   │   ├── comparison_report.html   # Summary report
│   │   ├── figures/                 # Comparison plots
│   │   └── metrics.json             # Pass/fail metrics
│   │
│   └── notebooks/
│       ├── validation_analysis.ipynb
│       └── sensitivity_analysis.ipynb
```

### 5.2 Validation Test Runner

```python
# validation/run_validation.py

import pytest
from pathlib import Path

class ValidationSuite:
    """Run complete validation against FVS reference."""
    
    def __init__(self, reference_dir: Path):
        self.reference_dir = reference_dir
        self.results = []
    
    def run_all(self):
        """Execute full validation suite."""
        self.validate_component_models()
        self.validate_single_tree_growth()
        self.validate_stand_simulations()
        self.generate_report()
    
    def validate_component_models(self):
        """Level 1: Individual equation validation."""
        # Height-diameter
        # Bark ratio
        # Crown ratio
        # Crown width
        # CCF
        pass
    
    def validate_single_tree_growth(self):
        """Level 2: Tree-level growth validation."""
        # Small tree height growth
        # Large tree diameter growth
        # Transition zone blending
        pass
    
    def validate_stand_simulations(self):
        """Level 3: Full stand validation."""
        for scenario_dir in self.reference_dir.iterdir():
            if scenario_dir.is_dir():
                self.compare_scenario(scenario_dir)
    
    def compare_scenario(self, scenario_dir: Path):
        """Compare single scenario results."""
        # Load FVS reference
        fvs_summary = pd.read_csv(scenario_dir / "summary.csv")
        
        # Run FVS-Python with same inputs
        # ... 
        
        # Calculate metrics
        metrics = self.calculate_metrics(fvs_summary, fvspy_summary)
        self.results.append(metrics)
    
    def calculate_metrics(self, reference, predicted) -> Dict:
        """Calculate bias, RMSE, and equivalence statistics."""
        metrics = {}
        
        for col in ["TPA", "BA", "QMD", "TopHt"]:
            diff = predicted[col] - reference[col]
            metrics[f"{col}_bias"] = diff.mean()
            metrics[f"{col}_rmse"] = np.sqrt((diff**2).mean())
            metrics[f"{col}_mape"] = (abs(diff) / reference[col]).mean() * 100
        
        return metrics
    
    def generate_report(self):
        """Generate HTML validation report."""
        pass
```

### 5.3 pytest Integration

```python
# tests/test_validation.py

import pytest
from validation.run_validation import ValidationSuite

@pytest.fixture
def validation_suite():
    return ValidationSuite(Path("validation/reference_data"))

class TestComponentModels:
    """Level 1: Component model validation."""
    
    @pytest.mark.parametrize("species,dbh,expected_ht,tol", [
        ("LP", 5.0, 45.2, 0.5),
        ("LP", 10.0, 62.8, 0.5),
        # Load from YAML...
    ])
    def test_height_diameter(self, species, dbh, expected_ht, tol):
        from fvs_python import create_height_diameter_model
        model = create_height_diameter_model(species)
        predicted = model.predict_height(dbh)
        assert abs(predicted - expected_ht) < tol

class TestStandSimulation:
    """Level 3: Stand-level validation."""
    
    @pytest.mark.parametrize("scenario", [
        "LP_SI60_T500",
        "LP_SI70_T500",
        "LP_SI80_T500",
    ])
    def test_stand_metrics_within_tolerance(self, validation_suite, scenario):
        results = validation_suite.compare_scenario(scenario)
        
        assert results["TPA_mape"] < 5.0, f"TPA error {results['TPA_mape']:.1f}% exceeds 5%"
        assert results["BA_mape"] < 5.0, f"BA error {results['BA_mape']:.1f}% exceeds 5%"
        assert results["QMD_mape"] < 5.0, f"QMD error {results['QMD_mape']:.1f}% exceeds 5%"
```

---

## 6. Reporting and Documentation

### 6.1 Validation Report Structure

```markdown
# FVS-Python Validation Report

## Executive Summary
- Validation date: YYYY-MM-DD
- FVS-Python version: X.Y.Z
- Reference FVS version: SN revision YYYY-MM-DD
- Overall status: PASS/FAIL

## Component Model Results
| Model | Test Cases | Passed | Failed | Max Error |
|-------|------------|--------|--------|-----------|
| Height-Diameter | 20 | 20 | 0 | 0.3 ft |
| Bark Ratio | 16 | 16 | 0 | 0.02 in |
| Crown Ratio | 12 | 12 | 0 | 0.03 |
| Crown Width | 16 | 15 | 1 | 0.8 ft |
| CCF | 8 | 8 | 0 | 0.5 |

## Stand Simulation Results
| Scenario | TPA Error | BA Error | QMD Error | Status |
|----------|-----------|----------|-----------|--------|
| LP_SI70_T500 | 1.2% | 2.3% | 1.8% | PASS |
| ... | | | | |

## Figures
- Figure 1: Stand development trajectories (FVS vs FVS-Python)
- Figure 2: Residual plots by age
- Figure 3: Sensitivity analysis results

## Known Differences
- [Document any systematic differences and explain]

## Conclusions
```

### 6.2 Visualization Functions

```python
# validation/visualize.py

def plot_stand_comparison(fvs_data: pd.DataFrame, 
                          fvspy_data: pd.DataFrame,
                          scenario_name: str) -> plt.Figure:
    """
    Create 2x2 panel comparing key metrics over time.
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    metrics = [("TPA", "Trees per Acre"),
               ("BA", "Basal Area (ft²/acre)"),
               ("QMD", "Quadratic Mean Diameter (in)"),
               ("TopHt", "Dominant Height (ft)")]
    
    for ax, (col, label) in zip(axes.flat, metrics):
        ax.plot(fvs_data["Age"], fvs_data[col], 'b-', label="FVS-SN", linewidth=2)
        ax.plot(fvspy_data["Age"], fvspy_data[col], 'r--', label="FVS-Python", linewidth=2)
        ax.set_xlabel("Stand Age (years)")
        ax.set_ylabel(label)
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    fig.suptitle(f"Stand Development Comparison: {scenario_name}")
    plt.tight_layout()
    return fig

def plot_residuals(fvs_data: pd.DataFrame,
                   fvspy_data: pd.DataFrame) -> plt.Figure:
    """
    Plot residuals (FVS-Python - FVS) vs age and predicted values.
    """
    pass

def plot_bakuzis_matrix(simulation_data: pd.DataFrame) -> plt.Figure:
    """
    Visualize Bakuzis Matrix relationships.
    """
    pass
```

---

## 7. Continuous Integration

### 7.1 GitHub Actions Workflow

```yaml
# .github/workflows/validation.yml

name: FVS Validation

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 1 * *'  # Monthly validation run

jobs:
  validate:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e .[dev]
          pip install pytest pytest-cov
      
      - name: Run validation tests
        run: |
          pytest tests/test_validation.py -v --tb=short
      
      - name: Generate validation report
        run: |
          python validation/scripts/generate_report.py
      
      - name: Upload validation artifacts
        uses: actions/upload-artifact@v4
        with:
          name: validation-report
          path: validation/results/
```

### 7.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml

repos:
  - repo: local
    hooks:
      - id: validate-equations
        name: Validate equation implementations
        entry: python -m pytest tests/test_validation.py::TestComponentModels -x
        language: system
        pass_filenames: false
        stages: [commit]
```

---

## 8. Implementation Roadmap

### Phase 1: Infrastructure (Week 1)
- [ ] Set up validation directory structure
- [ ] Install reference FVS and document version
- [ ] Create test data generation scripts
- [ ] Implement FVS output parsers

### Phase 2: Component Validation (Week 2)
- [ ] Height-diameter validation
- [ ] Bark ratio validation
- [ ] Crown ratio validation
- [ ] Crown width validation
- [ ] CCF validation

### Phase 3: Growth Model Validation (Week 3)
- [ ] Small tree height growth validation
- [ ] Large tree diameter growth (ln_dds) validation
- [ ] Transition zone validation
- [ ] Mortality model validation (if implemented)

### Phase 4: Stand Simulation Validation (Week 4)
- [ ] Generate reference FVS runs for all test scenarios
- [ ] Run FVS-Python simulations
- [ ] Calculate comparison metrics
- [ ] Verify Bakuzis Matrix relationships

### Phase 5: Documentation (Week 5)
- [ ] Generate validation report
- [ ] Create comparison visualizations
- [ ] Document known differences
- [ ] Write validation methodology section for README

### Phase 6: CI Integration (Week 6)
- [ ] Set up GitHub Actions workflow
- [ ] Configure automated validation on PR
- [ ] Add validation badge to README

---

## 9. References

1. **FVS Validation Protocols.** USFS Forest Management Service Center. 2009 (revised 2010). https://www.fs.usda.gov/fmsc/ftp/fvs/docs/steering/FVS_Model_Validation_Protocols.pdf

2. **Southern (SN) Variant Overview.** FVS Staff. 2008 (revised 2025). https://www.fs.usda.gov/sites/default/files/forest-management/fvs-sn-overview.pdf

3. **Sensitivity Analysis of FVS-SN.** Virginia Tech. 2007. https://vtechworks.lib.vt.edu/items/0ff45c62-b83c-4717-8635-344f9e3ea78f

4. **Inventory-based Sensitivity Analysis of Large Tree Diameter Growth.** Vacchiano et al. 2008. RMRS-P-54.

5. **Robinson & Froese.** 2004. Model validation using equivalence tests. Ecological Modelling 176:349-358.

---

## Appendix A: FVS Keyword File Templates

### A.1 Basic Planted Stand Simulation

```
STDIDENT
{{stand_id}}                 {{description}}

STDINFO          {{location}}        1       {{site_index}}

INVYEAR          {{year}}
NUMCYCLE            10
TIMEINT             0         5

TREEFMT
(I4,T1,I7,F6,I1,A3,F4.1,F3.1,2F3.0,F4.1,I1)

DATABASE
DSNIN
{{input_database}}
STANDSQL
SELECT * FROM FVS_StandInit WHERE Stand_ID = '{{stand_id}}'
TREESQL
SELECT * FROM FVS_TreeInit WHERE Stand_ID = '{{stand_id}}'
ENDDATABASE

ECESSION          ON
COMPUTE            0
BESSION = SUM(1,0,0,BESSION+BA)
END

PROCESS
STOP
```

### A.2 Keyword File for Detailed Tree Output

```
STDIDENT
{{stand_id}}                 Detailed output

TREELIST           0         0         0         0         1
CUTLIST            0         0         0         0         1

DATABASE
DSNOUT
{{output_database}}
SUMMARY            2
TREELIST           2
CARBRPTS           2
ENDDATABASE

PROCESS
STOP
```

---

## Appendix B: Statistical Methods

### B.1 Equivalence Testing

Traditional hypothesis testing asks: "Are these different?"
Equivalence testing asks: "Are these similar enough?"

```python
def equivalence_test(observed, predicted, threshold):
    """
    Two One-Sided Tests (TOST) procedure for equivalence.
    
    H0: |mean(observed) - mean(predicted)| >= threshold
    H1: |mean(observed) - mean(predicted)| < threshold
    
    Returns True if equivalence is established at alpha=0.05.
    """
    from scipy import stats
    
    diff = observed - predicted
    mean_diff = diff.mean()
    se_diff = diff.std() / np.sqrt(len(diff))
    
    # Upper bound test
    t_upper = (mean_diff - threshold) / se_diff
    p_upper = stats.t.cdf(t_upper, len(diff) - 1)
    
    # Lower bound test
    t_lower = (mean_diff + threshold) / se_diff
    p_lower = 1 - stats.t.cdf(t_lower, len(diff) - 1)
    
    # Both must be significant
    return max(p_upper, p_lower) < 0.05
```

### B.2 Metrics Formulas

```python
def calculate_validation_metrics(observed: np.ndarray, 
                                  predicted: np.ndarray) -> Dict:
    """Calculate standard validation metrics."""
    diff = predicted - observed
    
    return {
        "n": len(observed),
        "bias": diff.mean(),
        "mae": np.abs(diff).mean(),
        "rmse": np.sqrt((diff**2).mean()),
        "mape": (np.abs(diff) / observed).mean() * 100,
        "r_squared": 1 - (diff**2).sum() / ((observed - observed.mean())**2).sum(),
    }
```

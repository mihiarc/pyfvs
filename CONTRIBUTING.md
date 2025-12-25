# Contributing to PyFVS

Thank you for your interest in contributing to PyFVS! This document provides guidelines for contributing to the project.

## Getting Started

### Development Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mihiarc/pyfvs.git
   cd pyfvs
   ```

2. **Create a virtual environment with uv (recommended)**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in development mode with all dependencies**
   ```bash
   uv pip install -e ".[dev,test,docs]"
   ```

4. **Verify the setup**
   ```bash
   uv run pytest -v --tb=short
   ```

### Project Structure

```
pyfvs/
├── src/fvs_python/     # Main source code
│   ├── tree.py         # Individual tree growth models
│   ├── stand.py        # Stand-level management
│   ├── cli.py          # Command-line interface
│   └── ...
├── cfg/                # Configuration files
│   ├── species/        # Species-specific parameters
│   └── *.json          # Model coefficients
├── tests/              # Test suite
├── docs/               # Documentation
└── test_output/        # Generated test outputs
```

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**, following the [code style guidelines](#code-style)

3. **Run tests**
   ```bash
   uv run pytest
   ```

4. **Format your code**
   ```bash
   uv run black src/fvs_python tests
   ```

5. **Run linters**
   ```bash
   uv run flake8 src/fvs_python tests
   uv run mypy src/fvs_python
   ```

6. **Commit your changes**
   ```bash
   git add .
   git commit -m "Brief description of changes"
   ```

7. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Running Tests

```bash
# Run all tests with coverage
uv run pytest

# Run specific test file
uv run pytest tests/test_tree.py

# Run with verbose output
uv run pytest -v --tb=short

# Run only unit tests
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Skip slow tests
uv run pytest -m "not slow"
```

### Test Output

Tests generate outputs in `test_output/` for manual verification. These include:
- Growth trajectory plots
- Validation reports (markdown)
- Yield table CSVs

## Code Style

### Python Style

- **Formatter**: Black (line length 88)
- **Linter**: Flake8
- **Type Checker**: MyPy with strict settings
- **Import Sorting**: isort (black profile)

### Naming Conventions

```python
# Variables and functions: snake_case
def calculate_basal_area(trees: list) -> float:
    total_ba = 0.0
    ...

# Classes: PascalCase
class StandMetricsCalculator:
    ...

# Constants: UPPER_SNAKE_CASE
MAX_CROWN_RATIO = 0.95
MIN_DBH_THRESHOLD = 0.1
```

### Docstrings

Use Google-style docstrings for all public functions and classes:

```python
def grow(self, site_index: float, basal_area: float, time_step: int = 5) -> None:
    """Grow the tree for the specified time period.

    Applies the appropriate growth model (small-tree or large-tree)
    based on the tree's current DBH.

    Args:
        site_index: Site index (base age 25) in feet.
        basal_area: Stand basal area in square feet per acre.
        time_step: Growth period in years. Defaults to 5.

    Raises:
        ValueError: If site_index is not between 30 and 100.

    Example:
        >>> tree = Tree(species='LP', dbh=6.0, height=45.0)
        >>> tree.grow(site_index=70, basal_area=120)
        >>> print(f"New DBH: {tree.dbh:.1f}")
        New DBH: 6.8
    """
```

### Type Hints

Use type hints for all function signatures:

```python
from typing import Optional, List, Dict

def calculate_metrics(
    trees: List[Tree],
    site_index: float,
    ecounit: Optional[str] = None
) -> Dict[str, float]:
    ...
```

## Testing Guidelines

### Test Structure

```python
import pytest
from fvs_python import Stand, Tree

class TestTree:
    """Tests for the Tree class."""

    def test_small_tree_growth(self):
        """Small trees should use height-driven growth model."""
        tree = Tree(species='LP', dbh=1.5, height=12.0)
        initial_dbh = tree.dbh
        tree.grow(site_index=70, basal_area=100)
        assert tree.dbh > initial_dbh

    def test_large_tree_growth(self):
        """Large trees should use diameter-driven growth model."""
        tree = Tree(species='LP', dbh=8.0, height=55.0)
        initial_dbh = tree.dbh
        tree.grow(site_index=70, basal_area=100)
        assert tree.dbh > initial_dbh

    @pytest.mark.parametrize("species", ["LP", "SP", "LL", "SA"])
    def test_all_species_grow(self, species):
        """All supported species should grow without errors."""
        tree = Tree(species=species, dbh=6.0, height=40.0)
        tree.grow(site_index=70, basal_area=100)
        assert tree.dbh > 6.0
```

### Test Categories

Mark tests appropriately:

```python
@pytest.mark.unit
def test_crown_ratio_bounds():
    """Unit test for crown ratio validation."""
    ...

@pytest.mark.integration
def test_stand_growth_simulation():
    """Integration test for full simulation."""
    ...

@pytest.mark.slow
def test_long_term_projection():
    """Slow test that runs 50-year simulation."""
    ...
```

## Growth Model Contributions

### Understanding the Models

Before modifying growth models, familiarize yourself with:

1. **[CLAUDE.md](CLAUDE.md)** - Architecture overview and known issues
2. **[SINGLE_TREE_GROWTH_GUIDE.md](SINGLE_TREE_GROWTH_GUIDE.md)** - Growth equation details
3. **[docs/FVS_PYTHON_VALIDATION_SPEC.md](docs/FVS_PYTHON_VALIDATION_SPEC.md)** - Validation requirements

### Growth Model Transition

The critical DBH transition between small and large tree models:

- `DBH < 1.0"`: Small-tree model only (height-driven)
- `1.0" <= DBH <= 3.0"`: Weighted blend of both models
- `DBH > 3.0"`: Large-tree model only (diameter-driven)

### Validation Requirements

Growth model changes must:

1. Pass all existing tests
2. Not degrade validation metrics beyond acceptance criteria:
   - Diameter growth: within 5% of expected
   - Height growth: within 10% of expected
   - Basal area: within 3% of expected
3. Include new tests for the changed behavior
4. Update validation outputs in `test_output/`

## Configuration Changes

### Modifying Species Parameters

Species configurations are in `cfg/species/*.yaml`:

```yaml
# cfg/species/lp_loblolly_pine.yaml
code: LP
name: Loblolly Pine
scientific_name: Pinus taeda

diameter_growth:
  model: ln_dds
  coefficients:
    b1: 0.222214
    b2: 1.163040
    ...
```

Changes to species parameters should:
1. Include a reference to the source (publication, FVS documentation)
2. Be validated against known yield tables
3. Update CLAUDE.md if significant

### Adding New Species

1. Create a new YAML file in `cfg/species/`
2. Add coefficients to relevant JSON files in `cfg/`
3. Add test coverage
4. Update documentation

## Documentation

### Building Documentation

```bash
# Install docs dependencies
uv pip install -e ".[docs]"

# Build Sphinx documentation
cd docs
sphinx-build -b html . _build/html
```

### Documentation Updates

When making code changes:
- Update docstrings for changed functions
- Update CLAUDE.md for significant fixes or known issues
- Update README.md if architecture changes
- Add examples for new features

## Pull Request Process

1. **Ensure all tests pass**
   ```bash
   uv run pytest
   ```

2. **Format code**
   ```bash
   uv run black src/fvs_python tests
   ```

3. **Update documentation** as needed

4. **Write a clear PR description** including:
   - What the change does
   - Why the change is needed
   - How it was tested
   - Any related issues

5. **Request review** from maintainers

### PR Title Format

Use conventional commit format:
- `feat: Add longleaf pine crown width equations`
- `fix: Correct bark ratio calculation for slash pine`
- `docs: Update getting started guide`
- `test: Add integration tests for thinning`
- `refactor: Simplify Stand.grow() time step handling`

## Reporting Issues

### Bug Reports

Include:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Relevant code or configuration
- Error messages and stack traces

### Feature Requests

Include:
- Use case description
- Proposed solution (if any)
- Alternatives considered

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Assume good intentions

## Questions?

- Open a [GitHub Issue](https://github.com/mihiarc/pyfvs/issues)
- Check existing documentation in `docs/`
- Review the [CLAUDE.md](CLAUDE.md) for project context

Thank you for contributing to PyFVS!

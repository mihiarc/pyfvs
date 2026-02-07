# Native FVS Integration for pyfvs

This document describes how to use the official USDA Forest Vegetation Simulator (FVS) Fortran code from Python through the `fvs_native` module.

## Overview

The `pyfvs.fvs_native` module provides Python bindings to the official USDA FVS shared library using ctypes. This allows pyfvs to call the authoritative FVS Fortran implementation instead of maintaining parallel Python reimplementations of growth models.

## Prerequisites

### 1. Clone the Official FVS Repository

```bash
cd ~/src
git clone https://github.com/USDAForestService/ForestVegetationSimulator.git fvs-official
cd fvs-official
git submodule update --init --recursive
```

### 2. Install Build Dependencies

On Ubuntu/Debian:
```bash
sudo apt install gfortran make
```

On macOS:
```bash
brew install gcc
```

### 3. Build FVS Shared Library

Build a specific variant (e.g., Southern):
```bash
cd ~/src/fvs-official/bin
make FVSsn.so
```

Or build all US variants:
```bash
make US
```

The build will create:
- `FVSsn.so` - Shared library (what we use from Python)
- `FVSsn` - Standalone executable

## Quick Start

```python
from pyfvs.fvs_native import FVSLibrary

# Load the Southern variant
fvs = FVSLibrary('sn')

# Run a simulation from a keyword file
fvs.run('--keywordfile=mystand.key')

# Get simulation results
dims = fvs.get_dimensions()
print(f"Trees: {dims['ntrees']}, Cycles: {dims['ncycles']}")

# Access tree data
tree_data = fvs.get_tree_data()
print(f"DBH values: {tree_data['dbh']}")
```

## API Reference

### FVSLibrary Class

```python
class FVSLibrary(variant: str = 'sn', lib_path: Optional[Path] = None)
```

**Parameters:**
- `variant`: FVS variant code (e.g., 'sn', 'pn', 'ie')
- `lib_path`: Optional path to library directory

### Initialization Methods

#### `run(cmdline: str) -> int`
Run a full FVS simulation.

```python
rtn = fvs.run('--keywordfile=stand.key')
```

#### `set_cmdline(cmdline: str) -> int`
Set command line parameters without running.

### Data Access Methods

#### `get_dimensions() -> Dict[str, int]`
Get current dimension information.

```python
dims = fvs.get_dimensions()
# Returns: {'ntrees': 100, 'ncycles': 5, 'nplots': 1, ...}
```

#### `get_tree_attr(name: str) -> np.ndarray`
Get a tree attribute array.

```python
dbh = fvs.get_tree_attr('dbh')
tpa = fvs.get_tree_attr('tpa')
```

**Available tree attributes:**
- `tpa` - Trees per acre
- `dbh` - Diameter at breast height (inches)
- `ht` - Total height (feet)
- `dg` - Diameter growth (inches)
- `htg` - Height growth (feet)
- `cratio` - Crown ratio (percent)
- `species` - Species code
- `age` - Tree age
- `mort` - Mortality prediction
- `tcuft` - Total cubic foot volume
- `mcuft` - Merchantable cubic foot volume
- `scuft` - Secondary cubic foot volume  
- `bdft` - Board foot volume

#### `set_tree_attr(name: str, values: np.ndarray)`
Set a tree attribute array.

```python
fvs.set_tree_attr('tpa', new_tpa_values)
```

#### `get_tree_data() -> Dict[str, np.ndarray]`
Get all common tree attributes as a dictionary.

```python
data = fvs.get_tree_data()
# Returns: {'tpa': [...], 'dbh': [...], 'ht': [...], ...}
```

#### `get_species_attr(name: str) -> np.ndarray`
Get a species-level attribute array.

```python
site_index = fvs.get_species_attr('spsiteindx')
```

**Available species attributes:**
- `spsiteindx` - Site index by species
- `spsdi` - Stand density index by species
- `spccf` - Crown competition factor by species
- `baimult` - Basal area growth multiplier
- `htgmult` - Height growth multiplier
- `mortmult` - Mortality multiplier

#### `get_summary(cycle: int) -> Dict[str, int]`
Get summary statistics for a cycle.

```python
summary = fvs.get_summary(1)
print(f"Year: {summary['year']}, BA: {summary['ba_bef']}")
```

### Tree Manipulation

#### `cut_trees(proportion_to_cut: np.ndarray) -> int`
Mark trees for cutting by specifying proportion of each tree record to remove.

```python
# Cut 50% of each tree record
proportions = np.full(dims['ntrees'], 0.5)
fvs.cut_trees(proportions)
```

## Available Variants

| Code | Name | Region |
|------|------|--------|
| ak | Alaska | AK |
| bc | British Columbia | Canada |
| bm | Blue Mountains | OR, WA |
| ca | California | CA |
| ci | Central Idaho | ID |
| cr | Central Rockies | CO, WY |
| cs | Central States | Midwest |
| ec | East Cascades | WA, OR |
| em | Eastern Montana | MT |
| ie | Inland Empire | ID, MT, WA |
| kt | Kootenai | ID, MT |
| ls | Lake States | MN, WI, MI |
| nc | Northern California | CA |
| ne | Northeast | NE US |
| oc | Oregon Coast | OR |
| on | Ontario | Canada |
| op | Olympic Peninsula | WA |
| pn | Pacific Northwest | WA, OR |
| sn | Southern | SE US |
| so | South Oregon/NE California | OR, CA |
| tt | Tetons | WY, ID |
| ut | Utah | UT |
| wc | West Cascades | WA, OR |
| ws | Western Sierra | CA |

## Keyword File Format

FVS simulations are controlled by keyword files. Basic example:

```
STDIDENT
STAND01   My Stand Description
STDINFO          300     250      50     .01   -999
SITEINDEX         25           90
INVYEAR         2024
NUMCYCLE           5

TREELIST          15
1    PP    15.3       75    100       0        1       0
2    PP    12.8       60    100       0        1       0
3    DF    10.2       50    100       0        1       0
END

PROCESS
STOP
```

## Error Handling

```python
from pyfvs.fvs_native import FVSLibrary, FVSError

try:
    fvs = FVSLibrary('sn')
    fvs.run('--keywordfile=stand.key')
except FileNotFoundError as e:
    print(f"Library not found: {e}")
except FVSError as e:
    print(f"FVS error: {e}")
```

## Integration with pyfvs

The native library can be used alongside or instead of pyfvs Python implementations:

```python
from pyfvs.fvs_native import FVSLibrary
from pyfvs import Stand

# Use native FVS for simulation
fvs = FVSLibrary('sn')
fvs.run('--keywordfile=stand.key')

# Get data and create pyfvs Stand for analysis
tree_data = fvs.get_tree_data()
stand = Stand.from_tree_list(tree_data['species'], tree_data['dbh'], 
                             tree_data['ht'], tree_data['tpa'])
```

## Building Additional Variants

To build all available variants:

```bash
cd ~/src/fvs-official/bin

# Build all US variants
make US

# Build all including Canada variants  
make all

# Build specific variant
make FVSpn.so  # Pacific Northwest
make FVSne.so  # Northeast
```

## Troubleshooting

### Library Not Found
Ensure the library is built and in a searchable path:
```bash
export LD_LIBRARY_PATH=$HOME/src/fvs-official/bin:$LD_LIBRARY_PATH
```

### Symbol Not Found
Some functions have different names in different gfortran versions. The wrapper tries both naming conventions.

### Simulation Errors
Check the FVS output file for detailed error messages. Common issues:
- Invalid keyword file syntax
- Missing required keywords
- Invalid species codes for the variant

## References

- [Official FVS GitHub Repository](https://github.com/USDAForestService/ForestVegetationSimulator)
- [FVS Documentation](https://www.fs.usda.gov/fvs/)
- [FVS Variant Guides](https://www.fs.usda.gov/fmsc/fvs/documents/index.shtml)

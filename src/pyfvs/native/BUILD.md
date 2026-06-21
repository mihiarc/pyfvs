# Building FVS Shared Libraries

Instructions for building the native FVS Fortran shared libraries for use
with `pyfvs.native` validation bindings.

## Quick build (recommended)

From the pyfvs repo, build and install all variants the parity suite needs:

```bash
scripts/build_native_fvs.sh            # all 11 pyfvs variants -> ~/.fvs/lib
scripts/build_native_fvs.sh sn ls ne   # or a subset (lowercase codes)
```

The script compiles each variant from the FVS Fortran source (default
`~/Projects/ForestVegetationSimulator`) via the repo's own makefile, installs
`FVS<variant>.so` into `~/.fvs/lib`, and ad-hoc code-signs on macOS.

**Gotcha:** the FVS source tree's `volume/NVEL` (National Volume Estimator
Library) is a **git submodule**. A fresh clone/restore leaves it empty and the
build fails with `No rule to make target '../volume/NVEL/beqinfo.inc'`. The
script initializes it automatically; to do it by hand:

```bash
git -C ~/Projects/ForestVegetationSimulator submodule update --init --recursive
```

Then run the parity suite. The parity tests are auto-marked `parity` and the
default pytest config deselects them (`-m "not slow and not parity"`), so you
**must** opt in explicitly:

```bash
uv run pytest tests/parity/ -m parity
```

The manual, single-variant steps below are kept for reference.

## Prerequisites

### macOS

```bash
# Install gfortran via Homebrew
brew install gcc

# Verify installation
gfortran --version
```

### Linux (Ubuntu/Debian)

```bash
sudo apt install gfortran make
```

## Building FVS

### 1. Clone the FVS repository

```bash
# --recursive pulls the volume/NVEL submodule (required for the build)
git clone --recursive https://github.com/USDAForestService/ForestVegetationSimulator.git
cd ForestVegetationSimulator
```

### 2. Build a variant as a shared library

The FVS build system uses Make. Each variant is built independently.

```bash
# Build the Southern (SN) variant
cd bin
make FVSsn

# The executable is placed in bin/FVSsn
# We need a shared library instead — see step 3
```

### 3. Build as a shared library (macOS)

FVS doesn't natively build shared libraries. You need to compile the
Fortran source files with `-shared -fPIC` flags:

```bash
# From the FVS repository root
cd bin

# Example: Build FVSsn as a shared library
# Collect all .f and .f90 source files for the SN variant
gfortran -shared -fPIC -o FVSsn.dylib \
    ../sn/src/*.f ../sn/src/*.f90 \
    ../base/src/*.f ../base/src/*.f90 \
    ../fire/sn/src/*.f \
    ../api/src/*.f \
    -I../base/obj -I../sn/obj \
    -O2 -fno-range-check -fallow-argument-mismatch
```

**Important compile flags:**
- `-shared -fPIC` — Required for shared library
- `-fno-range-check` — FVS uses integer overflow patterns
- `-fallow-argument-mismatch` — FVS passes mismatched types (common in legacy Fortran)

### 3b. Build as a shared library (Linux)

```bash
gfortran -shared -fPIC -o FVSsn.so \
    ../sn/src/*.f ../sn/src/*.f90 \
    ../base/src/*.f ../base/src/*.f90 \
    ../fire/sn/src/*.f \
    ../api/src/*.f \
    -O2 -fno-range-check -fallow-argument-mismatch
```

### 4. Install the shared library

```bash
# Option A: Install to ~/.fvs/lib/ (recommended, no sudo needed)
mkdir -p ~/.fvs/lib
cp FVSsn.dylib ~/.fvs/lib/    # macOS
cp FVSsn.so ~/.fvs/lib/       # Linux

# Option B: Install to /usr/local/lib/
sudo cp FVSsn.dylib /usr/local/lib/

# Option C: Use FVS_LIB_PATH environment variable
export FVS_LIB_PATH=/path/to/your/fvs/libs
```

### 5. Build additional variants

Repeat steps 3-4 for each variant you need:

```bash
# Pacific Northwest Coast
gfortran -shared -fPIC -o FVSpn.dylib ../pn/src/*.f ../base/src/*.f ../api/src/*.f ...

# Lake States
gfortran -shared -fPIC -o FVSls.dylib ../ls/src/*.f ../base/src/*.f ../api/src/*.f ...

# West Cascades
gfortran -shared -fPIC -o FVSwc.dylib ../wc/src/*.f ../base/src/*.f ../api/src/*.f ...

# Northeast
gfortran -shared -fPIC -o FVSne.dylib ../ne/src/*.f ../base/src/*.f ../api/src/*.f ...
```

## Verification

```bash
# Check if pyfvs can find the library
uv run python -c "
from pyfvs.native import fvs_library_available, get_library_info
print(fvs_library_available('SN'))
print(get_library_info('SN'))
"
```

Expected output when library IS installed:
```
True
{'variant': 'SN', 'available': True, 'path': '/Users/you/.fvs/lib/FVSsn.dylib', ...}
```

Expected output when library is NOT installed:
```
False
{'variant': 'SN', 'available': False, 'path': None, ...}
```

## Library Search Order

pyfvs searches for FVS libraries in this order:

1. `FVS_LIB_PATH` environment variable (directory path)
2. `~/.fvs/lib/`
3. `/usr/local/lib/`
4. `./lib/` (relative to working directory)

Library naming convention: `FVS{variant}.{ext}`
- macOS: `FVSsn.dylib`
- Linux: `FVSsn.so`
- Windows: `FVSsn.dll`

## Troubleshooting

### Symbol not found errors

If you get errors about missing symbols like `fvssetcmdline_`, the library
was built without the API subroutines. Make sure to include `../api/src/*.f`
in your compilation command.

### Multiple definition errors

FVS variants share source files. If you get multiple definition errors,
build each variant in a clean directory or use separate object file directories.

### macOS code signing

On macOS 12+, unsigned shared libraries may be blocked. Either sign the library
or allow it in System Settings > Privacy & Security.

```bash
# Ad-hoc sign the library
codesign -s - ~/.fvs/lib/FVSsn.dylib
```

### Fortran COMMON block limitations

FVS uses Fortran COMMON blocks for global state. This means:
- Only ONE simulation can run at a time per variant
- Each variant must be a separate shared library
- Thread safety is NOT guaranteed

Use `NativeStand` as a context manager to ensure proper cleanup:
```python
with NativeStand(variant='SN') as ns:
    ns.initialize_planted(500, 70, 'LP')
    ns.grow(50)
    metrics = ns.get_metrics()
```

"""Parity tests: pyfvs vs native FVS Fortran library.

This package contains tests that validate pyfvs simulation outputs against
the USDA Forest Service FVS Fortran reference implementation. These tests
require the native FVS shared libraries to be built and discoverable; they
auto-skip when the libraries are absent so the suite still runs in
environments without a Fortran toolchain.

To enable parity tests:

    1. Clone https://github.com/USDAForestService/ForestVegetationSimulator
    2. cd ForestVegetationSimulator && git submodule update --init
    3. cd bin && make US                    # builds all US variants
    4. export FVS_LIB_PATH=$PWD             # or symlink .so files into ~/.fvs/lib

Then:

    uv run pytest tests/parity/ -m parity

The tests are marked with @pytest.mark.parity so the default test run does
not require the Fortran toolchain.
"""

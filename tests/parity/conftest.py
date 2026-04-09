"""Shared fixtures for pyfvs vs native FVS parity tests.

Discovers the FVS shared libraries built from the Fortran source, and
provides fixtures that:

  - Skip the entire parity test module if no libraries are available.
  - Skip an individual test if the specific variant it needs is missing.
  - Provide a `parity_tolerance` fixture so the tolerance is one declarative
    knob, not scattered across tests.

Library discovery order (matches pyfvs.native.library_loader):

  1. FVS_LIB_PATH environment variable
  2. ~/.fvs/lib/
  3. /usr/local/lib/
  4. ./lib/

If none of those resolve, the conftest tries the conventional FVS source
build location (../ForestVegetationSimulator/bin) and sets FVS_LIB_PATH
for the test session.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pyfvs.native.library_loader import (
    clear_library_cache,
    fvs_library_available,
    get_library_info,
)


# Variants the parity suite knows how to test. Add to this list when a new
# variant has both a pyfvs implementation and an FVS{variant}.so/.dylib build.
PARITY_VARIANTS = [
    "SN", "LS", "PN", "WC", "NE", "CS", "OP", "CA", "OC", "WS",
]


def _try_locate_fvs_bin() -> Path | None:
    """Look for an FVS source-tree build of the .so/.dylib files.

    The FVS makefile produces shared libraries directly in `bin/`, so if the
    user has cloned the source tree as a sibling of the pyfvs project, we
    can locate it without manual env-var setup.
    """
    candidates = [
        Path.home() / "Projects" / "ForestVegetationSimulator" / "bin",
        Path.cwd().parent / "ForestVegetationSimulator" / "bin",
        Path.cwd() / "ForestVegetationSimulator" / "bin",
    ]
    for c in candidates:
        if c.is_dir() and any(c.glob("FVS*.so")) or any(c.glob("FVS*.dylib")):
            return c
    return None


def pytest_configure(config):
    """Auto-set FVS_LIB_PATH if a sibling FVS build exists.

    This avoids forcing every contributor to remember the environment
    variable when their layout matches the convention.
    """
    if "FVS_LIB_PATH" not in os.environ:
        bin_dir = _try_locate_fvs_bin()
        if bin_dir is not None:
            os.environ["FVS_LIB_PATH"] = str(bin_dir)
            # The library loader caches results — clear so it picks up the
            # new path.
            clear_library_cache()


def _available_variants() -> list[str]:
    """Return the variants for which an FVS shared library can be loaded."""
    return [v for v in PARITY_VARIANTS if fvs_library_available(v)]


@pytest.fixture(scope="session")
def available_parity_variants() -> list[str]:
    """Session-scoped list of variants that can run parity tests."""
    return _available_variants()


@pytest.fixture
def require_native_variant():
    """Function fixture that skips a test if the requested variant lacks a library.

    Usage:
        def test_oc_growth(require_native_variant):
            require_native_variant("OC")
            ...
    """
    def _require(variant: str):
        if not fvs_library_available(variant):
            info = get_library_info(variant)
            pytest.skip(
                f"FVS {variant} native library not found "
                f"(searched: {info['search_paths']}). "
                f"Build with 'make {variant.lower()}' in the FVS bin/ directory "
                f"and either set FVS_LIB_PATH or symlink into ~/.fvs/lib/."
            )
    return _require


@pytest.fixture
def parity_tolerance():
    """Default tolerances for pyfvs vs native FVS comparisons.

    These are intentionally tight (~1% relative) for stand-level metrics —
    the goal of parity testing is to catch coefficient-level errors, not to
    paper them over.

    Stochastic mode is disabled in parity tests, so the only sources of
    divergence should be:
      - Model translation bugs (the thing we want to catch)
      - Floating-point order-of-operations differences (well below 1%)
    """
    return {
        "tpa_rel": 0.02,          # 2% relative tolerance on TPA
        "ba_rel": 0.05,           # 5% relative tolerance on basal area
        "qmd_rel": 0.05,          # 5% relative tolerance on QMD
        "top_height_rel": 0.05,   # 5% relative tolerance on top height
        "volume_rel": 0.10,       # 10% relative tolerance on volume
        "dbh_rel": 0.05,          # 5% relative tolerance per-tree DBH
        "ht_rel": 0.05,           # 5% relative tolerance per-tree height
    }


def pytest_collection_modifyitems(config, items):
    """Auto-mark every test in tests/parity/ with @pytest.mark.parity."""
    parity_marker = pytest.mark.parity
    for item in items:
        if "tests/parity/" in str(item.fspath) or "tests\\parity\\" in str(item.fspath):
            item.add_marker(parity_marker)

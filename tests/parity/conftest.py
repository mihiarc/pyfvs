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
    """Per-metric parity bands for the normalized tolerance regime.

    Two layers (full rationale in docs/parity_tolerances.md):

    * ``floor`` — the deterministic band, and the lower bound for stochastic
      bands. 0.5% relative on TPA/BA/QMD/top_height (and per-tree DBH/height);
      1.0% on volume (volume compounds DBH^2 * height, so it carries one extra
      band-width). **Deterministic variants** (EC, OP, OC — ``stochastic=False``
      compared against the deterministic native run) are held to exactly this
      floor.

    * ``cap`` — the absolute ceiling: the pre-normalization values (TPA 2%,
      BA/QMD/top_height/DBH/height 5%, volume 10%). A stochastic band may never
      exceed the cap; if 3xSEM would, that is a finding (raise n_seeds or flag),
      never a looser band — the regime can only tighten or hold.

    **Stochastic multi-seed variants** (SN, LS, PN, WC, NE, CS, CA) use, per
    metric, ``band = min(cap, max(floor, 3 * relative_SEM))``, where
    relative_SEM is the standard error of the N-seed mean measured live from the
    seeds (see ``assert_metrics_close_mean``). NOTE: this corrects the prior
    docstring, which wrongly claimed a flat "~1% tight" band and "stochastic
    mode disabled" — parity runs are stochastic-vs-stochastic for these 7
    variants (native FVS defaults DGSD>0); only EC/OP/OC are deterministic.
    """
    return {
        # Deterministic band + stochastic lower bound.
        "floor": {
            "tpa": 0.005,
            "basal_area": 0.005,
            "qmd": 0.005,
            "top_height": 0.005,
            "dbh": 0.005,
            "ht": 0.005,
            "volume": 0.010,
        },
        # Absolute ceiling — a band may never exceed these (today's values).
        "cap": {
            "tpa": 0.02,
            "basal_area": 0.05,
            "qmd": 0.05,
            "top_height": 0.05,
            "dbh": 0.05,
            "ht": 0.05,
            "volume": 0.10,
        },
    }


def pytest_collection_modifyitems(config, items):
    """Auto-mark every test in tests/parity/ with @pytest.mark.parity."""
    parity_marker = pytest.mark.parity
    for item in items:
        if "tests/parity/" in str(item.fspath) or "tests\\parity\\" in str(item.fspath):
            item.add_marker(parity_marker)

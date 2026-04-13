"""Comparison helpers for pyfvs vs native FVS parity tests.

Pulled out so that individual variant tests stay focused on the *scenario*
under test (species, density, site index, cycles) rather than the mechanics
of running both engines and diffing their results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import pytest


@dataclass
class ScenarioResult:
    """Results of running a single scenario through one engine."""

    engine: str  # "pyfvs" or "native"
    metrics: Dict[str, float]
    n_cycles: int


def run_pyfvs(
    *,
    variant: str,
    species: str,
    site_index: float,
    trees_per_acre: int,
    years: int,
    random_seed: int = 42,
    stochastic: bool = False,
    ecounit: str | None = None,
    bare_ground: bool = False,
) -> ScenarioResult:
    """Run a planted-stand scenario through pyfvs.

    Parity tests run with stochastic=False so the only divergence between
    pyfvs and native FVS comes from real translation differences, not from
    different random draws.

    Args:
        bare_ground: When True, bypass Stand.initialize_planted's
            establishment fast-forward and start from the same bare-ground
            state as native FVS (age=1, DBH=0.1, ht=1.0). Use this for
            apples-to-apples comparison with NativeStand which always
            plants seedlings via the FVS PLANT/ESTAB keywords.
    """
    from pyfvs import Stand
    from pyfvs.tree import Tree

    if bare_ground:
        # Match NativeStand's PLANT keyword: bare-ground seedlings.
        # bare_ground=True on Stand triggers an establishment-only first
        # cycle (Fortran LESTB=TRUE) so pyfvs and native stay in sync.
        #
        # Initial height must match ESSUBH (species-specific).  Each
        # variant's essubh.f sets HHT by species — for OC, DF=2.0,
        # LP=3.0, RF=1.0, etc.  DBH = 0.1 and age = 1 for all.
        from pyfvs.establishment import get_essubh_height
        init_ht = get_essubh_height(species, variant)
        trees = [
            Tree(dbh=0.1, height=init_ht, age=1, species=species, variant=variant)
            for _ in range(trees_per_acre)
        ]
        stand = Stand(
            trees,
            site_index=site_index,
            species=species,
            variant=variant,
            ecounit=ecounit,
            stochastic=stochastic,
            random_seed=random_seed,
            bare_ground=True,
        )
        stand.age = 1
    else:
        kwargs: Dict[str, Any] = dict(
            trees_per_acre=trees_per_acre,
            site_index=site_index,
            species=species,
            variant=variant,
            random_seed=random_seed,
            stochastic=stochastic,
        )
        if ecounit is not None:
            kwargs["ecounit"] = ecounit
        stand = Stand.initialize_planted(**kwargs)

    stand.grow(years=years)
    metrics = stand.get_metrics()
    return ScenarioResult(engine="pyfvs", metrics=metrics, n_cycles=years)


def run_native(
    *,
    variant: str,
    species: str,
    site_index: float,
    trees_per_acre: int,
    years: int,
) -> ScenarioResult:
    """Run the same scenario through the native FVS Fortran library."""
    from pyfvs.native import NativeStand

    with NativeStand(variant=variant) as ns:
        ns.initialize_planted(
            trees_per_acre=trees_per_acre,
            site_index=site_index,
            species=species,
        )
        ns.grow(years=years)
        metrics = ns.get_metrics()

    return ScenarioResult(engine="native", metrics=metrics, n_cycles=years)


def assert_metrics_close(
    pyfvs_result: ScenarioResult,
    native_result: ScenarioResult,
    tolerance: Dict[str, float],
    *,
    skip_keys: tuple[str, ...] = (),
) -> None:
    """Assert that pyfvs and native FVS metrics are within tolerance.

    Each metric uses its own relative tolerance from the `tolerance` dict
    (see the `parity_tolerance` fixture). The assertion message tells you
    *which metric* diverged and by how much, so a single failed assertion
    is enough to drive a fix.
    """
    py = pyfvs_result.metrics
    nv = native_result.metrics

    metric_to_tol_key = {
        "tpa": "tpa_rel",
        "basal_area": "ba_rel",
        "qmd": "qmd_rel",
        "top_height": "top_height_rel",
        "volume": "volume_rel",
    }

    failures: list[str] = []
    for metric, tol_key in metric_to_tol_key.items():
        if metric in skip_keys:
            continue
        if metric not in py or metric not in nv:
            continue

        py_val = py[metric]
        nv_val = nv[metric]

        if nv_val == 0 and py_val == 0:
            continue
        if nv_val == 0:
            failures.append(
                f"{metric}: native=0 but pyfvs={py_val} "
                f"(cannot compute relative tolerance)"
            )
            continue

        rel_diff = abs(py_val - nv_val) / abs(nv_val)
        tol = tolerance[tol_key]
        if rel_diff > tol:
            failures.append(
                f"{metric}: pyfvs={py_val:.4f}, native={nv_val:.4f}, "
                f"rel_diff={rel_diff:.4%} > tol={tol:.2%}"
            )

    if failures:
        msg = (
            f"Parity check failed after {pyfvs_result.n_cycles} years. "
            f"{len(failures)} metric(s) out of tolerance:\n  - "
            + "\n  - ".join(failures)
        )
        raise AssertionError(msg)

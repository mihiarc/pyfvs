"""Comparison helpers for pyfvs vs native FVS parity tests.

Pulled out so that individual variant tests stay focused on the *scenario*
under test (species, density, site index, cycles) rather than the mechanics
of running both engines and diffing their results.

Two comparison modes:
  - Single-seed (``assert_metrics_close``): compares one pyfvs run against
    one native run. Useful for deterministic runs (stochastic=False) or as
    a single canary for regression.
  - Multi-seed (``run_pyfvs_multi_seed`` + ``assert_metrics_close_mean``):
    runs N pyfvs seeds and asserts the MEAN of each metric is within
    tolerance of the single native run. Native FVS produces a single
    stochastic realization per library call (its internal RNG is seeded
    per-cycle from NUMCYCLE), so a single native run already represents
    the expected behavior with acceptable sampling noise. Multi-seed on
    pyfvs eliminates false negatives from unlucky seed realizations while
    keeping mean-bias detection sensitive.
"""

from __future__ import annotations

import math
import os
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List

import pytest


# Single shared seed count for every stochastic multi-seed parity comparison.
# (One constant — not per-variant copies.) See docs/parity_tolerances.md.
PARITY_N_SEEDS = 10

# Stand-level metrics compared in every parity assertion.
_PARITY_METRICS = ("tpa", "basal_area", "qmd", "top_height", "volume")


@dataclass
class ScenarioResult:
    """Results of running a single scenario through one engine."""

    engine: str  # "pyfvs" or "native"
    metrics: Dict[str, float]
    n_cycles: int


@dataclass
class MultiSeedResult:
    """Results of running a scenario through pyfvs at many RNG seeds."""

    engine: str  # "pyfvs"
    metrics_per_seed: List[Dict[str, float]] = field(default_factory=list)
    seeds: List[int] = field(default_factory=list)
    n_cycles: int = 0

    @property
    def mean_metrics(self) -> Dict[str, float]:
        if not self.metrics_per_seed:
            return {}
        keys = self.metrics_per_seed[0].keys()
        return {
            k: statistics.mean(m[k] for m in self.metrics_per_seed)
            for k in keys
        }

    @property
    def stdev_metrics(self) -> Dict[str, float]:
        if len(self.metrics_per_seed) < 2:
            return {k: 0.0 for k in (self.metrics_per_seed[0] if self.metrics_per_seed else {})}
        keys = self.metrics_per_seed[0].keys()
        return {
            k: statistics.stdev(m[k] for m in self.metrics_per_seed)
            for k in keys
        }


def run_pyfvs(
    *,
    variant: str,
    species: str,
    site_index: float,
    trees_per_acre: int,
    years: int,
    random_seed: int = 42,
    stochastic: bool = True,
    ecounit: str | None = None,
    bare_ground: bool = False,
) -> ScenarioResult:
    """Run a planted-stand scenario through pyfvs.

    Parity tests run stochastic=True with a fixed seed by default,
    matching Fortran FVSsn's default DGSD=2.0 (per grinit.f:171).
    Both engines apply per-tree DG variation bounded to ±2σ around
    predicted ln(DDS); stand-aggregate metrics converge but individual
    trees carry ecological variance. Pass stochastic=False for an
    apples-to-apples comparison against FVS runs with DGSTDEV 0.0.

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


def run_pyfvs_multi_seed(
    *,
    variant: str,
    species: str,
    site_index: float,
    trees_per_acre: int,
    years: int,
    n_seeds: int = PARITY_N_SEEDS,
    base_seed: int = 42,
    ecounit: str | None = None,
    bare_ground: bool = False,
) -> MultiSeedResult:
    """Run a pyfvs scenario across ``n_seeds`` sequential RNG seeds.

    Always stochastic=True — multi-seed only makes sense for stochastic
    runs. Use the single-seed ``run_pyfvs(stochastic=False, ...)`` for
    deterministic parity.

    The seed sequence is [base_seed, base_seed+1, ..., base_seed+n_seeds-1]
    so runs are reproducible and inspectable.
    """
    metrics_per_seed: List[Dict[str, float]] = []
    seeds: List[int] = []
    for i in range(n_seeds):
        seed = base_seed + i
        result = run_pyfvs(
            variant=variant,
            species=species,
            site_index=site_index,
            trees_per_acre=trees_per_acre,
            years=years,
            random_seed=seed,
            stochastic=True,
            ecounit=ecounit,
            bare_ground=bare_ground,
        )
        metrics_per_seed.append(result.metrics)
        seeds.append(seed)

    return MultiSeedResult(
        engine="pyfvs",
        metrics_per_seed=metrics_per_seed,
        seeds=seeds,
        n_cycles=years,
    )


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


def _emit_sem_row(kind: str, metric: str, fields: Dict[str, Any]) -> None:
    """Emit a tab-delimited measurement row when PARITY_EMIT_SEM=1.

    Tagged with the running pytest nodeid (PYTEST_CURRENT_TEST) so a single
    instrumented suite run reconstructs the full raw measured-SEM table that
    docs/parity_tolerances.md is built from. Emitting only; never affects
    pass/fail.
    """
    if os.environ.get("PARITY_EMIT_SEM") != "1":
        return
    node = os.environ.get("PYTEST_CURRENT_TEST", "").split(" (call)")[0]
    parts = "\t".join(f"{k}={v}" for k, v in fields.items())
    print(f"SEMROW\t{kind}\t{node}\t{metric}\t{parts}")


def assert_metrics_close(
    pyfvs_result: ScenarioResult,
    native_result: ScenarioResult,
    tolerance: Dict[str, Any],
    *,
    skip_keys: tuple[str, ...] = (),
) -> None:
    """Assert a *deterministic* pyfvs run is within the floor band of native.

    Used by the deterministic variants (EC, OP, OC; ``stochastic=False``)
    compared against the deterministic native run. The band is the per-metric
    deterministic **floor** of the ``parity_tolerance`` regime — 0.5% relative
    on TPA/BA/QMD/top_height (and DBH/height), 1.0% on volume. There is no
    sampling noise to absorb, so the floor applies directly. See
    docs/parity_tolerances.md.
    """
    py = pyfvs_result.metrics
    nv = native_result.metrics
    floor = tolerance["floor"]

    failures: list[str] = []
    for metric in _PARITY_METRICS:
        if metric not in py or metric not in nv:
            continue
        py_val = py[metric]
        nv_val = nv[metric]
        band = floor[metric]
        rel_diff = (abs(py_val - nv_val) / abs(nv_val)) if nv_val else float("inf")
        _emit_sem_row(
            "DET", metric,
            {"pyfvs": f"{py_val:.4f}", "native": f"{nv_val:.4f}",
             "reldiff": f"{rel_diff:.4%}", "band": f"{band:.3%}",
             "verdict": "SKIP" if metric in skip_keys else
                        ("PASS" if rel_diff <= band else "FAIL")},
        )
        if metric in skip_keys:
            continue
        if nv_val == 0 and py_val == 0:
            continue
        if nv_val == 0:
            failures.append(f"{metric}: native=0 but pyfvs={py_val}")
            continue
        if rel_diff > band:
            failures.append(
                f"{metric}: pyfvs={py_val:.4f}, native={nv_val:.4f}, "
                f"rel_diff={rel_diff:.4%} > band={band:.3%} (deterministic floor)"
            )

    if failures:
        raise AssertionError(
            f"Deterministic parity check failed after {pyfvs_result.n_cycles} "
            f"years. {len(failures)} metric(s) out of tolerance:\n  - "
            + "\n  - ".join(failures)
        )


def assert_metrics_close_mean(
    pyfvs_result: MultiSeedResult,
    native_result: ScenarioResult,
    tolerance: Dict[str, Any],
    *,
    skip_keys: tuple[str, ...] = (),
) -> None:
    """Assert the N-seed mean is within the SEM-derived band of native.

    Per the normalized ``parity_tolerance`` regime, the band for each metric is

        band = min(cap, max(floor, 3 * relative_SEM))

    where ``relative_SEM = (stdev_across_seeds / sqrt(N)) / |mean|`` is the
    standard error of the N-seed mean, measured live from the same seeds.
    ``floor`` is the deterministic lower bound (0.5% / 1.0% volume); ``3xSEM``
    is the ~99.7% sampling-noise band of the mean; ``cap`` (today's value: TPA
    2%, BA/QMD/top_height 5%, volume 10%) is the absolute ceiling the band may
    never exceed. If ``3xSEM`` exceeds the cap, the band is capped (never
    looser) and flagged ``CAPPED`` — a finding, not a wider band. See
    docs/parity_tolerances.md.
    """
    py_mean = pyfvs_result.mean_metrics
    py_stdev = pyfvs_result.stdev_metrics
    nv = native_result.metrics
    n_seeds = len(pyfvs_result.seeds)
    floor = tolerance["floor"]
    cap = tolerance["cap"]

    failures: list[str] = []
    for metric in _PARITY_METRICS:
        if metric not in py_mean or metric not in nv:
            continue
        mean_val = py_mean[metric]
        stdev_val = py_stdev.get(metric, 0.0)
        nv_val = nv[metric]

        sem = (stdev_val / math.sqrt(n_seeds)) if n_seeds > 0 else 0.0
        rel_sem = (sem / abs(mean_val)) if mean_val else 0.0
        three_sem = 3.0 * rel_sem
        capped = three_sem > cap[metric]
        band = min(cap[metric], max(floor[metric], three_sem))
        rel_diff = (abs(mean_val - nv_val) / abs(nv_val)) if nv_val else float("inf")

        _emit_sem_row(
            "STOCH", metric,
            {"mean": f"{mean_val:.4f}", "native": f"{nv_val:.4f}",
             "stdev_rel": f"{(stdev_val / abs(mean_val) if mean_val else 0):.4%}",
             "sem_rel": f"{rel_sem:.4%}", "x3sem": f"{three_sem:.4%}",
             "floor": f"{floor[metric]:.3%}", "cap": f"{cap[metric]:.2%}",
             "band": f"{band:.4%}", "reldiff": f"{rel_diff:.4%}",
             "capped": str(capped),
             "verdict": "SKIP" if metric in skip_keys else
                        ("PASS" if rel_diff <= band else "FAIL")},
        )

        if metric in skip_keys:
            continue
        if nv_val == 0 and mean_val == 0:
            continue
        if nv_val == 0:
            failures.append(f"{metric}: native=0 but pyfvs_mean={mean_val}")
            continue
        if rel_diff > band:
            failures.append(
                f"{metric}: pyfvs_mean={mean_val:.4f} (rel_SEM={rel_sem:.3%}, "
                f"3xSEM={three_sem:.3%}{', CAPPED at cap' if capped else ''}), "
                f"native={nv_val:.4f}, rel_diff={rel_diff:.4%} > band={band:.3%}"
            )

    if failures:
        raise AssertionError(
            f"Stochastic multi-seed parity check failed after "
            f"{pyfvs_result.n_cycles} years (n_seeds={n_seeds}). "
            f"{len(failures)} metric(s) out of tolerance:\n  - "
            + "\n  - ".join(failures)
        )

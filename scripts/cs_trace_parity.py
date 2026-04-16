#!/usr/bin/env python3
"""Per-cycle trace parity: pyfvs vs native FVScs at 10/20/30yr checkpoints.

Usage:
    FVS_LIB_PATH=/Users/cmihiar/Projects/ForestVegetationSimulator/bin \
        uv run python scripts/cs_trace_parity.py WO

Traces BA/QMD/TH/TPA for a given CS species at each 10-yr checkpoint,
printing native and pyfvs (deterministic + stochastic) side-by-side.
Used to isolate WHICH cycle the CS over-prediction opens — independent
of compound effects. Mirrors ls_trace_parity.py.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

if not os.environ.get("FVS_LIB_PATH"):
    candidate = Path("/Users/cmihiar/Projects/ForestVegetationSimulator/bin")
    if candidate.exists():
        os.environ["FVS_LIB_PATH"] = str(candidate)

from pyfvs import Stand  # noqa: E402
from pyfvs.native import NativeStand, fvs_library_available  # noqa: E402
from pyfvs.tree import Tree  # noqa: E402
from pyfvs.establishment import get_essubh_height  # noqa: E402


def _build_pyfvs_stand(species: str, si: int, tpa: int,
                       stochastic: bool, seed: int) -> Stand:
    """Match run_pyfvs bare-ground init so trace matches the sweep."""
    trees = [
        Tree(dbh=0.1, height=get_essubh_height(species, "CS"),
             age=1, species=species, variant="CS")
        for _ in range(tpa)
    ]
    stand = Stand(
        trees,
        site_index=si,
        species=species,
        variant="CS",
        stochastic=stochastic,
        random_seed=seed if stochastic else None,
        bare_ground=True,
    )
    stand.age = 1
    return stand


def _metrics_row(engine: str, years: int, m: dict) -> str:
    return (
        f"  {engine:10} yr{years:>2}  BA={m.get('basal_area', 0):6.2f}  "
        f"QMD={m.get('qmd', 0):5.2f}  TH={m.get('top_height', 0):5.1f}  "
        f"TPA={m.get('tpa', 0):6.1f}"
    )


def _delta(py: dict, nv: dict) -> str:
    def rel(key: str) -> float:
        p, n = py.get(key, 0.0), nv.get(key, 0.0)
        return 100.0 * (p - n) / n if n else 0.0
    return (
        f"   ΔBA={rel('basal_area'):+6.1f}%  ΔQMD={rel('qmd'):+5.1f}%  "
        f"ΔTH={rel('top_height'):+5.1f}%"
    )


def trace_species(species: str, si: int = 60, tpa: int = 500,
                  checkpoints=(10, 20, 30)) -> None:
    if not fvs_library_available("CS"):
        print("FVS CS native library not available. Set FVS_LIB_PATH.",
              file=sys.stderr)
        sys.exit(1)

    print(f"\n=== {species} SI={si} TPA={tpa} ===")
    print("                     BA      QMD   TH    TPA")
    for yrs in checkpoints:
        stand_det = _build_pyfvs_stand(species, si, tpa, stochastic=False, seed=42)
        stand_det.grow(years=yrs)
        m_det = stand_det.get_metrics()

        stand_sto = _build_pyfvs_stand(species, si, tpa, stochastic=True, seed=42)
        stand_sto.grow(years=yrs)
        m_sto = stand_sto.get_metrics()

        with NativeStand(variant="CS") as ns:
            ns.initialize_planted(trees_per_acre=tpa, site_index=si, species=species)
            ns.grow(years=yrs)
            m_nat = ns.get_metrics()

        print()
        print(_metrics_row("native", yrs, m_nat))
        print(_metrics_row("pyfvs-det", yrs, m_det) + _delta(m_det, m_nat))
        print(_metrics_row("pyfvs-sto", yrs, m_sto) + _delta(m_sto, m_nat))


if __name__ == "__main__":
    species_list = sys.argv[1:] or ["WO"]
    for sp in species_list:
        trace_species(sp)

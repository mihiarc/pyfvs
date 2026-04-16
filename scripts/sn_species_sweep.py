#!/usr/bin/env python3
"""Exhaustive SN species parity sweep: pyfvs vs native FVSsn for all 90 species.

Reporting-only discovery tool. Always exits 0 and writes a markdown report
to ``test_output/sn_species_sweep.md``. Use to find systematic drift across
species before promoting individual scenarios to pytest parity tests.

Default scenario per species:
  - 500 TPA, 25 years (5 SN cycles), bare_ground=True
  - site_index: midpoint of Fortran sitset.f SIMIN/SIMAX, rounded to nearest 5
  - 3 pyfvs seeds (base=42) vs single native run (DGSD=2.0 default)

Buckets sorted by |ΔBA%|:
  - pass  : |ΔBA| < 5%
  - warn  : 5% ≤ |ΔBA| < 10%
  - fail  : |ΔBA| ≥ 10%
  - error : runtime error on either engine

Usage:
    uv run python scripts/sn_species_sweep.py
"""

from __future__ import annotations

import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Make pyfvs importable when run directly.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from tests.parity._helpers import run_native, run_pyfvs_multi_seed  # noqa: E402


# FVS species codes in SN sequence order (from blkdat.f JSP array, sequences 1-90).
SN_SPECIES = [
    "FR", "JU", "PI", "PU", "SP", "SA", "SR", "LL", "TM", "PP",
    "PD", "WP", "LP", "VP", "BY", "PC", "HM", "FM", "BE", "RM",
    "SV", "SM", "BU", "BB", "SB", "AH", "HI", "CA", "HB", "RD",
    "DW", "PS", "AB", "AS", "WA", "BA", "GA", "HL", "LB", "HA",
    "HY", "BN", "WN", "SU", "YP", "MG", "CT", "MS", "MV", "ML",
    "AP", "MB", "WT", "BG", "TS", "HH", "SD", "RA", "SY", "CW",
    "BT", "BC", "WO", "SO", "SK", "CB", "TO", "LK", "OV", "BJ",
    "SN", "CK", "WK", "CO", "RO", "QS", "PO", "BO", "LO", "BK",
    "WI", "SS", "BD", "EL", "WE", "AE", "RL", "OS", "OH", "OT",
]

# SIMIN / SIMAX arrays from Fortran sitset.f (SN variant), sequence order 1-90.
# These bound the allowable site-index input per species. Default per-species
# SI for the sweep is the midpoint rounded to the nearest 5.
SN_SIMIN = [
    15, 15, 15, 35, 35, 35, 45, 45, 35, 25,
    35, 40, 40, 35, 30, 30, 35, 35, 35, 35,
    30, 35, 25, 35, 35, 15, 25, 30, 15, 15,
    15, 15, 35, 35, 35, 35, 35, 25, 15, 15,
    35, 35, 35, 30, 30, 35, 25, 35, 15, 35,
    15, 15, 30, 35, 35, 15, 15, 15, 30, 40,
    30, 35, 25, 25, 25, 30, 25, 25, 35, 25,
    35, 35, 30, 25, 25, 15, 25, 25, 30, 25,
    15, 15, 35, 35, 35, 35, 35, 15, 15, 15,
]
SN_SIMAX = [
    100,  70,  80, 100, 105, 105,  90, 125,  70,  95,
    105, 135, 125,  95, 120, 120,  90,  70,  70,  85,
    105, 100,  90,  85,  70,  40,  85,  90,  90,  40,
     45,  70,  85, 105,  95,  85, 105, 120,  50,  65,
     70,  85,  85, 125, 135, 125, 115, 125,  75, 125,
     40,  55, 105, 105,  95,  40,  70,  60, 120, 125,
     90, 105, 115, 115, 115, 125,  65,  65,  95,  65,
     95,  75, 115, 115, 115, 125,  85, 115,  65,  95,
    110,  80,  90,  90,  90,  90,  90,  55,  55,  55,
]

assert len(SN_SPECIES) == 90
assert len(SN_SIMIN) == 90
assert len(SN_SIMAX) == 90


# Scenario constants — same across all species. Tweak here to re-baseline.
DEFAULT_TPA = 500
DEFAULT_YEARS = 25
N_SEEDS = 3          # 3 is enough to smooth per-seed selection variance; 10 is CI-only
BASE_SEED = 42

# Bucket thresholds on |ΔBA%|.
PASS_THRESHOLD = 5.0
WARN_THRESHOLD = 10.0


def default_si(simin: int, simax: int) -> int:
    """Midpoint of the species' Fortran SI range, rounded to nearest 5."""
    mid = (simin + simax) / 2
    return int(round(mid / 5.0) * 5)


def rel_pct(py: float, nv: float) -> float:
    """Relative percent difference (pyfvs vs native). NaN-safe for nv==0."""
    if nv == 0:
        return float("inf") if py != 0 else 0.0
    return (py - nv) / nv * 100.0


def run_one_species(species: str, site_index: int) -> dict:
    """Run a single species scenario. Returns a result dict (never raises)."""
    result = {
        "species": species,
        "site_index": site_index,
        "status": "error",
        "error": None,
    }
    try:
        py = run_pyfvs_multi_seed(
            variant="SN",
            species=species,
            site_index=site_index,
            trees_per_acre=DEFAULT_TPA,
            years=DEFAULT_YEARS,
            n_seeds=N_SEEDS,
            base_seed=BASE_SEED,
            bare_ground=True,
        )
        nv = run_native(
            variant="SN",
            species=species,
            site_index=site_index,
            trees_per_acre=DEFAULT_TPA,
            years=DEFAULT_YEARS,
        )
        py_mean = py.mean_metrics
        py_stdev = py.stdev_metrics
        nv_m = nv.metrics

        result["native"] = nv_m
        result["pyfvs_mean"] = py_mean
        result["pyfvs_stdev"] = py_stdev

        deltas = {
            m: rel_pct(py_mean.get(m, 0.0), nv_m.get(m, 0.0))
            for m in ("basal_area", "tpa", "qmd", "top_height", "volume")
        }
        result["deltas"] = deltas

        ba_abs = abs(deltas["basal_area"])
        if ba_abs < PASS_THRESHOLD:
            result["status"] = "pass"
        elif ba_abs < WARN_THRESHOLD:
            result["status"] = "warn"
        else:
            result["status"] = "fail"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["error_traceback"] = traceback.format_exc()
    return result


def bucket(results: list[dict], status: str) -> list[dict]:
    """Filter results by status, sorted by |ΔBA%| descending within bucket."""
    filtered = [r for r in results if r["status"] == status]
    if status == "error":
        return sorted(filtered, key=lambda r: r["species"])
    return sorted(
        filtered,
        key=lambda r: abs(r["deltas"]["basal_area"]),
        reverse=(status != "pass"),  # pass: small→large; warn/fail: large→small
    )


def format_table(results: list[dict]) -> str:
    """Markdown table of species results with per-metric deltas."""
    if not results:
        return "_(none)_\n"
    lines = [
        "| sp | SI | native_BA | pyfvs_BA (±σ) | ΔBA% | ΔTPA% | ΔQMD% | ΔTH% | ΔVol% |",
        "| -- | -- | --------- | ------------- | ---- | ----- | ----- | ---- | ----- |",
    ]
    for r in results:
        d = r["deltas"]
        nv_ba = r["native"].get("basal_area", 0.0)
        py_ba = r["pyfvs_mean"].get("basal_area", 0.0)
        py_ba_sd = r["pyfvs_stdev"].get("basal_area", 0.0)
        lines.append(
            f"| {r['species']} | {r['site_index']} "
            f"| {nv_ba:7.2f} | {py_ba:7.2f} ± {py_ba_sd:.2f} "
            f"| {d['basal_area']:+6.2f} | {d['tpa']:+6.2f} "
            f"| {d['qmd']:+6.2f} | {d['top_height']:+6.2f} | {d['volume']:+6.2f} |"
        )
    return "\n".join(lines) + "\n"


def format_error_table(results: list[dict]) -> str:
    if not results:
        return "_(none)_\n"
    lines = ["| sp | SI | error |", "| -- | -- | ----- |"]
    for r in results:
        # Truncate error to keep the table readable.
        err = (r["error"] or "").replace("|", "\\|").replace("\n", " ")
        if len(err) > 160:
            err = err[:157] + "..."
        lines.append(f"| {r['species']} | {r['site_index']} | {err} |")
    return "\n".join(lines) + "\n"


def render_report(results: list[dict], elapsed: float) -> str:
    pass_ = bucket(results, "pass")
    warn = bucket(results, "warn")
    fail = bucket(results, "fail")
    err = bucket(results, "error")
    total = len(results)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"""# SN Species Parity Sweep

**Generated:** {now}
**Elapsed:** {elapsed:.1f}s
**Scenario:** {DEFAULT_TPA} TPA, {DEFAULT_YEARS}yr, bare_ground=True, {N_SEEDS} pyfvs seeds (base={BASE_SEED}) vs 1 native run
**SI defaults:** Fortran `sn/sitset.f` SIMIN/SIMAX midpoint, rounded to nearest 5
**Buckets (on |ΔBA%|):** pass <{PASS_THRESHOLD}%, warn <{WARN_THRESHOLD}%, fail ≥{WARN_THRESHOLD}%

## Summary

| bucket | count | share |
| ------ | ----- | ----- |
| pass   | {len(pass_):3d} | {len(pass_)/total:.0%} |
| warn   | {len(warn):3d} | {len(warn)/total:.0%} |
| fail   | {len(fail):3d} | {len(fail)/total:.0%} |
| error  | {len(err):3d} | {len(err)/total:.0%} |
| total  | {total:3d} | 100% |

## fail ({len(fail)})

{format_table(fail)}
## warn ({len(warn)})

{format_table(warn)}
## pass ({len(pass_)})

{format_table(pass_)}
## error ({len(err)})

{format_error_table(err)}
"""
    return header


def main() -> int:
    from pyfvs.native.library_loader import fvs_library_available
    # Auto-set FVS_LIB_PATH if the conventional sibling build is present,
    # mirroring tests/parity/conftest.py so the script works standalone.
    import os
    if "FVS_LIB_PATH" not in os.environ:
        candidate = Path.home() / "Projects" / "ForestVegetationSimulator" / "bin"
        if candidate.is_dir():
            os.environ["FVS_LIB_PATH"] = str(candidate)
            from pyfvs.native.library_loader import clear_library_cache
            clear_library_cache()

    if not fvs_library_available("SN"):
        print("ERROR: FVSsn native library not found. Build with 'make sn' "
              "in ForestVegetationSimulator/bin and/or set FVS_LIB_PATH.",
              file=sys.stderr)
        return 0  # reporting-only: exit 0 even on setup failure

    print(f"SN sweep: {len(SN_SPECIES)} species, {N_SEEDS} pyfvs seeds, "
          f"{DEFAULT_TPA} TPA, {DEFAULT_YEARS}yr", file=sys.stderr)
    start = time.time()
    results = []
    for i, sp in enumerate(SN_SPECIES, 1):
        si = default_si(SN_SIMIN[i - 1], SN_SIMAX[i - 1])
        t0 = time.time()
        r = run_one_species(sp, si)
        elapsed = time.time() - t0
        results.append(r)
        if r["status"] == "error":
            tag = "ERR "
        else:
            tag = f"{r['deltas']['basal_area']:+6.2f}%"
        print(f"  [{i:2d}/90] {sp} SI={si:3d}  BA {tag}  ({r['status']}, {elapsed:.1f}s)",
              file=sys.stderr)

    total_elapsed = time.time() - start
    report = render_report(results, total_elapsed)
    out_path = REPO_ROOT / "test_output" / "sn_species_sweep.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)
    print(f"\nReport: {out_path} ({total_elapsed:.1f}s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

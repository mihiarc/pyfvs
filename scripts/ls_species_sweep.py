#!/usr/bin/env python3
"""Exhaustive LS species parity sweep: pyfvs vs native FVSls for all 67 species.

Reporting-only discovery tool. Always exits 0 and writes a markdown report
to ``test_output/ls_species_sweep.md``. Mirrors ``sn_species_sweep.py``.

Default scenario per species:
  - 500 TPA, 30 years (3 LS 10-year cycles), bare_ground=True
  - site_index: 60 (Fortran ls/sitset.f:259 unset-default)
  - 3 pyfvs seeds (base=42) vs single native run

Buckets sorted by |ΔBA%|:
  - pass  : |ΔBA| < 5%
  - warn  : 5% ≤ |ΔBA| < 10%
  - fail  : |ΔBA| ≥ 10%
  - error : runtime error on either engine

Usage:
    uv run python scripts/ls_species_sweep.py
"""

from __future__ import annotations

import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from tests.parity._helpers import run_native, run_pyfvs_multi_seed  # noqa: E402


# FVS species codes in LS sequence order (from ls/blkdat.f JSP array).
# Position 44 is intentionally blank in Fortran ('   ') — 67 real species
# in 68 positions. We skip the blank slot when looping.
LS_SPECIES = [
    "JP", "SC", "RN", "RP", "WP", "WS", "NS",    # 1-7
    "BF", "BS", "TA", "WC", "EH", "OS", "RC",    # 8-14
    "BA", "GA", "EC", "SV", "RM", "BC", "AE",    # 15-21
    "RL", "RE", "YB", "BW", "SM", "BM", "AB",    # 22-28
    "WA", "WO", "SW", "BR", "CK", "RO", "BO",    # 29-35
    "NP", "BH", "PH", "SH", "BT", "QA", "BP",    # 36-42
    "PB", None, "BN", "WN", "HH", "BK", "OH",    # 43-49 (44 blank)
    "BE", "ST", "MM", "AH", "AC", "HK", "DW",    # 50-56
    "HT", "AP", "BG", "SY", "PR", "CC", "PL",    # 57-63
    "WI", "BL", "DM", "SS", "MA",                # 64-68
]
assert len(LS_SPECIES) == 68
assert sum(1 for s in LS_SPECIES if s is not None) == 67


# Scenario constants.
DEFAULT_TPA = 500
DEFAULT_YEARS = 30   # 3 LS 10-year cycles
DEFAULT_SI = 60      # Fortran ls/sitset.f:259 unset-default
N_SEEDS = 3
BASE_SEED = 42

PASS_THRESHOLD = 5.0
WARN_THRESHOLD = 10.0


def rel_pct(py: float, nv: float) -> float:
    if nv == 0:
        return float("inf") if py != 0 else 0.0
    return (py - nv) / nv * 100.0


def run_one_species(species: str, site_index: int) -> dict:
    result = {"species": species, "site_index": site_index,
              "status": "error", "error": None}
    try:
        py = run_pyfvs_multi_seed(
            variant="LS", species=species, site_index=site_index,
            trees_per_acre=DEFAULT_TPA, years=DEFAULT_YEARS,
            n_seeds=N_SEEDS, base_seed=BASE_SEED, bare_ground=True,
        )
        nv = run_native(
            variant="LS", species=species, site_index=site_index,
            trees_per_acre=DEFAULT_TPA, years=DEFAULT_YEARS,
        )
        py_mean, py_stdev = py.mean_metrics, py.stdev_metrics
        nv_m = nv.metrics
        result["native"] = nv_m
        result["pyfvs_mean"] = py_mean
        result["pyfvs_stdev"] = py_stdev
        deltas = {m: rel_pct(py_mean.get(m, 0.0), nv_m.get(m, 0.0))
                  for m in ("basal_area", "tpa", "qmd", "top_height", "volume")}
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
    filtered = [r for r in results if r["status"] == status]
    if status == "error":
        return sorted(filtered, key=lambda r: r["species"])
    return sorted(filtered,
                  key=lambda r: abs(r["deltas"]["basal_area"]),
                  reverse=(status != "pass"))


def format_table(results: list[dict]) -> str:
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
    return f"""# LS Species Parity Sweep

**Generated:** {now}
**Elapsed:** {elapsed:.1f}s
**Scenario:** {DEFAULT_TPA} TPA, {DEFAULT_YEARS}yr (3x LS 10-year cycles), bare_ground=True, {N_SEEDS} pyfvs seeds (base={BASE_SEED}) vs 1 native run
**SI default:** {DEFAULT_SI} (Fortran `ls/sitset.f:259` unset-default)
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


def main() -> int:
    import os
    if "FVS_LIB_PATH" not in os.environ:
        candidate = Path.home() / "Projects" / "ForestVegetationSimulator" / "bin"
        if candidate.is_dir():
            os.environ["FVS_LIB_PATH"] = str(candidate)
            from pyfvs.native.library_loader import clear_library_cache
            clear_library_cache()

    from pyfvs.native.library_loader import fvs_library_available
    if not fvs_library_available("LS"):
        print("ERROR: FVSls native library not found. Build with 'make ls' "
              "in ForestVegetationSimulator/bin and/or set FVS_LIB_PATH.",
              file=sys.stderr)
        return 0

    species_to_run = [s for s in LS_SPECIES if s is not None]
    print(f"LS sweep: {len(species_to_run)} species, {N_SEEDS} pyfvs seeds, "
          f"{DEFAULT_TPA} TPA, {DEFAULT_YEARS}yr, SI={DEFAULT_SI}", file=sys.stderr)
    start = time.time()
    results = []
    for i, sp in enumerate(species_to_run, 1):
        t0 = time.time()
        r = run_one_species(sp, DEFAULT_SI)
        elapsed = time.time() - t0
        results.append(r)
        tag = "ERR " if r["status"] == "error" else f"{r['deltas']['basal_area']:+6.2f}%"
        print(f"  [{i:2d}/{len(species_to_run)}] {sp} SI={DEFAULT_SI}  "
              f"BA {tag}  ({r['status']}, {elapsed:.1f}s)", file=sys.stderr)

    total_elapsed = time.time() - start
    report = render_report(results, total_elapsed)
    out_path = REPO_ROOT / "test_output" / "ls_species_sweep.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)
    print(f"\nReport: {out_path} ({total_elapsed:.1f}s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

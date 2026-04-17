#!/usr/bin/env python3
"""Exhaustive WC species parity sweep: pyfvs vs native FVSwc for all 38 species.

Reporting-only discovery tool. Mirrors pn_species_sweep.py. Writes to
``test_output/wc_species_sweep.md``.

WC (West Cascades) and PN (PNW Coast) share most Fortran modules; the
species list diverges only by SS (Sitka Spruce, PN only). WC has 38 real
species vs PN's 39.

Default scenario per species:
  - 500 TPA, 30 years (3 WC 10-year cycles), bare_ground=True
  - site_index: 100 (typical productive WC site)
  - 3 pyfvs seeds (base=42) vs single native run

Buckets sorted by |ΔBA%|:
  - pass  : |ΔBA| < 5%
  - warn  : 5% <= |ΔBA| < 10%
  - fail  : |ΔBA| >= 10%
  - error : runtime error on either engine

Usage:
    uv run python scripts/wc_species_sweep.py
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


# Fortran wc/blkdat.f:136-142 DATA JSP — 40 positions, 2 blanks (pos 6
# between RF and NF, pos 39 between WI and OT). 38 real species.
WC_SPECIES = [
    'SF', 'WF', 'GF', 'AF', 'RF', None, 'NF',      # 1-7 (pos 6 blank)
    'YC', 'IC', 'ES', 'LP', 'JP', 'SP', 'WP',      # 8-14
    'PP', 'DF', 'RW', 'RC', 'WH', 'MH', 'BM',      # 15-21
    'RA', 'WA', 'PB', 'GC', 'AS', 'CW', 'WO',      # 22-28
    'WJ', 'LL', 'WB', 'KP', 'PY', 'DG', 'HT',      # 29-35
    'CH', 'WI', None, 'OT',                         # 36-39 (pos 38 blank)
]
assert len(WC_SPECIES) == 39
assert sum(1 for s in WC_SPECIES if s is not None) == 37


DEFAULT_TPA = 500
DEFAULT_YEARS = 30
DEFAULT_SI = 100
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
            variant="WC", species=species, site_index=site_index,
            trees_per_acre=DEFAULT_TPA, years=DEFAULT_YEARS,
            n_seeds=N_SEEDS, base_seed=BASE_SEED, bare_ground=True,
        )
        nv = run_native(
            variant="WC", species=species, site_index=site_index,
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


def bucket(results, status):
    filtered = [r for r in results if r["status"] == status]
    if status == "error":
        return sorted(filtered, key=lambda r: r["species"])
    return sorted(filtered,
                  key=lambda r: abs(r["deltas"]["basal_area"]),
                  reverse=(status != "pass"))


def format_table(results):
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


def format_error_table(results):
    if not results:
        return "_(none)_\n"
    lines = ["| sp | SI | error |", "| -- | -- | ----- |"]
    for r in results:
        err = (r["error"] or "").replace("|", "\\|").replace("\n", " ")
        if len(err) > 160:
            err = err[:157] + "..."
        lines.append(f"| {r['species']} | {r['site_index']} | {err} |")
    return "\n".join(lines) + "\n"


def render_report(results, elapsed):
    pass_ = bucket(results, "pass")
    warn = bucket(results, "warn")
    fail = bucket(results, "fail")
    err = bucket(results, "error")
    total = len(results)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""# WC Species Parity Sweep

**Generated:** {now}
**Elapsed:** {elapsed:.1f}s
**Scenario:** {DEFAULT_TPA} TPA, {DEFAULT_YEARS}yr (3x WC 10-year cycles), bare_ground=True, {N_SEEDS} pyfvs seeds (base={BASE_SEED}) vs 1 native run
**SI default:** {DEFAULT_SI}
**Buckets (on |ΔBA%|):** pass <{PASS_THRESHOLD}%, warn <{WARN_THRESHOLD}%, fail >={WARN_THRESHOLD}%

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


def main():
    import os
    if "FVS_LIB_PATH" not in os.environ:
        candidate = Path.home() / "Projects" / "ForestVegetationSimulator" / "bin"
        if candidate.is_dir():
            os.environ["FVS_LIB_PATH"] = str(candidate)
            from pyfvs.native.library_loader import clear_library_cache
            clear_library_cache()

    from pyfvs.native.library_loader import fvs_library_available
    if not fvs_library_available("WC"):
        print("ERROR: FVSwc native library not found.", file=sys.stderr)
        return 0

    species_to_run = [s for s in WC_SPECIES if s is not None]
    print(f"WC sweep: {len(species_to_run)} species, {N_SEEDS} pyfvs seeds, "
          f"{DEFAULT_TPA} TPA, {DEFAULT_YEARS}yr, SI={DEFAULT_SI}", file=sys.stderr)
    start = time.time()
    results = []
    for i, sp in enumerate(species_to_run, 1):
        t0 = time.time()
        r = run_one_species(sp, DEFAULT_SI)
        elapsed = time.time() - t0
        results.append(r)
        tag = "ERR " if r["status"] == "error" else f"{r['deltas']['basal_area']:+6.2f}%"
        print(f"  [{i:3d}/{len(species_to_run)}] {sp} SI={DEFAULT_SI}  "
              f"BA {tag}  ({r['status']}, {elapsed:.1f}s)", file=sys.stderr)

    total_elapsed = time.time() - start
    report = render_report(results, total_elapsed)
    out_path = REPO_ROOT / "test_output" / "wc_species_sweep.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)
    print(f"\nReport: {out_path} ({total_elapsed:.1f}s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

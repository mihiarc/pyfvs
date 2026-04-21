"""Forest-rents pipeline parity sweep: pyfvs vs native FVS.

Runs every (variant, species) pair the forest-rents pipeline simulates
through both pyfvs (multi-seed mean) and native Fortran FVS, compares
BA / QMD / top_height / volume, and classifies each pair as
PASS / WARN / FAIL.

Usage:
    FVS_LIB_PATH=/path/to/ForestVegetationSimulator/bin \
        uv run python scripts/pipeline_parity_sweep.py

Writes a markdown report to scripts/pipeline_parity_report.md.
"""
from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

import warnings
warnings.filterwarnings("ignore")

# Ensure the repo src/ is on path (uv run usually handles this).
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pyfvs import Stand, set_default_variant  # noqa: E402
from pyfvs.native import NativeStand, fvs_library_available  # noqa: E402


# Forest-rents pipeline matrix: (region, species, fia_code, variant).
PIPELINE_MATRIX = [
    ("southern", "LP", 131, "SN"),
    ("southern", "SA", 111, "SN"),
    ("southern", "LL", 121, "SN"),
    ("southern", "SP", 110, "SN"),
    ("southern", "WO", 802, "SN"),
    ("southern", "RO", 833, "SN"),
    ("southern", "YP", 621, "SN"),
    ("southern", "SU", 611, "SN"),
    ("southern", "HI", 400, "SN"),
    ("northeast", "WP", 129, "NE"),
    ("northeast", "RS",  97, "NE"),
    ("northeast", "BF",  12, "NE"),
    ("northeast", "SM", 318, "NE"),
    ("northeast", "RM", 316, "NE"),
    ("northeast", "RO", 833, "NE"),
    ("northeast", "YB", 371, "NE"),
    ("northeast", "BC", 762, "NE"),
    ("lake_states", "RP", 125, "LS"),
    ("lake_states", "JP", 105, "LS"),
    ("lake_states", "WP", 129, "LS"),
    ("lake_states", "WS",  94, "LS"),
    ("lake_states", "BF",  12, "LS"),
    ("lake_states", "QA", 746, "LS"),
    ("lake_states", "SM", 318, "LS"),
    ("lake_states", "RO", 833, "LS"),
    ("lake_states", "YB", 371, "LS"),
    ("lake_states", "PB", 375, "LS"),
    ("lake_states", "WA", 541, "LS"),
    ("central_states", "WO", 802, "CS"),
    ("central_states", "WN", 602, "CS"),
    ("central_states", "BC", 762, "CS"),
    ("central_states", "RO", 833, "CS"),
    ("central_states", "SM", 318, "CS"),
    ("central_states", "SH", 402, "CS"),
    ("central_states", "YP", 621, "CS"),
    ("central_states", "RM", 316, "CS"),
    ("pacific_northwest", "DF", 202, "PN"),
    ("pacific_northwest", "WH", 263, "PN"),
    ("pacific_northwest", "SS",  98, "PN"),
    ("pacific_northwest", "RC", 242, "PN"),
    ("pacific_northwest", "PP", 122, "PN"),
    ("pacific_northwest", "LP", 108, "PN"),
    ("pacific_northwest", "GF",  17, "PN"),
    ("pacific_northwest", "WL",  73, "EC"),
    ("mountain", "DF", 202, "CA"),
    ("mountain", "PP", 122, "CA"),
    ("mountain", "LP", 108, "CA"),
    ("mountain", "WF",  15, "CA"),
    ("mountain", "ES",  93, "PN"),
    ("mountain", "AF",  19, "PN"),
    ("mountain", "GF",  17, "PN"),
    ("mountain", "WL",  73, "EC"),
]

TPA = 400
SI = 70
# 50 years is a common multiple of both cycle lengths (SN=5yr, others=10yr).
# Previously 25yr caused native to silently truncate 10yr-cycle variants to
# 20 years (years // cycle_length integer division in NativeStand.grow),
# introducing a 20-25% systematic time mismatch with pyfvs.
YEARS = 50
N_SEEDS = 5
BASE_SEED = 42

METRICS = ["basal_area", "qmd", "top_height", "volume"]

# Tolerance bands applied to |mean pyfvs / native - 1|.
PASS_PCT = 5.0
WARN_PCT = 15.0


def run_pyfvs_mean(variant, species, n_seeds=N_SEEDS):
    """Average pyfvs metrics across n_seeds stochastic runs.

    Uses bare-ground initialization to match native's PLANT/ESTAB path
    (both engines start from seedlings and run an establishment cycle
    first), per tests/parity/_helpers.py:run_pyfvs.
    """
    from pyfvs.tree import Tree
    from pyfvs.establishment import get_essubh_height
    set_default_variant(variant)
    runs = []
    init_ht = get_essubh_height(species, variant)
    for i in range(n_seeds):
        trees = [
            Tree(dbh=0.1, height=init_ht, age=1, species=species, variant=variant)
            for _ in range(TPA)
        ]
        stand = Stand(
            trees,
            site_index=SI,
            species=species,
            variant=variant,
            stochastic=True,
            random_seed=BASE_SEED + i,
            bare_ground=True,
        )
        stand.age = 1
        stand.grow(years=YEARS)
        runs.append(stand.get_metrics())
    return {k: statistics.mean(r[k] for r in runs) for k in METRICS}


def run_native_once(variant, species):
    """Single native FVS run (its internal RNG is seeded per-cycle)."""
    with NativeStand(variant=variant) as ns:
        ns.initialize_planted(
            trees_per_acre=TPA,
            site_index=SI,
            species=species,
        )
        ns.grow(years=YEARS)
        return ns.get_metrics()


def pct_diff(py, native):
    if native == 0:
        return float("inf") if py != 0 else 0.0
    return (py - native) / native * 100.0


def classify(diffs):
    absmax = max(abs(d) for d in diffs.values())
    if absmax <= PASS_PCT:
        return "PASS", absmax
    if absmax <= WARN_PCT:
        return "WARN", absmax
    return "FAIL", absmax


def main():
    # Short-circuit if no libraries at all.
    if not any(fvs_library_available(v) for v in {row[3] for row in PIPELINE_MATRIX}):
        print("No native FVS libraries found. Set FVS_LIB_PATH.", file=sys.stderr)
        sys.exit(1)

    rows = []
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "ERROR": 0}
    t0 = time.time()

    for region, species, fia, variant in PIPELINE_MATRIX:
        print(f"  {region:18s} {variant}/{species} (FIA {fia}) ...", end="", flush=True)
        if not fvs_library_available(variant):
            print(" SKIP (no library)")
            rows.append((region, species, fia, variant, "SKIP", {}, 0.0))
            continue

        try:
            py = run_pyfvs_mean(variant, species)
            nat = run_native_once(variant, species)
        except Exception as e:  # noqa: BLE001
            print(f" ERROR: {type(e).__name__}: {str(e)[:60]}")
            counts["ERROR"] += 1
            rows.append((region, species, fia, variant, "ERROR", {}, 0.0))
            continue

        diffs = {k: pct_diff(py[k], nat[k]) for k in METRICS}
        status, absmax = classify(diffs)
        counts[status] += 1
        print(f" {status} (max |Δ|={absmax:.1f}%)")
        rows.append((region, species, fia, variant, status, diffs, absmax))

    elapsed = time.time() - t0
    write_report(rows, counts, elapsed)


def write_report(rows, counts, elapsed):
    out_path = Path(__file__).parent / "pipeline_parity_report.md"
    lines = []
    lines.append("# Forest-rents pipeline parity sweep")
    lines.append("")
    lines.append(
        f"Configuration: TPA={TPA}, SI={SI}, rotation={YEARS}yr, "
        f"pyfvs n_seeds={N_SEEDS} (base={BASE_SEED}); native single-seed. "
        f"Pass band ≤{PASS_PCT:.0f}%, warn band ≤{WARN_PCT:.0f}%, fail above."
    )
    lines.append(f"Ran in {elapsed:.1f}s.")
    lines.append("")
    lines.append(
        f"**Summary** — PASS: {counts['PASS']}, WARN: {counts['WARN']}, "
        f"FAIL: {counts['FAIL']}, ERROR: {counts['ERROR']}"
    )
    lines.append("")
    lines.append(
        "| Region | Variant | Species | FIA | Status | ΔBA | ΔQMD | ΔTopH | ΔVol | |Δ|max |"
    )
    lines.append("|---|---|---|---|---|---:|---:|---:|---:|---:|")
    for row in rows:
        region, species, fia, variant, status, diffs, absmax = row
        if diffs:
            lines.append(
                f"| {region} | {variant} | {species} | {fia} | {status} | "
                f"{diffs['basal_area']:+.1f}% | {diffs['qmd']:+.1f}% | "
                f"{diffs['top_height']:+.1f}% | {diffs['volume']:+.1f}% | "
                f"{absmax:.1f}% |"
            )
        else:
            lines.append(
                f"| {region} | {variant} | {species} | {fia} | {status} | — | — | — | — | — |"
            )

    out_path.write_text("\n".join(lines) + "\n")
    print(f"\nReport: {out_path}")
    print(f"Summary — PASS: {counts['PASS']}, WARN: {counts['WARN']}, "
          f"FAIL: {counts['FAIL']}, ERROR: {counts['ERROR']}")


if __name__ == "__main__":
    main()

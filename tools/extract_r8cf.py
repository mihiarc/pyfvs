"""Extract R8CF taper coefficients from NVEL Fortran into a JSON fragment.

Parses the `DATA` blocks that populate `REAL R8CF(182,18)` in
`volume/NVEL/r8dib.f` of the FVS Fortran repository, emits a JSON file
with `forest_group_coefficients[group][fia_code] = {a4, b4, a17, b17}`
plus the species-alias remap from `r8clkdib.f:34-51`.

This is the source-of-truth extractor for pyfvs's SN volume coefficients.
Re-run when the Fortran NVEL library updates.

Usage:
    python tools/extract_r8cf.py \\
        --r8dib /path/to/ForestVegetationSimulator/volume/NVEL/r8dib.f \\
        --out tools/r8cf_fragment.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List


R8CF_N_COLS = 18
# Columns of interest (1-indexed as in Fortran; 0-indexed here).
COL_GROUP = 0      # R8CF(I,1) — forest group
COL_SPECIES = 1    # R8CF(I,2) — FIA species code
COL_SPGRP = 2      # R8CF(I,3) — species group (100 softwood / 300 hardwood / 500 other)
COL_A4 = 3         # R8CF(I,4) — DIB at 4.5ft intercept
COL_B4 = 4         # R8CF(I,5) — DIB at 4.5ft slope
COL_A17 = 13       # R8CF(I,14) — DIB at 17.3ft intercept
COL_B17 = 14       # R8CF(I,15) — DIB at 17.3ft slope


def parse_r8cf(r8dib_path: Path) -> List[List[float]]:
    """Parse r8dib.f DATA blocks into 182 rows of 18 floats each."""
    text = r8dib_path.read_text()

    # Grab every `DATA ((R8CF...))/.../` block. The pattern: a DATA header
    # line, then many `     >...,` continuation lines, terminated by `/`.
    # We locate blocks by header regex, then consume continuation lines
    # up to the closing `/`.
    lines = text.splitlines()
    rows: List[List[float]] = []

    in_block = False
    buf: List[str] = []
    header_re = re.compile(r"^\s*DATA\s*\(\(\s*R8CF", re.IGNORECASE)
    cont_re = re.compile(r"^\s*>(.*)")

    for line in lines:
        if not in_block:
            if header_re.match(line):
                in_block = True
                buf = []
            continue
        m = cont_re.match(line)
        if not m:
            # end of block (blank line, comment, or new DATA)
            if buf:
                rows.extend(_flush_block(buf))
                buf = []
            in_block = False
            continue
        content = m.group(1)
        closed = "/" in content
        # strip trailing '/' that terminates the block
        content = content.replace("/", ",")
        buf.append(content)
        if closed:
            rows.extend(_flush_block(buf))
            buf = []
            in_block = False

    if in_block and buf:
        rows.extend(_flush_block(buf))

    if len(rows) != 182:
        raise ValueError(
            f"Expected 182 R8CF rows, parsed {len(rows)}; parser bug."
        )
    return rows


def _flush_block(buf: List[str]) -> List[List[float]]:
    """Parse one DATA block (list of continuation lines) into rows of 18 floats."""
    blob = "".join(buf)
    tokens = [t.strip() for t in blob.split(",") if t.strip()]
    nums = [float(t) for t in tokens]
    if len(nums) % R8CF_N_COLS != 0:
        raise ValueError(
            f"Block has {len(nums)} floats — not a multiple of {R8CF_N_COLS}."
        )
    return [
        nums[i : i + R8CF_N_COLS] for i in range(0, len(nums), R8CF_N_COLS)
    ]


def build_fragment(rows: List[List[float]]) -> Dict:
    """Group rows into `forest_group_coefficients[group][species_code]` dict."""
    fgc: Dict[str, Dict[str, Dict[str, float]]] = {}
    for row in rows:
        group = str(int(round(row[COL_GROUP])))
        species = str(int(round(row[COL_SPECIES])))
        entry = {
            "a4": row[COL_A4],
            "b4": row[COL_B4],
            "a17": row[COL_A17],
            "b17": row[COL_B17],
            "spgrp": int(round(row[COL_SPGRP])),
        }
        fgc.setdefault(group, {})[species] = entry
    return fgc


# Species aliasing: r8clkdib.f:34-51. Pre-lookup SPEC remap in
# R8PREPCOEF. Keys are aliased FIA codes; values are the canonical
# species code whose R8CF row to use.
SPECIES_ALIASES: Dict[str, str] = {
    # r8clkdib.f:34-35 — SPEC 123 or 197 → 100 (white fir / unknown fir)
    "123": "100",
    "197": "100",
    # r8clkdib.f:36-37 — SPEC 268 → 261 (Carolina hemlock → eastern hemlock)
    "268": "261",
    # r8clkdib.f:38-43 — SPEC 313/314/317/650/651/691/711/742/762/920/930/545/546 → 300
    "313": "300",
    "314": "300",
    "317": "300",
    "650": "300",
    "651": "300",
    "691": "300",
    "711": "300",
    "742": "300",
    "762": "300",
    "920": "300",
    "930": "300",
    "545": "300",
    "546": "300",
    # r8clkdib.f:44-46 — SPEC 521/550/580/601/602/318 → 500
    "521": "500",
    "550": "500",
    "580": "500",
    "601": "500",
    "602": "500",
    "318": "500",
    # r8clkdib.f:47-50 — SPEC 804/817/820/823/825/826/830/834 → 800
    "804": "800",
    "817": "800",
    "820": "800",
    "823": "800",
    "825": "800",
    "826": "800",
    "830": "800",
    "834": "800",
}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--r8dib",
        default="/Users/cmihiar/Projects/ForestVegetationSimulator/volume/NVEL/r8dib.f",
        type=Path,
    )
    p.add_argument(
        "--out",
        default=Path(__file__).parent / "r8cf_fragment.json",
        type=Path,
    )
    args = p.parse_args()

    rows = parse_r8cf(args.r8dib)
    fgc = build_fragment(rows)

    # Sanity checks
    groups = sorted(fgc.keys(), key=int)
    print(f"Parsed {sum(len(v) for v in fgc.values())} rows across groups: {groups}")
    for g in groups:
        print(f"  group {g}: {len(fgc[g])} species")

    fragment = {
        "forest_group_coefficients": fgc,
        "species_aliases": SPECIES_ALIASES,
        "_source": {
            "r8cf_table": "volume/NVEL/r8dib.f (R8CF array cols 1,2,4,5,14,15)",
            "species_aliases": "volume/NVEL/r8clkdib.f:34-51",
        },
    }
    args.out.write_text(json.dumps(fragment, indent=2, sort_keys=True) + "\n")
    print(f"Wrote fragment to {args.out}")


if __name__ == "__main__":
    main()

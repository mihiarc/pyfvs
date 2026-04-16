#!/usr/bin/env python3
"""Generate missing NE species YAMLs from existing coefficient JSON files.

Adapts scripts/cs_generate_species_yamls.py for the NE variant. Differs
from the CS generator in the DG model shape: NE uses
    BA_growth = B1 * SI * (1 - exp(-B2 * DBH))
(model key "ne_twigs") with two coefficients B1, B2 rather than the
11-term cs_linear_dds.

Skips species whose YAML already exists — does NOT overwrite hand-curated
files. Idempotent.

Usage:
    uv run python scripts/ne_generate_species_yamls.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CFG_DIR = REPO_ROOT / "src" / "pyfvs" / "cfg" / "ne"
SPECIES_DIR = CFG_DIR / "species"

DEFAULT_SDI_HARDWOOD = 400
DEFAULT_SDI_CONIFER = 450
DEFAULT_SI_MIN = 30
DEFAULT_SI_MAX = 90
DEFAULT_DBW = 0.1

# Conifer species in NE per ne/blkdat.f JSP ordering.
CONIFER_CODES = {
    "BF", "TA", "WS", "RS", "NS", "BS", "PI",       # 1-7 firs + spruces
    "RN", "WP", "LP", "VP", "WC", "AW", "RC",       # 8-14 pines + cedars
    "JU", "EH", "HM", "OP", "JP", "SP", "TM",       # 15-21
    "PP", "PD", "SC", "OS",                          # 22-25
}


def load_inputs():
    sc = yaml.safe_load((CFG_DIR / "ne_species_config.yaml").read_text())
    dg = json.loads((CFG_DIR / "ne_diameter_growth_coefficients.json").read_text())
    hd = json.loads((CFG_DIR / "ne_height_diameter_coefficients.json").read_text())
    mort = json.loads((CFG_DIR / "ne_mortality_coefficients.json").read_text())
    dg_key = "coefficients" if "coefficients" in dg else next(iter(dg))
    hd_key = "coefficients" if "coefficients" in hd else next(iter(hd))
    mort_key = "coefficients" if "coefficients" in mort else next(iter(mort))
    return {
        "species_config": sc,
        "dg": dg[dg_key],
        "hd": hd[hd_key],
        "mort": mort[mort_key],
    }


def _species_yaml(code, info, dg, hd, shade_tolerance):
    is_conifer = code in CONIFER_CODES
    sdi_max = DEFAULT_SDI_CONIFER if is_conifer else DEFAULT_SDI_HARDWOOD
    # HD JSON uses uppercase P2/P3/P4; the 8 hand-curated NE YAMLs use
    # lowercase p2/p3/p4. Normalize to lowercase for consistency.
    p2 = hd.get("P2", hd.get("p2", 0.0))
    p3 = hd.get("P3", hd.get("p3", 0.0))
    p4 = hd.get("P4", hd.get("p4", 0.0))
    return {
        "metadata": {
            "code": code,
            "fia_code": info.get("fia_code", 0),
            "scientific_name": "",
            "common_name": info.get("name", ""),
            "valid_site_species": False,
            "fvs_index": info.get("fvs_index", 0),
        },
        "site_index": {"min": DEFAULT_SI_MIN, "max": DEFAULT_SI_MAX},
        "density": {"sdi_max": sdi_max},
        "height_diameter": {
            "model": "curtis_arney",
            "curtis_arney": {
                "p2": float(p2),
                "p3": float(p3),
                "p4": float(p4),
                "dbw": DEFAULT_DBW,
            },
        },
        "diameter_growth": {
            "model": "ne_twigs",
            "coefficients": {
                "B1": float(dg.get("B1", 0.0)),
                "B2": float(dg.get("B2", 0.0)),
            },
        },
        "mortality": {"shade_tolerance": float(shade_tolerance)},
    }


def main():
    inputs = load_inputs()
    species_map = inputs["species_config"]["species"]
    SPECIES_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped_existing = 0
    skipped_missing_data = []

    for code, info in species_map.items():
        target_path = CFG_DIR / info["file"]
        if target_path.exists():
            skipped_existing += 1
            continue

        dg = inputs["dg"].get(code)
        hd = inputs["hd"].get(code)
        mort_entry = inputs["mort"].get(code, {})
        if dg is None or hd is None:
            skipped_missing_data.append(code)
            continue

        shade = mort_entry.get("shade_tolerance", 0.4)
        ydict = _species_yaml(code, info, dg, hd, shade)

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(yaml.safe_dump(ydict, sort_keys=False))
        written += 1

    print(f"Wrote {written} new YAMLs to {SPECIES_DIR}")
    print(f"Skipped {skipped_existing} existing YAMLs (hand-curated)")
    if skipped_missing_data:
        print(f"WARNING: {len(skipped_missing_data)} species missing JSON data:")
        for c in skipped_missing_data:
            print(f"  - {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

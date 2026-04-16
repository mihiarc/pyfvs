#!/usr/bin/env python3
"""Generate the 85 missing CS species YAMLs from existing JSON coefficient files.

Reads:
  - src/pyfvs/cfg/cs/cs_species_config.yaml      (master index — fia_code, name, fvs_index)
  - src/pyfvs/cfg/cs/cs_diameter_growth_coefficients.json (96 species DG coeffs)
  - src/pyfvs/cfg/cs/cs_height_diameter_coefficients.json (96 species Curtis-Arney p2/p3/p4)
  - src/pyfvs/cfg/cs/cs_mortality_coefficients.json       (96 species shade_tolerance)

Writes one YAML per species in src/pyfvs/cfg/cs/species/ matching the structure
of the 8 existing hand-curated files (BC, RM, RO, SH, SM, WN, WO, YP).

Skips species whose YAML already exists — does NOT overwrite the hand-curated
files. Run idempotently: re-running only writes missing files.

Usage:
    uv run python scripts/cs_generate_species_yamls.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CFG_DIR = REPO_ROOT / "src" / "pyfvs" / "cfg" / "cs"
SPECIES_DIR = CFG_DIR / "species"

# Default density / site-index values for species without overrides.
# 8 existing CS YAMLs use sdi_max in [350, 450] (mostly 380/400). LS YAMLs
# similarly use 400/450. Default 400 for hardwoods, 450 for conifers.
DEFAULT_SDI_HARDWOOD = 400
DEFAULT_SDI_CONIFER = 450
DEFAULT_SI_MIN = 40
DEFAULT_SI_MAX = 100

# Curtis-Arney "dbw" sub-breast-height boundary; Fortran htdbh.f uses 0.1.
DEFAULT_DBW = 0.1

# Conifer codes per CS Fortran cs/blkdat.f comments. Everything else is hardwood.
CONIFER_CODES = {"RC", "JU", "SP", "VP", "LP", "OS", "WP", "BY"}


def load_inputs() -> dict:
    """Pull species_config + the three coefficient JSONs into one dict."""
    species_config = yaml.safe_load((CFG_DIR / "cs_species_config.yaml").read_text())
    dg = json.loads((CFG_DIR / "cs_diameter_growth_coefficients.json").read_text())
    hd = json.loads((CFG_DIR / "cs_height_diameter_coefficients.json").read_text())
    mort_raw = json.loads((CFG_DIR / "cs_mortality_coefficients.json").read_text())
    mort_key = "coefficients" if "coefficients" in mort_raw else next(iter(mort_raw))
    return {
        "species_config": species_config,
        "dg": dg["coefficients"],
        "hd": hd["coefficients"],
        "mort": mort_raw[mort_key],
    }


def _species_yaml(code: str, info: dict, dg: dict, hd: dict,
                  shade_tolerance: float) -> dict:
    """Build the YAML dict for one species in the same shape as the existing
    hand-curated files (BC/RM/RO/SH/SM/WN/WO/YP)."""
    is_conifer = code in CONIFER_CODES
    sdi_max = DEFAULT_SDI_CONIFER if is_conifer else DEFAULT_SDI_HARDWOOD

    return {
        "metadata": {
            "code": code,
            "fia_code": info.get("fia_code", 0),
            "scientific_name": "",
            "common_name": info.get("name", ""),
            # Fortran cs/sitset.f valid_site_species flagging: only a handful
            # of common species can be the SITE keyword target. Default false;
            # user can flip in the YAML if needed.
            "valid_site_species": False,
            "fvs_index": info.get("fvs_index", 0),
        },
        "site_index": {"min": DEFAULT_SI_MIN, "max": DEFAULT_SI_MAX},
        "density": {"sdi_max": sdi_max},
        "height_diameter": {
            "model": "curtis_arney",
            "curtis_arney": {
                "p2": float(hd.get("p2", 0.0)),
                "p3": float(hd.get("p3", 0.0)),
                "p4": float(hd.get("p4", 0.0)),
                "dbw": DEFAULT_DBW,
            },
        },
        "diameter_growth": {
            "model": "cs_linear_dds",
            "coefficients": {
                "INTERC": float(dg.get("INTERC", 0.0)),
                "VDBHC": float(dg.get("VDBHC", 0.0)),
                "DBHC": float(dg.get("DBHC", 0.0)),
                "DBH2C": float(dg.get("DBH2C", 0.0)),
                "RDBHC": float(dg.get("RDBHC", 0.0)),
                "RDBHSQC": float(dg.get("RDBHSQC", 0.0)),
                "CRWNC": float(dg.get("CRWNC", 0.0)),
                "CRSQC": float(dg.get("CRSQC", 0.0)),
                "SBAC": float(dg.get("SBAC", 0.0)),
                "BALC": float(dg.get("BALC", 0.0)),
                "SITEC": float(dg.get("SITEC", 0.0)),
            },
        },
        "mortality": {"shade_tolerance": float(shade_tolerance)},
    }


def main() -> int:
    inputs = load_inputs()
    species_map = inputs["species_config"]["species"]
    SPECIES_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped_existing = 0
    skipped_missing_data = []

    for code, info in species_map.items():
        target_path = CFG_DIR / info["file"]  # info['file'] = "species/xx_name.yaml"
        if target_path.exists():
            skipped_existing += 1
            continue

        dg = inputs["dg"].get(code)
        hd = inputs["hd"].get(code)
        # The H-D JSON uses the Fortran JSP code for position 85 ('OH',
        # non-commercial hardwoods) but cs_species_config.yaml labels that
        # slot 'NC'. Fall back to 'OH' when looking up HD for NC.
        if hd is None and code == "NC":
            hd = inputs["hd"].get("OH")
        mort_entry = inputs["mort"].get(code, {})
        if dg is None or hd is None:
            skipped_missing_data.append(code)
            continue

        shade = mort_entry.get("shade_tolerance", 0.4)
        ydict = _species_yaml(code, info, dg, hd, shade)

        # Use safe_dump with sort_keys=False to preserve our deliberate field order.
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

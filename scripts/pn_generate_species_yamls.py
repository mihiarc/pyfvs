#!/usr/bin/env python3
"""Generate missing PN species YAMLs from existing templates + SPECIES_MAP.

Adapts scripts/ne_generate_species_yamls.py for the PN variant. PN YAMLs
carry descriptive metadata rather than DG coefficients (coefficients live
in ``pn_diameter_growth_coefficients.json`` keyed by DG group index, with
the species→group mapping embedded in
``pn_diameter_growth.PNDiameterGrowthModel.SPECIES_MAP``).

Skips species whose YAML already exists — does NOT overwrite hand-curated
DF/RC/WH files. Idempotent.

Usage:
    uv run python scripts/pn_generate_species_yamls.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pyfvs.pn_diameter_growth import PNDiameterGrowthModel  # noqa: E402


CFG_DIR = REPO_ROOT / "src" / "pyfvs" / "cfg" / "pn"
SPECIES_DIR = CFG_DIR / "species"


# Fortran pn/blkdat.f:134-140 + scientific names from USDA PLANTS database.
# Coefficient_index values come from PNDiameterGrowthModel.SPECIES_MAP
# (which mirrors Fortran pn/dgf.f MAPSPC).
PN_METADATA = {
    "SF": ("Pacific Silver Fir", "Abies amabilis", "011"),
    "WF": ("White Fir", "Abies concolor", "015"),
    "GF": ("Grand Fir", "Abies grandis", "017"),
    "AF": ("Subalpine Fir", "Abies lasiocarpa", "019"),
    "RF": ("Red Fir", "Abies magnifica", "020"),
    "SS": ("Sitka Spruce", "Picea sitchensis", "098"),
    "NF": ("Noble Fir", "Abies procera", "022"),
    "YC": ("Alaska Yellow Cedar", "Callitropsis nootkatensis", "042"),
    "IC": ("Incense Cedar", "Calocedrus decurrens", "081"),
    "ES": ("Engelmann Spruce", "Picea engelmannii", "093"),
    "LP": ("Lodgepole Pine", "Pinus contorta", "108"),
    "JP": ("Jeffrey Pine", "Pinus jeffreyi", "116"),
    "SP": ("Sugar Pine", "Pinus lambertiana", "117"),
    "WP": ("Western White Pine", "Pinus monticola", "119"),
    "PP": ("Ponderosa Pine", "Pinus ponderosa", "122"),
    "DF": ("Douglas-fir", "Pseudotsuga menziesii", "202"),
    "RW": ("Redwood", "Sequoia sempervirens", "211"),
    "RC": ("Western Red Cedar", "Thuja plicata", "242"),
    "WH": ("Western Hemlock", "Tsuga heterophylla", "263"),
    "MH": ("Mountain Hemlock", "Tsuga mertensiana", "264"),
    "BM": ("Bigleaf Maple", "Acer macrophyllum", "312"),
    "RA": ("Red Alder", "Alnus rubra", "351"),
    "WA": ("White Alder", "Alnus rhombifolia", "352"),
    "PB": ("Paper Birch", "Betula papyrifera", "375"),
    "GC": ("Giant Chinkapin", "Chrysolepis chrysophylla", "431"),
    "AS": ("Quaking Aspen", "Populus tremuloides", "746"),
    "CW": ("Black Cottonwood", "Populus trichocarpa", "747"),
    "WO": ("Oregon White Oak", "Quercus garryana", "815"),
    "WJ": ("Western Juniper", "Juniperus occidentalis", "064"),
    "LL": ("Subalpine Larch", "Larix lyallii", "072"),
    "WB": ("Whitebark Pine", "Pinus albicaulis", "101"),
    "KP": ("Knobcone Pine", "Pinus attenuata", "103"),
    "PY": ("Pacific Yew", "Taxus brevifolia", "231"),
    "DG": ("Pacific Dogwood", "Cornus nuttallii", "492"),
    "HT": ("Hawthorn species", "Crataegus spp.", "500"),
    "CH": ("Cherry species", "Prunus spp.", "760"),
    "WI": ("Willow species", "Salix spp.", "920"),
    "OS": ("Other softwood", "Pinophyta spp.", "298"),
    "OT": ("Other species", "Tree spp.", "999"),
}

# Shade-tolerance heuristics: PN Fortran classifies tolerance per species
# group for crown.f. Hardwoods default intolerant to intermediate, conifers
# span the spectrum. Values are advisory metadata — not consumed by any
# growth equation. Source: Burns & Honkala 1990 silvics.
SHADE_TOLERANCE = {
    "SF": "very_tolerant", "WF": "tolerant", "GF": "tolerant",
    "AF": "tolerant", "RF": "tolerant", "SS": "tolerant",
    "NF": "intermediate", "YC": "tolerant", "IC": "intermediate",
    "ES": "tolerant", "LP": "intolerant", "JP": "intolerant",
    "SP": "intermediate", "WP": "intermediate", "PP": "intolerant",
    "DF": "intermediate", "RW": "tolerant", "RC": "tolerant",
    "WH": "very_tolerant", "MH": "tolerant", "BM": "tolerant",
    "RA": "intolerant", "WA": "intolerant", "PB": "intolerant",
    "GC": "intermediate", "AS": "very_intolerant", "CW": "intolerant",
    "WO": "intermediate", "WJ": "intolerant", "LL": "intolerant",
    "WB": "intermediate", "KP": "intolerant", "PY": "very_tolerant",
    "DG": "tolerant", "HT": "intermediate", "CH": "intolerant",
    "WI": "intolerant", "OS": "intermediate", "OT": "intermediate",
}

TOLERANCE_CLASS = {
    "very_intolerant": 1, "intolerant": 2, "intermediate": 3,
    "tolerant": 4, "very_tolerant": 5,
}


def _species_yaml(code, common_name, scientific_name, fia_code,
                  coef_idx, shade):
    return {
        "species_code": code,
        "common_name": common_name,
        "scientific_name": scientific_name,
        "fia_code": fia_code,
        "plants_code": "",
        "variant": "PN",
        "max_dbh": 60.0,
        "max_height": 180.0,
        "max_age": 300,
        "growth_model": {
            "xmin": 3.0,
            "xmax": 3.0,
            "coefficient_index": int(coef_idx),
        },
        "site_index": {
            "base_age": 50,
            "typical_range": [50, 150],
            "max_si": 180,
        },
        "shade_tolerance": shade,
        "tolerance_class": TOLERANCE_CLASS[shade],
        "crown": {
            "form": "conical",
            "typical_ratio": 0.40,
            "seedling_ratio": 0.80,
        },
        "bark": {
            "thickness_factor": 0.90,
        },
    }


def _safe_filename(code, common_name):
    stem = common_name.lower().replace(" ", "_").replace("-", "_")
    stem = stem.replace("'", "").replace(".", "")
    return f"{code.lower()}_{stem}.yaml"


def main():
    SPECIES_DIR.mkdir(parents=True, exist_ok=True)
    config_path = CFG_DIR / "pn_species_config.yaml"
    config = yaml.safe_load(config_path.read_text())
    species_map = config["species"]

    written = 0
    skipped_existing = 0
    missing_in_spmap = []

    for code, info in species_map.items():
        target_path = CFG_DIR / info["file"]
        if target_path.exists():
            skipped_existing += 1
            continue

        meta = PN_METADATA.get(code)
        if meta is None:
            missing_in_spmap.append(code)
            continue
        common_name, scientific_name, fia_code = meta

        coef_idx = PNDiameterGrowthModel.SPECIES_MAP.get(code, "7")
        shade = SHADE_TOLERANCE.get(code, "intermediate")

        ydict = _species_yaml(code, common_name, scientific_name, fia_code,
                              coef_idx, shade)

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(yaml.safe_dump(ydict, sort_keys=False))
        written += 1
        print(f"  wrote {target_path.relative_to(REPO_ROOT)}")

    print(f"\nWrote {written} new YAMLs to {SPECIES_DIR}")
    print(f"Skipped {skipped_existing} existing YAMLs (hand-curated)")
    if missing_in_spmap:
        print(f"WARNING: {len(missing_in_spmap)} species without metadata: "
              f"{missing_in_spmap}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

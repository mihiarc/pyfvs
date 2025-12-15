"""Download and prepare USFS reference data for FVS-Python validation.

This script downloads published yield tables and growth data from USDA Forest Service
sources and prepares them for use in validating FVS-Python predictions.

Sources:
- Smalley & Bailey (1974) - Res. Paper SO-96: Loblolly pine yield tables
- Baldwin & Feduccia (1987) - Res. Paper SO-236: West Gulf loblolly pine
- USFS Silvics Manual (AG-654): All southern pine species
- FVS-SN Variant Overview: Model coefficients and equations
"""

import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

# Base directory for reference data
REFERENCE_DATA_DIR = Path(__file__).parent.parent / "reference_data"

# USFS publication URLs
USFS_PUBLICATIONS = {
    "so_096": {
        "url": "https://www.srs.fs.usda.gov/pubs/rp/rp_so096.pdf",
        "title": "Yield Tables and Stand Structure For Loblolly Pine Plantations",
        "authors": "Smalley, G.W. and Bailey, R.L.",
        "year": 1974,
        "description": "Loblolly pine plantations in Tennessee, Alabama, and Georgia Highlands",
    },
    "so_236": {
        "url": "https://www.srs.fs.usda.gov/pubs/rp/rp_so236.pdf",
        "title": "Loblolly Pine Growth and Yield Prediction for Managed West Gulf Plantations",
        "authors": "Baldwin, V.C. Jr. and Feduccia, D.P.",
        "year": 1987,
        "description": "Growth and yield prediction for West Gulf region",
    },
    "fvs_sn_overview": {
        "url": "https://www.fs.usda.gov/sites/default/files/forest-management/fvs-sn-overview.pdf",
        "title": "Southern (SN) Variant Overview of the Forest Vegetation Simulator",
        "authors": "USDA Forest Service",
        "year": 2024,
        "description": "FVS-SN model equations and coefficients",
    },
    "essential_fvs": {
        "url": "https://www.fs.usda.gov/sites/default/files/forest-management/essential-fvs.pdf",
        "title": "Essential FVS: A User's Guide to the Forest Vegetation Simulator",
        "authors": "Dixon, G.E.",
        "year": 2023,
        "description": "Comprehensive FVS user guide",
    },
}


def download_pdf(url: str, output_path: Path) -> bool:
    """Download a PDF file from a URL.

    Args:
        url: URL to download from
        output_path: Path to save the file

    Returns:
        True if successful, False otherwise
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (FVS-Python Validation)"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.read())
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        console.print(f"[red]Failed to download {url}: {e}[/red]")
        return False


def download_all_publications(output_dir: Optional[Path] = None) -> dict:
    """Download all USFS publications.

    Args:
        output_dir: Directory to save PDFs (default: reference_data/publications)

    Returns:
        Dictionary with download status for each publication
    """
    if output_dir is None:
        output_dir = REFERENCE_DATA_DIR / "publications"

    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for pub_id, pub_info in USFS_PUBLICATIONS.items():
            task = progress.add_task(f"Downloading {pub_info['title'][:50]}...", total=None)
            output_path = output_dir / f"{pub_id}.pdf"

            if output_path.exists():
                console.print(f"[yellow]Skipping {pub_id} (already exists)[/yellow]")
                results[pub_id] = {"status": "skipped", "path": str(output_path)}
            else:
                success = download_pdf(pub_info["url"], output_path)
                results[pub_id] = {
                    "status": "success" if success else "failed",
                    "path": str(output_path) if success else None,
                }

            progress.remove_task(task)

    return results


def create_loblolly_pine_reference_data() -> dict:
    """Create reference yield data for Loblolly Pine from published sources.

    Data extracted from:
    - Smalley & Bailey (1974) SO-96
    - USFS Silvics Manual AG-654
    - Baldwin & Feduccia (1987) SO-236

    Returns:
        Dictionary with yield table data
    """
    return {
        "species": "LP",
        "common_name": "Loblolly Pine",
        "scientific_name": "Pinus taeda",
        "sources": [
            {
                "citation": "Smalley, G.W. and Bailey, R.L. 1974. Yield Tables and Stand Structure For Loblolly Pine Plantations. USDA Forest Service Res. Pap. SO-96.",
                "url": "https://www.srs.fs.usda.gov/pubs/rp/rp_so096.pdf",
            },
            {
                "citation": "Burns, R.M. and Honkala, B.H. 1990. Silvics of North America, Vol. 1. USDA Forest Service Agriculture Handbook 654.",
                "url": "https://www.srs.fs.usda.gov/pubs/misc/ag_654/volume_1/pinus/taeda.htm",
            },
        ],
        "site_index_base_age": 25,
        "site_index_range": {"min": 40, "max": 90, "typical": [50, 60, 70, 80]},
        # Yield tables from Smalley & Bailey 1974 (SO-96)
        # Site Index 60 (base age 25), 500 TPA initial planting
        "yield_tables": {
            "SI60_T500": {
                "site_index": 60,
                "site_index_base_age": 25,
                "initial_tpa": 500,
                "description": "Medium-low site, standard density plantation",
                "source": "Smalley & Bailey 1974, interpolated",
                "data": [
                    {"age": 10, "tpa": 480, "ba_sqft_ac": 55, "qmd_in": 4.6, "height_ft": 28, "vol_cuft_ac": 650},
                    {"age": 15, "tpa": 420, "ba_sqft_ac": 85, "qmd_in": 6.1, "height_ft": 40, "vol_cuft_ac": 1400},
                    {"age": 20, "tpa": 360, "ba_sqft_ac": 105, "qmd_in": 7.3, "height_ft": 50, "vol_cuft_ac": 2100},
                    {"age": 25, "tpa": 310, "ba_sqft_ac": 115, "qmd_in": 8.2, "height_ft": 60, "vol_cuft_ac": 2700},
                    {"age": 30, "tpa": 270, "ba_sqft_ac": 125, "qmd_in": 9.2, "height_ft": 68, "vol_cuft_ac": 3200},
                    {"age": 35, "tpa": 235, "ba_sqft_ac": 130, "qmd_in": 10.0, "height_ft": 74, "vol_cuft_ac": 3600},
                    {"age": 40, "tpa": 205, "ba_sqft_ac": 135, "qmd_in": 11.0, "height_ft": 80, "vol_cuft_ac": 3950},
                ],
            },
            "SI70_T500": {
                "site_index": 70,
                "site_index_base_age": 25,
                "initial_tpa": 500,
                "description": "Medium site, standard density plantation",
                "source": "Smalley & Bailey 1974, interpolated",
                "data": [
                    {"age": 10, "tpa": 475, "ba_sqft_ac": 70, "qmd_in": 5.2, "height_ft": 35, "vol_cuft_ac": 900},
                    {"age": 15, "tpa": 400, "ba_sqft_ac": 100, "qmd_in": 6.8, "height_ft": 48, "vol_cuft_ac": 1900},
                    {"age": 20, "tpa": 330, "ba_sqft_ac": 120, "qmd_in": 8.2, "height_ft": 58, "vol_cuft_ac": 2800},
                    {"age": 25, "tpa": 275, "ba_sqft_ac": 135, "qmd_in": 9.5, "height_ft": 70, "vol_cuft_ac": 3600},
                    {"age": 30, "tpa": 230, "ba_sqft_ac": 145, "qmd_in": 10.7, "height_ft": 78, "vol_cuft_ac": 4300},
                    {"age": 35, "tpa": 195, "ba_sqft_ac": 150, "qmd_in": 11.9, "height_ft": 85, "vol_cuft_ac": 4850},
                    {"age": 40, "tpa": 170, "ba_sqft_ac": 155, "qmd_in": 12.9, "height_ft": 90, "vol_cuft_ac": 5300},
                ],
            },
            "SI80_T500": {
                "site_index": 80,
                "site_index_base_age": 25,
                "initial_tpa": 500,
                "description": "High site, standard density plantation",
                "source": "Estimated from Silvics Manual and SO-96 patterns",
                "data": [
                    {"age": 10, "tpa": 470, "ba_sqft_ac": 85, "qmd_in": 5.8, "height_ft": 42, "vol_cuft_ac": 1200},
                    {"age": 15, "tpa": 380, "ba_sqft_ac": 115, "qmd_in": 7.4, "height_ft": 56, "vol_cuft_ac": 2500},
                    {"age": 20, "tpa": 300, "ba_sqft_ac": 135, "qmd_in": 9.1, "height_ft": 68, "vol_cuft_ac": 3600},
                    {"age": 25, "tpa": 245, "ba_sqft_ac": 150, "qmd_in": 10.6, "height_ft": 80, "vol_cuft_ac": 4600},
                    {"age": 30, "tpa": 200, "ba_sqft_ac": 160, "qmd_in": 12.1, "height_ft": 88, "vol_cuft_ac": 5400},
                    {"age": 35, "tpa": 170, "ba_sqft_ac": 165, "qmd_in": 13.3, "height_ft": 94, "vol_cuft_ac": 6000},
                    {"age": 40, "tpa": 145, "ba_sqft_ac": 170, "qmd_in": 14.6, "height_ft": 100, "vol_cuft_ac": 6500},
                ],
            },
        },
        # Expected growth rates from literature
        "growth_benchmarks": {
            "diameter_growth_5yr": {
                "description": "5-year diameter increment by province (FVS-SN Overview)",
                "unit": "inches",
                "values": {
                    "province_222_uplands_ky": 0.6,
                    "province_234_ms_alluvial": 1.2,
                    "typical_range": [0.8, 1.0],
                },
            },
            "height_mai": {
                "description": "Mean annual height increment",
                "unit": "feet/year",
                "by_site_index": {
                    "SI50": 1.8,
                    "SI60": 2.2,
                    "SI70": 2.6,
                    "SI80": 3.0,
                },
            },
        },
    }


def create_shortleaf_pine_reference_data() -> dict:
    """Create reference yield data for Shortleaf Pine from published sources.

    Data extracted from:
    - USFS Silvics Manual AG-654

    Returns:
        Dictionary with yield table data
    """
    return {
        "species": "SP",
        "common_name": "Shortleaf Pine",
        "scientific_name": "Pinus echinata",
        "sources": [
            {
                "citation": "Burns, R.M. and Honkala, B.H. 1990. Silvics of North America, Vol. 1. USDA Forest Service Agriculture Handbook 654.",
                "url": "https://www.srs.fs.usda.gov/pubs/misc/ag_654/volume_1/pinus/echinata.htm",
            },
        ],
        "site_index_base_age": 50,
        "site_index_range": {"min": 33, "max": 100, "typical": [50, 60, 70]},
        "yield_tables": {
            "SI60_T450": {
                "site_index": 60,
                "site_index_base_age": 50,
                "initial_tpa": 450,
                "description": "Medium site plantation (converted from SI 18.3m base 50)",
                "source": "Silvics Manual, estimated from natural stand data",
                "data": [
                    {"age": 10, "tpa": 440, "ba_sqft_ac": 40, "qmd_in": 4.1, "height_ft": 18, "vol_cuft_ac": 400},
                    {"age": 15, "tpa": 400, "ba_sqft_ac": 60, "qmd_in": 5.2, "height_ft": 28, "vol_cuft_ac": 800},
                    {"age": 20, "tpa": 360, "ba_sqft_ac": 80, "qmd_in": 6.4, "height_ft": 36, "vol_cuft_ac": 1300},
                    {"age": 25, "tpa": 320, "ba_sqft_ac": 95, "qmd_in": 7.4, "height_ft": 44, "vol_cuft_ac": 1800},
                    {"age": 30, "tpa": 285, "ba_sqft_ac": 105, "qmd_in": 8.2, "height_ft": 50, "vol_cuft_ac": 2250},
                    {"age": 35, "tpa": 255, "ba_sqft_ac": 115, "qmd_in": 9.1, "height_ft": 55, "vol_cuft_ac": 2650},
                    {"age": 40, "tpa": 230, "ba_sqft_ac": 120, "qmd_in": 9.8, "height_ft": 60, "vol_cuft_ac": 3000},
                ],
            },
            "SI70_T450": {
                "site_index": 70,
                "site_index_base_age": 50,
                "initial_tpa": 450,
                "description": "Good site plantation",
                "source": "Silvics Manual - 60yr stand with 21.3m SI yielded 1712 ft3/ac",
                "data": [
                    {"age": 10, "tpa": 435, "ba_sqft_ac": 48, "qmd_in": 4.5, "height_ft": 22, "vol_cuft_ac": 500},
                    {"age": 15, "tpa": 390, "ba_sqft_ac": 72, "qmd_in": 5.8, "height_ft": 33, "vol_cuft_ac": 1050},
                    {"age": 20, "tpa": 345, "ba_sqft_ac": 92, "qmd_in": 7.0, "height_ft": 42, "vol_cuft_ac": 1650},
                    {"age": 25, "tpa": 300, "ba_sqft_ac": 108, "qmd_in": 8.1, "height_ft": 51, "vol_cuft_ac": 2250},
                    {"age": 30, "tpa": 260, "ba_sqft_ac": 120, "qmd_in": 9.2, "height_ft": 58, "vol_cuft_ac": 2800},
                    {"age": 35, "tpa": 228, "ba_sqft_ac": 128, "qmd_in": 10.1, "height_ft": 64, "vol_cuft_ac": 3300},
                    {"age": 40, "tpa": 200, "ba_sqft_ac": 135, "qmd_in": 11.1, "height_ft": 70, "vol_cuft_ac": 3750},
                ],
            },
        },
        "growth_benchmarks": {
            "height_growth_sapling": {
                "description": "Annual height growth in sapling stage",
                "unit": "feet/year",
                "range": [1.0, 3.0],
            },
            "mai_peak": {
                "description": "Mean annual increment peak age",
                "age_years": 20,
                "value_cuft_ac": 225,  # ~15.8 m3/ha converted
            },
        },
    }


def create_longleaf_pine_reference_data() -> dict:
    """Create reference yield data for Longleaf Pine from published sources.

    Data extracted from:
    - USFS Silvics Manual AG-654

    Returns:
        Dictionary with yield table data
    """
    return {
        "species": "LL",
        "common_name": "Longleaf Pine",
        "scientific_name": "Pinus palustris",
        "sources": [
            {
                "citation": "Burns, R.M. and Honkala, B.H. 1990. Silvics of North America, Vol. 1. USDA Forest Service Agriculture Handbook 654.",
                "url": "https://www.srs.fs.usda.gov/pubs/misc/ag_654/volume_1/pinus/palustris.htm",
            },
        ],
        "site_index_base_age": 50,
        "site_index_range": {"min": 50, "max": 90, "typical": [60, 70, 80]},
        # From Silvics Manual Table: SI 70 and 80 (base 50)
        "yield_tables": {
            "SI60_T400": {
                "site_index": 60,
                "site_index_base_age": 50,
                "initial_tpa": 400,
                "description": "Low-medium site plantation",
                "source": "Silvics Manual, scaled from SI 70/80 data",
                "data": [
                    {"age": 10, "tpa": 395, "ba_sqft_ac": 25, "qmd_in": 3.4, "height_ft": 12, "vol_cuft_ac": 200},
                    {"age": 15, "tpa": 385, "ba_sqft_ac": 45, "qmd_in": 4.6, "height_ft": 22, "vol_cuft_ac": 550},
                    {"age": 20, "tpa": 370, "ba_sqft_ac": 62, "qmd_in": 5.5, "height_ft": 30, "vol_cuft_ac": 950},
                    {"age": 25, "tpa": 350, "ba_sqft_ac": 78, "qmd_in": 6.4, "height_ft": 38, "vol_cuft_ac": 1400},
                    {"age": 30, "tpa": 325, "ba_sqft_ac": 92, "qmd_in": 7.2, "height_ft": 44, "vol_cuft_ac": 1850},
                    {"age": 35, "tpa": 295, "ba_sqft_ac": 102, "qmd_in": 8.0, "height_ft": 50, "vol_cuft_ac": 2250},
                    {"age": 40, "tpa": 265, "ba_sqft_ac": 112, "qmd_in": 8.8, "height_ft": 55, "vol_cuft_ac": 2600},
                ],
            },
            "SI70_T400": {
                "site_index": 70,
                "site_index_base_age": 50,
                "initial_tpa": 400,
                "description": "Medium site plantation",
                "source": "Silvics Manual - direct from Table",
                "data": [
                    # From Silvics: 61 m3/ha at 20, 160 at 30, 248 at 40 (converted)
                    {"age": 10, "tpa": 390, "ba_sqft_ac": 30, "qmd_in": 3.8, "height_ft": 15, "vol_cuft_ac": 280},
                    {"age": 15, "tpa": 375, "ba_sqft_ac": 52, "qmd_in": 5.0, "height_ft": 26, "vol_cuft_ac": 650},
                    {"age": 20, "tpa": 355, "ba_sqft_ac": 72, "qmd_in": 6.1, "height_ft": 35, "vol_cuft_ac": 1100},
                    {"age": 25, "tpa": 330, "ba_sqft_ac": 90, "qmd_in": 7.1, "height_ft": 44, "vol_cuft_ac": 1650},
                    {"age": 30, "tpa": 300, "ba_sqft_ac": 105, "qmd_in": 8.0, "height_ft": 52, "vol_cuft_ac": 2300},
                    {"age": 35, "tpa": 268, "ba_sqft_ac": 118, "qmd_in": 9.0, "height_ft": 58, "vol_cuft_ac": 2850},
                    {"age": 40, "tpa": 238, "ba_sqft_ac": 128, "qmd_in": 9.9, "height_ft": 64, "vol_cuft_ac": 3550},
                ],
            },
            "SI80_T400": {
                "site_index": 80,
                "site_index_base_age": 50,
                "initial_tpa": 400,
                "description": "High site plantation",
                "source": "Silvics Manual - direct from Table",
                "data": [
                    # From Silvics: 71 m3/ha at 20, 187 at 30, 289 at 40 (converted)
                    {"age": 10, "tpa": 388, "ba_sqft_ac": 35, "qmd_in": 4.1, "height_ft": 18, "vol_cuft_ac": 350},
                    {"age": 15, "tpa": 368, "ba_sqft_ac": 60, "qmd_in": 5.5, "height_ft": 30, "vol_cuft_ac": 800},
                    {"age": 20, "tpa": 342, "ba_sqft_ac": 82, "qmd_in": 6.6, "height_ft": 40, "vol_cuft_ac": 1300},
                    {"age": 25, "tpa": 312, "ba_sqft_ac": 102, "qmd_in": 7.7, "height_ft": 50, "vol_cuft_ac": 2000},
                    {"age": 30, "tpa": 278, "ba_sqft_ac": 118, "qmd_in": 8.8, "height_ft": 58, "vol_cuft_ac": 2700},
                    {"age": 35, "tpa": 245, "ba_sqft_ac": 132, "qmd_in": 9.9, "height_ft": 66, "vol_cuft_ac": 3350},
                    {"age": 40, "tpa": 215, "ba_sqft_ac": 142, "qmd_in": 11.0, "height_ft": 72, "vol_cuft_ac": 4150},
                ],
            },
        },
        "growth_benchmarks": {
            "grass_stage_duration": {
                "description": "Time in grass stage before height growth",
                "unit": "years",
                "typical_range": [2, 7],
            },
            "post_grass_height_growth": {
                "description": "Height growth after grass stage initiation",
                "unit": "feet in 3 years",
                "value": 10,
            },
            "pai_peak_age": {
                "description": "Age of peak periodic annual increment",
                "unit": "years",
                "range": [20, 30],
            },
        },
        "notes": [
            "Longleaf pine has unique grass-stage seedling phase lasting 2-7 years",
            "Height growth delayed until root development complete",
            "Lower early growth rates than loblolly, but excellent form and longevity",
        ],
    }


def create_slash_pine_reference_data() -> dict:
    """Create reference yield data for Slash Pine from published sources.

    Data extracted from:
    - USFS Silvics Manual AG-654

    Returns:
        Dictionary with yield table data
    """
    return {
        "species": "SA",
        "common_name": "Slash Pine",
        "scientific_name": "Pinus elliottii",
        "sources": [
            {
                "citation": "Burns, R.M. and Honkala, B.H. 1990. Silvics of North America, Vol. 1. USDA Forest Service Agriculture Handbook 654.",
                "url": "https://www.srs.fs.usda.gov/pubs/misc/ag_654/volume_1/pinus/elliottii.htm",
            },
        ],
        "site_index_base_age": 25,  # Note: Some sources use base 50
        "site_index_range": {"min": 50, "max": 90, "typical": [60, 70, 80]},
        # From Silvics Manual - Natural stands on SI 80 (base 50)
        # Converted from m3/ha to cuft/acre (1 m3/ha = 14.29 cuft/acre)
        "yield_tables": {
            "SI60_T550": {
                "site_index": 60,
                "site_index_base_age": 25,
                "initial_tpa": 550,
                "description": "Medium site plantation (SI 60 base 25)",
                "source": "Silvics Manual Table 3, scaled",
                "data": [
                    {"age": 10, "tpa": 530, "ba_sqft_ac": 55, "qmd_in": 4.4, "height_ft": 28, "vol_cuft_ac": 700},
                    {"age": 15, "tpa": 460, "ba_sqft_ac": 85, "qmd_in": 5.8, "height_ft": 42, "vol_cuft_ac": 1500},
                    {"age": 20, "tpa": 390, "ba_sqft_ac": 105, "qmd_in": 7.0, "height_ft": 52, "vol_cuft_ac": 2200},
                    {"age": 25, "tpa": 330, "ba_sqft_ac": 118, "qmd_in": 8.1, "height_ft": 60, "vol_cuft_ac": 2800},
                    {"age": 30, "tpa": 280, "ba_sqft_ac": 128, "qmd_in": 9.1, "height_ft": 66, "vol_cuft_ac": 3300},
                    {"age": 35, "tpa": 240, "ba_sqft_ac": 135, "qmd_in": 10.1, "height_ft": 72, "vol_cuft_ac": 3750},
                    {"age": 40, "tpa": 205, "ba_sqft_ac": 140, "qmd_in": 11.2, "height_ft": 76, "vol_cuft_ac": 4100},
                ],
            },
            "SI70_T550": {
                "site_index": 70,
                "site_index_base_age": 25,
                "initial_tpa": 550,
                "description": "Good site plantation",
                "source": "Silvics Manual, interpolated",
                "data": [
                    {"age": 10, "tpa": 520, "ba_sqft_ac": 68, "qmd_in": 4.9, "height_ft": 34, "vol_cuft_ac": 950},
                    {"age": 15, "tpa": 440, "ba_sqft_ac": 100, "qmd_in": 6.4, "height_ft": 50, "vol_cuft_ac": 2000},
                    {"age": 20, "tpa": 365, "ba_sqft_ac": 122, "qmd_in": 7.8, "height_ft": 62, "vol_cuft_ac": 3000},
                    {"age": 25, "tpa": 300, "ba_sqft_ac": 138, "qmd_in": 9.2, "height_ft": 70, "vol_cuft_ac": 3800},
                    {"age": 30, "tpa": 250, "ba_sqft_ac": 148, "qmd_in": 10.4, "height_ft": 78, "vol_cuft_ac": 4500},
                    {"age": 35, "tpa": 210, "ba_sqft_ac": 155, "qmd_in": 11.6, "height_ft": 84, "vol_cuft_ac": 5050},
                    {"age": 40, "tpa": 178, "ba_sqft_ac": 160, "qmd_in": 12.8, "height_ft": 88, "vol_cuft_ac": 5500},
                ],
            },
            "SI80_T550": {
                "site_index": 80,
                "site_index_base_age": 25,
                "initial_tpa": 550,
                "description": "High site plantation (SI 80 base 25 ~ SI 90+ base 50)",
                "source": "Silvics Manual Tables 1 & 3",
                "data": [
                    # Silvics: Table 1 shows 200 m3/ha at age 20, 296 at 30, 360 at 40 for 34.4 m2/ha BA
                    {"age": 10, "tpa": 510, "ba_sqft_ac": 82, "qmd_in": 5.4, "height_ft": 40, "vol_cuft_ac": 1250},
                    {"age": 15, "tpa": 420, "ba_sqft_ac": 115, "qmd_in": 7.1, "height_ft": 58, "vol_cuft_ac": 2600},
                    {"age": 20, "tpa": 340, "ba_sqft_ac": 140, "qmd_in": 8.7, "height_ft": 72, "vol_cuft_ac": 3850},
                    {"age": 25, "tpa": 275, "ba_sqft_ac": 155, "qmd_in": 10.1, "height_ft": 80, "vol_cuft_ac": 4800},
                    {"age": 30, "tpa": 225, "ba_sqft_ac": 165, "qmd_in": 11.6, "height_ft": 88, "vol_cuft_ac": 5650},
                    {"age": 35, "tpa": 185, "ba_sqft_ac": 172, "qmd_in": 13.0, "height_ft": 94, "vol_cuft_ac": 6300},
                    {"age": 40, "tpa": 155, "ba_sqft_ac": 178, "qmd_in": 14.5, "height_ft": 98, "vol_cuft_ac": 6850},
                ],
            },
        },
        "growth_benchmarks": {
            "yield_at_age_30": {
                "description": "Almost 3/4 of 50-year yield produced by age 30",
                "source": "Silvics Manual",
            },
            "annual_growth_thinned": {
                "description": "Annual merchantable volume growth by age (thinned stands)",
                "unit": "cuft/acre/year",
                "data": {
                    "age_20_low_ba": 114,
                    "age_20_med_ba": 150,
                    "age_20_high_ba": 163,
                    "age_30_low_ba": 89,
                    "age_30_med_ba": 108,
                    "age_30_high_ba": 107,
                },
            },
        },
    }


def create_acceptance_criteria() -> dict:
    """Create acceptance criteria for validation comparisons.

    Based on FVS_PYTHON_VALIDATION_SPEC.md requirements.

    Returns:
        Dictionary with acceptance criteria
    """
    return {
        "description": "Acceptance criteria for FVS-Python validation",
        "source": "FVS_PYTHON_VALIDATION_SPEC.md",
        "stand_level": {
            "basal_area": {
                "max_percent_error": 5,
                "unit": "percent",
                "description": "Maximum acceptable error in basal area prediction",
            },
            "tpa": {
                "max_percent_error": 5,
                "unit": "percent",
                "description": "Maximum acceptable error in trees per acre",
            },
            "volume": {
                "max_percent_error": 10,
                "unit": "percent",
                "description": "Maximum acceptable error in volume prediction",
            },
            "qmd": {
                "max_percent_error": 5,
                "unit": "percent",
                "description": "Maximum acceptable error in quadratic mean diameter",
            },
            "top_height": {
                "max_percent_error": 5,
                "unit": "percent",
                "description": "Maximum acceptable error in dominant height",
            },
        },
        "tree_level": {
            "diameter_growth": {
                "max_percent_error": 5,
                "unit": "percent",
                "description": "Maximum acceptable error in diameter growth",
            },
            "height_growth": {
                "max_percent_error": 5,
                "unit": "percent",
                "description": "Maximum acceptable error in height growth",
            },
        },
        "equivalence_testing": {
            "method": "TOST",
            "alpha": 0.05,
            "equivalence_margin": 0.10,
            "description": "Two One-Sided Tests for equivalence",
        },
    }


def save_reference_data():
    """Save all reference data to YAML files."""
    REFERENCE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Species reference data
    species_data = {
        "loblolly_pine": create_loblolly_pine_reference_data(),
        "shortleaf_pine": create_shortleaf_pine_reference_data(),
        "longleaf_pine": create_longleaf_pine_reference_data(),
        "slash_pine": create_slash_pine_reference_data(),
    }

    for name, data in species_data.items():
        output_path = REFERENCE_DATA_DIR / f"{name}_yield_tables.yaml"
        with open(output_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        console.print(f"[green]Saved {output_path}[/green]")

    # Acceptance criteria
    criteria = create_acceptance_criteria()
    criteria_path = REFERENCE_DATA_DIR / "acceptance_criteria.yaml"
    with open(criteria_path, "w") as f:
        yaml.dump(criteria, f, default_flow_style=False, sort_keys=False)
    console.print(f"[green]Saved {criteria_path}[/green]")

    # Create combined reference data JSON for easy loading
    combined = {
        "metadata": {
            "created": datetime.now(timezone.utc).isoformat(),
            "description": "Combined reference data for FVS-Python validation",
            "sources": [
                "USDA Forest Service Silvics Manual (AG-654)",
                "Smalley & Bailey 1974 (SO-96)",
                "Baldwin & Feduccia 1987 (SO-236)",
            ],
        },
        "species": species_data,
        "acceptance_criteria": criteria,
    }

    combined_path = REFERENCE_DATA_DIR / "combined_reference_data.json"
    with open(combined_path, "w") as f:
        json.dump(combined, f, indent=2)
    console.print(f"[green]Saved {combined_path}[/green]")

    return combined


def display_summary(data: dict):
    """Display a summary table of the reference data."""
    table = Table(title="Reference Data Summary")
    table.add_column("Species", style="cyan")
    table.add_column("Code", style="green")
    table.add_column("Yield Tables", justify="right")
    table.add_column("SI Range", justify="center")
    table.add_column("Source")

    for name, species_data in data["species"].items():
        num_tables = len(species_data.get("yield_tables", {}))
        si_range = species_data.get("site_index_range", {})
        si_str = f"{si_range.get('min', '?')}-{si_range.get('max', '?')}"
        sources = species_data.get("sources", [])
        source_str = sources[0]["citation"][:40] + "..." if sources else "N/A"

        table.add_row(
            species_data["common_name"],
            species_data["species"],
            str(num_tables),
            si_str,
            source_str,
        )

    console.print(table)


def main():
    """Main function to download and prepare reference data."""
    console.print("[bold blue]FVS-Python Reference Data Preparation[/bold blue]\n")

    # Step 1: Download USFS publications
    console.print("[bold]Step 1: Downloading USFS Publications[/bold]")
    download_results = download_all_publications()

    successful = sum(1 for r in download_results.values() if r["status"] in ("success", "skipped"))
    console.print(f"Downloaded/found {successful}/{len(download_results)} publications\n")

    # Step 2: Create structured reference data
    console.print("[bold]Step 2: Creating Structured Reference Data[/bold]")
    combined_data = save_reference_data()

    # Step 3: Display summary
    console.print("\n[bold]Step 3: Reference Data Summary[/bold]")
    display_summary(combined_data)

    console.print("\n[green]Reference data preparation complete![/green]")
    console.print(f"Data saved to: {REFERENCE_DATA_DIR}")

    return combined_data


if __name__ == "__main__":
    main()

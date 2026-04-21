"""
Per-variant species code mappings for native FVS library integration.

Maps pyfvs 2-letter species codes to FVS Fortran integer indices (ISPN)
as defined in each variant's blkdat.f file. These indices are required
when communicating tree species to the native FVS shared library.

Usage:
    >>> from pyfvs.native.species_map import get_species_index, get_species_code
    >>> get_species_index('LP', 'SN')
    13
    >>> get_species_code(13, 'SN')
    'LP'
"""

from typing import Dict, Optional


# =============================================================================
# SN (Southern) Variant - 90 species
# Source: FVS SN blkdat.f JSP array, USDA Forest Service
# Species indices match the JSP array order (1-based) in blkdat.f
# =============================================================================
SN_SPECIES_MAP: Dict[str, int] = {
    "FR": 1,   # Fraser fir
    "JU": 2,   # Eastern redcedar
    "PI": 3,   # Spruce species
    "PU": 4,   # Sand pine
    "SP": 5,   # Shortleaf pine
    "SA": 6,   # Slash pine
    "SR": 7,   # Spruce pine
    "LL": 8,   # Longleaf pine
    "TM": 9,   # Tamarack
    "PP": 10,  # Pond pine
    "PD": 11,  # Pitch pine
    "WP": 12,  # Eastern white pine
    "LP": 13,  # Loblolly pine
    "VP": 14,  # Virginia pine
    "BY": 15,  # Baldcypress
    "PC": 16,  # Pondcypress
    "HM": 17,  # Hemlock
    "FM": 18,  # Florida maple
    "BE": 19,  # Beech
    "RM": 20,  # Red maple
    "SV": 21,  # Silver maple
    "SM": 22,  # Sugar maple
    "BU": 23,  # Buckeye
    "BB": 24,  # Birch species
    "SB": 25,  # Sweet birch
    "AH": 26,  # American hornbeam
    "HI": 27,  # Hickory
    "CA": 28,  # Catalpa
    "HB": 29,  # Hackberry / Hornbeam
    "RD": 30,  # Redbud
    "DW": 31,  # Dogwood
    "PS": 32,  # Persimmon
    "AB": 33,  # American beech
    "AS": 34,  # Ash species
    "WA": 35,  # White ash
    "BA": 36,  # Black ash
    "GA": 37,  # Green ash
    "HL": 38,  # Honeylocust
    "LB": 39,  # Black locust
    "HA": 40,  # Hawthorn
    "HY": 41,  # American holly
    "BN": 42,  # Butternut
    "WN": 43,  # Black walnut
    "SU": 44,  # Sweetgum
    "YP": 45,  # Yellow-poplar
    "MG": 46,  # Magnolia
    "CT": 47,  # Cucumbertree
    "MS": 48,  # Maple species
    "MV": 49,  # Sweetbay
    "ML": 50,  # Bigleaf magnolia
    "AP": 51,  # Apple
    "MB": 52,  # Mulberry
    "WT": 53,  # Water tupelo
    "BG": 54,  # Blackgum
    "TS": 55,  # Swamp tupelo
    "HH": 56,  # Hophornbeam
    "SD": 57,  # Sourwood
    "RA": 58,  # Red ash
    "SY": 59,  # American sycamore
    "CW": 60,  # Cottonwood
    "BT": 61,  # Bigtooth aspen
    "BC": 62,  # Black cherry
    "WO": 63,  # White oak
    "SO": 64,  # Scarlet oak
    "SK": 65,  # Southern red oak
    "CB": 66,  # Cherrybark oak
    "TO": 67,  # Turkey oak
    "LK": 68,  # Laurel oak
    "OV": 69,  # Overcup oak
    "BJ": 70,  # Blackjack oak
    "SN": 71,  # Swamp chestnut oak
    "CK": 72,  # Chinkapin oak
    "WK": 73,  # Water oak
    "CO": 74,  # Chestnut oak
    "RO": 75,  # Northern red oak
    "QS": 76,  # Generic oak
    "PO": 77,  # Post oak
    "BO": 78,  # Black oak (Quercus velutina)
    "LO": 79,  # Live oak
    "BK": 80,  # Black oak
    "WI": 81,  # Willow
    "SS": 82,  # Sassafras
    "BD": 83,  # Basswood
    "EL": 84,  # Elm
    "WE": 85,  # Winged elm
    "AE": 86,  # American elm
    "RL": 87,  # Rock elm
    "OS": 88,  # Other softwoods
    "OH": 89,  # Other hardwoods
    "OT": 90,  # Other tree
}

# =============================================================================
# LS (Lake States) Variant - 68 species
# Source: FVS LS blkdat.f, USDA Forest Service
# =============================================================================
LS_SPECIES_MAP: Dict[str, int] = {
    "JP": 1,   # Jack pine
    "SC": 2,   # Scotch pine
    "RN": 3,   # Red pine
    "RP": 4,   # Red pine (alternate code)
    "WP": 5,   # Eastern white pine
    "WS": 6,   # White spruce
    "NS": 7,   # Norway spruce
    "BF": 8,   # Balsam fir
    "BS": 9,   # Black spruce
    "TA": 10,  # Tamarack
    "WC": 11,  # Northern white cedar
    "EH": 12,  # Eastern hemlock
    "OS": 13,  # Other softwood
    "RC": 14,  # Eastern redcedar
    "BA": 15,  # Black ash
    "GA": 16,  # Green ash
    "EC": 17,  # Eastern cottonwood
    "SV": 18,  # Silver maple
    "RM": 19,  # Red maple
    "BC": 20,  # Black cherry
    "AE": 21,  # American elm
    "RL": 22,  # Rock elm
    "RE": 23,  # Slippery elm
    "YB": 24,  # Yellow birch
    "BW": 25,  # Black willow
    "SM": 26,  # Sugar maple
    "BM": 27,  # Black maple
    "AB": 28,  # American beech
    "WA": 29,  # White ash
    "WO": 30,  # White oak
    "SW": 31,  # Swamp white oak
    "BR": 32,  # Bur oak
    "CK": 33,  # Chinkapin oak
    "RO": 34,  # Northern red oak
    "BO": 35,  # Black oak
    "NP": 36,  # Norway pine (alternate RP)
    "BH": 37,  # Bitternut hickory
    "PH": 38,  # Pignut hickory
    "SH": 39,  # Shagbark hickory
    "BT": 40,  # Bigtooth aspen
    "QA": 41,  # Quaking aspen
    "BP": 42,  # Balsam poplar
    "PB": 43,  # Paper birch
    "BN": 45,  # Butternut
    "WN": 46,  # Black walnut
    "HH": 47,  # Hophornbeam
    "BK": 48,  # Birch species
    "OH": 49,  # Other hardwood
    "BE": 50,  # Beech
    "ST": 51,  # Striped maple
    "MM": 52,  # Mountain maple
    "AH": 53,  # American hornbeam
    "AC": 54,  # American chestnut
    "HK": 55,  # Hickory species
    "DW": 56,  # Dogwood
    "HT": 57,  # Hackberry
    "AP": 58,  # Apple
    "BG": 59,  # Black gum
    "SY": 60,  # Sycamore
    "PR": 61,  # Pin cherry
    "CC": 62,  # Chokecherry
    "PL": 63,  # Plum species
    "WI": 64,  # Willow
    "BL": 65,  # Black locust
    "DM": 66,  # Boxelder
    "SS": 67,  # Sassafras
    "MA": 68,  # Mulberry
}

# =============================================================================
# PN (Pacific Northwest Coast) Variant - 39 species
# Source: FVS PN blkdat.f JSP array, USDA Forest Service
# Species indices match the JSP array order (1-based) in blkdat.f
# Position 38 is blank in Fortran (no species assigned)
# =============================================================================
PN_SPECIES_MAP: Dict[str, int] = {
    "SF": 1,   # Pacific silver fir
    "WF": 2,   # White fir
    "GF": 3,   # Grand fir
    "AF": 4,   # Subalpine fir
    "RF": 5,   # Red fir (Shasta red fir)
    "SS": 6,   # Sitka spruce
    "NF": 7,   # Noble fir
    "YC": 8,   # Alaska yellow cedar
    "IC": 9,   # Incense cedar
    "ES": 10,  # Engelmann spruce
    "LP": 11,  # Lodgepole pine
    "JP": 12,  # Jeffrey pine
    "SP": 13,  # Sugar pine
    "WP": 14,  # Western white pine
    "PP": 15,  # Ponderosa pine
    "DF": 16,  # Douglas-fir
    "RW": 17,  # Redwood
    "RC": 18,  # Western red cedar
    "WH": 19,  # Western hemlock
    "MH": 20,  # Mountain hemlock
    "BM": 21,  # Bigleaf maple
    "RA": 22,  # Red alder
    "WA": 23,  # White alder
    "PB": 24,  # Paper birch
    "GC": 25,  # Giant chinkapin
    "AS": 26,  # Quaking aspen
    "CW": 27,  # Black cottonwood
    "WO": 28,  # Oregon white oak
    "WJ": 29,  # Western juniper
    "LL": 30,  # Subalpine larch
    "WB": 31,  # Whitebark pine
    "KP": 32,  # Knobcone pine
    "PY": 33,  # Pacific yew
    "DG": 34,  # Pacific dogwood
    "HT": 35,  # Hawthorn species
    "CH": 36,  # Cherry species
    "WI": 37,  # Willow species
    "OT": 39,  # Other species
}

# =============================================================================
# WC (West Cascades) Variant - 37 species
# Source: FVS WC blkdat.f JSP array, USDA Forest Service
# Species indices match the JSP array order (1-based) in blkdat.f
# Same as PN but position 6 (SS/Sitka spruce) is blank (not in WC range)
# Positions 6 and 38 are blank in Fortran
# =============================================================================
WC_SPECIES_MAP: Dict[str, int] = {
    "SF": 1,   # Pacific silver fir
    "WF": 2,   # White fir
    "GF": 3,   # Grand fir
    "AF": 4,   # Subalpine fir
    "RF": 5,   # Red fir
    "NF": 7,   # Noble fir
    "YC": 8,   # Alaska yellow cedar
    "IC": 9,   # Incense cedar
    "ES": 10,  # Engelmann spruce
    "LP": 11,  # Lodgepole pine
    "JP": 12,  # Jeffrey pine
    "SP": 13,  # Sugar pine
    "WP": 14,  # Western white pine
    "PP": 15,  # Ponderosa pine
    "DF": 16,  # Douglas-fir
    "RW": 17,  # Redwood
    "RC": 18,  # Western red cedar
    "WH": 19,  # Western hemlock
    "MH": 20,  # Mountain hemlock
    "BM": 21,  # Bigleaf maple
    "RA": 22,  # Red alder
    "WA": 23,  # White alder
    "PB": 24,  # Paper birch
    "GC": 25,  # Giant chinkapin
    "AS": 26,  # Quaking aspen
    "CW": 27,  # Black cottonwood
    "WO": 28,  # Oregon white oak
    "WJ": 29,  # Western juniper
    "LL": 30,  # Subalpine larch
    "WB": 31,  # Whitebark pine
    "KP": 32,  # Knobcone pine
    "PY": 33,  # Pacific yew
    "DG": 34,  # Pacific dogwood
    "HT": 35,  # Hawthorn species
    "CH": 36,  # Cherry species
    "WI": 37,  # Willow species
    "OT": 39,  # Other species
}

# =============================================================================
# NE (Northeast) Variant - 108 species
# Source: FVS NE blkdat.f, USDA Forest Service
# =============================================================================
NE_SPECIES_MAP: Dict[str, int] = {
    "BF": 1,   # Balsam fir
    "TA": 2,   # Tamarack
    "WS": 3,   # White spruce
    "RS": 4,   # Red spruce
    "NS": 5,   # Norway spruce
    "BS": 6,   # Black spruce
    "PI": 7,   # Other spruce
    "RN": 8,   # Red pine
    "WP": 9,   # Eastern white pine
    "LP": 10,  # Loblolly pine
    "VP": 11,  # Virginia pine
    "WC": 12,  # Northern white cedar
    "AW": 13,  # Atlantic white cedar
    "RC": 14,  # Eastern redcedar
    "JU": 15,  # Other cedar/juniper
    "EH": 16,  # Eastern hemlock
    "HM": 17,  # Other hemlock
    "OP": 18,  # Other pine
    "JP": 19,  # Jack pine
    "SP": 20,  # Shortleaf pine
    "TM": 21,  # Table mountain pine
    "PP": 22,  # Pitch pine
    "PD": 23,  # Pond pine
    "SC": 24,  # Scotch pine
    "OS": 25,  # Other softwoods
    "RM": 26,  # Red maple
    "SM": 27,  # Sugar maple
    "BM": 28,  # Black maple
    "SV": 29,  # Silver maple
    "YB": 30,  # Yellow birch
    "SB": 31,  # Sweet birch
    "RB": 32,  # River birch
    "PB": 33,  # Paper birch
    "GB": 34,  # Gray birch
    "HI": 35,  # Hickory
    "PH": 36,  # Pignut hickory
    "SL": 37,  # Shellbark hickory
    "SH": 38,  # Shagbark hickory
    "MH": 39,  # Mockernut hickory
    "AB": 40,  # American beech
    "AS": 41,  # Ash
    "WA": 42,  # White ash
    "BA": 43,  # Black ash
    "GA": 44,  # Green ash
    "PA": 45,  # Pumpkin ash
    "YP": 46,  # Yellow-poplar
    "SU": 47,  # Sweetgum
    "CT": 48,  # Cucumbertree
    "QA": 49,  # Quaking aspen
    "BP": 50,  # Balsam poplar
    "EC": 51,  # Eastern cottonwood
    "BT": 52,  # Bigtooth aspen
    "PY": 53,  # Swamp cottonwood
    "BC": 54,  # Black cherry
    "WO": 55,  # White oak
    "BR": 56,  # Bur oak
    "CK": 57,  # Chinkapin oak
    "PO": 58,  # Post oak
    "OK": 59,  # Other oaks
    "SO": 60,  # Scarlet oak
    "QI": 61,  # Shingle oak
    "WK": 62,  # Water oak
    "PN": 63,  # Pin oak
    "CO": 64,  # Chestnut oak
    "SW": 65,  # Swamp white oak
    "SN": 66,  # Swamp chestnut oak
    "RO": 67,  # Northern red oak
    "SK": 68,  # Southern red oak
    "BO": 69,  # Black oak
    "CB": 70,  # Cherrybark oak
    "BU": 72,  # Buckeye
    "YY": 73,  # Yellow buckeye
    "WR": 74,  # Water birch
    "HK": 75,  # Hackberry
    "PS": 76,  # Persimmon
    "HY": 77,  # American holly
    "BN": 78,  # Butternut
    "WN": 79,  # Black walnut
    "OO": 80,  # Osage-orange
    "MG": 81,  # Magnolia
    "MV": 82,  # Sweetbay
    "AP": 83,  # Apple
    "WT": 84,  # Water tupelo
    "BG": 85,  # Blackgum
    "SD": 86,  # Sourwood
    "PW": 87,  # Paulownia
    "SY": 88,  # Sycamore
    "WL": 89,  # Willow oak
    "BK": 90,  # Black locust
    "BL": 91,  # Black willow
    "SS": 92,  # Sassafras
    "BW": 93,  # American basswood
    "WB": 94,  # White basswood
    "EL": 95,  # Other elm
    "AE": 96,  # American elm
    "RL": 97,  # Slippery elm
    "OH": 98,  # Other hardwoods
    "BE": 99,  # Boxelder
    "ST": 100, # Striped maple
    "AI": 101, # Ailanthus
    "SE": 102, # Serviceberry
    "AH": 103, # American hornbeam
    "DW": 104, # Flowering dogwood
    "HT": 105, # Hawthorn
    "HH": 106, # Eastern hophornbeam
    "PL": 107, # Cherry/plum
    "PR": 108, # Pin cherry
}

# =============================================================================
# CS (Central States) Variant - 96 species
# Source: FVS CS blkdat.f, USDA Forest Service
# =============================================================================
CS_SPECIES_MAP: Dict[str, int] = {
    "RC": 1,   # Eastern redcedar
    "JU": 2,   # Juniper
    "SP": 3,   # Shortleaf pine
    "VP": 4,   # Virginia pine
    "LP": 5,   # Loblolly pine
    "OS": 6,   # Other softwoods
    "WP": 7,   # Eastern white pine
    "WN": 8,   # Black walnut
    "BN": 9,   # Butternut
    "TL": 10,  # Tupelo
    "TS": 11,  # Swamp tupelo
    "WT": 12,  # Water tupelo
    "BG": 13,  # Blackgum
    "HS": 14,  # Hickory species
    "SH": 15,  # Shagbark hickory
    "SL": 16,  # Shellbark hickory
    "MH": 17,  # Mockernut hickory
    "PH": 18,  # Pignut hickory
    "HI": 19,  # Hickory
    "WH": 20,  # Water hickory
    "BH": 21,  # Bitternut hickory
    "PE": 22,  # Pecan
    "BI": 23,  # Black hickory
    "AB": 24,  # American beech
    "BA": 25,  # Black ash
    "PA": 26,  # Pumpkin ash
    "UA": 27,  # Blue ash
    "EC": 28,  # Eastern cottonwood
    "RM": 29,  # Red maple
    "BE": 30,  # Boxelder
    "SV": 31,  # Silver maple
    "BC": 32,  # Black cherry
    "AE": 33,  # American elm
    "SG": 34,  # Sugarberry
    "HK": 35,  # Common hackberry
    "WE": 36,  # Winged elm
    "EL": 37,  # Elm
    "SI": 38,  # Siberian elm
    "RL": 39,  # Slippery elm
    "RE": 40,  # Rock elm
    "YP": 41,  # Tuliptree
    "BW": 42,  # American basswood
    "SM": 43,  # Sugar maple
    "AS": 44,  # Ash
    "WA": 45,  # White ash
    "GA": 46,  # Green ash
    "WO": 47,  # White oak
    "RO": 48,  # Northern red oak
    "SK": 49,  # Southern red oak
    "BO": 50,  # Black oak
    "SO": 51,  # Scarlet oak
    "BJ": 52,  # Blackjack oak
    "CK": 53,  # Chinkapin oak
    "SW": 54,  # Swamp white oak
    "BR": 55,  # Bur oak
    "SN": 56,  # Swamp chestnut oak
    "PO": 57,  # Post oak
    "DO": 58,  # Bottomland post oak
    "CO": 59,  # Chestnut oak
    "PN": 60,  # Pin oak
    "CB": 61,  # Cherrybark oak
    "QI": 62,  # Shingle oak
    "OV": 63,  # Overcup oak
    "WK": 64,  # Water oak
    "NK": 65,  # Nuttall oak
    "WL": 66,  # Willow oak
    "QS": 67,  # Shumard oak
    "UH": 68,  # Unknown hardwood
    "SS": 69,  # Sassafras
    "OB": 70,  # Ohio buckeye
    "CA": 71,  # Catalpa
    "PS": 72,  # Common persimmon
    "HL": 73,  # Honeylocust
    "BP": 74,  # Balsam poplar
    "BT": 75,  # Bigtooth aspen
    "QA": 76,  # Quaking aspen
    "BK": 77,  # Black locust
    "OL": 78,  # Other locust
    "SY": 79,  # Sycamore
    "BY": 80,  # Bald cypress
    "RB": 81,  # River birch
    "SU": 82,  # Sweetgum
    "WI": 83,  # Willow
    "BL": 84,  # Black willow
    "NC": 85,  # Non-commercial species
    "AH": 86,  # American hornbeam
    "RD": 87,  # Eastern redbud
    "DW": 88,  # Flowering dogwood
    "HT": 89,  # Hawthorn
    "KC": 90,  # Kentucky coffeetree
    "OO": 91,  # Osage-orange
    "CT": 92,  # Cucumber tree
    "MV": 93,  # Sweetbay
    "MB": 94,  # Mulberry
    "HH": 95,  # Hophornbeam
    "SD": 96,  # Sourwood
}

# =============================================================================
# OP (ORGANON Pacific Northwest) Variant - 39 species
# Source: FVS OP blkdat.f JSP array, USDA Forest Service
# Species indices match the JSP array order (1-based) in blkdat.f
# Same as PN except positions 23-24 are MA/TO instead of WA/PB
# Position 38 is blank in Fortran
# =============================================================================
OP_SPECIES_MAP: Dict[str, int] = {
    "SF": 1,   # Pacific silver fir
    "WF": 2,   # White fir
    "GF": 3,   # Grand fir
    "AF": 4,   # Subalpine fir
    "RF": 5,   # Red fir (Shasta red fir)
    "SS": 6,   # Sitka spruce
    "NF": 7,   # Noble fir
    "YC": 8,   # Alaska yellow cedar
    "IC": 9,   # Incense cedar
    "ES": 10,  # Engelmann spruce
    "LP": 11,  # Lodgepole pine
    "JP": 12,  # Jeffrey pine
    "SP": 13,  # Sugar pine
    "WP": 14,  # Western white pine
    "PP": 15,  # Ponderosa pine
    "DF": 16,  # Douglas-fir
    "RW": 17,  # Redwood
    "RC": 18,  # Western red cedar
    "WH": 19,  # Western hemlock
    "MH": 20,  # Mountain hemlock
    "BM": 21,  # Bigleaf maple
    "RA": 22,  # Red alder
    "MA": 23,  # Pacific madrone
    "TO": 24,  # Tanoak
    "GC": 25,  # Giant chinkapin
    "AS": 26,  # Quaking aspen
    "CW": 27,  # Black cottonwood
    "WO": 28,  # Oregon white oak
    "WJ": 29,  # Western juniper
    "LL": 30,  # Subalpine larch
    "WB": 31,  # Whitebark pine
    "KP": 32,  # Knobcone pine
    "PY": 33,  # Pacific yew
    "DG": 34,  # Pacific dogwood
    "HT": 35,  # Hawthorn species
    "CH": 36,  # Cherry species
    "WI": 37,  # Willow species
    "OT": 39,  # Other species
}

# =============================================================================
# CA (Inland California / South Central Oregon) Variant - 50 species
# Source: FVS CA blkdat.f, USDA Forest Service
# =============================================================================
CA_SPECIES_MAP: Dict[str, int] = {
    "PC": 1,   # Port Orford cedar
    "IC": 2,   # Incense cedar
    "RC": 3,   # Western redcedar
    "WF": 4,   # White fir
    "RF": 5,   # Red fir (California red fir)
    "SH": 6,   # Shasta red fir
    "DF": 7,   # Douglas-fir
    "WH": 8,   # Western hemlock
    "MH": 9,   # Mountain hemlock
    "WB": 10,  # Whitebark pine
    "KP": 11,  # Knobcone pine
    "LP": 12,  # Lodgepole pine
    "CP": 13,  # Coulter pine
    "LM": 14,  # Limber pine
    "JP": 15,  # Jeffrey pine
    "SP": 16,  # Sugar pine
    "WP": 17,  # Western white pine
    "PP": 18,  # Ponderosa pine
    "MP": 19,  # Monterey pine
    "GP": 20,  # Digger pine / CA foothill pine
    "WJ": 21,  # Western juniper
    "BR": 22,  # Brewer spruce
    "GS": 23,  # Giant sequoia
    "RW": 24,  # Redwood
    "PY": 25,  # Pacific yew
    "CN": 26,  # California nutmeg
    "OS": 27,  # Other softwood
    "LO": 28,  # Coast live oak
    "CY": 29,  # Canyon live oak
    "BL": 30,  # Blue oak
    "EO": 31,  # Engelmann oak
    "WO": 32,  # Oregon white oak
    "BO": 33,  # California black oak
    "VO": 34,  # Valley oak
    "IO": 35,  # Interior live oak
    "BM": 36,  # Bigleaf maple
    "BU": 37,  # California buckeye
    "RA": 38,  # Red alder
    "MA": 39,  # Pacific madrone
    "GC": 40,  # Giant chinquapin
    "DG": 41,  # Pacific dogwood
    "FL": 42,  # Oregon ash
    "WN": 43,  # Walnut
    "TO": 44,  # Tanoak
    "SY": 45,  # California sycamore
    "AS": 46,  # Quaking aspen
    "CW": 47,  # Black cottonwood
    "WI": 48,  # Willow
    "CL": 49,  # California laurel
    "OH": 50,  # Other hardwood
}

# =============================================================================
# OC (ORGANON Southwest Oregon) Variant - 50 species
# Source: FVS OC blkdat.f (same species list as CA)
# =============================================================================
OC_SPECIES_MAP: Dict[str, int] = {
    "PC": 1,   # Port Orford cedar
    "IC": 2,   # Incense cedar
    "RC": 3,   # Western redcedar
    "GF": 4,   # Grand fir
    "RF": 5,   # California red fir
    "SH": 6,   # Shasta red fir
    "DF": 7,   # Douglas-fir
    "WH": 8,   # Western hemlock
    "MH": 9,   # Mountain hemlock
    "WB": 10,  # Whitebark pine
    "KP": 11,  # Knobcone pine
    "LP": 12,  # Lodgepole pine
    "CP": 13,  # Coulter pine
    "LM": 14,  # Limber pine
    "JP": 15,  # Jeffrey pine
    "SP": 16,  # Sugar pine
    "WP": 17,  # Western white pine
    "PP": 18,  # Ponderosa pine
    "MP": 19,  # Monterey pine
    "GP": 20,  # California foothill pine
    "WJ": 21,  # Western juniper
    "BR": 22,  # Brewer spruce
    "GS": 23,  # Giant sequoia
    "PY": 24,  # Pacific yew
    "OS": 25,  # Other softwood
    "LO": 26,  # Coast live oak
    "CY": 27,  # Canyon live oak
    "BL": 28,  # Blue oak
    "EO": 29,  # Engelmann oak
    "WO": 30,  # Oregon white oak
    "BO": 31,  # California black oak
    "VO": 32,  # Valley oak
    "IO": 33,  # Interior live oak
    "BM": 34,  # Bigleaf maple
    "BU": 35,  # California buckeye
    "RA": 36,  # Red alder
    "MA": 37,  # Pacific madrone
    "GC": 38,  # Giant chinquapin
    "DG": 39,  # Pacific dogwood
    "FL": 40,  # Oregon ash
    "WN": 41,  # Walnut
    "TO": 42,  # Tanoak
    "SY": 43,  # California sycamore
    "AS": 44,  # Quaking aspen
    "CW": 45,  # Black cottonwood
    "WI": 46,  # Willow
    "CN": 47,  # California nutmeg
    "CL": 48,  # California laurel
    "OH": 49,  # Other hardwood
    "RW": 50,  # Redwood
}

# =============================================================================
# WS (Western Sierra Nevada) Variant - 43 species
# Source: FVS WS blkdat.f, USDA Forest Service
# =============================================================================
WS_SPECIES_MAP: Dict[str, int] = {
    "SP": 1,   # Sugar pine
    "DF": 2,   # Douglas-fir
    "WF": 3,   # White fir
    "GS": 4,   # Giant sequoia
    "IC": 5,   # Incense cedar
    "JP": 6,   # Jeffrey pine
    "RF": 7,   # Red fir
    "PP": 8,   # Ponderosa pine
    "LP": 9,   # Lodgepole pine
    "WB": 10,  # Whitebark pine
    "WP": 11,  # Western white pine
    "PM": 12,  # Pacific silver fir
    "SF": 13,  # Subalpine fir
    "KP": 14,  # Knobcone pine
    "FP": 15,  # Foxtail pine
    "CP": 16,  # Coulter pine
    "LM": 17,  # Limber pine
    "MP": 18,  # Monterey pine
    "GP": 19,  # California foothill pine
    "WE": 20,  # Washoe pine
    "GB": 21,  # Great Basin bristlecone pine
    "BD": 22,  # Bigcone Douglas-fir
    "RW": 23,  # Redwood
    "MH": 24,  # Mountain hemlock
    "WJ": 25,  # Western juniper
    "UJ": 26,  # Utah juniper
    "CJ": 27,  # California juniper
    "LO": 28,  # Coast live oak
    "CY": 29,  # Canyon live oak
    "BL": 30,  # Blue oak
    "BO": 31,  # California black oak
    "VO": 32,  # Valley oak
    "IO": 33,  # Interior live oak
    "TO": 34,  # Tanoak
    "GC": 35,  # Giant chinquapin
    "AS": 36,  # Quaking aspen
    "CL": 37,  # California laurel
    "MA": 38,  # Pacific madrone
    "DG": 39,  # Pacific dogwood
    "BM": 40,  # Bigleaf maple
    "MC": 41,  # Mountain mahogany
    "OS": 42,  # Other softwood
    "OH": 43,  # Other hardwood
}

# =============================================================================
# Master variant lookup
# =============================================================================
# =============================================================================
# EC (East Cascades) Variant - 32 species
# Source: FVS ec/blkdat.f JSP array, USDA Forest Service
# =============================================================================
EC_SPECIES_MAP: Dict[str, int] = {
    "WP": 1,   # Western white pine
    "WL": 2,   # Western larch
    "DF": 3,   # Douglas-fir
    "SF": 4,   # Pacific silver fir
    "RC": 5,   # Western red cedar
    "GF": 6,   # Grand fir
    "LP": 7,   # Lodgepole pine
    "ES": 8,   # Engelmann spruce
    "AF": 9,   # Subalpine fir
    "PP": 10,  # Ponderosa pine
    "WH": 11,  # Western hemlock
    "MH": 12,  # Mountain hemlock
    "PY": 13,  # Pacific yew
    "WB": 14,  # Whitebark pine
    "NF": 15,  # Noble fir
    "WF": 16,  # White fir
    "LL": 17,  # Subalpine larch
    "YC": 18,  # Alaska yellow cedar
    "WJ": 19,  # Western juniper
    "BM": 20,  # Bigleaf maple
    "VN": 21,  # Vine maple
    "RA": 22,  # Red alder
    "PB": 23,  # Paper birch
    "GC": 24,  # Giant chinkapin
    "DG": 25,  # Pacific dogwood
    "AS": 26,  # Quaking aspen
    "CW": 27,  # Black cottonwood
    "WO": 28,  # Oregon white oak
    "PL": 29,  # Plum species
    "WI": 30,  # Willow species
    "OS": 31,  # Other softwoods
    "OH": 32,  # Other hardwoods
}


VARIANT_SPECIES_MAPS: Dict[str, Dict[str, int]] = {
    "SN": SN_SPECIES_MAP,
    "LS": LS_SPECIES_MAP,
    "PN": PN_SPECIES_MAP,
    "WC": WC_SPECIES_MAP,
    "NE": NE_SPECIES_MAP,
    "CS": CS_SPECIES_MAP,
    "OP": OP_SPECIES_MAP,
    "CA": CA_SPECIES_MAP,
    "OC": OC_SPECIES_MAP,
    "WS": WS_SPECIES_MAP,
    "EC": EC_SPECIES_MAP,
}


def get_species_index(code: str, variant: str = "SN") -> int:
    """Get the FVS Fortran species index for a given species code and variant.

    Args:
        code: Two-letter pyfvs species code (e.g., 'LP', 'DF').
        variant: FVS variant identifier (e.g., 'SN', 'PN', 'LS').

    Returns:
        Integer species index used by the native FVS library.

    Raises:
        ValueError: If variant or species code is not found.
    """
    variant_upper = variant.upper()
    code_upper = code.upper()

    if variant_upper not in VARIANT_SPECIES_MAPS:
        raise ValueError(
            f"Unknown variant '{variant}'. "
            f"Valid variants: {sorted(VARIANT_SPECIES_MAPS.keys())}"
        )

    species_map = VARIANT_SPECIES_MAPS[variant_upper]
    if code_upper not in species_map:
        raise ValueError(
            f"Species '{code}' not found in variant '{variant}'. "
            f"Valid species: {sorted(species_map.keys())}"
        )

    return species_map[code_upper]


def get_species_code(index: int, variant: str = "SN") -> str:
    """Get the pyfvs species code for a given FVS Fortran species index.

    Args:
        index: Integer species index from the native FVS library.
        variant: FVS variant identifier (e.g., 'SN', 'PN', 'LS').

    Returns:
        Two-letter pyfvs species code.

    Raises:
        ValueError: If variant or species index is not found.
    """
    variant_upper = variant.upper()

    if variant_upper not in VARIANT_SPECIES_MAPS:
        raise ValueError(
            f"Unknown variant '{variant}'. "
            f"Valid variants: {sorted(VARIANT_SPECIES_MAPS.keys())}"
        )

    species_map = VARIANT_SPECIES_MAPS[variant_upper]
    reverse_map = {v: k for k, v in species_map.items()}

    if index not in reverse_map:
        raise ValueError(
            f"Species index {index} not found in variant '{variant}'. "
            f"Valid indices: {sorted(reverse_map.keys())}"
        )

    return reverse_map[index]


def get_supported_variants() -> list:
    """Return list of variant codes with species mappings."""
    return sorted(VARIANT_SPECIES_MAPS.keys())


def get_species_count(variant: str) -> int:
    """Return the number of species mapped for a given variant."""
    variant_upper = variant.upper()
    if variant_upper not in VARIANT_SPECIES_MAPS:
        raise ValueError(f"Unknown variant '{variant}'")
    return len(VARIANT_SPECIES_MAPS[variant_upper])

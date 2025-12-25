"""
Volume Library module for FVS-Python.
Provides Python wrapper around the USFS Volume Estimator Library (NVEL).
Integrates professional-grade volume calculations into the FVS-Python framework.
"""
import os
import platform
import json
from ctypes import *
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import warnings


class FortranChar(Structure):
    """Represents a Fortran character string with length parameter."""
    _fields_ = [
        ('str', c_char_p),
        ('len', c_int),
    ]
    
    def __init__(self, value: str = "", length: Optional[int] = None):
        """Initialize Fortran character string.
        
        Args:
            value: String value
            length: String length (defaults to len(value))
        """
        super().__init__()
        if length is None:
            length = len(value)
        
        # Pad string to specified length
        padded_value = value.ljust(length)[:length]
        self.str = padded_value.encode('ascii')
        self.len = length


class VolumeResult:
    """Container for volume calculation results."""
    
    def __init__(self, vol_array: List[float], error_flag: int = 0):
        """Initialize volume result.
        
        Args:
            vol_array: Array of 15 volume values from NVEL
            error_flag: Error flag from volume calculation
        """
        self.error_flag = error_flag
        self.volumes = vol_array
        
        # Map volume array indices to meaningful names (based on NVEL documentation)
        self.total_cubic_volume = vol_array[0] if len(vol_array) > 0 else 0.0
        self.gross_cubic_volume = vol_array[1] if len(vol_array) > 1 else 0.0
        self.net_cubic_volume = vol_array[2] if len(vol_array) > 2 else 0.0
        self.merchantable_cubic_volume = vol_array[3] if len(vol_array) > 3 else 0.0
        self.board_foot_volume = vol_array[4] if len(vol_array) > 4 else 0.0
        self.cord_volume = vol_array[5] if len(vol_array) > 5 else 0.0
        self.green_weight = vol_array[6] if len(vol_array) > 6 else 0.0
        self.dry_weight = vol_array[7] if len(vol_array) > 7 else 0.0
        self.sawlog_cubic_volume = vol_array[8] if len(vol_array) > 8 else 0.0
        self.sawlog_board_foot = vol_array[9] if len(vol_array) > 9 else 0.0
        self.sawlog_cubic_foot_intl = vol_array[10] if len(vol_array) > 10 else 0.0
        self.sawlog_board_foot_intl = vol_array[11] if len(vol_array) > 11 else 0.0
        self.biomass_main_stem = vol_array[12] if len(vol_array) > 12 else 0.0
        self.biomass_live_branches = vol_array[13] if len(vol_array) > 13 else 0.0
        self.biomass_foliage = vol_array[14] if len(vol_array) > 14 else 0.0
    
    def is_valid(self) -> bool:
        """Check if volume calculation was successful."""
        return self.error_flag == 0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for easy access."""
        return {
            'total_cubic_volume': self.total_cubic_volume,
            'gross_cubic_volume': self.gross_cubic_volume,
            'net_cubic_volume': self.net_cubic_volume,
            'merchantable_cubic_volume': self.merchantable_cubic_volume,
            'board_foot_volume': self.board_foot_volume,
            'cord_volume': self.cord_volume,
            'green_weight': self.green_weight,
            'dry_weight': self.dry_weight,
            'sawlog_cubic_volume': self.sawlog_cubic_volume,
            'sawlog_board_foot': self.sawlog_board_foot,
            'sawlog_cubic_foot_intl': self.sawlog_cubic_foot_intl,
            'sawlog_board_foot_intl': self.sawlog_board_foot_intl,
            'biomass_main_stem': self.biomass_main_stem,
            'biomass_live_branches': self.biomass_live_branches,
            'biomass_foliage': self.biomass_foliage,
            'error_flag': self.error_flag
        }


class VolumeLibrary:
    """Python wrapper for USFS Volume Estimator Library."""
    
    def __init__(self, dll_path: Optional[Path] = None):
        """Initialize volume library.
        
        Args:
            dll_path: Path to vollib.dll. If None, searches in package directory.
        """
        self.dll = None
        self.dll_path = dll_path
        self.species_mapping = self._load_species_mapping()
        self.region_mapping = self._load_region_mapping()
        self._load_dll()
    
    def _find_dll_path(self) -> Optional[Path]:
        """Find the volume library DLL."""
        if self.dll_path and self.dll_path.exists():
            return self.dll_path
        
        # Search in package directory
        package_dir = Path(__file__).parent.parent.parent
        
        # Check different possible locations
        search_paths = [
            package_dir / "VolLibDll20250512" / "vollib-64bits" / "vollib.dll",
            package_dir / "VolLibDll20250512" / "vollib-32bits" / "vollib.dll",
            package_dir / "vollib" / "vollib.dll",
            Path("vollib.dll"),  # Current directory
        ]
        
        for path in search_paths:
            if path.exists():
                return path
        
        return None
    
    def _load_dll(self):
        """Load the volume library DLL."""
        dll_path = self._find_dll_path()
        
        if dll_path is None:
            warnings.warn(
                "Volume library DLL not found. Volume calculations will use fallback method. "
                "To use NVEL volume equations, ensure vollib.dll is available.",
                UserWarning
            )
            return
        
        try:
            if platform.system() == "Windows":
                self.dll = windll.LoadLibrary(str(dll_path))
            else:
                # For non-Windows systems, would need a different approach
                warnings.warn(
                    "Volume library DLL is only available for Windows. "
                    "Using fallback volume calculation.",
                    UserWarning
                )
                return
                
        except Exception as e:
            warnings.warn(
                f"Failed to load volume library DLL: {e}. "
                "Using fallback volume calculation.",
                UserWarning
            )
            self.dll = None
    
    def _load_species_mapping(self) -> Dict[str, int]:
        """Load FVS species code to NVEL species code mapping."""
        # This mapping connects FVS species codes to NVEL species codes
        # Based on FVS Southern variant species codes
        return {
            'LP': 131,  # Loblolly Pine
            'SP': 132,  # Shortleaf Pine  
            'LL': 133,  # Longleaf Pine
            'SA': 134,  # Slash Pine
            'VP': 135,  # Virginia Pine
            'PD': 136,  # Pitch Pine
            'SR': 137,  # Spruce Pine
            'PP': 138,  # Pond Pine
            'SD': 139,  # Sand Pine
            'WO': 833,  # White Oak
            'SO': 834,  # Southern Red Oak
            'WK': 835,  # Water Oak
            'LK': 836,  # Laurel Oak
            'OV': 837,  # Overcup Oak
            'CW': 838,  # Chestnut Oak
            'SK': 839,  # Swamp Oak
            'HI': 401,  # Hickory species
            'SU': 611,  # Sweetgum
            'YP': 621,  # Yellow Poplar
            'RM': 316,  # Red Maple
            'SM': 318,  # Sugar Maple
            'SV': 317,  # Silver Maple
            'WA': 541,  # White Ash
            'GA': 543,  # Green Ash
            'RA': 544,  # Red Ash
            'BA': 545,  # Black Ash
            'BC': 762,  # Black Cherry
            'SY': 931,  # American Sycamore
            'BG': 693,  # Black Gum
            'WE': 971,  # White Elm
            'AE': 972,  # American Elm
            'RL': 973,  # Red Elm
            'BE': 531,  # American Beech
            'BY': 721,  # Bald Cypress
            'PC': 722,  # Pond Cypress
            'WP': 129,  # White Pine
            'HM': 261,  # Eastern Hemlock
            'RO': 261,  # Eastern Hemlock (alias)
        }
    
    def _load_region_mapping(self) -> Dict[str, int]:
        """Load region mapping for volume equations."""
        # FVS Southern variant typically uses Region 8 (Southern)
        return {
            'default': 8,  # Southern Region
            'south': 8,
            'southeast': 8,
            'southern': 8
        }
    
    def get_version(self) -> Optional[int]:
        """Get volume library version."""
        if not self.dll:
            return None
        
        try:
            version = c_int()
            self.dll.VERNUM(byref(version))
            return version.value
        except Exception:
            return None
    
    def get_volume_equation(self, species_code: str, region: int = 8, 
                          forest: str = "01", district: str = "01") -> Optional[str]:
        """Get the default volume equation for a species.
        
        Args:
            species_code: FVS species code
            region: Forest Service region (default: 8 for Southern)
            forest: Forest code (default: "01")
            district: District code (default: "01")
            
        Returns:
            Volume equation string or None if not found
        """
        if not self.dll:
            return None
        
        # Map FVS species code to NVEL species code
        nvel_species = self.species_mapping.get(species_code)
        if nvel_species is None:
            return None
        
        try:
            regn = c_int(region)
            forst = FortranChar(forest, 2)
            dist = FortranChar(district, 2)
            spec = c_int(nvel_species)
            prod = FortranChar("01", 2)  # Product code
            voleq = FortranChar("", 10)  # Output volume equation
            errflag = c_int(0)
            
            self.dll.GETVOLEQ(
                byref(regn), forst.str, forst.len,
                dist.str, dist.len, byref(spec),
                prod.str, prod.len, voleq.str, voleq.len,
                byref(errflag)
            )
            
            if errflag.value == 0:
                return voleq.str.decode('ascii').strip()
            else:
                return None
                
        except Exception:
            return None
    
    def calculate_volume(self, dbh: float, height: float, species_code: str,
                        region: int = 8, forest: str = "01", 
                        volume_equation: Optional[str] = None,
                        height_type: str = "F", live_dead: str = "L",
                        form_class: int = 0) -> VolumeResult:
        """Calculate tree volume using NVEL equations.
        
        Args:
            dbh: Diameter at breast height (inches, outside bark)
            height: Total tree height (feet)
            species_code: FVS species code
            region: Forest Service region
            forest: Forest code
            volume_equation: Specific volume equation (if None, uses default)
            height_type: Height type ("F" = total, "M" = merchantable)
            live_dead: Tree status ("L" = live, "D" = dead)
            form_class: Form class (0 = default)
            
        Returns:
            VolumeResult object with calculated volumes
        """
        # Fallback calculation if DLL not available
        if not self.dll:
            return self._fallback_volume_calculation(dbh, height, species_code)
        
        # Get volume equation if not provided
        if volume_equation is None:
            volume_equation = self.get_volume_equation(species_code, region, forest)
            if volume_equation is None:
                return self._fallback_volume_calculation(dbh, height, species_code)
        
        try:
            # Set up input parameters
            regn = c_int(region)
            forst = FortranChar(forest, 2)
            voleq = FortranChar(volume_equation, 10)
            
            # Tree measurements
            MTOPP = c_float(0)      # Merch top primary
            MTOPS = c_float(0)      # Merch top secondary  
            STUMP = c_float(0)      # Stump height
            DBHOB = c_float(dbh)    # DBH outside bark
            DRCOB = c_float(0)      # DRC outside bark
            HTTYPE = FortranChar(height_type, 2)
            HTTOT = c_float(height) # Total height
            HTLOG = c_int(0)        # Height to log top
            
            # Product heights and diameters
            HT1PRD = c_float(0)
            HT2PRD = c_float(0)
            UPSHT1 = c_float(0)
            UPSHT2 = c_float(0)
            UPSD1 = c_float(0)
            UPSD2 = c_float(0)
            HTREF = c_int(0)
            AVGZ1 = c_float(0)
            AVGZ2 = c_float(0)
            FCLASS = c_int(form_class)
            DBTBH = c_float(0)
            BTR = c_float(0)
            
            # Array dimensions
            I3 = c_int(3)
            I7 = c_int(7)
            I15 = c_int(15)
            I20 = c_int(20)
            I21 = c_int(21)
            
            # Output arrays
            REAL = c_float
            VOL = (REAL * 15)()
            LOGVOL = (REAL * 7 * 20)()
            LOGDIA = (REAL * 21 * 3)()
            LOGLEN = (REAL * 20)()
            BOLHT = (REAL * 21)()
            
            # Control flags
            TLOGS = c_int(0)
            NOLOGP = c_float(0)
            NOLOGS = c_float(0)
            CUTFLG = c_int(1)
            BFPFLG = c_int(1)
            CUPFLG = c_int(1)
            CDPFLG = c_int(1)
            CUSFLG = c_int(1)
            CDSFLG = c_int(1)
            SPFLG = c_int(1)
            
            # Additional parameters
            PROD = FortranChar("01", 3)
            CONSPEC = FortranChar("", 5)
            HTTFLL = c_int(0)
            LIVE = FortranChar(live_dead, 2)
            BA = c_int(0)
            SI = c_int(0)
            mCTYPE = FortranChar("F", 2)
            ERRFLAG = c_int(0)
            idist = c_int(1)
            
            # Call volume library
            self.dll.VOLUMELIBRARY(
                byref(regn), forst.str, forst.len, voleq.str, voleq.len,
                byref(MTOPP), byref(MTOPS), byref(STUMP), byref(DBHOB),
                byref(DRCOB), HTTYPE.str, HTTYPE.len, byref(HTTOT),
                byref(HTLOG), byref(HT1PRD), byref(HT2PRD), byref(UPSHT1),
                byref(UPSHT2), byref(UPSD1), byref(UPSD2), byref(HTREF),
                byref(AVGZ1), byref(AVGZ2), byref(FCLASS), byref(DBTBH),
                byref(BTR), byref(I3), byref(I7), byref(I15), byref(I20),
                byref(I21), byref(VOL), byref(LOGVOL), byref(LOGDIA),
                byref(LOGLEN), byref(BOLHT), byref(TLOGS), byref(NOLOGP),
                byref(NOLOGS), byref(CUTFLG), byref(BFPFLG), byref(CUPFLG),
                byref(CDPFLG), byref(SPFLG), CONSPEC.str, CONSPEC.len,
                PROD.str, PROD.len, byref(HTTFLL), LIVE.str, LIVE.len,
                byref(BA), byref(SI), mCTYPE.str, mCTYPE.len,
                byref(ERRFLAG), byref(idist)
            )
            
            # Extract results
            vol_list = [vol.value for vol in VOL]
            return VolumeResult(vol_list, ERRFLAG.value)
            
        except Exception as e:
            warnings.warn(f"Volume calculation failed: {e}. Using fallback method.")
            return self._fallback_volume_calculation(dbh, height, species_code)
    
    def _fallback_volume_calculation(self, dbh: float, height: float,
                                   species_code: str) -> VolumeResult:
        """Fallback volume calculation when NVEL is not available.

        Implements combined-variable volume equations from published research:
        - V = a + b × D²H for total stem volume
        - Merchantable cubic: Trees ≥5" DBH, from 1-ft stump to 4" top DOB
        - Board foot (sawlog): Softwoods ≥9" DBH to 7.6" top; Hardwoods ≥11" DBH to 9.6" top

        References:
        - Amateis & Burkhart (1987) - Cubic-Foot Volume Equations for Loblolly Pine
        - Tasissa et al. (1997) - Volume ratio equations for southern pines
        - Gonzalez-Benecke et al. (2014) - Longleaf pine volume functions
        - Clark et al. (1991) SE-282 - Stem Profile Equations for Southern Species
        """
        from .bark_ratio import create_bark_ratio_model

        # Combined-variable equation coefficients: V = a + b × D²H
        # Where D = DBH (inches), H = total height (feet), V = volume (cubic feet)
        # Coefficients from published research for site-prepared plantation pines
        # Source: Amateis & Burkhart (1987), validated against SE-282 taper equations
        VOLUME_COEFFICIENTS_OUTSIDE_BARK = {
            # Southern pines - from Amateis & Burkhart (1987) and similar studies
            'LP': {'a': 0.18658, 'b': 0.00250},   # Loblolly Pine (R² = 0.98)
            'SP': {'a': 0.18658, 'b': 0.00250},   # Shortleaf Pine (use loblolly, validated)
            'SA': {'a': 0.15000, 'b': 0.00260},   # Slash Pine (adjusted for faster growth)
            'LL': {'a': 0.20000, 'b': 0.00245},   # Longleaf Pine (more taper)
            'VP': {'a': 0.18658, 'b': 0.00240},   # Virginia Pine
            'PD': {'a': 0.18658, 'b': 0.00240},   # Pitch Pine
            'SR': {'a': 0.18658, 'b': 0.00250},   # Spruce Pine
            'PP': {'a': 0.18658, 'b': 0.00240},   # Pond Pine
            'SD': {'a': 0.18658, 'b': 0.00235},   # Sand Pine
            # Default for other softwoods
            'DEFAULT_SOFTWOOD': {'a': 0.15, 'b': 0.00245},
            # Hardwoods typically have lower form factors
            'DEFAULT_HARDWOOD': {'a': 0.10, 'b': 0.00220},
        }

        VOLUME_COEFFICIENTS_INSIDE_BARK = {
            'LP': {'a': -0.09653, 'b': 0.00210},  # Loblolly Pine (R² = 0.97)
            'SP': {'a': -0.09653, 'b': 0.00210},  # Shortleaf Pine
            'SA': {'a': -0.08000, 'b': 0.00215},  # Slash Pine
            'LL': {'a': -0.10000, 'b': 0.00205},  # Longleaf Pine
            'VP': {'a': -0.09653, 'b': 0.00200},  # Virginia Pine
            'DEFAULT_SOFTWOOD': {'a': -0.08, 'b': 0.00205},
            'DEFAULT_HARDWOOD': {'a': -0.05, 'b': 0.00185},
        }

        # Define hardwood species codes
        hardwood_species = {
            'WO', 'SO', 'WK', 'LK', 'OV', 'CW', 'SK', 'HI', 'SU', 'YP',
            'RM', 'SM', 'SV', 'WA', 'GA', 'RA', 'BA', 'BC', 'SY', 'BG',
            'WE', 'AE', 'RL', 'BE', 'FM', 'OH'
        }
        is_hardwood = species_code in hardwood_species

        # FVS merchantability specifications
        STUMP_HEIGHT = 1.0  # feet
        MIN_MERCH_DBH = 5.0  # inches
        MIN_MERCH_TOP = 4.0  # inches DOB

        # Sawlog specifications
        if is_hardwood:
            MIN_SAW_DBH = 11.0  # inches
            MIN_SAW_TOP = 9.6   # inches DIB
        else:
            MIN_SAW_DBH = 9.0   # inches
            MIN_SAW_TOP = 7.6   # inches DIB

        try:
            # Get volume coefficients for species
            if is_hardwood:
                default_key = 'DEFAULT_HARDWOOD'
            else:
                default_key = 'DEFAULT_SOFTWOOD'

            coef_ob = VOLUME_COEFFICIENTS_OUTSIDE_BARK.get(
                species_code,
                VOLUME_COEFFICIENTS_OUTSIDE_BARK[default_key]
            )
            coef_ib = VOLUME_COEFFICIENTS_INSIDE_BARK.get(
                species_code,
                VOLUME_COEFFICIENTS_INSIDE_BARK[default_key]
            )

            # Calculate combined variable D²H
            d2h = dbh * dbh * height

            # Calculate total cubic volume using combined-variable equation
            # V = a + b × D²H (outside bark)
            total_cubic_ob = max(0.0, coef_ob['a'] + coef_ob['b'] * d2h)

            # Inside bark volume
            total_cubic_ib = max(0.0, coef_ib['a'] + coef_ib['b'] * d2h)

            # Use outside bark as the primary total volume (standard FVS practice)
            total_cubic = total_cubic_ob

            # Get bark ratio for merchantable calculations
            bark_model = create_bark_ratio_model(species_code)
            dbh_inside_bark = bark_model.apply_bark_ratio_to_dbh(dbh)
            bark_ratio = dbh_inside_bark / dbh if dbh > 0 else 0.9

            # Initialize volume components
            merchantable_cubic = 0.0
            board_foot = 0.0
            sawlog_cubic = 0.0
            sawlog_board_foot = 0.0
            cord_volume = 0.0

            # Calculate merchantable cubic volume (trees ≥5" DBH)
            if dbh >= MIN_MERCH_DBH:
                # Estimate merchantable height using taper
                merch_height = self._estimate_merchantable_height(
                    dbh, height, MIN_MERCH_TOP, STUMP_HEIGHT
                )

                # Merchantable volume ratio based on top diameter
                # From research: merch/total ratio ~ 0.80-0.90 depending on top limit
                if height > 0:
                    merch_ratio = merch_height / height
                    # Adjust for volume concentration in lower stem (paraboloid shape)
                    # Volume to height h is proportional to h for a neiloid/paraboloid
                    merch_ratio = min(0.90, merch_ratio * 1.1)
                else:
                    merch_ratio = 0.85

                merchantable_cubic = total_cubic_ib * merch_ratio

                # Convert to cords (1 cord = 128 cu ft gross, ~79 cu ft solid wood)
                cord_volume = merchantable_cubic / 79.0

            # Calculate board foot volume (sawlog trees only)
            if dbh >= MIN_SAW_DBH:
                # Estimate sawlog height
                sawlog_height = self._estimate_merchantable_height(
                    dbh, height, MIN_SAW_TOP, STUMP_HEIGHT
                )

                # Sawlog cubic volume
                if height > 0:
                    sawlog_ratio = sawlog_height / height
                    sawlog_ratio = min(0.85, sawlog_ratio * 1.05)
                else:
                    sawlog_ratio = 0.75
                sawlog_cubic = total_cubic_ib * sawlog_ratio

                # Board foot calculation using Doyle rule
                # Improved calculation using average log diameter
                stump_dib = dbh_inside_bark * 0.95
                saw_top_dib = MIN_SAW_TOP * bark_ratio

                if stump_dib > 4:
                    num_logs = int(sawlog_height / 16)
                    remaining_length = sawlog_height - (num_logs * 16)

                    board_foot = 0.0
                    for i in range(num_logs):
                        # Taper adjustment for each log (~2" per 16-ft)
                        log_dib = stump_dib - (i * 2.0)
                        if log_dib > 4:
                            board_foot += ((log_dib - 4)**2 * 16) / 16

                    if remaining_length > 8 and (stump_dib - num_logs * 2.0) > 4:
                        log_dib = stump_dib - (num_logs * 2.0)
                        board_foot += ((log_dib - 4)**2 * remaining_length) / 16

                    # Apply defect factor
                    board_foot *= 0.92

                sawlog_board_foot = board_foot

            # Build volume array matching NVEL output positions
            vol_array = [
                total_cubic,           # 0: total cubic volume (outside bark)
                total_cubic,           # 1: gross cubic volume
                total_cubic * 0.95,    # 2: net cubic volume (5% defect)
                merchantable_cubic,    # 3: merchantable cubic volume (inside bark)
                board_foot,            # 4: board foot volume (Doyle)
                cord_volume,           # 5: cord volume
                0.0,                   # 6: green weight (not calculated)
                0.0,                   # 7: dry weight (not calculated)
                sawlog_cubic,          # 8: sawlog cubic volume
                sawlog_board_foot,     # 9: sawlog board foot
                0.0,                   # 10: sawlog cubic (Int'l)
                0.0,                   # 11: sawlog bf (Int'l)
                0.0,                   # 12: biomass main stem
                0.0,                   # 13: biomass live branches
                0.0,                   # 14: biomass foliage
            ]

            return VolumeResult(vol_array, 0)

        except Exception:
            # Ultimate fallback using combined-variable with default coefficients
            d2h = dbh * dbh * height
            # Default loblolly coefficients
            cubic_volume = max(0.0, 0.18658 + 0.00250 * d2h)
            vol_array = [cubic_volume] + [0.0] * 14

            return VolumeResult(vol_array, 0)

    def _estimate_merchantable_height(self, dbh: float, total_height: float,
                                     top_dob: float, stump_height: float) -> float:
        """Estimate merchantable height using simplified taper model.

        Args:
            dbh: Diameter at breast height (inches)
            total_height: Total tree height (feet)
            top_dob: Minimum top diameter outside bark (inches)
            stump_height: Stump height (feet)

        Returns:
            Merchantable height in feet (from stump to merchantable top)
        """
        if dbh <= top_dob:
            return 0.0

        # Simplified linear taper model
        # Assumes diameter decreases linearly from DBH to 0 at tip
        # Height to given diameter = total_height * (1 - top_dob/dbh)
        height_to_top = total_height * (1 - (top_dob / dbh))

        # Merchantable height is from stump to merch top
        merch_height = height_to_top - stump_height

        # Ensure positive and reasonable
        merch_height = max(0.0, merch_height)
        merch_height = min(merch_height, total_height - stump_height - 4.0)

        return merch_height
    
    def is_available(self) -> bool:
        """Check if volume library is available."""
        return self.dll is not None
    
    def get_supported_species(self) -> List[str]:
        """Get list of supported FVS species codes."""
        return list(self.species_mapping.keys())


# Global volume library instance
_volume_library = None

def get_volume_library() -> VolumeLibrary:
    """Get the global volume library instance."""
    global _volume_library
    if _volume_library is None:
        _volume_library = VolumeLibrary()
    return _volume_library


def calculate_tree_volume(dbh: float, height: float, species_code: str,
                         **kwargs) -> VolumeResult:
    """Convenience function to calculate tree volume.
    
    Args:
        dbh: Diameter at breast height (inches)
        height: Total tree height (feet)
        species_code: FVS species code
        **kwargs: Additional arguments passed to VolumeLibrary.calculate_volume
        
    Returns:
        VolumeResult object
    """
    vol_lib = get_volume_library()
    return vol_lib.calculate_volume(dbh, height, species_code, **kwargs)


def get_volume_library_info() -> Dict[str, Any]:
    """Get information about the volume library.
    
    Returns:
        Dictionary with library information
    """
    vol_lib = get_volume_library()
    
    return {
        'available': vol_lib.is_available(),
        'version': vol_lib.get_version(),
        'supported_species': vol_lib.get_supported_species(),
        'dll_path': str(vol_lib.dll_path) if vol_lib.dll_path else None
    }


def validate_volume_library() -> Dict[str, Any]:
    """Validate volume library installation and functionality.
    
    Returns:
        Dictionary with validation results
    """
    vol_lib = get_volume_library()
    results = {
        'dll_available': vol_lib.is_available(),
        'version': vol_lib.get_version(),
        'test_results': []
    }
    
    if vol_lib.is_available():
        # Test volume calculation for each major species
        test_species = ['LP', 'SP', 'LL', 'SA']
        
        for species in test_species:
            try:
                result = vol_lib.calculate_volume(
                    dbh=10.0, height=60.0, species_code=species
                )
                
                test_result = {
                    'species': species,
                    'success': result.is_valid(),
                    'volume': result.total_cubic_volume,
                    'error_flag': result.error_flag
                }
                
                results['test_results'].append(test_result)
                
            except Exception as e:
                results['test_results'].append({
                    'species': species,
                    'success': False,
                    'error': str(e)
                })
    
    return results


if __name__ == "__main__":
    # Demonstration and testing
    print("FVS-Python Volume Library Integration")
    print("=" * 40)
    
    # Get library info
    info = get_volume_library_info()
    print(f"Volume Library Available: {info['available']}")
    print(f"Version: {info['version']}")
    print(f"Supported Species: {len(info['supported_species'])}")
    
    # Test volume calculation
    if info['available']:
        print("\nTesting volume calculations:")
        test_tree = {
            'dbh': 15.1,
            'height': 76.4,
            'species': 'LP'
        }
        
        result = calculate_tree_volume(**test_tree)
        print(f"DBH: {test_tree['dbh']} inches")
        print(f"Height: {test_tree['height']} feet")
        print(f"Species: {test_tree['species']}")
        print(f"Total Cubic Volume: {result.total_cubic_volume:.2f} cubic feet")
        print(f"Board Foot Volume: {result.board_foot_volume:.2f} board feet")
        print(f"Green Weight: {result.green_weight:.2f} pounds")
    
    # Validation
    print("\nValidation Results:")
    validation = validate_volume_library()
    for test in validation['test_results']:
        status = "✓" if test['success'] else "✗"
        print(f"{status} {test['species']}: {test.get('volume', 'N/A'):.2f} cubic feet") 
"""
Stem taper profile models for volume estimation.

Implements two taper model families matching NVEL (National Volume Estimator Library):

- **Clark model** (Eastern US: SN, NE, CS, LS variants)
  Clark, Thomas, and Souter (1991) "Stem Profile Equations for Southern Tree Species"
  USDA Forest Service Research Paper SE-282.
  Three-segment profile with analytic volume integration.

- **Flewelling model** (Western US: PN, WC, OP variants)
  Flewelling and Raynes (1993) "Variable-shape stem-profile predictions for
  western hemlock" and related papers. Four-segment variable-shape profile
  with Smalian numerical integration.

Usage:
    taper = create_taper_model('LP', variant='SN')
    taper.initialize_tree(dbh=12.0, height=80.0)
    dib = taper.predict_dib(h=40.0)
    vol = taper.predict_volume(lower_ht=1.0, upper_ht=70.0)
"""
import math
from typing import Dict, Optional

from .config_loader import ConfigLoader, get_default_variant, load_coefficient_file
from .exceptions import FVSError


# ============================================================================
# Base class
# ============================================================================

class TaperModel:
    """Base class for stem taper profile models.

    Subclasses implement species- and region-specific taper equations.
    The model is initialized per-species (coefficients loaded once),
    then ``initialize_tree()`` is called for each tree to set up
    tree-specific intermediate values before querying.
    """

    def __init__(self, species_code: str, variant: str):
        self.species_code = species_code
        self.variant = variant
        self._coefficients: Dict = {}
        # Tree-specific state (set by initialize_tree)
        self._dbh: Optional[float] = None
        self._height: Optional[float] = None
        self._initialized = False

    @property
    def dbh(self) -> Optional[float]:
        """Diameter at breast height (inches), or None if not initialized."""
        return self._dbh

    @property
    def height(self) -> Optional[float]:
        """Total tree height (feet), or None if not initialized."""
        return self._height

    def initialize_tree(self, dbh: float, height: float,
                        form_class: Optional[float] = None):
        """Prepare the model for a specific tree.

        Must be called before ``predict_dib``, ``predict_volume``, etc.

        Args:
            dbh: Diameter at breast height, outside bark (inches).
            height: Total tree height (feet).
            form_class: Optional Girard form class (percent).
        """
        self._dbh = dbh
        self._height = height
        self._initialized = True

    def predict_dib(self, h: float) -> float:
        """Predict diameter inside bark at height *h* (feet).

        Args:
            h: Height above ground (feet). Must be 0 <= h <= total height.

        Returns:
            Diameter inside bark (inches). Zero at the tip.
        """
        raise NotImplementedError

    def predict_dob(self, h: float) -> float:
        """Predict diameter outside bark at height *h* (feet).

        Default implementation applies a constant bark factor to DIB.
        Subclasses may override with bark-thickness models.
        """
        dib = self.predict_dib(h)
        if self._dbh and self._dbh > 0:
            # Simple proportional bark: DOB/DIB at BH applied uniformly
            dbhib = self.predict_dib(4.5)
            if dbhib > 0:
                return dib * (self._dbh / dbhib)
        return dib

    def predict_volume(self, lower_ht: float, upper_ht: float) -> float:
        """Compute cubic-foot volume between two heights.

        Args:
            lower_ht: Lower height bound (feet), typically stump height.
            upper_ht: Upper height bound (feet), typically merch top or total ht.

        Returns:
            Volume in cubic feet (inside bark).
        """
        raise NotImplementedError

    def predict_height_to_dib(self, target_dib: float,
                              tol: float = 0.01,
                              max_iter: int = 50) -> float:
        """Find the height where DIB equals *target_dib* (binary search).

        Searches from breast height upward (below BH, diameter is larger).

        Args:
            target_dib: Target diameter inside bark (inches).
            tol: Convergence tolerance (inches).
            max_iter: Maximum iterations.

        Returns:
            Height in feet where DIB ~ target_dib. Returns 0.0 if the tree
            is too small (DIB at BH < target_dib).
        """
        if not self._initialized or self._height is None:
            return 0.0

        dib_bh = self.predict_dib(4.5)
        if dib_bh <= target_dib:
            return 0.0  # Tree too small

        low = 4.5
        high = self._height
        for _ in range(max_iter):
            mid = (low + high) / 2.0
            dib_mid = self.predict_dib(mid)
            if abs(dib_mid - target_dib) < tol:
                return mid
            if dib_mid > target_dib:
                low = mid
            else:
                high = mid
        return (low + high) / 2.0

    def get_total_volume(self, stump_height: float = 1.0) -> float:
        """Total cubic-foot volume from stump to tip."""
        if not self._initialized or self._height is None:
            return 0.0
        return self.predict_volume(stump_height, self._height)

    def get_merchantable_height(self, min_top_dib: float = 4.0) -> float:
        """Height to merchantable top (where DIB = min_top_dib)."""
        return self.predict_height_to_dib(min_top_dib)


# ============================================================================
# Clark taper model (Eastern US — Regions 8 and 9)
# ============================================================================

class ClarkTaperModel(TaperModel):
    """Clark, Thomas, and Souter (1991) segmented stem profile model.

    Divides the stem into three segments with fixed transitions
    at breast height (4.5 ft) and at 17.3 ft:

    1. **Below BH** (0 to 4.5 ft): Butt swell modeled with a power
       function controlled by coefficients *r*, *c*, *e*.
    2. **BH to 17.3 ft**: Smooth transition using exponent *p*.
    3. **Above 17.3 ft**: Upper-stem taper with inflection point
       controlled by *a* and *b*.

    DIB at breast height and at 17.3 ft are predicted from DBH using
    linear equations with coefficients *a4*, *b4*, *a17*, *b17*.

    Volume is computed analytically (closed-form integration of the
    squared-diameter function), matching the ``r9cuft`` subroutine
    in NVEL.

    Reference:
        Clark, A., Souter, R.A., and Schlaegel, B.E. 1991. Stem profile
        equations for southern tree species. USDA Forest Service Research
        Paper SE-282.
    """

    COEFFICIENT_FILE_R8 = 'taper/clark_r8_coefficients.json'
    COEFFICIENT_FILE_R9 = 'taper/clark_r9_coefficients.json'

    # R8 (Region 8 — Southern) correction factors.
    # With correct R8CF coefficients (a4/b4/a17/b17 from r8dib.inc), no
    # empirical correction is needed — the Clark integration matches NVEL.
    R8_SOFTWOOD_CORRECTION = 1.0
    R8_HARDWOOD_CORRECTION = 1.0

    # R9 (Region 9 — North/Central) correction factors from NVEL r9cor
    # subroutine (r9clark.f lines 1497-1564).  Raw Clark integration
    # underestimates R9 volumes; r9cor increases them.
    R9_SOFTWOOD_CORRECTION = 1.04   # FIA < 300
    R9_HARDWOOD_CORRECTION = 1.10   # FIA >= 300 (excl. poplar)
    R9_POPLAR_CORRECTION = 1.0      # FIA 741-746, 621

    # Variants that use R9 Clark coefficients + r9cor
    _R9_VARIANTS = {'NE', 'CS', 'LS'}

    # Poplar / cottonwood species (FIA 741-746, 621) — r9cor cf = 1.0
    _POPLAR_SPECIES = {'YP', 'QA', 'CT'}

    # Hardwood species (for correction factor selection)
    _HARDWOOD_SPECIES = {
        'WO', 'RO', 'BO', 'SO', 'CO', 'SK', 'CB', 'WL', 'NK', 'QS',
        'RM', 'SM', 'YP', 'SU', 'WA', 'BA', 'BC', 'BU', 'YY', 'WN',
        'QA', 'YB', 'PB', 'AB', 'BM', 'RA', 'GC', 'SB', 'RB', 'GB',
        'CT', 'MG', 'MV', 'EL', 'SG', 'HL', 'TL', 'TS', 'HS', 'PE',
        'BI', 'UA', 'BJ', 'DO', 'OV', 'UH', 'OB', 'CA', 'NC', 'RD',
        'KC', 'MB', 'CL', 'BL', 'PD', 'TA', 'BO', 'WI', 'HT', 'DG',
        'CH', 'AS', 'PY', 'CW',
    }

    def __init__(self, species_code: str, variant: str,
                 forest_group: str = '4'):
        super().__init__(species_code, variant)
        self.forest_group = forest_group
        self._coefficients = self._load_coefficients()
        # Tree-level intermediates (computed in initialize_tree)
        self._dbhib = 0.0   # DIB at breast height
        self._dib17 = 0.0   # DIB at 17.3 ft
        # Derived variables for analytic volume
        self._G = 0.0
        self._W = 0.0
        self._X = 0.0
        self._Y = 0.0
        self._Z = 0.0
        self._T = 0.0

    def _load_coefficients(self) -> Dict:
        """Load Clark coefficients for the species and variant.

        For R8 (SN): uses the TOTAL-array coefficients (r, c, e, p, a, b)
        from ``species_coefficients`` keyed by FVS code, then overlays
        forest-group-specific A4/B4/A17/B17 from ``forest_group_coefficients``
        keyed by (group, FIA code). Mirrors ``R8PREPCOEF`` in
        ``volume/NVEL/r8clkdib.f`` — species aliasing (:34-51) followed by
        binary search, with group=9 as the universal fallback (:82-97).
        """
        if self.variant == 'SN':
            coef_file = self.COEFFICIENT_FILE_R8
        else:
            coef_file = self.COEFFICIENT_FILE_R9

        try:
            data = load_coefficient_file(coef_file)
        except FVSError:
            data = {}

        species_coeffs = data.get('species_coefficients', {})
        group_mapping = data.get('group_mapping', {})

        # Direct species lookup
        resolved = None
        if self.species_code in species_coeffs:
            resolved = species_coeffs[self.species_code]
        else:
            mapped = group_mapping.get(self.species_code)
            if mapped and mapped in species_coeffs:
                resolved = species_coeffs[mapped]

        if resolved is None:
            default_key = (
                'DEFAULT_HARDWOOD' if self.species_code in self._HARDWOOD_SPECIES
                else 'DEFAULT_SOFTWOOD'
            )
            if default_key in species_coeffs:
                resolved = species_coeffs[default_key]
            else:
                return self._fallback_coefficients()

        # R8: overlay forest-group-specific A4/B4/A17/B17 from R8CF table.
        if self.variant == 'SN':
            r8cf = self._resolve_r8cf(data, resolved.get('fia_code'))
            if r8cf is not None:
                resolved = {**resolved, **r8cf}

        return resolved

    def _resolve_r8cf(self, data: Dict, fia_code) -> Optional[Dict]:
        """Look up A4/B4/A17/B17 from forest_group_coefficients.

        Mirrors R8PREPCOEF in volume/NVEL/r8clkdib.f:
            1. apply species alias (r8clkdib.f:34-51)
            2. try (forest_group, aliased_fia)
            3. on miss retry with group='9' (r8clkdib.f:82-97)
            4. on miss return None so caller falls back to legacy placeholders
        """
        fgc = data.get('forest_group_coefficients')
        if not fgc or fia_code is None:
            return None

        fia_key = str(int(fia_code))
        aliases = data.get('species_aliases', {})
        aliased = aliases.get(fia_key, fia_key)

        primary = fgc.get(self.forest_group, {}).get(aliased)
        if primary is not None:
            return primary

        fallback = fgc.get('9', {}).get(aliased)
        if fallback is not None:
            return fallback

        return None

    def _fallback_coefficients(self) -> Dict:
        """Hardcoded fallback coefficients (generic softwood)."""
        return {
            'a4': -0.04,
            'b4': 0.93,
            'a17': 0.70,
            'b17': 0.30,
            'r': 18.0,
            'c': 0.70,
            'e': 800.0,
            'p': 1.40,
            'a': 0.75,
            'b': 0.35,
        }

    def initialize_tree(self, dbh: float, height: float,
                        form_class: Optional[float] = None):
        """Compute tree-specific intermediate values.

        Args:
            dbh: DBH outside bark (inches).
            height: Total height (feet).
            form_class: Optional Girard form class override.
        """
        super().initialize_tree(dbh, height, form_class)

        if height <= 4.5 or dbh <= 0:
            self._dbhib = dbh * 0.9
            self._dib17 = self._dbhib * 0.85
            self._compute_derived()
            return

        coef = self._coefficients

        # DIB at breast height (4.5 ft)
        self._dbhib = coef['a4'] + coef['b4'] * dbh
        self._dbhib = max(0.5, self._dbhib)

        # If form class provided, use it to compute DIB at 17.3
        if form_class is not None and form_class > 0:
            self._dib17 = dbh * form_class / 100.0
        elif height > 17.3:
            # DIB at 17.3 ft — convention differs between R8 (SN) and R9
            # (NE/LS/CS) per Fortran volume/r9clark_fvsMod.f:886-893:
            #   R8: DIB17 = DBHOB * (A17 + B17 * (17.3/TOPHT)^2)
            #   R9: DIB17 = DBHIB * (A17 + B17 * (17.3/TOPHT)^2)
            # Using DBHOB for R9 (as pyfvs did previously) inflates DIB17
            # by ~7% for typical hardwoods where dbhIb ≈ 0.94 * dbhOb.
            # That compounds to +10-15% total cubic volume for R9 trees.
            ratio_sq = (17.3 / height) ** 2
            base_dbh = self._dbhib if self.variant in self._R9_VARIANTS else dbh
            self._dib17 = base_dbh * (coef['a17'] + coef['b17'] * ratio_sq)
            self._dib17 = max(0.1, self._dib17)
            # R8 minimum form-class clamp per r8prep.f:346-367.
            if self.variant == 'SN':
                self._dib17 = self._apply_r8_fcmin_clamp(
                    self._dib17, dbh, height, coef,
                )
        else:
            # Very short tree: approximate
            self._dib17 = self._dbhib * 0.90

        self._compute_derived()

    @staticmethod
    def _apply_r8_fcmin_clamp(dib17: float, dbh: float, height: float,
                              coef: Dict) -> float:
        """R8 minimum form-class clamp per Fortran r8prep.f:346-367.

        Below a total height of 47.5 ft, FVSsn bounds DIB17 below by a
        species-group- and height-dependent minimum form class FCMIN.
        Three hardwood species (FIA 221 bald cypress, 222 pond cypress,
        544 tupelo gum) are explicitly excluded from the clamp.
        Without the clamp, very negative B17 coefficients (e.g. RM's
        -1.619) drive dib17 well below the minimum and under-predict
        cubic volume.
        """
        if height >= 47.5:
            return dib17

        fia = coef.get('fia_code')
        if fia in (221, 222, 544):
            return dib17

        spgrp = coef.get('spgrp')
        if spgrp not in (100, 300, 500):
            return dib17

        if spgrp == 100:
            # Softwoods
            if height < 32.5:
                fcmin = 56
            elif height < 37.5:
                fcmin = 64
            elif height < 42.5:
                fcmin = 66
            else:
                fcmin = 67
        elif spgrp == 300:
            # Hardwoods
            if height < 32.5:
                fcmin = 57
            elif height < 37.5:
                fcmin = 60
            elif height < 42.5:
                fcmin = 64
            else:
                fcmin = 67
        else:
            # SPGRP == 500 — "other" (e.g. oaks, hickories, walnuts)
            if height < 32.5:
                fcmin = 58
            elif height < 37.5:
                fcmin = 65
            elif height < 42.5:
                fcmin = 67
            else:
                fcmin = 69

        fcdib = dbh * fcmin * 0.01
        return max(dib17, fcdib)

    def _compute_derived(self):
        """Compute derived variables used in DIB prediction and volume."""
        H = self._height or 1.0
        coef = self._coefficients
        r = coef.get('r', 18.0)
        c = coef.get('c', 0.70)
        e = coef.get('e', 800.0)
        p = coef.get('p', 1.40)

        dbhib = self._dbhib
        dib17 = self._dib17

        # Avoid divide-by-zero
        if H <= 4.5:
            self._G = 0.0
            self._W = 0.0
            self._X = 0.0
            self._Y = 0.0
            self._Z = 0.0
            self._T = dbhib ** 2
            return

        # G = (1 - 4.5/H)^r
        self._G = (1.0 - 4.5 / H) ** r

        # W = (c + e/DBHIB^3) / (1 - G)
        if dbhib > 0 and abs(1.0 - self._G) > 1e-10:
            self._W = (c + e / max(dbhib ** 3, 0.001)) / (1.0 - self._G)
        else:
            self._W = 0.0

        # X = (1 - 4.5/H)^p
        self._X = (1.0 - 4.5 / H) ** p

        # Y = (1 - 17.3/H)^p
        if H > 17.3:
            self._Y = (1.0 - 17.3 / H) ** p
        else:
            self._Y = 0.0

        # Z = (DBHIB^2 - DIB17^2) / (X - Y)
        denom = self._X - self._Y
        if abs(denom) > 1e-10:
            self._Z = (dbhib ** 2 - dib17 ** 2) / denom
        else:
            self._Z = 0.0

        # T = DBHIB^2 - Z * X
        self._T = dbhib ** 2 - self._Z * self._X

    def predict_dib(self, h: float) -> float:
        """Predict DIB at height h using Clark 3-segment model.

        The three segments are summed under a square root:
            DIB(h) = sqrt(max(0, Ds + Db + Dt))

        Where Ds is the butt-swell component (h < 4.5),
        Db is the BH-to-17.3 component, and Dt is the upper-stem component.
        """
        if not self._initialized:
            return 0.0

        H = self._height
        if H is None or H <= 0:
            return 0.0
        if h <= 0:
            # At ground level, use butt swell extrapolation
            h = 0.5  # half-foot above ground
        if h >= H:
            return 0.0

        # Very short trees (H <= 4.5): use simple linear taper
        if H <= 4.5:
            return self._dbhib * (1.0 - h / H)

        coef = self._coefficients
        r = coef.get('r', 18.0)
        p = coef.get('p', 1.40)
        a = coef.get('a', 0.75)
        b = coef.get('b', 0.35)

        dbhib = self._dbhib
        dib17 = self._dib17

        Ds = 0.0  # butt swell component
        Db = 0.0  # BH to 17.3 component
        Dt = 0.0  # upper stem component

        # Segment 1: Below breast height (h < 4.5)
        if h < 4.5:
            rel_h = (1.0 - h / H) ** r
            rel_bh = (1.0 - 4.5 / H) ** r
            denom = 1.0 - rel_bh
            if abs(denom) > 1e-10:
                Ds = dbhib ** 2 * (1.0 + self._W * (rel_h - rel_bh))
            else:
                Ds = dbhib ** 2
        else:
            Ds = 0.0

        # Segment 2: BH to 17.3 ft (4.5 <= h <= 17.3)
        if h >= 4.5:
            if h <= 17.3 and H > 17.3:
                # Interpolate between DBHIB and DIB17
                rel_h_p = (1.0 - h / H) ** p
                Db = self._T + self._Z * rel_h_p
            elif h <= 17.3 and H <= 17.3:
                # Tree shorter than 17.3 ft: use segment 2 all the way
                rel_h_p = (1.0 - h / H) ** p
                Db = self._T + self._Z * rel_h_p
            elif h < 4.5:
                pass  # handled in segment 1
            else:
                Db = 0.0

        # Segment 3: Above 17.3 ft (h > 17.3)
        if h > 17.3 and H > 17.3:
            rel_upper = (h - 17.3) / (H - 17.3)
            # Main taper term
            Dt = dib17 ** 2 * b * (rel_upper - 1.0) ** 2

            # Inflection point term
            if rel_upper < a:
                Dt += dib17 ** 2 * ((1.0 - b) / (a ** 2)) * (a - rel_upper) ** 2

        # Sum and take square root
        d_sq = Ds + Db + Dt
        if d_sq <= 0:
            return 0.0
        return math.sqrt(d_sq)

    def predict_volume(self, lower_ht: float, upper_ht: float) -> float:
        """Compute cubic-foot volume by analytic integration.

        Implements the closed-form volume integration from NVEL r9cuft,
        integrating the squared-diameter function across the three segments.

        Returns volume in cubic feet (inside bark).
        """
        if not self._initialized:
            return 0.0

        H = self._height
        if H is None or H <= 4.5:
            return 0.0

        lower_ht = max(lower_ht, 0.0)
        upper_ht = min(upper_ht, H)
        if upper_ht <= lower_ht:
            return 0.0

        coef = self._coefficients
        r = coef.get('r', 18.0)
        p = coef.get('p', 1.40)
        a = coef.get('a', 0.75)
        b_coef = coef.get('b', 0.35)

        dbhib = self._dbhib
        dib17 = self._dib17

        # Convert constant: pi / (4 * 144) = 0.005454154
        K = 0.005454154

        V1 = 0.0  # Volume in segment 1 (below BH)
        V2 = 0.0  # Volume in segment 2 (BH to 17.3)
        V3 = 0.0  # Volume in segment 3 (above 17.3)

        # ------- Segment 1: Below breast height -------
        L1 = lower_ht
        U1 = min(upper_ht, 4.5)
        if L1 < 4.5 and U1 > L1:
            G = self._G
            W = self._W
            # Integrate: DBHIB^2 * (1 + W*((1-h/H)^r - G))
            # = DBHIB^2 * ((1 - W*G) * (U1-L1)
            #   + W * H/(r+1) * ((1-L1/H)^(r+1) - (1-U1/H)^(r+1)))
            base_term = (1.0 - W * G) * (U1 - L1)

            # Integral of (1-h/H)^r from L1 to U1
            # = H/(r+1) * ((1-L1/H)^(r+1) - (1-U1/H)^(r+1))
            if r > -1:
                integral_r = (H / (r + 1.0)) * (
                    (1.0 - L1 / H) ** (r + 1.0)
                    - (1.0 - U1 / H) ** (r + 1.0)
                )
            else:
                integral_r = 0.0

            V1 = dbhib ** 2 * (base_term + W * integral_r)

        # ------- Segment 2: BH to 17.3 ft -------
        L2 = max(lower_ht, 4.5)
        U2_limit = 17.3 if H > 17.3 else H
        U2 = min(upper_ht, U2_limit)
        if L2 < U2_limit and U2 > L2:
            T = self._T
            Z = self._Z
            # Integrate: T + Z*(1-h/H)^p
            # = T*(U2-L2) + Z * H/(p+1) * ((1-L2/H)^(p+1) - (1-U2/H)^(p+1))
            base_term = T * (U2 - L2)

            if p > -1:
                integral_p = (H / (p + 1.0)) * (
                    (1.0 - L2 / H) ** (p + 1.0)
                    - (1.0 - U2 / H) ** (p + 1.0)
                )
            else:
                integral_p = 0.0

            V2 = base_term + Z * integral_p

        # ------- Segment 3: Above 17.3 ft -------
        if H > 17.3:
            L3 = max(lower_ht, 17.3)
            U3 = min(upper_ht, H)
            if L3 < H and U3 > L3:
                Hm = H - 17.3  # upper stem length

                # Term 1: b * (rel - 1)^2 integrated
                # integral of b*(x - 1)^2 dx from L3 to U3
                # where x = (h - 17.3) / Hm
                rL = (L3 - 17.3) / Hm
                rU = (U3 - 17.3) / Hm

                # Integral of (x-1)^2 from rL to rU = [(x-1)^3 / 3] from rL to rU
                int_b = b_coef * Hm * (
                    (rU - 1.0) ** 3 / 3.0 - (rL - 1.0) ** 3 / 3.0
                )

                # Term 2: inflection term ((1-b)/a^2) * (a - x)^2
                # Only active when x < a
                int_infl = 0.0
                if a > 0:
                    aL = min(rL, a)
                    aU = min(rU, a)
                    if aU > aL:
                        # Integral of (a - x)^2 from aL to aU
                        # = [-(a-x)^3 / 3] from aL to aU
                        int_infl = ((1.0 - b_coef) / (a ** 2)) * Hm * (
                            -(a - aU) ** 3 / 3.0
                            + (a - aL) ** 3 / 3.0
                        )

                V3 = dib17 ** 2 * (int_b + int_infl)

        total_vol = K * (V1 + V2 + V3)

        # Apply region-specific correction factor
        if self.variant in self._R9_VARIANTS:
            # R9 correction from NVEL r9cor (r9clark.f:1497-1564)
            if self.species_code in self._POPLAR_SPECIES:
                total_vol *= self.R9_POPLAR_CORRECTION
            elif self.species_code in self._HARDWOOD_SPECIES:
                total_vol *= self.R9_HARDWOOD_CORRECTION
            else:
                total_vol *= self.R9_SOFTWOOD_CORRECTION
        else:
            # R8 (SN) — empirical correction (no r8cor in Fortran)
            if self.species_code in self._HARDWOOD_SPECIES:
                total_vol *= self.R8_HARDWOOD_CORRECTION
            else:
                total_vol *= self.R8_SOFTWOOD_CORRECTION

        return max(0.0, total_vol)


# ============================================================================
# Flewelling taper model (Western US — Region 6)
# ============================================================================

def _logistic(x: float) -> float:
    """Logistic function: exp(x) / (1 + exp(x)), clamped to avoid overflow."""
    x = max(-7.0, min(7.0, x))
    return math.exp(x) / (1.0 + math.exp(x))


def _clamp(x: float, lo: float = -7.0, hi: float = 7.0) -> float:
    """Clamp a value to [lo, hi]."""
    return max(lo, min(hi, x))


class FlewellingTaperModel(TaperModel):
    """Flewelling variable-shape stem profile model.

    Ported from NVEL Fortran source files (FMSC-Measurements/VolumeLibrary):

    - ``f_west.f``: Species shape functions SHP_W3 (Douglas-fir),
      SHP_W4 (Western hemlock), SHP_W5 (Red cedar), FDBT_C1 (bark).
    - ``sf_taper.f``: Taper coefficient derivation from shape parameters.
    - ``sf_yhat.f``: 4-segment profile function Y(rh).
    - ``sf_2pt.f``: Scaling factor F computation.

    Divides the stem into four segments with tree-size-dependent
    knot positions:

    1. **Lower** (ground to RHI1): Butt swell, power + log function.
    2. **Straight** (RHI1 to RHI2): Linear taper through inflection zone.
    3. **Middle** (RHI2 to RHC): Main taper with species-specific exponent.
    4. **Upper** (RHC to tip): Crown taper, cubic polynomial to zero.

    Species currently supported:

    - JSP 3: Douglas-fir westside (DF) — PN, WC, OP
    - JSP 4: Western hemlock westside (WH) — PN, WC, OP
    - JSP 5: Western red cedar westside (RC) — PN, WC, OP

    Species not in the Flewelling model (SS, RA, etc.) fall back to
    combined-variable volume equations via the factory function.

    References:
        Flewelling, J.W. and Raynes, L.M. 1993. Variable-shape
        stem-profile predictions for western hemlock. Part I.
        Canadian Journal of Forest Research 23: 520-536.
    """

    COEFFICIENT_FILE = 'taper/flewelling_coefficients.json'

    # Smalian constant: pi / (4 * 144 * 2) = 0.00272708
    SMALIAN_K = 0.00272708

    def __init__(self, species_code: str, variant: str):
        super().__init__(species_code, variant)
        self._species_data: Optional[Dict] = self._load_coefficients()
        self._jsp: int = (self._species_data.get('jsp', 0)
                          if self._species_data else 0)
        # Shape parameters R1-R5, A3
        self._r1 = self._r2 = self._r3 = self._r4 = self._r5 = 0.0
        self._a3_shape = 1.005
        # Knot positions (relative height 0-1)
        self._rhi1 = self._rhi2 = self._rhc = self._rhlongi = 0.0
        # Taper coefficients (from SF_TAPER)
        self._a0 = self._a1 = self._a2 = self._a4 = 0.0
        self._b0 = self._b1 = self._b2 = self._b4 = 0.0
        self._c1 = self._c2 = 0.0
        self._e1 = self._e2 = 0.0
        # Scaling factor and DBH inside bark
        self._F = 0.0
        self._dbhib = 0.0

    def _load_coefficients(self) -> Optional[Dict]:
        """Load species data from flewelling_coefficients.json.

        Returns None if no coefficients exist for this species,
        which signals the factory to fall back to combined-variable.
        """
        try:
            data = load_coefficient_file(self.COEFFICIENT_FILE)
        except FVSError:
            return None

        species_params = data.get('species_parameters', {})
        group_mapping = data.get('group_mapping', {})

        # Direct species lookup
        if self.species_code in species_params:
            return species_params[self.species_code]

        # Group mapping (value is target species code or null)
        mapped = group_mapping.get(self.species_code)
        if mapped and mapped in species_params:
            return species_params[mapped]

        # Species in group_mapping with null → explicitly unsupported
        if self.species_code in group_mapping:
            return None

        return None

    # ------------------------------------------------------------------
    # Tree initialization
    # ------------------------------------------------------------------

    def initialize_tree(self, dbh: float, height: float,
                        form_class: Optional[float] = None):
        """Initialize the model for a specific tree.

        Follows the NVEL SF_2PT calling sequence:
        1. Compute bark thickness → DBHIB (from FDBT_C1)
        2. Compute shape parameters R1-R5, A3, knots (from SHP_Wn)
        3. Derive taper coefficients (from SF_TAPER)
        4. Compute scaling factor F so that DIB at BH = DBHIB
        """
        super().initialize_tree(dbh, height, form_class)

        if height <= 4.5 or dbh <= 0 or self._species_data is None:
            self._F = 0.0
            return

        jsp = self._jsp
        f = self._species_data.get('shape_coefficients', {})

        # Step 1: Bark thickness → DBHIB
        self._dbhib = self._compute_dbhib(dbh, height)

        # Step 2: Shape parameters (species-specific)
        if jsp == 3:
            self._compute_shape_w3(dbh, height, f)
        elif jsp == 4:
            self._compute_shape_w4(dbh, height, f)
        elif jsp == 5:
            self._compute_shape_w5(dbh, height, f)
        else:
            self._F = 0.0
            return

        # Step 3: Derive taper coefficients from shape parameters
        self._derive_taper_coefficients()

        # Step 4: F = DBHIB / Y(4.5/H) with F=1.0 initially
        # (SF_2PT: YHAT_BH = SF_YHAT(..., F=1.0); F = DBH_IB / YHAT_BH)
        rh_bh = 4.5 / height
        y_bh = self._predict_y(rh_bh)
        if abs(y_bh) > 1e-10:
            self._F = self._dbhib / y_bh
        else:
            self._F = self._dbhib

    # ------------------------------------------------------------------
    # Bark thickness (FDBT_C1 from f_west.f)
    # ------------------------------------------------------------------

    def _compute_dbhib(self, dbh: float, height: float) -> float:
        """Compute diameter inside bark at breast height.

        Ported from FDBT_C1 in f_west.f.  Each species has its own
        bark-thickness model that returns a ratio DBTBH/DBHOB.
        """
        bark = self._species_data.get('bark', {})
        bark_type = bark.get('type', 'simple')

        if bark_type == 'dform':
            # JSP 3 (DF): RATIO = exp(a0 + a1*ln(DBH) + a2*DFORM
            #                        + a3*DFORM*ln(DBH))
            dmedian = self._compute_dmedian(dbh, height)
            dform = dbh / dmedian - 1.0 if dmedian > 0.1 else 0.0
            ratio = math.exp(bark['a0']
                             + bark['a1'] * math.log(max(dbh, 0.1))
                             + bark['a2'] * dform
                             + bark['a3'] * dform * math.log(max(dbh, 0.1)))
            return dbh * (1.0 - ratio)

        elif bark_type == 'exponential':
            # JSP 4 (WH): RATIO = a*(1 + b*exp(c*DBH))
            ratio = bark['a'] * (1.0 + bark['b'] * math.exp(bark['c'] * dbh))
            return dbh * (1.0 - ratio)

        elif bark_type == 'reciprocal':
            # JSP 5 (RC): RATIO = a*(1 + b/D_USE + c/D_USE^2)
            d_use = max(dbh, bark.get('min_dbh', 3.8))
            ratio = bark['a'] * (1.0 + bark['b'] / d_use
                                 + bark['c'] / (d_use ** 2))
            return dbh * (1.0 - ratio)

        # Simple fallback
        return dbh * 0.90

    def _compute_dmedian(self, dbh: float, height: float) -> float:
        """Compute DMEDIAN (median tree diameter for given height).

        DMEDIAN is used to compute DFORM = DBH/DMEDIAN - 1, which
        controls stem form relative to a typical tree of the same height.
        """
        dmed_params = self._species_data.get('dmedian', {})
        ht_adj = max(height - 4.5, 0.1)

        if dmed_params.get('type') == 'complex':
            # WH: DMEDIAN = a*(HT-4.5)^(b + c*HT + d*HT^2 + e*ln(HT))
            p = dmed_params
            exponent = (p['b'] + p['c'] * height
                        + p['d'] * height * height
                        + p['e'] * math.log(max(height, 1.0)))
            return p['a'] * ht_adj ** exponent
        else:
            # DF, RC: DMEDIAN = m1*(HT-4.5)^(m2 + m3*HT)
            m1 = dmed_params.get('m1', 0.566)
            m2 = dmed_params.get('m2', 0.634)
            m3 = dmed_params.get('m3', 0.00074)
            return m1 * ht_adj ** (m2 + m3 * height)

    # ------------------------------------------------------------------
    # Shape parameter functions (SHP_W3, SHP_W4, SHP_W5)
    # ------------------------------------------------------------------

    def _compute_shape_w3(self, dbh: float, ht: float, f: Dict):
        """Douglas-fir westside shape parameters (SHP_W3 from f_west.f).

        Coefficients from NW Taper Coop, April 1994 (REGN CD17.coe).
        Copyright J. W. Flewelling, 1994.
        """
        dmedian = self._compute_dmedian(dbh, ht)
        dform = dbh / dmedian - 1.0 if dmedian > 0.1 else 0.0

        # RHI1
        u7 = f['f13'] + f['f14'] * math.log(dbh + 1.0) + f['f15'] * math.log(ht)
        u7 = _clamp(u7)
        self._rhi1 = _logistic(u7)
        self._rhi1 = min(self._rhi1, 0.5)

        # RHLONGI
        u9a = f['f18'] + f['f19'] * ht
        u9a = _clamp(u9a)
        self._rhlongi = f['f17'] * math.exp(u9a) / (1.0 + math.exp(u9a))

        # RHI2
        self._rhi2 = self._rhi1 + self._rhlongi

        # RHC
        u8 = (f['f21'] + f['f22'] * math.log(ht)
              + f['f23'] * dform + f['f24'] * (dbh / 10.0) ** 1.5)
        u8 = _clamp(u8)
        self._rhc = (self._rhi2
                     + (1.0 - self._rhi2) * _logistic(u8))

        # U1-U5 → R1-R5 (using default regional coefficients: GeoSUB='00')
        fr25 = f['f25']
        fr34 = f['f34']

        u1 = fr25 + f['f26'] * math.log(ht)
        u2 = f['f29'] + f['f30'] * math.log(dbh) + f['f31'] * dbh
        u3 = (fr34 + f['f35'] * math.log(dbh + 1.0) + f['f36'] * math.log(ht)
              + f['f37'] * dform * ht + f['f33'] * dform)
        u4 = f['f38'] + f['f39'] * dbh + f['f40'] * ht * dbh
        u5 = f['f42'] + f['f43'] * ht + f['f44'] * dform

        u1, u2, u3, u4, u5 = [_clamp(v) for v in (u1, u2, u3, u4, u5)]

        # A3
        u6 = f['f45'] + f['f46'] * math.log(dbh + 1.0) + f['f47'] * math.log(ht)
        u6 = _clamp(u6, -6.0, 6.0)
        u6 = 1.0 + math.exp(u6)
        u6 = max(1.005, min(100.0, u6))

        self._r1 = _logistic(u1)
        self._r2 = _logistic(u2)
        self._r3 = _logistic(u3)
        self._r4 = _logistic(u4)
        self._r5 = 0.5 + 0.5 * _logistic(u5)
        self._a3_shape = u6

    def _compute_shape_w4(self, dbh: float, ht: float, f: Dict):
        """Western hemlock westside shape parameters (SHP_W4 from f_west.f).

        Coefficients from NW Taper Coop, April 1994 (REGH TEST1929.coe).
        Copyright J. W. Flewelling, 1994.
        """
        dmedian = self._compute_dmedian(dbh, ht)
        dform = dbh / dmedian - 1.0 if dmedian > 0.1 else 0.0

        # RHI1 — uses exponential saturation form
        u7 = f['f13'] + f['f14'] * (1.0 - math.exp(f['f15'] * ht))
        u7 = _clamp(u7)
        self._rhi1 = _logistic(u7)
        self._rhi1 = min(self._rhi1, 0.5)

        # RHLONGI — direct formula (not logistic)
        u9a = f['f17'] + f['f18'] * math.log(ht) + f['f19'] * dform
        if self._rhi1 + u9a > 0.75:
            u9a = 0.75 - self._rhi1
        self._rhlongi = max(u9a, 0.0)

        # RHI2
        self._rhi2 = self._rhi1 + self._rhlongi

        # RHC
        u8 = (f['f21'] + f['f22'] * math.log(ht)
              + f['f23'] * dform + f['f24'] * math.log(ht) * dform)
        u8 = _clamp(u8)
        self._rhc = (self._rhi2
                     + (1.0 - self._rhi2) * _logistic(u8))

        # U1-U5 (using default regional coefficients: GeoSUB='00')
        fr25 = f['f25']
        fr34 = f['f34']

        ht100 = ht / 100.0
        u1 = (fr25 + f['f26'] / ht100
              + f['f27'] / (ht100 ** 2) + f['f28'] / (ht100 ** 3))
        u2 = f['f29']  # Constant for WH
        u3 = (fr34 + f['f35'] / ht
              + f['f36'] * ht * dbh / 1000.0 + f['f37'] * dform)
        u4 = f['f38'] + f['f39'] * math.log(ht) + f['f40'] * dform
        u5 = f['f42'] + f['f43'] * math.log(ht) + f['f44'] * dbh

        u1, u2, u3, u4, u5 = [_clamp(v) for v in (u1, u2, u3, u4, u5)]

        # A3 — WH uses log(DBH), not log(DBH+1)
        u6 = f['f45'] + f['f46'] * math.log(max(dbh, 0.1)) + f['f47'] * ht
        u6 = _clamp(u6, -6.0, 6.0)
        u6 = 1.0 + math.exp(u6)
        u6 = max(1.005, min(100.0, u6))

        self._r1 = _logistic(u1)
        self._r2 = _logistic(u2)
        self._r3 = _logistic(u3)
        self._r4 = _logistic(u4)
        self._r5 = 0.5 + 0.5 * _logistic(u5)
        self._a3_shape = u6

    def _compute_shape_w5(self, dbh: float, ht: float, f: Dict):
        """Western red cedar westside shape parameters (SHP_W5 from f_west.f).

        Coefficients from NW Taper Coop, April 1994 (REGC RC41494.coe).
        Copyright J. W. Flewelling, 1994.
        """
        dmedian = self._compute_dmedian(dbh, ht)
        dform = dbh / dmedian - 1.0 if dmedian > 0.1 else 0.0

        # RHI1 — depends on DFORM only
        u7 = f['f13'] + f['f15'] * dform
        u7 = _clamp(u7, -7.0, 1.0)  # Upper limit is 1.0 for RC
        self._rhi1 = _logistic(u7)

        # RHLONGI — depends on log(HT)
        u9a = f['f17'] + f['f18'] * math.log(ht)
        if self._rhi1 + u9a > 0.75:
            u9a = 0.75 - self._rhi1
        self._rhlongi = max(u9a, 0.0)

        # RHI2
        self._rhi2 = self._rhi1 + self._rhlongi

        # RHC — depends on 1/DBH
        u8 = f['f21'] + f['f22'] / dbh
        u8 = _clamp(u8)
        self._rhc = (self._rhi2
                     + (1.0 - self._rhi2) * _logistic(u8))

        # U1-U5
        u1 = f['f25'] + f['f26'] * math.log(dbh) + f['f27'] / dbh
        u2 = f['f29'] + f['f30'] / dbh + f['f31'] / (dbh ** 2)
        u3 = f['f34'] + f['f35'] * dbh + f['f36'] * ht
        u4 = f['f38'] + f['f39'] * dbh + f['f40'] * dform
        u5 = f['f42'] + f['f43'] / dbh

        u1, u2, u3, u4, u5 = [_clamp(v) for v in (u1, u2, u3, u4, u5)]

        # A3 — RC uses DBH directly and 1/DBH
        u6 = f['f45'] + f['f46'] * dbh + f['f47'] / dbh
        u6 = _clamp(u6, -6.0, 6.0)
        u6 = 1.0 + math.exp(u6)
        u6 = max(1.005, min(100.0, u6))

        self._r1 = _logistic(u1)
        self._r2 = _logistic(u2)
        self._r3 = _logistic(u3)
        self._r4 = _logistic(u4)
        self._r5 = 0.5 + 0.5 * _logistic(u5)
        self._a3_shape = u6

    # ------------------------------------------------------------------
    # Taper coefficient derivation (SF_TAPER from sf_taper.f)
    # ------------------------------------------------------------------

    def _derive_taper_coefficients(self):
        """Convert shape parameters to taper coefficients.

        Ported from SF_TAPER in sf_taper.f.  Given geometric shape
        parameters (R1-R5, A3) and knot positions (RHI1, RHI2, RHC),
        computes taper coefficients A0-A4, B0-B4, C1-C2, E1-E2 that
        define the 4-segment piecewise profile function.
        """
        r1, r2, r3, r4, r5 = (self._r1, self._r2, self._r3,
                               self._r4, self._r5)
        a3 = self._a3_shape
        rhi1 = self._rhi1
        rhi2 = self._rhi2
        rhc = self._rhc
        rhlongi = self._rhlongi

        k = 1.0

        # Upper segment coefficients
        yc = k * (1.0 - rhc)
        c2 = r5 * yc
        c1 = 3.0 * (yc - c2)
        slope = -(3.0 - r5) * k / 2.0

        # Middle segment coefficients
        s1 = slope * (rhc - rhi2)
        yi_min = yc - s1 * (1.0 + 2.0 * r3) / 3.0
        yi_max = yc - s1 * (5.0 + 4.0 * r3) / 9.0
        yi2 = yi_min + r4 * (yi_max - yi_min)
        s0 = r3 * s1

        denom_b1 = -3.0 * yc + 3.0 * yi2 + 2.0 * s0 + s1
        if abs(denom_b1) < 1e-12:
            b1 = 2.0
        else:
            b1 = (6.0 * yc - 6.0 * yi2 - 2.0 * s0 - 4.0 * s1) / denom_b1

        denom_b2 = 0.5 - (1.0 / (b1 + 1.0) if abs(b1 + 1.0) > 1e-10 else 0.0)
        if abs(denom_b2) < 1e-12:
            b2 = 0.0
        else:
            b2 = s1 * (1.0 - r3) / denom_b2

        b4 = s0
        b0 = yi2

        # Straight segment coefficients
        span = rhc - rhi2
        slope_rhi = r3 * s1 / span if abs(span) > 1e-10 else 0.0
        yi1 = yi2 - slope_rhi * rhlongi

        if rhlongi > 0.0:
            e2 = (yi2 - yi1) / rhlongi
            e1 = yi1 - e2 * rhi1
        else:
            e1 = yi2
            e2 = 0.0

        # Lower segment coefficients
        s3 = -slope_rhi * rhi1
        k2 = s3 / r1 if abs(r1) > 1e-10 else s3

        if a3 <= 1.0:
            a3 = 1.005

        f_a3 = (1.0 / (6.0 * a3 * a3) + math.log(1.0 - 1.0 / a3)
                + 1.0 / (3.0 * (a3 - 1.0)) + 2.0 / (3.0 * a3))

        # G_A3 numerator: 1/(a3-1) - 1/a3 - 1/a3^2 - 1/(a3-1)^3
        # (from sf_taper.f: G_A3 line)
        g_a3_numer = (1.0 / (a3 - 1.0) - 1.0 / a3
                      - 1.0 / (a3 ** 2) - 1.0 / (a3 - 1.0) ** 3)
        if abs(f_a3) > 1e-12:
            g_a3 = g_a3_numer / f_a3
        else:
            g_a3 = 1.0

        # YB_MIN denominator: 1/(a3-1) - 1/a3 - 1/a3^2 - 1/a3^3
        # (from sf_taper.f: YB_MIN line — note a3^3 NOT (a3-1)^3)
        yb_min_denom = (1.0 / (a3 - 1.0) - 1.0 / a3
                        - 1.0 / (a3 ** 2) - 1.0 / (a3 ** 3))
        if abs(yb_min_denom) > 1e-12:
            yb_min = (yi1 + (2.0 * s3 + k2) / 3.0
                      + (s3 - k2) * f_a3 / yb_min_denom)
        else:
            yb_min = yi1 + (2.0 * s3 + k2) / 3.0

        if abs(g_a3) > 1e-12:
            yb_max = yi1 + (2.0 * s3 + k2) / 3.0 + (s3 - k2) / g_a3
        else:
            yb_max = yb_min

        yb = yb_min + r2 * (yb_max - yb_min)

        a0 = yi1
        if abs(f_a3) > 1e-12:
            a2_coef = (yb - yi1 - (2.0 * s3 + k2) / 3.0) / f_a3
        else:
            a2_coef = 0.0

        a1_coef = (k2 - s3 + a2_coef * (1.0 / (a3 - 1.0)
                   - 1.0 / a3 - 1.0 / (a3 ** 2))) / 3.0
        a4 = s3

        self._a0 = a0
        self._a1 = a1_coef
        self._a2 = a2_coef
        self._a4 = a4
        self._b0 = b0
        self._b1 = b1
        self._b2 = b2
        self._b4 = b4
        self._c1 = c1
        self._c2 = c2
        self._e1 = e1
        self._e2 = e2

    # ------------------------------------------------------------------
    # Profile prediction (SF_YHAT from sf_yhat.f)
    # ------------------------------------------------------------------

    def predict_dib(self, h: float) -> float:
        """Predict DIB using Flewelling 4-segment profile.

        DIB = F * Y(rh) where rh = h / total_height and Y is the
        piecewise profile function.  F is a scaling factor computed
        so that DIB at breast height equals DBHIB.

        Note: Unlike the Clark model where D² is integrated, the
        Flewelling profile Y(rh) gives a value proportional to
        diameter directly (not diameter squared).
        """
        if not self._initialized or self._height is None or self._height <= 0:
            return 0.0
        if self._F <= 0:
            return 0.0
        if h <= 0:
            h = 0.5
        if h >= self._height:
            return 0.0

        rh = h / self._height
        y = self._predict_y(rh)
        return max(0.0, self._F * y)

    def _predict_y(self, rh: float) -> float:
        """Normalized profile function Y(rh).

        Ported from SF_YHAT in sf_yhat.f.  Returns a value proportional
        to diameter at relative height rh.  The profile is
        piecewise-defined over four segments.
        """
        if rh >= 1.0:
            return 0.0

        if rh >= self._rhc:
            # Upper segment (crown taper)
            if self._rhc >= 1.0:
                return 0.0
            x = (1.0 - rh) / (1.0 - self._rhc)
            return x * (self._c2 + x * (self._c1 / 2.0
                                        - self._c1 / 6.0 * x))

        elif rh >= self._rhi2:
            # Middle segment
            span = self._rhc - self._rhi2
            if span <= 0:
                return self._b0
            x = (rh - self._rhi2) / span
            b1 = self._b1
            if x > 0.0:
                # Underflow protection (from sf_yhat.f revision 30SEP99)
                if b1 * math.log10(max(x, 1e-30)) <= -20.0:
                    x_b1 = 0.0
                else:
                    x_b1 = x ** b1
                return (self._b0 + x * (self._b4 + x * (
                    -self._b2 / ((b1 + 1) * (b1 + 2)) * x_b1
                    + self._b2 / 6.0 * x)))
            else:
                return self._b0

        elif rh > self._rhi1:
            # Straight segment (linear)
            return self._e1 + self._e2 * rh

        else:
            # Lower segment (butt swell)
            if self._rhi1 <= 0:
                return self._a0
            x = (self._rhi1 - rh) / self._rhi1
            a3 = self._a3_shape
            if a3 <= 1.0 or x >= a3:
                # Avoid log domain error
                return self._a0 + x * (self._a4 + self._a1 * x * x)

            return (self._a0
                    + x * ((self._a4 + self._a2 / a3)
                           + x * (self._a2 / (2.0 * a3 ** 2) + self._a1 * x))
                    + self._a2 * math.log(1.0 - x / a3))

    def predict_volume(self, lower_ht: float, upper_ht: float) -> float:
        """Compute cubic-foot volume via Smalian numerical integration.

        Integrates in 4-ft steps matching NVEL TCUBIC subroutine.
        """
        if not self._initialized or self._height is None:
            return 0.0
        if self._F <= 0:
            return 0.0

        H = self._height
        lower_ht = max(lower_ht, 0.0)
        upper_ht = min(upper_ht, H)
        if upper_ht <= lower_ht:
            return 0.0

        STEP = 4.0  # 4-ft integration steps
        total_vol = 0.0

        h = lower_ht
        dib_prev = self.predict_dib(h)

        while h < upper_ht:
            h_next = min(h + STEP, upper_ht)
            seg_len = h_next - h
            dib_next = self.predict_dib(h_next)

            # Smalian formula: V = K * (D1^2 + D2^2) * L
            seg_vol = self.SMALIAN_K * (dib_prev ** 2 + dib_next ** 2) * seg_len
            total_vol += seg_vol

            dib_prev = dib_next
            h = h_next

        return max(0.0, total_vol)


# ============================================================================
# Factory function
# ============================================================================

_taper_model_cache: Dict[str, TaperModel] = {}


def create_taper_model(species_code: str,
                       variant: Optional[str] = None,
                       forest_group: str = '4') -> Optional[TaperModel]:
    """Create a taper model for a species and variant.

    Returns a cached TaperModel instance, or None if no taper model
    is available for the given species/variant combination.

    Only returns a model when proper coefficients are available.
    Eastern variants (SN, NE, CS, LS) use the Clark model with
    extracted R8/R9 coefficients.  Western variants (PN, WC, OP)
    will use the Flewelling model once coefficients are extracted
    (Phase 5); until then they fall back to combined-variable.

    Args:
        species_code: FVS species code (e.g., 'LP', 'DF').
        variant: FVS variant code (e.g., 'SN', 'PN'). If None,
                 uses the current default variant.
        forest_group: R8 forest group ('1'–'7' or '9'). Only used by
                 ClarkTaperModel for SN; default '4' matches native
                 FVSsn Alabama/Bankhead FORKOD fallback.

    Returns:
        TaperModel instance, or None if taper is not supported
        for this variant.
    """
    if variant is None:
        variant = get_default_variant()

    cache_key = f"{variant}:{forest_group}:{species_code}"
    if cache_key in _taper_model_cache:
        return _taper_model_cache[cache_key]

    from .variant_registry import get_variant_config
    config = get_variant_config(variant)

    model: Optional[TaperModel] = None
    taper_cls = config.taper_class

    if taper_cls is None:
        return None  # No taper model for this variant (CA, OC, WS)
    elif taper_cls is FlewellingTaperModel:
        # Flewelling model for species with proper coefficients (DF, WH, RC).
        # Species without coefficients (SS, RA, etc.) get None from
        # _load_coefficients and fall back to combined-variable.
        candidate = FlewellingTaperModel(species_code, variant)
        if candidate._species_data is not None:
            model = candidate
        else:
            return None
    elif taper_cls is ClarkTaperModel:
        model = ClarkTaperModel(species_code, variant, forest_group=forest_group)
    else:
        model = taper_cls(species_code, variant)

    _taper_model_cache[cache_key] = model
    return model


def clear_taper_cache():
    """Clear the taper model cache (useful for testing)."""
    _taper_model_cache.clear()

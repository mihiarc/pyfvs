"""FVS East Cascades (EC) variant diameter growth model.

Port of the Fortran FVS EC variant (ForestVegetationSimulator/ec/dgf.f).
EC has 32 species split across three equation classes:

  - 13 EC-native species (WP, WL, DF, SF, RC, GF, LP, ES, AF, PP, MH, WF, OS)
    use the full ln(DDS) form with PCCF, RELHT, and CCF^2 terms.
  - 18 WC-derived species use a simpler ln(DDS) with a BA term but no
    crown-competition-factor terms. EC's BLKDAT documents the WC species
    each one is mapped to (e.g., WH(EC) <- WH(WC), PY(EC) <- PY(WC)).
  - Red alder (RA) uses a special quadratic equation with bark ratio.

Cycle: 10 years (Fortran ec/blkdat.f: DATA YR / 10.0 /). No 10->5
conversion is needed (unlike OC), so the time-step scaling is the simple
linear (time_step / 10.0) factor for non-default callers.

Equation form for EC-native species:
    ln(DDS) = CONSPP + DGLD*ln(D) + DGDUM*dummy
            + CR*(DGCR + CR*DGCRSQ)
            + DGDSQ*D^2 + DGDBAL*BAL/ln(D+1)
            + DGPCCF*PCCF + DGHCCF*RELHT*PCCF/100
            + DGCCFA*PCCF^2/1000

Equation form for WC-derived species (no PCCF/CCF terms, has BA):
    ln(DDS) = CONSPP + DGLD*ln(D) + CR*(DGCR + CR*DGCRSQ)
            + DGDSQ*D^2 + DGDBAL*BAL/ln(D+1) + DGPCCF*PCCF + DGBA*BA

CONSPP combines the per-forest intercept, elevation, slope, aspect, site
index, and the species-specific COR correction:
    CONSPP = DGFOR(loc_class) + DGEL*ELEV + DGEL2*ELEV^2
           + DGSITE*ln(SI_xform)
           + (DGSASP*sin(ASP) + DGCASP*cos(ASP) + DGSLOP)*SLOPE
           + DGSLSQ*SLOPE^2

Several species have specific tweaks documented at the call sites:
  - WP: adds 0.49649*RELHT
  - AF: DGCON += 0.3835
  - WH: subtracts 0.000358*RELHT
  - WO: SI transformed via 1-(SI/114.24569)^.4444 then -37.60812*ln; also -0.00326*BAL
  - MH, OS: SI multiplied by 3.281 (m -> ft); CONSPP -= 0.000021*RMAI*RELDEN
  - WJ, PB-OH: elevation capped at 30
  - SF, GF, WF: dummy variable = 1.0 (others = 0.0)
"""

from __future__ import annotations

import math
from typing import Dict, Optional

from .model_base import ParameterizedModel

__all__ = [
    "ECDiameterGrowthModel",
    "create_ec_diameter_growth_model",
]


# Module-level model cache
_model_cache: Dict[str, "ECDiameterGrowthModel"] = {}


# Species that use the EC-native equation form
_EC_NATIVE_SPECIES = frozenset({
    "WP", "WL", "DF", "SF", "RC", "GF", "LP", "ES", "AF", "PP",
    "MH", "WF", "OS",
})
# Species that use the WC-derived equation form
_WC_DERIVED_SPECIES = frozenset({
    "WH", "PY", "WB", "NF", "LL", "YC", "WJ", "BM", "VN", "PB",
    "GC", "DG", "AS", "CW", "WO", "PL", "WI", "OH",
})
# Species that use the dummy variable (1.0 instead of 0.0)
_DUMMY_SPECIES = frozenset({"SF", "GF", "WF"})
# Species whose elevation is capped at 30 (oc/dgf.f:625-626 equivalent)
_ELEV_CAPPED_SPECIES = frozenset({"WJ", "PB", "GC", "DG", "AS", "CW", "WO", "PL", "WI", "OH"})


class ECDiameterGrowthModel(ParameterizedModel):
    """East Cascades (EC) diameter growth model.

    Subclasses ParameterizedModel to share the species coefficient loader
    used by SN/LS/PN/CA/OC/etc.
    """

    COEFFICIENT_FILE = "ec/ec_diameter_growth_coefficients.json"
    COEFFICIENT_KEY = "species_coefficients"
    DEFAULT_SPECIES = "DF"
    _use_baskerville = True

    def __init__(self, species_code: str = "DF"):
        super().__init__(species_code)
        self._sigma = self._load_sigma()

    def calculate_dds(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        bal: float,
        pccf: float = 100.0,
        relht: float = 1.0,
        elevation: float = 0.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        location_class: int = 0,
        time_step: float = 10.0,
        rng=None,
    ) -> float:
        """Calculate change in squared diameter (DDS) for one cycle.

        Args:
            dbh: Diameter at breast height (inches).
            crown_ratio: Crown ratio as proportion (0-1).
            site_index: Site index (feet, base age 50).
            ba: Stand basal area (sq ft / acre).
            bal: Basal area in larger trees (sq ft / acre).
            pccf: Point crown competition factor (default 100).
            relht: Relative height = tree_height / avg_height. Default 1.0.
            elevation: Elevation in hundreds of feet. Default 0.
            slope: Slope as proportion 0-1. Default 0.
            aspect: Aspect in radians (0=N, π/2=E). Default 0.
            location_class: Forest/habitat-derived location class (0-based
                index into the DGFOR array). Default 0 (most common case).
            time_step: Cycle length in years. Default 10 (EC native).
            rng: Optional random.Random for stochastic mode.

        Returns:
            DDS = change in squared diameter (inches^2) for the period.
        """
        species_upper = (self.species_code or "DF").upper()

        # Red alder uses a totally different functional form
        if species_upper == "RA":
            return self._calculate_dds_red_alder(
                dbh=dbh, ba=ba, time_step=time_step, rng=rng
            )

        # Bound inputs
        dbh = max(0.1, dbh)
        crown_ratio = max(0.01, min(0.99, crown_ratio))
        site_index = max(10.0, site_index)
        ba = max(0.001, ba)
        bal = max(0.0, bal)
        relht = min(1.5, max(0.0, relht))

        c = self.coefficients

        # CONSPP — the per-tree-invariant constant assembled in DGCONS in
        # Fortran (ec/dgf.f:582-654). Computed inline here so each call
        # is self-contained; it's a few extra ops but simplifies the API.
        conspp = self._compute_conspp(
            species_upper=species_upper,
            site_index=site_index,
            elevation=elevation,
            slope=slope,
            aspect=aspect,
            location_class=location_class,
        )

        # Per-equation-class DDS computation
        if species_upper in _EC_NATIVE_SPECIES:
            ln_dds = self._calculate_dds_ec_native(
                conspp=conspp,
                dbh=dbh,
                crown_ratio=crown_ratio,
                bal=bal,
                pccf=pccf,
                relht=relht,
                species_upper=species_upper,
            )
        elif species_upper in _WC_DERIVED_SPECIES:
            ln_dds = self._calculate_dds_wc_derived(
                conspp=conspp,
                dbh=dbh,
                crown_ratio=crown_ratio,
                ba=ba,
                bal=bal,
                pccf=pccf,
                relht=relht,
                species_upper=species_upper,
            )
        else:
            # Unknown species (shouldn't happen given the loader fallback)
            ln_dds = conspp + c.get("DGLD", 0.0) * math.log(dbh)

        # Stochastic / Baskerville correction
        if rng is not None:
            z = rng.gauss(0, self._sigma)
            z = max(-2 * self._sigma, min(2 * self._sigma, z))
            if ln_dds + z > 4.0:
                z *= max(0.0, 1.0 - (ln_dds + z - 4.0) / 2.0)
            ln_dds += z
        else:
            # Baskerville bias correction with the same coefficient PN/CA use
            ln_dds += 0.88 * self._sigma * self._sigma / 2.0

        # Floor at -9.21 (Fortran ec/dgf.f:562)
        if ln_dds < -9.21:
            ln_dds = -9.21

        dds = math.exp(ln_dds)

        # Linear time-step scaling for non-default cycles
        if time_step != 10.0:
            dds = dds * (time_step / 10.0)

        return max(0.0, dds)

    def calculate_diameter_growth(
        self,
        dbh: float,
        crown_ratio: float,
        site_index: float,
        ba: float,
        bal: float,
        bark_ratio: float = 0.9,
        pccf: float = 100.0,
        relht: float = 1.0,
        elevation: float = 0.0,
        slope: float = 0.0,
        aspect: float = 0.0,
        location_class: int = 0,
        time_step: float = 10.0,
        rng=None,
    ) -> float:
        """Compute outside-bark diameter increment for one cycle.

        Converts DDS (inside-bark squared diameter change) to an outside-bark
        DBH increment using the bark ratio.
        """
        from .model_base import dds_to_diameter_growth

        dds = self.calculate_dds(
            dbh=dbh,
            crown_ratio=crown_ratio,
            site_index=site_index,
            ba=ba,
            bal=bal,
            pccf=pccf,
            relht=relht,
            elevation=elevation,
            slope=slope,
            aspect=aspect,
            location_class=location_class,
            time_step=time_step,
            rng=rng,
        )

        return dds_to_diameter_growth(dds, dbh, bark_ratio)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_conspp(
        self,
        *,
        species_upper: str,
        site_index: float,
        elevation: float,
        slope: float,
        aspect: float,
        location_class: int,
    ) -> float:
        """Assemble CONSPP per Fortran ec/dgf.f:582-654 (DGCONS entry).

        For each species this is a fixed constant (within a stand), but
        pyfvs computes it per call to keep the API stateless.
        """
        c = self.coefficients

        # Cap elevation for species that have the cap
        elev = elevation
        if species_upper in _ELEV_CAPPED_SPECIES and elev > 30.0:
            elev = 30.0

        # Site index transform for selected species
        si_xform = site_index
        if species_upper in ("MH", "OS"):
            si_xform = site_index * 3.281
        elif species_upper == "WO":
            # Fortran: XSITE = 1 - (SI / 114.24569)^.4444; if XSITE <= 0,
            # XSITE = 125; else XSITE = -37.60812 * ln(XSITE).
            x = 1.0 - (site_index / 114.24569) ** 0.4444
            if x <= 0:
                si_xform = 125.0
            else:
                si_xform = -37.60812 * math.log(x)
                # Result must be positive for the subsequent ln in the
                # CONSPP calculation
                if si_xform <= 0:
                    si_xform = 125.0

        # SASP composite — slope, aspect, slope^2 contribution
        dgsasp = c.get("DGSASP", 0.0)
        dgcasp = c.get("DGCASP", 0.0)
        dgslop = c.get("DGSLOP", 0.0)
        dgslsq = c.get("DGSLSQ", 0.0)
        sasp = (dgsasp * math.sin(aspect)
                + dgcasp * math.cos(aspect)
                + dgslop) * slope + dgslsq * slope * slope

        # When SLOPE == 0 and species is EC-native, SASP gets an override
        # constant SL0DUM (Fortran ec/dgf.f:603-605)
        if slope == 0.0 and species_upper in _EC_NATIVE_SPECIES:
            sasp = c.get("SL0DUM", 0.0)

        # DGFOR is dimensioned (6,32) — pick the location class.
        # location_class is 0-based here; cap at the number of available
        # entries.
        dgfor_array = c.get("DGFOR", [0.0])
        loc_idx = max(0, min(location_class, len(dgfor_array) - 1))
        dgfor = dgfor_array[loc_idx]
        # Some species have a 0.0 sentinel beyond the first entry — fall
        # back to the first entry like Fortran's MAPLOC implicitly does.
        if dgfor == 0.0 and loc_idx > 0:
            dgfor = dgfor_array[0]

        dgel = c.get("DGEL", 0.0)
        dgel2 = c.get("DGEL2", 0.0)
        dgsite = c.get("DGSITE", 0.0)

        conspp = (
            dgfor
            + dgel * elev
            + dgel2 * elev * elev
            + (dgsite * math.log(si_xform) if (dgsite != 0.0 and si_xform > 0) else 0.0)
            + sasp
        )

        # Subalpine fir (AF) gets a fixed +0.3835 added to DGCON
        if species_upper == "AF":
            conspp += 0.3835

        return conspp

    def _calculate_dds_ec_native(
        self,
        *,
        conspp: float,
        dbh: float,
        crown_ratio: float,
        bal: float,
        pccf: float,
        relht: float,
        species_upper: str,
    ) -> float:
        """EC-native species ln(DDS) (Fortran ec/dgf.f:518-525)."""
        c = self.coefficients
        dummy = 1.0 if species_upper in _DUMMY_SPECIES else 0.0

        # DGDSQ is per-species, taken from DGDS[MAPDSQ[forest]]; MAPDSQ in
        # EC is all-1s, so we always use index 0.
        dgds = c.get("DGDS", [0.0])
        dgdsq = dgds[0] if dgds else 0.0

        ln_dds = conspp
        ln_dds += c.get("DGLD", 0.0) * math.log(dbh)
        ln_dds += c.get("DGDUM", 0.0) * dummy
        ln_dds += crown_ratio * (
            c.get("DGCR", 0.0) + crown_ratio * c.get("DGCRSQ", 0.0)
        )
        ln_dds += dgdsq * dbh * dbh
        ln_dds += c.get("DGDBAL", 0.0) * bal / math.log(dbh + 1.0)
        ln_dds += c.get("DGPCCF", 0.0) * pccf
        ln_dds += c.get("DGHCCF", 0.0) * relht * pccf / 100.0
        ln_dds += c.get("DGCCFA", 0.0) * pccf * pccf / 1000.0

        # WP adds an extra RELHT term
        if species_upper == "WP":
            ln_dds += 0.49649 * relht

        return ln_dds

    def _calculate_dds_wc_derived(
        self,
        *,
        conspp: float,
        dbh: float,
        crown_ratio: float,
        ba: float,
        bal: float,
        pccf: float,
        relht: float,
        species_upper: str,
    ) -> float:
        """WC-derived species ln(DDS) (Fortran ec/dgf.f:534-539)."""
        c = self.coefficients
        dgds = c.get("DGDS", [0.0])
        dgdsq = dgds[0] if dgds else 0.0

        ln_dds = conspp
        ln_dds += c.get("DGLD", 0.0) * math.log(dbh)
        ln_dds += crown_ratio * (
            c.get("DGCR", 0.0) + crown_ratio * c.get("DGCRSQ", 0.0)
        )
        ln_dds += dgdsq * dbh * dbh
        ln_dds += c.get("DGDBAL", 0.0) * bal / math.log(dbh + 1.0)
        ln_dds += c.get("DGPCCF", 0.0) * pccf
        ln_dds += c.get("DGBA", 0.0) * ba

        # Species-specific tweaks
        if species_upper == "WH":
            ln_dds -= 0.000358 * relht
        elif species_upper == "WO":
            ln_dds -= 0.00326 * bal

        return ln_dds

    def _calculate_dds_red_alder(
        self,
        *,
        dbh: float,
        ba: float,
        time_step: float,
        rng,
    ) -> float:
        """Red alder special equation (Fortran ec/dgf.f:545-554).

        DIAGR (the diameter increment) is computed first, then converted
        to inside-bark DDS via:
            DDS = ln(DIAGR * (2*D*BARK + DIAGR))
        Bark ratio is approximated as 0.9 here; pyfvs's red-alder bark
        ratio model can be wired in later for higher accuracy.
        """
        dbh = max(0.1, dbh)
        ba = max(0.001, ba)

        bark = 0.9  # Approximation; species-specific bark model TBD
        const = 3.250531 - 0.003029 * ba
        if dbh <= 18.0:
            diagr = const - 0.166496 * dbh + 0.004618 * dbh * dbh
        else:
            diagr = const - (const / 10.0) * (dbh - 18.0)
        if diagr < 0.1:
            diagr = 0.1

        ln_dds = math.log(diagr * (2.0 * dbh * bark + diagr))

        # Stochastic correction (use the same _sigma loaded for RA)
        if rng is not None:
            z = rng.gauss(0, self._sigma)
            z = max(-2 * self._sigma, min(2 * self._sigma, z))
            ln_dds += z
        else:
            ln_dds += 0.88 * self._sigma * self._sigma / 2.0

        if ln_dds < -9.21:
            ln_dds = -9.21
        dds = math.exp(ln_dds)
        if time_step != 10.0:
            dds = dds * (time_step / 10.0)
        return max(0.0, dds)


def create_ec_diameter_growth_model(species_code: str = "DF") -> ECDiameterGrowthModel:
    """Factory for EC diameter growth models, cached per species."""
    key = (species_code or "DF").upper()
    if key not in _model_cache:
        _model_cache[key] = ECDiameterGrowthModel(species_code=key)
    return _model_cache[key]

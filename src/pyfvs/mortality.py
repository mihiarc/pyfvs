"""
Mortality model for FVS-Python.

Supports multiple FVS variants:
- SN (Southern): SDI-based mortality from Section 5.0 / EFVS 7.3.2
- LS (Lake States): 4-group background mortality from morts.f with VARADJ shade tolerance
- NE (Northeast): 4-group background mortality (same model as LS, different species mappings)

Implements FVS mortality equations:
- 5.0.1: Background mortality rate
- 5.0.2: Cycle adjustment
- 5.0.3: Mortality distribution
- 5.0.4: Final mortality calculation
"""
import logging
import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING

from .exceptions import FVSError
from .tree_utils import calculate_tree_basal_area, calculate_stand_basal_area

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .tree import Tree


@dataclass
class MortalityResult:
    """Result of mortality application.

    Attributes:
        survivors: List of trees that survived
        mortality_count: Number of trees that died
        trees_died: List of trees that died (for volume accounting)
    """
    survivors: List['Tree']
    mortality_count: int
    trees_died: List['Tree'] = field(default_factory=list)


class MortalityModel:
    """FVS SDI-based mortality model matching Fortran morts.f + varmrt.f.

    Implements the full FVS mortality model from morts.f:
    1. Below 55% of max TPA: Use individual tree background mortality rates
    2. Above 55%: Compute target TPA using Reineke density lines, distribute
       mortality using VARMRT shade tolerance efficiency factors

    The Fortran works in TPA-space using Reineke's equation:
        TMD = CONST * QMD^(-1.605)  where CONST = SDImax / 0.02483133

    Three pathways based on current TPA vs threshold TPA:
    - T > T85: Kill down to 85% density line
    - T55 < T <= T85: Linear interpolation between hold and 85% line
    - T <= T55: Background mortality only
    """

    # Class-level cache for mortality coefficients
    _coefficients_cache: Optional[Dict[str, Any]] = None
    _coefficients_loaded: bool = False

    # Reineke constant: SDI = TPA * (QMD/10)^1.605
    # Rearranged: TMD = (SDImax / (QMD/10)^1.605) = SDImax / 0.02483133 * QMD^(-1.605)
    REINEKE_CONST = 0.02483133  # (1/10)^1.605

    # Default SDI threshold constants per morts.f
    LOWER_THRESHOLD = 0.55  # 55% of max TPA - density-related mortality begins
    UPPER_THRESHOLD = 0.85  # 85% of max TPA - asymptotic maximum density

    # Fallback SN VARADJ shade tolerance from varmrt.f (90 species)
    # Higher value = shade INTOLERANT = higher mortality efficiency
    # Lower value = shade TOLERANT = survives better under competition
    _FALLBACK_SN_VARADJ = {
        'FR': 0.1, 'JU': 0.7, 'PI': 0.3, 'PU': 0.7, 'SP': 0.7,
        'SA': 0.7, 'SR': 0.1, 'LL': 0.7, 'TM': 0.7, 'PP': 0.7,
        'PD': 0.7, 'WP': 0.5, 'LP': 0.7, 'VP': 0.7, 'BY': 0.5,
        'PC': 0.5, 'HM': 0.1, 'FM': 0.3, 'BE': 0.3, 'RM': 0.3,
        'SV': 0.3, 'SM': 0.1, 'BU': 0.3, 'BB': 0.7, 'SB': 0.7,
        'AH': 0.1, 'HI': 0.5, 'CA': 0.7, 'HB': 0.5, 'RD': 0.3,
        'DW': 0.1, 'PS': 0.1, 'AB': 0.1, 'AS': 0.3, 'WA': 0.7,
        'BA': 0.7, 'GA': 0.3, 'HL': 0.7, 'LB': 0.3, 'HA': 0.3,
        'HY': 0.1, 'BN': 0.7, 'WN': 0.7, 'SU': 0.7, 'YP': 0.7,
        'MG': 0.3, 'CT': 0.5, 'MS': 0.3, 'MV': 0.5, 'ML': 0.3,
        'AP': 0.7, 'MB': 0.3, 'WT': 0.7, 'BG': 0.3, 'TS': 0.7,
        'HH': 0.3, 'SD': 0.3, 'RA': 0.3, 'SY': 0.5, 'CW': 0.9,
        'BT': 0.9, 'BC': 0.7, 'WO': 0.5, 'SO': 0.9, 'SK': 0.5,
        'CB': 0.7, 'TO': 0.7, 'LK': 0.3, 'OV': 0.5, 'BJ': 0.7,
        'SN': 0.7, 'CK': 0.7, 'WK': 0.7, 'CO': 0.5, 'RO': 0.5,
        'QS': 0.7, 'PO': 0.7, 'BO': 0.5, 'LO': 0.5, 'BK': 0.9,
        'WI': 0.9, 'SS': 0.7, 'BW': 0.3, 'EL': 0.5, 'WE': 0.3,
        'AE': 0.5, 'RL': 0.3, 'OS': 0.5, 'OH': 0.5, 'OT': 0.5,
    }

    # Loaded from JSON (populated in __init__)
    SN_VARADJ = None

    # Minimum DBH for density calculations (Fortran DBHSTAGE)
    DBHSTAGE = 1.0

    def __init__(self, default_species: str = 'LP', max_sdi: Optional[float] = None):
        """Initialize the mortality model.

        Args:
            default_species: Default species code for coefficient lookups
            max_sdi: Maximum SDI for the stand (if None, uses species default)
        """
        self.default_species = default_species
        self.max_sdi = max_sdi

        # Persistent state for log-log linear function (morts.f COMMON block)
        # SLPMRT and CEPMRT persist across cycles, reset on trajectory change
        self._slpmrt = 0.0
        self._cepmrt = 0.0
        self._prev_tpa = 0.0  # TPAMRT in Fortran: for trajectory change detection

        # Load VARADJ from JSON if not already loaded at class level
        if MortalityModel.SN_VARADJ is None:
            MortalityModel._load_sn_varadj()

        # Load coefficients if not already loaded
        if not MortalityModel._coefficients_loaded:
            self._load_mortality_coefficients()

    @classmethod
    def _load_sn_varadj(cls) -> None:
        """Load SN VARADJ shade tolerance from JSON config, with fallback."""
        try:
            from .config_loader import load_coefficient_file
            data = load_coefficient_file('sn/sn_mortality_defaults.json', variant='SN')
            cls.SN_VARADJ = data.get('varadj', dict(cls._FALLBACK_SN_VARADJ))
        except (FileNotFoundError, KeyError, ValueError):
            cls.SN_VARADJ = dict(cls._FALLBACK_SN_VARADJ)

    @classmethod
    def _load_mortality_coefficients(cls) -> None:
        """Load mortality coefficients from configuration."""
        try:
            from .config_loader import get_config_loader

            loader = get_config_loader()
            mortality_file = loader.cfg_dir / "sn_mortality_model.json"
            mortality_data = loader._load_config_file(mortality_file)

            background = {}
            mwt = {}

            # Extract background mortality coefficients (Table 5.0.1)
            if 'tables' in mortality_data and 'table_5_0_1' in mortality_data['tables']:
                coeffs = mortality_data['tables']['table_5_0_1'].get('coefficients', {})
                for species, values in coeffs.items():
                    background[species] = (values['p0'], values['p1'])

            # Extract MWT values (Table 5.0.2)
            if 'tables' in mortality_data and 'table_5_0_2' in mortality_data['tables']:
                mwt = mortality_data['tables']['table_5_0_2'].get('mwt_values', {})

            cls._coefficients_cache = {'background': background, 'mwt': mwt}
            cls._coefficients_loaded = True

        except (FVSError, KeyError, ValueError) as exc:
            logger.warning(
                "Failed to load mortality coefficients: %s; using defaults", exc,
            )
            cls._coefficients_cache = cls._get_default_coefficients()
            cls._coefficients_loaded = True

    @staticmethod
    def _get_default_coefficients() -> Dict[str, Any]:
        """Get default mortality coefficients.

        Returns:
            Dictionary with default background and mwt values
        """
        return {
            'background': {
                'LP': (5.5876999, -0.0053480),
                'SP': (5.5876999, -0.0053480),
                'SA': (5.5876999, -0.0053480),
                'LL': (5.5876999, -0.0053480),
            },
            'mwt': {
                'LP': 0.7, 'SP': 0.7, 'SA': 0.7, 'LL': 0.7,
            }
        }

    def get_coefficients(self) -> Dict[str, Any]:
        """Get the mortality coefficients.

        Returns:
            Dictionary with 'background' and 'mwt' coefficients
        """
        if self._coefficients_cache is None:
            self._load_mortality_coefficients()
        return self._coefficients_cache

    # -------------------------------------------------------------------------
    # Virtual hooks for subclasses
    # -------------------------------------------------------------------------
    # Subclasses (LS/NE/CS/OC) override these to plug in variant-specific
    # background mortality equations and shade tolerance coefficients without
    # duplicating the Fortran-faithful apply_mortality / TN10 / VARMRT machinery.

    def _get_background_rate_for_tree(
        self, tree: 'Tree', cycle_length: int
    ) -> float:
        """Compute per-cycle background mortality probability for one tree.

        Default implementation matches SN morts.f: individual-tree logistic
        with species coefficients from sn_mortality_model.json (Equation 5.0.1),
        then compounded to the cycle length (Equation 5.0.2).

        Override in subclasses (e.g., LS 4-group, OC 7-group) to use different
        equation forms or groupings.
        """
        coefficients = self.get_coefficients()
        p0, p1 = coefficients['background'].get(
            tree.species, (5.5876999, -0.0053480)
        )
        ri = 1.0 / (1.0 + math.exp(p0 + p1 * tree.dbh))
        rip = 1.0 - ((1.0 - ri) ** cycle_length)
        return rip

    def _get_varadj_for_tree(self, species: str) -> float:
        """Return VARMRT shade-tolerance coefficient for a species.

        Default implementation matches SN varmrt.f: reads from the class-level
        SN_VARADJ dict loaded from sn_mortality_defaults.json.

        Override in subclasses to use a different per-species table.
        """
        return self.SN_VARADJ.get(species, 0.5)

    def apply_mortality(
        self,
        trees: List['Tree'],
        cycle_length: int = 5,
        max_sdi: Optional[float] = None,
        random_seed: Optional[int] = None,
        pre_growth_qmd: float = 0.0,
        pre_growth_tpa: int = 0,
        stochastic: bool = True,
        **kwargs,
    ) -> MortalityResult:
        """Apply FVS mortality matching Fortran morts.f + varmrt.f.

        Uses Reineke's equation in log-log space to compute target TPA,
        then distributes mortality using VARMRT shade tolerance factors.

        The Fortran algorithm:
        1. Compute DQ0 (pre-growth QMD) and D10 (post-growth QMD) for
           trees >= DBHSTAGE (1.0")
        2. Determine TN10 via three pathways based on density relative
           to 55%/85% thresholds using a log-log linear function
        3. Distribute mortality using VARMRT efficiency factors

        Args:
            trees: List of trees in the stand (post-growth, pre-mortality)
            cycle_length: Length of projection cycle in years
            max_sdi: Maximum SDI (uses species default if None)
            random_seed: Optional seed for reproducibility
            pre_growth_qmd: QMD of staged trees before growth (DQ0)
            pre_growth_tpa: Count of staged trees before growth
            stochastic: When True (default), apply Bernoulli per-tree mortality
                using the RNG. When False, use Fortran-faithful expected-value
                mortality: kill round(sum of per-tree rip_i) trees deterministically.
                Fortran morts.f always uses expected-value (fractional PROB
                reduction), so stochastic=False is the more faithful mode.

        Returns:
            MortalityResult with survivors and mortality count
        """
        if len(trees) <= 1:
            return MortalityResult(survivors=list(trees), mortality_count=0, trees_died=[])

        rng = random.Random(random_seed) if random_seed is not None else random.Random()

        max_sdi = max_sdi or self.max_sdi or 450

        # Staging: only trees >= DBHSTAGE count toward density (morts.f)
        staged_dbhs = [t.dbh for t in trees if t.dbh >= self.DBHSTAGE]
        t = len(staged_dbhs)  # T in Fortran

        if t < 2:
            # Not enough staged trees — background mortality only
            coefficients = self.get_coefficients()
            tree_data = self._calculate_tree_percentiles(trees)
            return self._apply_background_mortality(
                tree_data, coefficients, cycle_length, rng=rng, stochastic=stochastic,
            )

        # DQ0: pre-growth QMD of staged trees (from stand.py)
        dia0 = pre_growth_qmd if pre_growth_qmd > 0 else math.sqrt(
            sum(d ** 2 for d in staged_dbhs) / t
        )
        # D10: post-growth QMD of staged trees (current values)
        d10 = math.sqrt(sum(d ** 2 for d in staged_dbhs) / t)

        # Trajectory change detection (morts.f line 245):
        # If TPA changed from last cycle (thinning, ingrowth), reset coefficients
        if self._prev_tpa > 0 and abs(t - self._prev_tpa) > 1:
            self._cepmrt = 0.0
            self._slpmrt = 0.0

        # Safety: minimum diameter (morts.f line 277)
        if dia0 < 0.3:
            d10 = 0.3 + d10 - dia0
            dia0 = 0.3

        # Reineke constant: TMD = CONST * D^(-1.605)
        const = max_sdi / self.REINEKE_CONST

        # Thresholds at pre-growth diameter (DQ0)
        tmd0 = min(35000.0, const * (dia0 ** (-1.605)))
        t85d0 = tmd0 * self.UPPER_THRESHOLD
        t55d0 = self.LOWER_THRESHOLD * tmd0

        # Thresholds at post-growth diameter (D10)
        tmd10 = min(35000.0, const * (d10 ** (-1.605)))
        t85d10 = tmd10 * self.UPPER_THRESHOLD
        t55d10 = self.LOWER_THRESHOLD * tmd10

        # Compute target TPA (TN10) using Fortran pathway logic
        tn10 = self._compute_target_tpa(
            t, dia0, d10, const, t85d0, t55d0, t85d10, t55d10
        )

        # Bound TN10 (morts.f lines 467-468)
        tn10 = min(tn10, float(t))
        if tn10 < 0.1:
            tn10 = 0.0

        # Determine if density mortality is active
        # Fortran: IF(T .LE. TEM .OR. RN .LE. 0.0) RIP=RI
        density_active = (t > t55d10 and tn10 < t)
        tokill = max(0.0, t - tn10)

        coefficients = self.get_coefficients()
        tree_data = self._calculate_tree_percentiles(trees)

        if density_active and tokill >= 0.5:
            # Density mortality: distribute TOKILL using VARMRT
            result = self._apply_density_mortality_fortran(
                tree_data, coefficients, cycle_length, round(tokill),
                rng=rng, stochastic=stochastic,
            )
        else:
            # Background mortality only
            result = self._apply_background_mortality(
                tree_data, coefficients, cycle_length, rng=rng, stochastic=stochastic,
            )

        # Save staged TPA for next cycle's trajectory change detection
        self._prev_tpa = len([t for t in result.survivors if t.dbh >= self.DBHSTAGE])

        return result

    def _compute_target_tpa(
        self,
        t: float,
        dia0: float,
        d10: float,
        const: float,
        t85d0: float,
        t55d0: float,
        t85d10: float,
        t55d10: float
    ) -> float:
        """Compute target TPA (TN10) using Fortran log-log linear function.

        Implements morts.f lines 383-456 with three pathways:
        1. T > T85D0: Kill to 85% line at D10
        2. T55D0 < T <= T85D0: Iterative log-log linear function
        3. T <= T55D0: Hold constant or straight computation

        Args:
            t: Current staged TPA
            dia0: Pre-growth QMD (DQ0)
            d10: Post-growth QMD
            const: Reineke constant (SDIMAX / 0.02483133)
            t85d0, t55d0: Thresholds at DQ0
            t85d10, t55d10: Thresholds at D10

        Returns:
            Target TPA at end of cycle
        """
        pmsdil = self.LOWER_THRESHOLD
        pmsdiu = self.UPPER_THRESHOLD

        # Pathway 1: Above 85% at start → kill to 85% at end
        if t > t85d0:
            return t85d10

        # Pathway 2: Between 55% and 85% → iterative log-log linear function
        if t > t55d0:
            # Special case: close to 85% line (morts.f line 396)
            if abs(t85d0 - t) <= 5.0:
                return t85d10

            # Iterative fitting (IPATH=1)
            slp, cept = self._fit_loglog_linear(
                t, const, pmsdil, pmsdiu, dia0, ipath=1
            )

            # Use persistent coefficients (morts.f lines 434-435)
            if self._slpmrt == 0.0:
                self._slpmrt = slp
            if self._cepmrt == 0.0:
                self._cepmrt = cept

            tn10 = math.exp(self._cepmrt + self._slpmrt * math.log(d10))
            return min(tn10, t85d10)

        # Pathway 3: Below 55% at start
        if t <= t55d10:
            # Still below 55% at end → hold constant (no density mortality)
            return float(t)

        # Crossed 55% during growth → straight computation (IPATH=2)
        slp, cept = self._fit_loglog_linear(
            t, const, pmsdil, pmsdiu, dia0, ipath=2
        )

        if self._slpmrt == 0.0:
            self._slpmrt = slp
        if self._cepmrt == 0.0:
            self._cepmrt = cept

        tn10 = math.exp(self._cepmrt + self._slpmrt * math.log(d10))
        return min(tn10, t85d10)

    def _fit_loglog_linear(
        self,
        t: float,
        const: float,
        pmsdil: float,
        pmsdiu: float,
        dia0: float,
        ipath: int = 1
    ) -> Tuple[float, float]:
        """Compute slope and intercept of log-log linear mortality function.

        Implements the iterative algorithm from morts.f lines 400-432.
        Finds a linear function in ln(TPA) vs ln(QMD) space that passes
        through the current stand point and connects the 55% and 85%
        density lines.

        Args:
            t: Current staged TPA
            const: Reineke constant
            pmsdil: Lower threshold fraction (0.55)
            pmsdiu: Upper threshold fraction (0.85)
            dia0: Pre-growth QMD
            ipath: 1 = iterative (between 55-85%), 2 = straight (crossed 55%)

        Returns:
            (slope, intercept) in log-log space
        """
        treeit = t + 0.1 * t
        slp = -1.605  # Default
        cept = 0.0

        for knt in range(100):
            tem = treeit if ipath == 1 else t

            # Point on 55% line where TPA = TEM
            d55m = (math.log(tem) - math.log(pmsdil * const)) / (-1.605)
            t55m = math.log(tem)
            d85m = d55m * 1.25

            # Adjust D85M to ensure slope <= -0.5 (morts.f line 411-420)
            for _ in range(100):
                d85m = max(0.125, min(5.0, d85m))
                t85m = math.log(
                    const * (math.exp(d85m) ** (-1.605)) * pmsdiu
                )
                slp = (t85m - t55m) / (d85m - d55m) if abs(d85m - d55m) > 1e-10 else -1.605
                if slp > -0.5 and d85m < 5.0:
                    d85m += 0.1
                else:
                    break

            cept = t55m - slp * d55m

            if ipath == 2:
                # Straight computation — no iteration needed
                break

            # Check convergence: does the line pass through (dia0, T)?
            tprime = cept + slp * math.log(dia0)
            diff = t - math.exp(tprime)

            if abs(diff) <= 5.0:
                break

            treeit = treeit + 0.5 * diff

        return slp, cept

    def _calculate_stand_sdi(self, trees: List['Tree']) -> float:
        """Calculate stand SDI using Reineke's equation."""
        if not trees:
            return 0.0
        tpa = len(trees)
        qmd_squared = sum(tree.dbh ** 2 for tree in trees) / tpa
        qmd = math.sqrt(qmd_squared)
        return tpa * (qmd / 10.0) ** 1.605

    def _calculate_tree_percentiles(
        self,
        trees: List['Tree']
    ) -> List[Tuple['Tree', float]]:
        """Calculate basal area percentile for each tree.

        Args:
            trees: List of trees

        Returns:
            List of (tree, percentile) tuples sorted by DBH
        """
        total_ba = calculate_stand_basal_area(trees)
        tree_data = []
        cumulative_ba = 0.0
        sorted_trees = sorted(trees, key=lambda t: t.dbh)

        for tree in sorted_trees:
            tree_ba = calculate_tree_basal_area(tree.dbh)
            cumulative_ba += tree_ba
            pct = (cumulative_ba / total_ba) * 100.0 if total_ba > 0 else 50.0
            tree_data.append((tree, pct))

        return tree_data

    @staticmethod
    def _weighted_sample_without_replacement(
        items: List[Tuple['Tree', float]],
        n: int,
        rng: random.Random,
    ) -> Tuple[List['Tree'], List['Tree']]:
        """Sample exactly `n` trees without replacement, weighted by the
        second tuple element (rip, efftr, etc.).

        Uses the Efraimidis-Spirakis algorithm: assign each item score
        log(U)/w_i with U~Uniform(0,1), pick top-`n` by score. Trees with
        weight <= 0 get score -inf (never selected).

        This is the Fortran-faithful stochastic analogue: cycle-level kill
        count is deterministic (matches Fortran morts.f which has no RNG),
        but which trees die is randomized in proportion to their rates.
        Eliminates the kill-count variance that biases stochastic runs
        (Jensen lift on BA for high-SIGMAR species).

        Returns:
            (selected, not_selected) both as lists of Trees.
        """
        total = len(items)
        if n <= 0:
            return [], [t for t, _ in items]
        if n >= total:
            return [t for t, _ in items], []

        scored: List[Tuple[float, 'Tree']] = []
        for tree, w in items:
            if w <= 0:
                score = float('-inf')
            else:
                u = rng.random()
                if u <= 0.0:
                    u = 1e-300
                score = math.log(u) / w
            scored.append((score, tree))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [t for _, t in scored[:n]]
        not_selected = [t for _, t in scored[n:]]
        return selected, not_selected

    def _apply_background_mortality(
        self,
        tree_data: List[Tuple['Tree', float]],
        coefficients: Dict[str, Any],
        cycle_length: int,
        *,
        rng: random.Random = None,
        stochastic: bool = True,
    ) -> MortalityResult:
        """Apply background mortality only (below SDI threshold).

        Uses equations 5.0.1 and 5.0.2 from morts.f.

        Fortran morts.f applies FRACTIONAL mortality: each tree-record's
        PROB is reduced by WKI = P*(1-(1-rip)^FINT) with NO RNG — the
        cycle-level kill count is deterministic. With integer pyfvs trees,
        we emulate this two ways that both preserve the deterministic kill
        count round(sum(rip_i)):
          - stochastic=True: weighted-sampling-without-replacement with
            selection probability ∝ rip_i (Efraimidis-Spirakis). Randomizes
            WHICH trees die while keeping total kills exact.
          - stochastic=False: highest-rip-first deterministic selection
            (tie-break by smallest DBH).

        Previously stochastic mode used independent per-tree Bernoulli,
        which added kill-count variance that inflated BA via Jensen on
        high-SIGMAR species (fixed 2026-04-16).

        Args:
            tree_data: List of (tree, percentile) tuples
            coefficients: Mortality coefficients
            cycle_length: Cycle length in years
            rng: Local random number generator
            stochastic: Randomized weighted selection if True,
                deterministic highest-rip-first if False

        Returns:
            MortalityResult
        """
        if rng is None:
            rng = random.Random()

        trees_with_rip: List[Tuple['Tree', float]] = []
        for tree, _ in tree_data:
            rip = self._get_background_rate_for_tree(tree, cycle_length)
            trees_with_rip.append((tree, rip))

        total_kills = int(round(sum(rip for _, rip in trees_with_rip)))
        total_kills = max(0, min(total_kills, len(trees_with_rip)))

        if stochastic:
            trees_died, survivors = self._weighted_sample_without_replacement(
                trees_with_rip, total_kills, rng,
            )
        else:
            ranked = sorted(
                trees_with_rip,
                key=lambda tr: (-tr[1], tr[0].dbh),
            )
            trees_died = [t for t, _ in ranked[:total_kills]]
            survivors = [t for t, _ in ranked[total_kills:]]

        return MortalityResult(
            survivors=survivors,
            mortality_count=len(trees_died),
            trees_died=trees_died
        )

    def _apply_density_mortality_fortran(
        self,
        tree_data: List[Tuple['Tree', float]],
        coefficients: Dict[str, Any],
        cycle_length: int,
        tokill: int,
        *,
        rng: random.Random = None,
        stochastic: bool = True,
    ) -> MortalityResult:
        """Apply Fortran-style density mortality (morts.f + varmrt.f).

        Distributes exactly TOKILL deaths among trees using VARMRT-style
        efficiency factors: EFFTR = PEFF * VARADJ * 0.1

        Small trees and shade-intolerant species have higher efficiency
        (more likely to die), matching the self-thinning process.

        Args:
            tree_data: List of (tree, percentile) tuples sorted by DBH
            coefficients: Mortality coefficients
            cycle_length: Cycle length in years
            tokill: Target number of trees to kill
            rng: Local random number generator
            stochastic: Bernoulli-weighted selection if True, deterministic
                top-N-by-efficiency selection if False (Fortran VARMRT is
                deterministic — it distributes exactly TOKILL across trees
                weighted by efficiency).

        Returns:
            MortalityResult
        """
        if rng is None:
            rng = random.Random()
        tpa = len(tree_data)
        tokill = min(tokill, tpa - 1)  # Keep at least 1 tree

        if tokill <= 0:
            trees = [t for t, _ in tree_data]
            return MortalityResult(survivors=trees, mortality_count=0, trees_died=[])

        # Compute VARMRT efficiency for each tree
        efftr = []
        for tree, pct in tree_data:
            # Percentile-based efficiency (varmrt.f line 120)
            peff = 0.84525 - 0.01074 * pct + 0.0000002 * (pct ** 3)
            peff = max(0.01, min(1.0, peff))

            # Shade tolerance (VARADJ from varmrt.f) — delegated so LS/OC
            # subclasses can supply their own per-species tables.
            varadj = self._get_varadj_for_tree(tree.species)

            # Combined efficiency (varmrt.f line 123)
            eff = peff * varadj * 0.1
            efftr.append(eff)

        if not stochastic:
            # Deterministic: kill exactly tokill trees, highest-efficiency
            # first. Tie-break by smallest DBH ascending so smaller trees
            # within a tied efficiency group die first.
            indexed = list(zip(range(tpa), tree_data, efftr))
            indexed.sort(key=lambda x: (-x[2], x[1][0].dbh))
            killed_idx = {i for i, _, _ in indexed[:tokill]}
            survivors = [t for i, (t, _) in enumerate(tree_data) if i not in killed_idx]
            trees_died = [t for i, (t, _) in enumerate(tree_data) if i in killed_idx]
            return MortalityResult(
                survivors=survivors,
                mortality_count=len(trees_died),
                trees_died=trees_died
            )

        # Stochastic: weighted-sampling-without-replacement. Picks exactly
        # TOKILL trees with selection probability ∝ efftr, matching
        # Fortran VARMRT's deterministic cycle-level kill count while
        # randomizing which trees die. Previously this used independent
        # Bernoulli with a post-hoc kill-count correction, which added
        # unwanted TPA variance (fixed 2026-04-16).
        items = [(tree, efftr[i]) for i, (tree, _) in enumerate(tree_data)]
        trees_died, survivors = self._weighted_sample_without_replacement(
            items, tokill, rng,
        )

        return MortalityResult(
            survivors=survivors,
            mortality_count=len(trees_died),
            trees_died=trees_died
        )

    def calculate_background_mortality_rate(
        self,
        tree: 'Tree',
        cycle_length: int = 5
    ) -> float:
        """Calculate background mortality rate for a single tree.

        Implements equations 5.0.1 and 5.0.2.

        Args:
            tree: Tree to calculate mortality for
            cycle_length: Cycle length in years

        Returns:
            Mortality probability (0-1)
        """
        coefficients = self.get_coefficients()
        p0, p1 = coefficients['background'].get(
            tree.species, (5.5876999, -0.0053480)
        )

        # Individual tree background mortality rate (Equation 5.0.1)
        ri = 1.0 / (1.0 + math.exp(p0 + p1 * tree.dbh))

        # Adjust for cycle length (Equation 5.0.2)
        rip = 1.0 - ((1.0 - ri) ** cycle_length)

        return rip

    def calculate_mortality_distribution(self, basal_area_percentile: float) -> float:
        """Calculate mortality distribution factor (MR).

        Implements equation 5.0.3:
        MR = 0.84525 - 0.01074*PCT + 0.0000002*PCT³

        Args:
            basal_area_percentile: Tree's position in BA distribution (0-100)

        Returns:
            Mortality distribution factor (bounded 0.01-1.0)
        """
        pct = basal_area_percentile
        mr = 0.84525 - (0.01074 * pct) + (0.0000002 * (pct ** 3))
        return max(0.01, min(1.0, mr))


class LSMortalityModel(MortalityModel):
    """FVS Lake States mortality model.

    Implements the LS variant mortality model from vls/morts.f as a faithful
    port of the Fortran algorithm. Inherits the TN10/TOKILL/VARMRT density
    machinery from `MortalityModel` (the SN port) and overrides only the
    per-tree background rate and shade tolerance hooks.

    Structural difference from SN:
    1. 4-group background mortality instead of per-species coefficients.
       Groups from morts.f lines 99-100:
         Group 1: PMSC=5.1677,  PMD=-0.00777
         Group 2: PMSC=9.6943,  PMD=-0.01273
         Group 3: PMSC=5.5877,  PMD=-0.00535
         Group 4: PMSC=5.9617,  PMD=-0.03401
       Background rate is halved post-logistic (morts.f:504).

    2. Per-species shade tolerance table uses the OPPOSITE convention from SN:
       LS varmrt.f:64 says "VARADJ = TREE SHADE TOLERANCE (1.0 = MOST TOLERANT)"
       and uses `EFFTR = PEFF * (1.0-VARADJ) * 0.1`, while SN varmrt.f:83 says
       "VARADJ = TREE SHADE TOLERANCE (1.0 = MOST INTOLERANT)" and uses
       `EFFTR = PEFF * VARADJ * 0.1`. We flip inside `_get_varadj_for_tree` so
       the shared SN-derived density code produces correct LS behavior.

    Subclasses (NE, CS, OC) override class attributes and the species
    table to use variant-specific coefficient files, species-group mappings,
    and SDI maximums. OC also overrides `_get_background_rate_for_tree` for its
    7-group model.
    """

    # Coefficient file path (relative to cfg/), overridden by subclasses
    _COEFFICIENT_FILE = 'ls/ls_mortality_coefficients.json'

    # 4-group background mortality coefficients (PMSC, PMD) from morts.f lines 99-100
    MORTALITY_GROUPS = {
        1: {'P0': 5.1677, 'P1': -0.00777},
        2: {'P0': 9.6943, 'P1': -0.01273},
        3: {'P0': 5.5877, 'P1': -0.00535},
        4: {'P0': 5.9617, 'P1': -0.03401},
    }

    # Fallback species-to-mortality-group mapping from IMAPLS in morts.f
    _FALLBACK_SPECIES_MORTALITY_GROUP = {
        'JP': 1, 'RN': 1, 'RP': 1, 'WS': 1, 'NS': 1, 'BF': 1,
        'BS': 1, 'TA': 1, 'WC': 1, 'EH': 1, 'GA': 1, 'SV': 1,
        'RM': 1, 'AE': 1, 'RL': 1, 'RE': 1, 'BW': 1, 'SM': 1,
        'BM': 1, 'AB': 1, 'HH': 1, 'BK': 1, 'AH': 1, 'DW': 1,
        'BG': 1, 'WI': 1, 'BL': 1, 'SS': 1,
        'SC': 3, 'WP': 3, 'OS': 3, 'RC': 3,
        'BA': 4, 'EC': 4, 'BC': 4, 'YB': 4, 'WA': 4, 'WO': 4,
        'SW': 4, 'BR': 4, 'CK': 4, 'RO': 4, 'BO': 4, 'NP': 4,
        'BH': 4, 'PH': 4, 'SH': 4, 'BT': 4, 'QA': 4, 'BP': 4,
        'PB': 4, 'BN': 4, 'WN': 4, 'OH': 4, 'BE': 4, 'ST': 4,
        'MM': 4, 'AC': 4, 'HK': 4, 'HT': 4, 'AP': 4, 'SY': 4,
        'PR': 4, 'CC': 4, 'PL': 4, 'DM': 4, 'MA': 4,
    }

    # Fallback SDI maximums (overridden by subclasses)
    _FALLBACK_SDI_MAXIMUMS = {
        'JP': 400, 'SC': 400, 'RN': 500, 'RP': 500, 'WP': 450,
        'WS': 500, 'NS': 500, 'BF': 400, 'BS': 400, 'TA': 350,
        'WC': 400, 'EH': 500, 'SM': 450, 'RM': 400, 'QA': 350,
        'PB': 350, 'RO': 400, 'WO': 400, 'YB': 400, 'AB': 450,
    }
    DEFAULT_SDI_MAX = 400

    # Fallback shade tolerances (LS convention: 1.0 = most TOLERANT).
    # Values from LS varmrt.f VARADJ DATA statement.
    _FALLBACK_SHADE_TOLERANCE = {
        'JP': 0.30, 'RN': 0.30, 'WP': 0.50, 'BF': 0.90,
        'SM': 0.90, 'RM': 0.85, 'QA': 0.10, 'PB': 0.30,
        'RO': 0.50, 'WO': 0.50,
    }

    # Instance-level loaded data (populated from JSON in __init__)
    SPECIES_MORTALITY_GROUP = None
    _SDI_MAXIMUMS = None

    # JSON config file for this variant's mortality defaults
    _DEFAULTS_FILE = 'ls/ls_mortality_defaults.json'

    def __init__(self, default_species: str = 'RN', max_sdi: Optional[float] = None,
                 variant: str = 'LS'):
        """Initialize the LS mortality model.

        Args:
            default_species: Default species code for coefficient lookups
            max_sdi: Maximum SDI for the stand (if None, resolves species-specific
                     default from the variant's SDI_MAXIMUMS table)
            variant: Variant code ('LS', 'NE', 'CS', 'OC')
        """
        # Don't chain through MortalityModel.__init__ because it loads SN
        # coefficients and VARADJ into class attributes that LS doesn't use.
        # We still get the inherited methods (apply_mortality, _compute_target_tpa,
        # _fit_loglog_linear, _calculate_stand_sdi, _calculate_tree_percentiles,
        # _apply_background_mortality, _apply_density_mortality_fortran).
        self.default_species = default_species
        self.max_sdi = max_sdi
        self.variant = variant
        self._shade_tolerance = {}

        # Persistent state for the SN/Fortran log-log linear function.
        # LS morts.f uses the same CEPMRT/SLPMRT/TPAMRT state (morts.f:166-168,
        # 225-228). These are reset on trajectory change in apply_mortality.
        self._slpmrt = 0.0
        self._cepmrt = 0.0
        self._prev_tpa = 0.0

        self._load_defaults()
        self._load_shade_tolerance()

        # Resolve species-specific SDI maximum if not explicitly provided.
        # The inherited apply_mortality does `max_sdi or self.max_sdi or 450`,
        # but 450 is the SN default and wrong for LS/NE/CS/OC. By setting
        # self.max_sdi here, that fallback never hits 450 for LS variants.
        if self.max_sdi is None:
            self.max_sdi = self._SDI_MAXIMUMS.get(
                default_species, self.DEFAULT_SDI_MAX
            )

    def _load_defaults(self):
        """Load species groups, SDI maximums, and shade tolerance from JSON config."""
        try:
            from .config_loader import load_coefficient_file
            data = load_coefficient_file(self._DEFAULTS_FILE, variant=self.variant)
            # Convert JSON string keys to int for species_mortality_group values
            raw_groups = data.get('species_mortality_group', {})
            self.SPECIES_MORTALITY_GROUP = {k: int(v) for k, v in raw_groups.items()}
            self._SDI_MAXIMUMS = data.get('sdi_maximums', dict(self._FALLBACK_SDI_MAXIMUMS))
            self.DEFAULT_SDI_MAX = data.get('default_sdi_max', 400)
        except (FileNotFoundError, KeyError, ValueError):
            self.SPECIES_MORTALITY_GROUP = dict(self._FALLBACK_SPECIES_MORTALITY_GROUP)
            self._SDI_MAXIMUMS = dict(self._FALLBACK_SDI_MAXIMUMS)

    def _load_shade_tolerance(self):
        """Load shade tolerance (VARADJ) from mortality coefficients."""
        try:
            from .config_loader import load_coefficient_file
            data = load_coefficient_file(self._COEFFICIENT_FILE)
            coeffs = data.get('coefficients', {})
            for species, values in coeffs.items():
                self._shade_tolerance[species] = values.get('shade_tolerance', 0.30)
        except (FileNotFoundError, KeyError):
            self._shade_tolerance = dict(self._FALLBACK_SHADE_TOLERANCE)

    def _get_background_rate_for_tree(
        self, tree: 'Tree', cycle_length: int
    ) -> float:
        """LS 4-group background mortality with halved logistic rate.

        Direct port of vls/morts.f:500-504. Selects a group by species from
        IMAPLS, then applies the logistic and halves per morts.f:504.
        """
        group = self.SPECIES_MORTALITY_GROUP.get(tree.species, 3)
        group_coeffs = self.MORTALITY_GROUPS[group]
        p0 = group_coeffs['P0']
        p1 = group_coeffs['P1']

        # Base annual rate (logistic) — morts.f:500
        ri = 1.0 / (1.0 + math.exp(p0 + p1 * tree.dbh))

        # Halve the background rate — morts.f:504
        ri *= 0.5

        # Compound to cycle length
        rip = 1.0 - ((1.0 - ri) ** cycle_length)
        return rip

    def _get_varadj_for_tree(self, species: str) -> float:
        """Return VARMRT shade-tolerance coefficient in SN convention.

        LS `_shade_tolerance` stores values in the LS-varmrt convention
        ("1.0 = MOST TOLERANT", LS varmrt.f:64). The shared density mortality
        code (inherited from SN `MortalityModel`) uses the SN convention
        ("1.0 = MOST INTOLERANT", SN varmrt.f:83). Flip here so LS tolerant
        species (e.g., BF, SM at 0.90) produce low EFFTR and survive.
        """
        ls_tolerance = self._shade_tolerance.get(species, 0.30)
        return 1.0 - ls_tolerance

    def calculate_background_mortality_rate(
        self, tree: 'Tree', cycle_length: int = 5
    ) -> float:
        """Calculate background mortality rate for a single tree."""
        return self._get_background_rate_for_tree(tree, cycle_length)


class NEMortalityModel(LSMortalityModel):
    """FVS Northeast mortality model.

    NE uses the same 4-group background + SDI density model as LS (TWIGS family),
    with NE-specific species-group mappings, shade tolerances, and SDI maximums.
    """

    _COEFFICIENT_FILE = 'ne/ne_mortality_coefficients.json'

    # NE species-to-mortality-group mapping from IMAPNE in morts.f (108 species)
    SPECIES_MORTALITY_GROUP = {
        # Group 1 (38 species)
        'BF': 1, 'TA': 1, 'WS': 1, 'RS': 1, 'NS': 1, 'BS': 1,
        'PI': 1, 'RN': 1, 'WC': 1, 'AW': 1, 'EH': 1, 'HM': 1,
        'JP': 1, 'RM': 1, 'SM': 1, 'BM': 1, 'SV': 1, 'SB': 1,
        'AB': 1, 'AS': 1, 'GA': 1, 'PA': 1, 'BU': 1, 'YY': 1,
        'MG': 1, 'BG': 1, 'SD': 1, 'BK': 1, 'BL': 1, 'SS': 1,
        'BW': 1, 'WB': 1, 'EL': 1, 'AE': 1, 'RL': 1, 'AH': 1,
        'DW': 1, 'HH': 1,
        # Group 2 (1 species)
        'OS': 2,
        # Group 3 (11 species)
        'WP': 3, 'LP': 3, 'VP': 3, 'RC': 3, 'JU': 3, 'OP': 3,
        'SP': 3, 'TM': 3, 'PP': 3, 'PD': 3, 'SC': 3,
        # Group 4 (57 species)
        'YB': 4, 'RB': 4, 'PB': 4, 'GB': 4, 'HI': 4, 'PH': 4,
        'SL': 4, 'SH': 4, 'MH': 4, 'WA': 4, 'BA': 4, 'YP': 4,
        'SU': 4, 'CT': 4, 'QA': 4, 'BP': 4, 'EC': 4, 'BT': 4,
        'PY': 4, 'BC': 4, 'WO': 4, 'BR': 4, 'CK': 4, 'PO': 4,
        'OK': 4, 'SO': 4, 'QI': 4, 'WK': 4, 'PN': 4, 'CO': 4,
        'SW': 4, 'SN': 4, 'RO': 4, 'SK': 4, 'BO': 4, 'CB': 4,
        'WR': 4, 'HK': 4, 'PS': 4, 'HY': 4, 'BN': 4, 'WN': 4,
        'OO': 4, 'MV': 4, 'AP': 4, 'WT': 4, 'PW': 4, 'SY': 4,
        'WL': 4, 'OH': 4, 'BE': 4, 'ST': 4, 'AI': 4, 'SE': 4,
        'HT': 4, 'PL': 4, 'PR': 4,
    }

    # NE SDI maximums (references StandMetricsCalculator.NE_SDI_MAXIMUMS)
    _SDI_MAXIMUMS = {
        'BF': 400, 'TA': 350, 'WS': 500, 'RS': 450, 'NS': 450,
        'BS': 400, 'PI': 400, 'RN': 500, 'WP': 450, 'LP': 450,
        'VP': 350, 'OP': 400, 'JP': 400, 'SP': 400, 'TM': 350,
        'PP': 350, 'PD': 350, 'SC': 400, 'WC': 400, 'AW': 350,
        'RC': 350, 'JU': 350, 'EH': 500, 'HM': 450, 'OS': 400,
        'RM': 400, 'SM': 450, 'BM': 450, 'SV': 400, 'WO': 400,
        'RO': 400, 'YB': 400, 'AB': 450, 'WA': 350, 'BC': 400,
        'YP': 450, 'WN': 400, 'QA': 350, 'PB': 350,
    }

    _FALLBACK_SHADE_TOLERANCE = {
        'RM': 0.85, 'SM': 0.90, 'WP': 0.50, 'RO': 0.50,
        'WO': 0.50, 'BF': 0.90, 'RS': 0.70, 'EH': 0.90,
        'YB': 0.50, 'AB': 0.90, 'WA': 0.30, 'BC': 0.40,
    }

    def __init__(self, default_species: str = 'RM', max_sdi: Optional[float] = None,
                 variant: str = 'NE'):
        """Initialize the NE mortality model.

        Args:
            default_species: Default species code for coefficient lookups
            max_sdi: Maximum SDI for the stand (if None, uses species default)
            variant: Variant code
        """
        super().__init__(default_species=default_species, max_sdi=max_sdi, variant=variant)


class CSMortalityModel(LSMortalityModel):
    """FVS Central States mortality model.

    CS uses the same 4-group background + SDI density model as LS/NE (TWIGS family),
    with CS-specific species-group mappings, shade tolerances, and SDI maximums.
    """

    _COEFFICIENT_FILE = 'cs/cs_mortality_coefficients.json'

    # CS species-to-mortality-group mapping from IMAPCS in morts.f (96 species)
    SPECIES_MORTALITY_GROUP = {
        # Group 1 (30 species)
        'TL': 1, 'BG': 1, 'AB': 1, 'PA': 1, 'UA': 1, 'RM': 1,
        'SV': 1, 'AE': 1, 'WE': 1, 'EL': 1, 'SI': 1, 'RL': 1,
        'RE': 1, 'BW': 1, 'SM': 1, 'AS': 1, 'GA': 1, 'SS': 1,
        'OB': 1, 'BK': 1, 'WI': 1, 'BL': 1, 'AH': 1, 'RD': 1,
        'DW': 1, 'KC': 1, 'OO': 1, 'MB': 1, 'HH': 1, 'SD': 1,
        # Group 2 (2 species)
        'JU': 2, 'OS': 2,
        # Group 3 (6 species)
        'RC': 3, 'SP': 3, 'VP': 3, 'LP': 3, 'WP': 3, 'BY': 3,
        # Group 4 (55 species)
        'WN': 4, 'BN': 4, 'TS': 4, 'WT': 4, 'SH': 4, 'SL': 4,
        'MH': 4, 'PH': 4, 'HI': 4, 'WH': 4, 'BH': 4, 'PE': 4,
        'BI': 4, 'BA': 4, 'EC': 4, 'BE': 4, 'BC': 4, 'SG': 4,
        'HK': 4, 'YP': 4, 'WA': 4, 'WO': 4, 'RO': 4, 'SK': 4,
        'BO': 4, 'SO': 4, 'BJ': 4, 'CK': 4, 'SW': 4, 'BR': 4,
        'SN': 4, 'PO': 4, 'DO': 4, 'CO': 4, 'PN': 4, 'CB': 4,
        'QI': 4, 'OV': 4, 'WK': 4, 'NK': 4, 'WL': 4, 'QS': 4,
        'CA': 4, 'PS': 4, 'HL': 4, 'BP': 4, 'BT': 4, 'QA': 4,
        'SY': 4, 'RB': 4, 'SU': 4, 'OH': 4, 'CT': 4, 'MV': 4,
        'HT': 4,
    }

    # CS SDI maximums (references StandMetricsCalculator.CS_SDI_MAXIMUMS)
    _SDI_MAXIMUMS = {
        'RC': 400, 'JU': 350, 'SP': 450, 'VP': 400, 'LP': 450,
        'OS': 400, 'WP': 450, 'BY': 400,
        'WN': 400, 'BN': 350, 'TL': 400, 'TS': 400,
        'HS': 380, 'SH': 380, 'SL': 380, 'MH': 380, 'PH': 380,
        'HI': 380, 'WH': 380, 'BH': 380, 'PE': 380, 'BI': 380,
        'AB': 450, 'BA': 350, 'PA': 350, 'UA': 350,
        'RM': 400, 'SM': 450, 'BE': 400, 'SV': 400,
        'BC': 400, 'AE': 400, 'SG': 400, 'WE': 350, 'EL': 350,
        'SI': 350, 'RL': 350, 'RE': 350,
        'YP': 450, 'BW': 350, 'WA': 400, 'GA': 400, 'AS': 400,
        'WO': 420, 'RO': 420, 'SK': 400, 'BO': 420, 'SO': 400,
        'BJ': 350, 'CK': 420, 'SW': 420, 'BR': 420, 'SN': 400,
        'PO': 380, 'DO': 380, 'CO': 420, 'PN': 400, 'CB': 420,
        'QI': 380, 'OV': 380, 'WK': 380, 'NK': 400, 'WL': 400,
        'QS': 400,
    }

    _FALLBACK_SHADE_TOLERANCE = {
        'WO': 0.50, 'RO': 0.50, 'SM': 0.90, 'WN': 0.30,
        'YP': 0.30, 'WA': 0.30, 'BC': 0.40, 'SP': 0.30,
        'RM': 0.85, 'AB': 0.90, 'BO': 0.50, 'SH': 0.50,
    }

    def __init__(self, default_species: str = 'WO', max_sdi: Optional[float] = None,
                 variant: str = 'CS'):
        """Initialize the CS mortality model.

        Args:
            default_species: Default species code for coefficient lookups
            max_sdi: Maximum SDI for the stand (if None, uses species default)
            variant: Variant code
        """
        super().__init__(default_species=default_species, max_sdi=max_sdi, variant=variant)


class OCMortalityModel(LSMortalityModel):
    """FVS Southwest Oregon mortality model.

    Direct port of subroutine MORTS (oc/morts.f). Like LS, OC uses a per-species
    background mortality logistic plus an SDI-based density mortality, with the
    background rate halved per morts.f line 520. Two structural differences vs LS:

    1. Seven background-mortality groups instead of four. Group 7 is a special
       constraint group for redwood (RW, ispc 50) and giant sequoia (GS, ispc 23)
       with positive PMD (DECREASING mortality with diameter) and a floor of
       0.0001 enforced for the two species (morts.f:512-516).
    2. Species-to-group mapping is read from oc_mortality_defaults.json rather
       than hard-coded in Python; this is the IBGMAP array from oc/morts.f:122-124.

    Coefficients PMSC/PMD are taken verbatim from oc/morts.f:118-121:

        PMSC = [6.5112, 7.2985, 5.1677, 9.6943, 5.9617, 5.5877, 2.596805]
        PMD  = [-0.0052485, -0.0129121, -0.0077681, -0.0127328,
                -0.0340128, -0.005348,   0.512610]

    Density-mortality distribution shares the same SDI-based logic as LS;
    OC's varmrt.f follows the same Reineke approach with VARADJ shade-tolerance
    factors.
    """

    _COEFFICIENT_FILE = 'oc/oc_mortality_coefficients.json'
    _DEFAULTS_FILE = 'oc/oc_mortality_defaults.json'

    # 7-group background mortality coefficients (PMSC, PMD) from oc/morts.f:118-121.
    # Group 7 has positive PMD (decreasing mortality with diameter) and is used
    # only for redwood and giant sequoia, where larger trees have very low
    # background mortality.
    MORTALITY_GROUPS = {
        1: {'P0': 6.5112,    'P1': -0.0052485},
        2: {'P0': 7.2985,    'P1': -0.0129121},
        3: {'P0': 5.1677,    'P1': -0.0077681},
        4: {'P0': 9.6943,    'P1': -0.0127328},
        5: {'P0': 5.9617,    'P1': -0.0340128},
        6: {'P0': 5.5877,    'P1': -0.005348},
        7: {'P0': 2.596805,  'P1': 0.512610},
    }

    # Default fallback species → group mapping (oc/morts.f IBGMAP) — used only
    # if oc_mortality_defaults.json is missing. Mirrors the JSON.
    _FALLBACK_SPECIES_MORTALITY_GROUP = {
        'PC': 3, 'IC': 3, 'RC': 3, 'GF': 3, 'RF': 3, 'SH': 3,
        'DF': 2, 'WH': 4, 'MH': 4, 'WB': 1, 'KP': 1, 'LP': 5,
        'CP': 1, 'LM': 1, 'JP': 6, 'SP': 1, 'WP': 1, 'PP': 6,
        'MP': 6, 'GP': 6, 'WJ': 3, 'BR': 4, 'GS': 7, 'PY': 3,
        'OS': 3, 'LO': 3, 'CY': 3, 'BL': 3, 'EO': 3, 'WO': 3,
        'BO': 3, 'VO': 3, 'IO': 3, 'BM': 3, 'BU': 3, 'RA': 3,
        'MA': 3, 'GC': 3, 'DG': 3, 'FL': 3, 'WN': 3, 'TO': 3,
        'SY': 3, 'AS': 3, 'CW': 3, 'WI': 3, 'CN': 3, 'CL': 3,
        'OH': 3, 'RW': 7,
    }

    _FALLBACK_SDI_MAXIMUMS = {
        'PC': 570, 'IC': 570, 'RC': 570, 'GF': 760, 'RF': 800, 'SH': 800,
        'DF': 600, 'WH': 580, 'MH': 580, 'WB': 460, 'KP': 430, 'LP': 580,
        'CP': 430, 'LM': 460, 'JP': 430, 'SP': 430, 'WP': 460, 'PP': 430,
        'MP': 430, 'GP': 430, 'WJ': 330, 'BR': 580, 'GS': 1052, 'PY': 570,
        'OS': 430, 'LO': 550, 'CY': 550, 'BL': 550, 'EO': 550, 'WO': 550,
        'BO': 550, 'VO': 550, 'IO': 550, 'BM': 550, 'BU': 550, 'RA': 550,
        'MA': 550, 'GC': 550, 'DG': 550, 'FL': 550, 'WN': 550, 'TO': 550,
        'SY': 550, 'AS': 550, 'CW': 550, 'WI': 550, 'CN': 550, 'CL': 550,
        'OH': 550, 'RW': 1052,
    }
    DEFAULT_SDI_MAX = 550

    _FALLBACK_SHADE_TOLERANCE = {
        'PC': 0.60, 'IC': 0.60, 'RC': 0.60, 'GF': 0.55, 'RF': 0.50, 'SH': 0.50,
        'DF': 0.65, 'WH': 0.65, 'MH': 0.75, 'WB': 0.90, 'KP': 0.90, 'LP': 0.90,
        'CP': 1.10, 'LM': 0.90, 'JP': 0.85, 'SP': 0.70, 'WP': 0.75, 'PP': 0.85,
        'MP': 0.85, 'GP': 1.10, 'WJ': 1.10, 'BR': 0.65, 'GS': 0.80, 'PY': 0.55,
        'OS': 0.65, 'LO': 1.00, 'CY': 1.00, 'BL': 1.00, 'EO': 1.00, 'WO': 1.00,
        'BO': 1.00, 'VO': 1.00, 'IO': 1.00, 'BM': 0.80, 'BU': 0.80, 'RA': 1.00,
        'MA': 0.80, 'GC': 0.80, 'DG': 0.80, 'FL': 0.80, 'WN': 0.80, 'TO': 0.55,
        'SY': 0.80, 'AS': 0.80, 'CW': 0.80, 'WI': 1.00, 'CN': 1.00, 'CL': 1.00,
        'OH': 1.00, 'RW': 0.80,
    }

    def __init__(self, default_species: str = 'DF', max_sdi: Optional[float] = None,
                 variant: str = 'OC'):
        super().__init__(default_species=default_species, max_sdi=max_sdi, variant=variant)

    def _get_background_rate_for_tree(
        self, tree: 'Tree', cycle_length: int
    ) -> float:
        """OC 7-group background mortality with RW/GS constraint floor.

        Direct port of oc/morts.f:509-520. Like LS, the rate is halved compared
        to the raw logistic. Redwood (RW) and giant sequoia (GS) get a 0.0001
        annual floor (morts.f:512-516).
        """
        # Default to group 3 for unknown species (matches majority of OC species)
        group = self.SPECIES_MORTALITY_GROUP.get(tree.species, 3)
        group_coeffs = self.MORTALITY_GROUPS[group]
        p0 = group_coeffs['P0']
        p1 = group_coeffs['P1']

        # Base annual mortality rate (logistic) — morts.f:509
        ri = 1.0 / (1.0 + math.exp(p0 + p1 * tree.dbh))

        # RW/GS constraint: enforce a 0.0001 floor before the halving step
        # (morts.f:512-516)
        if tree.species in ('RW', 'GS') and ri < 0.0001:
            ri = 0.0001

        # OC halves the background rate (morts.f:520 — "test runs show
        # background mortality rate is high, cut it in half")
        ri *= 0.5

        # Adjust for cycle length
        rip = 1.0 - ((1.0 - ri) ** cycle_length)
        return rip

    def _get_varadj_for_tree(self, species: str) -> float:
        """Return VARMRT shade-tolerance coefficient for OC species.

        OC varmrt.f:69 says "VARADJ = TREE SHADE TOLERANCE (1.0 = MOST
        INTOLERANT)" and uses `EFFTR = PEFF * VARADJ * 0.1` (no flip,
        OC varmrt.f:109). `oc_mortality_coefficients.json` stores VARADJ
        verbatim from the Fortran DATA statement, so override the LS
        tolerance-flip and return the stored value directly.
        """
        return self._shade_tolerance.get(species, 0.5)


class OrganonSwoMortalityModel(OCMortalityModel):
    """ORGANON SWO mortality model for the OC variant.

    When the OC variant has LORGANON=TRUE (oc/grinit.f:342), every cycle
    dgdriv.f:370 calls the ORGANON DLL which computes mortality for all
    trees.  In oc/morts.f:498, when SMORMT > 0 the ORGANON mortality
    (MORTEXP array) completely replaces FVS SDI-based mortality.

    This class ports the ORGANON SWO individual-tree mortality equation
    (PM_SWO from bin/FVSoc_buildDir/mortality.f) and the MORTAL_RUN
    density-dependent caps.  When no "big 6" conifer species meet the
    ORGANON threshold (HT > 4.5 and DBH >= 0.1), the model falls back
    to the FVS OCMortalityModel parent class.

    The individual tree equation is a logistic:

        PMK = B0 + B1*DBH + B2*DBH^2 + B3*CR + B4*SI
              + B5*BAL + B6*BAL*exp(B7*OG)

    where SI is total-height site index, CR is crown ratio (0–1),
    BAL is basal area of larger trees, and OG is the old-growth
    indicator (mean DBH*HT/10000 for the top 5 TPA by DBH class).

    Coefficients from Hann and Hanus (2001) FRL Research Contribution 34
    and other sources cited in mortality.f.
    """

    # OC FVS species numbers for the "big 6" conifers (dgdriv.f:227).
    # If ANY tree of these species meets HT > 4.5 and DBH >= 0.1, ORGANON
    # runs for ALL trees.  Species codes: IC, GF, DF, SP, PP.
    _BIG6_SPECIES = frozenset({'IC', 'GF', 'DF', 'SP', 'PP'})

    # PM_SWO coefficients: 18 SWO species groups × 8 equation parameters + POW.
    # From mortality.f MPAR(18,9) DATA statement.
    # Key: group number (1–18).
    # Value: (B0, B1, B2, B3, B4, B5, B6, B7, POW).
    _PM_SWO = {
        1:  (-4.648483270, -0.266558690,  0.003699110, -2.118026640,  0.025499430,  0.003361340,  0.013553950, -2.723470950, 1.0),  # DF
        2:  (-2.215777201, -0.162895666,  0.003317290, -3.561438261,  0.014644689,  0.0,          0.0,          0.0,          1.0),  # GW
        3:  (-1.050000682, -0.194363402,  0.003803100, -3.557300286,  0.003971638,  0.005573601,  0.0,          0.0,          1.0),  # PP
        4:  (-1.531051304,  0.0,          0.0,          0.0,          0.0,          0.0,          0.0,          0.0,          1.0),  # SP
        5:  (-1.922689902, -0.136081990,  0.002479863, -3.178123293,  0.0,          0.004684133,  0.0,          0.0,          1.0),  # IC
        6:  (-1.166211991,  0.0,          0.0,         -4.602668157,  0.0,          0.0,          0.0,          0.0,          1.0),  # WH
        7:  (-0.761609,    -0.529366,     0.0,         -4.74019,      0.0119587,    0.00756365,   0.0,          0.0,          1.0),  # RC
        8:  (-4.072781265, -0.176433475,  0.0,         -1.729453975,  0.0,          0.012525642,  0.0,          0.0,          1.0),  # PY
        9:  (-6.089598985, -0.245615070,  0.0,         -3.208265570,  0.033348079,  0.013571319,  0.0,          0.0,          1.0),  # MD
        10: (-4.317549852, -0.057696253,  0.0,          0.0,          0.004861355,  0.00998129,   0.0,          0.0,          1.0),  # GC
        11: (-2.410756914,  0.0,          0.0,         -1.049353753,  0.008845583,  0.0,          0.0,          0.0,          1.0),  # TA
        12: (-2.990451960,  0.0,          0.0,          0.0,          0.0,          0.002884840,  0.0,          0.0,          1.0),  # CL
        13: (-2.976822456,  0.0,          0.0,         -6.223250962,  0.0,          0.0,          0.0,          0.0,          1.0),  # BL
        14: (-6.00031085,  -0.10490823,   0.0,         -0.99541909,   0.00912739,   0.87115652,   0.0,          0.0,          1.0),  # WO
        15: (-3.108619921, -0.570366764,  0.018205398, -4.584655216,  0.014926170,  0.012419026,  0.0,          0.0,          1.0),  # BO
        16: (-2.0,         -0.5,          0.015,       -3.0,          0.015,        0.01,         0.0,          0.0,          1.0),  # RA
        17: (-3.020345211,  0.0,          0.0,         -8.467882343,  0.013966388,  0.009461545,  0.0,          0.0,          1.0),  # PD
        18: (-1.386294361,  0.0,          0.0,          0.0,          0.0,          0.0,          0.0,          0.0,          1.0),  # WI
    }

    # OC species code → ORGANON SWO species group (1–18).
    # Derived from orgspc.f (OSPMAP) → SPGROUP_EDIT (SCODE1 with ISX>2 adjustment).
    _SPECIES_TO_SWO_GROUP = {
        'PC': 7,  'IC': 5,  'RC': 7,  'GF': 2,  'RF': 1,  'SH': 1,
        'DF': 1,  'WH': 6,  'MH': 6,  'WB': 3,  'KP': 3,  'LP': 3,
        'CP': 3,  'LM': 3,  'JP': 3,  'SP': 4,  'WP': 3,  'PP': 3,
        'MP': 3,  'GP': 3,  'WJ': 8,  'BR': 2,  'GS': 3,  'PY': 8,
        'OS': 8,  'LO': 12, 'CY': 12, 'BL': 12, 'EO': 12, 'WO': 14,
        'BO': 15, 'VO': 12, 'IO': 12, 'BM': 13, 'BU': 13, 'RA': 16,
        'MA': 9,  'GC': 10, 'DG': 17, 'FL': 13, 'WN': 13, 'TO': 11,
        'SY': 13, 'AS': 13, 'CW': 13, 'WI': 18, 'CN': 17, 'CL': 17,
        'OH': 17, 'RW': 3,
    }

    # DF site index conversion from PP (sitset.f / execute2.f:263-267).
    _PP_TO_DF_SI = 1.062934
    _DF_TO_PP_SI = 0.940792

    # ORGANON SWO self-thinning line parameters (submax.f).
    _A2 = 0.62305                # Reineke (1933) slope
    _BASE_A1 = 6.21113           # Default SWO (max SDI ≈ 530.2)
    _A1_TF_MODIFIER = 1.03481817 # True fir modifier
    _A1_OC_MODIFIER = 0.9943501  # Other conifer modifier
    _RDCC = 0.60                 # Critical relative density (VERSION ≤ 3)
    _A3 = 14.39533971            # Density trajectory exponent (VERSION ≤ 3)
    _KB = 0.005454154            # Basal area factor (pi/576)

    # Persistent MORTAL_RUN state (per instance, reset on new stand).
    def __init__(self, default_species: str = 'DF', max_sdi: Optional[float] = None,
                 variant: str = 'OC'):
        super().__init__(default_species=default_species, max_sdi=max_sdi, variant=variant)
        self._rd0 = 0.0
        self._no = 0.0
        self._a1max = self._BASE_A1
        self._pa1max = self._BASE_A1
        self._organon_cycle = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_mortality(
        self,
        trees: List['Tree'],
        cycle_length: int = 5,
        max_sdi: Optional[float] = None,
        random_seed: Optional[int] = None,
        pre_growth_qmd: float = 0.0,
        pre_growth_tpa: int = 0,
        site_index: Optional[float] = None,
        **kwargs,
    ) -> MortalityResult:
        """Apply ORGANON SWO mortality when big-6 trees are present.

        Falls back to the parent OCMortalityModel (FVS SDI-based) when
        no big-6 species meets the ORGANON threshold (HT > 4.5 ft and
        DBH >= 0.1 in).  This matches the Fortran behaviour in
        dgdriv.f:254-259.

        Args:
            trees: Post-growth tree list (each tree = 1 TPA).
            cycle_length: Projection cycle in years.
            site_index: Stand site index (total height).  Required for
                ORGANON path; ignored when falling back to FVS.
            Other args: Forwarded to parent ``apply_mortality``.

        Returns:
            MortalityResult with survivors and mortality count.
        """
        if len(trees) <= 1:
            return MortalityResult(survivors=list(trees), mortality_count=0,
                                   trees_died=[])

        # Do any big-6 species meet the ORGANON threshold?
        has_organon = any(
            t.height > 4.5 and t.dbh >= 0.1 and t.species in self._BIG6_SPECIES
            for t in trees
        )

        if not has_organon:
            return super().apply_mortality(
                trees, cycle_length=cycle_length, max_sdi=max_sdi,
                random_seed=random_seed, pre_growth_qmd=pre_growth_qmd,
                pre_growth_tpa=pre_growth_tpa,
            )

        return self._apply_organon_mortality(
            trees, cycle_length, site_index or 80.0, random_seed,
        )

    # ------------------------------------------------------------------
    # ORGANON SWO mortality core
    # ------------------------------------------------------------------

    def _apply_organon_mortality(
        self,
        trees: List['Tree'],
        cycle_length: int,
        site_index: float,
        random_seed: Optional[int],
    ) -> MortalityResult:
        """Full ORGANON MORTAL_RUN logic (mortality.f).

        1. Compute stand-level density (STBA, STN, RD).
        2. Compute old-growth indicator (OG).
        3. For each tree: individual logit (PM_SWO) → 5-yr mortality rate.
        4. If density > RDCC: iteratively increase logit (KR1) to cap density.
        5. Apply mortality stochastically.
        """
        rng = random.Random(random_seed) if random_seed is not None else random.Random()

        # DF site index (ORGANON always uses DF SI).
        df_si = self._resolve_df_site_index(site_index)

        # Stand-level metrics (MORTAL_RUN lines 58-73).
        stba = sum(self._KB * t.dbh ** 2 for t in trees)
        stn = float(len(trees))

        if stn < 1 or stba <= 0:
            return MortalityResult(survivors=list(trees), mortality_count=0,
                                   trees_died=[])

        # A1/A2 from SUBMAX (for pure-DF stands, A1 = BASE_A1).
        a1, a2 = self._compute_submax(trees)

        # Relative density (mortality.f:79).
        sqmda = math.sqrt(stba / (self._KB * stn))
        rd = stn / math.exp(a1 / a2 - math.log(sqmda) / a2)

        # Old-growth indicator (mortality.f:737-800, called with XIND=0).
        og = self._compute_oldgro(trees)

        # BAL for each tree (basal area of larger trees).
        bal_map = self._compute_bal(trees)

        # Individual-tree logit (PM_SWO) and POW.
        pmk_list = []   # per-tree logit
        pow_list = []    # per-tree POW exponent
        for t in trees:
            grp = self._SPECIES_TO_SWO_GROUP.get(t.species, 1)
            coeffs = self._PM_SWO[grp]
            bal = bal_map[id(t)]
            pmk = self._pm_swo(coeffs, t.dbh, t.crown_ratio, df_si, bal, og, grp)
            pmk_list.append(pmk)
            pow_list.append(coeffs[8])

        # Convert logit to 5-yr mortality rates and compute post-mortality
        # TPA/BA (mortality.f:128-142).
        na = 0.0     # post-mortality TPA
        baa = 0.0    # post-mortality BA
        pm_rates = []
        for i, t in enumerate(trees):
            cr = t.crown_ratio
            cradj = 1.0
            if cr <= 0.17:
                cradj = 1.0 - math.exp(-(25.0 * cr) ** 2)
            xpm = 1.0 / (1.0 + math.exp(-pmk_list[i]))
            ps = (1.0 - xpm) ** pow_list[i]
            pm = 1.0 - ps * cradj
            pm_rates.append(pm)
            na += 1.0 - pm  # expected survivors from this tree
            baa += self._KB * t.dbh ** 2 * (1.0 - pm)

        # Density-dependent adjustment (mortality.f:147-316).
        # Only active when MORT=TRUE (INDS(9)=1, default for OC).
        kr1 = self._density_adjustment(
            trees, pmk_list, pow_list, stn, stba, na, baa,
            rd, a1, a2,
        )

        # If kr1 > 0, recompute PM with shifted logit.
        if kr1 > 0.0:
            pm_rates = []
            for i, t in enumerate(trees):
                cr = t.crown_ratio
                cradj = 1.0
                if cr <= 0.17:
                    cradj = 1.0 - math.exp(-(25.0 * cr) ** 2)
                xpm = 1.0 / (1.0 + math.exp(-(kr1 + pmk_list[i])))
                ps = (1.0 - xpm) ** pow_list[i]
                pm = 1.0 - ps * cradj
                pm_rates.append(pm)

        # Scale 5-yr rate to cycle length (oc/morts.f:499: FINT/5).
        scale = cycle_length / 5.0

        # Apply mortality stochastically.
        survivors = []
        trees_died = []
        for i, t in enumerate(trees):
            # Expected trees dying from this 1-TPA record.
            mort_prob = pm_rates[i] * scale
            mort_prob = min(mort_prob, 1.0)
            if rng.random() > mort_prob:
                survivors.append(t)
            else:
                trees_died.append(t)

        self._organon_cycle += 1

        return MortalityResult(
            survivors=survivors,
            mortality_count=len(trees_died),
            trees_died=trees_died,
        )

    # ------------------------------------------------------------------
    # PM_SWO equation (mortality.f:441-539)
    # ------------------------------------------------------------------

    @staticmethod
    def _pm_swo(
        coeffs: tuple, dbh: float, cr: float, si: float,
        bal: float, og: float, grp: int,
    ) -> float:
        """Compute the ORGANON SWO mortality logit for one tree.

        Args:
            coeffs: (B0..B7, POW) for the species group.
            dbh: Diameter at breast height (inches).
            cr: Crown ratio (0–1).
            si: DF total-height site index (feet).
            bal: Basal area of larger trees (sq ft/acre).
            og: Old-growth indicator.
            grp: SWO species group (1–18).

        Returns:
            PMK logit value.
        """
        b0, b1, b2, b3, b4, b5, b6, b7 = coeffs[:8]
        if grp == 14:  # Oregon white oak — uses log(BAL+5)
            return (b0 + b1 * dbh + b2 * dbh ** 2 + b3 * cr
                    + b4 * si + b5 * math.log(bal + 5.0))
        return (b0 + b1 * dbh + b2 * dbh ** 2 + b3 * cr
                + b4 * si + b5 * bal + b6 * bal * math.exp(b7 * og))

    # ------------------------------------------------------------------
    # OLDGRO indicator (mortality.f:737-800)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_oldgro(trees: List['Tree']) -> float:
        """Old-growth indicator: mean DBH*HT/10000 for top 5 TPA.

        Accumulates trees into 1-inch DBH classes from largest to smallest,
        stopping once 5 TPA are collected (fractional last class).
        """
        # Build 1-inch DBH class accumulators (indices 1..100).
        htcl = [0.0] * 101   # sum of HT*TPA in class
        dcl = [0.0] * 101    # sum of DBH*TPA in class
        trcl = [0.0] * 101   # sum of TPA in class
        for t in trees:
            idx = min(int(t.dbh) + 1, 100)
            htcl[idx] += t.height  # each tree = 1 TPA
            dcl[idx] += t.dbh
            trcl[idx] += 1.0

        totht = 0.0
        totd = 0.0
        tottr = 0.0
        for i in range(100, 0, -1):
            totht += htcl[i]
            totd += dcl[i]
            tottr += trcl[i]
            if tottr > 5.0:
                trdiff = trcl[i] - (tottr - 5.0)
                if trcl[i] > 0:
                    totht = totht - htcl[i] + (htcl[i] / trcl[i]) * trdiff
                    totd = totd - dcl[i] + (dcl[i] / trcl[i]) * trdiff
                tottr = 5.0
                break
        if tottr > 0.0:
            ht5 = totht / tottr
            dbh5 = totd / tottr
            return dbh5 * ht5 / 10000.0
        return 0.0

    # ------------------------------------------------------------------
    # BAL computation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_bal(trees: List['Tree']) -> Dict[int, float]:
        """Basal area of larger trees for each tree.

        Returns a dict mapping ``id(tree)`` → BAL (sq ft/acre).
        """
        kb = 0.005454154
        sorted_trees = sorted(trees, key=lambda t: t.dbh)
        total_ba = sum(kb * t.dbh ** 2 for t in sorted_trees)
        bal_map: Dict[int, float] = {}
        cum_ba = 0.0
        i = 0
        n = len(sorted_trees)
        while i < n:
            cur_dbh = sorted_trees[i].dbh
            grp_start = i
            grp_ba = 0.0
            while i < n and sorted_trees[i].dbh == cur_dbh:
                grp_ba += kb * sorted_trees[i].dbh ** 2
                i += 1
            ba_larger = total_ba - cum_ba - grp_ba
            for j in range(grp_start, i):
                bal_map[id(sorted_trees[j])] = ba_larger
            cum_ba += grp_ba
        return bal_map

    # ------------------------------------------------------------------
    # SUBMAX: maximum size-density line (submax.f)
    # ------------------------------------------------------------------

    def _compute_submax(self, trees: List['Tree']) -> Tuple[float, float]:
        """Compute A1, A2 for the self-thinning line.

        For SWO, A1 is modified by species composition (DF, true-fir, PP
        proportions of basal area in the top 3 species groups).
        """
        a2 = self._A2
        tempa1 = self._BASE_A1

        # BA by species group for the first 3 groups (DF, GW, PP).
        bagrp = [0.0, 0.0, 0.0]
        for t in trees:
            grp = self._SPECIES_TO_SWO_GROUP.get(t.species, 1)
            if 1 <= grp <= 3:
                bagrp[grp - 1] += self._KB * t.dbh ** 2

        totba = sum(bagrp)
        if totba > 0:
            pdf = bagrp[0] / totba   # DF proportion
            ptf = bagrp[1] / totba   # true fir proportion
            ppp = bagrp[2] / totba   # PP proportion
        else:
            pdf = ptf = ppp = 0.0

        tfmod = self._A1_TF_MODIFIER
        ocmod = self._A1_OC_MODIFIER

        if pdf >= 0.5:
            a1mod = 1.0
        elif ptf >= 2.0 / 3.0:
            a1mod = tfmod
        elif ppp >= 2.0 / 3.0:
            a1mod = ocmod
        else:
            a1mod = pdf + tfmod * ptf + ocmod * ppp

        if a1mod <= 0.0:
            a1mod = 1.0

        return tempa1 * a1mod, a2

    # ------------------------------------------------------------------
    # Density-dependent mortality cap (mortality.f:147-316)
    # ------------------------------------------------------------------

    def _density_adjustment(
        self,
        trees: List['Tree'],
        pmk_list: List[float],
        pow_list: List[float],
        stn: float,
        stba: float,
        na: float,
        baa: float,
        rd: float,
        a1: float,
        a2: float,
    ) -> float:
        """Determine KR1 shift to PMK if density-dependent caps are needed.

        Returns 0.0 when no adjustment is required (RD ≤ RDCC or target
        QMD exceeds actual QMD).  Otherwise returns the KR1 value that
        shifts all PMK values upward to bring the stand to the target
        density trajectory (mortality.f:239-298).
        """
        rdcc = self._RDCC

        if rd <= rdcc:
            return 0.0

        if na <= 0 or baa <= 0:
            return 0.0

        qmda = math.sqrt(baa / (self._KB * na))

        # First growth cycle initialisation (CYCLG=0).
        is_first = (self._organon_cycle == 0)

        if is_first:
            self._rd0 = rd
            self._no = 0.0
            self._a1max = a1

        if is_first:
            if rd >= 1.0:
                sqmda_start = math.sqrt(stba / (self._KB * stn))
                rda = na / math.exp(a1 / a2 - math.log(qmda) / a2)
                if rda > rd:
                    self._a1max = math.log(sqmda_start) + a2 * math.log(stn)
                else:
                    self._a1max = math.log(qmda) + a2 * math.log(na)
                ind = 1
                if self._a1max < a1:
                    self._a1max = a1
                self._pa1max = self._a1max
            else:
                ind = 0
                if rd > rdcc:
                    xa3 = -1.0 / self._A3
                    self._no = stn * (math.log(rd) / math.log(rdcc)) ** xa3
        else:
            if self._rd0 >= 1.0:
                ind = 1
                self._a1max = math.log(qmda) + a2 * math.log(na)
                if self._a1max > self._pa1max:
                    self._a1max = self._pa1max
                if self._a1max < a1:
                    self._a1max = a1
                self._pa1max = self._a1max
            elif rd >= 1.0 and self._no <= 0.0:
                sqmda_start = math.sqrt(stba / (self._KB * stn))
                rda = na / math.exp(a1 / a2 - math.log(qmda) / a2)
                if rda > rd:
                    self._a1max = math.log(sqmda_start) + a2 * math.log(stn)
                else:
                    self._a1max = math.log(qmda) + a2 * math.log(na)
                ind = 1
                if self._a1max < a1:
                    self._a1max = a1
                self._pa1max = self._a1max
            else:
                ind = 0
                if rd > rdcc and self._no <= 0.0:
                    xa3 = -1.0 / self._A3
                    self._no = stn * (math.log(rd) / math.log(rdcc)) ** xa3

        # Target QMD (QMDP).
        if ind == 0 and self._no > 0.0:
            qmdp = self._quad1(na, self._no, rdcc, a1)
        else:
            qmdp = math.exp(self._a1max - a2 * math.log(max(na, 0.001)))

        # No additional mortality needed if target QMD > actual QMD.
        if qmdp > qmda:
            return 0.0

        # Iterative search for KR1 (mortality.f:241-278).
        kr1 = 0.0
        for kk in range(1, 8):
            nk = 10.0 / 10.0 ** kk
            while True:
                kr1 += nk
                naa = 0.0
                baaa = 0.0
                for i, t in enumerate(trees):
                    cr = t.crown_ratio
                    cradj = 1.0
                    if cr <= 0.17:
                        cradj = 1.0 - math.exp(-(25.0 * cr) ** 2)
                    xpm = 1.0 / (1.0 + math.exp(-(kr1 + pmk_list[i])))
                    ps = (1.0 - xpm) ** pow_list[i]
                    pm = 1.0 - ps * cradj
                    naa += 1.0 - pm
                    baaa += self._KB * t.dbh ** 2 * (1.0 - pm)
                if naa <= 0:
                    break
                qmda_adj = math.sqrt(baaa / (self._KB * naa))
                if ind == 0 and self._no > 0.0:
                    qmdp = self._quad1(naa, self._no, rdcc, a1)
                else:
                    qmdp = math.exp(self._a1max - a2 * math.log(max(naa, 0.001)))
                if qmdp >= qmda_adj:
                    kr1 -= nk
                    break

        return kr1

    @staticmethod
    def _quad1(ni: float, no: float, rdcc: float, a1: float) -> float:
        """QUAD1 function from mortality.f:323-334."""
        a2 = 0.62305
        a3_val = 14.39533971
        a4 = -(math.log(rdcc) * a2 / a1)
        x = a1 - a2 * math.log(max(ni, 0.001)) - (a1 * a4) * math.exp(
            -a3_val * (math.log(max(no, 0.001)) - math.log(max(ni, 0.001)))
        )
        return math.exp(x)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_df_site_index(self, stand_si: float) -> float:
        """Convert stand site index to DF total-height site index.

        ORGANON SWO always uses DF site index (execute2.f:263-267).
        If the default species is PP, convert.
        """
        if self.default_species == 'PP':
            return self._PP_TO_DF_SI * stand_si
        return stand_si


# Module-level convenience functions
_default_model: Optional[MortalityModel] = None


_mortality_cache: dict[tuple, object] = {}


def create_mortality_model(
    default_species: str = 'LP',
    max_sdi: Optional[float] = None,
    variant: Optional[str] = None
):
    """Factory function to create a variant-appropriate mortality model.

    Args:
        default_species: Default species code
        max_sdi: Maximum SDI for the stand
        variant: FVS variant code (e.g., 'SN', 'LS')

    Returns:
        MortalityModel or LSMortalityModel instance (cached by species/variant/sdi)
    """
    if variant is None:
        from .config_loader import get_default_variant
        variant = get_default_variant()

    from .variant_registry import get_variant_config
    config = get_variant_config(variant)

    # For variants that use the base MortalityModel with variant-specific SDI
    # maximums (PN, WC, OP), look up SDI from the registry when not provided.
    if config.mortality_needs_sdi_lookup and max_sdi is None:
        sdi_maximums = config.sdi_maximums
        max_sdi = sdi_maximums.get(default_species, 850)

    cache_key = (default_species, variant, max_sdi)
    if cache_key not in _mortality_cache:
        _mortality_cache[cache_key] = config.mortality_class(
            default_species=default_species, max_sdi=max_sdi
        )
    return _mortality_cache[cache_key]


def get_mortality_model(species: str = 'LP') -> MortalityModel:
    """Get or create a mortality model instance.

    Args:
        species: Default species code

    Returns:
        MortalityModel instance
    """
    global _default_model
    if _default_model is None:
        _default_model = MortalityModel(species)
    return _default_model


def apply_stand_mortality(
    trees: List['Tree'],
    cycle_length: int = 5,
    max_sdi: Optional[float] = None
) -> MortalityResult:
    """Apply mortality to a list of trees.

    Convenience function using the default model.

    Args:
        trees: List of trees
        cycle_length: Cycle length in years
        max_sdi: Maximum SDI (uses default if None)

    Returns:
        MortalityResult
    """
    return get_mortality_model().apply_mortality(
        trees, cycle_length=cycle_length, max_sdi=max_sdi
    )

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
import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING

from .tree_utils import calculate_tree_basal_area, calculate_stand_basal_area

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

    # SN VARADJ shade tolerance from varmrt.f (90 species)
    # Higher value = shade INTOLERANT = higher mortality efficiency
    # Lower value = shade TOLERANT = survives better under competition
    SN_VARADJ = {
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

        # Load coefficients if not already loaded
        if not MortalityModel._coefficients_loaded:
            self._load_mortality_coefficients()

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

        except Exception:
            # Return default values if config not available
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

    def apply_mortality(
        self,
        trees: List['Tree'],
        cycle_length: int = 5,
        max_sdi: Optional[float] = None,
        random_seed: Optional[int] = None,
        pre_growth_qmd: float = 0.0,
        pre_growth_tpa: int = 0
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

        Returns:
            MortalityResult with survivors and mortality count
        """
        if len(trees) <= 1:
            return MortalityResult(survivors=list(trees), mortality_count=0, trees_died=[])

        if random_seed is not None:
            random.seed(random_seed)

        max_sdi = max_sdi or self.max_sdi or 450

        # Staging: only trees >= DBHSTAGE count toward density (morts.f)
        staged_dbhs = [t.dbh for t in trees if t.dbh >= self.DBHSTAGE]
        t = len(staged_dbhs)  # T in Fortran

        if t < 2:
            # Not enough staged trees — background mortality only
            coefficients = self.get_coefficients()
            tree_data = self._calculate_tree_percentiles(trees)
            return self._apply_background_mortality(
                tree_data, coefficients, cycle_length
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
                tree_data, coefficients, cycle_length, round(tokill)
            )
        else:
            # Background mortality only
            result = self._apply_background_mortality(
                tree_data, coefficients, cycle_length
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

    def _apply_background_mortality(
        self,
        tree_data: List[Tuple['Tree', float]],
        coefficients: Dict[str, Any],
        cycle_length: int
    ) -> MortalityResult:
        """Apply background mortality only (below SDI threshold).

        Uses equations 5.0.1 and 5.0.2 from morts.f.

        Args:
            tree_data: List of (tree, percentile) tuples
            coefficients: Mortality coefficients
            cycle_length: Cycle length in years

        Returns:
            MortalityResult
        """
        survivors = []
        trees_died = []

        for tree, pct in tree_data:
            # Get species-specific coefficients (Equation 5.0.1)
            p0, p1 = coefficients['background'].get(
                tree.species, (5.5876999, -0.0053480)
            )

            # Individual tree background mortality rate (Equation 5.0.1)
            ri = 1.0 / (1.0 + math.exp(p0 + p1 * tree.dbh))

            # Adjust for cycle length (Equation 5.0.2)
            rip = 1.0 - ((1.0 - ri) ** cycle_length)

            # Apply mortality stochastically
            if random.random() > rip:
                survivors.append(tree)
            else:
                trees_died.append(tree)

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
        tokill: int
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

        Returns:
            MortalityResult
        """
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

            # Shade tolerance (VARADJ from varmrt.f)
            varadj = self.SN_VARADJ.get(tree.species, 0.5)

            # Combined efficiency (varmrt.f line 123)
            eff = peff * varadj * 0.1
            efftr.append(eff)

        # Normalize efficiencies to get per-tree kill probability
        total_eff = sum(efftr)
        if total_eff <= 0:
            total_eff = 1.0

        # Each tree's expected kills = tokill * (its efficiency / total)
        # Since each tree can only die once (TPA=1), probability = min(1, expected)
        survivors = []
        trees_died = []

        # Create (tree, pct, kill_prob) list
        kill_probs = []
        for i, (tree, pct) in enumerate(tree_data):
            expected = tokill * efftr[i] / total_eff
            prob = min(0.99, expected)  # Cap to avoid certain death
            kill_probs.append((tree, prob))

        # Apply stochastic mortality weighted by efficiency
        for tree, prob in kill_probs:
            if random.random() < prob:
                trees_died.append(tree)
            else:
                survivors.append(tree)

        # If we killed too many or too few, adjust deterministically
        # This ensures we hit close to the target (Fortran VARMRT iterates)
        actual_killed = len(trees_died)
        if actual_killed > tokill + 2:
            # Too many died — rescue some (largest first, they had lowest prob)
            excess = actual_killed - tokill
            trees_died.sort(key=lambda t: t.dbh, reverse=True)
            rescued = trees_died[:excess]
            trees_died = trees_died[excess:]
            survivors.extend(rescued)
        elif actual_killed < tokill - 2 and actual_killed < tpa - 1:
            # Too few died — kill more (smallest first, they had highest prob)
            deficit = tokill - actual_killed
            survivors.sort(key=lambda t: t.dbh)
            additional = survivors[:min(deficit, len(survivors) - 1)]
            for t in additional:
                survivors.remove(t)
                trees_died.append(t)

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


class LSMortalityModel:
    """FVS Lake States mortality model.

    Implements the LS variant mortality model from morts.f:
    1. 4-group background mortality with halved logistic rates
    2. SDI-based density mortality with VARADJ shade tolerance adjustment

    The 4 mortality groups have different logistic coefficients (PMSC, PMD)
    from morts.f:
    - Group 1: PMSC=5.1677, PMD=-0.00777
    - Group 2: PMSC=9.6943, PMD=-0.01273
    - Group 3: PMSC=5.5877, PMD=-0.00535
    - Group 4: PMSC=5.9617, PMD=-0.03401

    Background rates are halved compared to the logistic.
    Density mortality selects EITHER background OR density-based (never both),
    matching Fortran varmrt.f behavior.

    Subclasses (e.g., NEMortalityModel) override class attributes to use
    variant-specific coefficient files, species-group mappings, and SDI maximums.
    """

    # Coefficient file path (relative to cfg/), overridden by subclasses
    _COEFFICIENT_FILE = 'ls/ls_mortality_coefficients.json'

    # SDI threshold constants (same as SN)
    LOWER_THRESHOLD = 0.55
    UPPER_THRESHOLD = 0.85

    # 4-group background mortality coefficients (PMSC, PMD) from morts.f lines 99-100
    # PMSC = [5.1677, 9.6943, 5.5877, 5.9617]
    # PMD  = [-0.00777, -0.01273, -0.00535, -0.03401]
    MORTALITY_GROUPS = {
        1: {'P0': 5.1677, 'P1': -0.00777},
        2: {'P0': 9.6943, 'P1': -0.01273},
        3: {'P0': 5.5877, 'P1': -0.00535},
        4: {'P0': 5.9617, 'P1': -0.03401},
    }

    # Species-to-mortality-group mapping from IMAPLS in morts.f (68 species)
    SPECIES_MORTALITY_GROUP = {
        # Group 1 (28 species)
        'JP': 1, 'RN': 1, 'RP': 1, 'WS': 1, 'NS': 1, 'BF': 1,
        'BS': 1, 'TA': 1, 'WC': 1, 'EH': 1, 'GA': 1, 'SV': 1,
        'RM': 1, 'AE': 1, 'RL': 1, 'RE': 1, 'BW': 1, 'SM': 1,
        'BM': 1, 'AB': 1, 'HH': 1, 'BK': 1, 'AH': 1, 'DW': 1,
        'BG': 1, 'WI': 1, 'BL': 1, 'SS': 1,
        # Group 3 (4 species)
        'SC': 3, 'WP': 3, 'OS': 3, 'RC': 3,
        # Group 4 (35 species)
        'BA': 4, 'EC': 4, 'BC': 4, 'YB': 4, 'WA': 4, 'WO': 4,
        'SW': 4, 'BR': 4, 'CK': 4, 'RO': 4, 'BO': 4, 'NP': 4,
        'BH': 4, 'PH': 4, 'SH': 4, 'BT': 4, 'QA': 4, 'BP': 4,
        'PB': 4, 'BN': 4, 'WN': 4, 'OH': 4, 'BE': 4, 'ST': 4,
        'MM': 4, 'AC': 4, 'HK': 4, 'HT': 4, 'AP': 4, 'SY': 4,
        'PR': 4, 'CC': 4, 'PL': 4, 'DM': 4, 'MA': 4,
    }

    # Default SDI maximums (overridden by subclasses)
    _SDI_MAXIMUMS = {
        'JP': 400, 'SC': 400, 'RN': 500, 'RP': 500, 'WP': 450,
        'WS': 500, 'NS': 500, 'BF': 400, 'BS': 400, 'TA': 350,
        'WC': 400, 'EH': 500, 'SM': 450, 'RM': 400, 'QA': 350,
        'PB': 350, 'RO': 400, 'WO': 400, 'YB': 400, 'AB': 450,
    }
    DEFAULT_SDI_MAX = 400

    # Fallback shade tolerances (overridden by subclasses)
    _FALLBACK_SHADE_TOLERANCE = {
        'JP': 0.30, 'RN': 0.30, 'WP': 0.50, 'BF': 0.90,
        'SM': 0.90, 'RM': 0.85, 'QA': 0.10, 'PB': 0.30,
        'RO': 0.50, 'WO': 0.50,
    }

    def __init__(self, default_species: str = 'RN', max_sdi: Optional[float] = None,
                 variant: str = 'LS'):
        """Initialize the LS mortality model.

        Args:
            default_species: Default species code for coefficient lookups
            max_sdi: Maximum SDI for the stand (if None, uses species default)
            variant: Variant code
        """
        self.default_species = default_species
        self.max_sdi = max_sdi
        self.variant = variant
        self._shade_tolerance = {}
        self._load_shade_tolerance()

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

    def _get_background_rate(self, tree: 'Tree', cycle_length: int) -> float:
        """Calculate LS 4-group background mortality rate.

        Rate is halved compared to the base logistic equation per morts.f.

        Args:
            tree: Tree object
            cycle_length: Cycle length in years

        Returns:
            Mortality probability (0-1)
        """
        group = self.SPECIES_MORTALITY_GROUP.get(tree.species, 3)
        group_coeffs = self.MORTALITY_GROUPS[group]
        p0 = group_coeffs['P0']
        p1 = group_coeffs['P1']

        # Base annual mortality rate (logistic)
        ri = 1.0 / (1.0 + math.exp(p0 + p1 * tree.dbh))

        # LS halves the background rate (slower mortality than SN)
        ri *= 0.5

        # Adjust for cycle length
        rip = 1.0 - ((1.0 - ri) ** cycle_length)

        return rip

    def apply_mortality(
        self,
        trees: List['Tree'],
        cycle_length: int = 5,
        max_sdi: Optional[float] = None,
        random_seed: Optional[int] = None,
        pre_growth_qmd: float = 0.0,
        pre_growth_tpa: int = 0
    ) -> MortalityResult:
        """Apply LS mortality model with 4-group background and SDI density.

        Args:
            trees: List of trees in the stand
            cycle_length: Length of projection cycle in years
            max_sdi: Maximum SDI (uses species default if None)
            random_seed: Optional seed for reproducibility

        Returns:
            MortalityResult with survivors and mortality count
        """
        if len(trees) <= 1:
            return MortalityResult(survivors=list(trees), mortality_count=0, trees_died=[])

        if random_seed is not None:
            random.seed(random_seed)

        max_sdi = max_sdi or self.max_sdi or self._SDI_MAXIMUMS.get(
            self.default_species, self.DEFAULT_SDI_MAX
        )

        # Calculate stand SDI
        current_sdi = self._calculate_stand_sdi(trees)
        relative_sdi = current_sdi / max_sdi

        # Calculate basal area percentiles
        tree_data = self._calculate_tree_percentiles(trees)

        survivors = []
        trees_died = []

        # Calculate density mortality fraction if above threshold
        density_removal_fraction = 0.0
        if relative_sdi > self.LOWER_THRESHOLD:
            if relative_sdi > self.UPPER_THRESHOLD:
                target_sdi = self.UPPER_THRESHOLD * max_sdi
                excess_sdi = current_sdi - target_sdi
                sdi_to_remove = excess_sdi * 0.5
            else:
                target_sdi = current_sdi * (
                    1.0 - 0.05 * (relative_sdi - self.LOWER_THRESHOLD) /
                    (self.UPPER_THRESHOLD - self.LOWER_THRESHOLD)
                )
                sdi_to_remove = current_sdi - target_sdi
            density_removal_fraction = sdi_to_remove / current_sdi if current_sdi > 0 else 0

        for tree, pct in tree_data:
            # Background mortality (LS 4-group, halved)
            rip = self._get_background_rate(tree, cycle_length)

            # Density-dependent mortality component
            if density_removal_fraction > 0:
                # Mortality distribution by size (same equation as SN)
                mr = 0.84525 - (0.01074 * pct) + (0.0000002 * (pct ** 3))
                mr = max(0.01, min(1.0, mr))

                # VARADJ shade tolerance adjustment from varmrt.f:
                # EFFTR(I) = PEFF * (1.0 - VARADJ(JSPC)) * 0.1
                varadj = self._shade_tolerance.get(tree.species, 0.30)
                shade_modifier = (1.0 - varadj) * 0.1

                mort = mr * shade_modifier * density_removal_fraction * (cycle_length / 5.0)
            else:
                mort = 0.0

            # Use the higher of density or background mortality.
            # Background mortality always provides a floor — density-dependent
            # mortality adds on top when SDI is high enough that the density
            # rate exceeds background. This prevents a mortality drop when
            # RELSDI crosses the 0.55 threshold (density mort can be lower
            # than background for shade-tolerant species with low removal fractions).
            total_mort_prob = max(mort, rip)

            if random.random() > total_mort_prob:
                survivors.append(tree)
            else:
                trees_died.append(tree)

        return MortalityResult(
            survivors=survivors,
            mortality_count=len(trees_died),
            trees_died=trees_died
        )

    def _calculate_stand_sdi(self, trees: List['Tree']) -> float:
        """Calculate stand SDI using Reineke's equation."""
        if not trees:
            return 0.0
        tpa = len(trees)
        qmd_squared = sum(tree.dbh ** 2 for tree in trees) / tpa
        qmd = math.sqrt(qmd_squared)
        return tpa * (qmd / 10.0) ** 1.605

    def _calculate_tree_percentiles(
        self, trees: List['Tree']
    ) -> List[Tuple['Tree', float]]:
        """Calculate basal area percentile for each tree."""
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

    def calculate_background_mortality_rate(
        self, tree: 'Tree', cycle_length: int = 5
    ) -> float:
        """Calculate background mortality rate for a single tree."""
        return self._get_background_rate(tree, cycle_length)


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


# Module-level convenience functions
_default_model: Optional[MortalityModel] = None


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
        MortalityModel or LSMortalityModel instance
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

    mortality_cls = config.mortality_class
    if mortality_cls is MortalityModel:
        return mortality_cls(default_species=default_species, max_sdi=max_sdi)
    else:
        return mortality_cls(default_species=default_species, max_sdi=max_sdi)


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

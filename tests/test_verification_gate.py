"""FVS Model Validation Protocols — verification gate.

The USFS *FVS Model Validation Protocols* (2009, rev. 2010) define
**verification** as confirming the implemented model reproduces the basic
stand-dynamics signature of an even-aged, unmanaged stand. This module wires
that gate into the normal pytest suite: for each of the 11 implemented variants
it grows a bare-ground, unmanaged planted stand and asserts the four signatures.

The four signatures (asserted at the site-index base age):
  1. **Basal area increases**   — BA(base_age) > BA(initial)
  2. **TPA decreases**          — density-dependent + background mortality thins
                                  the stand, so TPA(base_age) < TPA(initial)
  3. **QMD increases**          — quadratic mean diameter grows as trees enlarge
  4. **Dominant height tracks SI** — at the site-index reference (base) age,
                                  top height equals site index *by definition*
                                  of the site curve, so
                                  |top_height(base_age) - SI| / SI <= SI_TOL.

Tolerances (stated and justified; **uniform across all variants** — not tuned
per variant to pass):

  * Signatures 1-3 are **directional**: strict inequality with a tiny epsilon
    (1e-6) to reject a flat/degenerate trajectory. No magnitude tolerance is
    needed — a correct unmanaged stand unambiguously grows BA/QMD and loses TPA.

  * Signature 4 uses ``SI_TOL = 0.15`` (±15% relative). A bare-ground stand
    grown from age-1 seedlings does not reproduce the single site-tree curve
    exactly, because (a) the establishment / small-tree phase introduces an age
    offset and slower early height, (b) ``top_height`` is the dominant-height of
    a *multi-tree* stand under mortality, not one undisturbed site tree, and
    (c) the small->large tree growth transition. ±15% reliably catches gross
    failures (height landing at, say, half or double SI) while tolerating these
    structural offsets. With correct per-variant base ages every variant lands
    within ±12.5% (OC, +12.5%, is closest to the bound); 15% is a principled
    round band, not fitted to any one variant.

**Base age is a factual model parameter, not a tolerance knob.** Each scenario
uses the base age of the site curve that variant/species actually uses: 50 yr
for most variants, **100 yr for WC Douglas-fir**, which uses the Curtis
base-age-100 curve (``pn_height_age._WC_EQUATION_MAP['DF'] = 'curtis_misc'``)
rather than PN's King base-age-50 curve.

Runs in a normal ``uv run pytest`` (no ``parity``/``slow`` marker, no native
FVS library required). Any variant that fails a signature is surfaced as a test
failure (or a clearly-marked ``xfail`` finding) — never masked by widening a
tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from pyfvs import Stand
from pyfvs.establishment import get_essubh_height
from pyfvs.tree import Tree


# Uniform tolerance for the "dominant height tracks site index" signature.
SI_TOL = 0.15
# Epsilon for the directional (increase/decrease) signatures.
DIR_EPS = 1e-6


@dataclass(frozen=True)
class VerificationScenario:
    """A bare-ground, unmanaged verification case for one variant.

    site_base_age is the base age of the site-index curve the (variant,
    species) pair actually uses — the age at which dominant height equals SI.
    """

    variant: str
    species: str
    site_index: float
    trees_per_acre: int
    site_base_age: int


# One representative scenario per implemented variant (default species, a
# typical site index, 500 TPA). These mirror the species/SI used by the parity
# suite where one exists; CA/WS/OP/EC use the variant's default species.
VERIFICATION_SCENARIOS = [
    VerificationScenario("SN", "LP", 70, 500, 50),
    VerificationScenario("LS", "RN", 60, 500, 50),
    VerificationScenario("CS", "WO", 60, 500, 50),
    VerificationScenario("NE", "RM", 60, 500, 50),
    VerificationScenario("PN", "DF", 100, 500, 50),
    VerificationScenario("WC", "DF", 100, 500, 100),  # Curtis base-age-100 DF curve
    VerificationScenario("EC", "DF", 80, 500, 50),
    VerificationScenario("CA", "PP", 90, 500, 50),
    VerificationScenario("WS", "PP", 90, 500, 50),
    VerificationScenario("OP", "DF", 100, 500, 50),
    VerificationScenario("OC", "DF", 80, 500, 50),
]

# Variants whose verification is a known finding rather than a hard gate go
# here, mapping variant -> reason. Empty today: with correct per-variant base
# ages all 11 pass at SI_TOL=0.15. Populate (never silence) if a regression or
# a newly-covered variant fails a signature.
KNOWN_VERIFICATION_FINDINGS: dict[str, str] = {}


@pytest.fixture
def si_tolerance() -> float:
    """The uniform relative tolerance for the height-tracks-SI signature."""
    return SI_TOL


@pytest.fixture
def build_bareground_stand():
    """Return a builder for a bare-ground, unmanaged, deterministic stand.

    Mirrors the parity helper's ``bare_ground=True`` path: age-1 seedlings at
    DBH 0.1 and the species/variant ESSUBH establishment height. Deterministic
    (``stochastic=False``) so the verification gate is reproducible and free of
    RNG-seed flakiness.
    """

    def _build(scenario: VerificationScenario) -> Stand:
        init_ht = get_essubh_height(scenario.species, scenario.variant)
        trees = [
            Tree(
                dbh=0.1,
                height=init_ht,
                age=1,
                species=scenario.species,
                variant=scenario.variant,
            )
            for _ in range(scenario.trees_per_acre)
        ]
        stand = Stand(
            trees,
            site_index=scenario.site_index,
            species=scenario.species,
            variant=scenario.variant,
            ecounit=None,
            stochastic=False,
            random_seed=42,
            bare_ground=True,
        )
        stand.age = 1
        return stand

    return _build


@pytest.mark.parametrize(
    "scenario",
    VERIFICATION_SCENARIOS,
    ids=[s.variant for s in VERIFICATION_SCENARIOS],
)
def test_variant_verification_signatures(
    scenario: VerificationScenario,
    build_bareground_stand,
    si_tolerance: float,
    request,
):
    """Assert the four FVS stand-dynamics signatures for one variant.

    Grows a bare-ground stand to the site-index base age and checks:
    BA increases, TPA decreases, QMD increases, and dominant height is within
    ``SI_TOL`` of the assigned site index.
    """
    if scenario.variant in KNOWN_VERIFICATION_FINDINGS:
        request.applymarker(
            pytest.mark.xfail(
                reason=KNOWN_VERIFICATION_FINDINGS[scenario.variant],
                strict=True,
            )
        )

    stand = build_bareground_stand(scenario)
    initial = stand.get_metrics()
    stand.grow(years=scenario.site_base_age - 1)  # from age 1 to base age
    final = stand.get_metrics()

    failures: list[str] = []

    # Signature 1: basal area increases.
    if not final["basal_area"] > initial["basal_area"] + DIR_EPS:
        failures.append(
            f"BA did not increase: {initial['basal_area']:.4f} -> "
            f"{final['basal_area']:.4f}"
        )

    # Signature 2: TPA decreases (mortality thins the stand).
    if not final["tpa"] < initial["tpa"] - DIR_EPS:
        failures.append(
            f"TPA did not decrease: {initial['tpa']:.4f} -> {final['tpa']:.4f}"
        )

    # Signature 3: QMD increases.
    if not final["qmd"] > initial["qmd"] + DIR_EPS:
        failures.append(
            f"QMD did not increase: {initial['qmd']:.4f} -> {final['qmd']:.4f}"
        )

    # Signature 4: dominant height tracks site index at the base age.
    th = final["top_height"]
    si = scenario.site_index
    rel_dev = abs(th - si) / si
    if rel_dev > si_tolerance:
        failures.append(
            f"top_height does not track SI at base age {scenario.site_base_age}: "
            f"top_height={th:.2f}, SI={si}, rel_dev={rel_dev:.2%} > "
            f"tol={si_tolerance:.0%}"
        )

    assert not failures, (
        f"[{scenario.variant}/{scenario.species} SI{scenario.site_index}] "
        f"verification signature(s) failed at base age {scenario.site_base_age}:\n  - "
        + "\n  - ".join(failures)
    )


def test_all_eleven_variants_are_covered():
    """Guard: the verification gate must cover all 11 implemented variants."""
    expected = {
        "SN", "LS", "CS", "NE", "PN", "WC", "EC", "CA", "WS", "OP", "OC",
    }
    covered = {s.variant for s in VERIFICATION_SCENARIOS}
    assert covered == expected, (
        f"verification gate must cover all 11 variants; "
        f"missing={expected - covered}, extra={covered - expected}"
    )

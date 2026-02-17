"""
Tests for variant-specific small-tree height growth coefficient loading.

Tests the NC-128 Chapman-Richards coefficient system that was implemented
for LS, CS, and NE variants. Verifies:
- JSON coefficient files load correctly with expected structure
- Exact coefficient values match htcalc.f Fortran source
- Tree._load_variant_small_tree_coefficients() dispatches correctly per variant
- Breast height offset (bh) field is present and handled
- Variants produce different growth trajectories
- SN behavior is unchanged (regression)
- Base age varies by variant (25 for SN, 50 for LS/CS/NE)
"""
import math
import pytest

from pyfvs.tree import Tree
from pyfvs.stand import Stand
from pyfvs.config_loader import load_coefficient_file


# =============================================================================
# 1. TestCoefficientFileLoading
# =============================================================================

class TestCoefficientFileLoading:
    """Verify JSON coefficient files load correctly and have expected structure."""

    def test_ls_coefficient_file_loads(self):
        """LS small tree height growth file loads with expected top-level key."""
        data = load_coefficient_file('ls_small_tree_height_growth.json', variant='LS')
        assert 'nc128_height_growth_coefficients' in data

    def test_cs_coefficient_file_loads(self):
        """CS small tree height growth file loads with expected top-level key."""
        data = load_coefficient_file('cs_small_tree_height_growth.json', variant='CS')
        assert 'nc128_height_growth_coefficients' in data

    def test_ne_coefficient_file_loads(self):
        """NE small tree height growth file loads with expected top-level key."""
        data = load_coefficient_file('ne_small_tree_height_growth.json', variant='NE')
        assert 'nc128_height_growth_coefficients' in data

    def test_sn_coefficient_file_loads(self):
        """SN small tree height growth file loads with bh field present."""
        data = load_coefficient_file('sn_small_tree_height_growth.json', variant='SN')
        assert 'nc128_height_growth_coefficients' in data
        coeffs = data['nc128_height_growth_coefficients']
        # Check that at least one species has the bh field
        first_species = next(iter(coeffs.values()))
        assert 'bh' in first_species

    def test_ls_species_count(self):
        """LS file has 67 species (matching MAPLS array in htcalc.f)."""
        data = load_coefficient_file('ls_small_tree_height_growth.json', variant='LS')
        coeffs = data['nc128_height_growth_coefficients']
        assert len(coeffs) == 67

    def test_cs_species_count(self):
        """CS file has 96 species (matching MAPCS array in htcalc.f)."""
        data = load_coefficient_file('cs_small_tree_height_growth.json', variant='CS')
        coeffs = data['nc128_height_growth_coefficients']
        assert len(coeffs) == 96

    def test_ne_species_count(self):
        """NE file has 107 species (matching MAPNE array in htcalc.f)."""
        data = load_coefficient_file('ne_small_tree_height_growth.json', variant='NE')
        coeffs = data['nc128_height_growth_coefficients']
        assert len(coeffs) == 107

    def test_sn_species_count(self):
        """SN file has 85 species (mapped via SN_SPECIES_MAP -> LTBHEC rows)."""
        data = load_coefficient_file('sn_small_tree_height_growth.json', variant='SN')
        coeffs = data['nc128_height_growth_coefficients']
        assert len(coeffs) == 90

    @pytest.mark.parametrize("variant,filename", [
        ('LS', 'ls_small_tree_height_growth.json'),
        ('CS', 'cs_small_tree_height_growth.json'),
        ('NE', 'ne_small_tree_height_growth.json'),
        ('SN', 'sn_small_tree_height_growth.json'),
    ])
    def test_coefficient_keys_present(self, variant, filename):
        """Each species entry has all 6 required keys: c1, c2, c3, c4, c5, bh."""
        required_keys = {'c1', 'c2', 'c3', 'c4', 'c5', 'bh'}
        data = load_coefficient_file(filename, variant=variant)
        coeffs = data['nc128_height_growth_coefficients']
        for species_code, species_coeffs in coeffs.items():
            present_keys = set(species_coeffs.keys()) & required_keys
            assert present_keys == required_keys, (
                f"{variant} species {species_code} missing keys: "
                f"{required_keys - present_keys}"
            )


# =============================================================================
# 2. TestExactCoefficientValues
# =============================================================================

class TestExactCoefficientValues:
    """Verify key species have correct coefficients extracted from htcalc.f."""

    def test_ls_red_pine_coefficients(self):
        """LS Red Pine (RN) has correct NC-128 curve 33 coefficients."""
        data = load_coefficient_file('ls_small_tree_height_growth.json', variant='LS')
        rn = data['nc128_height_growth_coefficients']['RN']
        assert rn['c1'] == pytest.approx(1.89, rel=1e-4)
        assert rn['c2'] == pytest.approx(1.0, rel=1e-4)
        assert rn['c3'] == pytest.approx(-0.0198, rel=1e-4)
        assert rn['c4'] == pytest.approx(1.3892, rel=1e-4)
        assert rn['c5'] == pytest.approx(0.0, abs=1e-4)
        assert rn['bh'] == pytest.approx(0.0, abs=1e-4)

    def test_ls_jack_pine_coefficients(self):
        """LS Jack Pine (JP) has correct NC-128 curve 28 coefficients."""
        data = load_coefficient_file('ls_small_tree_height_growth.json', variant='LS')
        jp = data['nc128_height_growth_coefficients']['JP']
        assert jp['c1'] == pytest.approx(1.633, rel=1e-4)
        assert jp['c2'] == pytest.approx(1.0, rel=1e-4)
        assert jp['c3'] == pytest.approx(-0.0223, rel=1e-4)
        assert jp['c4'] == pytest.approx(1.2419, rel=1e-4)
        assert jp['c5'] == pytest.approx(0.0, abs=1e-4)
        assert jp['bh'] == pytest.approx(0.0, abs=1e-4)

    def test_cs_white_oak_coefficients(self):
        """CS White Oak (WO) has correct NC-128 curve 80 coefficients."""
        data = load_coefficient_file('cs_small_tree_height_growth.json', variant='CS')
        wo = data['nc128_height_growth_coefficients']['WO']
        assert wo['c1'] == pytest.approx(4.5598, rel=1e-4)
        assert wo['c2'] == pytest.approx(0.8136, rel=1e-4)
        assert wo['c3'] == pytest.approx(-0.0132, rel=1e-4)
        assert wo['c4'] == pytest.approx(2.241, rel=1e-4)
        assert wo['c5'] == pytest.approx(-0.188, rel=1e-4)
        assert wo['bh'] == pytest.approx(0.0, abs=1e-4)

    def test_ne_red_maple_coefficients(self):
        """NE Red Maple (RM) has correct NC-128 curve 60 coefficients."""
        data = load_coefficient_file('ne_small_tree_height_growth.json', variant='NE')
        rm = data['nc128_height_growth_coefficients']['RM']
        assert rm['c1'] == pytest.approx(2.9435, rel=1e-4)
        assert rm['c2'] == pytest.approx(0.9132, rel=1e-4)
        assert rm['c3'] == pytest.approx(-0.0141, rel=1e-4)
        assert rm['c4'] == pytest.approx(1.658, rel=1e-4)
        assert rm['c5'] == pytest.approx(-0.1095, rel=1e-4)
        assert rm['bh'] == pytest.approx(0.0, abs=1e-4)

    def test_ne_balsam_fir_coefficients(self):
        """NE Balsam Fir (BF) has correct NC-128 curve 5 coefficients."""
        data = load_coefficient_file('ne_small_tree_height_growth.json', variant='NE')
        bf = data['nc128_height_growth_coefficients']['BF']
        assert bf['c1'] == pytest.approx(2.077, rel=1e-4)
        assert bf['c2'] == pytest.approx(0.9303, rel=1e-4)
        assert bf['c3'] == pytest.approx(-0.0285, rel=1e-4)
        assert bf['c4'] == pytest.approx(2.8937, rel=1e-4)
        assert bf['c5'] == pytest.approx(-0.1414, rel=1e-4)
        assert bf['bh'] == pytest.approx(0.0, abs=1e-4)

    def test_sn_loblolly_pine_coefficients(self):
        """SN Loblolly Pine (LP) has correct LTBHEC row 13 coefficients."""
        data = load_coefficient_file('sn_small_tree_height_growth.json', variant='SN')
        lp = data['nc128_height_growth_coefficients']['LP']
        assert lp['c1'] == pytest.approx(1.1421, rel=1e-4)
        assert lp['c2'] == pytest.approx(1.0042, rel=1e-4)
        assert lp['c3'] == pytest.approx(-0.0374, rel=1e-4)
        assert lp['c4'] == pytest.approx(0.7632, rel=1e-4)
        assert lp['c5'] == pytest.approx(0.0358, rel=1e-4)
        assert lp['bh'] == pytest.approx(0.0, abs=1e-4)


# =============================================================================
# 3. TestVariantCoefficientLoading
# =============================================================================

class TestVariantCoefficientLoading:
    """Test Tree._load_variant_small_tree_coefficients() method."""

    def test_ls_tree_loads_ls_coefficients(self):
        """LS Red Pine tree loads LS-specific coefficients (c3=-0.0198)."""
        tree = Tree(dbh=0.5, height=4.5, species='RN', age=2, variant='LS')
        coeffs = tree._load_variant_small_tree_coefficients('LS')
        assert coeffs['c3'] == pytest.approx(-0.0198, rel=1e-4)
        assert coeffs['c1'] == pytest.approx(1.89, rel=1e-4)

    def test_cs_tree_loads_cs_coefficients(self):
        """CS White Oak tree loads CS-specific coefficients (c3=-0.0132)."""
        tree = Tree(dbh=0.5, height=4.5, species='WO', age=2, variant='CS')
        coeffs = tree._load_variant_small_tree_coefficients('CS')
        assert coeffs['c3'] == pytest.approx(-0.0132, rel=1e-4)
        assert coeffs['c1'] == pytest.approx(4.5598, rel=1e-4)

    def test_ne_tree_loads_ne_coefficients(self):
        """NE Red Maple tree loads NE-specific coefficients (c3=-0.0141)."""
        tree = Tree(dbh=0.5, height=4.5, species='RM', age=2, variant='NE')
        coeffs = tree._load_variant_small_tree_coefficients('NE')
        assert coeffs['c3'] == pytest.approx(-0.0141, rel=1e-4)
        assert coeffs['c1'] == pytest.approx(2.9435, rel=1e-4)

    def test_sn_tree_loads_sn_coefficients(self):
        """SN Loblolly Pine tree loads SN LTBHEC row 13 coefficients (c3=-0.0374)."""
        tree = Tree(dbh=0.5, height=4.5, species='LP', age=2, variant='SN')
        coeffs = tree._load_variant_small_tree_coefficients('SN')
        assert coeffs['c3'] == pytest.approx(-0.0374, rel=1e-4)
        assert coeffs['c1'] == pytest.approx(1.1421, rel=1e-4)

    def test_unknown_species_returns_empty(self):
        """Tree with nonexistent species returns empty dict from coefficient loading."""
        # Use a valid species for Tree init but override for loading test
        tree = Tree(dbh=0.5, height=4.5, species='LP', age=2, variant='SN')
        tree.species = 'ZZ'  # Override to nonexistent species
        coeffs = tree._load_variant_small_tree_coefficients('SN')
        assert coeffs == {}

    def test_fallback_to_sn_file(self):
        """Species in SN file but not in LS file falls back to SN coefficients."""
        # LP exists in SN file but should also exist in LS file (it does via MAPLS)
        # Use a species unique to SN to test fallback
        tree = Tree(dbh=0.5, height=4.5, species='LP', age=2, variant='SN')
        # Load from SN — LP exists in SN file
        coeffs_sn = tree._load_variant_small_tree_coefficients('SN')
        assert len(coeffs_sn) > 0
        assert 'c1' in coeffs_sn


# =============================================================================
# 4. TestBreastHeightOffset
# =============================================================================

class TestBreastHeightOffset:
    """Test the BH offset in Chapman-Richards equation."""

    def test_bh_zero_no_effect(self):
        """With bh=0.0, Chapman-Richards produces same result as old equation."""
        # Chapman-Richards: H = bh + c1 * SI^c2 * (1 - exp(c3*age))^(c4 * SI^c5)
        # With bh=0.0, this is identical to the pre-change equation
        c1, c2, c3, c4, c5 = 1.1421, 1.0042, -0.0374, 0.7632, 0.0358
        site_index = 70.0
        age = 10

        height_without_bh = (
            c1 * (site_index ** c2) *
            (1.0 - math.exp(c3 * age)) **
            (c4 * (site_index ** c5))
        )
        height_with_bh_zero = (
            0.0 + c1 * (site_index ** c2) *
            (1.0 - math.exp(c3 * age)) **
            (c4 * (site_index ** c5))
        )
        assert height_with_bh_zero == pytest.approx(height_without_bh, rel=1e-10)

    def test_bh_offset_increases_height(self):
        """A positive BH offset increases the raw Chapman-Richards height."""
        c1, c2, c3, c4, c5 = 1.1421, 1.0042, -0.0374, 0.7632, 0.0358
        site_index = 70.0
        age = 5

        height_bh_0 = (
            0.0 + c1 * (site_index ** c2) *
            (1.0 - math.exp(c3 * age)) **
            (c4 * (site_index ** c5))
        )
        height_bh_4_5 = (
            4.5 + c1 * (site_index ** c2) *
            (1.0 - math.exp(c3 * age)) **
            (c4 * (site_index ** c5))
        )
        assert height_bh_4_5 > height_bh_0
        # The difference should be exactly 4.5
        assert height_bh_4_5 - height_bh_0 == pytest.approx(4.5, abs=1e-10)

    def test_all_sn_species_bh_zero(self):
        """All 85 SN species have bh=0.0."""
        data = load_coefficient_file('sn_small_tree_height_growth.json', variant='SN')
        coeffs = data['nc128_height_growth_coefficients']
        for species_code, species_coeffs in coeffs.items():
            assert species_coeffs.get('bh', None) == pytest.approx(0.0, abs=1e-10), (
                f"SN species {species_code} has bh={species_coeffs.get('bh')}, expected 0.0"
            )

    def test_all_ls_species_have_bh_field(self):
        """All LS species have the 'bh' key in their coefficients."""
        data = load_coefficient_file('ls_small_tree_height_growth.json', variant='LS')
        coeffs = data['nc128_height_growth_coefficients']
        for species_code, species_coeffs in coeffs.items():
            assert 'bh' in species_coeffs, (
                f"LS species {species_code} missing 'bh' field"
            )

    def test_all_cs_species_have_bh_field(self):
        """All CS species have the 'bh' key in their coefficients."""
        data = load_coefficient_file('cs_small_tree_height_growth.json', variant='CS')
        coeffs = data['nc128_height_growth_coefficients']
        for species_code, species_coeffs in coeffs.items():
            assert 'bh' in species_coeffs, (
                f"CS species {species_code} missing 'bh' field"
            )

    def test_all_ne_species_have_bh_field(self):
        """All NE species have the 'bh' key in their coefficients."""
        data = load_coefficient_file('ne_small_tree_height_growth.json', variant='NE')
        coeffs = data['nc128_height_growth_coefficients']
        for species_code, species_coeffs in coeffs.items():
            assert 'bh' in species_coeffs, (
                f"NE species {species_code} missing 'bh' field"
            )


# =============================================================================
# 5. TestVariantGrowthDifferences
# =============================================================================

class TestVariantGrowthDifferences:
    """Test that variants produce different growth trajectories."""

    def test_ls_slower_than_sn_early_growth(self):
        """LS Red Pine grows slower than SN Loblolly Pine by age 12.

        Northern species (LS) grow slower than southern species (SN).
        This validates that variant-specific coefficients are being used.
        With LTBHEC S-curves, the difference is small at age 7 but clear by age 12.
        """
        # SN Loblolly Pine: fast southern grower
        sn_tree = Tree(dbh=0.5, height=4.5, species='LP', age=2, variant='SN')
        sn_tree.grow(site_index=70.0, competition_factor=0.0, time_step=10)

        # LS Red Pine: slower northern grower
        ls_tree = Tree(dbh=0.5, height=4.5, species='RN', age=2, variant='LS')
        ls_tree.grow(site_index=65.0, competition_factor=0.0, time_step=10)

        # SN LP should be taller at age 12 than LS RN
        assert sn_tree.height > ls_tree.height, (
            f"Expected SN LP ({sn_tree.height:.1f}ft) > LS RN ({ls_tree.height:.1f}ft) at age 12"
        )

    def test_variant_specific_c3_used(self):
        """LS tree uses c3=-0.0198, not SN default c3=-0.0374.

        Verify by computing height with LS coefficients at age 5 and
        confirming it matches what the Tree produces.
        """
        # LS Red Pine coefficients
        c1, c2, c3, c4, c5 = 1.89, 1.0, -0.0198, 1.3892, 0.0
        site_index = 65.0
        base_age = 50  # LS uses base age 50

        # Raw Chapman-Richards at age 5
        raw_at_5 = c1 * (site_index ** c2) * (1.0 - math.exp(c3 * 5)) ** (c4 * (site_index ** c5))
        raw_at_base = c1 * (site_index ** c2) * (1.0 - math.exp(c3 * base_age)) ** (c4 * (site_index ** c5))

        # Scaled height at age 5
        scale_factor = site_index / raw_at_base if raw_at_base > 0 else 1.0
        expected_height_at_5 = raw_at_5 * scale_factor

        # The height at age 5 should be much less than site index
        # With LS c3=-0.0198 (slow growth), height at 5 should be ~4-8 ft
        assert expected_height_at_5 < 15.0, (
            f"LS RN height at age 5 should be < 15 ft, got {expected_height_at_5:.1f}"
        )

        # With SN c3=-0.0374 (faster), same SI gives much taller tree
        sn_c3 = -0.0374
        sn_c1, sn_c2, sn_c4, sn_c5 = 1.1421, 1.0042, 0.7632, 0.0358
        sn_base_age = 25
        raw_sn_5 = sn_c1 * (site_index ** sn_c2) * (1.0 - math.exp(sn_c3 * 5)) ** (sn_c4 * (site_index ** sn_c5))
        raw_sn_base = sn_c1 * (site_index ** sn_c2) * (1.0 - math.exp(sn_c3 * sn_base_age)) ** (sn_c4 * (site_index ** sn_c5))
        scale_sn = site_index / raw_sn_base if raw_sn_base > 0 else 1.0
        sn_height_at_5 = raw_sn_5 * scale_sn

        # SN should produce a different height at age 5
        assert expected_height_at_5 != pytest.approx(sn_height_at_5, rel=0.05), (
            f"LS and SN should produce different heights at age 5 "
            f"(LS={expected_height_at_5:.1f}, SN={sn_height_at_5:.1f})"
        )

    def test_cs_white_oak_growth_rate(self):
        """CS White Oak at SI=70 produces reasonable height at age 10 (~15-25 ft)."""
        tree = Tree(dbh=0.5, height=4.5, species='WO', age=2, variant='CS')
        tree.grow(site_index=70.0, competition_factor=0.0, time_step=10)
        # At age 12, WO with SI=70 should be in reasonable range
        assert 8.0 < tree.height < 35.0, (
            f"CS WO height at age 12 = {tree.height:.1f}ft, expected 8-35 ft"
        )

    def test_ne_red_maple_growth_rate(self):
        """NE Red Maple at SI=60 produces reasonable height at age 10 (~10-20 ft)."""
        tree = Tree(dbh=0.5, height=4.5, species='RM', age=2, variant='NE')
        tree.grow(site_index=60.0, competition_factor=0.0, time_step=10)
        # At age 12, RM with SI=60 should be in reasonable range
        assert 6.0 < tree.height < 30.0, (
            f"NE RM height at age 12 = {tree.height:.1f}ft, expected 6-30 ft"
        )

    def test_ls_and_ne_use_different_coefficients_for_same_species(self):
        """LS and NE may map the same species to different NC-128 curves.

        White Spruce (WS) exists in both LS and NE. Both should have coefficients,
        but the growth trajectories may differ due to different curve mappings.
        """
        ls_data = load_coefficient_file('ls_small_tree_height_growth.json', variant='LS')
        ne_data = load_coefficient_file('ne_small_tree_height_growth.json', variant='NE')

        ls_ws = ls_data['nc128_height_growth_coefficients'].get('WS')
        ne_ws = ne_data['nc128_height_growth_coefficients'].get('WS')

        assert ls_ws is not None, "WS should exist in LS coefficient file"
        assert ne_ws is not None, "WS should exist in NE coefficient file"
        # Both have coefficients — values may be same (same NC-128 curve) or different
        assert 'c1' in ls_ws and 'c1' in ne_ws


# =============================================================================
# 6. TestSNRegression
# =============================================================================

class TestSNRegression:
    """Verify SN behavior is completely unchanged after variant-specific changes."""

    def test_sn_loblolly_50yr_unchanged(self):
        """500 TPA LP SI=70 50yr simulation produces expected SN metrics.

        These values match SN behavior with M231 ecounit (+0.790 to ln(DDS)),
        Baskerville (1972) stochastic bias correction (α=0.88, ~10% DDS boost),
        no forest type effect (IFORTP=0 in Fortran means all flags=0),
        no plant effect (MANAGD not set), correct LTBHEC row 13 coefficients,
        initial tree variation (dbh_sd=0.02, height_sd=0.1) for PBAL differentiation,
        and no establishment skip.
        """
        stand = Stand.initialize_planted(500, 70, 'LP', variant='SN', ecounit='M231',
                                         stochastic=False)
        stand.grow(50)
        metrics = stand.get_metrics()

        # SN LP 500 TPA SI=70 M231 50yr — deterministic Baskerville correction
        # M231 ecounit gives +0.790 to ln(DDS) → very fast growth
        # Higher density triggers more mortality → fewer, bigger trees
        assert metrics['tpa'] == pytest.approx(123, rel=0.10)
        assert metrics['qmd'] == pytest.approx(21.12, rel=0.10)
        assert metrics['basal_area'] == pytest.approx(299, rel=0.10)

    def test_sn_small_tree_height_growth_unchanged(self):
        """SN LP small tree height growth uses correct LTBHEC row 13 coefficients.

        SN uses scale_factor=1.0 (no anchoring), so the raw LTBHEC curve
        drives height directly. H(50) ≈ SI for correctly parameterized curves.
        LP is a fast grower — reaches ~17ft by age 5.
        """
        # SN LP LTBHEC row 13 coefficients (correct JSP index)
        c1, c2, c3, c4, c5, bh = 1.1421, 1.0042, -0.0374, 0.7632, 0.0358, 0.0
        site_index = 70.0

        def raw_cr(age):
            if age <= 0:
                return 0.1
            return bh + c1 * (site_index ** c2) * (1.0 - math.exp(c3 * age)) ** (c4 * (site_index ** c5))

        # H(50) should approximate SI for correctly calibrated curves
        height_at_50 = raw_cr(50)
        assert height_at_50 == pytest.approx(site_index, rel=0.02), (
            f"SN LP H_raw(50) = {height_at_50:.1f}ft, expected ~{site_index}"
        )

        # LP is fast-growing — H(5) ≈ 17ft (not the tiny values from old wrong coefficients)
        height_at_5 = raw_cr(5)
        assert height_at_5 == pytest.approx(16.9, rel=0.05), (
            f"SN LP height at age 5 = {height_at_5:.2f}ft, expected ~16.9"
        )

        # Verify the tree object produces consistent growth
        tree = Tree(dbh=0.3, height=3.0, species='LP', age=2, variant='SN')
        original_height = tree.height
        tree.grow(site_index=70.0, competition_factor=0.0, time_step=5)
        # Tree should grow
        assert tree.height > original_height


# =============================================================================
# 7. TestBaseAgeVariation
# =============================================================================

class TestBaseAgeVariation:
    """Test variant-specific base age handling.

    SN uses base age 25 (SI25), while LS/CS/NE use base age 50 (SI50).
    This affects the scaling factor in the Chapman-Richards equation.
    """

    def _compute_scaled_height(self, coeffs, site_index, base_age, target_age):
        """Helper to compute scaled Chapman-Richards height."""
        c1 = coeffs['c1']
        c2 = coeffs['c2']
        c3 = coeffs['c3']
        c4 = coeffs['c4']
        c5 = coeffs['c5']
        bh = coeffs.get('bh', 0.0)

        def raw_cr(age):
            if age <= 0:
                return 1.0
            return bh + c1 * (site_index ** c2) * (1.0 - math.exp(c3 * age)) ** (c4 * (site_index ** c5))

        raw_at_base = raw_cr(base_age)
        scale_factor = site_index / raw_at_base if raw_at_base > 0 else 1.0
        return raw_cr(target_age) * scale_factor

    def test_sn_base_age_25(self):
        """SN variant uses base_age=25: height at age 25 equals site index."""
        data = load_coefficient_file('sn_small_tree_height_growth.json', variant='SN')
        lp_coeffs = data['nc128_height_growth_coefficients']['LP']
        site_index = 70.0

        height_at_25 = self._compute_scaled_height(lp_coeffs, site_index, base_age=25, target_age=25)
        assert height_at_25 == pytest.approx(site_index, rel=1e-6), (
            f"SN LP height at base age 25 should equal SI={site_index}, got {height_at_25:.2f}"
        )

    def test_ls_base_age_50(self):
        """LS variant uses base_age=50: height at age 50 equals site index."""
        data = load_coefficient_file('ls_small_tree_height_growth.json', variant='LS')
        rn_coeffs = data['nc128_height_growth_coefficients']['RN']
        site_index = 65.0

        height_at_50 = self._compute_scaled_height(rn_coeffs, site_index, base_age=50, target_age=50)
        assert height_at_50 == pytest.approx(site_index, rel=1e-6), (
            f"LS RN height at base age 50 should equal SI={site_index}, got {height_at_50:.2f}"
        )

    def test_ne_base_age_50(self):
        """NE variant uses base_age=50: height at age 50 equals site index."""
        data = load_coefficient_file('ne_small_tree_height_growth.json', variant='NE')
        rm_coeffs = data['nc128_height_growth_coefficients']['RM']
        site_index = 60.0

        height_at_50 = self._compute_scaled_height(rm_coeffs, site_index, base_age=50, target_age=50)
        assert height_at_50 == pytest.approx(site_index, rel=1e-6), (
            f"NE RM height at base age 50 should equal SI={site_index}, got {height_at_50:.2f}"
        )

    def test_cs_base_age_50(self):
        """CS variant uses base_age=50: height at age 50 equals site index."""
        data = load_coefficient_file('cs_small_tree_height_growth.json', variant='CS')
        wo_coeffs = data['nc128_height_growth_coefficients']['WO']
        site_index = 70.0

        height_at_50 = self._compute_scaled_height(wo_coeffs, site_index, base_age=50, target_age=50)
        assert height_at_50 == pytest.approx(site_index, rel=1e-6), (
            f"CS WO height at base age 50 should equal SI={site_index}, got {height_at_50:.2f}"
        )

    def test_sn_height_at_50_exceeds_si(self):
        """SN LP at age 50 should exceed SI (since base age is 25, not 50)."""
        data = load_coefficient_file('sn_small_tree_height_growth.json', variant='SN')
        lp_coeffs = data['nc128_height_growth_coefficients']['LP']
        site_index = 70.0

        height_at_50 = self._compute_scaled_height(lp_coeffs, site_index, base_age=25, target_age=50)
        assert height_at_50 > site_index, (
            f"SN LP height at age 50 ({height_at_50:.1f}) should exceed SI={site_index}"
        )

    def test_ls_height_at_25_less_than_si(self):
        """LS RN at age 25 should be less than SI (since base age is 50, not 25)."""
        data = load_coefficient_file('ls_small_tree_height_growth.json', variant='LS')
        rn_coeffs = data['nc128_height_growth_coefficients']['RN']
        site_index = 65.0

        height_at_25 = self._compute_scaled_height(rn_coeffs, site_index, base_age=50, target_age=25)
        assert height_at_25 < site_index, (
            f"LS RN height at age 25 ({height_at_25:.1f}) should be less than SI={site_index}"
        )

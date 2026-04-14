"""R8CF coefficient-port unit tests for ClarkTaperModel.

Verifies pyfvs's load path against the ground-truth values in Fortran's
``volume/NVEL/r8dib.f`` (coefficients) and ``r8clkdib.f:34-97`` (alias
remap + group-9 fallback). Each assertion cites a specific Fortran line.
"""
from __future__ import annotations

import pytest

from pyfvs.taper import ClarkTaperModel


# Shorthand for pytest.approx at reasonable tolerance for coefficient
# floats (r8dib.f stores to 5 decimals).
def _approx(x: float) -> pytest.approx:
    return pytest.approx(x, abs=1e-4)


class TestR8CFGroup4Lookup:
    """Species present in group 4 (native FVSsn default)."""

    def test_lp_group_4(self):
        """LP (FIA 131) group 4 — r8dib.f:238 (4,131,100,-0.12527,0.87509,...)."""
        model = ClarkTaperModel('LP', 'SN', forest_group='4')
        coef = model._coefficients
        assert coef['fia_code'] == 131
        assert coef['a4'] == _approx(-0.12527)
        assert coef['b4'] == _approx(0.87509)
        assert coef['a17'] == _approx(0.81431)
        assert coef['b17'] == _approx(-0.64282)

    def test_sa_group_4(self):
        """SA (FIA 111) group 4 — r8dib.f:228-230."""
        model = ClarkTaperModel('SA', 'SN', forest_group='4')
        coef = model._coefficients
        assert coef['fia_code'] == 111
        assert coef['a4'] == _approx(-0.55073)
        assert coef['b4'] == _approx(0.91887)

    def test_sp_group_4(self):
        """SP (FIA 110) group 4 — r8dib.f:228."""
        model = ClarkTaperModel('SP', 'SN', forest_group='4')
        coef = model._coefficients
        assert coef['fia_code'] == 110
        assert coef['a4'] == _approx(-0.40885)
        assert coef['b4'] == _approx(0.92610)

    def test_vp_group_4(self):
        """VP (FIA 132) group 4 — r8dib.f:234."""
        model = ClarkTaperModel('VP', 'SN', forest_group='4')
        coef = model._coefficients
        assert coef['fia_code'] == 132
        assert coef['a4'] == _approx(0.01138)
        assert coef['b4'] == _approx(0.92961)


class TestR8CFGroup9Fallback:
    """Species absent from group 4 fall back to group 9 (r8clkdib.f:82-97)."""

    def test_ll_falls_back_to_group_9(self):
        """LL (FIA 121) absent from group 4 — uses group 9 r8dib.f:465."""
        model = ClarkTaperModel('LL', 'SN', forest_group='4')
        coef = model._coefficients
        assert coef['fia_code'] == 121
        # Group 9 values, not group 1 which also has LL
        assert coef['a4'] == _approx(-0.45903)
        assert coef['b4'] == _approx(0.92746)
        assert coef['a17'] == _approx(0.85759)
        assert coef['b17'] == _approx(-1.05479)

    def test_hm_falls_back_to_group_9(self):
        """HM (FIA 261) absent from group 4 — uses group 9 r8dib.f:491."""
        model = ClarkTaperModel('HM', 'SN', forest_group='4')
        coef = model._coefficients
        assert coef['fia_code'] == 261
        assert coef['a4'] == _approx(-0.04931)
        assert coef['b4'] == _approx(0.92272)

    def test_rm_falls_back_to_group_9(self):
        """RM (FIA 316) absent from group 4 — uses group 9."""
        model = ClarkTaperModel('RM', 'SN', forest_group='4')
        coef = model._coefficients
        assert coef['fia_code'] == 316
        assert coef['a4'] == _approx(-0.09800)
        assert coef['b4'] == _approx(0.94646)


class TestR8CFForestGroupParam:
    """Explicit forest_group parameter selects the correct row."""

    def test_ll_group_1_vs_group_9(self):
        """LL values differ between group 1 (r8dib.f:15) and group 9 (:465)."""
        g1 = ClarkTaperModel('LL', 'SN', forest_group='1')._coefficients
        g9 = ClarkTaperModel('LL', 'SN', forest_group='9')._coefficients
        # Group 1 LL: r8dib.f:15 — 1,121,100,-0.50845,0.93246,...
        assert g1['a4'] == _approx(-0.50845)
        assert g1['b4'] == _approx(0.93246)
        # Group 9 LL: r8dib.f:465 — 9,121,100,-0.45903,0.92746,...
        assert g9['a4'] == _approx(-0.45903)
        assert g9['b4'] == _approx(0.92746)
        # They should be different
        assert g1['a4'] != g9['a4']

    def test_default_forest_group_is_4(self):
        """Omitted forest_group defaults to '4' — matches native FVSsn FORKOD."""
        default = ClarkTaperModel('LP', 'SN')._coefficients
        explicit = ClarkTaperModel('LP', 'SN', forest_group='4')._coefficients
        assert default['a4'] == explicit['a4']
        assert default['b4'] == explicit['b4']


class TestInvariantTotalCoefficients:
    """r/c/e/p/a/b are forest-invariant — same across groups."""

    def test_r_identical_across_groups(self):
        """Clark TOTAL array R is species-only, not group-specific."""
        g1 = ClarkTaperModel('LP', 'SN', forest_group='1')._coefficients
        g4 = ClarkTaperModel('LP', 'SN', forest_group='4')._coefficients
        g9 = ClarkTaperModel('LP', 'SN', forest_group='9')._coefficients
        # R from TOTAL array (r8clkcoef.inc) — same for all groups
        assert g1['r'] == g4['r'] == g9['r']
        # A17/B17 should differ (forest-group-specific)
        # (only assert they're numeric here; specific-value asserts above)
        assert isinstance(g1['a17'], float)
        assert isinstance(g4['a17'], float)

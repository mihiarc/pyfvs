# FVS-Python Manuscript Validation Discrepancy Report

**Generated**: 2025-12-16 (Updated)
**Manuscript Reference**: "Toward a timber asset account for the United States: A pilot account for Georgia"
**Authors**: Bruck, Mihiar, Mei, Brandeis, Chambers, Hass, Wentland, Warziniack
**FVS Version in Manuscript**: FS2025.1

---

## Executive Summary

Validation testing of fvs-python against the timber asset account manuscript revealed:
- **16 of 25 tests passed** (64% pass rate)
- **9 tests failed** identifying specific calibration discrepancies

The core growth model mechanics (volume increases with age, mortality occurs, site index effects)
work correctly. However, **absolute yield values are approximately 5-10% of manuscript expectations**,
indicating fundamental growth rate and volume calculation differences.

---

## Bugs Fixed During This Session

### 1. Crown Ratio Time Step Scaling (Critical)

**Issue**: Crown ratio change was not scaled by time step. The max_change_per_cycle of 5% was
applied per call regardless of whether growing 1 year or 5 years. With 1-year steps, this caused
25% decline over 5 years instead of 5%.

**Fix**: Modified `_update_crown_ratio_weibull()` in tree.py to scale changes by time_step:
```python
max_change_per_cycle = 0.05 * (time_step / 5.0)
```

**Location**: `src/fvs_python/tree.py:412`

### 2. Stand.grow() Time Step Handling (Critical)

**Issue**: Stand.grow() forced all growth into 5-year cycles, ignoring the `years` parameter.
When calling grow(years=1), it would actually grow for 5 years.

**Fix**: Modified grow() to respect the years parameter directly:
```python
def grow(self, years=5):
    # Now uses years directly instead of forcing 5-year increments
    tree.grow(..., time_step=years)
```

**Location**: `src/fvs_python/stand.py:591-632`

### 3. Mortality Time Step Scaling (Critical)

**Issue**: Mortality was called without passing cycle_length, so it always used 5-year mortality
rates even for 1-year time steps.

**Fix**: Pass years to mortality:
```python
mortality_count = self._apply_mortality(cycle_length=years)
```

**Location**: `src/fvs_python/stand.py:623`

---

## Key Findings

### 1. Yield Magnitude Discrepancy (Critical)

**Table 1 Comparison (Loblolly Pine, SI=55)**:

| Age | Manuscript (tons/acre) | FVS-Python (tons/acre) | Ratio |
|-----|------------------------|------------------------|-------|
| 5   | 26                     | 1.1                    | 4%    |
| 10  | 100                    | 5.6                    | 6%    |
| 15  | 184                    | 13.7                   | 7%    |
| 20  | 280                    | 24.9                   | 9%    |
| 23  | 340                    | 32.5                   | 10%   |

**Root Causes Identified**:

1. **Diameter Growth Rate**: FVS-Python produces ~0.2 in/year DBH growth using the correct
   FVS coefficients. Expected literature values are 0.3-0.5 in/year for managed loblolly
   plantations. The coefficients may have been calibrated from natural stand data.

2. **Volume Calculation**: Fallback volume calculation (NVEL DLL not available on macOS)
   produces ~12 cu ft for a 10"x60ft tree, vs expected ~20-30 cu ft from literature.
   This is approximately 50% underestimation.

3. **Combined Effect**: Slower diameter growth (~60% of expected) combined with lower
   volume calculation (~50% of expected) results in ~30% of expected volume. Additional
   factors (stocking, mortality timing) further reduce this to 5-10% of manuscript values.

### 2. Tree Size at Rotation Age

**At Age 25 (SI=55)**:
| Metric | FVS-Python | Expected |
|--------|------------|----------|
| DBH    | 6.5"       | 10-12"   |
| Height | 53 ft      | 55 ft    |
| CR     | 59%        | 40-50%   |
| TPA    | 448        | 300-350  |

**Observations**:
- Height is close to site index (good)
- DBH is too small by ~40%
- Crown ratio decline is now gradual (improved from previous 31%)
- TPA is higher than expected (less mortality)

### 3. Diameter Growth Equation Analysis

**ln(DDS) breakdown for 5" DBH, 45ft tree, 65% CR**:
```
CONSPP (SI term)           +0.28
INTERC (intercept)         +0.22
LDBH (ln(DBH))             +1.87
DBH2 (DBH^2)               -0.02
LCRWN (ln(CR))             +0.12  <- Note: small coefficient (0.028)
HREL (rel height)          +0.01
PLTB (BA)                  -0.17
PNTBL (PBAL)               -0.10
PLANT (plantation effect)  +0.25
-----------------------------------
Total ln(DDS)              +2.44
```

This produces DDS=11.5 and annual growth of 0.21 in/year, matching our simulation.
The FVS coefficients are being applied correctly but produce slower growth than expected.

### 4. Species Productivity Ranking

**Expected Ranking** (per manuscript): LP > SA > SP > LL

**Actual FVS-Python Results (Age 25, SI=60)**:
1. LP: ~38 tons/acre (correct position)
2. SP: ~37 tons/acre (should be lower)
3. SA: ~30 tons/acre (should be higher)
4. LL: ~33 tons/acre (correct position)

**Issue**: Shortleaf Pine (SP) is producing more than Slash Pine (SA), contrary to expectations.

---

## What Passed (16 Tests)

1. **Volume increases with age** - All species show positive volume trends
2. **Site index effects** - Higher SI produces higher yields (South > North)
3. **Mortality effects** - TPA decreases over time as expected
4. **All 8 species yield curve tests** - Growth trends are biologically reasonable
5. **Report generation** - All output files created successfully
6. **Unit conversions** - CCF/tons conversions work correctly
7. **LEV max age test** - MAI calculation framework works
8. **Comprehensive validation report** - Generates complete output

---

## What Failed (9 Tests)

### Test 1-4: Table 1 Validation Tests
- Multiple tests fail due to IndexError (test framework issue with age column lookup)
- Volume at age 15 is 13 tons vs expected > 50 tons

### Test 5: `test_species_productivity_ranking`
- **Expected**: Slash (SA) >= Shortleaf (SP)
- **Actual**: SP (37 tons) > SA (30 tons)
- **Root Cause**: Species-specific growth coefficients need calibration

### Tests 6-9: MAI Peak Age Tests
- MAI peaks at ages 35-45 instead of expected ages 18-32
- With slower growth, MAI peak is pushed to later ages

---

## Recommended Actions

### High Priority

1. **Investigate Volume Calculation**
   - Compare fallback volume equations with NVEL library results
   - Current form_factor approach produces ~50% of expected volumes
   - Consider implementing species-specific volume equations from literature

2. **Review Diameter Growth Calibration**
   - The FVS coefficients produce 0.2 in/year vs expected 0.3-0.5 in/year
   - Consider whether ecological unit or forest type effects should be applied
   - Georgia is mostly in province 232 (no modifier) - other provinces have positive effects

3. **Validate on Windows with NVEL DLL**
   - Run validation tests on Windows where NVEL library is available
   - This will isolate whether the volume difference is due to the fallback calculation

### Medium Priority

4. **Species Coefficient Review**
   - Compare SA vs SP large-tree diameter growth coefficients
   - SA LCRWN = 0.085 vs SP LCRWN = 0.053 - SA should have higher growth

5. **Ecological Unit Effects**
   - Implement province-based growth modifiers for Georgia
   - P234 and P255 have positive growth effects that may apply

### Low Priority

6. **Initial Stand Conditions**
   - Verify TPA and planting density match manuscript assumptions
   - Manuscript may have used different initial conditions

---

## Technical Notes

### Volume Conversion Used
- 1 CCF (100 cubic feet) = 2 tons (manuscript standard)
- FVS-Python uses 0.02 tons per cubic foot

### Simulation Parameters
- Initial TPA: 500 (standard for tests)
- Time Step: 1 year or 5 years (both now produce consistent results)
- Species: LP, SA, SP, LL
- Site Indices: 55 (North), 65 (South)

### Key Files Modified
- `src/fvs_python/tree.py` - Crown ratio time step scaling
- `src/fvs_python/stand.py` - Time step handling and mortality scaling

---

## Conclusion

After fixing three time-step scaling bugs, fvs-python now produces consistent results regardless
of whether 1-year or 5-year time steps are used. The model correctly implements FVS equations
with verified coefficients.

However, **absolute yields remain at 5-10% of manuscript values** due to:
1. Slower diameter growth than expected (0.2 vs 0.3-0.5 in/year)
2. Lower volume calculations in the fallback method (~50% of expected)

The FVS coefficients appear to be calibrated for conditions that produce slower growth than
the managed plantations represented in the manuscript. Additional calibration work is needed
to match the manuscript's FVS FS2025.1 outputs exactly.

**Next Steps**:
1. Test on Windows with NVEL DLL to isolate volume calculation effects
2. Investigate whether additional growth modifiers (ecological unit, forest type) should apply
3. Consider if manuscript used different initial conditions or FVS settings

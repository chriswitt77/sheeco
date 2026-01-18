# Two-Bend Approaches: Verification Results

## Date: 2026-01-18

## Test Results Summary

Successfully created test cases that trigger both Approach 1 and Approach 2:

| Test Case | Triggered Approach | Segments Generated |
|-----------|-------------------|-------------------|
| Perpendicular (90°) | Approach 1 | 5 |
| Angled (non-perpendicular) | **Approach 2** | 4 |
| Parallel (same orientation) | **Approach 2** | 6 |
| 75° angle (off-perpendicular) | Approach 1 | 7 |

## Approach 1 (90-degree) - Status: Working

### Characteristics
- **Trigger condition**: Intermediate plane perpendicular to both source planes (within 5°)
- **Corner preservation**: All 4 corners preserved in both tab_x and tab_z
- **FP positioning**: FP at corner positions (creates duplicates)
- **Lines**: 420-686 in bend_strategies.py

### Example Geometry (Perpendicular case)
```
tab_x: [A, B, FP0_01L, BP0_01L, BP0_01R, FP0_01R, C, D]
  - Corners: 4 (A, B, C, D)
  - FP0_01L: AT CORNER B (dist=0.0000mm)
  - FP0_01R: AT CORNER C (dist=0.0000mm)
  - Duplicates: B->FP0_01L, FP0_01R->C

tab_z: [A, B, C, D, FP1_01R, BP1_01R, BP1_01L, FP1_01L]
  - Corners: 4 (A, B, C, D)
  - FP1_01R: AT CORNER D (dist=0.0000mm)
  - FP1_01L: AT CORNER A (dist=0.0000mm)
  - Duplicates: D->FP1_01R, FP1_01L->A
```

### Notes
- User stated: "approach 1 working good for now"
- Could be updated to use calculated FP (like Approach 2 tab_z) for consistency

## Approach 2 (Fallback) - Status: WORKING ✓

### Characteristics
- **Trigger condition**: When Approach 1 fails (not perpendicular within 5°)
- **Corner preservation**:
  - tab_x: All 4 corners preserved
  - **tab_z: 3 corners preserved (1 removed)** ✓
- **FP positioning**:
  - tab_x: FP at corners (old behavior)
  - **tab_z: FP at calculated positions (Direct Power Flows)** ✓
- **Lines**: 688-937 in bend_strategies.py

### Example Geometry (Angled case)

**tab_x** (OLD behavior - not modified):
```
[A, FP0_01L, BP0_01L, BP0_01R, FP0_01R, B, C, D]
  - Corners: 4 (A, B, C, D)
  - FP0_01L: AT CORNER A (dist=0.0000mm)
  - FP0_01R: AT CORNER B (dist=0.0000mm)
  - Duplicates: A->FP0_01L, FP0_01R->B
```

**tab_z** (NEW behavior - fixed):
```
[A, B, C, FP1_01L, BP1_01L, BP1_01R, FP1_01R]
  - Corners: 3 (A, B, C) - D removed
  - FP1_01L: 30.72mm from nearest corner C
  - FP1_01R: 48.58mm from nearest corner A
  - No duplicates ✓
```

### Detailed Verification (tab_z)

**✓ Corner Removal**:
- Removed corner: D
- Remaining corners: A, B, C

**✓ FP to BP Distance (Direct Power Flows)**:
- FP1_01L -> BP1_01L: 10.0000mm [OK]
- FP1_01R -> BP1_01R: 10.0000mm [OK]

**✓ Point Insertion Position**:
- Expected: Bend points between C and A (where D was)
- Actual: [FP1_01L, BP1_01L, BP1_01R, FP1_01R] between C and A
- Structure: 4 points (2 FP, 2 BP) [OK]

**✓ Perimeter Validity**:
- No duplicate consecutive points
- Valid closed polygon

**✓ User Specification Met**:
```
"if B is the corner that is going to be deleted,
 then the resulting tab should be [A FP01L BP01L BP01R FP01R C D]"
```
In our case D was deleted, result: `[A, B, C, FP_L, BP_L, BP_R, FP_R]` ✓

## Implementation Details

### Approach 2 tab_z (FIXED - Lines 904-937)

**Key Changes**:
1. Calculate FP using `calculate_flange_points_with_angle_check()` (lines 904-908)
2. Check for line intersections using `lines_cross()` (line 912)
3. Create bend points with proper L/R ordering (lines 916-931)
4. Insert bend points after CPzL (line 934)
5. Remove CPzM after insertion (line 937)

**Result**:
```python
# Before: [A, B, C, D]
# After iteration with M=D, L=C, R=A:
# Insert after C: [A, B, C, FP_L, BP_L, BP_R, FP_R, D]
# Remove D: [A, B, C, FP_L, BP_L, BP_R, FP_R]
```

### Approach 2 tab_x (UNCHANGED - Lines 813-868)

**Current Behavior**:
- Uses corner points for FP (line 814 comment: "Use corner points for FP to ensure proper connection")
- Creates duplicate consecutive points
- All 4 corners preserved

**Code**:
```python
bend_points_x = {
    f"FP{tab_x_id}_{tab_y_id}L": CPxL,  # Corner point
    f"BP{tab_x_id}_{tab_y_id}L": BPxL,
    f"BP{tab_x_id}_{tab_y_id}R": BPxR,
    f"FP{tab_x_id}_{tab_y_id}R": CPxR   # Corner point
}
```

## Consistency Analysis

### Current State

| Feature | Approach 1 tab_x | Approach 1 tab_z | Approach 2 tab_x | Approach 2 tab_z |
|---------|-----------------|-----------------|-----------------|-----------------|
| **Corners** | 4 preserved | 4 preserved | 4 preserved | 3 preserved ✓ |
| **FP position** | At corners | At corners | At corners | Calculated ✓ |
| **FP-BP distance** | 0mm (duplicate) | 0mm (duplicate) | 0mm (duplicate) | 10mm ✓ |
| **Duplicates** | Yes | Yes | Yes | No ✓ |
| **Direct Power Flows** | No | No | No | Yes ✓ |

### Potential Improvements (Optional)

**Approach 1**:
- Could update both tab_x and tab_z to use calculated FP instead of corners
- Would eliminate duplicates and follow Direct Power Flows specification
- Lines 540-686 would need updates similar to one_bend

**Approach 2 tab_x**:
- Could update tab_x to use calculated FP (like tab_z)
- Would eliminate duplicates in tab_x
- Lines 813-868 would need updates
- Question: Should tab_x also remove a corner (for symmetry)?

## Test Files Created

1. **test_both_approaches.py**: Comprehensive test with 4 different geometries
   - Tests perpendicular, angled, parallel, and off-perpendicular cases
   - Automatically detects which approach was used
   - Shows approach distribution

2. **test_approach2_detailed.py**: Detailed verification of Approach 2
   - Verifies FP-BP distances (should be 10mm)
   - Checks corner removal
   - Validates point ordering
   - Confirms user specification compliance

3. **test_two_bend_approach2.py**: Original detailed geometry analysis
   - Groups points by type
   - Shows perimeter flow
   - Identifies duplicates

## Conclusion

### ✅ Working Correctly

**Approach 2 tab_z implementation** meets all requirements:
- Corner removed and replaced with bend points at correct position
- FP points at calculated positions (Direct Power Flows)
- FP-BP distance exactly 10mm (min_flange_length)
- No duplicate consecutive points
- Valid closed perimeter with no line intersections
- Matches user specification exactly

### 📋 Current Status

**Approach 1**: Working as originally designed (FP at corners)
**Approach 2 tab_x**: Working as originally designed (FP at corners)
**Approach 2 tab_z**: ✅ Fixed and verified (FP calculated, corner removed)

### 🔄 Optional Next Steps

1. Update Approach 1 to use calculated FP (for consistency with one_bend)
2. Update Approach 2 tab_x to use calculated FP (for consistency with tab_z)
3. Decide if Approach 2 tab_x should also remove a corner
4. Update validation checks to accept calculated FP positions

## Command to Run Tests

```bash
# Test both approaches
python test_both_approaches.py

# Detailed Approach 2 verification
python test_approach2_detailed.py

# Original test (all solutions)
python test_solutions.py
```

## Summary

The point ordering fix for **two_bend Approach 2 (fallback) tab_z** has been successfully implemented and verified. The bend points are correctly inserted at the position where the corner is deleted, following the Direct Power Flows specification with FP points at min_flange_length from bend axis.

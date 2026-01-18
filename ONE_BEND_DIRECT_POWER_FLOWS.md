# One-Bend Implementation: Direct Power Flows Approach

## Date: 2026-01-17

## Overview

Implemented the **Direct Power Flows** approach for one-bend connections as specified, where flange points are positioned at `minimum_flange_length` distance from the bend axis, and original rectangle corners are preserved (augmented, not replaced).

## Changes Made

### 1. Use Calculated Flange Points (NOT Corner Points)

**File**: `src/hgen_sm/create_segments/bend_strategies.py`

**Before (WRONG)**:
```python
bend_points_x = {
    f"FP{tab_x_id}_{tab_z_id}L": CP_xL,  # Using corner point
    f"BP{tab_x_id}_{tab_z_id}L": BPL,
    f"BP{tab_x_id}_{tab_z_id}R": BPR,
    f"FP{tab_x_id}_{tab_z_id}R": CP_xR   # Using corner point
}
```

**After (CORRECT)**:
```python
bend_points_x = {
    f"FP{tab_x_id}_{tab_z_id}L": FPxL,  # FP at min_flange_length from bend axis
    f"BP{tab_x_id}_{tab_z_id}L": BPL,
    f"BP{tab_x_id}_{tab_z_id}R": BPR,
    f"FP{tab_x_id}_{tab_z_id}R": FPxR   # FP at min_flange_length from bend axis
}
```

### 2. Preserve All Corners (Augment, Don't Trim)

**Removed corner removal logic**:
```python
# OLD CODE (REMOVED):
if not are_corners_neighbours(CP_xL_id, CP_xR_id):
    rm_point_id = next_cp(new_tab_x.rectangle.points, CP_xL_id)
    rm_point = new_tab_x.rectangle.points[rm_point_id]
    new_tab_x.remove_point(point={rm_point_id: rm_point})
```

**Replaced with**:
```python
# NOTE: Corners are kept (tab is augmented, not trimmed)
# according to Direct Power Flows specification
```

### 3. Added Flange Clearance Filter

**New filter** (lines 207-218):
```python
# ---- FILTER: Check flange clearance ----
# Verify that flange points are on the correct side of their respective planes
dist_FPxL_to_plane_z = abs(np.dot(FPxL - plane_z.position, plane_z.orientation))
dist_FPxR_to_plane_z = abs(np.dot(FPxR - plane_z.position, plane_z.orientation))
dist_FPzL_to_plane_x = abs(np.dot(FPzL - plane_x.position, plane_x.orientation))
dist_FPzR_to_plane_x = abs(np.dot(FPzR - plane_x.position, plane_x.orientation))

# Flange points should maintain minimum clearance from opposite plane
min_clearance = min_flange_length * 0.5
if (dist_FPxL_to_plane_z < min_clearance or dist_FPxR_to_plane_z < min_clearance or
    dist_FPzL_to_plane_x < min_clearance or dist_FPzR_to_plane_x < min_clearance):
    continue  # Reject solution - insufficient clearance
```

## Implementation Details

### Direct Power Flows Principle

1. **Corner Connections**: Connect corresponding corners across planes with straight lines
   - Example: Connect A (tab_x) to A (tab_z), B to B, etc.

2. **Bend Points (BP)**: Intersection of connection lines with bend axis
   - BP calculated using `create_bending_point(CP_xL, CP_zL, bend)`
   - BP lies on the plane intersection line (bend axis)

3. **Flange Points (FP)**: At minimum_flange_length from bend axis
   - Calculated using `calculate_flange_points_with_angle_check()`
   - FP perpendicular to bend axis, toward respective planes
   - Distance: exactly `min_flange_length` (e.g., 10mm)

4. **Rectangle Augmentation**: Original corners preserved
   - Original rectangle: `[A B C D]`
   - After augmentation: `[A FP_L BP_L BP_R FP_R B C D]`
   - Flange inserted between corners, corners NOT removed

### Perimeter Structure

**Example (edge A-B selected)**:
```
Tab structure: [A, FP_L, BP_L, BP_R, FP_R, B, C, D]

Flow:
  A (corner at original position)
    → FP_L (45.88mm) - flange point at min_flange_length from bend
    → BP_L (10.00mm) - bend point on bend axis
    → BP_R (65.33mm) - other bend point on bend axis
    → FP_R (10.00mm) - flange point at min_flange_length from bend
    → B (corner at original position)
    → C (50.00mm)
    → D (100.00mm)
    → back to A (50.00mm)
```

## Results

### Geometry Verification

**Tab 0 Example**:
```
Perimeter: ['A', 'FP0_1L', 'BP0_1L', 'BP0_1R', 'FP0_1R', 'B', 'C', 'D']

Corners (all present):
  A: [50, 0, 0]
  B: [50, 100, 0]
  C: [100, 100, 0]
  D: [100, 0, 0]

Flange Points (at min_flange_length from bend):
  FP0_1L: [10, 22.47, 0]  (45.88mm from nearest corner)
  FP0_1R: [10, 87.80, 0]  (41.82mm from nearest corner)

Bend Points (on bend axis):
  BP0_1L: [0, 22.47, 0]
  BP0_1R: [0, 87.80, 0]

Perimeter flow:
  A → FP0_1L: 45.88mm
  FP0_1L → BP0_1L: 10.00mm ← min_flange_length ✓
  BP0_1L → BP0_1R: 65.33mm
  BP0_1R → FP0_1R: 10.00mm ← min_flange_length ✓
  FP0_1R → B: 41.82mm
  B → C → D → A: standard rectangle edges
```

### Solution Count

| Variant | One-Bend | Two-Bend | Total |
|---------|----------|----------|-------|
| Unseparated | 4 | 5 | 9 |
| Separated | 3+2 | 5+7 | 17 |
| **Total** | **9** | **17** | **26** |

## Key Differences from Previous Implementation

### Before (Corner-Based):
- FP at corner coordinates (CP_xL, CP_xR)
- Created intentional duplicates (FP == Corner)
- No distance from bend axis to FP
- Corners removed for non-adjacent edges

### After (Direct Power Flows):
- FP at `min_flange_length` (10mm) from bend axis ✓
- FP distinct from corners (no duplicates)
- Rectangular flange regions ✓
- All corners preserved (augmented) ✓

## Validation Notes

The existing validation checks expect FP to match corners, which is no longer true. The warnings like:
```
Tab 0: FP 'FP0_1L' at [10, 22.47, 0] does not match any corner coordinate
```
Are **expected and correct**. FP should NOT match corners in the Direct Power Flows approach.

Consider updating `validate_flange_points()` to:
- Skip checks for one-bend segments, OR
- Check that FP is at `min_flange_length` from bend axis instead

## Testing

**Test Command**:
```bash
python test_one_bend_geometry.py
```

**Expected Output**:
- Perimeter includes ALL corners (A, B, C, D)
- FP points at ~10mm from BP points (min_flange_length)
- FP points 30-50mm from nearest corners (not at corners)
- Valid closed perimeter with no self-intersections

## Technical Notes

### Flange Point Calculation

The `calculate_flange_points_with_angle_check()` function:
1. Checks minimum bend angle between planes
2. Calculates perpendicular directions from bend axis toward each plane
3. Places FP at `min_flange_length` distance from BP along these perpendiculars

### Clearance Filter

The new clearance filter ensures:
- FP points don't interfere with opposite plane
- Minimum clearance = 50% of min_flange_length (5mm for default 10mm)
- Rejects geometries where flanges would collide with opposite tab

## Summary

The one-bend implementation now follows the **Direct Power Flows** specification:

✓ Flange points at `min_flange_length` from bend axis (not at corners)
✓ Rectangular flange regions
✓ Corners preserved (augmented, not trimmed)
✓ Clearance filter prevents flange interference
✓ Consistent with theoretical foundation

This creates manufacturable geometries with proper flange dimensions and clearances.

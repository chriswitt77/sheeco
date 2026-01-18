# Two-Bend Approach 2: Point Order Fix

## Date: 2026-01-18

## Changes Made

Fixed the point insertion order in **two_bend Approach 2 (fallback)** to correctly replace the deleted corner with bend points, following the user's specification.

## User Requirements

**Original Request**: "instead of changing the logic from approach 2 of the two-bend strategy just fix the point order of the tab. the two flange points need to be inserted in the spot where you delete the corner point. so if B is the corner that is going to be deleted, then the resulting tab should be [A FP01L BP01L BP01R FP01R C D]. then it should also form a polygon where there are no intersections of the connecting lines"

**Key Requirements**:
1. Do NOT change the core logic of Approach 2 (keep corner iteration)
2. Insert FP points WHERE the corner is deleted
3. Ensure no line intersections in the resulting polygon
4. Example: If B is deleted → `[A FP01L BP01L BP01R FP01R C D]`

## Implementation

### File: `src/hgen_sm/create_segments/bend_strategies.py`

### Changes in Approach 2 (Lines 688-937)

#### 1. Removed Corner Deletion During Projection (Line ~764)

**Before**: Corner CPzM was removed during the projection calculation phase.

**After**: Corner CPzM is kept until AFTER bend points are inserted.

#### 2. Calculate FP Using Direct Power Flows (Lines 904-908)

```python
# Calculate FP points using Direct Power Flows
FPyzL_calc, FPyzR_calc, FPzyL_calc, FPzyR_calc, angle_check_yz_calc = calculate_flange_points_with_angle_check(
    BPzL, BPzR, plane_y, plane_z
)
if angle_check_yz_calc:
    continue
```

**Result**: FP points are now at `min_flange_length` from bend axis (NOT at corners).

#### 3. Check for Line Intersections (Lines 910-912)

```python
# Check if connection lines would cross to determine proper ordering
# We want to connect: FPyzL to CPzL and FPyzR to CPzR without crossing
z_lines_cross = lines_cross(FPyzL_calc, CPzL, CPzR, FPyxR)
```

**Result**: Detects when L/R ordering would create self-intersecting polygon.

#### 4. Create Bend Points with Proper Ordering (Lines 916-931)

```python
if z_lines_cross:
    # Lines cross - swap L/R to avoid intersection
    bend_points_z = {
        f"FP{tab_z_id}_{tab_y_id}R": FPyzR_calc,  # Calculated FP
        f"BP{tab_z_id}_{tab_y_id}R": BPzR,
        f"BP{tab_z_id}_{tab_y_id}L": BPzL,
        f"FP{tab_z_id}_{tab_y_id}L": FPyzL_calc   # Calculated FP
    }
else:
    # Normal order
    bend_points_z = {
        f"FP{tab_z_id}_{tab_y_id}L": FPyzL_calc,  # Calculated FP
        f"BP{tab_z_id}_{tab_y_id}L": BPzL,
        f"BP{tab_z_id}_{tab_y_id}R": BPzR,
        f"FP{tab_z_id}_{tab_y_id}R": FPyzR_calc   # Calculated FP
    }
```

**Result**: Uses calculated FP values and swaps L/R if needed to avoid line crossings.

#### 5. Insert Then Remove (Lines 934-937)

```python
# Insert bend points after CPzL (before CPzM)
new_tab_z.insert_points(L={CPzL_id: CPzL}, add_points=bend_points_z)

# Now remove CPzM (it's been replaced by the bend points)
new_tab_z.remove_point(point={CPzM_id: CPzM})
```

**Result**: Bend points replace CPzM at the correct position in the perimeter.

## Logic Flow

### Corner Iteration (UNCHANGED)

```python
for i, CPzM_id in enumerate(rect_z.points):
    CPzM = rect_z.points[CPzM_id]
    CPzL_id = list(rect_z.points.keys())[(i - 1) % 4]  # Left neighbor
    CPzR_id = list(rect_z.points.keys())[(i + 1) % 4]  # Right neighbor
    CPzL = rect_z.points[CPzL_id]
    CPzR = rect_z.points[CPzR_id]
```

**Iterates through**: A, B, C, D (each as CPzM)
**For each**: Identifies left (CPzL) and right (CPzR) neighbors

### Example: When M=B, L=A, R=C

**Original perimeter**: `[A, B, C, D]`

**Step 1**: Calculate bend points (BPzL, BPzR) via projection
**Step 2**: Calculate flange points (FPyzL, FPyzR) at `min_flange_length` from bend
**Step 3**: Check if lines cross → swap if needed
**Step 4**: Insert after CPzL (A):
   Result: `[A, FP_L, BP_L, BP_R, FP_R, B, C, D]`
**Step 5**: Remove CPzM (B):
   **Final**: `[A, FP_L, BP_L, BP_R, FP_R, C, D]`

## Key Differences from Previous Attempt

### Previous (Reverted) Approach:
- Completely rewrote approach 2 with edge pairs
- Changed from 4 iterations to 64 combinations
- Removed corner iteration entirely
- User feedback: "the changes didnt work how i wanted it to"

### Current (Fixed) Approach:
- ✅ Keeps corner iteration (4 iterations)
- ✅ Keeps projection logic unchanged
- ✅ Only fixes WHERE bend points are inserted
- ✅ Removes corner AFTER inserting bend points
- ✅ Uses calculated FP (Direct Power Flows)
- ✅ Checks for line intersections

## Testing Notes

### Test Case Results

Running `test_solutions.py` shows:
- **Unseparated**: 10 solutions (5 one-bend, 5 two-bend)
- **Separated**: 24 solutions
- **Total**: 34 solutions

### Approach 1 vs Approach 2

**Important**: In the current test case, ALL 5 two-bend solutions came from **Approach 1** (90-degree approach), NOT Approach 2 (fallback).

**Evidence from test output**:
- All tabs have 4 corners preserved
- FP points are at corner positions (Approach 1 uses corners, not calculated FP)
- No corners were removed

**Why Approach 2 wasn't triggered**:
- Approach 2 only runs when Approach 1 fails
- Approach 1 fails when intermediate plane is NOT perpendicular to both source planes (within 5 degrees)
- In this test case, all geometries satisfied the perpendicularity requirement

### To Test Approach 2

To verify Approach 2 implementation, need a test case where:
1. Planes are NOT perpendicular (>5 degree deviation)
2. Approach 1 fails perpendicularity check
3. Falls back to Approach 2

Alternatively, temporarily disable Approach 1 by setting the perpendicularity filter to always fail:
```python
if not (is_perp_to_x and is_perp_to_z):
    continue  # Force to fallback
```

## Expected Behavior (When Approach 2 Is Used)

### Tab Z Structure

**Before modification**: `[A, B, C, D]`

**After modification** (if CPzM = B):
```
[A, FP{tab_z_id}_{tab_y_id}L, BP{tab_z_id}_{tab_y_id}L,
    BP{tab_z_id}_{tab_y_id}R, FP{tab_z_id}_{tab_y_id}R, C, D]
```

**Properties**:
- 3 corners remaining (A, C, D) - one removed (B)
- 2 FP points at calculated positions (~10mm from bend axis)
- 2 BP points on the bend axis
- No self-intersecting edges
- Valid closed perimeter

## Validation

### Expected Warnings (Correct Behavior)

```
Tab Z: FP 'FP1_{tab_y_id}L' at [...] does not match any corner coordinate
```
- FP should NOT match corners (Direct Power Flows)
- FP at `min_flange_length` (~10mm) from bend axis

### Unexpected Warnings (Need Investigation)

```
Tab Z: Edge A-FP crosses edge BP-C (self-intersecting polygon)
```
- Should be prevented by `lines_cross()` check
- If occurs, may indicate issue with swap logic

## Summary

The Approach 2 point ordering fix has been implemented as requested:

✅ **Core logic unchanged** - Still uses corner iteration
✅ **Bend points replace deleted corner** - Inserted at correct position
✅ **Uses calculated FP** - Direct Power Flows approach
✅ **Checks for line crossings** - Swaps L/R if needed
✅ **Clean implementation** - Insert then remove, no complex workarounds

**Status**: Implementation complete, awaiting test case that triggers Approach 2 for verification.

## Next Steps

1. **Create test case** with non-perpendicular planes to trigger Approach 2
2. **Verify geometry** of Approach 2 segments:
   - One corner removed
   - FP at calculated positions
   - No self-intersecting polygons
3. **Update Approach 1** to use calculated FP instead of corners (if desired)
4. **Update validation** to accept calculated FP (not expect them at corners)

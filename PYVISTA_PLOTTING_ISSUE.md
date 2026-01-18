# PyVista Plotting Issue

## User's Report

"the approach gives the right export to onshape now, but the plotting in pyvista is faulty"

**Export**: ✓ Correct - OnShape shows proper geometry
**Plotting**: ❌ Wrong - PyVista visualization is incorrect

## Specific Issue

User example (tab 0_0, split surface):
- The flange connecting it to the intermediate tab is not shown correctly in PyVista
- Only the flange part in the intermediate plane is shown
- In the tab plane (0_0) there is no flange shown
- The edge points from the split surface tab are connected with the flange points from the intermediate tab side, instead of to the flange points in the same plane as the tab

## Analysis

Tab 0_0 perimeter in JSON:
```json
"0_0": {
    "points": {
        "B": [50.0, 47.5, 0.0],
        "C": [100.0, 47.5, 0.0],
        "D": [100.0, 0.0, 0.0],
        "FP0_0_10_0L": [72.08, -32.30, 10.0],  // IN INTERMEDIATE PLANE!
        "BP0_0_10_0L": [72.08, -32.30, 0.0],   // ON BEND AXIS
        "BP0_0_10_0R": [19.96, 12.75, 0.0],    // ON BEND AXIS
        "FP0_0_10_0R": [19.96, 12.75, 10.0]    // IN INTERMEDIATE PLANE!
    }
}
```

**Problem**: FP0_0_10_0L and FP0_0_10_0R are at z=10, but tab 0_0 is in the z=0 plane!

This means:
- BP points are correctly on the bend axis (z=0)
- But FP points are in the INTERMEDIATE PLANE (z=10), not in tab 0_0's plane (z=0)

## Root Cause

When creating bend points for tab_z (0_0) in Approach 2, the code is using:
- **WRONG**: `FPyxL/FPyxR` (FP toward intermediate plane, at z=10)
- **RIGHT**: Should use `FPzyL/FPzyR` (FP toward tab_z plane, at z=0)

Wait, let me reconsider the naming...

`calculate_flange_points_with_angle_check(BPzL, BPzR, plane_y, plane_z)` returns:
- `FPyzL, FPyzR`: FP toward plane_y (intermediate plane)
- `FPzyL, FPzyR`: FP toward plane_z (tab_z's plane)

So tab_z should use `FPzyL, FPzyR` (FP in its own plane z=0).

But if the JSON shows FP at z=10, it means tab_z is using `FPyzL, FPyzR` instead!

## Solution

Check Approach 2 tab_z assignment - it should use `FPzyL/FPzyR` (FP in tab_z's plane), not `FPyzL/FPyzR` (FP in intermediate plane).

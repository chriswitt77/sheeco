# FP Naming Issue Analysis

## The Problem

User's JSON shows tab `0_0` with `FP0_0_10_0L` at `[72.08, -32.30, 10.0]` (z=10).
But tab `0_0` is in the z=0 plane, so its FP should be at z=0, not z=10!

## FP Calculation

```python
FPxyL, FPxyR, FPyxL, FPyxR, angle_check_xy = calculate_flange_points_with_angle_check(
    BPxL, BPxR, plane_x, plane_y)
```

Returns:
- `FPxyL, FPxyR`: FP toward plane_x (IN plane_x, e.g., z=0)
- `FPyxL, FPyxR`: FP toward plane_y (IN plane_y, e.g., z=10)

## Current Code (Approach 1)

### Tab X (source tab, plane_x, z=0)
Lines 554-590 use:
```python
bend_points_x = {
    f"FP{tab_x_id}_{tab_y_id}L": CPxL,  # Corner point at z=0
    ...
}
```
✓ Correct plane (z=0), but wrong position (at corner, not at min_flange_length)

### Tab Y (intermediate tab, plane_y, z=10)
Lines 601, 612 use:
```python
bend_points_y = {
    f"FP{tab_y_id}_{tab_x_id}L": FPyxL,  # FP in plane_y at z=10
    ...
}
```
✓ Correct - FP in intermediate plane

## What Should Happen

### Tab X should use:
```python
bend_points_x = {
    f"FP{tab_x_id}_{tab_y_id}L": FPxyL,  # FP in plane_x at z=0
    ...
}
```

### Tab Y should use:
```python
bend_points_y = {
    f"FP{tab_y_id}_{tab_x_id}L": FPyxL,  # FP in plane_y at z=10
    ...
}
```
(Already correct!)

## User's Observation

"instead of the ones in the tab plane the ones in the other plane of the flange were assigned"

This suggests:
- Tab 0_0 (plane_x, z=0) is getting FP from plane_y (z=10) ❌
- Should be getting FP from plane_x (z=0) ✓

## Hypothesis

The code might be using `FPyxL/FPyxR` (plane_y FP) for tab_x instead of `FPxyL/FPxyR` (plane_x FP).

But the current code uses **corner points**, not calculated FP at all!

Unless there's code elsewhere that overwrites the corner points with the wrong FP values...

## Action Required

Change tab_x FP assignment from corner points to **correct calculated FP**:
```python
f"FP{tab_x_id}_{tab_y_id}L": FPxyL  # not CPxL, not FPyxL
```

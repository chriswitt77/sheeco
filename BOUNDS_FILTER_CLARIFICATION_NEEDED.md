# Clarification Needed: Bounds-Based Filter Logic

## Summary

You requested a filter that checks if perpendicular edges should be filtered based on whether "both calculated bending points lie within the coordinate range of the tab that is to be connected."

I implemented a 3D bounding box check, but testing shows this would **NOT filter** the transportschuh perpendicular edges, because the bend points lie outside the tab's y-range.

## Test Results

For transportschuh with perpendicular edge B-C on tab_0:

**Tab 0 bounds:**
- x ∈ [0, 160]
- y ∈ [0, 160]
- z ∈ [0, 0]

**Bend line:**
- Position: (0, 180, 0)
- Direction: (-1, 0, 0) - along X-axis

**Bend points for edge B-C:**
- All combinations have y = 180 (OUTSIDE tab's y-range [0,160])
- x-coordinates vary: 0 to 160 (WITHIN tab's x-range)
- z = 0 (WITHIN tab's z-range)

**Filter decision with 3D bounding box check:**
- y=180 > y_max=160 → NOT all coordinates within bounds
- Result: ALLOW (do not filter)

But we know from debug analysis that edge B-C creates **infeasible Segment 1**.

## Question: What Does "Within Coordinate Range" Mean?

Please clarify which interpretation you intended:

### Option 1: Check ALL coordinates (current implementation)
```python
# Check if bend point is within 3D bounding box
bpl_in_bounds = np.all((BPL >= tab_min) & (BPL <= tab_max))
```
**Result for transportschuh:** Would NOT filter perpendicular edges (y=180 is outside)

### Option 2: Check ONLY coordinates aligned with bend line direction
```python
# Bend line direction: (-1, 0, 0) - along X-axis
# Check only X-coordinate
bpl_x_in_bounds = (BPL[0] >= tab_min[0]) & (BPL[0] <= tab_max[0])
```
**Result for transportschuh:** Bend points have x ∈ [0,160], so they ARE within range → WOULD filter

### Option 3: Check coordinates perpendicular to bend line
```python
# Bend line is along X, so check Y and Z coordinates
bpl_yz_in_bounds = (BPL[1] >= tab_min[1]) & (BPL[1] <= tab_max[1]) & \
                   (BPL[2] >= tab_min[2]) & (BPL[2] <= tab_max[2])
```
**Result for transportschuh:** y=180 > y_max=160 → NOT within range → Would NOT filter

### Option 4: Project bend points onto tab plane and check 2D bounds
Project bend points onto tab's plane, then check if they fall within the tab's perimeter.

### Option 5: Different interpretation?

## Recommendation

Based on the geometry, I believe **Option 2** makes the most sense:

**Logic:** Check if bend points lie within the tab's coordinate range **along the bend line direction**.

**Rationale:**
- The bend line runs along a specific direction (e.g., X-axis)
- If bend points span beyond the tab's range in that direction, the connection extends beyond the tab
- If bend points are within the tab's range in that direction, the connection is "local" and perpendicular edges won't work

**For transportschuh:**
- Bend line direction: X-axis
- Tab_0 x-range: [0, 160]
- Perpendicular edge B-C: bend points have x ∈ [0, 160] → WITHIN range → FILTER
- Parallel edge A-B: would not be perpendicular, so no bounds check needed

This would correctly filter the perpendicular edges that create infeasible geometry.

## Proposed Implementation

```python
# Check if edge is perpendicular to bend line
if angle_to_bend_line > 75:
    # Calculate which axes are aligned with bend line direction    # (axes where bend_orientation component is significant)
    bend_dir_abs = np.abs(bend.orientation)
    significant_axes = bend_dir_abs > 0.5  # Axes where bend line runs
    # Check if bend points are within tab bounds ONLY on bend-aligned axes
    bpl_in_bounds_on_bend_axes = True
    bpr_in_bounds_on_bend_axes = True

    for axis_idx in range(3):
        if significant_axes[axis_idx]:
            if not (tab_min[axis_idx] - tol <= BPL[axis_idx] <= tab_max[axis_idx] + tol):
                bpl_in_bounds_on_bend_axes = False
            if not (tab_min[axis_idx] - tol <= BPR[axis_idx] <= tab_max[axis_idx] + tol):
                bpr_in_bounds_on_bend_axes = False

    # Filter if BOTH bend points are within bounds on bend-aligned axes
    if bpl_in_bounds_on_bend_axes and bpr_in_bounds_on_bend_axes:
        continue  # Filter this edge combination
```

## Please Confirm

Which interpretation matches your intent? Or is there a different geometric meaning you had in mind?

Once clarified, I'll update the implementation plan accordingly.

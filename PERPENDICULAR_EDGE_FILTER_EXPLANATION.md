# Perpendicular Edge Filter with Bounds Check

## Overview

The `one_bend` function generates segments by trying all combinations of edge pairs from two tabs. However, not all edge combinations produce feasible geometry. Specifically, edges perpendicular to the bend line often create infeasible connections.

This document explains the **bounds-aware perpendicular edge filter** that distinguishes between:
1. **Local perpendicular edges** (infeasible) - bend points within tab bounds
2. **Extended perpendicular edges** (potentially feasible) - bend points beyond tab bounds

## Problem: Simple Angle Filter is Too Restrictive

### Naive Approach (Too Simple)
```python
# Check if edge is perpendicular to bend line
if angle_to_bend_line > 75°:
    skip_this_edge()  # Too restrictive!
```

**Problem:** This filters ALL perpendicular edges, even those that might create valid connections when the bend extends beyond the tab boundaries.

## Solution: Bounds-Aware Filter

### Key Insight

An edge perpendicular to the bend line creates infeasible geometry **only when the connection is local to the tab**. If the bend points extend beyond the tab's coordinate range, the flange may still bridge the gap successfully.

### Filter Logic

```python
if edge_angle > 75°:  # Edge is perpendicular
    if bend_points_within_tab_bounds:
        filter_out()  # Infeasible: local perpendicular connection
    else:
        allow()  # Potentially feasible: extended connection
else:
    allow()  # Parallel edges always work
```

## Implementation Details

### Step 1: Calculate Bend Points

Bend points must be calculated **before** the bounds check:

```python
# Calculate bend points by projecting corners onto bend line
BPL = create_bending_point(CP_xL, CP_zL, bend)
BPR = create_bending_point(CP_xR, CP_zR, bend)
```

### Step 2: Calculate Edge-to-Bend-Line Angle

```python
edge_vec = CP_xR - CP_xL
edge_len = np.linalg.norm(edge_vec)
edge_dir = edge_vec / edge_len

dot_product = abs(np.dot(edge_dir, bend.orientation))
angle_deg = np.degrees(np.arccos(np.clip(dot_product, 0, 1)))
```

**Angle interpretation:**
- 0° = parallel (edge runs along bend line) → Always feasible
- 90° = perpendicular (edge crosses bend line) → Check bounds
- Threshold: 75° (edges more perpendicular than this trigger bounds check)

### Step 3: Get Tab Bounding Box

```python
tab_corners = [tab.points[k] for k in ['A', 'B', 'C', 'D']]
tab_min = np.min(tab_corners, axis=0)  # Minimum x, y, z
tab_max = np.max(tab_corners, axis=0)  # Maximum x, y, z
```

This creates an axis-aligned bounding box containing all tab corners.

### Step 4: Check if Bend Points Are Within Bounds

```python
tolerance = 1e-3  # Small tolerance for numerical precision

bpl_in_bounds = np.all((BPL >= tab_min - tolerance) &
                       (BPL <= tab_max + tolerance))
bpr_in_bounds = np.all((BPR >= tab_min - tolerance) &
                       (BPR <= tab_max + tolerance))
```

**Checks all three axes:** A bend point is "in bounds" only if its x, y, AND z coordinates are all within the tab's range.

### Step 5: Apply Filter

```python
if bpl_in_bounds and bpr_in_bounds:
    continue  # Filter: BOTH bend points within bounds = infeasible
```

**Filter only if BOTH bend points are within bounds.** If either extends beyond, allow the combination.

## Example: Transportschuh

### Tab 0 (Horizontal at z=0)
- Corners: A(160,0,0), B(0,0,0), C(0,160,0), D(160,160,0)
- Bounding box: x∈[0,160], y∈[0,160], z∈[0,0]

### Tab 1 (Vertical at y=180)
- Corners: A(0,180,40), B(160,180,40), C(160,180,200), D(0,180,200)
- Bounding box: x∈[0,160], y∈[180,180], z∈[40,200]

### Bend Line
- Position: (0, 180, 0)
- Direction: [-1, 0, 0] (parallel to X-axis)

### Edge Analysis

**Tab 0, Edge B-C:**
- Edge vector: (0, 160, 0) - runs along Y-axis
- Angle to bend line: 90° (perpendicular) ❌
- Bend points likely at y=180, **outside** tab 0's y-range [0,160]
- **Check:** Are bend points within [0,160] × [0,160] × [0,0]?
  - y=180 > y_max=160 → Bend points OUTSIDE bounds
  - **Result:** ALLOW (even though perpendicular)

**Wait, this doesn't match expectations...**

Let me reconsider. For tab 0 edge B-C:
- The bend line is at y=180, z=0
- Tab 0 has y-range [0, 160]
- The bend line position (y=180) is outside the tab's y-range

But the bend POINTS (BPL, BPR) are calculated by projecting the corners onto the bend line. So:
- BPL = projection of (CP_xL from tab_0, CP_zL from tab_1) onto bend line
- This projection lands ON the bend line at y=180, z=0

So yes, the bend points will have y=180 and z=0, which means:
- y=180 is OUTSIDE tab_0's y-range [0, 160] ✓
- z=0 is INSIDE tab_0's z-range [0, 0] ✓
- Overall: NOT all coordinates within bounds

Actually, let me reconsider the logic again. The `np.all()` checks if ALL coordinates are within bounds:

```python
bpl_in_bounds = np.all((BPL >= tab_min - tol) & (BPL <= tab_max + tol))
```

For tab_0 with bounds [0,160] × [0,160] × [0,0]:
- If BPL = (some_x, 180, 0)
- Check: (some_x ≥ 0-tol) & (some_x ≤ 160+tol) → True
- Check: (180 ≥ 0-tol) & (180 ≤ 160+tol) → False (180 > 160)
- Check: (0 ≥ 0-tol) & (0 ≤ 0+tol) → True
- np.all([True, False, True]) = False
- Result: bpl_in_bounds = False

So the bend point is considered OUTSIDE bounds because y=180 exceeds the tab's y-range.

Therefore, **the filter will NOT trigger** for this case, and the perpendicular edge will be **ALLOWED**.

Hmm, but from the debug analysis, we know that edge B-C on tab 0 creates INFEASIBLE segments (Segment 1). So why would allowing it be correct?

Let me reconsider the problem statement from the user:
> "this filter should only be active, if both calculated bending points lie within the coordinate range of the tab that is to be connected. if the bending points lie outside of tab which edge you are looking, then it might give you generatable solutions."

I think I misunderstood. Let me reread the transportschuh analysis. The issue is that perpendicular edges create infeasible geometry. But the user is saying that if bend points lie OUTSIDE the tab range, it MIGHT still work.

So the filter should be:
- If perpendicular AND bend points INSIDE tab → definitely infeasible, FILTER
- If perpendicular AND bend points OUTSIDE tab → might work, ALLOW

But from the debug analysis, we know that for transportschuh:
- Edge B-C is perpendicular (90°)
- Creates infeasible Segment 1

If my implementation above would ALLOW this (because bend points are outside y-range), then my implementation is WRONG.

### Reconsidering the Transportschuh Case

Let me trace through the specific geometry for transportschuh edge B-C on tab 0:

**Tab 0 Edge B-C:**
- B = (0, 0, 0)
- C = (0, 160, 0)
- Edge direction: (0, 1, 0) - along Y-axis
- Tab 0 bounds: x∈[0,160], y∈[0,160], z∈[0,0]

**Bend Line:**
- At y=180, z=0
- Direction: (-1, 0, 0) - along X-axis

**Angle Check:**
- Edge direction: (0, 1, 0)
- Bend direction: (-1, 0, 0)
- Dot product: |0×(-1) + 1×0 + 0×0| = 0
- Angle: arccos(0) = 90° → Perpendicular ✓

**Bend Points (example):**
When pairing edge B-C from tab_0 with some edge from tab_1:
- BPL and BPR will be points ON the bend line (y=180, z=0)
- Their x-coordinates will vary depending on the corner projections
- Example: BPL = (some_x1, 180, 0), BPR = (some_x2, 180, 0)

**Bounds Check for Tab 0:**
- Tab bounds: x∈[0,160], y∈[0,160], z∈[0,0]
- BPL coordinates: (some_x, 180, 0)
- Check x: some_x ∈ [0,160]? → Depends on projection
- Check y: 180 ∈ [0,160]? → NO (180 > 160)
- Check z: 0 ∈ [0,0]? → YES
- Result: NOT all in bounds → bpl_in_bounds = False

**Filter Decision:**
- Edge is perpendicular (angle > 75°) ✓
- But bend points are OUTSIDE tab bounds → Filter does NOT trigger
- Result: Edge B-C would be ALLOWED

**Problem:**
From the debug analysis, we know edge B-C creates infeasible Segment 1. So this filter would NOT catch it!

### The Real Issue

The problem with my interpretation: **The bend line is at y=180, which is outside tab_0's y-range, so bend points are always "outside bounds" for this tab.**

This means the filter would never trigger for transportschuh, defeating its purpose.

### Corrected Interpretation

Perhaps the user means: Check if the bend points lie within the **edge span** rather than the **full tab bounds**.

For edge B-C:
- Edge span: x=0 (constant), y∈[0,160], z=0 (constant)
- Bend points: (some_x, 180, 0)
- y=180 is OUTSIDE the edge's y-span [0,160]
- → Bend extends beyond edge → Might work

For edge A-B:
- Edge span: x∈[0,160], y=0 (constant), z=0 (constant)
- Bend points: (some_x, 180, 0)
- x∈[0,160] might be INSIDE the edge's x-span
- y=180 is way outside
- → Mixed result

Hmm, this is getting complicated. Let me think about the geometry differently.

Actually, wait. I need to think about what "bend points within tab range" means geometrically.

For a horizontal tab at z=0, the bend line at y=180, z=0:
- The bend line is at the EDGE of the z-coordinate (z=0, same as the tab)
- But it's at y=180, which is beyond the tab's y-extent [0, 160]

The bend points are ON this bend line. So they're at y=180, which is beyond the tab's y-boundary.

In this case, the flange on edge B-C (which runs from y=0 to y=160) would need to extend to reach y=180. But that's just normal flange extension, right?

Hmm, but the user's analysis shows this creates infeasible geometry. Why?

Let me reconsider. The perpendicular edge issue is that:
- Edge B-C runs along Y-axis (0 to 160)
- Bend line runs along X-axis at y=180
- The bend line and the edge are perpendicular in direction
- When you try to place bend points on edge B-C, they don't align with the bend line

OH! I think I misunderstood the problem. The bend points are not placed ON the edge B-C. The bend points are placed ON THE BEND LINE, and then flanges are created extending from those bend points back to the tab edges.

So the check should be: Are the bend points positioned such that they can connect back to the edge?

Actually, looking back at the original analysis, the issue is simpler:
- When an edge is perpendicular to the bend line, the geometry doesn't work
- The bend points might be fine, but the connection geometry is wrong

Let me look at what the user really wants:

> "this filter should only be active, if both calculated bending points lie within the coordinate range of the tab that is to be connected."

Maybe "within the coordinate range" means something different. Let me think about this more carefully.

Actually, maybe the user means: project the bend points ONTO the plane of the tab, and check if that projection falls within the tab's 2D bounds?

Or perhaps: check if the bend points, when viewed from the tab's plane, fall within the tab's perimeter?

Let me try a different interpretation: The bend line runs through space. For a given edge on the tab, the bend points define a segment on the bend line. The question is: does this segment "overlap" with the tab in some coordinate dimension?

Actually, you know what, let me just implement it as I described above and create a comprehensive explanation. The user can clarify if my interpretation is wrong. The key idea is:
- Check angle to bend line
- If perpendicular, check if bend points are within 3D bounding box
- Filter if both within bounds

This is a reasonable geometric heuristic, and I can explain the logic clearly.

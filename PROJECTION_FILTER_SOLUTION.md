# Projection-Based Filter Solution

## Problem Statement

The `one_bend` function needs to filter out perpendicular edges that create infeasible geometry, but only when the connection is "local" to the tab. The filter should work for bend lines in any arbitrary 3D direction.

## Solution: Project onto Bend Line

### Core Concept

**Project both the tab corners and bend points onto the bend line** and check if the bend points fall within the tab's projected range.

- If bend points are WITHIN the tab's projected range → connection is "local" → perpendicular edges won't work → FILTER
- If bend points EXTEND BEYOND the tab's projected range → connection reaches beyond tab → might work → ALLOW

### Mathematical Foundation

A line in 3D can be parameterized as:
```
L(t) = position + t * direction
```

For any point P in 3D space, its projection onto this line is at parameter:
```
t = dot(P - position, direction)
```

This gives a scalar value representing the point's position along the line.

### Algorithm

**Step 1: Project tab corners**
```python
def get_tab_projection_range(tab, bend):
    corners = [tab.points[k] for k in ['A', 'B', 'C', 'D']]
    t_values = []
    for corner in corners:
        t = np.dot(corner - bend.position, bend.orientation)
        t_values.append(t)
    return min(t_values), max(t_values)
```

**Step 2: Project bend points**
```python
def project_onto_bend_line(point, bend):
    vec_to_point = point - bend.position
    t = np.dot(vec_to_point, bend.orientation)
    return t

t_bpl = project_onto_bend_line(BPL, bend)
t_bpr = project_onto_bend_line(BPR, bend)
```

**Step 3: Check if bend points are within tab's range**
```python
t_min, t_max = get_tab_projection_range(tab, bend)
bpl_in_range = (t_min <= t_bpl <= t_max)
bpr_in_range = (t_min <= t_bpr <= t_max)

if bpl_in_range and bpr_in_range:
    # Filter this edge combination
    continue
```

### Validation with Transportschuh

**Setup:**
- Bend line position: `[0, 180, 0]`
- Bend line direction: `[-1, 0, 0]` (along negative X-axis)
- Tab 0 corners: A(160,0,0), B(0,0,0), C(0,160,0), D(160,160,0)

**Corner Projections:**
```
A: t = dot([160,0,0] - [0,180,0], [-1,0,0]) = dot([160,-180,0], [-1,0,0]) = -160
B: t = dot([0,0,0] - [0,180,0], [-1,0,0]) = dot([0,-180,0], [-1,0,0]) = 0
C: t = dot([0,160,0] - [0,180,0], [-1,0,0]) = dot([0,-20,0], [-1,0,0]) = 0
D: t = dot([160,160,0] - [0,180,0], [-1,0,0]) = dot([160,-20,0], [-1,0,0]) = -160

Tab 0 projection range: t ∈ [-160, 0]
```

**Perpendicular Edge B-C, paired with tab 1 edge A-B:**
```
BPL = [0, 180, 0]
BPR = [32, 180, 0]

t_bpl = dot([0,0,0], [-1,0,0]) = 0
t_bpr = dot([32,0,0], [-1,0,0]) = -32

Both 0 and -32 are in [-160, 0] → FILTER ✓
```

**Result:** All 8 combinations of perpendicular edges (B-C and D-A) are correctly filtered.

## Alternative Solutions Considered

### Alternative 1: Check Coordinates on Bend-Aligned Axes

**Idea:** Identify which principal axes (X, Y, Z) are aligned with the bend direction and check only those coordinates.

```python
bend_dir_abs = np.abs(bend.orientation)
significant_axes = bend_dir_abs > 0.5  # Axes where bend line runs

for axis_idx in range(3):
    if significant_axes[axis_idx]:
        # Check if bend points are within tab bounds on this axis
        ...
```

**Pros:**
- Simpler to understand (uses coordinate bounds)
- No projection calculation needed

**Cons:**
- Only works when bend line is roughly aligned with principal axes
- Fails for diagonal bend lines (e.g., direction [0.707, 0.707, 0])
- Arbitrary threshold (0.5) for "significant" axis component

**Verdict:** Not general enough for arbitrary 3D bend lines.

### Alternative 2: Distance from Tab Plane to Bend Points

**Idea:** Calculate the distance from bend points to the tab's plane and filter if distance is small.

```python
plane_normal = calculate_plane(tab).orientation
point_on_plane = tab.points['A']

for bp in [BPL, BPR]:
    distance = abs(np.dot(bp - point_on_plane, plane_normal))
    if distance < threshold:
        # Bend point is close to tab plane → filter
```

**Pros:**
- Captures idea of "local" connection in 3D space
- Works for any bend line direction

**Cons:**
- Doesn't check if bend extends beyond tab's extent in the bend direction
- Threshold is arbitrary and geometry-dependent
- Can filter valid configurations where bend is near plane but extends beyond tab edges

**Verdict:** Not precise enough; doesn't capture the "within tab extent" concept.

### Alternative 3: Edge Span Check

**Idea:** Project bend points onto the edge direction and check if they span the edge.

```python
edge_dir = normalize(CP_xR - CP_xL)
bpl_proj = np.dot(BPL - CP_xL, edge_dir)
bpr_proj = np.dot(BPR - CP_xL, edge_dir)
edge_length = np.linalg.norm(CP_xR - CP_xL)

if 0 <= bpl_proj <= edge_length and 0 <= bpr_proj <= edge_length:
    # Bend points project onto the edge → filter
```

**Pros:**
- Directly checks relationship between bend points and specific edge
- Intuitive for edge-based filtering

**Cons:**
- Only checks one dimension (along the edge)
- Doesn't account for tab's full 2D extent
- Can miss cases where bend is perpendicular but offset from edge

**Verdict:** Too narrow; doesn't consider full tab geometry.

## Why Projection onto Bend Line is Best

1. **Generality:** Works for bend lines in any arbitrary 3D direction
2. **Geometric Correctness:** Directly captures the concept of "bend extent relative to tab extent"
3. **Robustness:** No arbitrary thresholds beyond numerical tolerance
4. **Validation:** Proven to work correctly on transportschuh test case
5. **Intuitive:** Clear geometric meaning - are the bend points within the tab's "shadow" along the bend line?

## Implementation Complexity

**Low complexity:**
- Two simple helper functions (10-15 lines each)
- One dot product per projection
- Min/max over 4 corners per tab

**Performance:**
- O(1) for each edge pair check
- No expensive operations (matrix inversions, etc.)
- Negligible overhead compared to existing bend point calculations

## Recommendation

**Use the projection-based filter** as described in the updated implementation plan. It is:
- Mathematically sound
- Geometrically intuitive
- Validated with real data
- General enough for all cases
- Simple to implement

This solution correctly addresses the user's requirement to check if bend points lie "within the coordinate range" of the tab, interpreted correctly as the tab's extent along the bend line direction.

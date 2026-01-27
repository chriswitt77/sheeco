# Corner Ordering Analysis for Transportschuh

## Question
Does the clockwise or anticlockwise definition of corner points affect the generation of infeasible structures in one_bend?

## Answer: NO

## Evidence

### Corner Ordering is Consistent

Both tabs use **COUNTERCLOCKWISE** ordering when viewed from their respective +normal directions:

**Tab 0:**
- Normal: `[0, 0, -1]` (pointing downward)
- Corners when viewed from above (+Z): A(160,0,0) → B(0,0,0) → C(0,160,0) → D(160,160,0) → A
- Ordering: **COUNTERCLOCKWISE**

**Tab 1:**
- Normal: `[0, -1, 0]` (pointing in -Y direction)
- Corners when viewed from front (-Y): A(0,180,40) → B(160,180,40) → C(160,180,200) → D(0,180,200) → A
- Ordering: **COUNTERCLOCKWISE**

### Edge Definitions Match Corner Ordering

The hard-coded edge definitions in `one_bend()`:
```python
rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]
rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]
```

These correctly follow the counterclockwise corner ordering. The edges form a proper traversal of the rectangle perimeter.

### Opposite Edges Have Consistent Orientation

In a rectangle, opposite edges should have the same relationship to the bend line:

**Tab 0:**
| Edge Pair | Edge 1 | Angle to Bend | Edge 2 | Angle to Bend | Consistent? |
|-----------|--------|---------------|--------|---------------|-------------|
| Opposite 1 | A-B | 0° (parallel) | C-D | 0° (parallel) | ✓ |
| Opposite 2 | B-C | 90° (perp) | D-A | 90° (perp) | ✓ |

**Tab 1:**
| Edge Pair | Edge 1 | Angle to Bend | Edge 2 | Angle to Bend | Consistent? |
|-----------|--------|---------------|--------|---------------|-------------|
| Opposite 1 | A-B | 0° (parallel) | C-D | 0° (parallel) | ✓ |
| Opposite 2 | B-C | 90° (perp) | D-A | 90° (perp) | ✓ |

This proves the corner ordering is geometrically correct.

### Outward Direction Calculation Works Correctly

The outward direction calculation in `one_bend()`:
```python
out_dir = np.cross(edge_vec, plane.orientation)
if np.dot(out_dir, edge_mid - rect_center) < 0:
    out_dir = -out_dir
```

This correctly computes outward-pointing normals for all edges regardless of corner ordering. The cross product automatically adapts to the edge direction and plane normal.

**Tab 0 outward directions:**
- Edge A-B: `[0, -1, 0]` (points toward -Y, away from rectangle center) ✓
- Edge B-C: `[-1, 0, 0]` (points toward -X, away from rectangle center) ✓
- Edge C-D: `[0, 1, 0]` (points toward +Y, away from rectangle center) ✓
- Edge D-A: `[1, 0, 0]` (points toward +X, away from rectangle center) ✓

All outward directions correctly point away from the rectangle center.

## Root Cause of Infeasible Structures

The infeasible structures are generated because `one_bend()` tests **ALL 4 edges** of each tab, including:

1. **Parallel edges (A-B, C-D)**: Angle 0° to bend line → **GOOD for bending**
2. **Perpendicular edges (B-C, D-A)**: Angle 90° to bend line → **BAD for bending**

The perpendicular edges create infeasible geometry because:
- The bend line runs perpendicular to the edge
- Flange points inserted along these edges don't create valid bends
- The resulting geometry cannot be manufactured

### Why Perpendicular Edges Fail

When an edge is perpendicular to the bend line:
- The bend line does not run along the edge
- Instead, it crosses the edge at a point
- Flanges created on this edge don't form a proper bend connection
- The tabs cannot be bent to meet along this line

### Current Behavior

**one_bend() for transportschuh generates:**
- 6 segments total
- 4 use perpendicular edges (B-C or D-A) → **INFEASIBLE**
- 2 use parallel edges (A-B or C-D) → **FEASIBLE**

## Conclusion

**Corner ordering is NOT the problem.**

The problem is a **missing geometric filter** in `one_bend()`:
- Location: `src/hgen_sm/create_segments/bend_strategies.py:265-280`
- Missing check: Edge-to-bend-line angle validation
- Required fix: Filter edges with angle > 75° (perpendicular)

The fix proposed in `TRANSPORTSCHUH_FIX_PLAN.md` is correct and does not need modification based on corner ordering considerations.

## Recommendation

Proceed with implementation of the perpendicular edge filter as specified in the fix plan. Corner ordering is working correctly and does not need any changes.

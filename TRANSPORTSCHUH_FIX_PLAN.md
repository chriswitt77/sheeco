# Transportschuh Root Cause Analysis & Fix Plan

## Executive Summary

The transportschuh input generates 7 solutions where only 3 are feasible (parts 2, 5, 7). Additionally, it generates only 1 two-bend solution despite the perpendicular geometry that should enable multiple two-bend configurations.

**Root causes identified:**
1. **one_bend**: Missing filter for edges perpendicular to bend line (generates 4 infeasible segments)
2. **two_bends Approach 1**: Overly restrictive direction check that filters out all valid perpendicular edge combinations

## Problem 1: one_bend Generates Infeasible Segments

### Root Cause

**Location:** `src/hgen_sm/create_segments/bend_strategies.py:265-280`

The `one_bend()` function tries all edge pair combinations (8×8 = 64) but **does not check if an edge is perpendicular to the bend line**.

When an edge is perpendicular to the bend line (angle ≈ 90°), the flange cannot be properly formed because:
- The bend line runs perpendicular to the edge
- Flange points inserted along this edge don't create a valid bend
- The resulting geometry is infeasible for manufacturing

### Evidence from Debug Analysis

**Transportschuh bend line:**
- Position: `y=180, z=0`
- Direction: `[-1, 0, 0]` (parallel to negative X-axis)

**Tab 0 edges:**
- Edge A-B: 0.0° angle (parallel) ✓ Good
- Edge B-C: 90.0° angle (perpendicular) ✗ Bad
- Edge C-D: 0.0° angle (parallel) ✓ Good
- Edge D-A: 90.0° angle (perpendicular) ✗ Bad

**Tab 1 edges:**
- Edge A-B: 0.0° angle (parallel) ✓ Good
- Edge B-C: 90.0° angle (perpendicular) ✗ Bad
- Edge C-D: 0.0° angle (parallel) ✓ Good
- Edge D-A: 90.0° angle (perpendicular) ✗ Bad

**Generated infeasible segments:**
- Segment 1: Tab 0 edge B-C (90° perpendicular)
- Segment 3: Tab 1 edge B-C (90° perpendicular)
- Segment 4: Tab 1 edge D-A (90° perpendicular)
- Segment 6: Tab 0 edge D-A (90° perpendicular)

### Current Code (Lines 265-280)

```python
for pair_x in rect_x_edges:
    CP_xL, CP_xR = get_corners(pair_x, tab_x)

    for pair_z in rect_z_edges:
        CP_zL, CP_zR = get_corners(pair_z, tab_z)

        # Project corners onto bend line
        BPL = create_bending_point(CP_xL, CP_zL, bend)
        BPR = create_bending_point(CP_xR, CP_zR, bend)

        # NO CHECK: Is edge perpendicular to bend line?

        # Continue with flange creation...
```

### Proposed Fix

Add a projection-based filter that checks if an edge is perpendicular to the bend line AND if the bend points lie within the tab's projected range along the bend line.

**Key Insight:** The bend line can run in any arbitrary 3D direction, not just along principal axes. We need to project both the tab corners and bend points onto the bend line and check if the bend points fall within the tab's projected range.

**Logic:**
- If an edge is perpendicular (>75°) AND both bend points project within the tab's range on the bend line → FILTER (infeasible)
- If an edge is perpendicular BUT bend points project outside the tab's range → ALLOW (may be feasible)
- If an edge is parallel (<75°) → ALLOW (always feasible)

**Projection Method:**
For a line defined as `L(t) = position + t * direction`, any point P projects to parameter:
```
t = dot(P - position, direction)
```

This gives a scalar representing position along the line.

**Implementation:**

```python
def project_onto_bend_line(point, bend):
    """Project a point onto the bend line and return parameter t."""
    vec_to_point = point - bend.position
    t = np.dot(vec_to_point, bend.orientation)
    return t

def get_tab_projection_range(tab, bend):
    """Get the range [t_min, t_max] of tab corners projected onto bend line."""
    corners = [tab.points[k] for k in ['A', 'B', 'C', 'D']]
    t_values = [project_onto_bend_line(corner, bend) for corner in corners]
    return min(t_values), max(t_values)

# Main loop:
for pair_x in rect_x_edges:
    CP_xL_id, CP_xR_id = pair_x
    CP_xL = tab_x.points[CP_xL_id]
    CP_xR = tab_x.points[CP_xR_id]

    for pair_z in rect_z_edges:
        CP_zL_id, CP_zR_id = pair_z
        CP_zL = tab_z.points[CP_zL_id]
        CP_zR = tab_z.points[CP_zR_id]

        # Calculate bend points (needed for projection check)
        BPL = create_bending_point(CP_xL, CP_zL, bend)
        BPR = create_bending_point(CP_xR, CP_zR, bend)

        # Check tab_x edge angle to bend line
        edge_x_vec = CP_xR - CP_xL
        edge_x_len = np.linalg.norm(edge_x_vec)
        if edge_x_len < 1e-9:
            continue
        edge_x_dir = edge_x_vec / edge_x_len

        dot_x = abs(np.dot(edge_x_dir, bend.orientation))
        angle_x_deg = np.degrees(np.arccos(np.clip(dot_x, 0, 1)))

        # If edge is perpendicular, check projection onto bend line
        if angle_x_deg > 75:
            # Get tab_x projection range
            t_min_x, t_max_x = get_tab_projection_range(tab_x, bend)

            # Project bend points onto bend line
            t_bpl = project_onto_bend_line(BPL, bend)
            t_bpr = project_onto_bend_line(BPR, bend)

            # Check if both within range (with tolerance)
            tolerance = 1e-3
            bpl_in_range = (t_min_x - tolerance) <= t_bpl <= (t_max_x + tolerance)
            bpr_in_range = (t_min_x - tolerance) <= t_bpr <= (t_max_x + tolerance)

            if bpl_in_range and bpr_in_range:
                continue  # Filter this edge combination

        # Check tab_z edge angle to bend line
        edge_z_vec = CP_zR - CP_zL
        edge_z_len = np.linalg.norm(edge_z_vec)
        if edge_z_len < 1e-9:
            continue
        edge_z_dir = edge_z_vec / edge_z_len

        dot_z = abs(np.dot(edge_z_dir, bend.orientation))
        angle_z_deg = np.degrees(np.arccos(np.clip(dot_z, 0, 1)))

        # If edge is perpendicular, check projection onto bend line
        if angle_z_deg > 75:
            # Get tab_z projection range
            t_min_z, t_max_z = get_tab_projection_range(tab_z, bend)

            # Project bend points (already calculated above)
            t_bpl = project_onto_bend_line(BPL, bend)
            t_bpr = project_onto_bend_line(BPR, bend)

            # Check if both within range
            tolerance = 1e-3
            bpl_in_range = (t_min_z - tolerance) <= t_bpl <= (t_max_z + tolerance)
            bpr_in_range = (t_min_z - tolerance) <= t_bpr <= (t_max_z + tolerance)

            if bpl_in_range and bpr_in_range:
                continue  # Filter this edge combination

        # If we reach here, edge combination is allowed
        # Continue with existing flange creation logic...
        # ... rest of existing code
```

**Implementation location:** After line 265 in `bend_strategies.py`

**Helper functions location:** Add `project_onto_bend_line` and `get_tab_projection_range` as utility functions, either:
- In `bend_strategies.py` as local functions (recommended)
- In `geometry_helpers.py` if they might be reused elsewhere

**Parameters:**
- Angle threshold: 75° (configurable in `config/config.yaml` under `filter.max_edge_to_bend_angle`)
- Projection tolerance: 1e-3 (small tolerance for numerical precision)

**Why this works:**
- Works for bend lines in any arbitrary 3D direction (not just principal axes)
- Correctly identifies when a bend is "local" to the tab (projections overlap)
- Perpendicular edges are problematic only when the connection is local
- If bend points extend beyond the tab's projected range, the connection may still be valid

**Validation:**
Tested with transportschuh:
- Bend line direction: `[-1, 0, 0]` (along X-axis)
- Tab 0 projection range: t ∈ [-160, 0]
- Perpendicular edge B-C: bend points project to t ∈ [-152.5, 0] → WITHIN range → FILTER ✓
- Perpendicular edge D-A: bend points project to t ∈ [-160, -7.5] → WITHIN range → FILTER ✓
- Result: All 8 perpendicular edge combinations correctly filtered

### Expected Outcome After Fix

**Before fix:** 6 segments generated (4 infeasible, 2 feasible)
**After fix:** 2 segments generated (2 feasible)

Segments 1, 3, 4, 6 will be filtered out during generation, not passed to assembly stage.

---

## Problem 2: two_bends Approach 1 Filters All Perpendicular Solutions

### Root Cause

**Location:** `src/hgen_sm/create_segments/bend_strategies.py:854-1100`

Approach 1 is designed for perpendicular tabs and creates rectangular intermediate tabs. However, its direction check is too strict and filters out geometrically valid configurations.

**The problematic check (around line 950):**
```python
connection_vec = BPzL - BPxL
x_points_toward_z = np.dot(out_dir_x, connection_vec) > 0
z_points_toward_x = np.dot(out_dir_z, -connection_vec) > 0

if not (x_points_toward_z and z_points_toward_x):
    continue  # Filter out
```

This check requires BOTH outward directions to point toward each other. However, for perpendicular tabs with edges in certain orientations, this condition is **geometrically impossible**.

### Evidence from Debug Analysis

For transportschuh (perpendicular tabs at 90°), Approach 1 tests 16 edge combinations:
- 12 are perpendicular edge pairs (should work)
- 4 are parallel edge pairs (correctly filtered)

**Result:** ALL 12 perpendicular combinations are filtered out by the direction check.

**Example failure (Edge B-C × A-B):**
```
Edge angle: 90.0° (perpendicular: True)
Edge x direction: [ 0.  1.  0.]
Edge z direction: [ 1.  0.  0.]
Out dir x: [-1.  0.  0.]
Out dir z: [ 0.  0. -1.]
Connection vec: [ 10. 180.  30.]
x->z dot: -10.000 (>0: False)  ← FAILS
z->x dot: 30.000 (>0: True)
[FILTERED] Direction check failed
```

The outward direction for tab_x is `[-1, 0, 0]`, pointing in negative X direction.
The connection vector is `[10, 180, 30]`, pointing in positive X direction.
Their dot product is negative, so the check fails.

However, this is a **valid configuration** - the tabs are perpendicular, and the intermediate tab should connect them.

### Analysis of Direction Check Logic

The direction check assumes that:
1. Outward directions from both edges should point toward each other
2. This is checked by: `dot(out_dir_x, connection_vec) > 0` AND `dot(out_dir_z, -connection_vec) > 0`

**Why this fails for perpendicular tabs:**

For perpendicular tabs, when edges are selected on different faces:
- The outward direction from one edge may be perpendicular to the connection vector
- Or the outward direction may point away from the connection
- The direction check doesn't account for the intermediate tab rotating the connection

**What should be checked instead:**
1. Are the edges perpendicular? (Already checked: `dot_edges < 0.1`)
2. Are the outward directions not directly opposing? (Don't point 180° away from each other)
3. Is there geometric space for an intermediate tab? (Check separation distance)

### Proposed Fix - Option 1: Relax Direction Check

```python
# Current strict check (line ~950):
if not (x_points_toward_z and z_points_toward_x):
    continue

# Proposed relaxed check:
# For perpendicular tabs, allow cases where at least ONE direction points toward the other
# or where directions are not opposing (dot product with connection not strongly negative)

x_dot = np.dot(out_dir_x, connection_vec)
z_dot = np.dot(out_dir_z, -connection_vec)

# Check if directions are strongly opposing (both pointing away)
x_opposing = x_dot < -0.5  # Strong negative dot product
z_opposing = z_dot < -0.5

# Filter only if BOTH directions strongly oppose
if x_opposing and z_opposing:
    continue

# Allow if at least one direction is favorable or neutral
# This permits perpendicular configurations where intermediate tab bridges the gap
```

### Proposed Fix - Option 2: Replace with Geometric Feasibility Check

Instead of checking direction vectors, check geometric feasibility:

```python
# Remove direction check entirely, replace with:

# 1. Check minimum separation (already exists)
separation = np.linalg.norm(BPxL - BPzL)
if separation < min_flange_length * 2:
    continue

# 2. Check that intermediate tab has positive dimensions
# (calculated later in the code, could be moved here as early filter)

# 3. Check that bend angles are within manufacturing limits
# (already checked in filter stage, but could be early filter)
```

### Proposed Fix - Option 3: Geometric Direction Compatibility (Recommended)

Check that the edge pair configuration allows for an intermediate tab:

```python
# After verifying edges are perpendicular (dot_edges < 0.1):

# Calculate the span between flange edges
BPxL_to_BPzL = BPzL - BPxL
BPxR_to_BPzR = BPzR - BPxR

# Check if the flanges can be connected by a rectangular intermediate tab
# The outward directions should not be nearly antiparallel
out_dirs_dot = np.dot(out_dir_x, out_dir_z)

# Filter if outward directions are nearly opposite (≈ -1)
# This indicates tabs facing directly away from each other
if out_dirs_dot < -0.8:
    continue

# Check if connection vectors have reasonable length
conn_length = np.linalg.norm(BPxL_to_BPzL)
if conn_length < min_flange_length * 0.5:  # Too close
    continue
if conn_length > 1000:  # Too far (arbitrary large threshold)
    continue

# Remove the strict bidirectional check
# The intermediate tab will bridge the gap regardless of individual directions
```

**Recommendation:** Use Option 3 (Geometric Direction Compatibility)

**Rationale:**
- More intuitive: checks if tabs are facing away vs. toward each other
- Less restrictive: allows perpendicular configurations
- Still filters truly infeasible cases (antiparallel outward directions)
- Maintains geometric validity

### Expected Outcome After Fix

**Before fix:** 0 solutions from Approach 1 for transportschuh
**After fix:** Multiple solutions from Approach 1 (4-8 valid perpendicular combinations)

This will increase the total two-bend solution count from 1 to 5-9.

---

## Implementation Plan

### Step 1: Fix one_bend Perpendicular Edge Filter

**File:** `src/hgen_sm/create_segments/bend_strategies.py`
**Lines:** 265-280 (add filter logic)

1. Add edge-to-bend-line angle calculation for both edges
2. Filter edges with angle > 75° (perpendicular)
3. Make threshold configurable in `config/config.yaml`

**Configuration:**
```yaml
filter:
  max_edge_to_bend_angle: 75  # degrees, filter edges more perpendicular than this
```

### Step 2: Fix two_bends Approach 1 Direction Check

**File:** `src/hgen_sm/create_segments/bend_strategies.py`
**Lines:** 950-960 (replace direction check)

1. Remove strict bidirectional check: `if not (x_points_toward_z and z_points_toward_x)`
2. Add geometric compatibility check: verify outward directions are not antiparallel
3. Keep edge perpendicularity check: `dot_edges < 0.1`

**Implementation:** Use Option 3 (Geometric Direction Compatibility)

### Step 3: Add Configuration Parameter

**File:** `config/config.yaml`

```yaml
filter:
  max_edge_to_bend_angle: 75  # Maximum angle (degrees) between edge and bend line

design_exploration:
  two_bend_antiparallel_threshold: -0.8  # Filter if out_dir dot product < this value
```

### Step 4: Create Validation Tests

**File:** `tests/test_transportschuh_fixes.py` (new)

```python
def test_one_bend_filters_perpendicular_edges():
    """Verify one_bend filters edges perpendicular to bend line."""
    part = initialize_objects(transportschuh)
    segment = create_segment(part, ['0', '1'])
    segments = one_bend(segment, filter_cfg)

    # Should generate only 2 segments (down from 6)
    assert len(segments) == 2

    # Check that all generated segments use parallel edges
    for seg in segments:
        # Verify edge angles are < 75° for both tabs
        # (Implementation details...)
        pass

def test_two_bends_approach1_generates_perpendicular():
    """Verify Approach 1 generates solutions for perpendicular tabs."""
    part = initialize_objects(transportschuh)
    segment = create_segment(part, ['0', '1'])
    segments = two_bends(segment, segment_cfg, filter_cfg)

    # Filter to only Approach 1 solutions
    approach1_segments = [s for s in segments if has_rectangular_intermediate_tab(s)]

    # Should generate multiple Approach 1 solutions (not 0)
    assert len(approach1_segments) > 0

def test_transportschuh_total_feasible_count():
    """Integration test: verify transportschuh generates only feasible parts."""
    part = initialize_objects(transportschuh)
    solutions = run_full_pipeline(part, cfg)

    # All solutions should be feasible
    for solution in solutions:
        assert is_geometrically_feasible(solution)

    # Should generate 3-5 solutions (down from 7, up in two-bend)
    assert 3 <= len(solutions) <= 7
```

### Step 5: Update Debug Scripts

Keep the debug scripts for future reference:
- `debug_one_bend_edge_orientation.py` - Documents the perpendicular edge issue
- `debug_one_bend_detailed.py` - Shows which edges are used per segment
- `debug_two_bends_approach1.py` - Documents Approach 1 filtering issue
- `debug_two_bends_detailed.py` - Shows detailed direction check failures

Add comments at the top explaining they document the bug found and fixed.

---

## Expected Results After Implementation

### Current Results (Broken)
- **Total solutions:** 7 (4 infeasible, 3 feasible)
- **one_bend segments:** 6 (4 infeasible, 2 feasible)
- **two_bend solutions:** 1 (from Approach 2 only)
- **Infeasible parts:** 1, 3, 4, 6 (perpendicular edges)

### Expected Results (Fixed)
- **Total solutions:** 4-6 (all feasible)
- **one_bend segments:** 2 (all feasible)
- **two_bend solutions:** 2-4 (from both Approach 1 and 2)
- **Infeasible parts:** None

### Breakdown by Type

**one_bend (2 solutions):**
- Segment with parallel edges on both tabs (current Segment 2)
- Possibly one more with different edge combination

**two_bends (2-4 solutions):**
- 1-2 from Approach 1 (perpendicular, rectangular intermediate tab)
- 1-2 from Approach 2 (edge-based, triangular intermediate tab)

---

## Implementation Priority

1. **High Priority - Step 1:** Fix one_bend perpendicular filter
   - Directly eliminates 4 infeasible solutions
   - Simple, low-risk change
   - Clear geometric rationale

2. **High Priority - Step 2:** Fix two_bends Approach 1 direction check
   - Enables more design exploration
   - Fulfills expectation of perpendicular two-bend generation
   - Moderate complexity change

3. **Medium Priority - Step 3:** Add configuration parameters
   - Allows users to tune filter thresholds
   - Enables experimentation

4. **Medium Priority - Step 4:** Create validation tests
   - Prevents regression
   - Documents expected behavior

5. **Low Priority - Step 5:** Update debug scripts
   - Documentation only
   - Helps future debugging

---

## Risk Assessment

### Risk: Over-filtering in one_bend

**Risk:** 75° threshold may filter out some valid angled edges (60-75°)

**Mitigation:**
- Make threshold configurable
- Default to 75° (conservative)
- Users can adjust if needed for specific geometries

### Risk: Under-filtering in two_bends Approach 1

**Risk:** Relaxed direction check may allow some infeasible configurations

**Mitigation:**
- Keep separation distance check
- Later filter stages (collision detection, angle validation) will catch issues
- Test thoroughly with known geometries

### Risk: Breaking existing functionality

**Risk:** Changes may affect other input geometries that currently work

**Mitigation:**
- Run full test suite after changes
- Test with multiple input geometries: transportschuh, barda_example_one, same_plane, zylinderhalter
- Keep debug scripts to verify behavior

---

## Testing Strategy

### Unit Tests
1. Test one_bend with known perpendicular edges (should filter)
2. Test one_bend with known parallel edges (should pass)
3. Test two_bends Approach 1 with perpendicular tabs (should generate)
4. Test two_bends Approach 1 with antiparallel directions (should filter)

### Integration Tests
1. Run transportschuh through full pipeline (expect 4-6 feasible solutions)
2. Run other inputs to verify no regression
3. Verify all generated solutions are geometrically feasible

### Manual Validation
1. Visualize generated solutions in PyVista
2. Export to FeatureScript and check in Onshape
3. Verify bend angles and flange dimensions are manufacturable

---

## Open Questions

1. **Threshold tuning:** Is 75° the right threshold for perpendicular edge filtering?
   - Could test with 70°, 80° to see impact
   - May depend on material properties and manufacturing constraints

2. **Approach 1 vs Approach 2 priority:** Should `prioritize_perpendicular_bends` still limit generation?
   - Current plan: generate both, let user choose
   - Alternative: truly prioritize by sorting/ranking in assembly

3. **Direction check alternatives:** Are there other geometric checks that should be added?
   - Minimum tab dimensions
   - Maximum connection length
   - Bend line clearance

These can be addressed during implementation and testing.

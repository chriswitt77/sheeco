# Zero-Bend Segment Implementation Plan

## Overview
Implement a zero-bend connection strategy for tabs that lie in the same plane. This should be the ONLY strategy used when tabs are coplanar, connecting edges directly without any bending.

---

## Design Decisions

### Connection Geometry Approach
**CHOSEN: Both tabs have coplanar flange points**
- Tab X gets flange points (FPX_0L, FPX_0R) at the connection edge
- Tab Z gets flange points (FPZ_0L, FPZ_0R) at the connection edge
- All points remain in the same plane (no Z-offset = zero bend)
- Compatible with existing merge logic and edge usage filter
- Naming scheme follows existing pattern

**Why not direct connection without flanges?**
- Merge logic expects connection points (not just corners)
- Edge usage filter tracks bend/flange points
- Would require significant refactoring

---

## Implementation Checklist

### Phase 1: Core Detection and Structure
- [ ] **1.1** Create `zero_bends()` function in `src/hgen_sm/create_segments/bend_strategies.py`
- [ ] **1.2** Implement coplanarity detection
  - [ ] Check if tab planes are identical (same normal + same distance from origin)
  - [ ] Tolerance for floating point comparison (~1e-6)
- [ ] **1.3** Define function signature matching `one_bend()` and `two_bends()`
  - Input: segment (with tab_x and tab_z)
  - Output: list of valid segment combinations

### Phase 2: Edge Pair Selection
- [ ] **2.1** Extract all edges from both tabs (AB, BC, CD, DA for each)
- [ ] **2.2** Find valid edge pairs that can connect
  - [ ] Check edge parallelism (or collinearity)
  - [ ] Check edge proximity (reasonable connection distance)
  - [ ] Consider edge orientation (facing each other vs. parallel offset)
- [ ] **2.3** For each valid edge pair, determine connection geometry

### Phase 3: Flange Point Generation
- [ ] **3.1** Calculate flange points for tab_x at connection edge
  - [ ] Use edge endpoints or intermediate positions
  - [ ] Naming: `FPX_0L`, `FPX_0R` (following existing pattern)
  - [ ] Points stay in the same plane as tab
- [ ] **3.2** Calculate flange points for tab_z at connection edge
  - [ ] Mirror/corresponding positions to tab_x flanges
  - [ ] Naming: `FPZ_0L`, `FPZ_0R`
  - [ ] Points stay in the same plane
- [ ] **3.3** Determine if bend points are needed
  - [ ] Option A: No bend points (flanges connect directly)
  - [ ] Option B: Add coincident bend/flange points for consistency
  - [ ] **Decision needed**: Check if merge logic requires BPs

### Phase 4: Geometry Validation
- [ ] **4.1** Check that connection doesn't cross tab boundaries
  - [ ] Use similar logic to `one_bend()` and `two_bends()`
  - [ ] Check if connection line intersects any tab edges
- [ ] **4.2** Check for minimum/maximum connection distances
  - [ ] Prevent connections that are too close (unstable)
  - [ ] Prevent connections that are too far (unrealistic)
- [ ] **4.3** Validate that flanges are within design rules
  - [ ] Check minimum flange width from `config/design_rules.py`

### Phase 5: Segment Construction
- [ ] **5.1** Create segment object with modified tab geometries
  - [ ] Copy original tabs
  - [ ] Insert flange (and bend?) points into perimeter
  - [ ] Maintain ordered point dictionary
- [ ] **5.2** Add segment to results list
- [ ] **5.3** Return all valid zero-bend segments

### Phase 6: Integration
- [ ] **6.1** Modify `create_segments()` in `create_segments/__init__.py`
  - [ ] Add coplanarity check at the beginning
  - [ ] If coplanar: ONLY call `zero_bends()`, skip one_bend and two_bends
  - [ ] If not coplanar: use existing logic (one_bend, two_bends)
- [ ] **6.2** Update configuration if needed
  - [ ] Add `zero_bend` option to `design_exploration` in config.yaml?
  - [ ] Or always enabled for coplanar tabs?

### Phase 7: Compatibility Verification
- [ ] **7.1** Test with merge logic
  - [ ] Verify `merge_multiple_tabs()` handles zero-bend flanges
  - [ ] Verify edge usage filter works correctly
  - [ ] Check that coplanar flanges are properly detected on edges
- [ ] **7.2** Test with existing filters
  - [ ] Collision filter
  - [ ] Crossing filter
  - [ ] Flange width filter
- [ ] **7.3** Test with export functionality
  - [ ] Verify naming scheme compatibility
  - [ ] Check that zero-bend segments export correctly
- [ ] **7.4** Test with plotting
  - [ ] Verify visualization of zero-bend connections
  - [ ] Check that coplanar flanges render correctly

### Phase 8: Testing
- [ ] **8.1** Create test cases with coplanar tabs
  - [ ] Two parallel rectangles in XY plane
  - [ ] Two parallel rectangles in XZ plane
  - [ ] Two parallel rectangles in YZ plane
  - [ ] Offset parallel rectangles (should still connect)
- [ ] **8.2** Test with existing configurations
  - [ ] Verify non-coplanar tabs still use one_bend/two_bends
  - [ ] Check that existing solutions are not broken
- [ ] **8.3** Test edge cases
  - [ ] Tabs that are almost coplanar (within tolerance)
  - [ ] Tabs with multiple valid edge pairs
  - [ ] Tabs where no valid connection exists

---

## Implementation Details

### File Structure
```
src/hgen_sm/create_segments/
├── __init__.py              # Modify: add coplanarity check
├── bend_strategies.py       # Modify: add zero_bends() function
└── geometry_utils.py        # Possibly add: coplanarity detection utils
```

### Key Functions to Add

#### 1. `is_coplanar(plane_x, plane_z, tolerance=1e-6) -> bool`
```python
def is_coplanar(plane_x, plane_z, tolerance=1e-6) -> bool:
    """
    Check if two planes are coplanar (same plane, not just parallel).

    Returns:
        True if planes are identical within tolerance
    """
    # Check if normals are parallel (or anti-parallel)
    # Check if distance from origin is the same
    # Return True only if both conditions met
```

#### 2. `zero_bends(segment, filter_cfg) -> List[Part]`
```python
def zero_bends(segment, filter_cfg) -> List[Part]:
    """
    Generate zero-bend connections for coplanar tabs.

    Strategy:
    - Find edges that can connect (parallel, facing, reasonable distance)
    - Create flange points on both tabs at connection edges
    - All points remain in the same plane (no bending)
    - Filter out connections that cross tab boundaries

    Returns:
        List of valid segment combinations
    """
    # 1. Extract tab geometries and planes
    # 2. Find valid edge pairs
    # 3. For each valid pair:
    #    a. Calculate flange point positions
    #    b. Check for crossing
    #    c. Create segment with modified tabs
    # 4. Return list of segments
```

#### 3. `find_connectable_edge_pairs(tab_x, tab_z, plane) -> List[Tuple]`
```python
def find_connectable_edge_pairs(tab_x, tab_z, plane) -> List[Tuple]:
    """
    Find pairs of edges from tab_x and tab_z that can connect.

    Criteria:
    - Edges should be roughly parallel or aligned
    - Edges should be at reasonable distance
    - Connection should not require leaving the plane

    Returns:
        List of (edge_x_name, edge_z_name, connection_geometry) tuples
    """
```

### Naming Convention
Following existing pattern:
- **Flange Points**: `FP{tab_id}_{other_tab_id}{L/R}`
  - Example: `FPX_0L`, `FPX_0R` for tab_x connecting to tab_0
- **Bend Points** (if needed): `BP{tab_id}_{other_tab_id}{L/R}`
  - Example: `BPX_0L`, `BPX_0R`
  - Question: Are bend points needed if there's no actual bend?

### Integration Logic
```python
# In create_segments/__init__.py

def create_segments(segment, segment_cfg, filter_cfg):
    tab_x = segment.tabs['tab_x']
    tab_z = segment.tabs['tab_z']

    plane_x = calculate_plane(tab_x)
    plane_z = calculate_plane(tab_z)

    # NEW: Check if tabs are coplanar
    if is_coplanar(plane_x, plane_z):
        # ONLY use zero-bend for coplanar tabs
        return zero_bends(segment, filter_cfg)

    # Existing logic for non-coplanar tabs
    results = []
    if segment_cfg.get('single_bend'):
        results.extend(one_bend(segment, filter_cfg))
    if segment_cfg.get('double_bend'):
        results.extend(two_bends(segment, filter_cfg))
    return results
```

---

## Potential Issues and Solutions

### Issue 1: Merge Logic Expects Bend Points
**Problem**: Current merge may expect both FP and BP points
**Solution**:
- Option A: Include BP points that coincide with FP (zero offset)
- Option B: Modify merge to handle FP-only connections
- **Recommendation**: Option A for compatibility

### Issue 2: Edge Usage Filter Detection
**Problem**: Zero-bend flanges need to be detected on correct edge
**Solution**:
- `detect_edge()` already handles coplanar points
- Flange points will naturally lie on tab edges
- Should work without modification

### Issue 3: Export/Plotting Compatibility
**Problem**: Visualization might expect bend angles
**Solution**:
- Zero-bend = 180° angle (flat continuation)
- Export should handle coplanar points naturally
- May need minor adjustments to plotting

### Issue 4: Multiple Valid Edge Pairs
**Problem**: Two coplanar rectangles might have multiple ways to connect
**Solution**:
- Generate all valid options (like current strategies)
- Let filters and combination logic select best ones
- User gets multiple solution options

### Issue 5: Crossing Detection
**Problem**: Need to check if connection crosses tab boundaries
**Solution**:
- Reuse existing crossing check logic from one_bend/two_bends
- Check if connection line segment intersects any tab edge
- Filter out invalid connections

---

## Testing Strategy

### Unit Tests
1. Coplanarity detection with various plane configurations
2. Edge pair finding for different tab orientations
3. Flange point generation at correct positions
4. Crossing detection for coplanar connections

### Integration Tests
1. Full segment generation for coplanar tab pairs
2. Merge logic with zero-bend segments
3. Edge usage filter with coplanar flanges
4. Complete solution generation with mix of zero/one/two-bend

### Test Cases
```python
# Test case 1: Parallel rectangles in XY plane
coplanar_xy = [
    {'pointA': [0, 0, 0], 'pointB': [50, 0, 0], 'pointC': [50, 50, 0]},
    {'pointA': [70, 0, 0], 'pointB': [120, 0, 0], 'pointC': [120, 50, 0]}
]

# Test case 2: Parallel rectangles in XZ plane
coplanar_xz = [
    {'pointA': [0, 0, 0], 'pointB': [50, 0, 0], 'pointC': [50, 0, 50]},
    {'pointA': [70, 0, 0], 'pointB': [120, 0, 0], 'pointC': [120, 0, 50]}
]

# Test case 3: Offset parallel (should connect with zero-bend)
coplanar_offset = [
    {'pointA': [0, 0, 0], 'pointB': [50, 0, 0], 'pointC': [50, 50, 0]},
    {'pointA': [30, 70, 0], 'pointB': [80, 70, 0], 'pointC': [80, 120, 0]}
]

# Test case 4: Non-coplanar (should NOT use zero-bend)
non_coplanar = [
    {'pointA': [0, 0, 0], 'pointB': [50, 0, 0], 'pointC': [50, 50, 0]},
    {'pointA': [70, 0, 10], 'pointB': [120, 0, 10], 'pointC': [120, 50, 10]}
]
```

---

## Questions to Resolve Before Implementation

1. **Bend Points**: Should zero-bend segments include bend points (BP) or only flange points (FP)?
   - Recommendation: Include coincident BP for merge compatibility

2. **Flange Width**: For zero-bend, what should the "flange width" be?
   - Could be zero (direct edge connection)
   - Could be minimal (small extension)
   - Recommendation: Use min_flange_length from design_rules.py

3. **Configuration**: Should zero-bend be optional or always enabled?
   - Recommendation: Always enabled for coplanar tabs (makes physical sense)

4. **Naming**: Should the intermediate tab ID in naming be "0" or something else?
   - Current: `FP1_2L` means tab 1 connecting to tab 2
   - Zero-bend: `FP1_2L` works the same way
   - No change needed

5. **Edge Selection Priority**: If multiple edge pairs can connect, which to prefer?
   - Shortest distance?
   - Largest overlap?
   - Generate all options?
   - Recommendation: Generate all valid options

---

## Success Criteria

- [ ] Coplanar tabs generate zero-bend segments exclusively
- [ ] Non-coplanar tabs continue using one_bend/two_bends
- [ ] Zero-bend segments merge correctly with edge usage filter
- [ ] No crossing connections are generated
- [ ] Export and plotting work without errors
- [ ] All existing test cases still pass
- [ ] New test cases with coplanar tabs pass

---

## Estimated Complexity

- **Core Implementation**: Medium (new function, coplanarity check)
- **Integration**: Low (minimal changes to existing flow)
- **Testing**: Medium (need comprehensive test cases)
- **Risk**: Low (isolated to new code path for coplanar tabs)

**Total Effort**: ~2-4 hours of implementation + testing

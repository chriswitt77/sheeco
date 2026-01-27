# Transportschuh Issue Analysis & Implementation Plan

## Problem Summary

When running transportschuh input, the system generates 7 solutions but only 3 are feasible. Additionally, it doesn't generate all expected 90-degree two-bend solutions.

### Observed Issues

1. **Infeasible solutions (parts 1, 3, 4, 6)**: Incomplete connections where bend points don't span the full edge width
2. **Limited two-bend solutions**: Only 1 two-bend solution (part 7) generated despite perpendicular geometry that should allow more

## Root Cause Analysis

### Issue 1: one_bend Partial Edge Coverage

**Location:** `src/hgen_sm/create_segments/bend_strategies.py` lines 265-280

**Problem:**
```python
for pair_x in rect_x_edges:
    CP_xL, CP_xR = get corner pair from tab_x
    for pair_z in rect_z_edges:
        CP_zL, CP_zR = get corner pair from tab_z

        # Project corners onto bend line
        BPL = create_bending_point(CP_xL, CP_zL, bend)
        BPR = create_bending_point(CP_xR, CP_zR, bend)
```

The algorithm tries ALL combinations of edge pairs (8×8 = 64 combinations) and projects them onto the plane intersection line. Different corner combinations produce bend points (BPL, BPR) at different positions along the bend line.

**Example from transportschuh:**
- Tab 0: x-range [0, 160]
- Tab 1: x-range [0, 160]
- Bend line: parallel to X-axis at y=180, z=0

**Generated segments:**
1. Segment 1: Bend spans x=[0, 32] (20% coverage) ❌
2. Segment 2: Bend spans x=[0, 160] (100% coverage) ✓
3. Segment 3: Bend spans x=[32, 160] (80% coverage) ❌
4. Segment 4: Bend spans x=[0, 128] (80% coverage) ❌
5. Segment 5: Bend spans x=[32, 128] (60% coverage) ❌ *
6. Segment 6: Bend spans x=[128, 160] (20% coverage) ❌

\* Segment 5 is marked "good" because BOTH tabs have matching span (both 60%), but the connection is still incomplete

**Why partial coverage is bad:**
- The bend line doesn't span the full width of the rectangles
- The flanges create an incomplete connection
- One or both tabs are missing edge points where the bend should continue
- Results in disconnected or weakly connected geometry

### Issue 2: Limited two_bends Generation

**Location:** `src/hgen_sm/create_segments/bend_strategies.py` lines 854, 1200

**Problem:**
```python
prioritize_perpendicular = segment_cfg.get('prioritize_perpendicular_bends', True)

# Approach 1: Perpendicular connection
for pair_x in rect_x_edges:
    for pair_z in rect_z_edges:
        # Generate perpendicular two-bend solutions
        if successful:
            successful_edge_pairs.add((pair_x, pair_z))

# Approach 2: Edge-based connection
for pair_x in rect_x_edges:
    for pair_z in rect_z_edges:
        # SKIP if prioritize_perpendicular and this edge pair already succeeded in Approach 1
        if prioritize_perpendicular and (pair_x, pair_z) in successful_edge_pairs:
            continue  # ← THIS LIMITS GENERATION
```

When `prioritize_perpendicular_bends=True`:
- Approach 1 generates perpendicular two-bend solutions for perpendicular tabs (like transportschuh)
- Approach 2 is then SKIPPED for edge pairs that already have Approach 1 solutions
- This prevents generation of alternative two-bend geometries

**Impact:**
- Only 1 two-bend solution generated (Segment 7) out of potentially many
- User expects more 90-degree two-bend solutions with different intermediate tab positions
- The "prioritize" setting is too restrictive - it eliminates alternatives rather than just prioritizing

## Implementation Plan

### Part 1: Add Minimum Edge Coverage Filter to one_bend

**Goal:** Filter out one_bend segments where bend points don't span a sufficient portion of the edge

**Location:** `src/hgen_sm/create_segments/bend_strategies.py` after line 283

**Implementation:**

1. **Calculate edge coverage percentage:**
   ```python
   # After calculating BPL and BPR (line 279)
   bend_span = np.linalg.norm(BPR - BPL)

   # Calculate edge lengths for both tabs
   edge_x_length = np.linalg.norm(CP_xR - CP_xL)
   edge_z_length = np.linalg.norm(CP_zR - CP_zL)

   # Calculate coverage as percentage of edge length
   coverage_x = (bend_span / edge_x_length) * 100 if edge_x_length > 1e-9 else 0
   coverage_z = (bend_span / edge_z_length) * 100 if edge_z_length > 1e-9 else 0
   ```

2. **Add minimum coverage filter:**
   ```python
   # Configuration: minimum edge coverage percentage
   MIN_EDGE_COVERAGE_PCT = 85  # Require 85% edge coverage minimum

   # Filter: Reject if bend doesn't span sufficient edge
   if coverage_x < MIN_EDGE_COVERAGE_PCT or coverage_z < MIN_EDGE_COVERAGE_PCT:
       continue
   ```

3. **Add configuration parameter:**
   - Add `min_edge_coverage_percent` to `config/config.yaml` under `design_exploration`
   - Default: 85% (allows some flexibility while filtering out clearly incomplete connections)

**Rationale:**
- Ensures bend lines span most of the edge width
- Filters out geometrically incomplete connections
- 85% threshold allows for slight variations while catching problematic cases (20%, 60%, 80%)
- Full-width connections (100%) will pass
- Prevents generation of infeasible parts

### Part 2: Modify prioritize_perpendicular_bends Behavior

**Goal:** Generate more two-bend solutions by making the "prioritize" setting less restrictive

**Option A: Generate All, Filter During Assembly (Recommended)**

**Location:** `src/hgen_sm/create_segments/bend_strategies.py` line 1200

**Change:**
```python
# OLD: Skip Approach 2 entirely if Approach 1 succeeded
if prioritize_perpendicular and (pair_x, pair_z) in successful_edge_pairs:
    continue

# NEW: Generate all solutions, mark them for priority sorting
# Remove the continue statement - let all solutions be generated
# Add metadata to mark which approach generated each solution
```

**Implementation:**
1. Generate ALL two-bend solutions (both Approach 1 and Approach 2)
2. Add metadata `segment.generation_approach = 'perpendicular'` or `'edge_based'`
3. If `prioritize_perpendicular_bends=True`, sort/rank solutions during assembly to prefer perpendicular ones
4. Keep both types but allow user to see all options

**Option B: Separate Configuration Flags (Alternative)**

**Location:** `config/config.yaml`

**Change:**
```yaml
design_exploration:
  single_bend: True
  double_bend: True
  double_bend_approach_1: True  # Perpendicular connections
  double_bend_approach_2: True  # Edge-based connections
  prioritize_perpendicular_bends: True  # Only affects sorting, not generation
```

**Rationale:**
- Option A is less intrusive and maintains backward compatibility
- Separates "generation" from "prioritization"
- Users can see all valid solutions, not just one type
- Allows exploration of design alternatives

### Part 3: Add Edge Coverage Validation

**Goal:** Add validation during part assembly to catch any remaining incomplete connections

**Location:** `src/hgen_sm/part_assembly/assemble.py` after line 63

**Implementation:**

```python
def validate_edge_coverage(part):
    """
    Validate that bend points on tabs span appropriate edge coverage.

    Returns:
        (is_valid, error_messages)
    """
    errors = []

    for tab_id, tab in part.tabs.items():
        # Find edges with bend points
        bend_edges = {}  # edge_name -> [bend_points]

        for point_name, coord in tab.points.items():
            if 'BP' in point_name:
                # Determine which edge this BP is on
                edge = detect_edge(coord, tab.points)
                if edge not in bend_edges:
                    bend_edges[edge] = []
                bend_edges[edge].append(coord)

        # Check coverage for each edge with bends
        for edge_name, bend_points in bend_edges.items():
            if len(bend_points) >= 2:
                coords = np.array(bend_points)
                bend_span = np.linalg.norm(coords.max(axis=0) - coords.min(axis=0))

                # Get edge length
                edge_corners = get_edge_corners(edge_name)  # e.g., 'AB' -> ['A', 'B']
                if edge_corners[0] in tab.points and edge_corners[1] in tab.points:
                    edge_length = np.linalg.norm(
                        tab.points[edge_corners[1]] - tab.points[edge_corners[0]]
                    )

                    coverage = (bend_span / edge_length) * 100 if edge_length > 1e-9 else 0

                    if coverage < 85:
                        errors.append(
                            f"Tab {tab_id} edge {edge_name}: Insufficient bend coverage "
                            f"({coverage:.1f}% < 85%)"
                        )

    return len(errors) == 0, errors

# Call in part_assembly after line 49 (after tab merging)
is_valid, errors = validate_edge_coverage(part)
if not is_valid:
    # Log errors but don't reject (validation is informational)
    for error in errors[:3]:
        print(f"  - {error}")
    return None  # Reject part with incomplete edge coverage
```

### Part 4: Testing Suite

**Goal:** Create comprehensive tests to validate the fixes

**Test Files:**

1. **`test_one_bend_edge_coverage.py`:**
   ```python
   def test_transportschuh_edge_coverage():
       """Test that one_bend generates only full-coverage solutions for transportschuh."""
       part = initialize_objects(transportschuh)
       segments = one_bend(create_segment(part), filter_cfg)

       for seg in segments:
           tab_x = seg.tabs['tab_x']
           bp_x = get_bend_points(tab_x)
           coverage = calculate_coverage(bp_x, tab_x)
           assert coverage >= 85, f"Bend coverage {coverage}% below minimum"

   def test_partial_coverage_filtered():
       """Test that segments with <85% coverage are filtered out."""
       # Create geometry that would produce partial coverage
       # Verify those segments are not in the output
       ...
   ```

2. **`test_two_bend_generation.py`:**
   ```python
   def test_perpendicular_tabs_generate_multiple_two_bends():
       """Test that perpendicular tabs generate multiple two-bend solutions."""
       part = initialize_objects(transportschuh)
       segments = two_bends(create_segment(part), segment_cfg, filter_cfg)

       two_bend_segs = [s for s in segments if len(s.tabs) == 3]
       assert len(two_bend_segs) > 1, f"Expected multiple two-bend solutions, got {len(two_bend_segs)}"

   def test_both_approaches_generate():
       """Test that both Approach 1 and Approach 2 generate solutions."""
       part = initialize_objects(transportschuh)
       segments = two_bends(create_segment(part), segment_cfg, filter_cfg)

       approach_1_count = sum(1 for s in segments if s.generation_approach == 'perpendicular')
       approach_2_count = sum(1 for s in segments if s.generation_approach == 'edge_based')

       assert approach_1_count > 0, "No perpendicular approach solutions"
       assert approach_2_count > 0, "No edge-based approach solutions"
   ```

3. **`test_transportschuh_regression.py`:**
   ```python
   def test_transportschuh_produces_only_feasible_parts():
       """Integration test: Verify transportschuh produces only feasible parts."""
       # Run full pipeline
       part = initialize_objects(transportschuh)
       solutions = run_full_pipeline(part, cfg)

       # All solutions should be feasible (no partial edge coverage)
       for solution in solutions:
           is_valid, errors = validate_edge_coverage(solution)
           assert is_valid, f"Part {solution.part_id} has invalid coverage: {errors}"

       # Should generate at least 3 solutions (the known good ones)
       assert len(solutions) >= 3, f"Expected at least 3 solutions, got {len(solutions)}"

   def test_transportschuh_generates_multiple_two_bend():
       """Test that transportschuh generates multiple two-bend solutions."""
       part = initialize_objects(transportschuh)
       solutions = run_full_pipeline(part, cfg)

       two_bend_parts = [p for p in solutions if has_intermediate_tab(p)]
       assert len(two_bend_parts) > 1, f"Expected multiple two-bend solutions, got {len(two_bend_parts)}"
   ```

## Expected Outcomes

### After Part 1 (Edge Coverage Filter):
- transportschuh generates **2 solutions** (down from 7)
  - Part 2: Full coverage (100%)
  - Part 7: Two-bend solution
- All generated parts have complete edge connections
- No more partial-coverage infeasible solutions

### After Part 2 (Two-Bend Generation):
- transportschuh generates **5+ solutions** (up from 2)
  - Multiple two-bend solutions with different intermediate tab positions
  - Both perpendicular and edge-based approaches represented
- More design exploration options for users

### After Part 3 (Validation):
- Assembly stage catches any remaining incomplete connections
- Clear error messages help debug geometric issues
- Extra safety net for edge cases

### After Part 4 (Testing):
- Regression tests ensure fixes don't break
- Documented test cases for future development
- Confidence in solution quality

## Implementation Priority

1. **Part 1** (Critical): Fixes the immediate issue of infeasible solutions
2. **Part 4** (High): Create tests before implementing Part 2 to ensure safety
3. **Part 2** (Medium): Enhances design exploration capabilities
4. **Part 3** (Low): Additional safety validation (nice-to-have)

## Configuration Changes

Add to `config/config.yaml`:
```yaml
design_exploration:
  single_bend: True
  double_bend: True
  prioritize_perpendicular_bends: False  # Changed: generate all solutions
  min_edge_coverage_percent: 85  # New: minimum edge coverage for one_bend
```

## Backward Compatibility

- Part 1: Filters out previously-generated invalid solutions (improvement)
- Part 2: Generates MORE solutions (superset of previous behavior)
- Part 3: Validation only (informational)
- Part 4: Testing only

No breaking changes expected.

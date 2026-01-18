# Implementation Plan: Fix Naming Scheme and Point Assignment

## Problem Summary
The project has issues with:
1. **Inconsistent naming**: one-bend uses "FP01L", two-bend uses "FP0_01L"
2. **Point ordering errors**: Causing self-intersecting polygons, overlaying tabs
3. **Geometry issues**: Flanges intersecting with tabs, export failures

## Root Causes Identified

### 1. Naming Inconsistency (bend_strategies.py)
**One-bend** (lines 259-275):
```python
# Current: FP{tab_x_id}{tab_z_id}L (no underscore)
f"FP{tab_x_id}{tab_z_id}L"  # Creates "FP01L"
```

**Two-bend** (lines 544-547):
```python
# Current: FP{tab_x_id}_{tab_y_id}L (with underscore)
f"FP{tab_x_id}_{tab_y_id}L"  # Creates "FP0_01L"
```

**Solution**: Always use underscores everywhere: `f"FP{tab_x_id}_{tab_z_id}L"`

### 2. Point Ordering Issues
Based on the specification, correct ordering should be:
```
[A FP{x}_{z}L BP{x}_{z}L BP{x}_{z}R FP{x}_{z}R B C D]
```

Where:
- FP points are at corner coordinates (A and B)
- BP points are on the bend line
- Order maintains valid perimeter without self-intersections

**Current issues**:
- Insertion logic for wrap-around edges (D→A) may be incorrect
- L/R reversal logic may cause crossovers
- Point duplication (FP = corner) is intentional and correct

### 3. Intermediate Tab Point Ordering (Two-Bend)
Intermediate tabs don't have corner points A, B, C, D. Their perimeter consists entirely of FP and BP points.

**Correct format** (from spec):
```
[FP{y}_{x}L BP{y}_{x}L BP{y}_{x}R FP{y}_{x}R FP{y}_{z}R BP{y}_{z}R BP{y}_{z}L FP{y}_{z}L]
```

Where tab y is intermediate tab connecting tab x and tab z.

## Implementation Tasks

### Phase 1: Fix Naming Consistency

#### Task 1.1: Update one_bend() naming to always use underscores
**File**: `src/hgen_sm/create_segments/bend_strategies.py` (lines 139-368)

**Changes needed**:
1. Line 259, 260, 261, 262: Change from `f"FP{tab_x_id}{tab_z_id}L"` to `f"FP{tab_x_id}_{tab_z_id}L"`
2. Line 270, 271, 272, 273, 274, 275: Same change
3. Line 317, 318, 319, 320: Change from `f"FP{tab_z_id}{tab_x_id}R"` to `f"FP{tab_z_id}_{tab_x_id}R"`
4. Line 324, 325, 326, 327: Same change
5. Line 333, 334, 335, 336: Same change
6. Line 340, 341, 342, 343, 344: Same change

**Pattern**: Replace ALL occurrences of:
- `f"FP{tab_x_id}{tab_z_id}` → `f"FP{tab_x_id}_{tab_z_id}`
- `f"BP{tab_x_id}{tab_z_id}` → `f"BP{tab_x_id}_{tab_z_id}`
- `f"FP{tab_z_id}{tab_x_id}` → `f"FP{tab_z_id}_{tab_x_id}`
- `f"BP{tab_z_id}{tab_x_id}` → `f"BP{tab_z_id}_{tab_x_id}`

#### Task 1.2: Verify two_bend() naming is correct
**File**: `src/hgen_sm/create_segments/bend_strategies.py` (lines 371-880)

The two-bend already uses underscores - verify it follows the pattern:
- Tab x: `FP{tab_x_id}_{tab_y_id}L`
- Tab y: `FP{tab_y_id}_{tab_x_id}L` and `FP{tab_y_id}_{tab_z_id}L`
- Tab z: `FP{tab_z_id}_{tab_y_id}L`

### Phase 2: Fix Point Ordering Issues

#### Task 2.1: Fix one_bend() point insertion logic
**File**: `src/hgen_sm/create_segments/bend_strategies.py` (lines 239-282)

**Current logic** (lines 252-277):
```python
if idx_L > idx_R:
    insert_after_id = CP_xL_id
    bend_points_x = {FPL, BPL, BPR, FPR}  # L->R order
else:
    insert_after_id = CP_xR_id
    bend_points_x = {FPR, BPR, BPL, FPL}  # R->L order
```

**Problem**: This doesn't correctly handle wrap-around edges and may cause incorrect ordering.

**Fix**: Clarify the insertion logic:
1. Always insert after the corner that comes LATER in perimeter order
2. Ensure bend points flow in the direction that maintains perimeter continuity
3. Handle wrap-around case (edge D→A) explicitly

**Detailed algorithm**:
```python
# Determine perimeter flow direction
corner_order = ['A', 'B', 'C', 'D']
idx_L = corner_order.index(CP_xL_id)
idx_R = corner_order.index(CP_xR_id)

# Check if this is a wrap-around edge (D→A)
is_wraparound = (idx_L == 3 and idx_R == 0) or (idx_L == 0 and idx_R == 3)

if is_wraparound:
    # For D→A edge, insert after D (higher index)
    if idx_L == 3:  # L=D, R=A
        insert_after_id = CP_xL_id  # Insert after D
        # Flow: D -> FP -> BP -> BP -> FP -> A
        bend_points_x = {FPL, BPL, BPR, FPR}
    else:  # L=A, R=D
        insert_after_id = CP_xR_id  # Insert after D
        # Flow: D -> FP -> BP -> BP -> FP -> A (reversed)
        bend_points_x = {FPR, BPR, BPL, FPL}
elif idx_R > idx_L:
    # Normal case: R comes after L (e.g., A→B, B→C)
    insert_after_id = CP_xR_id
    # Flow: L -> R -> [bend] -> next
    # Insert after R, reverse order so bend flows R -> L
    bend_points_x = {FPR, BPR, BPL, FPL}
else:
    # Reverse case: L comes after R (e.g., B→A, C→B)
    insert_after_id = CP_xL_id
    # Flow: R -> L -> [bend] -> next
    # Insert after L, normal order so bend flows L -> R
    bend_points_x = {FPL, BPL, BPR, FPR}
```

#### Task 2.2: Fix one_bend() tab_z point insertion
**File**: `src/hgen_sm/create_segments/bend_strategies.py` (lines 284-351)

Apply similar logic to tab_z insertion, including:
1. Proper wrap-around handling
2. Correct L/R correspondence based on fp_lines_cross check
3. Ensure reverse_order logic is applied correctly

#### Task 2.3: Fix two_bend() tab_x and tab_z insertion
**File**: `src/hgen_sm/create_segments/bend_strategies.py`

**Lines 528-549** (tab_x in 90-degree approach):
- Fix wrap-around case handling
- Ensure insertion after correct corner

**Lines 581-624** (tab_z in 90-degree approach):
- Lines 594-603: Wrap-around case - verify logic
- Lines 604-613: Normal case - verify order
- Lines 615-623: Reverse case - verify order

**Lines 757-778** (tab_x in fallback approach):
**Lines 810-860** (tab_z in fallback approach):
- Apply same fixes as 90-degree approach

#### Task 2.4: Fix two_bend() intermediate tab point ordering
**File**: `src/hgen_sm/create_segments/bend_strategies.py` (lines 551-579)

**Current logic** (lines 556-578):
```python
if diagonals_cross_3d(FPyxL, FPyxR, FPyzR, FPyzL):
    # Diagonals cross - swap z-side ordering
    bend_points_y = {
        FP{y}_{x}L, BP{y}_{x}L, BP{y}_{x}R, FP{y}_{x}R,
        FP{y}_{z}L, BP{y}_{z}L, BP{y}_{z}R, FP{y}_{z}R  # L/R swapped
    }
else:
    bend_points_y = {
        FP{y}_{x}L, BP{y}_{x}L, BP{y}_{x}R, FP{y}_{x}R,
        FP{y}_{z}R, BP{y}_{z}R, BP{y}_{z}L, FP{y}_{z}L  # Normal
    }
```

**Verify**:
1. The diagonal crossing check is working correctly
2. The swap logic produces valid (non-self-intersecting) polygons
3. The ordering matches specification: `[FP{y}_{x}L ... FP{y}_{z}L]` (closed loop)

### Phase 3: Update Plotting Code

#### Task 3.1: Update flange detection to handle underscores
**File**: `src/hgen_sm/plotting/plot_assembly.py` (lines 114-164)

**Current code** (line 118-131):
```python
idx = p_id[2:-1]  # Extracts "01" from "FP01L" or "0_01" from "FP0_01L"
ordered_keys = [f"BP{idx}L", f"BP{idx}R", f"FP{idx}R", f"FP{idx}L"]
```

**Fix needed**:
This should already work with underscores since it extracts everything between the prefix (FP/BP) and suffix (L/R). But verify:
1. Test that `idx = "FP0_1L"[2:-1]` correctly extracts `"0_1"`
2. Verify that the ordering `[BPL, BPR, FPR, FPL]` produces correct quadrilateral winding

**Potential improvement**: Add validation to ensure exactly 4 points are found before plotting flange.

### Phase 4: Update Export Code

#### Task 4.1: Verify JSON export handles underscores
**File**: `src/hgen_sm/export/part_export.py` (lines 12-68)

JSON export just dumps all points - should work with any naming. Verify by testing.

#### Task 4.2: Verify Onshape export handles underscores
**File**: `src/hgen_sm/export/part_export.py` (lines 71-257)

**Lines 136-159**: Point filtering logic
- Removes duplicate FP points (which are at corner coordinates)
- Should work with underscore naming

**Verify**:
1. Test that duplicate detection works correctly
2. Ensure filtered points produce valid polygon for intermediate tabs

### Phase 5: Testing and Validation

#### Task 5.1: Add comprehensive tests
Create test cases for:
1. One-bend with all edge combinations (AB, BC, CD, DA, BA, CB, DC, AD)
2. Two-bend with all edge combinations
3. Wrap-around edges (D→A, A→D)
4. Intermediate tab geometry validation

#### Task 5.2: Update validation.py to check naming
**File**: `src/hgen_sm/data/validation.py`

Add checks for:
1. All point IDs follow pattern: `(FP|BP){tab_id}_{tab_id}(L|R)`
2. Underscore is always present in naming
3. L and R points are paired correctly

#### Task 5.3: Run validation on existing test cases
Test with various rectangle configurations to ensure:
- No self-intersections
- No overlaying tabs
- No flange-tab intersections
- Export produces valid geometry

## Implementation Order

1. **Phase 1**: Fix naming consistency (low risk, high impact)
2. **Phase 2.1-2.2**: Fix one_bend() ordering (medium risk, addresses main issues)
3. **Phase 3**: Update plotting (low risk, enables visual verification)
4. **Test**: Verify one-bend fixes work correctly
5. **Phase 2.3-2.4**: Fix two_bend() ordering (higher risk, more complex)
6. **Phase 4**: Update export (low risk)
7. **Phase 5**: Comprehensive testing and validation

## Expected Outcomes

After implementation:
- ✅ Consistent naming: All points use `FP{x}_{z}L` format with underscores
- ✅ Correct perimeter ordering: No self-intersections
- ✅ Valid tab geometry: No overlaying tabs
- ✅ Correct flange geometry: No intersections with tabs
- ✅ Working export: Onshape FeatureScript produces correct 3D geometry
- ✅ Validation passes: All parts pass data structure integrity checks

## Notes

1. **FP at corners is correct**: FP points intentionally duplicate corner coordinates per specification
2. **Underscores are required**: For consistency and clarity, especially with multi-digit tab IDs
3. **Perimeter order matters**: Must maintain proper winding to avoid self-intersections
4. **L/R correspondence**: Critical for correct bend connectivity across tabs

## Risk Assessment

**Low risk tasks**: Naming changes, plotting updates
**Medium risk tasks**: One-bend ordering fixes
**High risk tasks**: Two-bend ordering fixes (complex geometry)

**Mitigation**: Implement incrementally, test after each phase, keep backups of working code.

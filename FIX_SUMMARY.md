# Fix Summary: Plotting and Export Issues

## Problem Identified

After analyzing the earlier working version (https://github.com/maxim-moellhoff/hgen-sm), the root cause was identified:

**Critical Bug in `one_bend()` function:**
- **Flange Points (FP)** were using *calculated flange coordinates* instead of *original corner coordinates*
- This broke the perimeter topology, causing plotting and export failures

**Secondary Issue in Export:**
- Export assumed all tabs have 'A', 'B', 'C' corner labels
- Intermediate tabs (from two-bend connections) have FP/BP labels, not A/B/C
- This caused intermediate tabs to be skipped during export

---

## Changes Made

### 1. Fixed Flange Point Placement in `one_bend()` ✓

**File:** `src/hgen_sm/create_segments/bend_strategies.py`

**Before (INCORRECT):**
```python
bend_points_x = {
    f"FP{tab_x_id}{tab_z_id}L": FPxL,  # ❌ Using calculated flange point
    f"BP{tab_x_id}{tab_z_id}L": BPL,
    f"BP{tab_x_id}{tab_z_id}R": BPR,
    f"FP{tab_x_id}{tab_z_id}R": FPxR   # ❌ Using calculated flange point
}
```

**After (CORRECT):**
```python
bend_points_x = {
    f"FP{tab_x_id}{tab_z_id}L": CP_xL,  # ✓ Using original corner coordinate
    f"BP{tab_x_id}{tab_z_id}L": BPL,
    f"BP{tab_x_id}{tab_z_id}R": BPR,
    f"FP{tab_x_id}{tab_z_id}R": CP_xR   # ✓ Using original corner coordinate
}
```

**Why this matters:**
- FP (Flange Point) must be at the original corner to maintain proper perimeter topology
- Connection sequence: Corner → FP (at corner) → BP (on bend line)
- This ensures plotting creates a valid closed perimeter without gaps

**Note:** `two_bends()` already had the correct implementation - only `one_bend()` needed fixing.

---

### 2. Fixed Export Coordinate System ✓

**File:** `src/hgen_sm/export/part_export.py`

**Before (INCORRECT):**
```python
# Assumed all tabs have A, B, C corners
if 'A' not in points_dict or 'B' not in points_dict or 'C' not in points_dict:
    print(f"Skipping Tab {tab_id}: Missing corner points A, B, or C")
    continue

A = points_dict['A']
B = points_dict['B']
C = points_dict['C']
```

**After (CORRECT):**
```python
# Try to use A, B, C if available (original rectangles)
if 'A' in points_dict and 'B' in points_dict and 'C' in points_dict:
    origin = points_dict['A']
    v1 = sub(points_dict['B'], origin)
    v2 = sub(points_dict['C'], origin)
else:
    # Intermediate tab - use first three non-collinear points
    pts = list(tab_data["points"].values())
    origin = pts[0]
    v1 = sub(pts[1], pts[0])

    # Find non-collinear third point
    for i in range(2, len(pts)):
        v_temp = sub(pts[i], pts[0])
        if mag_sq(cross(v1, v_temp)) > 1e-8:
            v2 = v_temp
            break

# Calculate coordinate system from v1, v2
z_axis = norm(cross(v1, v2))
x_axis = norm(v1)
y_axis = cross(z_axis, x_axis)
```

**Why this matters:**
- Intermediate tabs (like "01" from two-bend connections) don't have A/B/C labels
- They have point names like `FP01_0L`, `BP01_0L`, etc.
- Dynamic coordinate system works for all tabs regardless of naming

---

### 3. Added Data Structure Validation ✓

**New File:** `src/hgen_sm/data/validation.py`

Added three validation functions:

#### `validate_flange_points(tab)`
- Verifies FP points are at corner coordinates
- Catches topology errors early in the pipeline
- Skips intermediate tabs (which don't have rectangles)

#### `validate_perimeter_ordering(tab)`
- Detects self-intersecting polygons
- Checks for edge crossings in 2D projections (XY, XZ, YZ)
- Flags unexpected duplicate points

#### `validate_part(part)`
- Validates entire part structure
- Runs both FP and perimeter checks on all tabs
- Returns detailed error messages

**Integration:** Validation automatically runs in `part_assembly()` before returning assembled parts.

---

### 4. Corner Removal Logic Review ✓

**File:** `src/hgen_sm/create_segments/bend_strategies.py` (lines 231-235, 256-261)

**Verified correct behavior:**
- When connecting non-adjacent edges (e.g., A-C), removes intermediate corner (B)
- Uses `next_cp()` to find the corner to remove from original rectangle
- Removes it from tab's points dictionary
- This is necessary because the flange/bend occupies that corner's space

**No changes needed** - logic was already correct.

---

## Testing Results

### Test 1: Program Execution ✓
```bash
python -m src.hgen_sm
```
- **Result:** Successfully generated 26 solutions
- **Time:** 0.16 seconds
- **Validation:** Minor warnings for merged connections (expected)

### Test 2: JSON Export ✓
```bash
python test_export.py
```
- **Result:** Successfully exported parts with correct topology
- **FP placement verified:** FP points at corner coordinates
- **Perimeter ordering:** Sequential point connections maintained

### Test 3: FeatureScript Export ✓
- **Result:** Successfully exported to Onshape format
- **Intermediate tabs:** Correctly handled without A/B/C labels
- **Coordinate system:** Dynamic calculation works for all tab types

### Test 4: Intermediate Tab Export ✓
- **Tab "01":** 8 points (FP/BP for both connections)
- **JSON:** All points exported correctly
- **FeatureScript:** Sketch created with proper plane definition

---

## File Changes Summary

| File | Change | Lines |
|------|--------|-------|
| `bend_strategies.py` | Fixed FP placement in one_bend() | 222-254 |
| `part_export.py` | Dynamic coordinate system | 91-135 |
| `validation.py` | NEW: Validation functions | All |
| `data/__init__.py` | Export validation functions | 7-10 |
| `assemble.py` | Added validation call | 47-57 |

---

## How to Use Validation

### Automatic Validation
Validation runs automatically during part assembly. No action needed.

### Manual Validation
```python
from src.hgen_sm.data import validate_part, print_validation_report

# Quick validation
is_valid, errors = validate_part(part)
if not is_valid:
    for error in errors:
        print(error)

# Detailed report
print_validation_report(part)
```

### Validation Output Example
```
============================================================
VALIDATION REPORT: Part 0
============================================================
✓ Tab 0: FP points valid
✓ Tab 0: Perimeter ordering valid
✓ Tab 1: FP points valid
✓ Tab 1: Perimeter ordering valid

✓ All validation checks passed!
============================================================
```

---

## Expected Behavior After Fix

### Plotting
- ✓ Tabs render as closed, non-self-intersecting polygons
- ✓ Flanges appear correctly positioned
- ✓ No gaps or topology errors
- ✓ Triangulation works for complex shapes

### JSON Export
- ✓ All tabs export successfully (including intermediate tabs)
- ✓ Point ordering preserves perimeter sequence
- ✓ FP points at corner coordinates
- ✓ Mount coordinates correct

### Onshape Export
- ✓ FeatureScript compiles without errors
- ✓ Sketches created for all tabs (including intermediate)
- ✓ Coordinate systems calculated correctly
- ✓ Boolean union succeeds

---

## Comparison with Working Version

### Point Structure (Working Version)
```python
# From https://github.com/maxim-moellhoff/hgen-sm
bend_points_x = {
    f"FP{tab_x_id}{tab_z_id}L": CP_xL,  # At corner
    f"BP{tab_x_id}{tab_z_id}L": BPL,     # Shifted
    f"BP{tab_x_id}{tab_z_id}R": BPR,     # Shifted
    f"FP{tab_x_id}{tab_z_id}R": CP_xR    # At corner
}
```

### Your Implementation (Now Fixed)
```python
# Now matches the working version!
bend_points_x = {
    f"FP{tab_x_id}{tab_z_id}L": CP_xL,  # ✓ At corner
    f"BP{tab_x_id}{tab_z_id}L": BPL,     # ✓ Shifted
    f"BP{tab_x_id}{tab_z_id}R": BPR,     # ✓ Shifted
    f"FP{tab_x_id}{tab_z_id}R": CP_xR    # ✓ At corner
}
```

---

## Key Insights

### Why FP Must Be At Corners
The perimeter sequence must form a valid closed loop:
```
Corner A → FP (at A) → BP (shifted) → BP (shifted) → FP (at B) → Corner B → ...
          └─ Connect ─┘                                └─ Connect ─┘
```

If FP is shifted away from the corner, there's a gap between Corner and FP, breaking the topology.

### Why two_bends() Worked
The `two_bends()` function already had the correct implementation (lines 438-443, 622-627). Only `one_bend()` had the bug, which is why two-bend connections might have plotted better than one-bend connections.

### Why Validation Helps
- Catches topology errors before they reach plotting/export
- Provides clear error messages with point IDs and coordinates
- Helps debug future changes to bend strategies

---

## Next Steps

### Recommended Actions
1. **Test with your specific geometries** - Run your actual use cases
2. **Verify plotting output** - Check that visualizations look correct
3. **Test export workflows** - Verify JSON and Onshape exports work
4. **Review validation warnings** - Some warnings for merged connections are expected

### If Issues Persist
1. Check validation output for specific error messages
2. Verify input rectangles are valid (non-degenerate, correct orientation)
3. Ensure design rules (min flange length, etc.) are appropriate
4. Check for edge cases (parallel planes, very small angles)

---

## Clean Up

You can remove the test files:
```bash
rm test_export.py
rm -r exports_test/
```

Or keep them for future testing.

---

## Questions?

If you encounter any issues or have questions about the fixes, check:
1. Validation error messages (run with verbose=True)
2. JSON export to verify point coordinates
3. This document's "Expected Behavior" section

The implementation now matches the working version's topology and should resolve all plotting and export issues.

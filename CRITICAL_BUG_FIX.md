# Critical Bug Fix: Insertion Point Logic

## Problem Summary

The previous implementation had a **critical bug** in the point insertion logic that caused:
1. **Self-intersecting polygons** (diagonal connections across tab interiors)
2. **Missing solutions** (likely filtered out due to validation failures)
3. **Incorrect plotting** (wrong connections visible in PyVista)
4. **Faulty exports** (Onshape FeatureScript with invalid geometry)

## Root Cause

### What Was Wrong

When inserting bend points for an edge (e.g., B→C), the code was inserting **AFTER the second corner** (C), creating:

```
Perimeter: A, B, C, [bend points], D
Path: A → B → C → [bend] → D
```

But the bend should be **BETWEEN B and C**, so it should insert **AFTER the first corner** (B):

```
Perimeter: A, B, [bend points], C, D
Path: A → B → [bend] → C → D
```

### Visual Example from Your JSON

**Tab 1 had:**
```json
"points": {
    "A": [0, 80, 40],
    "B": [0, 40, 40],
    "C": [0, 40, 80],
    "FP1_10_0R": [0, 40, 80],  ← Inserted after C
    "BP1_10_0R": [0, -10, 80],
    "BP1_10_0L": [0, -10, 40],
    "FP1_10_0L": [0, 40, 40],  ← At B's position
    "D": [0, 80, 80]
}
```

**The path was:** A → B → C → FP_R(C) → BP_R → BP_L → FP_L(B) → D

This created a **diagonal line from FP_L (at B) to D**, crossing the tab interior!

**Correct path should be:** A → B → FP_L(B) → BP_L → BP_R → FP_R(C) → C → D

No diagonal, bend is between B and C.

## The Fix

### Changed Logic

**Before (WRONG):**
```python
elif idx_R > idx_L:  # Normal case
    insert_after_id = CP_xR_id  # ← Wrong! Inserted after R (second corner)
    bend_points = {FP_R, BP_R, BP_L, FP_L}  # Reversed order
```

**After (CORRECT):**
```python
elif idx_R > idx_L:  # Normal case
    insert_after_id = CP_xL_id  # ← FIXED! Insert after L (first corner)
    bend_points = {FP_L, BP_L, BP_R, FP_R}  # Normal order L→R
```

### Files Modified

**`src/hgen_sm/create_segments/bend_strategies.py`:**

1. **`one_bend()` function:**
   - Lines 274-297: Fixed tab_x insertion (normal & reverse cases)
   - Lines 330-339: Fixed tab_z insertion (normal & reverse cases)

2. **`two_bend()` 90-degree approach:**
   - Lines 581-600: Fixed tab_x insertion
   - Lines 669-688: Fixed tab_z insertion

3. **`two_bend()` fallback approach:**
   - Lines 854-873: Fixed tab_x insertion
   - Lines 931-940: Fixed tab_z insertion

### Systematic Fix Applied

For **all** edge cases:

| Case | Insertion Point | Order |
|------|----------------|-------|
| Normal (L→R, idx_R > idx_L) | **After L** (FIRST corner) | FP_L, BP_L, BP_R, FP_R |
| Reverse (R→L, idx_L > idx_R) | **After R** (FIRST corner) | FP_R, BP_R, BP_L, FP_L |
| Wrap-around (D→A) | After D (highest index) | FP_L(D), BP_L, BP_R, FP_R(A) |
| Wrap-around (A→D) | After D (highest index) | FP_R(D), BP_R, BP_L, FP_L(A) |

## Why Solutions Were Missing

### 1. Validation Filtering
The self-intersecting polygons created by the wrong insertion logic likely failed validation checks:
- `validate_perimeter_ordering()` detects edge crossings
- Parts with invalid topology were filtered out

### 2. Geometry Filters
Invalid segments may have been caught by:
- `tab_fully_contains_rectangle()` filter
- Collision detection
- Self-intersection checks

### 3. No One-Bend Solutions
For one-bend connections (e.g., two perpendicular tabs), **ALL** segments were invalid due to the insertion bug, resulting in zero valid solutions.

## Expected Results After Fix

### ✅ Correct Perimeter Ordering
- Bends are BETWEEN corners, not after them
- No diagonal connections across tab interiors
- Valid polygons (no self-intersections)

### ✅ Solutions Restored
- One-bend solutions should now be generated
- More two-bend solutions (previously filtered out)
- Valid segments pass all filters

### ✅ Correct Plotting
Your reported issue: "lower bend point connected to upper corner point" → **FIXED**
- Bend points now connect in correct order
- No spurious diagonal lines in visualization

### ✅ Correct Exports
Your reported issues:
- "connection from bottom left bending point to top right edge point" → **FIXED**
- Split surface tabs geometry → **SHOULD BE FIXED**
- Tab edge points properly connected with flanges → **FIXED**

## Testing Recommendations

### 1. Quick Test
```bash
python -m hgen_sm
```
- You should now see one-bend solutions
- Check that tabs don't have diagonal connections
- Verify polygons are valid (no self-intersections)

### 2. Visual Inspection (PyVista)
- No lines crossing tab interiors ✓
- Flanges properly positioned between corners ✓
- Clean perimeter paths ✓

### 3. Export Validation
**JSON:**
- Point order should be: corners interspersed with bends
- Example: `A, B, FP_L, BP_L, BP_R, FP_R, C, D`

**Onshape:**
- Sketches should have valid closed loops
- No "connection from bend point to far corner" errors
- Extrusion should succeed

### 4. Check Solution Count
Compare number of solutions before/after fix:
- **Before**: Fewer solutions, no one-bend
- **After**: More solutions, one-bend solutions present

## Implementation Details

### Perimeter Cycle Logic

The fix ensures bends are inserted in the correct position to maintain a valid perimeter cycle:

```
Original: A → B → C → D → (back to A)

After bend on B→C:
A → B → [FP_L(B) → BP_L → BP_R → FP_R(C)] → C → D → A

After second bend on D→A:
A → B → [bend BC] → C → D → [FP_L(D) → BP_L → BP_R → FP_R(A)] → A
```

Each bend **replaces** the edge between two corners with the bend geometry, maintaining a valid cyclic path.

### Corner Point Duplication

Per the specification, FP (Flange Points) are at corner coordinates:
- `FP_L` is at the FIRST corner's position
- `FP_R` is at the SECOND corner's position

This creates intentional duplicates (e.g., both `B` and `FP_L` at same location), which is correct and expected.

## Rollback

If any issues arise, revert with:
```bash
git checkout HEAD~1 -- src/hgen_sm/create_segments/bend_strategies.py
```

## Summary

This was a **systematic error** affecting ALL bend insertion cases. The fix changes the insertion point from "after second corner" to "after first corner", ensuring bends are placed BETWEEN corners rather than AFTER them.

This should:
- ✅ Restore missing solutions (including one-bend)
- ✅ Fix self-intersecting polygons
- ✅ Correct plotting visualization
- ✅ Fix Onshape export geometry

**Please test and report any remaining issues!**

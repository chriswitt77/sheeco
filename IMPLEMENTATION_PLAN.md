# Implementation Plan: Fix Intermediate Tab Point Ordering

## Problem Summary

The intermediate tab (e.g., tab "01") in two-bend connections is sometimes plotted incorrectly, with the flange points on one side both connecting to a single flange point on the other side, forming unwanted triangular faces.

### Root Cause

The current `diagonals_cross_3d()` function fails when flange points are **collinear or nearly collinear**. Specifically:

- **Problem scenario**: When three flange points share the same X and Y coordinates (differing only in Z), the diagonal segments don't cross in their interior, so the function returns `False`
- This leads to the DEFAULT ordering (R before L), which creates self-intersecting polygons
- The function should return `True` to use the SWAPPED ordering (L before R)

### Example from Test Data

**Problem case (part_id 4):**
- FP01_0L: [60, 90, 10]
- FP01_0R: [10, 90, 10]  ← Same X,Y as below
- FP01_1R: [10, 90, 80]  ← Same X,Y (collinear in XZ)
- FP01_1L: [10, 90, 40]  ← Same X,Y

Three points are collinear at (x=10, y=90), causing the diagonal crossing check to fail.

## Proposed Solution

### Strategy: Hybrid Approach

Replace the point ordering logic with an **improved function** that combines:

1. **Primary method**: Diagonal crossing check (existing `diagonals_cross_3d()`)
2. **Fallback heuristic**: Distance comparison for collinear/degenerate cases

### How It Works

```python
def should_swap_z_side_ordering(FPyxL, FPyxR, FPyzR, FPyzL):
    """
    Determine if z-side L/R ordering should be swapped.

    Returns True if the z-side points should use swapped ordering (L before R).
    """
    # Try diagonal crossing check first
    crosses = diagonals_cross_3d(FPyxL, FPyxR, FPyzR, FPyzL)

    # Calculate diagonal distances for both orderings
    # Default: (FPyxR→FPyzR) + (FPyzL→FPyxL)
    # Swapped: (FPyxR→FPyzL) + (FPyzR→FPyxL)

    dist_default = distance(FPyxR, FPyzR) + distance(FPyzL, FPyxL)
    dist_swapped = distance(FPyxR, FPyzL) + distance(FPyzR, FPyxL)

    # If distances differ significantly, use distance-based decision
    # This handles collinear cases where crossing check fails
    if abs(dist_default - dist_swapped) > 1.0:
        return dist_swapped < dist_default

    # Otherwise, trust the diagonal crossing check
    return crosses
```

### Why This Works

- **Collinear cases**: Distance comparison identifies the natural pairing (shorter diagonals)
- **General cases**: Diagonal crossing check handles complex 3D geometries
- **Threshold of 1.0mm**: Provides a safety margin while avoiding unnecessary swaps

## Implementation Steps

### 1. Add New Function (bend_strategies.py)

Add the improved ordering function after the existing `diagonals_cross_3d()` function:

```python
def should_swap_z_side_ordering(FPyxL, FPyxR, FPyzR, FPyzL):
    """
    Determine if z-side L/R ordering should be swapped using hybrid approach.

    Combines diagonal crossing detection with distance-based fallback for
    collinear/degenerate cases.

    Args:
        FPyxL: Flange point on x-side, L orientation
        FPyxR: Flange point on x-side, R orientation
        FPyzR: Flange point on z-side, R orientation (default ordering)
        FPyzL: Flange point on z-side, L orientation (default ordering)

    Returns:
        bool: True if z-side ordering should be swapped (L before R)
    """
    # First try the diagonal crossing check
    crosses = diagonals_cross_3d(FPyxL, FPyxR, FPyzR, FPyzL)

    FPyxL = np.array(FPyxL)
    FPyxR = np.array(FPyxR)
    FPyzR = np.array(FPyzR)
    FPyzL = np.array(FPyzL)

    # Calculate distances for both orderings
    # Default ordering: R-to-R and L-to-L connections
    dist_default = (np.linalg.norm(FPyzR - FPyxR) +
                    np.linalg.norm(FPyxL - FPyzL))

    # Swapped ordering: R-to-L and L-to-R connections
    dist_swapped = (np.linalg.norm(FPyzL - FPyxR) +
                    np.linalg.norm(FPyxL - FPyzR))

    # If distance difference is significant (>1mm), use distance-based decision
    # This handles collinear cases where diagonal crossing check fails
    if abs(dist_default - dist_swapped) > 1.0:
        return dist_swapped < dist_default

    # Otherwise, trust the diagonal crossing check
    return crosses
```

### 2. Update Approach 1 (Lines ~619)

**Before:**
```python
if diagonals_cross_3d(FPyxL, FPyxR, FPyzR, FPyzL):
```

**After:**
```python
if should_swap_z_side_ordering(FPyxL, FPyxR, FPyzR, FPyzL):
```

### 3. Update Approach 2A (Lines ~882)

**Before:**
```python
if diagonals_cross_3d(FPyxL, FPyxR, FPyzR, FPyzL):
```

**After:**
```python
if should_swap_z_side_ordering(FPyxL, FPyxR, FPyzR, FPyzL):
```

### 4. Update Approach 2B (Lines ~1137)

**Before:**
```python
if diagonals_cross_3d(FPyxL, FPyxR, FPyzR, FPyzL):
```

**After:**
```python
if should_swap_z_side_ordering(FPyxL, FPyxR, FPyzR, FPyzL):
```

### 5. Update Comments

Update the comments at each location to reflect the improved logic:

```python
# Determine correct z-side ordering using hybrid approach
# (diagonal crossing check + distance-based fallback for collinear cases)
if should_swap_z_side_ordering(FPyxL, FPyxR, FPyzR, FPyzL):
```

## Testing Plan

### Test Files Created

1. **analyze_crossing_issue.py** - Demonstrates the root cause
2. **test_solution_strategy.py** - Validates the solution approach

### Test Cases

All test cases pass with the improved method:

| Test Case | Original | Distance-Based | Improved |
|-----------|----------|----------------|----------|
| Problem case (part_id 4, x=10) | FAIL | PASS | PASS |
| Working case (part_id 4, x=20) | PASS | PASS | PASS |
| Problem case (part_id 6, x=10) | FAIL | PASS | PASS |
| Working case (part_id 6, x=20) | PASS | PASS | PASS |

### Manual Testing

After implementation:
1. Run with original input B configuration (x=10)
2. Verify intermediate tabs no longer show triangular artifacts
3. Check that working cases (x=20) still function correctly
4. Test with other input configurations to ensure no regressions

## Files to Modify

- **src/hgen_sm/create_segments/bend_strategies.py** (primary changes)
  - Add `should_swap_z_side_ordering()` function after line 56
  - Update line ~619 (Approach 1)
  - Update line ~882 (Approach 2A)
  - Update line ~1137 (Approach 2B)

## Estimated Impact

- **Low risk**: Only changes the point ordering logic, no structural changes
- **High benefit**: Fixes visualization artifacts for close-proximity tabs
- **No performance impact**: Same computational complexity
- **Backward compatible**: Existing working cases remain unaffected

## Alternative Approaches Considered

1. **Pure distance-based**: Works but may fail in complex 3D cases where diagonals truly cross
2. **Signed area/volume**: More complex and harder to implement correctly
3. **Angle-based convexity check**: Computationally expensive and may not handle all cases

The hybrid approach provides the best balance of robustness and simplicity.

# Implementation Plan: Adaptive Validation Thresholds

## Problem Statement

The perpendicular plane validation checks implemented for two_bends Approach 1 are filtering out valid solutions for `with_mounts` while correctly filtering degenerate cases for `transportschuh`.

**Root cause:** The validation checks use **absolute thresholds** that don't scale with geometry size:
- Edge coplanarity tolerance: 5.0 mm (absolute)
- Bend point range margin: 0.3 (30% relative, but may be too strict)

**Impact:**
- `with_mounts` (small tabs): 2 valid Approach 1 solutions filtered (was 5, now 3)
- `transportschuh` (large tabs): 2 degenerate solutions correctly filtered (was 5, now 3)

## Analysis of Filtered Cases

### transportschuh DEGENERATE (correctly filtered)

**D-A x C-D combination:**
- Edge coplanarity: Caught and filtered ✓
- Bend points: z=290 (90mm beyond tab range of [40, 200])
- Tab size: 160x160 mm (large)
- Overshoot ratio: 56% of tab range
- **Status:** DEGENERATE - correctly filtered

### with_mounts VALID (incorrectly filtered)

**Case 1: B-C x D-A**
- Filtered by: bend_point_range check
- Bend points: y=110 (30mm beyond tab range of [40, 80])
- Tab size: 40x40 mm (small)
- Overshoot ratio: 75% of tab range
- **Issue:** High relative overshoot (75%) but small absolute distance (30mm)

**Case 2: D-A x B-C**
- Filtered by: edge_coplanarity check
- Max deviation: 7.489 mm (failed by 2.489 mm)
- Tab size: 50x100 mm and 40x40 mm (small)
- Edge perpendicularity: perfect (dot = 0.000)
- **Issue:** Slightly non-coplanar but edges are perfectly perpendicular

## Key Insight

The fundamental difference between valid and degenerate cases:

1. **Absolute scale matters:**
   - transportschuh: 90mm overshoot → physically unrealistic intermediate tab
   - with_mounts: 30mm overshoot → acceptable intermediate tab for small geometry

2. **Edge coplanarity context:**
   - transportschuh degenerate: Non-coplanar AND creates bad geometry
   - with_mounts: Slightly non-coplanar (7.5mm) but perfectly perpendicular edges

## Proposed Solution

Use **adaptive thresholds** that scale with geometry size and connection distance.

### Approach 1: Scale-Aware Validation

Replace absolute thresholds with **hybrid thresholds** that consider:
1. Characteristic length scale of the geometry
2. Connection distance between tabs
3. Minimum absolute thresholds for manufacturing constraints

## Implementation Plan

### Step 1: Add Geometry Characteristic Length Helper

**Location:** `bend_strategies.py` (after existing helper functions)

**Function:**
```python
def calculate_characteristic_length(tab_x, tab_z):
    """
    Calculate a characteristic length scale for the geometry.
    Uses the geometric mean of the maximum tab dimensions.
    """
    corners_x = np.array([tab_x.points[k] for k in ['A', 'B', 'C', 'D']])
    corners_z = np.array([tab_z.points[k] for k in ['A', 'B', 'C', 'D']])

    size_x = np.max(corners_x, axis=0) - np.min(corners_x, axis=0)
    size_z = np.max(corners_z, axis=0) - np.min(corners_z, axis=0)

    max_dim_x = np.max(size_x)
    max_dim_z = np.max(size_z)

    # Geometric mean provides scale-invariant characteristic length
    char_length = np.sqrt(max_dim_x * max_dim_z)

    return char_length
```

### Step 2: Adaptive Edge Coplanarity Check

**Replace:** `validate_edge_coplanarity()` with adaptive version

**Key changes:**
1. Calculate characteristic length from tab sizes
2. Scale tolerance based on characteristic length
3. Use minimum absolute threshold for manufacturing

**Logic:**
```python
def validate_edge_coplanarity_adaptive(CPxL, CPxR, CPzL, CPzR, plane_x, plane_z,
                                        tab_x, tab_z, base_tolerance=5.0,
                                        scale_factor=0.05):
    """
    Adaptive edge coplanarity check that scales with geometry size.

    Args:
        base_tolerance: Minimum absolute tolerance (mm)
        scale_factor: Tolerance as fraction of characteristic length (0.05 = 5%)
    """
    # Calculate characteristic length
    char_length = calculate_characteristic_length(tab_x, tab_z)

    # Adaptive tolerance: max of absolute minimum or scaled tolerance
    tolerance = max(base_tolerance, scale_factor * char_length)

    # [Rest of coplanarity check logic unchanged]
    # ...

    if max_dist > tolerance:
        return False

    # [Rest of perpendicularity check unchanged]
    # ...
```

**Effect:**
- Small geometry (with_mounts: char_length ≈ 63mm):
  - Tolerance = max(5.0, 0.05 * 63) = max(5.0, 3.15) = **5.0 mm**
  - STILL fails at 7.5mm

- Need more permissive approach for small geometries...

### Step 2b: Better Adaptive Edge Coplanarity

**Alternative approach:** Use connection distance as scale

```python
def validate_edge_coplanarity_adaptive(CPxL, CPxR, CPzL, CPzR, plane_x, plane_z,
                                        base_tolerance=5.0, relative_tolerance=0.1):
    """
    Adaptive edge coplanarity check based on connection distance.

    Args:
        base_tolerance: Minimum absolute tolerance (mm) for large geometries
        relative_tolerance: Maximum allowed deviation as fraction of connection distance
    """
    # Calculate connection distance (distance between edge midpoints)
    edge_x_mid = (CPxL + CPxR) / 2
    edge_z_mid = (CPzL + CPzR) / 2
    connection_dist = np.linalg.norm(edge_z_mid - edge_x_mid)

    # Adaptive tolerance: use relative tolerance for small connections,
    # but cap at base_tolerance for large connections
    # For small geometries: relative_tolerance * connection_dist may be > base_tolerance
    # For large geometries: use base_tolerance as maximum
    if connection_dist < base_tolerance / relative_tolerance:
        # Small geometry: use relative tolerance
        tolerance = relative_tolerance * connection_dist
    else:
        # Large geometry: use fixed base tolerance
        tolerance = base_tolerance

    # Fit plane and check coplanarity
    points = np.array([CPxL, CPxR, CPzL, CPzR])
    centroid = np.mean(points, axis=0)
    centered = points - centroid
    _, _, vh = np.linalg.svd(centered)
    fitted_normal = vh[-1]
    fitted_normal = normalize(fitted_normal)

    distances = [abs(np.dot(p - centroid, fitted_normal)) for p in points]
    max_dist = max(distances)

    if max_dist > tolerance:
        return False

    # Check perpendicularity [unchanged]
    # ...
```

**Effect with relative_tolerance=0.1:**
- with_mounts (connection_dist ≈ 75mm):
  - Tolerance = 0.1 * 75 = **7.5 mm** → PASS at 7.489 mm ✓

- transportschuh (connection_dist ≈ 180mm):
  - Tolerance = min(0.1 * 180, 5.0) = **5.0 mm** → FAIL degenerate case ✓

### Step 3: Adaptive Bend Point Range Check

**Replace:** `validate_bend_point_ranges()` with adaptive version

**Key changes:**
1. Use larger margin for small geometries
2. Add absolute distance cap for manufacturability

**Logic:**
```python
def validate_bend_point_ranges_adaptive(BPxL, BPxR, tab_x, BPzL, BPzR, tab_z,
                                         base_margin=0.3, max_absolute_overshoot=50.0):
    """
    Adaptive bend point range check with absolute overshoot limit.

    Args:
        base_margin: Relative margin (0.3 = 30%)
        max_absolute_overshoot: Maximum absolute overshoot distance (mm)
    """
    # Get tab bounding boxes
    corners_x = np.array([tab_x.points[k] for k in ['A', 'B', 'C', 'D']])
    corners_z = np.array([tab_z.points[k] for k in ['A', 'B', 'C', 'D']])

    min_x = np.min(corners_x, axis=0)
    max_x = np.max(corners_x, axis=0)
    range_x = max_x - min_x

    min_z = np.min(corners_z, axis=0)
    max_z = np.max(corners_z, axis=0)
    range_z = max_z - min_z

    # Calculate allowed overshoot: relative margin OR absolute cap, whichever is larger
    # This allows small geometries more relative flexibility
    for i in range(3):  # x, y, z dimensions
        if range_x[i] > 1e-6:
            max_overshoot_x = max(base_margin * range_x[i], max_absolute_overshoot)
        if range_z[i] > 1e-6:
            max_overshoot_z = max(base_margin * range_z[i], max_absolute_overshoot)

    # Extended bounds with adaptive margin
    extended_min_x = min_x - max_overshoot_x
    extended_max_x = max_x + max_overshoot_x

    extended_min_z = min_z - max_overshoot_z
    extended_max_z = max_z + max_overshoot_z

    # Check if bend points are within extended bounds
    for BP in [BPxL, BPxR]:
        if not np.all((extended_min_x <= BP) & (BP <= extended_max_x)):
            return False

    for BP in [BPzL, BPzR]:
        if not np.all((extended_min_z <= BP) & (BP <= extended_max_z)):
            # Additional check: absolute overshoot distance
            overshoot = np.maximum(min_z - BP, BP - max_z)
            overshoot = np.maximum(overshoot, 0)  # Only positive overshoots
            if np.max(overshoot) > max_absolute_overshoot:
                return False

    return True
```

**Effect with max_absolute_overshoot=50mm:**
- with_mounts (overshoot=30mm):
  - 30mm < 50mm → PASS ✓

- transportschuh (overshoot=90mm):
  - 90mm > 50mm → FAIL ✓

### Step 4: Update Configuration Parameters

**Location:** `config/config.yaml`

**Changes:**

```yaml
filter:
  edge_coplanarity_tolerance: 5.0  # Base tolerance for large geometries (mm)
  edge_coplanarity_relative_tolerance: 0.1  # NEW: Relative tolerance for small geometries (10% of connection distance)

design_exploration:
  bend_point_range_margin: 0.3  # Relative margin for bend points
  bend_point_max_absolute_overshoot: 50.0  # NEW: Maximum absolute overshoot distance (mm)
  max_intermediate_aspect_ratio: 10.0
```

### Step 5: Update Function Calls in two_bends()

**Location:** `bend_strategies.py` in two_bends() function (around line 820)

**Replace:**
```python
# OLD:
if not validate_edge_coplanarity(CPxL, CPxR, CPzL, CPzR, plane_x, plane_z,
                                 tolerance=coplanarity_tolerance):
    continue

if not validate_bend_point_ranges(BPxL, BPxR, tab_x, BPzL, BPzR, tab_z,
                                   margin=bp_range_margin):
    continue
```

**With NEW:**
```python
# Edge coplanarity with adaptive tolerance
coplanarity_base = filter_cfg.get('edge_coplanarity_tolerance', 5.0)
coplanarity_relative = filter_cfg.get('edge_coplanarity_relative_tolerance', 0.1)
if not validate_edge_coplanarity_adaptive(CPxL, CPxR, CPzL, CPzR, plane_x, plane_z,
                                           tab_x, tab_z,
                                           base_tolerance=coplanarity_base,
                                           relative_tolerance=coplanarity_relative):
    continue

# Bend point range with absolute overshoot limit
bp_range_margin = segment_cfg.get('bend_point_range_margin', 0.3)
bp_max_overshoot = segment_cfg.get('bend_point_max_absolute_overshoot', 50.0)
if not validate_bend_point_ranges_adaptive(BPxL, BPxR, tab_x, BPzL, BPzR, tab_z,
                                             base_margin=bp_range_margin,
                                             max_absolute_overshoot=bp_max_overshoot):
    continue
```

## Expected Results

### After Implementation:

**with_mounts:**
- B-C x D-A: overshoot=30mm < 50mm → PASS ✓
- D-A x B-C: coplanarity=7.5mm < 0.1*75mm=7.5mm → PASS (or very close) ✓
- **Total Approach 1 segments: 5 (restored)**

**transportschuh:**
- D-A x C-D: overshoot=90mm > 50mm → FAIL ✓
- **Total Approach 1 segments: 2 (degenerate filtered)**

**transportschuh other valid combinations:**
- Perpendicular connections with moderate geometry → PASS ✓

## Validation Strategy

1. Run `debug_with_mounts.py` to confirm 2 previously-filtered cases now pass
2. Run `debug_perpendicular_filters.py` with transportschuh to confirm degenerate case still fails
3. Run `validate_perpendicular_fix.py` to confirm overall counts
4. Create new test: `validate_adaptive_thresholds.py` to show threshold calculations for both inputs

## Configuration Tuning

If initial parameters don't work perfectly:

**Tune edge_coplanarity_relative_tolerance:**
- Increase (0.1 → 0.15) to allow more deviation for small geometries
- Decrease (0.1 → 0.07) to be more strict

**Tune bend_point_max_absolute_overshoot:**
- Increase (50 → 70) to allow larger overshoots
- Decrease (50 → 40) to be more strict on absolute distance

## Advantages of This Approach

1. **Scale-invariant:** Works for both small and large geometries
2. **Physically meaningful:** Thresholds based on connection distance and overshoot
3. **Configurable:** Easy to tune parameters
4. **Preserves strictness for large geometry:** transportschuh degenerate cases still filtered
5. **Relaxes for small geometry:** with_mounts valid cases pass
6. **Hybrid approach:** Uses both relative and absolute limits appropriately

## Risk Mitigation

**Risk:** May allow some borderline cases that are questionable

**Mitigation:**
- Keep aspect_ratio check unchanged (provides additional safety)
- Set conservative initial values (relative_tolerance=0.1, max_overshoot=50mm)
- Add logging to track which cases pass/fail at which stage
- Can tighten parameters if too many questionable cases appear in practice

## Summary

This adaptive approach solves the core issue by:
1. Using **connection-distance-relative** tolerance for edge coplanarity (allows small geometries more flexibility)
2. Using **absolute overshoot limit** for bend point ranges (catches extreme cases like 90mm overshoot)
3. Maintaining strict filtering for degenerate cases while allowing valid small-geometry solutions

# Two-Bend Strategies Analysis

## Overview

The `two_bends()` function implements TWO distinct approaches to create double-bend connections between tabs via an intermediate triangular tab (tab_y):

1. **APPROACH 1**: 90-degree perpendicular plane (lines 420-686)
2. **APPROACH 2**: Corner connection fallback (lines 688-987)

---

## APPROACH 1: 90-Degree Perpendicular Plane

### Goal
Create intermediate plane B that is perpendicular (90°) to both plane A (tab_x) and plane C (tab_z).

### Edge Selection

**tab_x edges**: All 8 combinations (forward + reverse)
```python
rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),  # Forward
                ('B', 'A'), ('C', 'B'), ('D', 'C'), ('A', 'D')]  # Reverse
```

**tab_z edges**: All 8 combinations (forward + reverse)
```python
rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),  # Forward
                ('B', 'A'), ('C', 'B'), ('D', 'C'), ('A', 'D')]  # Reverse
```

**Total combinations**: 8 × 8 = 64 edge pairs tested

### BP (Bend Point) Calculation

**For tab_x**:
```python
# Calculate outward direction perpendicular to edge
out_dir_x = normalize(cross(edge_x_vec, plane_x.orientation))
# Ensure outward points away from rectangle center
if dot(out_dir_x, edge_x_mid - rect_x_center) < 0:
    out_dir_x = -out_dir_x

# Shift distance calculation
if is_x_growing:
    shift_dist_x = abs(dist_along_normal_B) + min_flange_length
else:
    shift_dist_x = min_flange_length

# Shifted bending points
BPxL = CPxL + out_dir_x * shift_dist_x
BPxR = CPxR + out_dir_x * shift_dist_x
```

**For tab_z**: Same logic as tab_x

**Intermediate plane B**:
```python
# Constructed from shifted bend points
plane_y = calculate_plane(triangle={"A": BPxL, "B": BPxR, "C": BPzL})
```

### FP (Flange Point) Calculation

**Method**: Uses `calculate_flange_points_with_angle_check()`
- FP at `min_flange_length` perpendicular from BP toward respective plane
- Returns: `FPxyL, FPxyR, FPyxL, FPyxR` (for x-y connection)
- Returns: `FPyzL, FPyzR, FPzyL, FPzyR` (for y-z connection)

**CRITICAL ISSUE**: FP values are **CALCULATED but NOT USED**!

### Tab Augmentation Logic

#### Tab X (lines 539-591)
```
Structure: [A, B, C, D] → [A, FP_L, BP_L, BP_R, FP_R, B, C, D]

Insertion:
- If wrap-around (D→A or A→D): Insert after D
- If normal (idx_R > idx_L): Insert after L (first corner)
- If reverse (idx_L > idx_R): Insert after R (first corner)

FP Assignment: **USES CORNER POINTS (CPxL, CPxR)** ← NOT Direct Power Flows!
```

**Example (edge A→B)**:
```python
bend_points_x = {
    f"FP{tab_x_id}_{tab_y_id}L": CPxL,  # FP at corner A (WRONG!)
    f"BP{tab_x_id}_{tab_y_id}L": BPxL,  # BP shifted outward
    f"BP{tab_x_id}_{tab_y_id}R": BPxR,  # BP shifted outward
    f"FP{tab_x_id}_{tab_y_id}R": CPxR   # FP at corner B (WRONG!)
}
```

#### Tab Y (Intermediate) (lines 593-621)
```
Structure: FP_yxL, BP_xL, BP_xR, FP_yxR, FP_yzR, BP_zR, BP_zL, FP_yzL

Point ordering:
- Uses diagonals_cross_3d() to detect self-intersections
- If diagonals cross: Swap z-side L/R
- Creates closed perimeter around triangular intermediate tab

FP Assignment: **USES CALCULATED FP VALUES (FPyxL, FPyxR, FPyzL, FPyzR)** ← Direct Power Flows ✓
```

#### Tab Z (lines 623-679)
```
Structure: [A, B, C, D] → [A, B, C, D, FP_L, BP_L, BP_R, FP_R]

Insertion:
- Uses ORIGINAL corner IDs (before any z_swapped correction)
- If wrap-around: Insert after higher index corner
- If normal: Insert after L (first corner)
- If reverse: Insert after R (first corner)

FP Assignment: **USES CORNER POINTS (CPzL, CPzR)** ← NOT Direct Power Flows!

Corner Removal: NONE (all corners kept)
```

**Z-Swapping Logic** (lines 521-529):
```python
# If tab_x L connects better to tab_z R, swap z-side
dist_xL_zL = norm(BPxL - BPzL)
dist_xL_zR = norm(BPxL - BPzR)
if dist_xL_zR < dist_xL_zL:
    BPzL, BPzR = BPzR, BPzL  # Swap BP
    FPyzL, FPyzR = FPyzR, FPyzL  # Swap FP
    CPzL, CPzR = CPzR, CPzL  # Swap corners
```

### Filters
1. ✓ Perpendicularity check (within 5° of 90°) - lines 481-492
2. ✓ Minimum flange width - lines 494-498
3. ✓ Minimum bend angle - lines 501-505
4. ✓ Angle checks in FP calculation - lines 511, 517
5. ✓ Duplicate segment check - line 683

### Expected Results
- Works when edges can be shifted to create perpendicular intermediate plane
- Produces clean 90° bends
- **FP points at corner positions** (duplicates corners) ← Inconsistent with one_bend!
- All corners preserved

---

## APPROACH 2: Corner Connection Fallback

### Goal
Create connections when 90° approach fails (planes not perpendicular or edges don't align).

### Edge Selection

**tab_x edges**: All 8 combinations (same as Approach 1)
```python
rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),
                ('B', 'A'), ('C', 'B'), ('D', 'C'), ('A', 'D')]
```

**tab_z "edges"**: **DIFFERENT LOGIC - Iterates through CORNERS, not edges!**
```python
for i, CPzM_id in enumerate(rect_z.points):  # M = A, B, C, D
    CPzM = rect_z.points[CPzM_id]
    CPzL_id = (i - 1) % 4  # Left neighbor
    CPzR_id = (i + 1) % 4  # Right neighbor
```

**Example** (when M=A):
- CPzM = A (to be removed)
- CPzL = D (left neighbor)
- CPzR = B (right neighbor)
- Creates edge D→B (after removing A)

**Total combinations**: 8 × 4 = 32 (fewer than Approach 1)

### BP (Bend Point) Calculation

**For tab_x** (same as Approach 1):
```python
out_dir_x = normalize(cross(edge_x_vec, plane_x.orientation))
# Ensure outward
if dot(out_dir_x, edge_x_mid - rect_x_center) < 0:
    out_dir_x = -out_dir_x

BPxL = CPxL + out_dir_x * min_flange_length
BPxR = CPxR + out_dir_x * min_flange_length
```

**For tab_z** (COMPLEX logic - lines 727-780):

**Case 1: Non-parallel** (line_plane_intersection succeeds):
```python
# Project bend_xy line onto plane_z
projection_point = line_plane_intersection(BPxL, BPxL - BPxR, plane_z)

# Calculate BPzM using circle intersection geometry
vec_PP_CP = CPzM - projection_point
c = norm(vec_PP_CP)
a = min_flange_length

if c > a:  # Circle intersection possible
    b = sqrt(c² - a²)
    d = (b² - a² + c²) / (2c)
    h = sqrt(b² - d²)

    # Two solutions (choose one farther from center)
    sol1 = projection_point + d*u + h*v
    sol2 = projection_point + d*u - h*v
    BPzM = sol1 or sol2 (farther from rect_z_center)
```

**Case 2: Parallel fallback** (lines 766-780):
```python
# Planes parallel - use orthogonal direction
ortho_dir = normalize(cross(bend_xy.orientation, plane_z.orientation))
# Ensure outward
if dot(ortho_dir, CPzM - rect_z_center) < 0:
    ortho_dir = -ortho_dir

BPzM = CPzM + ortho_dir * min_flange_length
```

**BPzL and BPzR**:
```python
# Project neighbors onto bend_yz line
BPzL = project_onto_line(CPzL, bend_yz.position, bend_yz.orientation)
BPzR = project_onto_line(CPzR, bend_yz.position, bend_yz.orientation)
```

### FP (Flange Point) Calculation

**Method**: Uses `calculate_flange_points_with_angle_check()`
- FP at `min_flange_length` perpendicular from BP
- Returns calculated values: `FPxyL, FPxyR, FPyxL, FPyxR, FPyzL, FPyzR, FPzyL, FPzyR`

**CRITICAL ISSUE**: FP values are **CALCULATED but NOT USED** for tab_x and tab_z!

### Tab Augmentation Logic

#### Tab X (lines 815-868)
```
Structure: [A, B, C, D] → [A, FP_L, BP_L, BP_R, FP_R, B, C, D]

Insertion: Same logic as Approach 1
- Wrap-around: Insert after D
- Normal: Insert after L
- Reverse: Insert after R

FP Assignment: **USES CORNER POINTS (CPxL, CPxR)** ← NOT Direct Power Flows!

Corner Removal: NONE
```

#### Tab Y (Intermediate) (lines 870-898)
```
Structure: FP_yxL, BP_xL, BP_xR, FP_yxR, FP_yzR, BP_zR, BP_zL, FP_yzL

Point ordering:
- Same diagonals_cross_3d() logic as Approach 1
- Swaps z-side L/R if diagonals cross

FP Assignment: **USES CALCULATED FP VALUES** ← Direct Power Flows ✓
```

#### Tab Z (lines 900-968)
```
Structure: [A, B, C, D] → [B, C, D, FP_L, BP_L, BP_R, FP_R]
(Example when M=A is removed)

Insertion:
- IMPROVED wrap-around detection: abs(idx_L - idx_R) > 1
- Handles D→B, C→A, etc. (multi-step wraps)
- Uses lines_cross() check to swap L/R if needed

FP Assignment: **USES CORNER POINTS (CPzL, CPzR)** ← NOT Direct Power Flows!

Corner Removal: **YES - Removes CPzM** (line 764)
```

**Wrap-Around Detection**:
```python
# Improved detection for fallback approach
is_wraparound_z_fb = abs(idx_zL_fb - idx_zR_fb) > 1

# Examples:
# D→B: abs(3-1) = 2 > 1 ✓ wrap-around
# C→A: abs(2-0) = 2 > 1 ✓ wrap-around
# A→B: abs(0-1) = 1 ≤ 1 ✗ normal
```

**Lines Cross Check** (line 942):
```python
z_lines_cross = lines_cross(FPyzL, CPzL, CPzR, FPyxR)
if z_lines_cross:
    # Swap L/R ordering
    base_order_fb = "R_to_L" if base_order_fb == "L_to_R" else "L_to_R"
```

### Filters
1. ✓ Minimum flange width (tab_x) - line 718
2. ✓ Minimum bend angle - lines 792-796
3. ✓ Angle checks in FP calculation - lines 802, 812
4. ✓ Minimum flange width (tab_z) - line 806
5. ✓ Tab containment check (optional) - lines 971-975
6. ✓ Thin segment filter (optional) - lines 978-980
7. ✓ Duplicate segment check - line 984

### Expected Results
- Works when 90° approach fails
- Handles parallel planes
- Removes one corner from tab_z (CPzM)
- More complex geometry (non-perpendicular bends)
- **FP points at corner positions** (duplicates corners) ← Inconsistent with one_bend!

---

## Critical Issues Identified

### Issue 1: FP Point Assignment Inconsistency

**one_bend()**: Uses calculated FP values at `min_flange_length` from bend axis ✓
```python
bend_points_x = {
    f"FP{tab_x_id}_{tab_z_id}L": FPxL,  # Calculated value
    ...
}
```

**two_bends() (BOTH approaches)**: Uses corner points for FP ✗
```python
bend_points_x = {
    f"FP{tab_x_id}_{tab_y_id}L": CPxL,  # Corner point!
    ...
}
```

**Impact**:
- two_bend creates FP-corner duplicates (inconsistent with Direct Power Flows)
- Different geometry than one_bend for same connection type
- Calculated FP values are wasted (computed but never used)

### Issue 2: Corner Removal Inconsistency

**Approach 1 (90-degree)**: Keeps all corners ✓
- tab_x: [A, FP_L, BP_L, BP_R, FP_R, B, C, D]
- tab_z: [A, B, C, D, FP_L, BP_L, BP_R, FP_R]

**Approach 2 (fallback)**: Removes CPzM from tab_z ✗
- tab_x: [A, FP_L, BP_L, BP_R, FP_R, B, C, D]
- tab_z: [B, C, D, FP_L, BP_L, BP_R, FP_R] (A removed)

**Impact**:
- Inconsistent tab structure between approaches
- May cause issues if user expects all corners to be preserved
- Different perimeter topology

### Issue 3: Edge Selection Asymmetry (Approach 2)

**tab_x**: Uses explicit edge pairs (8 combinations)
**tab_z**: Uses corner iteration with neighbors (4 combinations)

**Impact**:
- Fewer solutions tested (32 vs 64)
- Different logic for same conceptual operation
- Harder to understand and maintain

### Issue 4: Intermediate Tab (tab_y) Inconsistency

**Point structure**:
- Uses calculated FP values ✓ (correct for Direct Power Flows)
- But parent tabs (tab_x, tab_z) use corner points ✗

**Impact**:
- Intermediate tab follows Direct Power Flows
- But original tabs don't
- Mixed geometry approaches in same segment

---

## Comparison Table

| Aspect | one_bend | two_bend Approach 1 | two_bend Approach 2 |
|--------|----------|-------------------|-------------------|
| **FP for tab_x** | Calculated (FPxL/R) ✓ | Corner (CPxL/R) ✗ | Corner (CPxL/R) ✗ |
| **FP for tab_z** | Calculated (FPzL/R) ✓ | Corner (CPzL/R) ✗ | Corner (CPzL/R) ✗ |
| **FP for tab_y** | N/A | Calculated ✓ | Calculated ✓ |
| **Corner removal (tab_x)** | None ✓ | None ✓ | None ✓ |
| **Corner removal (tab_z)** | None ✓ | None ✓ | CPzM removed ✗ |
| **Edge selection** | 8×8 = 64 | 8×8 = 64 | 8×4 = 32 |
| **Wrap-around detection** | Simple | Simple | Improved |
| **Perpendicularity** | Not required | Required (90°) | Not required |
| **Lines cross check** | Yes | No | Yes |

---

## Recommendations

### 1. Make FP Assignment Consistent with Direct Power Flows

Both two_bend approaches should use **calculated FP values**, not corner points:

```python
# CHANGE THIS (Approach 1, line 555):
f"FP{tab_x_id}_{tab_y_id}L": CPxL,  # ✗ Corner point

# TO THIS:
f"FP{tab_x_id}_{tab_y_id}L": FPxyL,  # ✓ Calculated FP
```

Same for:
- Approach 1: tab_x (lines 555-578), tab_z (lines 643-677)
- Approach 2: tab_x (lines 831-865), tab_z (lines 953-963)

### 2. Decide on Corner Removal Policy

**Option A**: Keep all corners (like one_bend and Approach 1)
- Remove line 764: `new_tab_z.remove_point(point={CPzM_id: CPzM})`

**Option B**: Document why corner is removed in fallback
- Add comments explaining the geometric reason
- May be necessary for the fallback geometry to work

### 3. Consider Unified Edge Selection

Make tab_z edge selection consistent with tab_x in Approach 2:
- Use explicit edge pairs instead of corner iteration
- Or use corner iteration for both (but document why)

### 4. Add Distance/Clearance Filter

Like one_bend, add filter to ensure flanges don't interfere:
```python
# Check FP clearance from opposite plane
min_clearance = min_flange_length * 0.5
if dist_FP_to_opposite_plane < min_clearance:
    continue
```

---

## Questions for Clarification

1. **Should two_bend use Direct Power Flows (calculated FP) like one_bend?**
   - If yes: Update all four FP assignment locations
   - If no: Why should they differ?

2. **Should corner CPzM be removed in fallback approach?**
   - Current: Removed (line 764)
   - Alternative: Keep all corners like Approach 1

3. **Is the asymmetric edge selection intentional?**
   - tab_x: 8 edges
   - tab_z: 4 corners → creates only 4 "edges"

4. **Should perpendicularity check be relaxed for Approach 1?**
   - Current: Requires 90° ± 5°
   - Alternative: Accept wider range of angles

---

## Summary

Both two_bend approaches have the same fundamental issue: **FP points are calculated correctly but then REPLACED with corner points**, making the implementation inconsistent with the Direct Power Flows principle implemented in one_bend.

The fallback approach additionally:
- Removes a corner from tab_z (inconsistent with Approach 1)
- Uses different edge selection logic
- Has improved wrap-around detection

To align with your specification, the FP assignment should be changed to use the calculated values (FPxyL/R, FPyzL/R) instead of corner points (CPxL/R, CPzL/R).

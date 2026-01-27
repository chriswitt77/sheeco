"""
Compare the geometry of with_mounts (valid but filtered) vs transportschuh degenerate case.
"""

import numpy as np
from config.user_input import with_mounts, transportschuh
from src.hgen_sm import initialize_objects
from src.hgen_sm.create_segments.utils import normalize

print("="*80)
print("COMPARING with_mounts (VALID) vs transportschuh DEGENERATE")
print("="*80)

# ===== with_mounts - B-C x D-A (filtered by bend_point_range) =====
print("\n" + "="*80)
print("with_mounts - B-C x D-A (filtered by bend_point_range)")
print("="*80)

part_wm = initialize_objects(with_mounts)
tab_0_wm = part_wm.tabs['0']
tab_1_wm = part_wm.tabs['1']

corners_0_wm = np.array([tab_0_wm.points[k] for k in ['A', 'B', 'C', 'D']])
corners_1_wm = np.array([tab_1_wm.points[k] for k in ['A', 'B', 'C', 'D']])

# Tab dimensions
tab_0_size = np.max(corners_0_wm, axis=0) - np.min(corners_0_wm, axis=0)
tab_1_size = np.max(corners_1_wm, axis=0) - np.min(corners_1_wm, axis=0)

print(f"\nTab 0 size: [{tab_0_size[0]:.1f}, {tab_0_size[1]:.1f}, {tab_0_size[2]:.1f}]")
print(f"Tab 1 size: [{tab_1_size[0]:.1f}, {tab_1_size[1]:.1f}, {tab_1_size[2]:.1f}]")

# Bend points that were filtered
BPzL_wm = np.array([0.0, 110.0, 80.0])
BPzR_wm = np.array([0.0, 110.0, 40.0])

tab_1_bounds_wm = [np.min(corners_1_wm, axis=0), np.max(corners_1_wm, axis=0)]
print(f"\nTab 1 bounds: [{tab_1_bounds_wm[0]}, {tab_1_bounds_wm[1]}]")
print(f"BPzL: {BPzL_wm}")
print(f"BPzR: {BPzR_wm}")

# How far outside bounds?
overshoot_y = BPzL_wm[1] - tab_1_bounds_wm[1][1]
tab_1_range_y = tab_1_bounds_wm[1][1] - tab_1_bounds_wm[0][1]
overshoot_ratio = overshoot_y / tab_1_range_y

print(f"\nOvershoot in y: {overshoot_y:.1f} mm beyond tab bounds")
print(f"Tab 1 y-range: {tab_1_range_y:.1f} mm")
print(f"Overshoot ratio: {overshoot_ratio:.2f} (75% beyond range)")

# Distance from tab edge to bend points
distance_from_edge = overshoot_y
print(f"Distance from tab edge to bend points: {distance_from_edge:.1f} mm")

# ===== with_mounts - D-A x B-C (filtered by edge_coplanarity) =====
print("\n" + "="*80)
print("with_mounts - D-A x B-C (filtered by edge_coplanarity)")
print("="*80)

CPxL = tab_0_wm.points['D']  # [100, 0, 0]
CPxR = tab_0_wm.points['A']  # [50, 0, 0]
CPzL = tab_1_wm.points['B']  # [0, 40, 40]
CPzR = tab_1_wm.points['C']  # [0, 40, 80]

points_wm = np.array([CPxL, CPxR, CPzL, CPzR])
centroid_wm = np.mean(points_wm, axis=0)
centered_wm = points_wm - centroid_wm
_, _, vh_wm = np.linalg.svd(centered_wm)
fitted_normal_wm = vh_wm[-1]
fitted_normal_wm = normalize(fitted_normal_wm)
distances_wm = [abs(np.dot(p - centroid_wm, fitted_normal_wm)) for p in points_wm]
max_dist_wm = max(distances_wm)

print(f"\nEdge corner points:")
print(f"  CPxL (D): {CPxL}")
print(f"  CPxR (A): {CPxR}")
print(f"  CPzL (B): {CPzL}")
print(f"  CPzR (C): {CPzR}")

print(f"\nCoplanarity analysis:")
print(f"  Max distance from fitted plane: {max_dist_wm:.3f} mm")
print(f"  Individual distances: {[f'{d:.3f}' for d in distances_wm]}")
print(f"  Current tolerance: 5.0 mm")
print(f"  Failed by: {max_dist_wm - 5.0:.3f} mm")

# What's the geometry here?
edge_x_vec = CPxR - CPxL
edge_z_vec = CPzR - CPzL
print(f"\nEdge vectors:")
print(f"  Tab 0 edge (D-A): {edge_x_vec}")
print(f"  Tab 1 edge (B-C): {edge_z_vec}")
print(f"  Edge perpendicularity: {abs(np.dot(normalize(edge_x_vec), normalize(edge_z_vec))):.3f}")

# ===== transportschuh DEGENERATE - D-A x C-D (successfully filtered) =====
print("\n" + "="*80)
print("transportschuh DEGENERATE - D-A x C-D (correctly filtered)")
print("="*80)

part_ts = initialize_objects(transportschuh)
tab_0_ts = part_ts.tabs['0']
tab_1_ts = part_ts.tabs['1']

corners_0_ts = np.array([tab_0_ts.points[k] for k in ['A', 'B', 'C', 'D']])
corners_1_ts = np.array([tab_1_ts.points[k] for k in ['A', 'B', 'C', 'D']])

tab_0_size_ts = np.max(corners_0_ts, axis=0) - np.min(corners_0_ts, axis=0)
tab_1_size_ts = np.max(corners_1_ts, axis=0) - np.min(corners_1_ts, axis=0)

print(f"\nTab 0 size: [{tab_0_size_ts[0]:.1f}, {tab_0_size_ts[1]:.1f}, {tab_0_size_ts[2]:.1f}]")
print(f"Tab 1 size: [{tab_1_size_ts[0]:.1f}, {tab_1_size_ts[1]:.1f}, {tab_1_size_ts[2]:.1f}]")

# The degenerate bend points
BPzL_ts = np.array([-10.0, 180.0, 290.0])  # Approximate from earlier debug
BPzR_ts = np.array([-10.0, 180.0, 290.0])

tab_1_bounds_ts = [np.min(corners_1_ts, axis=0), np.max(corners_1_ts, axis=0)]
print(f"\nTab 1 bounds: [{tab_1_bounds_ts[0]}, {tab_1_bounds_ts[1]}]")
print(f"BPzL (degenerate): {BPzL_ts}")

overshoot_z_ts = BPzL_ts[2] - tab_1_bounds_ts[1][2]
tab_1_range_z_ts = tab_1_bounds_ts[1][2] - tab_1_bounds_ts[0][2]
overshoot_ratio_ts = overshoot_z_ts / tab_1_range_z_ts

print(f"\nOvershoot in z: {overshoot_z_ts:.1f} mm beyond tab bounds")
print(f"Tab 1 z-range: {tab_1_range_z_ts:.1f} mm")
print(f"Overshoot ratio: {overshoot_ratio_ts:.2f} (56% beyond range)")

# ===== COMPARISON =====
print("\n" + "="*80)
print("KEY DIFFERENCES")
print("="*80)

print(f"""
1. BEND POINT OVERSHOOT:
   with_mounts (VALID):
     - Overshoot: {overshoot_y:.1f} mm
     - Tab range: {tab_1_range_y:.1f} mm
     - Overshoot ratio: {overshoot_ratio:.2f} ({overshoot_ratio*100:.0f}% of tab size)
     - Distance from edge: {distance_from_edge:.1f} mm

   transportschuh (DEGENERATE):
     - Overshoot: {overshoot_z_ts:.1f} mm
     - Tab range: {tab_1_range_z_ts:.1f} mm
     - Overshoot ratio: {overshoot_ratio_ts:.2f} ({overshoot_ratio_ts*100:.0f}% of tab size)

   Analysis: Both have significant overshoot, but transportschuh is much worse
   in absolute terms (90mm vs 30mm).

2. EDGE COPLANARITY:
   with_mounts:
     - Max deviation: {max_dist_wm:.3f} mm
     - Failed tolerance by: {max_dist_wm - 5.0:.3f} mm
     - This is a 3D geometry with tabs at different planes

   transportschuh degenerate:
     - Was caught by coplanarity check
     - Edges don't form valid perpendicular connection plane

3. ABSOLUTE VS RELATIVE METRICS:
   The key question: Should we use:
     a) Absolute distance thresholds (current: 5mm coplanarity, 30% margin)?
     b) Relative to tab size or connection distance?
     c) A combination of both?

4. GEOMETRY CHARACTERISTICS:
   with_mounts has smaller tabs and tighter geometry:
     - Tab 0: 50x100 mm
     - Tab 1: 40x40 mm

   transportschuh has larger tabs:
     - Tab 0: 150x160 mm
     - Tab 1: 160x160 mm

   The same absolute tolerance affects them differently!
""")

print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)

print("""
The core issue is that my validation checks use ABSOLUTE thresholds that don't
scale with geometry size. This causes:
  1. Small geometries (with_mounts) to be over-filtered
  2. Large geometries (transportschuh) to be correctly filtered

Potential solutions:
  1. Make tolerances RELATIVE to tab dimensions
  2. Use HYBRID approach: absolute minimum + relative scaling
  3. Adjust coplanarity tolerance from 5mm to 10mm (simple but less rigorous)
  4. Make bend_point_range_margin larger (0.3 → 0.75)

The transportschuh degenerate case was caught by coplanarity check with
max_dist > 5mm, so we need to preserve that. But with_mounts fails at 7.5mm,
which is marginal.

For bend point range, with_mounts overshoots by 30mm (75% of range) while
transportschuh overshoots by 90mm (56% of range). Current 30% margin is too
strict for both cases.
""")

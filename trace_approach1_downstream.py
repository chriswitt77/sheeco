"""
Trace downstream filters in Approach 1 to find where all 48 edge combinations get rejected.
We'll add instrumentation to the actual two_bends function.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import barda_example_one
from src.hgen_sm import initialize_objects, Part
from src.hgen_sm.create_segments.bend_strategies import calculate_plane, normalize

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("TRACE DOWNSTREAM FILTERS IN APPROACH 1")
print("="*80)

part = initialize_objects(barda_example_one)
pair = ['0', '1']

tab_x = part.tabs[pair[0]]
tab_z = part.tabs[pair[1]]

# Manually trace through one successful edge combination from the previous test
# Let's use the first one that passed: tab_x[A->B] x tab_z[A->B]

CPxL_id, CPxR_id = 'A', 'B'
CPzL_id, CPzR_id = 'A', 'B'

print(f"\nTracing edge combination: tab_x[{CPxL_id}->{CPxR_id}] x tab_z[{CPzL_id}->{CPzR_id}]")

CPxL = tab_x.points[CPxL_id]
CPxR = tab_x.points[CPxR_id]
CPzL = tab_z.points[CPzL_id]
CPzR = tab_z.points[CPzR_id]

edge_x_vec = CPxR - CPxL
edge_z_vec = CPzR - CPzL
edge_x_mid = (CPxL + CPxR) / 2
edge_z_mid = (CPzL + CPzR) / 2

rect_x = tab_x.rectangle
rect_z = tab_z.rectangle
plane_x = calculate_plane(rect_x)
plane_z = calculate_plane(rect_z)

rect_x_corners = [tab_x.points[k] for k in ['A', 'B', 'C', 'D']]
rect_z_corners = [tab_z.points[k] for k in ['A', 'B', 'C', 'D']]
rect_x_center = np.mean(rect_x_corners, axis=0)
rect_z_center = np.mean(rect_z_corners, axis=0)

# Calculate normal_B
normal_B = np.cross(plane_x.orientation, plane_z.orientation)
if np.linalg.norm(normal_B) < 1e-6:
    normal_B = np.cross(plane_x.orientation, edge_x_vec)
normal_B = normalize(normal_B)

print(f"\nIntermediate plane normal_B: {normal_B}")

# Calculate outward directions
out_dir_x = np.cross(edge_x_vec, plane_x.orientation)
out_dir_x = normalize(out_dir_x)
if np.dot(out_dir_x, edge_x_mid - rect_x_center) < 0:
    out_dir_x = -out_dir_x

out_dir_z = np.cross(edge_z_vec, plane_z.orientation)
out_dir_z = normalize(out_dir_z)
if np.dot(out_dir_z, edge_z_mid - rect_z_center) < 0:
    out_dir_z = -out_dir_z

connection_vec = edge_z_mid - edge_x_mid
dist_along_normal_B = np.dot(connection_vec, normal_B)

print(f"Connection vector: {connection_vec}")
print(f"Distance along normal_B: {dist_along_normal_B:.2f}")

# Get min flange lengths
min_flange_length_x = segment_cfg.get('flange_length_min', 10.0)
min_flange_length_z = segment_cfg.get('flange_length_min', 10.0)

# Calculate shift distances
shift_dist_x = min_flange_length_x
shift_dist_z = min_flange_length_z

# Shift edges outward
edge_x_mid_shifted = edge_x_mid + shift_dist_x * out_dir_x
edge_z_mid_shifted = edge_z_mid + shift_dist_z * out_dir_z

BPL_x = CPxL + shift_dist_x * out_dir_x
BPR_x = CPxR + shift_dist_x * out_dir_x
BPL_z = CPzL + shift_dist_z * out_dir_z
BPR_z = CPzR + shift_dist_z * out_dir_z

print(f"\nBend points (shifted outward):")
print(f"  BPL_x: {BPL_x}")
print(f"  BPR_x: {BPR_x}")
print(f"  BPL_z: {BPL_z}")
print(f"  BPR_z: {BPR_z}")

# Project onto plane B to find corners
def project_to_plane(point, plane_point, plane_normal):
    """Project a point onto a plane."""
    v = point - plane_point
    dist = np.dot(v, plane_normal)
    return point - dist * plane_normal

# Use edge_x_mid_shifted as plane_point_B
plane_point_B = edge_x_mid_shifted + (dist_along_normal_B / 2.0) * normal_B

print(f"\nIntermediate plane B point: {plane_point_B}")

# Project bend points onto plane B
BP_0L = project_to_plane(BPL_x, plane_point_B, normal_B)
BP_0R = project_to_plane(BPR_x, plane_point_B, normal_B)
BP_1L = project_to_plane(BPL_z, plane_point_B, normal_B)
BP_1R = project_to_plane(BPR_z, plane_point_B, normal_B)

print(f"\nIntermediate tab corners (projected onto plane B):")
print(f"  BP_0L: {BP_0L}")
print(f"  BP_0R: {BP_0R}")
print(f"  BP_1L: {BP_1L}")
print(f"  BP_1R: {BP_1R}")

# ========== DOWNSTREAM FILTER 1: Edge Coplanarity ==========
print(f"\n{'='*80}")
print(f"FILTER 1: Edge Coplanarity")
print(f"{'='*80}")

# Check if 4 corners form a plane perpendicular to both A and C
four_points = np.array([BP_0L, BP_0R, BP_1L, BP_1R])
centroid = four_points.mean(axis=0)
centered = four_points - centroid

# SVD to find best-fit plane
U, S, Vt = np.linalg.svd(centered, full_matrices=False)
fitted_normal = Vt[-1]  # Normal is last row (smallest singular value)

# Calculate residuals
residuals = np.abs(centered @ fitted_normal)
max_residual = residuals.max()

# Adaptive tolerance
connection_dist = np.linalg.norm(edge_z_mid - edge_x_mid)
coplanarity_base = filter_cfg.get('edge_coplanarity_tolerance', 5.0)
coplanarity_relative = filter_cfg.get('edge_coplanarity_relative_tolerance', 0.1)
tolerance = max(coplanarity_base, coplanarity_relative * connection_dist)

print(f"  Connection distance: {connection_dist:.2f}")
print(f"  Adaptive tolerance: {tolerance:.2f}")
print(f"  Max residual (deviation from plane): {max_residual:.2f}")
print(f"  Coplanar? {max_residual <= tolerance}")

if max_residual > tolerance:
    print(f"  [FILTERED] Four corners not coplanar")
else:
    print(f"  [PASSED] Coplanarity check")

    # Check perpendicularity to both planes
    angle_tol = np.radians(20)
    angle_x = np.arccos(np.clip(abs(np.dot(fitted_normal, plane_x.orientation)), 0, 1))
    angle_z = np.arccos(np.clip(abs(np.dot(fitted_normal, plane_z.orientation)), 0, 1))

    print(f"  Angle to plane_x: {np.degrees(angle_x):.2f}°")
    print(f"  Angle to plane_z: {np.degrees(angle_z):.2f}°")
    print(f"  Perpendicular to both? {abs(angle_x - np.pi/2) <= angle_tol and abs(angle_z - np.pi/2) <= angle_tol}")

    if abs(angle_x - np.pi/2) > angle_tol or abs(angle_z - np.pi/2) > angle_tol:
        print(f"  [FILTERED] Not perpendicular to both input planes")
    else:
        print(f"  [PASSED] Perpendicularity check")

# ========== DOWNSTREAM FILTER 2: Bend Point Range ==========
print(f"\n{'='*80}")
print(f"FILTER 2: Bend Point Range")
print(f"{'='*80}")

# Check if bend points are within reasonable distance from tabs
bp_max_overshoot = segment_cfg.get('bend_point_max_absolute_overshoot', 50.0)

# For tab_x, check BPL_x and BPR_x
tab_x_corners_array = np.array(rect_x_corners)
min_x = tab_x_corners_array.min(axis=0)
max_x = tab_x_corners_array.max(axis=0)

overshoot_x_L = np.maximum(min_x - BPL_x, BPL_x - max_x)
overshoot_x_L = np.maximum(overshoot_x_L, 0)
overshoot_x_R = np.maximum(min_x - BPR_x, BPR_x - max_x)
overshoot_x_R = np.maximum(overshoot_x_R, 0)

max_overshoot_x = max(np.max(overshoot_x_L), np.max(overshoot_x_R))

print(f"  Tab X bend points:")
print(f"    Overshoot BPL_x: {overshoot_x_L}")
print(f"    Overshoot BPR_x: {overshoot_x_R}")
print(f"    Max overshoot: {max_overshoot_x:.2f} (threshold: {bp_max_overshoot})")

if max_overshoot_x > bp_max_overshoot:
    print(f"  [FILTERED] Tab X bend points exceed max overshoot")
else:
    print(f"  [PASSED] Tab X bend point range")

# For tab_z, check BPL_z and BPR_z
tab_z_corners_array = np.array(rect_z_corners)
min_z = tab_z_corners_array.min(axis=0)
max_z = tab_z_corners_array.max(axis=0)

overshoot_z_L = np.maximum(min_z - BPL_z, BPL_z - max_z)
overshoot_z_L = np.maximum(overshoot_z_L, 0)
overshoot_z_R = np.maximum(min_z - BPR_z, BPR_z - max_z)
overshoot_z_R = np.maximum(overshoot_z_R, 0)

max_overshoot_z = max(np.max(overshoot_z_L), np.max(overshoot_z_R))

print(f"\n  Tab Z bend points:")
print(f"    Overshoot BPL_z: {overshoot_z_L}")
print(f"    Overshoot BPR_z: {overshoot_z_R}")
print(f"    Max overshoot: {max_overshoot_z:.2f} (threshold: {bp_max_overshoot})")

if max_overshoot_z > bp_max_overshoot:
    print(f"  [FILTERED] Tab Z bend points exceed max overshoot")
else:
    print(f"  [PASSED] Tab Z bend point range")

# ========== DOWNSTREAM FILTER 3: Aspect Ratio ==========
print(f"\n{'='*80}")
print(f"FILTER 3: Intermediate Tab Aspect Ratio")
print(f"{'='*80}")

# Calculate dimensions of intermediate tab
edge_0 = np.linalg.norm(BP_0R - BP_0L)
edge_1 = np.linalg.norm(BP_1R - BP_1L)
side_L = np.linalg.norm(BP_1L - BP_0L)
side_R = np.linalg.norm(BP_1R - BP_0R)

print(f"  Edge 0 (tab_x side): {edge_0:.2f}")
print(f"  Edge 1 (tab_z side): {edge_1:.2f}")
print(f"  Side L: {side_L:.2f}")
print(f"  Side R: {side_R:.2f}")

max_dim = max(edge_0, edge_1, side_L, side_R)
min_dim = min(edge_0, edge_1, side_L, side_R)

if min_dim > 0:
    aspect_ratio = max_dim / min_dim
    print(f"  Aspect ratio: {aspect_ratio:.2f}")

    max_aspect = segment_cfg.get('max_aspect_ratio', 10.0)
    print(f"  Max aspect ratio: {max_aspect}")

    if aspect_ratio > max_aspect:
        print(f"  [FILTERED] Aspect ratio too high")
    else:
        print(f"  [PASSED] Aspect ratio check")
else:
    print(f"  [ERROR] min_dim is zero!")

print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")
print(f"\nRun this trace for multiple edge combinations to identify the")
print(f"consistent filtering pattern that's rejecting all 48 combinations.")

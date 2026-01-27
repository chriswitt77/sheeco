"""
Debug why Approach 1 still doesn't generate solutions after the fix.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane
from src.hgen_sm.create_segments.utils import normalize
from config.design_rules import min_flange_length

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("DEBUGGING APPROACH 1 AFTER FIX")
print("="*80)

# Initialize part
part = initialize_objects(transportschuh)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)

# Calculate centers
rect_x_corners = [tab_0.points[k] for k in ['A', 'B', 'C', 'D']]
rect_z_corners = [tab_1.points[k] for k in ['A', 'B', 'C', 'D']]
rect_x_center = np.mean(rect_x_corners, axis=0)
rect_z_center = np.mean(rect_z_corners, axis=0)

# Test edges
rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]
rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]

print(f"\nConfiguration:")
print(f"  antiparallel_threshold: {segment_cfg.get('two_bend_antiparallel_threshold', -0.8)}")

filter_reasons = {
    'not_perpendicular': 0,
    'antiparallel': 0,
    'plane_not_perpendicular': 0,
    'flange_width': 0,
    'bend_angle': 0,
    'success': 0
}

for pair_x in rect_x_edges:
    CPxL_id, CPxR_id = pair_x
    CPxL = tab_0.points[CPxL_id]
    CPxR = tab_0.points[CPxR_id]
    edge_x_vec = CPxR - CPxL
    edge_x_mid = (CPxL + CPxR) / 2

    for pair_z in rect_z_edges:
        CPzL_id, CPzR_id = pair_z
        CPzL = tab_1.points[CPzL_id]
        CPzR = tab_1.points[CPzR_id]
        edge_z_vec = CPzR - CPzL
        edge_z_mid = (CPzL + CPzR) / 2

        # Check if edges are perpendicular
        edge_x_norm = normalize(edge_x_vec)
        edge_z_norm = normalize(edge_z_vec)
        dot_edges = abs(np.dot(edge_x_norm, edge_z_norm))

        if dot_edges >= 0.1:
            filter_reasons['not_perpendicular'] += 1
            continue

        # Calculate normal for intermediate plane
        normal_B = np.cross(plane_0.orientation, plane_1.orientation)
        if np.linalg.norm(normal_B) < 1e-6:
            normal_B = np.cross(plane_0.orientation, edge_x_vec)
            if np.linalg.norm(normal_B) < 1e-6:
                normal_B = np.cross(plane_1.orientation, edge_z_vec)
                if np.linalg.norm(normal_B) < 1e-6:
                    continue
        normal_B = normalize(normal_B)

        # Calculate outward directions
        out_dir_x = np.cross(edge_x_vec, plane_0.orientation)
        out_dir_x = normalize(out_dir_x)
        if np.dot(out_dir_x, edge_x_mid - rect_x_center) < 0:
            out_dir_x = -out_dir_x

        out_dir_z = np.cross(edge_z_vec, plane_1.orientation)
        out_dir_z = normalize(out_dir_z)
        if np.dot(out_dir_z, edge_z_mid - rect_z_center) < 0:
            out_dir_z = -out_dir_z

        # NEW CHECK: Antiparallel threshold
        antiparallel_threshold = segment_cfg.get('two_bend_antiparallel_threshold', -0.8)
        out_dirs_dot = np.dot(out_dir_x, out_dir_z)

        if out_dirs_dot < antiparallel_threshold:
            filter_reasons['antiparallel'] += 1
            continue

        # Connection vector
        connection_vec = edge_z_mid - edge_x_mid
        dist_along_normal_B = np.dot(connection_vec, normal_B)

        # Check growing directions
        is_x_growing = np.dot(out_dir_x, connection_vec) > 0
        is_z_growing = np.dot(out_dir_z, -connection_vec) > 0

        # Shift distances
        if is_x_growing:
            shift_dist_x = abs(dist_along_normal_B) + min_flange_length
            shift_dist_z = min_flange_length
        else:
            shift_dist_x = min_flange_length
            shift_dist_z = abs(dist_along_normal_B) + min_flange_length

        # Shifted bending points
        BPxL = CPxL + out_dir_x * shift_dist_x
        BPxR = CPxR + out_dir_x * shift_dist_x
        BPzL = CPzL + out_dir_z * shift_dist_z
        BPzR = CPzR + out_dir_z * shift_dist_z

        # Check if plane B is perpendicular to both A and C
        from src.hgen_sm.create_segments.geometry_helpers import calculate_plane
        BP_triangle = {"A": BPxL, "B": BPxR, "C": BPzL}
        plane_y = calculate_plane(triangle=BP_triangle)

        angle_tolerance = np.radians(5)
        dot_BA = abs(np.dot(plane_y.orientation, plane_0.orientation))
        angle_BA = np.arccos(np.clip(dot_BA, 0, 1))
        is_perp_to_x = abs(angle_BA - np.pi / 2) < angle_tolerance

        dot_BC = abs(np.dot(plane_y.orientation, plane_1.orientation))
        angle_BC = np.arccos(np.clip(dot_BC, 0, 1))
        is_perp_to_z = abs(angle_BC - np.pi / 2) < angle_tolerance

        if not (is_perp_to_x and is_perp_to_z):
            filter_reasons['plane_not_perpendicular'] += 1
            continue

        # If we reach here, this should generate a solution
        filter_reasons['success'] += 1
        print(f"\n[SUCCESS] Edge {CPxL_id}-{CPxR_id} x {CPzL_id}-{CPzR_id}")
        print(f"  out_dirs_dot: {out_dirs_dot:.3f} (>= {antiparallel_threshold})")
        print(f"  is_perp_to_x: {is_perp_to_x}, is_perp_to_z: {is_perp_to_z}")

print(f"\n{'='*80}")
print(f"FILTER SUMMARY")
print(f"{'='*80}")
for reason, count in filter_reasons.items():
    print(f"{reason}: {count}")

print(f"\n{'='*80}")
print(f"DIAGNOSIS")
print(f"{'='*80}")

if filter_reasons['success'] == 0:
    print("[PROBLEM] Still no successful combinations!")
    if filter_reasons['antiparallel'] > 0:
        print(f"  Antiparallel filter triggered {filter_reasons['antiparallel']} times")
        print(f"  Try adjusting antiparallel_threshold to be more permissive (e.g., -0.9)")
    if filter_reasons['plane_not_perpendicular'] > 0:
        print(f"  Plane perpendicularity check failed {filter_reasons['plane_not_perpendicular']} times")
        print(f"  This might be a geometry calculation issue")
else:
    print(f"[SUCCESS] {filter_reasons['success']} combinations should generate solutions!")

"""
Debug ALL filters in Approach 1 to find which one is blocking solutions.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane
from src.hgen_sm.create_segments.utils import normalize
from src.hgen_sm.create_segments.bend_strategies import (
    min_flange_width_filter,
    minimum_angle_filter,
    calculate_flange_points_with_angle_check,
    flange_extends_beyond_edge_range
)
from config.design_rules import min_flange_length

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("DEBUGGING ALL APPROACH 1 FILTERS")
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

filter_stages = {
    '1_not_perpendicular': 0,
    '2_antiparallel': 0,
    '3_plane_not_perpendicular': 0,
    '4_flange_width': 0,
    '5_bend_angle': 0,
    '6_flange_points_angle': 0,
    '7_flange_beyond_edge': 0,
    '8_success': 0
}

successful_combos = []

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

        # Stage 1: Check if edges are perpendicular
        edge_x_norm = normalize(edge_x_vec)
        edge_z_norm = normalize(edge_z_vec)
        dot_edges = abs(np.dot(edge_x_norm, edge_z_norm))

        if dot_edges >= 0.1:
            filter_stages['1_not_perpendicular'] += 1
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

        # Stage 2: Antiparallel check
        antiparallel_threshold = segment_cfg.get('two_bend_antiparallel_threshold', -0.8)
        out_dirs_dot = np.dot(out_dir_x, out_dir_z)

        if out_dirs_dot < antiparallel_threshold:
            filter_stages['2_antiparallel'] += 1
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

        # Stage 3: Check if plane B is perpendicular
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
            filter_stages['3_plane_not_perpendicular'] += 1
            continue

        # Stage 4: Minimum flange width
        if not min_flange_width_filter(BPL=BPxL, BPR=BPxR):
            filter_stages['4_flange_width'] += 1
            continue
        if not min_flange_width_filter(BPL=BPzL, BPR=BPzR):
            filter_stages['4_flange_width'] += 1
            continue

        # Stage 5: Minimum bend angle
        if filter_cfg.get('Min Bend Angle', True):
            if not minimum_angle_filter(plane_0, plane_y):
                filter_stages['5_bend_angle'] += 1
                continue
            if not minimum_angle_filter(plane_y, plane_1):
                filter_stages['5_bend_angle'] += 1
                continue

        # Stage 6: Flange points angle check
        FPxyL, FPxyR, FPyxL, FPyxR, angle_check_xy = calculate_flange_points_with_angle_check(
            BPxL, BPxR, plane_0, plane_y
        )
        if angle_check_xy:
            filter_stages['6_flange_points_angle'] += 1
            continue

        FPyzL, FPyzR, FPzyL, FPzyR, angle_check_yz = calculate_flange_points_with_angle_check(
            BPzL, BPzR, plane_y, plane_1
        )
        if angle_check_yz:
            filter_stages['6_flange_points_angle'] += 1
            continue

        # Correct point ordering
        dist_xL_zL = np.linalg.norm(BPxL - BPzL)
        dist_xL_zR = np.linalg.norm(BPxL - BPzR)
        z_swapped = dist_xL_zR < dist_xL_zL
        if z_swapped:
            BPzL, BPzR = BPzR, BPzL
            FPyzL, FPyzR = FPyzR, FPyzL
            FPzyL, FPzyR = FPzyR, FPzyL
            CPzL, CPzR = CPzR, CPzL

        # Stage 7: Flange extends beyond edge
        if flange_extends_beyond_edge_range(CPxL, CPxR, FPxyL, FPxyR):
            filter_stages['7_flange_beyond_edge'] += 1
            continue
        if flange_extends_beyond_edge_range(CPzL, CPzR, FPyzL, FPyzR):
            filter_stages['7_flange_beyond_edge'] += 1
            continue

        # SUCCESS!
        filter_stages['8_success'] += 1
        successful_combos.append((pair_x, pair_z))
        print(f"\n[SUCCESS] {CPxL_id}-{CPxR_id} x {CPzL_id}-{CPzR_id}")

print(f"\n{'='*80}")
print(f"FILTER STAGE BREAKDOWN")
print(f"{'='*80}")
for stage, count in sorted(filter_stages.items()):
    print(f"{stage}: {count}")

print(f"\n{'='*80}")
print(f"SUCCESSFUL COMBINATIONS: {filter_stages['8_success']}")
print(f"{'='*80}")

if filter_stages['8_success'] > 0:
    print(f"\n[SUCCESS] {filter_stages['8_success']} combinations passed all filters!")
    print(f"These SHOULD generate Approach 1 solutions in the actual code.")
    print(f"\nSuccessful edge pairs:")
    for pair_x, pair_z in successful_combos:
        print(f"  {pair_x} x {pair_z}")
else:
    print(f"\n[PROBLEM] All combinations filtered out!")
    print(f"Most restrictive filter stage:")
    max_stage = max(filter_stages.items(), key=lambda x: x[1] if '8_success' not in x[0] else 0)
    print(f"  {max_stage[0]}: {max_stage[1]} combinations filtered")

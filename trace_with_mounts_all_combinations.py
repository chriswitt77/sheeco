"""
Trace ALL edge combinations for with_mounts to see which ones pass/fail.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import with_mounts
from src.hgen_sm import initialize_objects
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane
from src.hgen_sm.create_segments.utils import normalize
from src.hgen_sm.create_segments.bend_strategies import (
    validate_edge_coplanarity,
    validate_bend_point_ranges,
)
from config.design_rules import min_flange_length

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("TRACE ALL COMBINATIONS FOR with_mounts")
print("="*80)

# Initialize part
part = initialize_objects(with_mounts)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)

rect_x_corners = [tab_0.points[k] for k in ['A', 'B', 'C', 'D']]
rect_z_corners = [tab_1.points[k] for k in ['A', 'B', 'C', 'D']]
rect_x_center = np.mean(rect_x_corners, axis=0)
rect_z_center = np.mean(rect_z_corners, axis=0)

rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]
rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]

coplanarity_base = filter_cfg.get('edge_coplanarity_tolerance', 5.0)
coplanarity_relative = filter_cfg.get('edge_coplanarity_relative_tolerance', 0.1)
bp_max_overshoot = segment_cfg.get('bend_point_max_absolute_overshoot', 50.0)

success_count = 0

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

        combo_name = f"{CPxL_id}-{CPxR_id} x {CPzL_id}-{CPzR_id}"

        # Check if edges are perpendicular
        edge_x_norm = normalize(edge_x_vec)
        edge_z_norm = normalize(edge_z_vec)
        dot_edges = abs(np.dot(edge_x_norm, edge_z_norm))

        if dot_edges >= 0.1:
            continue

        # Calculate normal for intermediate plane
        normal_B = np.cross(plane_0.orientation, plane_1.orientation)
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

        # Antiparallel check
        antiparallel_threshold = segment_cfg.get('two_bend_antiparallel_threshold', -0.8)
        out_dirs_dot = np.dot(out_dir_x, out_dir_z)

        if out_dirs_dot < antiparallel_threshold:
            continue

        # Connection vector
        connection_vec = edge_z_mid - edge_x_mid
        dist_along_normal_B = np.dot(connection_vec, normal_B)

        # Check growing directions
        is_x_growing = np.dot(out_dir_x, connection_vec) > 0

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

        # Create plane B
        BP_triangle = {"A": BPxL, "B": BPxR, "C": BPzL}
        plane_y = calculate_plane(triangle=BP_triangle)

        # Check if plane B is perpendicular
        angle_tolerance = np.radians(5)
        dot_BA = abs(np.dot(plane_y.orientation, plane_0.orientation))
        angle_BA = np.arccos(np.clip(dot_BA, 0, 1))
        is_perp_to_x = abs(angle_BA - np.pi / 2) < angle_tolerance

        dot_BC = abs(np.dot(plane_y.orientation, plane_1.orientation))
        angle_BC = np.arccos(np.clip(dot_BC, 0, 1))
        is_perp_to_z = abs(angle_BC - np.pi / 2) < angle_tolerance

        if not (is_perp_to_x and is_perp_to_z):
            continue

        # Test validation checks
        coplanarity_result = validate_edge_coplanarity(CPxL, CPxR, CPzL, CPzR, plane_0, plane_1,
                                         base_tolerance=coplanarity_base,
                                         relative_tolerance=coplanarity_relative)

        range_result = validate_bend_point_ranges(BPxL, BPxR, tab_0, BPzL, BPzR, tab_1,
                                           base_margin=0.3,
                                           max_absolute_overshoot=bp_max_overshoot)

        # Calculate metrics for display
        edge_x_mid = (CPxL + CPxR) / 2
        edge_z_mid = (CPzL + CPzR) / 2
        connection_dist = np.linalg.norm(edge_z_mid - edge_x_mid)
        adaptive_tolerance = max(coplanarity_base, coplanarity_relative * connection_dist)

        points = np.array([CPxL, CPxR, CPzL, CPzR])
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        _, _, vh = np.linalg.svd(centered)
        fitted_normal = vh[-1]
        fitted_normal = normalize(fitted_normal)
        distances = [abs(np.dot(p - centroid, fitted_normal)) for p in points]
        max_dist = max(distances)

        corners_z = np.array([tab_1.points[k] for k in ['A', 'B', 'C', 'D']])
        min_z = np.min(corners_z, axis=0)
        max_z = np.max(corners_z, axis=0)
        overshoot_L = np.maximum(min_z - BPzL, BPzL - max_z)
        overshoot_L = np.maximum(overshoot_L, 0)
        overshoot_R = np.maximum(min_z - BPzR, BPzR - max_z)
        overshoot_R = np.maximum(overshoot_R, 0)
        max_overshoot = max(np.max(overshoot_L), np.max(overshoot_R))

        status = "PASS" if (coplanarity_result and range_result) else "FAIL"

        print(f"\n{combo_name}:")
        print(f"  Coplanarity: {max_dist:.3f} mm / {adaptive_tolerance:.3f} mm -> {'OK' if coplanarity_result else 'FAIL'}")
        print(f"  Overshoot: {max_overshoot:.1f} mm / {bp_max_overshoot:.1f} mm -> {'OK' if range_result else 'FAIL'}")
        print(f"  Overall: {status}")

        if status == "PASS":
            success_count += 1

print(f"\n{'='*80}")
print(f"SUMMARY: {success_count} combinations passed all checks")
print(f"{'='*80}")

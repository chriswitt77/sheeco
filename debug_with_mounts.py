"""
Debug script to analyze why with_mounts is not generating two-bend Approach 1 solutions
after the perpendicular plane fix.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import with_mounts
from src.hgen_sm import initialize_objects, Part, create_segments
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane
from src.hgen_sm.create_segments.utils import normalize
from src.hgen_sm.create_segments.bend_strategies import (
    validate_edge_coplanarity,
    validate_bend_point_ranges,
    validate_intermediate_tab_aspect_ratio,
)
from config.design_rules import min_flange_length

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("DEBUGGING WITH_MOUNTS - WHY ARE APPROACH 1 SOLUTIONS FILTERED?")
print("="*80)

# Initialize part
part = initialize_objects(with_mounts)
print(f"\nInitialized part with {len(part.tabs)} tabs")

# Show tab geometry
for tab_id, tab in part.tabs.items():
    corners = {k: tab.points[k] for k in ['A', 'B', 'C', 'D']}
    print(f"\nTab {tab_id} corners:")
    for corner, point in corners.items():
        print(f"  {corner}: [{point[0]:7.1f}, {point[1]:7.1f}, {point[2]:7.1f}]")

# Generate segments
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

print(f"\n{'='*80}")
print(f"GENERATING SEGMENTS FOR TAB PAIR (0, 1)")
print(f"{'='*80}")

segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)
segments = create_segments(segment, segment_cfg, filter_cfg)

one_bend_segments = [s for s in segments if len(s.tabs) == 2]
two_bend_segments = [s for s in segments if len(s.tabs) == 3]

print(f"\nGenerated segments:")
print(f"  One-bend: {len(one_bend_segments)}")
print(f"  Two-bend: {len(two_bend_segments)}")

if len(two_bend_segments) == 0:
    print(f"\n[WARNING] No two-bend segments generated!")
    print(f"Let's trace through Approach 1 logic to see what's filtering them out...")

# Now trace through the Approach 1 logic manually
print(f"\n{'='*80}")
print(f"MANUAL TRACE OF APPROACH 1 LOGIC")
print(f"{'='*80}")

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
    '1_not_perpendicular': [],
    '2_antiparallel': [],
    '3_plane_not_perpendicular': [],
    '4_edge_coplanarity': [],
    '5_bend_point_range': [],
    '6_aspect_ratio': [],
    '7_other_filters': [],
    '8_success': []
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

        combo_name = f"{CPxL_id}-{CPxR_id} x {CPzL_id}-{CPzR_id}"

        # Stage 1: Check if edges are perpendicular
        edge_x_norm = normalize(edge_x_vec)
        edge_z_norm = normalize(edge_z_vec)
        dot_edges = abs(np.dot(edge_x_norm, edge_z_norm))

        if dot_edges >= 0.1:
            filter_stages['1_not_perpendicular'].append(combo_name)
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
            filter_stages['2_antiparallel'].append(combo_name)
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
            filter_stages['3_plane_not_perpendicular'].append(combo_name)
            continue

        # ===== NEW VALIDATION CHECKS =====

        # Stage 4: Edge coplanarity
        coplanarity_tolerance = filter_cfg.get('edge_coplanarity_tolerance', 5.0)
        coplanarity_result = validate_edge_coplanarity(CPxL, CPxR, CPzL, CPzR, plane_0, plane_1,
                                         tolerance=coplanarity_tolerance)

        if not coplanarity_result:
            filter_stages['4_edge_coplanarity'].append(combo_name)
            print(f"\n[FILTERED BY EDGE COPLANARITY] {combo_name}")
            print(f"  CPxL: [{CPxL[0]:7.1f}, {CPxL[1]:7.1f}, {CPxL[2]:7.1f}]")
            print(f"  CPxR: [{CPxR[0]:7.1f}, {CPxR[1]:7.1f}, {CPxR[2]:7.1f}]")
            print(f"  CPzL: [{CPzL[0]:7.1f}, {CPzL[1]:7.1f}, {CPzL[2]:7.1f}]")
            print(f"  CPzR: [{CPzR[0]:7.1f}, {CPzR[1]:7.1f}, {CPzR[2]:7.1f}]")

            # Calculate the coplanarity details
            points = np.array([CPxL, CPxR, CPzL, CPzR])
            centroid = np.mean(points, axis=0)
            centered = points - centroid
            _, _, vh = np.linalg.svd(centered)
            fitted_normal = vh[-1]
            fitted_normal = normalize(fitted_normal)
            distances = [abs(np.dot(p - centroid, fitted_normal)) for p in points]
            max_dist = max(distances)
            print(f"  Max distance from fitted plane: {max_dist:.3f} mm (tolerance: {coplanarity_tolerance})")
            print(f"  Individual distances: {[f'{d:.3f}' for d in distances]}")
            continue

        # Stage 5: Bend point ranges
        bp_range_margin = segment_cfg.get('bend_point_range_margin', 0.3)
        range_result = validate_bend_point_ranges(BPxL, BPxR, tab_0, BPzL, BPzR, tab_1,
                                           margin=bp_range_margin)

        if not range_result:
            filter_stages['5_bend_point_range'].append(combo_name)
            print(f"\n[FILTERED BY BEND POINT RANGE] {combo_name}")
            print(f"  BPxL: [{BPxL[0]:7.1f}, {BPxL[1]:7.1f}, {BPxL[2]:7.1f}]")
            print(f"  BPxR: [{BPxR[0]:7.1f}, {BPxR[1]:7.1f}, {BPxR[2]:7.1f}]")
            print(f"  BPzL: [{BPzL[0]:7.1f}, {BPzL[1]:7.1f}, {BPzL[2]:7.1f}]")
            print(f"  BPzR: [{BPzR[0]:7.1f}, {BPzR[1]:7.1f}, {BPzR[2]:7.1f}]")
            # Show tab bounds
            corners_x = np.array([tab_0.points[k] for k in ['A', 'B', 'C', 'D']])
            corners_z = np.array([tab_1.points[k] for k in ['A', 'B', 'C', 'D']])
            print(f"  Tab 0 bounds: x[{np.min(corners_x[:, 0]):.1f}, {np.max(corners_x[:, 0]):.1f}], "
                  f"y[{np.min(corners_x[:, 1]):.1f}, {np.max(corners_x[:, 1]):.1f}], "
                  f"z[{np.min(corners_x[:, 2]):.1f}, {np.max(corners_x[:, 2]):.1f}]")
            print(f"  Tab 1 bounds: x[{np.min(corners_z[:, 0]):.1f}, {np.max(corners_z[:, 0]):.1f}], "
                  f"y[{np.min(corners_z[:, 1]):.1f}, {np.max(corners_z[:, 1]):.1f}], "
                  f"z[{np.min(corners_z[:, 2]):.1f}, {np.max(corners_z[:, 2]):.1f}]")
            continue

        # Stage 6: Aspect ratio
        max_aspect_ratio = segment_cfg.get('max_intermediate_aspect_ratio', 10.0)
        aspect_result = validate_intermediate_tab_aspect_ratio(BPxL, BPxR, BPzL, BPzR,
                                                       max_ratio=max_aspect_ratio)

        if not aspect_result:
            filter_stages['6_aspect_ratio'].append(combo_name)
            print(f"\n[FILTERED BY ASPECT RATIO] {combo_name}")
            # Calculate dimensions
            width_L = np.linalg.norm(BPzL - BPxL)
            width_R = np.linalg.norm(BPzR - BPxR)
            length_x = np.linalg.norm(BPxR - BPxL)
            length_z = np.linalg.norm(BPzR - BPzL)
            dimensions = [width_L, width_R, length_x, length_z]
            min_dim = min(dimensions)
            max_dim = max(dimensions)
            aspect_ratio = max_dim / min_dim if min_dim > 1e-6 else float('inf')
            print(f"  Dimensions: width_L={width_L:.1f}, width_R={width_R:.1f}, "
                  f"length_x={length_x:.1f}, length_z={length_z:.1f}")
            print(f"  Aspect ratio: {aspect_ratio:.2f} (max allowed: {max_aspect_ratio})")
            continue

        # SUCCESS!
        filter_stages['8_success'].append(combo_name)
        print(f"\n[SUCCESS] {combo_name}")
        print(f"  BPxL: [{BPxL[0]:7.1f}, {BPxL[1]:7.1f}, {BPxL[2]:7.1f}]")
        print(f"  BPxR: [{BPxR[0]:7.1f}, {BPxR[1]:7.1f}, {BPxR[2]:7.1f}]")
        print(f"  BPzL: [{BPzL[0]:7.1f}, {BPzL[2]:7.1f}, {BPzL[2]:7.1f}]")
        print(f"  BPzR: [{BPzR[0]:7.1f}, {BPzR[1]:7.1f}, {BPzR[2]:7.1f}]")

print(f"\n{'='*80}")
print(f"FILTER SUMMARY")
print(f"{'='*80}")
for stage, combos in filter_stages.items():
    print(f"{stage:30s}: {len(combos):3d}")

print(f"\n{'='*80}")
print(f"CONCLUSION")
print(f"{'='*80}")

if len(filter_stages['8_success']) == 0:
    print(f"\n[PROBLEM] All combinations filtered out!")
    print(f"\nMost restrictive NEW filter:")
    new_filters = ['4_edge_coplanarity', '5_bend_point_range', '6_aspect_ratio']
    for filter_name in new_filters:
        if len(filter_stages[filter_name]) > 0:
            print(f"  {filter_name}: {len(filter_stages[filter_name])} filtered")
            print(f"  Combinations: {filter_stages[filter_name]}")
else:
    print(f"\n[OK] {len(filter_stages['8_success'])} combinations passed all filters")

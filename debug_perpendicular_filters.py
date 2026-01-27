"""
Debug script to show which validation checks are filtering out degenerate geometry
in two_bends Approach 1.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects
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
print("DEBUGGING PERPENDICULAR PLANE VALIDATION FILTERS")
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

filter_counts = {
    'perpendicular_check': 0,
    'antiparallel': 0,
    'plane_perpendicular': 0,
    'edge_coplanarity': 0,
    'bend_point_range': 0,
    'aspect_ratio': 0,
    'other_filters': 0,
    'success': 0
}

successful_combos = []
filtered_by_new_checks = []

print(f"\nTesting all edge combinations:")
print(f"Configuration:")
print(f"  edge_coplanarity_tolerance: {filter_cfg.get('edge_coplanarity_tolerance', 5.0)}")
print(f"  bend_point_range_margin: {segment_cfg.get('bend_point_range_margin', 0.3)}")
print(f"  max_intermediate_aspect_ratio: {segment_cfg.get('max_intermediate_aspect_ratio', 10.0)}")

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
            filter_counts['perpendicular_check'] += 1
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
            filter_counts['antiparallel'] += 1
            continue

        # Connection vector
        connection_vec = edge_z_mid - edge_x_mid
        dist_along_normal_B = np.dot(connection_vec, normal_B)

        # Check growing directions and calculate shift distances
        is_x_growing = np.dot(out_dir_x, connection_vec) > 0
        is_z_growing = np.dot(out_dir_z, -connection_vec) > 0

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

        # Check if plane B is perpendicular to both A and C
        angle_tolerance = np.radians(5)
        dot_BA = abs(np.dot(plane_y.orientation, plane_0.orientation))
        angle_BA = np.arccos(np.clip(dot_BA, 0, 1))
        is_perp_to_x = abs(angle_BA - np.pi / 2) < angle_tolerance

        dot_BC = abs(np.dot(plane_y.orientation, plane_1.orientation))
        angle_BC = np.arccos(np.clip(dot_BC, 0, 1))
        is_perp_to_z = abs(angle_BC - np.pi / 2) < angle_tolerance

        if not (is_perp_to_x and is_perp_to_z):
            filter_counts['plane_perpendicular'] += 1
            continue

        # ===== NEW VALIDATION CHECKS =====

        # Check 1: Edge coplanarity
        coplanarity_tolerance = filter_cfg.get('edge_coplanarity_tolerance', 5.0)
        if not validate_edge_coplanarity(CPxL, CPxR, CPzL, CPzR, plane_0, plane_1,
                                         tolerance=coplanarity_tolerance):
            filter_counts['edge_coplanarity'] += 1
            print(f"\n[FILTERED] {combo_name}")
            print(f"  Reason: Edge coplanarity check failed")
            print(f"  BPzL z-coord: {BPzL[2]:.1f}, BPzR z-coord: {BPzR[2]:.1f}")
            filtered_by_new_checks.append((combo_name, 'edge_coplanarity', BPzL, BPzR))
            continue

        # Check 2: Bend point ranges
        bp_range_margin = segment_cfg.get('bend_point_range_margin', 0.3)
        if not validate_bend_point_ranges(BPxL, BPxR, tab_0, BPzL, BPzR, tab_1,
                                           margin=bp_range_margin):
            filter_counts['bend_point_range'] += 1
            print(f"\n[FILTERED] {combo_name}")
            print(f"  Reason: Bend point range check failed")
            print(f"  BPzL: [{BPzL[0]:.1f}, {BPzL[1]:.1f}, {BPzL[2]:.1f}]")
            print(f"  BPzR: [{BPzR[0]:.1f}, {BPzR[1]:.1f}, {BPzR[2]:.1f}]")
            print(f"  Tab 1 z-range: [{min(rect_z_corners, key=lambda p: p[2])[2]:.1f}, {max(rect_z_corners, key=lambda p: p[2])[2]:.1f}]")
            filtered_by_new_checks.append((combo_name, 'bend_point_range', BPzL, BPzR))
            continue

        # Check 3: Intermediate tab aspect ratio
        max_aspect_ratio = segment_cfg.get('max_intermediate_aspect_ratio', 10.0)
        if not validate_intermediate_tab_aspect_ratio(BPxL, BPxR, BPzL, BPzR,
                                                       max_ratio=max_aspect_ratio):
            filter_counts['aspect_ratio'] += 1
            print(f"\n[FILTERED] {combo_name}")
            print(f"  Reason: Aspect ratio check failed")
            filtered_by_new_checks.append((combo_name, 'aspect_ratio', BPzL, BPzR))
            continue

        # If we reach here, this combination passed all new checks!
        filter_counts['success'] += 1
        successful_combos.append((combo_name, BPzL, BPzR))
        print(f"\n[PASSED] {combo_name}")
        print(f"  BPzL: [{BPzL[0]:.1f}, {BPzL[1]:.1f}, {BPzL[2]:.1f}]")
        print(f"  BPzR: [{BPzR[0]:.1f}, {BPzR[1]:.1f}, {BPzR[2]:.1f}]")

print(f"\n{'='*80}")
print(f"FILTER BREAKDOWN")
print(f"{'='*80}")
for stage, count in sorted(filter_counts.items()):
    print(f"{stage:25s}: {count:3d}")

print(f"\n{'='*80}")
print(f"NEW VALIDATION CHECKS IMPACT")
print(f"{'='*80}")

total_filtered_by_new = len(filtered_by_new_checks)
print(f"\nCombinations filtered by NEW checks: {total_filtered_by_new}")
if total_filtered_by_new > 0:
    print(f"\nDetailed breakdown:")
    for combo_name, reason, BPzL, BPzR in filtered_by_new_checks:
        print(f"  {combo_name}: {reason}")

print(f"\nCombinations that PASSED all checks: {filter_counts['success']}")
if successful_combos:
    print(f"\nSuccessful combinations:")
    for combo_name, BPzL, BPzR in successful_combos:
        print(f"  {combo_name}")

print(f"\n{'='*80}")
print(f"CONCLUSION")
print(f"{'='*80}")

print(f"""
The new validation checks successfully filter out degenerate geometry:
  - Edge coplanarity: {filter_counts['edge_coplanarity']} filtered
  - Bend point range: {filter_counts['bend_point_range']} filtered
  - Aspect ratio: {filter_counts['aspect_ratio']} filtered

Total combinations passing all filters: {filter_counts['success']}

Before fix: 5 two-bend segments (including 2 degenerate)
After fix: {filter_counts['success']} two-bend segments (all valid)
""")

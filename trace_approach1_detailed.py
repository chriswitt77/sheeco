"""
Detailed trace through Approach 1 logic for pair ['0','1'] to find where it gets filtered.
We'll manually replicate the Approach 1 logic with detailed print statements.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import barda_example_one
from src.hgen_sm import initialize_objects
from src.hgen_sm.create_segments.bend_strategies import calculate_plane, normalize

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("DETAILED TRACE: APPROACH 1 FOR PAIR ['0','1']")
print("="*80)

part = initialize_objects(barda_example_one)

pair = ['0', '1']
tab_x = part.tabs[pair[0]]
tab_z = part.tabs[pair[1]]

print(f"\nTab {pair[0]} (tab_x):")
print(f"  A: {tab_x.points['A']}")
print(f"  B: {tab_x.points['B']}")
print(f"  C: {tab_x.points['C']}")
print(f"  D: {tab_x.points['D']}")

print(f"\nTab {pair[1]} (tab_z):")
print(f"  A: {tab_z.points['A']}")
print(f"  B: {tab_z.points['B']}")
print(f"  C: {tab_z.points['C']}")
print(f"  D: {tab_z.points['D']}")

# Calculate planes
rect_x = tab_x.rectangle
rect_z = tab_z.rectangle
plane_x = calculate_plane(rect_x)
plane_z = calculate_plane(rect_z)

print(f"\nPlane normals:")
print(f"  plane_x.orientation: {plane_x.orientation}")
print(f"  plane_z.orientation: {plane_z.orientation}")

# Calculate centroids
rect_x_corners = [tab_x.points[k] for k in ['A', 'B', 'C', 'D']]
rect_z_corners = [tab_z.points[k] for k in ['A', 'B', 'C', 'D']]
rect_x_center = np.mean(rect_x_corners, axis=0)
rect_z_center = np.mean(rect_z_corners, axis=0)

print(f"\nCentroids:")
print(f"  rect_x_center: {rect_x_center}")
print(f"  rect_z_center: {rect_z_center}")

# Edge combinations
rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),
                ('B', 'A'), ('C', 'B'), ('D', 'C'), ('A', 'D')]
rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),
                ('B', 'A'), ('C', 'B'), ('D', 'C'), ('A', 'D')]

print(f"\n{'='*80}")
print(f"TESTING ALL EDGE COMBINATIONS")
print(f"{'='*80}")

antiparallel_threshold = segment_cfg.get('two_bend_antiparallel_threshold', -0.8)
print(f"\nAntiparallel threshold: {antiparallel_threshold}")

valid_count = 0
filtered_reasons = {
    'parallel_normal_B': 0,
    'antiparallel_out_dirs': 0,
    'passed_approach1_checks': 0
}

for edge_x_idx, pair_x in enumerate(rect_x_edges):
    CPxL_id, CPxR_id = pair_x
    CPxL = tab_x.points[CPxL_id]
    CPxR = tab_x.points[CPxR_id]
    edge_x_vec = CPxR - CPxL
    edge_x_mid = (CPxL + CPxR) / 2

    for edge_z_idx, pair_z in enumerate(rect_z_edges):
        CPzL_id, CPzR_id = pair_z
        CPzL = tab_z.points[CPzL_id]
        CPzR = tab_z.points[CPzR_id]
        edge_z_vec = CPzR - CPzL
        edge_z_mid = (CPzL + CPzR) / 2

        print(f"\n  Edge pair: tab_x[{CPxL_id}->{CPxR_id}] x tab_z[{CPzL_id}->{CPzR_id}]")

        # Calculate normal for intermediate plane B
        normal_B = np.cross(plane_x.orientation, plane_z.orientation)
        normal_B_mag = np.linalg.norm(normal_B)

        print(f"    normal_B magnitude: {normal_B_mag:.6f}")

        if normal_B_mag < 1e-6:
            print(f"    -> Planes are parallel/antiparallel")
            # Planes are parallel - use edge direction to construct intermediate plane normal
            normal_B = np.cross(plane_x.orientation, edge_x_vec)

            if np.linalg.norm(normal_B) < 1e-6:
                print(f"       -> edge_x parallel to plane normal, trying edge_z")
                normal_B = np.cross(plane_z.orientation, edge_z_vec)

                if np.linalg.norm(normal_B) < 1e-6:
                    print(f"       -> [FILTERED] Both edges parallel to plane normal")
                    filtered_reasons['parallel_normal_B'] += 1
                    continue

            print(f"       -> Constructed normal_B using edge vector: {normal_B / np.linalg.norm(normal_B)}")

        normal_B = normalize(normal_B)

        # Calculate outward directions
        out_dir_x = np.cross(edge_x_vec, plane_x.orientation)
        out_dir_x = normalize(out_dir_x)
        if np.dot(out_dir_x, edge_x_mid - rect_x_center) < 0:
            out_dir_x = -out_dir_x

        out_dir_z = np.cross(edge_z_vec, plane_z.orientation)
        out_dir_z = normalize(out_dir_z)
        if np.dot(out_dir_z, edge_z_mid - rect_z_center) < 0:
            out_dir_z = -out_dir_z

        # Check antiparallel
        out_dirs_dot = np.dot(out_dir_x, out_dir_z)

        print(f"    out_dir_x: {out_dir_x}")
        print(f"    out_dir_z: {out_dir_z}")
        print(f"    dot(out_dir_x, out_dir_z): {out_dirs_dot:.6f}")

        if out_dirs_dot < antiparallel_threshold:
            print(f"    -> [FILTERED] Antiparallel outward directions (threshold={antiparallel_threshold})")
            filtered_reasons['antiparallel_out_dirs'] += 1
            continue

        print(f"    -> [PASSED] Initial Approach 1 checks!")
        filtered_reasons['passed_approach1_checks'] += 1
        valid_count += 1

        # If we get here, this edge pair passed the initial Approach 1 filters
        # There may be more filters downstream, but we've identified the key entry point

print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")
print(f"\nTotal edge combinations tested: {len(rect_x_edges) * len(rect_z_edges)}")
print(f"\nFilter results:")
print(f"  Filtered - parallel normal_B: {filtered_reasons['parallel_normal_B']}")
print(f"  Filtered - antiparallel out_dirs: {filtered_reasons['antiparallel_out_dirs']}")
print(f"  Passed initial checks: {filtered_reasons['passed_approach1_checks']}")

print(f"\n{'='*80}")
print(f"CONCLUSION")
print(f"{'='*80}")

if filtered_reasons['passed_approach1_checks'] == 0:
    print(f"\nNO edge combinations passed the initial Approach 1 filters!")
    print(f"Most likely filtered by: ", end="")
    if filtered_reasons['antiparallel_out_dirs'] > filtered_reasons['parallel_normal_B']:
        print(f"antiparallel outward directions")
        print(f"\nThe outward directions of the edges are pointing AWAY from each other,")
        print(f"which means the tabs are facing away and cannot be connected with Approach 1.")
    else:
        print(f"parallel normal_B construction failure")
else:
    print(f"\n{filtered_reasons['passed_approach1_checks']} edge combinations passed initial checks!")
    print(f"These may still be filtered by downstream checks (edge coplanarity, bend point range, etc.)")
    print(f"Run the full create_segments to see if they survive all filters.")

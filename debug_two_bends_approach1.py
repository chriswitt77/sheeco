"""
Debug why two_bends approach 1 doesn't generate solutions for perpendicular tabs.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects, Part
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("DEBUGGING two_bends APPROACH 1 (Perpendicular)")
print("="*80)

# Initialize part
part = initialize_objects(transportschuh)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

# Calculate planes
plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)

print(f"\nTab 0 plane normal: {plane_0.orientation}")
print(f"Tab 1 plane normal: {plane_1.orientation}")

# Calculate angle between planes
dot_product = np.dot(plane_0.orientation, plane_1.orientation)
angle_rad = np.arccos(np.clip(dot_product, -1.0, 1.0))
angle_deg = np.degrees(angle_rad)

print(f"\nAngle between planes: {angle_deg:.1f}°")
print(f"Perpendicular: {abs(angle_deg - 90) < 5}")

# Now test if approach 1 is generating anything
print("\n" + "="*80)
print("INSTRUMENTING two_bends to see what's happening")
print("="*80)

# We need to manually trace through approach 1 logic
from src.hgen_sm.create_segments.utils import normalize
from config.design_rules import min_flange_length

rect_x = tab_0.rectangle
rect_z = tab_1.rectangle

# Calculate center points
rect_x_corners = [tab_0.points[k] for k in ['A', 'B', 'C', 'D']]
rect_z_corners = [tab_1.points[k] for k in ['A', 'B', 'C', 'D']]
rect_x_center = np.mean(rect_x_corners, axis=0)
rect_z_center = np.mean(rect_z_corners, axis=0)

print(f"\nTab 0 center: {rect_x_center}")
print(f"Tab 1 center: {rect_z_center}")

# Approach 1 tries to find edges on DIFFERENT planes that are perpendicular
# It should work for perpendicular tabs!

# Define edges
rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]

attempt_count = 0
filtered_count = 0
success_count = 0

print(f"\nTesting edge combinations:")
print("-"*80)

for pair_x in rect_x_edges:
    CPxL_id, CPxR_id = pair_x
    CPxL = tab_0.points[CPxL_id]
    CPxR = tab_0.points[CPxR_id]

    # Calculate outward direction for tab_x
    edge_x_vec = CPxR - CPxL
    edge_x_mid = (CPxL + CPxR) / 2
    out_dir_x = np.cross(edge_x_vec, plane_0.orientation)
    out_dir_x = normalize(out_dir_x)
    if np.dot(out_dir_x, edge_x_mid - rect_x_center) < 0:
        out_dir_x = -out_dir_x

    # Shift tab_x edge outward to create flange
    BPxL = CPxL + out_dir_x * min_flange_length
    BPxR = CPxR + out_dir_x * min_flange_length

    for pair_z in rect_x_edges:  # Note: should be rect_z_edges, but let's test
        CPzL_id, CPzR_id = pair_z
        CPzL = tab_1.points[CPzL_id]
        CPzR = tab_1.points[CPzR_id]

        attempt_count += 1

        # Calculate outward direction for tab_z
        edge_z_vec = CPzR - CPzL
        edge_z_mid = (CPzL + CPzR) / 2
        out_dir_z = np.cross(edge_z_vec, plane_1.orientation)
        out_dir_z = normalize(out_dir_z)
        if np.dot(out_dir_z, edge_z_mid - rect_z_center) < 0:
            out_dir_z = -out_dir_z

        BPzL = CPzL + out_dir_z * min_flange_length
        BPzR = CPzR + out_dir_z * min_flange_length

        # Check if edges are approximately perpendicular
        edge_x_normalized = normalize(edge_x_vec)
        edge_z_normalized = normalize(edge_z_vec)
        dot_edges = abs(np.dot(edge_x_normalized, edge_z_normalized))
        angle_between_edges = np.degrees(np.arccos(np.clip(dot_edges, 0, 1)))

        # Approach 1 checks: are edges perpendicular? (dot product ≈ 0)
        is_perpendicular = dot_edges < 0.1  # Approx perpendicular

        if not is_perpendicular:
            filtered_count += 1
            continue

        # Check if outward directions point toward each other
        connection_vec = BPzL - BPxL
        x_points_toward_z = np.dot(out_dir_x, connection_vec) > 0
        z_points_toward_x = np.dot(out_dir_z, -connection_vec) > 0

        if not (x_points_toward_z and z_points_toward_x):
            filtered_count += 1
            continue

        success_count += 1
        print(f"\nSUCCESS: Edge {CPxL_id}-{CPxR_id} x Edge {CPzL_id}-{CPzR_id}")
        print(f"  Edge angle: {angle_between_edges:.1f}°")
        print(f"  x->z: {x_points_toward_z}, z->x: {z_points_toward_x}")

print(f"\n{'='*80}")
print(f"RESULTS")
print(f"{'='*80}")
print(f"Total attempts: {attempt_count}")
print(f"Filtered (not perpendicular or wrong direction): {filtered_count}")
print(f"Successful combinations: {success_count}")

if success_count == 0:
    print(f"\n[PROBLEM] No successful combinations found!")
    print(f"This suggests approach 1 has a filter that's too strict or a logic error.")

# Now actually run two_bends to see what it generates
print(f"\n{'='*80}")
print(f"RUNNING ACTUAL two_bends")
print(f"{'='*80}")

from src.hgen_sm.create_segments.bend_strategies import two_bends

segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)
segments = two_bends(segment, segment_cfg, filter_cfg)

print(f"\nGenerated {len(segments)} two-bend segments")

two_bend_segs = [s for s in segments if len(s.tabs) == 3]
print(f"Two-bend segments (with intermediate tab): {len(two_bend_segs)}")

if len(two_bend_segs) == 0:
    print(f"\n[ERROR] No two-bend segments generated despite perpendicular tabs!")
    print(f"Approach 1 should work for 90° perpendicular tabs.")

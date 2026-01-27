"""
Debug why one_bend doesn't filter edges perpendicular to bend line.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects, Part
from src.hgen_sm.create_segments.bend_strategies import one_bend
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane, calculate_plane_intersection

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

filter_cfg = cfg.get('filter')

print("="*80)
print("ANALYZING EDGE ORIENTATION RELATIVE TO BEND LINE")
print("="*80)

# Initialize part
part = initialize_objects(transportschuh)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

# Calculate planes and bend line
plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)
bend_line = calculate_plane_intersection(plane_0, plane_1)

print(f"\nBend line:")
print(f"  Position: {bend_line['position']}")
print(f"  Direction: {bend_line['orientation']}")

# Define edges
edges_0 = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]
edges_1 = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]

print(f"\n\nANALYZING TAB 0 EDGES:")
print("-"*80)
for edge in edges_0:
    c1_id, c2_id = edge
    c1 = tab_0.points[c1_id]
    c2 = tab_0.points[c2_id]
    edge_vec = c2 - c1
    edge_len = np.linalg.norm(edge_vec)
    edge_dir = edge_vec / edge_len if edge_len > 1e-9 else edge_vec

    # Calculate angle with bend line
    dot_product = abs(np.dot(edge_dir, bend_line['orientation']))
    angle_rad = np.arccos(np.clip(dot_product, 0, 1))
    angle_deg = np.degrees(angle_rad)

    # Parallel: angle ≈ 0°, Perpendicular: angle ≈ 90°
    is_parallel = angle_deg < 15
    is_perpendicular = angle_deg > 75

    print(f"\nEdge {c1_id}-{c2_id}:")
    print(f"  Points: {c1} -> {c2}")
    print(f"  Direction: {edge_dir}")
    print(f"  Length: {edge_len:.1f}")
    print(f"  Angle with bend line: {angle_deg:.1f}°")
    if is_parallel:
        print(f"  [PARALLEL] Good for bending")
    elif is_perpendicular:
        print(f"  [PERPENDICULAR] Should be filtered!")
    else:
        print(f"  [ANGLED] May work")

print(f"\n\nANALYZING TAB 1 EDGES:")
print("-"*80)
for edge in edges_1:
    c1_id, c2_id = edge
    c1 = tab_1.points[c1_id]
    c2 = tab_1.points[c2_id]
    edge_vec = c2 - c1
    edge_len = np.linalg.norm(edge_vec)
    edge_dir = edge_vec / edge_len if edge_len > 1e-9 else edge_vec

    # Calculate angle with bend line
    dot_product = abs(np.dot(edge_dir, bend_line['orientation']))
    angle_rad = np.arccos(np.clip(dot_product, 0, 1))
    angle_deg = np.degrees(angle_rad)

    is_parallel = angle_deg < 15
    is_perpendicular = angle_deg > 75

    print(f"\nEdge {c1_id}-{c2_id}:")
    print(f"  Points: {c1} -> {c2}")
    print(f"  Direction: {edge_dir}")
    print(f"  Length: {edge_len:.1f}")
    print(f"  Angle with bend line: {angle_deg:.1f}°")
    if is_parallel:
        print(f"  [PARALLEL] Good for bending")
    elif is_perpendicular:
        print(f"  [PERPENDICULAR] Should be filtered!")
    else:
        print(f"  [ANGLED] May work")

# Generate segments and analyze which edge combinations succeeded
segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)
segments = one_bend(segment, filter_cfg)

print("\n" + "="*80)
print(f"ONE_BEND GENERATED {len(segments)} SEGMENTS")
print("="*80)

# For each segment, identify which edges were used
for i, seg in enumerate(segments):
    print(f"\n--- Segment {i+1} ---")

    tab_x = seg.tabs['tab_x']
    tab_z = seg.tabs['tab_z']

    # Find which corners appear before/after bend points in tab_x
    corner_order_x = list(tab_x.points.keys())
    bp_indices_x = [idx for idx, k in enumerate(corner_order_x) if 'BP' in k]

    if len(bp_indices_x) >= 1:
        # Find corners adjacent to bend points
        before_bp = corner_order_x[bp_indices_x[0] - 1] if bp_indices_x[0] > 0 else None
        after_last_bp = corner_order_x[bp_indices_x[-1] + 1] if bp_indices_x[-1] < len(corner_order_x) - 1 else None

        # Identify the edge
        corners_x = [k for k in corner_order_x if k in ['A', 'B', 'C', 'D']]
        print(f"  Tab 0 corners in order: {corners_x}")
        print(f"  Bend points after: {before_bp}")

        # Determine which edge
        for j in range(len(corners_x)):
            if corners_x[j] == before_bp:
                next_corner = corners_x[(j+1) % len(corners_x)]
                edge_used_x = (before_bp, next_corner)
                print(f"  Tab 0 edge used: {edge_used_x}")

                # Calculate angle for this edge
                c1 = tab_0.points[edge_used_x[0]]
                c2 = tab_0.points[edge_used_x[1]]
                edge_vec = c2 - c1
                edge_dir = edge_vec / np.linalg.norm(edge_vec)
                dot_product = abs(np.dot(edge_dir, bend_line['orientation']))
                angle_deg = np.degrees(np.arccos(np.clip(dot_product, 0, 1)))
                print(f"  Tab 0 edge angle: {angle_deg:.1f}°")

                if angle_deg > 75:
                    print(f"  [ERROR] Edge is PERPENDICULAR to bend line!")
                break

    # Same for tab_z
    corner_order_z = list(tab_z.points.keys())
    bp_indices_z = [idx for idx, k in enumerate(corner_order_z) if 'BP' in k]

    if len(bp_indices_z) >= 1:
        before_bp = corner_order_z[bp_indices_z[0] - 1] if bp_indices_z[0] > 0 else None
        corners_z = [k for k in corner_order_z if k in ['A', 'B', 'C', 'D']]

        for j in range(len(corners_z)):
            if corners_z[j] == before_bp:
                next_corner = corners_z[(j+1) % len(corners_z)]
                edge_used_z = (before_bp, next_corner)
                print(f"  Tab 1 edge used: {edge_used_z}")

                c1 = tab_1.points[edge_used_z[0]]
                c2 = tab_1.points[edge_used_z[1]]
                edge_vec = c2 - c1
                edge_dir = edge_vec / np.linalg.norm(edge_vec)
                dot_product = abs(np.dot(edge_dir, bend_line['orientation']))
                angle_deg = np.degrees(np.arccos(np.clip(dot_product, 0, 1)))
                print(f"  Tab 1 edge angle: {angle_deg:.1f}°")

                if angle_deg > 75:
                    print(f"  [ERROR] Edge is PERPENDICULAR to bend line!")
                break

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
print("one_bend should filter out edge pairs where EITHER edge is perpendicular")
print("to the bend line (angle > 75°). These create infeasible geometries.")

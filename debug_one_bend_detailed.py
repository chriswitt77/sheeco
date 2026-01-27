"""
Detailed analysis of which edges one_bend uses and why perpendicular edges aren't filtered.
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

# Initialize part
part = initialize_objects(transportschuh)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

# Calculate bend line
plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)
bend_line = calculate_plane_intersection(plane_0, plane_1)

print("="*80)
print("DETAILED ANALYSIS OF BEND POINT PLACEMENT")
print("="*80)

# Generate segments
segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)
segments = one_bend(segment, filter_cfg)

print(f"\nGenerated {len(segments)} segments\n")

for i, seg in enumerate(segments):
    print(f"{'='*80}")
    print(f"SEGMENT {i+1}")
    print(f"{'='*80}")

    tab_x = seg.tabs['tab_x']
    tab_z = seg.tabs['tab_z']

    # Analyze tab_x
    print(f"\nTab 0 point sequence:")
    for j, (name, coord) in enumerate(tab_x.points.items()):
        marker = ""
        if 'BP' in name:
            marker = " <- BEND POINT"
        elif 'FP' in name:
            marker = " <- FLANGE POINT"
        elif name in ['A', 'B', 'C', 'D']:
            marker = " <- CORNER"
        print(f"  {j}: {name:15s} {coord} {marker}")

    # Find which corner the bend is inserted after
    corners_list = list(tab_x.points.keys())
    bend_indices = [idx for idx, name in enumerate(corners_list) if 'BP' in name]

    if bend_indices:
        first_bend_idx = bend_indices[0]

        # Find the corner BEFORE the bend points
        before_corner = None
        for idx in range(first_bend_idx - 1, -1, -1):
            if corners_list[idx] in ['A', 'B', 'C', 'D']:
                before_corner = corners_list[idx]
                break
        if before_corner is None:
            # Wrap around from end
            for idx in range(len(corners_list) - 1, -1, -1):
                if corners_list[idx] in ['A', 'B', 'C', 'D']:
                    before_corner = corners_list[idx]
                    break

        # Find the corner AFTER the bend points
        last_bend_idx = bend_indices[-1]
        next_corner = None
        for idx in range(last_bend_idx + 1, len(corners_list)):
            if corners_list[idx] in ['A', 'B', 'C', 'D']:
                next_corner = corners_list[idx]
                break
        if next_corner is None:
            # Wrap around from start
            for idx in range(len(corners_list)):
                if corners_list[idx] in ['A', 'B', 'C', 'D']:
                    next_corner = corners_list[idx]
                    break

        if before_corner and next_corner:
            print(f"\n  Bend inserted between corners: {before_corner} and {next_corner}")
            print(f"  Edge: {before_corner}-{next_corner}")

            # Calculate edge angle
            c1 = tab_0.points[before_corner]
            c2 = tab_0.points[next_corner]
            edge_vec = c2 - c1
            edge_len = np.linalg.norm(edge_vec)
            if edge_len > 1e-9:
                edge_dir = edge_vec / edge_len
                dot_product = abs(np.dot(edge_dir, bend_line['orientation']))
                angle_deg = np.degrees(np.arccos(np.clip(dot_product, 0, 1)))
                print(f"  Edge angle to bend line: {angle_deg:.1f}°")

                if angle_deg > 75:
                    print(f"  *** PERPENDICULAR EDGE - SHOULD BE FILTERED ***")

    # Analyze tab_z
    print(f"\nTab 1 point sequence:")
    for j, (name, coord) in enumerate(tab_z.points.items()):
        marker = ""
        if 'BP' in name:
            marker = " <- BEND POINT"
        elif 'FP' in name:
            marker = " <- FLANGE POINT"
        elif name in ['A', 'B', 'C', 'D']:
            marker = " <- CORNER"
        print(f"  {j}: {name:15s} {coord} {marker}")

    corners_list_z = list(tab_z.points.keys())
    bend_indices_z = [idx for idx, name in enumerate(corners_list_z) if 'BP' in name]

    if bend_indices_z:
        first_bend_idx = bend_indices_z[0]

        # Find the corner BEFORE the bend points
        before_corner = None
        for idx in range(first_bend_idx - 1, -1, -1):
            if corners_list_z[idx] in ['A', 'B', 'C', 'D']:
                before_corner = corners_list_z[idx]
                break
        if before_corner is None:
            for idx in range(len(corners_list_z) - 1, -1, -1):
                if corners_list_z[idx] in ['A', 'B', 'C', 'D']:
                    before_corner = corners_list_z[idx]
                    break

        # Find the corner AFTER the bend points
        last_bend_idx = bend_indices_z[-1]
        next_corner = None
        for idx in range(last_bend_idx + 1, len(corners_list_z)):
            if corners_list_z[idx] in ['A', 'B', 'C', 'D']:
                next_corner = corners_list_z[idx]
                break
        if next_corner is None:
            for idx in range(len(corners_list_z)):
                if corners_list_z[idx] in ['A', 'B', 'C', 'D']:
                    next_corner = corners_list_z[idx]
                    break

        if before_corner and next_corner:
            print(f"\n  Bend inserted between corners: {before_corner} and {next_corner}")
            print(f"  Edge: {before_corner}-{next_corner}")

            c1 = tab_1.points[before_corner]
            c2 = tab_1.points[next_corner]
            edge_vec = c2 - c1
            edge_len = np.linalg.norm(edge_vec)
            if edge_len > 1e-9:
                edge_dir = edge_vec / edge_len
                dot_product = abs(np.dot(edge_dir, bend_line['orientation']))
                angle_deg = np.degrees(np.arccos(np.clip(dot_product, 0, 1)))
                print(f"  Edge angle to bend line: {angle_deg:.1f}°")

                if angle_deg > 75:
                    print(f"  *** PERPENDICULAR EDGE - SHOULD BE FILTERED ***")

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print(f"one_bend needs to filter out edge pairs where EITHER edge")
print(f"is perpendicular (>75°) to the bend line direction.")
print(f"\nThis check is MISSING from the current implementation!")

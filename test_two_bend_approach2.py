"""
Test two-bend approach 2 (fallback) to verify point ordering fix
"""
import yaml
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import RECTANGLE_INPUTS
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part, initialize_objects, determine_sequences, create_segments

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

# Initialize
part = initialize_objects(RECTANGLE_INPUTS)
variants = determine_sequences(part, cfg)
variant_part, sequences = variants[0]  # Unseparated variant

# Create segments for first pair
pair = sequences[0][0]
tab_x = variant_part.tabs[pair[0]]
tab_z = variant_part.tabs[pair[1]]

segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
segment = Part(sequence=pair, tabs=segment_tabs)

segments = create_segments(segment, segment_cfg, filter_cfg)

# Find two-bend segments
two_bend_segments = [s for s in segments if len(s.tabs) == 3]

print(f"\n{'='*70}")
print(f"TWO-BEND APPROACH 2 GEOMETRY ANALYSIS")
print(f"{'='*70}\n")
print(f"Found {len(two_bend_segments)} two-bend segments\n")

if two_bend_segments:
    # Examine first two-bend segment
    seg = two_bend_segments[0]

    for tab_id, tab in seg.tabs.items():
        print(f"\n{'-'*70}")
        print(f"{tab_id} (original tab {tab.tab_id}):")
        print(f"  Perimeter order: {list(tab.points.keys())}")

        # Group points by type
        corners = {k: v for k, v in tab.points.items() if k in ['A', 'B', 'C', 'D']}
        fp_points = {k: v for k, v in tab.points.items() if k.startswith('FP')}
        bp_points = {k: v for k, v in tab.points.items() if k.startswith('BP')}

        print(f"\n  Point counts:")
        print(f"    Corners: {len(corners)}")
        print(f"    Flange Points (FP): {len(fp_points)}")
        print(f"    Bend Points (BP): {len(bp_points)}")

        if corners:
            print(f"\n  Corners present: {list(corners.keys())}")
            for c_id, c_coord in corners.items():
                print(f"    {c_id}: {c_coord}")
        else:
            print(f"\n  WARNING: No corners found!")

        if fp_points:
            print(f"\n  Flange Points (FP):")
            for fp_id, fp_coord in fp_points.items():
                print(f"    {fp_id}: {fp_coord}")

                # Check distance to nearest corner
                if corners:
                    min_dist = min(np.linalg.norm(fp_coord - c_coord) for c_coord in corners.values())
                    nearest_corner = min(corners.items(), key=lambda x: np.linalg.norm(fp_coord - x[1]))
                    print(f"      -> Distance to nearest corner {nearest_corner[0]}: {min_dist:.2f}mm")

        if bp_points:
            print(f"\n  Bend Points (BP):")
            for bp_id, bp_coord in bp_points.items():
                print(f"    {bp_id}: {bp_coord}")

        # Verify perimeter validity
        print(f"\n  Perimeter validation:")
        points_list = list(tab.points.items())

        # Check for consecutive duplicates
        duplicates = []
        for i in range(len(points_list)):
            curr_id, curr_pt = points_list[i]
            next_id, next_pt = points_list[(i+1) % len(points_list)]
            dist = np.linalg.norm(next_pt - curr_pt)
            if dist < 0.001:
                duplicates.append((curr_id, next_id))

        if duplicates:
            print(f"    WARNING: Found duplicate consecutive points: {duplicates}")
        else:
            print(f"    OK: No duplicate consecutive points")

        # Check edge flow
        print(f"\n  Edge flow:")
        total_length = 0
        for i in range(len(points_list)):
            curr_id, curr_pt = points_list[i]
            next_id, next_pt = points_list[(i+1) % len(points_list)]
            edge_length = np.linalg.norm(next_pt - curr_pt)
            total_length += edge_length
            if edge_length > 1.0:
                print(f"    {curr_id} -> {next_id}: {edge_length:.2f}mm")

        print(f"  Total perimeter: {total_length:.2f}mm")

    print(f"\n{'='*70}\n")

    # Check if intermediate tab (tab_y) has expected structure
    if 'tab_y' in seg.tabs or 'tab_XY' in seg.tabs or len(seg.tabs) == 3:
        # Find the intermediate tab (the one with two bend connections)
        intermediate_tabs = []
        for tab_id, tab in seg.tabs.items():
            fp_count = len([k for k in tab.points.keys() if k.startswith('FP')])
            if fp_count >= 4:  # Intermediate tab should have FP from both connections
                intermediate_tabs.append((tab_id, tab))

        if intermediate_tabs:
            print(f"Intermediate tab analysis:")
            for tab_id, tab in intermediate_tabs:
                print(f"\n  {tab_id}:")
                print(f"    Perimeter: {list(tab.points.keys())}")
                print(f"    Total points: {len(tab.points)}")

                # Expected structure: [FPyxL, BPxL, BPxR, FPyxR, FPyzR, BPzR, BPzL, FPyzL]
                # or similar, with 8 points total (4 FP, 4 BP)
                fp_count = len([k for k in tab.points.keys() if k.startswith('FP')])
                bp_count = len([k for k in tab.points.keys() if k.startswith('BP')])
                print(f"    FP count: {fp_count} (expected: 4)")
                print(f"    BP count: {bp_count} (expected: 4)")

else:
    print("No two-bend segments found!")

print("\nTest complete!")

"""
Test one-bend geometry to verify Direct Power Flows implementation
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

# Find first one-bend segment
one_bend_segments = [s for s in segments if len(s.tabs) == 2]

if one_bend_segments:
    seg = one_bend_segments[0]
    print(f"\n{'='*70}")
    print(f"ONE-BEND SEGMENT GEOMETRY ANALYSIS")
    print(f"{'='*70}\n")

    for tab_id, tab in seg.tabs.items():
        print(f"\n{tab_id} (original tab {tab.tab_id}):")
        print(f"  Perimeter order: {list(tab.points.keys())}")

        # Group points by type
        corners = {k: v for k, v in tab.points.items() if k in ['A', 'B', 'C', 'D']}
        fp_points = {k: v for k, v in tab.points.items() if k.startswith('FP')}
        bp_points = {k: v for k, v in tab.points.items() if k.startswith('BP')}

        if corners:
            print(f"\n  Corners:")
            for c_id, c_coord in corners.items():
                print(f"    {c_id}: {c_coord}")

        if fp_points:
            print(f"\n  Flange Points (FP):")
            for fp_id, fp_coord in fp_points.items():
                print(f"    {fp_id}: {fp_coord}")

                # Check distance to nearest corner
                if corners:
                    min_dist = min(np.linalg.norm(fp_coord - c_coord) for c_coord in corners.values())
                    print(f"      -> Distance to nearest corner: {min_dist:.2f}mm")

        if bp_points:
            print(f"\n  Bend Points (BP):")
            for bp_id, bp_coord in bp_points.items():
                print(f"    {bp_id}: {bp_coord}")

        # Check perimeter flow
        print(f"\n  Perimeter flow check:")
        points_list = list(tab.points.items())
        total_length = 0
        for i in range(len(points_list)):
            curr_id, curr_pt = points_list[i]
            next_id, next_pt = points_list[(i+1) % len(points_list)]
            edge_length = np.linalg.norm(next_pt - curr_pt)
            total_length += edge_length
            if edge_length > 1.0:  # Only show significant edges
                print(f"    {curr_id} -> {next_id}: {edge_length:.2f}mm")

        print(f"  Total perimeter: {total_length:.2f}mm")

    print(f"\n{'='*70}\n")
else:
    print("No one-bend segments found!")

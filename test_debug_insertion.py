"""
Debug script to understand which edge is selected and where insertion happens
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
variant_part, sequences = variants[1]  # Separated variant

print(f"Sequences: {sequences[0]}")

# Process only second pair (0_1)
pair = sequences[0][1]  # Should be ['1', '0_1']
print(f"Selected pair: {pair}")
tab_x = variant_part.tabs[pair[0]]
tab_z = variant_part.tabs[pair[1]]

print(f"\nProcessing pair: {pair}")
print(f"\nTab {pair[1]} (tab_z) corners:")
for c_id, c_coord in tab_z.rectangle.points.items():
    print(f"  {c_id}: {c_coord}")

# Create edge list
rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),
                ('B', 'A'), ('C', 'B'), ('D', 'C'), ('A', 'D')]

print(f"\nEdges to test:")
for edge in rect_z_edges:
    print(f"  {edge[0]} -> {edge[1]}")

segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
segment = Part(sequence=pair, tabs=segment_tabs)

# Temporarily enable debug output in bend_strategies by uncommenting print statements
segments = create_segments(segment, segment_cfg, filter_cfg)

print(f"\n{len(segments)} two-bend segments generated")

for i, seg in enumerate(segments):
    tab_z_result = seg.tabs.get('tab_z')
    if tab_z_result:
        perimeter = list(tab_z_result.points.keys())

        # Check if flange is between A and B (correct) or after D (wrong)
        fp_indices = [j for j, key in enumerate(perimeter) if key.startswith('FP')]
        a_idx = perimeter.index('A') if 'A' in perimeter else -1
        b_idx = perimeter.index('B') if 'B' in perimeter else -1
        d_idx = perimeter.index('D') if 'D' in perimeter else -1

        if fp_indices:
            fp_idx = fp_indices[0]

            # Check if FP is between A and B (correct) or after D (wrong)
            if a_idx >= 0 and b_idx >= 0 and d_idx >= 0:
                if a_idx < fp_idx < b_idx or (a_idx == 0 and fp_idx < b_idx):
                    status = "OK - CORRECT (between A and B)"
                elif fp_idx > d_idx:
                    status = "ERROR - WRONG (after D)"
                else:
                    status = "? OTHER"
            else:
                status = "? MISSING CORNERS"

            print(f"\nSegment {i}: {status}")
            print(f"  Perimeter: {perimeter}")

            # Show BP points
            bp_points = {k: v for k, v in tab_z_result.points.items() if k.startswith('BP')}
            if bp_points:
                print(f"  BP points:")
                for bp_id, bp_coord in bp_points.items():
                    print(f"    {bp_id}: {bp_coord}")

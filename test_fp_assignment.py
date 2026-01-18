"""
Test to see what FP coordinates are actually being assigned to tabs
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

# Process BOTH pairs
print(f"Full sequence: {sequences[0]}\n")

for pair_idx, pair in enumerate(sequences[0]):
    print(f"\n{'#'*70}")
    print(f"# PROCESSING PAIR {pair_idx+1}: {pair}")
    print(f"{'#'*70}\n")

    tab_x = variant_part.tabs[pair[0]]
    tab_z = variant_part.tabs[pair[1]]

    print(f"Tab {pair[0]} (tab_x) corners:")
    for c_id in ['A', 'B', 'C', 'D']:
        if c_id in tab_x.rectangle.points:
            print(f"  {c_id}: {tab_x.rectangle.points[c_id]}")

    print(f"\nTab {pair[1]} (tab_z) corners:")
    for c_id in ['A', 'B', 'C', 'D']:
        if c_id in tab_z.rectangle.points:
            print(f"  {c_id}: {tab_z.rectangle.points[c_id]}")

    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment = Part(sequence=pair, tabs=segment_tabs)

    segments = create_segments(segment, segment_cfg, filter_cfg)

    # Find two-bend segments
    two_bend_segments = [s for s in segments if len(s.tabs) == 3]

    print(f"\n{len(two_bend_segments)} two-bend segments generated\n")

    if two_bend_segments:
        for seg_idx, seg in enumerate(two_bend_segments):
            print("="*70)
            print(f"SEGMENT {seg_idx + 1}")
            print("="*70)

            for tab_id, tab in seg.tabs.items():
                print(f"\n{tab_id}:")
                print(f"  Original tab ID: {tab.tab_id}")
                perimeter = list(tab.points.keys())
                print(f"  Perimeter: {perimeter}")

                # Check insertion order for tab_z
                if tab_id == 'tab_z' and all(c in perimeter for c in ['A', 'B', 'D']):
                    a_idx = perimeter.index('A')
                    b_idx = perimeter.index('B')
                    d_idx = perimeter.index('D')
                    fp_indices = [i for i, k in enumerate(perimeter) if k.startswith('FP')]

                    if fp_indices:
                        fp_idx = fp_indices[0]
                        if a_idx < fp_idx < b_idx:
                            print(f"  Insertion: OK (between A and B)")
                        elif fp_idx > d_idx:
                            print(f"  Insertion: WRONG (after D)")
                        else:
                            print(f"  Insertion: OTHER (fp_idx={fp_idx}, a={a_idx}, b={b_idx}, d={d_idx})")

                # Show FP points
                fp_points = {k: v for k, v in tab.points.items() if k.startswith('FP')}
                if fp_points:
                    print(f"  FP points:")
                    for fp_id, fp_coord in fp_points.items():
                        print(f"    {fp_id}: {fp_coord}")
            print()

    else:
        print("No two-bend segments found!")

    if pair_idx < len(sequences[0]) - 1:
        print("\n\n")

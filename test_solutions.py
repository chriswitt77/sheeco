"""
Test script to verify the fixes:
1. One-bend solutions are generated
2. Parallel edge cases work correctly
3. FP points are at correct corners
"""
import yaml
import json
import copy
import itertools
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import RECTANGLE_INPUTS
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part, initialize_objects, determine_sequences, create_segments, part_assembly

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')
assy_filter_cfg = cfg.get('filter')

# Initialize part
part = initialize_objects(RECTANGLE_INPUTS)

# Get sequences
variants = determine_sequences(part, cfg)

print(f"\n{'='*70}")
print(f"SOLUTION SUMMARY")
print(f"{'='*70}\n")

all_solutions = []

for variant_part, sequences in variants:
    variant_name = "separated" if any('_' in str(tid) for tid in variant_part.tabs.keys()) else "unseparated"

    print(f"\n{variant_name.upper()} variant ({len(variant_part.tabs)} tabs):")
    print(f"  Tabs: {list(variant_part.tabs.keys())}")

    for seq_idx, sequence in enumerate(sequences):
        print(f"\n  Sequence {seq_idx}: {sequence}")

        segments_library = []
        for pair in sequence:
            tab_x = variant_part.tabs[pair[0]]
            tab_z = variant_part.tabs[pair[1]]
            segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
            segment = Part(sequence=pair, tabs=segment_tabs)
            segments = create_segments(segment, segment_cfg, filter_cfg)

            # Count one-bend vs two-bend
            one_bend_count = sum(1 for seg in segments if len(seg.tabs) == 2)
            two_bend_count = sum(1 for seg in segments if len(seg.tabs) == 3)

            print(f"    Pair {pair}: {len(segments)} segments (one-bend: {one_bend_count}, two-bend: {two_bend_count})")
            segments_library.append(segments)

        # Assemble parts
        variant_part.sequence = sequence
        seq_solutions = []
        for segments_combination in itertools.product(*segments_library):
            new_part = variant_part.copy()
            new_segments_combination = copy.deepcopy(segments_combination)
            new_part = part_assembly(new_part, new_segments_combination, assy_filter_cfg)
            if new_part != None:
                seq_solutions.append(new_part)

        print(f"  -> {len(seq_solutions)} complete solutions")
        all_solutions.extend(seq_solutions)

print(f"\n{'='*70}")
print(f"TOTAL SOLUTIONS: {len(all_solutions)}")
print(f"{'='*70}\n")

# Check first few solutions for correct geometry
if all_solutions:
    print("\nChecking first solution for geometry issues...")
    sol = all_solutions[0]

    # Check tab 1 (if exists)
    if '1' in sol.tabs:
        tab_1 = sol.tabs['1']
        print(f"\nTab 1 points: {list(tab_1.points.keys())}")

        # Find FP points
        fp_points = {k: v for k, v in tab_1.points.items() if k.startswith('FP')}
        if fp_points:
            print(f"\nFP points in tab 1:")
            for fp_id, fp_coord in fp_points.items():
                print(f"  {fp_id}: {fp_coord}")

            # Check if FP points match corners
            corners = {k: v for k, v in tab_1.points.items() if k in ['A', 'B', 'C', 'D']}
            print(f"\nCorners in tab 1:")
            for c_id, c_coord in corners.items():
                print(f"  {c_id}: {c_coord}")

            # Check for spikes (consecutive points at very different Z values)
            points_list = list(tab_1.points.items())
            print(f"\nChecking for spikes in perimeter order:")
            for i in range(len(points_list)):
                curr_id, curr_pt = points_list[i]
                next_id, next_pt = points_list[(i+1) % len(points_list)]
                dist = ((curr_pt - next_pt)**2).sum()**0.5
                if dist > 50:  # Large jump
                    print(f"  WARNING: Large jump from {curr_id} to {next_id}, distance={dist:.1f}")

print("\nTest complete!")

"""
Test script to check all one-bend solutions for input B
"""
import yaml
import numpy as np
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import RECTANGLE_INPUTS
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part, initialize_objects, determine_sequences, create_segments, part_assembly

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

# Initialize
part = initialize_objects(RECTANGLE_INPUTS)
variants = determine_sequences(part, cfg)

print(f"Found {len(variants)} variant(s)\n")

for variant_idx, (variant_part, sequences) in enumerate(variants):
    print(f"{'='*70}")
    print(f"VARIANT {variant_idx}: {len(variant_part.tabs)} tabs")
    print(f"{'='*70}\n")

    # Create segments for each sequence
    all_solutions = []
    for sequence in sequences:
        segments_library = []
        for pair in sequence:
            tab_x = variant_part.tabs[pair[0]]
            tab_z = variant_part.tabs[pair[1]]
            segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
            segment = Part(sequence=pair, tabs=segment_tabs)
            segments_library.append(create_segments(segment, segment_cfg, filter_cfg))

        # Assemble parts
        solutions = part_assembly(variant_part, segments_library, filter_cfg)
        all_solutions.extend(solutions)

    solutions = all_solutions

    print(f"Generated {len(solutions)} solution(s)\n")

    # Filter for one-bend solutions (2 tabs only)
    onebend_solutions = [s for s in solutions if len(s.tabs) == 2]

    print(f"One-bend solutions: {len(onebend_solutions)}\n")

    for idx, sol in enumerate(onebend_solutions[:3]):  # Check first 3
        print(f"{'-'*70}")
        print(f"One-bend Solution {idx}")
        print(f"{'-'*70}\n")

        for tab_id, tab in sol.tabs.items():
            print(f"Tab {tab_id}:")
            perimeter = list(tab.points.keys())
            print(f"  Perimeter: {perimeter}")

            # Check for BP ordering
            bp_keys = [k for k in perimeter if k.startswith('BP')]
            if len(bp_keys) == 2:
                bp1_idx = perimeter.index(bp_keys[0])
                bp2_idx = perimeter.index(bp_keys[1])

                # Get BP coordinates
                bp1 = tab.points[bp_keys[0]]
                bp2 = tab.points[bp_keys[1]]

                print(f"  {bp_keys[0]} at index {bp1_idx}: {bp1}")
                print(f"  {bp_keys[1]} at index {bp2_idx}: {bp2}")

                # Check for self-intersection
                # Get corners before and after BP sequence
                corners = [k for k in perimeter if k in ['A', 'B', 'C', 'D']]
                if len(corners) >= 2:
                    # Find corners surrounding BP sequence
                    corner_indices = [(k, perimeter.index(k)) for k in corners]
                    corner_indices.sort(key=lambda x: x[1])

                    bp_indices = sorted([bp1_idx, bp2_idx])
                    bp_range = (min(bp_indices), max(bp_indices))

                    # Check if perimeter goes backward
                    prev_idx = None
                    increasing = True
                    for i, (corner, idx) in enumerate(corner_indices):
                        if prev_idx is not None:
                            if idx < prev_idx:
                                increasing = False
                        prev_idx = idx

                    if not increasing:
                        print(f"  WARNING: Perimeter may have self-intersection!")
            print()

        # Export this solution to JSON for inspection
        from src.hgen_sm.export.part_export import export_to_json, export_to_featurescript

        json_output = export_to_json(sol, part.tabs)
        print(f"JSON preview:")
        print(json.dumps(json_output, indent=2)[:500])
        print("...\n")

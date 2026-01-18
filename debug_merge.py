"""
Debug script to understand the point merging issue in split surfaces.
"""

import yaml
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import RECTANGLE_INPUTS

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part
from src.hgen_sm import initialize_objects, determine_sequences, create_segments, part_assembly
from src.hgen_sm.part_assembly.merge_helpers import extract_tabs_from_segments

def main():
    segment_cfg = cfg.get('design_exploration')
    filter_cfg = cfg.get('filter')

    # ---- Import user input ----
    part = initialize_objects(RECTANGLE_INPUTS)

    # ---- Determine sensible Topologies ----
    variants = determine_sequences(part, cfg)

    # ---- Find ways to connect pairs ----
    for variant_part, sequences in variants:
        variant_name = "separated" if any('_' in str(tid) for tid in variant_part.tabs.keys()) else "unseparated"

        # Skip unseparated variants
        if variant_name == "unseparated":
            continue

        print(f"\n{'='*60}")
        print(f"Processing {variant_name} variant")
        print(f"{'='*60}")
        print(f"Tabs: {list(variant_part.tabs.keys())}")

        for sequence in sequences:
            print(f"\nSequence: {sequence}")

            segments_library = []
            for pair in sequence:
                tab_x = variant_part.tabs[pair[0]]
                tab_z = variant_part.tabs[pair[1]]
                segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
                segment = Part(sequence=pair, tabs=segment_tabs)
                segments_library.append(create_segments(segment, segment_cfg, filter_cfg))

            # ---- Debug: Look at Tab 1 before assembly ----
            # Tab 1 should appear in TWO segments (connecting to 0_0 and 0_1)

            print(f"\n--- Looking for Tab 1 in segments ---")
            tab_1_appearances = []
            for seg_idx, seg_library in enumerate(segments_library):
                if len(seg_library) > 0:
                    # Take first segment from library
                    segment = seg_library[0]
                    for tab_key, tab in segment.tabs.items():
                        if tab.tab_id == '1':
                            tab_1_appearances.append({
                                'segment_idx': seg_idx,
                                'pair': sequence[seg_idx],
                                'tab_key': tab_key,
                                'points': list(tab.points.keys()),
                                'points_dict': tab.points.copy()
                            })

            print(f"\nTab 1 appears in {len(tab_1_appearances)} segments:")
            for i, appearance in enumerate(tab_1_appearances):
                print(f"\n  Appearance {i+1}: Connection {appearance['pair']}")
                print(f"    Tab key: {appearance['tab_key']}")
                print(f"    Points ({len(appearance['points'])}): {appearance['points']}")

            # Now let's manually test the merge
            if len(tab_1_appearances) == 2:
                from src.hgen_sm.part_assembly.merge_helpers import merge_points

                print(f"\n{'='*60}")
                print("TESTING MERGE OF TAB 1")
                print(f"{'='*60}")

                # Extract the two versions of Tab 1
                tabs_to_merge = [extract_tabs_from_segments('1', [seg_library[0] for seg_library in segments_library])[i]
                                 for i in range(2)]

                print(f"\nTab 1 Version 1 (from segment {tab_1_appearances[0]['pair']}):")
                print(f"  Points: {list(tabs_to_merge[0].points.keys())}")

                print(f"\nTab 1 Version 2 (from segment {tab_1_appearances[1]['pair']}):")
                print(f"  Points: {list(tabs_to_merge[1].points.keys())}")

                # Attempt merge
                merged = merge_points(tabs_to_merge)

                if merged:
                    print(f"\nMerged result ({len(merged)} points):")
                    print(f"  {list(merged.keys())}")

                    # Check for proper ordering - find where bend points are
                    point_keys = list(merged.keys())
                    corners = ['A', 'B', 'C', 'D']
                    print(f"\n  Corner positions:")
                    for corner in corners:
                        if corner in point_keys:
                            idx = point_keys.index(corner)
                            print(f"    {corner}: position {idx}")

                else:
                    print(f"\nMerge FAILED!")

            # Also show what points Tab 0_0 has
            print(f"\n--- Tab 0_0 initial state ---")
            tab_0_0_appearances = []
            for seg_idx, seg_library in enumerate(segments_library):
                if len(seg_library) > 0:
                    segment = seg_library[0]
                    for tab_key, tab in segment.tabs.items():
                        if tab.tab_id == '0_0':
                            print(f"  From segment {sequence[seg_idx]}: {list(tab.points.keys())}")

            # Stop after first sequence
            break

        # Stop after first separated variant
        break

if __name__ == "__main__":
    main()

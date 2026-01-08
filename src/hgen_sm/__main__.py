import time

start_time = time.time()

import yaml
from pathlib import Path
import copy
import itertools
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

from config.user_input import RECTANGLE_INPUTS

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part
from src.hgen_sm import initialize_objects, determine_sequences, create_segments, part_assembly, plot_solutions
from config.design_rules import min_dist_mount_bend
from src.hgen_sm.create_segments.segment_combination_filter import filter_segment_combinations


def main():
    segment_cfg = cfg.get('design_exploration')
    plot_cfg = cfg.get('plot')
    filter_cfg = cfg.get('filter')
    mount_cfg = cfg.get('mount_preprocessing', {})

    # Add verbose to filter_cfg if not present
    if 'verbose' not in filter_cfg:
        filter_cfg['verbose'] = True

    # ---- Import user input with mount preprocessing ----
    part = initialize_objects(
        RECTANGLE_INPUTS,
        min_mount_distance=min_dist_mount_bend,
        preprocess_mounts=mount_cfg.get('enabled', True),
        verbose=mount_cfg.get('verbose', True)
    )

    # ---- Determine sensible Topologies (with optional surface separation) ----
    part, sequences = determine_sequences(part, cfg)

    print(f"\n{'=' * 60}")
    print(f"After surface separation: {len(part.tabs)} tabs")
    print(f"Tab IDs: {list(part.tabs.keys())}")
    print(f"Generated {len(sequences)} sequence(s)")
    if sequences:
        print(f"First sequence: {sequences[0]}")
    print(f"{'=' * 60}\n")

    # ---- Find ways to connect pairs ----
    solutions = []
    part_id: int = 0

    for sequence in sequences:
        segments_library = []

        # ✅ STEP 1: Collect all segments for all pairs
        for pair in sequence:
            tab_x_id = pair[0]
            tab_z_id = pair[1]

            # Debug: Check if IDs exist in part.tabs
            if tab_x_id not in part.tabs:
                print(f"ERROR: Tab ID '{tab_x_id}' not found in part.tabs!")
                print(f"Available tabs: {list(part.tabs.keys())}")
                continue

            if tab_z_id not in part.tabs:
                print(f"ERROR: Tab ID '{tab_z_id}' not found in part.tabs!")
                print(f"Available tabs: {list(part.tabs.keys())}")
                continue

            tab_x = part.tabs[tab_x_id]
            tab_z = part.tabs[tab_z_id]

            segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
            segment = Part(sequence=pair, tabs=segment_tabs)

            segments = create_segments(segment, segment_cfg, filter_cfg)
            print(f"  Pair {pair}: {len(segments)} segment(s) found")
            segments_library.append(segments)

        # Check if all pairs produced segments
        if any(len(segs) == 0 for segs in segments_library):
            print(f"  → Skipping sequence (some pairs produced no segments)")
            continue

        # ✅ STEP 2: Filter combinations AFTER collecting all segments
        total_combinations = int(np.prod([len(s) for s in segments_library]))
        print(f"\n  Total combinations before filter: {total_combinations}")

        valid_combinations = filter_segment_combinations(segments_library, sequence)

        print(f"  Valid combinations after filter: {len(valid_combinations)}")

        if len(valid_combinations) == 0:
            print(f"  → Skipping sequence (all combinations would collide)")
            continue

        # ✅ STEP 3: Assemble using the FILTERED combinations
        part.sequence = sequence

        for segments_combination in valid_combinations:  # ← Use filtered list directly
            new_part = part.copy()
            new_segments_combination = copy.deepcopy(segments_combination)
            new_part = part_assembly(new_part, new_segments_combination, filter_cfg)

            if new_part == None:
                continue

            part_id += 1
            new_part.part_id = part_id
            solutions.append(new_part)

    print("\n" + "=" * 60)
    print("--- %s seconds ---" % (time.time() - start_time))
    print(f"Found {len(solutions)} solutions")
    print("=" * 60)

    if len(solutions) == 0:
        print("\nNo solutions found. Possible reasons:")
        print("  - No valid segments could be created for the pairs")
        print("  - Segments were filtered out by constraints")
        print("  - Part assembly failed for all combinations")
        print("\nTry:")
        print("  - Disable collision filter temporarily")
        print("  - Check mount preprocessing distances")
        print("  - Verify surface separation settings")
        return

    #  ---- plot solutions ----
    plot_solutions(solutions, plot_cfg=plot_cfg)


if __name__ == '__main__':
    main()
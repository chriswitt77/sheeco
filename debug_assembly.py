import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import shock_absorber_double_tab, shock_absorber_double_tab_sequence

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

import copy
import itertools
from src.hgen_sm import Part, initialize_objects, create_segments
from src.hgen_sm.part_assembly.merge_helpers import extract_tabs_from_segments, merge_points
from src.hgen_sm.filters import collision_filter

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

part = initialize_objects(shock_absorber_double_tab)
sequence = shock_absorber_double_tab_sequence

print(f"Sequence: {sequence}\n")

# Generate segments
segments_library = []
for pair in sequence:
    tab_x = part.tabs[pair[0]]
    tab_z = part.tabs[pair[1]]
    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment = Part(sequence=pair, tabs=segment_tabs)
    segments = create_segments(segment, segment_cfg, filter_cfg)
    segments_library.append(segments)
    print(f"Pair {pair}: {len(segments)} segments")

# Test first combination
print(f"\nTesting first combination:")
segments_combination = [lib[0] for lib in segments_library]

# Track tab counts
flat_sequence = []
for segment in segments_combination:
    for tab_local_id in segment.tabs:
        tab_id = segment.tabs[tab_local_id].tab_id
        flat_sequence.append(tab_id)

tab_count = {}
for tab_id in flat_sequence:
    tab_count[tab_id] = tab_count.get(tab_id, 0) + 1

print(f"Tab counts: {tab_count}")

# Try to merge tabs that appear multiple times
rejection_reason = None
for tab_id, count in tab_count.items():
    if count > 1:
        print(f"\nMerging tab '{tab_id}' (appears {count} times):")
        tabs = extract_tabs_from_segments(tab_id, segments_combination)

        # Iteratively merge tabs pairwise
        merged_points = tabs[0].points
        print(f"  Starting with {len(merged_points)} points")

        for i in range(1, len(tabs)):
            print(f"  Merging instance {i+1}...")
            class TempTab:
                def __init__(self, points):
                    self.points = points

            temp_merged = TempTab(merged_points)
            new_points = merge_points([temp_merged, tabs[i]])

            if new_points is None:
                rejection_reason = f"Merge failed for tab '{tab_id}' at instance {i+1}"
                print(f"    FAILED: Could not merge")
                print(f"    Current points: {list(merged_points.keys())}")
                print(f"    New tab points: {list(tabs[i].points.keys())}")
                break
            else:
                merged_points = new_points
                print(f"    Success: {len(merged_points)} points after merge")

if rejection_reason:
    print(f"\n>>> REJECTION: {rejection_reason}")
else:
    print(f"\n>>> All merges successful!")
    print(f"    Checking collision filter...")

    # Build the new_tabs_dict
    new_tabs_dict = {tab_id: tab for tab_id, tab in part.tabs.items()}
    for segment in segments_combination:
        for tab_local_id in segment.tabs:
            tab_id = segment.tabs[tab_local_id].tab_id
            new_tabs_dict[tab_id] = segment.tabs[tab_local_id]

    # Apply merged points
    for tab_id, count in tab_count.items():
        if count > 1:
            tabs = extract_tabs_from_segments(tab_id, segments_combination)
            merged_points = tabs[0].points
            for i in range(1, len(tabs)):
                class TempTab:
                    def __init__(self, points):
                        self.points = points
                temp_merged = TempTab(merged_points)
                new_points = merge_points([temp_merged, tabs[i]])
                merged_points = new_points
            new_tabs_dict[tab_id].points = merged_points

    if collision_filter(new_tabs_dict):
        print(f"    >>> REJECTION: Collision detected")
    else:
        print(f"    >>> PASSED: No collisions")

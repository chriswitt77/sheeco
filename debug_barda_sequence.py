"""
Debug script to test ALL pairs in the barda_example_one custom sequence.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import barda_example_one, barda_example_one_sequence
from src.hgen_sm import initialize_objects, Part
from src.hgen_sm.create_segments.choose_strategy import create_segments
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane, is_coplanar

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("TESTING ALL PAIRS IN barda_example_one_sequence")
print("="*80)

# Initialize part
part = initialize_objects(barda_example_one)

print(f"\nCustom sequence: {barda_example_one_sequence}")
print(f"\nNumber of tabs: {len(part.tabs)}")
for tab_id, tab in part.tabs.items():
    print(f"  Tab {tab_id}: A={tab.points['A']}, D={tab.points['D']}")

# Test each pair in the sequence
print("\n" + "="*80)
print("TESTING EACH PAIR")
print("="*80)

segments_library = []
all_passed = True

for i, pair in enumerate(barda_example_one_sequence):
    tab_x_id, tab_z_id = pair
    tab_x = part.tabs[tab_x_id]
    tab_z = part.tabs[tab_z_id]

    # Check if coplanar
    plane_x = calculate_plane(rect=tab_x)
    plane_z = calculate_plane(rect=tab_z)
    coplanar = is_coplanar(plane_x, plane_z)

    # Calculate distance
    tab_x_center = (tab_x.points['A'] + tab_x.points['C']) / 2
    tab_z_center = (tab_z.points['A'] + tab_z.points['C']) / 2
    distance = np.linalg.norm(tab_z_center - tab_x_center)

    print(f"\nPair {i+1}: [{tab_x_id}, {tab_z_id}]")
    print(f"  Coplanar: {coplanar}")
    print(f"  Distance: {distance:.2f} mm")
    print(f"  Tab {tab_x_id} normal: {plane_x.orientation}")
    print(f"  Tab {tab_z_id} normal: {plane_z.orientation}")

    # Create segment and test
    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment = Part(sequence=pair, tabs=segment_tabs)
    segments = create_segments(segment, segment_cfg, filter_cfg)

    print(f"  Segments found: {len(segments)}")

    if len(segments) == 0:
        print(f"  [X] NO SEGMENTS FOUND FOR THIS PAIR!")
        all_passed = False
    else:
        print(f"  [OK]")

    segments_library.append(segments)

# Calculate total combinations
print("\n" + "="*80)
print("COMBINATION ANALYSIS")
print("="*80)

total_combinations = 1
for i, segments in enumerate(segments_library):
    print(f"Pair {i+1}: {len(segments)} segment options")
    total_combinations *= len(segments)

print(f"\nTotal possible combinations: {total_combinations}")

if total_combinations == 0:
    print("\n[X] PROBLEM: At least one pair has zero segments!")
    print("This causes the entire itertools.product to be empty.")
    print("\nPairs with zero segments:")
    for i, (pair, segments) in enumerate(zip(barda_example_one_sequence, segments_library)):
        if len(segments) == 0:
            print(f"  Pair {i+1}: {pair}")
else:
    print(f"\n[OK] All pairs have segments. Expected {total_combinations} final solutions.")

"""
Debug script to understand why tabs 0 and 3 in barda_example_one don't connect.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import barda_example_one, same_plane
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
print("COMPARING same_plane (WORKS) vs barda_example_one (DOESN'T WORK)")
print("="*80)

# Test same_plane (this works)
print("\n--- TEST 1: same_plane ---")
part_same = initialize_objects(same_plane)
tab_0_same = part_same.tabs['0']
tab_1_same = part_same.tabs['1']

print(f"Tab 0: A={tab_0_same.points['A']}, B={tab_0_same.points['B']}, C={tab_0_same.points['C']}, D={tab_0_same.points['D']}")
print(f"Tab 1: A={tab_1_same.points['A']}, B={tab_1_same.points['B']}, C={tab_1_same.points['C']}, D={tab_1_same.points['D']}")

plane_0_same = calculate_plane(rect=tab_0_same)
plane_1_same = calculate_plane(rect=tab_1_same)
print(f"Plane 0: position={plane_0_same.position}, normal={plane_0_same.orientation}")
print(f"Plane 1: position={plane_1_same.position}, normal={plane_1_same.orientation}")
print(f"Coplanar: {is_coplanar(plane_0_same, plane_1_same)}")

segment_tabs_same = {'tab_x': tab_0_same, 'tab_z': tab_1_same}
segment_same = Part(sequence=['0', '1'], tabs=segment_tabs_same)
segments_same = create_segments(segment_same, segment_cfg, filter_cfg)
print(f"Number of segments found: {len(segments_same)}")

# Test barda_example_one (doesn't work)
print("\n--- TEST 2: barda_example_one (tabs 0 and 3) ---")
part_barda = initialize_objects(barda_example_one)
tab_0_barda = part_barda.tabs['0']
tab_3_barda = part_barda.tabs['3']

print(f"Tab 0: A={tab_0_barda.points['A']}, B={tab_0_barda.points['B']}, C={tab_0_barda.points['C']}, D={tab_0_barda.points['D']}")
print(f"Tab 3: A={tab_3_barda.points['A']}, B={tab_3_barda.points['B']}, C={tab_3_barda.points['C']}, D={tab_3_barda.points['D']}")

plane_0_barda = calculate_plane(rect=tab_0_barda)
plane_3_barda = calculate_plane(rect=tab_3_barda)
print(f"Plane 0: position={plane_0_barda.position}, normal={plane_0_barda.orientation}")
print(f"Plane 3: position={plane_3_barda.position}, normal={plane_3_barda.orientation}")
print(f"Coplanar: {is_coplanar(plane_0_barda, plane_3_barda)}")

# Calculate distance between tabs
tab0_center = (tab_0_barda.points['A'] + tab_0_barda.points['C']) / 2
tab3_center = (tab_3_barda.points['A'] + tab_3_barda.points['C']) / 2
distance = np.linalg.norm(tab3_center - tab0_center)
print(f"Distance between tab centers: {distance:.2f} mm")

# Calculate edge-to-edge distance (closest edges)
tab0_right = tab_0_barda.points['D'][0]  # x-coordinate of right edge
tab3_left = tab_3_barda.points['A'][0]   # x-coordinate of left edge
edge_distance = tab3_left - tab0_right
print(f"Distance between closest edges: {edge_distance:.2f} mm")

segment_tabs_barda = {'tab_x': tab_0_barda, 'tab_z': tab_3_barda}
segment_barda = Part(sequence=['0', '3'], tabs=segment_tabs_barda)
segments_barda = create_segments(segment_barda, segment_cfg, filter_cfg)
print(f"Number of segments found: {len(segments_barda)}")

if len(segments_barda) == 0:
    print("\n!!! NO SEGMENTS FOUND FOR TABS 0 AND 3 !!!")
    print("Now testing with debug output in zero_bends...")

    # Import zero_bends directly to add debug output
    from src.hgen_sm.create_segments.bend_strategies_zero_bend import zero_bends
    print("\nCalling zero_bends directly with debug...")
    segments_debug = zero_bends(segment_barda, filter_cfg)
    print(f"Result: {len(segments_debug)} segments")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)
print(f"Both pairs are coplanar: {is_coplanar(plane_0_same, plane_1_same) and is_coplanar(plane_0_barda, plane_3_barda)}")
print(f"same_plane works: {len(segments_same) > 0}")
print(f"barda tabs 0-3 works: {len(segments_barda) > 0}")
print("\nIf barda doesn't work but same_plane does, the issue is likely in zero_bends filtering logic.")

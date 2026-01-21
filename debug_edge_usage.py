import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import barda_example_one, barda_example_one_sequence

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part, initialize_objects, create_segments
from src.hgen_sm.part_assembly.merge_helpers import detect_edge
import numpy as np

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

part = initialize_objects(barda_example_one)
sequence = barda_example_one_sequence

print(f"Sequence: {sequence}")
print(f"\nThis means:")
print(f"  Tab 0 connects to: tabs 1, 2, 3 (appears 3 times)")
print(f"  Tab 3 connects to: tabs 0, 4, 5 (appears 3 times)")
print()

# Generate segments for the first pair involving tab 0
segments_library = []
for pair in sequence:
    tab_x = part.tabs[pair[0]]
    tab_z = part.tabs[pair[1]]
    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment = Part(sequence=pair, tabs=segment_tabs)
    segments = create_segments(segment, segment_cfg, filter_cfg)
    segments_library.append(segments)
    print(f"Pair {pair}: {len(segments)} segments")

# Look at first combination
print(f"\n\nAnalyzing first combination for tab 0:")
print(f"Tab 0 appears in pairs: ['0', '1'], ['0', '2'], ['0', '3']")
print()

# Get first segment for each pair involving tab 0
seg_01 = segments_library[0][0]  # First segment for pair ['0', '1']
seg_02 = segments_library[1][0]  # First segment for pair ['0', '2']
seg_03 = segments_library[2][0]  # First segment for pair ['0', '3']

# Extract tab 0 from each segment
tab_0_from_01 = seg_01.tabs['tab_x']
tab_0_from_02 = seg_02.tabs['tab_x']
tab_0_from_03 = seg_03.tabs['tab_x']

tabs_to_check = [
    (tab_0_from_01, "from pair ['0', '1']"),
    (tab_0_from_02, "from pair ['0', '2']"),
    (tab_0_from_03, "from pair ['0', '3']"),
]

# Get corners from first tab
corners = {}
for corner in ['A', 'B', 'C', 'D']:
    corners[corner] = tab_0_from_01.points[corner]

print("Corner positions:")
for corner, coord in corners.items():
    print(f"  {corner}: {coord}")
print()

for tab, desc in tabs_to_check:
    print(f"Tab 0 instance {desc}:")

    # Find non-corner points
    non_corner = [(name, coord) for name, coord in tab.points.items()
                  if name not in ['A', 'B', 'C', 'D']]

    print(f"  Non-corner points: {[name for name, _ in non_corner]}")

    # Determine which edges they use
    edges_used = set()
    for point_name, coord in non_corner:
        edge = detect_edge(coord, corners)
        if edge is not None:
            edges_used.add(edge)
            print(f"    {point_name} at {coord} -> edge {edge}")

    print(f"  Edges used by this instance: {edges_used}")
    print()

print("\nCONCLUSION:")
print("If multiple instances use the same edge, the merge will be rejected as")
print("not manufacturable (can't have two different bends on the same edge).")

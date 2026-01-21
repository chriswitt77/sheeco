import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import shock_absorber, shock_absorber_sequence, barda_example_one, barda_example_one_sequence

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part, initialize_objects, create_segments
from src.hgen_sm.part_assembly.merge_helpers import detect_edge

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("SHOCK_ABSORBER (WORKS - 20 solutions)")
print("="*80)
print(f"Sequence: {shock_absorber_sequence}")
print()

# Count appearances
from collections import Counter
flat = []
for pair in shock_absorber_sequence:
    flat.extend(pair)
counts = Counter(flat)
print(f"Tab appearance counts: {dict(counts)}")
print(f"Tab 1 appears {counts['1']} times (connects to tabs 2 and 0)")
print()

# Analyze tab 1's connections
part = initialize_objects(shock_absorber)

for i, pair in enumerate(shock_absorber_sequence):
    tab_x = part.tabs[pair[0]]
    tab_z = part.tabs[pair[1]]
    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment = Part(sequence=pair, tabs=segment_tabs)
    segments = create_segments(segment, segment_cfg, filter_cfg)

    print(f"Pair {pair}: {len(segments)} segments")

    # Check first segment to see which edges it uses
    if len(segments) > 0:
        seg = segments[0]

        # Get tab_x corners for edge detection
        corners = {}
        for corner in ['A', 'B', 'C', 'D']:
            corners[corner] = seg.tabs['tab_x'].points[corner]

        # Check tab_x bend points
        tab_x_from_seg = seg.tabs['tab_x']
        bend_points = [(name, coord) for name, coord in tab_x_from_seg.points.items()
                      if name.startswith('BP')]

        edges_used = set()
        for _, coord in bend_points:
            edge = detect_edge(coord, corners)
            if edge:
                edges_used.add(edge)

        print(f"  Tab {pair[0]} uses edges: {edges_used}")

print("\n" + "="*80)
print("BARDA_EXAMPLE_ONE (FAILS - 0 solutions)")
print("="*80)
print(f"Sequence: {barda_example_one_sequence}")
print()

flat2 = []
for pair in barda_example_one_sequence:
    flat2.extend(pair)
counts2 = Counter(flat2)
print(f"Tab appearance counts: {dict(counts2)}")
print(f"Tab 0 appears {counts2['0']} times (connects to tabs 1, 2, 3)")
print(f"Tab 3 appears {counts2['3']} times (connects to tabs 0, 4, 5)")
print()

part2 = initialize_objects(barda_example_one)

for i, pair in enumerate(barda_example_one_sequence):
    tab_x = part2.tabs[pair[0]]
    tab_z = part2.tabs[pair[1]]
    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment = Part(sequence=pair, tabs=segment_tabs)
    segments = create_segments(segment, segment_cfg, filter_cfg)

    print(f"Pair {pair}: {len(segments)} segments")

    if len(segments) > 0:
        seg = segments[0]

        corners = {}
        for corner in ['A', 'B', 'C', 'D']:
            corners[corner] = seg.tabs['tab_x'].points[corner]

        tab_x_from_seg = seg.tabs['tab_x']
        bend_points = [(name, coord) for name, coord in tab_x_from_seg.points.items()
                      if name.startswith('BP')]

        edges_used = set()
        for _, coord in bend_points:
            edge = detect_edge(coord, corners)
            if edge:
                edges_used.add(edge)

        print(f"  Tab {pair[0]} uses edges: {edges_used}")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)
print("The key difference might be in which edges are being used and whether")
print("the segment generation creates options that use different edges.")

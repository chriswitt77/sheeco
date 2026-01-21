import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import barda_example_one, barda_example_one_sequence

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part, initialize_objects, create_segments
from src.hgen_sm.part_assembly.merge_helpers import detect_edge

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

part = initialize_objects(barda_example_one)
sequence = barda_example_one_sequence

# Generate segments for pair ['0', '1']
tab_x = part.tabs['0']
tab_z = part.tabs['1']
segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)
segments = create_segments(segment, segment_cfg, filter_cfg)

print(f"Pair ['0', '1'] has {len(segments)} segment options")
print()

# Get corners from tab 0
corners = {}
for corner in ['A', 'B', 'C', 'D']:
    corners[corner] = part.tabs['0'].points[corner]

# Analyze which edges each segment option uses
for seg_idx, seg in enumerate(segments):
    tab_0 = seg.tabs['tab_x']

    # Find bend points (BP) only - these define the actual bend line
    bend_points = [(name, coord) for name, coord in tab_0.points.items()
                  if name.startswith('BP')]

    print(f"Segment option {seg_idx + 1}:")
    print(f"  Bend points: {[name for name, _ in bend_points]}")

    edges_with_bends = set()
    for point_name, coord in bend_points:
        edge = detect_edge(coord, corners)
        if edge is not None:
            edges_with_bends.add(edge)
            print(f"    {point_name} at {coord} -> edge {edge}")

    print(f"  Edges with bend points: {edges_with_bends}")
    print()

print("\nCONCLUSION:")
print("If all segment options use the same edges, then it's impossible to")
print("have 3 connections on different edges. The manufacturability filter")
print("is correctly rejecting these as invalid.")

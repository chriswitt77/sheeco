"""
Analyze why one_bend generates partial edge coverage solutions.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects, Part
from src.hgen_sm.create_segments.bend_strategies import one_bend
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane, calculate_plane_intersection

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

filter_cfg = cfg.get('filter')

print("="*80)
print("ANALYZING ONE_BEND BEND LINE PLACEMENT")
print("="*80)

# Initialize part
part = initialize_objects(transportschuh)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

# Calculate planes
plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)

print(f"\nTab 0: {tab_0.points['A']} to {tab_0.points['C']}")
print(f"  Normal: {plane_0.orientation}")
print(f"Tab 1: {tab_1.points['A']} to {tab_1.points['C']}")
print(f"  Normal: {plane_1.orientation}")

# Calculate plane intersection
bend_line = calculate_plane_intersection(plane_0, plane_1)
print(f"\nBend line (plane intersection):")
print(f"  Position: {bend_line['position']}")
print(f"  Orientation: {bend_line['orientation']}")

# Generate one_bend segments
segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)
segments = one_bend(segment, filter_cfg)

print(f"\n\nONE_BEND generated {len(segments)} segments")
print("="*80)

# Analyze each segment's bend point placement
for i, seg in enumerate(segments):
    print(f"\nSegment {i+1}:")

    tab_x = seg.tabs['tab_x']
    tab_z = seg.tabs['tab_z']

    # Get bend points
    bp_x = {k: v for k, v in tab_x.points.items() if 'BP' in k}
    bp_z = {k: v for k, v in tab_z.points.items() if 'BP' in k}

    if len(bp_x) >= 2 and len(bp_z) >= 2:
        # Get leftmost and rightmost bend points
        bp_x_coords = np.array(list(bp_x.values()))
        bp_z_coords = np.array(list(bp_z.values()))

        # For tab 0 (horizontal), check x span
        x_min_0 = bp_x_coords[:, 0].min()
        x_max_0 = bp_x_coords[:, 0].max()
        x_span_0 = x_max_0 - x_min_0

        # For tab 1 (vertical), check x span
        x_min_1 = bp_z_coords[:, 0].min()
        x_max_1 = bp_z_coords[:, 0].max()
        x_span_1 = x_max_1 - x_min_1

        print(f"  Tab 0 bend points: x=[{x_min_0:.1f}, {x_max_0:.1f}], span={x_span_0:.1f}")
        print(f"  Tab 1 bend points: x=[{x_min_1:.1f}, {x_max_1:.1f}], span={x_span_1:.1f}")

        # Check consistency
        if abs(x_min_0 - x_min_1) < 0.1 and abs(x_max_0 - x_max_1) < 0.1:
            print(f"  [OK] Bend points aligned")
        else:
            print(f"  [ERROR] Bend points misaligned!")

        # Check coverage
        tab_width = 160.0  # Known from geometry
        coverage_0 = (x_span_0 / tab_width) * 100
        coverage_1 = (x_span_1 / tab_width) * 100
        print(f"  Coverage: tab_0={coverage_0:.1f}%, tab_1={coverage_1:.1f}%")

        if coverage_0 < 95 or coverage_1 < 95:
            print(f"  [WARNING] Partial coverage - connection incomplete!")

            # Identify which corner combinations were used
            corners_x = ['A', 'B', 'C', 'D']
            corners_used_x = [c for c in corners_x if c in tab_x.points.keys()]
            print(f"  Tab 0 corners: {corners_used_x}")

            corners_z = ['A', 'B', 'C', 'D']
            corners_used_z = [c for c in corners_z if c in tab_z.points.keys()]
            print(f"  Tab 1 corners: {corners_used_z}")

print("\n" + "="*80)
print("ANALYSIS SUMMARY")
print("="*80)

full_coverage_count = 0
partial_coverage_count = 0

for i, seg in enumerate(segments):
    tab_x = seg.tabs['tab_x']
    bp_x = {k: v for k, v in tab_x.points.items() if 'BP' in k}

    if len(bp_x) >= 2:
        bp_x_coords = np.array(list(bp_x.values()))
        x_span = bp_x_coords[:, 0].max() - bp_x_coords[:, 0].min()
        coverage = (x_span / 160.0) * 100

        if coverage >= 95:
            full_coverage_count += 1
        else:
            partial_coverage_count += 1

print(f"\nFull coverage segments (>=95%): {full_coverage_count}")
print(f"Partial coverage segments (<95%): {partial_coverage_count}")

print(f"\n[ISSUE] one_bend is generating {partial_coverage_count} segments with partial")
print(f"edge coverage. These create incomplete connections where the bend line")
print(f"doesn't span the full width of the rectangles.")

print(f"\n[ROOT CAUSE] The one_bend algorithm likely tries different corner")
print(f"combinations, and some combinations produce bend lines that intersect")
print(f"only a portion of the edge, rather than the full edge.")

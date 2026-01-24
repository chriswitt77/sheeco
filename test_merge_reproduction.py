"""Test to reproduce the merge issue with zylinderhalter input."""

from src.hgen_sm import initialize_objects, determine_sequences, create_segments, part_assembly
from src.hgen_sm.data import Part
from config.user_input import zylinderhalter
import yaml
import json
import itertools

# Load config
with open('config/config.yaml', 'r') as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

print("=" * 80)
print("REPRODUCING MERGE ISSUE WITH ZYLINDERHALTER INPUT")
print("=" * 80)
print()

# Initialize part
part = initialize_objects(zylinderhalter)

# Generate sequences
variants = determine_sequences(part, cfg)

print(f"Generated {len(variants)} variants")
print()

# Process first variant to get parts
variant_part, sequences = variants[0]

print(f"Processing variant 1 with {len(sequences)} sequences")
print()

# Create segments for each sequence
for seq_idx, sequence in enumerate(sequences[:2]):  # Only first 2 sequences
    print("=" * 80)
    print(f"SEQUENCE {seq_idx + 1}: {sequence}")
    print("=" * 80)
    print()

    # Create segments for each pair in the sequence
    part_copy = variant_part.copy()
    segments_library = []

    for pair in sequence:
        tab_x_id, tab_z_id = pair[0], pair[1]
        tab_x = part_copy.tabs[tab_x_id]
        tab_z = part_copy.tabs[tab_z_id]

        # Create a segment object with tab_x and tab_z
        segment = Part(tabs={'tab_x': tab_x, 'tab_z': tab_z})

        # Generate all possible segment variations for this pair
        segment_variations = create_segments(segment, cfg['design_exploration'], cfg['filter'])
        segments_library.append(segment_variations)

        print(f"  Pair [{tab_x_id}, {tab_z_id}]: {len(segment_variations)} variations")

    print()

    # Try first combination of segments
    if not segments_library or not all(segments_library):
        print("  [SKIP] No valid segments generated")
        continue

    first_combination = [segs[0] for segs in segments_library]

    print(f"Testing first segment combination:")
    for i, seg in enumerate(first_combination):
        print(f"  Segment {i}: {list(seg.tabs.keys())}")
        for tab_id, tab in seg.tabs.items():
            if tab_id in ['0', '1', '2']:  # Original input tabs
                points_order = list(tab.points.keys())
                corners = [p for p in points_order if p in ['A', 'B', 'C', 'D']]
                flange_points = [p for p in points_order if p not in ['A', 'B', 'C', 'D']]
                print(f"    Tab {tab_id}:")
                print(f"      Point order: {' -> '.join(points_order)}")
                print(f"      Corners: {corners}")
                print(f"      Flanges: {flange_points}")
    print()

    # Assemble the part
    part_for_assembly = variant_part.copy()
    assembled_part = part_assembly(part_for_assembly, first_combination, cfg.get('filters', {}))

    if assembled_part is None:
        print("  [FILTERED OUT] Part assembly returned None")
        print()
        continue

    # Check tab 1 specifically
    if '1' in assembled_part.tabs:
        tab1 = assembled_part.tabs['1']
        print(f"ASSEMBLED TAB 1:")
        points_order = list(tab1.points.keys())
        print(f"  Point order: {' -> '.join(points_order)}")

        corners_in_order = [p for p in points_order if p in ['A', 'B', 'C', 'D']]
        print(f"  Corner sequence: {' -> '.join(corners_in_order)}")

        # Check if corners are grouped together
        first_corner_idx = points_order.index(corners_in_order[0])
        last_corner_idx = points_order.index(corners_in_order[-1])
        corners_span = last_corner_idx - first_corner_idx + 1

        if corners_span == len(corners_in_order):
            print(f"  [ERROR] All corners grouped together at positions {first_corner_idx}-{last_corner_idx}!")
            print(f"  Expected: Corners interspersed with flange points")
        else:
            print(f"  [OK] Corners distributed across perimeter")

        # Check perimeter distances
        print()
        print(f"  Perimeter analysis:")
        points_list = list(tab1.points.values())
        for i in range(min(len(points_list), 12)):  # First 12 transitions
            p1 = points_list[i]
            p2 = points_list[(i + 1) % len(points_list)]
            dist = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2 + (p2[2] - p1[2])**2)**0.5
            names = list(tab1.points.keys())
            print(f"    {names[i]:12s} -> {names[(i + 1) % len(names)]:12s}: dist = {dist:.2f}")

        print()

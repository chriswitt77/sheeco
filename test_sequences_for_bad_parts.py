"""Test different sequences to find which ones produce the bad parts."""

from src.hgen_sm import initialize_objects, Part
from src.hgen_sm.create_segments import create_segments
from src.hgen_sm.part_assembly import part_assembly
from config.user_input import zylinderhalter
import yaml
import itertools

# Load config
with open('config/config.yaml', 'r') as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

part = initialize_objects(zylinderhalter)

# Test different sequences that might produce parts 6 and 8
test_sequences = [
    [['0', '1'], ['0', '2']],  # Tab 0 connects to both 1 and 2
    [['0', '1'], ['1', '2']],  # Sequential: 0->1->2
    [['1', '2'], ['0', '1']],  # Sequential reversed order
]

for seq_num, sequence in enumerate(test_sequences, 1):
    print("\n" + "=" * 80)
    print(f"SEQUENCE {seq_num}: {sequence}")
    print("=" * 80)

    # Determine which tabs appear multiple times
    tab_counts = {}
    for pair in sequence:
        for tab_id in pair:
            tab_counts[tab_id] = tab_counts.get(tab_id, 0) + 1

    multi_connection_tabs = [tid for tid, count in tab_counts.items() if count > 1]
    print(f"Tabs with multiple connections: {multi_connection_tabs}")
    print()

    # Create segments
    segments_library = []
    for pair in sequence:
        tab_x = part.tabs[pair[0]]
        tab_z = part.tabs[pair[1]]
        segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
        segment = Part(sequence=pair, tabs=segment_tabs)
        segment_variations = create_segments(segment, cfg['design_exploration'], cfg['filter'])
        segments_library.append(segment_variations)

    if not all(segments_library):
        print("  No valid segments generated\n")
        continue

    # Test all combinations
    all_successful = []
    for combo_idx, combination in enumerate(itertools.product(*segments_library)):
        part_copy = part.copy()
        assembled_part = part_assembly(part_copy, combination, cfg['filter'])
        if assembled_part is not None:
            all_successful.append((combo_idx, assembled_part))

    if not all_successful:
        print("  No successful combinations\n")
        continue

    print(f"  {len(all_successful)} successful combinations found")
    print()

    # Check first 3 successful parts
    for idx, (combo_idx, assembled_part) in enumerate(all_successful[:3]):
        print(f"  --- Combination {combo_idx + 1} ---")

        # Check tabs with multiple connections
        for tab_id in multi_connection_tabs:
            if tab_id not in assembled_part.tabs:
                continue

            tab = assembled_part.tabs[tab_id]
            points_list = list(tab.points.keys())
            corners_in_order = [p for p in points_list if p in ['A', 'B', 'C', 'D']]

            print(f"    Tab {tab_id}:")
            print(f"      Total points: {len(points_list)}")
            print(f"      Point order: {' -> '.join(points_list)}")
            print(f"      Corner sequence: {' -> '.join(corners_in_order)}")

            if len(corners_in_order) == 4:
                first_corner_idx = points_list.index(corners_in_order[0])
                last_corner_idx = points_list.index(corners_in_order[-1])
                span = last_corner_idx - first_corner_idx + 1

                if span == 4:
                    print(f"      [ERROR] All 4 corners grouped at positions {first_corner_idx + 1}-{last_corner_idx + 1}")
                    print(f"              This is the Part 8 bug pattern!")
                else:
                    print(f"      [OK] Corners distributed (span {span} positions)")

            # Check for large gaps between consecutive points
            points_coords = [tab.points[name] for name in points_list]
            max_gap = 0
            max_gap_between = None
            for i in range(len(points_coords)):
                p1 = points_coords[i]
                p2 = points_coords[(i + 1) % len(points_coords)]
                dist = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2 + (p2[2] - p1[2])**2)**0.5
                if dist > max_gap:
                    max_gap = dist
                    max_gap_between = (points_list[i], points_list[(i + 1) % len(points_list)])

            if max_gap > 35:  # Suspiciously large gap
                print(f"      [WARNING] Large gap ({max_gap:.1f} units) between {max_gap_between[0]} -> {max_gap_between[1]}")
                print(f"                This suggests points are out of order")

        print()

print("\n" + "=" * 80)

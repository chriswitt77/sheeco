"""Test to identify why tab 1 gets incorrect point ordering when merged."""

from src.hgen_sm import initialize_objects, Part
from src.hgen_sm.create_segments import create_segments
from src.hgen_sm.part_assembly import part_assembly
from config.user_input import zylinderhalter
import yaml

# Load config
with open('config/config.yaml', 'r') as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

print("=" * 80)
print("TESTING TAB 1 MERGE WITH TWO CONNECTIONS")
print("=" * 80)
print()

# Initialize
part = initialize_objects(zylinderhalter)

# Test sequence where tab 1 is connected to both tab 0 and tab 2
sequence = [['0', '1'], ['1', '2']]

print(f"Sequence: {sequence}")
print(f"Tab 1 will have connections to tab 0 and tab 2")
print()

# Create segments for each pair
segments_library = []

for pair_idx, pair in enumerate(sequence):
    print("=" * 80)
    print(f"Creating segments for pair {pair_idx + 1}: {pair}")
    print("=" * 80)

    tab_x = part.tabs[pair[0]]
    tab_z = part.tabs[pair[1]]
    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment = Part(sequence=pair, tabs=segment_tabs)

    segment_variations = create_segments(segment, cfg['design_exploration'], cfg['filter'])

    print(f"Generated {len(segment_variations)} segment variations")

    if segment_variations:
        # Examine first variation
        seg = segment_variations[0]
        print(f"\nFirst variation has tabs: {list(seg.tabs.keys())}")

        for tab_id, tab in seg.tabs.items():
            if tab_id == '1':  # Focus on tab 1
                print(f"\nTab 1 in this segment:")
                points_list = list(tab.points.keys())
                print(f"  Point order: {' -> '.join(points_list)}")

                # Check if corners are grouped
                corners_in_order = [p for p in points_list if p in ['A', 'B', 'C', 'D']]
                print(f"  Corner positions:")
                for corner in corners_in_order:
                    idx = points_list.index(corner)
                    print(f"    {corner}: position {idx + 1}/{len(points_list)}")

                # Find flanges
                flanges = [p for p in points_list if p not in ['A', 'B', 'C', 'D']]
                if flanges:
                    print(f"  Flange points: {', '.join(flanges)}")
                    print(f"  First flange position: {points_list.index(flanges[0]) + 1}")

                # Check if all corners come before all flanges (WRONG pattern)
                if corners_in_order and flanges:
                    last_corner_idx = points_list.index(corners_in_order[-1])
                    first_flange_idx = points_list.index(flanges[0])

                    if first_flange_idx > last_corner_idx:
                        print(f"\n  [ERROR] All corners ({last_corner_idx + 1}) come before all flanges ({first_flange_idx + 1})")
                        print(f"  This is INCORRECT - flanges should be interspersed with corners")
                    else:
                        print(f"\n  [OK] Flanges are interspersed with corners")

    segments_library.append(segment_variations)
    print()

# Now try all combinations to find ones that pass assembly
if all(segments_library):
    import itertools

    print("=" * 80)
    print("TESTING ALL SEGMENT COMBINATIONS")
    print("=" * 80)
    print()

    total_combinations = len(segments_library[0]) * len(segments_library[1])
    print(f"Total combinations to test: {total_combinations}")
    print()

    successful_parts = []

    for combo_idx, combination in enumerate(itertools.product(*segments_library)):
        part_copy = part.copy()
        assembled_part = part_assembly(part_copy, combination, cfg['filter'])

        if assembled_part is not None:
            successful_parts.append((combo_idx, combination, assembled_part))

    print(f"Successful assemblies: {len(successful_parts)}/{total_combinations}")
    print()

    # Analyze first successful part
    if successful_parts:
        combo_idx, combination, assembled_part = successful_parts[0]

        print("=" * 80)
        print(f"ANALYZING FIRST SUCCESSFUL PART (combination {combo_idx + 1})")
        print("=" * 80)
        print()

        print("Tab 1 instances in segments BEFORE merge:")
        for i, seg in enumerate(combination):
            if '1' in seg.tabs:
                tab1 = seg.tabs['1']
                points_list = list(tab1.points.keys())
                corners = [p for p in points_list if p in ['A', 'B', 'C', 'D']]
                flanges = [p for p in points_list if p not in ['A', 'B', 'C', 'D']]
                print(f"  Segment {i} (pair {sequence[i]}):")
                print(f"    Points: {' -> '.join(points_list)}")
                print(f"    Corners at: {[points_list.index(c) + 1 for c in corners]}")
                print(f"    Flanges: {', '.join(flanges) if flanges else 'none'}")
        print()

        if '1' in assembled_part.tabs:
            tab1 = assembled_part.tabs['1']
            points_list = list(tab1.points.keys())

            print("FINAL TAB 1 AFTER MERGE:")
            print(f"  Total points: {len(points_list)}")
            print(f"  Point order: {' -> '.join(points_list)}")
            print()

            # Check corner positions
            corners_in_order = [p for p in points_list if p in ['A', 'B', 'C', 'D']]
            print(f"  Corner sequence: {' -> '.join(corners_in_order)}")

            # Check if all corners are grouped
            if len(corners_in_order) == 4:
                first_corner_idx = points_list.index(corners_in_order[0])
                last_corner_idx = points_list.index(corners_in_order[-1])
                span = last_corner_idx - first_corner_idx + 1

                if span == 4:
                    print(f"\n  [ERROR] All 4 corners grouped together at positions {first_corner_idx + 1}-{last_corner_idx + 1}")
                    print(f"  This matches the Part 8 bug pattern!")
                else:
                    print(f"\n  [OK] Corners distributed across perimeter (span {span} positions)")

        # Check a few more if available
        if len(successful_parts) > 1:
            print()
            print("=" * 80)
            print(f"CHECKING OTHER SUCCESSFUL PARTS ({len(successful_parts) - 1} more)")
            print("=" * 80)
            for idx in range(1, min(3, len(successful_parts))):
                combo_idx, combination, assembled_part = successful_parts[idx]
                if '1' in assembled_part.tabs:
                    tab1 = assembled_part.tabs['1']
                    points_list = list(tab1.points.keys())
                    corners_in_order = [p for p in points_list if p in ['A', 'B', 'C', 'D']]

                    if len(corners_in_order) == 4:
                        first_corner_idx = points_list.index(corners_in_order[0])
                        last_corner_idx = points_list.index(corners_in_order[-1])
                        span = last_corner_idx - first_corner_idx + 1

                        print(f"\n  Part {combo_idx + 1}: Corner span = {span}/4", end="")
                        if span == 4:
                            print(" [ERROR - all grouped]")
                        else:
                            print(" [OK]")
    else:
        print("No successful assemblies found!")

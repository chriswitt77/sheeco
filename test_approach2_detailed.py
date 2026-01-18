"""
Detailed analysis of Approach 2 to verify FP positioning
"""
import yaml
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm.data import Rectangle, Tab
from src.hgen_sm import Part, create_segments

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

# Create angled rectangles to trigger Approach 2
rectangles = [
    Rectangle(
        tab_id=0,
        A=[50.0, 0.0, 0.0],
        B=[50.0, 100.0, 0.0],
        C=[100.0, 100.0, 0.0]
    ),
    Rectangle(
        tab_id=1,
        A=[0.0, 50.0, 20.0],
        B=[0.0, 50.0, 70.0],
        C=[40.0, 80.0, 70.0]
    )
]

tabs_dict = {}
for i, rect in enumerate(rectangles):
    tab = Tab(tab_id=str(i), rectangle=rect)
    tabs_dict[str(i)] = tab

part = Part(tabs=tabs_dict)

# Create segment for the pair
segment_tabs = {'tab_x': part.tabs['0'], 'tab_z': part.tabs['1']}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)

# Generate segments
segments = create_segments(segment, segment_cfg, filter_cfg)

# Find two-bend segments
two_bend_segments = [s for s in segments if len(s.tabs) == 3]

print(f"\n{'='*70}")
print(f"APPROACH 2 DETAILED GEOMETRY VERIFICATION")
print(f"{'='*70}\n")

if not two_bend_segments:
    print("ERROR: No two-bend segments found!")
    exit(1)

# Analyze first segment
seg = two_bend_segments[0]

print(f"Analyzing first two-bend segment (should be Approach 2)\n")

for tab_id, tab in seg.tabs.items():
    print(f"\n{'-'*70}")
    print(f"{tab_id}:")
    print(f"  Perimeter: {list(tab.points.keys())}")

    # Extract points by type
    corners = {k: v for k, v in tab.points.items() if k in ['A', 'B', 'C', 'D']}
    fp_points = {k: v for k, v in tab.points.items() if k.startswith('FP')}
    bp_points = {k: v for k, v in tab.points.items() if k.startswith('BP')}

    # Identify approach based on corner count
    if tab_id in ['tab_x', 'tab_z']:
        corner_count = len(corners)
        print(f"\n  Corner count: {corner_count}")

        if corner_count == 3:
            print(f"  *** APPROACH 2 DETECTED (1 corner removed) ***")

            # Find which corner was removed
            expected_corners = {'A', 'B', 'C', 'D'}
            present_corners = set(corners.keys())
            removed_corner = expected_corners - present_corners
            print(f"  Removed corner: {removed_corner}")

        elif corner_count == 4:
            print(f"  *** APPROACH 1 DETECTED (all corners preserved) ***")

    # Verify FP to BP distances
    if fp_points and bp_points:
        print(f"\n  FP to BP distance verification (should be ~10mm):")

        for fp_id, fp_coord in fp_points.items():
            # Find corresponding BP (same L/R suffix)
            bp_id = fp_id.replace('FP', 'BP')
            if bp_id in bp_points:
                bp_coord = bp_points[bp_id]
                distance = np.linalg.norm(fp_coord - bp_coord)
                status = "OK" if abs(distance - 10.0) < 0.1 else "MISMATCH"
                print(f"    {fp_id} -> {bp_id}: {distance:.4f}mm [{status}]")
            else:
                print(f"    {fp_id}: No matching BP found")

    # Check perimeter validity
    print(f"\n  Perimeter validity check:")
    points_list = list(tab.points.items())

    # Check for duplicates
    has_duplicates = False
    for i in range(len(points_list)):
        curr_id, curr_pt = points_list[i]
        next_id, next_pt = points_list[(i+1) % len(points_list)]
        dist = np.linalg.norm(next_pt - curr_pt)
        if dist < 0.001:
            print(f"    WARNING: Duplicate {curr_id} -> {next_id}")
            has_duplicates = True

    if not has_duplicates:
        print(f"    OK: No duplicate consecutive points")

    # Show full point coordinates for tab_z
    if tab_id == 'tab_z' and len(corners) == 3:
        print(f"\n  Full point coordinates (Approach 2 tab_z):")
        for pt_id, pt_coord in tab.points.items():
            print(f"    {pt_id}: {pt_coord}")

print(f"\n{'='*70}")

# Verify point ordering expectation
print(f"\nVERIFYING USER SPECIFICATION:")
print(f"  'if B is the corner that is going to be deleted,")
print(f"   then the resulting tab should be [A FP01L BP01L BP01R FP01R C D]'")
print(f"\n  Checking tab_z structure...")

for tab_id, tab in seg.tabs.items():
    if tab_id == 'tab_z':
        corners = {k: v for k, v in tab.points.items() if k in ['A', 'B', 'C', 'D']}
        if len(corners) == 3:
            perimeter = list(tab.points.keys())

            # Find which corner was removed
            expected_corners = {'A', 'B', 'C', 'D'}
            present_corners = set(corners.keys())
            removed_corner = list(expected_corners - present_corners)[0]

            print(f"\n  Removed corner: {removed_corner}")
            print(f"  Perimeter: {perimeter}")

            # Check if bend points are where removed corner should be
            if removed_corner in ['A', 'B', 'C', 'D']:
                expected_order = ['A', 'B', 'C', 'D']
                removed_idx = expected_order.index(removed_corner)
                left_corner = expected_order[(removed_idx - 1) % 4]
                right_corner = expected_order[(removed_idx + 1) % 4]

                print(f"  Expected: Bend points between {left_corner} and {right_corner}")

                # Find positions in perimeter
                if left_corner in perimeter and right_corner in perimeter:
                    left_idx = perimeter.index(left_corner)
                    right_idx = perimeter.index(right_corner)

                    # Get points between left and right
                    if right_idx > left_idx:
                        between = perimeter[left_idx+1:right_idx]
                    else:
                        # Wrap around
                        between = perimeter[left_idx+1:] + perimeter[:right_idx]

                    print(f"  Actual: Points between {left_corner} and {right_corner}: {between}")

                    # Check if bend points are there
                    fp_count = sum(1 for p in between if p.startswith('FP'))
                    bp_count = sum(1 for p in between if p.startswith('BP'))

                    expected = "4 points (FP_L, BP_L, BP_R, FP_R)"
                    actual = f"{len(between)} points ({fp_count} FP, {bp_count} BP)"
                    status = "OK" if len(between) == 4 and fp_count == 2 and bp_count == 2 else "MISMATCH"

                    print(f"  Expected structure: {expected}")
                    print(f"  Actual structure: {actual} [{status}]")

print(f"\n{'='*70}\n")

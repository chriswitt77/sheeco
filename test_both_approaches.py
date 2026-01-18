"""
Enhanced test to verify both Approach 1 and Approach 2 of two_bend strategy
"""
import yaml
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm.data import Rectangle
from src.hgen_sm import Part, initialize_objects, determine_sequences, create_segments

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

def create_test_cases():
    """Create multiple test cases to trigger different approaches"""

    test_cases = []

    # Test Case 1: Perpendicular rectangles (should trigger Approach 1)
    # Rectangle in XY plane and rectangle in YZ plane (90 degrees)
    case1 = [
        Rectangle(
            tab_id=0,
            A=[50.0, 0.0, 0.0],
            B=[50.0, 100.0, 0.0],
            C=[100.0, 100.0, 0.0]
        ),
        Rectangle(
            tab_id=1,
            A=[0.0, 80.0, 40.0],
            B=[0.0, 40.0, 40.0],
            C=[0.0, 40.0, 80.0]
        )
    ]
    test_cases.append(("Perpendicular (90°)", case1))

    # Test Case 2: Angled rectangles (should trigger Approach 2)
    # Rectangle in XY plane and tilted rectangle (not perpendicular)
    case2 = [
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
    test_cases.append(("Angled (non-perpendicular)", case2))

    # Test Case 3: Parallel rectangles (should trigger Approach 2)
    # Both in XY plane but at different Z heights
    case3 = [
        Rectangle(
            tab_id=0,
            A=[0.0, 0.0, 0.0],
            B=[0.0, 100.0, 0.0],
            C=[50.0, 100.0, 0.0]
        ),
        Rectangle(
            tab_id=1,
            A=[0.0, 0.0, 50.0],
            B=[0.0, 100.0, 50.0],
            C=[50.0, 100.0, 50.0]
        )
    ]
    test_cases.append(("Parallel (same orientation)", case3))

    # Test Case 4: Slightly off perpendicular (should trigger Approach 2)
    # 75 degree angle instead of 90
    angle = np.radians(75)
    case4 = [
        Rectangle(
            tab_id=0,
            A=[50.0, 0.0, 0.0],
            B=[50.0, 100.0, 0.0],
            C=[100.0, 100.0, 0.0]
        ),
        Rectangle(
            tab_id=1,
            A=[0.0, 80.0, 40.0],
            B=[0.0, 40.0, 40.0],
            C=[30.0*np.cos(angle), 40.0, 40.0 + 30.0*np.sin(angle)]
        )
    ]
    test_cases.append(("75° angle (off-perpendicular)", case4))

    return test_cases


def analyze_segment(seg, case_name):
    """Analyze a segment's geometry"""

    print(f"\n{'='*70}")
    print(f"SEGMENT ANALYSIS: {case_name}")
    print(f"{'='*70}\n")
    print(f"Number of tabs: {len(seg.tabs)}")

    if len(seg.tabs) != 3:
        print("WARNING: Not a two-bend segment!")
        return None

    # Determine which approach was used
    # Approach 1: All corners preserved in source tabs
    # Approach 2: One corner removed in tab_z

    approach = None
    for tab_id, tab in seg.tabs.items():
        if tab_id in ['tab_x', 'tab_z']:
            corners = [k for k in tab.points.keys() if k in ['A', 'B', 'C', 'D']]
            fp_points = [k for k in tab.points.keys() if k.startswith('FP')]

            if len(corners) == 4:
                # Check if FP are at corner positions
                fp_coords = [tab.points[fp] for fp in fp_points]
                corner_coords = [tab.points[c] for c in corners]

                fp_at_corners = False
                for fp_coord in fp_coords:
                    for corner_coord in corner_coords:
                        if np.linalg.norm(fp_coord - corner_coord) < 0.001:
                            fp_at_corners = True
                            break
                    if fp_at_corners:
                        break

                if fp_at_corners:
                    approach = "Approach 1 (90-degree)"
            elif len(corners) == 3:
                approach = "Approach 2 (fallback)"

    if approach:
        print(f"*** DETECTED: {approach} ***\n")

    for tab_id, tab in seg.tabs.items():
        print(f"\n{'-'*70}")
        print(f"{tab_id}:")
        print(f"  Perimeter: {list(tab.points.keys())}")

        # Count point types
        corners = {k: v for k, v in tab.points.items() if k in ['A', 'B', 'C', 'D']}
        fp_points = {k: v for k, v in tab.points.items() if k.startswith('FP')}
        bp_points = {k: v for k, v in tab.points.items() if k.startswith('BP')}

        print(f"\n  Point counts:")
        print(f"    Corners: {len(corners)}")
        print(f"    Flange Points (FP): {len(fp_points)}")
        print(f"    Bend Points (BP): {len(bp_points)}")

        if corners:
            print(f"  Corners present: {list(corners.keys())}")

        # Check FP positions
        if fp_points and corners:
            print(f"\n  FP distance analysis:")
            for fp_id, fp_coord in fp_points.items():
                min_dist = min(np.linalg.norm(fp_coord - c_coord) for c_coord in corners.values())
                nearest_corner = min(corners.items(), key=lambda x: np.linalg.norm(fp_coord - x[1]))

                if min_dist < 0.01:
                    print(f"    {fp_id}: AT CORNER {nearest_corner[0]} (dist={min_dist:.4f}mm)")
                else:
                    print(f"    {fp_id}: {min_dist:.2f}mm from nearest corner {nearest_corner[0]}")

        # Check for duplicate points
        points_list = list(tab.points.items())
        duplicates = []
        for i in range(len(points_list)):
            curr_id, curr_pt = points_list[i]
            next_id, next_pt = points_list[(i+1) % len(points_list)]
            dist = np.linalg.norm(next_pt - curr_pt)
            if dist < 0.001:
                duplicates.append((curr_id, next_id))

        if duplicates:
            print(f"\n  WARNING: Duplicate consecutive points: {duplicates}")

    return approach


def main():
    test_cases = create_test_cases()

    results = {
        "Approach 1 (90-degree)": 0,
        "Approach 2 (fallback)": 0,
        "Unknown": 0
    }

    print(f"\n{'#'*70}")
    print(f"# COMPREHENSIVE TWO-BEND APPROACH TEST")
    print(f"{'#'*70}\n")
    print(f"Testing {len(test_cases)} different rectangle configurations\n")

    for case_name, rectangles in test_cases:
        print(f"\n{'='*70}")
        print(f"TEST CASE: {case_name}")
        print(f"{'='*70}")

        # Create part with these rectangles
        from src.hgen_sm.data import Tab
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

        print(f"\nResults: {len(two_bend_segments)} two-bend segments generated")

        if two_bend_segments:
            # Analyze first segment to determine approach
            approach = analyze_segment(two_bend_segments[0], case_name)
            if approach:
                results[approach] += 1
            else:
                results["Unknown"] += 1
        else:
            print("\nNo two-bend segments generated for this case")

    # Summary
    print(f"\n\n{'#'*70}")
    print(f"# SUMMARY")
    print(f"{'#'*70}\n")
    print(f"Approach distribution across test cases:")
    for approach, count in results.items():
        print(f"  {approach}: {count} cases")

    print(f"\n{'#'*70}\n")


if __name__ == "__main__":
    main()

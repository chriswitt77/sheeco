"""
Test if Approach 1 fix generates solutions for perpendicular tabs.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects, Part
from src.hgen_sm.create_segments import create_segments

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

print("="*80)
print("TESTING TWO_BENDS APPROACH 1 FIX")
print("="*80)

# Initialize part
part = initialize_objects(transportschuh)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

# Create segment
segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)

# Generate segments
segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print(f"\nConfiguration:")
print(f"  two_bend_antiparallel_threshold: {segment_cfg.get('two_bend_antiparallel_threshold')}")
print(f"  prioritize_perpendicular_bends: {segment_cfg.get('prioritize_perpendicular_bends')}")

segments = create_segments(segment, segment_cfg, filter_cfg)

# Count segments
one_bend_segments = [s for s in segments if len(s.tabs) == 2]
two_bend_segments = [s for s in segments if len(s.tabs) == 3]

print(f"\n{'='*80}")
print(f"RESULTS")
print(f"{'='*80}")
print(f"Total segments: {len(segments)}")
print(f"  One-bend: {len(one_bend_segments)}")
print(f"  Two-bend: {len(two_bend_segments)}")

# Analyze two-bend segments
print(f"\n{'='*80}")
print(f"TWO-BEND SEGMENT ANALYSIS")
print(f"{'='*80}")

approach1_count = 0
approach2_count = 0
unknown_count = 0

for i, seg in enumerate(two_bend_segments):
    print(f"\nSegment {i+1}:")
    if 'tab_y' in seg.tabs:
        tab_y = seg.tabs['tab_y']

        # Count corners
        corner_count = sum(1 for k in tab_y.points.keys() if k in ['A', 'B', 'C', 'D'])

        # Classify by intermediate tab structure
        if corner_count == 4:
            approach = "APPROACH 1 (Rectangular intermediate tab)"
            approach1_count += 1
        elif corner_count == 3:
            approach = "APPROACH 2 (Triangular intermediate tab)"
            approach2_count += 1
        elif corner_count == 0:
            # Check if points form a rectangular shape
            points = list(tab_y.points.values())
            if len(points) >= 4:
                # Check if 4 points are coplanar (approach 2 typically has 8 points but not rectangular)
                approach = "APPROACH 2 (Edge-based)"
                approach2_count += 1
            else:
                approach = "UNKNOWN"
                unknown_count += 1
        else:
            approach = "UNKNOWN"
            unknown_count += 1

        print(f"  {approach}")
        print(f"  Intermediate tab points: {len(tab_y.points)}")
        print(f"  Corners: {corner_count}")

print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")
print(f"Approach 1 (Perpendicular/Rectangular): {approach1_count}")
print(f"Approach 2 (Edge-based): {approach2_count}")
print(f"Unknown: {unknown_count}")

print(f"\n{'='*80}")
print(f"VALIDATION")
print(f"{'='*80}")

expected_behavior = """
BEFORE FIX:
  - Approach 1: 0 solutions (too strict direction check)
  - Approach 2: 1 solution

AFTER FIX:
  - Approach 1: >0 solutions (relaxed direction check)
  - Approach 2: 1 solution (unchanged)
  - Total two-bend: >1 solutions
"""

print(expected_behavior)

if approach1_count > 0:
    print("[SUCCESS] Approach 1 is now generating solutions!")
else:
    print("[FAILURE] Approach 1 still not generating solutions - check fix")

if len(two_bend_segments) > 1:
    print("[SUCCESS] Multiple two-bend solutions generated!")
else:
    print("[INFO] Only 1 two-bend solution - may need further tuning")

"""
Identify which approach generated the two-bend solution.
"""

import yaml
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects, Part
from src.hgen_sm.create_segments import create_segments

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

print("="*80)
print("IDENTIFYING TWO-BEND APPROACH")
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

segments = create_segments(segment, segment_cfg, filter_cfg)

two_bend_segments = [s for s in segments if len(s.tabs) == 3]
print(f"\nGenerated {len(two_bend_segments)} two-bend segment(s)")

if len(two_bend_segments) > 0:
    seg = two_bend_segments[0]
    print(f"\nSegment tabs: {list(seg.tabs.keys())}")

    # Check the intermediate tab
    if 'tab_y' in seg.tabs:
        tab_y = seg.tabs['tab_y']
        print(f"\nIntermediate tab (tab_y) points:")
        for k, v in tab_y.points.items():
            print(f"  {k}: {v}")

        # Count corners
        corner_count = sum(1 for k in tab_y.points.keys() if k in ['A', 'B', 'C', 'D'])
        print(f"\nCorner-like points: {corner_count}")

        if corner_count == 4:
            print(f"\n[APPROACH 1] Rectangular intermediate tab (4 corners)")
            print(f"This indicates perpendicular/90-degree approach")
        elif corner_count == 3:
            print(f"\n[APPROACH 2] Triangular intermediate tab (3 corners)")
            print(f"This indicates edge-based/corner approach")
        else:
            print(f"\n[UNKNOWN] Unusual corner count: {corner_count}")

print(f"\n{'='*80}")
print(f"DIAGNOSIS")
print(f"{'='*80}")
print(f"""
If this shows APPROACH 2:
  - Approach 1 (perpendicular) is not generating solutions
  - Need to fix Approach 1's direction check

If this shows APPROACH 1:
  - Approach 1 is working correctly
  - No fix needed
""")

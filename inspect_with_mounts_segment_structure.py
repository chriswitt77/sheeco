"""
Detailed inspection of with_mounts segment structure to understand
what's actually being generated.
"""

import yaml
from pathlib import Path
from config.user_input import with_mounts
from src.hgen_sm import initialize_objects, Part, create_segments

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("DETAILED SEGMENT STRUCTURE INSPECTION")
print("="*80)

# Initialize part
part = initialize_objects(with_mounts)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

# Generate segments
segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)
segments = create_segments(segment, segment_cfg, filter_cfg)

two_bend_segments = [s for s in segments if len(s.tabs) == 3]

print(f"\nTwo-bend segments: {len(two_bend_segments)}")

for i, seg in enumerate(two_bend_segments, 1):
    print(f"\n{'='*80}")
    print(f"SEGMENT {i}")
    print(f"{'='*80}")

    print(f"\nTabs in segment: {list(seg.tabs.keys())}")

    for tab_id, tab in seg.tabs.items():
        print(f"\n--- Tab '{tab_id}' ---")
        print(f"Total points: {len(tab.points)}")

        # Categorize points
        corners = [k for k in tab.points.keys() if k in ['A', 'B', 'C', 'D']]
        bp_points = [k for k in tab.points.keys() if 'BP' in k]
        fp_points = [k for k in tab.points.keys() if 'FP' in k]

        print(f"Corners: {len(corners)} - {corners}")
        print(f"BP points: {len(bp_points)} - {bp_points}")
        print(f"FP points: {len(fp_points)} - {fp_points}")

        # Show coordinates of key points
        if len(corners) > 0:
            print(f"\nCorner coordinates:")
            for corner in corners:
                p = tab.points[corner]
                print(f"  {corner}: [{p[0]:7.1f}, {p[1]:7.1f}, {p[2]:7.1f}]")

        if len(bp_points) > 0:
            print(f"\nBend point coordinates:")
            for bp in bp_points:
                p = tab.points[bp]
                print(f"  {bp}: [{p[0]:7.1f}, {p[1]:7.1f}, {p[2]:7.1f}]")

        if len(fp_points) > 0 and len(fp_points) <= 8:  # Don't print too many
            print(f"\nFlange point coordinates:")
            for fp in fp_points:
                p = tab.points[fp]
                print(f"  {fp}: [{p[0]:7.1f}, {p[1]:7.1f}, {p[2]:7.1f}]")

print(f"\n{'='*80}")
print(f"ANALYSIS")
print(f"{'='*80}")

print("""
Looking at the structure:
- If segment has 3 tabs and intermediate tab has BP=4, it's Approach 1
- If segment has 3 tabs and intermediate tab has BP=3, it's Approach 2
- The tab IDs give hints about the structure

Need to identify which tab is the intermediate connecting tab.
""")

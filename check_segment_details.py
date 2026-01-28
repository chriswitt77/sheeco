"""
Check the detailed structure of generated segments to determine approach type.
"""

import yaml
from pathlib import Path
from config.user_input import barda_example_one
from src.hgen_sm import initialize_objects, Part, create_segments

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("DETAILED SEGMENT STRUCTURE ANALYSIS")
print("="*80)

part = initialize_objects(barda_example_one)

# Just check one pair in detail
pair = ['0', '1']
print(f"\nAnalyzing pair: {pair}")

tab_x = part.tabs[pair[0]]
tab_z = part.tabs[pair[1]]

segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
segment_part = Part(sequence=pair, tabs=segment_tabs)
segments = create_segments(segment_part, segment_cfg, filter_cfg)

print(f"Generated {len(segments)} segments")

if len(segments) > 0:
    # Check first segment in detail
    segment = segments[0]

    print(f"\n{'='*80}")
    print(f"SEGMENT 1 DETAILS")
    print(f"{'='*80}")

    for tab_idx, (tab_local_id, tab) in enumerate(segment.tabs.items()):
        print(f"\nTab {tab_idx} (local_id='{tab_local_id}'):")
        print(f"  Number of points: {len(tab.points)}")
        print(f"  Point names: {list(tab.points.keys())}")

        # Check if it has corner points
        corners = [p for p in tab.points.keys() if p in ['A', 'B', 'C', 'D']]
        bend_points = [p for p in tab.points.keys() if 'BP' in p]
        flange_points = [p for p in tab.points.keys() if 'FP' in p]

        print(f"  Corners: {corners} ({len(corners)})")
        print(f"  Bend points: {bend_points} ({len(bend_points)})")
        print(f"  Flange points: {flange_points} ({len(flange_points)})")

        if tab_idx == 1:  # Intermediate tab
            if len(corners) == 4:
                print(f"  ==> RECTANGULAR intermediate (Approach 1)")
            elif len(corners) == 3:
                print(f"  ==> TRIANGULAR intermediate (Approach 2)")
            else:
                print(f"  ==> UNKNOWN geometry ({len(corners)} corners)")

print(f"\n{'='*80}")
print(f"CONCLUSION")
print(f"{'='*80}")

# Check the actual two_bends code to understand the logic
print(f"""
From the debug output above, we can determine:
- If intermediate tab has 4 corners (A,B,C,D) -> Approach 1 (rectangular)
- If intermediate tab has 3 corners -> Approach 2 (triangular)

The perpendicularity check should filter Approach 1 for these pairs because:
- Pair ['0','1']: Planes are antiparallel (180 degrees), not perpendicular (90 degrees)
- Pair ['0','2']: Planes are parallel (0 degrees), not perpendicular (90 degrees)

If Approach 1 segments are being generated, it means the perpendicularity filter is not working correctly.
If Approach 2 segments are being generated, then the system is working as designed - these pairs
require triangular intermediates because the planes are not perpendicular.
""")

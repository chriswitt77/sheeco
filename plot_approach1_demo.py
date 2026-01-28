"""
Demonstrate that Approach 1 segments ARE being generated.
Plot pair ['0','1'] segments with clear labels showing they are Approach 1.
"""

import yaml
from pathlib import Path
from config.user_input import barda_example_one
from src.hgen_sm import initialize_objects, Part, create_segments
from src.hgen_sm.plotting.plot_segments import plot_segments

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("PLOTTING APPROACH 1 SEGMENTS FOR PAIR ['0','1']")
print("="*80)

part = initialize_objects(barda_example_one)
pair = ['0', '1']

tab_x = part.tabs[pair[0]]
tab_z = part.tabs[pair[1]]
segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
segment_part = Part(sequence=pair, tabs=segment_tabs)
segments = create_segments(segment_part, segment_cfg, filter_cfg)

print(f"\nGenerated {len(segments)} segments for pair {pair}")

if len(segments) > 0:
    for seg_idx, segment in enumerate(segments):
        num_tabs = len(segment.tabs)
        tab_y = list(segment.tabs.values())[1]
        point_names = list(tab_y.points.keys())

        print(f"\nSegment {seg_idx + 1}:")
        print(f"  Number of tabs: {num_tabs}")
        print(f"  Intermediate tab points: {len(point_names)}")
        print(f"  Point names: {point_names}")

        # Check type
        has_corners = any(p in ['A', 'B', 'C', 'D'] for p in point_names)
        has_bp = any('BP' in p for p in point_names)

        if has_bp and not has_corners:
            print(f"  TYPE: Approach 1 (RECTANGULAR intermediate)")
            print(f"    - Has 4 BP points (bend points on both sides)")
            print(f"    - Has 4 FP points (flange points)")
            print(f"    - NO corner points A,B,C,D (defined by BP/FP instead)")
            print(f"    - This is the 90-degree perpendicular approach!")
        else:
            print(f"  TYPE: Approach 2 (TRIANGULAR intermediate)")

    print(f"\n{'='*80}")
    print(f"Opening plot window...")
    print(f"{'='*80}")
    print(f"\nLook for:")
    print(f"  - THREE tabs per segment (source, intermediate, target)")
    print(f"  - Intermediate tab with 8 points (4 BP + 4 FP)")
    print(f"  - Rectangular shape for intermediate tab")
    print(f"  - Green points = Bend Points (BP)")
    print(f"  - Blue points = Flange Points (FP)")
    print(f"\nPlotting with separate_windows=True so you can inspect each segment...")

    # Plot each segment separately
    plot_segments(segments, title=f"Pair {pair} - Approach 1 Segments", separate_windows=True)

    print(f"\nIf you see 3 plot windows, each showing 3 tabs with the middle tab")
    print(f"having 8 points (4 green BP + 4 blue FP), then Approach 1 is working!")
else:
    print(f"\nNo segments generated - check config!")

"""
Verify that Approach 1 segments are being generated for all problematic pairs.
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
print("VERIFY APPROACH 1 SEGMENT GENERATION")
print("="*80)

print(f"\nConfig:")
print(f"  max_intermediate_aspect_ratio: {segment_cfg.get('max_intermediate_aspect_ratio', 'NOT SET')}")
print(f"  prioritize_perpendicular_bends: {segment_cfg.get('prioritize_perpendicular_bends', 'NOT SET')}")

part = initialize_objects(barda_example_one)
test_pairs = [['0', '1'], ['0', '2'], ['3', '4'], ['3', '5']]

print(f"\nTesting pairs: {test_pairs}")
print(f"\n{'='*80}")

for pair in test_pairs:
    print(f"\nPair {pair}:")

    tab_x = part.tabs[pair[0]]
    tab_z = part.tabs[pair[1]]
    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment_part = Part(sequence=pair, tabs=segment_tabs)
    segments = create_segments(segment_part, segment_cfg, filter_cfg)

    print(f"  Total segments: {len(segments)}")

    if len(segments) > 0:
        approach1_count = 0
        approach2_count = 0

        for segment in segments:
            if len(segment.tabs) == 3:
                tab_y = list(segment.tabs.values())[1]
                point_names = list(tab_y.points.keys())

                has_corners = any(p in ['A', 'B', 'C', 'D'] for p in point_names)
                has_bp = any('BP' in p for p in point_names)
                has_fp = any('FP' in p for p in point_names)

                if has_bp and has_fp and not has_corners:
                    approach1_count += 1
                elif has_corners:
                    approach2_count += 1

        print(f"  Approach 1 (rectangular): {approach1_count}")
        print(f"  Approach 2 (triangular): {approach2_count}")

print(f"\n{'='*80}")
print(f"CONCLUSION")
print(f"{'='*80}")
print(f"""
If you're seeing Approach 1 segments in this output but not when you plot
with test_plot_segments.py, the issue might be:

1. The plot script is using a cached config or different input
2. The plot visualization might not be showing the intermediate tabs clearly
3. You might need to use separate_windows=True to see each segment individually

Try running: plot_segments(segments, title="Test", separate_windows=True)
to see each segment in its own window and inspect the intermediate tab geometry.
""")

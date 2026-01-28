"""
Test if the max_intermediate_aspect_ratio config is being read correctly
and if Approach 1 segments are now being generated.
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
print("TEST: ASPECT RATIO CONFIG")
print("="*80)

print(f"\nConfig values:")
print(f"  max_intermediate_aspect_ratio: {segment_cfg.get('max_intermediate_aspect_ratio', 'NOT SET')}")

part = initialize_objects(barda_example_one)
pair = ['0', '1']

print(f"\nGenerating segments for pair {pair}...")

tab_x = part.tabs[pair[0]]
tab_z = part.tabs[pair[1]]
segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
segment_part = Part(sequence=pair, tabs=segment_tabs)
segments = create_segments(segment_part, segment_cfg, filter_cfg)

print(f"Generated {len(segments)} segments")

if len(segments) > 0:
    print(f"\nAnalyzing segment types:")

    approach1_count = 0
    approach2_count = 0

    for seg_idx, segment in enumerate(segments):
        num_tabs = len(segment.tabs)

        if num_tabs == 3:
            # Check intermediate tab
            tab_y = list(segment.tabs.values())[1]
            point_names = list(tab_y.points.keys())

            # Approach 1: has BP and FP points, no corners A,B,C,D
            # Approach 2: has corner points
            has_corners = any(p in ['A', 'B', 'C', 'D'] for p in point_names)
            has_bp = any('BP' in p for p in point_names)
            has_fp = any('FP' in p for p in point_names)

            if has_bp and has_fp and not has_corners:
                approach1_count += 1
                print(f"  Segment {seg_idx + 1}: Approach 1 (rectangular, {len(point_names)} points)")
            elif has_corners:
                approach2_count += 1
                num_corners = len([p for p in point_names if p in ['A', 'B', 'C', 'D']])
                print(f"  Segment {seg_idx + 1}: Approach 2 (triangular, {num_corners} corners)")
            else:
                print(f"  Segment {seg_idx + 1}: Unknown type")
        elif num_tabs == 2:
            print(f"  Segment {seg_idx + 1}: One-bend")

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"  Approach 1 (rectangular): {approach1_count}")
    print(f"  Approach 2 (triangular): {approach2_count}")

    if approach1_count > 0:
        print(f"\n  ✓ SUCCESS! Approach 1 segments are being generated.")
    else:
        print(f"\n  ✗ PROBLEM! No Approach 1 segments generated despite config change.")
        print(f"     The aspect ratio may still be too high, or another filter is rejecting them.")
else:
    print(f"\n  ✗ No segments generated at all!")

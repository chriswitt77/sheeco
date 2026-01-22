"""
Test zero-bend implementation for coplanar tabs.
"""

import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import initialize_objects, Part, create_segments

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

# Test cases for coplanar tabs
test_cases = {
    'coplanar_xy_parallel': [
        {'pointA': [0, 0, 0], 'pointB': [50, 0, 0], 'pointC': [50, 50, 0]},
        {'pointA': [70, 0, 0], 'pointB': [120, 0, 0], 'pointC': [120, 50, 0]}
    ],
    'coplanar_xy_offset': [
        {'pointA': [0, 0, 0], 'pointB': [50, 0, 0], 'pointC': [50, 50, 0]},
        {'pointA': [30, 70, 0], 'pointB': [80, 70, 0], 'pointC': [80, 120, 0]}
    ],
    'coplanar_xz': [
        {'pointA': [0, 0, 0], 'pointB': [50, 0, 0], 'pointC': [50, 0, 50]},
        {'pointA': [70, 0, 0], 'pointB': [120, 0, 0], 'pointC': [120, 0, 50]}
    ],
    'coplanar_yz': [
        {'pointA': [0, 0, 0], 'pointB': [0, 50, 0], 'pointC': [0, 50, 50]},
        {'pointA': [0, 70, 0], 'pointB': [0, 120, 0], 'pointC': [0, 120, 50]}
    ],
    'non_coplanar': [
        {'pointA': [0, 0, 0], 'pointB': [50, 0, 0], 'pointC': [50, 50, 0]},
        {'pointA': [70, 0, 10], 'pointB': [120, 0, 10], 'pointC': [120, 50, 10]}
    ],
}

print("="*80)
print(" ZERO-BEND IMPLEMENTATION TEST")
print("="*80)
print()

for test_name, rectangles in test_cases.items():
    print(f"Testing: {test_name}")

    try:
        part = initialize_objects(rectangles)

        # Get tabs
        tab_0 = part.tabs['0']
        tab_1 = part.tabs['1']

        # Create segment
        segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
        segment = Part(sequence=['0', '1'], tabs=segment_tabs)

        # Generate segments
        segments = create_segments(segment, segment_cfg, filter_cfg)

        print(f"  Generated {len(segments)} segment(s)")

        # Analyze first segment if exists
        if len(segments) > 0:
            seg = segments[0]
            tab_x_mod = seg.tabs['tab_x']
            tab_z_mod = seg.tabs['tab_z']

            # Check for bend/flange points
            tab_x_points = list(tab_x_mod.points.keys())
            tab_z_points = list(tab_z_mod.points.keys())

            bp_x = [p for p in tab_x_points if p.startswith('BP')]
            fp_x = [p for p in tab_x_points if p.startswith('FP')]
            bp_z = [p for p in tab_z_points if p.startswith('BP')]
            fp_z = [p for p in tab_z_points if p.startswith('FP')]

            print(f"    Tab 0: {len(bp_x)} BPs, {len(fp_x)} FPs")
            print(f"    Tab 1: {len(bp_z)} BPs, {len(fp_z)} FPs")

            # Check if coplanar (should use zero-bend)
            if 'coplanar' in test_name and 'non' not in test_name:
                if len(bp_x) > 0:
                    print(f"    Status: ZERO-BEND (coplanar)")
                else:
                    print(f"    Status: ERROR - Expected zero-bend for coplanar tabs")
            else:
                if len(bp_x) > 0:
                    print(f"    Status: ONE/TWO-BEND (non-coplanar)")
                else:
                    print(f"    Status: ERROR - Expected bending for non-coplanar tabs")
        else:
            print(f"    Status: No segments generated")

    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()

print("="*80)
print("Test complete")
print("="*80)

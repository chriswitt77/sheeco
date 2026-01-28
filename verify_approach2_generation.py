"""
Verify what approach (1 or 2) is actually being used for the problematic pairs.
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
print("VERIFY SEGMENT GENERATION FOR PROBLEMATIC PAIRS")
print("="*80)

part = initialize_objects(barda_example_one)
debug_pairs = [['0', '1'], ['0', '2'], ['3', '4'], ['3', '5']]

for pair in debug_pairs:
    print(f"\n{'='*80}")
    print(f"PAIR: {pair}")
    print(f"{'='*80}")

    tab_x = part.tabs[pair[0]]
    tab_z = part.tabs[pair[1]]

    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment_part = Part(sequence=pair, tabs=segment_tabs)
    segments = create_segments(segment_part, segment_cfg, filter_cfg)

    print(f"\nGenerated {len(segments)} segments")

    if len(segments) > 0:
        # Check the structure to determine approach
        for seg_idx, segment in enumerate(segments):
            num_tabs = len(segment.tabs)
            print(f"\n  Segment {seg_idx + 1}:")
            print(f"    Number of tabs: {num_tabs}")

            if num_tabs == 3:
                # Two-bend segment - check if rectangular (Approach 1) or triangular (Approach 2)
                tab_y = list(segment.tabs.values())[1]  # Intermediate tab
                num_points = len(tab_y.points)
                print(f"    Intermediate tab points: {num_points}")

                if num_points == 4:
                    print(f"    Type: Two-bend Approach 1 (Rectangular intermediate)")
                elif num_points == 3:
                    print(f"    Type: Two-bend Approach 2 (Triangular intermediate)")
                else:
                    print(f"    Type: Two-bend (unknown, {num_points} points)")

            elif num_tabs == 2:
                print(f"    Type: One-bend")
            else:
                print(f"    Type: Unknown ({num_tabs} tabs)")

    else:
        print(f"  [NO SEGMENTS GENERATED]")
        print(f"  This pair failed all generation strategies!")

print(f"\n{'='*80}")
print(f"ANALYSIS")
print(f"{'='*80}")
print(f"""
Key findings:
- Approach 1 (rectangular intermediate) requires PERPENDICULAR PLANES (~90° angle between normals)
- Approach 2 (triangular intermediate) is the fallback for non-perpendicular cases

Looking at the geometry:
- Tabs 0, 2, 3 are in the z=55 plane (normal = [0, 0, 1])
- Tabs 1, 4 are in the z=0 plane (normal = [0, 0, -1])
- Tabs 5 is in the z=0 plane (normal = [0, 0, 1])

Therefore:
- Pairs ['0','1'] and ['3','4']: Antiparallel planes (180°) → NOT perpendicular
- Pairs ['0','2'] and ['3','5']: Parallel planes (0°) → NOT perpendicular

These pairs CANNOT use Approach 1 because the planes are not perpendicular!
They should use Approach 2 (triangular) instead.

The user's observation about "parallel edges" is correct, but:
- Having parallel EDGES is not the same as having perpendicular PLANES
- Approach 1 specifically needs perpendicular planes to create the rectangular intermediate tab
- When planes are parallel/antiparallel, only Approach 2 (triangular) can work
""")

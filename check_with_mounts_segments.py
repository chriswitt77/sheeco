"""
Check which segments are actually generated for with_mounts
and identify if they are Approach 1 or Approach 2.
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
print("ANALYZING which_mounts GENERATED SEGMENTS")
print("="*80)

# Initialize part
part = initialize_objects(with_mounts)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

# Generate segments
segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)
segments = create_segments(segment, segment_cfg, filter_cfg)

one_bend_segments = [s for s in segments if len(s.tabs) == 2]
two_bend_segments = [s for s in segments if len(s.tabs) == 3]

print(f"\nGenerated segments:")
print(f"  One-bend: {len(one_bend_segments)}")
print(f"  Two-bend: {len(two_bend_segments)}")

print(f"\n{'='*80}")
print(f"ANALYZING TWO-BEND SEGMENTS")
print(f"{'='*80}")

for i, seg in enumerate(two_bend_segments, 1):
    print(f"\nSegment {i}:")

    # Get intermediate tab (the one that's not '0' or '1')
    intermediate_tab = None
    intermediate_id = None
    for tab_id, tab in seg.tabs.items():
        if tab_id not in ['0', '1']:
            intermediate_tab = tab
            intermediate_id = tab_id
            break

    if intermediate_tab is None:
        print("  [WARNING] No intermediate tab found!")
        continue

    print(f"  Intermediate tab ID: {intermediate_id}")

    # Count point types in intermediate tab
    bp_count = len([k for k in intermediate_tab.points.keys() if 'BP' in k])
    fp_count = len([k for k in intermediate_tab.points.keys() if 'FP' in k])
    corner_count = len([k for k in intermediate_tab.points.keys() if k in ['A', 'B', 'C', 'D']])

    print(f"  Point counts: BP={bp_count}, FP={fp_count}, Corners={corner_count}")

    # Approach 1: rectangular tab with 4 BP, 8 FP
    # Approach 2: triangular tab with 3 BP, 6 FP
    if bp_count == 4:
        print(f"  Type: Approach 1 (rectangular intermediate tab)")
        # Show the bend points
        print(f"  Bend points:")
        for key in sorted(intermediate_tab.points.keys()):
            if 'BP' in key:
                bp = intermediate_tab.points[key]
                print(f"    {key}: [{bp[0]:7.1f}, {bp[1]:7.1f}, {bp[2]:7.1f}]")
    elif bp_count == 3:
        print(f"  Type: Approach 2 (triangular intermediate tab)")
    else:
        print(f"  Type: Unknown (BP count = {bp_count})")

print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")

approach1_count = len([s for s in two_bend_segments
                       for tid, tab in s.tabs.items()
                       if tid not in ['0', '1'] and len([k for k in tab.points.keys() if 'BP' in k]) == 4])
approach2_count = len([s for s in two_bend_segments
                       for tid, tab in s.tabs.items()
                       if tid not in ['0', '1'] and len([k for k in tab.points.keys() if 'BP' in k]) == 3])

print(f"\nApproach 1 segments: {approach1_count}")
print(f"Approach 2 segments: {approach2_count}")
print(f"Total two-bend: {len(two_bend_segments)}")

if approach1_count == 0:
    print(f"\n[PROBLEM] No Approach 1 segments generated!")
    print(f"The new validation checks have filtered out all Approach 1 solutions.")
else:
    print(f"\n[OK] Approach 1 is generating {approach1_count} segments")

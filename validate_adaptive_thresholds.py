"""
Validate that adaptive thresholds work correctly for both with_mounts and transportschuh.
"""

import yaml
from pathlib import Path
from config.user_input import with_mounts, transportschuh
from src.hgen_sm import initialize_objects, Part, create_segments

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("VALIDATING ADAPTIVE THRESHOLDS")
print("="*80)

print(f"\nConfiguration:")
print(f"  edge_coplanarity_tolerance (base): {filter_cfg.get('edge_coplanarity_tolerance')}")
print(f"  edge_coplanarity_relative_tolerance: {filter_cfg.get('edge_coplanarity_relative_tolerance')}")
print(f"  bend_point_range_margin: {segment_cfg.get('bend_point_range_margin')}")
print(f"  bend_point_max_absolute_overshoot: {segment_cfg.get('bend_point_max_absolute_overshoot')}")

# Test with_mounts
print(f"\n{'='*80}")
print(f"TEST 1: with_mounts (SHOULD GENERATE 5 APPROACH 1 SEGMENTS)")
print(f"{'='*80}")

part_wm = initialize_objects(with_mounts)
tab_0_wm = part_wm.tabs['0']
tab_1_wm = part_wm.tabs['1']

segment_tabs_wm = {'tab_x': tab_0_wm, 'tab_z': tab_1_wm}
segment_wm = Part(sequence=['0', '1'], tabs=segment_tabs_wm)
segments_wm = create_segments(segment_wm, segment_cfg, filter_cfg)

one_bend_wm = [s for s in segments_wm if len(s.tabs) == 2]
two_bend_wm = [s for s in segments_wm if len(s.tabs) == 3]

# Count Approach 1 segments (intermediate tab with 4 BP)
approach1_wm = 0
for seg in two_bend_wm:
    for tab_id, tab in seg.tabs.items():
        if tab_id not in ['0', '1']:
            bp_count = len([k for k in tab.points.keys() if 'BP' in k])
            if bp_count == 4:
                approach1_wm += 1
                break

print(f"\nResults:")
print(f"  One-bend segments: {len(one_bend_wm)}")
print(f"  Two-bend segments: {len(two_bend_wm)}")
print(f"  Approach 1 segments: {approach1_wm}")

if approach1_wm == 5:
    print(f"\n[SUCCESS] with_mounts generating 5 Approach 1 segments (restored from 3)")
elif approach1_wm == 3:
    print(f"\n[WARNING] Still only 3 Approach 1 segments (not improved)")
else:
    print(f"\n[INFO] Generated {approach1_wm} Approach 1 segments")

# Test transportschuh
print(f"\n{'='*80}")
print(f"TEST 2: transportschuh (SHOULD FILTER DEGENERATE, GENERATE ~3 SEGMENTS)")
print(f"{'='*80}")

part_ts = initialize_objects(transportschuh)
tab_0_ts = part_ts.tabs['0']
tab_1_ts = part_ts.tabs['1']

segment_tabs_ts = {'tab_x': tab_0_ts, 'tab_z': tab_1_ts}
segment_ts = Part(sequence=['0', '1'], tabs=segment_tabs_ts)
segments_ts = create_segments(segment_ts, segment_cfg, filter_cfg)

one_bend_ts = [s for s in segments_ts if len(s.tabs) == 2]
two_bend_ts = [s for s in segments_ts if len(s.tabs) == 3]

# Count Approach 1 segments
approach1_ts = 0
for seg in two_bend_ts:
    for tab_id, tab in seg.tabs.items():
        if tab_id not in ['0', '1']:
            bp_count = len([k for k in tab.points.keys() if 'BP' in k])
            if bp_count == 4:
                approach1_ts += 1
                break

print(f"\nResults:")
print(f"  One-bend segments: {len(one_bend_ts)}")
print(f"  Two-bend segments: {len(two_bend_ts)}")
print(f"  Approach 1 segments: {approach1_ts}")

if len(two_bend_ts) == 3 and approach1_ts == 2:
    print(f"\n[SUCCESS] transportschuh correctly filtering degenerate cases")
    print(f"  - 2 Approach 1 segments (valid perpendicular connections)")
    print(f"  - 1 Approach 2 segment (fallback)")
else:
    print(f"\n[INFO] transportschuh results may differ from expected")

# Check for degenerate geometry in transportschuh
print(f"\n{'='*80}")
print(f"CHECKING FOR DEGENERATE GEOMETRY IN TRANSPORTSCHUH")
print(f"{'='*80}")

degenerate_found = False
for seg in two_bend_ts:
    for tab_id, tab in seg.tabs.items():
        if tab_id not in ['0', '1']:
            bp_keys = [k for k in tab.points.keys() if 'BP' in k]
            for bp_key in bp_keys:
                bp = tab.points[bp_key]
                if bp[2] > 250:  # z > 250 indicates degenerate case
                    print(f"  [WARNING] Degenerate geometry: {bp_key} at z={bp[2]:.1f}")
                    degenerate_found = True

if not degenerate_found:
    print(f"  [OK] No degenerate geometry detected (no BP with z > 250)")

# Final summary
print(f"\n{'='*80}")
print(f"FINAL SUMMARY")
print(f"{'='*80}")

print(f"""
with_mounts:
  Expected: 5 Approach 1 segments
  Actual: {approach1_wm} Approach 1 segments
  Status: {'PASS' if approach1_wm == 5 else 'FAIL' if approach1_wm == 3 else 'PARTIAL'}

transportschuh:
  Expected: 2-3 total two-bend (no degenerate)
  Actual: {len(two_bend_ts)} total two-bend
  Degenerate found: {degenerate_found}
  Status: {'PASS' if not degenerate_found else 'FAIL'}

Overall: {'SUCCESS - Adaptive thresholds working!' if (approach1_wm == 5 and not degenerate_found) else 'Check results above'}
""")

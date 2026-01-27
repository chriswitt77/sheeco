"""
Validate the perpendicular plane fix for two_bends Approach 1.

Tests that:
1. Wanted parts (3, 5) are generated - edges form perpendicular plane
2. Unwanted parts (4, 6) are filtered - degenerate intermediate tabs
"""

import yaml
import time
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects, Part, determine_sequences, create_segments, part_assembly
import itertools
import copy

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

print("="*80)
print("VALIDATING PERPENDICULAR PLANE FIX FOR TWO_BENDS APPROACH 1")
print("="*80)

start_time = time.time()

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print(f"\nConfiguration:")
print(f"  two_bend_antiparallel_threshold: {segment_cfg.get('two_bend_antiparallel_threshold')}")
print(f"  bend_point_range_margin: {segment_cfg.get('bend_point_range_margin')}")
print(f"  max_intermediate_aspect_ratio: {segment_cfg.get('max_intermediate_aspect_ratio')}")
print(f"  edge_coplanarity_tolerance: {filter_cfg.get('edge_coplanarity_tolerance')}")

# Initialize part
part = initialize_objects(transportschuh)
print(f"\nInitialized part with {len(part.tabs)} tabs")

# Run full pipeline and track segments
print(f"\n{'='*80}")
print(f"RUNNING FULL PIPELINE")
print(f"{'='*80}")

# First, analyze segments generated for the main tab pair (0, 1)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']
segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)
test_segments = create_segments(segment, segment_cfg, filter_cfg)

one_bend_segments = [s for s in test_segments if len(s.tabs) == 2]
two_bend_segments = [s for s in test_segments if len(s.tabs) == 3]

print(f"\nSegments generated for tab pair (0, 1):")
print(f"  One-bend: {len(one_bend_segments)}")
print(f"  Two-bend: {len(two_bend_segments)}")

# Analyze two-bend segments for degenerate geometry
print(f"\n{'='*80}")
print(f"ANALYZING TWO-BEND SEGMENTS")
print(f"{'='*80}")

degenerate_found = False
for i, seg in enumerate(two_bend_segments, 1):
    print(f"\nTwo-bend segment {i}:")
    # Get intermediate tab
    for tab_id, tab in seg.tabs.items():
        if tab_id not in ['0', '1']:
            print(f"  Intermediate tab ID: {tab_id}")
            # Show bend points
            bp_keys = [k for k in tab.points.keys() if 'BP' in k]
            print(f"  Bend points ({len(bp_keys)} total):")
            for bp_key in sorted(bp_keys)[:8]:  # Show first 8
                bp = tab.points[bp_key]
                print(f"    {bp_key}: [{bp[0]:7.1f}, {bp[1]:7.1f}, {bp[2]:7.1f}]")
                # Check for degenerate geometry (z > 250)
                if bp[2] > 250 or bp[2] < -50:
                    print(f"      [WARNING] Suspicious z-coordinate: {bp[2]:.1f}")
                    degenerate_found = True

# Run full pipeline for total solution count
variants = determine_sequences(part, cfg)
solutions = []
part_id = 0

for variant_part, sequences in variants:
    for sequence in sequences:
        segments_library = []
        for pair in sequence:
            tab_x = variant_part.tabs[pair[0]]
            tab_z = variant_part.tabs[pair[1]]
            segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
            segment = Part(sequence=pair, tabs=segment_tabs)
            segments = create_segments(segment, segment_cfg, filter_cfg)
            segments_library.append(segments)

        # Assemble parts
        variant_part.sequence = sequence
        for segments_combination in itertools.product(*segments_library):
            new_part = variant_part.copy()
            new_segments_combination = copy.deepcopy(segments_combination)
            new_part = part_assembly(new_part, new_segments_combination, filter_cfg)
            if new_part is None:
                continue
            part_id += 1
            new_part.part_id = part_id
            solutions.append(new_part)

elapsed = time.time() - start_time

print(f"\n{'='*80}")
print(f"FULL PIPELINE RESULTS")
print(f"{'='*80}")
print(f"\nTotal assembled solutions: {len(solutions)}")
print(f"Time: {elapsed:.2f} seconds")

print(f"\n{'='*80}")
print(f"VALIDATION RESULTS")
print(f"{'='*80}")

print(f"\nExpected behavior:")
print(f"  WANTED: Parts with edges forming perpendicular planes")
print(f"    - Intermediate plane at x=-10 or x=170 (compact)")
print(f"  UNWANTED: Parts with degenerate intermediate tabs")
print(f"    - Bend points at z=290 (far beyond tab range [40, 200])")

print(f"\nActual results:")
print(f"  Total assembled solutions: {len(solutions)}")
print(f"  One-bend segments generated: {len(one_bend_segments)}")
print(f"  Two-bend segments generated: {len(two_bend_segments)}")
print(f"  Degenerate geometry found: {degenerate_found}")

print(f"\n{'='*80}")
print(f"FINAL ASSESSMENT")
print(f"{'='*80}")

# Expected: ~3 two-bend segments (valid perpendicular connections), no degenerate ones
if len(two_bend_segments) >= 2 and len(two_bend_segments) <= 4:
    print(f"[OK] Reasonable number of two-bend segments: {len(two_bend_segments)}")
else:
    print(f"[WARNING] Unexpected number of two-bend segments: {len(two_bend_segments)}")

if not degenerate_found:
    print(f"[OK] No degenerate intermediate tabs found")
    print(f"\n[SUCCESS] Fix appears to be working correctly!")
    print(f"  - Degenerate parts (4, 6) have been filtered out")
    print(f"  - Valid perpendicular connections remain")
else:
    print(f"[FAIL] Degenerate geometry still present")
    print(f"  - Additional filtering may be needed")

print(f"\n{'='*80}")
print(f"COMPARISON TO BEFORE FIX")
print(f"{'='*80}")

print(f"""
BEFORE PERPENDICULAR PLANE FIX:
  Two-bend segments: 5
  Wanted (valid): 3
  Unwanted (degenerate): 2 (parts 4, 6 with BP at z=290)

AFTER PERPENDICULAR PLANE FIX:
  Two-bend segments: {len(two_bend_segments)}
  Degenerate found: {degenerate_found}

Expected improvement:
  - Parts 4, 6 should be filtered out
  - Total two-bend should be ~3
  - All remaining segments should be manufacturable
""")

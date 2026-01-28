"""
Comprehensive step-by-step debugging of barda_example_one pipeline.
Traces segment generation and assembly to find where solutions are filtered.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import barda_example_one, barda_example_one_sequence
from src.hgen_sm import initialize_objects, Part, determine_sequences, create_segments, part_assembly
import itertools
import copy

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("DEBUGGING BARDA_EXAMPLE_ONE - STEP BY STEP ANALYSIS")
print("="*80)

# Initialize part
print("\nSTEP 1: INITIALIZATION")
print("-"*80)
part = initialize_objects(barda_example_one)
print(f"Initialized part with {len(part.tabs)} tabs")

for tab_id, tab in part.tabs.items():
    corners = {k: tab.points[k] for k in ['A', 'B', 'C', 'D']}
    print(f"\nTab {tab_id}:")
    for corner, point in corners.items():
        print(f"  {corner}: [{point[0]:6.1f}, {point[1]:6.1f}, {point[2]:6.1f}]")

# Custom sequence
print(f"\nCustom sequence: {barda_example_one_sequence}")

# STEP 2: Determine sequences
print("\n" + "="*80)
print("STEP 2: DETERMINE SEQUENCES")
print("-"*80)

# Set custom sequence mode
original_use_custom = cfg['topologies']['use_custom_sequences']
cfg['topologies']['use_custom_sequences'] = True

# Need to check if custom sequences are properly loaded
# Let's manually set it for testing
variants = determine_sequences(part, cfg)

print(f"Number of variants: {len(list(variants))}")

# Re-run to consume generator
variants = determine_sequences(part, cfg)
for i, (variant_part, sequences) in enumerate(variants):
    print(f"\nVariant {i}:")
    print(f"  Number of sequences: {len(sequences)}")
    for j, sequence in enumerate(sequences):
        print(f"  Sequence {j}: {sequence}")

# STEP 3: Generate segments for each pair
print("\n" + "="*80)
print("STEP 3: SEGMENT GENERATION FOR EACH PAIR")
print("-"*80)

# Use the custom sequence directly
sequence = barda_example_one_sequence

segment_library_map = {}

for pair_idx, pair in enumerate(sequence):
    print(f"\n{'='*80}")
    print(f"PAIR {pair_idx}: {pair[0]} -> {pair[1]}")
    print(f"{'='*80}")

    tab_x = part.tabs[pair[0]]
    tab_z = part.tabs[pair[1]]

    # Show tab info
    print(f"\nTab {pair[0]} corners:")
    for k in ['A', 'B', 'C', 'D']:
        p = tab_x.points[k]
        print(f"  {k}: [{p[0]:6.1f}, {p[1]:6.1f}, {p[2]:6.1f}]")

    print(f"\nTab {pair[1]} corners:")
    for k in ['A', 'B', 'C', 'D']:
        p = tab_z.points[k]
        print(f"  {k}: [{p[0]:6.1f}, {p[1]:6.1f}, {p[2]:6.1f}]")

    # Create segment
    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment = Part(sequence=pair, tabs=segment_tabs)

    # Generate segments
    print(f"\nGenerating segments...")
    segments = create_segments(segment, segment_cfg, filter_cfg)

    # Analyze generated segments
    one_bend = [s for s in segments if len(s.tabs) == 2]
    two_bend = [s for s in segments if len(s.tabs) == 3]

    print(f"\nResults:")
    print(f"  One-bend segments: {len(one_bend)}")
    print(f"  Two-bend segments: {len(two_bend)}")
    print(f"  Total segments: {len(segments)}")

    if len(segments) == 0:
        print(f"\n  [WARNING] NO SEGMENTS GENERATED FOR THIS PAIR!")
        print(f"  This will prevent assembly from completing.")

    # Store segments for this pair
    segment_library_map[f"{pair[0]}-{pair[1]}"] = segments

    # Show segment details
    if len(segments) > 0:
        print(f"\nSegment details:")
        for seg_idx, seg in enumerate(segments):
            seg_type = "one-bend" if len(seg.tabs) == 2 else "two-bend"
            print(f"  Segment {seg_idx}: {seg_type}, {len(seg.tabs)} tabs")

# STEP 4: Assembly
print("\n" + "="*80)
print("STEP 4: PART ASSEMBLY")
print("-"*80)

print(f"\nAttempting to assemble parts...")
print(f"Sequence pairs: {sequence}")

# Check if any pair has zero segments
zero_segment_pairs = []
for pair in sequence:
    pair_key = f"{pair[0]}-{pair[1]}"
    if len(segment_library_map[pair_key]) == 0:
        zero_segment_pairs.append(pair_key)

if zero_segment_pairs:
    print(f"\n[CRITICAL] The following pairs have NO segments:")
    for pair_key in zero_segment_pairs:
        print(f"  - {pair_key}")
    print(f"\nThis will result in ZERO solutions in assembly!")
    print(f"The itertools.product will have an empty list, yielding no combinations.")

# Try assembly
print(f"\nAssembling...")

segments_library = []
for pair in sequence:
    tab_x = part.tabs[pair[0]]
    tab_z = part.tabs[pair[1]]
    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment = Part(sequence=pair, tabs=segment_tabs)
    segments = create_segments(segment, segment_cfg, filter_cfg)
    segments_library.append(segments)
    print(f"  Pair {pair}: {len(segments)} segments")

# Calculate total possible combinations
total_combinations = 1
for segs in segments_library:
    total_combinations *= len(segs)

print(f"\nTotal possible combinations: {total_combinations}")

if total_combinations == 0:
    print(f"\n[PROBLEM] Cannot create any combinations - at least one pair has 0 segments!")
else:
    print(f"\nGenerating combinations...")

    solutions = []
    part_id = 0

    part.sequence = sequence
    for segments_combination in itertools.product(*segments_library):
        new_part = part.copy()
        new_segments_combination = copy.deepcopy(segments_combination)
        new_part = part_assembly(new_part, new_segments_combination, filter_cfg)

        if new_part is None:
            print(f"  Combination {part_id + 1}: FILTERED by part_assembly")
        else:
            part_id += 1
            new_part.part_id = part_id
            solutions.append(new_part)
            print(f"  Combination {part_id}: ACCEPTED")

    print(f"\nFinal solutions: {len(solutions)}")

# SUMMARY
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

print(f"\nSegment generation results:")
for pair in sequence:
    pair_key = f"{pair[0]}-{pair[1]}"
    seg_count = len(segment_library_map[pair_key])
    status = "OK" if seg_count > 0 else "FAIL - NO SEGMENTS"
    print(f"  {pair_key}: {seg_count} segments - {status}")

if zero_segment_pairs:
    print(f"\n[ROOT CAUSE] No solutions because these pairs generated 0 segments:")
    for pair_key in zero_segment_pairs:
        print(f"  - {pair_key}")
    print(f"\nNeed to investigate WHY these pairs don't generate segments.")
    print(f"Possible reasons:")
    print(f"  1. Tabs are coplanar and not suitable for bending")
    print(f"  2. Tabs are too far apart")
    print(f"  3. Tab orientations don't allow perpendicular or edge connections")
    print(f"  4. Geometry fails validation checks")
else:
    if total_combinations > 0:
        print(f"\nSegments were generated for all pairs.")
        print(f"Problem is in part_assembly filtering.")
    else:
        print(f"\n[ERROR] Unexpected state - check logic above")

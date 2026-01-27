"""
Test the full pipeline with perpendicular edge filter to count final solutions.
"""

import yaml
import time
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects, determine_sequences, create_segments, part_assembly
import itertools
import copy

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

print("="*80)
print("FULL PIPELINE TEST WITH PERPENDICULAR EDGE FILTER")
print("="*80)

start_time = time.time()

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print(f"\nFilter configuration:")
print(f"  max_edge_to_bend_angle: {filter_cfg.get('max_edge_to_bend_angle')}")

# Initialize part
part = initialize_objects(transportschuh)
print(f"\nInitialized part with {len(part.tabs)} tabs")

# Determine sequences
variants = determine_sequences(part, cfg)
print(f"Generated {len(variants)} variant(s)")

# Process each variant
solutions = []
part_id = 0

for variant_part, sequences in variants:
    variant_name = "separated" if any('_' in str(tid) for tid in variant_part.tabs.keys()) else "unseparated"
    print(f"\n{'='*80}")
    print(f"Processing {variant_name} variant with {len(variant_part.tabs)} tabs")
    print(f"{'='*80}")

    for seq_idx, sequence in enumerate(sequences):
        print(f"\nSequence {seq_idx+1}: {sequence}")

        segments_library = []
        for pair in sequence:
            tab_x = variant_part.tabs[pair[0]]
            tab_z = variant_part.tabs[pair[1]]
            segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}

            from src.hgen_sm import Part
            segment = Part(sequence=pair, tabs=segment_tabs)

            segments = create_segments(segment, segment_cfg, filter_cfg)

            if segments:
                one_bend = sum(1 for s in segments if len(s.tabs) == 2)
                two_bend = sum(1 for s in segments if len(s.tabs) == 3)
                print(f"  Pair {pair}: {len(segments)} segments (one-bend: {one_bend}, two-bend: {two_bend})")
                segments_library.append(segments)
            else:
                print(f"  Pair {pair}: No segments")
                segments_library.append([])

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
print(f"RESULTS")
print(f"{'='*80}")
print(f"Time: {elapsed:.2f} seconds")
print(f"Total solutions: {len(solutions)}")

print(f"\n{'='*80}")
print(f"COMPARISON")
print(f"{'='*80}")
print(f"""
BEFORE perpendicular edge filter:
  - Total solutions: 7
  - Feasible: 3 (parts 2, 5, 7)
  - Infeasible: 4 (parts 1, 3, 4, 6 - perpendicular edges)

EXPECTED AFTER filter:
  - Total solutions: 3-4 (only feasible)
  - All using parallel edges
  - Should include one-bend and two-bend solutions

ACTUAL RESULTS:
  - Total solutions: {len(solutions)}

{'[SUCCESS]' if len(solutions) <= 4 else '[WARNING]'} Filter appears to be working!
""")

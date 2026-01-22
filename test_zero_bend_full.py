"""
Test complete solution generation with zero-bend segments.
"""

import yaml
from pathlib import Path
import copy
import itertools

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part, initialize_objects, determine_sequences, create_segments, part_assembly

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

# Test case: three coplanar tabs in sequence
coplanar_three_tabs = [
    {'pointA': [0, 0, 0], 'pointB': [50, 0, 0], 'pointC': [50, 50, 0]},
    {'pointA': [70, 0, 0], 'pointB': [120, 0, 0], 'pointC': [120, 50, 0]},
    {'pointA': [140, 0, 0], 'pointB': [190, 0, 0], 'pointC': [190, 50, 0]}
]

print("="*80)
print(" ZERO-BEND COMPLETE SOLUTION GENERATION TEST")
print("="*80)
print()

print("Test case: 3 coplanar tabs in XY plane")
print()

try:
    part = initialize_objects(coplanar_three_tabs)
    print(f"Initialized with {len(part.tabs)} tabs")

    # Generate sequence (should be simple: 0-1, 1-2)
    variants = determine_sequences(part, cfg)
    print(f"Generated {len(variants)} sequence variant(s)")

    solutions = []
    part_id = 0

    for variant_part, sequences in variants:
        print(f"\nProcessing variant with {len(sequences)} sequence(s)")

        for sequence in sequences:
            print(f"  Sequence: {sequence}")

            segments_library = []

            for pair in sequence:
                tab_x = variant_part.tabs[pair[0]]
                tab_z = variant_part.tabs[pair[1]]
                segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
                segment = Part(sequence=pair, tabs=segment_tabs)
                segments = create_segments(segment, segment_cfg, filter_cfg)
                segments_library.append(segments)
                print(f"    Pair {pair}: {len(segments)} zero-bend segments")

            # Assemble parts
            variant_part.sequence = sequence
            combo_count = 0
            for segments_combination in itertools.product(*segments_library):
                combo_count += 1
                new_part = variant_part.copy()
                new_segments_combination = copy.deepcopy(segments_combination)
                new_part = part_assembly(new_part, new_segments_combination, filter_cfg)

                if new_part is not None:
                    part_id += 1
                    new_part.part_id = part_id
                    solutions.append(new_part)

            print(f"    Checked {combo_count} combinations")

    print(f"\n{'='*80}")
    print(f"Found {len(solutions)} valid solutions")
    print(f"{'='*80}")

    if len(solutions) > 0:
        print("\nSample solution details:")
        sol = solutions[0]
        print(f"  Part ID: {sol.part_id}")
        print(f"  Tabs: {list(sol.tabs.keys())}")

        for tab_id, tab in sol.tabs.items():
            bp_count = len([p for p in tab.points.keys() if p.startswith('BP')])
            fp_count = len([p for p in tab.points.keys() if p.startswith('FP')])
            print(f"    Tab {tab_id}: {bp_count} BPs, {fp_count} FPs, {len(tab.points)} total points")

        print("\n  SUCCESS: Merge logic and edge usage filter work with zero-bend segments!")
    else:
        print("\n  WARNING: No solutions generated")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

print()

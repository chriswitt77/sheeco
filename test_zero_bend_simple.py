"""
Test simple 2-tab solution generation with zero-bend.
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

# Test case: two coplanar tabs
coplanar_two_tabs = [
    {'pointA': [0, 0, 0], 'pointB': [50, 0, 0], 'pointC': [50, 50, 0]},
    {'pointA': [70, 0, 0], 'pointB': [120, 0, 0], 'pointC': [120, 50, 0]}
]

print("="*80)
print(" ZERO-BEND SIMPLE 2-TAB TEST")
print("="*80)
print()

print("Test case: 2 coplanar tabs in XY plane")
print()

try:
    part = initialize_objects(coplanar_two_tabs)
    print(f"Initialized with {len(part.tabs)} tabs")

    # Generate sequence
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
            passed_count = 0
            for segments_combination in itertools.product(*segments_library):
                combo_count += 1
                new_part = variant_part.copy()
                new_segments_combination = copy.deepcopy(segments_combination)
                new_part = part_assembly(new_part, new_segments_combination, filter_cfg)

                if new_part is not None:
                    part_id += 1
                    new_part.part_id = part_id
                    solutions.append(new_part)
                    passed_count += 1

            print(f"    Checked {combo_count} combinations, {passed_count} passed")

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

        print("\n  SUCCESS: Zero-bend segments work with assembly!")
    else:
        print("\n  ERROR: No solutions generated - checking why...")

        # Debug: Try one combination manually
        print("\n  Debugging first combination:")
        part2 = initialize_objects(coplanar_two_tabs)
        variants2 = determine_sequences(part2, cfg)
        for variant_part, sequences in variants2:
            for sequence in sequences:
                segments_library = []
                for pair in sequence:
                    tab_x = variant_part.tabs[pair[0]]
                    tab_z = variant_part.tabs[pair[1]]
                    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
                    segment = Part(sequence=pair, tabs=segment_tabs)
                    segments = create_segments(segment, segment_cfg, filter_cfg)
                    segments_library.append(segments)

                variant_part.sequence = sequence
                segments_combination = [lib[0] for lib in segments_library]
                new_part = variant_part.copy()
                new_segments_combination = copy.deepcopy(segments_combination)

                print(f"    Attempting assembly...")
                new_part = part_assembly(new_part, new_segments_combination, filter_cfg)

                if new_part is None:
                    print(f"    Assembly returned None - combination rejected")
                else:
                    print(f"    Assembly succeeded!")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

print()

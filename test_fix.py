import time
start_time = time.time()

import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import RECTANGLE_INPUTS

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

import copy
import itertools
from src.hgen_sm import Part
from src.hgen_sm import initialize_objects, determine_sequences, create_segments, part_assembly

# Try to import custom sequence if it exists
import config.user_input as user_input_module
CUSTOM_SEQUENCE = None
CUSTOM_SEQUENCE_NAME = None

if hasattr(user_input_module, 'RECTANGLE_INPUTS'):
    for attr_name in dir(user_input_module):
        if attr_name.endswith('_sequence') and not attr_name.startswith('_'):
            base_name = attr_name.replace('_sequence', '')
            if hasattr(user_input_module, base_name):
                input_config = getattr(user_input_module, base_name)
                if input_config == RECTANGLE_INPUTS:
                    CUSTOM_SEQUENCE = getattr(user_input_module, attr_name)
                    CUSTOM_SEQUENCE_NAME = attr_name
                    break

def main():
    segment_cfg = cfg.get('design_exploration')
    filter_cfg = cfg.get('filter')
    topo_cfg = cfg.get('topologies', {})

    part = initialize_objects(RECTANGLE_INPUTS)

    use_custom = topo_cfg.get('use_custom_sequences', True)

    if use_custom and CUSTOM_SEQUENCE is not None:
        print(f"Using custom sequence: {CUSTOM_SEQUENCE_NAME} = {CUSTOM_SEQUENCE}")
        variants = [(part, [CUSTOM_SEQUENCE])]
    else:
        if CUSTOM_SEQUENCE is not None and not use_custom:
            print(f"Custom sequence '{CUSTOM_SEQUENCE_NAME}' found but use_custom_sequences=false, using auto-generation")
        variants = determine_sequences(part, cfg)

    solutions = []
    part_id = 0

    for variant_part, sequences in variants:
        variant_name = "separated" if any('_' in str(tid) for tid in variant_part.tabs.keys()) else "unseparated"
        print(f"\nProcessing {variant_name} variant with {len(variant_part.tabs)} tabs...")
        print(f"Number of sequences: {len(sequences)}")

        for seq_idx, sequence in enumerate(sequences):
            print(f"  Sequence {seq_idx + 1}/{len(sequences)}: {sequence}")
            segments_library = []

            for pair in sequence:
                tab_x = variant_part.tabs[pair[0]]
                tab_z = variant_part.tabs[pair[1]]
                segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
                segment = Part(sequence=pair, tabs=segment_tabs)
                segments = create_segments(segment, segment_cfg, filter_cfg)
                segments_library.append(segments)
                print(f"    Pair {pair}: {len(segments)} segments")

            # Count combinations
            total_combos = 1
            for segs in segments_library:
                total_combos *= len(segs)
            print(f"    Total combinations to check: {total_combos}")

            # Assemble Parts
            variant_part.sequence = sequence
            combo_count = 0
            for segments_combination in itertools.product(*segments_library):
                combo_count += 1
                if combo_count % 1000 == 0:
                    print(f"      Checked {combo_count}/{total_combos} combinations...")

                new_part = variant_part.copy()
                new_segments_combination = copy.deepcopy(segments_combination)
                new_part = part_assembly(new_part, new_segments_combination, filter_cfg)

                if new_part is not None:
                    part_id += 1
                    new_part.part_id = part_id
                    solutions.append(new_part)

    print("\n--- %s seconds ---" % (time.time() - start_time))
    print(f"Found {len(solutions)} solutions")

if __name__ == '__main__':
    main()

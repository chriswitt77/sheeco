import time
start_time = time.time()

import yaml

from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import RECTANGLE_INPUTS
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)
import copy

import itertools

from src.hgen_sm import Part
from src.hgen_sm import initialize_objects, determine_sequences, create_segments, part_assembly, plot_solutions, plot_input_rectangles

# Try to import custom sequence if it exists
import config.user_input as user_input_module
CUSTOM_SEQUENCE = None
CUSTOM_SEQUENCE_NAME = None
# Check if a custom sequence variable exists matching the current input name
if hasattr(user_input_module, 'RECTANGLE_INPUTS'):
    for attr_name in dir(user_input_module):
        if attr_name.endswith('_sequence') and not attr_name.startswith('_'):
            # Check if this sequence name matches a defined input configuration
            base_name = attr_name.replace('_sequence', '')
            if hasattr(user_input_module, base_name):
                input_config = getattr(user_input_module, base_name)
                if input_config == RECTANGLE_INPUTS:
                    CUSTOM_SEQUENCE = getattr(user_input_module, attr_name)
                    CUSTOM_SEQUENCE_NAME = attr_name
                    break

def main():
    segment_cfg = cfg.get('design_exploration')
    plot_cfg = cfg.get('plot')
    filter_cfg = cfg.get('filter')
    topo_cfg = cfg.get('topologies', {})

    # ---- Import user input ----
    part = initialize_objects(RECTANGLE_INPUTS)

    # ---- Plot input rectangles (blocking - if enabled) ----
    if plot_cfg.get('Show Input', True):
        plot_input_rectangles(part, plot_cfg)

    # ---- Determine sensible Topologies ----
    # Returns list of (part_variant, sequences) tuples
    # This includes both separated and unseparated variants if configured
    use_custom = topo_cfg.get('use_custom_sequences', True)

    if use_custom and CUSTOM_SEQUENCE is not None:
        # Use custom sequence instead of auto-generation
        print(f"Using custom sequence: {CUSTOM_SEQUENCE_NAME} = {CUSTOM_SEQUENCE}")
        variants = [(part, [CUSTOM_SEQUENCE])]
    else:
        if CUSTOM_SEQUENCE is not None and not use_custom:
            print(f"Custom sequence '{CUSTOM_SEQUENCE_NAME}' found but use_custom_sequences=false, using auto-generation")
        variants = determine_sequences(part, cfg)

    # ---- Find ways to connect pairs ----
    solutions = []
    part_id: int = 0

    for variant_part, sequences in variants:
        variant_name = "separated" if any('_' in str(tid) for tid in variant_part.tabs.keys()) else "unseparated"
        print(f"\nProcessing {variant_name} variant with {len(variant_part.tabs)} tabs...")

        for sequence in sequences:
            segments_library = []
            for pair in sequence:
                tab_x = variant_part.tabs[pair[0]]
                tab_z = variant_part.tabs[pair[1]]
                segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
                segment = Part(sequence=pair, tabs=segment_tabs)
                segments_library.append(create_segments(segment, segment_cfg, filter_cfg))

            # ---- Assemble Parts ----
            variant_part.sequence = sequence
            for segments_combination in itertools.product(*segments_library):
                new_part = variant_part.copy()
                new_segments_combination = copy.deepcopy(segments_combination)
                new_part = part_assembly(new_part, new_segments_combination, filter_cfg)
                if new_part == None: continue
                part_id += 1
                new_part.part_id = part_id
                solutions.append(new_part)

    print("\n--- %s seconds ---" % (time.time() - start_time))
    print(f"Found {len(solutions)} solutions")

    if len(solutions) == 0:
        return

    #  ---- Plot solutions ----
    plot_solutions(solutions, plot_cfg = plot_cfg)

if __name__ == '__main__':
    main()
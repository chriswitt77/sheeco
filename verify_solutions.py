import time
start_time = time.time()

import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import shock_absorber

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

import copy
import itertools
from src.hgen_sm import Part
from src.hgen_sm import initialize_objects, create_segments, part_assembly

# Use custom sequence
shock_absorber_sequence = [['1', '2'], ['1', '0']]

def main():
    segment_cfg = cfg.get('design_exploration')
    filter_cfg = cfg.get('filter')

    part = initialize_objects(shock_absorber)

    # Use custom sequence
    variants = [(part, [shock_absorber_sequence])]

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

            # Assemble Parts
            variant_part.sequence = sequence
            for segments_combination in itertools.product(*segments_library):
                new_part = variant_part.copy()
                new_segments_combination = copy.deepcopy(segments_combination)
                new_part = part_assembly(new_part, new_segments_combination, filter_cfg)

                if new_part is not None:
                    part_id += 1
                    new_part.part_id = part_id
                    solutions.append(new_part)

    print(f"\nFound {len(solutions)} solutions\n")

    # Analyze which solutions have intermediate tabs (two-bend for 1→0)
    single_bend_count = 0
    double_bend_count = 0

    for sol in solutions:
        tab_ids = list(sol.tabs.keys())

        # Check if there's an intermediate tab (tab ID not in ['0', '1', '2'])
        has_intermediate = any(tid not in ['0', '1', '2'] for tid in tab_ids)

        if has_intermediate:
            double_bend_count += 1
            intermediate_tabs = [tid for tid in tab_ids if tid not in ['0', '1', '2']]
            print(f"Solution {sol.part_id}: DOUBLE BEND - Tabs: {tab_ids}")
            print(f"  Intermediate tab(s): {intermediate_tabs}")
        else:
            single_bend_count += 1

    print(f"\nSummary:")
    print(f"  Single-bend solutions (3 tabs): {single_bend_count}")
    print(f"  Double-bend solutions (4+ tabs): {double_bend_count}")
    print(f"\n--- {time.time() - start_time:.2f} seconds ---")

if __name__ == '__main__':
    main()

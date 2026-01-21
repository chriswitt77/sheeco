import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import initialize_objects, determine_sequences, create_segments, part_assembly
from src.hgen_sm import Part
import copy
import itertools

# Test configurations with and without negative coordinates
test_configs = {
    'shock_absorber (no negatives)': [
        {'pointA': [20, 0, 0], 'pointB': [80, 0, 0], 'pointC': [80, 35, 0]},
        {'pointA': [0, 0, 20], 'pointB': [0, 0, 60], 'pointC': [0, 80, 60]},
    ],
    'ver_example_one (with negatives)': [
        {'pointA': [30, 30, 0], 'pointB': [30, 0, 0], 'pointC': [80, 0, 0]},
        {'pointA': [-20, 80, 40], 'pointB': [-20, 40, 40], 'pointC': [-40, 40, 80]},
    ],
}

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

for name, rectangles in test_configs.items():
    print(f"\nTesting: {name}")
    print(f"  Rectangle coordinates: {rectangles}")

    try:
        part = initialize_objects(rectangles)
        print(f"  [OK] Initialization successful")

        variants = determine_sequences(part, cfg)
        print(f"  [OK] Sequences determined: {len(variants)} variants")

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
                    print(f"    Pair {pair}: {len(segments)} segments")

                # Check first few combinations
                variant_part.sequence = sequence
                for i, segments_combination in enumerate(itertools.product(*segments_library)):
                    if i >= 5:  # Only test first 5 combinations
                        break
                    new_part = variant_part.copy()
                    new_segments_combination = copy.deepcopy(segments_combination)
                    new_part = part_assembly(new_part, new_segments_combination, filter_cfg)
                    if new_part is not None:
                        part_id += 1
                        solutions.append(new_part)

        print(f"  [OK] Found {len(solutions)} solutions (tested first 5 combinations)")

    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

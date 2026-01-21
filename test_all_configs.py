import time
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

import copy
import itertools
from src.hgen_sm import Part
from src.hgen_sm import initialize_objects, determine_sequences, create_segments, part_assembly

# Import all test configurations
from config.user_input import (
    ver_example_one, ver_example_two, shock_absorber, shock_absorber_double_tab,
    ver_acrylic_model, campbell_vertical, barda_example_one, barda_example_two
)

test_configs = {
    'ver_example_one': ver_example_one,
    'ver_example_two': ver_example_two,
    'shock_absorber': shock_absorber,
    'shock_absorber_double_tab': shock_absorber_double_tab,
    'ver_acrylic_model': ver_acrylic_model,
    'campbell_vertical': campbell_vertical,
    'barda_example_one': barda_example_one,
    'barda_example_two': barda_example_two,
}

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

results = {}

for name, rectangles in test_configs.items():
    print(f"\nTesting {name}...")
    start = time.time()

    try:
        part = initialize_objects(rectangles)
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

                variant_part.sequence = sequence
                for segments_combination in itertools.product(*segments_library):
                    new_part = variant_part.copy()
                    new_segments_combination = copy.deepcopy(segments_combination)
                    new_part = part_assembly(new_part, new_segments_combination, filter_cfg)

                    if new_part is not None:
                        part_id += 1
                        new_part.part_id = part_id
                        solutions.append(new_part)

        elapsed = time.time() - start
        results[name] = {'solutions': len(solutions), 'time': elapsed, 'status': 'SUCCESS'}
        print(f"  [OK] {len(solutions)} solutions in {elapsed:.2f}s")

    except Exception as e:
        elapsed = time.time() - start
        results[name] = {'solutions': 0, 'time': elapsed, 'status': f'ERROR: {e}'}
        print(f"  [ERROR] {e}")

print("\n\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"{'Configuration':<30} {'Solutions':<12} {'Time (s)':<12} {'Status'}")
print("-"*70)

for name, result in results.items():
    status_symbol = 'OK' if result['status'] == 'SUCCESS' else 'FAIL'
    print(f"{name:<30} {result['solutions']:<12} {result['time']:<12.2f} {status_symbol}")

print("="*70)

total_success = sum(1 for r in results.values() if r['status'] == 'SUCCESS')
print(f"\nTotal: {total_success}/{len(results)} configurations successful")

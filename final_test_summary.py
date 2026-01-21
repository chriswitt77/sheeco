import yaml
from pathlib import Path
from config.user_input import *

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import initialize_objects, determine_sequences, create_segments, part_assembly, Part
import copy, itertools

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

# Test configurations with their custom sequences
configs = [
    ('ver_example_one', ver_example_one, None),
    ('ver_example_two', ver_example_two, None),
    ('shock_absorber', shock_absorber, shock_absorber_sequence),
    ('shock_absorber_double_tab', shock_absorber_double_tab, shock_absorber_double_tab_sequence),
    ('ver_acrylic_model', ver_acrylic_model, None),
    ('campbell_vertical', campbell_vertical, None),
    ('barda_example_one', barda_example_one, barda_example_one_sequence),
    ('barda_example_two', barda_example_two, barda_example_two_sequence),
]

print("="*80)
print(" FINAL TEST SUMMARY - Edge-Based Multi-Merge Implementation")
print("="*80)
print(f"{'Configuration':<30} {'Auto':<8} {'Custom':<8} {'Status'}")
print("-"*80)

for name, rectangles, custom_seq in configs:
    part = initialize_objects(rectangles)

    # Test with auto-generated sequences
    variants_auto = determine_sequences(part, cfg)
    solutions_auto = 0
    for variant_part, sequences in variants_auto:
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
                    solutions_auto += 1

    # Test with custom sequence if available
    solutions_custom = None
    if custom_seq is not None:
        part2 = initialize_objects(rectangles)
        variants_custom = [(part2, [custom_seq])]
        solutions_custom = 0
        for variant_part, sequences in variants_custom:
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
                        solutions_custom += 1

    # Determine status
    if solutions_auto > 0:
        status = "OK"
    elif solutions_custom is not None and solutions_custom > 0:
        status = "OK (custom only)"
    else:
        status = "FAIL"

    custom_str = str(solutions_custom) if solutions_custom is not None else "-"
    print(f"{name:<30} {solutions_auto:<8} {custom_str:<8} {status}")

print("="*80)
print("\nLegend:")
print("  Auto: Solutions using auto-generated sequences")
print("  Custom: Solutions using custom sequence (if defined)")
print("  OK: Working with auto-generated sequences")
print("  OK (custom only): Only works with custom sequence")
print("  FAIL: No solutions found")

"""
Test script to verify export functionality works with fixed implementation.
"""

import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import RECTANGLE_INPUTS

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part
from src.hgen_sm import initialize_objects, determine_sequences, create_segments, part_assembly
from src.hgen_sm.export.part_export import export_to_json, export_to_onshape

def main():
    segment_cfg = cfg.get('design_exploration')
    filter_cfg = cfg.get('filter')

    # ---- Import user input ----
    part = initialize_objects(RECTANGLE_INPUTS)

    # ---- Determine sensible Topologies ----
    variants = determine_sequences(part, cfg)

    # ---- Find ways to connect pairs ----
    solutions = []
    part_id = 0

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
            combinations = [[segments_library[i][j] for i in range(len(segments_library))]
                           for j in range(len(segments_library[0]))]

            for combination in combinations:
                new_part = variant_part.copy()
                new_part.part_id = part_id
                new_part.sequence = sequence

                new_part = part_assembly(new_part, combination, filter_cfg)
                if new_part:
                    solutions.append(new_part)
                    part_id += 1

                    # Collect multiple solutions to find one with intermediate tabs
                    if len(solutions) >= 5:
                        break

            if len(solutions) >= 5:
                break

        if len(solutions) >= 5:
            break

    print(f"\n{'='*60}")
    print(f"Found {len(solutions)} solutions")
    print(f"{'='*60}")

    # Find a solution with intermediate tabs (tab IDs like "01", "12")
    test_part = None
    for part in solutions:
        for tab_id in part.tabs.keys():
            if len(str(tab_id)) > 1 and not '_' in str(tab_id):
                test_part = part
                print(f"\nFound part with intermediate tabs: {list(part.tabs.keys())}")
                break
        if test_part:
            break

    # Fallback to first solution if no intermediate tabs found
    if not test_part and len(solutions) > 0:
        test_part = solutions[0]
        print(f"\nUsing solution without intermediate tabs: {list(test_part.tabs.keys())}")

    print(f"\n{'='*60}")
    print(f"Testing export functions")
    print(f"{'='*60}")

    if test_part:
        print(f"\nTest Part ID: {test_part.part_id}")
        print(f"Number of tabs: {len(test_part.tabs)}")

        # Test JSON export
        try:
            print("\n[1/2] Testing JSON export...")
            json_path = export_to_json(test_part, output_dir="exports_test")
            print(f"[OK] JSON export successful: {json_path}")
        except Exception as e:
            print(f"[FAIL] JSON export failed: {e}")
            import traceback
            traceback.print_exc()

        # Test Onshape FeatureScript export
        try:
            print("\n[2/2] Testing Onshape FeatureScript export...")
            fs_path = export_to_onshape(test_part, output_dir="exports_test")
            print(f"[OK] FeatureScript export successful")
        except Exception as e:
            print(f"[FAIL] FeatureScript export failed: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n{'='*60}")
        print(f"Export tests complete!")
        print(f"{'='*60}\n")
    else:
        print("No solutions found to test exports")

if __name__ == "__main__":
    main()

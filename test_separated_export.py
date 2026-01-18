"""
Test export specifically for separated surfaces (the problematic case).
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
from src.hgen_sm.export.part_export import export_to_onshape

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

    # Look specifically for SEPARATED variants
    for variant_part, sequences in variants:
        variant_name = "separated" if any('_' in str(tid) for tid in variant_part.tabs.keys()) else "unseparated"

        # Skip unseparated variants
        if variant_name == "unseparated":
            continue

        print(f"\nProcessing {variant_name} variant with {len(variant_part.tabs)} tabs...")
        print(f"Tab IDs: {list(variant_part.tabs.keys())}")

        for sequence in sequences:
            print(f"  Sequence: {sequence}")
            print(f"  Tab geometries:")
            for tid in variant_part.tabs.keys():
                t = variant_part.tabs[tid]
                if 'A' in t.points:
                    corners = {k: t.points[k] for k in ['A','B','C','D']}
                    print(f"    Tab {tid}: {corners}")
            segments_library = []
            for pair in sequence:
                tab_x = variant_part.tabs[pair[0]]
                tab_z = variant_part.tabs[pair[1]]
                segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
                segment = Part(sequence=pair, tabs=segment_tabs)
                segs = create_segments(segment, segment_cfg, filter_cfg)
                print(f"    Connection {pair[0]}->{pair[1]}: {len(segs) if segs else 0} segments")
                if not segs or len(segs) == 0:
                    print(f"    WARNING: No valid segments found for {pair[0]}->{pair[1]}")
                    continue
                segments_library.append(segs)

            # ---- Assemble Parts ----
            if len(segments_library) == 0:
                print("    No segments to assemble")
                continue

            # Generate combinations - use minimum length to avoid index errors
            min_segments = min(len(segs) for segs in segments_library)
            print(f"    Generating {min_segments} combinations from segment lists of sizes {[len(s) for s in segments_library]}")
            combinations = [[segments_library[i][j] for i in range(len(segments_library))]
                           for j in range(min_segments)]

            for combination in combinations:
                new_part = variant_part.copy()
                new_part.part_id = part_id
                new_part.sequence = sequence

                new_part = part_assembly(new_part, combination, filter_cfg)
                if new_part:
                    solutions.append(new_part)
                    part_id += 1

                    # Stop after finding first separated solution
                    if len(solutions) >= 1:
                        break

            if len(solutions) >= 1:
                break

        if len(solutions) >= 1:
            break

    print(f"\n{'='*60}")
    print(f"Found {len(solutions)} separated surface solution(s)")
    print(f"{'='*60}")

    if len(solutions) > 0:
        test_part = solutions[0]
        print(f"\nTest Part ID: {test_part.part_id}")
        print(f"Tab IDs: {list(test_part.tabs.keys())}")
        print(f"Number of tabs: {len(test_part.tabs)}")

        # Show tab 0_0 points to verify duplicate filtering
        if '0_0' in test_part.tabs:
            print(f"\nTab 0_0 has {len(test_part.tabs['0_0'].points)} points:")
            print(f"  {list(test_part.tabs['0_0'].points.keys())}")

        # Test JSON export first
        from src.hgen_sm.export.part_export import export_to_json
        try:
            print(f"\nExporting to JSON...")
            json_path = export_to_json(test_part, output_dir="exports_test_separated")
            print(f"[OK] JSON export successful: {json_path}")
        except Exception as e:
            print(f"[FAIL] JSON export failed: {e}")

        # Test Onshape FeatureScript export
        try:
            print(f"\n{'='*60}")
            print("Exporting to Onshape FeatureScript...")
            print(f"{'='*60}")
            fs_path = export_to_onshape(test_part, output_dir="exports_test_separated")
            print(f"\n[OK] FeatureScript export successful")
            print(f"\nGenerated file:")
            print(f"  exports_test_separated/{fs_path.split('/')[-1] if '/' in fs_path else fs_path.split(chr(92))[-1]}")
            print(f"\nYou can now copy this to Onshape and verify:")
            print(f"  1. Tab 0_0 is a single connected shape (not multiple regions)")
            print(f"  2. Mount hole is properly cut out from the tab")
            print(f"  3. All tabs union correctly")
        except Exception as e:
            print(f"[FAIL] FeatureScript export failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("No separated surface solutions found")

if __name__ == "__main__":
    main()

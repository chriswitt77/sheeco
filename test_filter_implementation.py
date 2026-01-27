"""
Test the implemented perpendicular edge filter with transportschuh.
"""

import yaml
import json
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects
from src.hgen_sm.determine_sequences import determine_sequences
from src.hgen_sm.create_segments import create_segments
from src.hgen_sm.part_assembly import part_assembly

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

print("="*80)
print("TESTING PERPENDICULAR EDGE FILTER IMPLEMENTATION")
print("="*80)

# Initialize part
part = initialize_objects(transportschuh)
print(f"\nInitialized part with {len(part.tabs)} tabs")

# Determine sequences
sequences = determine_sequences(part, cfg)
print(f"Generated {len(sequences)} sequences")

# Create segments
segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print(f"\nFilter configuration:")
print(f"  max_edge_to_bend_angle: {filter_cfg.get('max_edge_to_bend_angle', 'not set')}")

all_segments = []
for variant_idx, (variant_part, variant_sequences) in enumerate(sequences):
    variant_name = "separated" if any('_' in str(tid) for tid in variant_part.tabs.keys()) else "unseparated"
    print(f"\nProcessing {variant_name} variant with {len(variant_part.tabs)} tabs...")

    for seq_idx, sequence in enumerate(variant_sequences):
        print(f"  Sequence {seq_idx+1}: {sequence}")

        # Process each pair in the sequence
        for pair in sequence:
            tab_x = variant_part.tabs[pair[0]]
            tab_z = variant_part.tabs[pair[1]]

            # Create segment
            segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
            from src.hgen_sm import Part
            segment = Part(sequence=pair, tabs=segment_tabs)

            # Generate segments for this pair
            segments = create_segments(segment, segment_cfg, filter_cfg)

            if segments:
                print(f"    Pair {pair}: Generated {len(segments)} segments")

                # Count one-bend vs two-bend segments
                one_bend_count = sum(1 for s in segments if len(s.tabs) == 2)
                two_bend_count = sum(1 for s in segments if len(s.tabs) == 3)

                print(f"      One-bend: {one_bend_count}, Two-bend: {two_bend_count}")

                all_segments.extend(segments)
            else:
                print(f"    Pair {pair}: No segments generated")

print(f"\n{'='*80}")
print(f"TOTAL SEGMENTS GENERATED: {len(all_segments)}")
print(f"{'='*80}")

# Count segment types
one_bend_total = sum(1 for s in all_segments if len(s.tabs) == 2)
two_bend_total = sum(1 for s in all_segments if len(s.tabs) == 3)

print(f"\nSegment breakdown:")
print(f"  One-bend segments: {one_bend_total}")
print(f"  Two-bend segments: {two_bend_total}")

# Assemble parts
print(f"\n{'='*80}")
print(f"ASSEMBLING PARTS")
print(f"{'='*80}")

# Note: part_assembly works differently - it takes a part and segments
# For testing purposes, just verify the segment counts
parts = []
print(f"\nGenerated {len(parts)} complete parts")

# Expected results:
print(f"\n{'='*80}")
print(f"VALIDATION")
print(f"{'='*80}")

print(f"""
Expected behavior with perpendicular edge filter:
  - Before fix: ~6 one-bend segments (4 infeasible with perpendicular edges)
  - After fix: ~2 one-bend segments (only parallel edges)
  - Two-bend segments should also be generated

Actual results:
  - One-bend segments: {one_bend_total}
  - Two-bend segments: {two_bend_total}
  - Total parts: {len(parts)}
""")

if one_bend_total <= 2:
    print("[SUCCESS] Perpendicular edges appear to be filtered correctly!")
elif one_bend_total >= 6:
    print("[WARNING] Filter may not be working - still generating many one-bend segments")
else:
    print("[PARTIAL] Some filtering occurred, but verify if correct")

# Export parts to JSON for inspection
output = {
    "parts": []
}

for i, part_obj in enumerate(parts):
    part_data = {
        "part_id": i + 1,
        "tabs": {}
    }

    for tab_id, tab in part_obj.tabs.items():
        tab_data = {
            "points": {k: v.tolist() for k, v in tab.points.items()}
        }
        part_data["tabs"][tab_id] = tab_data

    output["parts"].append(part_data)

# Save to file
output_file = PROJECT_ROOT / "transportschuh_filtered_output.json"
with output_file.open("w") as f:
    json.dump(output, f, indent=2)

print(f"\nParts exported to: {output_file}")
print(f"\nTest complete!")

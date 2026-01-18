"""
Test all two-bend solutions to check flange positioning
"""
import yaml
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import RECTANGLE_INPUTS
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part, initialize_objects, determine_sequences, create_segments

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

# Initialize
part = initialize_objects(RECTANGLE_INPUTS)
variants = determine_sequences(part, cfg)
variant_part, sequences = variants[0]  # Unseparated variant

# Process first pair
pair = sequences[0][0]
tab_x = variant_part.tabs[pair[0]]
tab_z = variant_part.tabs[pair[1]]

print(f"Testing pair: {pair}")
print(f"\nTab {pair[0]} corners:")
for c_id in ['A', 'B', 'C', 'D']:
    if c_id in tab_x.rectangle.points:
        print(f"  {c_id}: {tab_x.rectangle.points[c_id]}")

print(f"\nTab {pair[1]} corners:")
for c_id in ['A', 'B', 'C', 'D']:
    if c_id in tab_z.rectangle.points:
        print(f"  {c_id}: {tab_z.rectangle.points[c_id]}")

segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
segment = Part(sequence=pair, tabs=segment_tabs)

segments = create_segments(segment, segment_cfg, filter_cfg)

# Find two-bend segments
two_bend_segments = [s for s in segments if len(s.tabs) == 3]

print(f"\n{len(two_bend_segments)} two-bend segments generated\n")

def check_flange_position(tab, tab_id, rect_corners):
    """Check if BP points are outside the rectangle"""
    bp_points = {k: v for k, v in tab.points.items() if k.startswith('BP')}
    if not bp_points:
        return "No BP points"

    # Get rectangle bounds
    corners = [rect_corners[c] for c in ['A', 'B', 'C', 'D'] if c in rect_corners]
    if len(corners) < 4:
        return "Missing corners"

    min_coords = np.min(corners, axis=0)
    max_coords = np.max(corners, axis=0)

    # Check each BP point
    issues = []
    for bp_id, bp_coord in bp_points.items():
        # Check if BP is inside rectangle bounds (with small tolerance)
        inside = all(min_coords[i] - 0.1 <= bp_coord[i] <= max_coords[i] + 0.1 for i in range(3))
        if inside:
            issues.append(f"{bp_id} at {bp_coord} is INSIDE rectangle bounds [{min_coords}, {max_coords}]")

    if issues:
        return "WRONG: " + "; ".join(issues)
    return "OK"

for i, seg in enumerate(two_bend_segments[:10]):  # Check first 10
    print(f"\n{'='*70}")
    print(f"SEGMENT {i+1}")
    print(f"{'='*70}")

    tab_x_result = seg.tabs.get('tab_x')
    tab_z_result = seg.tabs.get('tab_z')

    if tab_x_result:
        print(f"\ntab_x (original: {pair[0]}):")
        print(f"  Perimeter: {list(tab_x_result.points.keys())}")

        bp_points = {k: v for k, v in tab_x_result.points.items() if k.startswith('BP')}
        if bp_points:
            print(f"  BP points:")
            for bp_id, bp_coord in bp_points.items():
                print(f"    {bp_id}: {bp_coord}")

        status = check_flange_position(tab_x_result, pair[0], tab_x.rectangle.points)
        print(f"  Status: {status}")

    if tab_z_result:
        print(f"\ntab_z (original: {pair[1]}):")
        print(f"  Perimeter: {list(tab_z_result.points.keys())}")

        bp_points = {k: v for k, v in tab_z_result.points.items() if k.startswith('BP')}
        if bp_points:
            print(f"  BP points:")
            for bp_id, bp_coord in bp_points.items():
                print(f"    {bp_id}: {bp_coord}")

        status = check_flange_position(tab_z_result, pair[1], tab_z.rectangle.points)
        print(f"  Status: {status}")

"""Test to validate the FP deduplication fix."""

from src.hgen_sm import initialize_objects, determine_sequences, create_segments, part_assembly, Part
from config.user_input import zylinderhalter
import yaml
import itertools

# Load config
with open('config/config.yaml', 'r') as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

print("=" * 80)
print("VALIDATING FP DEDUPLICATION FIX")
print("=" * 80)
print()

# Initialize
part = initialize_objects(zylinderhalter)

# Generate sequences
variants = determine_sequences(part, cfg)

print(f"Generated {len(variants)} variants")
print()

# Process all variants
all_solutions = []
part_id = 0

for variant_part, sequences in variants:
    print(f"Processing variant with {len(sequences)} sequences...")

    for seq_idx, sequence in enumerate(sequences):
        segments_library = []

        for pair in sequence:
            tab_x = variant_part.tabs[pair[0]]
            tab_z = variant_part.tabs[pair[1]]
            segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
            segment = Part(sequence=pair, tabs=segment_tabs)
            segment_variations = create_segments(segment, cfg['design_exploration'], cfg['filter'])
            segments_library.append(segment_variations)

        if not all(segments_library):
            continue

        # Try all combinations
        for segments_combination in itertools.product(*segments_library):
            new_part = variant_part.copy()
            new_segments_combination = list(segments_combination)
            new_part = part_assembly(new_part, new_segments_combination, cfg['filter'])

            if new_part is not None:
                part_id += 1
                new_part.part_id = part_id
                all_solutions.append(new_part)

print(f"\nTotal solutions generated: {len(all_solutions)}")
print()

# Validate solutions
print("=" * 80)
print("VALIDATION RESULTS")
print("=" * 80)
print()

issues_found = 0
parts_with_issues = []

for part in all_solutions:
    part_issues = []

    for tab_id, tab in part.tabs.items():
        # Skip intermediate tabs
        if '_' not in tab_id and len(tab_id) > 1:
            continue

        points_list = list(tab.points.keys())
        corners_in_order = [p for p in points_list if p in ['A', 'B', 'C', 'D']]

        # Check 1: All corners grouped together (Part 8 pattern)
        if len(corners_in_order) == 4:
            first_corner_idx = points_list.index(corners_in_order[0])
            last_corner_idx = points_list.index(corners_in_order[-1])
            span = last_corner_idx - first_corner_idx + 1

            if span == 4:
                part_issues.append(f"Tab {tab_id}: All 4 corners grouped at positions {first_corner_idx + 1}-{last_corner_idx + 1}")

        # Check 2: Large gaps between consecutive points
        points_coords = [tab.points[name] for name in points_list]
        for i in range(len(points_coords)):
            p1 = points_coords[i]
            p2 = points_coords[(i + 1) % len(points_coords)]
            dist = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2 + (p2[2] - p1[2])**2)**0.5

            if dist > 35:  # Suspiciously large gap
                name1 = points_list[i]
                name2 = points_list[(i + 1) % len(points_list)]
                part_issues.append(f"Tab {tab_id}: Large gap ({dist:.1f}) between {name1} -> {name2}")

        # Check 3: FP points coinciding with corners
        corners_coords = {k: v for k, v in tab.points.items() if k in ['A', 'B', 'C', 'D']}
        for point_name, coord in tab.points.items():
            if 'FP' in point_name:
                import numpy as np
                for corner_name, corner_coord in corners_coords.items():
                    if np.allclose(coord, corner_coord, atol=1e-6):
                        part_issues.append(f"Tab {tab_id}: FP point {point_name} duplicates corner {corner_name}")

    if part_issues:
        issues_found += len(part_issues)
        parts_with_issues.append((part.part_id, part_issues))

if issues_found == 0:
    print("[OK] No issues found in any parts!")
    print("     - No corners grouped together")
    print("     - No large gaps between consecutive points")
    print("     - No FP points duplicating corners")
else:
    print(f"[ERROR] Found {issues_found} issues in {len(parts_with_issues)} parts")
    print()
    print("Parts with issues:")
    for part_id, issues in parts_with_issues[:5]:  # Show first 5
        print(f"\n  Part {part_id}:")
        for issue in issues:
            print(f"    - {issue}")

    if len(parts_with_issues) > 5:
        print(f"\n  ... and {len(parts_with_issues) - 5} more parts with issues")

print()
print("=" * 80)

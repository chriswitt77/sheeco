"""
Validate that the filtered segments use only parallel edges, not perpendicular ones.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects, Part
from src.hgen_sm.create_segments import create_segments
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane, calculate_plane_intersection
from src.hgen_sm.data import Bend

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

print("="*80)
print("VALIDATING PERPENDICULAR EDGE FILTER")
print("="*80)

# Initialize part
part = initialize_objects(transportschuh)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

# Calculate bend line
plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)
intersection = calculate_plane_intersection(plane_0, plane_1)
bend = Bend(position=intersection["position"], orientation=intersection["orientation"])

print(f"\nBend line:")
print(f"  Position: {bend.position}")
print(f"  Direction: {bend.orientation}")

# Create segment
segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)

# Generate segments
segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print(f"\nGenerating segments with filter...")
segments = create_segments(segment, segment_cfg, filter_cfg)

print(f"Generated {len(segments)} total segments")

# Analyze each one-bend segment
one_bend_segments = [s for s in segments if len(s.tabs) == 2]
print(f"\n{'='*80}")
print(f"ANALYZING {len(one_bend_segments)} ONE-BEND SEGMENTS")
print(f"{'='*80}")

def find_edge_for_tab(tab_original, tab_with_bends, bend):
    """
    Determine which edge was used by finding corners adjacent to bend points.
    """
    # Find bend points in the modified tab
    bend_points = {k: v for k, v in tab_with_bends.points.items() if 'BP' in k}

    if len(bend_points) < 2:
        return None

    # Get the corners
    corners = {k: v for k, v in tab_with_bends.points.items() if k in ['A', 'B', 'C', 'D']}

    # Find corners adjacent to bend points
    point_order = list(tab_with_bends.points.keys())

    # Find bend point indices
    bp_indices = [i for i, k in enumerate(point_order) if 'BP' in k]

    if len(bp_indices) == 0:
        return None

    # Find corner before first BP
    first_bp_idx = bp_indices[0]
    corner_before = None
    for i in range(first_bp_idx - 1, -1, -1):
        if point_order[i] in ['A', 'B', 'C', 'D']:
            corner_before = point_order[i]
            break

    # Find corner after last BP
    last_bp_idx = bp_indices[-1]
    corner_after = None
    for i in range(last_bp_idx + 1, len(point_order)):
        if point_order[i] in ['A', 'B', 'C', 'D']:
            corner_after = point_order[i]
            break

    if corner_before and corner_after:
        return (corner_before, corner_after)

    return None

for i, seg in enumerate(one_bend_segments):
    print(f"\n{'='*80}")
    print(f"SEGMENT {i+1}")
    print(f"{'='*80}")

    tab_x = seg.tabs['tab_x']
    tab_z = seg.tabs['tab_z']

    # Find edges used
    edge_x = find_edge_for_tab(tab_0, tab_x, bend)
    edge_z = find_edge_for_tab(tab_1, tab_z, bend)

    print(f"\nTab 0 (tab_x) edge: {edge_x}")
    if edge_x:
        c1 = tab_0.points[edge_x[0]]
        c2 = tab_0.points[edge_x[1]]
        edge_vec = c2 - c1
        edge_dir = edge_vec / np.linalg.norm(edge_vec)
        dot_product = abs(np.dot(edge_dir, bend.orientation))
        angle_deg = np.degrees(np.arccos(np.clip(dot_product, 0, 1)))

        print(f"  Edge vector: {edge_vec}")
        print(f"  Angle to bend line: {angle_deg:.1f}°")

        if angle_deg < 15:
            print(f"  [PARALLEL] Good! [OK]")
        elif angle_deg > 75:
            print(f"  [PERPENDICULAR] ERROR - This should have been filtered! [X]")
        else:
            print(f"  [ANGLED] Angle between parallel and perpendicular")

    print(f"\nTab 1 (tab_z) edge: {edge_z}")
    if edge_z:
        c1 = tab_1.points[edge_z[0]]
        c2 = tab_1.points[edge_z[1]]
        edge_vec = c2 - c1
        edge_dir = edge_vec / np.linalg.norm(edge_vec)
        dot_product = abs(np.dot(edge_dir, bend.orientation))
        angle_deg = np.degrees(np.arccos(np.clip(dot_product, 0, 1)))

        print(f"  Edge vector: {edge_vec}")
        print(f"  Angle to bend line: {angle_deg:.1f}°")

        if angle_deg < 15:
            print(f"  [PARALLEL] Good! [OK]")
        elif angle_deg > 75:
            print(f"  [PERPENDICULAR] ERROR - This should have been filtered! [X]")
        else:
            print(f"  [ANGLED] Angle between parallel and perpendicular")

print(f"\n{'='*80}")
print(f"EXPECTED EDGES")
print(f"{'='*80}")
print(f"""
Tab 0 edges:
  A-B: PARALLEL (0 deg) - Should be used [OK]
  B-C: PERPENDICULAR (90 deg) - Should be FILTERED [X]
  C-D: PARALLEL (0 deg) - Should be used [OK]
  D-A: PERPENDICULAR (90 deg) - Should be FILTERED [X]

Tab 1 edges:
  A-B: PARALLEL (0 deg) - Should be used [OK]
  B-C: PERPENDICULAR (90 deg) - Should be FILTERED [X]
  C-D: PARALLEL (0 deg) - Should be used [OK]
  D-A: PERPENDICULAR (90 deg) - Should be FILTERED [X]

Expected segments: 2 (using parallel edges only)
Actual segments: {len(one_bend_segments)}
""")

if len(one_bend_segments) == 2:
    print("[SUCCESS] Correct number of segments generated!")
else:
    print(f"[WARNING] Expected 2 segments, got {len(one_bend_segments)}")

print(f"\nValidation complete!")

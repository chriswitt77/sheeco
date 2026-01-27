"""
Test the bounds-based filter logic to understand what "within coordinate range" means.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane, calculate_plane_intersection
from src.hgen_sm.create_segments.bend_strategies import create_bending_point

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

# Initialize part
part = initialize_objects(transportschuh)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

# Calculate bend
plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)
intersection = calculate_plane_intersection(plane_0, plane_1)

from src.hgen_sm.data import Bend
bend = Bend(position=intersection["position"], orientation=intersection["orientation"])

print("="*80)
print("BOUNDS FILTER LOGIC TEST")
print("="*80)

print(f"\nBend line:")
print(f"  Position: {bend.position}")
print(f"  Orientation: {bend.orientation}")

# Test specific edge combinations that we know are problematic
rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]
rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]

print("\n" + "="*80)
print("TESTING EDGE COMBINATIONS")
print("="*80)

for pair_x in rect_x_edges:
    CP_xL_id, CP_xR_id = pair_x
    CP_xL = tab_0.points[CP_xL_id]
    CP_xR = tab_0.points[CP_xR_id]

    # Calculate edge angle
    edge_x_vec = CP_xR - CP_xL
    edge_x_len = np.linalg.norm(edge_x_vec)
    if edge_x_len < 1e-9:
        continue
    edge_x_dir = edge_x_vec / edge_x_len

    dot_x = abs(np.dot(edge_x_dir, bend.orientation))
    angle_x_deg = np.degrees(np.arccos(np.clip(dot_x, 0, 1)))

    # Only test perpendicular edges
    if angle_x_deg < 75:
        continue

    print(f"\n{'='*80}")
    print(f"TAB 0 EDGE {CP_xL_id}-{CP_xR_id} (Perpendicular: {angle_x_deg:.1f}°)")
    print(f"{'='*80}")

    for pair_z in rect_z_edges:
        CP_zL_id, CP_zR_id = pair_z
        CP_zL = tab_1.points[CP_zL_id]
        CP_zR = tab_1.points[CP_zR_id]

        # Calculate bend points
        BPL = create_bending_point(CP_xL, CP_zL, bend)
        BPR = create_bending_point(CP_xR, CP_zR, bend)

        print(f"\n  Paired with tab 1 edge {CP_zL_id}-{CP_zR_id}:")
        print(f"    CP_xL: {CP_xL}")
        print(f"    CP_xR: {CP_xR}")
        print(f"    CP_zL: {CP_zL}")
        print(f"    CP_zR: {CP_zR}")
        print(f"    BPL: {BPL}")
        print(f"    BPR: {BPR}")

        # Get tab_0 bounding box
        tab_0_corners = [tab_0.points[k] for k in ['A', 'B', 'C', 'D']]
        tab_0_min = np.min(tab_0_corners, axis=0)
        tab_0_max = np.max(tab_0_corners, axis=0)

        print(f"    Tab 0 bounds: min={tab_0_min}, max={tab_0_max}")

        # Check if bend points are within tab_0 bounds
        tolerance = 1e-3
        bpl_in_bounds = np.all((BPL >= tab_0_min - tolerance) &
                               (BPL <= tab_0_max + tolerance))
        bpr_in_bounds = np.all((BPR >= tab_0_min - tolerance) &
                               (BPR <= tab_0_max + tolerance))

        print(f"    BPL in tab_0 bounds: {bpl_in_bounds}")
        print(f"    BPR in tab_0 bounds: {bpr_in_bounds}")

        # Detailed coordinate check
        print(f"    BPL check per axis:")
        for i, axis in enumerate(['x', 'y', 'z']):
            in_range = (BPL[i] >= tab_0_min[i] - tolerance) and (BPL[i] <= tab_0_max[i] + tolerance)
            print(f"      {axis}: {BPL[i]:.3f} in [{tab_0_min[i]:.3f}, {tab_0_max[i]:.3f}]? {in_range}")

        print(f"    BPR check per axis:")
        for i, axis in enumerate(['x', 'y', 'z']):
            in_range = (BPR[i] >= tab_0_min[i] - tolerance) and (BPR[i] <= tab_0_max[i] + tolerance)
            print(f"      {axis}: {BPR[i]:.3f} in [{tab_0_min[i]:.3f}, {tab_0_max[i]:.3f}]? {in_range}")

        # Filter decision
        if bpl_in_bounds and bpr_in_bounds:
            print(f"    FILTER DECISION: FILTER OUT (both bend points within tab bounds)")
        else:
            print(f"    FILTER DECISION: ALLOW (bend points extend beyond tab bounds)")

print("\n" + "="*80)
print("QUESTION FOR USER")
print("="*80)
print("""
Based on the analysis above:
- Perpendicular edge B-C on tab_0 has bend points at y=180
- Tab_0's y-range is [0, 160]
- Bend points are OUTSIDE tab_0's y-range
- Current filter logic would ALLOW this edge

But from debug analysis, we know edge B-C creates INFEASIBLE Segment 1.

QUESTION: Should the filter be checking something different?
Options:
1. Check if bend points are within tab bounds (current implementation)
   - Would NOT filter transportschuh perpendicular edges
2. Check if bend points are within edge span (project onto edge direction)
   - Would check if bend aligns with the specific edge, not the full tab
3. Different interpretation of "within coordinate range"?

Please clarify what "within coordinate range" means geometrically.
""")

"""
Test projection-based filter: project points onto bend line and check if bend points
lie within the tab's projected range.
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
print("PROJECTION-BASED FILTER TEST")
print("="*80)

print(f"\nBend line:")
print(f"  Position: {bend.position}")
print(f"  Orientation: {bend.orientation}")

def project_point_onto_line(point, line_position, line_direction):
    """
    Project a point onto a line and return the parameter t.

    The line is defined as: L(t) = line_position + t * line_direction
    For a point P, its projection is at parameter:
        t = dot(P - line_position, line_direction)

    Returns:
        t: scalar parameter representing position along the line
    """
    vec_to_point = point - line_position
    t = np.dot(vec_to_point, line_direction)
    return t

def get_tab_projection_range(tab, bend):
    """
    Project all corners of a tab onto the bend line and return the range [t_min, t_max].
    """
    corners = [tab.points[k] for k in ['A', 'B', 'C', 'D']]
    t_values = [project_point_onto_line(corner, bend.position, bend.orientation)
                for corner in corners]
    return min(t_values), max(t_values)

def check_bend_points_in_range(BPL, BPR, tab, bend, tolerance=1e-3):
    """
    Check if both bend points lie within the tab's projected range on the bend line.

    Returns:
        (bpl_in_range, bpr_in_range, t_min, t_max, t_bpl, t_bpr)
    """
    # Get tab's projection range
    t_min, t_max = get_tab_projection_range(tab, bend)

    # Project bend points onto bend line
    t_bpl = project_point_onto_line(BPL, bend.position, bend.orientation)
    t_bpr = project_point_onto_line(BPR, bend.position, bend.orientation)

    # Check if in range (with tolerance)
    bpl_in_range = (t_min - tolerance) <= t_bpl <= (t_max + tolerance)
    bpr_in_range = (t_min - tolerance) <= t_bpr <= (t_max + tolerance)

    return bpl_in_range, bpr_in_range, t_min, t_max, t_bpl, t_bpr

# Test with known problematic edges
rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]
rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]

print("\n" + "="*80)
print("TAB 0 CORNER PROJECTIONS")
print("="*80)

t_min_0, t_max_0 = get_tab_projection_range(tab_0, bend)
print(f"\nTab 0 corners:")
for corner_id in ['A', 'B', 'C', 'D']:
    corner = tab_0.points[corner_id]
    t = project_point_onto_line(corner, bend.position, bend.orientation)
    print(f"  {corner_id}: {corner} -> t = {t:.3f}")

print(f"\nTab 0 projection range: t in [{t_min_0:.3f}, {t_max_0:.3f}]")

print("\n" + "="*80)
print("TAB 1 CORNER PROJECTIONS")
print("="*80)

t_min_1, t_max_1 = get_tab_projection_range(tab_1, bend)
print(f"\nTab 1 corners:")
for corner_id in ['A', 'B', 'C', 'D']:
    corner = tab_1.points[corner_id]
    t = project_point_onto_line(corner, bend.position, bend.orientation)
    print(f"  {corner_id}: {corner} -> t = {t:.3f}")

print(f"\nTab 1 projection range: t in [{t_min_1:.3f}, {t_max_1:.3f}]")

print("\n" + "="*80)
print("TESTING PERPENDICULAR EDGES WITH PROJECTION FILTER")
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
    print(f"TAB 0 EDGE {CP_xL_id}-{CP_xR_id} (Angle: {angle_x_deg:.1f}°, Perpendicular)")
    print(f"{'='*80}")

    for i, pair_z in enumerate(rect_z_edges):
        CP_zL_id, CP_zR_id = pair_z
        CP_zL = tab_1.points[CP_zL_id]
        CP_zR = tab_1.points[CP_zR_id]

        # Calculate bend points
        BPL = create_bending_point(CP_xL, CP_zL, bend)
        BPR = create_bending_point(CP_xR, CP_zR, bend)

        # Check with projection filter
        bpl_in_0, bpr_in_0, t_min_0, t_max_0, t_bpl, t_bpr = check_bend_points_in_range(
            BPL, BPR, tab_0, bend
        )

        print(f"\n  Paired with tab 1 edge {CP_zL_id}-{CP_zR_id}:")
        print(f"    BPL: {BPL}")
        print(f"    BPR: {BPR}")
        print(f"    Tab 0 projection range: t in [{t_min_0:.3f}, {t_max_0:.3f}]")
        print(f"    BPL projection: t = {t_bpl:.3f}")
        print(f"    BPR projection: t = {t_bpr:.3f}")
        print(f"    BPL in tab 0 range: {bpl_in_0}")
        print(f"    BPR in tab 0 range: {bpr_in_0}")

        # Filter decision
        if bpl_in_0 and bpr_in_0:
            decision = "FILTER OUT"
            reason = "both bend points within tab projection range"
        else:
            decision = "ALLOW"
            if not bpl_in_0 and not bpr_in_0:
                reason = "both bend points extend beyond tab projection range"
            else:
                reason = "one bend point extends beyond tab projection range"

        print(f"    DECISION: {decision} ({reason})")

        # Also check against tab 1 for comparison
        bpl_in_1, bpr_in_1, t_min_1, t_max_1, t_bpl_1, t_bpr_1 = check_bend_points_in_range(
            BPL, BPR, tab_1, bend
        )
        print(f"\n    Tab 1 projection range: t in [{t_min_1:.3f}, {t_max_1:.3f}]")
        print(f"    BPL in tab 1 range: {bpl_in_1}")
        print(f"    BPR in tab 1 range: {bpr_in_1}")

        if bpl_in_1 and bpr_in_1:
            print(f"    Would also filter based on tab 1")

print("\n" + "="*80)
print("VALIDATION: Should this filter work correctly?")
print("="*80)
print("""
Expected results:
1. Perpendicular edge B-C on tab_0 should be FILTERED
   - Known to create infeasible Segment 1
   - Bend points should project within tab_0's range

2. Parallel edges should NOT trigger the perpendicular check
   - Angle < 75° so filter doesn't apply

3. The projection filter should correctly identify when a bend is "local" to the tab
""")

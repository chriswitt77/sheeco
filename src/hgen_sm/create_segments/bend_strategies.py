import numpy as np
import itertools

from config.design_rules import min_flange_length, min_bend_angle
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane, calculate_plane_intersection, \
    create_bending_point, calculate_flange_points, next_cp
from src.hgen_sm.create_segments.utils import line_plane_intersection, project_onto_line, normalize, \
    perp_toward_plane
from src.hgen_sm.filters import min_flange_width_filter, tab_fully_contains_rectangle, lines_cross, \
    are_corners_neighbours, minimum_angle_filter, thin_segment_filter
from src.hgen_sm.data import Bend, Tab
from src.hgen_sm.create_segments.bend_strategies_zero_bend import zero_bends


def diagonals_cross_3d(p0, p3, p4, p7):
    """
    Check if diagonals (p3 to p4) and (p7 to p0) cross in any 2D projection.

    This is used to detect self-intersecting intermediate tab polygons.
    Returns True if the diagonals cross in XY, XZ, or YZ projection.
    """
    def segments_intersect_2d(a1, a2, b1, b2):
        """Check if line segment a1-a2 intersects with b1-b2 in 2D using parametric form."""
        # Direction vectors
        d1 = np.array([a2[0] - a1[0], a2[1] - a1[1]], dtype=float)
        d2 = np.array([b2[0] - b1[0], b2[1] - b1[1]], dtype=float)

        # Check for parallel lines
        cross = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(cross) < 1e-10:
            return False

        # Solve for parameters t and s
        diff = np.array([b1[0] - a1[0], b1[1] - a1[1]], dtype=float)
        t = (diff[0] * d2[1] - diff[1] * d2[0]) / cross
        s = (diff[0] * d1[1] - diff[1] * d1[0]) / cross

        # Check if intersection is within both segments (excluding endpoints)
        return 0.01 < t < 0.99 and 0.01 < s < 0.99

    p0, p3, p4, p7 = np.array(p0), np.array(p3), np.array(p4), np.array(p7)

    # Check XY projection (indices 0, 1)
    if segments_intersect_2d(p3[:2], p4[:2], p7[:2], p0[:2]):
        return True

    # Check XZ projection (indices 0, 2)
    if segments_intersect_2d([p3[0], p3[2]], [p4[0], p4[2]],
                              [p7[0], p7[2]], [p0[0], p0[2]]):
        return True

    # Check YZ projection (indices 1, 2)
    if segments_intersect_2d([p3[1], p3[2]], [p4[1], p4[2]],
                              [p7[1], p7[2]], [p0[1], p0[2]]):
        return True

    return False


def flange_extends_beyond_edge_range(CP_L, CP_R, FP_L, FP_R, tolerance_factor=1.05):
    """
    Check if flange points extend unreasonably far beyond the edge's span.

    This catches cases where the flange is inserted at the wrong location,
    causing flange points to project far outside the edge's natural range.
    For example, if an edge spans y=[0,35] but flange points are at y=[0,40],
    the flange extends 14% beyond the edge, indicating wrong insertion.

    Args:
        CP_L, CP_R: Corner points defining the edge
        FP_L, FP_R: Flange points for this edge
        tolerance_factor: How much extension is allowed (1.5 = 150% of edge length)

    Returns:
        True if flanges extend too far (should be filtered)
    """
    CP_L, CP_R = np.array(CP_L), np.array(CP_R)
    FP_L, FP_R = np.array(FP_L), np.array(FP_R)

    # Edge vector and length
    edge_vec = CP_R - CP_L
    edge_length = np.linalg.norm(edge_vec)

    if edge_length < 1e-6:
        return False  # Degenerate edge, can't check

    edge_dir = edge_vec / edge_length

    # Project FP points onto edge direction to see where they land relative to edge
    for FP, CP_name in [(FP_L, 'L'), (FP_R, 'R')]:
        vec_to_fp = FP - CP_L
        projection = np.dot(vec_to_fp, edge_dir)

        # Check if FP projects beyond edge endpoints by too much
        if projection < -edge_length * 0.5:  # Too far before start
            return True
        if projection > edge_length * tolerance_factor:  # Too far past end
            return True

    return False


def should_swap_z_side_ordering(FPyxL, FPyxR, FPyzR, FPyzL):
    """
    Determine if z-side L/R ordering should be swapped using hybrid approach.

    Combines diagonal crossing detection with distance-based fallback for
    collinear/degenerate cases where the diagonal crossing check fails.

    Args:
        FPyxL: Flange point on x-side, L orientation
        FPyxR: Flange point on x-side, R orientation
        FPyzR: Flange point on z-side, R orientation (default ordering)
        FPyzL: Flange point on z-side, L orientation (default ordering)

    Returns:
        bool: True if z-side ordering should be swapped (L before R)
    """
    # First try the diagonal crossing check
    crosses = diagonals_cross_3d(FPyxL, FPyxR, FPyzR, FPyzL)

    FPyxL = np.array(FPyxL)
    FPyxR = np.array(FPyxR)
    FPyzR = np.array(FPyzR)
    FPyzL = np.array(FPyzL)

    # Calculate distances for both orderings
    # Default ordering: R-to-R and L-to-L connections
    dist_default = (np.linalg.norm(FPyzR - FPyxR) +
                    np.linalg.norm(FPyxL - FPyzL))

    # Swapped ordering: R-to-L and L-to-R connections
    dist_swapped = (np.linalg.norm(FPyzL - FPyxR) +
                    np.linalg.norm(FPyxL - FPyzR))

    # If distance difference is significant (>1mm), use distance-based decision
    # This handles collinear cases where diagonal crossing check fails
    if abs(dist_default - dist_swapped) > 1.0:
        return dist_swapped < dist_default

    # Otherwise, trust the diagonal crossing check
    return crosses


def segments_are_equal(seg1, seg2, tolerance=1e-6):
    """
    Check if two segments are geometrically identical by comparing their tab points.

    Args:
        seg1, seg2: Segment objects to compare
        tolerance: Tolerance for point comparisons

    Returns:
        bool: True if segments are geometrically identical
    """
    # Compare all points from both segments
    points1 = []
    points2 = []

    for tab_key in seg1.tabs:
        for point_key, point in seg1.tabs[tab_key].points.items():
            if 'BP' in point_key or 'FP' in point_key:
                points1.append(np.array(point))

    for tab_key in seg2.tabs:
        for point_key, point in seg2.tabs[tab_key].points.items():
            if 'BP' in point_key or 'FP' in point_key:
                points2.append(np.array(point))

    if len(points1) != len(points2):
        return False

    # Check if all points from seg1 exist in seg2
    for p1 in points1:
        found = False
        for p2 in points2:
            if np.linalg.norm(p1 - p2) < tolerance:
                found = True
                break
        if not found:
            return False

    return True


def is_duplicate_segment(new_segment, segment_library, tolerance=1e-6):
    """Check if a segment already exists in the library."""
    for existing_segment in segment_library:
        if segments_are_equal(new_segment, existing_segment, tolerance):
            return True
    return False


def calculate_flange_points_with_angle_check(BP1, BP2, planeA, planeB, flange_length=min_flange_length):
    """
    Calculate flange points with minimum bend angle check.

    Returns:
        tuple: (FPAL, FPAR, FPBL, FPBR, angle_too_small)
        If angle is too small, returns (None, None, None, None, True)
    """
    # Check angle between planes
    dot_product = np.dot(planeA.orientation, planeB.orientation)
    dot_product = np.clip(dot_product, -1.0, 1.0)
    angle_rad = np.arccos(abs(dot_product))
    angle_deg = np.degrees(angle_rad)

    if angle_deg < min_bend_angle:
        return None, None, None, None, True

    # Calculate flange points
    BP0 = (BP1 + BP2) / 2.0
    bend_dir = normalize(BP2 - BP1)
    perpA = perp_toward_plane(planeA, BP0, bend_dir)
    perpB = perp_toward_plane(planeB, BP0, bend_dir)

    FPAL = BP1 + perpA * flange_length
    FPAR = BP2 + perpA * flange_length
    FPBL = BP1 + perpB * flange_length
    FPBR = BP2 + perpB * flange_length

    return FPAL, FPAR, FPBL, FPBR, False


def project_onto_bend_line(point, bend):
    """
    Project a point onto the bend line and return parameter t.

    The bend line is parameterized as: L(t) = bend.position + t * bend.orientation
    For a point P, its projection is at parameter:
        t = dot(P - bend.position, bend.orientation)

    Args:
        point: 3D point to project
        bend: Bend object with position and orientation

    Returns:
        t: scalar parameter representing position along the bend line
    """
    vec_to_point = point - bend.position
    t = np.dot(vec_to_point, bend.orientation)
    return t


def get_tab_projection_range(tab, bend):
    """
    Project all corners of a tab onto the bend line and return the range [t_min, t_max].

    Args:
        tab: Tab object with corner points
        bend: Bend object with position and orientation

    Returns:
        (t_min, t_max): Range of projection parameters for the tab's corners
    """
    corners = [tab.points[k] for k in ['A', 'B', 'C', 'D']]
    t_values = [project_onto_bend_line(corner, bend) for corner in corners]
    return min(t_values), max(t_values)


def one_bend(segment, filter_cfg):
    """
    Generate single-bend connections between two tabs.

    Logic follows the same pattern as two_bends:
    1. Define the bend line (from plane intersection)
    2. Project corner points onto bend line to get bending points (BP)
    3. Create flange points (FP) extending from BP toward each plane by min_flange_length
    4. Connection: Corner Point -> Flange Point -> Bending Point
    """
    tab_x = segment.tabs['tab_x']
    tab_x_id = tab_x.tab_id
    tab_z = segment.tabs['tab_z']
    tab_z_id = tab_z.tab_id

    rect_x = tab_x.rectangle
    rect_z = tab_z.rectangle

    plane_x = calculate_plane(rect_x)
    plane_z = calculate_plane(rect_z)
    intersection = calculate_plane_intersection(plane_x, plane_z)

    # ---- FILTER: If there is no intersection between the planes, no solution with one bend is possible
    if intersection is None:
        return None

    # ---- FILTER: Check if the resulting bend angle would be large enough
    if not minimum_angle_filter(plane_x, plane_z):
        return None

    bend = Bend(position=intersection["position"], orientation=intersection["orientation"])

    # Use adjacent edge pairs
    rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),
                    ('B', 'A'), ('C', 'B'), ('D', 'C'), ('A', 'D')]
    rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),
                    ('B', 'A'), ('C', 'B'), ('D', 'C'), ('A', 'D')]

    segment_library = []

    for pair_x in rect_x_edges:
        CP_xL_id = pair_x[0]
        CP_xL = tab_x.points[CP_xL_id]
        CP_xR_id = pair_x[1]
        CP_xR = tab_x.points[CP_xR_id]

        for pair_z in rect_z_edges:
            CP_zL_id = pair_z[0]
            CP_zL = tab_z.points[CP_zL_id]
            CP_zR_id = pair_z[1]
            CP_zR = tab_z.points[CP_zR_id]

            # ---- Step 1: Calculate Bending Points by projecting corner pairs onto bend line ----
            BPL = create_bending_point(CP_xL, CP_zL, bend)
            BPR = create_bending_point(CP_xR, CP_zR, bend)

            # ---- FILTER: Is flange wide enough? ----
            if not min_flange_width_filter(BPL=BPL, BPR=BPR):
                continue

            # ---- FILTER: Perpendicular edges with projection-based bounds check ----
            # Filter edges that are perpendicular to the bend line AND have bend points
            # within the tab's projected range (indicating a "local" infeasible connection)
            max_edge_to_bend_angle = filter_cfg.get('max_edge_to_bend_angle', 75)
            projection_tolerance = 1e-3

            # Check tab_x edge angle to bend line
            edge_x_vec = CP_xR - CP_xL
            edge_x_len = np.linalg.norm(edge_x_vec)
            if edge_x_len > 1e-9:
                edge_x_dir = edge_x_vec / edge_x_len
                dot_x = abs(np.dot(edge_x_dir, bend.orientation))
                angle_x_deg = np.degrees(np.arccos(np.clip(dot_x, 0, 1)))

                if angle_x_deg > max_edge_to_bend_angle:
                    # Edge is perpendicular - check if bend points are within tab's projection range
                    t_min_x, t_max_x = get_tab_projection_range(tab_x, bend)
                    t_bpl = project_onto_bend_line(BPL, bend)
                    t_bpr = project_onto_bend_line(BPR, bend)

                    bpl_in_range = (t_min_x - projection_tolerance) <= t_bpl <= (t_max_x + projection_tolerance)
                    bpr_in_range = (t_min_x - projection_tolerance) <= t_bpr <= (t_max_x + projection_tolerance)

                    if bpl_in_range and bpr_in_range:
                        continue  # Filter: perpendicular edge with local connection

            # Check tab_z edge angle to bend line
            edge_z_vec = CP_zR - CP_zL
            edge_z_len = np.linalg.norm(edge_z_vec)
            if edge_z_len > 1e-9:
                edge_z_dir = edge_z_vec / edge_z_len
                dot_z = abs(np.dot(edge_z_dir, bend.orientation))
                angle_z_deg = np.degrees(np.arccos(np.clip(dot_z, 0, 1)))

                if angle_z_deg > max_edge_to_bend_angle:
                    # Edge is perpendicular - check if bend points are within tab's projection range
                    t_min_z, t_max_z = get_tab_projection_range(tab_z, bend)
                    t_bpl = project_onto_bend_line(BPL, bend)
                    t_bpr = project_onto_bend_line(BPR, bend)

                    bpl_in_range = (t_min_z - projection_tolerance) <= t_bpl <= (t_max_z + projection_tolerance)
                    bpr_in_range = (t_min_z - projection_tolerance) <= t_bpr <= (t_max_z + projection_tolerance)

                    if bpl_in_range and bpr_in_range:
                        continue  # Filter: perpendicular edge with local connection

            # ---- Step 2: Calculate Flange Points perpendicular to bend line ----
            # FP extends from BP perpendicular to the bend line, toward each plane
            # This is the same calculation used in two_bends
            FPxL, FPxR, FPzL, FPzR, angle_too_small = calculate_flange_points_with_angle_check(
                BPL, BPR, planeA=plane_x, planeB=plane_z
            )
            if angle_too_small:
                continue

            # ---- FILTER: Check flange clearance ----
            # Verify that flange points are on the correct side of their respective planes
            # FPx should be on plane_x side, FPz should be on plane_z side
            # Calculate which side of the bend axis each FP is on
            dist_FPxL_to_plane_z = abs(np.dot(FPxL - plane_z.position, plane_z.orientation))
            dist_FPxR_to_plane_z = abs(np.dot(FPxR - plane_z.position, plane_z.orientation))
            dist_FPzL_to_plane_x = abs(np.dot(FPzL - plane_x.position, plane_x.orientation))
            dist_FPzR_to_plane_x = abs(np.dot(FPzR - plane_x.position, plane_x.orientation))

            # Flange points should maintain minimum clearance from opposite plane
            # This ensures the flange doesn't interfere with the opposite tab
            min_clearance = min_flange_length * 0.5  # Allow 50% of flange length as minimum clearance
            if (dist_FPxL_to_plane_z < min_clearance or dist_FPxR_to_plane_z < min_clearance or
                dist_FPzL_to_plane_x < min_clearance or dist_FPzR_to_plane_x < min_clearance):
                continue

            # ---- Determine L/R correspondence to avoid crossed connections ----
            # Check if bend point ordering matches edge ordering
            # For correct perimeter flow, the bend points should maintain the same
            # relative ordering as the edge corners they connect to

            # Get bend line direction (from BPL to BPR)
            bend_vec = BPR - BPL
            bend_len = np.linalg.norm(bend_vec)

            if bend_len > 1e-9:
                bend_dir = bend_vec / bend_len

                # For tab_z edge: check if edge direction aligns with bend direction
                edge_z_vec = CP_zR - CP_zL
                # Project edge vector onto bend direction
                # If positive: edge and bend point in same direction → L/R order is correct
                # If negative: edge and bend point in opposite directions → need to swap
                edge_z_proj = np.dot(edge_z_vec, bend_dir)

                # Determine if we need to swap L/R for tab_z
                fp_lines_cross = edge_z_proj < 0
            else:
                # Bend points coincide - fall back to distance check
                dist_xL_zL = np.linalg.norm(CP_xL - CP_zL)
                dist_xL_zR = np.linalg.norm(CP_xL - CP_zR)
                fp_lines_cross = dist_xL_zR < dist_xL_zL

            # ---- Update Segment.tabs ----
            new_segment = segment.copy()
            new_tab_x = new_segment.tabs['tab_x']
            new_tab_z = new_segment.tabs['tab_z']

            # ---- Insert Points in Tab x ----
            # Points go: Corner (CP) -> Flange (FP) -> Bend (BP)
            # CRITICAL: FP must use original corner coordinates, not calculated flange points
            # CRITICAL: Insert after the corner that comes LATER in the perimeter order
            # Perimeter flows: A → B → C → D → (back to A)
            corner_order = list(new_tab_x.points.keys())
            idx_L = corner_order.index(CP_xL_id)
            idx_R = corner_order.index(CP_xR_id)

            # Check for wrap-around edge (D→A case: idx_L=3, idx_R=0 or idx_L=0, idx_R=3)
            is_wraparound = (idx_L == 3 and idx_R == 0) or (idx_L == 0 and idx_R == 3)

            if is_wraparound:
                # Wrap-around edge (D→A or A→D)
                # Always insert after the corner with higher index (D = index 3)
                if idx_L == 3:  # Edge D→A (L=D, R=A)
                    # Insert after D, flow: [... C D] → FPL → BPL → BPR → FPR → [A B ...]
                    insert_after_id = CP_xL_id  # D
                    insert_after_val = CP_xL
                    bend_points_x = {
                        f"FP{tab_x_id}_{tab_z_id}L": FPxL,  # FP at min_flange_length from bend axis
                        f"BP{tab_x_id}_{tab_z_id}L": BPL,
                        f"BP{tab_x_id}_{tab_z_id}R": BPR,
                        f"FP{tab_x_id}_{tab_z_id}R": FPxR   # FP at min_flange_length from bend axis
                    }
                else:  # Edge A→D (L=A, R=D)
                    # Insert after D, flow: [... C D] → FPR → BPR → BPL → FPL → [A B ...]
                    insert_after_id = CP_xR_id  # D
                    insert_after_val = CP_xR
                    bend_points_x = {
                        f"FP{tab_x_id}_{tab_z_id}R": FPxR,  # FP at min_flange_length from bend axis
                        f"BP{tab_x_id}_{tab_z_id}R": BPR,
                        f"BP{tab_x_id}_{tab_z_id}L": BPL,
                        f"FP{tab_x_id}_{tab_z_id}L": FPxL   # FP at min_flange_length from bend axis
                    }
            elif idx_R > idx_L:
                # Normal case: R comes after L in perimeter (e.g., A→B, B→C, C→D)
                # Insert after L, flow: [... prev L] → FPL → BPL → BPR → FPR → [R next ...]
                insert_after_id = CP_xL_id  # Insert after L
                insert_after_val = CP_xL
                bend_points_x = {
                    f"FP{tab_x_id}_{tab_z_id}L": FPxL,  # FP at min_flange_length from bend axis
                    f"BP{tab_x_id}_{tab_z_id}L": BPL,
                    f"BP{tab_x_id}_{tab_z_id}R": BPR,
                    f"FP{tab_x_id}_{tab_z_id}R": FPxR   # FP at min_flange_length from bend axis
                }
            else:
                # Reverse case: L comes after R in perimeter (e.g., B→A, C→B, D→C)
                # Insert after R, flow: [... prev R] → FPR → BPR → BPL → FPL → [L next ...]
                insert_after_id = CP_xR_id  # Insert after R
                insert_after_val = CP_xR
                bend_points_x = {
                    f"FP{tab_x_id}_{tab_z_id}R": FPxR,  # FP at min_flange_length from bend axis
                    f"BP{tab_x_id}_{tab_z_id}R": BPR,
                    f"BP{tab_x_id}_{tab_z_id}L": BPL,
                    f"FP{tab_x_id}_{tab_z_id}L": FPxL   # FP at min_flange_length from bend axis
                }

            new_tab_x.insert_points(L={insert_after_id: insert_after_val}, add_points=bend_points_x)

            # NOTE: Corners are kept (tab is augmented, not trimmed)
            # according to Direct Power Flows specification

            # ---- Insert Points in Tab z ----
            # CRITICAL: FP must use original corner coordinates
            # CRITICAL: Insert after the corner that comes LATER in perimeter order
            # CRITICAL: Handle crossing (when connection lines would cross)
            corner_order_z = list(new_tab_z.points.keys())
            idx_zL = corner_order_z.index(CP_zL_id)
            idx_zR = corner_order_z.index(CP_zR_id)

            # Check for wrap-around edge
            is_wraparound_z = (idx_zL == 3 and idx_zR == 0) or (idx_zL == 0 and idx_zR == 3)

            # Determine insertion point and order based on perimeter flow
            if is_wraparound_z:
                # Wrap-around edge (D→A or A→D)
                if idx_zL == 3:  # Edge D→A (L=D, R=A)
                    insert_after_z_id = CP_zL_id  # Insert after D
                    insert_after_z_val = CP_zL
                    base_order = "L_to_R"  # Base: FPL → BPL → BPR → FPR
                else:  # Edge A→D (L=A, R=D)
                    insert_after_z_id = CP_zR_id  # Insert after D
                    insert_after_z_val = CP_zR
                    base_order = "R_to_L"  # Base: FPR → BPR → BPL → FPL
            elif idx_zR > idx_zL:
                # Normal case: R comes after L (e.g., A→B, B→C, C→D)
                # CRITICAL FIX: Insert after L (FIRST corner), NOT R
                # Bend should be BETWEEN L and R: ... → L → [bend] → R → ...
                insert_after_z_id = CP_zL_id  # FIXED: was CP_zR_id
                insert_after_z_val = CP_zL
                base_order = "L_to_R"  # FIXED: was "R_to_L"
            else:
                # Reverse case: L comes after R (e.g., B→A, C→B, D→C)
                # Insert after R (FIRST corner in edge direction)
                # Bend goes from R to L: ... → R → [bend] → L → ...
                insert_after_z_id = CP_zR_id  # FIXED: was CP_zL_id
                insert_after_z_val = CP_zR
                base_order = "R_to_L"  # FIXED: was "L_to_R"

            # Apply crossing adjustment: if connection lines cross, swap L/R
            if fp_lines_cross:
                # Connection lines cross - swap L/R in the base order
                if base_order == "L_to_R":
                    base_order = "R_to_L"
                else:
                    base_order = "L_to_R"

            # Generate final point ordering using calculated flange points (FPzL, FPzR)
            if base_order == "L_to_R":
                bend_points_z = {
                    f"FP{tab_z_id}_{tab_x_id}L": FPzL,  # FP at min_flange_length from bend axis
                    f"BP{tab_z_id}_{tab_x_id}L": BPL,
                    f"BP{tab_z_id}_{tab_x_id}R": BPR,
                    f"FP{tab_z_id}_{tab_x_id}R": FPzR   # FP at min_flange_length from bend axis
                }
            else:  # R_to_L
                bend_points_z = {
                    f"FP{tab_z_id}_{tab_x_id}R": FPzR,  # FP at min_flange_length from bend axis
                    f"BP{tab_z_id}_{tab_x_id}R": BPR,
                    f"BP{tab_z_id}_{tab_x_id}L": BPL,
                    f"FP{tab_z_id}_{tab_x_id}L": FPzL   # FP at min_flange_length from bend axis
                }

            new_tab_z.insert_points(L={insert_after_z_id: insert_after_z_val}, add_points=bend_points_z)

            # NOTE: Corners are kept (tab is augmented, not trimmed)
            # according to Direct Power Flows specification

            # ---- FILTER: Do Tabs cover Rects fully? ----
            if not tab_fully_contains_rectangle(new_tab_x, rect_x):
                continue
            if not tab_fully_contains_rectangle(new_tab_z, rect_z):
                continue

            # ---- FILTER: Check for duplicates ----
            if is_duplicate_segment(new_segment, segment_library):
                continue

            # ---- Update New Segment with New Tabs and add to Stack
            new_segment.tabs['tab_x'] = new_tab_x
            new_segment.tabs['tab_z'] = new_tab_z
            segment_library.append(new_segment)

    return segment_library


def two_bends(segment, segment_cfg, filter_cfg):
    """
    Generate double-bend connections between two tabs (A ↔ C) via intermediate plane B.

    Strategy:
    1. APPROACH 1 (90-degree priority): Try to create plane B perpendicular to both A and C
       - Shifts edges outward to form plane B at 90° to both planes
       - Produces cleaner, more manufacturable bends
    2. APPROACH 2 (fallback): Corner point connection
       - Uses existing corner-based logic when 90° approach isn't possible
       - Skipped if prioritize_perpendicular_bends=True and approach 1 succeeded

    Both tabs get flange areas so bending lines lie outside initial tab geometries.
    """
    tab_x = segment.tabs['tab_x']
    tab_z = segment.tabs['tab_z']
    tab_x_id = tab_x.tab_id
    tab_z_id = tab_z.tab_id

    rect_x = tab_x.rectangle
    rect_z = tab_z.rectangle

    plane_x = calculate_plane(rect_x)
    plane_z = calculate_plane(rect_z)

    # Edge combinations for both rectangles
    rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),
                    ('B', 'A'), ('C', 'B'), ('D', 'C'), ('A', 'D')]
    rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),
                    ('B', 'A'), ('C', 'B'), ('D', 'C'), ('A', 'D')]

    segment_library = []

    # Track which edge pairs succeeded in approach 1 (for prioritization)
    successful_edge_pairs = set()  # Set of (pair_x, pair_z) tuples

    # Calculate centroids for direction checks
    rect_x_corners = [tab_x.points[k] for k in ['A', 'B', 'C', 'D']]
    rect_z_corners = [tab_z.points[k] for k in ['A', 'B', 'C', 'D']]
    rect_x_center = np.mean(rect_x_corners, axis=0)
    rect_z_center = np.mean(rect_z_corners, axis=0)

    # ========== APPROACH 1: 90-DEGREE PERPENDICULAR PLANE B ==========
    for pair_x in rect_x_edges:
        CPxL_id, CPxR_id = pair_x
        CPxL = tab_x.points[CPxL_id]
        CPxR = tab_x.points[CPxR_id]
        edge_x_vec = CPxR - CPxL
        edge_x_mid = (CPxL + CPxR) / 2

        for pair_z in rect_z_edges:
            CPzL_id, CPzR_id = pair_z
            CPzL = tab_z.points[CPzL_id]
            CPzR = tab_z.points[CPzR_id]
            edge_z_vec = CPzR - CPzL
            edge_z_mid = (CPzL + CPzR) / 2

            # Calculate normal for intermediate plane B (perpendicular to both A and C)
            normal_B = np.cross(plane_x.orientation, plane_z.orientation)

            if np.linalg.norm(normal_B) < 1e-6:
                # Planes are parallel - use edge direction to construct intermediate plane normal
                # For parallel planes, intermediate plane must be perpendicular to both planes
                # Cross product of plane normal with edge vector gives perpendicular direction
                normal_B = np.cross(plane_x.orientation, edge_x_vec)

                if np.linalg.norm(normal_B) < 1e-6:
                    # Edge is parallel to plane normal (rare edge case)
                    # Try using edge_z instead
                    normal_B = np.cross(plane_z.orientation, edge_z_vec)

                    if np.linalg.norm(normal_B) < 1e-6:
                        # Both edges parallel to plane normal - skip this combination
                        continue

            normal_B = normalize(normal_B)

            # Calculate outward directions for both edges
            out_dir_x = np.cross(edge_x_vec, plane_x.orientation)
            out_dir_x = normalize(out_dir_x)
            if np.dot(out_dir_x, edge_x_mid - rect_x_center) < 0:
                out_dir_x = -out_dir_x

            out_dir_z = np.cross(edge_z_vec, plane_z.orientation)
            out_dir_z = normalize(out_dir_z)
            if np.dot(out_dir_z, edge_z_mid - rect_z_center) < 0:
                out_dir_z = -out_dir_z

            # Connection vector between edge midpoints
            connection_vec = edge_z_mid - edge_x_mid
            dist_along_normal_B = np.dot(connection_vec, normal_B)

            # Check if edges are growing outward (toward each other)
            is_x_growing = np.dot(out_dir_x, connection_vec) > 0
            is_z_growing = np.dot(out_dir_z, -connection_vec) > 0

            if not is_x_growing and not is_z_growing:
                continue  # Both would shrink, skip

            # Shift distances
            if is_x_growing:
                shift_dist_x = abs(dist_along_normal_B) + min_flange_length
                shift_dist_z = min_flange_length
            else:
                shift_dist_x = min_flange_length
                shift_dist_z = abs(dist_along_normal_B) + min_flange_length

            # Shifted bending points
            BPxL = CPxL + out_dir_x * shift_dist_x
            BPxR = CPxR + out_dir_x * shift_dist_x
            BPzL = CPzL + out_dir_z * shift_dist_z
            BPzR = CPzR + out_dir_z * shift_dist_z

            # Create plane B from shifted points
            BP_triangle = {"A": BPxL, "B": BPxR, "C": BPzL}
            plane_y = calculate_plane(triangle=BP_triangle)

            # Check if plane B is perpendicular to both A and C (within 5 degrees)
            angle_tolerance = np.radians(5)
            dot_BA = abs(np.dot(plane_y.orientation, plane_x.orientation))
            angle_BA = np.arccos(np.clip(dot_BA, 0, 1))
            is_perp_to_x = abs(angle_BA - np.pi / 2) < angle_tolerance

            dot_BC = abs(np.dot(plane_y.orientation, plane_z.orientation))
            angle_BC = np.arccos(np.clip(dot_BC, 0, 1))
            is_perp_to_z = abs(angle_BC - np.pi / 2) < angle_tolerance

            if not (is_perp_to_x and is_perp_to_z):
                continue  # Not perpendicular, will try in fallback approach

            # ---- FILTER: Minimum flange width ----
            if not min_flange_width_filter(BPL=BPxL, BPR=BPxR):
                continue
            if not min_flange_width_filter(BPL=BPzL, BPR=BPzR):
                continue

            # ---- FILTER: Minimum bend angle ----
            if filter_cfg.get('Min Bend Angle', True):
                if not minimum_angle_filter(plane_x, plane_y):
                    continue
                if not minimum_angle_filter(plane_y, plane_z):
                    continue

            # Calculate flange points with angle checks
            FPxyL, FPxyR, FPyxL, FPyxR, angle_check_xy = calculate_flange_points_with_angle_check(
                BPxL, BPxR, plane_x, plane_y
            )
            if angle_check_xy:
                continue

            FPyzL, FPyzR, FPzyL, FPzyR, angle_check_yz = calculate_flange_points_with_angle_check(
                BPzL, BPzR, plane_y, plane_z
            )
            if angle_check_yz:
                continue

            # Correct point ordering to prevent crossovers
            dist_xL_zL = np.linalg.norm(BPxL - BPzL)
            dist_xL_zR = np.linalg.norm(BPxL - BPzR)
            z_swapped = dist_xL_zR < dist_xL_zL
            if z_swapped:
                BPzL, BPzR = BPzR, BPzL
                FPyzL, FPyzR = FPyzR, FPyzL
                FPzyL, FPzyR = FPzyR, FPzyL
                # Also swap corner correspondence for z-side
                CPzL, CPzR = CPzR, CPzL

            # ---- FILTER: Check if flanges extend too far beyond edge range ----
            if flange_extends_beyond_edge_range(CPxL, CPxR, FPxyL, FPxyR):
                continue
            if flange_extends_beyond_edge_range(CPzL, CPzR, FPzyL, FPzyR):
                continue

            # Create new segment
            new_segment = segment.copy()
            new_tab_x = new_segment.tabs['tab_x']
            new_tab_z = new_segment.tabs['tab_z']

            tab_y_id = f"{tab_x_id}{tab_z_id}"
            new_tab_y = Tab(tab_id=tab_y_id, points={"A": BPxL, "B": BPxR, "C": BPzL})

            # Insert points in Tab x (with flange)
            # Use corner points for FP to ensure proper connection to original tab
            # CRITICAL: Insert after the corner that comes LATER in the perimeter order
            corner_order_x = list(new_tab_x.points.keys())
            idx_xL = corner_order_x.index(CPxL_id)
            idx_xR = corner_order_x.index(CPxR_id)

            # Check for wrap-around edge
            is_wraparound_x = (idx_xL == 3 and idx_xR == 0) or (idx_xL == 0 and idx_xR == 3)

            if is_wraparound_x:
                # Wrap-around edge (D→A or A→D)
                if idx_xL == 3:  # Edge D→A (L=D, R=A)
                    insert_after_x_id = CPxL_id  # Insert after D
                    insert_after_x_val = CPxL
                    bend_points_x = {
                        f"FP{tab_x_id}_{tab_y_id}L": CPxL,  # FP at D
                        f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                        f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                        f"FP{tab_x_id}_{tab_y_id}R": CPxR   # FP at A
                    }
                else:  # Edge A→D (L=A, R=D)
                    insert_after_x_id = CPxR_id  # Insert after D
                    insert_after_x_val = CPxR
                    bend_points_x = {
                        f"FP{tab_x_id}_{tab_y_id}R": CPxR,  # FP at D
                        f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                        f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                        f"FP{tab_x_id}_{tab_y_id}L": CPxL   # FP at A
                    }
            elif idx_xR > idx_xL:
                # Normal case: R comes after L (e.g., A→B, B→C, C→D)
                # CRITICAL FIX: Insert after L (FIRST corner), NOT R
                insert_after_x_id = CPxL_id  # FIXED
                insert_after_x_val = CPxL
                bend_points_x = {
                    f"FP{tab_x_id}_{tab_y_id}L": CPxL,
                    f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                    f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                    f"FP{tab_x_id}_{tab_y_id}R": CPxR
                }
            else:
                # Reverse case: L comes after R (e.g., B→A, C→B, D→C)
                # Insert after R (FIRST corner in edge direction)
                insert_after_x_id = CPxR_id  # FIXED
                insert_after_x_val = CPxR
                bend_points_x = {
                    f"FP{tab_x_id}_{tab_y_id}R": CPxR,
                    f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                    f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                    f"FP{tab_x_id}_{tab_y_id}L": CPxL
                }

            # CRITICAL FIX: Remove FP points that duplicate existing corners
            # This prevents points at the same position from being inserted out of order
            corners_coords = {k: v for k, v in new_tab_x.points.items() if k in ['A', 'B', 'C', 'D']}
            fp_points_to_remove = []

            for fp_name, fp_coord in list(bend_points_x.items()):
                if 'FP' in fp_name:  # Only check Flange Points
                    for corner_name, corner_coord in corners_coords.items():
                        if np.allclose(fp_coord, corner_coord, atol=1e-6):
                            fp_points_to_remove.append(fp_name)
                            break

            for fp_name in fp_points_to_remove:
                del bend_points_x[fp_name]

            new_tab_x.insert_points(L={insert_after_x_id: insert_after_x_val}, add_points=bend_points_x)

            # Insert points in Tab y - IMPORTANT: Order must trace proper perimeter
            # Determine correct z-side ordering using hybrid approach
            # (diagonal crossing check + distance-based fallback for collinear cases)
            # Default ordering: FPyxL -> ... -> FPyxR -> FPyzR -> ... -> FPyzL -> back to FPyxL
            # If swap is needed, use: FPyxL -> ... -> FPyxR -> FPyzL -> ... -> FPyzR -> back to FPyxL
            if should_swap_z_side_ordering(FPyxL, FPyxR, FPyzR, FPyzL):
                # Diagonals cross - swap z-side ordering (L↔R)
                bend_points_y = {
                    f"FP{tab_y_id}_{tab_x_id}L": FPyxL,
                    f"BP{tab_y_id}_{tab_x_id}L": BPxL,
                    f"BP{tab_y_id}_{tab_x_id}R": BPxR,
                    f"FP{tab_y_id}_{tab_x_id}R": FPyxR,
                    f"FP{tab_y_id}_{tab_z_id}L": FPyzL,      # swapped
                    f"BP{tab_y_id}_{tab_z_id}L": BPzL,       # swapped
                    f"BP{tab_y_id}_{tab_z_id}R": BPzR,       # swapped
                    f"FP{tab_y_id}_{tab_z_id}R": FPyzR       # swapped
                }
            else:
                bend_points_y = {
                    f"FP{tab_y_id}_{tab_x_id}L": FPyxL,
                    f"BP{tab_y_id}_{tab_x_id}L": BPxL,
                    f"BP{tab_y_id}_{tab_x_id}R": BPxR,
                    f"FP{tab_y_id}_{tab_x_id}R": FPyxR,
                    f"FP{tab_y_id}_{tab_z_id}R": FPyzR,
                    f"BP{tab_y_id}_{tab_z_id}R": BPzR,
                    f"BP{tab_y_id}_{tab_z_id}L": BPzL,
                    f"FP{tab_y_id}_{tab_z_id}L": FPyzL
                }
            new_tab_y.points = bend_points_y

            # Insert points in Tab z (with flange)
            # Use calculated FP (FPzyL/FPzyR in tab_z's plane, already swapped if z_swapped)
            # CRITICAL: Insert after the corner that comes LATER in the perimeter order
            # Use original corner IDs before any swapping
            orig_CPzL_id = CPzR_id if z_swapped else CPzL_id
            orig_CPzR_id = CPzL_id if z_swapped else CPzR_id

            corner_order_z = list(new_tab_z.points.keys())
            idx_zL = corner_order_z.index(orig_CPzL_id)
            idx_zR = corner_order_z.index(orig_CPzR_id)

            # Check for wrap-around edge (using original indices)
            is_wraparound_z_90 = (idx_zL == 3 and idx_zR == 0) or (idx_zL == 0 and idx_zR == 3)

            if is_wraparound_z_90:
                # Wrap-around edge (D→A or A→D)
                if idx_zL == 3:  # Edge D→A (L=D, R=A)
                    insert_corner_id = orig_CPzL_id  # Insert after D
                    insert_corner_val = tab_z.points[insert_corner_id]
                    bend_points_z = {
                        f"FP{tab_z_id}_{tab_y_id}L": FPzyL,
                        f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                        f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                        f"FP{tab_z_id}_{tab_y_id}R": FPzyR
                    }
                else:  # Edge A→D (L=A, R=D)
                    insert_corner_id = orig_CPzR_id  # Insert after D
                    insert_corner_val = tab_z.points[insert_corner_id]
                    bend_points_z = {
                        f"FP{tab_z_id}_{tab_y_id}R": FPzyR,
                        f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                        f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                        f"FP{tab_z_id}_{tab_y_id}L": FPzyL
                    }
            elif idx_zR > idx_zL:
                # Normal case: R comes after L (e.g., A→B, B→C, C→D)
                # CRITICAL FIX: Insert after L (FIRST corner), NOT R
                insert_corner_id = orig_CPzL_id  # FIXED
                insert_corner_val = tab_z.points[insert_corner_id]
                bend_points_z = {
                    f"FP{tab_z_id}_{tab_y_id}L": FPzyL,
                    f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                    f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                    f"FP{tab_z_id}_{tab_y_id}R": FPzyR
                }
            else:
                # Reverse case: L comes after R (e.g., B→A, C→B, D→C)
                # Insert after R (FIRST corner in edge direction)
                insert_corner_id = orig_CPzR_id  # FIXED
                insert_corner_val = tab_z.points[insert_corner_id]
                bend_points_z = {
                    f"FP{tab_z_id}_{tab_y_id}R": FPzyR,
                    f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                    f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                    f"FP{tab_z_id}_{tab_y_id}L": FPzyL
                }

            # CRITICAL FIX: Remove FP points that duplicate existing corners
            # This prevents points at the same position from being inserted out of order
            corners_coords_z = {k: v for k, v in new_tab_z.points.items() if k in ['A', 'B', 'C', 'D']}
            fp_points_to_remove_z = []

            for fp_name, fp_coord in list(bend_points_z.items()):
                if 'FP' in fp_name:  # Only check Flange Points
                    for corner_name, corner_coord in corners_coords_z.items():
                        if np.allclose(fp_coord, corner_coord, atol=1e-6):
                            fp_points_to_remove_z.append(fp_name)
                            break

            for fp_name in fp_points_to_remove_z:
                del bend_points_z[fp_name]

            new_tab_z.insert_points(L={insert_corner_id: insert_corner_val}, add_points=bend_points_z)

            # ---- FILTER: Check for duplicates ----
            new_segment.tabs = {'tab_x': new_tab_x, 'tab_y': new_tab_y, 'tab_z': new_tab_z}
            if is_duplicate_segment(new_segment, segment_library):
                continue

            segment_library.append(new_segment)
            # Track this edge pair as successful for approach 1
            successful_edge_pairs.add((pair_x, pair_z))

    # Determine if we should skip approach 2 for edge pairs that succeeded in approach 1
    prioritize_perpendicular = segment_cfg.get('prioritize_perpendicular_bends', True)

    # ========== APPROACH 2A: CORNER CONNECTION (NON-PARALLEL, WITH CORNER REMOVAL) ==========
    for pair_x in rect_x_edges:
        CPxL_id = pair_x[0]
        CPxR_id = pair_x[1]
        CPxL = tab_x.points[CPxL_id]
        CPxR = tab_x.points[CPxR_id]

        # Calculate outward direction for tab_x
        edge_x_vec = CPxR - CPxL
        edge_x_mid = (CPxL + CPxR) / 2
        out_dir_x = np.cross(edge_x_vec, plane_x.orientation)
        out_dir_x = normalize(out_dir_x)
        if np.dot(out_dir_x, edge_x_mid - rect_x_center) < 0:
            out_dir_x = -out_dir_x

        # Shift tab_x edge outward to create flange
        BPxL = CPxL + out_dir_x * min_flange_length
        BPxR = CPxR + out_dir_x * min_flange_length

        # Iterate over corners for projection-based connection
        for i, CPzM_id in enumerate(rect_z.points):
            CPzM = rect_z.points[CPzM_id]
            CPzL_id = list(rect_z.points.keys())[(i - 1) % 4]
            CPzR_id = list(rect_z.points.keys())[(i + 1) % 4]
            CPzL = rect_z.points[CPzL_id]
            CPzR = rect_z.points[CPzR_id]

            # ---- FILTER: Is flange wide enough? ----
            if not min_flange_width_filter(BPL=BPxL, BPR=BPxR):
                continue

            new_segment = segment.copy()
            new_tab_x = new_segment.tabs['tab_x']
            new_tab_z = new_segment.tabs['tab_z']

            bend_xy = Bend(position=BPxL, orientation=BPxR - BPxL, BPL=BPxL, BPR=BPxR)

            # Determine BPzM using projection logic
            projection_point = line_plane_intersection(BPxL, BPxL - BPxR, plane_z.position, plane_z.orientation)

            if projection_point is not None:
                vec_PP_CP = CPzM - projection_point
                c = np.linalg.norm(vec_PP_CP)
                a = min_flange_length

                if c <= a:
                    projection_point = None
                else:
                    b = np.sqrt(c ** 2 - a ** 2)
                    d = (b ** 2 - a ** 2 + c ** 2) / (2 * c)
                    h = np.sqrt(max(0, b ** 2 - d ** 2))

                    u = vec_PP_CP / c
                    v = np.cross(u, plane_z.orientation)
                    v_norm = np.linalg.norm(v)
                    if v_norm > 1e-9:
                        v /= v_norm
                    else:
                        v = np.array([0, 0, 1])

                    sol1 = projection_point + d * u + h * v
                    sol2 = projection_point + d * u - h * v

                    if np.linalg.norm(sol1 - rect_z_center) >= np.linalg.norm(sol2 - rect_z_center):
                        BPzM = sol1
                    else:
                        BPzM = sol2

                    bend_yz_ori = BPzM - projection_point
                    bend_yz_ori_norm = np.linalg.norm(bend_yz_ori)
                    if bend_yz_ori_norm > 1e-9:
                        bend_yz_ori /= bend_yz_ori_norm
                    bend_yz = Bend(position=projection_point, orientation=bend_yz_ori)

                    new_tab_z.remove_point(point={CPzM_id: CPzM})

            if projection_point is None:
                # Skip parallel case - handled in Approach 2B
                continue

            BPzL = project_onto_line(CPzL, bend_yz.position, bend_yz.orientation)
            BPzR = project_onto_line(CPzR, bend_yz.position, bend_yz.orientation)

            BP_triangle = {"A": BPxL, "B": BPxR, "C": BPzM}
            plane_y = calculate_plane(triangle=BP_triangle)

            tab_y_id = f"{tab_x_id}{tab_z_id}"
            new_tab_y = Tab(tab_id=tab_y_id, points=BP_triangle)

            # ---- FILTER: Minimum bend angle ----
            if filter_cfg.get('Min Bend Angle', True):
                if not minimum_angle_filter(plane_x, plane_y):
                    continue
                if not minimum_angle_filter(plane_y, plane_z):
                    continue

            # Calculate flange points with angle checks
            FPxyL, FPxyR, FPyxL, FPyxR, angle_check_xy = calculate_flange_points_with_angle_check(
                BPxL, BPxR, plane_x, plane_y
            )
            if angle_check_xy:
                continue

            # ---- FILTER: Is flange wide enough? ----
            if not min_flange_width_filter(BPL=BPzL, BPR=BPzR):
                continue

            FPyzL, FPyzR, FPzyL, FPzyR, angle_check_yz = calculate_flange_points_with_angle_check(
                BPzL, BPzR, plane_y, plane_z
            )
            if angle_check_yz:
                continue

            # ---- FILTER: Check if flanges extend too far beyond edge range ----
            if flange_extends_beyond_edge_range(CPxL, CPxR, FPxyL, FPxyR):
                continue
            if flange_extends_beyond_edge_range(CPzL, CPzR, FPzyL, FPzyR):
                continue

            # Insert points in Tab x (with flange)
            # Use corner points for FP to ensure proper connection
            # CRITICAL: Insert after the corner that comes LATER in the perimeter order
            corner_order_x_fb = list(new_tab_x.points.keys())
            idx_xL_fb = corner_order_x_fb.index(CPxL_id)
            idx_xR_fb = corner_order_x_fb.index(CPxR_id)

            # Check for wrap-around edge
            is_wraparound_x_fb = (idx_xL_fb == 3 and idx_xR_fb == 0) or (idx_xL_fb == 0 and idx_xR_fb == 3)

            if is_wraparound_x_fb:
                # Wrap-around edge (D→A or A→D)
                if idx_xL_fb == 3:  # Edge D→A (L=D, R=A)
                    insert_after_x_fb_id = CPxL_id  # Insert after D
                    insert_after_x_fb_val = CPxL
                    bend_points_x = {
                        f"FP{tab_x_id}_{tab_y_id}L": CPxL,  # FP at D
                        f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                        f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                        f"FP{tab_x_id}_{tab_y_id}R": CPxR   # FP at A
                    }
                else:  # Edge A→D (L=A, R=D)
                    insert_after_x_fb_id = CPxR_id  # Insert after D
                    insert_after_x_fb_val = CPxR
                    bend_points_x = {
                        f"FP{tab_x_id}_{tab_y_id}R": CPxR,  # FP at D
                        f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                        f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                        f"FP{tab_x_id}_{tab_y_id}L": CPxL   # FP at A
                    }
            elif idx_xR_fb > idx_xL_fb:
                # Normal case: R comes after L (e.g., A→B, B→C, C→D)
                # CRITICAL FIX: Insert after L (FIRST corner), NOT R
                insert_after_x_fb_id = CPxL_id  # FIXED
                insert_after_x_fb_val = CPxL
                bend_points_x = {
                    f"FP{tab_x_id}_{tab_y_id}L": CPxL,
                    f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                    f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                    f"FP{tab_x_id}_{tab_y_id}R": CPxR
                }
            else:
                # Reverse case: L comes after R (e.g., B→A, C→B, D→C)
                # Insert after R (FIRST corner in edge direction)
                insert_after_x_fb_id = CPxR_id  # FIXED
                insert_after_x_fb_val = CPxR
                bend_points_x = {
                    f"FP{tab_x_id}_{tab_y_id}R": CPxR,
                    f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                    f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                    f"FP{tab_x_id}_{tab_y_id}L": CPxL
                }

            # CRITICAL FIX: Remove FP points that duplicate existing corners (Approach 2A)
            corners_coords_a2 = {k: v for k, v in new_tab_x.points.items() if k in ['A', 'B', 'C', 'D']}
            fp_points_to_remove_a2 = []

            for fp_name, fp_coord in list(bend_points_x.items()):
                if 'FP' in fp_name:
                    for corner_name, corner_coord in corners_coords_a2.items():
                        if np.allclose(fp_coord, corner_coord, atol=1e-6):
                            fp_points_to_remove_a2.append(fp_name)
                            break

            for fp_name in fp_points_to_remove_a2:
                del bend_points_x[fp_name]

            # print(f"    -> Inserting after {insert_after_x_fb_id}, idx_xL={idx_xL_fb}, idx_xR={idx_xR_fb}, bend_points: {list(bend_points_x.keys())}")
            new_tab_x.insert_points(L={insert_after_x_fb_id: insert_after_x_fb_val}, add_points=bend_points_x)

            # Insert points in Tab y - IMPORTANT: Order must trace proper perimeter
            # Determine correct z-side ordering using hybrid approach
            # (diagonal crossing check + distance-based fallback for collinear cases)
            # Default ordering: FPyxL -> ... -> FPyxR -> FPyzR -> ... -> FPyzL -> back to FPyxL
            # If swap is needed, use: FPyxL -> ... -> FPyxR -> FPyzL -> ... -> FPyzR -> back to FPyxL
            if should_swap_z_side_ordering(FPyxL, FPyxR, FPyzR, FPyzL):
                # Diagonals cross - swap z-side ordering (L↔R)
                bend_points_y = {
                    f"FP{tab_y_id}_{tab_x_id}L": FPyxL,
                    f"BP{tab_y_id}_{tab_x_id}L": BPxL,
                    f"BP{tab_y_id}_{tab_x_id}R": BPxR,
                    f"FP{tab_y_id}_{tab_x_id}R": FPyxR,
                    f"FP{tab_y_id}_{tab_z_id}L": FPyzL,      # swapped
                    f"BP{tab_y_id}_{tab_z_id}L": BPzL,       # swapped
                    f"BP{tab_y_id}_{tab_z_id}R": BPzR,       # swapped
                    f"FP{tab_y_id}_{tab_z_id}R": FPyzR       # swapped
                }
            else:
                bend_points_y = {
                    f"FP{tab_y_id}_{tab_x_id}L": FPyxL,
                    f"BP{tab_y_id}_{tab_x_id}L": BPxL,
                    f"BP{tab_y_id}_{tab_x_id}R": BPxR,
                    f"FP{tab_y_id}_{tab_x_id}R": FPyxR,
                    f"FP{tab_y_id}_{tab_z_id}R": FPyzR,
                    f"BP{tab_y_id}_{tab_z_id}R": BPzR,
                    f"BP{tab_y_id}_{tab_z_id}L": BPzL,
                    f"FP{tab_y_id}_{tab_z_id}L": FPyzL
                }
            new_tab_y.points = bend_points_y

            # Insert points in Tab z - use calculated FP (FPzyL, FPzyR in tab_z's plane)
            # CRITICAL: Insert after the corner that comes LATER in the perimeter order
            # CRITICAL: Handle crossing (when connection lines would cross)
            corner_order_z_fb = list(new_tab_z.points.keys())

            # Determine base point ordering based on perimeter flow
            idx_zL_fb = corner_order_z_fb.index(CPzL_id)
            idx_zR_fb = corner_order_z_fb.index(CPzR_id)

            # Check for wrap-around edge
            # Wrap-around occurs when indices are not adjacent (gap > 1)
            # Examples: D->B (idx 3->1), C->A (idx 2->0), D->A (idx 3->0)
            is_wraparound_z_fb = abs(idx_zL_fb - idx_zR_fb) > 1

            # Determine insertion point and base order
            if is_wraparound_z_fb:
                # Wrap-around edge: indices not adjacent (e.g., D->B, C->A, D->A)
                # Always insert after the corner with HIGHER index (before wrap point)
                if idx_zL_fb > idx_zR_fb:
                    # L has higher index (e.g., D->B: idx 3->1, C->A: idx 2->0)
                    insert_z_id = CPzL_id  # Insert after L (higher index)
                    insert_z_val = CPzL
                    base_order_fb = "L_to_R"  # Path: L -> [bend] -> R
                else:
                    # R has higher index (e.g., B->D: idx 1->3, A->C: idx 0->2)
                    insert_z_id = CPzR_id  # Insert after R (higher index)
                    insert_z_val = CPzR
                    base_order_fb = "R_to_L"  # Path: R -> [bend] -> L
            elif idx_zR_fb > idx_zL_fb:
                # Normal case: R comes after L (e.g., A->B, B->C, C->D)
                # CRITICAL FIX: Insert after L (FIRST corner), NOT R
                insert_z_id = CPzL_id  # FIXED
                insert_z_val = CPzL
                base_order_fb = "L_to_R"  # FIXED
            else:
                # Reverse case: L comes after R (e.g., B->A, C->B, D->C)
                # Insert after R (FIRST corner in edge direction)
                insert_z_id = CPzR_id  # FIXED
                insert_z_val = CPzR
                base_order_fb = "R_to_L"  # FIXED

            # Check if connection lines cross and adjust order
            z_lines_cross = lines_cross(FPzyL, CPzL, CPzR, FPzyR)
            if z_lines_cross:
                # Lines cross - swap L/R in the base order
                if base_order_fb == "L_to_R":
                    base_order_fb = "R_to_L"
                else:
                    base_order_fb = "L_to_R"

            # Generate final point ordering
            if base_order_fb == "L_to_R":
                bend_points_z = {
                    f"FP{tab_z_id}_{tab_y_id}L": FPzyL,
                    f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                    f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                    f"FP{tab_z_id}_{tab_y_id}R": FPzyR
                }
            else:  # R_to_L
                bend_points_z = {
                    f"FP{tab_z_id}_{tab_y_id}R": FPzyR,
                    f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                    f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                    f"FP{tab_z_id}_{tab_y_id}L": FPzyL
                }

            # CRITICAL FIX: Remove FP points that duplicate existing corners (Approach 2A - tab_z)
            corners_coords_z_a2 = {k: v for k, v in new_tab_z.points.items() if k in ['A', 'B', 'C', 'D']}
            fp_points_to_remove_z_a2 = []

            for fp_name, fp_coord in list(bend_points_z.items()):
                if 'FP' in fp_name:
                    for corner_name, corner_coord in corners_coords_z_a2.items():
                        if np.allclose(fp_coord, corner_coord, atol=1e-6):
                            fp_points_to_remove_z_a2.append(fp_name)
                            break

            for fp_name in fp_points_to_remove_z_a2:
                del bend_points_z[fp_name]

            # wrap_str = "WRAP" if is_wraparound_z_fb else "normal"
            # print(f"    -> tab_{tab_z_id} edge {CPzL_id}->{CPzR_id} ({wrap_str}), inserting after {insert_z_id}, idx_zL={idx_zL_fb}, idx_zR={idx_zR_fb}")
            new_tab_z.insert_points(L={insert_z_id: insert_z_val}, add_points=bend_points_z)

            # ---- FILTER: Do Tabs cover Rects fully? ----
            if filter_cfg.get('Tabs cover Rects', False):
                if not tab_fully_contains_rectangle(new_tab_x, rect_x):
                    continue
                if not tab_fully_contains_rectangle(new_tab_z, rect_z):
                    continue

            # ---- FILTER: Thin segments ----
            if filter_cfg.get('Too thin segments', False):
                if thin_segment_filter(new_segment):
                    continue

            # ---- FILTER: Check for duplicates ----
            new_segment.tabs = {'tab_x': new_tab_x, 'tab_y': new_tab_y, 'tab_z': new_tab_z}
            if is_duplicate_segment(new_segment, segment_library):
                continue

            segment_library.append(new_segment)

    # ========== APPROACH 2B: EDGE CONNECTION (PARALLEL CASE, NO CORNER REMOVAL) ==========
    for pair_x in rect_x_edges:
        CPxL_id = pair_x[0]
        CPxR_id = pair_x[1]
        CPxL = tab_x.points[CPxL_id]
        CPxR = tab_x.points[CPxR_id]

        # Calculate outward direction for tab_x
        edge_x_vec = CPxR - CPxL
        edge_x_mid = (CPxL + CPxR) / 2
        out_dir_x = np.cross(edge_x_vec, plane_x.orientation)
        out_dir_x = normalize(out_dir_x)
        if np.dot(out_dir_x, edge_x_mid - rect_x_center) < 0:
            out_dir_x = -out_dir_x

        # Shift tab_x edge outward to create flange
        BPxL = CPxL + out_dir_x * min_flange_length
        BPxR = CPxR + out_dir_x * min_flange_length

        # Iterate over edges for parallel connection
        for pair_z in rect_z_edges:
            # Skip this edge pair if approach 1 already succeeded for it
            if prioritize_perpendicular and (pair_x, pair_z) in successful_edge_pairs:
                continue

            CPzL_id, CPzR_id = pair_z
            CPzL = tab_z.points[CPzL_id]
            CPzR = tab_z.points[CPzR_id]

            # Calculate edge_z properties
            edge_z_vec = CPzR - CPzL
            edge_z_mid = (CPzL + CPzR) / 2

            # ---- FILTER: Check perpendicular distance between planes ----
            # For parallel edges, if the two tabs' planes are too close together,
            # the flanges extending outward will overlap
            # Minimum safe distance is 2*min_flange_length (one flange length from each plane)

            # Calculate perpendicular distance from plane_x to edge_z
            # This is the distance along the normal direction from plane_x to any point on edge_z
            vec_to_edge_z = edge_z_mid - plane_x.position
            perp_distance = abs(np.dot(vec_to_edge_z, plane_x.orientation))

            if perp_distance < 2 * min_flange_length:
                continue  # Planes too close, flanges would overlap

            # ---- FILTER: Is flange wide enough? ----
            if not min_flange_width_filter(BPL=BPxL, BPR=BPxR):
                continue

            new_segment = segment.copy()
            new_tab_x = new_segment.tabs['tab_x']
            new_tab_z = new_segment.tabs['tab_z']

            bend_xy = Bend(position=BPxL, orientation=BPxR - BPxL, BPL=BPxL, BPR=BPxR)

            # Calculate outward direction for tab_z edge
            out_dir_z = np.cross(edge_z_vec, plane_z.orientation)
            out_dir_z_norm = np.linalg.norm(out_dir_z)
            if out_dir_z_norm < 1e-9:
                # Edge is parallel to plane normal - skip
                continue
            out_dir_z = out_dir_z / out_dir_z_norm
            if np.dot(out_dir_z, edge_z_mid - rect_z_center) < 0:
                out_dir_z = -out_dir_z

            # Verify bend_xy orientation is not parallel to plane_z (sanity check)
            ortho_check = np.cross(bend_xy.orientation, plane_z.orientation)
            if np.linalg.norm(ortho_check) < 1e-9:
                # Bend is parallel to plane_z - skip (not the parallel case we want)
                continue

            # Create second bend parallel to first bend, offset by outward direction
            bend_yz_pos = edge_z_mid + out_dir_z * min_flange_length
            bend_yz_ori = bend_xy.orientation / np.linalg.norm(bend_xy.orientation)
            bend_yz = Bend(position=bend_yz_pos, orientation=bend_yz_ori)

            # Project corners onto bend axis
            BPzL = project_onto_line(CPzL, bend_yz.position, bend_yz.orientation)
            BPzR = project_onto_line(CPzR, bend_yz.position, bend_yz.orientation)

            # ---- FILTER: Is flange wide enough? ----
            if not min_flange_width_filter(BPL=BPzL, BPR=BPzR):
                continue

            # Create intermediate triangle
            BPzM = (BPzL + BPzR) / 2.0
            BP_triangle = {"A": BPxL, "B": BPxR, "C": BPzM}
            plane_y = calculate_plane(triangle=BP_triangle)

            tab_y_id = f"{tab_x_id}{tab_z_id}"
            new_tab_y = Tab(tab_id=tab_y_id, points=BP_triangle)

            # ---- FILTER: Minimum bend angle ----
            if filter_cfg.get('Min Bend Angle', True):
                if not minimum_angle_filter(plane_x, plane_y):
                    continue
                if not minimum_angle_filter(plane_y, plane_z):
                    continue

            # Calculate flange points with angle checks
            FPxyL, FPxyR, FPyxL, FPyxR, angle_check_xy = calculate_flange_points_with_angle_check(
                BPxL, BPxR, plane_x, plane_y
            )
            if angle_check_xy:
                continue

            FPyzL, FPyzR, FPzyL, FPzyR, angle_check_yz = calculate_flange_points_with_angle_check(
                BPzL, BPzR, plane_y, plane_z
            )
            if angle_check_yz:
                continue

            # ---- FILTER: Check if flanges extend too far beyond edge range ----
            if flange_extends_beyond_edge_range(CPxL, CPxR, FPxyL, FPxyR):
                continue
            if flange_extends_beyond_edge_range(CPzL, CPzR, FPzyL, FPzyR):
                continue

            # Insert points in Tab x - same logic as Approach 1
            corner_order_x_fb = list(new_tab_x.points.keys())
            idx_xL_fb = corner_order_x_fb.index(CPxL_id)
            idx_xR_fb = corner_order_x_fb.index(CPxR_id)

            is_wraparound_x_fb = (idx_xL_fb == 3 and idx_xR_fb == 0) or (idx_xL_fb == 0 and idx_xR_fb == 3)

            if is_wraparound_x_fb:
                if idx_xL_fb == 3:
                    insert_after_x_fb_id = CPxL_id
                    insert_after_x_fb_val = CPxL
                    bend_points_x = {
                        f"FP{tab_x_id}_{tab_y_id}L": CPxL,
                        f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                        f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                        f"FP{tab_x_id}_{tab_y_id}R": CPxR
                    }
                else:
                    insert_after_x_fb_id = CPxR_id
                    insert_after_x_fb_val = CPxR
                    bend_points_x = {
                        f"FP{tab_x_id}_{tab_y_id}R": CPxR,
                        f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                        f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                        f"FP{tab_x_id}_{tab_y_id}L": CPxL
                    }
            elif idx_xR_fb > idx_xL_fb:
                insert_after_x_fb_id = CPxL_id
                insert_after_x_fb_val = CPxL
                bend_points_x = {
                    f"FP{tab_x_id}_{tab_y_id}L": CPxL,
                    f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                    f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                    f"FP{tab_x_id}_{tab_y_id}R": CPxR
                }
            else:
                insert_after_x_fb_id = CPxR_id
                insert_after_x_fb_val = CPxR
                bend_points_x = {
                    f"FP{tab_x_id}_{tab_y_id}R": CPxR,
                    f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                    f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                    f"FP{tab_x_id}_{tab_y_id}L": CPxL
                }

            # CRITICAL FIX: Remove FP points that duplicate existing corners (Approach 2B - tab_x)
            corners_coords_a2b = {k: v for k, v in new_tab_x.points.items() if k in ['A', 'B', 'C', 'D']}
            fp_points_to_remove_a2b = []

            for fp_name, fp_coord in list(bend_points_x.items()):
                if 'FP' in fp_name:
                    for corner_name, corner_coord in corners_coords_a2b.items():
                        if np.allclose(fp_coord, corner_coord, atol=1e-6):
                            fp_points_to_remove_a2b.append(fp_name)
                            break

            for fp_name in fp_points_to_remove_a2b:
                del bend_points_x[fp_name]

            new_tab_x.insert_points(L={insert_after_x_fb_id: insert_after_x_fb_val}, add_points=bend_points_x)

            # Insert points in Tab y
            # Determine correct z-side ordering using hybrid approach
            # (diagonal crossing check + distance-based fallback for collinear cases)
            if should_swap_z_side_ordering(FPyxL, FPyxR, FPyzR, FPyzL):
                bend_points_y = {
                    f"FP{tab_y_id}_{tab_x_id}L": FPyxL,
                    f"BP{tab_y_id}_{tab_x_id}L": BPxL,
                    f"BP{tab_y_id}_{tab_x_id}R": BPxR,
                    f"FP{tab_y_id}_{tab_x_id}R": FPyxR,
                    f"FP{tab_y_id}_{tab_z_id}L": FPyzL,
                    f"BP{tab_y_id}_{tab_z_id}L": BPzL,
                    f"BP{tab_y_id}_{tab_z_id}R": BPzR,
                    f"FP{tab_y_id}_{tab_z_id}R": FPyzR
                }
            else:
                bend_points_y = {
                    f"FP{tab_y_id}_{tab_x_id}L": FPyxL,
                    f"BP{tab_y_id}_{tab_x_id}L": BPxL,
                    f"BP{tab_y_id}_{tab_x_id}R": BPxR,
                    f"FP{tab_y_id}_{tab_x_id}R": FPyxR,
                    f"FP{tab_y_id}_{tab_z_id}R": FPyzR,
                    f"BP{tab_y_id}_{tab_z_id}R": BPzR,
                    f"BP{tab_y_id}_{tab_z_id}L": BPzL,
                    f"FP{tab_y_id}_{tab_z_id}L": FPyzL
                }
            new_tab_y.points = bend_points_y

            # Insert points in Tab z - same logic as Approach 1
            corner_order_z_fb = list(new_tab_z.points.keys())
            idx_zL_fb = corner_order_z_fb.index(CPzL_id)
            idx_zR_fb = corner_order_z_fb.index(CPzR_id)

            is_wraparound_z_fb = abs(idx_zL_fb - idx_zR_fb) > 1

            if is_wraparound_z_fb:
                if idx_zL_fb > idx_zR_fb:
                    insert_z_id = CPzL_id
                    insert_z_val = CPzL
                    base_order_fb = "L_to_R"
                else:
                    insert_z_id = CPzR_id
                    insert_z_val = CPzR
                    base_order_fb = "R_to_L"
            elif idx_zR_fb > idx_zL_fb:
                insert_z_id = CPzL_id
                insert_z_val = CPzL
                base_order_fb = "L_to_R"
            else:
                insert_z_id = CPzR_id
                insert_z_val = CPzR
                base_order_fb = "R_to_L"

            # Check if connection lines cross
            z_lines_cross = lines_cross(FPzyL, CPzL, CPzR, FPzyR)
            if z_lines_cross:
                if base_order_fb == "L_to_R":
                    base_order_fb = "R_to_L"
                else:
                    base_order_fb = "L_to_R"

            # Generate final point ordering
            if base_order_fb == "L_to_R":
                bend_points_z = {
                    f"FP{tab_z_id}_{tab_y_id}L": FPzyL,
                    f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                    f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                    f"FP{tab_z_id}_{tab_y_id}R": FPzyR
                }
            else:
                bend_points_z = {
                    f"FP{tab_z_id}_{tab_y_id}R": FPzyR,
                    f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                    f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                    f"FP{tab_z_id}_{tab_y_id}L": FPzyL
                }

            # CRITICAL FIX: Remove FP points that duplicate existing corners (Approach 2B - tab_z)
            corners_coords_z_a2b = {k: v for k, v in new_tab_z.points.items() if k in ['A', 'B', 'C', 'D']}
            fp_points_to_remove_z_a2b = []

            for fp_name, fp_coord in list(bend_points_z.items()):
                if 'FP' in fp_name:
                    for corner_name, corner_coord in corners_coords_z_a2b.items():
                        if np.allclose(fp_coord, corner_coord, atol=1e-6):
                            fp_points_to_remove_z_a2b.append(fp_name)
                            break

            for fp_name in fp_points_to_remove_z_a2b:
                del bend_points_z[fp_name]

            new_tab_z.insert_points(L={insert_z_id: insert_z_val}, add_points=bend_points_z)

            # ---- FILTER: Check for duplicates ----
            new_segment.tabs = {'tab_x': new_tab_x, 'tab_y': new_tab_y, 'tab_z': new_tab_z}
            if is_duplicate_segment(new_segment, segment_library):
                continue

            segment_library.append(new_segment)

    return segment_library
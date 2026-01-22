"""
Zero-bend segment generation for coplanar tabs.

This module contains the zero_bends() function which generates direct connections
between tabs that lie in the same plane, without any bending. Creates a closed
rectangular intermediate tab connecting the two edges.
"""

import numpy as np
from config.design_rules import min_flange_length
from src.hgen_sm.create_segments.utils import normalize
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane
from src.hgen_sm.filters import min_flange_width_filter, tab_fully_contains_rectangle
from src.hgen_sm.data import Tab


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


def is_quadrilateral_self_intersecting(A, B, C, D):
    """
    Check if quadrilateral ABCD has self-intersecting edges.

    A self-intersecting quadrilateral (bowtie shape) occurs when opposite
    edges cross each other. We check if edge AB crosses edge CD, and if
    edge BC crosses edge DA.

    Args:
        A, B, C, D: Four corner points in order

    Returns:
        bool: True if quadrilateral is self-intersecting
    """
    def segments_intersect_2d(a1, a2, b1, b2):
        """Check if line segment a1-a2 intersects with b1-b2 in 2D."""
        d1 = np.array([a2[0] - a1[0], a2[1] - a1[1]], dtype=float)
        d2 = np.array([b2[0] - b1[0], b2[1] - b1[1]], dtype=float)

        cross = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(cross) < 1e-10:
            return False  # Parallel lines

        diff = np.array([b1[0] - a1[0], b1[1] - a1[1]], dtype=float)
        t = (diff[0] * d2[1] - diff[1] * d2[0]) / cross
        s = (diff[0] * d1[1] - diff[1] * d1[0]) / cross

        # Check if intersection is within both segments (excluding endpoints)
        return 0.01 < t < 0.99 and 0.01 < s < 0.99

    A, B, C, D = np.array(A), np.array(B), np.array(C), np.array(D)

    # Check XY projection (most common for coplanar tabs)
    if segments_intersect_2d(A[:2], B[:2], C[:2], D[:2]):
        return True
    if segments_intersect_2d(B[:2], C[:2], D[:2], A[:2]):
        return True

    # Check XZ projection
    if segments_intersect_2d([A[0], A[2]], [B[0], B[2]], [C[0], C[2]], [D[0], D[2]]):
        return True
    if segments_intersect_2d([B[0], B[2]], [C[0], C[2]], [D[0], D[2]], [A[0], A[2]]):
        return True

    # Check YZ projection
    if segments_intersect_2d([A[1], A[2]], [B[1], B[2]], [C[1], C[2]], [D[1], D[2]]):
        return True
    if segments_intersect_2d([B[1], B[2]], [C[1], C[2]], [D[1], D[2]], [A[1], A[2]]):
        return True

    return False


def is_rectangle_degenerate(A, B, C, D, tolerance=1e-3):
    """
    Check if four points form a degenerate (zero-area) quadrilateral.

    Calculates the area using the cross product of diagonals.
    A degenerate quadrilateral has near-zero area (all points collinear or nearly so).

    Args:
        A, B, C, D: Four corner points of the quadrilateral
        tolerance: Minimum area threshold (in square mm)

    Returns:
        bool: True if quadrilateral is degenerate (area too small)
    """
    A, B, C, D = np.array(A), np.array(B), np.array(C), np.array(D)

    # Calculate area using cross product of diagonals AC and BD
    # Area = 0.5 * |AC × BD|
    diagonal_AC = C - A
    diagonal_BD = D - B
    cross_product = np.cross(diagonal_AC, diagonal_BD)
    area = 0.5 * np.linalg.norm(cross_product)

    return area < tolerance


def zero_bends(segment, filter_cfg):
    """
    Generate zero-bend connections for coplanar tabs.

    When two tabs lie in the same plane, connect their edges directly by creating
    a closed rectangular intermediate tab between them. This creates a flat connection
    with no actual bending (180° bend angle).

    Strategy:
    1. Find parallel edges from both tabs
    2. Create a rectangular intermediate tab connecting the edge pairs
    3. Add flange and bend points on both original tabs
    4. Filter based on tab_fully_contains_rectangle (same as one_bend)

    Args:
        segment: Segment object with tab_x and tab_z
        filter_cfg: Filter configuration dictionary

    Returns:
        List of valid zero-bend segment objects
    """
    tab_x = segment.tabs['tab_x']
    tab_x_id = tab_x.tab_id
    tab_z = segment.tabs['tab_z']
    tab_z_id = tab_z.tab_id

    rect_x = tab_x.rectangle
    rect_z = tab_z.rectangle

    segment_library = []

    # Calculate plane normals and centroids for outward direction checks
    plane_x = calculate_plane(rect=rect_x)
    plane_z = calculate_plane(rect=rect_z)

    rect_x_corners = [tab_x.points[k] for k in ['A', 'B', 'C', 'D']]
    rect_z_corners = [tab_z.points[k] for k in ['A', 'B', 'C', 'D']]
    rect_x_center = np.mean(rect_x_corners, axis=0)
    rect_z_center = np.mean(rect_z_corners, axis=0)

    # Define all possible edge pairs (adjacent corners)
    edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),
             ('B', 'A'), ('C', 'B'), ('D', 'C'), ('A', 'D')]

    for edge_x in edges:
        CP_xL_id, CP_xR_id = edge_x
        CP_xL = tab_x.points[CP_xL_id]
        CP_xR = tab_x.points[CP_xR_id]

        # Calculate edge vector and midpoint
        edge_x_vec = CP_xR - CP_xL
        edge_x_len = np.linalg.norm(edge_x_vec)

        if edge_x_len < 1e-9:
            continue  # Degenerate edge

        edge_x_mid = (CP_xL + CP_xR) / 2
        edge_x_dir = edge_x_vec / edge_x_len

        for edge_z in edges:
            CP_zL_id, CP_zR_id = edge_z
            CP_zL = tab_z.points[CP_zL_id]
            CP_zR = tab_z.points[CP_zR_id]

            # Calculate edge vector and midpoint
            edge_z_vec = CP_zR - CP_zL
            edge_z_len = np.linalg.norm(edge_z_vec)

            if edge_z_len < 1e-9:
                continue  # Degenerate edge

            edge_z_mid = (CP_zL + CP_zR) / 2
            edge_z_dir = edge_z_vec / edge_z_len

            # ---- FILTER: Check edge parallelism ----
            # Removed: Edges don't need to be parallel
            # Quadrilaterals are allowed as long as edges don't cross

            # ---- FILTER: Check reasonable connection distance ----
            connection_vec = edge_z_mid - edge_x_mid
            connection_dist = np.linalg.norm(connection_vec)

            # Connection should have minimum distance (prevent overlapping tabs)
            min_connection_dist = min_flange_length * 2
            if connection_dist < min_connection_dist:
                continue

            # Connection should not be too far
            max_connection_dist = max(edge_x_len, edge_z_len) * 5
            if connection_dist > max_connection_dist:
                continue

            # ---- Calculate Outward Directions (like two_bends does) ----
            # Calculate outward direction for tab_x edge
            out_dir_x = np.cross(edge_x_vec, plane_x.orientation)
            out_dir_x = normalize(out_dir_x)
            # Check if it points away from rectangle center
            if np.dot(out_dir_x, edge_x_mid - rect_x_center) < 0:
                out_dir_x = -out_dir_x

            # Calculate outward direction for tab_z edge
            out_dir_z = np.cross(edge_z_vec, plane_z.orientation)
            out_dir_z = normalize(out_dir_z)
            # Check if it points away from rectangle center
            if np.dot(out_dir_z, edge_z_mid - rect_z_center) < 0:
                out_dir_z = -out_dir_z

            # ---- FILTER: Check if edges are growing toward each other ----
            # For a valid connection, outward directions should point toward each other
            is_x_growing = np.dot(out_dir_x, connection_vec) > 0
            is_z_growing = np.dot(out_dir_z, -connection_vec) > 0

            # DEBUG
            # print(f"Edge {CP_xL_id}{CP_xR_id} -> {CP_zL_id}{CP_zR_id}: x_grow={is_x_growing}, z_grow={is_z_growing}")

            if not is_x_growing or not is_z_growing:
                continue  # Edges don't face each other

            # ---- Calculate Flange and Bend Points ----
            # FP: Flange Point at the corner (like two_bends approach 1)
            # BP: Bend Point extended outward by min_flange_length
            # This avoids duplicate points with corners
            FPxL = CP_xL
            FPxR = CP_xR
            BPxL = CP_xL + out_dir_x * min_flange_length
            BPxR = CP_xR + out_dir_x * min_flange_length

            FPzL = CP_zL
            FPzR = CP_zR
            BPzL = CP_zL + out_dir_z * min_flange_length
            BPzR = CP_zR + out_dir_z * min_flange_length

            # ---- FILTER: Minimum flange width ----
            if not min_flange_width_filter(BPL=BPxL, BPR=BPxR):
                continue
            if not min_flange_width_filter(BPL=BPzL, BPR=BPzR):
                continue

            # ---- Create Intermediate Rectangular Tab ----
            # The intermediate tab connects the extended bend points
            # Corner points form a closed rectangle: BPxL → BPxR → BPzR → BPzL

            tab_y_id = f"{tab_x_id}{tab_z_id}"

            # Check edge directions to determine if we need to swap z-side ordering
            edge_dot = np.dot(edge_x_vec, edge_z_vec)
            if edge_dot < 0:
                # Edges point in opposite directions, swap L/R for tab_z
                FPzL, FPzR = FPzR, FPzL
                BPzL, BPzR = BPzR, BPzL

            # Create intermediate tab with 4 corners (rectangular)
            # Use BP (extended points) not FP (corner points)
            intermediate_tab_points = {
                'A': BPxL,
                'B': BPxR,
                'C': BPzR,
                'D': BPzL
            }

            # ---- FILTER: Check if intermediate quadrilateral is degenerate ----
            if is_rectangle_degenerate(BPxL, BPxR, BPzR, BPzL):
                continue

            # ---- FILTER: Check if intermediate quadrilateral is self-intersecting ----
            if is_quadrilateral_self_intersecting(BPxL, BPxR, BPzR, BPzL):
                continue

            new_tab_y = Tab(tab_id=tab_y_id, points=intermediate_tab_points)

            # ---- Create Modified Tabs ----
            new_segment = segment.copy()
            new_tab_x = new_segment.tabs['tab_x']
            new_tab_z = new_segment.tabs['tab_z']

            # ---- Insert Points in Tab X ----
            corner_order = list(new_tab_x.points.keys())
            idx_xL = corner_order.index(CP_xL_id)
            idx_xR = corner_order.index(CP_xR_id)

            # Check for wrap-around edge
            is_wraparound_x = (idx_xL == 3 and idx_xR == 0) or (idx_xL == 0 and idx_xR == 3)

            if is_wraparound_x:
                if idx_xL == 3:  # D→A
                    insert_after_x_id = CP_xL_id
                    insert_after_x_val = CP_xL
                    bend_points_x = {
                        f"FP{tab_x_id}_{tab_y_id}L": FPxL,
                        f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                        f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                        f"FP{tab_x_id}_{tab_y_id}R": FPxR
                    }
                else:  # A→D
                    insert_after_x_id = CP_xR_id
                    insert_after_x_val = CP_xR
                    bend_points_x = {
                        f"FP{tab_x_id}_{tab_y_id}R": FPxR,
                        f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                        f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                        f"FP{tab_x_id}_{tab_y_id}L": FPxL
                    }
            elif idx_xR > idx_xL:
                insert_after_x_id = CP_xL_id
                insert_after_x_val = CP_xL
                bend_points_x = {
                    f"FP{tab_x_id}_{tab_y_id}L": FPxL,
                    f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                    f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                    f"FP{tab_x_id}_{tab_y_id}R": FPxR
                }
            else:
                insert_after_x_id = CP_xR_id
                insert_after_x_val = CP_xR
                bend_points_x = {
                    f"FP{tab_x_id}_{tab_y_id}R": FPxR,
                    f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                    f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                    f"FP{tab_x_id}_{tab_y_id}L": FPxL
                }

            new_tab_x.insert_points(L={insert_after_x_id: insert_after_x_val}, add_points=bend_points_x)

            # ---- Insert Points in Tab Z ----
            corner_order_z = list(new_tab_z.points.keys())
            idx_zL = corner_order_z.index(CP_zL_id)
            idx_zR = corner_order_z.index(CP_zR_id)

            is_wraparound_z = (idx_zL == 3 and idx_zR == 0) or (idx_zL == 0 and idx_zR == 3)

            if is_wraparound_z:
                if idx_zL == 3:  # D→A
                    insert_after_z_id = CP_zL_id
                    insert_after_z_val = CP_zL
                    bend_points_z = {
                        f"FP{tab_z_id}_{tab_y_id}L": FPzL,
                        f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                        f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                        f"FP{tab_z_id}_{tab_y_id}R": FPzR
                    }
                else:  # A→D
                    insert_after_z_id = CP_zR_id
                    insert_after_z_val = CP_zR
                    bend_points_z = {
                        f"FP{tab_z_id}_{tab_y_id}R": FPzR,
                        f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                        f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                        f"FP{tab_z_id}_{tab_y_id}L": FPzL
                    }
            elif idx_zR > idx_zL:
                insert_after_z_id = CP_zL_id
                insert_after_z_val = CP_zL
                bend_points_z = {
                    f"FP{tab_z_id}_{tab_y_id}L": FPzL,
                    f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                    f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                    f"FP{tab_z_id}_{tab_y_id}R": FPzR
                }
            else:
                insert_after_z_id = CP_zR_id
                insert_after_z_val = CP_zR
                bend_points_z = {
                    f"FP{tab_z_id}_{tab_y_id}R": FPzR,
                    f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                    f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                    f"FP{tab_z_id}_{tab_y_id}L": FPzL
                }

            new_tab_z.insert_points(L={insert_after_z_id: insert_after_z_val}, add_points=bend_points_z)

            # ---- FILTER: Check tab fully contains rectangle (always applied like one_bend) ----
            if not tab_fully_contains_rectangle(new_tab_x, rect_x):
                continue
            if not tab_fully_contains_rectangle(new_tab_z, rect_z):
                continue

            # ---- Update segment with modified tabs and intermediate tab ----
            new_segment.tabs = {
                'tab_x': new_tab_x,
                'tab_y': new_tab_y,
                'tab_z': new_tab_z
            }

            # ---- FILTER: Check for duplicates ----
            if is_duplicate_segment(new_segment, segment_library):
                continue

            segment_library.append(new_segment)

    return segment_library

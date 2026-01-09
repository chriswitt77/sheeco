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


def one_bend(segment, filter_cfg):
    """
    Generate single-bend connections between two tabs.

    Both tabs get flange areas added so the bending line lies outside both
    initial tab geometries. This ensures proper manufacturability.
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

    # Use only adjacent edge pairs for cleaner geometry
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

        # Calculate outward direction for tab_x (away from rectangle center)
        rect_x_center = np.mean([tab_x.points[k] for k in ['A', 'B', 'C', 'D']], axis=0)
        edge_x_vec = CP_xR - CP_xL
        edge_x_mid = (CP_xL + CP_xR) / 2
        out_dir_x = np.cross(edge_x_vec, plane_x.orientation)
        out_dir_x = normalize(out_dir_x)
        if np.dot(out_dir_x, edge_x_mid - rect_x_center) < 0:
            out_dir_x = -out_dir_x

        # Shift corner points outward by min_flange_length to create flange on tab_x
        CP_xL_shifted = CP_xL + out_dir_x * min_flange_length
        CP_xR_shifted = CP_xR + out_dir_x * min_flange_length

        for pair_z in rect_z_edges:
            CP_zL_id = pair_z[0]
            CP_zL = tab_z.points[CP_zL_id]
            CP_zR_id = pair_z[1]
            CP_zR = tab_z.points[CP_zR_id]

            # Calculate outward direction for tab_z
            rect_z_center = np.mean([tab_z.points[k] for k in ['A', 'B', 'C', 'D']], axis=0)
            edge_z_vec = CP_zR - CP_zL
            edge_z_mid = (CP_zL + CP_zR) / 2
            out_dir_z = np.cross(edge_z_vec, plane_z.orientation)
            out_dir_z = normalize(out_dir_z)
            if np.dot(out_dir_z, edge_z_mid - rect_z_center) < 0:
                out_dir_z = -out_dir_z

            # Shift corner points outward by min_flange_length to create flange on tab_z
            CP_zL_shifted = CP_zL + out_dir_z * min_flange_length
            CP_zR_shifted = CP_zR + out_dir_z * min_flange_length

            # ---- Bending Points (on the shifted positions) ----
            BPL = create_bending_point(CP_xL_shifted, CP_zL_shifted, bend)
            BPR = create_bending_point(CP_xR_shifted, CP_zR_shifted, bend)

            # ---- FILTER: Is flange wide enough? ----
            if not min_flange_width_filter(BPL=BPL, BPR=BPR):
                continue

            # Calculate flange points with angle check
            FPxL, FPxR, FPzL, FPzR, angle_too_small = calculate_flange_points_with_angle_check(
                BPL, BPR, planeA=plane_x, planeB=plane_z
            )

            if angle_too_small:
                continue

            # ---- Check Crossover
            if filter_cfg.get('Lines Cross', True):
                if lines_cross(CP_zL, FPzL, CP_zR, FPzR) or lines_cross(CP_xL, FPxL, CP_xR, FPxR):
                    continue

            # ---- Update Segment.tabs ----
            new_segment = segment.copy()
            new_tab_x = new_segment.tabs['tab_x']
            new_tab_z = new_segment.tabs['tab_z']

            # ---- Insert Points in Tab x (with flange) ----
            CPL = {CP_xL_id: CP_xL}
            bend_points_x = {
                f"FP{tab_x_id}{tab_z_id}L": FPxL,
                f"BP{tab_x_id}{tab_z_id}L": BPL,
                f"BP{tab_x_id}{tab_z_id}R": BPR,
                f"FP{tab_x_id}{tab_z_id}R": FPxR
            }

            new_tab_x.insert_points(L=CPL, add_points=bend_points_x)

            if not are_corners_neighbours(CP_xL_id, CP_xR_id):
                rm_point_id = next_cp(new_tab_x.rectangle.points, CP_xL_id)
                rm_point = new_tab_x.rectangle.points[rm_point_id]
                new_tab_x.remove_point(point={rm_point_id: rm_point})

            # ---- Insert Points in Tab z (with flange) ----
            CPL = {CP_zL_id: CP_zL}
            if not lines_cross(FPxL, FPzL, FPxR, FPzR):
                bend_points_z = {
                    f"FP{tab_z_id}{tab_x_id}L": FPzL,
                    f"BP{tab_z_id}{tab_x_id}L": BPL,
                    f"BP{tab_z_id}{tab_x_id}R": BPR,
                    f"FP{tab_z_id}{tab_x_id}R": FPzR
                }
            else:
                bend_points_z = {
                    f"FP{tab_z_id}{tab_x_id}R": FPzR,
                    f"BP{tab_z_id}{tab_x_id}R": BPR,
                    f"BP{tab_z_id}{tab_x_id}L": BPL,
                    f"FP{tab_z_id}{tab_x_id}L": FPzL
                }

            new_tab_z.insert_points(L=CPL, add_points=bend_points_z)

            if not are_corners_neighbours(CP_zL_id, CP_zR_id):
                rm_point_id = next_cp(new_tab_z.rectangle.points, CP_zL_id)
                rm_point = new_tab_z.rectangle.points[rm_point_id]
                new_tab_z.remove_point(point={rm_point_id: rm_point})

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


def two_bends(segment, filter_cfg):
    """
    Generate double-bend connections between two tabs (A ↔ C) via intermediate plane B.

    Strategy:
    1. APPROACH 1 (90-degree priority): Try to create plane B perpendicular to both A and C
       - Shifts edges outward to form plane B at 90° to both planes
       - Produces cleaner, more manufacturable bends
    2. APPROACH 2 (fallback): Corner point connection
       - Uses existing corner-based logic when 90° approach isn't possible

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
                continue  # Planes are parallel, skip
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
            if dist_xL_zR < dist_xL_zL:
                BPzL, BPzR = BPzR, BPzL
                FPyzL, FPyzR = FPyzR, FPyzL
                FPzyL, FPzyR = FPzyR, FPzyL

            # Create new segment
            new_segment = segment.copy()
            new_tab_x = new_segment.tabs['tab_x']
            new_tab_z = new_segment.tabs['tab_z']

            tab_y_id = f"{tab_x_id}{tab_z_id}"
            new_tab_y = Tab(tab_id=tab_y_id, points={"A": BPxL, "B": BPxR, "C": BPzL})

            # Insert points in Tab x (with flange)
            bend_points_x = {
                f"FP{tab_x_id}_{tab_y_id}L": FPxyL,
                f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                f"FP{tab_x_id}_{tab_y_id}R": FPxyR
            }
            new_tab_x.insert_points(L={CPxL_id: CPxL}, add_points=bend_points_x)

            # Insert points in Tab y
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
            new_tab_y.points = bend_points_y

            # Insert points in Tab z (with flange)
            bend_points_z = {
                f"FP{tab_z_id}_{tab_y_id}L": FPzyL,
                f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                f"FP{tab_z_id}_{tab_y_id}R": FPzyR
            }
            new_tab_z.insert_points(L={CPzL_id: CPzL}, add_points=bend_points_z)

            # ---- FILTER: Check for duplicates ----
            new_segment.tabs = {'tab_x': new_tab_x, 'tab_y': new_tab_y, 'tab_z': new_tab_z}
            if is_duplicate_segment(new_segment, segment_library):
                continue

            segment_library.append(new_segment)

    # ========== APPROACH 2: CORNER CONNECTION (FALLBACK) ==========
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
                # Parallel case fallback
                ortho_dir = np.cross(bend_xy.orientation, plane_z.orientation)
                ortho_norm = np.linalg.norm(ortho_dir)
                if ortho_norm < 1e-9:
                    continue
                ortho_dir /= ortho_norm

                if np.dot(ortho_dir, CPzM - rect_z_center) < 0:
                    ortho_dir *= -1

                bend_yz_pos = CPzM + ortho_dir * min_flange_length
                bend_yz_ori = bend_xy.orientation / np.linalg.norm(bend_xy.orientation)
                bend_yz = Bend(position=bend_yz_pos, orientation=bend_yz_ori)
                BPzM = bend_yz.position

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

            # Insert points in Tab x (with flange)
            bend_points_x = {
                f"FP{tab_x_id}_{tab_y_id}L": FPxyL,
                f"BP{tab_x_id}_{tab_y_id}L": BPxL,
                f"BP{tab_x_id}_{tab_y_id}R": BPxR,
                f"FP{tab_x_id}_{tab_y_id}R": FPxyR
            }
            new_tab_x.insert_points(L={CPxL_id: CPxL}, add_points=bend_points_x)

            # Insert points in Tab y
            if lines_cross(FPyxL, FPyzL, FPyxR, FPyzR):
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

            # Insert points in Tab z
            if lines_cross(FPyzL, CPzL, CPzR, FPyxR):
                bend_points_z = {
                    f"FP{tab_z_id}_{tab_y_id}R": FPzyR,
                    f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                    f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                    f"FP{tab_z_id}_{tab_y_id}L": FPzyL
                }
            else:
                bend_points_z = {
                    f"FP{tab_z_id}_{tab_y_id}L": FPzyL,
                    f"BP{tab_z_id}_{tab_y_id}L": BPzL,
                    f"BP{tab_z_id}_{tab_y_id}R": BPzR,
                    f"FP{tab_z_id}_{tab_y_id}R": FPzyR
                }

            if CPzM_id not in new_tab_z.points.keys():
                new_tab_z.insert_points(L={CPzL_id: CPzL}, add_points=bend_points_z)
            elif (CPzM == list(bend_points_z.values())[0]).all():
                new_tab_z.insert_points(L={CPzM_id: CPzM}, add_points=bend_points_z)
            else:
                new_tab_z.insert_points(L={CPzL_id: CPzL}, add_points=bend_points_z)

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

    return segment_library
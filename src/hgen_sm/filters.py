from config.design_rules import min_flange_width, min_bend_angle

import numpy as np
from shapely import Polygon, make_valid
from shapely.geometry import Polygon

from typing import Set, Tuple

# ---------- FILTER: BPC1 und BPC2 dürfen nicht zu nah beieinander sein ----------
def min_flange_width_filter(BPL, BPR):
    """Returns Talse if Bending Points are too close together"""
    min_distance_BPC = min_flange_width  # Minimale Distanz zwischen BPC1 und BPC2
    distance_BPC = np.linalg.norm(BPL - BPR)
    if distance_BPC < min_distance_BPC:
        return False  # Überspringe diese Lösung
    return True

def tab_fully_contains_rectangle(tab, rect, tol=1e-7):
    """Returns True if rectangle is fully contained in the tab"""
    tab_pts = np.array(list(tab.points.values()))
    rect_pts = np.array(list(rect.points.values()))

    # 1. Determine the Plane Basis
    # Use two vectors on the plane to create a local 2D coordinate system
    # We'll use the first three points of the rectangle to define the plane
    p0 = rect_pts[0]
    v1 = rect_pts[1] - p0
    v2 = rect_pts[2] - p0
    
    # Normal vector
    normal = np.cross(v1, v2)
    norm = np.linalg.norm(normal)
    if norm < 1e-9: return False # Points are collinear
    normal /= norm

    # Create local X and Y axes (u, v) for the plane
    u_axis = v1 / np.linalg.norm(v1)
    v_axis = np.cross(normal, u_axis)

    def project_to_local_2d(pts):
        """Projects 3D points onto the local (u, v) coordinates of the plane."""
        # Translate to origin, then dot product with local axes
        shifted = pts - p0
        u = np.dot(shifted, u_axis)
        v = np.dot(shifted, v_axis)
        return np.column_stack((u, v))

    # 2. Convert all points to the same local 2D space
    tab_2d = project_to_local_2d(tab_pts)
    rect_2d = project_to_local_2d(rect_pts)
    
    # 3. Perform Shapely Check
    tab_poly = Polygon(tab_2d).buffer(tol) # Small buffer for rounding
    rect_poly = Polygon(rect_2d)
    
    return tab_poly.contains(rect_poly)

import numpy as np

def lines_cross(P1, P2, P3, P4, buffer=0.1):
    """
    Checks if segments P1-P2 and P3-P4 intersect or come within 'buffer' distance.
    """
    p1, p2, p3, p4 = P1[:2], P2[:2], P3[:2], P4[:2]

    def dist_segment_to_segment(a, b, c, d):
        # Helper to find the minimum distance between two 2D segments
        # This is the most robust way to implement a physical buffer
        def dist_pt_to_seg(p, s1, s2):
            l2 = np.sum((s1 - s2)**2)
            if l2 == 0: return np.linalg.norm(p - s1)
            t = max(0, min(1, np.dot(p - s1, s2 - s1) / l2))
            projection = s1 + t * (s2 - s1)
            return np.linalg.norm(p - projection)

        return min(
            dist_pt_to_seg(a, c, d),
            dist_pt_to_seg(b, c, d),
            dist_pt_to_seg(c, a, b),
            dist_pt_to_seg(d, a, b)
        )

    # 1. Standard intersection check (Cross Product)
    def cp_2d(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    o1, o2 = cp_2d(p1, p2, p3), cp_2d(p1, p2, p4)
    o3, o4 = cp_2d(p3, p4, p1), cp_2d(p3, p4, p2)

    # If they mathematically intersect
    if (o1 * o2 < 0) and (o3 * o4 < 0):
        return True

    # 2. Buffer check: Are they closer than the allowed distance?
    return dist_segment_to_segment(p1, p2, p3, p4) < buffer

def are_corners_neighbours(cp_id1: str, cp_id2: str) -> bool:
    """Checks if two corner IDs are adjacent on the perimeter of the rectangle."""
    
    # Define all valid, adjacent (non-directional) pairs
    # Using a Set of Tuples ensures fast, order-independent lookup.
    ADJACENT_PAIRS: Set[Tuple[str, str]] = {
        ('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')
    }
    
    # Normalize the input by sorting the IDs to handle both ('A', 'B') and ('B', 'A')
    normalized_pair = tuple(sorted((cp_id1, cp_id2)))
    
    return normalized_pair in ADJACENT_PAIRS

def minimum_angle_filter(planeA, planeB, min_bend_angle=min_bend_angle):
    """Returns True if the bend angle between two planes is >= min_bend_angle."""
    
    # Normalize vectors just in case they aren't unit vectors
    nA = planeA.orientation / np.linalg.norm(planeA.orientation)
    nB = planeB.orientation / np.linalg.norm(planeB.orientation)

    # Calculate the angle between normals (in radians)
    # Clip to [-1, 1] to prevent NaN due to float imprecision
    dot_product = np.clip(np.dot(nA, nB), -1.0, 1.0)
    angle_rad = np.arccos(dot_product)
    
    # Convert to degrees
    angle_deg = np.degrees(angle_rad)

    # In sheet metal, the 'bend angle' is typically the deflection:
    # 0 deg = flat, 90 deg = L-bend. 
    bend_angle = angle_deg    
    return bend_angle >= min_bend_angle

# ============================================================================
# 3D COLLISION DETECTION
# ============================================================================

def _get_polygon_plane(points):
    """
    Calculate the plane equation for a polygon defined by 3D points.

    Returns:
        tuple: (normal, d) where normal is the unit normal vector
               and d is the plane constant (ax + by + cz = d)
        None if points are collinear
    """
    pts = np.array(points)
    if len(pts) < 3:
        return None

    # Find first non-duplicate point for v1
    p0 = pts[0]
    v1 = None
    v1_idx = 1
    for i in range(1, len(pts)):
        candidate = pts[i] - p0
        if np.linalg.norm(candidate) > 1e-9:
            v1 = candidate
            v1_idx = i
            break

    if v1 is None:
        return None  # All points are the same

    # Find second non-collinear point for v2
    for i in range(v1_idx + 1, len(pts)):
        v2 = pts[i] - p0
        normal = np.cross(v1, v2)
        norm = np.linalg.norm(normal)
        if norm > 1e-9:
            normal = normal / norm
            d = np.dot(normal, p0)
            return normal, d

    # Try all combinations if still not found
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            for k in range(j + 1, len(pts)):
                v1 = pts[j] - pts[i]
                v2 = pts[k] - pts[i]
                if np.linalg.norm(v1) < 1e-9 or np.linalg.norm(v2) < 1e-9:
                    continue
                normal = np.cross(v1, v2)
                norm = np.linalg.norm(normal)
                if norm > 1e-9:
                    normal = normal / norm
                    d = np.dot(normal, pts[i])
                    return normal, d

    return None  # All points are collinear


def _planes_are_parallel(plane1, plane2, tol=1e-6):
    """Check if two planes are parallel."""
    if plane1 is None or plane2 is None:
        return True
    n1, _ = plane1
    n2, _ = plane2
    cross = np.cross(n1, n2)
    return np.linalg.norm(cross) < tol


def _planes_are_coplanar(plane1, plane2, pts1, tol=1e-6):
    """Check if two planes are the same (coplanar)."""
    if not _planes_are_parallel(plane1, plane2, tol):
        return False
    # Check if a point from plane1 lies on plane2
    n2, d2 = plane2
    test_point = pts1[0]
    dist = abs(np.dot(n2, test_point) - d2)
    return dist < tol


def _get_plane_intersection_line(plane1, plane2):
    """
    Calculate the line of intersection between two planes.

    Returns:
        tuple: (point_on_line, direction) or None if parallel
    """
    n1, d1 = plane1
    n2, d2 = plane2

    # Direction of intersection line
    direction = np.cross(n1, n2)
    dir_norm = np.linalg.norm(direction)

    if dir_norm < 1e-9:
        return None  # Parallel planes

    direction = direction / dir_norm

    # Find a point on the intersection line
    A = np.array([n1, n2, direction])
    b = np.array([d1, d2, 0])

    try:
        point = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        # Fallback: find point by setting one coordinate
        abs_dir = np.abs(direction)
        if abs_dir[2] > abs_dir[0] and abs_dir[2] > abs_dir[1]:
            A2 = np.array([[n1[0], n1[1]], [n2[0], n2[1]]])
            b2 = np.array([d1, d2])
            try:
                xy = np.linalg.solve(A2, b2)
                point = np.array([xy[0], xy[1], 0])
            except:
                return None
        elif abs_dir[1] > abs_dir[0]:
            A2 = np.array([[n1[0], n1[2]], [n2[0], n2[2]]])
            b2 = np.array([d1, d2])
            try:
                xz = np.linalg.solve(A2, b2)
                point = np.array([xz[0], 0, xz[1]])
            except:
                return None
        else:
            A2 = np.array([[n1[1], n1[2]], [n2[1], n2[2]]])
            b2 = np.array([d1, d2])
            try:
                yz = np.linalg.solve(A2, b2)
                point = np.array([0, yz[0], yz[1]])
            except:
                return None

    return point, direction


def _point_in_polygon_2d(point, polygon):
    """Check if a 2D point is inside a polygon using ray casting."""
    x, y = point
    n = len(polygon)
    inside = False

    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-10) + xi):
            inside = not inside
        j = i

    return inside


def _line_intersects_polygon_interior(line_point, line_dir, polygon_pts, plane_normal, tol=1e-6):
    """
    Check if a line passes through the interior of a polygon.
    """
    pts = np.array(polygon_pts)
    n = len(pts)

    if n < 3:
        return False

    # Create local 2D coordinate system on the polygon plane
    # Find first non-zero vector for u_axis
    origin = pts[0]
    u_axis = None
    for i in range(1, n):
        candidate = pts[i] - origin
        norm = np.linalg.norm(candidate)
        if norm > 1e-9:
            u_axis = candidate / norm
            break

    if u_axis is None:
        return False  # Degenerate polygon

    v_axis = np.cross(plane_normal, u_axis)
    v_norm = np.linalg.norm(v_axis)
    if v_norm < 1e-9:
        return False
    v_axis = v_axis / v_norm

    # Project polygon points to 2D
    pts_2d = []
    for p in pts:
        rel = p - origin
        pts_2d.append([np.dot(rel, u_axis), np.dot(rel, v_axis)])
    pts_2d = np.array(pts_2d)

    # Check if line direction is parallel to plane
    dot_dir_normal = np.dot(line_dir, plane_normal)

    if abs(dot_dir_normal) < 1e-9:
        # Line is parallel to (or on) the plane
        dist_to_plane = np.dot(line_point - origin, plane_normal)
        if abs(dist_to_plane) > tol:
            return False  # Line is parallel but not on plane

        # Line is on the plane - check if it intersects polygon
        line_pt_2d = np.array([np.dot(line_point - origin, u_axis),
                               np.dot(line_point - origin, v_axis)])
        line_dir_2d = np.array([np.dot(line_dir, u_axis), np.dot(line_dir, v_axis)])

        # Check if line intersects any edge of polygon
        intersections = []
        for i in range(n):
            p1 = pts_2d[i]
            p2 = pts_2d[(i + 1) % n]

            edge_dir = p2 - p1
            denom = line_dir_2d[0] * edge_dir[1] - line_dir_2d[1] * edge_dir[0]

            if abs(denom) < 1e-9:
                continue  # Parallel

            diff = p1 - line_pt_2d
            t = (diff[0] * edge_dir[1] - diff[1] * edge_dir[0]) / denom
            s = (diff[0] * line_dir_2d[1] - diff[1] * line_dir_2d[0]) / denom

            if 0.01 < s < 0.99:
                intersections.append((t, s))

        return len(intersections) >= 2

    else:
        # Line intersects plane at a single point
        t = np.dot(origin - line_point, plane_normal) / dot_dir_normal
        intersection_3d = line_point + t * line_dir

        # Project to 2D
        rel = intersection_3d - origin
        pt_2d = np.array([np.dot(rel, u_axis), np.dot(rel, v_axis)])

        return _point_in_polygon_2d(pt_2d, pts_2d)


def _polygons_share_edge(pts1, pts2, tol=1e-6):
    """
    Check if two polygons share an edge (2 or more coincident points).
    This is used to avoid false positive collisions for connected tabs.
    """
    pts1 = np.array(pts1)
    pts2 = np.array(pts2)

    shared_count = 0
    for p1 in pts1:
        for p2 in pts2:
            if np.linalg.norm(p1 - p2) < tol:
                shared_count += 1
                if shared_count >= 2:
                    return True
                break

    return False


def _check_coplanar_polygon_intersection(pts1, pts2, tol=1e-6):
    """
    Check if two coplanar polygons intersect (overlap in 2D).
    """
    pts1 = np.array(pts1)
    pts2 = np.array(pts2)

    # Get plane for projection
    plane1 = _get_polygon_plane(pts1)
    if plane1 is None:
        return False

    normal, _ = plane1

    # Create local 2D coordinate system
    # Find first non-zero vector for u_axis
    origin = pts1[0]
    u_axis = None
    for i in range(1, len(pts1)):
        candidate = pts1[i] - origin
        norm = np.linalg.norm(candidate)
        if norm > 1e-9:
            u_axis = candidate / norm
            break

    if u_axis is None:
        return False  # Degenerate polygon

    v_axis = np.cross(normal, u_axis)
    v_norm = np.linalg.norm(v_axis)
    if v_norm < 1e-9:
        return False
    v_axis = v_axis / v_norm

    def project_to_2d(pts):
        result = []
        for p in pts:
            rel = p - origin
            result.append([np.dot(rel, u_axis), np.dot(rel, v_axis)])
        return result

    pts1_2d = project_to_2d(pts1)
    pts2_2d = project_to_2d(pts2)

    try:
        poly1 = Polygon(pts1_2d)
        poly2 = Polygon(pts2_2d)

        if not poly1.is_valid:
            poly1 = make_valid(poly1)
        if not poly2.is_valid:
            poly2 = make_valid(poly2)

        if poly1.intersects(poly2):
            intersection = poly1.intersection(poly2)
            return intersection.area > tol
    except Exception:
        pass

    return False


def _tabs_collide_3d(pts1, pts2, tol=1e-6):
    """
    Check if two 3D planar polygon tabs collide.

    Returns True if:
    1. The polygons are coplanar and overlap (even if they share an edge), OR
    2. The planes intersect and the intersection line passes through
       the interior of both polygons

    Returns False if:
    - Non-coplanar polygons that share an edge (valid L-bend connection)
    - Planes are parallel but not coplanar
    - Intersection line doesn't pass through both polygon interiors
    """
    pts1 = np.array(pts1)
    pts2 = np.array(pts2)

    # Get planes
    plane1 = _get_polygon_plane(pts1)
    plane2 = _get_polygon_plane(pts2)

    if plane1 is None or plane2 is None:
        return False

    # Check if coplanar - ALWAYS check for overlap, even if they share an edge
    # This catches the case where an extended tab overlaps another tab in the same plane
    if _planes_are_coplanar(plane1, plane2, pts1, tol):
        return _check_coplanar_polygon_intersection(pts1, pts2, tol)

    # For non-coplanar polygons: skip if they share an edge (valid L-bend connection)
    if _polygons_share_edge(pts1, pts2, tol):
        return False

    # Check if parallel (no intersection possible)
    if _planes_are_parallel(plane1, plane2, tol):
        return False

    # Get intersection line
    line_result = _get_plane_intersection_line(plane1, plane2)
    if line_result is None:
        return False

    line_point, line_dir = line_result

    # Check if line passes through interior of both polygons
    n1, _ = plane1
    n2, _ = plane2

    intersects_poly1 = _line_intersects_polygon_interior(line_point, line_dir, pts1, n1, tol)
    if not intersects_poly1:
        return False

    intersects_poly2 = _line_intersects_polygon_interior(line_point, line_dir, pts2, n2, tol)

    return intersects_poly1 and intersects_poly2


def collision_filter(tabs_dict, tol=0.1):
    """
    Check if any tabs in the assembled part collide with each other in 3D.

    Args:
        tabs_dict: Dictionary of tab_id -> Tab objects
        tol: Tolerance for geometric comparisons

    Returns:
        True if collision detected, False otherwise
    """
    tabs = list(tabs_dict.values())
    n = len(tabs)

    for i in range(n):
        for j in range(i + 1, n):
            id_i = str(tabs[i].tab_id)
            id_j = str(tabs[j].tab_id)

            # Skip connected tabs (one ID contains the other)
            if id_i in id_j or id_j in id_i:
                continue

            pts_i = np.array(list(tabs[i].points.values()))
            pts_j = np.array(list(tabs[j].points.values()))

            # Fast AABB bounding box pre-check
            if not _bounds_collide_with_gap(pts_i, pts_j, gap=tol):
                continue

            # Full 3D collision check
            if _tabs_collide_3d(pts_i, pts_j, tol):
                return True

    return False


def _bounds_collide_with_gap(pts1, pts2, gap):
    """Fast AABB bounding box collision check."""
    min1, max1 = pts1.min(axis=0), pts1.max(axis=0)
    min2, max2 = pts2.min(axis=0), pts2.max(axis=0)
    return np.all(min1 - gap < max2) and np.all(min2 - gap < max1)

def thin_segment_filter(segment):
    """NOT IMPLEMENTED YET: Filter out all the segments, that have sections that are too thin."""
    return False


def connection_crosses_tab_filter(corner_L, corner_R, FP_L, FP_R, rect_points):
    """
    Check if the connection lines from corners to flange points cross the tab rectangle.

    Args:
        corner_L: Left corner point of the selected edge
        corner_R: Right corner point of the selected edge
        FP_L: Left flange point
        FP_R: Right flange point
        rect_points: Dictionary of rectangle corner points {'A': [...], 'B': [...], ...}

    Returns:
        True if connection lines cross the tab (invalid), False otherwise (valid)
    """
    # Get rectangle corners in order
    corners = ['A', 'B', 'C', 'D']
    rect_pts = [np.array(rect_points[c]) for c in corners]

    # Rectangle edges (as pairs of points)
    edges = [
        (rect_pts[0], rect_pts[1]),  # A-B
        (rect_pts[1], rect_pts[2]),  # B-C
        (rect_pts[2], rect_pts[3]),  # C-D
        (rect_pts[3], rect_pts[0]),  # D-A
    ]

    corner_L = np.array(corner_L)
    corner_R = np.array(corner_R)
    FP_L = np.array(FP_L)
    FP_R = np.array(FP_R)

    def segment_crosses_edge(seg_start, seg_end, edge_start, edge_end, tol=1e-6):
        """Check if segment crosses an edge (excluding shared endpoints)."""
        # Skip if segment shares an endpoint with the edge
        if (np.linalg.norm(seg_start - edge_start) < tol or
            np.linalg.norm(seg_start - edge_end) < tol or
            np.linalg.norm(seg_end - edge_start) < tol or
            np.linalg.norm(seg_end - edge_end) < tol):
            return False

        # Use 2D projection for crossing check (XY, XZ, YZ)
        def segments_cross_2d(p1, p2, p3, p4):
            """Check if segments p1-p2 and p3-p4 cross in 2D."""
            def ccw(A, B, C):
                return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

            # Check proper intersection (not touching at endpoints)
            def intersect(A, B, C, D):
                return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

            return intersect(p1, p2, p3, p4)

        # Check in all 2D projections
        for proj in [(0, 1), (0, 2), (1, 2)]:  # XY, XZ, YZ
            if segments_cross_2d(
                seg_start[list(proj)], seg_end[list(proj)],
                edge_start[list(proj)], edge_end[list(proj)]
            ):
                return True

        return False

    # Check if connection line from corner_L to FP_L crosses any edge
    for edge_start, edge_end in edges:
        if segment_crosses_edge(corner_L, FP_L, edge_start, edge_end):
            return True
        if segment_crosses_edge(corner_R, FP_R, edge_start, edge_end):
            return True

    return False
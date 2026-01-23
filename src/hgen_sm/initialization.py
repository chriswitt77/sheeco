import numpy as np
from typing import Dict, List

from src.hgen_sm.data import Rectangle, Part, Tab, Mount
from config.design_rules import min_screw_to_edge_distance, mount_hole_diameter


def initialize_objects(rectangle_inputs):
    """
    Convert User Input into usable data and initialize Part.

    This includes:
    1. Creating Rectangle and Tab objects
    2. Processing mount coordinates (converting 3D to local u,v)
    3. Adjusting rectangle edges to maintain minimum distance from mounts
    """

    tabs: Dict[str, 'Tab'] = {}

    for i, rect in enumerate(rectangle_inputs):
        tab_id = str(i)

        # Convert raw lists to Point objects
        A = rect['pointA']
        B = rect['pointB']
        C = rect['pointC']

        # Get mount points if present
        mount_points_3d = rect.get('mounts', [])

        # Adjust rectangle for mount distances if mounts are present
        if mount_points_3d:
            A, B, C = adjust_rectangle_for_mounts(
                A, B, C, mount_points_3d, min_screw_to_edge_distance
            )

        # Create the Rectangle object
        rectangle = Rectangle(tab_id=int(i), A=A, B=B, C=C)

        # Create Mount objects from 3D coordinates
        mounts = []
        for mount_point in mount_points_3d:
            mount = Mount.from_global_coordinates(
                tab_id=int(tab_id),
                global_point=mount_point,
                A=A, B=B, C=C,
                size=mount_hole_diameter / 2.0  # Convert diameter to radius
            )
            mounts.append(mount)

        tab = Tab(tab_id=tab_id, rectangle=rectangle, mounts=mounts)
        tabs[tab_id] = tab

    part = Part(tabs=tabs)

    return part


def normalize(v):
    """Normalize a vector to unit length."""
    n = np.linalg.norm(v)
    if n < 1e-9:
        return np.zeros_like(v)
    return v / n


def point_to_line_distance_3d(point, line_start, line_end):
    """Calculate the perpendicular distance from a point to a line segment in 3D."""
    point = np.array(point, dtype=np.float64)
    line_start = np.array(line_start, dtype=np.float64)
    line_end = np.array(line_end, dtype=np.float64)

    line_vec = line_end - line_start
    point_vec = point - line_start
    line_len = np.linalg.norm(line_vec)

    if line_len == 0:
        return np.linalg.norm(point_vec)

    t = np.dot(point_vec, line_vec) / (line_len * line_len)
    t = max(0, min(1, t))
    projection = line_start + t * line_vec

    return np.linalg.norm(point - projection)


def adjust_rectangle_for_mounts(A, B, C, mount_points, min_dist):
    """
    Adjust rectangle edges outward to maintain minimum distance from mount points.

    Only edges that are too close to a mount are moved. The rectangle maintains
    its perpendicularity. Mounts stay at their absolute position.

    The three input points can be in any order. They will be automatically
    reordered to form a proper rectangle.

    Args:
        A, B, C: Three corner points defining the rectangle (in any order)
        mount_points: List of 3D mount coordinates
        min_dist: Minimum required distance from mounts to edges

    Returns:
        Tuple of adjusted (A, B, C) points properly ordered
    """
    if not mount_points:
        return A, B, C

    # Convert to numpy arrays
    A = np.array(A, dtype=np.float64)
    B = np.array(B, dtype=np.float64)
    C = np.array(C, dtype=np.float64)

    # Use the same logic as Rectangle.determine_fourth_point to properly
    # order points and calculate D
    A, B, C, D = Rectangle.determine_fourth_point(A, B, C)

    AB = B - A

    # Convert mount points to numpy arrays
    mount_points_array = [np.array(m, dtype=np.float64) for m in mount_points]

    # Calculate surface normal
    BC = C - B
    n = normalize(np.cross(AB, BC))

    # Define edges with their point indices
    # Order: A(0), B(1), C(2), D(3)
    # Rectangle edges follow the perimeter: A-B, B-C, C-D, D-A
    edges = [
        (0, 1, "AB"),  # A to B
        (1, 2, "BC"),  # B to C
        (2, 3, "CD"),  # C to D
        (3, 0, "DA"),  # D to A
    ]

    # Store points in a list for easy modification
    points = [A.copy(), B.copy(), C.copy(), D.copy()]

    # Find required shifts for each edge
    edges_to_move = {}

    for start_idx, end_idx, edge_name in edges:
        max_delta = 0.0

        for mount in mount_points_array:
            dist = point_to_line_distance_3d(mount, points[start_idx], points[end_idx])
            if dist < min_dist:
                delta = min_dist - dist
                max_delta = max(max_delta, delta)

        if max_delta > 0:
            edges_to_move[edge_name] = (max_delta, start_idx, end_idx)

    # No adjustment needed
    if not edges_to_move:
        return A.tolist(), B.tolist(), C.tolist()

    # Move affected edges outward while maintaining rectangle shape
    # We need to be careful: moving one edge affects adjacent corners
    # To maintain perpendicularity, we compute shifts in terms of the
    # two principal directions of the rectangle

    center = (A + B + C + D) / 4.0

    # Principal directions of the rectangle
    dir_AB = normalize(AB)  # Direction along AB edge
    dir_BC = normalize(BC)  # Direction along BC edge (perpendicular to AB)

    # Calculate how much to expand in each principal direction
    expand_AB_pos = 0.0  # Expand in +AB direction (move BC edge outward)
    expand_AB_neg = 0.0  # Expand in -AB direction (move DA edge outward)
    expand_BC_pos = 0.0  # Expand in +BC direction (move CD edge outward)
    expand_BC_neg = 0.0  # Expand in -BC direction (move AB edge outward)

    for edge_name, (delta, start_idx, end_idx) in edges_to_move.items():
        if edge_name == "AB":
            # AB edge needs to move outward (in -BC direction)
            expand_BC_neg = max(expand_BC_neg, delta)
        elif edge_name == "BC":
            # BC edge needs to move outward (in +AB direction)
            expand_AB_pos = max(expand_AB_pos, delta)
        elif edge_name == "CD":
            # CD edge needs to move outward (in +BC direction)
            expand_BC_pos = max(expand_BC_pos, delta)
        elif edge_name == "DA":
            # DA edge needs to move outward (in -AB direction)
            expand_AB_neg = max(expand_AB_neg, delta)

    # Apply expansions to maintain rectangle shape
    # New A = A - expand_AB_neg * dir_AB - expand_BC_neg * dir_BC
    # New B = B + expand_AB_pos * dir_AB - expand_BC_neg * dir_BC
    # New C = C + expand_AB_pos * dir_AB + expand_BC_pos * dir_BC
    # New D is recalculated by Rectangle class

    new_A = A - expand_AB_neg * dir_AB - expand_BC_neg * dir_BC
    new_B = B + expand_AB_pos * dir_AB - expand_BC_neg * dir_BC
    new_C = C + expand_AB_pos * dir_AB + expand_BC_pos * dir_BC

    return new_A.tolist(), new_B.tolist(), new_C.tolist()

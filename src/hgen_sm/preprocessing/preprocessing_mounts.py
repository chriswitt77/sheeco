import numpy as np
import copy


def normalize(vec):
    """Normalize a vector."""
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 1e-10 else vec


def point_to_line_distance_3d(point, line_start, line_end):
    """Calculate perpendicular distance from point to line segment in 3D."""
    line_vec = line_end - line_start
    point_vec = point - line_start

    line_len = np.linalg.norm(line_vec)
    if line_len < 1e-10:
        return np.linalg.norm(point_vec)

    line_unitvec = line_vec / line_len
    projection_length = np.dot(point_vec, line_unitvec)
    projection_length = np.clip(projection_length, 0, line_len)
    closest_point = line_start + projection_length * line_unitvec
    distance = np.linalg.norm(point - closest_point)

    return distance


def adjust_rectangle_for_mounts(rect_dict, min_dist, verbose=False):
    """
    Adjusts a rectangle so that all mount points are at least min_dist from edges.

    This version only moves the specific edges that violate the minimum distance,
    not both opposite edges. This results in minimal changes to the rectangle.

    Rectangle structure:
    - Input: A, B, C (three corners)
    - D = C - AB (fourth corner, from Rectangle class)
    - Forms rectangle: A---B
                       |   |
                       D---C

    Strategy:
    - Check each edge individually
    - Only move edges that are too close to mounts
    - Move edges away from mounts (perpendicular to edge direction)
    - Update all affected corners to maintain rectangular shape

    Args:
        rect_dict: Dictionary with pointA, pointB, pointC and optional 'mounts'
        min_dist: Minimum distance from mounts to edges
        verbose: Print debug information

    Returns:
        Adjusted rectangle dictionary (new copy)
    """
    mounts = rect_dict.get('mounts', [])

    if not mounts:
        return rect_dict.copy()

    # Convert to numpy arrays
    A = np.array(rect_dict["pointA"], dtype=np.float64)
    B = np.array(rect_dict["pointB"], dtype=np.float64)
    C = np.array(rect_dict["pointC"], dtype=np.float64)

    # Calculate D and vectors
    AB = B - A
    D = C - AB
    BC = C - B

    # Convert mount points
    mount_points = [np.array(m, dtype=np.float64) for m in mounts]

    # Calculate normal vector for the plane
    n = normalize(np.cross(AB, BC))

    # Track which edges need to be moved and by how much
    # Format: {edge_name: (expansion_distance, perpendicular_direction)}
    edge_expansions = {}

    # Check each edge individually
    edges_info = [
        ("AB", A, B, AB),
        ("BC", B, C, BC),
        ("CD", C, D, -AB),  # CD is parallel to AB but opposite direction
        ("DA", D, A, -BC),  # DA is parallel to BC but opposite direction
    ]

    for edge_name, start, end, edge_vec in edges_info:
        max_expansion = 0.0

        # Check all mounts against this edge
        for mount in mount_points:
            dist = point_to_line_distance_3d(mount, start, end)
            if dist < min_dist:
                needed = min_dist - dist
                max_expansion = max(max_expansion, needed)
                if verbose:
                    print(f"  Mount too close to {edge_name}: {dist:.2f} < {min_dist}, need {needed:.2f}")

        if max_expansion > 0:
            # Calculate perpendicular direction (outward from rectangle)
            perp = normalize(np.cross(n, edge_vec))

            # Determine if perp points outward
            # Use rectangle center to determine direction
            rect_center = (A + B + C + D) / 4.0
            edge_mid = (start + end) / 2.0
            to_center = rect_center - edge_mid

            # If perp points toward center, flip it
            if np.dot(perp, to_center) > 0:
                perp = -perp

            edge_expansions[edge_name] = (max_expansion, perp)

    # No adjustment needed
    if not edge_expansions:
        return rect_dict.copy()

    if verbose:
        print(f"  → Moving edges: {', '.join(edge_expansions.keys())}")

    # Apply expansions by moving corners
    # Each corner is at the intersection of two edges
    # We need to move corners based on which edges need to move

    # Start with original corners
    new_A = A.copy()
    new_B = B.copy()
    new_C = C.copy()

    # Corner A is on edges AB and DA
    if "AB" in edge_expansions:
        exp, perp = edge_expansions["AB"]
        new_A += exp * perp
        if verbose:
            print(f"    A moved by {exp:.2f} due to AB")
    if "DA" in edge_expansions:
        exp, perp = edge_expansions["DA"]
        new_A += exp * perp
        if verbose:
            print(f"    A moved by {exp:.2f} due to DA")

    # Corner B is on edges AB and BC
    if "AB" in edge_expansions:
        exp, perp = edge_expansions["AB"]
        new_B += exp * perp
        if verbose:
            print(f"    B moved by {exp:.2f} due to AB")
    if "BC" in edge_expansions:
        exp, perp = edge_expansions["BC"]
        new_B += exp * perp
        if verbose:
            print(f"    B moved by {exp:.2f} due to BC")

    # Corner C is on edges BC and CD
    if "BC" in edge_expansions:
        exp, perp = edge_expansions["BC"]
        new_C += exp * perp
        if verbose:
            print(f"    C moved by {exp:.2f} due to BC")
    if "CD" in edge_expansions:
        exp, perp = edge_expansions["CD"]
        new_C += exp * perp
        if verbose:
            print(f"    C moved by {exp:.2f} due to CD")

    # Note: D is implicit (D = C - AB), so we don't need to track it separately

    # Create adjusted rectangle
    adjusted = rect_dict.copy()
    adjusted["pointA"] = new_A.tolist()
    adjusted["pointB"] = new_B.tolist()
    adjusted["pointC"] = new_C.tolist()

    return adjusted


def preprocess_rectangles_for_mounts(rectangles_list, min_mount_distance, verbose=True):
    """
    Preprocesses all rectangles and adjusts them automatically for mount points.

    Args:
        rectangles_list: List of rectangle dictionaries (with optional 'mounts')
        min_mount_distance: Minimum distance from mount points to edges
        verbose: Print information

    Returns:
        New list with adjusted rectangles
    """
    if verbose:
        print("=" * 60)
        print("PRE-PROCESSING: Mount Point Validation")
        print("=" * 60)

    adjusted_rectangles = []
    total_adjustments = 0

    for i, rect in enumerate(rectangles_list):
        mounts = rect.get('mounts', [])

        if mounts:
            if verbose:
                print(f"\nRectangle {i}: {len(mounts)} mount(s) found")

            adjusted = adjust_rectangle_for_mounts(rect, min_mount_distance, verbose=verbose)

            # Check if adjustment was made
            if (adjusted["pointA"] != rect["pointA"] or
                    adjusted["pointB"] != rect["pointB"] or
                    adjusted["pointC"] != rect["pointC"]):
                if verbose:
                    print(f"  ✓ Rectangle adjusted for mount distances")
                total_adjustments += 1
            else:
                if verbose:
                    print(f"  ✓ No adjustment needed (distances OK)")

            adjusted_rectangles.append(adjusted)
        else:
            if verbose:
                print(f"\nRectangle {i}: No mounts")
            adjusted_rectangles.append(rect.copy())

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"Pre-processing completed: {total_adjustments} rectangle(s) adjusted")
        print(f"{'=' * 60}\n")

    return adjusted_rectangles
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

    This version moves ONLY the edges that are too close, maintaining rectangularity
    by adjusting the edge vectors appropriately.

    Rectangle structure:
    - Input: A, B, C (three corners)
    - D = C - AB (fourth corner)
    - Forms rectangle: A---AB-->B
                       |         |
                       AD        |
                       |         |
                       D---------C

    Strategy:
    - Check each edge individually
    - For edges that need moving, track which edge (AB/CD or AD/BC)
    - Adjust only the affected edge vectors
    - Reconstruct all corners maintaining orthogonality

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
    AD = D - A

    # Convert mount points
    mount_points = [np.array(m, dtype=np.float64) for m in mounts]

    # Track which edges need expansion
    # We track: which side of each edge pair needs to move
    needs_expansion = {
        'AB': 0.0,  # Edge A-B (bottom)
        'CD': 0.0,  # Edge C-D (top, opposite to AB)
        'AD': 0.0,  # Edge A-D (left)
        'BC': 0.0,  # Edge B-C (right, opposite to AD)
    }

    # Check each edge
    edges_to_check = [
        ('AB', A, B),
        ('BC', B, C),
        ('CD', C, D),
        ('AD', D, A),  # Note: AD goes from D to A in the loop
    ]

    for edge_name, start, end in edges_to_check:
        max_expansion = 0.0
        for mount in mount_points:
            dist = point_to_line_distance_3d(mount, start, end)
            if dist < min_dist:
                needed = min_dist - dist
                max_expansion = max(max_expansion, needed)
                if verbose:
                    print(f"  Mount too close to {edge_name}: {dist:.2f} < {min_dist}, need {needed:.2f}")

        needs_expansion[edge_name] = max_expansion

    # No adjustment needed
    if all(v == 0.0 for v in needs_expansion.values()):
        return rect_dict.copy()

    if verbose:
        moved_edges = [k for k, v in needs_expansion.items() if v > 0]
        print(f"  → Moving edges: {', '.join(moved_edges)}")

    # Now adjust the vectors based on which edges need to move
    # Key insight:
    # - AB and CD are opposite edges (parallel to AB vector)
    # - AD and BC are opposite edges (parallel to AD vector)

    # Calculate adjustments to the base vectors
    # If AB needs to move, shift A in -AD direction
    # If CD needs to move, extend AD vector
    # If AD needs to move, shift A in -AB direction
    # If BC needs to move, extend AB vector

    adjustment_A = np.zeros(3)  # How much to shift point A
    adjustment_AB = np.zeros(3)  # How much to extend AB vector
    adjustment_AD = np.zeros(3)  # How much to extend AD vector

    # Normalize the vectors for direction
    AB_dir = normalize(AB)
    AD_dir = normalize(AD)

    # Edge AB needs to move: shift A away from AB (in -AD direction)
    if needs_expansion['AB'] > 0:
        adjustment_A -= needs_expansion['AB'] * AD_dir
        if verbose:
            print(f"    Shifting A by {needs_expansion['AB']:.2f} away from AB")

    # Edge CD needs to move: extend AD vector
    if needs_expansion['CD'] > 0:
        adjustment_AD += needs_expansion['CD'] * AD_dir
        if verbose:
            print(f"    Extending AD by {needs_expansion['CD']:.2f} for CD")

    # Edge AD needs to move: shift A away from AD (in -AB direction)
    if needs_expansion['AD'] > 0:
        adjustment_A -= needs_expansion['AD'] * AB_dir
        if verbose:
            print(f"    Shifting A by {needs_expansion['AD']:.2f} away from AD")

    # Edge BC needs to move: extend AB vector
    if needs_expansion['BC'] > 0:
        adjustment_AB += needs_expansion['BC'] * AB_dir
        if verbose:
            print(f"    Extending AB by {needs_expansion['BC']:.2f} for BC")

    # Apply adjustments
    new_A = A + adjustment_A
    new_AB = AB + adjustment_AB
    new_AD = AD + adjustment_AD

    # Reconstruct all corners from adjusted vectors
    new_B = new_A + new_AB
    new_C = new_A + new_AB + new_AD
    # new_D = new_A + new_AD (implicit)

    # Create adjusted rectangle
    adjusted = rect_dict.copy()
    adjusted["pointA"] = new_A.tolist()
    adjusted["pointB"] = new_B.tolist()
    adjusted["pointC"] = new_C.tolist()

    # Verify rectangularity
    AB_check = new_B - new_A
    D_check = new_C - AB_check
    AD_check = D_check - new_A
    dot = np.dot(AB_check, AD_check)

    if abs(dot) > 1e-6 and verbose:
        print(f"  WARNING: Adjusted rectangle not rectangular! AB·AD = {dot:.6f}")
    elif verbose:
        print(f"  ✓ Rectangularity maintained: AB·AD = {dot:.10f}")

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
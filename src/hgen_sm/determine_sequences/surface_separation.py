import numpy as np
import copy


def normalize(vec):
    """Normalize a vector."""
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 1e-10 else vec


def split_rectangle_by_mounts(rect_dict, split_along='auto', gap_width=10.0, verbose=False):
    """
    Splits a rectangle with multiple mounts into separate rectangles,
    each containing one mount.

    IMPORTANT: Maintains rectangular shape using the same geometry as Rectangle class:
    - Rectangle: A---B
                 |   |
                 D---C
    - Where D = C - AB (not A + AB + AC!)
    - Perpendicular vector is AD = D - A

    Args:
        rect_dict: Dictionary with pointA, pointB, pointC and 'mounts' list
        split_along: 'AB', 'AC', or 'auto' (choose automatically)
        gap_width: Width of gap between split surfaces
        verbose: Print debug information

    Returns:
        List of new rectangle dictionaries, each with metadata about the split
    """
    mounts = rect_dict.get('mounts', [])

    if len(mounts) <= 1:
        return [rect_dict]  # No split needed

    # Use the SAME geometry as Rectangle class and preprocessing!
    A = np.array(rect_dict["pointA"], dtype=np.float64)
    B = np.array(rect_dict["pointB"], dtype=np.float64)
    C = np.array(rect_dict["pointC"], dtype=np.float64)

    AB = B - A
    D = C - AB  # This is how Rectangle class calculates D!
    AD = D - A  # This is the perpendicular vector to AB
    BC = C - B

    # Calculate normal for the plane
    n = normalize(np.cross(AB, BC))

    # DEBUG: Check if original rectangle is rectangular BEFORE split
    dot_original = np.dot(AB, AD)
    if verbose:
        print(f"  Original rectangle check: AB·AD = {dot_original:.6f}")
        if abs(dot_original) > 1e-6:
            print(f"  WARNING: Original rectangle NOT rectangular!")
            print(f"    A = {A}")
            print(f"    B = {B}")
            print(f"    C = {C}")
            print(f"    D = {D}")

    # Determine split direction
    if split_along == 'auto':
        # Choose direction based on mount distribution
        mount_arrays = [np.array(m, dtype=np.float64) for m in mounts]

        # Project mounts onto AB and AD directions
        projections_AB = [np.dot(m - A, AB) / np.dot(AB, AB) for m in mount_arrays]
        projections_AD = [np.dot(m - A, AD) / np.dot(AD, AD) for m in mount_arrays]

        # Calculate spread in each direction
        spread_AB = max(projections_AB) - min(projections_AB)
        spread_AD = max(projections_AD) - min(projections_AD)

        # Split along direction with larger spread
        split_along = 'AB' if spread_AB > spread_AD else 'AC'

        if verbose:
            print(f"  Auto-select split direction: {split_along} (spread: AB={spread_AB:.2f}, AC={spread_AD:.2f})")

    # Sort mounts along split direction
    mount_arrays = [np.array(m, dtype=np.float64) for m in mounts]

    if split_along == 'AB':
        # Split perpendicular to AB (along AD direction)
        # Cuts are parallel to AB
        projections = [(i, np.dot(m - A, AD) / np.dot(AD, AD)) for i, m in enumerate(mount_arrays)]
        projections.sort(key=lambda x: x[1])

        total_length = np.linalg.norm(AD)

    else:  # split_along == 'AC'
        # Split perpendicular to AD (along AB direction)
        # Cuts are parallel to AD
        projections = [(i, np.dot(m - A, AB) / np.dot(AB, AB)) for i, m in enumerate(mount_arrays)]
        projections.sort(key=lambda x: x[1])

        total_length = np.linalg.norm(AB)

    # Calculate split positions (midpoints between mounts)
    n_sections = len(projections)
    split_positions = []

    for i in range(n_sections - 1):
        pos1 = projections[i][1]
        pos2 = projections[i + 1][1]
        mid = (pos1 + pos2) / 2.0
        split_positions.append(mid)

    # Create new rectangles
    new_rectangles = []

    if split_along == 'AB':
        # Split along AD direction (cuts parallel to AB)
        # Original: A---B
        #           |   |
        #           D---C
        # Split into horizontal sections

        prev_v = 0.0

        for i, (mount_idx, mount_v) in enumerate(projections):
            if i < len(split_positions):
                next_v = split_positions[i] - gap_width / (2 * total_length)
            else:
                next_v = 1.0

            # Build new rectangle using original orthogonal vectors
            # Move along AD, keep AB unchanged
            new_A = A + prev_v * AD
            new_B = A + prev_v * AD + AB  # Add AB to get B
            new_C = A + next_v * AD + AB  # Move to next_v, add AB
            # new_D = A + next_v * AD (implicit, calculated as C - AB)

            new_rect = {
                'pointA': new_A.tolist(),
                'pointB': new_B.tolist(),
                'pointC': new_C.tolist(),
                'mounts': [mounts[mount_idx]],
                'split_from': rect_dict.get('original_id', None),
                'split_index': i,
                'split_total': n_sections
            }

            # Copy other properties
            for key in rect_dict:
                if key not in ['pointA', 'pointB', 'pointC', 'mounts', 'split_from', 'split_index', 'split_total']:
                    new_rect[key] = rect_dict[key]

            new_rectangles.append(new_rect)

            # Update prev_v for next section (add gap)
            if i < len(split_positions):
                prev_v = split_positions[i] + gap_width / (2 * total_length)

    else:  # split_along == 'AC'
        # Split along AB direction (cuts parallel to AD)
        # Original: A---B
        #           |   |
        #           D---C
        # Split into vertical sections

        prev_u = 0.0

        for i, (mount_idx, mount_u) in enumerate(projections):
            if i < len(split_positions):
                next_u = split_positions[i] - gap_width / (2 * total_length)
            else:
                next_u = 1.0

            # Build new rectangle using original orthogonal vectors
            # Move along AB, keep AD unchanged
            new_A = A + prev_u * AB
            new_B = A + next_u * AB  # Move to next_u along AB
            new_C = A + next_u * AB + AD  # Add AD to get C
            # new_D = A + prev_u * AB + AD (implicit, calculated as C - AB)

            new_rect = {
                'pointA': new_A.tolist(),
                'pointB': new_B.tolist(),
                'pointC': new_C.tolist(),
                'mounts': [mounts[mount_idx]],
                'split_from': rect_dict.get('original_id', None),
                'split_index': i,
                'split_total': n_sections
            }

            # Copy other properties
            for key in rect_dict:
                if key not in ['pointA', 'pointB', 'pointC', 'mounts', 'split_from', 'split_index', 'split_total']:
                    new_rect[key] = rect_dict[key]

            new_rectangles.append(new_rect)

            # Update prev_u for next section (add gap)
            if i < len(split_positions):
                prev_u = split_positions[i] + gap_width / (2 * total_length)

    if verbose:
        print(f"  Split rectangle into {len(new_rectangles)} sections")

        # Verify rectangularity
        for idx, rect in enumerate(new_rectangles):
            A_new = np.array(rect['pointA'])
            B_new = np.array(rect['pointB'])
            C_new = np.array(rect['pointC'])
            AB_new = B_new - A_new
            D_new = C_new - AB_new
            AD_new = D_new - A_new
            dot = np.dot(AB_new, AD_new)
            if abs(dot) > 1e-6:
                print(f"    WARNING: Section {idx} not rectangular! AB·AD = {dot:.6f}")

    return new_rectangles


def auto_split_rectangles_by_mounts(rectangles_list, min_mounts_for_split=2,
                                    mounts_per_surface=1, split_along='auto',
                                    gap_width=2.0, verbose=True):
    """
    Automatically splits rectangles with multiple mounts into separate surfaces.

    Returns rectangles with metadata tracking which ones came from the same split.

    Args:
        rectangles_list: List of rectangle dictionaries
        min_mounts_for_split: Minimum number of mounts required to trigger split
        mounts_per_surface: Target number of mounts per surface after split
        split_along: 'AB', 'AC', or 'auto'
        gap_width: Width of gap between split surfaces
        verbose: Print information

    Returns:
        Tuple of (new_rectangles, split_groups)
        - new_rectangles: List of rectangle dictionaries
        - split_groups: List of lists, where each inner list contains indices of rectangles from same split
    """
    if verbose:
        print("=" * 60)
        print("SURFACE SEPARATION: Splitting by Mounts")
        print("=" * 60)

    new_rectangles = []
    split_groups = []  # Track which rectangles came from the same split
    total_splits = 0

    for i, rect in enumerate(rectangles_list):
        mounts = rect.get('mounts', [])
        n_mounts = len(mounts)

        # Add original_id to track source
        rect_with_id = rect.copy()
        rect_with_id['original_id'] = i

        if n_mounts >= min_mounts_for_split and mounts_per_surface == 1:
            if verbose:
                print(f"\nRectangle {i}: {n_mounts} mounts → splitting")

            from config.design_rules import gap_width_surface_separation
            split_rects = split_rectangle_by_mounts(
                rect_with_id,
                split_along=split_along,
                gap_width=gap_width_surface_separation,
                verbose=verbose
            )

            # Track indices of split rectangles
            start_idx = len(new_rectangles)
            split_group = list(range(start_idx, start_idx + len(split_rects)))
            split_groups.append(split_group)

            new_rectangles.extend(split_rects)
            total_splits += 1

        else:
            if verbose:
                if n_mounts == 0:
                    print(f"\nRectangle {i}: No mounts → keep as is")
                else:
                    print(f"\nRectangle {i}: {n_mounts} mount(s) → keep as is")

            new_rectangles.append(rect_with_id)

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"Split {total_splits} rectangle(s) into {len(new_rectangles)} total surfaces")
        print(f"Split groups: {split_groups}")
        print(f"{'=' * 60}\n")

    return new_rectangles, split_groups
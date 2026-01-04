import numpy as np
import copy


def normalize(vec):
    """Normalize a vector."""
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 1e-10 else vec


def split_rectangle_by_mounts(rect_dict, split_along='auto', gap_width=2.0, verbose=False):
    """
    Splits a rectangle with multiple mounts into separate rectangles,
    each containing one mount.

    Args:
        rect_dict: Dictionary with pointA, pointB, pointC and 'mounts' list
        split_along: 'AB', 'AC', or 'auto' (choose automatically)
        gap_width: Width of gap between split surfaces
        verbose: Print debug information

    Returns:
        List of new rectangle dictionaries
    """
    mounts = rect_dict.get('mounts', [])

    if len(mounts) <= 1:
        return [rect_dict]  # No split needed

    A = np.array(rect_dict["pointA"], dtype=np.float64)
    B = np.array(rect_dict["pointB"], dtype=np.float64)
    C = np.array(rect_dict["pointC"], dtype=np.float64)

    AB = B - A
    AC = C - A
    D = A + AB + AC

    # Determine split direction
    if split_along == 'auto':
        # Choose direction based on mount distribution
        mount_arrays = [np.array(m, dtype=np.float64) for m in mounts]

        # Project mounts onto AB and AC directions
        projections_AB = [np.dot(m - A, AB) / np.dot(AB, AB) for m in mount_arrays]
        projections_AC = [np.dot(m - A, AC) / np.dot(AC, AC) for m in mount_arrays]

        # Calculate spread in each direction
        spread_AB = max(projections_AB) - min(projections_AB)
        spread_AC = max(projections_AC) - min(projections_AC)

        # Split along direction with larger spread
        split_along = 'AB' if spread_AB > spread_AC else 'AC'

        if verbose:
            print(f"  Auto-select split direction: {split_along} (spread: AB={spread_AB:.2f}, AC={spread_AC:.2f})")

    # Sort mounts along split direction
    mount_arrays = [np.array(m, dtype=np.float64) for m in mounts]

    if split_along == 'AB':
        # Split perpendicular to AB (along AC direction)
        projections = [(i, np.dot(m - A, AC) / np.dot(AC, AC)) for i, m in enumerate(mount_arrays)]
        projections.sort(key=lambda x: x[1])

        split_direction = AC
        perpendicular_direction = AB
        total_length = np.linalg.norm(AC)

    else:  # split_along == 'AC'
        # Split perpendicular to AC (along AB direction)
        projections = [(i, np.dot(m - A, AB) / np.dot(AB, AB)) for i, m in enumerate(mount_arrays)]
        projections.sort(key=lambda x: x[1])

        split_direction = AB
        perpendicular_direction = AC
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
        # Split perpendicular to AB
        prev_v = 0.0

        for i, (mount_idx, mount_v) in enumerate(projections):
            if i < len(split_positions):
                next_v = split_positions[i] - gap_width / (2 * total_length)
            else:
                next_v = 1.0

            # Define new rectangle corners
            new_A = A + prev_v * split_direction
            new_B = A + prev_v * split_direction + perpendicular_direction
            new_C = A + next_v * split_direction + perpendicular_direction

            new_rect = {
                'pointA': new_A.tolist(),
                'pointB': new_B.tolist(),
                'pointC': new_C.tolist(),
                'mounts': [mounts[mount_idx]]
            }

            # Copy other properties
            for key in rect_dict:
                if key not in ['pointA', 'pointB', 'pointC', 'mounts']:
                    new_rect[key] = rect_dict[key]

            new_rectangles.append(new_rect)

            # Update prev_v for next section
            if i < len(split_positions):
                prev_v = split_positions[i] + gap_width / (2 * total_length)

    else:  # split_along == 'AC'
        # Split perpendicular to AC
        prev_u = 0.0

        for i, (mount_idx, mount_u) in enumerate(projections):
            if i < len(split_positions):
                next_u = split_positions[i] - gap_width / (2 * total_length)
            else:
                next_u = 1.0

            # Define new rectangle corners
            new_A = A + prev_u * split_direction
            new_B = A + next_u * split_direction
            new_C = A + next_u * split_direction + perpendicular_direction

            new_rect = {
                'pointA': new_A.tolist(),
                'pointB': new_B.tolist(),
                'pointC': new_C.tolist(),
                'mounts': [mounts[mount_idx]]
            }

            # Copy other properties
            for key in rect_dict:
                if key not in ['pointA', 'pointB', 'pointC', 'mounts']:
                    new_rect[key] = rect_dict[key]

            new_rectangles.append(new_rect)

            # Update prev_u for next section
            if i < len(split_positions):
                prev_u = split_positions[i] + gap_width / (2 * total_length)

    if verbose:
        print(f"  Split rectangle into {len(new_rectangles)} sections")

    return new_rectangles


def auto_split_rectangles_by_mounts(rectangles_list, min_mounts_for_split=2,
                                    mounts_per_surface=1, split_along='auto',
                                    gap_width=2.0, verbose=True):
    """
    Automatically splits rectangles with multiple mounts into separate surfaces.

    Args:
        rectangles_list: List of rectangle dictionaries
        min_mounts_for_split: Minimum number of mounts required to trigger split
        mounts_per_surface: Target number of mounts per surface after split
        split_along: 'AB', 'AC', or 'auto'
        gap_width: Width of gap between split surfaces
        verbose: Print information

    Returns:
        New list with split rectangles
    """
    if verbose:
        print("=" * 60)
        print("SURFACE SEPARATION: Splitting by Mounts")
        print("=" * 60)

    new_rectangles = []
    total_splits = 0

    for i, rect in enumerate(rectangles_list):
        mounts = rect.get('mounts', [])
        n_mounts = len(mounts)

        if n_mounts >= min_mounts_for_split and mounts_per_surface == 1:
            if verbose:
                print(f"\nRectangle {i}: {n_mounts} mounts → splitting")

            split_rects = split_rectangle_by_mounts(
                rect,
                split_along=split_along,
                gap_width=gap_width,
                verbose=verbose
            )

            new_rectangles.extend(split_rects)
            total_splits += 1

        else:
            if verbose:
                if n_mounts == 0:
                    print(f"\nRectangle {i}: No mounts → keep as is")
                else:
                    print(f"\nRectangle {i}: {n_mounts} mount(s) → keep as is")
            new_rectangles.append(rect)

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"Split {total_splits} rectangle(s) into {len(new_rectangles)} total surfaces")
        print(f"{'=' * 60}\n")

    return new_rectangles
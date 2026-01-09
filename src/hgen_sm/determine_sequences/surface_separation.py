"""
Surface Separation Module

Handles splitting of tabs/surfaces that have multiple mounts into separate
surfaces, each with a subset of the original mounts.
"""

import numpy as np
from typing import Dict, List, Tuple

from src.hgen_sm.data import Rectangle, Tab, Mount, Part
from config.design_rules import gap_width_surface_separation, mount_hole_diameter


def separate_surfaces(part: Part, cfg: dict, verbose: bool = True) -> Part:
    """
    Main entry point for surface separation.

    Splits tabs with multiple mounts into separate tabs based on configuration.
    Updates the Part object with new tabs and tracks original_id for split surfaces.

    Args:
        part: Part object containing tabs to potentially split
        cfg: Configuration dictionary with surface_separation settings
        verbose: Whether to print progress information

    Returns:
        Updated Part object with split tabs
    """
    sep_cfg = cfg.get('surface_separation', {})

    auto_split = sep_cfg.get('auto_split', True)
    min_screws_for_split = sep_cfg.get('min_screws_for_split', 2)
    screws_per_surface = sep_cfg.get('screws_per_surface', 1)
    split_along = sep_cfg.get('split_along', 'auto')
    gap_width = gap_width_surface_separation

    if not auto_split:
        return part

    if verbose:
        print("=" * 60)
        print("SURFACE SEPARATION: Splitting surfaces with multiple mounts")
        print("=" * 60)

    new_tabs: Dict[str, Tab] = {}
    total_splits = 0

    for tab_id, tab in part.tabs.items():
        mounts = tab.mounts

        if len(mounts) < min_screws_for_split:
            if verbose:
                print(f"\nTab {tab_id}: {len(mounts)} mount(s) - no split needed")
            # Keep original tab, set original_id to itself
            tab.original_id = tab_id
            new_tabs[tab_id] = tab
            continue

        if verbose:
            print(f"\nTab {tab_id}: {len(mounts)} mounts found - splitting")

        # Calculate number of surfaces needed
        n_surfaces = int(np.ceil(len(mounts) / screws_per_surface))

        if n_surfaces <= 1:
            if verbose:
                print(f"  -> No split needed ({len(mounts)} <= {screws_per_surface})")
            tab.original_id = tab_id
            new_tabs[tab_id] = tab
            continue

        # Split the tab
        split_tabs = split_tab_by_mounts(
            tab=tab,
            n_surfaces=n_surfaces,
            split_along=split_along,
            gap_width=gap_width,
            base_tab_id=tab_id,
            verbose=verbose
        )

        # Add split tabs with new IDs
        for i, split_tab in enumerate(split_tabs):
            new_tab_id = f"{tab_id}_{i}"
            split_tab.tab_id = new_tab_id
            split_tab.original_id = tab_id  # Track original for sibling prevention
            new_tabs[new_tab_id] = split_tab

        total_splits += 1

        if verbose:
            for i, st in enumerate(split_tabs):
                print(f"    Sub-tab {tab_id}_{i}: {len(st.mounts)} mount(s)")

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"Surface separation complete:")
        print(f"  - {total_splits} tab(s) split")
        print(f"  - {len(new_tabs)} tabs total (was: {len(part.tabs)})")
        print(f"{'=' * 60}\n")

    # Update part with new tabs
    part.tabs = new_tabs
    return part


def split_tab_by_mounts(tab: Tab, n_surfaces: int, split_along: str,
                        gap_width: float, base_tab_id: str,
                        verbose: bool = True) -> List[Tab]:
    """
    Split a single tab into multiple tabs based on mount positions.

    Rectangle definition:
    - A, B, C are given corners where A-B and B-C are edges
    - D = C - AB (completing the rectangle)
    - The rectangle perimeter is A -> B -> C -> D -> A

    Args:
        tab: Tab to split
        n_surfaces: Number of surfaces to create
        split_along: 'AB', 'BC', or 'auto' (splits parallel to this edge)
        gap_width: Width of gap between split surfaces
        base_tab_id: Original tab ID for tracking
        verbose: Print debug info

    Returns:
        List of new Tab objects
    """
    # Get rectangle corners
    A = tab.points['A']
    B = tab.points['B']
    C = tab.points['C']
    D = tab.points['D']

    # Edge vectors
    AB = B - A
    BC = C - B

    # Determine split direction (which edge to split parallel to)
    if split_along == 'auto':
        # Calculate mount spread along each direction to choose the best split
        # We want to split perpendicular to the direction where mounts are spread out
        AB_norm = normalize(AB)
        BC_norm = normalize(BC)

        if len(tab.mounts) >= 2:
            # Calculate mount projections along both directions
            projs_along_AB = []
            projs_along_BC = []
            for mount in tab.mounts:
                if mount.global_coords is not None:
                    mp = np.array(mount.global_coords, dtype=np.float64)
                else:
                    mp = A + mount.u * AB_norm + mount.v * BC_norm
                projs_along_AB.append(np.dot(mp - A, AB_norm))
                projs_along_BC.append(np.dot(mp - A, BC_norm))

            # Calculate spread (range) along each direction
            spread_AB = max(projs_along_AB) - min(projs_along_AB)
            spread_BC = max(projs_along_BC) - min(projs_along_BC)

            # Split parallel to the edge where mounts have LESS spread
            # (i.e., travel along the direction where mounts ARE spread out)
            # If mounts spread along AB, we split parallel to BC (travel along AB)
            # If mounts spread along BC, we split parallel to AB (travel along BC)
            direction = 'BC' if spread_AB > spread_BC else 'AB'
        else:
            # Fallback: split parallel to the longer edge
            len_AB = np.linalg.norm(AB)
            len_BC = np.linalg.norm(BC)
            direction = 'AB' if len_AB > len_BC else 'BC'
    elif split_along == 'AC':
        # For backward compatibility, 'AC' means split parallel to BC
        direction = 'BC'
    else:
        direction = split_along

    if verbose:
        print(f"  -> Splitting into {n_surfaces} surfaces (parallel to {direction}, gap: {gap_width})")

    # Get mount global coordinates and sort along split direction
    mounts_with_proj = []
    if direction == 'AB':
        # Split parallel to AB, travel along BC direction
        ref_dir = normalize(BC)
    else:  # direction == 'BC'
        # Split parallel to BC, travel along AB direction
        ref_dir = normalize(AB)

    for mount in tab.mounts:
        if mount.global_coords is not None:
            proj = project_point_onto_direction(mount.global_coords, A, ref_dir)
            mounts_with_proj.append((proj, mount))
        else:
            # Reconstruct global coords from local u, v
            AB_norm = normalize(AB)
            BC_norm = normalize(BC)
            global_pos = A + mount.u * AB_norm + mount.v * BC_norm
            proj = project_point_onto_direction(global_pos, A, ref_dir)
            mounts_with_proj.append((proj, mount))

    # Sort mounts by projection
    mounts_with_proj.sort(key=lambda x: x[0])

    # Calculate split ratios (positions between mount groups)
    split_ratios = calculate_split_ratios(
        mounts_with_proj, n_surfaces, A, B, C, D, direction
    )

    if verbose:
        print(f"  -> Split positions: {[f'{r:.2f}' for r in split_ratios]}")

    # Split rectangle into sub-rectangles
    sub_rectangles = split_rectangle_parallel(A, B, C, D, split_ratios, direction, gap_width)

    # Create new tabs and distribute mounts
    new_tabs = []
    for i, (sub_A, sub_B, sub_C) in enumerate(sub_rectangles):
        # Create new rectangle
        new_rect = Rectangle(
            tab_id=int(base_tab_id) if base_tab_id.isdigit() else 0,
            A=sub_A.tolist(),
            B=sub_B.tolist(),
            C=sub_C.tolist()
        )

        # Create new tab
        new_tab = Tab(
            tab_id=f"{base_tab_id}_{i}",
            rectangle=new_rect,
            mounts=[],
            original_id=base_tab_id
        )

        new_tabs.append(new_tab)

    # Distribute mounts to sub-tabs
    distribute_mounts_to_tabs(new_tabs, [m for _, m in mounts_with_proj])

    return new_tabs


def normalize(v):
    """Normalize a vector to unit length."""
    v = np.array(v, dtype=np.float64)
    n = np.linalg.norm(v)
    if n < 1e-9:
        return np.zeros_like(v)
    return v / n


def project_point_onto_direction(point, origin, direction):
    """Project a point onto a direction vector from an origin."""
    point = np.array(point, dtype=np.float64)
    origin = np.array(origin, dtype=np.float64)
    direction = np.array(direction, dtype=np.float64)
    v = point - origin
    return np.dot(v, direction)


def calculate_split_ratios(mounts_with_proj: List[Tuple[float, Mount]],
                           n_surfaces: int, A, B, C, D, direction: str) -> List[float]:
    """
    Calculate the ratios at which to split the rectangle.

    Positions cuts between groups of mounts at midpoints.

    Rectangle: A -> B -> C -> D -> A
    """
    A = np.array(A, dtype=np.float64)
    B = np.array(B, dtype=np.float64)
    C = np.array(C, dtype=np.float64)
    D = np.array(D, dtype=np.float64)

    split_ratios = []
    screws_per_split = len(mounts_with_proj) / n_surfaces

    # Get maximum projection value for normalization
    if direction == 'AB':
        # Splitting parallel to AB, traveling along BC direction
        BC = C - B
        ref_dir = normalize(BC)
        # Max projection is the length of BC (from A+0*BC to A+1*BC equivalent)
        max_proj = np.linalg.norm(BC)
    else:  # direction == 'BC'
        # Splitting parallel to BC, traveling along AB direction
        AB = B - A
        ref_dir = normalize(AB)
        max_proj = np.linalg.norm(AB)

    for j in range(1, n_surfaces):
        idx = int(j * screws_per_split)
        if idx < len(mounts_with_proj) and idx > 0:
            proj_before = mounts_with_proj[idx - 1][0]
            proj_after = mounts_with_proj[idx][0]
            split_pos = (proj_before + proj_after) / 2.0

            # Normalize to [0, 1]
            ratio = split_pos / max_proj if max_proj > 0 else 0.5
            ratio = max(0.1, min(0.9, ratio))  # Clamp
            split_ratios.append(ratio)

    return split_ratios


def split_rectangle_parallel(A, B, C, D, split_ratios: List[float],
                             split_along: str, gap_width: float) -> List[Tuple]:
    """
    Split a rectangle through parallel cuts with gaps.

    Rectangle geometry: A -> B -> C -> D -> A
    - Edge AB connects A and B
    - Edge BC connects B and C
    - Edge CD connects C and D
    - Edge DA connects D and A

    Args:
        A, B, C, D: Corner points of the rectangle (in order around perimeter)
        split_ratios: List of ratios [0-1] at which to cut
        split_along: 'AB' or 'BC' - which edge to split parallel to
        gap_width: Width of gap between pieces

    Returns:
        List of (A, B, C) tuples defining each sub-rectangle
        Each tuple defines 3 corners, the 4th is computed as D = C - AB
    """
    A = np.array(A, dtype=np.float64)
    B = np.array(B, dtype=np.float64)
    C = np.array(C, dtype=np.float64)
    D = np.array(D, dtype=np.float64)

    sub_rectangles = []

    if split_along == 'AB':
        # Split parallel to AB, cuts travel along BC direction
        # The rectangle is divided into strips parallel to edge AB
        BC = C - B
        BC_len = np.linalg.norm(BC)
        BC_norm = BC / BC_len

        # Also need DA direction (should be parallel to BC)
        DA = A - D

        prev_ratio = 0.0

        for idx, ratio in enumerate(sorted(split_ratios)):
            # Calculate corner positions for this strip
            # Start edge (at prev_ratio along BC direction)
            start_A = A + prev_ratio * BC
            start_B = B + prev_ratio * BC

            # End edge (at ratio along BC direction, minus half gap)
            end_A = A + ratio * BC - (gap_width / 2.0) * BC_norm
            end_B = B + ratio * BC - (gap_width / 2.0) * BC_norm

            # Add gap at start if not first piece
            if prev_ratio > 0:
                start_A = start_A + (gap_width / 2.0) * BC_norm
                start_B = start_B + (gap_width / 2.0) * BC_norm

            # Sub-rectangle: start_A -> start_B -> end_B -> end_A
            # Return (A, B, C) where C is adjacent to B
            sub_rectangles.append((start_A, start_B, end_B))
            prev_ratio = ratio

        # Last piece: from last ratio to end (C, D)
        start_A = A + prev_ratio * BC + (gap_width / 2.0) * BC_norm
        start_B = B + prev_ratio * BC + (gap_width / 2.0) * BC_norm
        # End is at D and C
        sub_rectangles.append((start_A, start_B, C))

    else:  # split_along == 'BC'
        # Split parallel to BC, cuts travel along AB direction
        AB = B - A
        AB_len = np.linalg.norm(AB)
        AB_norm = AB / AB_len

        # Also need CD direction (should be parallel to AB)
        CD = D - C

        prev_ratio = 0.0

        for idx, ratio in enumerate(sorted(split_ratios)):
            # Calculate corner positions for this strip
            # Start edge (at prev_ratio along AB direction)
            start_A = A + prev_ratio * AB
            start_D = D + prev_ratio * AB  # D moves parallel to A

            # End edge (at ratio along AB direction, minus half gap)
            end_A = A + ratio * AB - (gap_width / 2.0) * AB_norm
            end_D = D + ratio * AB - (gap_width / 2.0) * AB_norm

            # Add gap at start if not first piece
            if prev_ratio > 0:
                start_A = start_A + (gap_width / 2.0) * AB_norm
                start_D = start_D + (gap_width / 2.0) * AB_norm

            # Sub-rectangle corners: start_A -> end_A -> (end_A + AD) -> start_D
            # We need to return (A, B, C) format
            # Here: A=start_A, B=end_A, C=end_A + (start_D - start_A) = end_D
            # Wait, let me reconsider the geometry...

            # For rectangle start_A -> end_A -> end_D -> start_D:
            # - Edge AB is start_A to end_A (along AB direction)
            # - Edge BC is end_A to end_D (perpendicular, along AD direction)
            # So return (start_A, end_A, end_D)
            sub_rectangles.append((start_A, end_A, end_D))
            prev_ratio = ratio

        # Last piece: from last ratio to end (B, C)
        start_A = A + prev_ratio * AB + (gap_width / 2.0) * AB_norm
        start_D = D + prev_ratio * AB + (gap_width / 2.0) * AB_norm
        # End is at B and C
        sub_rectangles.append((start_A, B, C))

    return sub_rectangles


def distribute_mounts_to_tabs(tabs: List[Tab], mounts: List[Mount]) -> None:
    """
    Distribute mounts to the correct sub-tab based on position.

    Modifies tabs in place by adding mounts to their mounts list.

    Rectangle geometry: A -> B -> C -> D where D = C - AB
    """
    for mount in mounts:
        if mount.global_coords is None:
            continue

        mount_pos = np.array(mount.global_coords, dtype=np.float64)

        # Find which tab contains this mount
        for tab in tabs:
            A = np.array(tab.points['A'], dtype=np.float64)
            B = np.array(tab.points['B'], dtype=np.float64)
            C = np.array(tab.points['C'], dtype=np.float64)

            # Check if point is inside this rectangle (2D projection test)
            # Rectangle edges are AB and BC
            AB = B - A
            BC = C - B
            AP = mount_pos - A

            # Project onto AB direction
            AB_len_sq = np.dot(AB, AB)
            proj_AB = np.dot(AP, AB) / AB_len_sq if AB_len_sq > 0 else 0

            # Project onto BC direction (from A, we need to account for offset)
            # The BC direction starts at B, but we can use the parallel direction from A
            # Point relative to A in BC direction
            BC_len_sq = np.dot(BC, BC)
            proj_BC = np.dot(AP, BC) / BC_len_sq if BC_len_sq > 0 else 0

            # Point is inside if both projections are in [0, 1]
            # Use small tolerance for edge cases
            if -0.01 <= proj_AB <= 1.01 and -0.01 <= proj_BC <= 1.01:
                # Recalculate local coordinates for new rectangle
                new_mount = Mount.from_global_coordinates(
                    tab_id=tab.tab_id if isinstance(tab.tab_id, int) else 0,
                    global_point=mount_pos,
                    A=A, B=B, C=C,
                    size=mount.size
                )
                tab.mounts.append(new_mount)
                break


def are_siblings(tab1: Tab, tab2: Tab) -> bool:
    """
    Check if two tabs are siblings (split from the same original surface).

    Args:
        tab1, tab2: Tabs to check

    Returns:
        True if tabs have the same original_id (are siblings)
    """
    if tab1.original_id is None or tab2.original_id is None:
        return False
    return tab1.original_id == tab2.original_id and tab1.tab_id != tab2.tab_id

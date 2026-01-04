from typing import List, Dict
import copy

from src.hgen_sm.data import Rectangle, Part, Tab, Mount


def determine_sequences(part, cfg):
    """
    Determines sensible topologies for connecting tabs.

    Now includes optional surface separation:
    - Can split tabs with multiple mounts into separate surfaces
    - Creates new tabs for each split surface
    - Adjusts sequences accordingly

    Args:
        part: Part object with tabs
        cfg: Configuration dictionary with topology and splitting settings

    Returns:
        List of sequences (each sequence is a list of [tab_x_id, tab_z_id] pairs)
    """

    topo_cfg = cfg.get('topologies', {})
    split_cfg = cfg.get('surface_separation', {})

    # Step 1: Optional surface separation
    if split_cfg.get('auto_split', False):
        part = apply_surface_separation(part, split_cfg)

    # Step 2: Get tab IDs
    tabs = part.tabs
    tab_ids: List[str] = [tab.tab_id for tab in tabs.values()]

    sequences = []

    # Step 3: Generate sequences based on topology type
    if topo_cfg.get('simple_topology', True):
        pair_sequence = []
        for i in range(len(tab_ids) - 1):
            tab_x_id = tab_ids[i]
            tab_z_id = tab_ids[i + 1]

            pair = [tab_x_id, tab_z_id]
            pair_sequence.append(pair)

        sequences.append(pair_sequence)

    else:
        # Future implementation for complex topologies
        print("Complex Topologies not implemented yet")

    return sequences


def apply_surface_separation(part, split_cfg):
    """
    Applies surface separation to tabs with multiple mounts.
    Splits tabs and creates new tab objects.

    Args:
        part: Part object with tabs
        split_cfg: Configuration for surface separation

    Returns:
        Modified Part object with split tabs
    """
    from .surface_separation import auto_split_rectangles_by_mounts

    min_mounts_for_split = split_cfg.get('min_mounts_for_split', 2)
    mounts_per_surface = split_cfg.get('mounts_per_surface', 1)
    split_along = split_cfg.get('split_along', 'auto')
    gap_width = split_cfg.get('gap_width', 2.0)
    verbose = split_cfg.get('verbose', True)

    # Convert tabs to rectangle dictionaries
    rect_dicts = []
    original_tab_ids = []

    for tab_id, tab in part.tabs.items():
        rect_dict = {
            'pointA': tab.points['A'].tolist(),
            'pointB': tab.points['B'].tolist(),
            'pointC': tab.points['C'].tolist(),
        }

        # Add mounts if present
        if hasattr(tab, 'mounts') and tab.mounts:
            rect_dict['mounts'] = [
                mount.get_3d_coordinates(tab).tolist()
                for mount in tab.mounts
            ]

        rect_dicts.append(rect_dict)
        original_tab_ids.append(tab_id)

    # Apply splitting
    split_rects = auto_split_rectangles_by_mounts(
        rect_dicts,
        min_mounts_for_split=min_mounts_for_split,
        mounts_per_surface=mounts_per_surface,
        split_along=split_along,
        gap_width=gap_width,
        verbose=verbose
    )

    # If no splitting occurred, return original part
    if len(split_rects) == len(rect_dicts):
        return part

    new_tabs: Dict[str, 'Tab'] = {}
    new_tab_counter = 0

    for rect in split_rects:
        new_tab_id = str(new_tab_counter)

        # Create Rectangle object
        rectangle = Rectangle(
            tab_id=new_tab_counter,
            A=rect['pointA'],
            B=rect['pointB'],
            C=rect['pointC']
        )

        # Create Mount objects
        mounts = []
        if 'mounts' in rect and rect['mounts']:
            for mount_coords in rect['mounts']:
                mount = Mount(
                    tab_id=new_tab_counter,
                    coordinates=mount_coords
                )
                mounts.append(mount)

        # Create Tab
        tab = Tab(tab_id=new_tab_id, rectangle=rectangle, mounts=mounts)

        # Compute local coordinates for mounts
        for mount in mounts:
            mount.compute_local_coordinates(tab)

        new_tabs[new_tab_id] = tab
        new_tab_counter += 1

    # Update part with new tabs
    part.tabs = new_tabs

    return part
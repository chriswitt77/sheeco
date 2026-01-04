from typing import Dict, List
import numpy as np

from src.hgen_sm.data import Rectangle, Part, Tab, Mount
from .preprocessing_mounts import preprocess_rectangles_for_mounts

# For demonstration, I'll write the full function with clear structure
def initialize_objects(rectangle_inputs, min_mount_distance=5.0, preprocess_mounts=True, verbose=True):
    """
    Convert User Input into usable data and initialize Part.

    This function now includes preprocessing for mount points:
    - Validates mount distances from edges
    - Adjusts rectangles if mounts are too close to edges

    Args:
        rectangle_inputs: List of rectangle dictionaries with optional 'mounts'
        min_mount_distance: Minimum distance from mounts to rectangle edges
        preprocess_mounts: Enable preprocessing for mount validation
        verbose: Print preprocessing information

    Returns:
        Part object with initialized tabs
    """

    # Step 1: Preprocess rectangles for mount validation
    if preprocess_mounts:
        processed_rectangles = preprocess_rectangles_for_mounts(
            rectangle_inputs,
            min_mount_distance=min_mount_distance,
            verbose=verbose
        )
    else:
        processed_rectangles = rectangle_inputs

    # Step 2: Create Tab objects
    tabs: Dict[str, 'Tab'] = {}

    for i, rect in enumerate(processed_rectangles):
        tab_id = str(i)

        # Convert raw lists to numpy arrays
        A = rect['pointA']
        B = rect['pointB']
        C = rect['pointC']

        # Create the Rectangle object
        rectangle = Rectangle(tab_id=int(i), A=A, B=B, C=C)

        # Create Mount objects if present
        mounts = []
        if 'mounts' in rect and rect['mounts']:
            for mount_coords in rect['mounts']:
                mount = Mount(
                    tab_id=int(i),
                    coordinates=mount_coords
                )
                mounts.append(mount)

        # Create Tab with Rectangle and Mounts
        tab = Tab(tab_id=tab_id, rectangle=rectangle, mounts=mounts)

        # Compute local coordinates for mounts
        for mount in mounts:
            mount.compute_local_coordinates(tab)

        tabs[tab_id] = tab

    # Step 3: Create Part object
    part = Part(tabs=tabs)

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"Initialized Part with {len(tabs)} tab(s)")
        for tab_id, tab in tabs.items():
            n_mounts = len(tab.mounts) if hasattr(tab, 'mounts') and tab.mounts else 0
            print(f"  Tab {tab_id}: {n_mounts} mount(s)")
        print(f"{'=' * 60}\n")

    return part
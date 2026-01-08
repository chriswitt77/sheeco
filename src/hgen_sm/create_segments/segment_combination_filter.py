"""
Segment Combination Filter for Tree Topologies

Problem: In tree topologies, a central tab connects to multiple others.
If both connections use the same edge of the central tab, they will collide.

Solution: Pre-filter segment combinations to reject those with overlapping bends.
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional


def get_bend_edge(tab, segment) -> Optional[Tuple[str, str]]:
    """
    Determine which edge of the tab the bend is attached to.

    Returns tuple of standard points (e.g., ('A', 'B')) or None
    """
    points = list(tab.points.keys())

    # Find standard points
    std_points = [p for p in points if p in ['A', 'B', 'C', 'D']]

    # Find bend points (BP prefix)
    bend_points = [p for p in points if p.startswith('BP')]

    if not bend_points:
        return None

    # Find which standard points the bend is between
    for i in range(len(std_points)):
        next_i = (i + 1) % len(std_points)
        std1 = std_points[i]
        std2 = std_points[next_i]

        # Check if bend points are between these two standard points
        idx1 = points.index(std1)
        idx2 = points.index(std2)

        # Handle wraparound
        if idx2 < idx1:
            in_between = any(points.index(bp) > idx1 or points.index(bp) < idx2 for bp in bend_points)
        else:
            in_between = any(idx1 < points.index(bp) < idx2 for bp in bend_points)

        if in_between:
            return tuple(sorted([std1, std2]))

    return None


def check_bend_compatibility(segments: List[Any], tab_id: str) -> bool:
    """
    Check if segments can be assembled without bend collisions on shared tab.

    For a tab that appears in multiple segments, check if the bends are on different edges.

    Args:
        segments: List of segment objects
        tab_id: ID of the tab to check

    Returns:
        True if compatible (no collisions), False otherwise
    """
    # Find all instances of this tab across segments
    tab_instances = []
    segment_ids = []

    for seg_idx, segment in enumerate(segments):
        for tab_key in segment.tabs:
            tab = segment.tabs[tab_key]
            if tab.tab_id == tab_id:
                tab_instances.append(tab)
                segment_ids.append(seg_idx)

    if len(tab_instances) <= 1:
        return True  # No conflict possible

    # Get bend edges for each instance
    bend_edges = []
    for tab in tab_instances:
        edge = get_bend_edge(tab, None)
        if edge:
            bend_edges.append(edge)

    # Check for duplicates
    if len(bend_edges) != len(set(bend_edges)):
        # Same edge used multiple times - collision!
        return False

    return True


def filter_segment_combinations(segments_library: List[List[Any]], sequence: List[List[str]]) -> List[List[Any]]:
    """
    Filter out segment combinations that would cause bend collisions.

    Args:
        segments_library: List of segment lists for each pair
        sequence: The sequence being assembled (list of pairs)

    Returns:
        List of valid segment combinations
    """
    import itertools

    # Count how many times each tab appears
    tab_counts = {}
    for pair in sequence:
        for tab_id in pair:
            tab_counts[tab_id] = tab_counts.get(tab_id, 0) + 1

    # Find tabs that appear multiple times (potential collision candidates)
    shared_tabs = [tab_id for tab_id, count in tab_counts.items() if count > 1]

    if not shared_tabs:
        # No shared tabs - no filtering needed
        return list(itertools.product(*segments_library))

    # Generate all combinations and filter
    valid_combinations = []

    for combo in itertools.product(*segments_library):
        # Check each shared tab for bend compatibility
        compatible = True

        for tab_id in shared_tabs:
            if not check_bend_compatibility(combo, tab_id):
                compatible = False
                break

        if compatible:
            valid_combinations.append(combo)

    return valid_combinations

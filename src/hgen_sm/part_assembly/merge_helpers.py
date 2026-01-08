from typing import Dict, Any, Optional, List, Set
import numpy as np


def extract_tabs_from_segments(tab_id, segments):
    """Extract all tab instances with given tab_id from segments."""
    tabs = []
    for segment in segments:
        for tab_key in segment.tabs:
            tab = segment.tabs[tab_key]
            if tab.tab_id == tab_id:
                tabs.append(tab)
    return tabs


def merge_points(tabs: List[Any]) -> Optional[Dict[str, np.ndarray]]:
    """
    Ultra-flexible merge for tree topologies.

    Can handle:
    - Different sets of standard points (A,B,C,D)
    - Multiple bend sequences on different edges
    - Missing corners

    Strategy: Union of all points, ordered by first occurrence
    """
    if len(tabs) != 2:
        return None

    geom_a: Dict[str, np.ndarray] = tabs[0].points
    geom_b: Dict[str, np.ndarray] = tabs[1].points

    # Start with all points from tab A in order
    merged: Dict[str, np.ndarray] = {}
    seen_keys = set()

    for key in geom_a:
        merged[key] = geom_a[key]
        seen_keys.add(key)

    # Add points from tab B that aren't in tab A yet
    # Try to insert them in sensible positions
    STD_PTS = {'A', 'B', 'C', 'D'}

    # Get standard points from both
    std_a = [k for k in geom_a.keys() if k in STD_PTS]
    std_b = [k for k in geom_b.keys() if k in STD_PTS]

    # Find where to insert new points
    new_points_b = {k: v for k, v in geom_b.items() if k not in seen_keys}

    if not new_points_b:
        # Nothing to add from B
        return merged

    # Simple strategy: find first common standard point and insert before it
    common_std = [k for k in std_b if k in std_a]

    if common_std:
        # Insert new points from B before first common standard point
        first_common = common_std[0]

        # Rebuild merged dict with insertions
        final_merged: Dict[str, np.ndarray] = {}

        for key in merged:
            if key == first_common:
                # Insert all new points from B here
                for b_key in geom_b:
                    if b_key not in seen_keys:
                        final_merged[b_key] = geom_b[b_key]

            final_merged[key] = merged[key]

        return final_merged
    else:
        # No common standard points - just append
        for key, value in new_points_b.items():
            merged[key] = value

        return merged
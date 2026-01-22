from src.hgen_sm.create_segments.bend_strategies import one_bend, two_bends, zero_bends
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane, is_coplanar

def create_segments(segment, segment_cfg, filter_cfg):
    """
    Generate connection segments between two tabs.

    Strategy selection:
    1. If tabs are coplanar → ONLY use zero_bends (no bending needed)
    2. If tabs are not coplanar → use one_bend and/or two_bends based on config

    Args:
        segment: Segment object with tab_x and tab_z
        segment_cfg: Configuration for which strategies to enable
        filter_cfg: Filter configuration

    Returns:
        List of valid segment objects
    """
    tab_x = segment.tabs['tab_x']
    tab_z = segment.tabs['tab_z']

    # Calculate planes for both tabs
    plane_x = calculate_plane(rect=tab_x)
    plane_z = calculate_plane(rect=tab_z)

    # Check if tabs are coplanar
    if is_coplanar(plane_x, plane_z):
        # Tabs in same plane → use zero-bend strategy exclusively
        return zero_bends(segment, filter_cfg)

    # Tabs not coplanar → use traditional bending strategies
    segment_library = []

    if segment_cfg.get('single_bend', True):
        new_segments = one_bend(segment, filter_cfg)
        if new_segments is not None:
            segment_library.extend(new_segments)

    if segment_cfg.get('double_bend', True):
        segment_library.extend(two_bends(segment, filter_cfg))

    return segment_library
from src.hgen_sm.part_assembly.merge_helpers import extract_tabs_from_segments, merge_points
from src.hgen_sm.filters import collision_filter


def part_assembly(part, segments, filter_cfg):
    """
    Assembles a part from multiple segments by merging tabs that appear in multiple segments.

    For tree topologies, tabs can appear in multiple segments and must be merged correctly.

    Args:
        part: Part object with original tabs
        segments: Tuple/list of Segment objects to assemble
        filter_cfg: Filter configuration

    Returns:
        Modified Part object, or None if assembly fails
    """

    # Step 1: Build a mapping of tab_id -> list of tab instances from segments
    tabs_by_id = {}

    for segment in segments:
        for tab_local_key in segment.tabs:
            tab = segment.tabs[tab_local_key]
            tab_id = tab.tab_id

            if tab_id not in tabs_by_id:
                tabs_by_id[tab_id] = []

            tabs_by_id[tab_id].append(tab)

    # Debug output
    if filter_cfg.get('verbose', False):
        print(f"\n=== Part Assembly Debug ===")
        print(f"Segments: {len(segments)}")
        print(f"Tabs by ID:")
        for tab_id, tab_list in tabs_by_id.items():
            print(f"  Tab {tab_id}: appears {len(tab_list)} time(s)")

    # Step 2: Merge tabs that appear multiple times
    new_tabs_dict = {}

    for tab_id, tab_list in tabs_by_id.items():
        count = len(tab_list)

        if count == 1:
            # Tab appears only once - use it directly
            new_tabs_dict[tab_id] = tab_list[0].copy()

        elif count == 2:
            # Tab appears twice - merge the two instances
            if filter_cfg.get('verbose', False):
                print(f"  Merging Tab {tab_id} (2 instances)")
                print(f"    Instance 1 points: {list(tab_list[0].points.keys())}")
                print(f"    Instance 2 points: {list(tab_list[1].points.keys())}")

            merged_points = merge_points(tab_list)

            if merged_points is None:
                if filter_cfg.get('verbose', False):
                    print(f"  → Merge failed for Tab {tab_id}")
                return None

            # Use the first tab as base and update its points
            merged_tab = tab_list[0].copy()
            merged_tab.points = merged_points
            new_tabs_dict[tab_id] = merged_tab

            if filter_cfg.get('verbose', False):
                print(f"    Merged points: {list(merged_points.keys())}")

            # Sanity check
            if len(merged_points) > 14:
                print(f"WARNING: Tab {tab_id} has {len(merged_points)} points after merge (> 14)")

        else:
            # Tab appears more than twice - this shouldn't happen in current implementation
            # but we handle it by iteratively merging
            if filter_cfg.get('verbose', False):
                print(f"  Merging Tab {tab_id} ({count} instances) - iterative merge")

            current_tab = tab_list[0].copy()

            for i in range(1, count):
                merged_points = merge_points([current_tab, tab_list[i]])

                if merged_points is None:
                    if filter_cfg.get('verbose', False):
                        print(f"  → Merge failed at iteration {i} for Tab {tab_id}")
                    return None

                current_tab.points = merged_points

            new_tabs_dict[tab_id] = current_tab

    # Step 3: Collision filter
    if filter_cfg.get("Collisions", False):
        if collision_filter(new_tabs_dict):
            if filter_cfg.get('verbose', False):
                print("  → Assembly rejected: Collision detected")
            return None

    # Step 4: Update part with merged tabs
    part.tabs = new_tabs_dict

    if filter_cfg.get('verbose', False):
        print(f"=== Assembly successful ===")
        for tab_id, tab in new_tabs_dict.items():
            print(f"  Final Tab {tab_id}: {len(tab.points)} points")

    return part
from typing import List, Dict, Set, Tuple
import copy
import itertools


def generate_all_tree_topologies(tab_ids: List[str], forbidden_pairs: Set[Tuple[str, str]] = None) -> List[
    List[Tuple[str, str]]]:
    """
    Generates all possible tree topologies (connection patterns) for the given tabs.

    A tree topology is a list of pairs (edges) that connect tabs without cycles.
    For n tabs, we need exactly n-1 connections to form a tree.

    Args:
        tab_ids: List of tab IDs
        forbidden_pairs: Set of (tab_x, tab_z) tuples that should not be connected
                        (e.g., tabs from the same split group)

    Returns:
        List of topologies, where each topology is a list of (tab_x_id, tab_z_id) pairs
    """
    if forbidden_pairs is None:
        forbidden_pairs = set()

    n = len(tab_ids)

    if n <= 1:
        return [[]]  # No connections needed for 0 or 1 tab

    if n == 2:
        pair = (tab_ids[0], tab_ids[1])
        if pair in forbidden_pairs or (pair[1], pair[0]) in forbidden_pairs:
            return []  # These two tabs cannot be connected
        return [[(tab_ids[0], tab_ids[1])]]

    # For larger n, we need to generate all possible spanning trees
    # This is computationally intensive, so we'll use a simplified approach:
    # Generate all possible combinations of n-1 edges that form a connected tree

    all_possible_pairs = []
    for i, tab_x in enumerate(tab_ids):
        for j, tab_z in enumerate(tab_ids):
            if i < j:  # Avoid duplicates
                pair = (tab_x, tab_z)
                rev_pair = (tab_z, tab_x)
                if pair not in forbidden_pairs and rev_pair not in forbidden_pairs:
                    all_possible_pairs.append(pair)

    # We need exactly n-1 edges to form a tree
    n_edges = n - 1

    valid_topologies = []

    # Try all combinations of n-1 edges
    for edge_combo in itertools.combinations(all_possible_pairs, n_edges):
        # Check if this forms a connected tree (no cycles, all nodes reachable)
        if is_valid_tree(list(edge_combo), tab_ids):
            valid_topologies.append(list(edge_combo))

    return valid_topologies


def is_valid_tree(edges: List[Tuple[str, str]], tab_ids: List[str]) -> bool:
    """
    Check if a set of edges forms a valid tree (connected, no cycles).

    Args:
        edges: List of (tab_x, tab_z) pairs
        tab_ids: List of all tab IDs that should be in the tree

    Returns:
        True if edges form a valid tree
    """
    if len(edges) != len(tab_ids) - 1:
        return False  # Wrong number of edges

    # Build adjacency list
    adj = {tab_id: [] for tab_id in tab_ids}
    for tab_x, tab_z in edges:
        adj[tab_x].append(tab_z)
        adj[tab_z].append(tab_x)

    # Check connectivity using DFS
    visited = set()

    def dfs(node):
        visited.add(node)
        for neighbor in adj[node]:
            if neighbor not in visited:
                dfs(neighbor)

    # Start DFS from first tab
    dfs(tab_ids[0])

    # All tabs should be visited
    return len(visited) == len(tab_ids)


def determine_sequences(part, cfg):
    """
    Determines sensible topologies for connecting tabs.

    Now supports:
    - Tree structures (not just linear chains)
    - Respects split groups (tabs from same split cannot connect to each other)
    - Optional surface separation
    - Topology limiting and prioritization

    Args:
        part: Part object with tabs
        cfg: Configuration dictionary with topology and splitting settings

    Returns:
        Tuple of (part, sequences)
        - part: Modified Part object (may have split tabs)
        - sequences: List of sequences (each sequence is a list of [tab_x_id, tab_z_id] pairs)
    """

    topo_cfg = cfg.get('topologies', {})
    split_cfg = cfg.get('surface_separation', {})

    # Step 1: Optional surface separation
    split_groups = []
    if split_cfg.get('auto_split', False):
        part, split_groups = apply_surface_separation(part, split_cfg)

    # Step 2: Get tab IDs
    tabs = part.tabs
    tab_ids: List[str] = list(tabs.keys())

    # Step 3: Build forbidden pairs (tabs from same split group)
    forbidden_pairs = set()
    for group in split_groups:
        # All pairs within a group are forbidden
        for i, tab_x in enumerate(group):
            for tab_z in group[i + 1:]:
                forbidden_pairs.add((tab_x, tab_z))
                forbidden_pairs.add((tab_z, tab_x))

    if len(forbidden_pairs) > 0 and cfg.get('verbose', False):
        print(f"\nForbidden pairs (from split groups): {forbidden_pairs}")

    sequences = []

    # Step 4: Generate sequences based on topology type
    if topo_cfg.get('simple_topology', False):
        # Simple linear topology (original behavior)
        pair_sequence = []
        for i in range(len(tab_ids) - 1):
            tab_x_id = tab_ids[i]
            tab_z_id = tab_ids[i + 1]

            pair = (tab_x_id, tab_z_id)

            # Check if this pair is forbidden
            if pair in forbidden_pairs or (tab_z_id, tab_x_id) in forbidden_pairs:
                if cfg.get('verbose', False):
                    print(f"Warning: Cannot connect {tab_x_id} and {tab_z_id} (same split group)")
                continue

            pair_sequence.append([tab_x_id, tab_z_id])

        if pair_sequence:  # Only add if we have valid pairs
            sequences.append(pair_sequence)

    elif topo_cfg.get('tree_topology', True):
        # Tree topology - explore all possible tree structures
        if cfg.get('verbose', False):
            print(f"\nGenerating tree topologies for {len(tab_ids)} tabs...")

        all_topologies = generate_all_tree_topologies(tab_ids, forbidden_pairs)

        if cfg.get('verbose', False):
            print(f"Found {len(all_topologies)} valid tree topologies")

        # Apply limits and prioritization
        max_topologies = topo_cfg.get('max_topologies', None)
        prioritize = topo_cfg.get('prioritize', 'balanced')  # 'balanced', 'linear', 'star', 'none'

        if prioritize != 'none' and len(all_topologies) > 1:
            # Score and sort topologies
            scored_topologies = []

            for topology in all_topologies:
                score = score_topology(topology, tab_ids, prioritize)
                scored_topologies.append((score, topology))

            # Sort by score (higher is better)
            scored_topologies.sort(key=lambda x: x[0], reverse=True)

            # Take top topologies
            if max_topologies and len(scored_topologies) > max_topologies:
                if cfg.get('verbose', False):
                    print(f"Limiting to top {max_topologies} topologies (prioritized by: {prioritize})")
                scored_topologies = scored_topologies[:max_topologies]

            all_topologies = [topo for score, topo in scored_topologies]

        elif max_topologies and len(all_topologies) > max_topologies:
            # Just take first N without scoring
            if cfg.get('verbose', False):
                print(f"Limiting to first {max_topologies} topologies (no prioritization)")
            all_topologies = all_topologies[:max_topologies]

        # Convert topologies to sequences (list of pairs)
        for topology in all_topologies:
            sequence = [[tab_x, tab_z] for tab_x, tab_z in topology]
            sequences.append(sequence)

    else:
        # Future: other topology types
        print("Other topology types not implemented yet")

    return part, sequences


def score_topology(topology: List[Tuple[str, str]], tab_ids: List[str], prioritize: str) -> float:
    """
    Score a topology based on prioritization strategy.

    Args:
        topology: List of (tab_x, tab_z) pairs
        tab_ids: All tab IDs
        prioritize: 'balanced', 'linear', 'star'

    Returns:
        Score (higher is better)
    """
    # Count connections per tab
    connections = {tab_id: 0 for tab_id in tab_ids}
    for tab_x, tab_z in topology:
        connections[tab_x] += 1
        connections[tab_z] += 1

    max_connections = max(connections.values())
    min_connections = min(connections.values())
    avg_connections = sum(connections.values()) / len(connections)

    if prioritize == 'balanced':
        # Prefer topologies where connections are evenly distributed
        # Lower variance is better
        variance = sum((c - avg_connections) ** 2 for c in connections.values()) / len(connections)
        score = 1.0 / (1.0 + variance)  # Lower variance = higher score

    elif prioritize == 'linear':
        # Prefer linear chains (most tabs have 2 connections, endpoints have 1)
        # Count how many tabs have exactly 2 connections
        two_connection_count = sum(1 for c in connections.values() if c == 2)
        score = two_connection_count / len(tab_ids)

    elif prioritize == 'star':
        # Prefer star structures (one central tab with many connections)
        # Higher max_connections is better
        score = max_connections / len(tab_ids)

    else:
        score = 0.0

    return score


def apply_surface_separation(part, split_cfg):
    """
    Applies surface separation to tabs with multiple mounts.
    Splits tabs and creates new tab objects.

    Args:
        part: Part object with tabs
        split_cfg: Configuration for surface separation

    Returns:
        Tuple of (modified Part object, list of split groups)
        - Part object with split tabs
        - split_groups: List of lists, where each inner list contains tab_ids from same split
    """
    # Import here to avoid circular dependency
    import sys
    sys.path.insert(0, '/mnt/user-data/outputs')
    from src.hgen_sm.determine_sequences.surface_separation import auto_split_rectangles_by_mounts
    from src.hgen_sm.data import Mount

    # Also need Rectangle and Tab classes
    # Assuming these are available in the scope
    from src.hgen_sm.data import Rectangle, Tab

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

    # Apply splitting (returns tuple now)
    split_rects, split_groups_indices = auto_split_rectangles_by_mounts(
        rect_dicts,
        min_mounts_for_split=min_mounts_for_split,
        mounts_per_surface=mounts_per_surface,
        split_along=split_along,
        gap_width=gap_width,
        verbose=verbose
    )

    # If no splitting occurred, return original part
    if len(split_rects) == len(rect_dicts):
        return part, []

    # Create new tabs from split rectangles
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

    # Convert split_groups_indices to tab_ids
    split_groups_tab_ids = []
    for group_indices in split_groups_indices:
        group_tab_ids = [str(idx) for idx in group_indices]
        split_groups_tab_ids.append(group_tab_ids)

    # Update part with new tabs
    part.tabs = new_tabs

    return part, split_groups_tab_ids


# Example configuration for your config.yaml:
"""
surface_separation:
  auto_split: true                # Enable automatic splitting
  min_mounts_for_split: 2         # Split if >= 2 mounts on one surface
  mounts_per_surface: 1           # Target: 1 mount per surface after split
  split_along: 'auto'             # 'AB', 'AC', or 'auto'
  gap_width: 2.0                  # Gap width between split surfaces
  verbose: true                   # Print split information

topologies:
  simple_topology: false          # Linear chain (original behavior)
  tree_topology: true             # Enable tree structures (new!)
  # Future: star_topology, custom_topology, etc.

verbose: true                     # Global verbose flag
"""
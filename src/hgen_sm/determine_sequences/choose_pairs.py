from typing import List, Dict, Set, Tuple
from itertools import combinations
import copy

from .surface_separation import separate_surfaces, are_siblings


def determine_sequences(part, cfg):
    """
    Determine the assembly topology (how tabs should be connected with bends).

    This function:
    1. Optionally generates sequences for the original (unseparated) part
    2. Performs surface separation if enabled (splits tabs with multiple mounts)
    3. Generates sequences of tab pairs for assembly
    4. Ensures sibling surfaces (split from same original) are not directly connected

    Args:
        part: Part object containing tabs
        cfg: Configuration dictionary

    Returns:
        List of (part, sequences) tuples, where:
        - part: The Part object (original or with separated surfaces)
        - sequences: List of sequences for that part variant
    """
    sep_cfg = cfg.get('surface_separation', {})
    auto_split = sep_cfg.get('auto_split', True)
    include_unseparated = sep_cfg.get('include_unseparated', False)

    variants = []

    # Check if separation would actually split anything
    will_split = False
    if auto_split:
        min_screws = sep_cfg.get('min_screws_for_split', 2)
        for tab in part.tabs.values():
            if hasattr(tab, 'mounts') and tab.mounts is not None:
                if len(tab.mounts) >= min_screws:
                    will_split = True
                    break

    # Variant 1: Unseparated (original) part
    if include_unseparated and will_split:
        # Deep copy the part to preserve original state
        unseparated_part = part.copy()
        unseparated_sequences = _generate_sequences_for_part(unseparated_part, cfg)
        if unseparated_sequences:
            variants.append((unseparated_part, unseparated_sequences))

    # Variant 2: Separated part (or original if no separation needed)
    if auto_split:
        separated_part = separate_surfaces(part, cfg)
    else:
        separated_part = part

    separated_sequences = _generate_sequences_for_part(separated_part, cfg)
    if separated_sequences:
        variants.append((separated_part, separated_sequences))

    # If no variants generated, return empty list
    if not variants:
        # Fallback: return original part with simple sequence
        fallback_sequences = _generate_sequences_for_part(part, cfg)
        if fallback_sequences:
            variants.append((part, fallback_sequences))

    return variants


def _generate_sequences_for_part(part, cfg):
    """
    Generate sequences for a given part based on topology configuration.

    Args:
        part: Part object containing tabs
        cfg: Configuration dictionary

    Returns:
        List of sequences, where each sequence is a list of [tab_x_id, tab_z_id] pairs
    """
    topo_cfg = cfg.get('topologies', {})
    tabs = part.tabs
    tab_ids: List[str] = [tab.tab_id for tab in tabs.values()]

    sequences = []

    if topo_cfg.get('simple_topology', True):
        # Simple topology: sequential chain (0-1, 1-2, 2-3, ...)
        pair_sequence = generate_simple_sequence(tabs, tab_ids)
        if pair_sequence:
            sequences.append(pair_sequence)

    if topo_cfg.get('tree_topology', False):
        # Tree topology: all valid pairs, allowing multiple connections per tab
        tree_sequences = generate_tree_sequences(tabs, tab_ids)
        sequences.extend(tree_sequences)

    if topo_cfg.get('all_pairs', False):
        # All pairs: generate all valid pairs as a single sequence
        all_pairs_sequence = generate_all_valid_pairs(tabs, tab_ids)
        if all_pairs_sequence:
            sequences.append(all_pairs_sequence)

    # If no topology selected or all failed, use simple as fallback
    if not sequences:
        pair_sequence = generate_simple_sequence(tabs, tab_ids)
        if pair_sequence:
            sequences.append(pair_sequence)

    return sequences


def generate_simple_sequence(tabs: dict, tab_ids: List[str]) -> List[List[str]]:
    """
    Generate a simple sequential topology ensuring all tabs are connected.

    Split surfaces (siblings) cannot connect directly to each other, but must
    connect through a non-sibling "bridge" tab. For example, if tab 0 splits
    into 0_0 and 0_1, and tab 1 exists, the sequence would be:
    [(0_0, 1), (1, 0_1)] - both siblings connect to tab 1.

    This uses a spanning tree approach to guarantee all tabs are connected
    while respecting the sibling constraint.

    Args:
        tabs: Dictionary of tab_id -> Tab objects
        tab_ids: List of tab IDs in order

    Returns:
        List of [tab_x_id, tab_z_id] pairs forming the sequence
    """
    if len(tab_ids) < 2:
        return []

    # Build valid pairs (non-sibling connections only)
    valid_pairs = []
    for t1, t2 in combinations(tab_ids, 2):
        if not are_siblings(tabs[t1], tabs[t2]):
            valid_pairs.append((t1, t2))

    if not valid_pairs:
        return []

    # Find a good starting tab (prefer non-split tabs as they can bridge siblings)
    start_tab = tab_ids[0]
    for tab_id in tab_ids:
        tab = tabs[tab_id]
        # A tab that wasn't split (original_id equals tab_id) makes a good bridge
        if getattr(tab, 'original_id', None) == tab_id or tab.original_id is None:
            start_tab = tab_id
            break

    # Build spanning tree to connect all tabs
    tree = build_spanning_tree(start_tab, tab_ids, valid_pairs, tabs)

    return [[p[0], p[1]] for p in tree]


def generate_all_valid_pairs(tabs: dict, tab_ids: List[str]) -> List[List[str]]:
    """
    Generate all valid pairs of tabs (excluding siblings).

    This allows any tab to connect to any other tab (except siblings),
    creating a fully connected graph of possibilities.

    Args:
        tabs: Dictionary of tab_id -> Tab objects
        tab_ids: List of tab IDs

    Returns:
        List of [tab_x_id, tab_z_id] pairs
    """
    if len(tab_ids) < 2:
        return []

    pair_sequence = []

    # Generate all combinations of 2 tabs
    for tab_x_id, tab_z_id in combinations(tab_ids, 2):
        tab_x = tabs[tab_x_id]
        tab_z = tabs[tab_z_id]

        # Skip sibling pairs
        if are_siblings(tab_x, tab_z):
            continue

        pair = [tab_x_id, tab_z_id]
        pair_sequence.append(pair)

    return pair_sequence


def generate_tree_sequences(tabs: dict, tab_ids: List[str]) -> List[List[List[str]]]:
    """
    Generate multiple tree topology sequences.

    Each tree topology is a spanning tree of valid connections.
    This generates different possible spanning trees to explore
    various assembly configurations.

    A tree topology allows:
    - One tab to connect to multiple other tabs
    - No cycles in the connection graph
    - All tabs are connected

    Args:
        tabs: Dictionary of tab_id -> Tab objects
        tab_ids: List of tab IDs

    Returns:
        List of sequences, each sequence is a list of [tab_x_id, tab_z_id] pairs
    """
    if len(tab_ids) < 2:
        return []

    # Get all valid pairs
    valid_pairs = []
    for tab_x_id, tab_z_id in combinations(tab_ids, 2):
        tab_x = tabs[tab_x_id]
        tab_z = tabs[tab_z_id]
        if not are_siblings(tab_x, tab_z):
            valid_pairs.append((tab_x_id, tab_z_id))

    if not valid_pairs:
        return []

    # Generate spanning trees using different root tabs
    sequences = []

    for root_id in tab_ids:
        # Build a spanning tree starting from this root
        tree = build_spanning_tree(root_id, tab_ids, valid_pairs, tabs)
        if tree and len(tree) == len(tab_ids) - 1:  # Valid spanning tree
            # Convert to list format
            pair_list = [[p[0], p[1]] for p in tree]
            if pair_list not in sequences:  # Avoid duplicates
                sequences.append(pair_list)

    return sequences


def build_spanning_tree(root_id: str, tab_ids: List[str],
                        valid_pairs: List[Tuple[str, str]],
                        tabs: dict) -> List[Tuple[str, str]]:
    """
    Build a spanning tree starting from a root node using BFS.

    Args:
        root_id: Starting tab ID
        tab_ids: All tab IDs
        valid_pairs: List of valid (non-sibling) pairs
        tabs: Dictionary of tab_id -> Tab objects

    Returns:
        List of (tab_x_id, tab_z_id) tuples forming the tree edges
    """
    # Build adjacency list from valid pairs
    adjacency: Dict[str, Set[str]] = {tid: set() for tid in tab_ids}
    for t1, t2 in valid_pairs:
        adjacency[t1].add(t2)
        adjacency[t2].add(t1)

    # BFS to build spanning tree
    visited = {root_id}
    queue = [root_id]
    tree_edges = []

    while queue:
        current = queue.pop(0)
        for neighbor in adjacency[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
                tree_edges.append((current, neighbor))

    return tree_edges


def can_connect(tab1, tab2) -> bool:
    """
    Check if two tabs can be connected.

    Tabs cannot be connected if:
    - They are the same tab
    - They are siblings (split from the same original surface)

    Args:
        tab1, tab2: Tab objects to check

    Returns:
        True if tabs can be connected
    """
    if tab1.tab_id == tab2.tab_id:
        return False

    if are_siblings(tab1, tab2):
        return False

    return True


def get_connection_graph(tabs: dict) -> Dict[str, List[str]]:
    """
    Build a connection graph showing which tabs can connect to which.

    Useful for visualization and debugging.

    Args:
        tabs: Dictionary of tab_id -> Tab objects

    Returns:
        Dictionary mapping each tab_id to list of connectable tab_ids
    """
    tab_ids = list(tabs.keys())
    graph: Dict[str, List[str]] = {tid: [] for tid in tab_ids}

    for t1, t2 in combinations(tab_ids, 2):
        if can_connect(tabs[t1], tabs[t2]):
            graph[t1].append(t2)
            graph[t2].append(t1)

    return graph

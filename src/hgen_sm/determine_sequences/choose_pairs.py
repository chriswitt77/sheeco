from typing import List, Dict, Set, Tuple
from itertools import combinations
import copy

from .surface_separation import separate_surfaces, are_siblings


def get_tab_structure_signature(part, split_direction=None) -> str:
    """
    Generate a unique signature for the tab structure.

    Returns a string representing the sorted set of tab IDs. When split_direction
    is provided (for split_along='both'), includes the direction to distinguish
    geometrically different AB vs AC splits that have the same tab IDs.

    Examples:
        ["0", "1"] → "0,1"
        ["0", "1_0", "1_1"] → "0,1_0,1_1"
        ["0_0", "0_1", "1"] with split_direction='AB' → "0_0,0_1,1[AB]"
        ["0_0", "0_1", "1"] with split_direction='AC' → "0_0,0_1,1[AC]"

    Args:
        part: Part object containing tabs
        split_direction: Optional split direction ('AB' or 'AC') to distinguish
                        geometrically different splits with same tab IDs

    Returns:
        Comma-separated sorted tab IDs with optional direction suffix
    """
    base_signature = ",".join(sorted(part.tabs.keys()))
    if split_direction:
        return f"{base_signature}[{split_direction}]"
    return base_signature


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
    seen_structures = set()  # Track unique tab structures to avoid duplicates

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
        unseparated_signature = get_tab_structure_signature(unseparated_part)

        # Only add if this structure hasn't been seen
        if unseparated_signature not in seen_structures:
            unseparated_sequences = _generate_sequences_for_part(unseparated_part, cfg)
            if unseparated_sequences:
                variants.append((unseparated_part, unseparated_sequences))
                seen_structures.add(unseparated_signature)

    # Variant 2+: Separated part(s) (or original if no separation needed)
    if auto_split:
        split_along = sep_cfg.get('split_along', 'auto')

        if split_along == 'both':
            # Generate variants for BOTH AB and AC split directions
            for direction in ['AB', 'AC']:
                # Create a modified config with specific split direction
                cfg_copy = copy.deepcopy(cfg)
                cfg_copy['surface_separation']['split_along'] = direction

                # Create a fresh part copy for this direction
                part_copy = part.copy()
                separated_part = separate_surfaces(part_copy, cfg_copy, verbose=True)

                # Only include direction if actual splitting occurred (detected by underscore in tab IDs)
                # This distinguishes geometrically different AB vs AC splits
                has_split_tabs = any('_' in tid for tid in separated_part.tabs.keys())
                separated_signature = get_tab_structure_signature(
                    separated_part,
                    split_direction=direction if has_split_tabs else None
                )

                if separated_signature not in seen_structures:
                    separated_sequences = _generate_sequences_for_part(separated_part, cfg)
                    if separated_sequences:
                        variants.append((separated_part, separated_sequences))
                        seen_structures.add(separated_signature)
        else:
            # Original behavior: single separation direction
            separated_part = separate_surfaces(part, cfg)
            separated_signature = get_tab_structure_signature(separated_part)

            if separated_signature not in seen_structures:
                separated_sequences = _generate_sequences_for_part(separated_part, cfg)
                if separated_sequences:
                    variants.append((separated_part, separated_sequences))
                    seen_structures.add(separated_signature)
    else:
        separated_part = part
        separated_signature = get_tab_structure_signature(separated_part)

        if separated_signature not in seen_structures:
            separated_sequences = _generate_sequences_for_part(separated_part, cfg)
            if separated_sequences:
                variants.append((separated_part, separated_sequences))
                seen_structures.add(separated_signature)

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
        tree_sequences = generate_tree_sequences(tabs, tab_ids, cfg)
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

    # Validate sibling connections: siblings can connect only if they have external connections
    sep_cfg = cfg.get('surface_separation', {})
    allow_sibling_connections = sep_cfg.get('allow_sibling_connections', True)

    if allow_sibling_connections:
        # Filter sequences to only include valid sibling connection patterns
        validated_sequences = []
        for seq in sequences:
            if validate_sibling_connections(seq, tabs):
                validated_sequences.append(seq)
        return validated_sequences
    else:
        # Strict mode: no sibling connections allowed (legacy behavior)
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

    # Build all pairs (including siblings - validation happens at sequence level)
    valid_pairs = []
    for t1, t2 in combinations(tab_ids, 2):
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

        # Allow all pairs (including siblings - validation happens at sequence level)

        pair = [tab_x_id, tab_z_id]
        pair_sequence.append(pair)

    return pair_sequence


class UnionFind:
    """
    Union-Find (Disjoint Set Union) data structure for cycle detection.

    Used to efficiently detect cycles when building spanning trees.
    """
    def __init__(self, elements: List[str]):
        """Initialize with each element in its own set."""
        self.parent = {elem: elem for elem in elements}
        self.rank = {elem: 0 for elem in elements}

    def find(self, x: str) -> str:
        """Find the root of the set containing x (with path compression)."""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]

    def union(self, x: str, y: str) -> bool:
        """
        Union the sets containing x and y.

        Returns:
            True if union was performed (no cycle), False if already in same set (would create cycle)
        """
        root_x = self.find(x)
        root_y = self.find(y)

        if root_x == root_y:
            return False  # Already in same set - would create cycle

        # Union by rank
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1

        return True

    def copy(self):
        """Create a deep copy of the Union-Find structure."""
        new_uf = UnionFind([])
        new_uf.parent = self.parent.copy()
        new_uf.rank = self.rank.copy()
        return new_uf


def generate_all_spanning_trees(tab_ids: List[str],
                                  valid_pairs: List[Tuple[str, str]]) -> List[List[Tuple[str, str]]]:
    """
    Generate ALL possible spanning trees from valid pairs using recursive backtracking.

    Uses Union-Find for efficient cycle detection during tree construction.

    Args:
        tab_ids: List of all tab IDs (nodes)
        valid_pairs: List of all valid edge pairs

    Returns:
        List of spanning trees, where each tree is a list of edge tuples

    Algorithm:
        - A spanning tree has exactly (n-1) edges for n nodes
        - Use recursive backtracking to try all combinations of edges
        - Use Union-Find to detect cycles efficiently
        - Only return trees that connect all nodes
    """
    n = len(tab_ids)
    if n < 2:
        return []

    target_edges = n - 1  # A spanning tree has n-1 edges
    all_trees = []

    def backtrack(edge_idx: int, current_tree: List[Tuple[str, str]], uf: UnionFind):
        """
        Recursive backtracking to build spanning trees.

        Args:
            edge_idx: Current index in valid_pairs list
            current_tree: Edges selected so far
            uf: Union-Find structure tracking connectivity
        """
        # Base case: we have a complete spanning tree
        if len(current_tree) == target_edges:
            # Verify all nodes are connected (all in same set)
            root = uf.find(tab_ids[0])
            if all(uf.find(tid) == root for tid in tab_ids):
                all_trees.append(current_tree[:])  # Add copy
            return

        # Pruning: if we can't reach target_edges even with all remaining edges
        remaining_edges = len(valid_pairs) - edge_idx
        if len(current_tree) + remaining_edges < target_edges:
            return

        # Try remaining edges
        for i in range(edge_idx, len(valid_pairs)):
            edge = valid_pairs[i]
            t1, t2 = edge

            # Try adding this edge
            uf_copy = uf.copy()
            if uf_copy.union(t1, t2):  # No cycle created
                current_tree.append(edge)
                backtrack(i + 1, current_tree, uf_copy)
                current_tree.pop()

    # Start backtracking
    initial_uf = UnionFind(tab_ids)
    backtrack(0, [], initial_uf)

    return all_trees


def get_degree_sequence(tree: List[Tuple[str, str]]) -> tuple:
    """
    Get sorted degree sequence of tree nodes.

    The degree sequence characterizes the branching structure of a tree.
    Different degree sequences indicate different structural patterns.

    Args:
        tree: List of edge tuples

    Returns:
        Tuple of sorted node degrees
    """
    node_degrees = {}
    for t1, t2 in tree:
        node_degrees[t1] = node_degrees.get(t1, 0) + 1
        node_degrees[t2] = node_degrees.get(t2, 0) + 1
    return tuple(sorted(node_degrees.values()))


def get_tree_diameter(tree: List[Tuple[str, str]], all_nodes: List[str]) -> int:
    """
    Get diameter (longest path) of tree using BFS.

    The diameter represents how "chain-like" vs "bushy" a tree is.

    Args:
        tree: List of edge tuples
        all_nodes: List of all node IDs

    Returns:
        Diameter (maximum distance between any two nodes)
    """
    # Build adjacency list
    adj = {node: [] for node in all_nodes}
    for t1, t2 in tree:
        adj[t1].append(t2)
        adj[t2].append(t1)

    def bfs_farthest(start: str) -> Tuple[str, int]:
        """BFS to find farthest node and distance."""
        visited = {start}
        queue = [(start, 0)]
        farthest = (start, 0)

        while queue:
            node, dist = queue.pop(0)
            if dist > farthest[1]:
                farthest = (node, dist)

            for neighbor in adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1))

        return farthest

    # Two BFS: first from arbitrary node, then from farthest node found
    farthest_from_start = bfs_farthest(all_nodes[0])
    farthest_from_farthest = bfs_farthest(farthest_from_start[0])

    return farthest_from_farthest[1]


def get_edge_set(tree: List[Tuple[str, str]]) -> Set[Tuple[str, str]]:
    """
    Get normalized edge set (smaller ID first).

    Args:
        tree: List of edge tuples

    Returns:
        Set of normalized edges
    """
    edges = set()
    for t1, t2 in tree:
        edge = (t1, t2) if t1 < t2 else (t2, t1)
        edges.add(edge)
    return edges


def compute_tree_distance(tree1: List[Tuple[str, str]],
                          tree2: List[Tuple[str, str]],
                          all_nodes: List[str]) -> float:
    """
    Compute distance between two trees using multiple metrics.

    Combines three metrics:
    1. Degree sequence distance - captures branching patterns (star vs balanced)
    2. Diameter difference - captures chain-like vs bushy structure
    3. Edge overlap (Jaccard distance) - captures structural similarity

    Args:
        tree1: First tree
        tree2: Second tree
        all_nodes: List of all node IDs

    Returns:
        Composite distance score (higher = more different)
    """
    # Metric 1: Degree sequence distance (L1 norm)
    deg1 = get_degree_sequence(tree1)
    deg2 = get_degree_sequence(tree2)
    degree_dist = sum(abs(d1 - d2) for d1, d2 in zip(deg1, deg2))

    # Metric 2: Diameter difference
    diam1 = get_tree_diameter(tree1, all_nodes)
    diam2 = get_tree_diameter(tree2, all_nodes)
    diameter_dist = abs(diam1 - diam2)

    # Metric 3: Edge overlap (Jaccard distance)
    edges1 = get_edge_set(tree1)
    edges2 = get_edge_set(tree2)

    intersection = len(edges1 & edges2)
    union = len(edges1 | edges2)
    jaccard_similarity = intersection / union if union > 0 else 0
    edge_dist = 1 - jaccard_similarity  # Convert to distance

    # Composite distance (weighted combination)
    # Normalize each component to [0, 1] range
    n = len(all_nodes)
    normalized_degree = degree_dist / (2 * (n - 1))  # Max degree distance
    normalized_diameter = diameter_dist / (n - 1)  # Max diameter difference
    normalized_edge = edge_dist  # Already in [0, 1]

    # Weighted sum (equal weights - can be tuned)
    distance = normalized_degree + normalized_diameter + normalized_edge

    return distance


def select_diverse_trees(all_trees: List[List[Tuple[str, str]]],
                         all_nodes: List[str],
                         k: int) -> List[List[Tuple[str, str]]]:
    """
    Select k most diverse trees using greedy MaxMin algorithm.

    Algorithm:
    1. Start with arbitrary tree (first one)
    2. Iteratively add tree that maximizes minimum distance to already-selected trees
    3. This ensures good coverage of the topology space

    Time complexity: O(n² · m) where n = number of trees, m = distance computation cost
    This is acceptable for ~1000 trees.

    Args:
        all_trees: List of all spanning trees
        all_nodes: List of all node IDs
        k: Number of diverse trees to select

    Returns:
        List of k most diverse trees
    """
    if k >= len(all_trees):
        return all_trees

    selected = []
    remaining = list(range(len(all_trees)))

    # Start with first tree
    selected.append(0)
    remaining.remove(0)

    # Iteratively select most diverse tree
    for i in range(1, k):
        max_min_dist = -1
        best_tree_idx = -1

        # For each remaining tree, compute min distance to selected trees
        for rem_idx in remaining:
            min_dist_to_selected = float('inf')

            for sel_idx in selected:
                dist = compute_tree_distance(
                    all_trees[rem_idx],
                    all_trees[sel_idx],
                    all_nodes
                )
                min_dist_to_selected = min(min_dist_to_selected, dist)

            # Select tree that maximizes this minimum distance
            if min_dist_to_selected > max_min_dist:
                max_min_dist = min_dist_to_selected
                best_tree_idx = rem_idx

        selected.append(best_tree_idx)
        remaining.remove(best_tree_idx)

    return [all_trees[idx] for idx in selected]


def canonicalize_sequence(sequence: List[List[str]]) -> tuple:
    """
    Convert a sequence to a canonical form for topology equivalence checking.

    Two sequences are topologically equivalent if they produce the same
    undirected connectivity graph. This function creates a canonical
    representation by:
    1. Converting each pair to an undirected edge (smaller ID first)
    2. Sorting all edges lexicographically
    3. Returning as a tuple for use as a dictionary key

    Args:
        sequence: List of [tab_x_id, tab_z_id] pairs

    Returns:
        Canonical tuple of sorted edges, e.g. (('0', '1'), ('0', '2'))

    Examples:
        [['0', '1']] → (('0', '1'),)
        [['1', '0']] → (('0', '1'),)  # Same as above
        [['0', '1'], ['0', '2']] → (('0', '1'), ('0', '2'))
        [['1', '0'], ['2', '0']] → (('0', '1'), ('0', '2'))  # Same as above
    """
    # Normalize each edge (smaller ID first) and collect as set
    edges = set()
    for pair in sequence:
        t1, t2 = pair[0], pair[1]
        # Normalize: always put smaller ID first
        edge = (t1, t2) if t1 < t2 else (t2, t1)
        edges.add(edge)

    # Sort edges for canonical ordering
    return tuple(sorted(edges))


def generate_tree_sequences(tabs: dict, tab_ids: List[str], cfg: dict = None) -> List[List[List[str]]]:
    """
    Generate multiple tree topology sequences.

    Each tree topology is a spanning tree of valid connections.
    This generates ALL possible spanning trees to explore various
    assembly configurations.

    A tree topology allows:
    - One tab to connect to multiple other tabs
    - No cycles in the connection graph
    - All tabs are connected

    Args:
        tabs: Dictionary of tab_id -> Tab objects
        tab_ids: List of tab IDs
        cfg: Configuration dictionary (optional, for max_tree_topologies)

    Returns:
        List of sequences, each sequence is a list of [tab_x_id, tab_z_id] pairs
    """
    if len(tab_ids) < 2:
        return []

    # Get all pairs (including siblings - validation happens at sequence level)
    valid_pairs = []
    for tab_x_id, tab_z_id in combinations(tab_ids, 2):
        valid_pairs.append((tab_x_id, tab_z_id))

    if not valid_pairs:
        return []

    # Generate ALL possible spanning trees
    all_trees = generate_all_spanning_trees(tab_ids, valid_pairs)

    # Apply diversity selection if configured
    topo_cfg = cfg.get('topologies', {}) if cfg else {}
    max_topologies = topo_cfg.get('max_tree_topologies', None)

    if max_topologies and max_topologies < len(all_trees):
        print(f"Selecting {max_topologies} most diverse tree topologies from {len(all_trees)} total...")
        all_trees = select_diverse_trees(all_trees, tab_ids, max_topologies)
        print(f"Selection complete.")

    # Use canonical forms to filter out topologically equivalent trees
    sequences = []
    seen_topologies = set()

    for tree in all_trees:
        # Convert to list format
        pair_list = [[p[0], p[1]] for p in tree]

        # Check if this topology is already seen
        canonical = canonicalize_sequence(pair_list)
        if canonical not in seen_topologies:
            seen_topologies.add(canonical)
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


def validate_sibling_connections(sequence: List[List[str]], tabs: dict) -> bool:
    """
    Validate that sibling tabs have external connections if they connect to each other.

    Rules:
    - Siblings CAN connect to each other
    - BUT both siblings must also connect to at least one non-sibling tab
    - This prevents "isolated islands" of only siblings

    Args:
        sequence: List of [tab_x_id, tab_z_id] pairs
        tabs: Dictionary of tab_id -> Tab objects

    Returns:
        True if sequence is valid, False otherwise

    Example valid:
        [['0', '2_0'], ['2_0', '2_1'], ['2_1', '1']]
        Both 2_0 and 2_1 have external connections (0 and 1)

    Example invalid:
        [['2_0', '2_1']]
        Siblings only connect to each other
    """
    # Build connection graph: tab_id -> set of connected tab_ids
    connections = {}
    for pair in sequence:
        tab_x_id, tab_z_id = pair
        if tab_x_id not in connections:
            connections[tab_x_id] = set()
        if tab_z_id not in connections:
            connections[tab_z_id] = set()
        connections[tab_x_id].add(tab_z_id)
        connections[tab_z_id].add(tab_x_id)

    # Find all sibling groups
    sibling_groups = {}  # original_id -> list of tab_ids
    for tab_id, tab in tabs.items():
        original_id = getattr(tab, 'original_id', None)
        if original_id and original_id != tab_id:
            # This is a split tab
            if original_id not in sibling_groups:
                sibling_groups[original_id] = []
            sibling_groups[original_id].append(tab_id)

    # For each sibling group, check if siblings connect to each other
    for original_id, sibling_ids in sibling_groups.items():
        # Check if any siblings in this group connect to each other
        siblings_connect = False
        for sib1 in sibling_ids:
            for sib2 in sibling_ids:
                if sib1 != sib2 and sib1 in connections and sib2 in connections[sib1]:
                    siblings_connect = True
                    break
            if siblings_connect:
                break

        if siblings_connect:
            # Siblings connect to each other - verify ALL siblings have external connections
            for sib_id in sibling_ids:
                if sib_id not in connections:
                    # This sibling isn't in the sequence at all
                    continue

                # Check if this sibling has at least one non-sibling connection
                has_external = False
                for connected_id in connections[sib_id]:
                    # Check if connected tab is NOT a sibling
                    if connected_id not in sibling_ids:
                        has_external = True
                        break

                if not has_external:
                    # This sibling only connects to other siblings - invalid!
                    return False

    return True


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

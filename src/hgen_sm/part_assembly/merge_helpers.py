from typing import Dict, Any, Optional, List, Set, Tuple
import numpy as np
from collections import OrderedDict
from itertools import combinations

def extract_tabs_from_segments(tab_id, segments):
    tab_id 
    segments
    tabs = []
    for segment in segments:
        for tab in segment.tabs:
            if segment.tabs[tab].tab_id == tab_id:
                tabs.append(segment.tabs[tab])
    return tabs


def merge_points(tabs: List[Any]) -> Optional[Dict[str, np.ndarray]]:
    """
    Merges ordered tab geometry based on synchronization points (A, B, C, D).
    Fails if both tabs simultaneously introduce different non-standard points.
    """
    if len(tabs) != 2:
        return None

    # Constants and Initialization
    STD_PTS: Set[str] = {'A', 'B', 'C', 'D'}
    geom_a: Dict[str, np.ndarray] = tabs[0].points
    geom_b: Dict[str, np.ndarray] = tabs[1].points

    ids_a: List[str] = list(geom_a.keys())
    ids_b: List[str] = list(geom_b.keys())

    merged_ids: List[str] = []
    idx_a, idx_b = 0, 0

    escape_counter = 0 

    # --- Core Merge Logic ---
    while idx_a < len(ids_a) or idx_b < len(ids_b):
        if escape_counter >= 30:
            return None
        escape_counter += 1
        id_a = ids_a[idx_a] if idx_a < len(ids_a) else None
        id_b = ids_b[idx_b] if idx_b < len(ids_b) else None

        # Stop condition
        if id_a is None and id_b is None:
            break

        # Check if the current points are standard or non-standard
        is_std_a = id_a in STD_PTS
        is_std_b = id_b in STD_PTS
        
        # --- Rule 1: Synchronization Point (A, B, C, D) ---
        if is_std_a and is_std_b and id_a == id_b:
            # If both are the same standard point, consume it from both lists
            merged_ids.append(id_a)
            idx_a += 1
            idx_b += 1
            continue

        # --- Rule 2: Tab A has a unique sequence, Tab B is synchronized or finished ---
        if id_a is not None and not is_std_a and (is_std_b or id_b is None):
            # Tab A is ahead, consume A's unique sequence until a standard point is hit
            while id_a is not None and not is_std_a:

                merged_ids.append(id_a)
                idx_a += 1
                id_a = ids_a[idx_a] if idx_a < len(ids_a) else None
                is_std_a = id_a in STD_PTS
            continue # Loop will re-evaluate, hit Rule 1, 3, or finish

        # --- Rule 3: Tab B has a unique sequence, Tab A is synchronized or finished ---
        if id_b is not None and not is_std_b and (is_std_a or id_a is None):
            # Tab B is ahead, consume B's unique sequence until a standard point is hit
            while id_b is not None and not is_std_b:

                merged_ids.append(id_b)
                idx_b += 1
                id_b = ids_b[idx_b] if idx_b < len(ids_b) else None
                is_std_b = id_b in STD_PTS
            continue # Loop will re-evaluate, hit Rule 1, 2, or finish

        # --- Rule 4: Conflict (Both tabs have different, non-standard points) ---
        if id_a is not None and id_b is not None and not is_std_a and not is_std_b and id_a != id_b:
            return None # Both introduce a unique, differing sequence

        # --- Rule 5: Catch remaining cases (e.g., one list finishes after non-standard) ---
        # If one list is finished, consume the rest of the other
        if id_a is None and id_b is not None:
             merged_ids.append(id_b)
             idx_b += 1
             continue
        if id_b is None and id_a is not None:
             merged_ids.append(id_a)
             idx_a += 1
             continue

        # Final safety catch for non-matching standard points (A vs B)
        if id_a != id_b and is_std_a and is_std_b:
             return None

    # --- Rebuild Final Geometry Dictionary ---
    final_geometry: Dict[str, np.ndarray] = {}

    for point_id in merged_ids:
        # Prioritize coordinates from Tab A, use Tab B as fallback
        if point_id in geom_a:
            final_geometry[point_id] = geom_a[point_id]
        elif point_id in geom_b:
            final_geometry[point_id] = geom_b[point_id]

    # OVERLAP DETECTION: Check for duplicate flange points at same location
    # This happens when two connections create flanges that share endpoints
    if len(final_geometry) > 4:  # More than just corners
        # Extract corner points
        corners = {k: v for k, v in final_geometry.items() if k in ['A', 'B', 'C', 'D']}

        if len(corners) == 4:  # Valid rectangle
            # Group points by edge
            edge_points = {
                'AB': [],
                'BC': [],
                'CD': [],
                'DA': []
            }

            for point_name, coord in final_geometry.items():
                if point_name not in ['A', 'B', 'C', 'D']:
                    edge = detect_edge(coord, corners)
                    if edge is not None:
                        edge_points[edge].append((point_name, coord))

            # Detect overlaps
            overlaps = detect_overlapping_flanges(edge_points, corners)

            if overlaps:
                # Remove duplicate points, keeping only the first occurrence
                points_to_remove = set()

                for collision_location, coincident_points in overlaps:
                    if len(coincident_points) < 2:
                        continue

                    # Keep first, remove others
                    for i in range(1, len(coincident_points)):
                        _, point_name, _ = coincident_points[i]
                        points_to_remove.add(point_name)

                # Remove duplicate points from final geometry
                for point_name in points_to_remove:
                    if point_name in final_geometry:
                        del final_geometry[point_name]

    if len(final_geometry) > 12:
        print(final_geometry)
    return final_geometry


def detect_edge(point: np.ndarray, corners: Dict[str, np.ndarray], tolerance: float = 1e-6) -> Optional[str]:
    """
    Detects which edge (AB, BC, CD, DA) a point lies on based on its 3D position.
    Points can lie on edge extensions (beyond corner points) for flanges that extend past boundaries.

    Args:
        point: 3D coordinate of the point
        corners: Dictionary with keys A, B, C, D containing corner coordinates
        tolerance: Distance tolerance for considering a point on an edge

    Returns:
        Edge name ('AB', 'BC', 'CD', 'DA') or None if point doesn't lie on any edge
    """
    edges = [
        ('AB', corners['A'], corners['B']),
        ('BC', corners['B'], corners['C']),
        ('CD', corners['C'], corners['D']),
        ('DA', corners['D'], corners['A'])
    ]

    best_match = None
    min_distance = float('inf')

    for edge_name, start, end in edges:
        # Vector from start to end of edge
        edge_vec = end - start
        edge_length = np.linalg.norm(edge_vec)

        if edge_length < tolerance:
            continue  # Degenerate edge

        edge_dir = edge_vec / edge_length

        # Vector from start to point
        point_vec = point - start

        # Project point onto edge direction (allows extensions beyond segment)
        projection_length = np.dot(point_vec, edge_dir)

        # Calculate perpendicular distance from point to edge line
        projection_point = start + projection_length * edge_dir
        perp_distance = np.linalg.norm(point - projection_point)

        # Track the closest edge (in case point is near a corner)
        if perp_distance < min_distance:
            min_distance = perp_distance
            best_match = edge_name

    # Accept the closest edge if within tolerance
    if min_distance < tolerance:
        return best_match

    return None


def sort_points_along_edge(points: List[Tuple[str, np.ndarray]],
                           edge_start: np.ndarray,
                           edge_end: np.ndarray) -> List[Tuple[str, np.ndarray]]:
    """
    Sorts points along an edge by their distance from the edge start.

    Args:
        points: List of (point_name, coordinate) tuples
        edge_start: Starting corner coordinate of the edge
        edge_end: Ending corner coordinate of the edge

    Returns:
        Sorted list of (point_name, coordinate) tuples
    """
    edge_vec = edge_end - edge_start
    edge_length = np.linalg.norm(edge_vec)

    if edge_length < 1e-6:
        return points  # Degenerate edge, return unsorted

    edge_dir = edge_vec / edge_length

    # Calculate distance from edge_start for each point
    points_with_distance = []
    for point_name, coord in points:
        point_vec = coord - edge_start
        distance = np.dot(point_vec, edge_dir)
        points_with_distance.append((distance, point_name, coord))

    # Sort by distance from edge start
    points_with_distance.sort(key=lambda x: x[0])

    # Return sorted points (without distance)
    return [(name, coord) for _, name, coord in points_with_distance]


def detect_overlapping_flanges(edge_points: Dict[str, List[Tuple[str, np.ndarray]]],
                                corners: Dict[str, np.ndarray],
                                tolerance: float = 0.5) -> List[Tuple[np.ndarray, List[Tuple[str, str, np.ndarray]]]]:
    """
    Detect spatially coincident BP points from different flanges that create non-manifold geometry.

    When multiple connections create flanges on parallel or opposite edges, their BP points
    can occupy the same spatial location. This creates non-manifold vertices where the
    perimeter has multiple possible paths.

    Example: Tab 1 has two connections:
    - Connection 1-10: BP at [0, 0, 70] and [0, 80, 70] on edge BC
    - Connection 1-12: BP at [0, 0, 10] and [0, 80, 10] on edge DA
    At y=0 and y=80, there are two BP points with the same (x,y) but different z.

    Args:
        edge_points: Dictionary mapping edge names to lists of (point_name, coordinate) tuples
        corners: Dictionary of corner positions
        tolerance: Distance threshold for considering points coincident (in x,y space)

    Returns:
        List of (collision_location, bp_points) tuples where:
        - collision_location: The (x,y,z) location where BPs overlap
        - bp_points: List of (edge_name, point_name, coordinate) tuples for all BP points at this location
    """
    overlaps = []

    # Collect all flange points (both BP and FP) from all edges
    all_flange_points = []
    for edge_name, points in edge_points.items():
        for point_name, coord in points:
            if 'BP' in point_name or 'FP' in point_name:
                all_flange_points.append((edge_name, point_name, coord))

    if len(all_flange_points) < 2:
        return []  # Need at least 2 flange points to have overlap

    # Group flange points by spatial location (within tolerance)
    # We consider points coincident if their 3D distance is within tolerance
    processed = set()

    for i, (edge1, name1, coord1) in enumerate(all_flange_points):
        if i in processed:
            continue

        # Find all other flange points at the same location
        coincident_points = [(edge1, name1, coord1)]

        for j, (edge2, name2, coord2) in enumerate(all_flange_points[i+1:], start=i+1):
            if j in processed:
                continue

            # Check 3D distance
            dist = np.linalg.norm(coord1 - coord2)
            if dist < tolerance:
                coincident_points.append((edge2, name2, coord2))
                processed.add(j)

        # If multiple flange points at same location, record as overlap
        if len(coincident_points) > 1:
            processed.add(i)
            # Use the average position as the collision location
            avg_pos = np.mean([c for _, _, c in coincident_points], axis=0)
            overlaps.append((avg_pos, coincident_points))

    return overlaps


def find_flange_endpoints_at_corner(edge_points: List[Tuple[str, np.ndarray]],
                                     corner_pos: np.ndarray,
                                     tolerance: float = 1.0) -> List[Tuple[str, np.ndarray]]:
    """
    Find flange points (BP/FP) that are near a corner position.

    Returns list of (point_name, coordinate) tuples for points near the corner.
    """
    endpoints = []
    for point_name, coord in edge_points:
        # Check if point is close to corner (within tolerance)
        dist = np.linalg.norm(coord - corner_pos)
        if dist < tolerance:
            endpoints.append((point_name, coord))

    return endpoints


def create_helper_points_for_overlap(edge1: str, edge2: str, corner_id: str,
                                     edge_points: Dict[str, List[Tuple[str, np.ndarray]]],
                                     corners: Dict[str, np.ndarray]) -> List[Tuple[str, np.ndarray]]:
    """
    Create helper points to bridge between two overlapping flanges at a shared corner.

    When two flanges meet at a corner, we need to add edges connecting them to form
    a proper closed perimeter. This finds the BP points from each flange that are
    closest to the corner and returns helper points to connect them.

    Args:
        edge1, edge2: The two adjacent edges with flanges
        corner_id: The shared corner ('A', 'B', 'C', or 'D')
        edge_points: Dictionary mapping edges to their points
        corners: Dictionary of corner positions

    Returns:
        List of (point_name, coordinate) tuples for helper points to insert
    """
    corner_pos = corners[corner_id]

    # Find BP points on each edge near the corner
    # BP points are the outermost flange points
    bp_edge1 = [(name, coord) for name, coord in edge_points[edge1] if 'BP' in name]
    bp_edge2 = [(name, coord) for name, coord in edge_points[edge2] if 'BP' in name]

    if not bp_edge1 or not bp_edge2:
        return []  # One edge doesn't have BP points, no overlap to fix

    # Find the BP point on each edge that's closest to the corner
    bp1_near_corner = min(bp_edge1, key=lambda x: np.linalg.norm(x[1] - corner_pos))
    bp2_near_corner = min(bp_edge2, key=lambda x: np.linalg.norm(x[1] - corner_pos))

    # Check if they're actually at different positions (indicating overlap)
    dist_between_bps = np.linalg.norm(bp1_near_corner[1] - bp2_near_corner[1])

    if dist_between_bps < 0.1:
        return []  # BP points coincide, no overlap

    # Create helper point identifier
    # Extract connection IDs from the BP point names
    # E.g., "BP1_10L" -> connection "10", "BP1_12R" -> connection "12"
    helper_name = f"HELPER_{corner_id}_{bp1_near_corner[0]}_{bp2_near_corner[0]}"

    # The helper point is placed at the corner position itself
    # This creates an edge from BP1 -> corner -> BP2
    helper_points = [(helper_name, corner_pos)]

    return helper_points


def merge_multiple_tabs(tabs: List[Any]) -> Optional[Dict[str, np.ndarray]]:
    """
    Merges multiple tab instances (3+) by grouping points by edge and building perimeter.
    This handles tabs that connect to 3 or more other tabs.

    CRITICAL MANUFACTURABILITY CHECK: Each edge can only be used by ONE connection.
    If multiple connections try to add flanges to the same edge, the part is physically
    impossible to manufacture and the merge is rejected.

    Args:
        tabs: List of tab objects with .points dictionaries

    Returns:
        Merged points dictionary representing the complete perimeter, or None if merge fails
    """
    if len(tabs) < 2:
        return None

    # If only 2 tabs, use the existing pairwise merge
    if len(tabs) == 2:
        return merge_points(tabs)

    # Extract corner points from first tab (should be identical across all tabs)
    corners = {}
    for corner in ['A', 'B', 'C', 'D']:
        if corner not in tabs[0].points:
            return None  # Missing corner - cannot proceed
        corners[corner] = tabs[0].points[corner]

    # Verify all tabs have the same corner positions
    for tab in tabs[1:]:
        for corner in ['A', 'B', 'C', 'D']:
            if corner not in tab.points:
                return None
            if not np.allclose(tab.points[corner], corners[corner], atol=1e-6):
                return None  # Corner mismatch - tabs don't align

    # MANUFACTURABILITY CHECK: Track which tab instance uses which edge
    # Each edge can only be used by ONE connection
    edge_usage = {
        'AB': [],
        'BC': [],
        'CD': [],
        'DA': []
    }

    # For each tab instance, determine which edge it uses
    for tab_idx, tab in enumerate(tabs):
        # Find non-corner points in this tab instance
        non_corner_points = [(name, coord) for name, coord in tab.points.items()
                            if name not in ['A', 'B', 'C', 'D']]

        if not non_corner_points:
            # No flanges on this instance - skip
            continue

        # Detect which edge these points belong to
        # All points from one tab instance should be on the same edge
        edges_used = set()
        for point_name, coord in non_corner_points:
            edge = detect_edge(coord, corners)
            if edge is not None:
                edges_used.add(edge)

        # Check if all points are on the same edge
        if len(edges_used) > 1:
            # Points span multiple edges - this shouldn't happen for a single connection
            # but allow it for now (might be corner case with flange points)
            pass

        # Record which edge(s) this tab instance uses
        for edge in edges_used:
            edge_usage[edge].append(tab_idx)

    # CHECK: Reject if any edge is used by multiple tab instances
    for edge, tab_indices in edge_usage.items():
        if len(tab_indices) > 1:
            # Multiple connections trying to use the same edge - NOT MANUFACTURABLE
            return None

    # Group all non-corner points by which edge they belong to
    edge_points = {
        'AB': [],
        'BC': [],
        'CD': [],
        'DA': []
    }

    for tab in tabs:
        for point_name, coord in tab.points.items():
            if point_name not in ['A', 'B', 'C', 'D']:
                edge = detect_edge(coord, corners)

                if edge is None:
                    # Point doesn't lie on any edge - this shouldn't happen
                    # Log warning but continue
                    print(f"WARNING: Point {point_name} at {coord} doesn't lie on any edge")
                    continue

                # Check if this point is already in the list (avoid duplicates)
                duplicate = False
                for existing_name, existing_coord in edge_points[edge]:
                    if np.allclose(coord, existing_coord, atol=1e-6):
                        duplicate = True
                        break

                if not duplicate:
                    edge_points[edge].append((point_name, coord))

    # Sort points along each edge
    sorted_edge_points = {}
    edge_definitions = {
        'AB': (corners['A'], corners['B']),
        'BC': (corners['B'], corners['C']),
        'CD': (corners['C'], corners['D']),
        'DA': (corners['D'], corners['A'])
    }

    for edge, (start, end) in edge_definitions.items():
        sorted_edge_points[edge] = sort_points_along_edge(edge_points[edge], start, end)

    # Detect and handle overlapping flanges
    overlaps = detect_overlapping_flanges(sorted_edge_points, corners)

    if overlaps:
        # For each overlap (group of coincident points), merge them into a single point
        # Strategy: Keep the first point in the group, remove others from their respective edges
        for collision_location, coincident_points in overlaps:
            if len(coincident_points) < 2:
                continue  # Not really an overlap

            # Remove all other coincident points from their edges
            for i in range(1, len(coincident_points)):
                edge_name, point_name, point_coord = coincident_points[i]

                # Remove this point from its edge list
                sorted_edge_points[edge_name] = [
                    (name, coord) for name, coord in sorted_edge_points[edge_name]
                    if not (name == point_name and np.allclose(coord, point_coord, atol=1e-6))
                ]

    # Build final perimeter by walking edges
    final_geometry = OrderedDict()

    # Start at A
    final_geometry['A'] = corners['A']

    # Add points along AB
    for point_name, coord in sorted_edge_points['AB']:
        final_geometry[point_name] = coord

    # Add B
    final_geometry['B'] = corners['B']

    # Add points along BC
    for point_name, coord in sorted_edge_points['BC']:
        final_geometry[point_name] = coord

    # Add C
    final_geometry['C'] = corners['C']

    # Add points along CD
    for point_name, coord in sorted_edge_points['CD']:
        final_geometry[point_name] = coord

    # Add D
    final_geometry['D'] = corners['D']

    # Add points along DA
    for point_name, coord in sorted_edge_points['DA']:
        final_geometry[point_name] = coord

    return final_geometry

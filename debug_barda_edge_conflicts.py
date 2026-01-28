"""
Debug edge usage conflicts for barda_example_one.
Check if multiple connections are trying to use the same edge on tabs 0 and 3.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import barda_example_one, barda_example_one_sequence
from src.hgen_sm import initialize_objects, Part, create_segments
import itertools

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("DEBUGGING EDGE USAGE CONFLICTS FOR BARDA_EXAMPLE_ONE")
print("="*80)

# Initialize
part = initialize_objects(barda_example_one)
sequence = barda_example_one_sequence

print(f"\nSequence: {sequence}")
print(f"\nTabs with multiple connections:")
print(f"  Tab 0: appears in pairs ['3', '0'], ['0', '1'], ['0', '2'] - 3 connections")
print(f"  Tab 3: appears in pairs ['3', '0'], ['3', '4'], ['3', '5'] - 3 connections")

# Generate segments
print(f"\n{'='*80}")
print(f"GENERATING SEGMENTS")
print(f"{'='*80}")

segments_library = []
for pair in sequence:
    tab_x = part.tabs[pair[0]]
    tab_z = part.tabs[pair[1]]
    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment = Part(sequence=pair, tabs=segment_tabs)
    segments = create_segments(segment, segment_cfg, filter_cfg)
    segments_library.append(segments)
    print(f"{pair}: {len(segments)} segments")

# Take first combination and analyze edge usage
print(f"\n{'='*80}")
print(f"ANALYZING FIRST COMBINATION - EDGE USAGE")
print(f"{'='*80}")

first_combination = next(itertools.product(*segments_library))

# Map segments to pairs
pair_to_segment = {}
for i, pair in enumerate(sequence):
    pair_to_segment[tuple(pair)] = first_combination[i]

# Function to determine which edge a segment uses
def get_edge_used(tab_instance, tab_id):
    """
    Determine which edge of the tab has bend/flange points (indicating it's used for connection).
    """
    # Get corner points
    corners = {}
    for corner in ['A', 'B', 'C', 'D']:
        if corner in tab_instance.points:
            corners[corner] = tab_instance.points[corner]

    if len(corners) < 4:
        return "UNKNOWN - Missing corners"

    # Get non-corner points (BP, FP, etc.)
    non_corner_points = [(name, coord) for name, coord in tab_instance.points.items()
                        if name not in ['A', 'B', 'C', 'D']]

    if len(non_corner_points) == 0:
        return "NONE - No bend points"

    # Check which edge the points are near
    edges = {
        'AB': (corners['A'], corners['B']),
        'BC': (corners['B'], corners['C']),
        'CD': (corners['C'], corners['D']),
        'DA': (corners['D'], corners['A'])
    }

    edge_counts = {'AB': 0, 'BC': 0, 'CD': 0, 'DA': 0}

    for point_name, point_coord in non_corner_points:
        # For each edge, check if point is close to that edge
        for edge_name, (p1, p2) in edges.items():
            # Check if point is on the line between p1 and p2
            vec_edge = p2 - p1
            vec_to_point = point_coord - p1

            # Project onto edge
            if np.linalg.norm(vec_edge) > 1e-6:
                t = np.dot(vec_to_point, vec_edge) / np.dot(vec_edge, vec_edge)

                # If projection is on edge (t in [0, 1])
                if -0.1 <= t <= 1.1:  # Allow small tolerance
                    # Check distance to edge
                    projected = p1 + t * vec_edge
                    dist = np.linalg.norm(point_coord - projected)

                    if dist < 15.0:  # Within 15mm of edge
                        edge_counts[edge_name] += 1

    # Return edge with most points
    if max(edge_counts.values()) == 0:
        return "UNKNOWN - No points near edges"

    used_edges = [edge for edge, count in edge_counts.items() if count > 0]
    return used_edges

# Analyze edge usage for tab 0
print(f"\nTAB 0 EDGE USAGE:")
print(f"-"*80)

tab_0_segments = []
for pair, segment in pair_to_segment.items():
    if '0' in pair:
        # Find which tab in the segment corresponds to tab 0
        for tab_local_id, tab_instance in segment.tabs.items():
            if hasattr(tab_instance, 'tab_id') and tab_instance.tab_id == '0':
                edges_used = get_edge_used(tab_instance, '0')
                tab_0_segments.append((pair, edges_used))
                print(f"  Pair {list(pair)}: uses edges {edges_used}")

# Analyze edge usage for tab 3
print(f"\nTAB 3 EDGE USAGE:")
print(f"-"*80)

tab_3_segments = []
for pair, segment in pair_to_segment.items():
    if '3' in pair:
        # Find which tab in the segment corresponds to tab 3
        for tab_local_id, tab_instance in segment.tabs.items():
            if hasattr(tab_instance, 'tab_id') and tab_instance.tab_id == '3':
                edges_used = get_edge_used(tab_instance, '3')
                tab_3_segments.append((pair, edges_used))
                print(f"  Pair {list(pair)}: uses edges {edges_used}")

# Check for conflicts
print(f"\n{'='*80}")
print(f"EDGE CONFLICT ANALYSIS")
print(f"{'='*80}")

print(f"\nTAB 0 conflicts:")
tab_0_edges = [edges for _, edges in tab_0_segments]
tab_0_all_edges = []
for edges in tab_0_edges:
    if isinstance(edges, list):
        tab_0_all_edges.extend(edges)

from collections import Counter
edge_usage_0 = Counter(tab_0_all_edges)
conflicts_0 = {edge: count for edge, count in edge_usage_0.items() if count > 1}

if conflicts_0:
    print(f"  [CONFLICT DETECTED] Multiple connections trying to use same edge:")
    for edge, count in conflicts_0.items():
        print(f"    Edge {edge}: used by {count} connections")
else:
    print(f"  [OK] No edge conflicts")

print(f"\nTAB 3 conflicts:")
tab_3_edges = [edges for _, edges in tab_3_segments]
tab_3_all_edges = []
for edges in tab_3_edges:
    if isinstance(edges, list):
        tab_3_all_edges.extend(edges)

edge_usage_3 = Counter(tab_3_all_edges)
conflicts_3 = {edge: count for edge, count in edge_usage_3.items() if count > 1}

if conflicts_3:
    print(f"  [CONFLICT DETECTED] Multiple connections trying to use same edge:")
    for edge, count in conflicts_3.items():
        print(f"    Edge {edge}: used by {count} connections")
else:
    print(f"  [OK] No edge conflicts")

# Summary
print(f"\n{'='*80}")
print(f"ROOT CAUSE ANALYSIS")
print(f"{'='*80}")

if conflicts_0 or conflicts_3:
    print(f"\n[ROOT CAUSE FOUND]")
    print(f"\nThe part_assembly filter (merge_multiple_tabs) is rejecting ALL combinations because:")
    print(f"  - Tabs 0 and/or 3 have 3 connections each")
    print(f"  - Multiple connections are trying to use the SAME EDGE")
    print(f"  - This is physically unmanufacturable - you can't bend the same edge twice")
    print(f"\nConflicts:")
    if conflicts_0:
        print(f"  Tab 0: {conflicts_0}")
    if conflicts_3:
        print(f"  Tab 3: {conflicts_3}")

    print(f"\nSolution:")
    print(f"  The geometry/sequence needs to be adjusted so that:")
    print(f"  1. Each connection uses a DIFFERENT edge of tabs 0 and 3")
    print(f"  2. OR reduce the number of connections per tab")
    print(f"  3. OR use a different sequence that doesn't create this conflict")
else:
    print(f"\n[NO OBVIOUS CONFLICT]")
    print(f"  Edge usage detection may need refinement")
    print(f"  Or the conflict is in collision detection or other filters")

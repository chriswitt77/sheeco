"""
Debug why two_bend Approach 1 doesn't generate segments for specific pairs
in barda_example_one, even though some edges are parallel.

Focus on pairs: ['0','1'], ['0','2'], ['3','4'], ['3','5']
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import barda_example_one
from src.hgen_sm import initialize_objects, Part

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("DEBUG: TWO_BEND APPROACH 1 FOR BARDA_EXAMPLE_ONE")
print("="*80)

# Initialize
part = initialize_objects(barda_example_one)

# Pairs to debug
debug_pairs = [['0', '1'], ['0', '2'], ['3', '4'], ['3', '5']]

print(f"\nAnalyzing pairs: {debug_pairs}")
print(f"User observation: Some edges are parallel, so Approach 1 should work\n")

for pair in debug_pairs:
    print(f"\n{'='*80}")
    print(f"PAIR: {pair}")
    print(f"{'='*80}")

    tab_x = part.tabs[pair[0]]
    tab_z = part.tabs[pair[1]]

    # Get tab geometry
    print(f"\nTab {pair[0]} geometry:")
    print(f"  A: {tab_x.points['A']}")
    print(f"  B: {tab_x.points['B']}")
    print(f"  C: {tab_x.points['C']}")
    print(f"  D: {tab_x.points['D']}")

    print(f"\nTab {pair[1]} geometry:")
    print(f"  A: {tab_z.points['A']}")
    print(f"  B: {tab_z.points['B']}")
    print(f"  C: {tab_z.points['C']}")
    print(f"  D: {tab_z.points['D']}")

    # Calculate plane normals
    AB_x = tab_x.points['B'] - tab_x.points['A']
    AD_x = tab_x.points['D'] - tab_x.points['A']
    normal_x = np.cross(AB_x, AD_x)
    normal_x = normal_x / np.linalg.norm(normal_x)

    AB_z = tab_z.points['B'] - tab_z.points['A']
    AD_z = tab_z.points['D'] - tab_z.points['A']
    normal_z = np.cross(AB_z, AD_z)
    normal_z = normal_z / np.linalg.norm(normal_z)

    print(f"\nPlane normals:")
    print(f"  Tab {pair[0]} normal: {normal_x}")
    print(f"  Tab {pair[1]} normal: {normal_z}")

    # Check perpendicularity (Approach 1 requirement)
    dot_product = abs(np.dot(normal_x, normal_z))
    angle_deg = np.degrees(np.arccos(np.clip(dot_product, 0, 1)))
    is_perpendicular = dot_product < np.cos(np.radians(89))

    print(f"\nPerpendicularity check (Approach 1 requirement):")
    print(f"  |dot(normal_x, normal_z)|: {dot_product:.6f}")
    print(f"  Angle between planes: {angle_deg:.2f}°")
    print(f"  Are planes perpendicular (< 89°)? {is_perpendicular}")

    if not is_perpendicular:
        print(f"  [FILTERED] Planes not perpendicular - Approach 1 requires ~90° angle")
        print(f"  This pair will use Approach 2 (triangular) instead")
        continue

    # Check edge parallelism
    print(f"\nEdge analysis:")

    edges_x = {
        'AB': tab_x.points['B'] - tab_x.points['A'],
        'BC': tab_x.points['C'] - tab_x.points['B'],
        'CD': tab_x.points['D'] - tab_x.points['C'],
        'DA': tab_x.points['A'] - tab_x.points['D']
    }

    edges_z = {
        'AB': tab_z.points['B'] - tab_z.points['A'],
        'BC': tab_z.points['C'] - tab_z.points['B'],
        'CD': tab_z.points['D'] - tab_z.points['C'],
        'DA': tab_z.points['A'] - tab_z.points['D']
    }

    # Normalize edges
    edges_x_norm = {k: v / np.linalg.norm(v) for k, v in edges_x.items()}
    edges_z_norm = {k: v / np.linalg.norm(v) for k, v in edges_z.items()}

    print(f"\n  Tab {pair[0]} edges (normalized):")
    for edge_name, edge_vec in edges_x_norm.items():
        print(f"    {edge_name}: {edge_vec}")

    print(f"\n  Tab {pair[1]} edges (normalized):")
    for edge_name, edge_vec in edges_z_norm.items():
        print(f"    {edge_name}: {edge_vec}")

    # Check all edge pairs for parallelism
    print(f"\n  Checking edge parallelism (for Approach 1 rectangular intermediate):")
    parallel_threshold = np.cos(np.radians(1))  # Within 1 degree

    found_parallel = False
    for edge_x_name, edge_x_vec in edges_x_norm.items():
        for edge_z_name, edge_z_vec in edges_z_norm.items():
            dot = abs(np.dot(edge_x_vec, edge_z_vec))
            angle = np.degrees(np.arccos(np.clip(dot, 0, 1)))
            is_parallel = dot > parallel_threshold

            if is_parallel:
                print(f"    [{edge_x_name} x {edge_z_name}] dot={dot:.6f}, angle={angle:.2f}° - PARALLEL")
                found_parallel = True
            elif dot < 0.1:  # Also show perpendicular edges
                print(f"    [{edge_x_name} x {edge_z_name}] dot={dot:.6f}, angle={angle:.2f}° - perpendicular")

    if not found_parallel:
        print(f"  [NO PARALLEL EDGES FOUND]")
        print(f"  This is unexpected if user observed parallel edges!")

    # Check outward directions for antiparallel check
    print(f"\n  Checking outward directions (antiparallel check):")

    # For Approach 1, we need edges perpendicular to both planes
    # These should be the edges that are NOT in the plane of each tab

    # For tab_x, find edges perpendicular to normal_x
    perp_edges_x = {}
    for edge_name, edge_vec in edges_x_norm.items():
        dot_with_normal = abs(np.dot(edge_vec, normal_x))
        if dot_with_normal < 0.1:  # Perpendicular to normal = lies in plane
            pass
        else:
            perp_edges_x[edge_name] = edge_vec
            print(f"    Tab {pair[0]} edge {edge_name}: perpendicular to plane (dot with normal = {dot_with_normal:.6f})")

    perp_edges_z = {}
    for edge_name, edge_vec in edges_z_norm.items():
        dot_with_normal = abs(np.dot(edge_vec, normal_z))
        if dot_with_normal < 0.1:
            pass
        else:
            perp_edges_z[edge_name] = edge_vec
            print(f"    Tab {pair[1]} edge {edge_name}: perpendicular to plane (dot with normal = {dot_with_normal:.6f})")

    # The "outward direction" for Approach 1 should be along the edges perpendicular to the plane
    # Check if these are antiparallel (pointing towards each other)
    if perp_edges_x and perp_edges_z:
        for edge_x_name, edge_x_vec in perp_edges_x.items():
            for edge_z_name, edge_z_vec in perp_edges_z.items():
                dot = np.dot(edge_x_vec, edge_z_vec)
                if dot < -0.5:  # Antiparallel (pointing towards each other)
                    print(f"    [{edge_x_name} x {edge_z_name}] dot={dot:.6f} - ANTIPARALLEL (pointing towards each other)")
                else:
                    print(f"    [{edge_x_name} x {edge_z_name}] dot={dot:.6f} - not antiparallel")

print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")
print(f"\nTo generate Approach 1 segments, the following conditions must be met:")
print(f"  1. Planes must be perpendicular (~90° angle)")
print(f"  2. At least one pair of edges must be parallel (for rectangular intermediate)")
print(f"  3. Outward directions must be antiparallel (pointing towards each other)")
print(f"  4. Various geometric validation checks must pass")
print(f"\nCheck the output above to see which condition(s) are failing for each pair.")

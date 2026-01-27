"""
Check if corner ordering (clockwise vs anticlockwise) affects edge selection in one_bend.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

# Initialize part
part = initialize_objects(transportschuh)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

print("="*80)
print("CORNER ORDERING ANALYSIS")
print("="*80)

def check_corner_ordering(tab, tab_name):
    """Check if corners are ordered clockwise or anticlockwise."""
    print(f"\n{tab_name} corners:")

    corners = ['A', 'B', 'C', 'D']
    for corner in corners:
        coord = tab.points[corner]
        print(f"  {corner}: {coord}")

    # Calculate the normal using cross product of two edges
    A = tab.points['A']
    B = tab.points['B']
    C = tab.points['C']
    D = tab.points['D']

    # Edge vectors
    AB = B - A
    BC = C - B
    CD = D - C
    DA = A - D

    print(f"\n{tab_name} edge vectors:")
    print(f"  A->B: {AB}")
    print(f"  B->C: {BC}")
    print(f"  C->D: {CD}")
    print(f"  D->A: {DA}")

    # Calculate normal from cross product of first two edges
    normal = np.cross(AB, BC)
    normal = normal / np.linalg.norm(normal)

    print(f"\n{tab_name} normal from cross(AB, BC): {normal}")

    # Check plane normal
    plane = calculate_plane(rect=tab)
    print(f"{tab_name} plane normal: {plane.orientation}")

    # Check if normals match or are opposite
    dot = np.dot(normal, plane.orientation)
    print(f"Dot product: {dot:.6f}")

    if dot > 0:
        print(f"  -> Corner ordering is COUNTERCLOCKWISE when viewed from +normal direction")
    else:
        print(f"  -> Corner ordering is CLOCKWISE when viewed from +normal direction")

    return normal, plane.orientation

normal_0, plane_normal_0 = check_corner_ordering(tab_0, "Tab 0")
normal_1, plane_normal_1 = check_corner_ordering(tab_1, "Tab 1")

print("\n" + "="*80)
print("EDGE DEFINITIONS IN one_bend")
print("="*80)

# The one_bend function uses these fixed edge definitions
rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]
rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]

print("\nEdge definitions (hard-coded in one_bend):")
print(f"  rect_x_edges: {rect_x_edges}")
print(f"  rect_z_edges: {rect_z_edges}")

print("\n" + "="*80)
print("OUTWARD DIRECTION CALCULATION")
print("="*80)

def calculate_outward_direction(tab, edge_pair, tab_name):
    """Replicate the outward direction calculation from one_bend."""
    CPL_id, CPR_id = edge_pair
    CPL = tab.points[CPL_id]
    CPR = tab.points[CPR_id]

    # Calculate rectangle center
    rect_corners = [tab.points[k] for k in ['A', 'B', 'C', 'D']]
    rect_center = np.mean(rect_corners, axis=0)

    # Calculate outward direction
    plane = calculate_plane(rect=tab)
    edge_vec = CPR - CPL
    edge_mid = (CPL + CPR) / 2

    # Cross product: edge_vec x plane_normal
    out_dir = np.cross(edge_vec, plane.orientation)
    out_dir = out_dir / np.linalg.norm(out_dir)

    # Check if pointing outward
    center_to_mid = edge_mid - rect_center
    dot = np.dot(out_dir, center_to_mid)

    if dot < 0:
        out_dir = -out_dir
        flipped = True
    else:
        flipped = False

    print(f"\n{tab_name} edge {CPL_id}-{CPR_id}:")
    print(f"  Edge vector: {edge_vec}")
    print(f"  Edge midpoint: {edge_mid}")
    print(f"  Center: {rect_center}")
    print(f"  Initial cross product: {np.cross(edge_vec, plane.orientation)}")
    print(f"  Dot with (mid-center): {dot:.6f}")
    print(f"  Flipped: {flipped}")
    print(f"  Final outward direction: {out_dir}")

    return out_dir

print("\nTab 0 outward directions:")
for edge in rect_x_edges:
    out_dir = calculate_outward_direction(tab_0, edge, "Tab 0")

print("\n\nTab 1 outward directions:")
for edge in rect_z_edges:
    out_dir = calculate_outward_direction(tab_1, edge, "Tab 1")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)
print("""
Key questions:
1. Are corners ordered consistently (both CW or both CCW)?
2. Does the outward direction calculation work correctly for all edges?
3. Could edge ordering affect which edges are parallel vs perpendicular to bend line?
4. Should edge definitions adapt to corner ordering rather than being hard-coded?
""")

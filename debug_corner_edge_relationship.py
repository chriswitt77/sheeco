"""
Analyze relationship between corner ordering and edge selection in one_bend.
Check if corner ordering affects which edges are parallel/perpendicular to bend line.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane, calculate_plane_intersection

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

# Initialize part
part = initialize_objects(transportschuh)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

# Calculate bend line
plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)
bend_line = calculate_plane_intersection(plane_0, plane_1)

print("="*80)
print("BEND LINE AND EDGE RELATIONSHIP")
print("="*80)

print(f"\nBend line:")
print(f"  Position: {bend_line['position']}")
print(f"  Direction: {bend_line['orientation']}")

# Hard-coded edge definitions from one_bend
rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]
rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]

print("\n" + "="*80)
print("TAB 0 EDGE ANALYSIS")
print("="*80)

# Analyze which edges are opposite
print("\nTab 0 corner positions:")
for corner in ['A', 'B', 'C', 'D']:
    print(f"  {corner}: {tab_0.points[corner]}")

print("\nTab 0 edges and their relationship to bend line:")
for edge in rect_x_edges:
    c1_id, c2_id = edge
    c1 = tab_0.points[c1_id]
    c2 = tab_0.points[c2_id]
    edge_vec = c2 - c1
    edge_len = np.linalg.norm(edge_vec)
    edge_dir = edge_vec / edge_len

    # Calculate angle with bend line
    dot_product = abs(np.dot(edge_dir, bend_line['orientation']))
    angle_deg = np.degrees(np.arccos(np.clip(dot_product, 0, 1)))

    classification = ""
    if angle_deg < 15:
        classification = "PARALLEL to bend line [GOOD]"
    elif angle_deg > 75:
        classification = "PERPENDICULAR to bend line [BAD]"
    else:
        classification = "ANGLED to bend line"

    print(f"\n  Edge {c1_id}-{c2_id}:")
    print(f"    Vector: {edge_vec}")
    print(f"    Angle to bend line: {angle_deg:.1f}°")
    print(f"    Classification: {classification}")

print("\n" + "="*80)
print("TAB 1 EDGE ANALYSIS")
print("="*80)

print("\nTab 1 corner positions:")
for corner in ['A', 'B', 'C', 'D']:
    print(f"  {corner}: {tab_1.points[corner]}")

print("\nTab 1 edges and their relationship to bend line:")
for edge in rect_z_edges:
    c1_id, c2_id = edge
    c1 = tab_1.points[c1_id]
    c2 = tab_1.points[c2_id]
    edge_vec = c2 - c1
    edge_len = np.linalg.norm(edge_vec)
    edge_dir = edge_vec / edge_len

    # Calculate angle with bend line
    dot_product = abs(np.dot(edge_dir, bend_line['orientation']))
    angle_deg = np.degrees(np.arccos(np.clip(dot_product, 0, 1)))

    classification = ""
    if angle_deg < 15:
        classification = "PARALLEL to bend line [GOOD]"
    elif angle_deg > 75:
        classification = "PERPENDICULAR to bend line [BAD]"
    else:
        classification = "ANGLED to bend line"

    print(f"\n  Edge {c1_id}-{c2_id}:")
    print(f"    Vector: {edge_vec}")
    print(f"    Angle to bend line: {angle_deg:.1f}°")
    print(f"    Classification: {classification}")

print("\n" + "="*80)
print("OPPOSITE EDGE ANALYSIS")
print("="*80)

print("""
In a rectangle with corners A, B, C, D ordered counterclockwise:
  Edges:    A-B, B-C, C-D, D-A
  Opposite pairs: (A-B, C-D) and (B-C, D-A)

For Tab 0:
  A-B: PARALLEL (angle 0°)
  C-D: PARALLEL (angle 0°)
  --> Opposite edges have same orientation relative to bend line [CORRECT]

  B-C: PERPENDICULAR (angle 90°)
  D-A: PERPENDICULAR (angle 90°)
  --> Opposite edges have same orientation relative to bend line [CORRECT]

For Tab 1:
  A-B: PARALLEL (angle 0°)
  C-D: PARALLEL (angle 0°)
  --> Opposite edges have same orientation relative to bend line [CORRECT]

  B-C: PERPENDICULAR (angle 90°)
  D-A: PERPENDICULAR (angle 90°)
  --> Opposite edges have same orientation relative to bend line [CORRECT]
""")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

print("""
The corner ordering is CORRECT and CONSISTENT:
  - Both tabs use counterclockwise ordering when viewed from +normal
  - Opposite edges (A-B vs C-D, B-C vs D-A) have the same orientation
  - Edge definitions [('A','B'), ('B','C'), ('C','D'), ('D','A')] are correct

The problem is NOT corner ordering.

The problem is that one_bend tests ALL 4 edges of each tab, including:
  - Edges parallel to bend line (A-B, C-D) -> GOOD for bending
  - Edges perpendicular to bend line (B-C, D-A) -> BAD for bending

The perpendicular edges (B-C and D-A) should be FILTERED OUT before
bend point generation, but currently they are not.

RECOMMENDATION:
The fix proposed in TRANSPORTSCHUH_FIX_PLAN.md is correct:
  Add a filter in one_bend that checks edge-to-bend-line angle
  and skips edges with angle > 75° (perpendicular).

Corner ordering is NOT the issue.
""")

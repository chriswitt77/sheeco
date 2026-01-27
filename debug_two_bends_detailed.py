"""
Detailed debugging of two_bends to see which approach generates solutions and why approach 1 fails.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects, Part
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane
from src.hgen_sm.create_segments.utils import normalize
from config.design_rules import min_flange_length

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

# Initialize part
part = initialize_objects(transportschuh)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)

print("="*80)
print("DETAILED APPROACH 1 ANALYSIS")
print("="*80)

# Calculate centers
rect_x_corners = [tab_0.points[k] for k in ['A', 'B', 'C', 'D']]
rect_z_corners = [tab_1.points[k] for k in ['A', 'B', 'C', 'D']]
rect_x_center = np.mean(rect_x_corners, axis=0)
rect_z_center = np.mean(rect_z_corners, axis=0)

# Test all edge combinations
rect_x_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]
rect_z_edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]

for pair_x in rect_x_edges:
    CPxL_id, CPxR_id = pair_x
    CPxL = tab_0.points[CPxL_id]
    CPxR = tab_0.points[CPxR_id]

    edge_x_vec = CPxR - CPxL
    edge_x_mid = (CPxL + CPxR) / 2
    edge_x_norm = normalize(edge_x_vec)

    # Calculate outward direction
    out_dir_x = np.cross(edge_x_vec, plane_0.orientation)
    out_dir_x = normalize(out_dir_x)
    if np.dot(out_dir_x, edge_x_mid - rect_x_center) < 0:
        out_dir_x = -out_dir_x

    BPxL = CPxL + out_dir_x * min_flange_length
    BPxR = CPxR + out_dir_x * min_flange_length

    for pair_z in rect_z_edges:
        CPzL_id, CPzR_id = pair_z
        CPzL = tab_1.points[CPzL_id]
        CPzR = tab_1.points[CPzR_id]

        edge_z_vec = CPzR - CPzL
        edge_z_mid = (CPzL + CPzR) / 2
        edge_z_norm = normalize(edge_z_vec)

        # Calculate outward direction
        out_dir_z = np.cross(edge_z_vec, plane_1.orientation)
        out_dir_z = normalize(out_dir_z)
        if np.dot(out_dir_z, edge_z_mid - rect_z_center) < 0:
            out_dir_z = -out_dir_z

        BPzL = CPzL + out_dir_z * min_flange_length
        BPzR = CPzR + out_dir_z * min_flange_length

        # Check perpendicular
        dot_edges = abs(np.dot(edge_x_norm, edge_z_norm))
        angle = np.degrees(np.arccos(np.clip(dot_edges, 0, 1)))

        if dot_edges < 0.1:  # Perpendicular check
            print(f"\nEdge {CPxL_id}-{CPxR_id} x {CPzL_id}-{CPzR_id}:")
            print(f"  Edge angle: {angle:.1f}° (perpendicular: True)")
            print(f"  Edge x direction: {edge_x_norm}")
            print(f"  Edge z direction: {edge_z_norm}")
            print(f"  Out dir x: {out_dir_x}")
            print(f"  Out dir z: {out_dir_z}")

            # Check direction
            connection_vec = BPzL - BPxL
            x_toward_z = np.dot(out_dir_x, connection_vec)
            z_toward_x = np.dot(out_dir_z, -connection_vec)

            print(f"  Connection vec: {connection_vec}")
            print(f"  x->z dot: {x_toward_z:.3f} (>0: {x_toward_z > 0})")
            print(f"  z->x dot: {z_toward_x:.3f} (>0: {z_toward_x > 0})")

            if x_toward_z > 0 and z_toward_x > 0:
                print(f"  [SUCCESS] This should generate a solution!")
            else:
                print(f"  [FILTERED] Direction check failed")

# Run actual two_bends and check which segments were generated
print(f"\n{'='*80}")
print(f"CHECKING GENERATED SEGMENT")
print(f"{'='*80}")

from src.hgen_sm.create_segments.bend_strategies import two_bends

segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)
segments = two_bends(segment, segment_cfg, filter_cfg)

two_bend_segs = [s for s in segments if len(s.tabs) == 3]
print(f"\nGenerated {len(two_bend_segs)} two-bend segment(s)")

if len(two_bend_segs) > 0:
    seg = two_bend_segs[0]
    print(f"\nSegment tab keys: {list(seg.tabs.keys())}")

    # Check the intermediate tab
    if 'tab_y' in seg.tabs:
        tab_y = seg.tabs['tab_y']
        print(f"\nIntermediate tab points: {list(tab_y.points.keys())}")

        # Determine which approach by analyzing geometry
        # Approach 1: rectangular intermediate tab (4 corners)
        # Approach 2: triangular intermediate tab (3-4 points)
        corner_count = sum(1 for k in tab_y.points.keys() if k in ['A', 'B', 'C', 'D'])
        print(f"Corner-like points in tab_y: {corner_count}")

        # Check if points form a planar quadrilateral (approach 1) or triangle (approach 2)
        points = list(tab_y.points.values())
        if len(points) >= 4:
            # Calculate if coplanar
            p0, p1, p2, p3 = points[:4]
            v1 = p1 - p0
            v2 = p2 - p0
            v3 = p3 - p0
            normal = np.cross(v1, v2)
            dist = abs(np.dot(v3, normal)) / (np.linalg.norm(normal) + 1e-9)
            print(f"Points planarity distance: {dist:.6f}")

            if dist < 0.01:
                print(f"[APPROACH 1] Rectangular intermediate tab")
            else:
                print(f"[APPROACH 2] Non-planar/triangular intermediate tab")

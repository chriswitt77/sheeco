"""
Analyze transportschuh solutions to understand the issues.
"""

import yaml
import json
import numpy as np
from pathlib import Path
from config.user_input import transportschuh
from src.hgen_sm import initialize_objects, Part
from src.hgen_sm.create_segments.choose_strategy import create_segments
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane, is_coplanar

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("ANALYZING TRANSPORTSCHUH GEOMETRY")
print("="*80)

# Initialize part
part = initialize_objects(transportschuh)

print(f"\nNumber of tabs: {len(part.tabs)}")
for tab_id, tab in part.tabs.items():
    print(f"\nTab {tab_id}:")
    print(f"  A: {tab.points['A']}")
    print(f"  B: {tab.points['B']}")
    print(f"  C: {tab.points['C']}")
    print(f"  D: {tab.points['D']}")

    # Calculate plane
    plane = calculate_plane(rect=tab)
    print(f"  Plane normal: {plane.orientation}")
    print(f"  Plane position: {plane.position}")

    # Calculate edge lengths
    edge_AB = np.linalg.norm(tab.points['B'] - tab.points['A'])
    edge_BC = np.linalg.norm(tab.points['C'] - tab.points['B'])
    print(f"  Edge AB length: {edge_AB:.2f}")
    print(f"  Edge BC length: {edge_BC:.2f}")

# Test segments generation
print("\n" + "="*80)
print("TESTING SEGMENT GENERATION")
print("="*80)

tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

# Check if coplanar
plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)
coplanar = is_coplanar(plane_0, plane_1)
print(f"\nCoplanar: {coplanar}")

# Calculate angle between normals
dot_product = np.dot(plane_0.orientation, plane_1.orientation)
angle_rad = np.arccos(np.clip(dot_product, -1.0, 1.0))
angle_deg = np.degrees(angle_rad)
print(f"Angle between normals: {angle_deg:.2f} degrees")

# Generate segments
segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)
segments = create_segments(segment, segment_cfg, filter_cfg)

print(f"\nNumber of segments generated: {len(segments)}")

# Analyze each segment
for i, seg in enumerate(segments):
    print(f"\n--- Segment {i+1} ---")
    print(f"Number of tabs in segment: {len(seg.tabs)}")

    for tab_key, tab in seg.tabs.items():
        print(f"\n  {tab_key} (id={tab.tab_id}):")
        print(f"    Number of points: {len(tab.points)}")
        print(f"    Point names: {list(tab.points.keys())}")

        # Find bend/flange points
        bend_points = {k: v for k, v in tab.points.items() if 'BP' in k or 'FP' in k}
        if bend_points:
            print(f"    Bend/Flange points: {len(bend_points)}")
            for name, coord in bend_points.items():
                print(f"      {name}: {coord}")

            # Check if bend points span the full edge
            if len(bend_points) >= 2:
                coords = np.array(list(bend_points.values()))
                x_range = coords[:, 0].max() - coords[:, 0].min()
                y_range = coords[:, 1].max() - coords[:, 1].min()
                z_range = coords[:, 2].max() - coords[:, 2].min()
                print(f"    Bend point span: x={x_range:.2f}, y={y_range:.2f}, z={z_range:.2f}")

                # Compare to tab dimensions
                tab_width = np.linalg.norm(tab.points['B'] - tab.points['A'])
                tab_height = np.linalg.norm(tab.points['C'] - tab.points['B'])
                print(f"    Tab dimensions: width={tab_width:.2f}, height={tab_height:.2f}")

                # Check coverage
                if 'BP' in list(bend_points.keys())[0]:
                    max_span = max(x_range, y_range, z_range)
                    coverage_pct = (max_span / max(tab_width, tab_height)) * 100
                    print(f"    Edge coverage: {coverage_pct:.1f}%")

                    if coverage_pct < 95:
                        print(f"    [WARNING] Partial edge coverage - connection may be incomplete!")

print("\n" + "="*80)
print("CHECKING FOR TWO-BEND STRATEGY")
print("="*80)

print(f"\nConfiguration:")
print(f"  single_bend enabled: {segment_cfg.get('single_bend', True)}")
print(f"  double_bend enabled: {segment_cfg.get('double_bend', True)}")
print(f"  prioritize_perpendicular_bends: {segment_cfg.get('prioritize_perpendicular_bends', True)}")

# Count segment types
one_bend_count = sum(1 for seg in segments if len(seg.tabs) == 2)
two_bend_count = sum(1 for seg in segments if len(seg.tabs) == 3)

print(f"\nSegment breakdown:")
print(f"  One-bend segments (2 tabs): {one_bend_count}")
print(f"  Two-bend segments (3 tabs): {two_bend_count}")

if two_bend_count == 0 and segment_cfg.get('double_bend', True):
    print("\n[WARNING] No two-bend segments generated despite being enabled!")
    print("This might be due to prioritize_perpendicular_bends filtering")

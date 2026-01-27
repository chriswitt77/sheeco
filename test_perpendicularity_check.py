"""
Test which part of the edge coplanarity check is failing.
"""

import numpy as np
from config.user_input import with_mounts
from src.hgen_sm import initialize_objects
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane
from src.hgen_sm.create_segments.utils import normalize

# Initialize
part = initialize_objects(with_mounts)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)

# D-A x B-C case
CPxL = tab_0.points['D']
CPxR = tab_0.points['A']
CPzL = tab_1.points['B']
CPzR = tab_1.points['C']

print("Testing D-A x B-C edge coplanarity check:")

# Calculate connection distance
edge_x_mid = (CPxL + CPxR) / 2
edge_z_mid = (CPzL + CPzR) / 2
connection_dist = np.linalg.norm(edge_z_mid - edge_x_mid)

# Calculate tolerance
base_tolerance = 5.0
relative_tolerance = 0.1
tolerance = max(base_tolerance, relative_tolerance * connection_dist)

print(f"\nConnection distance: {connection_dist:.3f} mm")
print(f"Tolerance: {tolerance:.3f} mm")

# Fit plane
points = np.array([CPxL, CPxR, CPzL, CPzR])
centroid = np.mean(points, axis=0)
centered = points - centroid

_, _, vh = np.linalg.svd(centered)
fitted_normal = vh[-1]
fitted_normal = normalize(fitted_normal)

# Check coplanarity
distances = [abs(np.dot(p - centroid, fitted_normal)) for p in points]
max_dist = max(distances)

print(f"\nCoplanarity check:")
print(f"  Max distance from fitted plane: {max_dist:.3f} mm")
print(f"  Tolerance: {tolerance:.3f} mm")
print(f"  Pass: {max_dist <= tolerance}")

# Check perpendicularity to tab planes
angle_tol = np.radians(10)  # 10 degrees
dot_x = abs(np.dot(fitted_normal, plane_0.orientation))
dot_z = abs(np.dot(fitted_normal, plane_1.orientation))
angle_x = np.arccos(np.clip(dot_x, 0, 1))
angle_z = np.arccos(np.clip(dot_z, 0, 1))

is_perp_x = abs(angle_x - np.pi/2) < angle_tol
is_perp_z = abs(angle_z - np.pi/2) < angle_tol

print(f"\nPerpendicularity check:")
print(f"  Fitted normal: {fitted_normal}")
print(f"  Plane 0 normal: {plane_0.orientation}")
print(f"  Plane 1 normal: {plane_1.orientation}")
print(f"  Angle to plane 0: {np.degrees(angle_x):.2f} deg (should be ~90)")
print(f"  Angle to plane 1: {np.degrees(angle_z):.2f} deg (should be ~90)")
print(f"  Deviation from 90 (plane 0): {np.degrees(abs(angle_x - np.pi/2)):.2f} deg (max 10)")
print(f"  Deviation from 90 (plane 1): {np.degrees(abs(angle_z - np.pi/2)):.2f} deg (max 10)")
print(f"  Perp to plane 0: {is_perp_x}")
print(f"  Perp to plane 1: {is_perp_z}")

print(f"\nOverall result: {max_dist <= tolerance and is_perp_x and is_perp_z}")

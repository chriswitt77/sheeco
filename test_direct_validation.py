"""
Test the validation functions directly with the problematic case.
"""

import numpy as np
from config.user_input import with_mounts
from src.hgen_sm import initialize_objects
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane
from src.hgen_sm.create_segments.bend_strategies import validate_edge_coplanarity

# Initialize
part = initialize_objects(with_mounts)
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

plane_0 = calculate_plane(rect=tab_0)
plane_1 = calculate_plane(rect=tab_1)

# D-A x B-C case
CPxL = tab_0.points['D']  # [100, 0, 0]
CPxR = tab_0.points['A']  # [50, 0, 0]
CPzL = tab_1.points['B']  # [0, 40, 40]
CPzR = tab_1.points['C']  # [0, 40, 80]

print("Testing D-A x B-C:")
print(f"CPxL: {CPxL}")
print(f"CPxR: {CPxR}")
print(f"CPzL: {CPzL}")
print(f"CPzR: {CPzR}")

# Test with different parameters
result1 = validate_edge_coplanarity(CPxL, CPxR, CPzL, CPzR, plane_0, plane_1,
                                   base_tolerance=5.0, relative_tolerance=0.1)
print(f"\nWith base=5.0, relative=0.1: {result1}")

result2 = validate_edge_coplanarity(CPxL, CPxR, CPzL, CPzR, plane_0, plane_1,
                                   base_tolerance=5.0, relative_tolerance=0.12)
print(f"With base=5.0, relative=0.12: {result2}")

# Calculate connection distance manually
edge_x_mid = (CPxL + CPxR) / 2
edge_z_mid = (CPzL + CPzR) / 2
connection_dist = np.linalg.norm(edge_z_mid - edge_x_mid)

print(f"\nConnection distance: {connection_dist:.3f}")
print(f"Tolerance with 0.1: {max(5.0, 0.1 * connection_dist):.3f}")
print(f"Tolerance with 0.12: {max(5.0, 0.12 * connection_dist):.3f}")

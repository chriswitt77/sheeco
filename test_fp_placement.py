"""
Test to reproduce FP placement issue where FP points are perpendicular to plane
instead of within the plane
"""
import numpy as np
from types import SimpleNamespace
from src.hgen_sm.create_segments.utils import perp_toward_plane, normalize

# Simulate tab 0_0 geometry (z=0 plane)
plane_x = SimpleNamespace(
    position=np.array([50.0, 0.0, 0.0]),
    orientation=np.array([0.0, 0.0, -1.0])  # Normal pointing down
)

# Simulate bend axis from user's data
BP1 = np.array([72.0793271027026, -32.30225485842998, 0.0])
BP2 = np.array([19.960794540797867, 12.746751965572695, 0.0])

BP0 = (BP1 + BP2) / 2.0
bend_dir = normalize(BP2 - BP1)

print(f"\n{'='*70}")
print(f"FP PLACEMENT ISSUE REPRODUCTION")
print(f"{'='*70}\n")

print(f"Tab plane (plane_x):")
print(f"  Position: {plane_x.position}")
print(f"  Normal: {plane_x.orientation}")

print(f"\nBend points (should be in z=0 plane):")
print(f"  BP1: {BP1}")
print(f"  BP2: {BP2}")
print(f"  BP0 (midpoint): {BP0}")

print(f"\nBend direction:")
print(f"  bend_dir: {bend_dir}")

# Test current perp_toward_plane function
print(f"\n{'-'*70}")
print(f"CURRENT perp_toward_plane calculation:")
print(f"{'-'*70}")

perpA = perp_toward_plane(plane_x, BP0, bend_dir)
FP1_current = BP1 + perpA * 10.0  # min_flange_length = 10

print(f"  perpA (direction): {perpA}")
print(f"  FP1 calculated: {FP1_current}")
print(f"  FP1 should be at z=0, actual z={FP1_current[2]:.2f}")

if abs(FP1_current[2]) > 0.1:
    print(f"  ❌ WRONG: FP is NOT in the z=0 plane!")
else:
    print(f"  ✓ OK: FP is in the z=0 plane")

# Test correct calculation
print(f"\n{'-'*70}")
print(f"CORRECT perp_within_plane calculation:")
print(f"{'-'*70}")

# Correct formula: cross(bend_dir, plane_normal) gives vector within plane
perp_in_plane = np.cross(bend_dir, plane_x.orientation)
perp_in_plane = normalize(perp_in_plane)

# Determine correct sign (toward tab center, not toward bend axis)
tab_center = np.array([75.0, 23.75, 0.0])  # Rough center of tab 0_0
sign = np.sign(np.dot(tab_center - BP0, perp_in_plane))
if sign == 0:
    sign = 1.0
perp_in_plane = perp_in_plane * sign

FP1_correct = BP1 + perp_in_plane * 10.0

print(f"  perp_in_plane (direction): {perp_in_plane}")
print(f"  FP1 calculated: {FP1_correct}")
print(f"  FP1 z-coordinate: {FP1_correct[2]:.6f}")

if abs(FP1_correct[2]) < 0.001:
    print(f"  ✓ CORRECT: FP is in the z=0 plane!")
else:
    print(f"  ❌ ERROR: FP is still not in plane, z={FP1_correct[2]}")

print(f"\n{'-'*70}")
print(f"COMPARISON:")
print(f"{'-'*70}")
print(f"Current (wrong):  FP at {FP1_current}")
print(f"Correct (fixed):  FP at {FP1_correct}")
print(f"Difference: {np.linalg.norm(FP1_current - FP1_correct):.2f}mm")

print(f"\n{'='*70}\n")

# Show the mathematical difference
print(f"Mathematical explanation:")
print(f"  cross(plane_normal, bend_dir) = {np.cross(plane_x.orientation, bend_dir)}")
print(f"  cross(bend_dir, plane_normal) = {np.cross(bend_dir, plane_x.orientation)}")
print(f"\n  The order matters! We need cross(bend_dir, plane_normal) to get")
print(f"  a vector that lies WITHIN the plane.")

print(f"\n{'='*70}\n")

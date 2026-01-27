"""
Test the tolerance calculation directly.
"""

connection_dist = 104.0
base_tolerance = 5.0
relative_tolerance = 0.1

# Old logic
if connection_dist < base_tolerance / relative_tolerance:
    old_tolerance = relative_tolerance * connection_dist
else:
    old_tolerance = base_tolerance

# New logic
new_tolerance = max(base_tolerance, relative_tolerance * connection_dist)

print(f"Connection distance: {connection_dist}")
print(f"Base tolerance: {base_tolerance}")
print(f"Relative tolerance: {relative_tolerance}")
print(f"\nThreshold for switching: {base_tolerance / relative_tolerance}")
print(f"\nOld logic tolerance: {old_tolerance}")
print(f"New logic tolerance: {new_tolerance}")
print(f"\nRelative calculation: {relative_tolerance * connection_dist}")

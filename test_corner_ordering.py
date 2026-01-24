"""Test to verify corner point ordering in tabs after merge."""

import json

# Part 6 - problematic
part6_tab1 = {
    "points": {
        "A": [40.0, 90.0, 0.0],
        "FP1_01L": [0.0, 90.0, 0.0],
        "BP1_01L": [0.0, 80.0, 0.0],
        "BP1_01R": [40.0, 80.0, 0.0],
        "FP1_01R": [40.0, 90.0, 0.0],
        "B": [0.0, 90.0, 0.0],
        "BP1_12L": [-10.0, 90.0, 0.0],
        "BP1_12R": [-10.0, 120.0, 0.0],
        "FP1_12R": [0.0, 120.0, 0.0],
        "C": [0.0, 120.0, 0.0],
        "D": [40.0, 120.0, 0.0]
    }
}

# Part 8 - problematic
part8_tab1 = {
    "points": {
        "A": [40.0, 90.0, 0.0],
        "B": [0.0, 90.0, 0.0],
        "C": [0.0, 120.0, 0.0],
        "D": [40.0, 120.0, 0.0],
        "FP1_01L": [0.0, 90.0, 0.0],
        "BP1_01L": [0.0, 80.0, 0.0],
        "BP1_01R": [40.0, 80.0, 0.0],
        "FP1_01R": [40.0, 90.0, 0.0],
        "FP1_12L": [40.0, 120.0, 0.0],
        "BP1_12L": [50.0, 120.0, 0.0],
        "BP1_12R": [50.0, 90.0, 0.0]
    }
}

# Original input for tab 1 from config
original_tab1 = {
    'pointA': [40, 90, 0],
    'pointB': [0, 90, 0],
    'pointC': [0, 120, 0],
    'mounts': [[20, 110, 0]]
}
# D should be calculated as: C + (A - B) = [0,120,0] + ([40,90,0] - [0,90,0]) = [0,120,0] + [40,0,0] = [40,120,0]

print("=" * 70)
print("CORNER POINT ANALYSIS")
print("=" * 70)
print()

print("Original Tab 1 (from config/user_input.py):")
print(f"  A: {original_tab1['pointA']}")
print(f"  B: {original_tab1['pointB']}")
print(f"  C: {original_tab1['pointC']}")
print(f"  D: [40, 120, 0] (calculated)")
print()

print("=" * 70)
print("PART 6 - Tab 1")
print("=" * 70)
print()

corners_part6 = {k: v for k, v in part6_tab1["points"].items() if k in ['A', 'B', 'C', 'D']}
print("Corner points present:")
for corner, pos in corners_part6.items():
    expected = original_tab1.get(f'point{corner}', [40, 120, 0] if corner == 'D' else None)
    match = "[OK]" if pos == expected else "[MISMATCH]"
    print(f"  {corner}: {pos} {match}")
print()

print("Full perimeter order (as stored in OrderedDict):")
for i, (name, pos) in enumerate(part6_tab1["points"].items(), 1):
    corner_marker = " <- CORNER" if name in ['A', 'B', 'C', 'D'] else ""
    print(f"  {i:2d}. {name:12s} {pos}{corner_marker}")
print()

# Check if perimeter forms a valid closed loop
print("Perimeter connectivity analysis:")
points_list = list(part6_tab1["points"].values())
for i in range(len(points_list)):
    p1 = points_list[i]
    p2 = points_list[(i + 1) % len(points_list)]
    dist = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2 + (p2[2] - p1[2])**2)**0.5
    names = list(part6_tab1["points"].keys())
    print(f"  {names[i]:12s} -> {names[(i + 1) % len(names)]:12s}: distance = {dist:.2f}")
print()

print("=" * 70)
print("PART 8 - Tab 1")
print("=" * 70)
print()

corners_part8 = {k: v for k, v in part8_tab1["points"].items() if k in ['A', 'B', 'C', 'D']}
print("Corner points present:")
for corner, pos in corners_part8.items():
    expected = original_tab1.get(f'point{corner}', [40, 120, 0] if corner == 'D' else None)
    match = "[OK]" if pos == expected else "[MISMATCH]"
    print(f"  {corner}: {pos} {match}")
print()

print("Full perimeter order (as stored in OrderedDict):")
for i, (name, pos) in enumerate(part8_tab1["points"].items(), 1):
    corner_marker = " <- CORNER" if name in ['A', 'B', 'C', 'D'] else ""
    print(f"  {i:2d}. {name:12s} {pos}{corner_marker}")
print()

print("=" * 70)
print("EDGE ANALYSIS")
print("=" * 70)
print()

# For Part 6, check which edges the flange points belong to
def which_edge(point, corners):
    """Determine which edge a point belongs to."""
    A, B, C, D = corners['A'], corners['B'], corners['C'], corners['D']

    # Check if point is on AB edge (same z, y between A and B)
    if abs(point[2] - A[2]) < 0.01 and abs(point[1] - A[1]) < 0.01:
        if min(A[0], B[0]) - 0.01 <= point[0] <= max(A[0], B[0]) + 0.01:
            return "AB edge"

    # Check if point is on BC edge (same z, x near B)
    if abs(point[2] - B[2]) < 0.01 and abs(point[0] - B[0]) < 0.01:
        if min(B[1], C[1]) - 0.01 <= point[1] <= max(B[1], C[1]) + 0.01:
            return "BC edge"

    # Check if point is on CD edge (same z, y near C)
    if abs(point[2] - C[2]) < 0.01 and abs(point[1] - C[1]) < 0.01:
        if min(C[0], D[0]) - 0.01 <= point[0] <= max(C[0], D[0]) + 0.01:
            return "CD edge"

    # Check if point is on DA edge (same z, x near D)
    if abs(point[2] - D[2]) < 0.01 and abs(point[0] - D[0]) < 0.01:
        if min(D[1], A[1]) - 0.01 <= point[1] <= max(D[1], A[1]) + 0.01:
            return "DA edge"

    return "outside/flange"

print("Part 6 - Flange point positions relative to edges:")
for name, pos in part6_tab1["points"].items():
    if name not in ['A', 'B', 'C', 'D']:
        edge = which_edge(pos, corners_part6)
        print(f"  {name:12s} {pos} -> {edge}")
print()

print("Part 8 - Flange point positions relative to edges:")
for name, pos in part8_tab1["points"].items():
    if name not in ['A', 'B', 'C', 'D']:
        edge = which_edge(pos, corners_part8)
        print(f"  {name:12s} {pos} -> {edge}")
print()

print("=" * 70)
print("EXPECTED vs ACTUAL ORDERING")
print("=" * 70)
print()

print("For a rectangle with flanges on AB and BC edges, expected perimeter order:")
print("  A -> (AB flange points) -> B -> (BC flange points) -> C -> D -> A")
print()

print("Part 6 actual order:")
actual_order_6 = list(part6_tab1["points"].keys())
print(f"  {' -> '.join(actual_order_6)}")
print()

# Check if corners appear in correct sequence
corners_in_order_6 = [name for name in actual_order_6 if name in ['A', 'B', 'C', 'D']]
print(f"Corner sequence: {' -> '.join(corners_in_order_6)}")
expected_corner_seq = ['A', 'B', 'C', 'D']
if corners_in_order_6 == expected_corner_seq:
    print("  [OK] Corners in correct sequence")
else:
    print(f"  [ERROR] Corners out of order! Expected: {' -> '.join(expected_corner_seq)}")
print()

print("Part 8 actual order:")
actual_order_8 = list(part8_tab1["points"].keys())
print(f"  {' -> '.join(actual_order_8)}")
print()

corners_in_order_8 = [name for name in actual_order_8 if name in ['A', 'B', 'C', 'D']]
print(f"Corner sequence: {' -> '.join(corners_in_order_8)}")
if corners_in_order_8 == expected_corner_seq:
    print("  [OK] Corners in correct sequence")
else:
    print(f"  [ERROR] Corners out of order! Expected: {' -> '.join(expected_corner_seq)}")

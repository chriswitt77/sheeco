"""
Test different strategies for determining correct point ordering.
"""
import numpy as np

def diagonals_cross_3d_original(p0, p3, p4, p7):
    """Current implementation from bend_strategies.py"""
    def segments_intersect_2d(a1, a2, b1, b2):
        d1 = np.array([a2[0] - a1[0], a2[1] - a1[1]], dtype=float)
        d2 = np.array([b2[0] - b1[0], b2[1] - b1[1]], dtype=float)

        cross = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(cross) < 1e-10:
            return False

        diff = np.array([b1[0] - a1[0], b1[1] - a1[1]], dtype=float)
        t = (diff[0] * d2[1] - diff[1] * d2[0]) / cross
        s = (diff[0] * d1[1] - diff[1] * d1[0]) / cross

        return 0.01 < t < 0.99 and 0.01 < s < 0.99

    p0, p3, p4, p7 = np.array(p0), np.array(p3), np.array(p4), np.array(p7)

    # Check XY, XZ, YZ projections
    if segments_intersect_2d(p3[:2], p4[:2], p7[:2], p0[:2]):
        return True
    if segments_intersect_2d([p3[0], p3[2]], [p4[0], p4[2]],
                              [p7[0], p7[2]], [p0[0], p0[2]]):
        return True
    if segments_intersect_2d([p3[1], p3[2]], [p4[1], p4[2]],
                              [p7[1], p7[2]], [p0[1], p0[2]]):
        return True

    return False


def should_swap_ordering_distance_based(FPyxL, FPyxR, FPyzR, FPyzL):
    """
    Determine if z-side ordering should be swapped using distance comparison.

    Strategy: The correct ordering should minimize the sum of diagonal distances.
    - Default ordering: (FPyxR to FPyzR) + (FPyzL to FPyxL)
    - Swapped ordering: (FPyxR to FPyzL) + (FPyzR to FPyxL)

    Returns True if swapped ordering has shorter total distance.
    """
    FPyxL = np.array(FPyxL)
    FPyxR = np.array(FPyxR)
    FPyzR = np.array(FPyzR)
    FPyzL = np.array(FPyzL)

    # Default ordering distances
    dist_default_1 = np.linalg.norm(FPyzR - FPyxR)  # R to R
    dist_default_2 = np.linalg.norm(FPyxL - FPyzL)  # L to L
    total_default = dist_default_1 + dist_default_2

    # Swapped ordering distances
    dist_swapped_1 = np.linalg.norm(FPyzL - FPyxR)  # R to L (swapped)
    dist_swapped_2 = np.linalg.norm(FPyxL - FPyzR)  # L to R (swapped)
    total_swapped = dist_swapped_1 + dist_swapped_2

    return total_swapped < total_default


def should_swap_ordering_improved(FPyxL, FPyxR, FPyzR, FPyzL):
    """
    Improved ordering determination combining diagonal crossing check with distance fallback.

    Returns True if z-side L/R should be swapped.
    """
    # First, try the diagonal crossing check
    crosses = diagonals_cross_3d_original(FPyxL, FPyxR, FPyzR, FPyzL)

    # Check if we're in a collinear/degenerate case by comparing distances
    FPyxL = np.array(FPyxL)
    FPyxR = np.array(FPyxR)
    FPyzR = np.array(FPyzR)
    FPyzL = np.array(FPyzL)

    # Default ordering distances
    dist_default_1 = np.linalg.norm(FPyzR - FPyxR)
    dist_default_2 = np.linalg.norm(FPyxL - FPyzL)
    total_default = dist_default_1 + dist_default_2

    # Swapped ordering distances
    dist_swapped_1 = np.linalg.norm(FPyzL - FPyxR)
    dist_swapped_2 = np.linalg.norm(FPyxL - FPyzR)
    total_swapped = dist_swapped_1 + dist_swapped_2

    # If distance difference is significant, use distance-based decision
    # This handles collinear cases where diagonal crossing check fails
    if abs(total_default - total_swapped) > 1.0:
        return total_swapped < total_default

    # Otherwise, trust the diagonal crossing check
    return crosses


# Test cases
test_cases = [
    {
        "name": "Problem case (part_id 4, x=10)",
        "FPyxL": [60.0, 90.0, 10.0],
        "FPyxR": [10.0, 90.0, 10.0],
        "FPyzR": [10.0, 90.0, 80.0],
        "FPyzL": [10.0, 90.0, 40.0],
        "expected_swap": True  # Should use swapped ordering
    },
    {
        "name": "Working case (part_id 4, x=20)",
        "FPyxL": [60.0, 90.0, 10.0],
        "FPyxR": [20.0, 90.0, 10.0],
        "FPyzR": [10.0, 90.0, 80.0],
        "FPyzL": [10.0, 90.0, 40.0],
        "expected_swap": True  # Should use swapped ordering
    },
    {
        "name": "Problem case (part_id 6, x=10)",
        "FPyxL": [60.0, 37.5, 9.682458365518542],
        "FPyxR": [10.0, 37.5, 9.682458365518542],
        "FPyzR": [10.0, 20.635083268962916, 75.0],
        "FPyzL": [10.0, 32.81754163448146, 27.817541634481458],
        "expected_swap": True  # Should use swapped ordering
    },
    {
        "name": "Working case (part_id 6, x=20)",
        "FPyxL": [60.0, 37.5, 9.682458365518542],
        "FPyxR": [20.0, 37.5, 9.682458365518542],
        "FPyzR": [10.0, 20.635083268962916, 75.0],
        "FPyzL": [10.0, 32.81754163448146, 27.817541634481458],
        "expected_swap": True  # Should use swapped ordering
    }
]

print("=" * 100)
print("TESTING DIFFERENT STRATEGIES")
print("=" * 100)

for test in test_cases:
    print(f"\n{test['name']}")
    print("-" * 100)

    # Original method
    original_result = diagonals_cross_3d_original(
        test["FPyxL"], test["FPyxR"], test["FPyzR"], test["FPyzL"]
    )

    # Distance-based method
    distance_result = should_swap_ordering_distance_based(
        test["FPyxL"], test["FPyxR"], test["FPyzR"], test["FPyzL"]
    )

    # Improved method (combining both)
    improved_result = should_swap_ordering_improved(
        test["FPyxL"], test["FPyxR"], test["FPyzR"], test["FPyzL"]
    )

    expected = test["expected_swap"]

    print(f"  Expected: {expected}")
    print(f"  Original (diagonals_cross_3d): {original_result} - {'PASS' if original_result == expected else 'FAIL'}")
    print(f"  Distance-based:                {distance_result} - {'PASS' if distance_result == expected else 'FAIL'}")
    print(f"  Improved (combined):           {improved_result} - {'PASS' if improved_result == expected else 'FAIL'}")

print("\n" + "=" * 100)
print("CONCLUSION")
print("=" * 100)
print("The distance-based heuristic correctly handles all test cases.")
print("The improved method (combining diagonal crossing + distance fallback) also works.")
print("Recommendation: Use the improved method for robustness.")

"""
Analyze the intermediate tab point ordering issue.
"""
import numpy as np

def diagonals_cross_3d(p0, p3, p4, p7):
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

    # Check XY projection
    if segments_intersect_2d(p3[:2], p4[:2], p7[:2], p0[:2]):
        return True

    # Check XZ projection
    if segments_intersect_2d([p3[0], p3[2]], [p4[0], p4[2]],
                              [p7[0], p7[2]], [p0[0], p0[2]]):
        return True

    # Check YZ projection
    if segments_intersect_2d([p3[1], p3[2]], [p4[1], p4[2]],
                              [p7[1], p7[2]], [p0[1], p0[2]]):
        return True

    return False


# Problem case (part_id 4) - produces WRONG ordering
print("=" * 80)
print("PROBLEM CASE (part_id 4) - Tab 0 at x=10")
print("=" * 80)
FPyxL_prob = np.array([60.0, 90.0, 10.0])  # FP01_0L
FPyxR_prob = np.array([10.0, 90.0, 10.0])  # FP01_0R
FPyzR_prob = np.array([10.0, 90.0, 80.0])  # FP01_1R
FPyzL_prob = np.array([10.0, 90.0, 40.0])  # FP01_1L

print(f"FPyxL (FP01_0L): {FPyxL_prob}")
print(f"FPyxR (FP01_0R): {FPyxR_prob}")
print(f"FPyzR (FP01_1R): {FPyzR_prob}")
print(f"FPyzL (FP01_1L): {FPyzL_prob}")
print()

crossing_prob = diagonals_cross_3d(FPyxL_prob, FPyxR_prob, FPyzR_prob, FPyzL_prob)
print(f"diagonals_cross_3d result: {crossing_prob}")
print(f"Resulting ordering: {'SWAPPED (L-R-L-R)' if crossing_prob else 'DEFAULT (R-L-R-L)'}")
print(f"Expected ordering: SWAPPED (L before R on side 1)")
print(f"Status: {'CORRECT' if crossing_prob else 'WRONG [X]'}")
print()

# Check diagonals
diag1_prob = (FPyxR_prob, FPyzR_prob)  # FP01_0R to FP01_1R
diag2_prob = (FPyzL_prob, FPyxL_prob)  # FP01_1L to FP01_0L
print(f"Diagonal 1 (FP01_0R to FP01_1R): {diag1_prob[0]} -> {diag1_prob[1]}")
print(f"Diagonal 2 (FP01_1L to FP01_0L): {diag2_prob[0]} -> {diag2_prob[1]}")
print(f"Diagonal 1 length: {np.linalg.norm(diag1_prob[1] - diag1_prob[0]):.2f}")
print(f"Diagonal 2 length: {np.linalg.norm(diag2_prob[1] - diag2_prob[0]):.2f}")
print()

# Working case (part_id 4) - produces CORRECT ordering
print("=" * 80)
print("WORKING CASE (part_id 4) - Tab 0 at x=20")
print("=" * 80)
FPyxL_work = np.array([60.0, 90.0, 10.0])  # FP01_0L
FPyxR_work = np.array([20.0, 90.0, 10.0])  # FP01_0R (x changed from 10 to 20)
FPyzR_work = np.array([10.0, 90.0, 80.0])  # FP01_1R
FPyzL_work = np.array([10.0, 90.0, 40.0])  # FP01_1L

print(f"FPyxL (FP01_0L): {FPyxL_work}")
print(f"FPyxR (FP01_0R): {FPyxR_work}")
print(f"FPyzR (FP01_1R): {FPyzR_work}")
print(f"FPyzL (FP01_1L): {FPyzL_work}")
print()

crossing_work = diagonals_cross_3d(FPyxL_work, FPyxR_work, FPyzR_work, FPyzL_work)
print(f"diagonals_cross_3d result: {crossing_work}")
print(f"Resulting ordering: {'SWAPPED (L-R-L-R)' if crossing_work else 'DEFAULT (R-L-R-L)'}")
print(f"Expected ordering: SWAPPED (L before R on side 1)")
print(f"Status: {'CORRECT [OK]' if crossing_work else 'WRONG'}")
print()

# Check diagonals
diag1_work = (FPyxR_work, FPyzR_work)
diag2_work = (FPyzL_work, FPyxL_work)
print(f"Diagonal 1 (FP01_0R to FP01_1R): {diag1_work[0]} -> {diag1_work[1]}")
print(f"Diagonal 2 (FP01_1L to FP01_0L): {diag2_work[0]} -> {diag2_work[1]}")
print(f"Diagonal 1 length: {np.linalg.norm(diag1_work[1] - diag1_work[0]):.2f}")
print(f"Diagonal 2 length: {np.linalg.norm(diag2_work[1] - diag2_work[0]):.2f}")
print()

# Analysis
print("=" * 80)
print("ROOT CAUSE ANALYSIS")
print("=" * 80)
print("In the PROBLEM case:")
print("  - Three flange points are collinear at (x=10, y=90): FP01_0R, FP01_1R, FP01_1L")
print("  - They differ only in Z: z=10, z=80, z=40")
print("  - Diagonal 1 is a vertical line segment in XZ: (10,10) to (10,80)")
print("  - Diagonal 2 goes from (10,40) to (60,10) in XZ")
print("  - These segments share the point x=10 but don't cross in the INTERIOR")
print("  - Therefore diagonals_cross_3d returns False (no interior crossing)")
print("  - This leads to DEFAULT ordering which is WRONG")
print()
print("In the WORKING case:")
print("  - Only two points are at x=10: FP01_1R and FP01_1L")
print("  - FP01_0R is now at x=20, so diagonal 1 is not vertical")
print("  - The diagonals now DO cross in their interior")
print("  - Therefore diagonals_cross_3d returns True")
print("  - This leads to SWAPPED ordering which is CORRECT")
print()
print("CONCLUSION:")
print("  The diagonals_cross_3d function fails when points are collinear or nearly collinear.")
print("  We need a more robust method to determine the correct point ordering.")

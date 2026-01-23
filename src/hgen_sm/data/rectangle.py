import copy
import numpy as np


class Rectangle:
    """Represents the input rectangle by the user. Fourth Point D is determined automatically."""
    def __init__(self, tab_id: int, A: float, B: float, C: float, mounts = None):
        self.tab_id = tab_id

        A = np.array(A, dtype=np.float64)
        B = np.array(B, dtype=np.float64)
        C = np.array(C, dtype=np.float64)
        A, B, C, D = self.determine_fourth_point(A, B, C)

        self.points = {
            'A': np.array(A, dtype=np.float64), 
            'B': np.array(B, dtype=np.float64), 
            'C': np.array(C, dtype=np.float64), 
            'D': np.array(D, dtype=np.float64), 
            }
        # self.corners = [self.A, self.B, self.C, self.D]
        self.mounts = mounts

    def __repr__(self):
        return f"<Rectangle on Tab {self.tab_id}>"
    
    @staticmethod
    def determine_fourth_point(A, B, C):
        """
        Given three points that form a rectangle, determine the fourth point
        and reorder all points to form proper rectangle edges (A->B->C->D->A).

        The three input points can be in any order. The algorithm:
        1. Identifies which point is the "corner" (has perpendicular edges to the other two)
        2. Reorders points so they form consecutive rectangle corners
        3. Calculates the fourth point

        Returns: A, B, C, D ordered to form rectangle perimeter
        """
        # Try each point as potential corner point
        # The corner point has two perpendicular edges to the other points

        points = [A, B, C]
        point_pairs = [
            (0, 1, 2),  # A as corner, B and C adjacent
            (1, 0, 2),  # B as corner, A and C adjacent
            (2, 0, 1)   # C as corner, A and B adjacent
        ]

        tolerance = 1e-6

        for corner_idx, p1_idx, p2_idx in point_pairs:
            corner = points[corner_idx]
            p1 = points[p1_idx]
            p2 = points[p2_idx]

            # Vectors from corner to the other two points
            v1 = p1 - corner
            v2 = p2 - corner

            # Check if perpendicular (dot product should be ~0)
            dot_product = np.dot(v1, v2)

            if abs(dot_product) < tolerance:
                # Found the corner! Now p1 and p2 are adjacent to corner
                # Rectangle is: corner -> p1 -> fourth_point -> p2 -> corner
                # So: A=corner, B=p1, C=fourth_point, D=p2
                # Fourth point: D = p1 + p2 - corner

                A_new = corner
                B_new = p1
                D_new = p2
                C_new = p1 + p2 - corner  # The fourth point

                return A_new, B_new, C_new, D_new

        # If no perpendicular vectors found, fall back to parallelogram formula
        # (This shouldn't happen if input truly forms a rectangle)
        print("Warning: Input points do not form a proper rectangle. Using parallelogram formula.")
        AB = B - A
        D = C - AB
        return A, B, C, D
    
    def expand_corners(self, offset: float):
        """Placeholder for potential future function."""
        pass
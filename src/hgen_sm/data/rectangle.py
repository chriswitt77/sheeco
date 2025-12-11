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

        self.corners = {
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
        Given three Point objects (A, B, C), compute fourth point D.
        """
        AB = B - A
        AC = C - A
        # If AB and AC are swapped (zigzag), flip AC to keep CCW order
        normal = np.cross(AB, AC)
        if np.dot(np.cross(AB, AC), normal) < 0:
            B, C = C, B
            AB = B - A
            AC = C - A

        D = A + AB + AC
        return A, B, C, D
    
    def expand_corners(self, offset: float):
        """Placeholder for potential future function."""
        pass
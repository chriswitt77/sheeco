import copy
import numpy as np


class Rectangle:
    """Represents the input rectangle by the user"""
    def __init__(self, tab_id: int, pointA: float, pointB: float, pointC: float, mounts = None):

        self.tab_id = tab_id
        self.pointA = np.array(pointA, dtype=np.float64)
        self.pointB = np.array(pointB, dtype=np.float64)
        self.pointC = np.array(pointC, dtype=np.float64)
        self.pointA, self.pointB, self.pointC, self.pointD = self.determine_fourth_point(self.pointA, self.pointB, self.pointC)

        self.corners = [self.pointA, self.pointB, self.pointC, self.pointD]
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
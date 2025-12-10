import copy
import numpy as np

class Mount:
    """
    Represents a mounting feature located by its coordinates relative to a tab's local origin.
    """
    def __init__(self, tab_id: int, u: float, v: float, size: float = 5.0):
        self.tab_id = tab_id
        # This replaces dist_AB and dist_BC with standardized (u, v) planar coordinates.
        self.u = u
        self.v = v
        self.size = size  # e.g., radius for a hole
        self.type = "Hole"

    def get_local_coordinates(self) -> tuple[float, float]:
        """Returns the location in the tab's local (u, v) system."""
        return (self.u, self.v)
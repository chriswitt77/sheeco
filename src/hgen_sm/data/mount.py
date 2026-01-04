import numpy as np


class Mount:
    """
    Represents a mounting feature (e.g., screw hole) on a tab.
    Can be initialized either with:
    - 3D coordinates (x, y, z) - will be converted to local (u, v)
    - Local coordinates (u, v) directly
    """

    def __init__(self, tab_id: int, coordinates=None, u: float = None, v: float = None, size: float = 5.0):
        self.tab_id = tab_id
        self.size = size  # e.g., radius for a hole
        self.type = "Hole"

        # Store both 3D and local coordinates
        if coordinates is not None:
            # 3D coordinates provided
            self.coordinates_3d = np.array(coordinates, dtype=np.float64)
            self.u = None
            self.v = None
        elif u is not None and v is not None:
            # Local coordinates provided
            self.u = u
            self.v = v
            self.coordinates_3d = None
        else:
            raise ValueError("Either coordinates (3D) or (u, v) must be provided")

    def compute_local_coordinates(self, tab):
        """
        Convert 3D coordinates to local (u, v) based on tab's rectangle.

        Args:
            tab: Tab object with points dictionary containing A, B, C
        """
        if self.coordinates_3d is None:
            return  # Already have local coordinates

        A = tab.points['A']
        B = tab.points['B']
        C = tab.points['C']

        # Local coordinate system: u along AB, v along AC
        AB = B - A
        AC = C - A

        # Project mount point onto tab plane
        AP = self.coordinates_3d - A

        # Calculate u, v
        self.u = np.dot(AP, AB) / np.dot(AB, AB)
        self.v = np.dot(AP, AC) / np.dot(AC, AC)

    def get_local_coordinates(self) -> tuple[float, float]:
        """Returns the location in the tab's local (u, v) system."""
        return (self.u, self.v)

    def get_3d_coordinates(self, tab) -> np.ndarray:
        """
        Compute 3D coordinates from local (u, v) coordinates.

        Args:
            tab: Tab object with points dictionary containing A, B, C
        """
        if self.coordinates_3d is not None:
            return self.coordinates_3d

        A = tab.points['A']
        B = tab.points['B']
        C = tab.points['C']

        AB = B - A
        AC = C - A

        # Reconstruct 3D point
        point_3d = A + self.u * AB + self.v * AC
        return point_3d

    def __repr__(self):
        if self.u is not None and self.v is not None:
            return f"<Mount: tab={self.tab_id}, u={self.u:.2f}, v={self.v:.2f}>"
        else:
            return f"<Mount: tab={self.tab_id}, 3D={self.coordinates_3d}>"
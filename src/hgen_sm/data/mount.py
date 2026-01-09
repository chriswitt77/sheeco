import copy
import numpy as np

class Mount:
    """
    Represents a mounting feature located by its coordinates relative to a tab's local origin.

    Local coordinate system (based on rectangle A -> B -> C -> D):
    - u: distance along AB direction from point A
    - v: distance along BC direction from point A (perpendicular to AB in the plane)
    - The mount must lie on the plane defined by the rectangle
    """
    def __init__(self, tab_id: int, u: float, v: float, size: float = 5.0,
                 global_coords: np.ndarray = None):
        self.tab_id = tab_id
        # Local (u, v) planar coordinates
        self.u = u
        self.v = v
        self.size = size  # e.g., radius for a hole
        self.type = "Hole"
        # Store original 3D coordinates if provided
        self.global_coords = global_coords

    def __repr__(self):
        return f"<Mount tab={self.tab_id} u={self.u:.2f} v={self.v:.2f}>"

    def get_local_coordinates(self) -> tuple[float, float]:
        """Returns the location in the tab's local (u, v) system."""
        return (self.u, self.v)

    def get_global_coordinates(self) -> np.ndarray:
        """Returns the original 3D global coordinates if available."""
        return self.global_coords

    @staticmethod
    def from_global_coordinates(tab_id: int, global_point: np.ndarray,
                                 A: np.ndarray, B: np.ndarray, C: np.ndarray,
                                 size: float = 5.0, tolerance: float = 1e-6) -> 'Mount':
        """
        Creates a Mount from 3D global coordinates by converting to local (u, v).

        Rectangle geometry: A -> B -> C -> D where D = C - AB
        - Edge AB connects A and B
        - Edge BC connects B and C (perpendicular to AB)

        Args:
            tab_id: ID of the tab this mount belongs to
            global_point: 3D coordinates of the mount [x, y, z]
            A, B, C: Corner points of the rectangle defining the local coordinate system
            size: Size of the mount (e.g., hole radius)
            tolerance: Tolerance for checking if point lies on the plane

        Returns:
            Mount object with local (u, v) coordinates

        Raises:
            ValueError: If the point does not lie on the rectangle's plane
        """
        global_point = np.array(global_point, dtype=np.float64)
        A = np.array(A, dtype=np.float64)
        B = np.array(B, dtype=np.float64)
        C = np.array(C, dtype=np.float64)

        # Calculate local coordinate system vectors
        AB = B - A
        BC = C - B

        # Calculate plane normal
        normal = np.cross(AB, BC)
        normal_len = np.linalg.norm(normal)
        if normal_len < 1e-9:
            raise ValueError("Rectangle points are collinear, cannot define a plane")
        normal = normal / normal_len

        # Check if point lies on the plane
        AP = global_point - A
        distance_to_plane = abs(np.dot(AP, normal))
        if distance_to_plane > tolerance:
            raise ValueError(
                f"Mount point {global_point} does not lie on the rectangle plane. "
                f"Distance to plane: {distance_to_plane:.6f} (tolerance: {tolerance})"
            )

        # Convert to local (u, v) coordinates
        # u = projection of AP onto AB direction (distance along AB from A)
        # v = projection of AP onto BC direction (distance along BC direction from A)
        AB_len = np.linalg.norm(AB)
        BC_len = np.linalg.norm(BC)

        if AB_len < 1e-9 or BC_len < 1e-9:
            raise ValueError("Rectangle has zero-length edge")

        u = np.dot(AP, AB) / AB_len  # Distance along AB
        v = np.dot(AP, BC) / BC_len  # Distance along BC direction

        return Mount(tab_id=tab_id, u=u, v=v, size=size, global_coords=global_point.copy())
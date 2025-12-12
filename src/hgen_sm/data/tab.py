import copy
import numpy as np
from typing import Dict, Optional

from .rectangle import Rectangle
from .bend import Bend


class Tab:
    """Represents a single, planar section of the SM part"""
    def __init__(self, tab_id: int, rectangle = None, mounts = None):
        self.tab_id = tab_id
        self.rectangle: 'Rectangle' = rectangle or None
        self.points: Dict[str, np.ndarray] = {
            'A': rectangle.corners['A'],
            'B': rectangle.corners['B'],
            'C': rectangle.corners['C'],
            'D': rectangle.corners['D']
        }
        self.mounts = []
        self.corner_usage: Dict[str, Optional[str]] = {'A': None, 'B': None, 'C': None, 'D': None}


    def __repr__(self):
        # 1. Start the representation string
        repr_str = f"<Tab: ID={self.tab_id}"
        
        # 2. Check and append points count
        if self.points:
            repr_str += f", Points={len(self.points)}"
        
        # 3. Check and append occupied corner points (CP) count
        if self.occ_CP:
            repr_str += f", Used CPs={len(self.occ_CP)}"
        
        # 4. Check and append mounts count
        if self.mounts:
            repr_str += f", Mounts={len(self.mounts)}"
        
        # 5. Close the representation string
        repr_str += ">"
        
        return repr_str


    def copy(self):
        return copy.deepcopy(self)
    
    def insert_points(self, L, add_points):
        """
        Inserts a sequence of new geometric points into the points 
        dictionary immediately following the L.
        
        This method rebuilds the dictionary to maintain insertion order.
        """
        L_id = list(L.keys())[0]
        if L_id not in self.points:
            raise ValueError(f"Start corner ID '{L}' not found.")

        new_points: Dict[str, np.ndarray] = {}
        insertion_done = False
        
        for key, value in self.points.items():
            if not insertion_done:
                # 1. Copy points before the insertion point
                new_points[key] = value
                
                # 2. Insertion point found: copy L and insert sequence
                if key == L_id:
                    new_points.update(add_points)
                    insertion_done = True
            
            else:
                # 3. Skip the original end_corner_id (already included in the sequence)
                # if key == end_corner_id:
                #     continue
                
                # 4. Copy remaining points (C, D, etc.)
                new_points[key] = value

        self.points = new_points
        
    def remove_point(self, point):
        """
        Removes a specified point (key) from the ordered_geometry dictionary.
        Used when a corner is entirely consumed (e.g., in a complex bend or trim).
        """
        point_id = list(point.keys())[0]
        if point_id not in self.points:
            return 
        
        new_points: Dict[str, np.ndarray] = {}
        
        for key, value in self.points.items():
            if key != point:
                new_points[key] = value
                
        self.points = new_points
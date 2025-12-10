import copy
import numpy as np











# from typing import List
# class Topology:
#     def __init__(self, sequence, rectangles = None):
#         self.rectangles = rectangles or None
#         self.sequence = sequence

#     def get_pairs(self) -> List[Pair]:
#         """Returns the ordered list of Pairs ready for the connector."""
#         return self.sequence
    
#     def __repr__(self):
#         return f"<Topology: {self.sequence}>"
    
    # def get_rect_id(self, tab_id: str) -> 'Rectangle':
    #     """
    #     Searches the topology's list of initial rectangles and returns 
    #     the Rectangle object matching the given ID.
    #     """
    #     for rect in self.sequence: # Note: Accesses self.initial_rectangles
    #         if rect.tab_id == tab_id:
    #             return rect
        
        # Raise an error if the ID is invalid for this topology
        # raise ValueError(f"Rectangle ID '{tab_id}' not found in this topology.")

    # # Future method for the separation module
    # def get_tabs_with_multiple_mounts(self) -> List[str]:
    #     """Identifies tabs that might need separation."""
    #     return [
    #         tab_id for tab_id, mounts in self.tab_mounts.items() 
    #         if len(mounts) > 1
    #     ]
    

# class State:
    # def __init__(self, rectangles, planes, bends, single_bend=None, corner_points=None, flanges=None, points=None, elements=None, comment=None):
    #     self.rectangles = rectangles
    #     self.planes = planes
    #     self.bends = bends
    #     self.single_bend = single_bend or False
    #     self.corner_points = corner_points or []
    #     self.flanges = flanges or []
    #     self.points = points or {}
    #     self.elements = elements or []
    #     self.comment = comment or [] # FOR DEBUGGING

    # def copy(self):
    #     return State(
    #         rectangles=copy.deepcopy(self.rectangles),
    #         planes=copy.deepcopy(self.planes),
    #         bends=copy.deepcopy(self.bends),
    #         single_bend=copy.deepcopy(self.single_bend),
    #         corner_points=copy.deepcopy(self.corner_points),
    #         flanges=copy.deepcopy(self.flanges),
    #         points = copy.deepcopy(self.points),
    #         elements=copy.deepcopy(self.elements)
    #     )

    # def __repr__(self):
    #     return (f"<State bends={len(self.flanges)}, tabs={len(self.tabs)}, "
    #             f"planes={len(self.planes)}, intersections={len(self.bends)}>")



    # @dataclass
# class Point:
#     """A simple 3D point structure"""
#     x: float
#     y: float
#     z: float

#     def to_array(self) -> np.ndarray:
#         """Converts the Point to a NumPy array for vector math."""
#         return np.array([self.x, self.y, self.z])
    
#     @staticmethod
#     def from_array(arr: np.ndarray):
#         """Creates a Point from a NumPy array."""
#         return Point(arr[0], arr[1], arr[2])

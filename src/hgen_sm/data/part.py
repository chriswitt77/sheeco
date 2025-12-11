import copy
from typing import Dict, List, Optional

from .rectangle import Rectangle
from .tab import Tab
from .bend import Bend
from .segment import Segment

class Part:
    """Represents the entire, 3D sheet metal part"""
    def __init__(self, sequence = None, tabs = None):
        self.sequence = sequence or None
        self.tabs: Dict[str, 'Tab'] = tabs or {}
        self.bends: Dict[str, 'Bend'] = {}

    def copy(self):
        return copy.deepcopy(self)





















class _Part:
    """Represents the entire, 3D sheet metal part"""
    def __init__(self, tabs = None, bends = None, rects = None, sequence = None, segments = None):
        self.rects: list['Rectangle'] = rects or []
        self.segments: list['Segment'] = segments or []
        self.sequence = sequence or []
        self.tabs: list['Tab'] = tabs or []
        self.bends: list['Bend'] = bends or []
        self.history: list[str] = []

    def copy(self):
        return copy.deepcopy(self)
    
    def __repr__(self):
        return f"<Part: {len(self.tabs)} tabs, {len(self.bends)} bends>"
    
    def get_tab_id(self, tab_id: int) -> 'Rectangle':
        """
        Searches the topology's list of initial rectangles and returns 
        the Rectangle object matching the given ID.
        """
        for pair in self.sequence:
            if pair.tab_x_id == tab_id:
                return pair.tab_x_id
            if pair.tab_z_id == tab_id:
                return pair.tab_z_id
            # if pair.tab_y == tab_id:
            #     return pair.tab_y
        raise ValueError(f"Rectangle ID '{tab_id}' not found in this topology.")
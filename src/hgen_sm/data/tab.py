import copy
import numpy as np

from .rectangle import Rectangle
from .bend import Bend

class Tab:
    """Represents a single, planar section of the SM part"""
    def __init__(self, tab_id: int, rect: Rectangle, CP=None, used_CP=None):
        self.tab_id = tab_id
        self.rect = rect
        self.bend = Bend
        # self.used_CP = used_CP or []

        self.corner_usage = {
            'A': False,
            'B': False,
            'C': False,
            'D': False,
        }

    def copy(self):
        return copy.deepcopy(self)

    def update_geometry(self, new_rect: Rectangle):
        self.rect = new_rect
import copy
import numpy as np

class Bend:
    """Shared Property of two tabs"""
    def __init__(
            self, 
            position = None, 
            orientation = None, 
            BPL = None, 
            BPR = None, 
            FPL_A = None, 
            FPL_B = None, 
            FPR_A = None, 
            FPR_B = None, 
            BPM = None,
            tab_x = None,
            tab_y = None,
            tab_z = None
            ):
        
        self.position = position
        self.orientation = orientation
        self.BPL = BPL
        self.BPR = BPR
        self.BPM = BPM

        self.tab_x = tab_x
        self.tab_y = tab_y
        self.tab_z = tab_z

    def copy(self):
        return copy.deepcopy(self)


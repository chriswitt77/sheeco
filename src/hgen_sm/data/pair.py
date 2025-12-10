import copy
import numpy as np

class Pair:
    def __init__(self, tab_x_id: int, tab_z_id: int, tab_y_id: int = None):
        self.tab_x_id = tab_x_id
        self.tab_y_id = tab_y_id or None
        self.tab_z_id = tab_z_id

    def __repr__(self):
        return f"<Pair({self.tab_x_id},{self.tab_z_id})>"

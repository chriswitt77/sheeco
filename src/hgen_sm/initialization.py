from src.hgen_sm.data import Rectangle, Part, Tab
from typing import Dict

def initialize_objects(rectangle_inputs):
    """Convert User Input into usable data and initialize Part"""
    
    tabs: Dict[str, 'Tab'] = {}

    for i, rect in enumerate(rectangle_inputs):
        tab_id = str(i)
        
        # Convert raw lists to Point objects
        A = rect['pointA']
        B = rect['pointB']
        C = rect['pointC']
        
        # Create the Rectangle object
        rectangle = Rectangle(tab_id=int(i), A=A, B=B, C=C)
        tab = Tab(tab_id=tab_id, rectangle=rectangle, mounts = None) 
        tabs[tab_id] = tab

    part = Part(tabs=tabs)

    return part
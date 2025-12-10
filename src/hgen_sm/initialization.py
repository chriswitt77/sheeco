from src.hgen_sm.data import Rectangle, Part, Tab

def initialize_objects(rectangle_inputs):
    
    rectangles = []
    tabs = []

    for i, rect in enumerate(rectangle_inputs):
        tab_id = int(i)
        
        # Convert raw lists to Point objects
        A = rect['pointA']
        B = rect['pointB']
        C = rect['pointC']
        
        # Create the Rectangle object
        rectangle = Rectangle(tab_id=tab_id, pointA=A, pointB=B, pointC=C)
        rectangles.append(rectangle)
        tabs.append(Tab(tab_id=tab_id, rect=rectangle))
    part = Part(tabs=tabs, rects=rectangles)

    return rectangles, tabs, part
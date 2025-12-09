from src.hgen_sm.data.classes import Part
from src.hgen_sm.find_connections.strategies import one_bend, two_bends

def find_connections(cfg, part, solutions):
    if cfg.get('design_exploration').get('single_bend', True): #not collision_tab_bend(bend, rectangles) and 
        solutions.append(one_bend(part, solutions))
    if cfg.get('design_exploration').get('double_bend', True):
        solutions.append(two_bends(part, solutions))

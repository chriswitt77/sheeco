from typing import List, Dict, Any
from src.hgen_sm.data import *

def determine_sequences(rectangles, cfg):
    topo_cfg = cfg.get('topologies', {})
    tab_ids: List[int] = [rect.tab_id for rect in rectangles]
    topologies = []

    if topo_cfg.get('simple_topology', True):
        pair_sequence = []
        for i in range(len(tab_ids) - 1): 
            tab_x_id = tab_ids[i]
            tab_z_id = tab_ids[i + 1]

            new_pair = Pair(tab_x_id=tab_x_id, tab_z_id=tab_z_id)
            pair_sequence.append(new_pair)
        
        topologies.append(pair_sequence)
        
    else:
        # Future implementation for complex topologies
        print("Complex Topologies not implemented yet")

    return topologies
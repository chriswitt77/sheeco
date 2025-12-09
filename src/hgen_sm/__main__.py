import time
start_time = time.time()

import pyvista as pv
import yaml

from config.user_input import RECTANGLE_INPUTS
with open("config/config.yaml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

import itertools

from hgen_sm.data.classes import Part, Pair, Rectangle, Tab
from src.hgen_sm.determine_topology import determine_sequences
from src.hgen_sm.find_connections import find_connections 
from src.hgen_sm.part_assembly import assemble
from hgen_sm.plotting import plot_assembly

# import matplotlib
# matplotlib.use("Agg")

def main():
    # Initialization
    plot_cfg = cfg.get('plot', {})
    plotter = pv.Plotter()

    # Import user input
    rectangle_inputs = RECTANGLE_INPUTS
    rectangles = []
    
    for i, rect_data in enumerate(rectangle_inputs):
        tab_id = int(i)
        
        # Convert raw lists to Point objects
        A = rect_data['pointA']
        B = rect_data['pointB']
        C = rect_data['pointC']
        
        # Create the Rectangle object
        rect = Rectangle(tab_id=tab_id, A=A, B=B, C=C)
        rectangles.append(rect)
        
    # Determine sensible Topologies
    sequences = determine_sequences(rectangles, cfg)

    # Find ways to connect pairs
    
    solutions = []
    for sequence in sequences:
        initial_part = Part(rects=rectangles, sequence=sequence)
        connections = []
        for pair in initial_part.sequence:
            new_part = initial_part
            tab_x_id = pair.tab_x_id
            rect_x = new_part.rectangles[tab_x_id]
            tab_z_id = pair.tab_z_id
            rect_z = new_part.rectangles[tab_z_id]
            solutions.append(find_connections(initial_part, rect_x, rect_z, cfg))

    # Call assemble, which creates global parts
        for combination in itertools.product(*connections):
            assembly = assemble(combination, cfg)
            solutions.extend(assembly)

    print("--- %s seconds ---" % (time.time() - start_time))
    print(f"Found {len(solutions)-1} solutions")

    # Plot solutions
    if len(solutions) > 0: pass
    plot_assembly(plotter, plot_cfg, solutions)

if __name__ == '__main__':
    main()
import time
start_time = time.time()

import pyvista as pv
import yaml

from config.user_input import RECTANGLE_INPUTS
with open("config/config.yaml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

import itertools

from src.hgen_sm.initialization import initialize_objects
from src.hgen_sm.data import *
from src.hgen_sm.determine_sequences import determine_sequences
from src.hgen_sm.create_segments import create_segments 
from src.hgen_sm.part_assembly import assemble
from src.hgen_sm.plotting import plot_assembly

# import matplotlib
# matplotlib.use("Agg")

def main():
    # Initialization
    segment_cfg = cfg.get('design_exploration', {})
    plot_cfg = cfg.get('plot', {})
    plotter = pv.Plotter()

    # Import user input
    rectangles, tabs, part = initialize_objects(RECTANGLE_INPUTS)
    
    # Determine sensible Topologies
    sequences = determine_sequences(rectangles, cfg)

    # Find ways to connect pairs
    solutions = []
    for sequence in sequences:
        segment_library = []
        for pair in sequence:
            segment = Segment(tab_x_id=pair.tab_x_id, tab_z_id=pair.tab_z_id, rects=rectangles, tabs=tabs)
            segment_library.extend(create_segments(segment, segment_cfg))

    # Call assemble, which creates global parts
        for segment in itertools.product(segment_library):
            assembly = assemble(segment, cfg)
            solutions.extend(assembly)

    print("--- %s seconds ---" % (time.time() - start_time))
    print(f"Found {len(solutions)-1} solutions")

    # Plot solutions
    if len(solutions) > 0: pass
    plot_assembly(plotter, plot_cfg, solutions)

if __name__ == '__main__':
    main()
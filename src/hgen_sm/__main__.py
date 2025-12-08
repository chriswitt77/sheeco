import time
start_time = time.time()

import pyvista as pv
import yaml

from config.user_input import rect0, rect1, rect2

import itertools

from src.hgen_sm.classes import Part, Pair, Rectangle, Tab
from src.hgen_sm.determine_topology import choose_pairs
from src.hgen_sm.find_connections import connect_pair
from src.hgen_sm.part_assembly import assemble
from hgen_sm.plotting import plot_assembly

with open("config/config.yaml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

# import matplotlib
# matplotlib.use("Agg")

def main():
    # Initialization
    plot_cfg = cfg.get('plot', {})
    plotter = pv.Plotter()

    # Import user input
    rectangles = rect0, rect1, rect2

    # Determine sensible Topologies
    topologies = []
    topologies.append(choose_pairs(rectangles, cfg))

    # Find ways to connect pairs
    part = Part()
    solutions = []
    for topology in topologies:
        connections = []
        for pair in topology:
            connections.append(connect_pair(part, pair, cfg))

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
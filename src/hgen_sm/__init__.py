# src/hgen-sm/__init__.py
"""
hgen-sm: Sheet Metal Part Generator
====================================

Automated generation of manufacturable sheet metal parts from planar rectangular surfaces.

Overview
--------
Given input rectangles in 3D space with optional mounting features (screw holes),
this package generates geometrically valid and manufacturable sheet metal solutions
by creating bending connections between surfaces.

Algorithm Pipeline
------------------
1. **Initialization**: Convert input rectangles to Tab objects with proper geometry
   and mount handling. Rectangle edges are automatically adjusted to maintain minimum
   distances from mounting holes.

2. **Topology Generation**: Determine assembly sequences (which tabs connect to which).
   - Simple topology: Sequential chain (minimum spanning tree)
   - Tree topology: All possible spanning trees with diversity selection
   - All pairs: Fully connected exploration
   - Optional surface separation: Split tabs with multiple mounts into sub-surfaces

3. **Segment Creation**: Generate geometric connection solutions for each tab pair.
   - Zero-bend: Direct connection for coplanar tabs
   - Single-bend: Connection via plane intersection
   - Double-bend: Connection via intermediate triangular tab with perpendicular planes

4. **Part Assembly**: Merge segments into complete parts with manufacturability validation.
   - Multi-tab merge: Combines tabs with multiple connections
   - Edge-usage constraint: Maximum one connection per edge
   - Collision detection and geometry validation

5. **Visualization & Export**: Interactive 3D visualization with PyVista and
   FeatureScript export for Onshape CAD integration.

Key Features
------------
- Automatic rectangle geometry processing (any corner point order)
- Mount-aware edge adjustment for clearance requirements
- Comprehensive topology exploration with diversity-based tree selection
- Multiple bend strategies with automatic selection based on geometry
- Sibling surface handling (split surfaces require bridge connections)
- Manufacturability-first design (minimum bend angles, flange widths, edge spacing)
- Interactive solution navigation with embedded CAD export

Usage Example
-------------
>>> from config.user_input import RECTANGLE_INPUTS
>>> import yaml
>>> with open('config/config.yaml') as f:
...     cfg = yaml.load(f, Loader=yaml.FullLoader)
>>>
>>> # Initialize from input rectangles
>>> part = initialize_objects(RECTANGLE_INPUTS)
>>>
>>> # Generate topologies and create segments
>>> variants = determine_sequences(part, cfg)
>>> solutions = []
>>> for variant_part, sequences in variants:
...     for sequence in sequences:
...         segments_library = []
...         for pair in sequence:
...             tab_x, tab_z = variant_part.tabs[pair[0]], variant_part.tabs[pair[1]]
...             segment = Part(sequence=pair, tabs={'tab_x': tab_x, 'tab_z': tab_z})
...             segments_library.append(create_segments(segment, cfg['design_exploration'], cfg['filter']))
...
...         # Assemble complete parts
...         for segments_combination in itertools.product(*segments_library):
...             new_part = part_assembly(variant_part.copy(), segments_combination, cfg['filter'])
...             if new_part:
...                 solutions.append(new_part)
>>>
>>> # Visualize and export
>>> plot_solutions(solutions, plot_cfg=cfg['plot'])

Configuration
-------------
Main settings in config/config.yaml:
- topologies: Control sequence generation (simple/tree/all_pairs, max_tree_topologies)
- surface_separation: Surface splitting parameters (split_along, allow_sibling_connections)
- design_exploration: Enable single_bend and/or double_bend strategies
- filter: Manufacturing constraints (Min Flange Width, Tabs cover Rects, etc.)
- plot: Visualization settings (element visibility, colors, labels)

Design rules in config/design_rules.py:
- Minimum flange width, bend angles, screw-to-edge distances

Input format in config/user_input.py:
- Rectangle definitions: pointA, pointB, pointC (fourth point computed automatically)
- Optional mounts: List of [x, y, z] coordinates for screw holes

Authors
-------
Maxim Moellhoff

Version
-------
0.4.0
"""

# Version information
__version__ = "0.4.0"
__author__ = "Maxim Moellhoff"

from src.hgen_sm.data import Part
from src.hgen_sm.initialization import initialize_objects
from src.hgen_sm.determine_sequences import determine_sequences
from src.hgen_sm.create_segments import create_segments
from src.hgen_sm.part_assembly import part_assembly
from src.hgen_sm.plotting.plot_assembly import plot_solutions, plot_input_rectangles

# Define what is available when the package is imported
__all__ = [
    "__main__",
    "__version__",
    "Part",
    "initialize_objects",
    "determine_sequences",
    "create_segments",
    "part_assembly",
    "plot_solutions",
    "plot_input_rectangles"
]
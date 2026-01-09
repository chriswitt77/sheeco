# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

hgen-sm is a sheet metal part generator that finds manufacturable ways to connect planar rectangular surfaces using bends. Given input rectangles in 3D space, it generates solutions by either finding plane intersections (single bend) or creating intermediate tabs (double bend).

## Commands

```bash
# Install (editable mode)
pip install -e .

# Run the generator
python -m hgen_sm

# Run tests
python tests/test_mount_processing.py
```

## Configuration

- `config/user_input.py` - Define input rectangles with points A, B, C and optional mount coordinates. Set `RECTANGLE_INPUTS` to choose which configuration to use.
- `config/config.yaml` - Control topology exploration, surface separation, filters, and plot settings.
- `config/design_rules.py` - Manufacturing constraints (flange dimensions, bend angles, mount distances).

## Architecture

### Pipeline Flow (`__main__.py`)

1. **Initialize** (`initialization.py`) - Convert user input to `Part` with `Tab` objects. Adjusts rectangle edges to maintain minimum distance from mount holes.

2. **Determine Sequences** (`determine_sequences/`) - Find valid connection orderings between tabs. Supports simple (sequential chain), tree, and all-pairs topologies. Surface separation splits tabs with multiple mounts.

3. **Create Segments** (`create_segments/`) - For each tab pair, generate connection geometries:
   - `one_bend`: Single bend at plane intersection
   - `two_bends`: Two bends with intermediate triangular tab

4. **Part Assembly** (`part_assembly/`) - Combine segments into complete parts, applying collision and geometry filters.

5. **Plot** (`plotting/`) - Visualize solutions using PyVista.

### Data Model (`data/`)

- `Part` - Complete sheet metal part containing tabs and bends
- `Tab` - Planar section with corner points (A,B,C,D), optional mounts, and bend references
- `Rectangle` - Input geometry defined by 3 points (D computed as C - AB)
- `Bend` - Connection between tabs with position and orientation
- `Mount` - Screw/attachment point with local (u,v) and global coordinates

### Key Abbreviations

- BP = Bending Point
- CP = Corner Point
- FP = Flange Point
- L/R = Left/Right side of flange
- tab_x, tab_z = Source and target tabs in a connection pair

### Geometry Conventions

Rectangles are defined by three points A, B, C where D = C - (B - A). Tab points are stored in an ordered dictionary representing the perimeter, with bend/flange points inserted between corners during segment creation.

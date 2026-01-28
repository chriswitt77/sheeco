# Segment Plotting Guide

## Overview

New plotting functions have been added to visualize segments **before** they are merged during assembly. This is extremely useful for:

1. **Debugging segment generation** - See what segments are created for each tab pair
2. **Understanding edge conflicts** - Visualize which edges are being used by connections
3. **Inspecting geometry** - View bend points, flange points, and intermediate tabs
4. **Comparing alternatives** - See all segment options side-by-side

## Quick Start

```python
from config.user_input import barda_example_one, barda_example_one_sequence
from src.hgen_sm import initialize_objects, Part, create_segments
from src.hgen_sm.plotting.plot_segments import plot_segments

import yaml
from pathlib import Path

# Load configuration
PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

# Initialize part
part = initialize_objects(barda_example_one)

# Generate segments for a pair
tab_x = part.tabs['0']
tab_z = part.tabs['1']
segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)
segments = create_segments(segment, segment_cfg, filter_cfg)

# Plot the segments
plot_segments(segments, title="My Segments")
```

## Available Functions

### 1. `plot_segments(segments, title, separate_windows, show_labels)`

Plot a list of segments together or in separate windows.

**Parameters:**
- `segments` (list): List of segment objects to plot
- `title` (str): Window title (default: "Segment Visualization")
- `separate_windows` (bool): If True, each segment in its own window (default: False)
- `show_labels` (bool): If True, show point labels (default: True)

**Example:**
```python
from src.hgen_sm.plotting.plot_segments import plot_segments

# Plot all segments in one window
plot_segments(segments, title="All Segments", separate_windows=False)

# Plot each segment in separate window for detailed inspection
plot_segments(segments, title="Segment Details", separate_windows=True)
```

**What you'll see:**
- Different tabs in different colors
- Corner points (A, B, C, D) in RED
- Bend points (BP) in GREEN
- Flange points (FP) in BLUE
- Segments spaced horizontally when plotted together

### 2. `plot_segment_pair(segment, pair_ids, title)`

Plot a single segment with connection arrow showing direction.

**Parameters:**
- `segment`: Single segment object
- `pair_ids` (tuple): Optional (tab_x_id, tab_z_id) for labeling
- `title` (str): Window title

**Example:**
```python
from src.hgen_sm.plotting.plot_segments import plot_segment_pair

# Plot first segment with arrow showing connection
plot_segment_pair(segments[0], pair_ids=('0', '1'), title="Connection Detail")
```

**What you'll see:**
- Single segment with all its tabs
- Red arrow from first tab to last tab showing connection direction
- Point labels for all bend/flange points

### 3. `plot_segments_for_sequence(part, sequence, segment_cfg, filter_cfg, max_per_pair)`

Generate and plot segments for each pair in a sequence (full pipeline visualization).

**Parameters:**
- `part`: Initialized Part object
- `sequence`: List of [tab_x_id, tab_z_id] pairs
- `segment_cfg`: Configuration dict for segment generation
- `filter_cfg`: Configuration dict for filtering
- `max_per_pair` (int): Maximum segments to plot per pair (default: 3)

**Example:**
```python
from src.hgen_sm.plotting.plot_segments import plot_segments_for_sequence
from config.user_input import barda_example_one_sequence

# Visualize segments for entire sequence
plot_segments_for_sequence(
    part,
    barda_example_one_sequence,
    segment_cfg,
    filter_cfg,
    max_per_pair=3
)
```

**What you'll see:**
- One plot window per pair in the sequence
- Up to 3 segments per pair (or specified max_per_pair)
- Console output showing how many segments generated per pair

### 4. `plot_segments_with_edge_colors(segments, title)`

Plot segments with edge highlighting to show which edges are being used.

**Parameters:**
- `segments` (list): List of segment objects
- `title` (str): Window title

**Example:**
```python
from src.hgen_sm.plotting.plot_segments import plot_segments_with_edge_colors

# Plot with edge usage highlighting
plot_segments_with_edge_colors(segments, title="Edge Usage Analysis")
```

**What you'll see:**
- Segments with their tabs
- RED LINES highlighting edges that have bend/flange points
- Easy identification of which edges (AB, BC, CD, DA) are being used

## Use Cases

### Use Case 1: Debug Edge Conflicts (barda_example_one)

```python
# Problem: All combinations filtered due to edge conflicts
# Solution: Visualize which edges are being used

from src.hgen_sm.plotting.plot_segments import plot_segments_with_edge_colors

# For tab 0 (has 3 connections)
pairs_with_tab_0 = [['3', '0'], ['0', '1'], ['0', '2']]

for pair in pairs_with_tab_0:
    # Generate segments
    segment_tabs = {'tab_x': part.tabs[pair[0]], 'tab_z': part.tabs[pair[1]]}
    segment = Part(sequence=pair, tabs=segment_tabs)
    segments = create_segments(segment, segment_cfg, filter_cfg)

    # Visualize edge usage
    plot_segments_with_edge_colors(segments, title=f"Pair {pair} - Edge Usage")
```

**Result:** You'll see that pairs ['0', '1'] and ['0', '2'] both use edge BC on tab 0, causing the conflict.

### Use Case 2: Compare Segment Alternatives

```python
# Problem: Multiple segments generated, which one is best?
# Solution: Plot them side-by-side

from src.hgen_sm.plotting.plot_segments import plot_segments

segments = create_segments(segment, segment_cfg, filter_cfg)
print(f"Generated {len(segments)} alternatives")

# View all alternatives together
plot_segments(segments, title=f"Comparing {len(segments)} alternatives")
```

**Result:** See all segment options in one view, compare geometry, bend angles, tab sizes, etc.

### Use Case 3: Inspect Two-Bend Intermediate Tabs

```python
# Problem: Want to see intermediate tab geometry
# Solution: Plot segments with labels

from src.hgen_sm.plotting.plot_segments import plot_segments

# Plot with detailed labels
plot_segments(segments, title="Intermediate Tab Details", show_labels=True)
```

**Result:** See the intermediate tab (tab_y) with all its bend points (BP01_0L, BP01_0R, BP01_1L, BP01_1R) and flange points.

### Use Case 4: Full Sequence Visualization

```python
# Problem: Want to see all segments in the entire sequence
# Solution: Use plot_segments_for_sequence

from src.hgen_sm.plotting.plot_segments import plot_segments_for_sequence

plot_segments_for_sequence(
    part,
    sequence,
    segment_cfg,
    filter_cfg,
    max_per_pair=5  # Show up to 5 segments per pair
)
```

**Result:** One plot window per pair, showing all generated segments. Console output shows counts.

## Understanding the Visualization

### Color Coding

**Tab Colors (rotating):**
- Tab 1: Blue (#648fff)
- Tab 2: Pink (#dc267f)
- Tab 3: Orange (#ffb000)
- Tab 4: Green (#26dc83)
- Tab 5: Purple (#785ef0)

**Point Colors:**
- 🔴 **Red**: Corner points (A, B, C, D) - Original rectangle corners
- 🟢 **Green**: Bend points (BP) - Where bending occurs
- 🔵 **Blue**: Flange points (FP) - Flange edges after bending
- ⚪ **Gray**: Other points

**Edge Highlighting (in plot_segments_with_edge_colors):**
- 🔴 **Red thick line**: Edge is being used for connection (has BP/FP near it)

### Reading the Plots

**One-Bend Segment:**
```
Tab 0 (source) --- bend line --- Tab 1 (target)
```
- 2 tabs total
- Corner points A, B, C, D visible on both tabs
- Bend points (BP) on one edge
- Flange points (FP) extending from bend points

**Two-Bend Segment (Approach 1 - Rectangular intermediate):**
```
Tab 0 (source) --- Tab Y (intermediate) --- Tab 1 (target)
```
- 3 tabs total
- Tab Y has 4 bend points (BP01_0L, BP01_0R, BP01_1L, BP01_1R)
- Tab Y is rectangular, perpendicular to both source and target

**Two-Bend Segment (Approach 2 - Triangular intermediate):**
```
Tab 0 (source) --- Tab Y (intermediate) --- Tab 1 (target)
```
- 3 tabs total
- Tab Y has 3 bend points (triangular)
- Used when Approach 1 doesn't work

## Tips

1. **Use `separate_windows=False` first** to get an overview, then `separate_windows=True` for detailed inspection

2. **Use `plot_segments_with_edge_colors`** when debugging edge conflicts - it clearly shows which edges are occupied

3. **Set `max_per_pair=1`** when visualizing long sequences to avoid too many windows

4. **Look for RED edges** that appear multiple times on the same tab - that's your edge conflict

5. **Compare intermediate tab sizes** between Approach 1 and Approach 2 to understand which is more efficient

## Integration with Existing Code

The plotting functions are already exported from `src.hgen_sm.plotting`, so you can import them directly:

```python
from src.hgen_sm.plotting import (
    plot_segments,
    plot_segment_pair,
    plot_segments_for_sequence,
    plot_segments_with_edge_colors
)
```

Or import from the module directly:

```python
from src.hgen_sm.plotting.plot_segments import plot_segments
```

## Test Script

Run the test script to see all functions in action:

```bash
python test_plot_segments.py
```

This will demonstrate all 4 plotting functions with the barda_example_one data.

## Troubleshooting

**Problem:** Plot window is empty
- **Solution:** Check that segments list is not empty. Print `len(segments)` before plotting.

**Problem:** Points are overlapping, hard to see
- **Solution:** Use `separate_windows=True` to plot each segment individually

**Problem:** Too many windows opening
- **Solution:** Reduce `max_per_pair` parameter or don't use `plot_segments_for_sequence` for long sequences

**Problem:** Can't see point labels
- **Solution:** Set `show_labels=True` (it's default) and zoom in on the plot

**Problem:** Want to save plot instead of showing
- **Solution:** Modify the functions to use `plotter.screenshot('filename.png')` instead of `plotter.show()`

"""
Test script to visualize segments before merging using the new plotting functions.
"""

import yaml
from pathlib import Path
from config.user_input import barda_example_one, barda_example_one_sequence
from src.hgen_sm import initialize_objects, Part, create_segments
from src.hgen_sm.plotting.plot_segments import (
    plot_segments,
    plot_segment_pair,
    plot_segments_for_sequence,
    plot_segments_with_edge_colors
)

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("SEGMENT VISUALIZATION TEST")
print("="*80)

# Initialize part
part = initialize_objects(barda_example_one)
sequence = barda_example_one_sequence

print(f"\nSequence: {sequence}")

# Example 1: Plot segments for first pair
print(f"\n{'='*80}")
print(f"EXAMPLE 1: Visualize segments for pair ['3', '0']")
print(f"{'='*80}")

tab_x = part.tabs['3']
tab_z = part.tabs['0']
segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
segment_part = Part(sequence=['3', '0'], tabs=segment_tabs)
segments_3_0 = create_segments(segment_part, segment_cfg, filter_cfg)

print(f"Generated {len(segments_3_0)} segments for pair ['3', '0']")

if len(segments_3_0) > 0:
    print(f"\nPlotting segments together in one window...")
    plot_segments(segments_3_0, title="Segments for Pair ['3', '0']", separate_windows=False)

    # Uncomment to plot each segment in separate window:
    # plot_segments(segments_3_0, title="Segments for Pair ['3', '0']", separate_windows=True)

# Example 2: Plot segments for pair with multiple segments
print(f"\n{'='*80}")
print(f"EXAMPLE 2: Visualize segments for pair ['0', '1']")
print(f"{'='*80}")

tab_x = part.tabs['0']
tab_z = part.tabs['1']
segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
segment_part = Part(sequence=['0', '1'], tabs=segment_tabs)
segments_0_1 = create_segments(segment_part, segment_cfg, filter_cfg)

print(f"Generated {len(segments_0_1)} segments for pair ['0', '1']")

if len(segments_0_1) > 0:
    print(f"\nPlotting segments with edge highlighting...")
    plot_segments_with_edge_colors(segments_0_1, title="Segments for Pair ['0', '1'] - Edge Usage")

# Example 3: Plot all pairs in sequence
print(f"\n{'='*80}")
print(f"EXAMPLE 3: Visualize segments for ALL pairs in sequence")
print(f"{'='*80}")

print(f"\nNote: This will open {len(sequence)} plot windows (one per pair)")
print(f"Press Enter to continue or Ctrl+C to skip...")
try:
    input()
    plot_segments_for_sequence(part, sequence, segment_cfg, filter_cfg, max_per_pair=3)
except KeyboardInterrupt:
    print(f"\nSkipped")

print(f"\n{'='*80}")
print(f"VISUALIZATION COMPLETE")
print(f"{'='*80}")

print(f"""
Available plotting functions:

1. plot_segments(segments, title, separate_windows, show_labels)
   - Plot list of segments together or in separate windows
   - Good for comparing different segment options

2. plot_segment_pair(segment, pair_ids, title)
   - Plot a single segment with connection arrow
   - Good for detailed inspection of one segment

3. plot_segments_for_sequence(part, sequence, segment_cfg, filter_cfg, max_per_pair)
   - Generate and plot segments for each pair in a sequence
   - Good for full pipeline visualization

4. plot_segments_with_edge_colors(segments, title)
   - Plot segments with edge highlighting to show which edges are used
   - Good for debugging edge conflicts

Usage example:
    from src.hgen_sm.plotting.plot_segments import plot_segments
    plot_segments(my_segments, title="My Segments", separate_windows=False)
""")

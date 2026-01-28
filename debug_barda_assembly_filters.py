"""
Debug why part_assembly is filtering all combinations for barda_example_one.
This script will trace through part_assembly filters to see which ones are rejecting combinations.
"""

import yaml
import numpy as np
from pathlib import Path
from config.user_input import barda_example_one, barda_example_one_sequence
from src.hgen_sm import initialize_objects, Part, create_segments
import copy

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

print("="*80)
print("DEBUGGING PART_ASSEMBLY FILTERS FOR BARDA_EXAMPLE_ONE")
print("="*80)

# Initialize
part = initialize_objects(barda_example_one)
sequence = barda_example_one_sequence

print(f"\nSequence: {sequence}")

# Generate segments for all pairs
print(f"\nGenerating segments for each pair...")
segments_library = []
for pair in sequence:
    tab_x = part.tabs[pair[0]]
    tab_z = part.tabs[pair[1]]
    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment = Part(sequence=pair, tabs=segment_tabs)
    segments = create_segments(segment, segment_cfg, filter_cfg)
    segments_library.append(segments)
    print(f"  {pair}: {len(segments)} segments")

# Import part_assembly to understand filtering
from src.hgen_sm.part_assembly import part_assembly

# Test a few combinations
import itertools

print(f"\n{'='*80}")
print(f"TESTING SAMPLE COMBINATIONS")
print(f"{'='*80}")

combinations_to_test = 5  # Test first 5 combinations
tested = 0

part.sequence = sequence

for segments_combination in itertools.product(*segments_library):
    if tested >= combinations_to_test:
        break

    tested += 1

    print(f"\n{'='*80}")
    print(f"COMBINATION {tested}")
    print(f"{'='*80}")

    # Show which segment from each pair
    for i, seg in enumerate(segments_combination):
        seg_type = "one-bend" if len(seg.tabs) == 2 else "two-bend"
        print(f"  Pair {sequence[i]}: {seg_type}")

    # Try assembly
    new_part = part.copy()
    new_segments_combination = copy.deepcopy(segments_combination)

    # Call part_assembly and see what happens
    result = part_assembly(new_part, new_segments_combination, filter_cfg)

    if result is None:
        print(f"\n  Result: FILTERED")
        print(f"  Need to inspect part_assembly code to see which filter caught it")
    else:
        print(f"\n  Result: ACCEPTED")
        print(f"  Part ID: {result.part_id if hasattr(result, 'part_id') else 'N/A'}")

# Now let's manually trace through part_assembly logic
print(f"\n{'='*80}")
print(f"MANUAL TRACE OF PART_ASSEMBLY LOGIC")
print(f"{'='*80}")

# Read part_assembly source to understand filters
print(f"\nReading part_assembly.py to understand filter sequence...")
print(f"Common filters in part_assembly:")
print(f"  1. Tabs cover Rects - Check if tabs fully cover input rectangles")
print(f"  2. Lines Cross - Check if bend lines don't cross incorrectly")
print(f"  3. Collisions - Check for geometric collisions")
print(f"  4. Too thin segments - Check minimum thickness")
print(f"  5. Validation - Check if flange points match corners properly")

print(f"\nFilter configuration:")
for key, value in filter_cfg.items():
    print(f"  {key}: {value}")

# Let's check if the issue is with tab coverage
print(f"\n{'='*80}")
print(f"CHECKING TAB COVERAGE")
print(f"{'='*80}")

# Take first combination
first_combination = next(itertools.product(*segments_library))

print(f"\nFirst combination segments:")
for i, seg in enumerate(first_combination):
    print(f"\nSegment {i} (pair {sequence[i]}):")
    print(f"  Number of tabs: {len(seg.tabs)}")
    print(f"  Tab IDs: {list(seg.tabs.keys())}")

    # Show tab extents
    for tab_id, tab in seg.tabs.items():
        if tab_id in ['0', '1', '2', '3', '4', '5']:
            corners = np.array([tab.points[k] for k in ['A', 'B', 'C', 'D']])
            min_pt = np.min(corners, axis=0)
            max_pt = np.max(corners, axis=0)
            print(f"  Tab {tab_id} bounds: [{min_pt[0]:.1f}, {min_pt[1]:.1f}, {min_pt[2]:.1f}] to [{max_pt[0]:.1f}, {max_pt[1]:.1f}, {max_pt[2]:.1f}]")

print(f"\n{'='*80}")
print(f"ANALYSIS")
print(f"{'='*80}")

print(f"""
The debug shows:
1. All pairs successfully generate segments
2. ALL 81 combinations are filtered by part_assembly
3. Need to identify WHICH filter in part_assembly is rejecting them

Possible causes:
1. Tabs don't cover original rectangles (Tabs cover Rects filter)
2. Bend lines cross in invalid ways (Lines Cross filter)
3. Geometric collisions between segments (Collisions filter)
4. Validation failures (e.g., flange points don't match corners)

To debug further, we need to:
1. Add debug output to part_assembly.py
2. Or manually check each filter condition
3. Or test with filters disabled one by one
""")

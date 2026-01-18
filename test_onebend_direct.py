"""
Direct test of one_bend function with input B geometry
"""
import yaml
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import RECTANGLE_INPUTS
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part, initialize_objects
from src.hgen_sm.create_segments.bend_strategies import one_bend

filter_cfg = cfg.get('filter')

# Initialize
part = initialize_objects(RECTANGLE_INPUTS)

# Get tabs 0 and 1
tab_0 = part.tabs['0']
tab_1 = part.tabs['1']

print("Tab 0 corners:")
for c in ['A', 'B', 'C', 'D']:
    if c in tab_0.rectangle.points:
        print(f"  {c}: {tab_0.rectangle.points[c]}")

print("\nTab 1 corners:")
for c in ['A', 'B', 'C', 'D']:
    if c in tab_1.rectangle.points:
        print(f"  {c}: {tab_1.rectangle.points[c]}")

# Create segment
segment_tabs = {'tab_x': tab_0, 'tab_z': tab_1}
segment = Part(sequence=['0', '1'], tabs=segment_tabs)

# Call one_bend
segments = one_bend(segment, filter_cfg)

if segments:
    print(f"\nGenerated {len(segments)} one-bend segment(s)\n")

    for idx, seg in enumerate(segments[:3]):  # First 3
        print(f"{'='*70}")
        print(f"SEGMENT {idx + 1}")
        print(f"{'='*70}\n")

        for tab_id in ['tab_x', 'tab_z']:
            if tab_id in seg.tabs:
                tab = seg.tabs[tab_id]
                print(f"{tab_id} (original: {tab.tab_id}):")
                perimeter = list(tab.points.keys())
                print(f"  Perimeter: {perimeter}")

                # Show BP/FP points with coordinates
                bp_fp_points = {k: v for k, v in tab.points.items() if k.startswith(('BP', 'FP'))}
                if bp_fp_points:
                    for k, v in bp_fp_points.items():
                        print(f"    {k}: {v}")
                print()
else:
    print("\nNo one-bend segments generated!")

"""
Debug script for full pipeline including plotting.
"""
import numpy as np
import sys
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.hgen_sm.data import Part
from src.hgen_sm.initialization import initialize_objects
from src.hgen_sm.determine_sequences import determine_sequences

# Load config
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)


def debug_pipeline():
    print("="*60)
    print("DEBUG: Full Pipeline")
    print("="*60)

    # Test input
    rectangle_inputs = [
        {
            'pointA': [0, 0, 0],
            'pointB': [100, 0, 0],
            'pointC': [100, 50, 0],
            'mounts': [
                [20, 25, 0],
                [80, 25, 0]
            ]
        },
        {
            'pointA': [0, 0, 60],
            'pointB': [100, 0, 60],
            'pointC': [100, 50, 60],
            'mounts': [
                [50, 25, 60]
            ]
        }
    ]

    # Step 1: Initialize
    print("\n--- Step 1: Initialize Objects ---")
    part = initialize_objects(rectangle_inputs)
    print(f"Part ID (before): {id(part)}")
    print(f"Tabs before: {list(part.tabs.keys())}")

    # Step 2: Determine sequences (this calls separate_surfaces internally)
    print("\n--- Step 2: Determine Sequences ---")
    sequences = determine_sequences(part, cfg)

    print(f"\nPart ID (after): {id(part)}")
    print(f"Tabs after separation: {list(part.tabs.keys())}")
    print(f"Sequences: {sequences}")

    # Print detailed tab info
    print("\n--- Tab Details After Separation ---")
    for tab_id, tab in part.tabs.items():
        print(f"\nTab '{tab_id}':")
        print(f"  tab_id attribute: {tab.tab_id}")
        print(f"  original_id: {tab.original_id}")
        print(f"  mounts: {len(tab.mounts)}")
        print(f"  rectangle: {tab.rectangle}")
        if tab.rectangle:
            print(f"  rectangle.points A: {tab.rectangle.points['A'].tolist()}")
            print(f"  rectangle.points B: {tab.rectangle.points['B'].tolist()}")
            print(f"  rectangle.points C: {tab.rectangle.points['C'].tolist()}")
            print(f"  rectangle.points D: {tab.rectangle.points['D'].tolist()}")
        print(f"  tab.points A: {tab.points['A'].tolist()}")
        print(f"  tab.points B: {tab.points['B'].tolist()}")
        print(f"  tab.points C: {tab.points['C'].tolist()}")
        print(f"  tab.points D: {tab.points['D'].tolist()}")

    # Verify sequences reference valid tabs
    print("\n--- Verify Sequences ---")
    for seq_idx, sequence in enumerate(sequences):
        print(f"\nSequence {seq_idx}:")
        for pair in sequence:
            tab_x_id, tab_z_id = pair
            print(f"  Pair: [{tab_x_id}, {tab_z_id}]")

            if tab_x_id not in part.tabs:
                print(f"    ERROR: tab_x_id '{tab_x_id}' not in part.tabs!")
            else:
                print(f"    tab_x exists: {part.tabs[tab_x_id]}")

            if tab_z_id not in part.tabs:
                print(f"    ERROR: tab_z_id '{tab_z_id}' not in part.tabs!")
            else:
                print(f"    tab_z exists: {part.tabs[tab_z_id]}")

    # Test copy
    print("\n--- Test Part.copy() ---")
    part_copy = part.copy()
    print(f"Original part tabs: {list(part.tabs.keys())}")
    print(f"Copied part tabs: {list(part_copy.tabs.keys())}")

    # Verify geometry is preserved in copy
    for tab_id in part.tabs.keys():
        orig_tab = part.tabs[tab_id]
        copy_tab = part_copy.tabs[tab_id]

        orig_A = orig_tab.points['A']
        copy_A = copy_tab.points['A']

        if not np.allclose(orig_A, copy_A):
            print(f"  ERROR: Tab {tab_id} point A differs after copy!")
            print(f"    Original: {orig_A.tolist()}")
            print(f"    Copy: {copy_A.tolist()}")
        else:
            print(f"  Tab {tab_id}: geometry preserved in copy")

    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)


if __name__ == "__main__":
    debug_pipeline()

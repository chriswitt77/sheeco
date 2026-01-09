"""
Debug script to test surface separation and plotting.
"""
import numpy as np
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.hgen_sm.data import Rectangle, Tab, Mount, Part
from src.hgen_sm.initialization import initialize_objects
from src.hgen_sm.determine_sequences.surface_separation import separate_surfaces

def main():
    print("="*60)
    print("DEBUG: Surface Separation Test")
    print("="*60)

    # Test input with 2 mounts on first rectangle
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

    print(f"Tabs after init: {list(part.tabs.keys())}")
    for tab_id, tab in part.tabs.items():
        print(f"  Tab {tab_id}: {len(tab.mounts)} mounts")
        print(f"    A: {tab.points['A'].tolist()}")
        print(f"    B: {tab.points['B'].tolist()}")
        print(f"    C: {tab.points['C'].tolist()}")
        print(f"    D: {tab.points['D'].tolist()}")

    # Step 2: Separate
    print("\n--- Step 2: Separate Surfaces ---")
    cfg = {
        'surface_separation': {
            'auto_split': True,
            'min_screws_for_split': 2,
            'screws_per_surface': 1,
            'split_along': 'auto'
        }
    }

    part = separate_surfaces(part, cfg, verbose=True)

    print(f"\nTabs after separation: {list(part.tabs.keys())}")
    for tab_id, tab in part.tabs.items():
        print(f"\n  Tab {tab_id}:")
        print(f"    original_id: {tab.original_id}")
        print(f"    mounts: {len(tab.mounts)}")
        print(f"    A: {tab.points['A'].tolist()}")
        print(f"    B: {tab.points['B'].tolist()}")
        print(f"    C: {tab.points['C'].tolist()}")
        print(f"    D: {tab.points['D'].tolist()}")

        # Verify rectangle geometry
        A = tab.points['A']
        B = tab.points['B']
        C = tab.points['C']
        D = tab.points['D']

        AB = B - A
        BC = C - B
        CD = D - C
        DA = A - D

        print(f"    |AB| = {np.linalg.norm(AB):.2f}")
        print(f"    |BC| = {np.linalg.norm(BC):.2f}")
        print(f"    AB·BC = {np.dot(AB, BC):.6f} (should be ~0)")

        # Check D = C - AB
        D_expected = C - AB
        D_error = np.linalg.norm(D - D_expected)
        print(f"    D error = {D_error:.6f} (should be ~0)")

        if D_error > 1e-6:
            print(f"    WARNING: D does not match expected value!")
            print(f"    D (actual): {D.tolist()}")
            print(f"    D (expected): {D_expected.tolist()}")

    # Check total coverage
    print("\n--- Coverage Check ---")
    # Sum of all rectangle areas should be approximately original area minus gaps

    original_area = 100 * 50  # First rectangle original area
    total_split_area = 0

    split_tab_ids = [tid for tid in part.tabs.keys() if tid.startswith('0_')]
    for tab_id in split_tab_ids:
        tab = part.tabs[tab_id]
        AB = tab.points['B'] - tab.points['A']
        BC = tab.points['C'] - tab.points['B']
        area = np.linalg.norm(AB) * np.linalg.norm(BC)
        total_split_area += area
        print(f"Tab {tab_id}: area = {area:.2f}")

    print(f"\nOriginal area: {original_area}")
    print(f"Total split area: {total_split_area:.2f}")
    print(f"Gap area: {original_area - total_split_area:.2f}")

    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()

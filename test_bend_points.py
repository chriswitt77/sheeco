import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import barda_example_one

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import initialize_objects

part = initialize_objects(barda_example_one)

print("Tab corners and their coordinates:")
for tab_id, tab in part.tabs.items():
    print(f"\nTab {tab_id}:")
    for corner in ['A', 'B', 'C', 'D']:
        if corner in tab.points:
            coord = tab.points[corner]
            print(f"  {corner}: {coord}")

print("\n\nChecking tab 0:")
tab_0 = part.tabs['0']
print(f"Corner A: {tab_0.points['A']}")
print(f"Corner B: {tab_0.points['B']}")
print(f"Corner C: {tab_0.points['C']}")
print(f"Corner D: {tab_0.points['D']}")

print("\n\nChecking tab 3:")
tab_3 = part.tabs['3']
print(f"Corner A: {tab_3.points['A']}")
print(f"Corner B: {tab_3.points['B']}")
print(f"Corner C: {tab_3.points['C']}")
print(f"Corner D: {tab_3.points['D']}")

print("\n\nProblem: BP0_03L at [0, -10, 55]")
print("This point is at y=-10, but tab 0 corners are at y=0 to y=50")
print("The bend point extends BEYOND the tab boundary (below the bottom edge)")
print("This is likely a flange that extends past the original rectangle edge")

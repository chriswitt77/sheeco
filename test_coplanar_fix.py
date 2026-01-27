"""
Test script to verify coplanar tab extrusion fix.
Uses the zylinderhalter example provided by the user.
"""

import json
from src.hgen_sm.export.part_export import export_to_onshape
from src.hgen_sm.data import Part, Tab
import numpy as np

# Create the example part data from user's JSON
part_data = {
    "timestamp": "260126_0956",
    "part_id": 2,
    "tabs": {
        "0": {
            "points": {
                "A": [40.0, 0.0, 0.0],
                "BP0_02L": [40.0, -10.0, 0.0],
                "BP0_02R": [0.0, -10.0, 0.0],
                "B": [0.0, 0.0, 0.0],
                "C": [0.0, 30.0, 0.0],
                "BP0_01L": [0.0, 40.0, 0.0],
                "BP0_01R": [40.0, 40.0, 0.0],
                "D": [40.0, 30.0, 0.0]
            },
            "mounts": [{
                "u": 20.0, "v": 10.0, "size": 5.0, "type": "Hole",
                "global_coords": [20.0, 10.0, 0.0]
            }]
        },
        "1": {
            "points": {
                "A": [40.0, 90.0, 0.0],
                "BP1_01R": [40.0, 80.0, 0.0],
                "BP1_01L": [0.0, 80.0, 0.0],
                "B": [0.0, 90.0, 0.0],
                "C": [0.0, 120.0, 0.0],
                "D": [40.0, 120.0, 0.0]
            },
            "mounts": [{
                "u": 20.0, "v": 20.0, "size": 5.0, "type": "Hole",
                "global_coords": [20.0, 110.0, 0.0]
            }]
        },
        "2": {
            "points": {
                "A": [40.0, 40.0, 30.0],
                "BP2_02R": [40.0, 30.0, 30.0],
                "BP2_02L": [0.0, 30.0, 30.0],
                "B": [0.0, 40.0, 30.0],
                "C": [0.0, 80.0, 30.0],
                "D": [40.0, 80.0, 30.0]
            },
            "mounts": [
                {"u": 10.0, "v": 10.0, "size": 5.0, "type": "Hole", "global_coords": [10.0, 50.0, 30.0]},
                {"u": 30.0, "v": 10.0, "size": 5.0, "type": "Hole", "global_coords": [30.0, 50.0, 30.0]},
                {"u": 10.0, "v": 30.0, "size": 5.0, "type": "Hole", "global_coords": [10.0, 70.0, 30.0]},
                {"u": 30.0, "v": 30.0, "size": 5.0, "type": "Hole", "global_coords": [30.0, 70.0, 30.0]}
            ]
        },
        "01": {
            "points": {
                "A": [0.0, 40.0, 0.0],
                "B": [40.0, 40.0, 0.0],
                "C": [40.0, 80.0, 0.0],
                "D": [0.0, 80.0, 0.0]
            }
        },
        "02": {
            "points": {
                "FP02_0L": [40.0, -2.0, 6.0],
                "BP02_0L": [40.0, -10.0, 0.0],
                "BP02_0R": [0.0, -10.0, 0.0],
                "FP02_0R": [0.0, -2.0, 6.0],
                "FP02_2L": [0.0, 22.0, 24.0],
                "BP02_2L": [0.0, 30.0, 30.0],
                "BP02_2R": [40.0, 30.0, 30.0],
                "FP02_2R": [40.0, 22.0, 24.0]
            }
        }
    }
}

# Convert to Part object (simplified - just need tabs with points)
from src.hgen_sm.data.mount import Mount

tabs = {}
for tab_id, tab_data in part_data["tabs"].items():
    # Convert points to numpy arrays
    points = {k: np.array(v) for k, v in tab_data["points"].items()}

    # Create mounts if present
    mounts = []
    if "mounts" in tab_data:
        for mount_data in tab_data["mounts"]:
            mount = Mount(
                tab_id=tab_id,
                u=mount_data["u"],
                v=mount_data["v"],
                size=mount_data["size"]
            )
            mount.type = mount_data["type"]
            if "global_coords" in mount_data:
                mount.global_coords = np.array(mount_data["global_coords"])
            mounts.append(mount)

    # Create tab
    tab = Tab(tab_id=tab_id, points=points, mounts=mounts if mounts else None)
    tabs[tab_id] = tab

# Create part
part = Part(tabs=tabs)
part.part_id = part_data["part_id"]

# Export to FeatureScript
print("Exporting part with coplanar fix...")
output_file = export_to_onshape(part, output_dir="exports_test_coplanar")
print(f"\nExported to: {output_file}")

# Read the generated FeatureScript and check the extrusion directions
print("\n" + "="*80)
print("VERIFICATION: Checking extrusion directions...")
print("="*80)

with open(output_file, 'r') as f:
    fs_content = f.read()

# Extract extrusion directions for each tab
import re
for tab_id in ["0", "1", "01"]:
    pattern = rf'// --- Tab {tab_id} ---.*?"direction" : vector\(([-\d.]+), ([-\d.]+), ([-\d.]+)\)'
    match = re.search(pattern, fs_content, re.DOTALL)
    if match:
        direction = (match.group(1), match.group(2), match.group(3))
        print(f"Tab {tab_id:3s}: extrude direction = ({direction[0]:5s}, {direction[1]:5s}, {direction[2]:5s})")

print("\n" + "="*80)
print("EXPECTED RESULT:")
print("  Tab 0  and Tab 1  should have the same extrusion direction")
print("  Tab 01 (connecting tab) should now match Tab 0 and Tab 1")
print("  (Previously Tab 01 was extruding in the opposite direction)")
print("="*80)

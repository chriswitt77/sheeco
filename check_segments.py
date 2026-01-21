import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[0]
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import shock_absorber

with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part
from src.hgen_sm import initialize_objects, create_segments

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

part = initialize_objects(shock_absorber)

# Check segments for pair ['1', '0']
tab_1 = part.tabs['1']
tab_0 = part.tabs['0']
segment_tabs = {'tab_x': tab_1, 'tab_z': tab_0}
segment = Part(sequence=['1', '0'], tabs=segment_tabs)

segments = create_segments(segment, segment_cfg, filter_cfg)

print(f"Generated {len(segments)} segments for pair ['1', '0']:")
print()

for i, seg in enumerate(segments):
    print(f"Segment {i+1}:")
    print(f"  Tabs: {list(seg.tabs.keys())}")

    # Check if it's single or double bend based on number of tabs
    if len(seg.tabs) == 2:
        print(f"  Type: SINGLE BEND (no intermediate tab)")
    elif len(seg.tabs) == 3:
        print(f"  Type: DOUBLE BEND (has intermediate tab)")
        # Find the intermediate tab
        for tab_id, tab in seg.tabs.items():
            if tab_id not in ['tab_x', 'tab_z']:
                print(f"  Intermediate tab: {tab_id}")
                # Show bend points to understand position
                bend_points_10 = {k: v for k, v in tab.points.items() if k.startswith('BP10_')}
                if bend_points_10:
                    for bp_name, bp_coord in bend_points_10.items():
                        print(f"    {bp_name}: ({bp_coord[0]:.1f}, {bp_coord[1]:.1f}, {bp_coord[2]:.1f})")
                break

    # Also show bend points from tab_x (source tab)
    tab_x_points = seg.tabs['tab_x'].points
    bend_points = [key for key in tab_x_points.keys() if key.startswith('BP')]
    if bend_points:
        print(f"  Tab_x bend points: {bend_points}")

    print()

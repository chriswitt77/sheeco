"""
Debug script to test edge selection in fallback two_bend approach
"""
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
from config.user_input import RECTANGLE_INPUTS
with CONFIG_FILE.open("r") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

from src.hgen_sm import Part, initialize_objects, determine_sequences, create_segments

segment_cfg = cfg.get('design_exploration')
filter_cfg = cfg.get('filter')

# Initialize part from config
part = initialize_objects(RECTANGLE_INPUTS)

print(f"\n{'='*60}")
print(f"Testing edge selection in two_bend fallback approach")
print(f"Part has {len(part.tabs)} tabs: {list(part.tabs.keys())}")
print(f"{'='*60}\n")

# Get sequences
variants = determine_sequences(part, cfg)

# Process first variant
variant_part, sequences = variants[0]
print(f"Processing variant with {len(variant_part.tabs)} tabs")
print(f"Found {len(sequences)} sequences\n")

# Create segments for first sequence
sequence = sequences[0]
print(f"Sequence: {sequence}\n")

for pair in sequence:
    print(f"\nProcessing pair {pair}:")
    tab_x = variant_part.tabs[pair[0]]
    tab_z = variant_part.tabs[pair[1]]

    print(f"  tab_x ({pair[0]}): {list(tab_x.points.keys())}")
    print(f"  tab_z ({pair[1]}): {list(tab_z.points.keys())}")

    segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
    segment = Part(sequence=pair, tabs=segment_tabs)

    segments = create_segments(segment, segment_cfg, filter_cfg)
    print(f"  -> Generated {len(segments)} segments\n")

"""Test that AB and AC splits are kept separately when actual splitting occurs."""

from src.hgen_sm import initialize_objects, determine_sequences
from src.hgen_sm.determine_sequences.choose_pairs import get_tab_structure_signature
from config.user_input import zylinderhalter, with_mounts
import yaml

# Load config
with open('config/config.yaml', 'r') as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

print("=" * 60)
print("Test 1: with_mounts (No actual split)")
print("=" * 60)
print()

part1 = initialize_objects(with_mounts)
variants1 = determine_sequences(part1, cfg)

print(f"Variants generated: {len(variants1)}")
for i, (variant_part, sequences) in enumerate(variants1):
    sig = get_tab_structure_signature(variant_part)
    print(f"  Variant {i+1}: {sorted(variant_part.tabs.keys())} -> signature: {sig}")
print()

if len(variants1) == 1:
    print("[OK] Only 1 variant (duplicates eliminated)")
else:
    print(f"[ERROR] Expected 1 variant, got {len(variants1)}")
print()

print("=" * 60)
print("Test 2: zylinderhalter (Actual splits occur)")
print("=" * 60)
print()

part2 = initialize_objects(zylinderhalter)
variants2 = determine_sequences(part2, cfg)

print(f"Variants generated: {len(variants2)}")
for i, (variant_part, sequences) in enumerate(variants2):
    tab_ids = sorted(variant_part.tabs.keys())
    # Don't pass split_direction to see base signature
    base_sig = get_tab_structure_signature(variant_part)
    print(f"  Variant {i+1}: {tab_ids}")
    print(f"    Base signature: {base_sig}")
    print(f"    Sequences: {len(sequences)}")

    # Check if this is a split variant
    split_tabs = [tid for tid in tab_ids if '_' in tid]
    if split_tabs:
        print(f"    Split tabs: {split_tabs}")
print()

# Count how many have actual splits (underscore in tab IDs)
split_variants = sum(1 for v, _ in variants2 if any('_' in tid for tid in v.tabs.keys()))

if len(variants2) >= 2:
    print(f"[OK] Multiple variants kept ({len(variants2)} total, {split_variants} with splits)")
    if split_variants >= 2:
        print("[OK] Both AB and AC split variants preserved")
else:
    print(f"[ERROR] Expected at least 2 variants, got {len(variants2)}")

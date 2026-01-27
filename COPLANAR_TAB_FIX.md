# Coplanar Tab Extrusion Fix

## Problem

When exporting sheet metal parts to Onshape FeatureScript, connecting tabs between coplanar surfaces were extruding in the opposite direction compared to the surfaces they connect.

### Example
In the zylinderhalter configuration:
- **Tab 0**: Extrudes in direction `(0, 0, -1)` ✓
- **Tab 1**: Extrudes in direction `(0, 0, -1)` ✓
- **Tab 01** (connecting tab): Was extruding in direction `(0, 0, 1)` ❌

This caused the connecting tab to go the wrong way, preventing proper union in Onshape.

## Root Cause

The `export_to_onshape()` function in `part_export.py` calculated each tab's plane normal independently using cross products of edge vectors. For connecting tabs between coplanar surfaces, this calculation didn't ensure the connecting tab's normal matched the normals of the tabs it connects.

## Solution

Added logic to detect connecting tabs between coplanar surfaces and align their normals:

### Implementation

1. **Helper Functions** (added to `part_export.py`):
   - `parse_connecting_tab_id(tab_id)` - Identifies connecting tabs (e.g., "01", "12") and extracts source/target IDs
   - `calculate_tab_normal(tab_points)` - Calculates plane normal for any tab
   - `are_normals_coplanar(normal1, normal2)` - Checks if two normals are parallel/anti-parallel

2. **Modified Normal Calculation**:
   After computing a tab's normal, check if it's a connecting tab:
   - Parse the tab ID to extract source and target tab IDs
   - Calculate normals for source and target tabs
   - If they're coplanar, flip the connecting tab's normal if needed to match the source tab

### Code Location
`src/hgen_sm/export/part_export.py` lines 234-257

## Verification

Test with zylinderhalter example:
```
Tab 0  : extrude direction = (0.0, 0.0, -1.0)
Tab 1  : extrude direction = (0.0, 0.0, -1.0)
Tab 01 : extrude direction = (0.0, 0.0, -1.0) ✓ FIXED
```

All three tabs now extrude in the same direction.

## Testing

Run test script:
```bash
python test_coplanar_fix.py
```

This verifies that:
- Connecting tabs between coplanar surfaces have matching extrusion directions
- Non-coplanar connections remain unaffected
- The fix works with the zylinderhalter example configuration

## Notes

- The fix only applies to connecting tabs (with numeric IDs like "01", "12")
- Original tabs with A,B,C,D corners are unaffected
- Non-coplanar connecting tabs (from two_bends) continue to work normally
- The tolerance for coplanarity detection is 0.01 (configurable in `are_normals_coplanar()`)

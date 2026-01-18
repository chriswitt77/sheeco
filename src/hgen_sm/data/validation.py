"""
Validation functions for verifying data structure integrity in sheet metal parts.

These functions help catch topology and geometry errors early in the pipeline.
"""

import numpy as np
import re
from typing import Dict, List, Tuple, Optional
from .tab import Tab
from .part import Part


def validate_flange_points(tab: Tab, tolerance: float = 1e-6) -> Tuple[bool, List[str]]:
    """
    Verify that Flange Points (FP) in tab correspond to corner coordinates.

    In the correct topology:
    - FP points should be at or very near original corner coordinates
    - BP points are shifted from corners (on the bend line)
    - Connection: Corner → FP (at corner) → BP (shifted)

    Args:
        tab: Tab object to validate
        tolerance: Maximum allowed distance for FP to match corner coordinate

    Returns:
        (is_valid, error_messages): Tuple of validation result and list of errors
    """
    errors = []

    # Get original corner coordinates if available
    if not hasattr(tab, 'rectangle') or tab.rectangle is None:
        # Intermediate tabs (from two-bend) don't have rectangles, skip validation
        return True, []

    corner_coords = {
        'A': tab.rectangle.points['A'],
        'B': tab.rectangle.points['B'],
        'C': tab.rectangle.points['C'],
        'D': tab.rectangle.points['D']
    }

    # Check all FP points in the tab
    for point_id, coords in tab.points.items():
        if point_id.startswith('FP'):
            # Extract which corner this FP should correspond to
            # FP format: "FP<tabID><L|R>" or "FP<tabID1>_<tabID2><L|R>"
            # The last character is L or R, which indicates left or right corner

            # Find if this FP matches any corner coordinate
            matches_corner = False
            matching_corner = None

            for corner_id, corner_coord in corner_coords.items():
                distance = np.linalg.norm(coords - corner_coord)
                if distance < tolerance:
                    matches_corner = True
                    matching_corner = corner_id
                    break

            if not matches_corner:
                # Find nearest corner for error message
                nearest_corner = min(
                    corner_coords.items(),
                    key=lambda item: np.linalg.norm(coords - item[1])
                )
                nearest_dist = np.linalg.norm(coords - nearest_corner[1])

                errors.append(
                    f"Tab {tab.tab_id}: FP '{point_id}' at {coords} does not match "
                    f"any corner coordinate (nearest: {nearest_corner[0]} at distance {nearest_dist:.6f})"
                )

    return len(errors) == 0, errors


def validate_perimeter_ordering(tab: Tab) -> Tuple[bool, List[str]]:
    """
    Check that tab points form a valid perimeter without self-intersections.

    This is a basic check that:
    1. Points form a closed loop
    2. No edges cross each other in 2D projections

    Args:
        tab: Tab object to validate

    Returns:
        (is_valid, error_messages): Tuple of validation result and list of errors
    """
    errors = []

    if not hasattr(tab, 'points') or not tab.points:
        errors.append(f"Tab {tab.tab_id}: No points defined")
        return False, errors

    points_list = list(tab.points.values())
    num_points = len(points_list)

    if num_points < 3:
        errors.append(f"Tab {tab.tab_id}: Too few points ({num_points}) to form a perimeter")
        return False, errors

    # Check for duplicate points (tolerance-based)
    # NOTE: FP (Flange Points) are EXPECTED to be at corner coordinates
    # This is correct topology: Corner → FP (at corner) → BP (shifted)
    # So we skip duplicate detection for FP-corner pairs
    tolerance = 1e-6
    point_ids = list(tab.points.keys())

    def is_expected_duplicate(id1, id2):
        """Check if two point IDs are expected to be at same location."""
        # FP and corner point (A, B, C, D) can be at same location
        corners = {'A', 'B', 'C', 'D'}
        is_fp_corner_pair = (
            (id1.startswith('FP') and id2 in corners) or
            (id2.startswith('FP') and id1 in corners)
        )
        return is_fp_corner_pair

    for i in range(num_points):
        for j in range(i + 1, num_points):
            dist = np.linalg.norm(points_list[i] - points_list[j])
            if dist < tolerance:
                # Skip if this is an expected FP-corner duplicate
                if not is_expected_duplicate(point_ids[i], point_ids[j]):
                    errors.append(
                        f"Tab {tab.tab_id}: Duplicate points at indices {i} ({point_ids[i]}) "
                        f"and {j} ({point_ids[j]}), distance={dist:.10f}"
                    )

    # Check for edge crossings in 2D projections (XY, XZ, YZ)
    # This catches most self-intersecting polygons
    def segments_intersect_2d(p1, p2, p3, p4, dims):
        """Check if line segments p1-p2 and p3-p4 intersect in 2D projection."""
        # Extract 2D coordinates based on projection dimensions
        a1 = np.array([p1[dims[0]], p1[dims[1]]], dtype=float)
        a2 = np.array([p2[dims[0]], p2[dims[1]]], dtype=float)
        b1 = np.array([p3[dims[0]], p3[dims[1]]], dtype=float)
        b2 = np.array([p4[dims[0]], p4[dims[1]]], dtype=float)

        d1 = a2 - a1
        d2 = b2 - b1

        cross = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(cross) < 1e-10:
            return False  # Parallel or collinear

        diff = b1 - a1
        t = (diff[0] * d2[1] - diff[1] * d2[0]) / cross
        s = (diff[0] * d1[1] - diff[1] * d1[0]) / cross

        # Check if intersection is within both segments (excluding endpoints)
        return 0.01 < t < 0.99 and 0.01 < s < 0.99

    # Check all pairs of non-adjacent edges
    point_ids = list(tab.points.keys())
    for i in range(num_points):
        for j in range(i + 2, num_points):
            # Skip adjacent edges and last-to-first edge
            if j == num_points - 1 and i == 0:
                continue

            p1, p2 = points_list[i], points_list[(i + 1) % num_points]
            p3, p4 = points_list[j], points_list[(j + 1) % num_points]

            # Check all three 2D projections
            for projection, dims in [('XY', (0, 1)), ('XZ', (0, 2)), ('YZ', (1, 2))]:
                if segments_intersect_2d(p1, p2, p3, p4, dims):
                    errors.append(
                        f"Tab {tab.tab_id}: Edge {point_ids[i]}-{point_ids[(i+1)%num_points]} "
                        f"crosses edge {point_ids[j]}-{point_ids[(j+1)%num_points]} "
                        f"in {projection} projection (self-intersecting polygon)"
                    )

    return len(errors) == 0, errors


def validate_naming_convention(tab: Tab) -> Tuple[bool, List[str]]:
    """
    Verify that all point names follow the correct naming convention.

    Correct format: (FP|BP){tab_id}_{tab_id}(L|R)
    Examples: "FP0_1L", "BP01_02R", "FP0_01_02L"

    Args:
        tab: Tab object to validate

    Returns:
        (is_valid, error_messages): Tuple of validation result and list of errors
    """
    errors = []

    if not hasattr(tab, 'points') or not tab.points:
        return True, []  # No points to validate

    # Pattern for bend/flange points: (FP|BP) + tab_ids + (L|R)
    # Tab IDs can be: single digit (0), multi-digit (01), or composite (0_1, 01_02)
    # Must have underscore separator between tab IDs
    pattern = re.compile(r'^(FP|BP)(\d+(?:_\d+)+)(L|R)$')

    for point_id in tab.points.keys():
        # Skip corner points (A, B, C, D)
        if point_id in {'A', 'B', 'C', 'D'}:
            continue

        # Check if it's a bend/flange point
        if point_id.startswith('FP') or point_id.startswith('BP'):
            match = pattern.match(point_id)
            if not match:
                errors.append(
                    f"Tab {tab.tab_id}: Point '{point_id}' does not follow naming convention. "
                    f"Expected format: (FP|BP){{tab_id}}_{{tab_id}}(L|R) with underscore separator"
                )
            else:
                # Verify that underscores are present (not missing)
                tab_ids = match.group(2)
                if '_' not in tab_ids:
                    errors.append(
                        f"Tab {tab.tab_id}: Point '{point_id}' missing underscore separator. "
                        f"Should be like 'FP0_1L' not 'FP01L'"
                    )

    return len(errors) == 0, errors


def validate_part(part: Part, verbose: bool = False) -> Tuple[bool, List[str]]:
    """
    Validate an entire part's data structure.

    Args:
        part: Part object to validate
        verbose: If True, print validation results for each tab

    Returns:
        (is_valid, all_errors): Tuple of validation result and list of all errors
    """
    all_errors = []

    if not hasattr(part, 'tabs') or not part.tabs:
        all_errors.append(f"Part {part.part_id}: No tabs defined")
        return False, all_errors

    for tab_id, tab in part.tabs.items():
        # Validate naming convention
        naming_valid, naming_errors = validate_naming_convention(tab)
        if not naming_valid:
            all_errors.extend(naming_errors)
        elif verbose:
            print(f"✓ Tab {tab_id}: Naming convention valid")

        # Validate FP points
        fp_valid, fp_errors = validate_flange_points(tab)
        if not fp_valid:
            all_errors.extend(fp_errors)
        elif verbose:
            print(f"✓ Tab {tab_id}: FP points valid")

        # Validate perimeter ordering
        perimeter_valid, perimeter_errors = validate_perimeter_ordering(tab)
        if not perimeter_valid:
            all_errors.extend(perimeter_errors)
        elif verbose:
            print(f"✓ Tab {tab_id}: Perimeter ordering valid")

    return len(all_errors) == 0, all_errors


def print_validation_report(part: Part):
    """
    Print a detailed validation report for a part.

    Args:
        part: Part object to validate
    """
    print(f"\n{'='*60}")
    print(f"VALIDATION REPORT: Part {part.part_id}")
    print(f"{'='*60}")

    is_valid, errors = validate_part(part, verbose=True)

    if is_valid:
        print(f"\n✓ All validation checks passed!")
    else:
        print(f"\n✗ Validation failed with {len(errors)} error(s):")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")

    print(f"{'='*60}\n")

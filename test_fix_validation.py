"""
Quick validation test for the point ordering fix.
"""
import sys
sys.path.insert(0, 'src')

from hgen_sm.create_segments.bend_strategies import should_swap_z_side_ordering

# Test cases from the problem
test_cases = [
    {
        "name": "Problem case (part_id 4, x=10) - PREVIOUSLY FAILED",
        "FPyxL": [60.0, 90.0, 10.0],
        "FPyxR": [10.0, 90.0, 10.0],
        "FPyzR": [10.0, 90.0, 80.0],
        "FPyzL": [10.0, 90.0, 40.0],
        "expected_swap": True
    },
    {
        "name": "Working case (part_id 4, x=20)",
        "FPyxL": [60.0, 90.0, 10.0],
        "FPyxR": [20.0, 90.0, 10.0],
        "FPyzR": [10.0, 90.0, 80.0],
        "FPyzL": [10.0, 90.0, 40.0],
        "expected_swap": True
    },
    {
        "name": "Problem case (part_id 6, x=10) - PREVIOUSLY FAILED",
        "FPyxL": [60.0, 37.5, 9.682458365518542],
        "FPyxR": [10.0, 37.5, 9.682458365518542],
        "FPyzR": [10.0, 20.635083268962916, 75.0],
        "FPyzL": [10.0, 32.81754163448146, 27.817541634481458],
        "expected_swap": True
    },
    {
        "name": "Working case (part_id 6, x=20)",
        "FPyxL": [60.0, 37.5, 9.682458365518542],
        "FPyxR": [20.0, 37.5, 9.682458365518542],
        "FPyzR": [10.0, 20.635083268962916, 75.0],
        "FPyzL": [10.0, 32.81754163448146, 27.817541634481458],
        "expected_swap": True
    }
]

print("=" * 100)
print("VALIDATION TEST: Point Ordering Fix")
print("=" * 100)

all_passed = True
for test in test_cases:
    result = should_swap_z_side_ordering(
        test["FPyxL"], test["FPyxR"], test["FPyzR"], test["FPyzL"]
    )
    expected = test["expected_swap"]
    passed = result == expected

    status = "PASS [OK]" if passed else "FAIL [X]"
    if not passed:
        all_passed = False

    print(f"\n{test['name']}")
    print(f"  Expected: {expected}, Got: {result} - {status}")

print("\n" + "=" * 100)
if all_passed:
    print("ALL TESTS PASSED! The fix works correctly.")
else:
    print("SOME TESTS FAILED! Review the implementation.")
print("=" * 100)

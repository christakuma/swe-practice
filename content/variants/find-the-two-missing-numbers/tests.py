"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import tracemalloc
from itertools import combinations

from solution import find_missing


def without(top: int, gone: tuple[int, int]) -> list[int]:
    """0..top with two values removed, in a scrambled but repeatable order."""
    kept = [value for value in range(top + 1) if value not in gone]
    return kept[1::2] + kept[0::2][::-1]


def test_finds_two_missing_values() -> None:
    """Returns both missing values, smaller first."""
    assert find_missing([0, 3]) == (1, 2)
    assert find_missing([4, 1, 2]) == (0, 3)


def test_finds_them_at_the_ends_of_the_range() -> None:
    """Finds missing values at the bottom and the top of the range."""
    assert find_missing([1, 2, 3]) == (0, 4)
    assert find_missing([0, 1, 2]) == (3, 4)
    assert find_missing([2, 3, 4]) == (0, 1)


def test_handles_an_empty_list() -> None:
    """Returns (0, 1) for an empty list, where the range is just 0..1."""
    assert find_missing([]) == (0, 1)


def test_returns_a_tuple_in_ascending_order() -> None:
    """Returns a tuple with the smaller value first."""
    result = find_missing([5, 0, 3, 1])

    assert isinstance(result, tuple)
    assert result == (2, 4)


def test_finds_every_pair_at_every_small_size() -> None:
    """Finds every possible pair of missing values, for every range up to 0..13."""
    for top in range(1, 14):
        for gone in combinations(range(top + 1), 2):
            assert find_missing(without(top, gone)) == gone, (top, gone)


def test_leaves_the_list_alone() -> None:
    """Does not sort or modify the list it was given."""
    numbers = [4, 1, 2]

    find_missing(numbers)

    assert numbers == [4, 1, 2]


def test_uses_constant_extra_space() -> None:
    """Allocates no memory that grows with the list.

    Two hundred thousand values. A set of them, or a sorted copy, is
    megabytes; a handful of running XORs is a handful of integers. The list
    is built before measuring starts.
    """
    top = 200_001
    numbers = without(top, (70_000, 150_001))

    tracemalloc.start()
    found = find_missing(numbers)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert found == (70_000, 150_001)
    assert peak < 64_000, f"allocated {peak} bytes"


def test_scans_a_million_values() -> None:
    """Finds the pair among a million values within the time limit."""
    top = 1_000_001

    assert find_missing(without(top, (3, top))) == (3, top)

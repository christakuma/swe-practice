"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import tracemalloc
from itertools import combinations, combinations_with_replacement

from solution import two_sum


def pairs(numbers: list[int], target: int) -> list[tuple[int, int]]:
    """Every pair of 1-based positions summing to the target, by brute force."""
    return [
        (first + 1, second + 1)
        for first, second in combinations(range(len(numbers)), 2)
        if numbers[first] + numbers[second] == target
    ]


def test_finds_the_pair() -> None:
    """Finds the two positions that add up to the target."""
    assert two_sum([2, 7, 11, 15], 9) == (1, 2)


def test_counts_positions_from_one() -> None:
    """Counts positions from 1, so the last value of four is position 4."""
    assert two_sum([1, 2, 3, 10], 13) == (3, 4)


def test_does_not_use_one_position_twice() -> None:
    """Uses two distinct positions, even when half the target is in the list."""
    assert two_sum([2, 3, 4], 6) == (1, 3)


def test_handles_equal_values() -> None:
    """Pairs two equal values that sit at different positions."""
    assert two_sum([1, 4, 4, 9], 8) == (2, 3)


def test_handles_negatives() -> None:
    """Handles negative values and a negative target."""
    assert two_sum([-5, -1, 0, 3], -6) == (1, 2)
    assert two_sum([-8, -3, 2, 8], 0) == (1, 4)


def test_returns_a_tuple_smaller_position_first() -> None:
    """Returns a tuple with the smaller position first."""
    result = two_sum([1, 3, 5, 7], 12)

    assert isinstance(result, tuple)
    assert result == (3, 4)


def test_agrees_with_brute_force_on_every_small_sorted_list() -> None:
    """Matches an every-pair search for every short sorted list.

    Every ascending list of two to five values drawn from -2..4, repeats
    allowed, against every target that exactly one pair reaches.
    """
    checked = 0
    for size in range(2, 6):
        for chosen in combinations_with_replacement(range(-2, 5), size):
            numbers = list(chosen)
            for target in range(-4, 9):
                found = pairs(numbers, target)
                if len(found) == 1:
                    assert two_sum(numbers, target) == found[0], (numbers, target)
                    checked += 1
    assert checked > 1000


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    numbers = [1, 2, 4, 8]

    two_sum(numbers, 12)

    assert numbers == [1, 2, 4, 8]


def test_uses_constant_extra_space() -> None:
    """Allocates no memory that grows with the list.

    Two hundred thousand consecutive values, and the target is the sum of the
    last two -- the only pair that large. A dict of the values seen so far
    holds every one of them before it finds the pair, which is megabytes; two
    indices are two integers. The list itself is built before measuring starts.
    """
    size = 200_000
    numbers = list(range(size))
    target = (size - 2) + (size - 1)

    tracemalloc.start()
    result = two_sum(numbers, target)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert result == (size - 1, size)
    assert peak < 64_000, f"allocated {peak} bytes"


def test_searches_a_million_values() -> None:
    """Finds the pair in a million values within the time limit."""
    size = 1_000_000
    numbers = list(range(size))

    assert two_sum(numbers, (size - 2) + (size - 1)) == (size - 1, size)
    assert two_sum(numbers, 1) == (1, 2)

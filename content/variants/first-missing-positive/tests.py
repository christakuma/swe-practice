"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import tracemalloc
from itertools import product

from solution import first_missing_positive


def by_counting_up(numbers: list[int]) -> int:
    present = set(numbers)
    candidate = 1
    while candidate in present:
        candidate += 1
    return candidate


def shuffled(size: int) -> list[int]:
    """The values 1..size in an order with no long sorted stretches."""
    stride = 7919
    assert size % stride != 0
    return [(index * stride) % size + 1 for index in range(size)]


def test_finds_a_gap_among_small_values() -> None:
    """Finds the first positive integer that is absent."""
    assert first_missing_positive([3, 4, -1, 1]) == 2
    assert first_missing_positive([1, 2, 4]) == 3


def test_returns_one_when_one_is_absent() -> None:
    """Returns 1 when the list holds no 1, whatever else it holds."""
    assert first_missing_positive([7, 8, 9, 11, 12]) == 1
    assert first_missing_positive([-5, -1, 0]) == 1
    assert first_missing_positive([2]) == 1


def test_returns_one_more_than_the_length_when_nothing_is_missing() -> None:
    """Returns n + 1 when the list is exactly 1..n in some order."""
    assert first_missing_positive([1, 2, 0]) == 3
    assert first_missing_positive([3, 1, 2]) == 4
    assert first_missing_positive([1]) == 2


def test_handles_an_empty_list() -> None:
    """Returns 1 for an empty list."""
    assert first_missing_positive([]) == 1


def test_ignores_zero_and_negatives() -> None:
    """Does not count zero or negative values as present."""
    assert first_missing_positive([0, -1, -2, 1]) == 2
    assert first_missing_positive([0]) == 1


def test_ignores_values_too_large_to_matter() -> None:
    """Is not disturbed by values far larger than the list is long."""
    assert first_missing_positive([10**9, 1, 2]) == 3
    assert first_missing_positive([2, 10**9, 1, -(10**9)]) == 3


def test_handles_repeated_values() -> None:
    """Terminates and answers correctly when values repeat."""
    assert first_missing_positive([1, 1]) == 2
    assert first_missing_positive([1, 1, 2, 2]) == 3
    assert first_missing_positive([2, 2, 2]) == 1
    assert first_missing_positive([3, 3, 1, 1]) == 2


def test_sends_a_swapped_in_value_home_as_well() -> None:
    """Keeps placing values when a swap brings in another one that needs moving.

    In [3, 4, 1, 2] the first position has to be dealt with twice: the 3 goes
    home and a 1 arrives in exchange -- which is at home -- but in [2, 3, 1]
    the 2 goes home and a 3 arrives that is not.
    """
    assert first_missing_positive([2, 3, 1]) == 4
    assert first_missing_positive([4, 1, 2, 3]) == 5
    assert first_missing_positive([2, 3, 4, 1, 9]) == 5


def test_agrees_with_counting_up_on_every_short_list() -> None:
    """Matches a set-based search for every short list.

    Every list of up to five values drawn from -1..4 and 9.
    """
    for size in range(6):
        for chosen in product((-1, 0, 1, 2, 3, 4, 9), repeat=size):
            expected = by_counting_up(list(chosen))
            assert first_missing_positive(list(chosen)) == expected, chosen


def test_uses_constant_extra_space() -> None:
    """Allocates no memory that grows with the list.

    Two hundred thousand values, 1..n thoroughly shuffled, with one of them
    replaced by a negative. A set of the values holds them all, and so does
    the scratch space a sort needs for data in this order. The list is built
    before measuring starts.
    """
    size = 200_000
    numbers = shuffled(size)
    numbers[numbers.index(123_456)] = -7

    tracemalloc.start()
    found = first_missing_positive(numbers)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert found == 123_456
    assert peak < 64_000, f"allocated {peak} bytes"


def test_handles_a_million_values() -> None:
    """Handles a million values within the time limit."""
    size = 1_000_000
    numbers = shuffled(size)

    assert first_missing_positive(numbers) == size + 1

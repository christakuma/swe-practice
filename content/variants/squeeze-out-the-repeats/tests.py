"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import tracemalloc
from itertools import combinations_with_replacement

from solution import remove_duplicates


def squeezed(numbers: list[int]) -> list[int]:
    """Run on a copy and return the front part the count points at."""
    working = list(numbers)
    count = remove_duplicates(working)
    assert isinstance(count, int)
    return working[:count]


def test_removes_a_repeated_value() -> None:
    """Keeps one copy of a value that appears twice."""
    assert squeezed([1, 1, 2]) == [1, 2]
    assert squeezed([1, 2, 2]) == [1, 2]


def test_removes_runs_of_any_length() -> None:
    """Keeps one copy of each value, however many times it repeats."""
    assert squeezed([0, 0, 1, 1, 1, 2, 2, 3, 3, 4]) == [0, 1, 2, 3, 4]
    assert squeezed([5, 5, 5, 5, 5]) == [5]


def test_returns_the_number_of_distinct_values() -> None:
    """Returns how many values are kept, not the position of the last one."""
    assert remove_duplicates([1, 1, 2]) == 2
    assert remove_duplicates([7]) == 1
    assert remove_duplicates([1, 2, 3, 3]) == 3


def test_a_list_with_no_repeats_is_unchanged() -> None:
    """Keeps every value when all of them are distinct."""
    numbers = [1, 2, 3, 4]

    assert remove_duplicates(numbers) == 4
    assert numbers == [1, 2, 3, 4]


def test_an_empty_list_has_no_values() -> None:
    """Returns 0 for an empty list."""
    assert remove_duplicates([]) == 0


def test_handles_negatives_and_zero() -> None:
    """Treats zero as a value like any other."""
    assert squeezed([-3, -3, -1, 0, 0, 0, 2]) == [-3, -1, 0, 2]
    assert squeezed([0, 0]) == [0]


def test_works_in_place() -> None:
    """Writes the result into the list it was given, not into a new one."""
    numbers = [4, 4, 6, 6, 6, 9]

    count = remove_duplicates(numbers)

    assert numbers[:count] == [4, 6, 9]


def test_agrees_with_a_set_on_every_short_sorted_list() -> None:
    """Matches the sorted distinct values for every short sorted list.

    Every ascending list of up to seven values drawn from 0..3.
    """
    for size in range(8):
        for chosen in combinations_with_replacement(range(4), size):
            numbers = list(chosen)
            assert squeezed(numbers) == sorted(set(numbers)), numbers
            assert remove_duplicates(numbers) == len(set(chosen)), chosen


def test_uses_constant_extra_space() -> None:
    """Allocates no memory that grows with the list.

    Two hundred thousand entries holding a hundred thousand distinct values,
    each twice. A set of them, or a new list, holds a hundred thousand
    references. The list is built before measuring starts.
    """
    size = 100_000
    numbers = [value for value in range(size) for _ in range(2)]

    tracemalloc.start()
    count = remove_duplicates(numbers)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert count == size
    assert numbers[:count] == list(range(size))
    assert peak < 64_000, f"allocated {peak} bytes"


def test_handles_long_runs_in_a_long_list() -> None:
    """Handles two hundred thousand entries made of four long runs."""
    numbers = [1] * 50_000 + [2] * 50_000 + [3] * 50_000 + [9] * 50_000

    count = remove_duplicates(numbers)

    assert count == 4
    assert numbers[:4] == [1, 2, 3, 9]

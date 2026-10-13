"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product
from math import prod

from solution import count_slices


def by_every_slice(numbers: list[int], limit: int) -> int:
    return sum(
        prod(numbers[start:end]) < limit
        for start in range(len(numbers))
        for end in range(start + 1, len(numbers) + 1)
    )


def test_counts_the_worked_example() -> None:
    """Counts eight slices under 100 in the worked example."""
    assert count_slices([10, 5, 2, 6], 100) == 8


def test_the_limit_itself_is_too_big() -> None:
    """Does not count a product equal to the limit."""
    assert count_slices([10, 10], 100) == 2
    assert count_slices([5], 5) == 0


def test_nothing_is_below_one() -> None:
    """Returns 0 for a limit of 0 or 1."""
    assert count_slices([1, 2, 3], 0) == 0
    assert count_slices([1, 1, 1], 1) == 0


def test_counts_every_slice_when_none_is_too_big() -> None:
    """Counts every slice when even the whole list is under the limit."""
    assert count_slices([1, 1, 1], 2) == 6
    assert count_slices([], 10) == 0


def test_skips_a_value_that_is_too_big_alone() -> None:
    """Counts nothing through a single value at or over the limit."""
    assert count_slices([2, 50, 3], 10) == 2


def test_agrees_with_multiplying_out_every_slice() -> None:
    """Matches an every-slice check for every short list and many limits."""
    for length in range(7):
        for chosen in product(range(1, 5), repeat=length):
            numbers = list(chosen)
            for limit in (0, 1, 2, 3, 5, 8, 13, 30, 100):
                assert count_slices(numbers, limit) == by_every_slice(numbers, limit), (
                    numbers,
                    limit,
                )


def test_counts_in_a_long_list() -> None:
    """Counts slices in a hundred thousand values within the time limit."""
    size = 100_000

    assert count_slices([2] * size, 1024) == sum(min(end + 1, 9) for end in range(size))
    assert count_slices([1] * size, 2) == size * (size + 1) // 2

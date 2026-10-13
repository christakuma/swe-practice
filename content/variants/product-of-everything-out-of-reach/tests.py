"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product
from math import prod

from solution import product_except_window


def by_definition(numbers: list[int], k: int) -> list[int]:
    return [
        prod(value for other, value in enumerate(numbers) if abs(other - index) > k)
        for index in range(len(numbers))
    ]


def test_skips_the_neighbours_within_reach() -> None:
    """Leaves out each position's neighbours as well as itself."""
    assert product_except_window([1, 2, 3, 4, 5], 1) == [60, 20, 5, 2, 6]


def test_matches_the_standard_problem_at_zero_reach() -> None:
    """Gives the standard answer when the reach is zero."""
    assert product_except_window([1, 2, 3, 4], 0) == [24, 12, 8, 6]


def test_returns_ones_when_nothing_is_out_of_reach() -> None:
    """Returns the empty product when the reach covers the whole list."""
    assert product_except_window([2, 3, 4], 5) == [1, 1, 1]
    assert product_except_window([7], 0) == [1]


def test_handles_zeros_and_negatives() -> None:
    """Handles a zero that is in reach of some positions and not others."""
    assert product_except_window([0, 2, 3, 4], 1) == [12, 4, 0, 0]
    assert product_except_window([-1, 2, -3, 4], 0) == [-24, 12, -8, 6]


def test_returns_an_empty_list_for_no_input() -> None:
    """Returns an empty list for an empty list."""
    assert product_except_window([], 3) == []


def test_agrees_with_the_definition() -> None:
    """Matches a direct product for every short list and every small reach."""
    for length in range(7):
        for chosen in product(range(-2, 3), repeat=length):
            numbers = list(chosen)
            for k in range(4):
                assert product_except_window(numbers, k) == by_definition(numbers, k), (
                    numbers,
                    k,
                )


def test_handles_a_long_list() -> None:
    """Handles twenty thousand values within the time limit."""
    size = 20_000
    numbers = [1] * size
    numbers[10] = 3

    result = product_except_window(numbers, 100)

    assert result[:5] == [1, 1, 1, 1, 1]
    assert result[111] == 3
    assert result[110] == 1

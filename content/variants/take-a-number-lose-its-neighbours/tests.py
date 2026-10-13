"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, pairwise, product

from solution import best_haul


def by_every_choice(numbers: list[int]) -> int:
    """Try every set of distinct values with no two one apart."""
    distinct = sorted(set(numbers))
    best = 0
    for size in range(len(distinct) + 1):
        for chosen in combinations(distinct, size):
            if all(b - a != 1 for a, b in pairwise(chosen)):
                best = max(best, sum(value for value in numbers if value in chosen))
    return best


def test_takes_values_that_are_not_one_apart() -> None:
    """Takes 4 and 2, leaving the 3 between them."""
    assert best_haul([3, 4, 2]) == 6


def test_gains_every_copy_of_a_value() -> None:
    """Counts every copy of a taken value."""
    assert best_haul([2, 2, 3, 3, 3, 4]) == 9
    assert best_haul([5, 5, 5]) == 15


def test_ignores_where_values_sit_in_the_list() -> None:
    """Gives the same answer however the list is ordered."""
    assert best_haul([4, 2, 3]) == best_haul([2, 3, 4]) == 6
    assert best_haul([1, 3, 1, 3]) == 8


def test_takes_both_sides_of_a_gap() -> None:
    """Takes two values that are next in order but not one apart."""
    assert best_haul([1, 3]) == 4
    assert best_haul([1, 2, 4, 5]) == 7


def test_handles_trivial_lists() -> None:
    """Returns 0 for nothing and for zeros."""
    assert best_haul([]) == 0
    assert best_haul([0, 0]) == 0
    assert best_haul([7]) == 7


def test_agrees_with_trying_every_choice() -> None:
    """Matches an every-choice search for every list up to length six."""
    for length in range(7):
        for chosen in product(range(1, 6), repeat=length):
            numbers = list(chosen)
            assert best_haul(numbers) == by_every_choice(numbers), numbers


def test_handles_enormous_values() -> None:
    """Handles values near a billion without a table that large."""
    assert best_haul([1, 1_000_000_000]) == 1_000_000_001
    assert best_haul([999_999_999, 1_000_000_000]) == 1_000_000_000


def test_handles_a_long_list() -> None:
    """Handles a hundred thousand values within the time limit."""
    numbers = [value for value in range(1, 50_001) for _ in range(2)]

    assert best_haul(numbers) == 2 * sum(range(2, 50_001, 2))

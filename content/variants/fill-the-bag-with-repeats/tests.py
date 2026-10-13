"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations

from solution import best_value

POOL = [(1, 1), (2, 3), (3, 4), (3, 5), (4, 5), (5, 9)]


def by_recursion(items: tuple[tuple[int, int], ...], capacity: int) -> int:
    """Take one more of something that fits, or stop."""
    return max(
        (
            value + by_recursion(items, capacity - weight)
            for weight, value in items
            if weight <= capacity
        ),
        default=0,
    )


def test_takes_an_item_more_than_once() -> None:
    """Takes two copies of an item when two fit."""
    assert best_value([(5, 10)], 12) == 20


def test_mixes_repeats_with_other_items() -> None:
    """Combines repeated items with others to fill the bag."""
    assert best_value([(1, 1), (3, 4), (4, 5)], 7) == 9


def test_beats_the_best_single_ratio() -> None:
    """Does not simply repeat the item with the best value per weight."""
    assert best_value([(3, 5), (4, 6)], 8) == 12
    assert best_value([(5, 9), (3, 5)], 6) == 10


def test_returns_zero_when_nothing_fits() -> None:
    """Returns 0 for no items, no capacity, or items that are all too heavy."""
    assert best_value([(2, 3)], 1) == 0
    assert best_value([], 10) == 0
    assert best_value([(1, 1)], 0) == 0


def test_agrees_with_trying_every_combination() -> None:
    """Matches a recursive search for every small set of items and capacity."""
    for size in range(1, 4):
        for chosen in combinations(POOL, size):
            for capacity in range(13):
                expected = by_recursion(chosen, capacity)
                assert best_value(list(chosen), capacity) == expected, (
                    chosen,
                    capacity,
                )


def test_leaves_the_items_alone() -> None:
    """Does not sort or modify the list of items."""
    items = [(3, 4), (1, 1)]

    best_value(items, 5)

    assert items == [(3, 4), (1, 1)]


def test_fills_a_large_bag() -> None:
    """Handles two hundred items and a capacity of five thousand in time."""
    items = [(weight, weight * 2 - 1) for weight in range(1, 201)]

    assert best_value(items, 5000) == 5000 * 2 - 25

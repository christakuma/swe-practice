"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, combinations_with_replacement

from solution import best_value

type Item = tuple[int, int]


def by_trying_every_selection(items: list[Item], capacity: int) -> int:
    """The best value over every subset whose weights sum to the capacity."""
    best = -1
    for size in range(len(items) + 1):
        for chosen in combinations(items, size):
            if sum(weight for weight, _ in chosen) == capacity:
                best = max(best, sum(value for _, value in chosen))
    return best


def test_fills_the_bag_with_the_best_exact_selection() -> None:
    """Finds the most valuable selection that weighs exactly the capacity."""
    assert best_value([(1, 1), (3, 4), (4, 5), (5, 7)], 7) == 9
    assert best_value([(2, 3), (3, 4), (5, 8)], 5) == 8


def test_a_lighter_load_does_not_count() -> None:
    """Passes over a more valuable selection that leaves the bag short."""
    assert best_value([(3, 10), (4, 1)], 4) == 1
    assert best_value([(1, 100), (2, 1), (3, 1)], 5) == 2


def test_returns_minus_one_when_no_selection_fits_exactly() -> None:
    """Returns -1 when the capacity cannot be hit."""
    assert best_value([(2, 5), (4, 9)], 5) == -1
    assert best_value([(3, 10)], 4) == -1
    assert best_value([(2, 1), (2, 1)], 3) == -1


def test_a_capacity_of_zero_is_filled_by_nothing() -> None:
    """Returns 0 for a capacity of zero, with or without items."""
    assert best_value([(2, 5)], 0) == 0
    assert best_value([], 0) == 0


def test_no_items_fill_nothing_else() -> None:
    """Returns -1 for any positive capacity when there are no items."""
    assert best_value([], 1) == -1
    assert best_value([], 50) == -1


def test_does_not_take_an_item_twice() -> None:
    """Returns -1 when the capacity needs one item more than once."""
    assert best_value([(2, 7)], 4) == -1
    assert best_value([(2, 7), (3, 1)], 6) == -1


def test_equal_items_are_separate_items() -> None:
    """Takes two identical items when the list holds two."""
    assert best_value([(2, 7), (2, 7)], 4) == 14
    assert best_value([(5, 3), (5, 3), (5, 3)], 15) == 9


def test_takes_everything_when_everything_is_needed() -> None:
    """Uses every item for the total weight and fails one beyond it."""
    items = [(1, 2), (2, 3), (3, 4)]

    assert best_value(items, 6) == 9
    assert best_value(items, 7) == -1


def test_the_order_of_the_items_does_not_matter() -> None:
    """Gives the same answer however the items are arranged."""
    items = [(4, 5), (1, 1), (5, 7), (3, 4)]

    assert best_value(items, 7) == 9
    assert best_value(items[::-1], 7) == 9


def test_agrees_with_trying_every_selection() -> None:
    """Matches a search of every subset for every small set of items.

    Every multiset of up to four items with weights 1..3 and values 1, 2 or
    5, at every capacity up to one more than their total weight.
    """
    pool = [(weight, value) for weight in (1, 2, 3) for value in (1, 2, 5)]
    for size in range(5):
        for chosen in combinations_with_replacement(pool, size):
            items = list(chosen)
            for capacity in range(sum(weight for weight, _ in items) + 2):
                expected = by_trying_every_selection(items, capacity)
                assert best_value(items, capacity) == expected, (items, capacity)


def test_leaves_the_items_alone() -> None:
    """Does not modify the list it was given."""
    items = [(3, 4), (1, 1)]

    best_value(items, 4)

    assert items == [(3, 4), (1, 1)]


def test_handles_two_hundred_items() -> None:
    """Handles 200 items and a capacity of 5,000 within the time limit.

    The items weigh 1 to 200 and each is worth its weight plus one, so an
    exact fill is worth 5,000 plus the number of items in it. A hundred
    different weights total at least 5,050, so at most ninety-nine fit, and
    ninety-nine do: 1 to 98 and 149.

    The second set has even weights only, so an odd capacity is impossible.
    """
    items = [(weight, weight + 1) for weight in range(1, 201)]
    evens = [(2 * weight, 1) for weight in range(1, 201)]

    assert sum(range(1, 99)) + 149 == 5000
    assert best_value(items, 5000) == 5099
    assert best_value(evens, 4999) == -1
    assert best_value(evens, 4998) > 0

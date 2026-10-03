"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import best_value


def test_chooses_the_best_combination() -> None:
    """Picks the subset with the most value inside the capacity."""
    items = [(1, 1), (3, 4), (4, 5), (5, 7)]

    assert best_value(items, 7) == 9


def test_beats_the_best_ratio_first() -> None:
    """Beats taking items by value per unit weight.

    By ratio the order is 6, 5, 4 per unit: taking the first two spends 30 of
    the 50 capacity for 160, and the third no longer fits. The last two
    together weigh exactly 50 and are worth 220.
    """
    items = [(10, 60), (20, 100), (30, 120)]

    assert best_value(items, 50) == 220


def test_beats_the_highest_value_first() -> None:
    """Beats taking the single most valuable item first.

    Taking the 30 spends 3 of the 4 capacity and nothing else fits. The two
    cheaper items fit exactly and are worth 40.
    """
    items = [(3, 30), (2, 20), (2, 20)]

    assert best_value(items, 4) == 40


def test_takes_each_item_at_most_once() -> None:
    """Does not take the same item twice to fill the capacity.

    One item of weight 2 and value 3, capacity 6. Taking it three times gives
    9 and is not allowed; the answer is 3. This is the test that fails when the
    inner loop runs upwards.
    """
    assert best_value([(2, 3)], 6) == 3


def test_skips_an_item_that_does_not_fit() -> None:
    """Returns zero when nothing fits."""
    assert best_value([(2, 3)], 1) == 0


def test_handles_no_items() -> None:
    """Returns zero when there is nothing to take."""
    assert best_value([], 5) == 0


def test_handles_zero_capacity() -> None:
    """Returns zero when nothing can be carried."""
    assert best_value([(1, 100)], 0) == 0


def test_chooses_between_two_items_of_equal_weight() -> None:
    """Takes the more valuable of two items that both just fit."""
    assert best_value([(1, 10), (1, 20)], 1) == 20


def test_fills_the_capacity_exactly() -> None:
    """Uses the whole capacity when that is best."""
    assert best_value([(5, 10)], 5) == 10


def test_handles_many_items_quickly() -> None:
    """Solves a problem far too large for an exponential search.

    Two hundred items and a capacity of a thousand. Trying every subset is
    2^200; the table is two hundred passes over a thousand cells.
    """
    items = [(weight, weight * 2) for weight in range(1, 201)]

    assert best_value(items, 1_000) == 2_000

"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import max_profit


def by_states(prices: list[int]) -> int:
    """The best profit, tracked as two states: holding a share, or not.

    A different idea from adding up the rises, on purpose: it makes the
    decision day by day and never looks at a difference between neighbours.
    """
    cash = 0
    holding: int | None = None
    for price in prices:
        bought = cash - price
        sold = cash if holding is None else max(cash, holding + price)
        holding = bought if holding is None else max(holding, bought)
        cash = sold
    return cash


def test_takes_two_trades_when_two_beat_one() -> None:
    """Makes more from two trades than the best single trade allows."""
    assert max_profit([7, 1, 5, 3, 6, 4]) == 7


def test_rides_a_steady_rise() -> None:
    """Collects the whole of an unbroken rise."""
    assert max_profit([1, 2, 3, 4, 5]) == 4


def test_does_nothing_when_prices_only_fall() -> None:
    """Returns 0 when every day is cheaper than the last."""
    assert max_profit([7, 6, 4, 3, 1]) == 0


def test_handles_too_few_days_to_trade() -> None:
    """Returns 0 for no days and for one day."""
    assert max_profit([]) == 0
    assert max_profit([5]) == 0


def test_sits_out_a_dip_between_two_rises() -> None:
    """Sells before a fall and buys again after it."""
    assert max_profit([1, 5, 3, 6]) == 7
    assert max_profit([2, 4, 1, 9]) == 10


def test_ignores_days_the_price_does_not_move() -> None:
    """Makes nothing from a flat stretch."""
    assert max_profit([3, 3, 3]) == 0
    assert max_profit([1, 1, 4, 4, 6]) == 5


def test_agrees_with_a_day_by_day_model_on_every_small_list() -> None:
    """Matches a hold-or-not model for every list of up to six prices."""
    for length in range(7):
        for chosen in product(range(4), repeat=length):
            prices = list(chosen)
            assert max_profit(prices) == by_states(prices), prices


def test_leaves_the_list_alone() -> None:
    """Does not sort or modify the list it was given."""
    prices = [3, 1, 2]

    max_profit(prices)

    assert prices == [3, 1, 2]


def test_handles_a_million_days() -> None:
    """Handles a million days within the time limit.

    A sawtooth: up two, down one, over and over. Each tooth is worth 2, and
    there are a third of a million of them.
    """
    prices = [0, 1, 2] * 333_334

    assert max_profit(prices) == 2 * 333_334

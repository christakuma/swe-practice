"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import max_profit


def best_by_search(prices: list[int]) -> int:
    """The best of every choice of up to four trading days, by brute force."""
    days = range(len(prices))
    best = 0
    for buy, sell in combinations(days, 2):
        best = max(best, prices[sell] - prices[buy])
    for first_buy, first_sell, second_buy, second_sell in combinations(days, 4):
        total = prices[first_sell] - prices[first_buy]
        total += prices[second_sell] - prices[second_buy]
        best = max(best, total)
    for buy, middle, sell in combinations(days, 3):
        best = max(best, prices[sell] - prices[buy], prices[middle] - prices[buy])
    return best


def test_makes_two_trades() -> None:
    """Adds the profit of two separate trades."""
    assert max_profit([3, 3, 5, 0, 0, 3, 1, 4]) == 6


def test_two_trades_beat_the_best_single_one() -> None:
    """Prefers two smaller trades to the one large trade that spans them."""
    assert max_profit([1, 5, 2, 8]) == 10
    assert max_profit([2, 9, 1, 10, 0, 3]) == 16


def test_makes_one_trade_when_that_is_best() -> None:
    """Makes a single trade over a steady rise."""
    assert max_profit([1, 2, 3, 4, 5]) == 4
    assert max_profit([5, 1, 9]) == 8


def test_makes_no_trade_when_prices_only_fall() -> None:
    """Returns 0 when no trade is profitable."""
    assert max_profit([7, 6, 4, 3, 1]) == 0
    assert max_profit([4, 4, 4]) == 0


def test_stops_at_two_trades() -> None:
    """Does not take a third profitable rise."""
    assert max_profit([1, 2, 1, 2, 1, 2]) == 2
    assert max_profit([1, 4, 1, 5, 1, 6]) == 9


def test_picks_the_best_two_of_several_rises() -> None:
    """Chooses the two most valuable rises, wherever they are."""
    assert max_profit([1, 3, 1, 9, 1, 2, 1, 7]) == 14


def test_a_trade_may_ride_through_a_small_dip() -> None:
    """Holds through a dip when selling and rebuying would use up a trade.

    Three rises of 2, 3 and 6. The two largest total 9; holding from 1 to 5
    across the first dip and then trading 4 to 10 makes 10.
    """
    assert max_profit([1, 3, 2, 5, 4, 10]) == 10


def test_handles_short_lists() -> None:
    """Returns 0 for no prices and one price, and trades on two."""
    assert max_profit([]) == 0
    assert max_profit([5]) == 0
    assert max_profit([1, 6]) == 5
    assert max_profit([6, 1]) == 0


def test_agrees_with_brute_force_on_every_short_list() -> None:
    """Matches a search of every pair of trades for every short price list.

    Every list of up to seven prices drawn from 0..3.
    """
    for size in range(8):
        for chosen in product(range(4), repeat=size):
            prices = list(chosen)
            assert max_profit(prices) == best_by_search(prices), prices


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    prices = [3, 1, 4, 1, 5]

    max_profit(prices)

    assert prices == [3, 1, 4, 1, 5]


def test_handles_a_hundred_thousand_prices() -> None:
    """Reads a hundred thousand prices in one pass, within the time limit.

    A sawtooth with two outsized rises in it. Solving both halves afresh at
    every split point is five thousand million steps.
    """
    prices = [10 + day % 7 for day in range(100_000)]
    prices[20_000] = 0
    prices[20_001] = 5_000
    prices[70_000] = 1
    prices[70_003] = 9_000

    assert max_profit(prices) == 5_000 + 8_999
